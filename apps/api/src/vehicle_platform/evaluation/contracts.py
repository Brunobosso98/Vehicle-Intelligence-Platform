from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vehicle_platform.features.domain import stable_hash

EVALUATION_SCHEMA_VERSION = "phase9g-evaluation-v1"
PROTOCOL_VERSION = "phase9g-protocol-v1"


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class SourceRole(StrEnum):
    SYNTHETIC = "synthetic"
    IMPORTED_FIXTURE = "imported_fixture"
    IMPORTED = "imported"
    REAL_VEHICLE = "real_vehicle"


class CalibrationMethod(StrEnum):
    IDENTITY = "identity"
    SIGMOID = "sigmoid"
    ISOTONIC = "isotonic"


class MetricStatus(StrEnum):
    DEFINED = "DEFINED"
    UNDEFINED = "UNDEFINED"
    INSUFFICIENT_SUPPORT = "INSUFFICIENT_SUPPORT"
    NONINDEPENDENT_DESCRIPTIVE = "NONINDEPENDENT_DESCRIPTIVE"


class ApplicabilityStatus(StrEnum):
    SYNTHETIC_ONLY = "SYNTHETIC_ONLY"
    EVALUATION_INSUFFICIENT = "EVALUATION_INSUFFICIENT"
    REAL_DATA_UNLABELED = "REAL_DATA_UNLABELED"
    INCOMPATIBLE = "INCOMPATIBLE"
    OOD_WARNING = "OOD_WARNING"
    NO_REFERENCE = "NO_REFERENCE"
    NOT_CALIBRATED = "NOT_CALIBRATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class AllowedClaimCategory(StrEnum):
    SYNTHETIC_FIXTURE_METRIC = "SYNTHETIC_FIXTURE_METRIC"
    UNLABELED_DISTRIBUTION_METRIC = "UNLABELED_DISTRIBUTION_METRIC"
    MEASURED_SOURCE_COVERAGE = "MEASURED_SOURCE_COVERAGE"
    UNCALIBRATED_SCORE = "UNCALIBRATED_SCORE"
    SCIENTIFIC_LIMITATION = "SCIENTIFIC_LIMITATION"


class EvaluationState(StrEnum):
    VERIFIED_FIXTURE_EVALUATION = "VERIFIED_FIXTURE_EVALUATION"
    SUPPORT_INSUFFICIENT = "SUPPORT_INSUFFICIENT"
    UNLABELED_REAL_DATA = "UNLABELED_REAL_DATA"
    OUT_OF_DOMAIN = "OUT_OF_DOMAIN"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    SOURCE_ROLE_MISMATCH = "SOURCE_ROLE_MISMATCH"
    TEMPORAL_LEAKAGE_BLOCKED = "TEMPORAL_LEAKAGE_BLOCKED"
    ARTIFACT_INVALID = "ARTIFACT_INVALID"
    REFERENCE_INELIGIBLE = "REFERENCE_INELIGIBLE"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    NOT_CALIBRATED = "NOT_CALIBRATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    EVALUATOR_FAILED = "EVALUATOR_FAILED"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


class ConfidenceInterval(StrictContract):
    lower: float | None
    upper: float | None
    method: str
    unit: str
    cluster_count: int = Field(ge=0, le=100_000)
    resamples: int = Field(ge=0, le=10_000)
    status: MetricStatus

    @model_validator(mode="after")
    def ordered_bounds(self) -> ConfidenceInterval:
        if (self.lower is None) != (self.upper is None):
            raise ValueError("confidence bounds must both be defined or both be absent")
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("confidence interval lower bound exceeds upper bound")
        return self


class MetricDefinition(StrictContract):
    name: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=80)
    unit: str = Field(min_length=1, max_length=40)
    formula: str = Field(min_length=1, max_length=500)
    denominator_definition: str = Field(min_length=1, max_length=500)
    independence_unit: str | None = Field(default=None, max_length=40)


class MetricResult(StrictContract):
    definition: MetricDefinition
    value: float | None
    status: MetricStatus
    undefined_reason: str | None = Field(default=None, max_length=160)
    denominator: int = Field(ge=0, le=1_000_000)
    positive_support: int = Field(ge=0, le=1_000_000)
    negative_support: int = Field(ge=0, le=1_000_000)
    excluded_or_abstained: int = Field(ge=0, le=1_000_000)
    source_role: SourceRole
    fold_id: str = Field(min_length=1, max_length=80)
    uncertainty: ConfidenceInterval

    @model_validator(mode="after")
    def consistent_result(self) -> MetricResult:
        if self.positive_support + self.negative_support > self.denominator:
            raise ValueError("positive and negative support exceeds metric denominator")
        if self.value is None and self.status is MetricStatus.DEFINED:
            raise ValueError("defined metrics require a finite value")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("metric value must be finite")
        if self.value is None and not self.undefined_reason:
            raise ValueError("undefined metrics require a reason")
        return self


class ReliabilityBin(StrictContract):
    lower: float = Field(ge=0.0, le=1.0)
    upper: float = Field(ge=0.0, le=1.0)
    count: int = Field(ge=0, le=1_000_000)
    mean_score: float | None = Field(default=None, ge=0.0, le=1.0)
    observed_positive_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    weighted_absolute_error: float | None = Field(default=None, ge=0.0, le=1.0)
    rate_interval: ConfidenceInterval

    @model_validator(mode="after")
    def valid_bin(self) -> ReliabilityBin:
        if self.lower > self.upper:
            raise ValueError("reliability bin bounds are reversed")
        if self.count == 0 and any(
            item is not None
            for item in (self.mean_score, self.observed_positive_rate, self.weighted_absolute_error)
        ):
            raise ValueError("empty reliability bins cannot contain fabricated statistics")
        if self.count > 0 and any(
            item is None
            for item in (self.mean_score, self.observed_positive_rate, self.weighted_absolute_error)
        ):
            raise ValueError("nonempty reliability bins require measured statistics")
        return self


class CalibrationValidityScope(StrictContract):
    source_role: SourceRole
    task: str = Field(min_length=1, max_length=80)
    label_definition_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_version_id: str = Field(min_length=1, max_length=80)
    model_artifact_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_set_version: str = Field(min_length=1, max_length=80)
    vehicle_context_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    configuration_context_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    cutoff: datetime
    not_for_serving: bool = True

    @model_validator(mode="after")
    def aware_cutoff(self) -> CalibrationValidityScope:
        if self.cutoff.tzinfo is None:
            raise ValueError("calibration scope cutoff must be timezone-aware")
        if not self.not_for_serving:
            raise ValueError("Phase 9G calibration candidates are never serving artifacts")
        return self


class CalibrationCandidate(StrictContract):
    method: CalibrationMethod
    state: str = Field(pattern=r"^(ELIGIBLE|INSUFFICIENT_SUPPORT|SELECTED|REJECTED)$")
    task: str = Field(min_length=1, max_length=80)
    model_version_id: str = Field(min_length=1, max_length=80)
    input_score_semantics: str = Field(min_length=1, max_length=160)
    calibration_row_count: int = Field(ge=0, le=100_000)
    calibration_positive_count: int = Field(ge=0, le=100_000)
    calibration_negative_count: int = Field(ge=0, le=100_000)
    calibration_cluster_count: int = Field(ge=0, le=100_000)
    calibration_dataset_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_metrics: dict[str, Any] = Field(default_factory=dict)
    test_metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_checksum: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    artifact_bytes: int = Field(default=0, ge=0, le=65_536)
    validity_scope: CalibrationValidityScope
    not_for_serving: bool = True

    @model_validator(mode="after")
    def support_consistency(self) -> CalibrationCandidate:
        if (
            self.calibration_positive_count + self.calibration_negative_count
            > self.calibration_row_count
        ):
            raise ValueError("calibration class support exceeds calibration row count")
        if not self.not_for_serving:
            raise ValueError("calibration candidate cannot be marked for serving")
        if self.state in {"ELIGIBLE", "SELECTED"} and self.method is not CalibrationMethod.IDENTITY:
            if self.artifact_checksum is None or self.artifact_bytes <= 0:
                raise ValueError("fitted candidates require a checksummed research artifact")
        return self


class DatasetManifest(StrictContract):
    schema_version: str = EVALUATION_SCHEMA_VERSION
    source_role: SourceRole
    source_kind: str = Field(min_length=1, max_length=40)
    row_count: int = Field(ge=0, le=100_000)
    labeled_count: int = Field(ge=0, le=100_000)
    unlabeled_count: int = Field(ge=0, le=100_000)
    vehicle_count: int = Field(ge=0, le=10_000)
    configuration_count: int = Field(ge=0, le=50_000)
    session_count: int = Field(ge=0, le=100_000)
    feature_set_version: str = Field(min_length=1, max_length=80)
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    row_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    cutoff: datetime
    known_at_policy: str = Field(min_length=1, max_length=80)
    generator_version: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def counts_and_cutoff(self) -> DatasetManifest:
        if self.labeled_count + self.unlabeled_count != self.row_count:
            raise ValueError("labeled and unlabeled counts must conserve dataset rows")
        if self.cutoff.tzinfo is None:
            raise ValueError("dataset cutoff must be timezone-aware")
        return self


class FoldManifest(StrictContract):
    fold_id: str = Field(min_length=1, max_length=80)
    partition: str = Field(pattern=r"^(TRAIN|CALIBRATION|VALIDATION|TEST|WALK_FORWARD)$")
    row_count: int = Field(ge=0, le=100_000)
    positive_count: int = Field(ge=0, le=100_000)
    negative_count: int = Field(ge=0, le=100_000)
    session_count: int = Field(ge=0, le=100_000)
    vehicle_count: int = Field(ge=0, le=10_000)
    start_at: datetime | None = None
    end_at: datetime | None = None
    row_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    session_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    eligible: bool
    exclusions: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fold_valid(self) -> FoldManifest:
        if self.positive_count + self.negative_count > self.row_count:
            raise ValueError("fold class counts exceed row count")
        if self.start_at and self.start_at.tzinfo is None:
            raise ValueError("fold start must be timezone-aware")
        if self.end_at and self.end_at.tzinfo is None:
            raise ValueError("fold end must be timezone-aware")
        if self.start_at and self.end_at and self.start_at > self.end_at:
            raise ValueError("fold time window is reversed")
        return self


class StressScenario(StrictContract):
    scenario_id: str = Field(min_length=1, max_length=80)
    family: str = Field(min_length=1, max_length=40)
    oracle_kind: str = Field(min_length=1, max_length=80)
    oracle_positive_families: tuple[str, ...] = Field(max_length=4)
    expected_changes: tuple[str, ...] = Field(max_length=16)
    source_role: SourceRole
    generator_version: str = Field(min_length=1, max_length=80)
    metadata_excluded_from_features: bool = True


class DriftComparison(StrictContract):
    feature_family: str = Field(min_length=1, max_length=80)
    metric: str = Field(
        pattern=(
            r"^(PSI|KS|WASSERSTEIN|MEDIAN_SHIFT|IQR_RATIO|LABEL_PREVALENCE|"
            r"CONCEPT_CHANGE|CALIBRATION)$"
        )
    )
    baseline_window: str = Field(min_length=1, max_length=80)
    comparison_window: str = Field(min_length=1, max_length=80)
    value: float | None
    unit: str = Field(min_length=1, max_length=40)
    status: MetricStatus
    cutoff: datetime
    labeled_support: int = Field(ge=0, le=100_000)
    warning_threshold: float | None = None
    warning: bool
    interpretation: str = Field(min_length=1, max_length=240)

    @model_validator(mode="after")
    def finite_window(self) -> DriftComparison:
        if self.cutoff.tzinfo is None:
            raise ValueError("drift cutoff must be timezone-aware")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("drift statistic must be finite")
        if self.value is None and self.status is MetricStatus.DEFINED:
            raise ValueError("defined drift comparison needs a measured value")
        if (
            self.metric in {"LABEL_PREVALENCE", "CONCEPT_CHANGE", "CALIBRATION"}
            and self.labeled_support == 0
        ):
            raise ValueError("label-dependent drift cannot be defined without labels")
        return self


class ApplicabilityAssessment(StrictContract):
    subject_kind: str = Field(pattern=r"^(9B_TASK|9C_FAMILY|9D_RECEIPT|9E_EVIDENCE|9F_AGENT)$")
    subject_key: str = Field(min_length=1, max_length=80)
    subject_version: str = Field(min_length=1, max_length=80)
    source_role: SourceRole
    status: ApplicabilityStatus
    reason_codes: tuple[str, ...] = Field(min_length=1, max_length=12)
    required_signals: tuple[str, ...] = Field(max_length=32)
    observed_signal_count: int = Field(ge=0, le=32)
    required_signal_count: int = Field(ge=0, le=32)
    labeled_outcomes: int = Field(ge=0, le=100_000)
    evaluation_rows: int = Field(ge=0, le=100_000)
    operational_scope: str = Field(min_length=1, max_length=160)
    allowed_claims: tuple[AllowedClaimCategory, ...] = Field(min_length=1, max_length=8)
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calibration_available: bool
    diagnostic_claim_allowed: bool = False

    @model_validator(mode="after")
    def prohibit_diagnosis(self) -> ApplicabilityAssessment:
        if self.diagnostic_claim_allowed:
            raise ValueError("Phase 9G never permits diagnostic claims")
        if (
            self.source_role in {SourceRole.REAL_VEHICLE, SourceRole.IMPORTED}
            and self.labeled_outcomes == 0
        ):
            if self.status is not ApplicabilityStatus.REAL_DATA_UNLABELED:
                raise ValueError("unlabeled real/imported sources must remain explicitly unlabeled")
        return self


class EvaluationEvidenceRef(StrictContract):
    kind: str = Field(min_length=1, max_length=40)
    version: str = Field(min_length=1, max_length=80)
    entity_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_role: SourceRole
    known_at: datetime

    @model_validator(mode="after")
    def aware_known_at(self) -> EvaluationEvidenceRef:
        if self.known_at.tzinfo is None:
            raise ValueError("evidence known_at timestamp must be timezone-aware")
        return self


class EvaluationProtocol(StrictContract):
    schema_version: str = EVALUATION_SCHEMA_VERSION
    protocol_version: str = PROTOCOL_VERSION
    tasks: tuple[str, ...] = Field(min_length=3, max_length=3)
    anomaly_families: tuple[str, ...] = Field(min_length=4, max_length=4)
    split_policy: str = Field(min_length=1, max_length=80)
    calibration_fraction: float = Field(gt=0.0, lt=0.8)
    validation_fraction: float = Field(gt=0.0, lt=0.8)
    calibration_methods: tuple[CalibrationMethod, ...] = Field(min_length=3, max_length=3)
    calibration_minimum_rows: int = Field(ge=10, le=100_000)
    calibration_minimum_each_class: int = Field(ge=5, le=10_000)
    calibration_minimum_clusters: int = Field(ge=5, le=10_000)
    isotonic_minimum_rows: int = Field(ge=50, le=100_000)
    isotonic_minimum_each_class: int = Field(ge=20, le=10_000)
    isotonic_minimum_clusters: int = Field(ge=20, le=10_000)
    reliability_bins: int = Field(ge=2, le=10)
    bootstrap_resamples: int = Field(ge=0, le=10_000)
    seed: int = Field(ge=0, le=2**31 - 1)
    max_rows: int = Field(ge=1, le=100_000)
    max_artifact_bytes: int = Field(ge=1024, le=65_536)
    thresholds: tuple[float, ...] = Field(min_length=3, max_length=21)
    no_auto_promotion: bool = True
    no_real_failure_probability: bool = True

    @model_validator(mode="after")
    def fixed_contracts(self) -> EvaluationProtocol:
        if len(set(self.tasks)) != 3 or len(set(self.anomaly_families)) != 4:
            raise ValueError("protocol must include all unique 9B tasks and 9C families")
        if set(self.calibration_methods) != set(CalibrationMethod):
            raise ValueError("protocol must compare identity, sigmoid and isotonic")
        if any(not 0 < item < 1 for item in self.thresholds):
            raise ValueError("research thresholds must be strictly between zero and one")
        if self.calibration_fraction + self.validation_fraction >= 0.90:
            raise ValueError("evaluation protocol must reserve at least ten percent for test")
        if not self.no_auto_promotion or not self.no_real_failure_probability:
            raise ValueError("Phase 9G protocol must preserve the serving and science fences")
        return self

    @property
    def checksum(self) -> str:
        return stable_hash(self.model_dump(mode="json"))


class ScientificReadinessReport(StrictContract):
    engineering_pipeline: str = Field(pattern=r"^(PASS|FAIL)$")
    synthetic_calibration: str = Field(
        pattern=r"^(SYNTHETIC_ONLY|INSUFFICIENT_SUPPORT|NOT_ESTABLISHED)$"
    )
    real_world_predictive_validity: str = Field(pattern=r"^NOT_ESTABLISHED$")
    real_world_calibration: str = Field(pattern=r"^NOT_ESTABLISHED$")
    production_use: str = Field(pattern=r"^PROHIBITED$")
    failure_labels_available: bool = False
    unsupported_claims: tuple[str, ...] = Field(min_length=1, max_length=16)


class EvaluationRun(StrictContract):
    schema_version: str = EVALUATION_SCHEMA_VERSION
    protocol_version: str = PROTOCOL_VERSION
    protocol_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    logical_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_role: SourceRole
    dataset_manifest: DatasetManifest
    folds: tuple[FoldManifest, ...] = Field(min_length=4, max_length=32)
    evidence: tuple[EvaluationEvidenceRef, ...] = Field(min_length=1, max_length=128)
    metrics: tuple[MetricResult, ...] = Field(max_length=1_000)
    calibration_candidates: tuple[CalibrationCandidate, ...] = Field(max_length=128)
    applicability: tuple[ApplicabilityAssessment, ...] = Field(max_length=128)
    drift: tuple[DriftComparison, ...] = Field(max_length=256)
    stress_scenarios: tuple[StressScenario, ...] = Field(max_length=128)
    engineering_status: str = Field(pattern=r"^(PASS|FAIL)$")
    scientific_readiness: ScientificReadinessReport
    report_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    no_source_mutations: bool
    serving_artifacts_unchanged: bool
    not_for_serving: bool = True

    @model_validator(mode="after")
    def safety_invariants(self) -> EvaluationRun:
        if (
            not self.no_source_mutations
            or not self.serving_artifacts_unchanged
            or not self.not_for_serving
        ):
            raise ValueError("evaluation run violates source immutability or serving fence")
        if self.scientific_readiness.real_world_predictive_validity != "NOT_ESTABLISHED":
            raise ValueError("real-world predictive validity cannot be established in Phase 9G")
        return self


def protocol_fingerprint(protocol: EvaluationProtocol) -> str:
    return stable_hash(protocol.model_dump(mode="json"))
