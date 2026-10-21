from __future__ import annotations

import asyncio
import hashlib
import hmac
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from time import monotonic

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from vehicle_platform.api.errors import response
from vehicle_platform.core.config import Settings
from vehicle_platform.observability.telemetry import Telemetry

PREDICTION_PREFIX = "/api/v1/prediction-service"


@dataclass
class PredictionBudgetState:
    peak_in_flight: int = 0


class PredictionRequestBudgetMiddleware:
    """Authenticate and bound prediction requests before FastAPI reads JSON or the DB."""

    def __init__(
        self,
        app: ASGIApp,
        settings: Settings,
        telemetry: Telemetry | None = None,
        state: PredictionBudgetState | None = None,
    ) -> None:
        self.app = app
        self.settings = settings
        self.telemetry = telemetry
        self.state = state or PredictionBudgetState()
        self.trusted_networks = tuple(
            ip_network(item, strict=False)
            for item in settings.prediction_trusted_networks.split(",")
        )
        self.in_flight = 0
        self.peak_in_flight = 0
        self.rate_capacity = settings.prediction_requests_per_minute
        self.rate = self.rate_capacity / 60.0
        self.tokens = float(self.rate_capacity)
        self.updated = monotonic()

    def _take_rate_token(self) -> bool:
        now = monotonic()
        self.tokens = min(
            self.rate_capacity, self.tokens + max(0.0, now - self.updated) * self.rate
        )
        self.updated = now
        if self.tokens < 1.0:
            return False
        self.tokens -= 1.0
        return True

    def _enabled(self) -> bool:
        return (
            self.settings.prediction_service_enabled
            and self.settings.environment in {"development", "test"}
            and self.settings.prediction_operator_token is not None
        )

    def _authorized(self, scope: Scope) -> bool:
        headers = [
            value for name, value in scope.get("headers", []) if name.lower() == b"authorization"
        ]
        if len(headers) != 1 or len(headers[0]) > 2048:
            return False
        try:
            scheme, token = headers[0].decode("ascii").split(" ", 1)
        except (UnicodeDecodeError, ValueError):
            return False
        if scheme.lower() != "bearer" or not 32 <= len(token) <= 1024 or " " in token:
            return False
        expected_token = self.settings.prediction_operator_token
        if expected_token is None:
            return False
        expected = hashlib.sha256(expected_token.get_secret_value().encode("utf-8")).digest()
        supplied = hashlib.sha256(token.encode("ascii")).digest()
        return hmac.compare_digest(expected, supplied)

    def _trusted_peer(self, scope: Scope) -> bool:
        client = scope.get("client")
        if not isinstance(client, (tuple, list)) or not client:
            return False
        try:
            address = ip_address(str(client[0]))
        except ValueError:
            return False
        return any(address in network for network in self.trusted_networks)

    async def _reject(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        status: int,
        code: str,
        message: str,
        *,
        retry_after: int | None = None,
    ) -> None:
        request = Request(scope)
        if self.telemetry is not None:
            self.telemetry.log(
                "prediction.request.rejected",
                getattr(request.state, "request_id", "unavailable"),
                error_code=code,
                prediction_endpoint="admission",
                prediction_status=str(status),
                prediction_reason=code.lower(),
            )
            if status in {401, 403, 408, 413, 429, 503, 504}:
                self.telemetry.prediction_budget_denials.add(1, {"reason": code.lower()})
        rejected = response(request, status, code, message)
        if status == 401:
            rejected.headers["WWW-Authenticate"] = "Bearer"
        if retry_after is not None:
            rejected.headers["Retry-After"] = str(retry_after)
        if self.telemetry is None:
            await rejected(scope, receive, send)
        else:
            with self.telemetry.tracer.start_as_current_span("prediction.request.denied") as span:
                span.set_attribute("prediction.reason", code.lower())
                await rejected(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path", "")).rstrip("/")
        if path != PREDICTION_PREFIX and not path.startswith(PREDICTION_PREFIX + "/"):
            await self.app(scope, receive, send)
            return
        if not self._enabled():
            await self._reject(
                scope,
                receive,
                send,
                503,
                "PREDICTION_SERVICE_DISABLED",
                "Prediction service is unavailable",
            )
            return
        if not self._trusted_peer(scope):
            await self._reject(
                scope,
                receive,
                send,
                403,
                "PREDICTION_NETWORK_DENIED",
                "Prediction service is restricted to configured private networks",
            )
            return
        if not self._authorized(scope):
            await self._reject(
                scope,
                receive,
                send,
                401,
                "PREDICTION_UNAUTHORIZED",
                "Valid operator bearer authorization is required",
            )
            return
        if not self._take_rate_token():
            await self._reject(
                scope,
                receive,
                send,
                429,
                "PREDICTION_RATE_LIMITED",
                "Prediction request budget exceeded",
                retry_after=2,
            )
            return
        if self.in_flight >= self.settings.prediction_max_concurrent_requests:
            await self._reject(
                scope,
                receive,
                send,
                429,
                "PREDICTION_BUSY",
                "Prediction service is busy",
                retry_after=1,
            )
            return
        self.in_flight += 1
        self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
        self.state.peak_in_flight = max(self.state.peak_in_flight, self.in_flight)
        endpoint = self._endpoint(scope)
        started = monotonic()
        if self.telemetry is not None:
            self.telemetry.prediction_in_flight.add(1, {"endpoint": endpoint})
        response_started = False

        async def bounded_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            async with asyncio.timeout(self.settings.prediction_request_timeout_seconds):
                if self.telemetry is None:
                    await self._forward(scope, receive, bounded_send)
                else:
                    with self.telemetry.tracer.start_as_current_span(
                        "prediction.request.admission"
                    ):
                        await self._forward(scope, receive, bounded_send)
        except TimeoutError:
            if not response_started:
                await self._reject(
                    scope,
                    receive,
                    send,
                    504,
                    "PREDICTION_REQUEST_TIMEOUT",
                    "Prediction request exceeded its time budget",
                )
        finally:
            self.in_flight -= 1
            if self.telemetry is not None:
                self.telemetry.prediction_in_flight.add(-1, {"endpoint": endpoint})
                self.telemetry.prediction_duration.record(
                    monotonic() - started, {"endpoint": endpoint}
                )

    @staticmethod
    def _endpoint(scope: Scope) -> str:
        path = str(scope.get("path", "")).rstrip("/")
        if path.endswith("/verify"):
            return "evidence_verify"
        if "/evidence" in path:
            return "evidence"
        if path.endswith("/next-pull"):
            return "next_pull"
        if path.endswith("/anomalies"):
            return "anomalies"
        if path.endswith("/versions"):
            return "versions"
        if "/runs/" in path:
            return "receipt"
        return "other"

    async def _forward(self, scope: Scope, receive: Receive, send: Send) -> None:

        method = str(scope.get("method", "GET")).upper()
        body = bytearray()
        if method == "POST":
            content_types = [
                value for name, value in scope.get("headers", []) if name.lower() == b"content-type"
            ]
            media_type = (
                content_types[0].split(b";", 1)[0].strip().lower()
                if len(content_types) == 1
                else b""
            )
            if media_type != b"application/json":
                await self._reject(
                    scope,
                    receive,
                    send,
                    415,
                    "PREDICTION_CONTENT_TYPE_REQUIRED",
                    "Prediction requests require application/json",
                )
                return
            lengths = [
                value
                for name, value in scope.get("headers", [])
                if name.lower() == b"content-length"
            ]
            if len(lengths) > 1:
                await self._reject(
                    scope,
                    receive,
                    send,
                    400,
                    "PREDICTION_INVALID_CONTENT_LENGTH",
                    "Invalid request length",
                )
                return
            if lengths:
                try:
                    declared_length = int(lengths[0])
                except ValueError:
                    await self._reject(
                        scope,
                        receive,
                        send,
                        400,
                        "PREDICTION_INVALID_CONTENT_LENGTH",
                        "Invalid request length",
                    )
                    return
                if declared_length < 0 or declared_length > self.settings.prediction_max_body_bytes:
                    await self._reject(
                        scope,
                        receive,
                        send,
                        413,
                        "PREDICTION_BODY_TOO_LARGE",
                        "Prediction request exceeds the body limit",
                    )
                    return

            try:
                async with asyncio.timeout(self.settings.prediction_body_timeout_seconds):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        chunk = message.get("body", b"")
                        if len(body) + len(chunk) > self.settings.prediction_max_body_bytes:
                            await self._reject(
                                scope,
                                receive,
                                send,
                                413,
                                "PREDICTION_BODY_TOO_LARGE",
                                "Prediction request exceeds the body limit",
                            )
                            return
                        body.extend(chunk)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                await self._reject(
                    scope,
                    receive,
                    send,
                    408,
                    "PREDICTION_BODY_TIMEOUT",
                    "Prediction request body was not completed in time",
                )
                return
        elif any(
            name.lower() == b"content-length" and value != b"0"
            for name, value in scope.get("headers", [])
        ):
            await self._reject(
                scope,
                receive,
                send,
                413,
                "PREDICTION_BODY_NOT_ALLOWED",
                "Prediction retrieval requests do not accept a body",
            )
            return

        delivered = False

        async def bounded_receive() -> Message:
            nonlocal delivered
            if method == "POST" and not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self._run_with_disconnect(scope, bounded_receive, send)

    async def _run_with_disconnect(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Cancel downstream work when the ASGI server reports a disconnected client."""
        messages: asyncio.Queue[Message] = asyncio.Queue(maxsize=1)
        disconnected = asyncio.Event()

        async def invoke_app() -> None:
            await self.app(scope, messages.get, send)

        app_task: asyncio.Task[None] = asyncio.create_task(invoke_app())

        async def pump_receive() -> None:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    disconnected.set()
                    app_task.cancel()
                    return
                await messages.put(message)

        receive_task = asyncio.create_task(pump_receive())
        try:
            try:
                await app_task
            except asyncio.CancelledError:
                if not disconnected.is_set():
                    raise
        finally:
            if not app_task.done():
                app_task.cancel()
            await asyncio.gather(app_task, return_exceptions=True)
            receive_task.cancel()
            await asyncio.gather(receive_task, return_exceptions=True)
