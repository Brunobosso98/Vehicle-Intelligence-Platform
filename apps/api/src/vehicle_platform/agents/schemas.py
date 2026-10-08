from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


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


class RunAudit(StrictModel):
    run_id: UUID
    tool_calls: list[ToolCall] = Field(max_length=32)
    evidence: list[Evidence] = Field(max_length=100)


class StreamEvent(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
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
    ]
    data: dict[str, Any] = Field(default_factory=dict)
