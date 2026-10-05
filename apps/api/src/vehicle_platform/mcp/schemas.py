from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Limit = Annotated[int, Field(ge=1, le=100)]
PullIDs = Annotated[list[UUID], Field(min_length=2, max_length=20)]
SessionIDs = Annotated[list[UUID], Field(min_length=2, max_length=10)]
Signals = Annotated[list[str], Field(min_length=1, max_length=8)]
Samples = Annotated[int, Field(ge=1, le=1000)]
Metric = Literal["boost", "iat", "coolant", "oil", "fuel", "speed", "throttle"]


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
