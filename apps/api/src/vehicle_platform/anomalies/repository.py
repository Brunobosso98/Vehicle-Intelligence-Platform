from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import text

from vehicle_platform.anomalies.domain import (
    MAX_REFERENCE_ROWS,
    MAX_SCORE_ROWS,
    AnomalyDetectorDefinition,
    AnomalyReason,
    AnomalyReferenceDataset,
    FeatureObservation,
    ReferenceRow,
    SourceRole,
)
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.infrastructure.database import Database

MAX_REFERENCE_PAYLOAD_BYTES = 32 * 1024 * 1024
FEATURE_SET_VERSION = "phase9a-pull-v2"


class AnomalyRepositoryError(ValueError):
    def __init__(self, reason: AnomalyReason, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class AnomalyDataRepository:
    """Read and validate canonical Phase 9A snapshots for offline 9C work."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def load_anchor(
        self,
        pull_id: UUID,
        observation_cutoff: datetime,
        source_role: SourceRole,
        definition: AnomalyDetectorDefinition,
    ) -> tuple[ReferenceRow, UUID, str]:
        _aware_cutoff(observation_cutoff)
        if source_role is SourceRole.MIXED:
            raise AnomalyRepositoryError(
                AnomalyReason.SOURCE_NOT_ALLOWLISTED,
                "mixed-source fitting is not allowed",
            )
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT fs.*,p.started_at AS pull_started_at,p.ended_at AS pull_ended_at,"
                            "s.source_type,v.checksum AS feature_version_checksum "
                            "FROM feature_sets fs JOIN pulls p ON p.id=fs.pull_id "
                            "JOIN driving_sessions s ON s.id=fs.session_id "
                            "JOIN feature_set_versions v ON v.id=fs.feature_set_version_id "
                            "WHERE fs.pull_id=:pull_id AND fs.entity_scope='pull' "
                            "AND v.version=:feature_version AND fs.observation_cutoff<=:cutoff "
                            "ORDER BY fs.observation_cutoff DESC,fs.generated_at DESC,fs.id DESC LIMIT 1"
                        ),
                        {
                            "pull_id": pull_id,
                            "feature_version": FEATURE_SET_VERSION,
                            "cutoff": observation_cutoff,
                        },
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise AnomalyRepositoryError(
                AnomalyReason.FEATURE_SET_VERSION_MISMATCH,
                "anchor pull has no Phase 9A FeatureSet available by the requested cutoff",
            )
        anchor = _reference_row(row, definition.feature_keys)
        if anchor.source_role is not source_role:
            raise AnomalyRepositoryError(
                AnomalyReason.SOURCE_ROLE_MISMATCH,
                "explicit source role differs from the anchor FeatureSet role",
            )
        version_id = cast(UUID, row["feature_set_version_id"])
        version_checksum = str(row["feature_version_checksum"])
        if row["generator_version"] != "phase9a-feature-generator-v2":
            raise AnomalyRepositoryError(
                AnomalyReason.FEATURE_SET_VERSION_MISMATCH,
                "anchor FeatureSet generator is not the approved Phase 9A v2 generator",
            )
        return anchor, version_id, version_checksum

    async def materialize_reference(
        self,
        anchor: ReferenceRow,
        feature_set_version_id: UUID,
        feature_set_version_checksum: str,
        definition: AnomalyDetectorDefinition,
        source_role: SourceRole,
    ) -> AnomalyReferenceDataset:
        reference_cutoff = anchor.pull_started_at
        async with self.database.session() as db:
            preflight = (
                (
                    await db.execute(
                        text(
                            "WITH selected AS ("
                            "SELECT DISTINCT ON (fs.pull_id) fs.id,fs.feature_values,"
                            "fs.quality_metadata,fs.provenance "
                            "FROM feature_sets fs JOIN pulls p ON p.id=fs.pull_id "
                            "JOIN driving_sessions s ON s.id=fs.session_id "
                            "WHERE fs.vehicle_id=:vehicle_id AND fs.entity_scope='pull' "
                            "AND fs.feature_set_version_id=:feature_version_id "
                            "AND p.started_at<:reference_cutoff AND p.ended_at<:reference_cutoff "
                            "AND p.created_at<=:reference_cutoff AND s.created_at<=:reference_cutoff "
                            "AND fs.observation_cutoff<=:reference_cutoff "
                            "ORDER BY fs.pull_id,fs.observation_cutoff DESC,fs.generated_at DESC,fs.id DESC"
                            ") SELECT count(*) AS row_count,"
                            "COALESCE(sum(octet_length(feature_values::text) + "
                            "octet_length(quality_metadata::text) + octet_length(provenance::text)),0) "
                            "AS payload_bytes FROM selected"
                        ),
                        {
                            "vehicle_id": UUID(anchor.vehicle_id),
                            "feature_version_id": feature_set_version_id,
                            "reference_cutoff": reference_cutoff,
                        },
                    )
                )
                .mappings()
                .one()
            )
            if int(preflight["row_count"]) > MAX_REFERENCE_ROWS:
                raise AnomalyRepositoryError(
                    AnomalyReason.RESOURCE_LIMIT,
                    "reference candidate set exceeds the 10000-row bound",
                )
            if int(preflight["payload_bytes"]) > MAX_REFERENCE_PAYLOAD_BYTES:
                raise AnomalyRepositoryError(
                    AnomalyReason.RESOURCE_LIMIT,
                    "reference source payload exceeds the 32 MiB bound",
                )
            candidates = (
                (
                    await db.execute(
                        text(
                            "WITH selected AS ("
                            "SELECT DISTINCT ON (fs.pull_id) fs.id "
                            "FROM feature_sets fs JOIN pulls p ON p.id=fs.pull_id "
                            "JOIN driving_sessions s ON s.id=fs.session_id "
                            "WHERE fs.vehicle_id=:vehicle_id AND fs.entity_scope='pull' "
                            "AND fs.feature_set_version_id=:feature_version_id "
                            "AND p.started_at<:reference_cutoff AND p.ended_at<:reference_cutoff "
                            "AND p.created_at<=:reference_cutoff AND s.created_at<=:reference_cutoff "
                            "AND fs.observation_cutoff<=:reference_cutoff "
                            "ORDER BY fs.pull_id,fs.observation_cutoff DESC,fs.generated_at DESC,fs.id DESC"
                            ") SELECT fs.*,p.started_at AS pull_started_at,p.ended_at AS pull_ended_at,"
                            "p.vehicle_id AS pull_vehicle_id,p.configuration_id AS pull_configuration_id,"
                            "p.session_id AS pull_session_id,p.created_at AS pull_created_at,"
                            "s.source_type,s.created_at AS session_created_at "
                            "FROM selected selected_fs JOIN feature_sets fs ON fs.id=selected_fs.id "
                            "JOIN pulls p ON p.id=fs.pull_id JOIN driving_sessions s ON s.id=fs.session_id "
                            "ORDER BY p.started_at,p.session_id,p.id"
                        ),
                        {
                            "vehicle_id": UUID(anchor.vehicle_id),
                            "feature_version_id": feature_set_version_id,
                            "reference_cutoff": reference_cutoff,
                        },
                    )
                )
                .mappings()
                .all()
            )

        eligible: list[ReferenceRow] = []
        exclusions: list[dict[str, str]] = []
        seen_source_hashes: set[str] = set()
        for row in candidates:
            candidate = _reference_row(row, definition.feature_keys)
            reason = _cohort_exclusion(anchor, candidate, source_role)
            if reason is None:
                reason = _quality_exclusion(candidate, definition)
            if reason is None:
                reason = _feature_exclusion(candidate, definition)
            if reason is None and not set(definition.required_signal_keys).intersection(
                candidate.available_signals
            ):
                reason = AnomalyReason.REQUIRED_SIGNAL_UNAVAILABLE.value
            if reason is None and candidate.source_hash in seen_source_hashes:
                reason = "duplicate_source_lineage"
            if reason is not None:
                exclusions.append({"row_id": candidate.row_id, "reason": reason})
                continue
            seen_source_hashes.add(candidate.source_hash)
            eligible.append(candidate)
        eligible.sort(
            key=lambda item: (
                item.pull_started_at,
                item.session_id,
                item.pull_id,
                str(item.feature_set_id),
            )
        )
        return AnomalyReferenceDataset(
            family=definition.family,
            feature_set_version=FEATURE_SET_VERSION,
            feature_set_version_checksum=feature_set_version_checksum,
            observation_cutoff=reference_cutoff,
            cohort=anchor.cohort,
            rows=tuple(eligible),
            exclusions=tuple(exclusions),
            source_role=source_role,
            created_at=datetime.now(UTC),
            anchor_session_id=anchor.session_id,
        )

    async def load_targets(
        self,
        pull_ids: tuple[UUID, ...],
        observation_cutoff: datetime,
        definition: AnomalyDetectorDefinition,
    ) -> tuple[ReferenceRow, ...]:
        _aware_cutoff(observation_cutoff)
        if not pull_ids or len(pull_ids) > MAX_SCORE_ROWS:
            raise AnomalyRepositoryError(
                AnomalyReason.RESOURCE_LIMIT,
                "score selection must contain between one and 1000 pulls",
            )
        if len(set(pull_ids)) != len(pull_ids):
            raise AnomalyRepositoryError(
                AnomalyReason.FEATURE_SCHEMA_MISMATCH,
                "score selection contains duplicate pull IDs",
            )
        async with self.database.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT DISTINCT ON (fs.pull_id) fs.*,p.started_at AS pull_started_at,"
                            "p.ended_at AS pull_ended_at,s.source_type "
                            "FROM feature_sets fs JOIN pulls p ON p.id=fs.pull_id "
                            "JOIN driving_sessions s ON s.id=fs.session_id "
                            "JOIN feature_set_versions v ON v.id=fs.feature_set_version_id "
                            "WHERE fs.pull_id=ANY(:pull_ids) AND fs.entity_scope='pull' "
                            "AND v.version=:feature_version AND fs.observation_cutoff<=:cutoff "
                            "ORDER BY fs.pull_id,fs.observation_cutoff DESC,fs.generated_at DESC,fs.id DESC"
                        ),
                        {
                            "pull_ids": list(pull_ids),
                            "feature_version": FEATURE_SET_VERSION,
                            "cutoff": observation_cutoff,
                        },
                    )
                )
                .mappings()
                .all()
            )
        return tuple(_reference_row(row, definition.feature_keys) for row in rows)


def _reference_row(row: Any, feature_keys: tuple[str, ...]) -> ReferenceRow:
    feature_values = _json_object(row.get("feature_values"))
    quality_metadata = _json_object(row.get("quality_metadata"))
    provenance = _json_object(row.get("provenance"))
    source_context = _json_object(provenance.get("source_context"))
    role_value = quality_metadata.get("data_role")
    if not isinstance(role_value, str) or role_value not in {item.value for item in SourceRole}:
        role_value = _fallback_source_role(str(row["source_type"]))
    role = SourceRole(role_value)
    features: dict[str, FeatureObservation] = {}
    for key in feature_keys:
        serialized = _json_object(feature_values.get(key))
        value = serialized.get("value")
        unit = serialized.get("unit")
        quality = serialized.get("quality")
        numeric: float | None
        if value is None:
            numeric = None
        elif isinstance(value, bool) or not isinstance(value, (int, float)):
            numeric = None
            quality = "invalid"
        else:
            numeric = float(value)
            if not math.isfinite(numeric):
                numeric = None
                quality = "invalid"
        features[key] = FeatureObservation(
            key=key,
            value=numeric,
            unit=str(unit) if unit is not None else None,
            quality=str(quality) if quality is not None else "invalid",
            missing_reason=(
                str(serialized["missing_reason"])
                if serialized.get("missing_reason") is not None
                else None
            ),
            available_at=_datetime(serialized.get("available_at")),
            source_window_end=_datetime(serialized.get("source_window_end")),
            source_signals=tuple(
                sorted(str(item) for item in serialized.get("source_signals", []) if item)
            ),
        )
    source_signals = quality_metadata.get("available_signals", [])
    return ReferenceRow(
        row_id=stable_hash(
            {
                "feature_set_id": str(row["id"]),
                "source_hash": str(row["source_hash"]),
                "observation_cutoff": row["observation_cutoff"].isoformat(),
            }
        ),
        feature_set_id=cast(UUID, row["id"]),
        vehicle_id=str(row["vehicle_id"]),
        configuration_id=(
            str(row["configuration_id"]) if row["configuration_id"] is not None else None
        ),
        session_id=str(row["session_id"]),
        pull_id=str(row["pull_id"]),
        pull_started_at=cast(datetime, row["pull_started_at"]),
        pull_ended_at=cast(datetime, row["pull_ended_at"]),
        observation_cutoff=cast(datetime, row["observation_cutoff"]),
        source_hash=str(row["source_hash"]),
        provenance_hash=str(row["provenance_hash"]),
        source_type=str(row["source_type"]),
        source_role=role,
        modification_ids=tuple(
            sorted(str(item) for item in source_context.get("active_modification_ids", []))
        ),
        available_signals=tuple(
            sorted(str(item) for item in source_signals if isinstance(item, str))
        ),
        quality_metadata=quality_metadata,
        features=features,
    )


def _cohort_exclusion(
    anchor: ReferenceRow,
    candidate: ReferenceRow,
    source_role: SourceRole,
) -> str | None:
    if candidate.vehicle_id != anchor.vehicle_id:
        return AnomalyReason.VEHICLE_MISMATCH.value
    if candidate.session_id == anchor.session_id:
        return AnomalyReason.SESSION_OVERLAP.value
    if candidate.pull_ended_at >= anchor.pull_started_at:
        return AnomalyReason.FUTURE_REFERENCE.value
    if candidate.observation_cutoff >= anchor.pull_started_at:
        return AnomalyReason.FUTURE_REFERENCE.value
    if candidate.configuration_id != anchor.configuration_id:
        return AnomalyReason.CONFIGURATION_MISMATCH.value
    if candidate.modification_ids != anchor.modification_ids:
        return AnomalyReason.MODIFICATION_MISMATCH.value
    if candidate.source_type != anchor.source_type or candidate.source_role is not source_role:
        return AnomalyReason.SOURCE_ROLE_MISMATCH.value
    return None


def _quality_exclusion(
    row: ReferenceRow,
    definition: AnomalyDetectorDefinition,
) -> str | None:
    policy = definition.quality_policy
    completeness = row.quality_metadata.get("pull_completeness")
    if not isinstance(completeness, (int, float)) or not math.isfinite(float(completeness)):
        return AnomalyReason.LOW_PULL_COMPLETENESS.value
    if float(completeness) < float(policy["minimum_pull_completeness"]):
        return AnomalyReason.LOW_PULL_COMPLETENESS.value
    invalid_count = row.quality_metadata.get("invalid_observation_count", 0)
    duplicate_count = row.quality_metadata.get("duplicate_timestamp_count", 0)
    if not isinstance(invalid_count, int) or invalid_count > int(
        policy["maximum_invalid_observation_count"]
    ):
        return AnomalyReason.INVALID_SAMPLES_PRESENT.value
    if not isinstance(duplicate_count, int) or duplicate_count > int(
        policy["maximum_duplicate_timestamp_count"]
    ):
        return AnomalyReason.DUPLICATE_SAMPLES_PRESENT.value
    return None


def _feature_exclusion(
    row: ReferenceRow,
    definition: AnomalyDetectorDefinition,
) -> str | None:
    for key in definition.feature_keys:
        item = row.features.get(key)
        feature = DEFAULT_REGISTRY.resolve(key)
        if item is None or item.value is None:
            if item is None or item.missing_reason is None or item.quality == "invalid":
                return AnomalyReason.INVALID_FEATURE_VALUE.value
            if key in definition.required_feature_keys:
                if item is not None and item.missing_reason == "unavailable_signal":
                    return AnomalyReason.REQUIRED_SIGNAL_UNAVAILABLE.value
                return AnomalyReason.REQUIRED_FEATURE_MISSING.value
            continue
        if item.unit != feature.unit:
            return AnomalyReason.UNIT_MISMATCH.value
        permitted_quality = (
            {"valid"} if key in definition.required_feature_keys else {"valid", "limited"}
        )
        if item.quality not in permitted_quality:
            return AnomalyReason.INVALID_SAMPLES_PRESENT.value
        if not math.isfinite(item.value):
            return AnomalyReason.INVALID_FEATURE_VALUE.value
        if feature.bounds:
            low, high = feature.bounds
            if (low is not None and item.value < low) or (high is not None and item.value > high):
                return AnomalyReason.INVALID_FEATURE_VALUE.value
        if item.available_at is None or item.available_at > row.observation_cutoff:
            return AnomalyReason.FUTURE_FEATURE.value
        if item.source_window_end is not None and item.source_window_end > row.observation_cutoff:
            return AnomalyReason.FUTURE_FEATURE.value
    return None


def _fallback_source_role(source_type: str) -> str:
    if source_type == "synthetic":
        return SourceRole.SYNTHETIC.value
    if source_type in {"csv", "replay"}:
        return SourceRole.IMPORTED.value
    if source_type == "obd":
        return SourceRole.REAL_VEHICLE.value
    return SourceRole.MIXED.value


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        decoded = json.loads(value)
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _aware_cutoff(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AnomalyRepositoryError(
            AnomalyReason.INVALID_CUTOFF,
            "observation cutoff must include a timezone offset",
        )
