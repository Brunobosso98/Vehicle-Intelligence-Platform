import re
from time import perf_counter
from uuid import uuid4

from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from vehicle_platform.observability.telemetry import Telemetry


class CorrelationMiddleware:
    def __init__(self, app: ASGIApp, telemetry: Telemetry) -> None:
        self.app = app
        self.telemetry = telemetry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}
        supplied = headers.get("x-request-id", "")
        request_id = supplied if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", supplied) else str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = perf_counter()
        status = 500
        method = scope["method"]
        metric_method = (
            method
            if method
            in {"GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"}
            else "_OTHER"
        )
        # Only route templates enter metric labels, preventing unbounded cardinality.
        with self.telemetry.tracer.start_as_current_span(
            "HTTP request",
            context=extract(headers),
            kind=SpanKind.SERVER,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            span.set_attribute("request.id", request_id)
            span.set_attribute("http.request.method", scope["method"])

            async def correlated_send(message: Message) -> None:
                nonlocal status
                if message["type"] == "http.response.start":
                    status = message["status"]
                    message.setdefault("headers", []).extend(
                        [
                            (b"x-request-id", request_id.encode()),
                            (b"x-content-type-options", b"nosniff"),
                        ]
                    )
                await send(message)

            try:
                await self.app(scope, receive, correlated_send)
            finally:
                route = getattr(scope.get("route"), "path", "unmatched")
                attributes = {
                    "http.route": route,
                    "http.request.method": metric_method,
                    "http.response.status_code": status,
                }
                span.update_name(f"{scope['method']} {route}")
                span.set_attributes(attributes)
                self.telemetry.requests.add(1, attributes)
                self.telemetry.latency.record(perf_counter() - started, attributes)
                self.telemetry.log("request.completed", request_id)
