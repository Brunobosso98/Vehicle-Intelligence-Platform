import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.openai_provider import OpenAIProvider
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.evaluation.diagnostics import TracedOpenAIProvider, public_json
from vehicle_platform.evaluation.metering import MeteredClient, ToolMeter
from vehicle_platform.mcp.schemas import Envelope


async def test_structured_diagnostics_redact_secrets_and_exclude_private_reasoning(
    tmp_path, monkeypatch
):
    settings = AgentSettings(model="gpt-6-luna", api_key=SecretStr("private-key-sentinel"))
    observer = MagicMock()
    provider = TracedOpenAIProvider(settings, observer, tmp_path)
    response = SimpleNamespace(
        model="gpt-6-luna",
        service_tier="flex",
        output_text=json.dumps({"claims": [], "private": "private-key-sentinel"}),
        output=[
            SimpleNamespace(type="reasoning", text="hidden-reasoning-sentinel"),
            SimpleNamespace(
                type="function_call",
                name="get_vehicle",
                arguments='{"private":"private-key-sentinel"}',
            ),
        ],
    )
    monkeypatch.setattr(OpenAIProvider, "_create", AsyncMock(return_value=(response, "ticket")))
    await provider._create("investigation", input="private-key-sentinel", max_output_tokens=2048)
    provider._record(response, "ticket")
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 2
    combined = "".join(path.read_text() for path in files)
    assert "private-key-sentinel" not in combined
    assert "hidden-reasoning-sentinel" not in combined
    assert "[redacted]" in combined and "get_vehicle" in combined
    observer.complete.assert_called_once()
    await provider.close()


async def test_provider_trace_failure_contains_only_category(tmp_path, monkeypatch):
    provider = TracedOpenAIProvider(
        AgentSettings(model="gpt-6-luna", api_key=SecretStr("private")), MagicMock(), tmp_path
    )
    monkeypatch.setattr(
        OpenAIProvider, "_create", AsyncMock(side_effect=AgentError("provider_timeout"))
    )
    with pytest.raises(AgentError, match="provider_timeout"):
        await provider._create("investigation", input="private")
    assert json.loads(next(tmp_path.glob("*.failure.json")).read_text()) == {
        "category": "provider_timeout"
    }
    assert public_json("unparsed-private-sentinel")["invalid_json"] is True
    assert "unparsed-private-sentinel" not in json.dumps(public_json("unparsed-private-sentinel"))
    await provider.close()


async def test_opt_in_mcp_traces_preserve_sanitized_arguments_and_results(tmp_path):
    vehicle = "00000000-0000-0000-0000-000000000001"
    settings = AgentSettings(model="gpt-6-luna", api_key=SecretStr("private"))
    meter = ToolMeter(tmp_path, settings)
    meter.start("21:G03:0", vehicle)
    source = AsyncMock()
    source.call.return_value = Envelope(
        data={"note": "private", "count": 3}, context={"vehicle_id": vehicle}
    )
    await MeteredClient(source, meter).call(
        "get_vehicle", {"vehicle_id": vehicle, "note": "private"}
    )
    payload = json.loads(next(tmp_path.glob("mcp-*.json")).read_text())
    assert payload["arguments"]["note"] == "[redacted]"
    assert payload["result"]["data"] == {"note": "[redacted]", "count": 3}
    assert payload["status"] == "completed"
    source.call.side_effect = AgentError("mcp_tool_error")
    with pytest.raises(AgentError):
        await MeteredClient(source, meter).call("get_vehicle", {"vehicle_id": vehicle})
    assert len(list(tmp_path.glob("mcp-*.json"))) == 2
    with pytest.raises(ValueError, match="sanitization"):
        ToolMeter(tmp_path)


async def test_parallel_mcp_traces_cannot_overwrite_each_other(tmp_path):
    import asyncio

    vehicle = "00000000-0000-0000-0000-000000000001"
    meter = ToolMeter(tmp_path, AgentSettings())
    meter.start("21:G03:0", vehicle)
    source = AsyncMock()

    async def read(name, arguments):
        await asyncio.sleep(0)
        return Envelope(data={}, context={"vehicle_id": vehicle})

    source.call.side_effect = read
    client = MeteredClient(source, meter)
    await asyncio.gather(*(client.call("get_vehicle", {"vehicle_id": vehicle}) for _ in range(2)))
    assert len(list(tmp_path.glob("mcp-*.json"))) == 2
