from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from vehicle_platform.features.domain import canonical_json, require_aware, stable_hash

MAX_REFERENCE_ROWS = 10_000
MAX_SCORE_ROWS = 1_000
MAX_FEATURES_PER_DETECTOR = 8
MAX_FINDING_REASONS = 8


class AnomalyFamily(StrEnum):
    THERMAL = "thermal"
    BOOST_AIR = "boost_air"
    PERFORMANCE = "performance"
    FUEL = "fuel"
    MULTIVARIATE = "multivariate"


class DetectorMethod(StrEnum):
    ROBUST_MAD = "robust_mad"
    ISOLATION_FOREST = "isolation_forest"


class AnomalyStatus(StrEnum):
    ANOMALOUS = "ANOMALOUS"
    INLIER = "INLIER"
    INSUFFICIENT_REFERENCE = "INSUFFICIENT_REFERENCE"
    INSUFFICIENT_SIGNAL = "INSUFFICIENT_SIGNAL"
    LOW_QUALITY = "LOW_QUALITY"
    INCOMPATIBLE_CONTEXT = "INCOMPATIBLE_CONTEXT"
    UNSUPPORTED_SOURCE = "UNSUPPORTED_SOURCE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class AnomalyReason(StrEnum):
    INVALID_CUTOFF = "INVALID_CUTOFF"
    CUTOFF_BEFORE_PULL_END = "CUTOFF_BEFORE_PULL_END"
    FUTURE_FEATURE = "FUTURE_FEATURE"
    FUTURE_REFERENCE = "FUTURE_REFERENCE"
    FEATURE_SET_VERSION_MISMATCH = "FEATURE_SET_VERSION_MISMATCH"
    FEATURE_SCHEMA_MISMATCH = "FEATURE_SCHEMA_MISMATCH"
    INVALID_FEATURE_VALUE = "INVALID_FEATURE_VALUE"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    REQUIRED_FEATURE_MISSING = "REQUIRED_FEATURE_MISSING"
    LOW_PULL_COMPLETENESS = "LOW_PULL_COMPLETENESS"
    INVALID_SAMPLES_PRESENT = "INVALID_SAMPLES_PRESENT"
    DUPLICATE_SAMPLES_PRESENT = "DUPLICATE_SAMPLES_PRESENT"
    SOURCE_ROLE_MISMATCH = "SOURCE_ROLE_MISMATCH"
    SOURCE_NOT_ALLOWLISTED = "SOURCE_NOT_ALLOWLISTED"
    REQUIRED_SIGNAL_UNAVAILABLE = "REQUIRED_SIGNAL_UNAVAILABLE"
    VEHICLE_MISMATCH = "VEHICLE_MISMATCH"
    CONFIGURATION_MISMATCH = "CONFIGURATION_MISMATCH"
    MODIFICATION_MISMATCH = "MODIFICATION_MISMATCH"
    SESSION_OVERLAP = "SESSION_OVERLAP"
    REFERENCE_SUPPORT_TOO_LOW = "REFERENCE_SUPPORT_TOO_LOW"
    REFERENCE_SESSION_SUPPORT_TOO_LOW = "REFERENCE_SESSION_SUPPORT_TOO_LOW"
    REFERENCE_SPAN_TOO_SHORT = "REFERENCE_SPAN_TOO_SHORT"
    FEATURE_COVERAGE_TOO_LOW = "FEATURE_COVERAGE_TOO_LOW"
    CONSTANT_FEATURES_ONLY = "CONSTANT_FEATURES_ONLY"
    ARTIFACT_CORRUPTED = "ARTIFACT_CORRUPTED"
    ARTIFACT_SCHEMA_MISMATCH = "ARTIFACT_SCHEMA_MISMATCH"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    DATA_LEAKAGE_BLOCKED = "DATA_LEAKAGE_BLOCKED"
    INTERNAL_FAILURE = "INTERNAL_FAILURE"


class SourceRole(StrEnum):
    SYNTHETIC = "synthetic"
    REAL_VEHICLE = "real_vehicle"
    IMPORTED = "imported"
    IMPORTED_FIXTURE = "imported_fixture"
    MIXED = "mixed"


class DetectorLifecycle(StrEnum):
    CANDIDATE = "CANDIDATE"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    RETIRED = "RETIRED"


class DeviationDirection(StrEnum):
    BOTH = "both"
    HIGH = "high"
    LOW = "low"


FeatureTransform = Literal["identity", "difference"]
Horizon = Literal["AFTER_PULL_OFFLINE"]


@dataclass(frozen=True)
class DetectorFeatureSpec:
    """A bounded canonical feature input and an optional contextual contrast."""

    key: str
    unit: str
    temporal_availability: str
    required: bool = False
    direction: DeviationDirection = DeviationDirection.BOTH
    transform: FeatureTransform = "identity"
    context_key: str | None = None
    context_unit: str | None = None
    context_temporal_availability: str | None = None

    def __post_init__(self) -> None:
        if not self.key or not self.unit or not self.temporal_availability:
            raise ValueError("anomaly feature key, unit and temporal availability are required")
        if self.transform == "difference":
            if not self.context_key or self.context_unit != self.unit:
                raise ValueError(
                    "difference features require a context feature with matching units"
                )
        elif self.context_key is not None or self.context_unit is not None:
            raise ValueError("context features are valid only for the difference transform")

    @property
    def score_key(self) -> str:
        if self.context_key is None:
            return self.key
        return f"{self.key}__minus__{self.context_key}"

    @property
    def input_keys(self) -> tuple[str, ...]:
        if self.context_key is not None:
            return (self.key, self.context_key)
        return (self.key,)

    def manifest(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "unit": self.unit,
            "temporal_availability": self.temporal_availability,
            "required": self.required,
            "direction": self.direction.value,
            "transform": self.transform,
            "context_key": self.context_key,
            "context_unit": self.context_unit,
            "context_temporal_availability": self.context_temporal_availability,
            "score_key": self.score_key,
        }


@dataclass(frozen=True)
class AnomalyDetectorDefinition:
    key: str
    version: str
    family: AnomalyFamily
    method: DetectorMethod
    intent: str
    features: tuple[DetectorFeatureSpec, ...]
    required_signal_keys: tuple[str, ...]
    supported_source_roles: tuple[SourceRole, ...]
    cohort_policy: dict[str, Any]
    quality_policy: dict[str, Any]
    seed: int
    fit_parameters: dict[str, Any]
    normalization_policy: dict[str, Any]
    threshold_policy: dict[str, Any]
    scoring_version: str
    lifecycle_status: DetectorLifecycle = DetectorLifecycle.CANDIDATE
    horizon: Horizon = "AFTER_PULL_OFFLINE"

    def __post_init__(self) -> None:
        if len(self.features) == 0 or len(self.features) > MAX_FEATURES_PER_DETECTOR:
            raise ValueError("detector feature count must be between one and eight")
        if len({item.score_key for item in self.features}) != len(self.features):
            raise ValueError("detector score feature keys must be unique")
        inputs = self.feature_keys
        if len(inputs) > MAX_FEATURES_PER_DETECTOR:
            raise ValueError("detector input feature count exceeds the fixed limit")
        if not self.key or not self.version or not self.intent:
            raise ValueError("detector identity and intent are required")
        if self.seed < 0 or not self.scoring_version:
            raise ValueError("detector seed and scoring version are invalid")
        if not self.required_signal_keys:
            raise ValueError("detector must declare source capability signals")
        if SourceRole.MIXED in self.supported_source_roles:
            raise ValueError("mixed-source detector fitting is not supported")
        for name in (
            "cohort_policy",
            "quality_policy",
            "fit_parameters",
            "normalization_policy",
            "threshold_policy",
        ):
            canonical_json(getattr(self, name))

    @property
    def feature_keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(key for item in self.features for key in item.input_keys))

    @property
    def score_feature_keys(self) -> tuple[str, ...]:
        return tuple(item.score_key for item in self.features)

    @property
    def required_feature_keys(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(key for item in self.features if item.required for key in item.input_keys)
        )

    @property
    def checksum(self) -> str:
        return stable_hash(self.manifest())

    def manifest(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "version": self.version,
            "family": self.family.value,
            "method": self.method.value,
            "intent": self.intent,
            "feature_keys": list(self.feature_keys),
            "features": [item.manifest() for item in self.features],
            "expected_temporal_availability": {
                key: next(
                    (
                        availability
                        for feature in self.features
                        for feature_key, availability in (
                            (feature.key, feature.temporal_availability),
                            (feature.context_key, feature.context_temporal_availability),
                        )
                        if key == feature_key and availability is not None
                    ),
                    "unknown",
                )
                for key in self.feature_keys
            },
            "required_signal_keys": list(self.required_signal_keys),
            "supported_source_roles": [role.value for role in self.supported_source_roles],
            "cohort_policy": self.cohort_policy,
            "quality_policy": self.quality_policy,
            "seed": self.seed,
            "fit_parameters": self.fit_parameters,
            "normalization_policy": self.normalization_policy,
            "threshold_policy": self.threshold_policy,
            "scoring_version": self.scoring_version,
            "lifecycle_status": self.lifecycle_status.value,
            "horizon": self.horizon,
        }


@dataclass(frozen=True)
class CohortIdentity:
    vehicle_id: str
    configuration_id: str | None
    modification_ids: tuple[str, ...]
    source_role: SourceRole
    source_type: str
    compatibility_version: str = "same-vehicle-effective-configuration-modifications-source-v1"

    def __post_init__(self) -> None:
        if not self.vehicle_id or not self.source_type:
            raise ValueError("cohort vehicle and source type are required")
        object.__setattr__(self, "modification_ids", tuple(sorted(set(self.modification_ids))))
        if self.source_role is SourceRole.MIXED:
            raise ValueError("a detector cohort cannot use a mixed source role")

    def manifest(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "configuration_id": self.configuration_id,
            "modification_ids": list(self.modification_ids),
            "source_role": self.source_role.value,
            "source_type": self.source_type,
            "compatibility_version": self.compatibility_version,
        }

    @property
    def checksum(self) -> str:
        return stable_hash(self.manifest())


@dataclass(frozen=True)
class FeatureObservation:
    key: str
    value: float | None
    unit: str | None
    quality: str
    missing_reason: str | None
    available_at: datetime | None
    source_window_end: datetime | None
    source_signals: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("available_at", self.available_at),
            ("source_window_end", self.source_window_end),
        ):
            if value is not None:
                require_aware(value, name)


@dataclass(frozen=True)
class ReferenceRow:
    row_id: str
    feature_set_id: UUID
    vehicle_id: str
    configuration_id: str | None
    session_id: str
    pull_id: str
    pull_started_at: datetime
    pull_ended_at: datetime
    observation_cutoff: datetime
    source_hash: str
    provenance_hash: str
    source_type: str
    source_role: SourceRole
    modification_ids: tuple[str, ...]
    available_signals: tuple[str, ...]
    quality_metadata: dict[str, Any]
    features: dict[str, FeatureObservation]

    def __post_init__(self) -> None:
        for name, value in (
            ("pull_started_at", self.pull_started_at),
            ("pull_ended_at", self.pull_ended_at),
            ("observation_cutoff", self.observation_cutoff),
        ):
            require_aware(value, name)
        if self.pull_ended_at < self.pull_started_at:
            raise ValueError("pull time range is inverted")
        if self.observation_cutoff < self.pull_started_at:
            raise ValueError("feature observation cutoff predates its pull")
        if not self.row_id or len(self.source_hash) != 64 or len(self.provenance_hash) != 64:
            raise ValueError("reference row identity and source hashes are invalid")
        object.__setattr__(self, "modification_ids", tuple(sorted(set(self.modification_ids))))
        object.__setattr__(self, "available_signals", tuple(sorted(set(self.available_signals))))

    @property
    def cohort(self) -> CohortIdentity:
        return CohortIdentity(
            vehicle_id=self.vehicle_id,
            configuration_id=self.configuration_id,
            modification_ids=self.modification_ids,
            source_role=self.source_role,
            source_type=self.source_type,
        )

    def manifest(self, feature_keys: tuple[str, ...]) -> dict[str, Any]:
        selected_features = {
            key: self.features[key].value if key in self.features else None for key in feature_keys
        }
        selected_missing = {
            key: self.features[key].missing_reason
            for key in feature_keys
            if key in self.features and self.features[key].value is None
        }
        return {
            "row_id": self.row_id,
            "feature_set_id": str(self.feature_set_id),
            "vehicle_id": self.vehicle_id,
            "configuration_id": self.configuration_id,
            "session_id": self.session_id,
            "pull_id": self.pull_id,
            "pull_started_at": self.pull_started_at.isoformat(),
            "pull_ended_at": self.pull_ended_at.isoformat(),
            "observation_cutoff": self.observation_cutoff.isoformat(),
            "source_hash": self.source_hash,
            "provenance_hash": self.provenance_hash,
            "cohort_checksum": self.cohort.checksum,
            "features": selected_features,
            "missing": selected_missing,
        }


@dataclass(frozen=True)
class AnomalyReferenceDataset:
    family: AnomalyFamily
    feature_set_version: str
    feature_set_version_checksum: str
    observation_cutoff: datetime
    cohort: CohortIdentity
    rows: tuple[ReferenceRow, ...]
    exclusions: tuple[dict[str, str], ...]
    source_role: SourceRole
    created_at: datetime
    anchor_session_id: str | None = None
    policy_version: str = "same-vehicle-cohort-cutoff-v1"

    def __post_init__(self) -> None:
        require_aware(self.observation_cutoff, "reference observation_cutoff")
        require_aware(self.created_at, "reference created_at")
        if len(self.rows) > MAX_REFERENCE_ROWS:
            raise ValueError("reference dataset exceeds the 10000-row bound")
        if self.source_role != self.cohort.source_role:
            raise ValueError("reference source role differs from its cohort")
        if len({row.feature_set_id for row in self.rows}) != len(self.rows):
            raise ValueError("reference dataset contains duplicate FeatureSets")
        for row in self.rows:
            if row.observation_cutoff > self.observation_cutoff:
                raise ValueError("reference dataset contains a future FeatureSet")
            if row.cohort != self.cohort:
                raise ValueError("reference dataset contains an incompatible cohort row")

    def manifest(self, definition: AnomalyDetectorDefinition) -> dict[str, Any]:
        ordered = tuple(
            sorted(
                self.rows,
                key=lambda item: (
                    item.pull_started_at,
                    item.session_id,
                    item.pull_id,
                    str(item.feature_set_id),
                ),
            )
        )
        return {
            "schema_version": "phase9c-reference-v1",
            "family": self.family.value,
            "detector_definition_checksum": definition.checksum,
            "feature_set_version": self.feature_set_version,
            "feature_set_version_checksum": self.feature_set_version_checksum,
            "feature_keys": list(definition.feature_keys),
            "observation_cutoff": self.observation_cutoff.isoformat(),
            "anchor_session_id": self.anchor_session_id,
            "cohort": self.cohort.manifest(),
            "cohort_checksum": self.cohort.checksum,
            "row_ids": [row.row_id for row in ordered],
            "selected_rows": [row.manifest(definition.feature_keys) for row in ordered],
            "row_count": len(ordered),
            "independent_session_count": len({row.session_id for row in ordered}),
            "first_pull_at": (
                min(row.pull_started_at for row in ordered).isoformat() if ordered else None
            ),
            "last_pull_at": (
                max(row.pull_started_at for row in ordered).isoformat() if ordered else None
            ),
            "source_role": self.source_role.value,
            "policy_version": self.policy_version,
            "exclusions": sorted(
                (dict(item) for item in self.exclusions),
                key=lambda item: (item.get("row_id", ""), item.get("reason", "")),
            ),
        }

    def checksum(self, definition: AnomalyDetectorDefinition) -> str:
        return stable_hash(self.manifest(definition))

    @property
    def temporal_span(self) -> timedelta:
        if len(self.rows) < 2:
            return timedelta(0)
        starts = [row.pull_started_at for row in self.rows]
        return max(starts) - min(starts)


@dataclass(frozen=True)
class AnomalyFindingResult:
    status: AnomalyStatus
    score: float | None
    threshold: float | None
    coverage: float
    observed_features: tuple[str, ...]
    absent_features: tuple[str, ...]
    contributions: tuple[dict[str, Any], ...]
    reasons: tuple[AnomalyReason, ...]
    score_orientation: str = "higher_is_more_statistically_unusual"

    def __post_init__(self) -> None:
        if not 0.0 <= self.coverage <= 1.0:
            raise ValueError("finding coverage must be in [0, 1]")
        if len(self.reasons) > MAX_FINDING_REASONS:
            raise ValueError("finding has too many reason codes")
        if self.score is not None and not math.isfinite(self.score):
            raise ValueError("finding score must be finite")
        if self.threshold is not None and not math.isfinite(self.threshold):
            raise ValueError("finding threshold must be finite")

    def manifest(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "score": self.score,
            "threshold": self.threshold,
            "coverage": self.coverage,
            "observed_features": list(self.observed_features),
            "absent_features": list(self.absent_features),
            "contributions": list(self.contributions),
            "reason_codes": [reason.value for reason in self.reasons],
            "score_orientation": self.score_orientation,
            "horizon": "AFTER_PULL_OFFLINE",
            "interpretation": "engineering statistical deviation, not a confirmed fault",
        }


@dataclass(frozen=True)
class AnomalyRunResult:
    run_identity: str
    status: str
    detector_version_id: UUID
    reference_dataset_id: UUID
    observation_cutoff: datetime
    source_role: SourceRole
    finding_ids: tuple[UUID, ...]
    counts: dict[str, int]
    duration_seconds: float
    artifact_checksum: str | None
    input_checksum: str
    error_category: str | None = None
    trace_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        require_aware(self.observation_cutoff, "run observation_cutoff")
        require_aware(self.created_at, "run created_at")
        if self.duration_seconds < 0:
            raise ValueError("run duration cannot be negative")
        if len(self.input_checksum) != 64 or (
            self.artifact_checksum is not None and len(self.artifact_checksum) != 64
        ):
            raise ValueError("run checksums must be SHA-256 when present")
        if self.trace_id is not None and len(self.trace_id) != 32:
            raise ValueError("trace ID must be a 32-character hexadecimal value")


def finding_idempotency_key(
    *,
    detector_version_id: UUID,
    observation: ReferenceRow,
    observation_cutoff: datetime,
    scoring_version: str,
    threshold: float | None,
) -> str:
    require_aware(observation_cutoff, "finding observation_cutoff")
    return stable_hash(
        {
            "detector_version_id": str(detector_version_id),
            "feature_set_id": str(observation.feature_set_id),
            "source_hash": observation.source_hash,
            "provenance_hash": observation.provenance_hash,
            "observation_cutoff": observation_cutoff.isoformat(),
            "scope": {
                "vehicle_id": observation.vehicle_id,
                "configuration_id": observation.configuration_id,
                "session_id": observation.session_id,
                "pull_id": observation.pull_id,
            },
            "scoring_version": scoring_version,
            "threshold": threshold,
            "horizon": "AFTER_PULL_OFFLINE",
        }
    )
