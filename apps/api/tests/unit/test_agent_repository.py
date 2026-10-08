"""Agent repository SQL/serialization boundaries; real transactions are tested separately."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError
from test_agents import make_run

from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.repository import AgentRepository
from vehicle_platform.agents.schemas import StreamEvent, ToolCall


@pytest.fixture
def storage():
    database = MagicMock()
    db = MagicMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    db.execute, db.scalar, db.commit = AsyncMock(), AsyncMock(), AsyncMock()
    connection = AsyncMock()
    connection.get_raw_connection.return_value = MagicMock()
    db.connection = AsyncMock(return_value=connection)
    database.session.return_value = db
    return AgentRepository(database), db


def rows(db, values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    db.execute.return_value = result


async def test_missing_driver_fails_closed(storage):
    repo, db = storage
    db.connection.return_value.get_raw_connection.return_value.driver_connection = None
    with pytest.raises(AgentError, match="database_unavailable"):
        await repo.create(make_run(uuid4()))


async def test_watchdog_bounds_unresponsive_cancellation_cleanup(storage, monkeypatch):
    repo, db = storage
    released = asyncio.Event()
    driver = db.connection.return_value.get_raw_connection.return_value.driver_connection
    driver.terminate.side_effect = released.set
    monkeypatch.setattr("vehicle_platform.agents.repository.DATABASE_TIMEOUT", 0.01)

    async def blocked(*args, **kwargs):
        await asyncio.Event().wait()

    async def cleanup(*args):
        await released.wait()
        return False

    db.execute.side_effect = blocked
    db.__aexit__.side_effect = cleanup
    async with asyncio.timeout(0.3):
        with pytest.raises(AgentError, match="database_unavailable"):
            await repo.create(make_run(uuid4()))
    driver.terminate.assert_called_once()


async def test_repository_run_audit_and_stream_serialization(storage):
    repo, db = storage
    run = make_run(uuid4())
    await repo.create(run)
    assert str(db.execute.call_args.args[0]).startswith("INSERT INTO agent_runs")
    assert db.execute.call_args.args[1]["snapshot"] == run.model_dump_json()
    await repo.save(run)
    assert "status='running'" in str(db.execute.call_args.args[0])
    db.scalar.return_value = run.model_dump(mode="json")
    assert await repo.get(run.vehicle_id, run.id) == run
    repo.reconcile = AsyncMock()
    rows(db, [run.model_dump(mode="json")])
    assert await repo.recent(run.vehicle_id, 1) == [run]
    assert "LIMIT :limit" in str(db.execute.call_args.args[0])
    call = ToolCall(
        id=uuid4(),
        run_id=run.id,
        tool_name="get_vehicle",
        started_at=run.started_at,
        argument_hash="a" * 64,
    )
    await repo.audit(call)
    assert "ON CONFLICT(id)" in str(db.execute.call_args.args[0])
    rows(db, [call.model_dump(mode="json")])
    assert await repo.calls(run.vehicle_id, run.id) == [call]
    assert "LIMIT 32" in str(db.execute.call_args.args[0])
    event = StreamEvent(sequence=1, run_id=run.id, type="run_started", data={})
    await repo.event(event)
    rows(db, [event.model_dump(mode="json")])
    assert await repo.events(run.vehicle_id, run.id, 0) == [event]
    assert "LIMIT 400" in str(db.execute.call_args.args[0])
    run.status = "completed"
    completed = StreamEvent(sequence=2, run_id=run.id, type="run_completed", data={})
    commits = db.commit.await_count
    await repo.finish(run, completed)
    assert db.commit.await_count == commits + 1
    assert "UPDATE agent_runs" in str(db.execute.call_args_list[-2].args[0])
    assert "INSERT INTO agent_stream_events" in str(db.execute.call_args_list[-1].args[0])
    assert all("telemetry_samples" not in str(c.args[0]) for c in db.execute.call_args_list)


async def test_repository_not_found_and_bounds(storage):
    repo, db = storage
    db.scalar.return_value = None
    with pytest.raises(AgentError, match="run_not_found"):
        await repo.get(uuid4(), uuid4())
    for limit in (0, 21):
        with pytest.raises(AgentError, match="invalid_limit"):
            await repo.recent(uuid4(), limit)
    for sequence, data in ((401, {}), (1, {"oversized": "x" * 131073})):
        with pytest.raises(AgentError, match="stream_budget_exhausted"):
            await repo.event(
                StreamEvent(sequence=sequence, run_id=uuid4(), type="run_started", data=data)
            )


@pytest.mark.parametrize("last", [1, 400])
async def test_interrupted_run_reconciliation_is_bounded_and_terminal(storage, last):
    repo, db = storage
    run = make_run(uuid4())
    run.started_at = datetime.now(UTC) - timedelta(seconds=250)
    rows(db, [run.model_dump(mode="json")])
    db.scalar.return_value = last
    await repo.reconcile(run.vehicle_id)
    sql = [str(c.args[0]) for c in db.execute.call_args_list]
    assert "LIMIT 20 FOR UPDATE SKIP LOCKED" in sql[0]
    assert "UPDATE agent_runs SET status='failed'" in sql[1]
    assert "execution_interrupted" in sql[2]
    assert any("INSERT INTO agent_stream_events" in value for value in sql) == (last < 400)
    assert db.commit.await_count == 1


async def test_stale_retrieval_refreshes_reconciled_state(storage):
    repo, db = storage
    run = make_run(uuid4())
    run.started_at = datetime.now(UTC) - timedelta(seconds=250)
    failed = run.model_copy(update={"status": "failed", "error_category": "execution_interrupted"})
    db.scalar.side_effect = [run.model_dump(mode="json"), failed.model_dump(mode="json")]
    repo.reconcile = AsyncMock()
    assert (await repo.get(run.vehicle_id, run.id)).status == "failed"
    repo.reconcile.assert_awaited_once_with(run.vehicle_id)


@pytest.mark.parametrize(
    "error", [SQLAlchemyError("secret"), ConnectionError("secret"), TimeoutError()]
)
async def test_database_errors_are_normalized_and_session_closes(storage, error):
    repo, db = storage
    db.scalar.side_effect = error
    with pytest.raises(AgentError, match="database_unavailable"):
        await repo.get(uuid4(), uuid4())
    db.__aexit__.assert_awaited_once()
