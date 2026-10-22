from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from vehicle_platform.anomalies.domain import SourceRole
from vehicle_platform.predictions.domain import AnomalyDecision, PredictionResponse

PREDICTION_EVIDENCE_SCHEMA = "phase9e-prediction-evidence-v1"
PREDICTION_EVIDENCE_PROJECTION = "phase9e-safe-projection-v1"
PREDICTION_EVIDENCE_VERIFIER = "phase9e-source-verifier-v1"
MAX_EVIDENCE_NODES = 32
MAX_EVIDENCE_EDGES = 64
MAX_EVIDENCE_FACTS = 48
MAX_EVIDENCE_GAPS = 16
MAX_EVIDENCE_CLAIMS = 8
MAX_EVIDENCE_JSON_BYTES = 65_536
MAX_FACT_JSON_BYTES = 4_096


class EvidenceResultKind(StrEnum):
    NEXT_PULL = "next_pull"
    ANOMALY = "anomaly"


class EvidenceHorizon(StrEnum):
    NEXT_PULL = "NEXT_PULL"
    AFTER_PULL_OFFLINE = "AFTER_PULL_OFFLINE"


class EvidenceCompleteness(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    ABSTAINED = "ABSTAINED"


class EvidenceIntegrity(StrEnum):
    VERIFIED = "VERIFIED"
    VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE = "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE"
    FAILED_SOURCE_MISMATCH = "FAILED_SOURCE_MISMATCH"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"
    UNSUPPORTED_SCHEMA = "UNSUPPORTED_SCHEMA"


class ArtifactAvailability(StrEnum):
    VERIFIED = "VERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNAVAILABLE = "UNAVAILABLE"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"


class SourceKind(StrEnum):
    PREDICTION_RECEIPT = "prediction_receipt"
    SERVING_BINDING = "serving_binding"
    APPROVAL_EVENT = "approval_event"
    FEATURE_SET = "feature_set"
    FEATURE_VERSION = "feature_version"
    MODEL_VERSION = "model_version"
    DETECTOR_VERSION = "detector_version"
    ANOMALY_RUN = "anomaly_run"
    ANOMALY_FINDING = "anomaly_finding"
    REFERENCE_DATASET = "reference_dataset"


class EvidenceNodeType(StrEnum):
    PREDICTION_RECEIPT = "PREDICTION_RECEIPT"
    SERVING_BINDING = "SERVING_BINDING"
    APPROVAL_EVENT = "APPROVAL_EVENT"
    FEATURE_SET = "FEATURE_SET"
    FEATURE_VERSION = "FEATURE_VERSION"
    MODEL_VERSION = "MODEL_VERSION"
    DETECTOR_VERSION = "DETECTOR_VERSION"
    ANOMALY_RUN = "ANOMALY_RUN"
    ANOMALY_FINDING = "ANOMALY_FINDING"
    REFERENCE_DATASET = "REFERENCE_DATASET"


class EvidenceEdgeType(StrEnum):
    DERIVED_FROM = "DERIVED_FROM"
    SCORED_WITH = "SCORED_WITH"
    SELECTED_BY = "SELECTED_BY"
    OBSERVED_IN = "OBSERVED_IN"
    SUPPORTED_BY = "SUPPORTED_BY"
    COMPARED_AGAINST = "COMPARED_AGAINST"
    MEASURED_AT = "MEASURED_AT"
    LIMITED_BY = "LIMITED_BY"


class EvidenceFactType(StrEnum):
    SOURCE_MEASUREMENT = "SOURCE_MEASUREMENT"
    COMPUTED_FEATURE = "COMPUTED_FEATURE"
    MODEL_OUTPUT = "MODEL_OUTPUT"
    STATISTICAL_REFERENCE = "STATISTICAL_REFERENCE"
    CONTEXT_DESCRIPTOR = "CONTEXT_DESCRIPTOR"
    QUALITY_INDICATOR = "QUALITY_INDICATOR"
    INTERPRETATION_LIMIT = "INTERPRETATION_LIMIT"


class FactQuality(StrEnum):
    VALID = "VALID"
    LIMITED = "LIMITED"
    MISSING = "MISSING"
    INVALID = "INVALID"
    NOT_CHECKABLE = "NOT_CHECKABLE"


class EvidenceGapCode(StrEnum):
    NO_FEATURE_SET = "NO_FEATURE_SET"
    INPUT_ABSTAINED = "INPUT_ABSTAINED"
    SIGNAL_UNAVAILABLE = "SIGNAL_UNAVAILABLE"
    FEATURE_NOT_YET_OBSERVED = "FEATURE_NOT_YET_OBSERVED"
    LOW_QUALITY = "LOW_QUALITY"
    REFERENCE_INSUFFICIENT = "REFERENCE_INSUFFICIENT"
    CONTEXT_INCOMPATIBLE = "CONTEXT_INCOMPATIBLE"
    UNKNOWN_CONFIG = "UNKNOWN_CONFIG"
    MODEL_ARTIFACT_UNAVAILABLE = "MODEL_ARTIFACT_UNAVAILABLE"
    PROVENANCE_MISMATCH = "PROVENANCE_MISMATCH"
    EVIDENCE_SOURCE_MISSING = "EVIDENCE_SOURCE_MISSING"
    SOURCE_SCHEMA_MISMATCH = "SOURCE_SCHEMA_MISMATCH"
    CUTOFF_MISMATCH = "CUTOFF_MISMATCH"
    UNSUPPORTED_SOURCE = "UNSUPPORTED_SOURCE"
    AMBIGUOUS_ASSOCIATION = "AMBIGUOUS_ASSOCIATION"
    INCOMPLETE_PROJECTION = "INCOMPLETE_PROJECTION"
    UNVERIFIED_SOURCE = "UNVERIFIED_SOURCE"


class ClaimCategory(StrEnum):
    MODEL_OUTPUT = "MODEL_OUTPUT"
    STATISTICAL_ASSOCIATION = "STATISTICAL_ASSOCIATION"
    SOURCE_QUALITY = "SOURCE_QUALITY"
    ABSTENTION = "ABSTENTION"


class ClaimTemplate(StrEnum):
    NEXT_PULL_RESULT = "NEXT_PULL_RESULT"
    ANOMALY_RESULT = "ANOMALY_RESULT"
    ABSTENTION = "ABSTENTION"
    FEATURE_ASSOCIATION = "FEATURE_ASSOCIATION"


class ClaimValidation(StrEnum):
    CONSISTENT = "CONSISTENT"
    CONTRADICTORY = "CONTRADICTORY"
    NOT_CHECKABLE = "NOT_CHECKABLE"


class SourceTrustRole(StrEnum):
    IMMUTABLE_SOURCE = "IMMUTABLE_SOURCE"
    VERSIONED_SOURCE = "VERSIONED_SOURCE"
    DERIVED_SNAPSHOT = "DERIVED_SNAPSHOT"


class ProjectionClass(StrEnum):
    OPERATOR_RESULT = "OPERATOR_RESULT"
    INTERNAL_LINEAGE = "INTERNAL_LINEAGE"
    INTERNAL_SOURCE = "INTERNAL_SOURCE"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EvidenceNode(StrictModel):
    node_id: str = Field(min_length=1, max_length=80)
    node_type: EvidenceNodeType
    source_kind: SourceKind
    source_entity_id: UUID
    source_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_schema_checksum: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    valid_from: AwareDatetime | None = None
    valid_through: AwareDatetime | None = None
    trust_role: SourceTrustRole
    projection_class: ProjectionClass

    @model_validator(mode="after")
    def validate_time_scope(self) -> EvidenceNode:
        if self.valid_from and self.valid_through and self.valid_from > self.valid_through:
            raise ValueError("evidence node time scope is inverted")
        return self


class EvidenceEdge(StrictModel):
    edge_id: str = Field(min_length=1, max_length=80)
    source_node_id: str = Field(min_length=1, max_length=80)
    target_node_id: str = Field(min_length=1, max_length=80)
    relation: EvidenceEdgeType

    @model_validator(mode="after")
    def reject_self_reference(self) -> EvidenceEdge:
        if self.source_node_id == self.target_node_id:
            raise ValueError("evidence edge cannot reference itself")
        return self


class EvidenceFact(StrictModel):
    fact_id: str = Field(min_length=1, max_length=80)
    key: str = Field(min_length=1, max_length=160)
    fact_type: EvidenceFactType
    value: Any = None
    unit: str | None = Field(default=None, max_length=48)
    source_node_id: str = Field(min_length=1, max_length=80)
    cutoff: AwareDatetime
    cutoff_eligible: bool
    quality: FactQuality
    missing_reason: str | None = Field(default=None, max_length=80)
    observed_at: AwareDatetime | None = None
    available_at: AwareDatetime | None = None
    source_window_start: AwareDatetime | None = None
    source_window_end: AwareDatetime | None = None
    ordinal: int = Field(default=0, ge=0, le=127)
    meaning: str = Field(min_length=1, max_length=240)

    @field_validator("value")
    @classmethod
    def finite_json_value(cls, value: Any) -> Any:
        _validate_json_value(value)
        return value

    @model_validator(mode="after")
    def validate_value_and_time(self) -> EvidenceFact:
        if self.value is None and self.quality not in {
            FactQuality.MISSING,
            FactQuality.INVALID,
            FactQuality.NOT_CHECKABLE,
        }:
            raise ValueError("null evidence facts require a missing or not-checkable quality")
        if self.value is not None and self.missing_reason is not None:
            raise ValueError("available evidence facts cannot carry a missing reason")
        if self.source_window_start and self.source_window_end:
            if self.source_window_start > self.source_window_end:
                raise ValueError("evidence fact source window is inverted")
        for value in (
            self.observed_at,
            self.available_at,
            self.source_window_end,
        ):
            if value is not None and value > self.cutoff:
                raise ValueError("evidence fact exceeds its historical cutoff")
        return self


class EvidenceGap(StrictModel):
    code: EvidenceGapCode
    source_node_id: str | None = Field(default=None, max_length=80)
    reason_code: str | None = Field(default=None, max_length=80)


class ClaimScope(StrictModel):
    result_type: EvidenceResultKind
    horizon: EvidenceHorizon
    source_role: SourceRole
    cutoff: AwareDatetime


class ClaimBinding(StrictModel):
    claim_id: str = Field(min_length=1, max_length=80)
    template: ClaimTemplate
    category: ClaimCategory
    fact_ids: list[str] = Field(min_length=1, max_length=8)
    expected_value: Any = None
    expected_unit: str | None = Field(default=None, max_length=48)
    cutoff: AwareDatetime
    scope: ClaimScope
    validation: ClaimValidation

    @field_validator("expected_value")
    @classmethod
    def finite_expected_value(cls, value: Any) -> Any:
        _validate_json_value(value)
        return value


class OriginalPrediction(StrictModel):
    status: str = Field(min_length=1, max_length=48)
    reason_code: str | None = Field(default=None, max_length=80)
    score: float | None = None
    threshold: float | None = None
    decision: bool | AnomalyDecision | None = None
    score_is_probability: Literal[False] = False

    @field_validator("score", "threshold")
    @classmethod
    def finite_scores(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("prediction values must be finite")
        return value


class EvidenceSourceSummary(StrictModel):
    source_role: SourceRole
    source_type: str | None = Field(default=None, max_length=24)
    quality_class: Literal["high", "degraded", "insufficient", "unavailable"]
    receipt_coverage: float = Field(ge=0, le=1)
    feature_coverage: float = Field(ge=0, le=1)
    observed_feature_count: int = Field(ge=0, le=128)
    expected_feature_count: int = Field(ge=0, le=128)
    missing_reason_counts: dict[str, int] = Field(default_factory=dict, max_length=16)
    available_signals: list[str] = Field(default_factory=list, max_length=32)
    invalid_observation_count: int | None = Field(default=None, ge=0, le=1_000_000)
    duplicate_timestamp_count: int | None = Field(default=None, ge=0, le=1_000_000)
    pull_completeness: float | None = Field(default=None, ge=0, le=1)
    feature_set_available: bool
    reference_row_count: int | None = Field(default=None, ge=0, le=10_000)
    reference_session_count: int | None = Field(default=None, ge=0, le=10_000)
    artifact_availability: ArtifactAvailability

    @field_validator("missing_reason_counts")
    @classmethod
    def bounded_missing_reasons(cls, value: dict[str, int]) -> dict[str, int]:
        if any(
            not key or len(key) > 80 or type(count) is not int or not 0 <= count <= 128
            for key, count in value.items()
        ):
            raise ValueError("missing reason counts must be bounded nonnegative integers")
        return value


class PredictionEvidenceBundle(StrictModel):
    schema_version: Literal["phase9e-prediction-evidence-v1"]
    projection_version: Literal["phase9e-safe-projection-v1"]
    verifier_policy_version: Literal["phase9e-source-verifier-v1"]
    evidence_id: UUID
    receipt_id: UUID
    receipt_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    logical_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    content_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    provenance_manifest_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    result_type: EvidenceResultKind
    horizon: EvidenceHorizon
    task: str | None = Field(default=None, max_length=80)
    family: str | None = Field(default=None, max_length=32)
    source_role: SourceRole
    requested_cutoff: AwareDatetime
    effective_cutoff: AwareDatetime
    completeness: EvidenceCompleteness
    integrity: EvidenceIntegrity
    prediction: OriginalPrediction
    source_summary: EvidenceSourceSummary
    root_node_id: Literal["receipt"] = "receipt"
    nodes: list[EvidenceNode] = Field(min_length=1, max_length=MAX_EVIDENCE_NODES)
    edges: list[EvidenceEdge] = Field(max_length=MAX_EVIDENCE_EDGES)
    facts: list[EvidenceFact] = Field(max_length=MAX_EVIDENCE_FACTS)
    gaps: list[EvidenceGap] = Field(max_length=MAX_EVIDENCE_GAPS)
    claims: list[ClaimBinding] = Field(max_length=MAX_EVIDENCE_CLAIMS)
    omitted_count: int = Field(default=0, ge=0, le=1_000_000)
    interpretation: str = Field(min_length=1, max_length=500)
    limitations: list[str] = Field(min_length=1, max_length=12)
    generated_at: AwareDatetime

    @field_validator("interpretation")
    @classmethod
    def reject_unapproved_claims(cls, value: str) -> str:
        text = value.casefold()
        disallowed = (
            "caused",
            "proves a defect",
            "confirmed fault",
            "failure probability",
            "safe to drive",
            "must replace",
            "urgent maintenance",
            "remaining useful life",
        )
        if any(fragment in text for fragment in disallowed):
            raise ValueError("interpretation contains an unapproved diagnostic statement")
        return value

    @model_validator(mode="after")
    def validate_graph_bindings(self) -> PredictionEvidenceBundle:
        node_ids = [item.node_id for item in self.nodes]
        fact_ids = [item.fact_id for item in self.facts]
        if len(node_ids) != len(set(node_ids)) or self.root_node_id not in node_ids:
            raise ValueError("evidence node identifiers must be unique and include the root")
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("evidence fact identifiers must be unique")
        nodes = set(node_ids)
        facts = set(fact_ids)
        if any(
            edge.source_node_id not in nodes or edge.target_node_id not in nodes
            for edge in self.edges
        ):
            raise ValueError("evidence edges must reference nodes in the same bundle")
        if any(fact.source_node_id not in nodes for fact in self.facts):
            raise ValueError("evidence facts must reference nodes in the same bundle")
        if any(
            gap.source_node_id is not None and gap.source_node_id not in nodes for gap in self.gaps
        ):
            raise ValueError("evidence gaps must reference nodes in the same bundle")
        if any(not set(claim.fact_ids).issubset(facts) for claim in self.claims):
            raise ValueError("claim bindings must reference facts in the same bundle")
        if self.result_type is EvidenceResultKind.NEXT_PULL:
            if self.horizon is not EvidenceHorizon.NEXT_PULL or self.task is None or self.family:
                raise ValueError("supervised evidence requires NEXT_PULL and a task only")
        elif (
            self.horizon is not EvidenceHorizon.AFTER_PULL_OFFLINE
            or self.family is None
            or self.task
        ):
            raise ValueError("anomaly evidence requires AFTER_PULL_OFFLINE and a family only")
        if self.requested_cutoff < self.effective_cutoff:
            raise ValueError("effective cutoff cannot be later than requested cutoff")
        return self


# The root contract is also exported under the domain name used in the specification.
PredictionEvidence = PredictionEvidenceBundle


class PredictionEvidenceProjection(StrictModel):
    schema_version: Literal["phase9e-safe-projection-v1"]
    evidence_id: UUID
    receipt_id: UUID
    result_type: EvidenceResultKind
    horizon: EvidenceHorizon
    task: str | None
    family: str | None
    source_role: SourceRole
    cutoff: AwareDatetime
    status: str
    reason_code: str | None
    score: float | None
    threshold: float | None
    decision: bool | AnomalyDecision | None
    score_is_probability: Literal[False] = False
    completeness: EvidenceCompleteness
    integrity: EvidenceIntegrity
    coverage: float = Field(ge=0, le=1)
    observed_feature_count: int = Field(ge=0, le=128)
    expected_feature_count: int = Field(ge=0, le=128)
    source_type: str | None = Field(default=None, max_length=24)
    missing_reason_counts: dict[str, int] = Field(default_factory=dict, max_length=16)
    available_signals: list[str] = Field(default_factory=list, max_length=32)
    invalid_observation_count: int | None = Field(default=None, ge=0, le=1_000_000)
    duplicate_timestamp_count: int | None = Field(default=None, ge=0, le=1_000_000)
    pull_completeness: float | None = Field(default=None, ge=0, le=1)
    artifact_availability: ArtifactAvailability
    facts: list[dict[str, Any]] = Field(max_length=MAX_EVIDENCE_FACTS)
    gaps: list[EvidenceGap] = Field(max_length=MAX_EVIDENCE_GAPS)
    claims: list[dict[str, Any]] = Field(max_length=MAX_EVIDENCE_CLAIMS)
    omitted_count: int = Field(ge=0, le=1_000_000)
    node_count: int = Field(ge=1, le=MAX_EVIDENCE_NODES)
    edge_count: int = Field(ge=0, le=MAX_EVIDENCE_EDGES)
    fact_count: int = Field(ge=0, le=MAX_EVIDENCE_FACTS)
    fingerprint: str = Field(min_length=12, max_length=36)
    interpretation: str = Field(min_length=1, max_length=500)
    limitations: list[str] = Field(min_length=1, max_length=12)


class EvidenceVerificationResult(StrictModel):
    schema_version: Literal["phase9e-verification-result-v1"]
    evidence_id: UUID
    receipt_id: UUID
    integrity: EvidenceIntegrity
    checked_at: AwareDatetime
    source_count: int = Field(ge=0, le=MAX_EVIDENCE_NODES)
    reason_codes: list[str] = Field(max_length=16)


@dataclass(frozen=True)
class SourceRecordSnapshot:
    kind: SourceKind
    entity_id: UUID
    checksum: str
    schema_checksum: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class EvidenceSourceSnapshot:
    receipt: SourceRecordSnapshot
    response: PredictionResponse
    records: dict[SourceKind, SourceRecordSnapshot]
    integrity: EvidenceIntegrity
    gaps: tuple[EvidenceGapCode, ...]
    artifact_availability: ArtifactAvailability


@dataclass(frozen=True)
class VerificationOutcome:
    integrity: EvidenceIntegrity
    reason_codes: tuple[str, ...]
    source_count: int


def _validate_json_value(value: Any, depth: int = 0) -> None:
    if depth > 8:
        raise ValueError("evidence JSON exceeds its nesting limit")
    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str) and len(value) > MAX_FACT_JSON_BYTES:
            raise ValueError("evidence string exceeds its size limit")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("evidence numbers must be finite")
        return
    if isinstance(value, list):
        if len(value) > 64:
            raise ValueError("evidence arrays exceed their item limit")
        for item in value:
            _validate_json_value(item, depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 32 or any(not isinstance(key, str) or len(key) > 160 for key in value):
            raise ValueError("evidence object exceeds its key limit")
        for item in value.values():
            _validate_json_value(item, depth + 1)
        return
    raise ValueError("evidence values must be bounded JSON values")
