import json
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any, cast
from uuid import UUID

from opentelemetry import trace
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from vehicle_platform.features.context import FeatureContext, HistoricalPull, TelemetryFeatureSample
from vehicle_platform.features.domain import (
    EntityScope,
    FeatureQuality,
    FeatureSet,
    FeatureSetVersion,
    FeatureValue,
    MissingReason,
    canonical_json,
    require_aware,
    stable_hash,
)
from vehicle_platform.features.registry import DEFAULT_REGISTRY, FeatureRegistry
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.telemetry.domain import SIGNAL_BY_KEY

GENERATOR_VERSION = "phase9a-feature-generator-v2"
SOURCE_SCHEMA_VERSION = "canonical-telemetry-v2"
FEATURE_SET_VERSION = "phase9a-pull-v2"
PRE_PULL_LOOKBACK = timedelta(minutes=5)
MAX_FEATURE_OBSERVATIONS = 50_000
MAX_HISTORY_CANDIDATES = 1_000
MAX_HISTORY_PULLS = 20
MAX_FEATURE_BATCH = 100


class FeatureGenerationLimitError(ValueError):
    pass


class FeatureVersionConflict(ValueError):
    pass


class FeatureLeakageRejected(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def default_feature_version(registry: FeatureRegistry = DEFAULT_REGISTRY) -> FeatureSetVersion:
    return FeatureSetVersion(
        version=FEATURE_SET_VERSION,
        definitions=registry.list(),
        generator_version=GENERATOR_VERSION,
        source_schema_version=SOURCE_SCHEMA_VERSION,
        selection_policy={"scope": "finalized_pull", "history_limit": MAX_HISTORY_PULLS},
        quality_policy={"minimum_signal_coverage": 0.5, "interpolation": "none"},
        temporal_policy={
            "observation_cutoff": "observed_at_and_ingested_at_must_not_exceed_cutoff",
            "pre_pull_telemetry": "latest_vehicle_sample_per_thermal_signal_within_5m_before_pull_start",
            "history": "strictly_prior_pull_start_and_same_vehicle_configuration_and_modifications",
            "event": "event_interval_and_created_at_must_not_exceed_cutoff",
        },
    )


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        decoded = json.loads(value)
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _sample(row: Any) -> TelemetryFeatureSample:
    return TelemetryFeatureSample(
        sample_id=str(row["sample_id"]),
        observed_at=row["observed_at"],
        ingested_at=row["ingested_at"],
        signal=str(row["signal_key"]),
        value=float(row["numeric_value"]),
        unit=str(row["normalized_unit"]),
        quality=str(row["quality"]),
        content_hash=str(row["content_hash"]),
        sequence_number=row["sequence_number"],
    )


def _deduplicate(
    samples: list[TelemetryFeatureSample],
) -> tuple[tuple[TelemetryFeatureSample, ...], int]:
    selected: dict[tuple[datetime, str], TelemetryFeatureSample] = {}
    for sample in sorted(
        samples,
        key=lambda item: (
            item.observed_at,
            item.signal,
            -1 if item.sequence_number is None else item.sequence_number,
            item.sample_id,
        ),
    ):
        selected[(sample.observed_at, sample.signal)] = sample
    return (
        tuple(
            sorted(
                selected.values(), key=lambda item: (item.observed_at, item.signal, item.sample_id)
            )
        ),
        len(samples) - len(selected),
    )


def _modification_ids(
    rows: list[dict[str, Any]], at: datetime, configuration_id: str | None
) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(row["id"])
            for row in rows
            if row["installed_at"] <= at
            and (row["removed_at"] is None or row["removed_at"] > at)
            and (
                row["configuration_id"] is None or str(row["configuration_id"]) == configuration_id
            )
        )
    )


class FeatureGenerationService:
    def __init__(
        self,
        database: Database,
        telemetry: Telemetry | None = None,
        registry: FeatureRegistry = DEFAULT_REGISTRY,
        *,
        stage_timing_observer: Callable[[str, float], None] | None = None,
    ) -> None:
        self.database = database
        self.telemetry = telemetry
        self.registry = registry
        self.stage_timing_observer = stage_timing_observer
        self.tracer = (
            telemetry.tracer if telemetry else trace.get_tracer("vehicle_platform.features")
        )
        self.version = default_feature_version(registry)

    def _observe_stage(self, stage: str, started: float) -> None:
        if self.stage_timing_observer is not None:
            self.stage_timing_observer(stage, max(0.0, perf_counter() - started))

    async def ensure_version(self) -> UUID:
        async with self.database.session() as db:
            await self._ensure_version(db)
            await db.commit()
            row = (
                await db.execute(
                    text("SELECT id FROM feature_set_versions WHERE version=:version"),
                    {"version": self.version.version},
                )
            ).one()
            return cast(UUID, row.id)

    async def _ensure_version(self, db: AsyncSession) -> UUID:
        await db.execute(
            text(
                "INSERT INTO feature_set_versions(version,generator_version,source_schema_version,"
                "feature_definitions,selection_policy,quality_policy,temporal_policy,checksum) "
                "VALUES(:version,:generator,:source_schema,CAST(:definitions AS jsonb),"
                "CAST(:selection AS jsonb),CAST(:quality AS jsonb),CAST(:temporal AS jsonb),:checksum) "
                "ON CONFLICT(version) DO NOTHING"
            ),
            {
                "version": self.version.version,
                "generator": self.version.generator_version,
                "source_schema": self.version.source_schema_version,
                "definitions": canonical_json(
                    [item.manifest() for item in self.version.definitions]
                ),
                "selection": canonical_json(self.version.selection_policy),
                "quality": canonical_json(self.version.quality_policy),
                "temporal": canonical_json(self.version.temporal_policy),
                "checksum": self.version.checksum,
            },
        )
        row = (
            await db.execute(
                text(
                    "SELECT id,checksum FROM feature_set_versions WHERE version=:version FOR SHARE"
                ),
                {"version": self.version.version},
            )
        ).one_or_none()
        if row is None:
            raise RuntimeError("feature set version registration failed")
        if row.checksum != self.version.checksum:
            raise FeatureVersionConflict(
                "registered feature version differs from this code; bump the feature set version"
            )
        return cast(UUID, row.id)

    async def generate_pull(
        self, pull_id: UUID, observation_cutoff: datetime | None = None
    ) -> FeatureSet:
        request_started_at = datetime.now(UTC)
        started_clock = perf_counter()
        outcome = "failed"
        counts: dict[str, int] = {"generated": 0, "reused": 0, "nulls": 0}
        try:
            with self.tracer.start_as_current_span("features.generate") as root:
                async with self.database.session() as db:
                    database_read_started = perf_counter()
                    version_id = await self._ensure_version(db)
                    cutoff = observation_cutoff
                    pull, session, vehicle = await self._load_owner_context(db, pull_id)
                    if cutoff is None:
                        cutoff = max(pull["created_at"], pull["ended_at"])
                    require_aware(cutoff, "observation_cutoff")
                    if pull["created_at"] > cutoff:
                        raise FeatureLeakageRejected("pull_not_observed_by_cutoff")
                    if session["created_at"] > cutoff or vehicle["created_at"] > cutoff:
                        raise FeatureLeakageRejected("entity_context_not_observed_by_cutoff")
                    with self.tracer.start_as_current_span("features.configuration_resolve"):
                        (
                            configuration,
                            config_id,
                            mods,
                            config_available,
                        ) = await self._resolve_context(db, pull, session, vehicle, cutoff)
                    with self.tracer.start_as_current_span("features.telemetry_read"):
                        current_rows = await self._load_pull_samples(db, pull, cutoff)
                        pre_pull_rows = await self._load_pre_pull_samples(db, pull, cutoff)
                        candidates, all_history_mods = await self._load_history_candidates(
                            db, pull, config_id, cutoff
                        )
                        current_mod_ids = _modification_ids(mods, pull["started_at"], config_id)
                        compatible = []
                        for candidate in candidates:
                            if self._compatible_history(
                                candidate, pull, config_id, current_mod_ids, all_history_mods
                            ):
                                compatible.append(candidate)
                        prior_pulls = await self._load_prior_samples(
                            db, compatible[:MAX_HISTORY_PULLS], cutoff
                        )
                        events = await self._load_prior_events(db, pull, config_id, cutoff)
                    self._observe_stage("database_read", database_read_started)
                    compute_started = perf_counter()
                    context = self._build_context(
                        pull=pull,
                        session=session,
                        vehicle=vehicle,
                        configuration=configuration,
                        modifications=mods,
                        current_rows=current_rows,
                        pre_pull_rows=pre_pull_rows,
                        prior_pulls=prior_pulls,
                        prior_pull_count=len(compatible),
                        session_prior_pull_count=sum(
                            candidate["session_id"] == pull["session_id"]
                            for candidate in compatible
                        ),
                        events=events,
                        cutoff=cutoff,
                        config_id=config_id,
                        config_available=config_available,
                    )
                    with self.tracer.start_as_current_span("features.compute"):
                        values = self.registry.compute(context)
                    counts["nulls"] = sum(item.value is None for item in values.values())
                    source_payload = self._source_payload(
                        pull,
                        session,
                        vehicle,
                        configuration,
                        mods,
                        current_rows,
                        pre_pull_rows,
                        compatible,
                        prior_pulls,
                        events,
                        cutoff,
                    )
                    source_hash = stable_hash(source_payload)
                    provenance = self._provenance(context, values, source_hash, source_payload)
                    provenance_hash = stable_hash(
                        {
                            "vehicle_id": context.vehicle_id,
                            "configuration_id": config_id,
                            "session_id": context.session_id,
                            "pull_id": context.pull_id,
                            "source_hash": source_hash,
                            "feature_set_version": self.version.version,
                            "generator_version": self.version.generator_version,
                        }
                    )
                    self._observe_stage("compute", compute_started)
                    persistence_started = perf_counter()
                    lock = int(
                        stable_hash(
                            [context.pull_id, self.version.version, cutoff.isoformat(), source_hash]
                        )[:16],
                        16,
                    ) & ((1 << 63) - 1)
                    with self.tracer.start_as_current_span("features.persistence") as span:
                        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
                        inserted = (
                            await db.execute(
                                text(
                                    "INSERT INTO feature_sets(vehicle_id,configuration_id,session_id,pull_id,"
                                    "entity_scope,feature_set_version_id,source_window_start,source_window_end,"
                                    "observation_cutoff,feature_values,quality_metadata,provenance,source_hash,"
                                    "provenance_hash,generator_version) VALUES(:vehicle,:configuration,:session,:pull,"
                                    "'pull',:version,:source_start,:source_end,:cutoff,CAST(:values AS jsonb),"
                                    "CAST(:quality AS jsonb),CAST(:provenance AS jsonb),:source_hash,:provenance_hash,:generator) "
                                    "ON CONFLICT ON CONSTRAINT uq_feature_set_identity DO NOTHING RETURNING id,generated_at"
                                ),
                                {
                                    "vehicle": UUID(context.vehicle_id),
                                    "configuration": UUID(config_id) if config_id else None,
                                    "session": UUID(context.session_id),
                                    "pull": UUID(context.pull_id),
                                    "version": version_id,
                                    "source_start": pull["started_at"],
                                    "source_end": max(
                                        pull["started_at"], min(pull["ended_at"], cutoff)
                                    ),
                                    "cutoff": cutoff,
                                    "values": canonical_json(
                                        {key: value.manifest() for key, value in values.items()}
                                    ),
                                    "quality": canonical_json(context.quality_metadata),
                                    "provenance": canonical_json(provenance),
                                    "source_hash": source_hash,
                                    "provenance_hash": provenance_hash,
                                    "generator": self.version.generator_version,
                                },
                            )
                        ).one_or_none()
                        span.set_attribute("feature_set_version", self.version.version)
                    if inserted is None:
                        existing = (
                            (
                                await db.execute(
                                    text(
                                        "SELECT * "
                                        "FROM feature_sets WHERE vehicle_id=:vehicle AND entity_scope='pull' "
                                        "AND pull_id=:pull AND feature_set_version_id=:version AND source_hash=:source_hash"
                                    ),
                                    {
                                        "vehicle": UUID(context.vehicle_id),
                                        "pull": UUID(context.pull_id),
                                        "version": version_id,
                                        "source_hash": source_hash,
                                    },
                                )
                            )
                            .mappings()
                            .one()
                        )
                        feature_set = self._to_feature_set(
                            existing,
                            context,
                            source_hash,
                            self.version.version,
                            provenance_hash=str(existing["provenance_hash"]),
                        )
                        counts["reused"] = 1
                        outcome = "reused"
                    else:
                        await self._write_generation_run(
                            db,
                            version_id,
                            pull_id,
                            status="completed",
                            generated=1,
                            reused=0,
                            failed=0,
                            source_hash=source_hash,
                            started_at=request_started_at,
                        )
                        await db.commit()
                        row = await self._fetch_feature_set(db, inserted.id)
                        feature_set = self._to_feature_set(
                            row,
                            context,
                            source_hash,
                            self.version.version,
                            provenance_hash=provenance_hash,
                        )
                        counts["generated"] = 1
                        outcome = "generated"
                    if counts["reused"]:
                        await self._write_generation_run(
                            db,
                            version_id,
                            pull_id,
                            status="completed",
                            generated=0,
                            reused=1,
                            failed=0,
                            source_hash=source_hash,
                            started_at=request_started_at,
                        )
                        await db.commit()
                    self._observe_stage("persistence", persistence_started)
                    root.set_attribute("feature_set_version", self.version.version)
                    root.set_attribute("feature_count", len(values))
                    root.set_attribute("null_count", counts["nulls"])
            if self.telemetry:
                self.telemetry.feature_generation_runs.add(1, {"outcome": outcome})
                self.telemetry.feature_sets_generated.add(
                    counts["generated"], {"outcome": "generated"}
                )
                self.telemetry.feature_sets_generated.add(counts["reused"], {"outcome": "reused"})
                for key, value in values.items():
                    if value.value is None:
                        definition = self.registry.resolve(key)
                        self.telemetry.feature_null_values.add(
                            1,
                            {
                                "category": definition.category.value,
                                "reason": value.missing_reason.value
                                if value.missing_reason
                                else "unknown",
                            },
                        )
            return feature_set
        except FeatureLeakageRejected as exc:
            if self.telemetry:
                self.telemetry.leakage_rejections.add(1, {"reason": exc.reason})
            await self._record_failure(pull_id, exc, started_at=request_started_at)
            raise
        except Exception as exc:
            await self._record_failure(pull_id, exc, started_at=request_started_at)
            raise
        finally:
            if self.telemetry:
                self.telemetry.feature_generation_duration.record(
                    perf_counter() - started_clock, {"outcome": outcome}
                )
                if outcome == "failed":
                    self.telemetry.feature_generation_failures.add(1, {"error": "generation_error"})

    async def generate_session(
        self,
        session_id: UUID,
        *,
        observation_cutoff: datetime | None = None,
        max_pulls: int = MAX_FEATURE_BATCH,
    ) -> dict[str, Any]:
        if not 1 <= max_pulls <= MAX_FEATURE_BATCH:
            raise ValueError(f"max_pulls must be between 1 and {MAX_FEATURE_BATCH}")
        async with self.database.session() as db:
            ids = (
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE session_id=:session ORDER BY started_at,id LIMIT :limit"
                        ),
                        {"session": session_id, "limit": max_pulls + 1},
                    )
                )
                .scalars()
                .all()
            )
        if len(ids) > max_pulls:
            raise FeatureGenerationLimitError("session exceeds bounded feature-generation batch")
        generated = reused = failed = 0
        errors: list[str] = []
        source_hashes: list[str] = []
        for pull_id in ids:
            try:
                request_started = datetime.now(UTC)
                result = await self.generate_pull(pull_id, observation_cutoff)
                source_hashes.append(result.source_hash)
                if result.generated_at < request_started:
                    reused += 1
                else:
                    generated += 1
            except Exception as exc:
                failed += 1
                errors.append(type(exc).__name__[:80])
        return {
            "session_id": str(session_id),
            "feature_set_version": self.version.version,
            "generated": generated,
            "reused": reused,
            "failed": failed,
            "error_categories": sorted(set(errors)),
            "source_snapshot_hash": stable_hash(sorted(source_hashes)) if source_hashes else None,
        }

    async def estimate_session(
        self, session_id: UUID, *, max_pulls: int = MAX_FEATURE_BATCH
    ) -> dict[str, Any]:
        if not 1 <= max_pulls <= MAX_FEATURE_BATCH:
            raise ValueError(f"max_pulls must be between 1 and {MAX_FEATURE_BATCH}")
        async with self.database.session() as db:
            pull_ids = (
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE session_id=:session ORDER BY started_at,id LIMIT :limit"
                        ),
                        {"session": session_id, "limit": max_pulls + 1},
                    )
                )
                .scalars()
                .all()
            )
            version_id = (
                await db.execute(
                    text("SELECT id FROM feature_set_versions WHERE version=:version"),
                    {"version": self.version.version},
                )
            ).scalar_one_or_none()
            existing_count = 0
            if version_id is not None and pull_ids:
                existing_count = await db.scalar(
                    text(
                        "SELECT count(DISTINCT pull_id) FROM feature_sets "
                        "WHERE feature_set_version_id=:version AND pull_id=ANY(:pulls)"
                    ),
                    {"version": version_id, "pulls": pull_ids[:max_pulls]},
                )
        exceeds_batch = len(pull_ids) > max_pulls
        bounded_count = min(len(pull_ids), max_pulls)
        return {
            "session_id": str(session_id),
            "feature_set_version": self.version.version,
            "candidate_pulls": bounded_count,
            "reusable_feature_sets": int(existing_count or 0),
            "expected_new_feature_sets": max(0, bounded_count - int(existing_count or 0)),
            "exceeds_batch_limit": exceeds_batch,
            "max_pulls": max_pulls,
            "mutates_database": False,
        }

    async def _load_owner_context(
        self, db: AsyncSession, pull_id: UUID
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        row = (
            (
                await db.execute(
                    text(
                        "SELECT p.*,s.started_at AS session_started_at,s.ended_at AS session_ended_at,"
                        "s.status AS session_status,s.metadata AS session_metadata,s.configuration_id AS session_configuration_id,"
                        "s.created_at AS session_created_at,s.source_type AS session_source_type,"
                        "v.manufacturer AS vehicle_manufacturer,v.model AS vehicle_model,v.generation AS vehicle_generation,"
                        "v.model_year AS vehicle_model_year,v.engine_code AS vehicle_engine_code,"
                        "v.transmission AS vehicle_transmission,v.created_at AS vehicle_created_at "
                        "FROM pulls p JOIN driving_sessions s ON s.id=p.session_id "
                        "JOIN vehicles v ON v.id=p.vehicle_id WHERE p.id=:id"
                    ),
                    {"id": pull_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise LookupError("pull not found")
        pull = dict(row)
        session = {
            "id": pull["session_id"],
            "started_at": pull["session_started_at"],
            "ended_at": pull["session_ended_at"],
            "status": pull["session_status"],
            "metadata": _json_object(pull["session_metadata"]),
            "configuration_id": pull["session_configuration_id"],
            "created_at": pull["session_created_at"],
            "source_type": pull["session_source_type"],
        }
        vehicle = {
            "id": pull["vehicle_id"],
            "manufacturer": pull["vehicle_manufacturer"],
            "model": pull["vehicle_model"],
            "generation": pull["vehicle_generation"],
            "model_year": pull["vehicle_model_year"],
            "engine_code": pull["vehicle_engine_code"],
            "transmission": pull["vehicle_transmission"],
            "created_at": pull["vehicle_created_at"],
        }
        return pull, session, vehicle

    async def _resolve_context(
        self,
        db: AsyncSession,
        pull: dict[str, Any],
        session: dict[str, Any],
        vehicle: dict[str, Any],
        cutoff: datetime,
    ) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]], datetime]:
        explicit_id = session["configuration_id"] or pull["configuration_id"]
        configuration: Any = None
        if explicit_id:
            configuration = (
                (
                    await db.execute(
                        text(
                            "SELECT * FROM vehicle_configurations WHERE id=:id AND vehicle_id=:vehicle "
                            "AND created_at<=:cutoff"
                        ),
                        {"id": explicit_id, "vehicle": pull["vehicle_id"], "cutoff": cutoff},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if configuration is not None and not (
                configuration["effective_at"] <= pull["started_at"]
                and (
                    configuration["ended_at"] is None
                    or configuration["ended_at"] > pull["started_at"]
                )
            ):
                configuration = None
        if configuration is None:
            configuration = (
                (
                    await db.execute(
                        text(
                            "SELECT * FROM vehicle_configurations WHERE vehicle_id=:vehicle "
                            "AND effective_at<=:at AND (ended_at IS NULL OR ended_at>:at) "
                            "AND created_at<=:cutoff ORDER BY effective_at DESC,id LIMIT 1"
                        ),
                        {"vehicle": pull["vehicle_id"], "at": pull["started_at"], "cutoff": cutoff},
                    )
                )
                .mappings()
                .one_or_none()
            )
        configuration = dict(configuration) if configuration else None
        config_id = str(configuration["id"]) if configuration else None
        mods = (
            (
                await db.execute(
                    text(
                        "SELECT * FROM modifications WHERE vehicle_id=:vehicle AND installed_at<=:at "
                        "AND (removed_at IS NULL OR removed_at>:at) AND created_at<=:cutoff "
                        "AND (configuration_id IS NULL OR configuration_id=CAST(:configuration AS uuid)) "
                        "ORDER BY installed_at,id LIMIT 1001"
                    ),
                    {
                        "vehicle": pull["vehicle_id"],
                        "at": pull["started_at"],
                        "cutoff": cutoff,
                        "configuration": config_id,
                    },
                )
            )
            .mappings()
            .all()
        )
        if len(mods) > 1000:
            raise FeatureGenerationLimitError(
                "configuration modification context exceeds 1000 rows"
            )
        modification_rows = [dict(item) for item in mods]
        config_recorded = configuration["created_at"] if configuration else session["created_at"]
        metadata_available = max(
            [vehicle["created_at"], session["created_at"], pull["created_at"], config_recorded]
            + [row["created_at"] for row in modification_rows]
        )
        return configuration, config_id, modification_rows, cast(datetime, metadata_available)

    async def _load_pull_samples(
        self, db: AsyncSession, pull: dict[str, Any], cutoff: datetime
    ) -> list[TelemetryFeatureSample]:
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT sample_id,observed_at,ingested_at,signal_key,numeric_value,normalized_unit,"
                        "quality,content_hash,sequence_number FROM telemetry_samples "
                        "WHERE session_id=:session AND observed_at>=:start AND observed_at<=:end "
                        "AND observed_at<=:cutoff AND ingested_at<=:cutoff AND signal_key=ANY(:signals) "
                        "ORDER BY observed_at,signal_key,COALESCE(sequence_number,-1),sample_id LIMIT :limit"
                    ),
                    {
                        "session": pull["session_id"],
                        "start": pull["started_at"],
                        "end": pull["ended_at"],
                        "cutoff": cutoff,
                        "signals": list(SIGNAL_BY_KEY),
                        "limit": MAX_FEATURE_OBSERVATIONS + 1,
                    },
                )
            )
            .mappings()
            .all()
        )
        if len(rows) > MAX_FEATURE_OBSERVATIONS:
            raise FeatureGenerationLimitError("pull exceeds 50000 selected telemetry observations")
        return [_sample(row) for row in rows]

    async def _load_pre_pull_samples(
        self, db: AsyncSession, pull: dict[str, Any], cutoff: datetime
    ) -> list[TelemetryFeatureSample]:
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT DISTINCT ON (signal_key) sample_id,observed_at,ingested_at,signal_key,"
                        "numeric_value,normalized_unit,quality,content_hash,sequence_number "
                        "FROM telemetry_samples JOIN driving_sessions s "
                        "ON s.id=telemetry_samples.session_id AND s.vehicle_id=telemetry_samples.vehicle_id "
                        "AND s.created_at<=:cutoff AND s.started_at<=:cutoff "
                        "WHERE telemetry_samples.vehicle_id=:vehicle "
                        "AND observed_at>=:lookback AND observed_at<:start "
                        "AND observed_at<=:cutoff AND ingested_at<=:cutoff "
                        "AND signal_key=ANY(:signals) "
                        "ORDER BY signal_key,observed_at DESC,COALESCE(sequence_number,-1) DESC,sample_id DESC"
                    ),
                    {
                        "vehicle": pull["vehicle_id"],
                        "lookback": pull["started_at"] - PRE_PULL_LOOKBACK,
                        "start": pull["started_at"],
                        "cutoff": cutoff,
                        "signals": [
                            "engine.intake_air_temperature",
                            "engine.oil_temperature",
                            "engine.coolant_temperature",
                        ],
                    },
                )
            )
            .mappings()
            .all()
        )
        return sorted(
            (_sample(row) for row in rows),
            key=lambda item: (item.observed_at, item.signal, item.sample_id),
        )

    async def _load_history_candidates(
        self,
        db: AsyncSession,
        pull: dict[str, Any],
        configuration_id: str | None,
        cutoff: datetime,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT p.*,s.configuration_id AS session_configuration_id,s.started_at AS source_session_started_at,"
                        "s.created_at AS source_session_created_at,"
                        "COALESCE((SELECT vc.id FROM vehicle_configurations vc WHERE vc.id=s.configuration_id "
                        "AND vc.vehicle_id=p.vehicle_id AND vc.effective_at<=p.started_at "
                        "AND (vc.ended_at IS NULL OR vc.ended_at>p.started_at) AND vc.created_at<=:cutoff),"
                        "(SELECT vc.id FROM vehicle_configurations vc WHERE vc.vehicle_id=p.vehicle_id "
                        "AND vc.effective_at<=p.started_at AND (vc.ended_at IS NULL OR vc.ended_at>p.started_at) "
                        "AND vc.created_at<=:cutoff ORDER BY vc.effective_at DESC,vc.id LIMIT 1)) AS effective_configuration_id "
                        "FROM pulls p JOIN driving_sessions s ON s.id=p.session_id "
                        "WHERE p.vehicle_id=:vehicle AND p.id<>:pull AND p.ended_at<:pull_start "
                        "AND p.created_at<=:cutoff AND s.created_at<=:cutoff AND s.started_at<=:pull_start "
                        "ORDER BY p.started_at DESC,p.id DESC LIMIT :limit"
                    ),
                    {
                        "vehicle": pull["vehicle_id"],
                        "pull": pull["id"],
                        "pull_start": pull["started_at"],
                        "cutoff": cutoff,
                        "limit": MAX_HISTORY_CANDIDATES + 1,
                    },
                )
            )
            .mappings()
            .all()
        )
        if len(rows) > MAX_HISTORY_CANDIDATES:
            raise FeatureGenerationLimitError(
                "compatible history candidate scan exceeds 1000 pulls"
            )
        candidates = [dict(row) for row in rows]
        modifications = (
            (
                await db.execute(
                    text(
                        "SELECT id,configuration_id,category,installed_at,removed_at,created_at "
                        "FROM modifications WHERE vehicle_id=:vehicle AND created_at<=:cutoff "
                        "AND installed_at<=:pull_start ORDER BY installed_at,id LIMIT 1001"
                    ),
                    {
                        "vehicle": pull["vehicle_id"],
                        "cutoff": cutoff,
                        "pull_start": pull["started_at"],
                    },
                )
            )
            .mappings()
            .all()
        )
        if len(modifications) > 1000:
            raise FeatureGenerationLimitError("historical modification scan exceeds 1000 rows")
        return candidates, [dict(row) for row in modifications]

    def _compatible_history(
        self,
        candidate: dict[str, Any],
        pull: dict[str, Any],
        configuration_id: str | None,
        current_mod_ids: tuple[str, ...],
        modifications: list[dict[str, Any]],
    ) -> bool:
        candidate_config = (
            str(candidate["effective_configuration_id"])
            if candidate["effective_configuration_id"]
            else None
        )
        if configuration_id is None:
            if candidate["session_id"] != pull["session_id"] or candidate_config is not None:
                return False
        elif candidate_config != configuration_id:
            return False
        prior_mod_ids = _modification_ids(modifications, candidate["started_at"], candidate_config)
        candidate["active_modification_ids"] = list(prior_mod_ids)
        return current_mod_ids == prior_mod_ids

    async def _load_prior_samples(
        self,
        db: AsyncSession,
        candidates: list[dict[str, Any]],
        cutoff: datetime,
    ) -> tuple[HistoricalPull, ...]:
        if not candidates:
            return ()
        ids = [row["id"] for row in candidates]
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT p.id AS pull_id,t.sample_id,t.observed_at,t.ingested_at,t.signal_key,"
                        "t.numeric_value,t.normalized_unit,t.quality,t.content_hash,t.sequence_number "
                        "FROM pulls p JOIN telemetry_samples t ON t.session_id=p.session_id "
                        "AND t.observed_at>=p.started_at AND t.observed_at<=p.ended_at "
                        "WHERE p.id=ANY(:ids) AND t.observed_at<=:cutoff AND t.ingested_at<=:cutoff "
                        "AND t.quality='valid' AND t.signal_key=ANY(:signals) "
                        "ORDER BY p.started_at DESC,p.id,t.observed_at,t.signal_key,COALESCE(t.sequence_number,-1),t.sample_id LIMIT :limit"
                    ),
                    {
                        "ids": ids,
                        "cutoff": cutoff,
                        "signals": list(SIGNAL_BY_KEY),
                        "limit": MAX_FEATURE_OBSERVATIONS + 1,
                    },
                )
            )
            .mappings()
            .all()
        )
        if len(rows) > MAX_FEATURE_OBSERVATIONS:
            raise FeatureGenerationLimitError(
                "historical feature read exceeds 50000 telemetry observations"
            )
        grouped: dict[str, list[TelemetryFeatureSample]] = defaultdict(list)
        for row in rows:
            grouped[str(row["pull_id"])].append(_sample(row))
        return tuple(
            HistoricalPull(
                row=candidate,
                samples=_deduplicate(grouped.get(str(candidate["id"]), []))[0],
                effective_configuration_id=(
                    str(candidate["effective_configuration_id"])
                    if candidate["effective_configuration_id"]
                    else None
                ),
            )
            for candidate in candidates
        )

    async def _load_prior_events(
        self,
        db: AsyncSession,
        pull: dict[str, Any],
        configuration_id: str | None,
        cutoff: datetime,
    ) -> tuple[dict[str, Any], ...]:
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT e.id,e.vehicle_id,e.session_id,e.pull_id,e.event_type,e.category,e.started_at,e.ended_at,e.created_at,"
                        "COALESCE((SELECT vc.id FROM vehicle_configurations vc WHERE vc.id=s.configuration_id "
                        "AND vc.vehicle_id=e.vehicle_id AND vc.effective_at<=e.started_at "
                        "AND (vc.ended_at IS NULL OR vc.ended_at>e.started_at) AND vc.created_at<=:cutoff),"
                        "(SELECT vc.id FROM vehicle_configurations vc WHERE vc.vehicle_id=e.vehicle_id "
                        "AND vc.effective_at<=e.started_at AND (vc.ended_at IS NULL OR vc.ended_at>e.started_at) "
                        "AND vc.created_at<=:cutoff ORDER BY vc.effective_at DESC,vc.id LIMIT 1)) AS effective_configuration_id "
                        "FROM detected_events e JOIN driving_sessions s ON s.id=e.session_id "
                        "WHERE e.vehicle_id=:vehicle AND e.started_at<:pull_start AND e.ended_at<:pull_start "
                        "AND e.ended_at<=:cutoff "
                        "AND e.created_at<=:cutoff AND s.created_at<=:cutoff AND s.started_at<=:pull_start "
                        "ORDER BY e.started_at,e.id LIMIT 1001"
                    ),
                    {
                        "vehicle": pull["vehicle_id"],
                        "pull_start": pull["started_at"],
                        "cutoff": cutoff,
                    },
                )
            )
            .mappings()
            .all()
        )
        if len(rows) > 1000:
            raise FeatureGenerationLimitError("prior event scan exceeds 1000 events")
        timeline_rows = (
            (
                await db.execute(
                    text(
                        "SELECT id,configuration_id,category,installed_at,removed_at,created_at "
                        "FROM modifications WHERE vehicle_id=:vehicle AND installed_at<=:pull_start "
                        "AND created_at<=:cutoff ORDER BY installed_at,id LIMIT 1001"
                    ),
                    {
                        "vehicle": pull["vehicle_id"],
                        "pull_start": pull["started_at"],
                        "cutoff": cutoff,
                    },
                )
            )
            .mappings()
            .all()
        )
        if len(timeline_rows) > 1000:
            raise FeatureGenerationLimitError("event modification timeline exceeds 1000 rows")
        timeline_modifications = [dict(item) for item in timeline_rows]
        compatible: list[dict[str, Any]] = []
        for row in rows:
            configuration = (
                str(row["effective_configuration_id"])
                if row["effective_configuration_id"]
                else None
            )
            if configuration != configuration_id or (
                configuration_id is None and row["session_id"] != pull["session_id"]
            ):
                continue
            active = _modification_ids(timeline_modifications, row["started_at"], configuration)
            current_active = _modification_ids(
                timeline_modifications, pull["started_at"], configuration_id
            )
            if active != current_active:
                continue
            compatible.append(dict(row))
        return tuple(compatible)

    def _build_context(
        self,
        *,
        pull: dict[str, Any],
        session: dict[str, Any],
        vehicle: dict[str, Any],
        configuration: dict[str, Any] | None,
        modifications: list[dict[str, Any]],
        current_rows: list[TelemetryFeatureSample],
        pre_pull_rows: list[TelemetryFeatureSample],
        prior_pulls: tuple[HistoricalPull, ...],
        prior_pull_count: int,
        session_prior_pull_count: int,
        events: tuple[dict[str, Any], ...],
        cutoff: datetime,
        config_id: str | None,
        config_available: datetime,
    ) -> FeatureContext:
        deduplicated, duplicate_count = _deduplicate(current_rows)
        valid = tuple(item for item in deduplicated if item.quality == "valid")
        timestamps = {item.observed_at for item in deduplicated}
        frame_count = len(timestamps)
        metadata = _json_object(pull.get("metadata"))
        declared = metadata.get("available_signals")
        expected_signals = (
            [str(signal) for signal in declared if signal in SIGNAL_BY_KEY]
            if isinstance(declared, list)
            else sorted({item.signal for item in deduplicated})
        )
        signal_counts: dict[str, int] = {
            signal: len({item.observed_at for item in valid if item.signal == signal})
            for signal in expected_signals
        }
        coverage = {
            signal: min(1.0, count / frame_count) if frame_count else 0.0
            for signal, count in signal_counts.items()
        }
        source_type = str(session["source_type"])
        declared_role = session["metadata"].get("data_role")
        if source_type == "synthetic":
            data_role = "synthetic"
        elif declared_role in {"synthetic", "real_vehicle", "imported", "imported_fixture"}:
            data_role = declared_role
        elif source_type in {"csv", "replay"}:
            data_role = (
                "imported_fixture" if session["metadata"].get("fixture") is True else "imported"
            )
        else:
            data_role = "real_vehicle"
        quality = {
            "source_type": source_type,
            "data_role": data_role,
            "observation_cutoff": cutoff.isoformat(),
            "raw_observation_count": len(current_rows),
            "valid_observation_count": len(valid),
            "invalid_observation_count": sum(item.quality != "valid" for item in current_rows),
            "duplicate_timestamp_count": duplicate_count,
            "timestamp_frame_count": frame_count,
            "expected_signals": expected_signals,
            "signal_coverage": coverage,
            "available_signals": sorted(signal for signal, count in signal_counts.items() if count),
            "pull_completeness": float(pull.get("data_completeness") or 0.0),
            "quality_flags": sorted(str(item) for item in (pull.get("quality_flags") or [])),
            "interpolation": "none",
        }
        context_available = max(session["created_at"], pull["created_at"])
        repeated_pull_index = session_prior_pull_count + 1
        return FeatureContext(
            pull=pull,
            session=session,
            vehicle=vehicle,
            configuration=configuration,
            modifications=tuple(modifications),
            raw_samples=deduplicated,
            valid_samples=valid,
            prior_pulls=prior_pulls,
            prior_pull_count=prior_pull_count,
            repeated_pull_index=repeated_pull_index,
            events=events,
            observation_cutoff=cutoff,
            effective_configuration_id=config_id,
            context_available_at=context_available,
            configuration_available_at=config_available,
            signal_coverage=coverage,
            frame_count=frame_count,
            quality_metadata=quality,
            pre_pull_samples=tuple(pre_pull_rows),
        )

    def _source_payload(
        self,
        pull: dict[str, Any],
        session: dict[str, Any],
        vehicle: dict[str, Any],
        configuration: dict[str, Any] | None,
        modifications: list[dict[str, Any]],
        current_rows: list[TelemetryFeatureSample],
        pre_pull_rows: list[TelemetryFeatureSample],
        candidates: list[dict[str, Any]],
        prior_pulls: tuple[HistoricalPull, ...],
        events: tuple[dict[str, Any], ...],
        cutoff: datetime,
    ) -> dict[str, Any]:
        return {
            "vehicle": {
                "id": str(vehicle["id"]),
                "manufacturer": vehicle["manufacturer"],
                "model": vehicle["model"],
                "generation": vehicle["generation"],
                "model_year": vehicle["model_year"],
                "engine_code": vehicle["engine_code"],
                "transmission": vehicle["transmission"],
                "created_at": vehicle["created_at"].isoformat(),
            },
            "configuration": self._configuration_source(configuration),
            "active_modifications": [self._modification_source(item) for item in modifications],
            "session": {
                "id": str(session["id"]),
                "started_at": session["started_at"].isoformat() if session["started_at"] else None,
                "ended_at": session["ended_at"].isoformat() if session["ended_at"] else None,
                "created_at": session["created_at"].isoformat(),
                "source_type": session["source_type"],
                "status": session["status"],
                "metadata": session["metadata"],
            },
            "pull": self._pull_source(pull),
            "telemetry": [self._sample_source(item) for item in current_rows],
            "pre_pull_telemetry": [self._sample_source(item) for item in pre_pull_rows],
            "prior_candidates": [
                {
                    "id": str(item["id"]),
                    "session_id": str(item["session_id"]),
                    "started_at": item["started_at"].isoformat(),
                    "ended_at": item["ended_at"].isoformat(),
                    "created_at": item["created_at"].isoformat(),
                    "configuration_id": str(item["effective_configuration_id"])
                    if item["effective_configuration_id"]
                    else None,
                    "active_modification_ids": item.get("active_modification_ids", []),
                }
                for item in candidates
            ],
            "prior_pull_samples": [
                {
                    "pull_id": prior.id,
                    "samples": [self._sample_source(item) for item in prior.samples],
                }
                for prior in prior_pulls
            ],
            "events": [
                {
                    "id": str(item["id"]),
                    "session_id": str(item["session_id"]),
                    "pull_id": str(item["pull_id"]) if item["pull_id"] else None,
                    "type": item["event_type"],
                    "started_at": item["started_at"].isoformat(),
                    "ended_at": item["ended_at"].isoformat(),
                    "created_at": item["created_at"].isoformat(),
                }
                for item in events
            ],
            "cutoff": cutoff.isoformat(),
            "feature_set_version_checksum": self.version.checksum,
        }

    @staticmethod
    def _configuration_source(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "id": str(row["id"]),
            "vehicle_id": str(row["vehicle_id"]),
            "effective_at": row["effective_at"].isoformat(),
            "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
            "created_at": row["created_at"].isoformat(),
            "description": row["description"],
            "metadata": row["metadata"],
            "provenance": row["provenance"],
        }

    @staticmethod
    def _modification_source(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "configuration_id": str(row["configuration_id"]) if row["configuration_id"] else None,
            "category": row["category"],
            "manufacturer": row["manufacturer"],
            "product": row["product"],
            "installed_at": row["installed_at"].isoformat(),
            "removed_at": row["removed_at"].isoformat() if row["removed_at"] else None,
            "created_at": row["created_at"].isoformat(),
        }

    @staticmethod
    def _pull_source(row: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "id",
            "session_id",
            "vehicle_id",
            "configuration_id",
            "started_at",
            "ended_at",
            "created_at",
            "detector_name",
            "algorithm_version",
            "configuration_hash",
            "data_completeness",
            "sample_count",
            "quality_flags",
            "metadata",
        )
        return {
            key: row[key].isoformat() if isinstance(row[key], datetime) else row[key]
            for key in keys
        }

    @staticmethod
    def _sample_source(sample: TelemetryFeatureSample) -> dict[str, Any]:
        return {
            "sample_id": sample.sample_id,
            "observed_at": sample.observed_at.isoformat(),
            "ingested_at": sample.ingested_at.isoformat(),
            "signal": sample.signal,
            "value": sample.value,
            "unit": sample.unit,
            "quality": sample.quality,
            "content_hash": sample.content_hash,
            "sequence_number": sample.sequence_number,
        }

    def _provenance(
        self,
        context: FeatureContext,
        values: dict[str, FeatureValue],
        source_hash: str,
        source_payload: dict[str, Any],
    ) -> dict[str, Any]:
        definitions = {item.key: item for item in self.version.definitions}
        return {
            "vehicle_id": context.vehicle_id,
            "configuration_id": context.effective_configuration_id,
            "session_id": context.session_id,
            "pull_id": context.pull_id,
            "source_hash": source_hash,
            "source_window": {
                "start": context.start.isoformat(),
                "end": max(context.start, min(context.end, context.observation_cutoff)).isoformat(),
                "observation_cutoff": context.observation_cutoff.isoformat(),
            },
            "feature_set_version": self.version.version,
            "generator_version": self.version.generator_version,
            "source_schema_version": self.version.source_schema_version,
            "lineage": {
                key: {
                    "algorithm_id": definitions[key].algorithm_id,
                    "algorithm_version": definitions[key].algorithm_version,
                    **value.manifest(),
                }
                for key, value in values.items()
            },
            "source_context": {
                "configuration": source_payload["configuration"],
                "active_modifications": source_payload["active_modifications"],
                "active_modification_ids": sorted(
                    str(item["id"]) for item in source_payload["active_modifications"]
                ),
                "prior_candidates": source_payload["prior_candidates"][:MAX_HISTORY_PULLS],
                "prior_candidate_count": len(source_payload["prior_candidates"]),
                "event_count": len(source_payload["events"]),
            },
        }

    async def _write_generation_run(
        self,
        db: AsyncSession,
        version_id: UUID,
        pull_id: UUID,
        *,
        status: str,
        generated: int,
        reused: int,
        failed: int,
        source_hash: str | None,
        started_at: datetime,
        error_categories: tuple[str, ...] = (),
    ) -> None:
        span_context = trace.get_current_span().get_span_context()
        trace_id = format(span_context.trace_id, "032x") if span_context.is_valid else None
        await db.execute(
            text(
                "INSERT INTO feature_generation_runs(feature_set_version_id,requested_scope,requested_entity_id,"
                "status,generated_count,reused_count,failed_count,error_categories,source_snapshot_hash,trace_id,started_at) "
                "VALUES(:version,'pull',:pull,:status,:generated,:reused,:failed,:errors,:source,:trace,:started)"
            ),
            {
                "version": version_id,
                "pull": pull_id,
                "status": status,
                "generated": generated,
                "reused": reused,
                "failed": failed,
                "errors": list(error_categories),
                "source": source_hash,
                "trace": trace_id,
                "started": started_at,
            },
        )

    async def _record_failure(
        self, pull_id: UUID, error: Exception, *, started_at: datetime | None = None
    ) -> None:
        category = type(error).__name__[:80]
        try:
            async with self.database.session() as db:
                version_id = await self._ensure_version(db)
                await self._write_generation_run(
                    db,
                    version_id,
                    pull_id,
                    status="failed",
                    generated=0,
                    reused=0,
                    failed=1,
                    source_hash=None,
                    started_at=started_at or datetime.now(UTC),
                    error_categories=(category,),
                )
                await db.commit()
        except Exception:
            # Failure recording is best-effort; do not replace the bounded original error.
            return

    async def _fetch_feature_set(self, db: AsyncSession, identifier: UUID) -> Any:
        return (
            (
                await db.execute(
                    text(
                        "SELECT fs.*,v.version AS feature_version FROM feature_sets fs "
                        "JOIN feature_set_versions v ON v.id=fs.feature_set_version_id WHERE fs.id=:id"
                    ),
                    {"id": identifier},
                )
            )
            .mappings()
            .one()
        )

    def _to_feature_set(
        self,
        row: Any,
        context: FeatureContext,
        source_hash: str,
        version: str,
        *,
        provenance_hash: str,
    ) -> FeatureSet:
        serialized = _json_object(row["feature_values"])
        values = {
            key: FeatureValue(
                value=item.get("value"),
                unit=item.get("unit"),
                quality=FeatureQuality(item["quality"]),
                missing_reason=(
                    MissingReason(item["missing_reason"]) if item.get("missing_reason") else None
                ),
                available_at=datetime.fromisoformat(item["available_at"])
                if item.get("available_at")
                else None,
                source_window_start=datetime.fromisoformat(item["source_window_start"])
                if item.get("source_window_start")
                else None,
                source_window_end=datetime.fromisoformat(item["source_window_end"])
                if item.get("source_window_end")
                else None,
                source_signals=tuple(item.get("source_signals", [])),
                source_entities=tuple(item.get("source_entities", [])),
                details=item.get("details", {}),
            )
            for key, item in serialized.items()
        }
        return FeatureSet(
            id=row["id"],
            vehicle_id=row["vehicle_id"],
            configuration_id=row["configuration_id"],
            session_id=row["session_id"],
            pull_id=row["pull_id"],
            scope=EntityScope(row["entity_scope"]),
            feature_set_version=version,
            generated_at=row["generated_at"],
            source_window_start=row["source_window_start"],
            source_window_end=row["source_window_end"],
            observation_cutoff=row["observation_cutoff"],
            values=values,
            quality_metadata=_json_object(row["quality_metadata"]),
            provenance=_json_object(row["provenance"]),
            provenance_hash=provenance_hash,
            source_hash=source_hash,
            generator_version=self.version.generator_version,
        )
