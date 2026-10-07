"""Independent acceptance against actual official MCP clients and real domain fixtures."""

import asyncio
import json
import os
from typing import Any
from uuid import uuid4

from mcp import Client, MCPError
from mcp_fixtures import fingerprint, seed
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr
from vehicle_platform.core.config import Settings
from vehicle_platform.mcp.adapter import Adapter
from vehicle_platform.mcp.config import MCPSettings
from vehicle_platform.mcp.database import ReadOnlyDatabase
from vehicle_platform.mcp.server import create_server
from vehicle_platform.mcp.tools import TOOL_NAMES
from vehicle_platform.observability.exporter import SanitizingExporter
from vehicle_platform.observability.telemetry import Telemetry


async def evaluate(client: Client, f: dict[str, Any]) -> dict[str, Any]:
    inventory = await client.list_tools()
    assert {tool.name for tool in inventory.tools} == TOOL_NAMES
    for tool in inventory.tools:
        assert tool.input_schema and tool.output_schema and tool.description
        assert tool.annotations.read_only_hint and not tool.annotations.destructive_hint
    vehicle, session, pull = f["vehicle"], f["sessions"][0], f["pulls"][0][0]
    context = {"vehicle_id": vehicle}
    checks = []

    async def call(name: str, **arguments: Any) -> Any:
        result = await client.call_tool(name, arguments)
        assert not result.is_error, (name, result.content)
        content = result.structured_content
        assert (
            content and content["schema_version"] == "1.0" and content["mcp_request_id"]
        )
        assert len(json.dumps(content).encode()) <= 524288
        checks.append(name)
        return content

    async def error(name: str, code: str, **arguments: Any) -> None:
        result = await client.call_tool(name, arguments)
        assert result.is_error and code in result.content[0].text, (name, result)
        checks.append(f"{name}:{code}")

    vehicles = await call("list_vehicles", limit=1)
    assert vehicles["returned"] == 1 and vehicles["truncated"]
    found = await call("get_vehicle", **context)
    assert found["data"]["model"] == "phase6" and found["data"]["id"] == vehicle
    await error("get_vehicle", "NOT_FOUND", vehicle_id=str(uuid4()))
    await error("get_vehicle", "INVALID_ARGUMENT", vehicle_id="private-input")
    await error("list_vehicles", "INVALID_ARGUMENT", limit=101)
    await call(
        "get_vehicle_configuration", **context, configuration_id=f["configurations"][0]
    )
    configurations = await call("list_vehicle_configurations", **context, limit=100)
    assert {item["id"] for item in configurations["data"]} == set(f["configurations"])
    assert all(item["vehicle_id"] == vehicle for item in configurations["data"])
    limited = await call("list_vehicle_configurations", **context, limit=1)
    assert limited["returned"] == 1 and limited["truncated"]
    await error("list_vehicle_configurations", "INVALID_ARGUMENT", **context, limit=101)
    await call("list_vehicle_modifications", **context)
    sessions = await call("list_sessions", **context, limit=2)
    assert sessions["returned"] == 2 and sessions["truncated"]
    await call("get_session", **context, session_id=session)
    summary = await call("get_session_summary", **context, session_id=session)
    assert (
        summary["data"]["result"]["session_summary"]["telemetry_observation_count"]
        == f["observation_count"]
    )
    assert summary["provenance"]["analysis_run_id"] is None
    assert len(summary["provenance"]["source_fingerprint"]) == 64
    await call("get_session_analytics", **context, session_id=session)
    capabilities = await call("get_session_capabilities", **context, session_id=session)
    assert "engine.rpm" in capabilities["data"]["available_signals"]
    pulls = await call("list_session_pulls", **context, session_id=session)
    assert [item["id"] for item in pulls["data"]] == f["pulls"][0]
    await call("get_pull", **context, pull_id=pull)
    profile = await call("get_pull_summary", **context, pull_id=pull)
    assert profile["data"]["algorithm_version"] == "1.1.0"
    await error("get_pull_summary", "NOT_FOUND", **context, pull_id=str(uuid4()))
    await call("compare_pulls", **context, pull_ids=f["pulls"][0][:2])
    await call("get_repeated_pull_analysis", **context, pull_ids=f["pulls"][0])
    await error(
        "compare_pulls",
        "INCOMPATIBLE_CONTEXT",
        **context,
        pull_ids=[pull, f["pulls"][3][0]],
    )
    await error(
        "get_session",
        "INCOMPATIBLE_CONTEXT",
        vehicle_id=f["other_vehicle"],
        session_id=session,
    )
    await error(
        "get_pull", "INCOMPATIBLE_CONTEXT", vehicle_id=f["other_vehicle"], pull_id=pull
    )
    await error(
        "get_vehicle_configuration",
        "INCOMPATIBLE_CONTEXT",
        vehicle_id=f["other_vehicle"],
        configuration_id=f["configurations"][0],
    )
    events = await call("list_session_events", **context, session_id=session)
    assert f["event"] in {item["id"] for item in events["data"]}
    await call("list_pull_events", **context, pull_id=pull)
    event = await call("get_event", **context, event_id=f["event"])
    assert event["data"]["event_type"] == "boost_drop" and event["data"]["evidence"]
    baseline = await call(
        "get_vehicle_baseline", **context, configuration_id=f["configurations"][0]
    )
    assert baseline["data"]["result"]["session_count"] == 3
    assert baseline["data"]["status"] == "completed"
    empty = await call(
        "get_vehicle_baseline", **context, configuration_id=f["configurations"][2]
    )
    assert empty["data"]["status"] == "insufficient"
    assert "insufficient_history" in {w["code"] for w in empty["warnings"]}
    trend = await call("get_vehicle_trend", **context, metric="boost")
    assert set(trend["data"]["result"]["segments_by_configuration"]) == set(
        f["configurations"][:2]
    )
    compared = await call(
        "compare_configurations",
        **context,
        before_pull_ids=[f["pulls"][i][0] for i in range(3)],
        after_pull_ids=[f["pulls"][i][0] for i in range(3, 6)],
    )
    assert compared["data"]["result"]["metric_deltas"]["boost"]["absolute"] == 0
    await call("get_cross_session_analytics", **context, session_ids=f["sessions"][:2])
    await error(
        "get_cross_session_analytics",
        "INCOMPATIBLE_CONTEXT",
        **context,
        session_ids=[session, f["sessions"][3]],
    )
    window = {"start": f["start"], "end": f["end"]}
    samples = await call(
        "get_telemetry_window",
        **context,
        session_id=session,
        signals=["engine.rpm"],
        window=window,
        max_samples=2,
    )
    assert samples["returned"] == 2 and samples["truncated"]
    assert all(
        item["unit"] == "rpm" and item["sample_id"]
        for item in samples["data"]["points"]
    )
    missing = await call(
        "get_telemetry_window",
        **context,
        session_id=session,
        signals=["electrical.battery_voltage"],
        window=window,
    )
    assert missing["returned"] == 0 and missing["data"]["points"] == []
    assert any(w["code"] == "missing_signal" for w in missing["warnings"])
    partial = await call(
        "get_telemetry_window",
        **context,
        session_id=session,
        signals=["engine.rpm", "engine.boost_pressure"],
        window=window,
        max_samples=1,
    )
    assert partial["returned"] == 1 and partial["truncated"]
    assert "partial_window" in {w["code"] for w in partial["warnings"]}
    assert "missing_signal" not in {w["code"] for w in partial["warnings"]}
    await error(
        "get_telemetry_window",
        "UNSUPPORTED_CAPABILITY",
        **context,
        session_id=session,
        signals=["unsupported"],
        window=window,
    )
    await error(
        "get_telemetry_window",
        "INVALID_ARGUMENT",
        **context,
        session_id=session,
        signals=["engine.rpm"],
        window=window,
        max_samples=1001,
    )
    resources = await client.list_resource_templates()
    assert len(resources.resource_templates) == 3
    for uri in (
        f"vehicle://{vehicle}",
        f"session://{vehicle}/{session}",
        f"pull://{vehicle}/{pull}",
    ):
        resource = await client.read_resource(uri)
        assert json.loads(resource.contents[0].text)["schema_version"] == "1.0"
    for uri, expected in (
        ("unknown://resource", "NOT_FOUND"),
        ("vehicle://invalid-id", "INVALID_ARGUMENT"),
    ):
        try:
            await client.read_resource(uri)
        except MCPError as exc:
            assert expected in str(exc)
            assert "invalid-id" not in str(exc)
        else:
            raise AssertionError("invalid resource accepted")
    return {
        "checks": checks,
        "protocol": client.protocol_version,
        "tool_count": len(inventory.tools),
    }


async def main() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed(url)
    before = await fingerprint(url)
    settings = Settings(database_url=SecretStr(url), environment="test")
    database = ReadOnlyDatabase(settings)
    telemetry = Telemetry(settings, database, service_name="vehicle-platform-mcp")
    exporter = InMemorySpanExporter()
    telemetry.traces.add_span_processor(
        SimpleSpanProcessor(SanitizingExporter(exporter))
    )
    try:
        server = create_server(
            Adapter(database, settings, telemetry), telemetry, MCPSettings()
        )
        async with Client(server) as client:
            report = await evaluate(client, fixture)
        assert await fingerprint(url) == before, "MCP must not change persisted state"
        spans = exporter.get_finished_spans()
        tools = [span for span in spans if span.name == "mcp.tool"]
        queries = [span for span in spans if "db.system" in (span.attributes or {})]
        domains = [span for span in spans if span.name == "analytics.source_selection"]
        assert tools and queries and domains
        assert any(
            domain.parent
            and any(tool.context.span_id == domain.parent.span_id for tool in tools)
            for domain in domains
        )
        assert any(query.parent for query in queries)
        assert all(
            "db.statement" not in (span.attributes or {})
            and "db.query.text" not in (span.attributes or {})
            for span in spans
        )
        assert all(event.name != "exception" for span in spans for event in span.events)
        report["delivered_spans"] = {
            "tools": len(tools),
            "domain": len(domains),
            "database": len(queries),
        }
        print(json.dumps({"phase6_acceptance": "PASS", **report}))
    finally:
        await database.close()
        telemetry.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
