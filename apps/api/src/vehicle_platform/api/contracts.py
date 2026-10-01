from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    status: Literal["ok"] = "ok"


class Ready(BaseModel):
    status: Literal["ready"] = "ready"
    database: Literal["ready"] = "ready"


class Version(BaseModel):
    application: str = "vehicle-intelligence-platform"
    version: str
    git_sha: str | None
    build_timestamp: datetime | None
    environment: Literal["development", "test", "production"]


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
