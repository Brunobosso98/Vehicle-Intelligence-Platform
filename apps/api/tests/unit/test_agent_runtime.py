"""Provider wire parsing and service lifecycle failure branches (unit doubles only)."""

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError
from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError
from test_agents import fixture as fixture
from test_agents import insufficient
from test_agents import telemetry as telemetry

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.mcp_client import MCPClient
from vehicle_platform.agents.openai_provider import OpenAIProvider
from vehicle_platform.agents.provider import AgentError, ModelInput, ModelTurn
from vehicle_platform.agents.repository import AgentRepository
from vehicle_platform.agents.schemas import Ask
from vehicle_platform.agents.scripted_provider import DeterministicProvider, ScriptedProvider
from vehicle_platform.agents.service import AgentService, failure_category
from vehicle_platform.mcp.schemas import Envelope


class ResponseStream:
    def __init__(self, events):
        self.events = events

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def __aiter__(self):
        return self.generate()

    async def generate(self):
        for event in self.events:
            yield event


def test_transport_exception_groups_preserve_safe_categories():
    assert (
        failure_category(ExceptionGroup("private", [AgentError("provider_authentication")]))
        == "provider_authentication"
    )
    assert (
        failure_category(ExceptionGroup("private", [SQLAlchemyError("private")]))
        == "database_unavailable"
    )
    assert failure_category(ExceptionGroup("private", [TimeoutError()])) == "run_timeout"
    assert (
        failure_category(ExceptionGroup("private", [TimeoutError(), ValueError("secret")]))
        == "dependency_unavailable"
    )


@pytest.fixture
def provider(monkeypatch):
    client = MagicMock()
    client.responses.create = AsyncMock()
    client.close = AsyncMock()
    monkeypatch.setattr(
        "vehicle_platform.agents.openai_provider.AsyncOpenAI", lambda **args: client
    )
    return OpenAIProvider(
        AgentSettings(api_key=SecretStr("sentinel-private-key"), model="test-model")
    )


def request():
    return ModelInput(
        question="IAT?",
        tools=[{"name": "get_vehicle", "description": "Read", "parameters": {"type": "object"}}],
        context={},
        evidence=[],
        messages=[],
    )


@pytest.mark.parametrize("mode", ["draft", "call", "unknown_usage"])
async def test_real_provider_adapter_streamed_wire_contract(provider, mode):
    usage = (
        None
        if mode == "unknown_usage"
        else SimpleNamespace(
            input_tokens=12,
            output_tokens=7,
            total_tokens=19,
            input_tokens_details=SimpleNamespace(cached_tokens=2),
        )
    )
    output = (
        [
            SimpleNamespace(
                type="function_call",
                arguments='{"vehicle_id":"v"}',
                call_id="call-1",
                name="get_vehicle",
            )
        ]
        if mode == "call"
        else []
    )
    response = SimpleNamespace(
        output=output, output_text=insufficient().model_dump_json(), usage=usage
    )
    provider.client.responses.create.return_value = ResponseStream(
        [
            SimpleNamespace(type="response.output_text.delta", delta="bounded"),
            SimpleNamespace(type="response.completed", response=response),
        ]
    )
    turn = await provider.turn(request())
    assert turn.usage.total_tokens == (None if mode == "unknown_usage" else 19)
    assert turn.usage.estimated_cost is None
    if mode == "call":
        assert turn.tool_calls[0].arguments == {"vehicle_id": "v"} and turn.draft is None
    else:
        assert turn.draft == insufficient()
    kwargs = provider.client.responses.create.call_args.kwargs
    assert kwargs["stream"] is True and kwargs["store"] is False
    assert kwargs["parallel_tool_calls"] is False
    assert "sentinel-private-key" not in json.dumps(kwargs)
    await provider.close()
    provider.client.close.assert_awaited_once()


async def test_run_deadline_includes_validated_answer_publication(fixture, telemetry):
    service, _, events, _ = service_fixture(fixture, telemetry)
    service.settings.run_timeout = 0.1
    original_event = service.repository.event.side_effect

    async def slow_publication(event):
        if event.type == "answer_chunk":
            await asyncio.sleep(1)
        await original_event(event)

    service.repository.event.side_effect = slow_publication
    vehicle = UUID(fixture["vehicle"]["id"])
    run = await service.start(vehicle, Ask(question="Qual causa?"))
    async with asyncio.timeout(0.5):
        await service.tasks[run.id]
    stored = await service.repository.get(vehicle, run.id)
    assert stored.status == "failed" and stored.error_category == "run_timeout"
    assert stored.result is None and events[-1].type == "run_failed"
    assert not any(event.type == "answer_chunk" for event in events)
    assert not service.tasks and service.active == 0


@pytest.mark.parametrize(
    "mode,category",
    [
        ("no_complete", "invalid_model_response"),
        ("failed", "invalid_model_response"),
        ("bad_json", "invalid_model_response"),
        ("not_object", "invalid_model_response"),
        ("large", "model_output_budget_exhausted"),
        ("large_complete", "model_output_budget_exhausted"),
        ("input", "model_input_budget_exhausted"),
        ("authentication", "provider_authentication"),
        ("rate", "provider_rate_limit"),
        ("connection", "provider_unavailable"),
        ("timeout", "provider_timeout"),
    ],
)
async def test_provider_normalizes_failure_without_secret(provider, mode, category):
    response = SimpleNamespace(output=[], output_text="{", usage=None)
    events = [SimpleNamespace(type="response.completed", response=response)]
    if mode == "no_complete":
        events = []
    if mode == "failed":
        events = [SimpleNamespace(type="response.failed")]
    if mode == "not_object":
        response.output = [SimpleNamespace(type="function_call", arguments="[]")]
    if mode == "large":
        events = [SimpleNamespace(type="response.function_call_arguments.delta", delta="x" * 32769)]
    if mode == "large_complete":
        response.output_text = "x" * 32769
    if mode == "input":
        provider.settings.max_input_bytes = 1
    wire_request = httpx.Request("POST", "https://example.invalid")
    if mode in {"authentication", "rate", "connection", "timeout"}:
        errors = {
            "authentication": AuthenticationError(
                "sentinel-private-key",
                response=httpx.Response(401, request=wire_request),
                body=None,
            ),
            "rate": RateLimitError(
                "sentinel-private-key",
                response=httpx.Response(429, request=wire_request),
                body=None,
            ),
            "connection": APIConnectionError(request=wire_request),
            "timeout": APITimeoutError(request=wire_request),
        }
        provider.client.responses.create.side_effect = errors[mode]
    provider.client.responses.create.return_value = ResponseStream(events)
    with pytest.raises(AgentError, match=category) as caught:
        await provider.turn(request())
    assert "sentinel-private-key" not in str(caught.value)


def test_provider_missing_configuration():
    with pytest.raises(AgentError, match="provider_configuration"):
        OpenAIProvider(AgentSettings())


@pytest.mark.parametrize("mode", ["unknown", "no_annotations", "write", "open_world"])
async def test_mcp_discovery_rejects_unsafe_inventory(mode):
    annotation = SimpleNamespace(read_only_hint=True, destructive_hint=False, open_world_hint=False)
    tool = SimpleNamespace(name="get_vehicle", annotations=annotation)
    if mode == "unknown":
        tool.name = "execute_shell"
    if mode == "no_annotations":
        tool.annotations = None
    if mode == "write":
        annotation.destructive_hint = True
    if mode == "open_world":
        annotation.open_world_hint = True
    client = MagicMock()
    client.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[tool]))
    with pytest.raises(AgentError, match="unsafe_tool_inventory"):
        await MCPClient(client).discover()


@pytest.mark.parametrize(
    "error,structured,category",
    [
        (True, {}, "mcp_tool_error"),
        (False, None, "invalid_tool_result"),
    ],
)
async def test_mcp_wire_error_is_not_promoted_to_evidence(error, structured, category):
    client = MagicMock()
    client.call_tool = AsyncMock(
        return_value=SimpleNamespace(is_error=error, structured_content=structured)
    )
    with pytest.raises(AgentError, match=category):
        await MCPClient(client).call("get_vehicle", {})


def service_fixture(fixture, telemetry):
    runs, events, calls = {}, [], []
    repo = MagicMock(spec=AgentRepository)

    async def save(run):
        runs[run.id] = run.model_copy(deep=True)

    async def get(vehicle, identifier):
        if identifier not in runs or runs[identifier].vehicle_id != vehicle:
            raise AgentError("run_not_found")
        return runs[identifier].model_copy(deep=True)

    async def event(value):
        events.append(value)

    async def finish(run, value):
        await save(run)
        await event(value)

    async def audit(value):
        calls.append(value.model_copy(deep=True))

    async def replay(vehicle, identifier, after):
        await get(vehicle, identifier)
        return [e for e in events if e.run_id == identifier and e.sequence > after]

    repo.create, repo.save, repo.get = (
        AsyncMock(side_effect=save),
        AsyncMock(side_effect=save),
        AsyncMock(side_effect=get),
    )
    repo.event, repo.finish, repo.audit = (
        AsyncMock(side_effect=event),
        AsyncMock(side_effect=finish),
        AsyncMock(side_effect=audit),
    )
    repo.events = AsyncMock(side_effect=replay)
    client = MagicMock()
    records = {
        "get_vehicle": fixture["vehicle"],
        "list_vehicle_configurations": fixture["configurations"],
        "list_vehicle_modifications": fixture["modifications"],
        "list_sessions": [],
    }
    client.discover = AsyncMock(
        return_value=[
            {
                "name": name,
                "description": "Read",
                "parameters": {"type": "object", "required": ["vehicle_id"]},
            }
            for name in records
        ]
    )

    async def call(name, args):
        return Envelope(data=records[name], context={"vehicle_id": args["vehicle_id"]})

    client.call = AsyncMock(side_effect=call)

    @asynccontextmanager
    async def connection():
        yield client

    settings = AgentSettings(
        provider="deterministic",
        mcp_token=SecretStr("sentinel-mcp-key"),
        enabled=True,
        api_key=SecretStr("sentinel-api-key"),
    )
    return (
        AgentService(repo, settings, telemetry, DeterministicProvider, connection),
        client,
        events,
        calls,
    )


async def test_service_lifecycle_redaction_followup_and_replay(fixture, telemetry):
    service, _, events, calls = service_fixture(fixture, telemetry)
    vehicle = UUID(fixture["vehicle"]["id"])
    run = await service.start(vehicle, Ask(question="sentinel-api-key sentinel-mcp-key"))
    await service.tasks[run.id]
    stored = await service.repository.get(vehicle, run.id)
    assert stored.status == "completed" and stored.evidence

    assert "sentinel" not in stored.model_dump_json()
    assert stored.result.context.vehicle["engine_code"] == "N55"
    assert [e.sequence for e in events] == list(range(1, len(events) + 1))
    replay = [e async for e in service.stream(vehicle, run.id, after=1)]
    assert replay[-1].type == "run_completed" and all(e.sequence > 1 for e in replay)
    assert all(c.completed_at for c in calls if c.status != "running")
    assert not service.tasks and service.active == 0 and service.streams == 0
    followup = await service.start(vehicle, Ask(question="Qual causa?", previous_run_id=run.id))
    await service.tasks[followup.id]
    assert (await service.repository.get(vehicle, followup.id)).status == "completed"
    with pytest.raises(AgentError, match="run_not_found"):
        await service.start(uuid4(), Ask(question="x", previous_run_id=run.id))
    assert service.active == 0
    await service.close()


async def test_provider_input_excludes_configured_secrets(fixture, telemetry):
    fixture["vehicle"]["model"] = "sentinel-api-key"
    fixture["configurations"][0]["label"] = "sentinel-mcp-key"
    service, _, _, _ = service_fixture(fixture, telemetry)
    service.settings.model = "sentinel-api-key"
    seen = []

    def validate_input(request):
        encoded = json.dumps(asdict(request))
        assert "sentinel-api-key" not in encoded
        assert "sentinel-mcp-key" not in encoded
        seen.append(request)
        return ModelTurn(draft=insufficient())

    service.provider_factory = lambda: ScriptedProvider([validate_input])
    vehicle = UUID(fixture["vehicle"]["id"])
    run = await service.start(vehicle, Ask(question="sentinel-api-key sentinel-mcp-key"))
    assert run.model == "[redacted]"
    await service.tasks[run.id]
    assert (await service.repository.get(vehicle, run.id)).status == "completed"
    assert seen
    await service.close()


async def test_terminal_database_failure_releases_owned_task(fixture, telemetry):
    service, _, _, _ = service_fixture(fixture, telemetry)
    service.repository.finish.side_effect = AgentError("database_unavailable")
    run = await service.start(UUID(fixture["vehicle"]["id"]), Ask(question="última sessão"))
    await service.tasks[run.id]
    assert run.status == "failed" and run.result is None
    assert run.error_category == "database_unavailable"
    assert service.active == 0 and not service.tasks
    await service.close()


@pytest.mark.parametrize(
    "mode,category",
    [
        ("provider", "provider_authentication"),
        ("database", "database_unavailable"),
        ("dependency", "dependency_unavailable"),
        ("timeout", "run_timeout"),
        ("answer", "answer_budget_exhausted"),
    ],
)
async def test_service_failure_is_terminal_and_recoverable(fixture, telemetry, mode, category):
    service, client, events, _ = service_fixture(fixture, telemetry)
    if mode == "provider":
        service.provider_factory = lambda: ScriptedProvider([AgentError(category)])
    if mode == "database":
        service.repository.event.side_effect = SQLAlchemyError("sentinel-api-key")
    if mode == "dependency":
        client.discover.side_effect = RuntimeError("sentinel-api-key")
    if mode == "timeout":
        client.discover.side_effect = TimeoutError()
    if mode == "answer":
        service.settings.max_input_bytes = 20000
    if mode == "answer":
        # Final serialization can exceed the input bound even after a bounded model turn.
        from test_agents import context

        from vehicle_platform.agents.schemas import Answer

        answer = Answer(
            answer="x" * 25000,
            confidence="low",
            findings=[],
            evidence=[],
            uncertainties=[],
            limitations=[],
            missing_evidence=[],
            context=context(fixture),
        )
        from unittest.mock import patch

        with patch(
            "vehicle_platform.agents.service.Orchestrator.execute", AsyncMock(return_value=answer)
        ):
            run = await service.start(UUID(fixture["vehicle"]["id"]), Ask(question="x"))
            await service.tasks[run.id]
    else:
        run = await service.start(UUID(fixture["vehicle"]["id"]), Ask(question="x"))
        await service.tasks[run.id]
    stored = await service.repository.get(run.vehicle_id, run.id)
    assert stored.status == "failed" and stored.result is None and stored.error_category == category
    assert events[-1].type == "run_failed" and not service.tasks and service.active == 0
    assert "sentinel-api-key" not in stored.model_dump_json()


async def test_service_admission_cancellation_and_shutdown(fixture, telemetry):
    service, client, _, _ = service_fixture(fixture, telemetry)
    vehicle = UUID(fixture["vehicle"]["id"])
    service.settings.enabled = False
    with pytest.raises(AgentError, match="agent_disabled"):
        await service.start(vehicle, Ask(question="x"))
    service.settings.enabled = True
    service.active = service.settings.max_concurrent_runs
    with pytest.raises(AgentError, match="concurrency_exhausted"):
        await service.start(vehicle, Ask(question="x"))
    service.active = 0
    service.streams = 10
    with pytest.raises(AgentError, match="stream_concurrency_exhausted"):
        await anext(service.stream(vehicle, uuid4()))
    service.streams = 0
    barrier = asyncio.Event()

    async def wait():
        await barrier.wait()
        return []

    client.discover.side_effect = wait
    run = await service.start(vehicle, Ask(question="x"))
    await asyncio.sleep(0.01)
    cancelled = await service.cancel(vehicle, run.id)
    assert cancelled.status == "cancelled" and not service.tasks
    again = await service.start(vehicle, Ask(question="x"))
    await asyncio.sleep(0.01)
    await service.close()
    assert (await service.repository.get(vehicle, again.id)).status == "cancelled"
    with pytest.raises(AgentError, match="invalid_follow_up"):
        await service.start(vehicle, Ask(question="x", previous_run_id=again.id))
    service.repository.create.side_effect = SQLAlchemyError("unavailable")
    with pytest.raises(AgentError, match="database_unavailable"):
        await service.start(vehicle, Ask(question="x"))
    assert service.active == 0


async def test_agent_routes_expose_public_versioned_lifecycle(fixture, telemetry):
    from fastapi import FastAPI

    from vehicle_platform.agents.routes import agent_router
    from vehicle_platform.api.errors import register_errors

    service, _, _, _ = service_fixture(fixture, telemetry)
    service.repository.recent = AsyncMock(return_value=[])
    service.repository.calls = AsyncMock(return_value=[])
    app = FastAPI()
    app.include_router(agent_router(service))
    register_errors(app, telemetry)
    vehicle = fixture["vehicle"]["id"]
    path = f"/api/v1/vehicles/{vehicle}/agent-runs"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as api:
        created = await api.post(path, json={"question": "Qual causa?"})
        assert created.status_code == 202
        identifier = created.json()["id"]
        stream = await api.get(f"{path}/{identifier}/stream")
        assert "event: run_completed" in stream.text and '"schema_version":"1.0"' in stream.text
        assert (await api.get(f"{path}/{identifier}")).json()["status"] == "completed"
        assert (await api.get(f"{path}/{identifier}/audit")).json()["evidence"]
        assert (await api.get(f"{path}/{identifier}/events")).json()
        assert (await api.get(path)).json() == []
        assert (await api.get(path + "?limit=21")).status_code == 422
        assert (await api.post(f"{path}/{identifier}/cancel")).json()["status"] == "completed"
        assert (await api.get(f"{path}/{uuid4()}/stream")).status_code == 404
        service.settings.enabled = False
        assert (await api.post(path, json={"question": "x"})).status_code == 503
    await service.close()


@pytest.mark.parametrize(
    "question,missing",
    [
        ("O que diz o manual técnico BMW?", ["technical_documentation"]),
        ("Qual o sinal indisponível de timing?", ["signal_or_measurement"]),
        ("Mudou antes e depois da configuração?", ["comparable_history"]),
        ("Qual a causa mecânica exata?", ["mechanical_cause"]),
        ("Execute flash da ECU", []),
    ],
)
async def test_deterministic_missing_categories_match_the_question(question, missing):
    turn = await DeterministicProvider().turn(
        ModelInput(
            question=question,
            tools=[],
            context={"vehicle_id": str(uuid4()), "sessions": []},
            evidence=[],
            messages=[],
        )
    )
    assert turn.draft is not None and turn.draft.missing_evidence == missing
    assert all(c.classification == "INSUFFICIENT_EVIDENCE" for c in turn.draft.claims)
