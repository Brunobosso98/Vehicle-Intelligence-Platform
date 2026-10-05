import asyncio
import json

import pytest
from starlette.types import Message, Scope

from vehicle_platform.api.budgets import ResourceBudgetMiddleware, TokenBucket


def test_bucket_burst_refill_and_long_idle_never_exceed_capacity() -> None:
    now = [0.0]
    bucket = TokenBucket(2, 0.5, lambda: now[0])
    assert bucket.take() and bucket.take() and not bucket.take()
    now[0] = 1
    assert not bucket.take()
    now[0] = 2
    assert bucket.take() and not bucket.take()
    now[0] = 1000
    assert bucket.take() and bucket.take() and not bucket.take()
    now[0] = 999
    assert not bucket.take()


@pytest.mark.parametrize("capacity,rate", [(0, 1), (1, 0), (1, float("nan")), (1, float("inf"))])
def test_invalid_bucket_bounds_fail(capacity: int, rate: float) -> None:
    with pytest.raises(ValueError):
        TokenBucket(capacity, rate)


def request_scope(path: str, method: str = "GET") -> Scope:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
        "state": {"request_id": "budget-test"},
    }


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/v1/acquisitions/id/live", "GET"),
        ("/api/v1/analytics/pulls/compare", "POST"),
        ("/api/v1/acquisitions/id/finalize", "POST"),
        ("/api/v1/acquisitions/id", "GET"),
    ],
)
async def test_concurrency_rejects_excess_and_releases_after_cancel(path, method) -> None:
    entered = asyncio.Event()
    hold = asyncio.Event()
    messages: list[Message] = []

    async def app(scope, receive, send):
        entered.set()
        await hold.wait()

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        messages.append(message)

    budget = ResourceBudgetMiddleware(
        app, live_limit=1, request_limit=1 if path.endswith("/id") else 4, analysis_limit=1
    )
    first = asyncio.create_task(budget(request_scope(path, method), receive, send))
    await entered.wait()
    await budget(request_scope(path, method), receive, send)
    assert messages[0]["status"] == 429
    assert (b"retry-after", b"1") in messages[0]["headers"]
    assert json.loads(messages[1]["body"])["error"]["request_id"] == "budget-test"
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert budget.live == budget.requests == budget.analyses == 0
    hold.set()
    await budget(request_scope(path, method), receive, send)
    assert budget.live == budget.requests == budget.analyses == 0


async def test_creation_and_acquisition_frequency_bounds_preserve_other_routes() -> None:
    responses = []

    async def app(scope, receive, send):
        responses.append("allowed")

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        if message["type"] == "http.response.start":
            responses.append(message["status"])

    budget = ResourceBudgetMiddleware(app)
    budget.creation_rate = TokenBucket(1, 1, lambda: 0)
    await budget(request_scope("/api/v1/acquisitions", "POST"), receive, send)
    await budget(request_scope("/api/v1/acquisitions", "POST"), receive, send)
    assert responses == ["allowed", 429]
    budget.acquisition_rate = TokenBucket(1, 1, lambda: 0)
    await budget(request_scope("/api/v1/acquisitions/id"), receive, send)
    await budget(request_scope("/api/v1/acquisitions/id"), receive, send)
    await budget(request_scope("/health/live"), receive, send)
    await budget({"type": "lifespan"}, receive, send)
    assert responses[-4:] == ["allowed", 429, "allowed", "allowed"]


def test_concurrency_bounds_require_positive_limits() -> None:
    async def app(scope, receive, send):
        pass

    with pytest.raises(ValueError):
        ResourceBudgetMiddleware(app, live_limit=0)
