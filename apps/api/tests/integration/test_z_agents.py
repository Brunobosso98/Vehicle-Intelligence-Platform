"""Agent-owned persistence over disposable TimescaleDB and actual MCP protocol."""

import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from mcp import Client
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.mcp_client import MCPClient
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import AgentRun, ToolCall
from vehicle_platform.agents.scripted_provider import DeterministicProvider, ScriptedProvider
from vehicle_platform.core.config import Settings
from vehicle_platform.main import create_app
from vehicle_platform.mcp.adapter import Adapter
from vehicle_platform.mcp.config import MCPSettings
from vehicle_platform.mcp.database import ReadOnlyDatabase
from vehicle_platform.mcp.server import create_server

pytestmark = pytest.mark.integration
API = Path(__file__).resolve().parents[2]


@pytest.fixture
def url():
    value = os.environ.get("TEST_DATABASE_URL", "")
    if not value.rsplit("/", 1)[-1].startswith("vehicle_test"):
        pytest.fail("Agent integration requires disposable vehicle_test* database")
    return value


async def test_parent_migration_preserves_phase6(url):
    import asyncio

    engine = create_async_engine(url)
    async with engine.connect() as db:
        original = await db.scalar(text("SELECT count(*) FROM vehicles"))
    for command, target in (("downgrade", "0008"), ("upgrade", "head")):
        child = await asyncio.create_subprocess_exec(
            str(API / ".venv/bin/alembic"),
            command,
            target,
            cwd=API,
            env=os.environ | {"DATABASE_URL": url},
        )
        assert await child.wait() == 0
        async with engine.connect() as db:
            assert await db.scalar(text("SELECT count(*) FROM vehicles")) == original
            assert (
                await db.scalar(
                    text(
                        "SELECT count(*) FROM timescaledb_information.hypertables "
                        "WHERE hypertable_name='telemetry_samples'"
                    )
                )
                == 1
            )
            agent = await db.scalar(text("SELECT to_regclass('agent_runs')"))
            assert (agent is None) == (command == "downgrade")
    await engine.dispose()


async def test_real_database_agent_lifecycle_failure_recovery_and_audit(url):
    settings = Settings(database_url=url, environment="test")
    app = create_app(settings)
    service = app.state.agent_service
    service.settings = AgentSettings(enabled=False, provider="deterministic")
    service.settings.enabled = True  # In-process authenticated transport requires no network token.
    service.provider_factory = DeterministicProvider
    reader = ReadOnlyDatabase(settings)

    @asynccontextmanager
    async def connection():
        async with Client(
            create_server(
                Adapter(reader, settings, app.state.telemetry), app.state.telemetry, MCPSettings()
            )
        ) as client:
            yield MCPClient(client)

    service.client_factory = connection
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api,
    ):
        vehicle = (
            await api.post(
                "/api/v1/vehicles",
                json={"manufacturer": "BMW", "model": "agent-integration", "engine_code": "N55"},
            )
        ).json()["id"]
        other = (
            await api.post(
                "/api/v1/vehicles", json={"manufacturer": "BMW", "model": "isolated-agent"}
            )
        ).json()["id"]
        path = f"/api/v1/vehicles/{vehicle}/agent-runs"
        created = await api.post(path, json={"question": "Qual a causa mecânica exata?"})
        assert created.status_code == 202
        identifier = created.json()["id"]
        stream = await api.get(f"{path}/{identifier}/stream")
        assert "event: run_completed" in stream.text
        run = (await api.get(f"{path}/{identifier}")).json()
        assert run["status"] == "completed" and run["result"]["confidence"] == "low"
        assert run["usage"]["total_tokens"] == 0 and run["usage"]["estimated_cost"] is None
        audit = (await api.get(f"{path}/{identifier}/audit")).json()
        assert len(audit["tool_calls"]) == 4 and audit["evidence"]
        assert all(
            c["status"] == "completed" and c["argument_hash"] and c["mcp_request_id"]
            for c in audit["tool_calls"]
        )
        assert all(
            e["run_id"] == identifier and e["vehicle_id"] == vehicle for e in audit["evidence"]
        )
        assert all(
            e["tool_call_id"] in {c["id"] for c in audit["tool_calls"]} for e in audit["evidence"]
        )
        assert (
            await api.get(f"/api/v1/vehicles/{other}/agent-runs/{identifier}")
        ).status_code == 404
        assert (await api.get(path + "?limit=0")).status_code == 422
        assert (await api.get(f"{path}/{identifier}/events?after=400")).json() == []
        sequence = (await api.get(f"{path}/{identifier}/events")).json()
        assert sequence[-1]["type"] == "run_completed"
        assert [e["sequence"] for e in sequence] == list(range(1, len(sequence) + 1))

        service.provider_factory = lambda: ScriptedProvider([AgentError("provider_authentication")])
        failed = (await api.post(path, json={"question": "Como está?"})).json()["id"]
        failure_stream = await api.get(f"{path}/{failed}/stream")
        failed_run = (await api.get(f"{path}/{failed}")).json()
        assert failed_run["status"] == "failed" and failed_run["result"] is None
        assert failed_run["error_category"] == "provider_authentication"
        assert "event: run_failed" in failure_stream.text
        assert (await api.get(f"{path}/{failed}/audit")).json()["evidence"]
        service.provider_factory = DeterministicProvider
        recovered = (
            await api.post(path, json={"question": "Qual a causa?", "previous_run_id": identifier})
        ).json()["id"]
        await api.get(f"{path}/{recovered}/stream")
        assert (await api.get(f"{path}/{recovered}")).json()["status"] == "completed"
        assert (
            await api.post(
                f"/api/v1/vehicles/{other}/agent-runs",
                json={"question": "follow up", "previous_run_id": identifier},
            )
        ).status_code == 404
        assert len((await api.get(path + "?limit=2")).json()) == 2
        persisted = await service.repository.get(UUID(vehicle), UUID(identifier))
        assert persisted.result.context.vehicle["engine_code"] == "N55"
        assert persisted.evidence == persisted.result.evidence
        interrupted = AgentRun(
            id=uuid4(),
            vehicle_id=UUID(vehicle),
            user_question="controlled interruption",
            status="running",
            provider="deterministic",
            model="test",
            agent_version="phase7a-v1",
            prompt_version="grounded-v1",
            started_at=datetime.now(UTC) - timedelta(seconds=200),
        )
        await service.repository.create(interrupted)
        await service.repository.audit(
            ToolCall(
                id=uuid4(),
                run_id=interrupted.id,
                tool_name="get_vehicle",
                argument_hash="fixture",
                started_at=interrupted.started_at,
            )
        )
        reconciled = (await api.get(f"{path}/{interrupted.id}")).json()
        assert reconciled["status"] == "failed" and reconciled["result"] is None
        assert reconciled["error_category"] == "execution_interrupted"
        interrupted_audit = (await api.get(f"{path}/{interrupted.id}/audit")).json()
        assert interrupted_audit["tool_calls"][0]["status"] == "failed"
        assert interrupted_audit["tool_calls"][0]["completed_at"]
        interrupted_events = (await api.get(f"{path}/{interrupted.id}/events")).json()
        assert interrupted_events[0]["type"] == "run_failed"
        assert len((await api.get(f"{path}/{interrupted.id}/events")).json()) == 1
        metrics = (await api.get("/metrics")).text
        assert "agent_runs_total" in metrics and "agent_run_errors_total" in metrics
    await reader.close()
