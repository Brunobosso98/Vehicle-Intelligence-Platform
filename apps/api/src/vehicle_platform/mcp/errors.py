import json
from enum import StrEnum
from uuid import UUID

from mcp.server.mcpserver.exceptions import ToolError


class ErrorCode(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INCOMPATIBLE_CONTEXT = "INCOMPATIBLE_CONTEXT"
    RESULT_TOO_LARGE = "RESULT_TOO_LARGE"
    RATE_LIMITED = "RATE_LIMITED"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class PlatformError(Exception):
    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def tool_error(code: ErrorCode, request_id: UUID) -> ToolError:
    return ToolError(json.dumps({"code": code.value, "mcp_request_id": str(request_id)}))
