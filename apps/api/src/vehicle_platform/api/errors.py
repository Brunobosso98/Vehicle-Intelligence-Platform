from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from vehicle_platform.agents.provider import AgentError
from vehicle_platform.api.contracts import ErrorDetail, ErrorResponse
from vehicle_platform.infrastructure.database import DependencyUnavailable
from vehicle_platform.observability.telemetry import Telemetry


def response(request: Request, status: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unavailable")
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, request_id=request_id))
    return JSONResponse(status_code=status, content=body.model_dump())


def register_errors(app: FastAPI, telemetry: Telemetry) -> None:
    @app.exception_handler(AgentError)
    async def agent_error(request: Request, exc: AgentError) -> JSONResponse:
        telemetry.log(
            "agent.request.failed",
            getattr(request.state, "request_id", "unavailable"),
            error_code=exc.category,
            exception_type=type(exc.__context__).__name__ if exc.__context__ else "AgentError",
        )
        status = (
            404
            if exc.category in {"run_not_found", "vehicle_not_found"}
            else 429
            if "concurrency" in exc.category
            else 503
            if exc.category in {"agent_disabled", "database_unavailable"}
            else 422
        )
        return response(
            request, status, exc.category.upper(), "Agent request could not be processed"
        )

    @app.exception_handler(DependencyUnavailable)
    async def unavailable(request: Request, exc: DependencyUnavailable) -> JSONResponse:
        telemetry.readiness_failures.add(1)
        return response(request, 503, "DATABASE_UNAVAILABLE", "Service dependency unavailable")

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        return response(request, 422, "VALIDATION_ERROR", "Invalid request")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return response(request, exc.status_code, "HTTP_ERROR", "Request could not be processed")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        telemetry.log(
            "request.failed",
            getattr(request.state, "request_id", "unavailable"),
            exception_type=type(exc).__name__,
        )
        return response(request, 500, "INTERNAL_ERROR", "Unexpected server error")
