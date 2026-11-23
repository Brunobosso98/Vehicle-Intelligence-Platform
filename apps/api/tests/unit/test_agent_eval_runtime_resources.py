"""Run-scoped child resource measurements for Phase 11 acceptance."""

import asyncio
import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from agent_runtime import (  # noqa: E402
    Process,
    ask,
    begin_resource_measurement,
    free_port,
    resource_measurement_since,
)


class DelayedSSEBody(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b"id: 1\nevent: run_started\ndata: {}\n\n"
        await asyncio.sleep(0.01)
        yield b"id: 2\nevent: run_completed\ndata: {}\n\n"

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_resource_measurement_records_real_runner_child_process():
    port = free_port()
    baseline = begin_resource_measurement()
    process = Process(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        os.environ.copy(),
        f"http://127.0.0.1:{port}/",
    )
    try:
        await process.start()
    finally:
        await process.stop()
        process.close()

    measurement = resource_measurement_since(baseline)
    assert measurement["platform"] in {"linux", "darwin"}
    assert measurement["child_process_count"] == 1
    assert measurement["peak_child_rss_bytes"] > 0
    assert measurement["child_cpu_user_ms"] >= 0
    assert measurement["child_cpu_system_ms"] >= 0


@pytest.mark.asyncio
async def test_ask_measures_first_sse_event_from_stream_delivery():
    run = {"id": "run-1", "status": "completed", "result": {"answer": "recorded"}}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": "run-1"})
        if request.url.path.endswith("/stream"):
            if request.url.params.get("after") == "2":
                return httpx.Response(200, content=b"")
            if request.url.params.get("after") == "0":
                return httpx.Response(
                    200,
                    content=(
                        b"id: 1\nevent: run_started\ndata: {}\n\n"
                        b"id: 2\nevent: run_completed\ndata: {}\n\n"
                    ),
                )
            return httpx.Response(200, stream=DelayedSSEBody())
        if request.url.path.endswith("/audit"):
            return httpx.Response(200, json={"tool_calls": []})
        return httpx.Response(200, json=run)

    async with httpx.AsyncClient(
        base_url="http://phase11.test", transport=httpx.MockTransport(handler)
    ) as client:
        result = await ask(client, "vehicle-1", "What was recorded?")

    assert result["first_sse_event_ms"] >= 0
    assert result["sse_replay"]["verified"] is True
