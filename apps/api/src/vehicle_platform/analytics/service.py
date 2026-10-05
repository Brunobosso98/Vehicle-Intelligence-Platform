# ruff: noqa: E501
import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from time import perf_counter
from typing import Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from opentelemetry import trace
from sqlalchemy import text

from vehicle_platform.analytics.domain import (
    AnalyticsConfig,
    PullInput,
    Sample,
    baseline,
    comparable_groups,
    compare_pulls,
    configuration_comparison,
    pull_profile,
    repeated_pulls,
    trend,
)
from vehicle_platform.analytics.instrumentation import CURRENT_TRACER
from vehicle_platform.api.domain_contracts import AnalyticsResultResponse
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.telemetry.service import validate_vehicle_context

ALGORITHM_NAME = "deterministic-automotive-analytics"
ALGORITHM_VERSION = "1.1.0"
MAX_OBSERVATIONS = 500_000


class AnalyticsLimitError(ValueError):
    pass


class AnalyticsService:
    def __init__(
        self, database: Database, telemetry: Telemetry | None = None, *, read_only: bool = False
    ) -> None:
        self.read_only = read_only
        self.database = database
        self.telemetry = telemetry
        self.tracer = (
            telemetry.tracer if telemetry else trace.get_tracer("vehicle_platform.analytics")
        )

    async def _load(self, pull_ids: list[UUID]) -> list[PullInput]:
        if not pull_ids or len(pull_ids) > 20 or len(set(pull_ids)) != len(pull_ids):
            raise AnalyticsLimitError("between 1 and 20 pull IDs are required")
        with self.tracer.start_as_current_span("analytics.source_selection"):
            with self.tracer.start_as_current_span("analytics.telemetry_load"):
                return await self._load_selected(pull_ids)

    async def _load_selected(self, pull_ids: list[UUID]) -> list[PullInput]:
        async with self.database.session() as db:
            pulls = (
                (
                    await db.execute(
                        text("SELECT * FROM pulls WHERE id = ANY(:ids) ORDER BY started_at,id"),
                        {"ids": pull_ids},
                    )
                )
                .mappings()
                .all()
            )
            if len(pulls) != len(set(pull_ids)):
                raise LookupError("pull not found")
            output: list[PullInput] = []
            total = 0
            for pull in pulls:
                rows = (
                    await db.execute(
                        text("""SELECT observed_at,signal_key,numeric_value FROM telemetry_samples
                    WHERE session_id=:session AND observed_at>=:start AND observed_at<=:end
                    AND quality='valid' ORDER BY observed_at,signal_key,sample_id LIMIT :limit"""),
                        {
                            "session": pull["session_id"],
                            "start": pull["started_at"],
                            "end": pull["ended_at"],
                            "limit": MAX_OBSERVATIONS - total + 1,
                        },
                    )
                ).all()
                total += len(rows)
                if total > MAX_OBSERVATIONS:
                    raise AnalyticsLimitError("analytics request exceeds 500000 observations")
                frames: dict[datetime, dict[str, float]] = {}
                for at, signal, value in rows:
                    frames.setdefault(at, {})[signal] = value
                samples = tuple(
                    Sample(at, values["engine.rpm"], values)
                    for at, values in frames.items()
                    if "engine.rpm" in values
                )
                events = (
                    (
                        await db.execute(
                            text(
                                "SELECT id,event_type,started_at FROM detected_events WHERE pull_id=:id ORDER BY started_at,id LIMIT 1000"
                            ),
                            {"id": pull["id"]},
                        )
                    )
                    .mappings()
                    .all()
                )
                markers = tuple(
                    {
                        "id": str(event["id"]),
                        "event_type": event["event_type"],
                        "observed_at": event["started_at"].isoformat(),
                        "rpm": min(
                            samples,
                            key=lambda sample: abs(
                                (sample.observed_at - event["started_at"]).total_seconds()
                            ),
                        ).rpm,
                    }
                    for event in events
                    if samples
                )
                output.append(
                    PullInput(
                        str(pull["id"]),
                        str(pull["session_id"]),
                        str(pull["vehicle_id"]),
                        str(pull["configuration_id"]) if pull["configuration_id"] else None,
                        pull["started_at"],
                        pull["ended_at"],
                        pull["data_completeness"],
                        samples,
                        tuple(str(event["id"]) for event in events),
                        tuple(pull["quality_flags"]),
                        markers,
                    )
                )
            return output

    async def _persist(
        self,
        analytics_type: str,
        pulls: list[PullInput],
        config: AnalyticsConfig,
        compute: Callable[[], dict[str, object]],
        recompute: bool,
        selection: dict[str, object] | None = None,
    ) -> AnalyticsResultResponse:
        started = perf_counter()
        source = hashlib.sha256(
            json.dumps(
                {
                    "pulls": [asdict(p) for p in sorted(pulls, key=lambda p: p.id)],
                    "selection": selection,
                },
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode()
        ).hexdigest()
        if pulls:
            vehicle_id, configuration_id = UUID(pulls[0].vehicle_id), pulls[0].configuration_id
        elif selection and selection.get("vehicle_id"):
            vehicle_id = UUID(str(selection["vehicle_id"]))
            configuration_id = (
                str(selection["configuration_id"]) if selection.get("configuration_id") else None
            )
        else:
            raise AnalyticsLimitError("analytics selection requires vehicle context")
        async with self.database.session() as db:
            # Serialize only identical semantic identities. Explicit recompute
            # remains an immutable new run; concurrent default requests reuse it.
            lock_key = int(
                hashlib.sha256(
                    f"{analytics_type}:{ALGORITHM_VERSION}:{config.configuration_hash}:{source}".encode()
                ).hexdigest()[:16],
                16,
            ) & ((1 << 63) - 1)
            if not self.read_only:
                await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
                existing = (
                    (
                        await db.execute(
                            text("""SELECT * FROM analytics_runs WHERE analytics_type=:type AND algorithm_version=:version
                    AND configuration_hash=:hash AND source_fingerprint=:source ORDER BY generated_at DESC LIMIT 1"""),
                            {
                                "type": analytics_type,
                                "version": ALGORITHM_VERSION,
                                "hash": config.configuration_hash,
                                "source": source,
                            },
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if existing and not recompute:
                    return AnalyticsResultResponse.model_validate({**existing, "reused": True})
            tracing = CURRENT_TRACER.set(self.tracer)
            try:
                with self.tracer.start_as_current_span("analytics.metric_extraction"):
                    result = compute()
            except Exception:
                if self.telemetry:
                    self.telemetry.analytics_failures.add(1, {"type": analytics_type})
                raise
            finally:
                CURRENT_TRACER.reset(tracing)
            result.setdefault(
                "source_ids",
                {"pulls": [p.id for p in pulls], "sessions": sorted({p.session_id for p in pulls})},
            )
            result.setdefault(
                "observation_count", sum(len(sample.values) for p in pulls for sample in p.samples)
            )
            result.setdefault("pull_count", len(pulls))
            result.setdefault("session_count", len({p.session_id for p in pulls}))
            result.setdefault(
                "data_quality_flags", sorted({flag for p in pulls for flag in p.quality_flags})
            )
            result.setdefault("completeness", min((p.completeness for p in pulls), default=0))
            result.setdefault("metric_definition", analytics_type)
            result.setdefault("normalization_method", f"{config.rpm_bin_size}_rpm_half_open_bins")
            result.setdefault("evidence_quality", "observed; not causal")
            result.setdefault(
                "baseline_source",
                "selected canonical pulls" if analytics_type == "vehicle_baseline" else None,
            )
            status_value = str(result.get("sufficiency", "sufficient"))
            status = "completed" if status_value == "sufficient" else status_value
            limitation_value = result.get("limitations", [])
            warnings = (
                [str(item) for item in limitation_value]
                if isinstance(limitation_value, list)
                else []
            )
            if self.read_only:
                # A deterministic transient calculation identity, never a persisted run ID.
                return AnalyticsResultResponse(
                    id=uuid5(
                        NAMESPACE_URL,
                        f"{analytics_type}:{ALGORITHM_VERSION}:{config.configuration_hash}:{source}",
                    ),
                    analytics_type=analytics_type,
                    algorithm_name=ALGORITHM_NAME,
                    algorithm_version=ALGORITHM_VERSION,
                    configuration_hash=config.configuration_hash,
                    source_fingerprint=source,
                    vehicle_id=vehicle_id,
                    configuration_id=UUID(configuration_id) if configuration_id else None,
                    status=cast(Literal["completed", "limited", "insufficient", "failed"], status),
                    warnings=warnings,
                    result=result,
                    generated_at=datetime.now(UTC),
                    reused=False,
                )
            with self.tracer.start_as_current_span("analytics.persistence"):
                row = (
                    (
                        await db.execute(
                            text("""INSERT INTO analytics_runs
                (analytics_type,algorithm_name,algorithm_version,configuration_hash,source_fingerprint,vehicle_id,configuration_id,status,warnings,input_summary,result)
                VALUES(:type,:name,:version,:hash,:source,:vehicle,:configuration,:status,:warnings,CAST(:input AS jsonb),CAST(:result AS jsonb)) RETURNING *"""),
                            {
                                "type": analytics_type,
                                "name": ALGORITHM_NAME,
                                "version": ALGORITHM_VERSION,
                                "hash": config.configuration_hash,
                                "source": source,
                                "vehicle": vehicle_id,
                                "configuration": UUID(configuration_id)
                                if configuration_id
                                else None,
                                "status": status,
                                "warnings": warnings,
                                "input": json.dumps(
                                    {
                                        "pull_ids": [p.id for p in pulls],
                                        "observation_count": sum(
                                            len(sample.values)
                                            for p in pulls
                                            for sample in p.samples
                                        ),
                                    }
                                ),
                                "result": json.dumps(result, default=str),
                            },
                        )
                    )
                    .mappings()
                    .one()
                )
                await db.commit()
            if self.telemetry:
                labels = {"type": analytics_type, "status": status}
                self.telemetry.analytics_runs.add(1, labels)
                self.telemetry.analytics_duration.record(perf_counter() - started, labels)
                if status != "completed":
                    self.telemetry.analytics_insufficient.add(1, {"type": analytics_type})
                if analytics_type in {
                    "pull_comparison",
                    "cross_session",
                    "configuration_comparison",
                }:
                    self.telemetry.analytics_pull_comparisons.add(1, {"type": analytics_type})
                    if result.get("sufficiency") == "insufficient":
                        self.telemetry.analytics_rejected_comparisons.add(
                            1, {"reason": "insufficient_comparable_evidence"}
                        )
                self.telemetry.logger.info(
                    "analytics.completed",
                    extra={
                        "analytics_type": analytics_type,
                        "algorithm_version": ALGORITHM_VERSION,
                        "pull_count": len(pulls),
                        "outcome": status,
                    },
                )
                if analytics_type == "vehicle_baseline":
                    self.telemetry.analytics_baseline_builds.add(1)
                    self.telemetry.analytics_baseline_contributors.record(len(pulls))
                if analytics_type == "trend":
                    self.telemetry.analytics_trend_builds.add(1)
            return AnalyticsResultResponse.model_validate({**row, "reused": False})

    async def pull(
        self, pull_id: UUID, config: AnalyticsConfig, recompute: bool = False
    ) -> AnalyticsResultResponse:
        pulls = await self._load([pull_id])
        return await self._persist(
            "pull", pulls, config, lambda: pull_profile(pulls[0], config), recompute
        )

    async def comparison(
        self, ids: list[UUID], config: AnalyticsConfig, recompute: bool = False
    ) -> AnalyticsResultResponse:
        pulls = await self._load(ids)
        return await self._persist(
            "pull_comparison", pulls, config, lambda: compare_pulls(pulls, config), recompute
        )

    async def repeated(
        self, ids: list[UUID], config: AnalyticsConfig, recompute: bool = False
    ) -> AnalyticsResultResponse:
        pulls = await self._load(ids)
        return await self._persist(
            "repeated_pulls", pulls, config, lambda: repeated_pulls(pulls, config), recompute
        )

    async def session(
        self, session_id: UUID, config: AnalyticsConfig, recompute: bool = False
    ) -> AnalyticsResultResponse:
        async with self.database.session() as db:
            session = (
                (
                    await db.execute(
                        text("SELECT * FROM driving_sessions WHERE id=:id"), {"id": session_id}
                    )
                )
                .mappings()
                .one_or_none()
            )
            if session is None:
                raise LookupError("session not found")
            ids = list(
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE session_id=:id ORDER BY started_at LIMIT 20"
                        ),
                        {"id": session_id},
                    )
                ).scalars()
            )
            signals = (
                (
                    await db.execute(
                        text(
                            "SELECT signal_key,count(*) AS observations,min(observed_at) AS first,max(observed_at) AS last FROM telemetry_samples WHERE session_id=:id GROUP BY signal_key"
                        ),
                        {"id": session_id},
                    )
                )
                .mappings()
                .all()
            )
            segments = (
                await db.execute(
                    text(
                        "SELECT segment_type,count(*) AS count FROM session_segments WHERE session_id=:id GROUP BY segment_type"
                    ),
                    {"id": session_id},
                )
            ).all()
            events = (
                await db.execute(
                    text(
                        "SELECT category,count(*) AS count FROM detected_events WHERE session_id=:id GROUP BY category"
                    ),
                    {"id": session_id},
                )
            ).all()
            capability = (
                await db.execute(
                    text(
                        "SELECT report FROM dataset_capability_reports WHERE driving_session_id=:id ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"id": session_id},
                )
            ).scalar_one_or_none()
        pulls = await self._load(ids) if ids else []
        summary = {
            "session_id": str(session_id),
            "duration_seconds": (
                max(s["last"] for s in signals) - min(s["first"] for s in signals)
            ).total_seconds()
            if signals
            else None,
            "telemetry_observation_count": sum(s["observations"] for s in signals),
            "segment_counts": {str(kind): count for kind, count in segments},
            "event_counts_by_category": {str(kind): count for kind, count in events},
            "event_count": sum(count for _, count in events),
            "signal_coverage": [
                {
                    "signal": s["signal_key"],
                    "observation_count": s["observations"],
                    "first_observed_at": s["first"],
                    "last_observed_at": s["last"],
                }
                for s in signals
            ],
            "post_log_capability_report": capability,
            "limitations": [] if capability else ["no_acquisition_capability_report"],
            "quality": session["status"],
            "comparable_pull_groups": [
                [p.id for p in group] for group in comparable_groups(pulls, config)
            ],
        }
        return await self._persist(
            "session",
            pulls,
            config,
            lambda: {**repeated_pulls(pulls, config), "session_summary": summary},
            recompute,
            {
                "vehicle_id": str(session["vehicle_id"]),
                "configuration_id": str(session["configuration_id"])
                if session["configuration_id"]
                else None,
                "session_summary": summary,
            },
        )

    async def cross_sessions(
        self, session_ids: list[UUID], config: AnalyticsConfig, recompute: bool = False
    ) -> AnalyticsResultResponse:
        if not 2 <= len(session_ids) <= 10 or len(set(session_ids)) != len(session_ids):
            raise AnalyticsLimitError("cross-session comparison requires 2 to 10 sessions")
        async with self.database.session() as db:
            sessions = (
                (
                    await db.execute(
                        text(
                            "SELECT id,vehicle_id,configuration_id FROM driving_sessions WHERE id=ANY(:ids) ORDER BY id"
                        ),
                        {"ids": session_ids},
                    )
                )
                .mappings()
                .all()
            )
            if len(sessions) != len(session_ids):
                raise LookupError("session not found")
            if len({row["vehicle_id"] for row in sessions}) != 1:
                raise AnalyticsLimitError("cross-session sources must belong to one vehicle")
            ids: list[UUID] = list(
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE session_id = ANY(:ids) "
                            "ORDER BY started_at,id LIMIT 20"
                        ),
                        {"ids": session_ids},
                    )
                ).scalars()
            )
        pulls = await self._load(ids) if ids else []
        return await self._persist(
            "cross_session",
            pulls,
            config,
            lambda: (
                compare_pulls(pulls, config)
                if len(pulls) >= 2
                else {
                    "sufficiency": "insufficient",
                    "limitations": ["fewer_than_two_detected_pulls"],
                }
            ),
            recompute,
            {
                "vehicle_id": str(sessions[0]["vehicle_id"]),
                "configuration_id": str(sessions[0]["configuration_id"])
                if sessions[0]["configuration_id"]
                else None,
                "session_ids": sorted(map(str, session_ids)),
            },
        )

    async def vehicle_baseline(
        self,
        vehicle_id: UUID,
        configuration_id: UUID,
        config: AnalyticsConfig,
        recompute: bool = False,
    ) -> AnalyticsResultResponse:
        async with self.database.session() as db:
            await validate_vehicle_context(db, vehicle_id, configuration_id)
            ids: list[UUID] = list(
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE vehicle_id=:vehicle AND configuration_id=:configuration AND data_completeness>=:quality ORDER BY started_at DESC LIMIT 20"
                        ),
                        {
                            "vehicle": vehicle_id,
                            "configuration": configuration_id,
                            "quality": config.minimum_completeness,
                        },
                    )
                ).scalars()
            )
        pulls = await self._load(ids) if ids else []
        return await self._persist(
            "vehicle_baseline",
            pulls,
            config,
            lambda: baseline(pulls, config),
            recompute,
            {"vehicle_id": str(vehicle_id), "configuration_id": str(configuration_id)},
        )

    async def trends(
        self, vehicle_id: UUID, metric: str, config: AnalyticsConfig
    ) -> AnalyticsResultResponse:
        if metric not in {"boost", "iat", "coolant", "oil", "fuel", "speed", "throttle"}:
            raise AnalyticsLimitError("unsupported trend metric")
        async with self.database.session() as db:
            await validate_vehicle_context(db, vehicle_id, None)
            ids: list[UUID] = list(
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE vehicle_id=:vehicle ORDER BY started_at DESC LIMIT 20"
                        ),
                        {"vehicle": vehicle_id},
                    )
                ).scalars()
            )
        pulls = await self._load(ids) if ids else []
        return await self._persist(
            "trend",
            pulls,
            config,
            lambda: trend(pulls, metric, config),
            False,
            {"metric": metric, "vehicle_id": str(vehicle_id)},
        )

    async def modifications(
        self, before_ids: list[UUID], after_ids: list[UUID], config: AnalyticsConfig
    ) -> AnalyticsResultResponse:
        pulls = await self._load(before_ids + after_ids)
        by_id = {p.id: p for p in pulls}
        before, after = (
            [by_id[str(item)] for item in before_ids],
            [by_id[str(item)] for item in after_ids],
        )
        return await self._persist(
            "modification_comparison",
            pulls,
            config,
            lambda: configuration_comparison(before, after, config),
            False,
            {
                "before": sorted(map(str, before_ids)),
                "after": sorted(map(str, after_ids)),
            },
        )
