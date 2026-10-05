# ruff: noqa: S104
import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr, ValidationError

from vehicle_platform.core.config import Settings
from vehicle_platform.mcp.adapter import Adapter
from vehicle_platform.mcp.auth import ReadTokenVerifier
from vehicle_platform.mcp.config import MCPSettings
from vehicle_platform.mcp.errors import ErrorCode, PlatformError
from vehicle_platform.mcp.instrumentation import Instrumentation
from vehicle_platform.mcp.schemas import Envelope, Window
from vehicle_platform.mcp.server import create_server
from vehicle_platform.mcp.tools import TOOL_NAMES
from vehicle_platform.observability.telemetry import Telemetry


@pytest.fixture
def telemetry():
    settings = Settings(database_url=SecretStr("postgresql+asyncpg://test:password@localhost/test"))
    value = Telemetry(settings)
    yield value
    value.shutdown()


@pytest.mark.parametrize("seconds", [0, -1, 61])
def test_window_bounds(seconds):
    start = datetime.now(UTC)
    with pytest.raises(ValidationError):
        Window(start=start, end=start + timedelta(seconds=seconds))


def test_window_requires_timezone():
    with pytest.raises(ValidationError):
        Window(start=datetime(2026, 1, 1), end=datetime(2026, 1, 1, 0, 0, 1))


@pytest.mark.parametrize("token", [None, "short"])
def test_http_requires_token(token):
    with pytest.raises(ValidationError):
        MCPSettings(transport="streamable-http", token=token)


async def test_auth(telemetry):
    token = "x" * 40
    settings = MCPSettings(transport="streamable-http", token=SecretStr(token))
    verifier = ReadTokenVerifier(settings, telemetry)
    assert await verifier.verify_token("invalid") is None
    accepted = await verifier.verify_token(token)
    assert accepted and accepted.scopes == ["mcp:read"]
    settings.token_expires_at = 1
    assert await verifier.verify_token(token) is None
    settings.token_expires_at = None
    settings.token_scope = "other"  # noqa: S105 - scope
    assert (await verifier.verify_token(token)).scopes == ["other"]
    settings.token = None
    assert await verifier.verify_token(token) is None


async def test_discovery_and_errors(telemetry):
    adapter = MagicMock(spec=Adapter)
    adapter.catalog = MagicMock()
    adapter.catalog.vehicles = AsyncMock(return_value=[{"id": "fixture"}])
    adapter.envelope = Adapter.envelope.__get__(adapter)
    async with Client(create_server(adapter, telemetry, MCPSettings())) as client:
        assert client.protocol_version
        inventory = await client.list_tools()
        assert {item.name for item in inventory.tools} == TOOL_NAMES
        for item in inventory.tools:
            assert item.description
            assert item.input_schema
            assert item.output_schema
            assert item.annotations.read_only_hint
            assert item.annotations.destructive_hint is False
        templates = await client.list_resource_templates()
        assert len(templates.resource_templates) == 3
        result = await client.call_tool("list_vehicles", {"limit": 1})
        assert not result.is_error
        assert result.structured_content["data"] == [{"id": "fixture"}]
        for arguments in ({"limit": 101}, {"limit": 0}, {"limit": "SECRET"}):
            error = await client.call_tool("list_vehicles", arguments)
            assert error.is_error
            assert "INVALID_ARGUMENT" in error.content[0].text
            assert "SECRET" not in error.content[0].text


@pytest.mark.parametrize(
    "exception,expected",
    [
        (PlatformError(ErrorCode.INCOMPATIBLE_CONTEXT), "INCOMPATIBLE_CONTEXT"),
        (LookupError("secret"), "NOT_FOUND"),
        (ValueError("secret"), "INVALID_ARGUMENT"),
        (OSError("secret"), "BACKEND_UNAVAILABLE"),
        (RuntimeError("secret"), "INTERNAL_ERROR"),
    ],
)
async def test_instrumented_errors(telemetry, exception, expected):
    instrumentation = Instrumentation(telemetry, MCPSettings())

    async def failing():
        raise exception

    with pytest.raises(ToolError, match=expected) as error:
        await instrumentation.wrap(failing)()
    assert "secret" not in str(error.value)
    assert instrumentation.active == 0


async def test_timeout_size_rate_and_spans(telemetry):
    exporter = InMemorySpanExporter()
    telemetry.traces.add_span_processor(SimpleSpanProcessor(exporter))
    settings = MCPSettings(execution_timeout=0.01, max_result_bytes=1024)
    instrumentation = Instrumentation(telemetry, settings)

    async def delayed():
        await asyncio.Event().wait()
        return Envelope(data={})

    with pytest.raises(ToolError, match="BACKEND_UNAVAILABLE"):
        await instrumentation.wrap(delayed)()

    async def large():
        return Envelope(data={"value": "x" * 2048})

    with pytest.raises(ToolError, match="RESULT_TOO_LARGE"):
        await instrumentation.wrap(large)()
    instrumentation.active = settings.max_active_calls
    with pytest.raises(ToolError, match="RATE_LIMITED"):
        await instrumentation.wrap(large)()
    instrumentation.active = 0

    async def success():
        with telemetry.tracer.start_as_current_span("domain.fixture"):
            return Envelope(data=[{"id": 1}], truncated=True)

    result = await instrumentation.wrap(success)()
    assert result.mcp_request_id
    spans = exporter.get_finished_spans()
    domain = next(span for span in spans if span.name == "domain.fixture")
    parent = next(span for span in spans if span.context.span_id == domain.parent.span_id)
    assert parent.name == "mcp.tool"
    metrics = telemetry.render_metrics().decode()
    for name in (
        "mcp_tool_calls",
        "mcp_tool_errors",
        "mcp_tool_duration",
        "mcp_active_calls",
        "mcp_result_items",
        "mcp_truncated_results",
    ):
        assert name in metrics


async def test_adapter_isolation_and_envelope():
    adapter = object.__new__(Adapter)
    adapter.catalog = MagicMock()
    adapter.catalog.get = AsyncMock(return_value={"vehicle_id": str(uuid4())})
    with pytest.raises(PlatformError, match="INCOMPATIBLE_CONTEXT"):
        await adapter.entity("session", uuid4(), uuid4())
    adapter.analysis = MagicMock()
    adapter.analysis.pull = AsyncMock(return_value=None)
    with pytest.raises(PlatformError, match="NOT_FOUND"):
        await adapter.pull(uuid4(), uuid4())
    result = adapter.envelope([{"n": n} for n in range(3)], {}, limit=2)
    assert result.returned == 2 and result.truncated
    assert result.warnings[0].code == "truncated_result"
    assert not adapter.envelope({}, {}).truncated


@pytest.mark.parametrize(
    "host,url", [("example.org", "https://example.org/mcp"), ("0.0.0.0", "http://example.org/mcp")]
)
def test_network_config_rejected(host, url):
    with pytest.raises(ValidationError):
        MCPSettings(
            transport="streamable-http", token=SecretStr("x" * 40), host=host, resource_url=url
        )


async def test_all_tools_with_service_adapters(telemetry):
    from vehicle_platform.analytics.domain import AnalyticsConfig
    from vehicle_platform.api.domain_contracts import AnalyticsResultResponse

    vehicle, config_a, config_b = uuid4(), uuid4(), uuid4()
    session_a, session_b, pull_a, pull_b, pull_c, pull_d, event_id = [uuid4() for _ in range(7)]
    adapter = object.__new__(Adapter)
    adapter.config = AnalyticsConfig()
    records = {
        vehicle: {"id": str(vehicle)},
        config_a: {"vehicle_id": str(vehicle)},
        config_b: {"vehicle_id": str(vehicle)},
        session_a: {"vehicle_id": str(vehicle), "configuration_id": str(config_a)},
        session_b: {"vehicle_id": str(vehicle), "configuration_id": str(config_a)},
    }
    adapter.catalog = MagicMock()
    adapter.catalog.get = AsyncMock(side_effect=lambda kind, key: records[key])
    adapter.catalog.sessions = AsyncMock(return_value=[records[session_a]])
    adapter.catalog.modifications = AsyncMock(return_value=[])

    def pull_record(key):
        model = MagicMock()
        model.vehicle_id = vehicle
        model.model_dump.return_value = {
            "id": str(key),
            "vehicle_id": str(vehicle),
            "configuration_id": str(config_a if key in {pull_a, pull_b} else config_b),
        }
        return model

    adapter.analysis = MagicMock()
    adapter.analysis.pull = AsyncMock(side_effect=pull_record)
    adapter.analysis.pulls = AsyncMock(return_value=[pull_record(pull_a)])
    adapter.events = MagicMock()
    event = MagicMock()
    event.vehicle_id = vehicle
    event.model_dump.return_value = {"id": str(event_id)}
    adapter.events.event = AsyncMock(return_value=event)
    adapter.events.events = AsyncMock(return_value=[event])
    adapter.acquisition = MagicMock()
    adapter.acquisition.capability_report = AsyncMock(return_value={"available_signals": []})
    analytics = AnalyticsResultResponse(
        id=uuid4(),
        analytics_type="fixture",
        algorithm_name="fixture",
        algorithm_version="1.1.0",
        configuration_hash="a" * 64,
        source_fingerprint="b" * 64,
        vehicle_id=vehicle,
        configuration_id=config_a,
        status="limited",
        warnings=["missing_signal"],
        result={},
        generated_at=datetime.now(UTC),
    )
    adapter.analytics = MagicMock()
    for name in (
        "session",
        "pull",
        "comparison",
        "repeated",
        "vehicle_baseline",
        "trends",
        "modifications",
        "cross_sessions",
    ):
        setattr(adapter.analytics, name, AsyncMock(return_value=analytics))
    adapter.telemetry = MagicMock()
    from vehicle_platform.api.domain_contracts import TelemetryWindow

    adapter.telemetry.query = AsyncMock(
        return_value=TelemetryWindow(
            session_id=session_a, points=[], returned=0, truncated=True, start=None, end=None
        )
    )
    calls = {
        "get_vehicle": {"vehicle_id": vehicle},
        "get_vehicle_configuration": {"vehicle_id": vehicle, "configuration_id": config_a},
        "list_vehicle_modifications": {"vehicle_id": vehicle},
        "list_sessions": {"vehicle_id": vehicle, "configuration_id": config_a},
        "get_session": {"vehicle_id": vehicle, "session_id": session_a},
        "get_session_summary": {"vehicle_id": vehicle, "session_id": session_a},
        "get_session_analytics": {"vehicle_id": vehicle, "session_id": session_a},
        "get_session_capabilities": {"vehicle_id": vehicle, "session_id": session_a},
        "list_session_pulls": {"vehicle_id": vehicle, "session_id": session_a},
        "get_pull": {"vehicle_id": vehicle, "pull_id": pull_a},
        "get_pull_summary": {"vehicle_id": vehicle, "pull_id": pull_a},
        "compare_pulls": {"vehicle_id": vehicle, "pull_ids": [pull_a, pull_b]},
        "get_repeated_pull_analysis": {"vehicle_id": vehicle, "pull_ids": [pull_a, pull_b]},
        "list_session_events": {"vehicle_id": vehicle, "session_id": session_a},
        "list_pull_events": {"vehicle_id": vehicle, "pull_id": pull_a},
        "get_event": {"vehicle_id": vehicle, "event_id": event_id},
        "get_vehicle_baseline": {"vehicle_id": vehicle, "configuration_id": config_a},
        "get_vehicle_trend": {"vehicle_id": vehicle, "metric": "boost"},
        "compare_configurations": {
            "vehicle_id": vehicle,
            "before_pull_ids": [pull_a, pull_b],
            "after_pull_ids": [pull_c, pull_d],
        },
        "get_cross_session_analytics": {
            "vehicle_id": vehicle,
            "session_ids": [session_a, session_b],
        },
        "get_telemetry_window": {
            "vehicle_id": vehicle,
            "session_id": session_a,
            "signals": ["engine.rpm"],
            "window": {
                "start": datetime.now(UTC).isoformat(),
                "end": (datetime.now(UTC) + timedelta(seconds=1)).isoformat(),
            },
        },
    }
    import json

    async with Client(create_server(adapter, telemetry, MCPSettings())) as client:
        for name, args in calls.items():
            args = json.loads(json.dumps(args, default=str))
            result = await client.call_tool(name, args)
            assert not result.is_error, (name, result)
        for uri in (
            f"vehicle://{vehicle}",
            f"session://{vehicle}/{session_a}",
            f"pull://{vehicle}/{pull_a}",
        ):
            assert (await client.read_resource(uri)).contents
        negative = [
            ("compare_pulls", {"pull_ids": [pull_a, pull_a]}),
            ("compare_pulls", {"pull_ids": [pull_a, pull_c]}),
            (
                "compare_configurations",
                {"before_pull_ids": [pull_a, pull_b], "after_pull_ids": [pull_a, pull_b]},
            ),
            (
                "compare_configurations",
                {"before_pull_ids": [pull_a, pull_b], "after_pull_ids": [pull_a, pull_b] * 10},
            ),
            ("get_cross_session_analytics", {"session_ids": [session_a, session_a]}),
            (
                "get_telemetry_window",
                {
                    "session_id": session_a,
                    "signals": ["unsupported"],
                    "window": calls["get_telemetry_window"]["window"],
                },
            ),
            (
                "get_telemetry_window",
                {
                    "session_id": session_a,
                    "signals": ["engine.rpm", "engine.rpm"],
                    "window": calls["get_telemetry_window"]["window"],
                },
            ),
        ]
        for name, args in negative:
            result = await client.call_tool(
                name, json.loads(json.dumps({"vehicle_id": vehicle, **args}, default=str))
            )
            assert result.is_error
        records[session_b]["configuration_id"] = str(config_b)
        assert (
            await client.call_tool(
                "get_cross_session_analytics",
                {"vehicle_id": str(vehicle), "session_ids": [str(session_a), str(session_b)]},
            )
        ).is_error
        adapter.events.event.return_value = None
        adapter.events.event.side_effect = None
        assert (
            await client.call_tool(
                "get_event", {"vehicle_id": str(vehicle), "event_id": str(event_id)}
            )
        ).is_error
        event.vehicle_id = uuid4()
        adapter.events.event.return_value = event
        assert (
            await client.call_tool(
                "get_event", {"vehicle_id": str(vehicle), "event_id": str(event_id)}
            )
        ).is_error


async def test_http_trace_context_and_auth_rejections(telemetry):
    from starlette.requests import Request
    from starlette.responses import Response

    from vehicle_platform.mcp.instrumentation import HTTPInstrumentation

    exporter = InMemorySpanExporter()
    telemetry.traces.add_span_processor(SimpleSpanProcessor(exporter))
    middleware = HTTPInstrumentation(telemetry)
    trace_id = "1" * 32
    request = Request(
        {"type": "http", "headers": [(b"traceparent", f"00-{trace_id}-{'2' * 16}-01".encode())]}
    )
    for status in (200, 401, 403):

        async def next_request(request, selected_status=status):
            return Response(status_code=selected_status)

        assert (await middleware.dispatch(request, next_request)).status_code == status
    assert all(span.context.trace_id == int(trace_id, 16) for span in exporter.get_finished_spans())
    assert "mcp_auth_failures" in telemetry.render_metrics().decode()


async def test_read_only_database_setup():
    from sqlalchemy import event

    from vehicle_platform.mcp.database import ReadOnlyDatabase

    settings = Settings(database_url=SecretStr("postgresql+asyncpg://test:password@localhost/test"))
    database = ReadOnlyDatabase(settings)
    assert database.timeout == settings.readiness_timeout
    assert database.engine.sync_engine.get_execution_options()["postgresql_readonly"] is True
    assert database.sessions.kw["bind"] is database.engine
    captured = {}

    def capture_connect(dialect, record, arguments, parameters):
        captured.update(parameters)
        raise RuntimeError("stop before network connection")

    event.listen(database.engine.sync_engine, "do_connect", capture_connect)
    with pytest.raises(RuntimeError, match="stop before network"):
        async with database.engine.connect():
            pass
    assert captured["command_timeout"] == 5
    assert captured["server_settings"] == {
        "default_transaction_read_only": "on",
        "statement_timeout": "5000",
        "lock_timeout": "1000",
    }
    await database.close()


async def test_analytics_selection_reports_truncation():
    from vehicle_platform.api.domain_contracts import AnalyticsResultResponse

    adapter = object.__new__(Adapter)
    adapter.catalog = MagicMock()
    adapter.catalog.history_truncated = AsyncMock(return_value=True)
    result = AnalyticsResultResponse(
        id=uuid4(),
        analytics_type="session",
        algorithm_name="fixture",
        algorithm_version="1.1.0",
        configuration_hash="a" * 64,
        source_fingerprint="b" * 64,
        vehicle_id=uuid4(),
        configuration_id=None,
        status="completed",
        warnings=[],
        result={},
        generated_at=datetime.now(UTC),
    )
    response = await adapter.analytical(result, {"session_id": uuid4()})
    assert response.truncated and response.warnings[0].code == "truncated_result"
    adapter.catalog.history_truncated.return_value = False
    result.analytics_type = "cross_session"
    response = await adapter.analytical(result, {"session_ids": [uuid4(), uuid4()]})
    assert not response.truncated


async def test_actual_response_limit_and_unknown_tool(telemetry):
    from vehicle_platform.mcp.schemas import Envelope
    from vehicle_platform.mcp.server import SafeMCPServer

    server = SafeMCPServer("size")
    server.result_byte_limit = 1024

    async def big() -> Envelope:
        return Envelope(data={"value": "x" * 1024})

    server.add_tool(big)
    async with Client(server) as client:
        result = await client.call_tool("big", {})
        assert result.is_error and "RESULT_TOO_LARGE" in result.content[0].text
        unknown = await client.call_tool("unknown", {})
        assert unknown.is_error


async def test_database_abort_invalidated_connection():
    from vehicle_platform.mcp.database import ReadOnlyDatabase

    connection = MagicMock()
    ReadOnlyDatabase._abort_invalidated(connection, MagicMock(), RuntimeError())
    connection.driver_connection.terminate.assert_called_once()
    ReadOnlyDatabase._abort_invalidated(None, MagicMock(), None)


async def test_resource_errors_are_safe(telemetry, caplog):
    from mcp import MCPError

    adapter = MagicMock(spec=Adapter)
    adapter.catalog = MagicMock()
    adapter.entity = AsyncMock(side_effect=PlatformError(ErrorCode.NOT_FOUND))
    async with Client(create_server(adapter, telemetry, MCPSettings())) as client:
        for uri, code in (
            ("unknown://SECRET", "NOT_FOUND"),
            ("vehicle://SECRET", "INVALID_ARGUMENT"),
            (f"vehicle://{uuid4()}", "NOT_FOUND"),
        ):
            with pytest.raises(MCPError, match=code) as caught:
                await client.read_resource(uri)
            assert "SECRET" not in str(caught.value)
    assert "SECRET" not in caplog.text
