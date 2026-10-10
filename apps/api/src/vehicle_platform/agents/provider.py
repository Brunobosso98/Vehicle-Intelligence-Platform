from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import Field

from vehicle_platform.agents.schemas import Draft, StrictModel, Usage

if TYPE_CHECKING:
    from vehicle_platform.agents.investigation.proposal import (
        InvestigationInput,
        InvestigationProposal,
    )


class AgentError(Exception):
    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


class ToolRequest(StrictModel):
    call_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=80)
    arguments: dict[str, Any]


@dataclass
class ModelTurn:
    tool_calls: list[ToolRequest] = field(default_factory=list)
    draft: Draft | None = None
    usage: Usage = field(default_factory=Usage)


@dataclass
class ModelInput:
    question: str
    tools: list[dict[str, Any]]
    context: dict[str, Any]
    evidence: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    correction: str | None = None


class Provider(Protocol):
    async def turn(self, request: ModelInput) -> ModelTurn: ...
    async def propose(self, request: "InvestigationInput") -> "InvestigationProposal": ...
    async def close(self) -> None: ...
