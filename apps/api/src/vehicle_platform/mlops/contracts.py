from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vehicle_platform.evaluation.contracts import SourceRole
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.ml.domain import MLTask

SCHEMA_VERSION = "phase10-mlops-v1"
_HASH_PATTERN = r"^[0-9a-f]{64}$"
_SHA_PATTERN = r"^[0-9a-f]{40}$"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class PipelineKind(StrEnum):
    SUPERVISED = "supervised"
    ANOMALY = "anomaly"


class RunState(StrEnum):
    PLANNED = "PLANNED"
    QUEUED = "QUEUED"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    INSUFFICIENT_SUPPORT = "INSUFFICIENT_SUPPORT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"


class StepState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    SKIPPED_INELIGIBLE = "SKIPPED_INELIGIBLE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class GateState(StrEnum):
    PASS = "PASS"  # noqa: S105 -- gate status, not a credential
    FAIL = "FAIL"
    INSUFFICIENT_SUPPORT = "INSUFFICIENT_SUPPORT"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_EXECUTED = "NOT_EXECUTED"


class ProposalState(StrEnum):
    DRAFT = "DRAFT"
    EVALUATING = "EVALUATING"
    EVALUATED = "EVALUATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED_FOR_CONTROLLED_REVIEW = "APPROVED_FOR_CONTROLLED_REVIEW"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class DatasetBinding(Contract):
    schema_version: Literal["phase10-dataset-binding-v1"] = "phase10-dataset-binding-v1"
    source_role: SourceRole
    source_fingerprint: str = Field(pattern=_HASH_PATTERN)
    row_fingerprint: str = Field(pattern=_HASH_PATTERN)
    feature_set_version: str = Field(min_length=1, max_length=80)
    feature_checksum: str = Field(pattern=_HASH_PATTERN)
    label_checksum: str | None = Field(default=None, pattern=_HASH_PATTERN)
    row_count: int = Field(ge=0, le=20000)
    session_count: int = Field(ge=0, le=5000)
    cutoff: datetime

    @model_validator(mode="after")
    def validate_cutoff(self) -> DatasetBinding:
        offset = self.cutoff.utcoffset()
        if offset is None:
            raise ValueError("cutoff must have a UTC offset")
        if offset.total_seconds() != 0:
            raise ValueError("cutoff must be expressed in UTC")
        if self.session_count > self.row_count:
            raise ValueError("session count exceeds row count")
        return self


class PipelineRun(Contract):
    schema_version: Literal["phase10-run-state-v1"] = "phase10-run-state-v1"
    run_id: UUID
    definition_fingerprint: str = Field(pattern=_HASH_PATTERN)
    logical_fingerprint: str = Field(pattern=_HASH_PATTERN)
    attempt: int = Field(ge=1, le=100)
    source_role: SourceRole
    state: RunState
    fencing_token: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class PipelineStepRun(Contract):
    schema_version: Literal["phase10-step-state-v1"] = "phase10-step-state-v1"
    run_id: UUID
    step_name: Literal[
        "select", "validate", "fit", "verify_artifact", "evaluate", "compare", "report"
    ]
    attempt: int = Field(ge=1, le=100)
    source_role: SourceRole
    state: StepState
    input_checksum: str = Field(pattern=_HASH_PATTERN)
    output_checksum: str | None = Field(default=None, pattern=_HASH_PATTERN)


class ExperimentManifest(Contract):
    schema_version: Literal["phase10-experiment-v1"] = "phase10-experiment-v1"
    definition_fingerprint: str = Field(pattern=_HASH_PATTERN)
    repository_sha: str = Field(pattern=_SHA_PATTERN)
    source_role: SourceRole
    source_fingerprint: str = Field(pattern=_HASH_PATTERN)
    dataset_checksum: str = Field(pattern=_HASH_PATTERN)
    feature_checksum: str = Field(pattern=_HASH_PATTERN)
    label_checksum: str | None = Field(default=None, pattern=_HASH_PATTERN)
    cutoff: datetime
    seed: int = Field(ge=0, le=2**31 - 1)
    split_fingerprint: str = Field(pattern=_HASH_PATTERN)
    protocol_version: str = Field(min_length=1, max_length=80)
    library_versions: dict[str, str] = Field(max_length=32)


class ArtifactRef(Contract):
    schema_version: Literal["phase10-artifact-ref-v1"] = "phase10-artifact-ref-v1"
    artifact_kind: Literal["supervised_model", "anomaly_detector", "evaluation_report"]
    version_id: UUID
    checksum: str = Field(pattern=_HASH_PATTERN)
    size_bytes: int = Field(ge=1, le=50 * 1024 * 1024)
    source_role: SourceRole


class CandidateRef(Contract):
    schema_version: Literal["phase10-candidate-ref-v1"] = "phase10-candidate-ref-v1"
    candidate_kind: PipelineKind
    version_id: UUID
    artifact_checksum: str = Field(pattern=_HASH_PATTERN)
    evaluation_checksum: str = Field(pattern=_HASH_PATTERN)
    source_role: SourceRole
    task_or_family: str = Field(min_length=1, max_length=80)


class CandidateComparison(Contract):
    schema_version: Literal["phase10-candidate-comparison-v1"] = "phase10-candidate-comparison-v1"
    status: Literal["COMPARABLE_OFFLINE", "NOT_COMPARABLE"]
    source_role: SourceRole
    matched_cohort_checksum: str | None = Field(default=None, pattern=_HASH_PATTERN)
    champion_version_id: UUID | None = None
    challenger_version_id: UUID
    reason: str | None = Field(default=None, max_length=120)
    serving_action: Literal["NONE"] = "NONE"
    real_world_predictive_validity: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"


class CandidateDossier(Contract):
    schema_version: Literal["phase10-candidate-dossier-v1"]
    candidate_kind: PipelineKind
    candidate_version_id: UUID
    task_or_family: str = Field(min_length=1, max_length=80)
    horizon: Literal["next_pull"] | None
    source_role: Literal["synthetic"]
    dataset_lineage: dict[str, str | int | None]
    training_family: str | None
    holdout_status: str
    holdout_performance_and_uncertainty: dict[str, Any]
    cross_family_specificity: dict[str, Any] | None
    artifact_checksum: str = Field(pattern=_HASH_PATTERN)
    scientific_readiness: str | dict[str, Any]
    applicability_limits: tuple[str, ...] = Field(min_length=4, max_length=8)
    intended_environment: Literal["development", "test"]
    review_status: Literal["REVIEW_REQUIRED"]
    serving_approval: Literal["PENDING_SEPARATE_AUTHORIZED_PHASE_9D_ACTION"]
    serving_action: Literal["NONE"]
    real_world_predictive_validity: Literal["NOT_ESTABLISHED"]
    real_world_mechanical_failure_predictive_reliability: Literal["NOT_ESTABLISHED"]
    scientific_limitations: tuple[str, ...] = Field(min_length=4, max_length=8)


class MonitoringWindow(Contract):
    schema_version: Literal["phase10-monitoring-window-v1"] = "phase10-monitoring-window-v1"
    protocol_checksum: str = Field(pattern=_HASH_PATTERN)
    source_role: SourceRole
    start: datetime
    end: datetime
    receipts: int = Field(ge=0, le=10000)
    sessions: int = Field(ge=0, le=5000)
    scored: int = Field(ge=0, le=10000)
    abstained: int = Field(ge=0, le=10000)
    status: Literal["OBSERVED", "NO_OBSERVATIONS", "INSUFFICIENT_SUPPORT"]


class DriftFinding(Contract):
    schema_version: Literal["phase10-drift-finding-v1"] = "phase10-drift-finding-v1"
    drift_kind: Literal[
        "feature_source",
        "score_distribution",
        "missingness",
        "source_role",
        "label_prevalence",
        "performance",
        "calibration",
        "reference_cohort",
    ]
    status: Literal["WARNING", "NO_PREDECLARED_WARNING", "UNKNOWN", "INSUFFICIENT_SUPPORT"]
    baseline_checksum: str = Field(pattern=_HASH_PATTERN)
    comparison_checksum: str = Field(pattern=_HASH_PATTERN)
    value: float | None = None
    threshold: float | None = None
    real_world_predictive_validity: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"


class ReviewProposal(Contract):
    schema_version: Literal["phase10-proposal-v1"] = "phase10-proposal-v1"
    run_id: UUID
    definition_fingerprint: str = Field(pattern=_HASH_PATTERN)
    candidate_kind: PipelineKind
    candidate_version_id: UUID
    artifact_checksum: str = Field(pattern=_HASH_PATTERN)
    evaluation_checksum: str = Field(pattern=_HASH_PATTERN)
    comparison_checksum: str = Field(pattern=_HASH_PATTERN)
    comparison_status: Literal["COMPARABLE_OFFLINE", "NOT_COMPARABLE"]
    candidate_dossier: CandidateDossier
    candidate_dossier_checksum: str = Field(pattern=_HASH_PATTERN)
    source_role: Literal["synthetic"]
    scientific_readiness: str | dict[str, object]
    scientific_limitations: tuple[str, ...] = Field(min_length=4, max_length=8)
    status: Literal["REVIEW_REQUIRED"]
    serving_permission: Literal[False]
    serving_action: Literal["NONE"]
    real_world_predictive_validity: Literal["NOT_ESTABLISHED"]


class ReviewDecision(Contract):
    schema_version: Literal["phase10-review-decision-v1"] = "phase10-review-decision-v1"
    proposal_id: UUID
    proposal_checksum: str = Field(pattern=_HASH_PATTERN)
    decision: Literal["accept", "reject"]
    reviewer_id: str = Field(min_length=2, max_length=120)
    reviewer_role: Literal["mlops_reviewer"]
    reason: str = Field(min_length=20, max_length=500)
    environment: Literal["development", "test"]
    serving_action: Literal["NONE"]


class RollbackPlan(Contract):
    schema_version: Literal["phase10-rollback-plan-v1"] = "phase10-rollback-plan-v1"
    proposal_id: UUID
    proposal_checksum: str = Field(pattern=_HASH_PATTERN)
    target_binding_id: UUID
    target_event_id: UUID
    target_version_id: UUID
    target_artifact_checksum: str = Field(pattern=_HASH_PATTERN)
    expected_active_binding_id: UUID
    expected_active_event_id: UUID
    environment: Literal["development", "test"]
    state: Literal["READY_FOR_SEPARATE_9D_REVIEW", "BLOCKED"]
    serving_action: Literal["NONE"]
    real_world_predictive_validity: Literal["NOT_ESTABLISHED"]


class ReproductionReceipt(Contract):
    schema_version: Literal["phase10-reproduction-v1"] = "phase10-reproduction-v1"
    definition_fingerprint: str = Field(pattern=_HASH_PATTERN)
    source_fingerprint: str = Field(pattern=_HASH_PATTERN)
    expected_evaluation_checksum: str = Field(pattern=_HASH_PATTERN)
    reproduced_evaluation_checksum: str = Field(pattern=_HASH_PATTERN)
    expected_metrics_checksum: str = Field(pattern=_HASH_PATTERN)
    reproduced_metrics_checksum: str = Field(pattern=_HASH_PATTERN)
    status: Literal["REPRODUCED", "MISMATCH", "BLOCKED"]


class RunSummary(Contract):
    schema_version: Literal["phase10-run-summary-v1"] = "phase10-run-summary-v1"
    run_id: UUID
    definition_fingerprint: str = Field(pattern=_HASH_PATTERN)
    state: RunState
    completed_steps: int = Field(ge=0, le=7)
    failed_steps: int = Field(ge=0, le=7)
    artifact_checksum: str | None = Field(default=None, pattern=_HASH_PATTERN)
    proposal_id: UUID | None = None
    scientific_readiness: GateState
    serving_action: Literal["NONE"] = "NONE"
    real_world_predictive_validity: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"


class ResourceBudget(Contract):
    schema_version: Literal["phase10-budget-v1"] = "phase10-budget-v1"
    max_rows: int = Field(default=20000, ge=1, le=20000)
    max_sessions: int = Field(default=5000, ge=1, le=5000)
    max_features: int = Field(default=32, ge=1, le=32)
    max_candidates: int = Field(default=3, ge=1, le=3)
    max_artifact_bytes: int = Field(default=50 * 1024 * 1024, ge=1, le=50 * 1024 * 1024)
    max_bootstrap_resamples: Literal[200] = 200
    wall_seconds: int = Field(default=1800, ge=1, le=3600)
    memory_mib: int = Field(default=4096, ge=1024, le=8192)
    statement_timeout_seconds: int = Field(default=60, ge=1, le=120)


class AnomalyOracleLabel(Contract):
    """Explicit fixture oracle kept separate from every detector input feature."""

    pull_id: UUID
    scenario: Literal[
        "clean",
        "thermal",
        "boost_air",
        "performance",
        "fuel",
        "ambiguous",
        "quality_excluded",
        "unlabeled",
    ]


class PipelineDefinition(Contract):
    schema_version: Literal["phase10-definition-v2"] = "phase10-definition-v2"
    definition_version: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$")
    kind: PipelineKind
    task: MLTask | None = None
    family: Literal["thermal", "boost_air", "performance", "fuel"] | None = None
    method: Literal["robust_mad", "isolation_forest"] | None = None
    anchor_pull_id: UUID | None = None
    source_role: SourceRole
    cutoff: datetime
    protocol_version: Literal["phase9g-protocol-v2"] = "phase9g-protocol-v2"
    seed: Literal[9142] = 9142
    git_sha: str = Field(pattern=_SHA_PATTERN)
    expected_source_fingerprint: str = Field(pattern=_HASH_PATTERN)
    expected_dataset_checksum: str = Field(pattern=_HASH_PATTERN)
    expected_feature_checksum: str = Field(pattern=_HASH_PATTERN)
    evaluation_cutoff: datetime | None = None
    training_pull_ids: tuple[UUID, ...] = Field(default=(), max_length=20000)
    evaluation_pull_ids: tuple[UUID, ...] = Field(default=(), max_length=1000)
    expected_evaluation_checksum: str | None = Field(default=None, pattern=_HASH_PATTERN)
    expected_evaluation_source_fingerprint: str | None = Field(default=None, pattern=_HASH_PATTERN)
    evaluation_oracle: tuple[AnomalyOracleLabel, ...] = Field(default=(), max_length=1000)
    expected_oracle_checksum: str | None = Field(default=None, pattern=_HASH_PATTERN)
    budget: ResourceBudget = Field(default_factory=ResourceBudget)

    @model_validator(mode="after")
    def validate_definition(self) -> PipelineDefinition:
        offset = self.cutoff.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("cutoff must be expressed in UTC")
        if self.kind is PipelineKind.SUPERVISED:
            if (
                self.task is None
                or any(x is not None for x in (self.family, self.method, self.anchor_pull_id))
                or self.evaluation_oracle
                or self.expected_oracle_checksum is not None
            ):
                raise ValueError("supervised definitions require a task only")
            if (
                self.evaluation_cutoff is None
                or self.evaluation_cutoff.utcoffset() != timedelta(0)
                or self.evaluation_cutoff <= self.cutoff
                or not self.training_pull_ids
                or len(set(self.training_pull_ids)) != len(self.training_pull_ids)
                or tuple(sorted(self.training_pull_ids, key=str)) != self.training_pull_ids
                or not self.evaluation_pull_ids
                or len(set(self.evaluation_pull_ids)) != len(self.evaluation_pull_ids)
                or tuple(sorted(self.evaluation_pull_ids, key=str)) != self.evaluation_pull_ids
                or set(self.training_pull_ids).intersection(self.evaluation_pull_ids)
                or len(self.training_pull_ids) > self.budget.max_rows
                or self.expected_evaluation_checksum is None
                or self.expected_evaluation_source_fingerprint is None
            ):
                raise ValueError(
                    "supervised definitions require bounded, disjoint training and later "
                    "evaluation cohorts"
                )
        else:
            if (
                self.training_pull_ids
                or self.task is not None
                or any(x is None for x in (self.family, self.method, self.anchor_pull_id))
            ):
                raise ValueError("anomaly definitions require family, method and anchor")
            evaluation_fields = (
                self.evaluation_cutoff,
                self.expected_evaluation_checksum,
                self.expected_evaluation_source_fingerprint,
                self.expected_oracle_checksum,
            )
            if any(item is not None for item in evaluation_fields):
                if (
                    any(item is None for item in evaluation_fields)
                    or not self.evaluation_pull_ids
                    or len(self.evaluation_oracle) != len(self.evaluation_pull_ids)
                    or tuple(sorted(self.evaluation_pull_ids, key=str)) != self.evaluation_pull_ids
                    or tuple(sorted(self.evaluation_oracle, key=lambda item: str(item.pull_id)))
                    != self.evaluation_oracle
                    or tuple(item.pull_id for item in self.evaluation_oracle)
                    != self.evaluation_pull_ids
                    or self.evaluation_cutoff is None
                    or self.evaluation_cutoff.utcoffset() != timedelta(0)
                    or self.evaluation_cutoff <= self.cutoff
                ):
                    raise ValueError("anomaly evaluation requires a later frozen cohort and oracle")
                oracle_checksum = stable_hash(
                    [item.model_dump(mode="json") for item in self.evaluation_oracle]
                )
                if oracle_checksum != self.expected_oracle_checksum:
                    raise ValueError("anomaly oracle checksum does not match its labels")
            elif self.evaluation_pull_ids or self.evaluation_oracle:
                raise ValueError("anomaly evaluation cohort and oracle must be supplied together")
        return self

    @property
    def fingerprint(self) -> str:
        return stable_hash(self.model_dump(mode="json"))


class EvaluationGate(Contract):
    schema_version: Literal["phase10-gate-v1"] = "phase10-gate-v1"
    name: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,79}$")
    status: GateState
    numerator: int = Field(ge=0, le=100000)
    denominator: int = Field(ge=0, le=100000)
    reason: str = Field(min_length=1, max_length=240)
    policy_version: str = Field(min_length=1, max_length=80)
    evidence_checksum: str | None = Field(default=None, pattern=_HASH_PATTERN)

    @model_validator(mode="after")
    def valid_counts(self) -> EvaluationGate:
        if self.numerator > self.denominator:
            raise ValueError("gate numerator exceeds denominator")
        return self


def utc_now() -> datetime:
    return datetime.now(UTC)
