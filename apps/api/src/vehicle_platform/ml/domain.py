from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from vehicle_platform.features.domain import LabelDefinition, stable_hash


class MLTask(StrEnum):
    THERMAL_DEGRADATION = "NEXT_PULL_THERMAL_DEGRADATION"
    PERFORMANCE_DEGRADATION = "NEXT_PULL_PERFORMANCE_DEGRADATION"
    FUEL_DEVIATION = "NEXT_PULL_FUEL_DEVIATION"


class ModelState(StrEnum):
    TRAINING = "TRAINING"
    EVALUATED = "EVALUATED"
    REJECTED = "REJECTED"
    CANDIDATE = "CANDIDATE"


class CandidateFamily(StrEnum):
    DUMMY = "dummy"
    LOGISTIC_REGRESSION = "logistic_regression"
    RANDOM_FOREST = "random_forest"


class LabelExclusionReason(StrEnum):
    MISSING_OUTCOME_SIGNAL = "MISSING_OUTCOME_SIGNAL"
    INSUFFICIENT_OUTCOME_QUALITY = "INSUFFICIENT_OUTCOME_QUALITY"
    NO_COMPATIBLE_PRIOR = "NO_COMPATIBLE_PRIOR"
    NO_COMPATIBLE_NEXT_PULL = "NO_COMPATIBLE_NEXT_PULL"
    CONFIGURATION_BOUNDARY = "CONFIGURATION_BOUNDARY"
    LABEL_NOT_APPLICABLE = "LABEL_NOT_APPLICABLE"
    FUTURE_DATA = "FUTURE_DATA"
    INCOMPATIBLE_SESSION = "INCOMPATIBLE_SESSION"


@dataclass(frozen=True)
class CandidateSpec:
    key: CandidateFamily
    parameters: dict[str, Any]
    complexity_rank: int

    def __post_init__(self) -> None:
        if self.complexity_rank < 0:
            raise ValueError("candidate complexity rank cannot be negative")
        object.__setattr__(self, "parameters", dict(self.parameters))

    def manifest(self) -> dict[str, Any]:
        return {
            "family": self.key.value,
            "parameters": self.parameters,
            "complexity_rank": self.complexity_rank,
        }


@dataclass(frozen=True)
class ModelSpec:
    task: MLTask
    version: str
    label_definition: LabelDefinition
    feature_set_version: str
    input_dataset_name: str
    outcome_dataset_name: str
    feature_keys: tuple[str, ...]
    outcome_feature_keys: tuple[str, ...]
    candidates: tuple[CandidateSpec, ...]
    primary_metric: str = "average_precision"
    minimum_rows: int = 100
    minimum_positive: int = 20
    minimum_negative: int = 20
    seed: int = 9142
    split_version: str = "chronological-session-groups-v1"
    threshold_grid: tuple[float, ...] = tuple(i / 20 for i in range(2, 17))
    selection_margin: float = 0.025
    minimum_f1: float = 0.70
    minimum_balanced_accuracy: float = 0.70
    minimum_average_precision_lift: float = 0.10
    maximum_feature_count: int = 32

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", self.version):
            raise ValueError("invalid model specification version")
        if self.label_definition.key != self.task.value:
            raise ValueError("model task and label definition differ")
        if self.label_definition.horizon.kind.value != "next_pull":
            raise ValueError("Phase 9B mandatory tasks require a next-pull label")
        if (
            not self.feature_set_version
            or not self.input_dataset_name
            or not self.outcome_dataset_name
        ):
            raise ValueError("model datasets and feature set version are required")
        if not self.feature_keys or len(self.feature_keys) > self.maximum_feature_count:
            raise ValueError("model feature count is outside its bounded range")
        if len(self.feature_keys) != len(set(self.feature_keys)):
            raise ValueError("model feature keys must be unique")
        if not set(self.outcome_feature_keys).issubset(self.label_definition.source_feature_keys):
            raise ValueError("outcome dataset features must be declared by the label")
        if set(self.feature_keys).intersection(self.label_definition.source_feature_keys):
            raise ValueError("model inputs overlap target outcome source features")
        families = [candidate.key for candidate in self.candidates]
        if len(families) != len(set(families)):
            raise ValueError("model candidate families must be unique")
        required = {
            CandidateFamily.DUMMY,
            CandidateFamily.LOGISTIC_REGRESSION,
            CandidateFamily.RANDOM_FOREST,
        }
        if not required.issubset(families):
            raise ValueError("each task requires dummy, linear and nonlinear candidates")
        if len(self.candidates) > 20:
            raise ValueError("candidate trial count exceeds the hard limit of 20")
        if self.minimum_rows < 1 or self.minimum_positive < 1 or self.minimum_negative < 1:
            raise ValueError("training data minimums must be positive")
        if self.seed < 0 or self.maximum_feature_count < 1:
            raise ValueError("invalid random seed or feature count")
        if not self.threshold_grid or any(not 0 < item < 1 for item in self.threshold_grid):
            raise ValueError("threshold candidates must lie strictly between zero and one")
        if any(
            not 0 <= value <= 1
            for value in (
                self.selection_margin,
                self.minimum_f1,
                self.minimum_balanced_accuracy,
                self.minimum_average_precision_lift,
            )
        ):
            raise ValueError("model acceptance thresholds must be in [0, 1]")

    @property
    def checksum(self) -> str:
        return stable_hash(self.manifest())

    def manifest(self) -> dict[str, Any]:
        return {
            "task": self.task.value,
            "version": self.version,
            "label_definition": self.label_definition.manifest(),
            "feature_set_version": self.feature_set_version,
            "input_dataset_name": self.input_dataset_name,
            "outcome_dataset_name": self.outcome_dataset_name,
            "feature_keys": list(self.feature_keys),
            "outcome_feature_keys": list(self.outcome_feature_keys),
            "candidates": [candidate.manifest() for candidate in self.candidates],
            "primary_metric": self.primary_metric,
            "minimum_rows": self.minimum_rows,
            "minimum_positive": self.minimum_positive,
            "minimum_negative": self.minimum_negative,
            "seed_policy": {
                "python_seed": self.seed,
                "numpy_seed": self.seed,
                "estimator_random_state": self.seed,
                "split_version": self.split_version,
            },
            "threshold_grid": list(self.threshold_grid),
            "selection_margin": self.selection_margin,
            "minimum_f1": self.minimum_f1,
            "minimum_balanced_accuracy": self.minimum_balanced_accuracy,
            "minimum_average_precision_lift": self.minimum_average_precision_lift,
            "maximum_feature_count": self.maximum_feature_count,
        }


@dataclass(frozen=True)
class SupervisedRow:
    row_id: str
    group_id: str
    vehicle_id: str
    configuration_id: str
    session_id: str
    input_pull_id: str
    target_pull_id: str
    input_started_at: datetime
    input_available_at: datetime
    target_started_at: datetime
    input_feature_set_id: str
    target_feature_set_id: str
    input_source_hash: str
    target_source_hash: str
    features: dict[str, float | None]
    missing: dict[str, str]
    feature_quality: dict[str, str]
    target: bool
    scenario_family: str | None = None
    quality_class: str = "high_quality"
    label_provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            self.input_started_at.tzinfo is None
            or self.input_available_at.tzinfo is None
            or self.target_started_at.tzinfo is None
        ):
            raise ValueError("supervised row timestamps must be timezone-aware")
        if self.input_available_at >= self.target_started_at:
            raise ValueError("input features must be available strictly before the target pull")
        if not self.features:
            raise ValueError("supervised row requires model input features")
        if set(self.features).intersection(
            {"vehicle_id", "configuration_id", "session_id", "pull_id", "target_pull_id"}
        ):
            raise ValueError("entity identity cannot be used as a model feature")


@dataclass(frozen=True)
class SupervisedDataset:
    task: MLTask
    model_spec: ModelSpec
    input_dataset_checksum: str
    outcome_dataset_checksum: str
    checksum: str
    source_fingerprint: str
    rows: tuple[SupervisedRow, ...]
    exclusions: tuple[dict[str, Any], ...]
    manifest: dict[str, Any]


@dataclass(frozen=True)
class TemporalSplit:
    train: tuple[SupervisedRow, ...]
    validation: tuple[SupervisedRow, ...]
    test: tuple[SupervisedRow, ...]
    cutoffs: dict[str, str]
    group_counts: dict[str, int]
    row_ids: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class MLModel:
    id: UUID
    task: MLTask
    description: str
    label_definition_id: UUID
    prediction_horizon: str
    intended_scope: str
    state: ModelState
    created_at: datetime


@dataclass(frozen=True)
class MLModelVersion:
    id: UUID
    model_id: UUID
    task: MLTask
    version: str
    algorithm: str
    hyperparameters: dict[str, Any]
    random_seed: int
    feature_set_version_id: UUID
    dataset_definition_id: UUID
    outcome_dataset_definition_id: UUID
    supervised_dataset_id: UUID
    label_definition_id: UUID
    dataset_checksum: str
    train_count: int
    validation_count: int
    test_count: int
    temporal_range: dict[str, str]
    metrics: dict[str, Any]
    input_schema: dict[str, Any]
    threshold: float
    artifact_path: str
    artifact_checksum: str
    repository_sha: str
    library_versions: dict[str, str]
    state: ModelState
    created_at: datetime


@dataclass(frozen=True)
class TrainingRun:
    id: UUID
    task: MLTask
    dataset_checksum: str
    candidate_models: tuple[dict[str, Any], ...]
    selected_model_version_id: UUID | None
    started_at: datetime
    finished_at: datetime
    seed: int
    state: ModelState
    metrics: dict[str, Any]
    artifact_checksum: str | None
    error_category: str | None
    trace_id: str | None
