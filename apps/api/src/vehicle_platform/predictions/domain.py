from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from vehicle_platform.anomalies.domain import SourceRole
from vehicle_platform.ml.domain import MLTask

PredictionKind = Literal["next_pull", "anomaly"]
AnomalyFamily = Literal["thermal", "boost_air", "performance", "fuel"]
AnomalyDecision = Literal["ANOMALOUS", "INLIER"]


class PredictionStatus(StrEnum):
    READY_SCORE = "READY_SCORE"
    ABSTAINED_INSUFFICIENT_SIGNAL = "ABSTAINED_INSUFFICIENT_SIGNAL"
    ABSTAINED_LOW_QUALITY = "ABSTAINED_LOW_QUALITY"
    ABSTAINED_INSUFFICIENT_REFERENCE = "ABSTAINED_INSUFFICIENT_REFERENCE"
    ABSTAINED_INCOMPATIBLE_CONTEXT = "ABSTAINED_INCOMPATIBLE_CONTEXT"
    ABSTAINED_UNSUPPORTED_SOURCE = "ABSTAINED_UNSUPPORTED_SOURCE"
    ABSTAINED_CUTOFF = "ABSTAINED_CUTOFF"


class ServingEventType(StrEnum):
    APPROVED = "APPROVED"
    ACTIVATED = "ACTIVATED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"
    ROLLED_BACK = "ROLLED_BACK"


class PredictionError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class PredictionRequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pull_id: UUID
    vehicle_id: UUID | None = None
    observation_cutoff: AwareDatetime
    source_role: SourceRole

    @field_validator("source_role")
    @classmethod
    def disallow_mixed_source(cls, value: SourceRole) -> SourceRole:
        if value is SourceRole.MIXED:
            raise ValueError("mixed source role cannot be served")
        return value


class NextPullRequest(PredictionRequestBase):
    task: MLTask
    model_version_id: UUID | None = None


class AnomalyRequest(PredictionRequestBase):
    family: AnomalyFamily
    detector_version_id: UUID | None = None


class PredictionQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quality_class: Literal["high", "degraded", "insufficient", "unavailable"]
    observed_feature_count: int = Field(ge=0, le=128)
    expected_feature_count: int = Field(ge=0, le=128)
    coverage: float = Field(ge=0, le=1)
    missing_reason_counts: dict[str, Annotated[int, Field(ge=0, le=128)]] = Field(
        default_factory=dict, max_length=16
    )


class PredictionLineage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_set_id: UUID | None = None
    anomaly_run_id: UUID | None = None
    anomaly_finding_id: UUID | None = None


class PredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase9d-prediction-response-v1"] = "phase9d-prediction-response-v1"
    result_type: PredictionKind
    task: MLTask | None = None
    family: AnomalyFamily | None = None
    horizon: Literal["NEXT_PULL", "AFTER_PULL_OFFLINE"]
    status: PredictionStatus
    reason_code: str | None = Field(default=None, max_length=80)
    receipt_id: UUID
    requested_cutoff: AwareDatetime
    effective_cutoff: AwareDatetime | None = None
    source_role: SourceRole
    model_version_id: UUID | None = None
    detector_version_id: UUID | None = None
    feature_set_version: str | None = Field(default=None, max_length=80)
    decision: bool | AnomalyDecision | None = None
    engineering_validation_score: float | None = Field(default=None, ge=0, le=1)
    anomaly_score: float | None = Field(default=None, ge=0)
    threshold: float | None = Field(default=None, ge=0)
    score_is_probability: Literal[False] = False
    interpretation: str = Field(min_length=1, max_length=240)
    limitation: str = Field(min_length=1, max_length=400)
    quality: PredictionQuality
    lineage: PredictionLineage


@dataclass(frozen=True)
class FeatureSnapshot:
    feature_set_id: UUID
    pull_id: UUID
    vehicle_id: UUID
    configuration_id: UUID | None
    session_id: UUID
    feature_set_version_id: UUID
    feature_set_version: str
    feature_set_version_checksum: str
    generated_at: datetime
    observation_cutoff: datetime
    source_window_end: datetime
    source_hash: str
    provenance_hash: str
    source_role: SourceRole
    source_type: str
    available_signals: tuple[str, ...]
    resolved_configuration_id: UUID | None
    values: dict[str, dict[str, object]]
    quality_metadata: dict[str, object]
    provenance: dict[str, object]
    pull_started_at: datetime
    pull_ended_at: datetime
    pull_created_at: datetime
    session_created_at: datetime
    vehicle_created_at: datetime
    configuration_created_at: datetime | None
    configuration_effective_at: datetime | None
    configuration_ended_at: datetime | None
    current_modification_ids: tuple[str, ...]


@dataclass(frozen=True)
class PullContext:
    pull_id: UUID
    vehicle_id: UUID
    session_id: UUID
    pull_configuration_id: UUID | None
    session_configuration_id: UUID | None
    pull_started_at: datetime
    pull_ended_at: datetime | None
    pull_created_at: datetime
    session_created_at: datetime
    vehicle_created_at: datetime
    session_status: str
    source_type: str
    source_role: SourceRole


@dataclass(frozen=True)
class ServingBinding:
    id: UUID
    result_kind: PredictionKind
    subject_key: str
    source_role: SourceRole
    environment: str
    scope: str
    model_version_id: UUID | None
    detector_version_id: UUID | None
    artifact_checksum: str
    feature_set_version: str
    feature_set_checksum: str
    schema_checksum: str
    reason: str
    operator_id: str
    review_reference: str
    latest_event_id: UUID
    latest_event_type: ServingEventType

    @property
    def is_active(self) -> bool:
        return self.latest_event_type in {
            ServingEventType.ACTIVATED,
            ServingEventType.ROLLED_BACK,
        }


@dataclass(frozen=True)
class ServingCandidate:
    result_kind: PredictionKind
    subject_key: str
    version_id: UUID
    source_role: SourceRole
    lifecycle_state: str
    artifact_checksum: str
    feature_set_version: str
    feature_set_checksum: str
    schema_checksum: str
    evaluation_class: str
    validation_status: str
    interpretation: str


@dataclass(frozen=True)
class FeatureSelection:
    requested_cutoff: datetime
    effective_cutoff: datetime
    snapshot: FeatureSnapshot
