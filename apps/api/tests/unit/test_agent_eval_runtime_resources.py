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
    runtime,
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


@pytest.mark.asyncio
async def test_ask_sends_prediction_capability_only_for_explicit_evidence_reads():
    run = {"id": "run-1", "status": "completed", "result": {"answer": "recorded"}}
    post_request: httpx.Request | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal post_request
        if request.method == "POST":
            post_request = request
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
        result = await ask(
            client,
            "vehicle-1",
            "What does the recorded prediction show?",
            prediction_evidence_ids=("00000000-0000-4000-8000-000000000001",),
            prediction_capability="controlled-runtime-capability",
        )

    assert post_request is not None
    assert post_request.headers["X-VIP-Prediction-Agent-Capability"] == (
        "controlled-runtime-capability"
    )
    assert result["sse_replay"]["verified"] is True


@pytest.mark.asyncio
async def test_ask_rejects_prediction_evidence_without_runtime_capability():
    async with httpx.AsyncClient(
        base_url="http://phase11.test",
        transport=httpx.MockTransport(
            lambda _request: pytest.fail("request must be rejected before API call")
        ),
    ) as client:
        with pytest.raises(ValueError, match="require a runtime capability"):
            await ask(
                client,
                "vehicle-1",
                "What does the prediction show?",
                prediction_evidence_ids=("00000000-0000-4000-8000-000000000001",),
            )


@pytest.mark.asyncio
async def test_prediction_evidence_runtime_passes_controlled_service_to_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "PREDICTION_SERVICE_ENABLED",
        "PREDICTION_OPERATOR_TOKEN",
        "VIP_AGENT_PREDICTION_SERVICE_ENABLED",
        "VIP_AGENT_PREDICTION_EVIDENCE_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)

    api_environments: list[dict[str, str]] = []

    async def capture_environment(process: Process) -> None:
        if "uvicorn" in process.args:
            api_environments.append(process.env)

    monkeypatch.setattr(Process, "start", capture_environment)
    async with runtime(
        "postgresql+asyncpg://vehicle:test-only@127.0.0.1:5432/vehicle_test",
        enable_prediction_evidence=True,
        prediction_vehicle_id="00000000-0000-4000-8000-000000000001",
    ):
        pass

    assert len(api_environments) == 1
    api_env = api_environments[0]
    assert api_env["PREDICTION_SERVICE_ENABLED"] == "true"
    assert len(api_env["PREDICTION_OPERATOR_TOKEN"]) >= 43
    assert api_env["VIP_AGENT_PREDICTION_SERVICE_ENABLED"] == "true"
    assert api_env["VIP_AGENT_PREDICTION_EVIDENCE_ENABLED"] == "true"
