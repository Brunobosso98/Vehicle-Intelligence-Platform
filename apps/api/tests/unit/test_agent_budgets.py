"""Admission limits exercised before request decoding, including fragmented bodies."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from vehicle_platform.agents.config import AgentSettings, redact_data
from vehicle_platform.api.budgets import AgentRequestBudgetMiddleware


def scope(path="/api/v1/vehicles/test/agent-runs", method="POST"):
    return {"type": "http", "path": path, "method": method, "headers": []}


def test_redaction_preserves_numeric_json_and_escaped_strings():
    settings = AgentSettings(api_key="310", mcp_token='secret"quoted')
    original = {"310": [310, 310.5, True, None, '310 secret"quoted'], "safe": {"n": 310}}
    assert redact_data(original, settings) == {
        "[redacted]": [310, 310.5, True, None, "[redacted] [redacted]"],
        "safe": {"n": 310},
    }
    assert original["310"][0] == 310
    assert redact_data("unchanged", AgentSettings()) == "unchanged"


@pytest.mark.parametrize("value", [0, -1])
def test_invalid_budgets(value):
    with pytest.raises(ValueError):
        AgentRequestBudgetMiddleware(AsyncMock(), body_limit=value)


@pytest.mark.parametrize("mode", ["fragmented", "read", "cancel", "other", "websocket"])
async def test_request_passthrough_and_bounded_body(mode):
    receive = AsyncMock(
        side_effect=[
            {"type": "http.request", "body": b'{"q":', "more_body": True},
            {"type": "http.request", "body": b'"ok"}', "more_body": False},
            {"type": "http.disconnect"},
        ]
    )
    send = AsyncMock()
    captured = []

    async def app(request_scope, receiver, sender):
        if mode == "fragmented":
            captured.append(await receiver())
            captured.append(await receiver())

    middleware = AgentRequestBudgetMiddleware(app)
    request = scope()
    if mode == "read":
        request["method"] = "GET"
    if mode == "cancel":
        request["path"] += "/id/cancel"
    if mode == "other":
        request["path"] = "/health/live"
    if mode == "websocket":
        request["type"] = "websocket"
    await middleware(request, receive, send)
    assert middleware.requests == 0
    if mode == "fragmented":
        assert captured[0]["body"] == b'{"q":"ok"}'
        assert captured[1]["type"] == "http.disconnect"
    else:
        receive.assert_not_awaited()


@pytest.mark.parametrize(
    "mode,status",
    [
        ("large", 413),
        ("timeout", 408),
        ("disconnect", None),
        ("rate", 429),
        ("concurrency", 429),
    ],
)
async def test_budget_failures_release_reservation(mode, status):
    app, send = AsyncMock(), AsyncMock()
    middleware = AgentRequestBudgetMiddleware(app, body_limit=4, body_timeout=0.01)
    initial = 0
    if mode == "rate":
        middleware.creation_rate.tokens = 0
    if mode == "concurrency":
        initial = middleware.requests = middleware.request_limit
    if mode == "timeout":

        async def slow():
            await asyncio.sleep(1)

        receive = slow
    else:
        receive = AsyncMock(
            return_value={
                "type": "http.disconnect" if mode == "disconnect" else "http.request",
                "body": b"12345",
                "more_body": False,
            }
        )
    await middleware(scope(), receive, send)
    app.assert_not_awaited()
    assert middleware.requests == initial
    if status is None:
        send.assert_not_awaited()
    else:
        assert send.call_args_list[0].args[0]["status"] == status


async def test_request_failure_releases_reservation():
    app = AsyncMock(side_effect=ValueError("controlled test"))
    middleware = AgentRequestBudgetMiddleware(app)
    receive = AsyncMock(return_value={"type": "http.request", "body": b"{}"})
    with pytest.raises(ValueError):
        await middleware(scope(), receive, AsyncMock())
    assert middleware.requests == 0


async def test_request_cancellation_releases_reservation():
    entered = asyncio.Event()

    async def waiting():
        entered.set()
        await asyncio.Event().wait()

    middleware = AgentRequestBudgetMiddleware(AsyncMock())
    task = asyncio.create_task(middleware(scope(), waiting, AsyncMock()))
    await entered.wait()
    assert middleware.requests == 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert middleware.requests == 0
