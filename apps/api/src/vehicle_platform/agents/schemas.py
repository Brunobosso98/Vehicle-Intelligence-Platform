from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class Classification(StrEnum):
    OBSERVATION = "OBSERVATION"
    ASSOCIATION = "ASSOCIATION"
    HYPOTHESIS = "HYPOTHESIS"
    SUPPORTED_CONCLUSION = "SUPPORTED_CONCLUSION"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class Ask(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: UUID | None = None
    previous_run_id: UUID | None = None


class Usage(StrictModel):
    input_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost: float | None = None
    pricing_version: str | None = None


class Fact(StrictModel):
    path: str = Field(max_length=300)
    value: str | float | int | bool | None
    unit: str | None = Field(default=None, max_length=80)


class Evidence(StrictModel):
    id: UUID
    run_id: UUID
    vehicle_id: UUID
    evidence_type: str
    source_tool: str
    tool_call_id: UUID
    source_fingerprint: str
    configuration_id: UUID | None = None
    session_id: UUID | None = None
    pull_id: UUID | None = None
    event_id: UUID | None = None
    analysis_run_id: UUID | None = None
    entity_id: UUID | None = None
    summary: str = Field(max_length=500)
    facts: list[Fact] = Field(default_factory=list, max_length=160)
    provenance: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list, max_length=32)
    truncated: bool = False


class Binding(StrictModel):
    evidence_id: UUID
    path: str = Field(max_length=300)
    value: str | float | int | bool | None
    unit: str | None = Field(default=None, max_length=80)


class Claim(StrictModel):
    classification: Classification
    template: Literal[
        "recorded_fact",
        "temporal_association",
        "insufficient_evidence",
        "thermal_hypothesis",
        "unsafe_operation_refused",
    ]
    bindings: list[Binding] = Field(max_length=8)
    evidence_ids: list[UUID] = Field(max_length=8)


class Draft(StrictModel):
    confidence: Literal["low", "moderate", "high"]
    claims: list[Claim] = Field(max_length=16)
    missing_evidence: list[
        Literal[
            "mechanical_cause",
            "signal_or_measurement",
            "comparable_history",
            "technical_documentation",
            "data_quality",
            "configuration_context",
        ]
    ] = Field(max_length=4)


class Finding(Claim):
    statement: str = Field(max_length=3000)


class VehicleContext(StrictModel):
    vehicle_id: UUID
    vehicle: dict[str, Any] = Field(default_factory=dict)
    active_configuration_id: UUID | None = None
    configurations: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    modifications: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    sessions: list[dict[str, Any]] = Field(default_factory=list, max_length=10)
    capabilities: dict[str, dict[str, Any]] = Field(default_factory=dict)
    as_of: AwareDatetime
    warnings: list[str] = Field(default_factory=list, max_length=32)


EvidenceGap = Literal[
    "mechanical_cause",
    "signal_or_measurement",
    "comparable_history",
    "technical_documentation",
    "data_quality",
    "configuration_context",
]


class Specialist(StrEnum):
    DATA_QUALITY = "data_quality"
    PERFORMANCE = "performance"
    THERMAL = "thermal"
    FUEL_AIR_BOOST = "fuel_air_boost"


class Intent(StrEnum):
    FACTUAL = "factual"
    PERFORMANCE = "performance"
    THERMAL = "thermal"
    FUEL_AIR_BOOST = "fuel_air_boost"
    REPEATED_DEGRADATION = "repeated_degradation"
    MULTI_MECHANISM = "multi_mechanism"
    CONFIGURATION = "configuration_comparison"
    DATA_QUALITY = "data_quality"
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    UNSAFE = "unsafe"


class SpecialistBudget(StrictModel):
    model_turns: int = Field(default=4, ge=1, le=6)
    mcp_calls: int = Field(default=6, ge=0, le=8)
    telemetry_windows: int = Field(default=0, ge=0, le=1)
    result_bytes: int = Field(default=16384, ge=1024, le=32768)
    evidence_items: int = Field(default=32, ge=1, le=50)
    timeout_seconds: float = Field(default=25, gt=0, le=45)


class SpecialistRequest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    specialist: Specialist
    supervisor_run_id: UUID
    vehicle_id: UUID
    context: VehicleContext
    question: str = Field(min_length=1, max_length=2000)
    scoped_objective: str = Field(min_length=1, max_length=500)
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=50)
    session_ids: list[UUID] = Field(default_factory=list, max_length=10)
    pull_ids: list[UUID] = Field(default_factory=list, max_length=20)
    allowed_tools: list[str] = Field(max_length=16)
    budget: SpecialistBudget
    deadline: AwareDatetime
    prompt_version: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def same_vehicle(self) -> "SpecialistRequest":
        if self.context.vehicle_id != self.vehicle_id:
            raise ValueError("specialist context must belong to its vehicle")
        known = {str(item["id"]) for item in self.context.sessions}
        if any(str(identifier) not in known for identifier in self.session_ids):
            raise ValueError("specialist session must be in resolved context")
        return self


class SpecialistFinding(Finding):
    finding_id: UUID
    specialist: Specialist
    strength: Literal["low", "moderate", "high"]
    limitations: list[str] = Field(default_factory=list, max_length=16)
    session_ids: list[UUID] = Field(default_factory=list, max_length=10)
    configuration_ids: list[UUID] = Field(default_factory=list, max_length=20)


class SpecialistResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    specialist: Specialist
    supervisor_run_id: UUID
    vehicle_id: UUID
    status: Literal["completed", "failed", "timed_out", "cancelled", "skipped"]
    prompt_version: str = Field(min_length=1, max_length=80)
    findings: list[SpecialistFinding] = Field(default_factory=list, max_length=8)
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=50)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list, max_length=4)
    data_quality_warnings: list[str] = Field(default_factory=list, max_length=32)
    blocks_interpretation: bool = False
    confidence: Literal["low", "moderate", "high"] = "low"
    model_turn_count: int = Field(default=0, ge=0, le=6)
    tool_call_count: int = Field(default=0, ge=0, le=8)
    telemetry_call_count: int = Field(default=0, ge=0, le=1)
    cache_hits: int = Field(default=0, ge=0, le=8)
    duration_seconds: float = Field(default=0, ge=0)
    error_category: str | None = Field(default=None, max_length=80)
    trace_id: str | None = Field(default=None, max_length=32)
    usage: Usage = Field(default_factory=Usage)
    budget: SpecialistBudget | None = None


class SupervisorLimits(StrictModel):
    specialists: int = Field(ge=1, le=3)
    concurrent_specialists: int = Field(ge=1, le=3)
    model_turns: int = Field(ge=2, le=32)
    mcp_calls: int = Field(ge=4, le=32)
    telemetry_windows: int = Field(ge=0, le=2)
    retries: int = Field(ge=0, le=2)
    timeout_seconds: float = Field(gt=0, le=180)
    evidence_items: int = Field(ge=4, le=100)
    input_bytes: int = Field(ge=4096, le=524288)
    tool_result_bytes: int = Field(ge=1024, le=262144)


class RoutingProposal(StrictModel):
    """Model chooses typed intent and candidates; application policy owns final dispatch."""

    intent: Intent
    specialists: list[Specialist] = Field(default_factory=list, max_length=3)
    usage: Usage = Field(default_factory=Usage)


class RoutingDecision(StrictModel):
    intent: Intent
    considered: list[Specialist] = Field(max_length=4)
    selected: list[Specialist] = Field(max_length=3)
    skipped: list[Specialist] = Field(max_length=4)
    data_quality_gate: bool
    hints: list[str] = Field(max_length=16)
    reason: str = Field(max_length=500)


class Conflict(StrictModel):
    conflict_id: UUID
    finding_ids: list[UUID] = Field(min_length=2, max_length=8)
    type: Literal["factual", "temporal_scope", "sufficiency", "competing_hypotheses"]
    severity: Literal["warning", "critical"]
    explanation: str = Field(max_length=500)
    resolvable_with_existing_evidence: bool
    requires_investigation: bool


class Sufficiency(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    PARTIALLY_SUFFICIENT = "PARTIALLY_SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    UNRELIABLE_DATA = "UNRELIABLE_DATA"


class SupervisorReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    prompt_version: Literal["supervisor-v1"] = "supervisor-v1"
    routing: RoutingDecision
    specialists: list[SpecialistResult] = Field(default_factory=list, max_length=4)
    conflicts: list[Conflict] = Field(default_factory=list, max_length=8)
    sufficiency: Sufficiency = Sufficiency.INSUFFICIENT
    investigation_recommended: bool = False
    investigation_id: UUID | None = None
    cache_hits: int = Field(default=0, ge=0)
    routing_seconds: float = Field(default=0, ge=0)
    routing_usage: Usage = Field(default_factory=Usage)
    synthesis_usage: Usage = Field(default_factory=Usage)
    evidence_consumers: dict[str, list[Specialist]] = Field(default_factory=dict, max_length=100)
    limits: SupervisorLimits | None = None
    configuration_hash: str | None = Field(default=None, min_length=64, max_length=64)
    model_turn_count: int = Field(default=0, ge=0, le=32)
    retry_count: int = Field(default=0, ge=0, le=2)


class SpecialistDraft(StrictModel):
    """Provider result before application grounding and public statement rendering."""

    specialist: Specialist
    supervisor_run_id: UUID
    vehicle_id: UUID
    draft: Draft


class Answer(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    answer: str = Field(max_length=48000)
    confidence: Literal["low", "moderate", "high"]
    findings: list[Finding] = Field(max_length=16)
    evidence: list[Evidence] = Field(max_length=100)
    uncertainties: list[str] = Field(max_length=32)
    limitations: list[str] = Field(max_length=32)
    missing_evidence: list[str] = Field(max_length=4)
    context: VehicleContext


class ToolCall(StrictModel):
    id: UUID
    run_id: UUID
    tool_name: str
    started_at: datetime
    completed_at: datetime | None = None
    status: Literal["running", "completed", "failed"] = "running"
    argument_hash: str
    evidence_ids: list[UUID] = Field(default_factory=list)
    returned: int = 0
    truncated: bool = False
    duration_seconds: float | None = None
    error_category: str | None = None
    mcp_request_id: UUID | None = None


class AgentRun(StrictModel):
    id: UUID
    vehicle_id: UUID
    user_question: str
    status: Literal["running", "completed", "failed", "cancelled"]
    provider: str
    model: str
    agent_version: str
    prompt_version: str
    started_at: datetime
    completed_at: datetime | None = None
    result: Answer | None = None
    evidence: list[Evidence] = Field(default_factory=list, max_length=100)
    usage: Usage = Field(default_factory=Usage)
    tool_call_count: int = 0
    duration_seconds: float | None = None
    error_category: str | None = None
    trace_id: str | None = None
    supervisor: SupervisorReport | None = None


class RunAudit(StrictModel):
    run_id: UUID
    tool_calls: list[ToolCall] = Field(max_length=32)
    evidence: list[Evidence] = Field(max_length=100)


class StreamEvent(StrictModel):
    schema_version: Literal["1.0", "1.1"] = "1.0"
    sequence: int = Field(ge=1)
    run_id: UUID
    type: Literal[
        "run_started",
        "context_resolved",
        "tool_started",
        "tool_completed",
        "evidence_added",
        "answer_chunk",
        "run_completed",
        "run_failed",
        "run_cancelled",
        "supervisor_started",
        "routing_completed",
        "specialist_started",
        "specialist_tool_started",
        "specialist_tool_completed",
        "specialist_completed",
        "specialist_failed",
        "conflict_detected",
        "sufficiency_evaluated",
        "investigation_proposed",
        "synthesis_started",
    ]
    data: dict[str, Any] = Field(default_factory=dict)
