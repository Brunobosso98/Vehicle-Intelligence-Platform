"""Public Phase 7B artifacts and explicit lifecycle rules.

These models contain product-visible evidence and decisions, never model reasoning.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from vehicle_platform.acquisition.domain import Support
from vehicle_platform.agents.schemas import StrictModel


class InvestigationStatus(StrEnum):
    DRAFT = "DRAFT"
    EVIDENCE_GAPS_IDENTIFIED = "EVIDENCE_GAPS_IDENTIFIED"
    CAPABILITIES_RESOLVED = "CAPABILITIES_RESOLVED"
    RECIPE_PROPOSED = "RECIPE_PROPOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    ACQUISITION_READY = "ACQUISITION_READY"
    AWAITING_DATA = "AWAITING_DATA"
    DATA_RECEIVED = "DATA_RECEIVED"
    REANALYZING = "REANALYZING"
    COMPLETED = "COMPLETED"
    INCONCLUSIVE = "INCONCLUSIVE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


TERMINAL = frozenset(
    {
        InvestigationStatus.COMPLETED,
        InvestigationStatus.INCONCLUSIVE,
        InvestigationStatus.REJECTED,
        InvestigationStatus.CANCELLED,
        InvestigationStatus.FAILED,
    }
)
TRANSITIONS: dict[InvestigationStatus, frozenset[InvestigationStatus]] = {
    InvestigationStatus.DRAFT: frozenset(
        {
            InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED,
            InvestigationStatus.CANCELLED,
            InvestigationStatus.FAILED,
        }
    ),
    InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED: frozenset(
        {
            InvestigationStatus.CAPABILITIES_RESOLVED,
            InvestigationStatus.INCONCLUSIVE,
            InvestigationStatus.CANCELLED,
            InvestigationStatus.FAILED,
        }
    ),
    InvestigationStatus.CAPABILITIES_RESOLVED: frozenset(
        {
            InvestigationStatus.RECIPE_PROPOSED,
            InvestigationStatus.INCONCLUSIVE,
            InvestigationStatus.CANCELLED,
            InvestigationStatus.FAILED,
        }
    ),
    InvestigationStatus.RECIPE_PROPOSED: frozenset(
        {
            InvestigationStatus.AWAITING_APPROVAL,
            InvestigationStatus.CANCELLED,
            InvestigationStatus.FAILED,
        }
    ),
    InvestigationStatus.AWAITING_APPROVAL: frozenset(
        {
            InvestigationStatus.APPROVED,
            InvestigationStatus.REJECTED,
            InvestigationStatus.CANCELLED,
            InvestigationStatus.FAILED,
        }
    ),
    InvestigationStatus.APPROVED: frozenset(
        {
            InvestigationStatus.ACQUISITION_READY,
            InvestigationStatus.AWAITING_APPROVAL,
            InvestigationStatus.CANCELLED,
            InvestigationStatus.FAILED,
        }
    ),
    InvestigationStatus.ACQUISITION_READY: frozenset(
        {
            InvestigationStatus.AWAITING_DATA,
            InvestigationStatus.AWAITING_APPROVAL,
            InvestigationStatus.CANCELLED,
            InvestigationStatus.FAILED,
        }
    ),
    InvestigationStatus.AWAITING_DATA: frozenset(
        {
            InvestigationStatus.DATA_RECEIVED,
            InvestigationStatus.CANCELLED,
            InvestigationStatus.FAILED,
        }
    ),
    InvestigationStatus.DATA_RECEIVED: frozenset(
        {InvestigationStatus.REANALYZING, InvestigationStatus.CANCELLED, InvestigationStatus.FAILED}
    ),
    InvestigationStatus.REANALYZING: frozenset(
        {
            InvestigationStatus.COMPLETED,
            InvestigationStatus.INCONCLUSIVE,
            InvestigationStatus.FAILED,
        }
    ),
    **{status: frozenset() for status in TERMINAL},
}


class HypothesisCategory(StrEnum):
    THERMAL = "THERMAL"
    AIRFLOW_BOOST = "AIRFLOW_BOOST"
    FUELING = "FUELING"
    THROTTLE_TORQUE_INTERVENTION = "THROTTLE_TORQUE_INTERVENTION"
    DATA_QUALITY = "DATA_QUALITY"
    CONFIGURATION_ASSOCIATION = "CONFIGURATION_ASSOCIATION"
    PERFORMANCE_VARIATION = "PERFORMANCE_VARIATION"
    UNKNOWN_OTHER = "UNKNOWN_OTHER"


class HypothesisStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    UNRESOLVED = "UNRESOLVED"
    NOT_TESTABLE_WITH_CURRENT_CAPABILITIES = "NOT_TESTABLE_WITH_CURRENT_CAPABILITIES"


class GapType(StrEnum):
    SIGNAL_OR_MEASUREMENT = "signal_or_measurement"
    COMPARABLE_HISTORY = "comparable_history"
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    DATA_QUALITY = "data_quality"
    CONFIGURATION_CONTEXT = "configuration_context"
    MECHANICAL_CAUSE = "mechanical_cause"


class GapStatus(StrEnum):
    OPEN = "OPEN"
    AVAILABLE_IN_EXISTING_DATA = "AVAILABLE_IN_EXISTING_DATA"
    NEEDS_NEW_CAPTURE = "NEEDS_NEW_CAPTURE"
    UNAVAILABLE_WITH_CURRENT_SOURCE = "UNAVAILABLE_WITH_CURRENT_SOURCE"
    RESOLVED = "RESOLVED"
    WAIVED = "WAIVED"


class SignalRole(StrEnum):
    ENGINE_SPEED = "engine_speed_context"
    VEHICLE_SPEED = "vehicle_speed_context"
    THROTTLE = "throttle_opening_behavior"
    BOOST = "boost_pressure_behavior"
    INTAKE_TEMPERATURE = "intake_temperature_behavior"
    COOLANT_TEMPERATURE = "coolant_temperature_context"
    OIL_TEMPERATURE = "oil_temperature_context"
    HIGH_FUEL_PRESSURE = "high_fuel_pressure_behavior"
    LOW_FUEL_PRESSURE = "low_fuel_pressure_behavior"
    LAMBDA = "lambda_behavior"
    TIMING = "timing_behavior"
    DATA_QUALITY = "timestamp_sequence_quality"


class Resolution(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    EVENT_CONTEXT = "EVENT_CONTEXT"


class Availability(StrEnum):
    AVAILABLE = "AVAILABLE"
    AVAILABLE_DEGRADED = "AVAILABLE_DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Feasibility(StrEnum):
    FEASIBLE = "FEASIBLE"
    FEASIBLE_WITH_DEGRADATION = "FEASIBLE_WITH_DEGRADATION"
    PARTIALLY_FEASIBLE = "PARTIALLY_FEASIBLE"
    NOT_FEASIBLE = "NOT_FEASIBLE"


class InvestigationError(ValueError):
    """A public investigation rule was violated."""


class Hypothesis(StrictModel):
    id: UUID
    category: HypothesisCategory
    statement: str = Field(min_length=8, max_length=300)
    discriminating_goal: str = Field(min_length=8, max_length=300)
    status: HypothesisStatus = HypothesisStatus.CANDIDATE
    support_level: str = Field(default="unknown", max_length=80)
    evidence_for: list[UUID] = Field(default_factory=list, max_length=8)
    evidence_against: list[UUID] = Field(default_factory=list, max_length=8)
    missing_gap_ids: list[UUID] = Field(default_factory=list, max_length=12)
    created_by: str = Field(default="agent", max_length=40)
    updated_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    limitations: list[str] = Field(default_factory=list, max_length=8)


class EvidenceGap(StrictModel):
    id: UUID
    category: GapType
    description: str = Field(min_length=8, max_length=300)
    why_it_matters: str = Field(min_length=8, max_length=300)
    hypothesis_ids: list[UUID] = Field(default_factory=list, max_length=5)
    required: bool = True
    signal_need_ids: list[UUID] = Field(default_factory=list, max_length=16)
    status: GapStatus = GapStatus.OPEN
    resolution_source: str | None = Field(default=None, max_length=160)


class SignalNeed(StrictModel):
    id: UUID
    role: SignalRole
    required: bool
    resolution: Resolution
    gap_ids: list[UUID] = Field(min_length=1, max_length=12)
    hypothesis_ids: list[UUID] = Field(default_factory=list, max_length=5)
    canonical_signal: str | None = Field(default=None, max_length=100)
    availability: Availability = Availability.UNKNOWN
    source_support: Availability = Availability.UNKNOWN
    recorded_in_session: bool | None = None
    provenance: str = Field(default="unresolved", max_length=160)
    unavailable_reason: str | None = Field(default=None, max_length=300)


class RecipeReference(StrictModel):
    key: str = Field(min_length=1, max_length=80)
    version: int = Field(ge=1)
    configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    minimum_duration_seconds: int = Field(ge=1, le=86400)
    vehicle_scope: str = Field(max_length=80)
    supported_modes: list[str] = Field(max_length=3)
    sampling_algorithm_version: str = Field(max_length=20)
    feasibility: Feasibility
    required_missing: list[str] = Field(default_factory=list, max_length=16)
    dropped_signals: list[str] = Field(default_factory=list, max_length=16)
    rate_compromises: list[str] = Field(default_factory=list, max_length=16)
    rationale: list[str] = Field(default_factory=list, max_length=16)
    source: str = Field(max_length=80)


class CapabilitySnapshot(StrictModel):
    adapter: str = Field(max_length=80)
    signals: dict[str, Support] = Field(max_length=100)
    maximum_requests_per_second: float = Field(ge=0, le=1000)
    observed_at: AwareDatetime
    source_acquisition_id: UUID | None = None
    source_preflight_id: UUID | None = None


class Approval(StrictModel):
    status: str = Field(default="PENDING", pattern="^(PENDING|APPROVED|REJECTED|INVALIDATED)$")
    recipe_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    approved_at: AwareDatetime | None = None
    actor: str | None = Field(default=None, max_length=100)


class InvestigationOutcome(StrictModel):
    conclusion: str = Field(max_length=2000)
    classification: str = Field(max_length=80)
    confidence: str = Field(pattern="^(low|moderate|high)$")
    evidence_summary: list[str] = Field(default_factory=list, max_length=16)
    resolved_gap_ids: list[UUID] = Field(default_factory=list, max_length=12)
    unresolved_gap_ids: list[UUID] = Field(default_factory=list, max_length=12)
    supported_hypothesis_ids: list[UUID] = Field(default_factory=list, max_length=5)
    weakened_hypothesis_ids: list[UUID] = Field(default_factory=list, max_length=5)
    limitations: list[str] = Field(default_factory=list, max_length=16)
    follow_up: str | None = Field(default=None, max_length=500)


class Transition(StrictModel):
    status: InvestigationStatus
    at: AwareDatetime


class InvestigationPlan(StrictModel):
    schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
    id: UUID
    agent_run_id: UUID
    vehicle_id: UUID
    question: str = Field(min_length=1, max_length=2000)
    goal: str = Field(min_length=8, max_length=500)
    status: InvestigationStatus = InvestigationStatus.DRAFT
    version: int = Field(default=1, ge=1, le=100)
    created_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    configuration_id: UUID | None = None
    source_session_id: UUID | None = None
    source_adapter: Literal["synthetic", "replay", "obd"] | None = None
    source_id: str = Field(default="", max_length=80)
    capability_snapshot: CapabilitySnapshot | None = None
    findings_summary: str = Field(default="", max_length=2000)
    hypotheses: list[Hypothesis] = Field(default_factory=list, max_length=5)
    gaps: list[EvidenceGap] = Field(default_factory=list, max_length=12)
    signal_needs: list[SignalNeed] = Field(default_factory=list, max_length=16)
    recipe: RecipeReference | None = None
    approval: Approval = Field(default_factory=Approval)
    linked_session_ids: list[UUID] = Field(default_factory=list, max_length=4)
    reanalysis_run_id: UUID | None = None
    outcome: InvestigationOutcome | None = None
    cycle_count: int = Field(default=0, ge=0, le=1)
    prompt_version: str = Field(default="investigation-v1", max_length=40)
    trace_id: str | None = Field(default=None, max_length=64)
    transitions: list[Transition] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def references_are_local(self) -> "InvestigationPlan":
        hypothesis_ids = {item.id for item in self.hypotheses}
        gap_ids = {item.id for item in self.gaps}
        need_ids = {item.id for item in self.signal_needs}
        if (
            len(hypothesis_ids) != len(self.hypotheses)
            or len(gap_ids) != len(self.gaps)
            or len(need_ids) != len(self.signal_needs)
        ):
            raise ValueError("duplicate investigation identifiers")
        for hypothesis in self.hypotheses:
            if not set(hypothesis.missing_gap_ids) <= gap_ids:
                raise ValueError("hypothesis references unknown gap")
        for gap in self.gaps:
            if (
                not set(gap.hypothesis_ids) <= hypothesis_ids
                or not set(gap.signal_need_ids) <= need_ids
            ):
                raise ValueError("gap references unknown investigation artifact")
        for need in self.signal_needs:
            if not set(need.gap_ids) <= gap_ids or not set(need.hypothesis_ids) <= hypothesis_ids:
                raise ValueError("signal need references unknown investigation artifact")
        if self.approval.status == "APPROVED" and (
            self.recipe is None or self.approval.recipe_hash != self.recipe.configuration_hash
        ):
            raise ValueError("approval must bind the current recipe hash")
        return self

    def move(self, status: InvestigationStatus) -> None:
        if status not in TRANSITIONS[self.status]:
            raise InvestigationError(f"invalid investigation transition: {self.status} to {status}")
        if status is InvestigationStatus.APPROVED and (
            self.recipe is None
            or self.approval.status != "APPROVED"
            or self.approval.recipe_hash != self.recipe.configuration_hash
            or self.recipe.feasibility
            not in {Feasibility.FEASIBLE, Feasibility.FEASIBLE_WITH_DEGRADATION}
        ):
            raise InvestigationError("approval requires the exact feasible recipe")
        if status is InvestigationStatus.AWAITING_APPROVAL and self.recipe is None:
            raise InvestigationError("approval requires a recipe")
        if status is InvestigationStatus.REANALYZING and not self.linked_session_ids:
            raise InvestigationError("reanalysis requires linked canonical data")
        self.status = status
        self.updated_at = datetime.now(UTC)
        self.transitions.append(Transition(status=status, at=self.updated_at))

    def replace_recipe(self, reference: RecipeReference | None) -> None:
        if self.recipe != reference:
            if self.status in {
                InvestigationStatus.AWAITING_DATA,
                InvestigationStatus.DATA_RECEIVED,
                InvestigationStatus.REANALYZING,
                *TERMINAL,
            }:
                raise InvestigationError("cannot replace recipe after acquisition linkage")
            self.recipe = reference
            self.approval = Approval(
                status="INVALIDATED" if self.approval.status == "APPROVED" else "PENDING"
            )
            if self.status in {
                InvestigationStatus.APPROVED,
                InvestigationStatus.ACQUISITION_READY,
            }:
                self.move(InvestigationStatus.AWAITING_APPROVAL)
            self.updated_at = datetime.now(UTC)


class InvestigationEvent(StrictModel):
    schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
    investigation_id: UUID
    sequence: int = Field(ge=1, le=100)
    type: str = Field(min_length=1, max_length=60)
    at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    status: InvestigationStatus
    detail: str | None = Field(default=None, max_length=300)
