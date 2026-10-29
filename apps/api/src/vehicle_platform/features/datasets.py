import json
import math
import os
import re
import tempfile
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any, cast
from uuid import UUID

from sqlalchemy import text

from vehicle_platform.features.domain import (
    CutoffPolicy,
    DatasetDefinition,
    EntityScope,
    FeatureDType,
    FeatureQuality,
    HorizonKind,
    MissingReason,
    TemporalAvailability,
    canonical_json,
    require_aware,
    stable_hash,
)
from vehicle_platform.features.registry import FeatureRegistry
from vehicle_platform.features.service import FeatureGenerationLimitError
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.observability.telemetry import Telemetry

MAX_DATASET_ROWS = 100_000
MAX_DATASET_SOURCE_BYTES = 32 * 1024 * 1024
MAX_DATASET_SOURCE_ENTITIES = 200_000
MAX_EXPORT_BYTES = 64 * 1024 * 1024


class DatasetValidationError(ValueError):
    pass


@dataclass(frozen=True)
class DatasetCandidate:
    """A pull considered by DatasetBuilder, including pulls excluded from feature rows."""

    pull_id: str
    vehicle_id: str
    configuration_id: str | None
    session_id: str
    started_at: str
    ended_at: str
    active_modification_ids: tuple[str, ...] = ()
    feature_set_id: str | None = None
    feature_set_source_hash: str | None = None
    row_id: str | None = None
    exclusion_reason: str | None = None

    def manifest(self) -> dict[str, Any]:
        return {
            "pull_id": self.pull_id,
            "vehicle_id": self.vehicle_id,
            "configuration_id": self.configuration_id,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "active_modification_ids": list(self.active_modification_ids),
            "feature_set_id": self.feature_set_id,
            "feature_set_source_hash": self.feature_set_source_hash,
            "row_id": self.row_id,
            "exclusion_reason": self.exclusion_reason,
        }


@dataclass(frozen=True)
class DatasetBuild:
    definition: DatasetDefinition
    rows: tuple[dict[str, Any], ...]
    exclusions: tuple[dict[str, str], ...]
    checksum: str
    manifest: dict[str, Any]
    profile: dict[str, Any]
    candidates: tuple[DatasetCandidate, ...] = ()


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start: datetime
    train_end: datetime
    validation_end: datetime
    test_end: datetime
    train: tuple[dict[str, Any], ...]
    validation: tuple[dict[str, Any], ...]
    test: tuple[dict[str, Any], ...]


class DatasetBuilder:
    def __init__(
        self,
        database: Database,
        registry: FeatureRegistry,
        telemetry: Telemetry | None = None,
    ) -> None:
        self.database = database
        self.registry = registry
        self.telemetry = telemetry

    async def build(
        self,
        definition: DatasetDefinition,
        *,
        candidate_pull_ids: Sequence[UUID] | None = None,
    ) -> DatasetBuild:
        started = perf_counter()
        outcome = "failed"
        try:
            if candidate_pull_ids is not None:
                if len(candidate_pull_ids) > MAX_DATASET_ROWS:
                    raise FeatureGenerationLimitError(
                        "dataset candidate pull selection exceeds 100000 pulls"
                    )
                if len(set(candidate_pull_ids)) != len(candidate_pull_ids):
                    raise DatasetValidationError(
                        "dataset candidate pull selection contains duplicates"
                    )
            if self.telemetry:
                with self.telemetry.tracer.start_as_current_span("features.dataset.build") as span:
                    result = await self._build(definition, candidate_pull_ids)
                    span.set_attribute("dataset.row_count", len(result.rows))
                    span.set_attribute("dataset.excluded_count", len(result.exclusions))
            else:
                result = await self._build(definition, candidate_pull_ids)
            outcome = "completed"
            if self.telemetry:
                self.telemetry.dataset_builds.add(1, {"outcome": outcome})
                self.telemetry.dataset_rows.add(len(result.rows))
                self.telemetry.dataset_exclusions.add(len(result.exclusions))
            return result
        except Exception:
            if self.telemetry:
                self.telemetry.dataset_builds.add(1, {"outcome": "failed"})
            raise
        finally:
            if self.telemetry:
                self.telemetry.dataset_build_duration.record(
                    perf_counter() - started, {"outcome": outcome}
                )

    async def _build(
        self,
        definition: DatasetDefinition,
        candidate_pull_ids: Sequence[UUID] | None,
    ) -> DatasetBuild:
        selected = tuple(self.registry.resolve(key) for key in definition.selected_features)
        if definition.label_definition and set(definition.selected_features).intersection(
            definition.label_definition.source_feature_keys
        ):
            raise DatasetValidationError("selected features overlap label source features")
        async with self.database.session() as db:
            feature_version = (
                await db.execute(
                    text("SELECT id FROM feature_set_versions WHERE version=:version"),
                    {"version": definition.feature_set_version},
                )
            ).scalar_one_or_none()
            if feature_version is None:
                raise DatasetValidationError("feature set version is not registered")
            pull_params: dict[str, Any] = {
                "cutoff": definition.observation_cutoff,
                "limit": MAX_DATASET_ROWS + 1,
                "has_candidate_pull_ids": candidate_pull_ids is not None,
                "candidate_pull_ids": (
                    list(candidate_pull_ids) if candidate_pull_ids is not None else None
                ),
            }
            pull_rows = (
                (
                    await db.execute(
                        text(
                            "SELECT p.id,p.vehicle_id,p.configuration_id,p.session_id,p.started_at,p.ended_at,p.created_at,"
                            "s.created_at AS session_created_at,v.created_at AS vehicle_created_at "
                            "FROM pulls p JOIN driving_sessions s ON s.id=p.session_id "
                            "JOIN vehicles v ON v.id=p.vehicle_id "
                            "WHERE p.started_at<=:cutoff AND p.created_at<=:cutoff "
                            "AND (:has_candidate_pull_ids IS FALSE OR "
                            "p.id=ANY(CAST(:candidate_pull_ids AS uuid[]))) "
                            "ORDER BY p.started_at,p.vehicle_id,p.id LIMIT :limit"
                        ),
                        pull_params,
                    )
                )
                .mappings()
                .all()
            )
            if len(pull_rows) > MAX_DATASET_ROWS:
                raise FeatureGenerationLimitError("dataset candidate query exceeds 100000 pulls")
            pull_ids = [row["id"] for row in pull_rows]
            if not pull_ids:
                feature_sets: Sequence[Any] = []
            else:
                selected_feature_sets = (
                    "SELECT DISTINCT ON (fs.pull_id) fs.id,fs.pull_id,fs.observation_cutoff,fs.generated_at "
                    "FROM feature_sets fs JOIN pulls p ON p.id=fs.pull_id "
                    "WHERE fs.feature_set_version_id=:version AND fs.entity_scope='pull' "
                    "AND fs.pull_id=ANY(:pull_ids) AND fs.observation_cutoff<=CASE "
                    "WHEN :cutoff_policy='row_start' THEN LEAST(:cutoff,p.started_at) "
                    "WHEN :cutoff_policy='row_end' THEN LEAST(:cutoff,p.ended_at) ELSE :cutoff END "
                    "ORDER BY fs.pull_id,fs.observation_cutoff DESC,fs.generated_at DESC,fs.id DESC"
                )
                selection_params = {
                    "version": feature_version,
                    "pull_ids": pull_ids,
                    "cutoff": definition.observation_cutoff,
                    "cutoff_policy": definition.cutoff_policy.value,
                }
                preflight = (
                    await db.execute(
                        text(
                            "SELECT count(*) AS row_count,COALESCE(sum("  # noqa: S608
                            "octet_length(fs.feature_values::text)+octet_length(fs.quality_metadata::text)+"
                            "octet_length(fs.provenance::text)),0) AS source_bytes "
                            f"FROM ({selected_feature_sets}) selected JOIN feature_sets fs ON fs.id=selected.id"
                        ),
                        selection_params,
                    )
                ).one()
                if preflight.row_count > MAX_DATASET_ROWS:
                    raise FeatureGenerationLimitError("dataset has more than 100000 feature rows")
                if preflight.source_bytes > MAX_DATASET_SOURCE_BYTES:
                    raise FeatureGenerationLimitError("dataset source payload exceeds 32 MiB")
                feature_sets = (
                    (
                        await db.execute(
                            text(
                                f"WITH selected AS ({selected_feature_sets}) "  # noqa: S608
                                "SELECT fs.*,v.version AS feature_version FROM selected s "
                                "JOIN feature_sets fs ON fs.id=s.id "
                                "JOIN feature_set_versions v ON v.id=fs.feature_set_version_id "
                                "ORDER BY fs.pull_id"
                            ),
                            selection_params,
                        )
                    )
                    .mappings()
                    .all()
                )
            source_refs: dict[str, Any] = {"by_target": {}}
            if feature_sets:
                source = _feature_source_refs(feature_sets)
                if (
                    sum(len(values) for key, values in source.items() if key != "by_target")
                    > MAX_DATASET_SOURCE_ENTITIES
                ):
                    raise FeatureGenerationLimitError(
                        "dataset lineage exceeds 200000 source entities"
                    )
                target_cutoffs = {
                    str(item["pull_id"]): item["observation_cutoff"] for item in feature_sets
                }
                source_refs = await self._validate_source_ownership(
                    db,
                    source,
                    target_cutoffs,
                )
                annotated = []
                for item in feature_sets:
                    copy = dict(item)
                    provenance = _json_object(copy["provenance"])
                    copy["_feature_provenance"] = provenance
                    annotated.append(copy)
                feature_sets = annotated
            dataset = self._materialize(definition, selected, pull_rows, feature_sets, source_refs)
            definition_id = await self._ensure_definition(db, definition)
            await db.execute(
                text(
                    "INSERT INTO dataset_build_runs(dataset_definition_id,feature_set_version_id,"
                    "observation_cutoff,status,row_count,excluded_count,checksum,manifest) "
                    "VALUES(:definition,:feature_version,:cutoff,'completed',:rows,:excluded,:checksum,CAST(:manifest AS jsonb))"
                ),
                {
                    "definition": definition_id,
                    "feature_version": feature_version,
                    "cutoff": definition.observation_cutoff,
                    "rows": len(dataset.rows),
                    "excluded": len(dataset.exclusions),
                    "checksum": dataset.checksum,
                    "manifest": canonical_json(dataset.manifest),
                },
            )
            await db.commit()
        return dataset

    async def _ensure_definition(self, db: Any, definition: DatasetDefinition) -> UUID:
        await db.execute(
            text(
                "INSERT INTO dataset_definitions(name,version,definition,checksum) "
                "VALUES(:name,:version,CAST(:definition AS jsonb),:checksum) "
                "ON CONFLICT(name,version) DO NOTHING"
            ),
            {
                "name": definition.name,
                "version": definition.version,
                "definition": canonical_json(definition.manifest()),
                "checksum": definition.checksum,
            },
        )
        row = (
            await db.execute(
                text(
                    "SELECT id,checksum FROM dataset_definitions WHERE name=:name AND version=:version"
                ),
                {"name": definition.name, "version": definition.version},
            )
        ).one()
        if row.checksum != definition.checksum:
            raise DatasetValidationError("dataset name/version was already registered differently")
        return cast(UUID, row.id)

    def _materialize(
        self,
        definition: DatasetDefinition,
        selected: tuple[Any, ...],
        pull_rows: Iterable[Any],
        feature_sets: Iterable[Any],
        source_refs: dict[str, Any],
    ) -> DatasetBuild:
        by_pull: dict[str, list[Any]] = {}
        for feature_set in feature_sets:
            by_pull.setdefault(str(feature_set["pull_id"]), []).append(feature_set)
        rows: list[dict[str, Any]] = []
        exclusions: list[dict[str, str]] = []
        candidate_records: list[DatasetCandidate] = []
        materialized_bytes = 0
        first_configuration: str | None = None
        configuration_is_set = False
        for pull in pull_rows:
            pull_id = str(pull["id"])
            candidate: dict[str, Any] = {
                "pull_id": pull_id,
                "vehicle_id": str(pull["vehicle_id"]),
                "configuration_id": (
                    str(pull["configuration_id"]) if pull["configuration_id"] else None
                ),
                "session_id": str(pull["session_id"]),
                "started_at": pull["started_at"].isoformat(),
                "ended_at": pull["ended_at"].isoformat(),
                "active_modification_ids": (),
                "feature_set_id": None,
                "feature_set_source_hash": None,
                "row_id": None,
            }

            row_cutoff = _row_cutoff(definition, pull)
            if row_cutoff < pull["created_at"]:
                _record_candidate_exclusion(
                    exclusions, candidate_records, candidate, "pull_not_observed_by_cutoff"
                )
                continue
            feature_set_candidates = [
                item
                for item in by_pull.get(pull_id, [])
                if item["observation_cutoff"] <= row_cutoff
            ]
            if not feature_set_candidates:
                _record_candidate_exclusion(
                    exclusions, candidate_records, candidate, "feature_set_missing_or_after_cutoff"
                )
                continue
            feature_set = max(
                feature_set_candidates,
                key=lambda item: (
                    item["observation_cutoff"],
                    item["generated_at"],
                    str(item["id"]),
                ),
            )
            actual_configuration = (
                str(feature_set["configuration_id"]) if feature_set["configuration_id"] else None
            )
            if (
                feature_set["vehicle_id"] != pull["vehicle_id"]
                or feature_set["session_id"] != pull["session_id"]
                or feature_set["pull_id"] != pull["id"]
            ):
                _record_candidate_exclusion(
                    exclusions, candidate_records, candidate, "entity_ownership_mismatch"
                )
                continue
            provenance = feature_set.get("_feature_provenance") or _json_object(
                feature_set["provenance"]
            )
            source_context = provenance.get("source_context", {})
            candidate["configuration_id"] = actual_configuration
            candidate["active_modification_ids"] = tuple(
                sorted(str(value) for value in source_context.get("active_modification_ids", []))
            )
            candidate["feature_set_id"] = str(feature_set["id"])
            candidate["feature_set_source_hash"] = str(feature_set["source_hash"])
            target_source_refs = source_refs.get("by_target", {}).get(pull_id, {})
            target_source = target_source_refs.get("pull_rows", {}).get(pull_id)
            expected_configuration = (
                str(target_source["effective_configuration_id"])
                if target_source is not None and target_source["effective_configuration_id"]
                else None
            )
            if target_source is None or actual_configuration != expected_configuration:
                _record_candidate_exclusion(
                    exclusions, candidate_records, candidate, "configuration_mismatch"
                )
                continue
            if not definition.allow_configuration_mixing:
                if not configuration_is_set:
                    first_configuration = actual_configuration
                    configuration_is_set = True
                elif actual_configuration != first_configuration:
                    _record_candidate_exclusion(
                        exclusions, candidate_records, candidate, "configuration_mixing_disallowed"
                    )
                    continue
            quality = _json_object(feature_set["quality_metadata"])
            if float(quality.get("pull_completeness") or 0.0) < definition.minimum_quality:
                _record_candidate_exclusion(
                    exclusions, candidate_records, candidate, "minimum_quality_not_met"
                )
                continue
            vector = _json_object(feature_set["feature_values"])
            prior_count = _prior_count(vector)
            if prior_count < definition.minimum_history:
                _record_candidate_exclusion(
                    exclusions, candidate_records, candidate, "minimum_history_not_met"
                )
                continue
            output_values: dict[str, Any] = {}
            missing: dict[str, str] = {}
            feature_quality: dict[str, str] = {}
            feature_failure: str | None = None
            for definition_item in selected:
                item = vector.get(definition_item.key)
                if not isinstance(item, dict):
                    item = _missing_value(MissingReason.NOT_OBSERVED_YET, definition_item.unit)
                if not _eligible(definition_item, item, row_cutoff, pull, definition):
                    item = _missing_value(MissingReason.NOT_OBSERVED_YET, definition_item.unit)
                reason = item.get("missing_reason")
                value = item.get("value")
                quality_value = item.get("quality")
                feature_quality[definition_item.key] = (
                    str(quality_value) if quality_value is not None else "invalid"
                )
                if value is None:
                    missing[definition_item.key] = str(
                        reason or MissingReason.COMPUTATION_ERROR.value
                    )
                    if definition_item.key in definition.required_features:
                        feature_failure = f"required_feature_unavailable:{definition_item.key}"
                else:
                    if not _valid_serialized_value(definition_item, item):
                        feature_failure = f"invalid_persisted_feature:{definition_item.key}"
                    output_values[definition_item.key] = value
            if feature_failure:
                _record_candidate_exclusion(
                    exclusions, candidate_records, candidate, feature_failure
                )
                continue
            if not _lineage_is_safe(
                selected,
                vector,
                provenance,
                source_refs,
                pull,
                feature_set,
                row_cutoff,
                definition,
            ):
                _record_candidate_exclusion(
                    exclusions, candidate_records, candidate, "leakage_or_lineage_rejected"
                )
                continue
            identity = {
                "vehicle_id": str(pull["vehicle_id"]),
                "configuration_id": actual_configuration,
                "session_id": str(pull["session_id"]),
                "pull_id": pull_id,
                "observation_cutoff": row_cutoff.isoformat(),
                "feature_set_version": definition.feature_set_version,
            }
            row_id = stable_hash(identity)
            row = {
                "row_id": row_id,
                **identity,
                "started_at": pull["started_at"].isoformat(),
                "ended_at": pull["ended_at"].isoformat(),
                "feature_set_id": str(feature_set["id"]),
                "feature_set_source_hash": str(feature_set["source_hash"]),
                "provenance_hash": str(feature_set["provenance_hash"]),
                "quality": quality,
                "features": output_values,
                "missing": missing,
                "feature_quality": feature_quality,
                "active_modification_ids": list(candidate["active_modification_ids"]),
            }
            materialized_bytes += len(canonical_json(row).encode("utf-8"))
            if materialized_bytes > MAX_EXPORT_BYTES:
                raise FeatureGenerationLimitError("materialized dataset exceeds 64 MiB")
            rows.append(row)
            candidate["row_id"] = row_id
            candidate_records.append(DatasetCandidate(**candidate, exclusion_reason=None))
        rows.sort(
            key=lambda item: (
                item["observation_cutoff"],
                item["vehicle_id"],
                item["configuration_id"] or "",
                item["session_id"],
                item["pull_id"],
            )
        )
        if len({item["row_id"] for item in rows}) != len(rows):
            raise DatasetValidationError("dataset row identity collision")
        candidate_records.sort(
            key=lambda item: (
                item.started_at,
                item.vehicle_id,
                item.configuration_id or "",
                item.session_id,
                item.pull_id,
            )
        )
        profile = profile_dataset(rows, selected, definition, exclusions=exclusions)
        excluded_counts = dict(sorted(Counter(item["reason"] for item in exclusions).items()))
        checksum_payload = {
            "definition_checksum": definition.checksum,
            "rows": [
                {
                    "row_id": item["row_id"],
                    "feature_set_source_hash": item["feature_set_source_hash"],
                    "features": item["features"],
                    "missing": item["missing"],
                    "feature_quality": item["feature_quality"],
                    "active_modification_ids": item["active_modification_ids"],
                }
                for item in rows
            ],
            "candidate_rows": [item.manifest() for item in candidate_records],
            "exclusions": sorted(exclusions, key=lambda item: (item["pull_id"], item["reason"])),
        }
        checksum = stable_hash(checksum_payload)
        manifest = {
            "dataset_name": definition.name,
            "dataset_version": definition.version,
            "dataset_definition_checksum": definition.checksum,
            "checksum": checksum,
            "row_schema_version": "phase9a-dataset-row-v2",
            "row_count": len(rows),
            "candidate_count": len(candidate_records),
            "feature_list": [item.key for item in selected],
            "feature_set_version": definition.feature_set_version,
            "observation_cutoff": definition.observation_cutoff.isoformat(),
            "time_range": profile["time_range"],
            "vehicle_count": len({item["vehicle_id"] for item in rows}),
            "configuration_count": len({item["configuration_id"] for item in rows}),
            "vehicle_distribution": profile["vehicle_distribution"],
            "configuration_distribution": profile["configuration_distribution"],
            "missing_stats": profile["missing_stats"],
            "quality_stats": profile["quality_stats"],
            "excluded_row_count": len(exclusions),
            "excluded_rows_by_reason": excluded_counts,
            "source": definition.source,
            "row_scope": EntityScope.PULL.value,
            "export_format": "jsonl",
        }
        return DatasetBuild(
            definition,
            tuple(rows),
            tuple(sorted(exclusions, key=lambda item: (item["pull_id"], item["reason"]))),
            checksum,
            manifest,
            profile,
            tuple(candidate_records),
        )

    async def _validate_source_ownership(
        self,
        db: Any,
        refs: dict[str, Any],
        target_cutoffs: dict[str, datetime],
    ) -> dict[str, Any]:
        by_target_refs = refs.get("by_target", {})
        pull_pairs = {
            (target_id, source_id, cutoff)
            for target_id, cutoff in target_cutoffs.items()
            for source_id in {
                target_id,
                *by_target_refs.get(target_id, {}).get("pulls", set()),
            }
        }
        event_pairs = {
            (target_id, event_id, cutoff)
            for target_id, cutoff in target_cutoffs.items()
            for event_id in by_target_refs.get(target_id, {}).get("events", set())
        }
        if len(pull_pairs) + len(event_pairs) > MAX_DATASET_SOURCE_ENTITIES:
            raise FeatureGenerationLimitError("dataset lineage link count exceeds 200000")
        config_ids = refs.get("configurations", set())
        result: dict[str, Any] = {
            "by_target": {
                target_id: {"pull_rows": {}, "event_rows": {}} for target_id in target_cutoffs
            },
            "configuration_rows": {},
            "modification_rows": {},
        }
        if pull_pairs:
            pairs_json = json.dumps(
                [
                    {
                        "target_pull_id": target_id,
                        "source_id": source_id,
                        "cutoff": cutoff.isoformat(),
                    }
                    for target_id, source_id, cutoff in sorted(pull_pairs)
                ],
                sort_keys=True,
            )
            rows = (
                (
                    await db.execute(
                        text(
                            "WITH pairs AS (SELECT * FROM jsonb_to_recordset(CAST(:pairs AS jsonb)) "
                            "AS pair(target_pull_id uuid,source_id uuid,cutoff timestamptz)), "
                            "source_pulls AS (SELECT p.id,p.vehicle_id,p.configuration_id,p.session_id,"
                            "p.started_at,p.ended_at,p.created_at,s.created_at AS session_created_at,"
                            "v.created_at AS vehicle_created_at,s.configuration_id AS session_configuration_id "
                            "FROM pulls p JOIN driving_sessions s ON s.id=p.session_id "
                            "JOIN vehicles v ON v.id=p.vehicle_id WHERE p.id IN (SELECT source_id FROM pairs)) "
                            "SELECT pairs.target_pull_id,sp.*,COALESCE(session_config.id,latest_config.id) "
                            "AS effective_configuration_id,ARRAY(SELECT m.id::text FROM modifications m "
                            "WHERE m.vehicle_id=sp.vehicle_id "
                            "AND m.installed_at<=sp.started_at AND (m.removed_at IS NULL OR m.removed_at>sp.started_at) "
                            "AND m.created_at<=pairs.cutoff AND (m.configuration_id IS NULL "
                            "OR m.configuration_id=COALESCE(session_config.id,latest_config.id)) "
                            "ORDER BY m.id) AS active_modification_ids "
                            "FROM pairs JOIN source_pulls sp ON sp.id=pairs.source_id "
                            "LEFT JOIN LATERAL (SELECT vc.id FROM vehicle_configurations vc "
                            "WHERE vc.id=sp.session_configuration_id AND vc.vehicle_id=sp.vehicle_id "
                            "AND vc.effective_at<=sp.started_at "
                            "AND (vc.ended_at IS NULL OR vc.ended_at>sp.started_at) "
                            "AND vc.created_at<=pairs.cutoff LIMIT 1) session_config ON TRUE "
                            "LEFT JOIN LATERAL (SELECT vc.id FROM vehicle_configurations vc "
                            "WHERE vc.vehicle_id=sp.vehicle_id AND vc.effective_at<=sp.started_at "
                            "AND (vc.ended_at IS NULL OR vc.ended_at>sp.started_at) "
                            "AND vc.created_at<=pairs.cutoff ORDER BY vc.effective_at DESC,vc.id LIMIT 1) "
                            "latest_config ON TRUE"
                        ),
                        {"pairs": pairs_json},
                    )
                )
                .mappings()
                .all()
            )
            for row in rows:
                result["by_target"][str(row["target_pull_id"])]["pull_rows"][str(row["id"])] = row
        if event_pairs:
            pairs_json = json.dumps(
                [
                    {
                        "target_pull_id": target_id,
                        "source_id": event_id,
                        "cutoff": cutoff.isoformat(),
                    }
                    for target_id, event_id, cutoff in sorted(event_pairs)
                ],
                sort_keys=True,
            )
            rows = (
                (
                    await db.execute(
                        text(
                            "WITH pairs AS (SELECT * FROM jsonb_to_recordset(CAST(:pairs AS jsonb)) "
                            "AS pair(target_pull_id uuid,source_id uuid,cutoff timestamptz)), "
                            "source_events AS (SELECT e.id,e.vehicle_id,e.session_id,e.started_at,e.ended_at,e.created_at,"
                            "s.created_at AS session_created_at,v.created_at AS vehicle_created_at,"
                            "s.configuration_id AS session_configuration_id "
                            "FROM detected_events e JOIN driving_sessions s ON s.id=e.session_id "
                            "JOIN vehicles v ON v.id=e.vehicle_id WHERE e.id IN (SELECT source_id FROM pairs)) "
                            "SELECT pairs.target_pull_id,se.*,COALESCE(session_config.id,latest_config.id) "
                            "AS effective_configuration_id,ARRAY(SELECT m.id::text FROM modifications m "
                            "WHERE m.vehicle_id=se.vehicle_id AND m.installed_at<=se.started_at "
                            "AND (m.removed_at IS NULL OR m.removed_at>se.started_at) "
                            "AND m.created_at<=pairs.cutoff AND (m.configuration_id IS NULL "
                            "OR m.configuration_id=COALESCE(session_config.id,latest_config.id)) "
                            "ORDER BY m.id) AS active_modification_ids "
                            "FROM pairs JOIN source_events se ON se.id=pairs.source_id "
                            "LEFT JOIN LATERAL (SELECT vc.id FROM vehicle_configurations vc "
                            "WHERE vc.id=se.session_configuration_id AND vc.vehicle_id=se.vehicle_id "
                            "AND vc.effective_at<=se.started_at "
                            "AND (vc.ended_at IS NULL OR vc.ended_at>se.started_at) "
                            "AND vc.created_at<=pairs.cutoff LIMIT 1) session_config ON TRUE "
                            "LEFT JOIN LATERAL (SELECT vc.id FROM vehicle_configurations vc "
                            "WHERE vc.vehicle_id=se.vehicle_id AND vc.effective_at<=se.started_at "
                            "AND (vc.ended_at IS NULL OR vc.ended_at>se.started_at) "
                            "AND vc.created_at<=pairs.cutoff ORDER BY vc.effective_at DESC,vc.id LIMIT 1) "
                            "latest_config ON TRUE"
                        ),
                        {"pairs": pairs_json},
                    )
                )
                .mappings()
                .all()
            )
            for row in rows:
                result["by_target"][str(row["target_pull_id"])]["event_rows"][str(row["id"])] = row
        if config_ids:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT id,vehicle_id,effective_at,ended_at,created_at "
                            "FROM vehicle_configurations WHERE id=ANY(:ids)"
                        ),
                        {"ids": [UUID(item) for item in sorted(config_ids)]},
                    )
                )
                .mappings()
                .all()
            )
            result["configuration_rows"] = {str(row["id"]): row for row in rows}
        modification_ids = refs.get("modifications", set())
        if modification_ids:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT id,vehicle_id,configuration_id,installed_at,removed_at,created_at "
                            "FROM modifications WHERE id=ANY(:ids)"
                        ),
                        {"ids": [UUID(item) for item in sorted(modification_ids)]},
                    )
                )
                .mappings()
                .all()
            )
            result["modification_rows"] = {str(row["id"]): row for row in rows}
        for target_refs in result["by_target"].values():
            target_refs["configuration_rows"] = result["configuration_rows"]
            target_refs["modification_rows"] = result["modification_rows"]
        return result


def _record_candidate_exclusion(
    exclusions: list[dict[str, str]],
    candidates: list[DatasetCandidate],
    candidate: dict[str, Any],
    reason: str,
) -> None:
    exclusions.append({"pull_id": candidate["pull_id"], "reason": reason})
    candidates.append(DatasetCandidate(**candidate, exclusion_reason=reason))


def _row_cutoff(definition: DatasetDefinition, pull: Any) -> datetime:
    if definition.cutoff_policy is CutoffPolicy.ROW_START:
        return min(definition.observation_cutoff, cast(datetime, pull["started_at"]))
    if definition.cutoff_policy is CutoffPolicy.ROW_END:
        return min(definition.observation_cutoff, cast(datetime, pull["ended_at"]))
    return definition.observation_cutoff


def _eligible(
    feature: Any,
    item: dict[str, Any],
    cutoff: datetime,
    pull: Any,
    dataset: DatasetDefinition,
) -> bool:
    if item.get("value") is None:
        return True
    available = _datetime(item.get("available_at"))
    end = _datetime(item.get("source_window_end"))
    if available is None or available > cutoff or (end is not None and end > cutoff):
        return False
    if dataset.horizon.kind is HorizonKind.MINUTES_AHEAD and dataset.horizon.duration is None:
        return False
    pull_start = cast(datetime, pull["started_at"])
    pull_end = cast(datetime, pull["ended_at"])
    if feature.availability is TemporalAvailability.PRE_EVENT:
        return end is None or end <= pull_start
    if feature.availability is TemporalAvailability.HISTORICAL_ONLY:
        return end is None or end < pull_start
    if feature.availability is TemporalAvailability.DURING_WINDOW:
        if dataset.horizon.kind is HorizonKind.END_OF_CURRENT_PULL:
            return cutoff <= pull_end
        return True
    if feature.availability is TemporalAvailability.POST_WINDOW:
        if dataset.horizon.kind is HorizonKind.END_OF_CURRENT_PULL:
            return cutoff >= pull_end
        return end is None or end <= cutoff
    return False


def _valid_serialized_value(definition: Any, item: dict[str, Any]) -> bool:
    value = item.get("value")
    if value is None or item.get("unit") != definition.unit:
        return False
    try:
        quality = FeatureQuality(item["quality"])
        if quality not in {FeatureQuality.VALID, FeatureQuality.LIMITED}:
            return False
        if definition.dtype is FeatureDType.FLOAT:
            valid = (
                not isinstance(value, bool)
                and isinstance(value, (int, float))
                and math.isfinite(value)
            )
            return valid and _within_bounds(definition, float(value))
        if definition.dtype is FeatureDType.INTEGER:
            return type(value) is int and _within_bounds(definition, float(value))
        if definition.dtype is FeatureDType.BOOLEAN:
            return type(value) is bool
        if definition.dtype is FeatureDType.CATEGORICAL:
            return isinstance(value, str)
        if definition.dtype is FeatureDType.CATEGORICAL_LIST:
            return isinstance(value, list) and all(isinstance(child, str) for child in value)
    except (KeyError, ValueError):
        return False
    return False


def _lineage_is_safe(
    selected: tuple[Any, ...],
    vector: dict[str, Any],
    provenance: dict[str, Any],
    source_refs: dict[str, Any],
    pull: Any,
    feature_set: Any,
    cutoff: datetime,
    definition: DatasetDefinition,
) -> bool:
    source_refs = source_refs.get("by_target", {}).get(str(feature_set["pull_id"]))
    if source_refs is None:
        return False
    lineage_cutoff = feature_set["observation_cutoff"]
    target_source = source_refs.get("pull_rows", {}).get(str(pull["id"]))
    if target_source is None or (
        target_source["vehicle_id"] != pull["vehicle_id"]
        or target_source["session_id"] != pull["session_id"]
        or target_source["started_at"] != pull["started_at"]
        or target_source["ended_at"] != pull["ended_at"]
        or target_source["created_at"] > lineage_cutoff
        or target_source["session_created_at"] > lineage_cutoff
        or target_source["vehicle_created_at"] > lineage_cutoff
        or target_source["effective_configuration_id"] != feature_set["configuration_id"]
    ):
        return False
    if not _configuration_modifications_are_safe(
        provenance, source_refs, pull, feature_set, lineage_cutoff
    ):
        return False
    for feature in selected:
        item = vector.get(feature.key)
        if not isinstance(item, dict) or item.get("value") is None:
            continue
        if not _eligible(feature, item, cutoff, pull, definition):
            return False
        source_entities = [str(value) for value in item.get("source_entities", [])]
        is_event = "event" in feature.key
        is_prior_pull = feature.key.startswith(
            (
                "history.",
                "temporal_context.pull_order_index",
                "temporal_context.prior_pull_count",
                "thermal.recovery_",
                "thermal.iat_recovery_delta_k",
                "thermal.oil_recovery_delta_k",
                "thermal.pull_to_pull",
                "performance.relative_to_prior",
                "boost_air.history_",
                "fuel.history_",
            )
        )
        if feature.key == "raw_context.engine_code":
            if source_entities != [str(pull["vehicle_id"])]:
                return False
        elif feature.key.startswith("raw_context.configuration_"):
            configuration_id = (
                str(feature_set["configuration_id"]) if feature_set["configuration_id"] else None
            )
            if configuration_id is None or source_entities != [configuration_id]:
                return False
            config_row = source_refs.get("configuration_rows", {}).get(configuration_id)
            if config_row is None or (
                config_row["vehicle_id"] != pull["vehicle_id"]
                or config_row["effective_at"] > pull["started_at"]
                or (
                    config_row["ended_at"] is not None
                    and config_row["ended_at"] <= pull["started_at"]
                )
                or config_row["created_at"] > lineage_cutoff
            ):
                return False
        elif feature.key == "quality.truncated":
            if source_entities != [str(pull["session_id"])]:
                return False
        elif not is_event and not is_prior_pull and source_entities != [str(pull["id"])]:
            return False
        if is_event or is_prior_pull:
            if not source_entities:
                empty_history_is_valid = (
                    (feature.key == "temporal_context.pull_order_index" and item.get("value") == 1)
                    or (
                        feature.key == "temporal_context.prior_pull_count"
                        and item.get("value") == 0
                    )
                    or (is_event and item.get("value") == 0)
                )
                if not empty_history_is_valid:
                    return False
            source_table = "event_rows" if is_event else "pull_rows"
            source_rows = source_refs.get(source_table, {})
            feature_context = provenance.get("source_context", {})
            prior_context = {
                str(candidate.get("id")): candidate
                for candidate in feature_context.get("prior_candidates", [])
            }
            for source_id in source_entities:
                if is_event:
                    source = source_rows.get(source_id)
                    if source is None:
                        return False
                    if (
                        source["vehicle_id"] != pull["vehicle_id"]
                        or source["ended_at"] > lineage_cutoff
                        or source["created_at"] > lineage_cutoff
                        or source["session_created_at"] > lineage_cutoff
                        or source["vehicle_created_at"] > lineage_cutoff
                        or source["started_at"] >= pull["started_at"]
                        or source["ended_at"] >= pull["started_at"]
                    ):
                        return False
                    expected = (
                        str(feature_set["configuration_id"])
                        if feature_set["configuration_id"]
                        else None
                    )
                    actual = (
                        str(source["effective_configuration_id"])
                        if source["effective_configuration_id"]
                        else None
                    )
                    if actual != expected:
                        return False
                    if sorted(source.get("active_modification_ids", [])) != sorted(
                        feature_context.get("active_modification_ids", [])
                    ):
                        return False
                else:
                    source = source_rows.get(source_id)
                    candidate = prior_context.get(source_id)
                    if source is None or candidate is None:
                        return False
                    if (
                        source["vehicle_id"] != pull["vehicle_id"]
                        or source["ended_at"] >= pull["started_at"]
                        or source["ended_at"] > lineage_cutoff
                        or source["created_at"] > lineage_cutoff
                        or source["session_created_at"] > lineage_cutoff
                        or source["vehicle_created_at"] > lineage_cutoff
                    ):
                        return False
                    expected = (
                        str(feature_set["configuration_id"])
                        if feature_set["configuration_id"]
                        else None
                    )
                    actual = (
                        str(source["effective_configuration_id"])
                        if source["effective_configuration_id"]
                        else None
                    )
                    if actual != expected:
                        return False
                    if candidate.get("configuration_id") != actual:
                        return False
                    if sorted(candidate.get("active_modification_ids", [])) != sorted(
                        feature_context.get("active_modification_ids", [])
                    ):
                        return False
                    if sorted(candidate.get("active_modification_ids", [])) != sorted(
                        source.get("active_modification_ids", [])
                    ):
                        return False
    return True


def _configuration_modifications_are_safe(
    provenance: dict[str, Any],
    source_refs: dict[str, Any],
    pull: Any,
    feature_set: Any,
    cutoff: datetime,
) -> bool:
    context = provenance.get("source_context", {})
    modification_rows = source_refs.get("modification_rows", {})
    target_source = source_refs.get("pull_rows", {}).get(str(pull["id"]), pull)
    expected_config = (
        str(feature_set["configuration_id"]) if feature_set["configuration_id"] else None
    )
    expected_active = sorted(str(value) for value in context.get("active_modification_ids", []))
    current_active = sorted(
        str(value) for value in target_source.get("active_modification_ids", [])
    )
    if expected_active != current_active:
        return False
    for identifier in expected_active:
        item = modification_rows.get(str(identifier))
        if item is None:
            return False
        if (
            item["vehicle_id"] != pull["vehicle_id"]
            or item["installed_at"] > pull["started_at"]
            or (item["removed_at"] is not None and item["removed_at"] <= pull["started_at"])
            or item["created_at"] > cutoff
            or (
                item["configuration_id"] is not None
                and str(item["configuration_id"]) != expected_config
            )
        ):
            return False
    return True


def _feature_source_refs(feature_sets: Iterable[Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "pulls": set(),
        "events": set(),
        "configurations": set(),
        "modifications": set(),
    }
    for feature_set in feature_sets:
        target_id = str(feature_set["pull_id"])
        target_refs = result.setdefault(
            "by_target", {target_id: {"pulls": set(), "events": set()}}
        ).setdefault(target_id, {"pulls": set(), "events": set()})
        if feature_set["configuration_id"] is not None:
            result["configurations"].add(str(feature_set["configuration_id"]))
        vector = _json_object(feature_set["feature_values"])
        provenance = _json_object(feature_set["provenance"])
        context = provenance.get("source_context", {})
        result["modifications"].update(
            str(item) for item in context.get("active_modification_ids", [])
        )
        candidate_context = {
            str(candidate.get("id")): candidate for candidate in context.get("prior_candidates", [])
        }
        for key, item in vector.items():
            if not isinstance(item, dict):
                continue
            for entity in item.get("source_entities", []):
                source = str(entity)
                if "event" in key:
                    result["events"].add(source)
                    target_refs["events"].add(source)
                elif key.startswith(
                    (
                        "history.",
                        "temporal_context.pull_order_index",
                        "temporal_context.prior_pull_count",
                        "thermal.recovery_",
                        "thermal.pull_to_pull",
                        "performance.relative_to_prior",
                        "boost_air.history_",
                        "fuel.history_",
                    )
                ):
                    result["pulls"].add(source)
                    target_refs["pulls"].add(source)
                    candidate = candidate_context.get(source)
                    if candidate:
                        result["modifications"].update(
                            str(value) for value in candidate.get("active_modification_ids", [])
                        )
                elif key.startswith("raw_context.configuration_"):
                    result["configurations"].add(source)
        if (
            vector.get("temporal_context.prior_pull_count", {}).get("value", 0)
            or vector.get("temporal_context.pull_order_index", {}).get("value", 1) > 1
        ):
            for candidate in context.get("prior_candidates", []):
                result["pulls"].add(str(candidate["id"]))
                target_refs["pulls"].add(str(candidate["id"]))
                result["modifications"].update(
                    str(value) for value in candidate.get("active_modification_ids", [])
                )
    return result


def _prior_count(vector: dict[str, Any]) -> int:
    item = vector.get("temporal_context.prior_pull_count", {})
    value = item.get("value") if isinstance(item, dict) else None
    return value if type(value) is int else 0


def _within_bounds(definition: Any, value: float) -> bool:
    if definition.bounds is None:
        return True
    lower, upper = definition.bounds
    return (lower is None or value >= lower) and (upper is None or value <= upper)


def _missing_value(reason: MissingReason, unit: str | None) -> dict[str, Any]:
    return {
        "value": None,
        "unit": unit,
        "quality": FeatureQuality.UNAVAILABLE.value,
        "missing_reason": reason.value,
        "available_at": None,
        "source_window_start": None,
        "source_window_end": None,
        "source_entities": [],
    }


def _datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _observation_time(row: dict[str, Any]) -> datetime:
    value = _datetime(row.get("observation_cutoff"))
    if value is None:
        raise DatasetValidationError("row observation_cutoff must be a datetime")
    return value


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        decoded = json.loads(value)
        return decoded if isinstance(decoded, dict) else {}
    return {}


def chronological_split(
    rows: Iterable[dict[str, Any]], train_end: datetime, validation_end: datetime
) -> dict[str, tuple[dict[str, Any], ...]]:
    require_aware(train_end, "train_end")
    require_aware(validation_end, "validation_end")
    if train_end >= validation_end:
        raise ValueError("train_end must precede validation_end")
    ordered = sorted(rows, key=lambda item: (_observation_time(item), item["row_id"]))
    train, validation, test = [], [], []
    for row in ordered:
        observed = _observation_time(row)
        if observed <= train_end:
            train.append(row)
        elif observed <= validation_end:
            validation.append(row)
        else:
            test.append(row)
    return {"train": tuple(train), "validation": tuple(validation), "test": tuple(test)}


def walk_forward_windows(
    rows: Iterable[dict[str, Any]],
    *,
    train_span: timedelta,
    validation_span: timedelta,
    test_span: timedelta,
    step: timedelta,
    minimum_history: int = 0,
) -> tuple[WalkForwardWindow, ...]:
    if (
        min(
            train_span.total_seconds(),
            validation_span.total_seconds(),
            test_span.total_seconds(),
            step.total_seconds(),
        )
        <= 0
    ):
        raise ValueError("walk-forward spans and step must be positive")
    if minimum_history < 0:
        raise ValueError("minimum_history cannot be negative")
    ordered = sorted(rows, key=lambda item: (_observation_time(item), item["row_id"]))
    valid_times = [_observation_time(row) for row in ordered]
    if not valid_times:
        return ()
    first, last = min(valid_times), max(valid_times)
    windows: list[WalkForwardWindow] = []
    train_start = first
    while train_start + train_span + validation_span + test_span <= last + timedelta(
        microseconds=1
    ):
        train_end = train_start + train_span
        validation_end = train_end + validation_span
        test_end = validation_end + test_span
        train_rows = tuple(
            row
            for row in ordered
            if train_start <= _observation_time(row) < train_end
            and _prior_count_from_row(row) >= minimum_history
        )
        validation_rows = tuple(
            row for row in ordered if train_end <= _observation_time(row) < validation_end
        )
        test_rows = tuple(
            row for row in ordered if validation_end <= _observation_time(row) < test_end
        )
        if train_rows and validation_rows and test_rows:
            windows.append(
                WalkForwardWindow(
                    train_start,
                    train_end,
                    validation_end,
                    test_end,
                    train_rows,
                    validation_rows,
                    test_rows,
                )
            )
        train_start += step
    return tuple(windows)


def _prior_count_from_row(row: dict[str, Any]) -> int:
    value = row.get("features", {}).get("temporal_context.prior_pull_count", 0)
    return value if type(value) is int else 0


def profile_dataset(
    rows: Iterable[dict[str, Any]],
    selected: tuple[Any, ...],
    definition: DatasetDefinition,
    *,
    exclusions: Iterable[dict[str, str]] = (),
) -> dict[str, Any]:
    data = tuple(rows)
    excluded = tuple(exclusions)
    by_feature: dict[str, Any] = {}
    outliers: list[dict[str, Any]] = []
    for feature in selected:
        values = [row["features"].get(feature.key) for row in data]
        present = [value for value in values if value is not None]
        numeric = [float(value) for value in present if type(value) in {int, float}]
        item: dict[str, Any] = {
            "unit": feature.unit,
            "availability": feature.availability.value,
            "null_count": len(values) - len(present),
            "null_rate": (len(values) - len(present)) / len(values) if values else 0.0,
        }
        if numeric:
            ordered = sorted(numeric)
            mean = math.fsum(numeric) / len(numeric)
            stddev = math.sqrt(math.fsum((value - mean) ** 2 for value in numeric) / len(numeric))
            quantiles = {str(q): _quantile(ordered, q) for q in (0.0, 0.25, 0.5, 0.75, 0.95, 1.0)}
            item.update(
                {
                    "count": len(numeric),
                    "min": ordered[0],
                    "max": ordered[-1],
                    "mean": mean,
                    "stddev": stddev,
                    "quantiles": quantiles,
                }
            )
            low, high = _quantile(ordered, 0.25), _quantile(ordered, 0.75)
            spread = high - low
            lower_bound, upper_bound = low - 1.5 * spread, high + 1.5 * spread
            for row in data:
                value = row["features"].get(feature.key)
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and (value < lower_bound or value > upper_bound)
                ):
                    outliers.append(
                        {
                            "row_id": row["row_id"],
                            "feature": feature.key,
                            "value": value,
                            "classification": (
                                "synthetic_boundary"
                                if row["quality"].get("data_role") == "synthetic"
                                else "possible_real_extreme"
                            ),
                        }
                    )
        else:
            item.update(
                {
                    "count": len(present),
                    "unique_count": len(set(str(value) for value in present)),
                    "category_counts": dict(
                        sorted(Counter(str(value) for value in present).items())
                    ),
                }
            )
        by_feature[feature.key] = item
    cutoff_dates = sorted(row["observation_cutoff"] for row in data)
    return {
        "row_count": len(data),
        "features": by_feature,
        "time_range": {
            "earliest": cutoff_dates[0] if cutoff_dates else None,
            "latest": cutoff_dates[-1] if cutoff_dates else None,
        },
        "temporal_density_by_day": dict(
            sorted(Counter(str(value)[:10] for value in cutoff_dates).items())
        ),
        "vehicle_distribution": dict(sorted(Counter(row["vehicle_id"] for row in data).items())),
        "configuration_distribution": dict(
            sorted(Counter(row["configuration_id"] or "UNKNOWN" for row in data).items())
        ),
        "missing_stats": {
            "missing_feature_values": sum(len(row["missing"]) for row in data),
            "missing_by_feature": dict(
                sorted(Counter(key for row in data for key in row["missing"]).items())
            ),
        },
        "quality_stats": {
            "quality_state_counts": dict(
                sorted(
                    Counter(
                        str(
                            row["quality"].get("pull_completeness", 0.0)
                            >= definition.minimum_quality
                        )
                        for row in data
                    ).items()
                )
            ),
            "mean_pull_completeness": (
                math.fsum(float(row["quality"].get("pull_completeness", 0.0)) for row in data)
                / len(data)
            )
            if data
            else 0.0,
            "source_roles": dict(
                sorted(
                    Counter(str(row["quality"].get("data_role", "unknown")) for row in data).items()
                )
            ),
            "excluded_quality_row_count": sum(
                item["reason"] == "minimum_quality_not_met" for item in excluded
            ),
            "excluded_quality_rows": sorted(
                (
                    {
                        "row_id": item["pull_id"],
                        "classification": "quality_failure",
                        "reason": item["reason"],
                    }
                    for item in excluded
                    if item["reason"] == "minimum_quality_not_met"
                ),
                key=lambda item: (item["row_id"], item["reason"]),
            ),
        },
        "outliers": sorted(outliers, key=lambda item: (item["feature"], item["row_id"])),
    }


def _quantile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("quantile requires values")
    position = (len(values) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def export_model_ready(dataset: DatasetBuild, name: str) -> tuple[Path, Path]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", name):
        raise ValueError("export name must be a bounded filename token")
    root = Path(__file__).resolve().parents[5] / "apps" / "api" / ".artifacts" / "phase9a"
    root.mkdir(parents=True, exist_ok=True)
    resolved_root = root.resolve()
    data_path = resolved_root / f"{name}.jsonl"
    manifest_path = resolved_root / f"{name}.manifest.json"
    rows = "".join(canonical_json(row) + "\n" for row in dataset.rows).encode("utf-8")
    manifest = canonical_json(dataset.manifest).encode("utf-8") + b"\n"
    if len(rows) + len(manifest) > MAX_EXPORT_BYTES:
        raise DatasetValidationError("dataset export exceeds 64 MiB limit")
    _atomic_write(resolved_root, data_path.name, rows)
    _atomic_write(resolved_root, manifest_path.name, manifest)
    return data_path, manifest_path


def _atomic_write(root: Path, filename: str, content: bytes) -> None:
    if Path(filename).name != filename or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", filename
    ):
        raise ValueError("export filename is invalid")
    target = root / filename
    if target.resolve().parent != root:
        raise ValueError("export path escapes approved artifact directory")
    descriptor, temporary = tempfile.mkstemp(prefix=".phase9a-", dir=root)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
