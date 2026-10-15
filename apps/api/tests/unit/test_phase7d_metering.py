from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.evaluation.metering import MeteredClient, ToolMeter
from vehicle_platform.mcp.schemas import Envelope

VEHICLE = "00000000-0000-0000-0000-000000000001"
FOREIGN = "00000000-0000-0000-0000-000000000002"


def source():
    client = AsyncMock()
    client.discover.return_value = [{"name": "get_vehicle"}]
    client.call.return_value = Envelope(data={}, context={"vehicle_id": VEHICLE})
    return client


async def test_meter_covers_phase7b_reads_and_preserves_safe_hashes():
    meter = ToolMeter()
    wrapped = MeteredClient(source(), meter)
    await wrapped.call("get_vehicle", {"vehicle_id": VEHICLE})
    assert not meter.calls
    meter.start("1:G01:0", VEHICLE)
    for _ in range(2):
        await wrapped.call("get_session_capabilities", {"vehicle_id": VEHICLE, "session_id": "s"})
    calls = meter.calls["1:G01:0"]
    assert len(calls) == 2 and all(
        c["status"] == "completed" and c["duration_seconds"] >= 0 for c in calls
    )
    assert calls[0]["argument_hash"] == calls[1]["argument_hash"]
    assert all("arguments" not in c for c in calls)
    assert await wrapped.discover() == [{"name": "get_vehicle"}]


@pytest.mark.parametrize(
    "name,vehicle,category",
    [
        ("write_ecu", VEHICLE, "forbidden_tool"),
        ("list_vehicles", VEHICLE, "forbidden_tool"),
        ("get_vehicle", FOREIGN, "incompatible_context"),
    ],
)
async def test_unsafe_or_foreign_requests_never_reach_mcp(name, vehicle, category):
    client = source()
    meter = ToolMeter()
    meter.start("1:H01:0", VEHICLE)
    with pytest.raises(AgentError, match=category):
        await MeteredClient(client, meter).call(name, {"vehicle_id": vehicle})
    client.call.assert_not_called()


async def test_total_cap_includes_phase7b_and_resets_only_for_next_case():
    client = source()
    meter = ToolMeter()
    wrapped = MeteredClient(client, meter)
    meter.start("1:G01:0", VEHICLE)
    for _ in range(43):
        await wrapped.call("get_session_capabilities", {"vehicle_id": VEHICLE})
    with pytest.raises(AgentError, match="BUDGET_VIOLATION"):
        await wrapped.call("get_session_capabilities", {"vehicle_id": VEHICLE})
    assert client.call.await_count == 43
    meter.start("1:G01:1", VEHICLE)
    await wrapped.call("get_session_capabilities", {"vehicle_id": VEHICLE})
    assert len(meter.calls["1:G01:1"]) == 1


async def test_single_telemetry_window_and_failed_reads_are_measured():
    client = source()
    meter = ToolMeter()
    meter.start("1:B01:0", VEHICLE)
    wrapped = MeteredClient(client, meter)
    client.call.side_effect = AgentError("mcp_tool_error")
    with pytest.raises(AgentError, match="mcp_tool_error"):
        await wrapped.call("get_telemetry_window", {"vehicle_id": VEHICLE})
    assert meter.calls["1:B01:0"][0]["status"] == "failed"
    with pytest.raises(AgentError, match="BUDGET_VIOLATION"):
        await wrapped.call("get_telemetry_window", {"vehicle_id": VEHICLE})
    client.call.side_effect = None
    client.call.return_value = Envelope(data={}, context={"vehicle_id": FOREIGN})
    with pytest.raises(AgentError, match="incompatible_context"):
        await wrapped.call("get_vehicle", {"vehicle_id": VEHICLE})


async def test_evaluation_factory_wraps_the_actual_connect_seam(monkeypatch):
    client = source()

    @asynccontextmanager
    async def connect(settings):
        yield client

    monkeypatch.setattr("vehicle_platform.evaluation.metering.connect", connect)
    meter = ToolMeter()
    meter.start("1:A01:0", VEHICLE)
    async with meter.client(AgentSettings()) as wrapped:
        await wrapped.call("get_vehicle", {"vehicle_id": VEHICLE})
    assert len(meter.calls["1:A01:0"]) == 1
