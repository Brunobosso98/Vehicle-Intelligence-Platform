import math
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from vehicle_platform.anomalies.domain import SourceRole
from vehicle_platform.prediction_evidence.domain import (
    ArtifactAvailability,
    EvidenceCompleteness,
    EvidenceHorizon,
    EvidenceIntegrity,
    EvidenceResultKind,
    FactQuality,
)

Limit = Annotated[int, Field(ge=1, le=100)]
PullIDs = Annotated[list[UUID], Field(min_length=2, max_length=20)]
SessionIDs = Annotated[list[UUID], Field(min_length=2, max_length=10)]
Signals = Annotated[list[str], Field(min_length=1, max_length=8)]
Samples = Annotated[int, Field(ge=1, le=1000)]
Metric = Literal["boost", "iat", "coolant", "oil", "fuel", "speed", "throttle"]
Scalar = str | int | float | bool | None


class Window(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def bounded(self) -> "Window":
        if self.start.utcoffset() is None or self.end.utcoffset() is None:
            raise ValueError("timezone required")
        if not 0 < (self.end - self.start).total_seconds() <= 60:
            raise ValueError("window must be positive and at most 60 seconds")
        return self


class Warning(BaseModel):
    code: str
    details: dict[str, Any] = Field(default_factory=dict)


class Envelope(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    data: dict[str, Any] | list[dict[str, Any]]
    context: dict[str, UUID | list[UUID] | None] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    truncated: bool = False
    returned: int = 1
    warnings: list[Warning] = Field(default_factory=list)
    mcp_request_id: UUID | None = None


class PredictionEvidenceFact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)
    key: str = Field(min_length=1, max_length=160)
    fact_type: Literal["SOURCE_MEASUREMENT", "COMPUTED_FEATURE", "QUALITY_INDICATOR"]
    value: Scalar
    unit: str | None = Field(default=None, max_length=48)
    quality: FactQuality
    cutoff: AwareDatetime
    observed_at: AwareDatetime | None = None
    available_at: AwareDatetime | None = None


class PredictionEvidenceMCPProjection(BaseModel):
    """Private MCP response; the agent removes source identifiers before provider input."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)
    schema_version: Literal["prediction-agent-summary-v1"]
    evidence_id: UUID
    receipt_id: UUID
    source_vehicle_id: UUID
    source_session_id: UUID
    source_pull_id: UUID
    source_configuration_id: UUID | None
    source_feature_set_id: UUID | None
    result_type: EvidenceResultKind
    horizon: EvidenceHorizon
    task: str | None = Field(default=None, max_length=80)
    family: str | None = Field(default=None, max_length=32)
    source_role: SourceRole
    requested_cutoff: AwareDatetime
    effective_cutoff: AwareDatetime
    status: str = Field(min_length=1, max_length=48)
    reason_code: str | None = Field(default=None, max_length=80)
    model_version: str | None = Field(default=None, max_length=80)
    model_algorithm: str | None = Field(default=None, max_length=80)
    detector_version: str | None = Field(default=None, max_length=80)
    detector_algorithm_version: str | None = Field(default=None, max_length=80)
    detector_method: str | None = Field(default=None, max_length=32)
    decision: bool | str | None = None
    score: float | None = None
    threshold: float | None = None
    score_is_probability: Literal[False] = False
    completeness: EvidenceCompleteness
    integrity: EvidenceIntegrity
    verification_reasons: list[str] = Field(max_length=16)
    quality_class: Literal["high", "degraded", "insufficient", "unavailable"]
    coverage: float = Field(ge=0, le=1)
    feature_coverage: float = Field(ge=0, le=1)
    observed_feature_count: int = Field(ge=0, le=128)
    expected_feature_count: int = Field(ge=0, le=128)
    source_type: str | None = Field(default=None, max_length=24)
    missing_reason_counts: dict[str, int] = Field(default_factory=dict, max_length=16)
    available_signals: list[str] = Field(default_factory=list, max_length=32)
    invalid_observation_count: int | None = Field(default=None, ge=0, le=1_000_000)
    duplicate_timestamp_count: int | None = Field(default=None, ge=0, le=1_000_000)
    pull_completeness: float | None = Field(default=None, ge=0, le=1)
    artifact_availability: ArtifactAvailability
    reference_row_count: int | None = Field(default=None, ge=0, le=10_000)
    reference_session_count: int | None = Field(default=None, ge=0, le=10_000)
    facts: list[PredictionEvidenceFact] = Field(max_length=32)
    gaps: list[str] = Field(max_length=16)
    omitted_count: int = Field(ge=0, le=1_000_000)

    @model_validator(mode="after")
    def state_and_values_are_consistent(self) -> "PredictionEvidenceMCPProjection":
        numeric_values = (
            self.score,
            self.threshold,
            self.coverage,
            self.feature_coverage,
            self.pull_completeness,
        )
        if any(value is not None and not math.isfinite(value) for value in numeric_values) or any(
            isinstance(item.value, float) and not math.isfinite(item.value) for item in self.facts
        ):
            raise ValueError("prediction projection contains a non-finite value")
        if (
            (
                self.integrity is EvidenceIntegrity.VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE
                and self.artifact_availability is not ArtifactAvailability.UNAVAILABLE
            )
            or (
                self.integrity is EvidenceIntegrity.VERIFIED
                and self.artifact_availability
                not in {ArtifactAvailability.VERIFIED, ArtifactAvailability.NOT_APPLICABLE}
            )
            or (
                self.artifact_availability is ArtifactAvailability.CHECKSUM_MISMATCH
                and self.integrity is not EvidenceIntegrity.FAILED_SOURCE_MISMATCH
            )
        ):
            raise ValueError("prediction artifact and integrity states disagree")
        return self
