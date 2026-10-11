"""Phase 7B optimistic SQL boundary; disposable PostgreSQL tests cover execution."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from vehicle_platform.acquisition.adapters import SyntheticLiveAdapter
from vehicle_platform.agents.investigation.domain import (
    Approval,
    InvestigationPlan,
    InvestigationStatus,
    Resolution,
    SignalNeed,
    SignalRole,
)
from vehicle_platform.agents.investigation.planning import plan_recipe
from vehicle_platform.agents.investigation.repository import InvestigationRepository
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import AgentRun


@pytest.fixture
def storage():
    db = MagicMock()
    db.execute, db.scalar, db.commit = AsyncMock(), AsyncMock(), AsyncMock()

    @asynccontextmanager
    async def session():
        yield db

    agents = MagicMock()
    agents.session = session
    return InvestigationRepository(agents), db


def item(status: InvestigationStatus = InvestigationStatus.DRAFT) -> InvestigationPlan:
    return InvestigationPlan(
        id=uuid4(),
        vehicle_id=uuid4(),
        agent_run_id=uuid4(),
        question="Why did the vehicle slow down?",
        goal="Compare measured conditions across sessions",
        status=status,
    )


def result_with(value=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


async def test_create_get_recent_update_and_replay(storage):
    repo, db = storage
    plan = item()
    db.execute.return_value = result_with(plan.id)
    assert await repo.create(plan) == plan
    assert db.commit.await_count == 1
    db.scalar.return_value = plan.model_dump(mode="json")
    assert await repo.get(plan.vehicle_id, plan.id) == plan
    with pytest.raises(AgentError, match="investigation_not_found"):
        db.scalar.return_value = None
        await repo.get(plan.vehicle_id, uuid4())
    db.scalar.return_value = plan.model_dump(mode="json")
    rows = MagicMock()
    rows.scalars.return_value.all.return_value = [plan.model_dump(mode="json")]
    db.execute.return_value = rows
    assert await repo.recent(plan.vehicle_id, 1) == [plan]
    with pytest.raises(AgentError, match="invalid_limit"):
        await repo.recent(plan.vehicle_id, 21)
    db.execute.return_value = result_with(plan.id)
    plan.move(InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED)
    updated = await repo.update(plan, 1, "evidence_gap_identified")
    assert updated.version == 2
    assert db.commit.await_count == 2
    event_row = {
        "investigation_id": str(plan.id),
        "sequence": 1,
        "type": "investigation_created",
        "status": "DRAFT",
    }
    db.scalar.return_value = updated.model_dump(mode="json")
    rows.scalars.return_value.all.return_value = [event_row]
    db.execute.return_value = rows
    events = await repo.events(plan.vehicle_id, plan.id)
    assert len(events) == 1 and events[0].type == "investigation_created"
    with pytest.raises(AgentError, match="invalid_cursor"):
        await repo.events(plan.vehicle_id, plan.id, 101)


async def test_create_conflict_and_stale_update_fail_closed(storage):
    repo, db = storage
    plan = item()
    db.execute.return_value = result_with(None)
    db.scalar.return_value = plan.model_dump(mode="json")
    assert await repo.create(plan) == plan
    db.scalar.return_value = None
    with pytest.raises(AgentError, match="invalid_investigation_run"):
        await repo.create(plan)
    db.execute.return_value = result_with(None)
    with pytest.raises(AgentError, match="stale_investigation_version"):
        await repo.update(plan, 1, "stale")
    with pytest.raises(AgentError, match="investigation_budget_exhausted"):
        await repo.update(plan, 100, "over-budget")


async def approved_plan() -> InvestigationPlan:
    plan = item(InvestigationStatus.ACQUISITION_READY)
    source = await SyntheticLiveAdapter(samples=1).capabilities()
    recipe = plan_recipe(
        [
            SignalNeed(
                id=uuid4(),
                role=SignalRole.ENGINE_SPEED,
                required=True,
                resolution=Resolution.MEDIUM,
                gap_ids=[uuid4()],
            )
        ],
        source,
    ).reference
    assert recipe is not None
    plan.recipe = recipe
    plan.configuration_id = uuid4()
    plan.source_adapter = "synthetic"
    plan.source_id = "fixture-source"
    plan.approval = Approval(
        status="APPROVED",
        recipe_hash=recipe.configuration_hash,
        approved_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    return InvestigationPlan.model_validate(plan.model_dump())


async def test_session_link_context_guards_and_idempotence(storage):
    repo, db = storage
    plan = await approved_plan()
    session_id = uuid4()
    db.scalar.return_value = plan.model_dump(mode="json")
    with pytest.raises(AgentError, match="stale_investigation_version"):
        await repo.link_session(plan.vehicle_id, plan.id, session_id, 99)
    with pytest.raises(AgentError, match="investigation_not_found"):
        db.scalar.return_value = None
        await repo.link_session(plan.vehicle_id, plan.id, session_id, plan.version)
    db.scalar.return_value = plan.model_dump(mode="json")
    acquisition = {
        "vehicle_id": plan.vehicle_id,
        "configuration_id": plan.configuration_id,
        "source_reference": plan.source_id,
        "adapter": plan.source_adapter,
        "session_status": "completed",
        "state": "completed",
        "started_at": datetime.now(UTC),
        "recipe_key": plan.recipe.key,
        "recipe_version": plan.recipe.version,
        "recipe_configuration_hash": plan.recipe.configuration_hash,
    }
    row = MagicMock()
    row.mappings.return_value.one_or_none.return_value = acquisition
    db.execute.return_value = row
    linked = await repo.link_session(plan.vehicle_id, plan.id, session_id, plan.version)
    assert linked.status is InvestigationStatus.DATA_RECEIVED
    assert linked.linked_session_ids == [session_id] and linked.cycle_count == 1
    assert db.commit.await_count == 1
    db.scalar.return_value = linked.model_dump(mode="json")
    again = await repo.link_session(plan.vehicle_id, plan.id, session_id, 1)
    assert again == linked and db.commit.await_count == 1
    db.scalar.return_value = plan.model_dump(mode="json")
    row.mappings.return_value.one_or_none.return_value = acquisition | {"vehicle_id": uuid4()}
    with pytest.raises(AgentError, match="incompatible_investigation_session"):
        await repo.link_session(plan.vehicle_id, plan.id, uuid4(), plan.version)


async def test_claim_reanalysis_is_atomic_and_unique(storage):
    repo, db = storage
    plan = await approved_plan()
    plan.status = InvestigationStatus.DATA_RECEIVED
    plan.linked_session_ids = [uuid4()]
    plan.cycle_count = 1
    run = AgentRun(
        id=uuid4(),
        vehicle_id=plan.vehicle_id,
        user_question=plan.question,
        status="running",
        provider="deterministic",
        model="scripted-v1",
        agent_version="phase7a-v1",
        prompt_version="grounded-v1",
        started_at=datetime.now(UTC),
    )
    db.scalar.return_value = plan.model_dump(mode="json")
    claimed = await repo.claim_reanalysis(plan.vehicle_id, plan.id, run)
    assert claimed.status is InvestigationStatus.REANALYZING
    assert claimed.reanalysis_run_id == run.id
    assert db.commit.await_count == 1
    db.scalar.return_value = claimed.model_dump(mode="json")
    assert await repo.claim_reanalysis(plan.vehicle_id, plan.id, run) == claimed
    assert db.commit.await_count == 1
    db.scalar.return_value = plan.model_dump(mode="json")
    run.user_question = "Different question"
    with pytest.raises(AgentError, match="invalid_reanalysis_state"):
        await repo.claim_reanalysis(plan.vehicle_id, plan.id, run)
