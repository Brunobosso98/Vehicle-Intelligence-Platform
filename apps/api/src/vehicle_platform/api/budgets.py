"""Constant-memory local request budgets for the Phase 4 resource boundaries."""

import asyncio
import math
from collections.abc import Callable
from time import monotonic

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from vehicle_platform.api.errors import response


class TokenBucket:
    def __init__(self, capacity: int, rate: float, clock: Callable[[], float] = monotonic) -> None:
        if capacity < 1 or not math.isfinite(rate) or rate <= 0:
            raise ValueError("request budget requires positive finite bounds")
        self.capacity, self.rate, self.clock = capacity, rate, clock
        self.tokens = float(capacity)
        self.updated = clock()

    def take(self) -> bool:
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + max(0, now - self.updated) * self.rate)
        self.updated = now
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True


class ResourceBudgetMiddleware:
    """Per-process budgets, with no unbounded per-client identifier dictionaries.

    The event-loop counters are reserved without an await and released even on
    disconnect/cancellation. They are local engineering bounds, not account quotas.
    """

    def __init__(
        self,
        app: ASGIApp,
        live_limit: int = 10,
        request_limit: int = 64,
        analysis_limit: int = 4,
    ) -> None:
        if min(live_limit, request_limit, analysis_limit) < 1:
            raise ValueError("concurrency budgets must be positive")
        self.app = app
        self.live_limit, self.request_limit, self.analysis_limit = (
            live_limit,
            request_limit,
            analysis_limit,
        )
        self.live = self.requests = self.analyses = 0
        self.acquisition_rate = TokenBucket(100, 100)
        self.creation_rate = TokenBucket(10, 10 / 60)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "").rstrip("/")
        acquisition = path.startswith("/api/v1/acquisitions")
        analysis = scope.get("method") == "POST" and (
            "/analytics" in path
            or "/trends/" in path
            or path.endswith(("/analysis", "/event-analysis", "/finalize"))
        )
        if scope["type"] != "http" or not (acquisition or analysis):
            await self.app(scope, receive, send)
            return
        live = acquisition and path.endswith("/live") and scope["method"] == "GET"
        creation = path == "/api/v1/acquisitions" and scope["method"] == "POST"
        denied = (
            self.requests >= self.request_limit
            or (live and self.live >= self.live_limit)
            or (analysis and self.analyses >= self.analysis_limit)
            or (acquisition and not self.acquisition_rate.take())
            or (creation and not self.creation_rate.take())
        )
        if denied:
            rejected = response(
                Request(scope),
                429,
                "RESOURCE_BUDGET_EXCEEDED",
                "Retry after the local request budget becomes available",
            )
            rejected.headers["Retry-After"] = "6" if creation else "1"
            await rejected(scope, receive, send)
            return
        self.requests += 1
        self.live += int(live)
        self.analyses += int(analysis)
        try:
            await self.app(scope, receive, send)
        finally:
            self.requests -= 1
            self.live -= int(live)
            self.analyses -= int(analysis)


class AgentRequestBudgetMiddleware:
    """Bound admission and body buffering before FastAPI parses an agent question."""

    def __init__(
        self,
        app: ASGIApp,
        request_limit: int = 64,
        body_limit: int = 32768,
        body_timeout: float = 5,
    ) -> None:
        if min(request_limit, body_limit, body_timeout) <= 0:
            raise ValueError("agent request budgets must be positive")
        self.app = app
        self.request_limit, self.body_limit, self.body_timeout = (
            request_limit,
            body_limit,
            body_timeout,
        )
        self.requests = 0
        self.creation_rate = TokenBucket(20, 20 / 60)
        self.read_rate = TokenBucket(200, 100)

    async def reject(self, scope: Scope, receive: Receive, send: Send, status: int) -> None:
        rejected = response(
            Request(scope), status, "AGENT_REQUEST_BUDGET_EXCEEDED", "Agent request budget exceeded"
        )
        if status == 429:
            rejected.headers["Retry-After"] = "3"
        await rejected(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "").rstrip("/")
        if (
            scope["type"] != "http"
            or not path.startswith("/api/v1/vehicles/")
            or "/agent-runs" not in path
        ):
            await self.app(scope, receive, send)
            return
        creation = scope.get("method") == "POST" and path.endswith("/agent-runs")
        rate = self.creation_rate if creation else self.read_rate
        if self.requests >= self.request_limit or not rate.take():
            await self.reject(scope, receive, send, 429)
            return
        self.requests += 1
        try:
            if not creation:
                await self.app(scope, receive, send)
                return
            body = bytearray()
            try:
                async with asyncio.timeout(self.body_timeout):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        chunk = message.get("body", b"")
                        if len(body) + len(chunk) > self.body_limit:
                            await self.reject(scope, receive, send, 413)
                            return
                        body.extend(chunk)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                await self.reject(scope, receive, send, 408)
                return

            delivered = False

            async def bounded_receive() -> Message:
                nonlocal delivered
                if delivered:
                    return await receive()
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            await self.app(scope, bounded_receive, send)
        finally:
            self.requests -= 1
