import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

FeatureScalar = str | int | float | bool | None
FeatureValueData = FeatureScalar | list[str]


class FeatureCategory(StrEnum):
    RAW_CONTEXT = "raw_context"
    SESSION = "session"
    PULL = "pull"
    THERMAL = "thermal"
    PERFORMANCE = "performance"
    BOOST_AIR = "boost_air"
    FUEL = "fuel"
    QUALITY = "quality"
    HISTORY = "history"
    TEMPORAL_CONTEXT = "temporal_context"


class EntityScope(StrEnum):
    VEHICLE = "vehicle"
    CONFIGURATION = "configuration"
    SESSION = "session"
    PULL = "pull"
    WINDOW = "window"


class FeatureDType(StrEnum):
    FLOAT = "float"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"
    CATEGORICAL_LIST = "categorical_list"


class TemporalAvailability(StrEnum):
    PRE_EVENT = "pre_event"
    DURING_WINDOW = "during_window"
    POST_WINDOW = "post_window"
    HISTORICAL_ONLY = "historical_only"


class AcquisitionClass(StrEnum):
    CORE = "CORE"
    OPTIONAL = "OPTIONAL"
    SOURCE_SPECIFIC = "SOURCE_SPECIFIC"


class MissingReason(StrEnum):
    UNAVAILABLE_SIGNAL = "unavailable_signal"
    INSUFFICIENT_COVERAGE = "insufficient_coverage"
    INVALID_QUALITY = "invalid_quality"
    NOT_APPLICABLE = "not_applicable"
    NOT_OBSERVED_YET = "not_observed_yet"
    COMPUTATION_ERROR = "computation_error"


class FeatureQuality(StrEnum):
    VALID = "valid"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


class HorizonKind(StrEnum):
    NEXT_PULL = "next_pull"
    NEXT_SESSION = "next_session"
    END_OF_CURRENT_PULL = "end_of_current_pull"
    MINUTES_AHEAD = "minutes_ahead"


class CutoffPolicy(StrEnum):
    ROW_START = "row_start"
    ROW_END = "row_end"
    GLOBAL = "global"


class SplitPolicy(StrEnum):
    CHRONOLOGICAL = "chronological"
    WALK_FORWARD = "walk_forward"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone offset")


@dataclass(frozen=True)
class PredictionHorizon:
    kind: HorizonKind
    minutes: int | None = None

    def __post_init__(self) -> None:
        if self.kind is HorizonKind.MINUTES_AHEAD:
            if self.minutes is None or not 1 <= self.minutes <= 1440:
                raise ValueError("minutes_ahead horizon requires 1..1440 minutes")
        elif self.minutes is not None:
            raise ValueError("minutes is valid only for minutes_ahead")

    @property
    def duration(self) -> timedelta | None:
        return timedelta(minutes=self.minutes) if self.minutes is not None else None


@dataclass(frozen=True)
class FeatureDefinition:
    key: str
    name: str
    description: str
    category: FeatureCategory
    unit: str | None
    dtype: FeatureDType
    scope: EntityScope
    required_signals: tuple[str, ...] = ()
    optional_signals: tuple[str, ...] = ()
    acquisition_class: AcquisitionClass = AcquisitionClass.CORE
    minimum_quality: float = 0.0
    algorithm_id: str = "vehicle-platform.feature"
    algorithm_version: str = "1"
    availability: TemporalAvailability = TemporalAvailability.PRE_EVENT
    nullable: bool = True
    bounds: tuple[float | None, float | None] | None = None
    tags: tuple[str, ...] = ()
    active: bool = True

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", self.key):
            raise ValueError("feature key must be canonical dotted lower_snake_case")
        if not self.name.strip() or not self.description.strip():
            raise ValueError("feature name and description are required")
        if self.dtype in {FeatureDType.FLOAT, FeatureDType.INTEGER} and not self.unit:
            raise ValueError("numeric features require a canonical unit")
        if not 0 <= self.minimum_quality <= 1:
            raise ValueError("minimum_quality must be between zero and one")
        if not self.algorithm_id or not self.algorithm_version:
            raise ValueError("algorithm identity and version are required")
        if self.bounds and self.bounds[0] is not None and self.bounds[1] is not None:
            if self.bounds[0] > self.bounds[1]:
                raise ValueError("feature bounds must be increasing")

    def manifest(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "unit": self.unit,
            "dtype": self.dtype.value,
            "scope": self.scope.value,
            "required_signals": list(self.required_signals),
            "optional_signals": list(self.optional_signals),
            "acquisition_class": self.acquisition_class.value,
            "minimum_quality": self.minimum_quality,
            "algorithm_id": self.algorithm_id,
            "algorithm_version": self.algorithm_version,
            "availability": self.availability.value,
            "nullable": self.nullable,
            "bounds": list(self.bounds) if self.bounds else None,
            "tags": list(self.tags),
            "active": self.active,
        }


@dataclass(frozen=True)
class FeatureSetVersion:
    version: str
    definitions: tuple[FeatureDefinition, ...]
    generator_version: str
    source_schema_version: str
    selection_policy: dict[str, Any]
    quality_policy: dict[str, Any]
    temporal_policy: dict[str, Any]
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}", self.version):
            raise ValueError("invalid feature set version")
        require_aware(self.created_at, "created_at") if self.created_at else None
        keys = [item.key for item in self.definitions]
        if not keys or len(keys) != len(set(keys)):
            raise ValueError("feature set version must contain unique definitions")

    def manifest(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "definitions": [item.manifest() for item in self.definitions],
            "generator_version": self.generator_version,
            "source_schema_version": self.source_schema_version,
            "selection_policy": self.selection_policy,
            "quality_policy": self.quality_policy,
            "temporal_policy": self.temporal_policy,
        }

    @property
    def checksum(self) -> str:
        return stable_hash(self.manifest())


@dataclass(frozen=True)
class FeatureValue:
    value: FeatureValueData
    unit: str | None
    quality: FeatureQuality
    missing_reason: MissingReason | None
    available_at: datetime | None
    source_window_start: datetime | None
    source_window_end: datetime | None
    source_signals: tuple[str, ...] = ()
    source_entities: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("available_at", self.available_at),
            ("source_window_start", self.source_window_start),
            ("source_window_end", self.source_window_end),
        ):
            if value is not None:
                require_aware(value, name)
        if self.source_window_start and self.source_window_end:
            if self.source_window_start > self.source_window_end:
                raise ValueError("feature source window is inverted")
        if self.value is None and self.missing_reason is None:
            raise ValueError("missing feature values require an explicit reason")
        if self.value is not None and self.missing_reason is not None:
            raise ValueError("available feature values cannot have a missing reason")
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("feature numeric values must be finite")
        if isinstance(self.value, list) and any(not isinstance(item, str) for item in self.value):
            raise ValueError("categorical list values must contain strings")

    def manifest(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "quality": self.quality.value,
            "missing_reason": self.missing_reason.value if self.missing_reason else None,
            "available_at": self.available_at.isoformat() if self.available_at else None,
            "source_window_start": (
                self.source_window_start.isoformat() if self.source_window_start else None
            ),
            "source_window_end": (
                self.source_window_end.isoformat() if self.source_window_end else None
            ),
            "source_signals": list(self.source_signals),
            "source_entities": list(self.source_entities),
            "details": self.details,
        }


@dataclass(frozen=True)
class FeatureSet:
    id: UUID
    vehicle_id: UUID
    configuration_id: UUID | None
    session_id: UUID
    pull_id: UUID
    scope: EntityScope
    feature_set_version: str
    generated_at: datetime
    source_window_start: datetime
    source_window_end: datetime
    observation_cutoff: datetime
    values: dict[str, FeatureValue]
    quality_metadata: dict[str, Any]
    provenance: dict[str, Any]
    provenance_hash: str
    source_hash: str
    generator_version: str


@dataclass(frozen=True)
class LabelDefinition:
    key: str
    source_signals: tuple[str, ...] = ()
    source_feature_keys: tuple[str, ...] = ()
    post_outcome: bool = True
    version: str = "1.0.0"
    name: str = ""
    description: str = ""
    dtype: str = "boolean"
    task_type: str = "classification"
    horizon: PredictionHorizon = field(
        default_factory=lambda: PredictionHorizon(HorizonKind.NEXT_PULL)
    )
    source_outcome: str = "future_observable_outcome"
    algorithm_id: str = "vehicle-platform.label"
    algorithm_version: str = "1"
    required_signals: tuple[str, ...] = ()
    quality_policy: dict[str, Any] = field(default_factory=dict)
    compatibility_policy: dict[str, Any] = field(default_factory=dict)
    threshold_policy: dict[str, Any] = field(default_factory=dict)
    provenance_policy: dict[str, Any] = field(default_factory=dict)
    active: bool = True

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,119}", self.key):
            raise ValueError("label key must be a bounded stable identifier")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", self.version):
            raise ValueError("invalid label definition version")
        if self.dtype not in {"boolean", "float", "integer"}:
            raise ValueError("unsupported label dtype")
        if self.task_type not in {"classification", "regression"}:
            raise ValueError("unsupported label task type")
        if not self.algorithm_id or not self.algorithm_version or not self.source_outcome:
            raise ValueError("label algorithm and outcome source are required")
        signals = tuple(dict.fromkeys((*self.source_signals, *self.required_signals)))
        object.__setattr__(self, "source_signals", signals)
        object.__setattr__(self, "required_signals", signals)
        for name in (
            "quality_policy",
            "compatibility_policy",
            "threshold_policy",
            "provenance_policy",
        ):
            object.__setattr__(self, name, dict(getattr(self, name)))

    def manifest(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "version": self.version,
            "name": self.name or self.key,
            "description": self.description,
            "dtype": self.dtype,
            "task_type": self.task_type,
            "horizon": {"kind": self.horizon.kind.value, "minutes": self.horizon.minutes},
            "source_outcome": self.source_outcome,
            "source_signals": list(self.source_signals),
            "required_signals": list(self.required_signals),
            "source_feature_keys": list(self.source_feature_keys),
            "algorithm_id": self.algorithm_id,
            "algorithm_version": self.algorithm_version,
            "quality_policy": self.quality_policy,
            "compatibility_policy": self.compatibility_policy,
            "threshold_policy": self.threshold_policy,
            "provenance_policy": self.provenance_policy,
            "post_outcome": self.post_outcome,
            "active": self.active,
        }

    @property
    def checksum(self) -> str:
        return stable_hash(self.manifest())


@dataclass(frozen=True)
class DatasetDefinition:
    name: str
    version: str
    row_scope: EntityScope
    feature_set_version: str
    selected_features: tuple[str, ...]
    observation_cutoff: datetime
    cutoff_policy: CutoffPolicy = CutoffPolicy.ROW_END
    horizon: PredictionHorizon = field(
        default_factory=lambda: PredictionHorizon(HorizonKind.NEXT_PULL)
    )
    minimum_history: int = 0
    minimum_quality: float = 0.0
    required_features: tuple[str, ...] = ()
    allow_configuration_mixing: bool = False
    split_policy: SplitPolicy = SplitPolicy.CHRONOLOGICAL
    label_definition: LabelDefinition | None = None
    source: Literal["synthetic", "real_vehicle", "imported", "imported_fixture", "mixed"] = (
        "synthetic"
    )

    def __post_init__(self) -> None:
        require_aware(self.observation_cutoff, "observation_cutoff")
        if self.row_scope is not EntityScope.PULL:
            raise ValueError("Phase 9A dataset rows are pull-scoped")
        if not self.name.strip() or not self.version.strip():
            raise ValueError("dataset name and version are required")
        if not self.selected_features or len(self.selected_features) > 64:
            raise ValueError("dataset must select 1..64 features")
        if len(set(self.selected_features)) != len(self.selected_features):
            raise ValueError("dataset feature keys must be unique")
        if not set(self.required_features).issubset(self.selected_features):
            raise ValueError("required features must be selected")
        if self.minimum_history < 0 or not 0 <= self.minimum_quality <= 1:
            raise ValueError("invalid dataset history or quality requirement")
        if self.label_definition and self.label_definition.key in self.selected_features:
            raise ValueError("label key cannot be selected as an input feature")
        if self.label_definition and set(self.selected_features).intersection(
            self.label_definition.source_feature_keys
        ):
            raise ValueError("dataset feature selection conflicts with label source features")

    def manifest(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "row_scope": self.row_scope.value,
            "feature_set_version": self.feature_set_version,
            "selected_features": list(self.selected_features),
            "observation_cutoff": self.observation_cutoff.isoformat(),
            "cutoff_policy": self.cutoff_policy.value,
            "horizon": {"kind": self.horizon.kind.value, "minutes": self.horizon.minutes},
            "minimum_history": self.minimum_history,
            "minimum_quality": self.minimum_quality,
            "required_features": list(self.required_features),
            "allow_configuration_mixing": self.allow_configuration_mixing,
            "split_policy": self.split_policy.value,
            "label_definition": self.label_definition.manifest() if self.label_definition else None,
            "source": self.source,
        }

    @property
    def checksum(self) -> str:
        return stable_hash(self.manifest())
