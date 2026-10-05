import asyncio
import json
from collections.abc import Awaitable, Callable
from functools import wraps
from time import perf_counter
from typing import ParamSpec
from uuid import uuid4

from mcp.types import CallToolResult, TextContent
from opentelemetry.trace import StatusCode
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from vehicle_platform.analytics.service import AnalyticsLimitError
from vehicle_platform.mcp.config import MCPSettings
from vehicle_platform.mcp.errors import ErrorCode, PlatformError, tool_error
from vehicle_platform.mcp.schemas import Envelope
from vehicle_platform.observability.telemetry import Telemetry

P = ParamSpec("P")


class Instrumentation:
    def __init__(self, telemetry: Telemetry, settings: MCPSettings) -> None:
        self.telemetry, self.settings = telemetry, settings
        self.active = 0
        meter = telemetry.metrics.get_meter("vehicle_platform.mcp")
        self.calls = meter.create_counter("mcp.tool.calls")
        self.errors = meter.create_counter("mcp.tool.errors")
        self.duration = meter.create_histogram("mcp.tool.duration", unit="s")
        self.active_metric = meter.create_up_down_counter("mcp.active.calls")
        self.items = meter.create_histogram("mcp.result.items")
        self.truncations = meter.create_counter("mcp.truncated.results")

    def wrap(self, function: Callable[P, Awaitable[Envelope]]) -> Callable[P, Awaitable[Envelope]]:
        @wraps(function)
        async def call(*args: P.args, **kwargs: P.kwargs) -> Envelope:
            request_id, started = uuid4(), perf_counter()
            labels = {"tool": function.__name__, "transport": self.settings.transport}
            code: ErrorCode | None = None
            response: Envelope | None = None
            admitted = self.active < self.settings.max_active_calls
            if admitted:
                self.active += 1
                self.active_metric.add(1)
            with self.telemetry.tracer.start_as_current_span(
                "mcp.tool",
                record_exception=False,
                set_status_on_exception=False,
                attributes={**labels, "mcp.request_id": str(request_id)},
            ) as span:
                try:
                    if not admitted:
                        raise PlatformError(ErrorCode.RATE_LIMITED)
                    async with asyncio.timeout(self.settings.execution_timeout):
                        response = await function(*args, **kwargs)
                        response.mcp_request_id = request_id
                        structured = response.model_dump(mode="json")
                        wire_result = CallToolResult(
                            content=[
                                TextContent(
                                    type="text", text=json.dumps(structured, separators=(",", ":"))
                                )
                            ],
                            structured_content=structured,
                        )
                        if len(
                            wire_result.model_dump_json().encode()
                        ) > self.settings.max_result_bytes - min(
                            1024, self.settings.max_result_bytes // 10
                        ):
                            raise PlatformError(ErrorCode.RESULT_TOO_LARGE)
                        return response
                except PlatformError as exc:
                    code = exc.code
                except LookupError:
                    code = ErrorCode.NOT_FOUND
                except AnalyticsLimitError:
                    code = ErrorCode.RESULT_TOO_LARGE
                except ValueError:
                    code = ErrorCode.INVALID_ARGUMENT
                except (SQLAlchemyError, OSError, TimeoutError):
                    code = ErrorCode.BACKEND_UNAVAILABLE
                except Exception:
                    code = ErrorCode.INTERNAL_ERROR
                finally:
                    if admitted:
                        self.active -= 1
                        self.active_metric.add(-1)
                    elapsed = perf_counter() - started
                    status = "error" if code else "success"
                    self.calls.add(1, {**labels, "status": status})
                    self.duration.record(elapsed, labels)
                    if code:
                        self.errors.add(1, {**labels, "code": code.value})
                        span.set_status(StatusCode.ERROR)
                        span.set_attribute("mcp.error_code", code.value)
                    if response:
                        self.items.record(response.returned, labels)
                        if response.truncated:
                            self.truncations.add(1, labels)
                    self.telemetry.log(
                        "mcp.call.completed",
                        str(request_id),
                        tool_name=function.__name__,
                        transport=self.settings.transport,
                        status=status,
                        duration_seconds=elapsed,
                        result_count=response.returned if response else 0,
                        truncated=response.truncated if response else False,
                        error_code=code.value if code else None,
                    )
                raise tool_error(code or ErrorCode.INTERNAL_ERROR, request_id)

        return call


class HTTPInstrumentation:
    """ASGI boundary preserving W3C trace context and counting SDK auth rejections."""

    def __init__(self, telemetry: Telemetry) -> None:
        self.telemetry = telemetry
        self.auth_failures = telemetry.metrics.get_meter("vehicle_platform.mcp").create_counter(
            "mcp.auth.failures"
        )

    async def dispatch(
        self, request: "Request", call_next: "RequestResponseEndpoint"
    ) -> "Response":
        from opentelemetry.propagate import extract

        with self.telemetry.tracer.start_as_current_span(
            "mcp.request",
            context=extract(dict(request.headers)),
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            response = await call_next(request)
            span.set_attribute("http.response.status_code", response.status_code)
            if response.status_code in {401, 403}:
                self.auth_failures.add(
                    1,
                    {
                        "reason": "http_unauthenticated"
                        if response.status_code == 401
                        else "http_forbidden"
                    },
                )
            return response
