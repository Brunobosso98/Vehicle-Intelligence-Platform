from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypedDict

from vehicle_platform.agents.evidence import EvidenceRegistry
from vehicle_platform.agents.provider import ModelTurn
from vehicle_platform.agents.schemas import AgentRun, Answer, Ask, ToolCall, VehicleContext

EventSink = Callable[[str, dict[str, Any]], Awaitable[None]]
AuditSink = Callable[[ToolCall], Awaitable[None]]


@dataclass
class Execution:
    run: AgentRun
    ask: Ask
    registry: EvidenceRegistry
    emit: EventSink
    audit: AuditSink
    context: VehicleContext | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    cache: dict[str, dict[str, Any]] = field(default_factory=dict)
    turn: ModelTurn | None = None
    final: Answer | None = None
    steps: int = 0
    corrections: int = 0
    telemetry_calls: int = 0
    comparisons: int = 0
    correction: str | None = None


class GraphState(TypedDict):
    execution: Execution
