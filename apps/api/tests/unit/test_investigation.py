import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr, ValidationError

from vehicle_platform.acquisition.adapters import SyntheticLiveAdapter
from vehicle_platform.acquisition.capabilities import (
    SourceCapabilitySnapshot,
    fresh,
    validated_report,
)
from vehicle_platform.acquisition.domain import DeviceCapabilities, Support
from vehicle_platform.acquisition.recipes import BY_KEY
from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.investigation.domain import (
    Approval,
    CapabilitySnapshot,
    EvidenceGap,
    Feasibility,
    GapStatus,
    GapType,
    Hypothesis,
    HypothesisCategory,
    HypothesisStatus,
    InvestigationError,
    InvestigationEvent,
    InvestigationPlan,
    InvestigationStatus,
    Resolution,
    SignalNeed,
    SignalRole,
)
from vehicle_platform.agents.investigation.existing import ExistingEvidence, search_existing
from vehicle_platform.agents.investigation.follow_up import (
    outcome,
    resolve_followup_gaps,
    update_hypotheses,
)
from vehicle_platform.agents.investigation.instrumentation import InvestigationInstrumentation
from vehicle_platform.agents.investigation.planning import plan_recipe
from vehicle_platform.agents.investigation.proposal import InvestigationProposal, materialize
from vehicle_platform.agents.investigation.routes import investigation_router
from vehicle_platform.agents.investigation.service import InvestigationService, investigable
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import (
    AgentRun,
    Answer,
    Classification,
    Evidence,
    Fact,
    Finding,
    ToolCall,
    VehicleContext,
)
from vehicle_platform.agents.scripted_provider import DeterministicProvider
from vehicle_platform.api.domain_contracts import PreflightRequest


def plan() -> InvestigationPlan:
    return InvestigationPlan(
        id=uuid4(),
        agent_run_id=uuid4(),
        vehicle_id=uuid4(),
        question="Why did performance change?",
        goal="Discriminate observed thermal and fueling associations",
    )


def need(role: SignalRole, *, required: bool = True) -> SignalNeed:
    return SignalNeed(
        id=uuid4(),
        role=role,
        required=required,
        resolution=Resolution.MEDIUM,
        gap_ids=[uuid4()],
    )


def test_lifecycle_rejects_skip_and_terminal_reentry() -> None:
    item = plan()
    with pytest.raises(InvestigationError, match="invalid investigation transition"):
        item.move(InvestigationStatus.APPROVED)
    item.move(InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED)
    item.move(InvestigationStatus.INCONCLUSIVE)
    assert [transition.status for transition in item.transitions] == [
        InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED,
        InvestigationStatus.INCONCLUSIVE,
    ]
    with pytest.raises(InvestigationError):
        item.move(InvestigationStatus.DRAFT)


def test_local_references_and_closed_signal_taxonomy() -> None:
    item = plan()
    gap = EvidenceGap(
        id=uuid4(),
        category=GapType.SIGNAL_OR_MEASUREMENT,
        description="Intake temperature missing from repeated load windows",
        why_it_matters="Separates thermal association from other variation",
        hypothesis_ids=[uuid4()],
    )
    hypothesis = Hypothesis(
        id=uuid4(),
        category=HypothesisCategory.THERMAL,
        statement="Thermal conditions may be associated with the measured change",
        discriminating_goal="Compare temperature and duration across compatible windows",
        missing_gap_ids=[gap.id],
    )
    item.hypotheses = [hypothesis]
    item.gaps = [gap]
    with pytest.raises(ValidationError, match="unknown investigation artifact"):
        InvestigationPlan.model_validate(item.model_dump())
    with pytest.raises(ValidationError):
        SignalNeed.model_validate({**need(SignalRole.TIMING).model_dump(), "role": "write_ecu"})


async def test_phase4_recipe_and_sampling_planner_are_used() -> None:
    adapter = SyntheticLiveAdapter(samples=1)
    source = await adapter.capabilities()
    thermal = need(SignalRole.INTAKE_TEMPERATURE)
    fueling = need(SignalRole.HIGH_FUEL_PRESSURE)
    proposed = plan_recipe([thermal, fueling], source)
    assert proposed.recipe is BY_KEY["performance-pull"]
    assert proposed.reference is not None
    assert proposed.reference.configuration_hash == proposed.recipe.configuration_hash
    assert proposed.reference.feasibility is Feasibility.FEASIBLE
    assert proposed.preflight is not None
    assert proposed.preflight.sampling_plan


def test_source_support_differs_from_session_recording() -> None:
    source = DeviceCapabilities(
        "trusted-test-source", {"engine.boost_pressure": Support.SUPPORTED}, 70
    )
    proposed = plan_recipe([need(SignalRole.BOOST)], source, recorded_signals=set())
    boost = proposed.needs[0]
    assert boost.source_support.value == "AVAILABLE"
    assert boost.recorded_in_session is False
    assert proposed.reference is not None
    assert proposed.reference.feasibility is Feasibility.NOT_FEASIBLE


def test_unverified_and_uncollectable_needs_never_become_ready() -> None:
    thermal = plan_recipe([need(SignalRole.INTAKE_TEMPERATURE)], None)
    assert thermal.reference is not None
    assert thermal.reference.feasibility is Feasibility.NOT_FEASIBLE
    timing = plan_recipe([need(SignalRole.TIMING)], None)
    assert timing.recipe is None
    assert timing.needs[0].canonical_signal == "engine.ignition_timing"
    assert timing.needs[0].availability.value == "UNAVAILABLE"


def test_source_preflight_accepts_only_read_only_adapter_channels() -> None:
    allowed = PreflightRequest(
        adapter="elm327-standard-read-only-v1",
        signals={"engine.rpm": "supported", "vehicle.speed": "unsupported"},
        maximum_requests_per_second=8,
    )
    assert validated_report("obd", allowed).signals["engine.rpm"] is Support.SUPPORTED
    with pytest.raises(ValueError, match="standard adapter"):
        validated_report(
            "obd", allowed.model_copy(update={"signals": {"engine.boost_pressure": "supported"}})
        )
    with pytest.raises(ValueError, match="standard adapter"):
        validated_report("obd", allowed.model_copy(update={"adapter": "write-capable"}))
    with pytest.raises(ValueError, match="standard adapter"):
        validated_report("obd", allowed.model_copy(update={"maximum_requests_per_second": 100}))
    with pytest.raises(ValueError, match="source mismatch"):
        validated_report("replay", allowed)


def test_source_snapshot_freshness_is_bounded() -> None:
    from datetime import timedelta

    assert fresh(datetime.now(UTC))
    assert not fresh(datetime.now(UTC) - timedelta(days=2))
    assert not fresh(datetime.now(UTC) + timedelta(days=1))


async def test_investigation_api_requires_operator_token() -> None:
    service = MagicMock()
    service.agents.settings.investigation_token = SecretStr("operator-test-secret")
    app = FastAPI()
    app.include_router(investigation_router(service))
    vehicle_id = uuid4()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        path = f"/api/v1/vehicles/{vehicle_id}/investigations"
        assert (await client.get(path)).status_code == 401
        assert (
            await client.get(path, headers={"X-Investigation-Token": "wrong"})
        ).status_code == 401
        assert (
            await client.post(
                path + "/source-preflight", headers={"X-Investigation-Token": "wrong"}, json={}
            )
        ).status_code == 401


def test_recipe_change_invalidates_exact_approval() -> None:
    source = DeviceCapabilities(
        "trusted-test-source",
        {item.signal: Support.SUPPORTED for item in BY_KEY["performance-pull"].requirements},
        70,
    )
    first = plan_recipe([need(SignalRole.BOOST)], source).reference
    second = plan_recipe([need(SignalRole.HIGH_FUEL_PRESSURE)], source).reference
    assert first is not None and second is not None
    item = plan()
    item.replace_recipe(first)
    for status in (
        InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED,
        InvestigationStatus.CAPABILITIES_RESOLVED,
        InvestigationStatus.RECIPE_PROPOSED,
        InvestigationStatus.AWAITING_APPROVAL,
    ):
        item.move(status)
    item.approval = Approval(status="APPROVED", recipe_hash=first.configuration_hash)
    item.move(InvestigationStatus.APPROVED)
    item.replace_recipe(second)
    assert item.status is InvestigationStatus.AWAITING_APPROVAL
    assert item.approval.status == "INVALIDATED"
    assert item.approval.recipe_hash is None
    item.approval = Approval(status="APPROVED", recipe_hash=second.configuration_hash)
    item.move(InvestigationStatus.APPROVED)
    item.move(InvestigationStatus.ACQUISITION_READY)
    item.move(InvestigationStatus.AWAITING_DATA)
    with pytest.raises(InvestigationError, match="after acquisition linkage"):
        item.replace_recipe(first)


class MemoryInvestigations:
    def __init__(self) -> None:
        self.value: InvestigationPlan | None = None

    async def create(self, item: InvestigationPlan) -> InvestigationPlan:
        self.value = item.model_copy(deep=True)
        return item.model_copy(deep=True)

    async def get(self, vehicle_id, investigation_id) -> InvestigationPlan:
        assert self.value is not None
        assert self.value.vehicle_id == vehicle_id and self.value.id == investigation_id
        return self.value.model_copy(deep=True)

    async def update(self, item: InvestigationPlan, version: int, event: str) -> InvestigationPlan:
        assert self.value is not None and self.value.version == version
        self.value = item.model_copy(update={"version": version + 1}, deep=True)
        return self.value.model_copy(deep=True)


def insufficient_run(question: str) -> AgentRun:
    vehicle_id, run_id = uuid4(), uuid4()
    context = VehicleContext(vehicle_id=vehicle_id, as_of=datetime.now(UTC))
    finding = Finding(
        classification=Classification.INSUFFICIENT_EVIDENCE,
        template="insufficient_evidence",
        bindings=[],
        evidence_ids=[],
        statement="Current evidence is insufficient",
    )
    answer = Answer(
        answer=finding.statement,
        confidence="low",
        findings=[finding],
        evidence=[],
        uncertainties=[],
        limitations=[],
        missing_evidence=["signal_or_measurement"],
        context=context,
    )
    return AgentRun(
        id=run_id,
        vehicle_id=vehicle_id,
        user_question=question,
        status="completed",
        provider="deterministic",
        model="scripted-v1",
        agent_version="phase7a-v1",
        prompt_version="grounded-v1",
        started_at=datetime.now(UTC),
        result=answer,
    )


async def test_service_creates_plan_and_approval_requires_exact_version() -> None:
    run = insufficient_run("Why did the third pull get slower with timing missing?")
    agent = MagicMock()
    agent.settings = AgentSettings(
        enabled=True,
        provider="deterministic",
        mcp_token=SecretStr("local-test-mcp"),
        investigation_token=SecretStr("local-test-operator"),
    )
    agent.repository.get = AsyncMock(return_value=run)
    agent.provider_factory = DeterministicProvider
    agent.redact.side_effect = lambda value: value

    @asynccontextmanager
    async def client():
        yield MagicMock()

    agent.client_factory = client
    repository = MemoryInvestigations()
    service = InvestigationService(agent, repository, MagicMock())
    created = await service.create(run.vehicle_id, run.id, "synthetic", "fixture")
    assert created.status is InvestigationStatus.AWAITING_APPROVAL
    assert len(created.hypotheses) == 3
    assert created.recipe is not None
    assert created.recipe.key == "performance-pull"
    assert created.recipe.feasibility is Feasibility.FEASIBLE_WITH_DEGRADATION
    assert any(
        item.role is SignalRole.TIMING and item.availability.value == "UNAVAILABLE"
        for item in created.signal_needs
    )
    with pytest.raises(AgentError, match="stale_investigation_version"):
        await service.approve(
            run.vehicle_id,
            created.id,
            created.version - 1,
            created.recipe.configuration_hash,
            "operator",
        )
    with pytest.raises(AgentError, match="stale_recipe_hash"):
        await service.approve(run.vehicle_id, created.id, created.version, "0" * 64, "operator")
    approved = await service.approve(
        run.vehicle_id, created.id, created.version, created.recipe.configuration_hash, "operator"
    )
    assert approved.status is InvestigationStatus.ACQUISITION_READY
    assert approved.approval.recipe_hash == created.recipe.configuration_hash
    repeated = await service.approve(
        run.vehicle_id, created.id, created.version, created.recipe.configuration_hash, "operator"
    )
    assert repeated.version == approved.version


def test_follow_up_support_and_weakening_require_new_grounded_evidence() -> None:
    item = plan()
    session_id, followup_id = uuid4(), uuid4()
    item.reanalysis_run_id = followup_id
    item.linked_session_ids = [session_id]
    item.hypotheses = [
        Hypothesis(
            id=uuid4(),
            category=HypothesisCategory.THERMAL,
            statement="Thermal conditions may explain the measured change",
            discriminating_goal="Compare temperatures across compatible pulls",
        )
    ]
    run = insufficient_run("Why is temperature associated with slower pulls?")
    run.id, run.vehicle_id = followup_id, item.vehicle_id
    assert run.result is not None
    run.result.context.vehicle_id = item.vehicle_id
    call = ToolCall(
        id=uuid4(),
        run_id=followup_id,
        tool_name="list_session_events",
        started_at=datetime.now(UTC),
        status="completed",
        argument_hash="a" * 64,
    )
    event = Evidence(
        id=uuid4(),
        run_id=followup_id,
        vehicle_id=item.vehicle_id,
        evidence_type="event",
        source_tool="list_session_events",
        tool_call_id=call.id,
        source_fingerprint="f" * 64,
        session_id=session_id,
        summary="Measured intake temperature rise",
        facts=[Fact(path="/event_type", value="iat_rise")],
    )
    run.evidence = [event]
    supported = update_hypotheses(item, run, [call])
    assert supported[0].status is HypothesisStatus.SUPPORTED
    assert supported[0].evidence_for == [event.id]
    item.hypotheses = supported
    assert outcome(item, run).classification == "ASSOCIATION"

    quality = Evidence(
        id=uuid4(),
        run_id=followup_id,
        vehicle_id=item.vehicle_id,
        evidence_type="capabilities",
        source_tool="get_session_capabilities",
        tool_call_id=uuid4(),
        source_fingerprint="b" * 64,
        session_id=session_id,
        summary="Complete temperature channel",
    )
    run.result.context.capabilities[str(session_id)] = {
        "signal_quality": [
            {"signal": "engine.intake_air_temperature", "actual_hz": 5, "missing_ratio": 0.01}
        ]
    }
    run.evidence = [quality]
    weakened = update_hypotheses(item, run, [call])
    assert weakened[0].status is HypothesisStatus.WEAKENED
    assert weakened[0].evidence_against == [quality.id]
    run.evidence = [quality.model_copy(update={"warnings": ["truncated source"]})]
    unresolved = update_hypotheses(item, run, [call])
    assert unresolved[0].status is HypothesisStatus.UNRESOLVED
    assert (
        outcome(item.model_copy(update={"hypotheses": unresolved}), run).classification
        == "INCONCLUSIVE"
    )


def test_investigation_metrics_and_logs_have_bounded_fields() -> None:
    telemetry = MagicMock()
    telemetry.metrics.get_meter.return_value.create_counter.side_effect = lambda name: MagicMock(
        name=name
    )
    signals = InvestigationInstrumentation(telemetry)
    item = plan()
    for event in (
        "investigation_created",
        "evidence_gap_identified",
        "capability_resolution_completed",
        "recipe_proposed",
        "approved",
        "reanalysis_started",
    ):
        signals.transition(item, event)
    signals.investigations.add.assert_called_once_with(1)
    signals.approvals.add.assert_called_once_with(1)
    signals.reanalyses.add.assert_called_once_with(1)
    source = DeviceCapabilities(
        "fixture",
        {
            requirement.signal: Support.SUPPORTED
            for requirement in BY_KEY["performance-pull"].requirements
        },
        70,
    )
    recipe = plan_recipe([need(SignalRole.BOOST)], source).reference
    assert recipe is not None
    item.recipe = recipe
    signals.transition(item, "recipe_proposed")
    signals.feasible.add.assert_called_once_with(1)
    item.status = InvestigationStatus.COMPLETED
    signals.transition(item, "investigation_completed")
    item.status = InvestigationStatus.INCONCLUSIVE
    signals.transition(item, "investigation_inconclusive")
    item.status = InvestigationStatus.FAILED
    signals.transition(item, "investigation_failed")
    signals.completed.add.assert_called_once_with(1)
    signals.inconclusive.add.assert_called_once_with(1)
    signals.failures.add.assert_called_once_with(1)
    assert signals.duration.record.call_count == 3
    fields = telemetry.log.call_args.kwargs
    assert fields["investigation_id"] == str(item.id)
    assert "question" not in fields and "token" not in fields


def test_investigable_requires_grounded_material_gap() -> None:
    run = insufficient_run("Why is timing missing?")
    assert investigable(run)
    assert run.result is not None
    run.result.missing_evidence = ["mechanical_cause"]
    assert not investigable(run)
    run.result.missing_evidence = ["signal_or_measurement"]
    run.status = "running"
    assert not investigable(run)
    run.status = "completed"
    run.result = None
    assert not investigable(run)


def test_semantic_proposal_rejects_duplicate_and_unsafe_gap() -> None:
    good = {
        "hypotheses": [{"category": "THERMAL"}],
        "gaps": [
            {
                "category": "signal_or_measurement",
                "hypothesis_indexes": [0],
                "signal_roles": ["intake_temperature_behavior"],
            }
        ],
    }
    proposal = InvestigationProposal.model_validate(good)
    hypotheses, gaps, needs = materialize(proposal, insufficient_run("Why?"))
    assert len(hypotheses) == len(gaps) == len(needs) == 1
    assert needs[0].gap_ids == [gaps[0].id]
    assert hypotheses[0].missing_gap_ids == [gaps[0].id]
    with pytest.raises(ValidationError):
        InvestigationProposal.model_validate(good | {"hypotheses": good["hypotheses"] * 2})
    with pytest.raises(ValidationError):
        InvestigationProposal.model_validate(
            good
            | {
                "gaps": [
                    {
                        "category": "technical_documentation",
                        "hypothesis_indexes": [0],
                        "signal_roles": ["intake_temperature_behavior"],
                    }
                ]
            }
        )
    with pytest.raises(ValidationError):
        InvestigationProposal.model_validate(
            good | {"gaps": [{"category": "signal_or_measurement", "hypothesis_indexes": [1]}]}
        )


async def test_existing_search_respects_signal_quality_and_vehicle_context() -> None:
    run = insufficient_run("Why is timing missing?")
    assert run.result is not None
    session_id, configuration_id = uuid4(), uuid4()
    run.result.context.active_configuration_id = configuration_id
    run.result.context.sessions = [
        {
            "id": str(session_id),
            "status": "completed",
            "configuration_id": str(configuration_id),
            "temporal_configuration_valid": True,
        }
    ]
    signal_need = need(SignalRole.BOOST)
    gap = EvidenceGap(
        id=signal_need.gap_ids[0],
        category=GapType.SIGNAL_OR_MEASUREMENT,
        description="Boost is missing in compatible windows",
        why_it_matters="Separates observed airflow associations",
        signal_need_ids=[signal_need.id],
    )
    client = MagicMock()
    envelope = MagicMock()
    envelope.context = {"vehicle_id": str(run.vehicle_id)}
    envelope.data = {
        "available_signals": ["engine.boost_pressure"],
        "signal_quality": [
            {"signal": "engine.boost_pressure", "actual_hz": 8, "missing_ratio": 0.05}
        ],
    }
    client.call = AsyncMock(return_value=envelope)
    found = await search_existing(run, [gap], [signal_need], client)
    assert found.gaps[0].status is GapStatus.AVAILABLE_IN_EXISTING_DATA
    assert found.mcp_calls == 1
    envelope.data["signal_quality"][0]["missing_ratio"] = 0.9
    degraded = await search_existing(run, [gap], [signal_need], client)
    assert degraded.gaps[0].status is GapStatus.NEEDS_NEW_CAPTURE
    envelope.context = {"vehicle_id": str(uuid4())}
    with pytest.raises(AgentError, match="incompatible_context"):
        await search_existing(run, [gap], [signal_need], client)


async def test_reject_cancel_and_stale_version_are_persisted() -> None:
    agent = MagicMock()
    repository = MemoryInvestigations()
    service = InvestigationService(agent, repository, MagicMock())
    item = plan()
    source = DeviceCapabilities(
        "fixture",
        {
            requirement.signal: Support.SUPPORTED
            for requirement in BY_KEY["performance-pull"].requirements
        },
        70,
    )
    item.replace_recipe(plan_recipe([need(SignalRole.BOOST)], source).reference)
    item.move(InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED)
    item.move(InvestigationStatus.CAPABILITIES_RESOLVED)
    item.move(InvestigationStatus.RECIPE_PROPOSED)
    item.move(InvestigationStatus.AWAITING_APPROVAL)
    item = await repository.create(item)
    with pytest.raises(AgentError, match="stale_investigation_version"):
        await service.reject(item.vehicle_id, item.id, item.version + 1)
    rejected = await service.reject(item.vehicle_id, item.id, item.version)
    assert rejected.status is InvestigationStatus.REJECTED
    assert rejected.approval.status == "REJECTED"
    cancelled = plan()
    cancelled = await repository.create(cancelled)
    cancelled = await service.cancel(cancelled.vehicle_id, cancelled.id, cancelled.version)
    assert cancelled.status is InvestigationStatus.CANCELLED


async def test_create_rejects_invalid_identity_capacity_and_sufficient_answer() -> None:
    run = insufficient_run("Why is timing missing?")
    agents = MagicMock()
    agents.repository.get = AsyncMock(return_value=run)
    service = InvestigationService(agents, MemoryInvestigations(), MagicMock())
    with pytest.raises(AgentError, match="invalid_source_identity"):
        await service.create(run.vehicle_id, run.id, "synthetic", "")
    service.active = 4
    with pytest.raises(AgentError, match="investigation_concurrency_exhausted"):
        await service.create(run.vehicle_id, run.id, "synthetic", "source")
    service.active = 0
    assert run.result is not None
    run.result.missing_evidence = ["mechanical_cause"]
    with pytest.raises(AgentError, match="evidence_not_investigable"):
        await service.create(run.vehicle_id, run.id, "synthetic", "source")
    assert service.active == 0


async def test_refresh_rejects_stale_state_and_missing_source() -> None:
    repository = MemoryInvestigations()
    item = await repository.create(plan())
    agents = MagicMock()
    service = InvestigationService(agents, repository, MagicMock())
    with pytest.raises(AgentError, match="stale_investigation_version"):
        await service.refresh(item.vehicle_id, item.id, item.version + 1)
    with pytest.raises(AgentError, match="invalid_investigation_state"):
        await service.refresh(item.vehicle_id, item.id, item.version)
    item.move(InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED)
    item = await repository.update(item, item.version, "evidence_gap_identified")
    with pytest.raises(AgentError, match="invalid_source_identity"):
        await service.refresh(item.vehicle_id, item.id, item.version)


async def test_source_capability_policy_and_report_validation() -> None:
    agents = MagicMock()
    agents.settings.provider = "openai"
    source = MagicMock()
    service = InvestigationService(agents, MemoryInvestigations(), source)
    with pytest.raises(AgentError, match="synthetic_investigation_source_disabled"):
        await service._source_capabilities(uuid4(), None, "synthetic", "source")
    source.latest = AsyncMock(return_value=None)
    assert await service._source_capabilities(uuid4(), None, "obd", "source") is None
    source.register = AsyncMock(side_effect=ValueError("invalid"))
    report = PreflightRequest(
        adapter="elm327-standard-read-only-v1",
        signals={"engine.rpm": "supported"},
        maximum_requests_per_second=8,
    )
    with pytest.raises(AgentError, match="invalid_source_preflight"):
        await service.register_source(uuid4(), uuid4(), "obd", "source", report)


async def test_approval_rejects_stale_capability_and_unready_plan() -> None:
    repository = MemoryInvestigations()
    item = plan()
    source = DeviceCapabilities(
        "fixture",
        {
            requirement.signal: Support.SUPPORTED
            for requirement in BY_KEY["performance-pull"].requirements
        },
        70,
    )
    item.replace_recipe(plan_recipe([need(SignalRole.BOOST)], source).reference)
    assert item.recipe is not None
    item = await repository.create(item)
    service = InvestigationService(MagicMock(), repository, MagicMock())
    with pytest.raises(AgentError, match="stale_source_capabilities"):
        await service.approve(
            item.vehicle_id, item.id, item.version, item.recipe.configuration_hash, "operator"
        )
    item.capability_snapshot = CapabilitySnapshot(
        adapter="fixture",
        signals=source.signals,
        maximum_requests_per_second=70,
        observed_at=datetime.now(UTC),
    )
    item.source_adapter = "obd"
    item = await repository.update(item, item.version, "capability_resolution_completed")
    service._source_capabilities = AsyncMock(return_value=item.capability_snapshot)
    with pytest.raises(AgentError, match="invalid_investigation_state"):
        await service.approve(
            item.vehicle_id, item.id, item.version, item.recipe.configuration_hash, "operator"
        )


async def test_followup_reconciliation_handles_running_failed_and_stale_write() -> None:
    repository = MemoryInvestigations()
    item = plan()
    for status in (
        InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED,
        InvestigationStatus.CAPABILITIES_RESOLVED,
        InvestigationStatus.RECIPE_PROPOSED,
    ):
        item.move(status)
    item.status = InvestigationStatus.REANALYZING
    item.reanalysis_run_id = uuid4()
    item.linked_session_ids = [uuid4()]
    item = await repository.create(item)
    agents = MagicMock()
    run = insufficient_run("Why is timing missing?")
    run.id, run.vehicle_id = item.reanalysis_run_id, item.vehicle_id
    agents.repository.get = AsyncMock(return_value=run)
    service = InvestigationService(agents, repository, MagicMock())
    run.status = "running"
    assert (await service.complete_follow_up(item.vehicle_id, item.id)).version == item.version
    run.status = "failed"
    failed = await service.complete_follow_up(item.vehicle_id, item.id)
    assert failed.status is InvestigationStatus.FAILED
    assert (await service.complete_follow_up(item.vehicle_id, item.id)).version == failed.version


def test_followup_gap_resolution_requires_matching_clean_capability_evidence() -> None:
    item = plan()
    session_id = uuid4()
    item.linked_session_ids = [session_id]
    signal_need = need(SignalRole.BOOST)
    item.signal_needs = [signal_need]
    measurement = EvidenceGap(
        id=signal_need.gap_ids[0],
        category=GapType.SIGNAL_OR_MEASUREMENT,
        description="Measured boost unavailable in the old session",
        why_it_matters="Compare airflow behavior across pulls",
        signal_need_ids=[signal_need.id],
        status=GapStatus.NEEDS_NEW_CAPTURE,
    )
    quality = EvidenceGap(
        id=uuid4(),
        category=GapType.DATA_QUALITY,
        description="Sampling gaps obscure operating conditions",
        why_it_matters="Poor data can mimic vehicle behavior",
        status=GapStatus.NEEDS_NEW_CAPTURE,
    )
    history = EvidenceGap(
        id=uuid4(),
        category=GapType.COMPARABLE_HISTORY,
        description="Comparable history is currently absent",
        why_it_matters="A baseline is required for comparison",
        status=GapStatus.NEEDS_NEW_CAPTURE,
    )
    available = measurement.model_copy(
        update={"id": uuid4(), "status": GapStatus.AVAILABLE_IN_EXISTING_DATA}
    )
    item.gaps = [measurement, quality, history, available]
    run = insufficient_run("Why is boost missing?")
    run.id, run.vehicle_id = uuid4(), item.vehicle_id
    assert run.result is not None
    run.result.context.capabilities[str(session_id)] = {
        "signal_quality": [
            {"signal": "engine.boost_pressure", "actual_hz": 10, "missing_ratio": 0.01},
            {"signal": "engine.rpm", "actual_hz": 10, "missing_ratio": 0.01},
        ]
    }
    capability = Evidence(
        id=uuid4(),
        run_id=run.id,
        vehicle_id=item.vehicle_id,
        evidence_type="capabilities",
        source_tool="get_session_capabilities",
        tool_call_id=uuid4(),
        source_fingerprint="a" * 64,
        session_id=session_id,
        summary="Signals recorded with usable quality",
    )
    comparison = capability.model_copy(
        update={
            "id": uuid4(),
            "source_tool": "compare_pulls",
            "evidence_type": "comparison",
            "facts": [Fact(path="/comparison/sufficiency", value="sufficient")],
        }
    )
    run.evidence = [capability, comparison]
    resolved = resolve_followup_gaps(item, run)
    assert all(gap.status is GapStatus.RESOLVED for gap in resolved)
    assert resolved[0].resolution_source == "grounded_reanalysis_session_capabilities"
    assert resolved[1].resolution_source == "grounded_reanalysis_session_quality"
    assert resolved[2].resolution_source == "grounded_reanalysis_comparison"
    run.evidence = [capability.model_copy(update={"warnings": ["truncated"]})]
    degraded = resolve_followup_gaps(item, run)
    assert degraded[0].status is GapStatus.NEEDS_NEW_CAPTURE
    assert degraded[1].status is GapStatus.NEEDS_NEW_CAPTURE
    assert degraded[2].status is GapStatus.NEEDS_NEW_CAPTURE
    item.linked_session_ids = []
    with pytest.raises(AgentError, match="invalid_reanalysis_context"):
        resolve_followup_gaps(item, run)


def test_followup_rejects_cross_run_and_does_not_infer_causation() -> None:
    item = plan()
    run = insufficient_run("Why did performance change?")
    with pytest.raises(AgentError, match="invalid_reanalysis_context"):
        update_hypotheses(item, run, [])
    with pytest.raises(AgentError, match="invalid_reanalysis_context"):
        outcome(item, run.model_copy(update={"result": None}))
    item.vehicle_id = run.vehicle_id
    item.reanalysis_run_id = run.id
    item.linked_session_ids = [uuid4()]
    hypothesis = Hypothesis(
        id=uuid4(),
        category=HypothesisCategory.CONFIGURATION_ASSOCIATION,
        statement="Configuration may be associated with the change",
        discriminating_goal="Compare compatible before and after windows",
    )
    item.hypotheses = [hypothesis]
    updated = update_hypotheses(item, run, [])
    assert updated[0].status is HypothesisStatus.UNRESOLVED
    item.hypotheses = updated
    assert outcome(item, run).classification == "INCONCLUSIVE"


async def test_refresh_distinguishes_unknown_source_and_documentation_gap() -> None:
    repository = MemoryInvestigations()
    item = plan()
    item.source_adapter = "obd"
    item.source_id = "offline"
    signal_need = need(SignalRole.BOOST)
    item.signal_needs = [signal_need]
    item.gaps = [
        EvidenceGap(
            id=signal_need.gap_ids[0],
            category=GapType.SIGNAL_OR_MEASUREMENT,
            description="Boost measurements are absent",
            why_it_matters="Discriminates measured airflow behavior",
            signal_need_ids=[signal_need.id],
            status=GapStatus.NEEDS_NEW_CAPTURE,
        )
    ]
    item.move(InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED)
    item = await repository.create(item)
    source = MagicMock()
    source.latest = AsyncMock(return_value=None)
    service = InvestigationService(MagicMock(), repository, source)
    unresolved = await service.refresh(item.vehicle_id, item.id, item.version)
    assert unresolved.status is InvestigationStatus.CAPABILITIES_RESOLVED
    assert unresolved.signal_needs[0].source_support.value == "UNKNOWN"
    assert unresolved.recipe is not None
    assert unresolved.recipe.feasibility is Feasibility.NOT_FEASIBLE

    documentation = plan()
    documentation.source_adapter = "obd"
    documentation.source_id = "offline"
    documentation.gaps = [
        EvidenceGap(
            id=uuid4(),
            category=GapType.TECHNICAL_DOCUMENTATION,
            description="Factory specification is unavailable",
            why_it_matters="Telemetry cannot supply a documentary reference",
        )
    ]
    documentation.move(InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED)
    documentation = await repository.create(documentation)
    result = await service.refresh(
        documentation.vehicle_id, documentation.id, documentation.version
    )
    assert result.status is InvestigationStatus.INCONCLUSIVE
    assert result.recipe is None


def test_proposal_materialization_enforces_evidence_ownership_and_quality() -> None:
    run = insufficient_run("Why is boost missing?")
    evidence = Evidence(
        id=uuid4(),
        run_id=run.id,
        vehicle_id=run.vehicle_id,
        evidence_type="event",
        source_tool="list_session_events",
        tool_call_id=uuid4(),
        source_fingerprint="a" * 64,
        summary="Measured boost drop",
    )
    run.evidence = [evidence]
    raw = {
        "hypotheses": [{"category": "AIRFLOW_BOOST", "evidence_for": [str(evidence.id)]}],
        "gaps": [
            {
                "category": "signal_or_measurement",
                "hypothesis_indexes": [0],
                "signal_roles": ["boost_pressure_behavior", "boost_pressure_behavior"],
            }
        ],
    }
    proposal = InvestigationProposal.model_validate(raw)
    hypotheses, gaps, needs = materialize(proposal, run)
    assert len(needs) == 1
    assert hypotheses[0].evidence_for == [evidence.id]
    assert gaps[0].signal_need_ids == [needs[0].id]
    run.evidence = [evidence.model_copy(update={"vehicle_id": uuid4()})]
    with pytest.raises(AgentError, match="unknown_evidence"):
        materialize(proposal, run)
    run.evidence = [evidence.model_copy(update={"warnings": ["low quality"]})]
    with pytest.raises(AgentError, match="low_quality_hypothesis_evidence"):
        materialize(proposal, run)
    run.status = "failed"
    with pytest.raises(AgentError, match="invalid_investigation_run"):
        materialize(proposal, run)


async def test_existing_search_prefers_grounded_analysis_and_keeps_document_gap_open() -> None:
    run = insufficient_run("Why did performance change?")
    comparison = Evidence(
        id=uuid4(),
        run_id=run.id,
        vehicle_id=run.vehicle_id,
        evidence_type="comparison",
        source_tool="compare_configurations",
        tool_call_id=uuid4(),
        source_fingerprint="a" * 64,
        summary="Comparable configuration analysis",
        facts=[Fact(path="/comparison/sufficiency", value="sufficient")],
    )
    run.evidence = [comparison]
    history = EvidenceGap(
        id=uuid4(),
        category=GapType.COMPARABLE_HISTORY,
        description="Comparable sessions are absent",
        why_it_matters="A baseline is needed for comparison",
    )
    configuration = history.model_copy(
        update={"id": uuid4(), "category": GapType.CONFIGURATION_CONTEXT}
    )
    documentation = history.model_copy(
        update={"id": uuid4(), "category": GapType.TECHNICAL_DOCUMENTATION}
    )
    client = MagicMock()
    result = await search_existing(run, [history, configuration, documentation], [], client)
    assert result.gaps[0].status is GapStatus.NEEDS_NEW_CAPTURE
    assert result.gaps[1].status is GapStatus.AVAILABLE_IN_EXISTING_DATA
    assert result.gaps[2].status is GapStatus.OPEN
    run.evidence = [comparison.model_copy(update={"source_tool": "compare_pulls"})]
    result = await search_existing(run, [history], [], client)
    assert result.gaps[0].status is GapStatus.AVAILABLE_IN_EXISTING_DATA
    run.evidence = [comparison.model_copy(update={"warnings": ["truncated"]})]
    result = await search_existing(run, [configuration], [], client)
    assert result.gaps[0].status is GapStatus.OPEN
    run.result = None
    with pytest.raises(AgentError, match="invalid_investigation_run"):
        await search_existing(run, [history], [], client)


async def test_reanalysis_claims_one_run_and_reuses_durable_identifier() -> None:
    vehicle_id, session_id = uuid4(), uuid4()
    item = plan()
    item.vehicle_id = vehicle_id
    item.linked_session_ids = [session_id]
    item.status = InvestigationStatus.DATA_RECEIVED
    repository = MagicMock()
    repository.get = AsyncMock(return_value=item)

    async def claim(_vehicle, _investigation, run):
        item.status = InvestigationStatus.REANALYZING
        item.reanalysis_run_id = run.id
        return item

    repository.claim_reanalysis = AsyncMock(side_effect=claim)
    agents = MagicMock()
    agents.settings = AgentSettings(
        enabled=True, provider="deterministic", mcp_token=SecretStr("local-test-mcp")
    )
    agents.redact.side_effect = lambda text: text
    agents.start = AsyncMock()
    agents.tasks = {}
    service = InvestigationService(agents, repository, MagicMock())
    started = await service.reanalyze(vehicle_id, item.id)
    assert started.status is InvestigationStatus.REANALYZING
    assert started.reanalysis_run_id is not None
    assert agents.start.await_args.kwargs["run_id"] == started.reanalysis_run_id
    assert agents.start.await_args.args[1].session_id == session_id
    await service.reanalyze(vehicle_id, item.id)
    repository.claim_reanalysis.assert_awaited_once()
    assert agents.start.await_count == 2
    item.linked_session_ids = []
    with pytest.raises(AgentError, match="invalid_reanalysis_state"):
        await service.reanalyze(vehicle_id, item.id)
    item.status = InvestigationStatus.CANCELLED
    assert await service.reanalyze(vehicle_id, item.id) is item


async def test_link_get_and_close_reconcile_followup() -> None:
    item = plan()
    item.status = InvestigationStatus.DATA_RECEIVED
    repository = MagicMock()
    repository.link_session = AsyncMock(return_value=item)
    repository.get = AsyncMock(return_value=item)
    service = InvestigationService(MagicMock(), repository, MagicMock())
    service.reanalyze = AsyncMock(return_value=item)
    linked = await service.link(item.vehicle_id, item.id, uuid4(), 1)
    assert linked is item
    service.reanalyze.assert_awaited_once()
    item.status = InvestigationStatus.REANALYZING
    service.complete_follow_up = AsyncMock(return_value=item)
    assert await service.get(item.vehicle_id, item.id) is item
    service.complete_follow_up.assert_awaited_once()
    item.status = InvestigationStatus.COMPLETED
    assert await service.get(item.vehicle_id, item.id) is item
    pending = asyncio.create_task(asyncio.sleep(10))
    service.followups[item.id] = pending
    await service.close()
    assert pending.cancelled()


async def test_successful_followup_persists_conservative_outcome() -> None:
    repository = MemoryInvestigations()
    item = plan()
    session_id, run_id = uuid4(), uuid4()
    item.linked_session_ids = [session_id]
    item.reanalysis_run_id = run_id
    item.status = InvestigationStatus.REANALYZING
    item.hypotheses = [
        Hypothesis(
            id=uuid4(),
            category=HypothesisCategory.THERMAL,
            statement="Thermal conditions may be associated with the change",
            discriminating_goal="Compare intake temperature across compatible windows",
        )
    ]
    item = await repository.create(item)
    run = insufficient_run("Why was the pull slower?")
    run.id, run.vehicle_id = run_id, item.vehicle_id
    assert run.result is not None
    run.result.context.vehicle_id = item.vehicle_id
    call = ToolCall(
        id=uuid4(),
        run_id=run_id,
        tool_name="list_session_events",
        started_at=datetime.now(UTC),
        status="completed",
        argument_hash="a" * 64,
    )
    run.evidence = [
        Evidence(
            id=uuid4(),
            run_id=run_id,
            vehicle_id=item.vehicle_id,
            evidence_type="event",
            source_tool="list_session_events",
            tool_call_id=call.id,
            source_fingerprint="a" * 64,
            session_id=session_id,
            summary="Measured intake temperature rise",
            facts=[Fact(path="/event_type", value="iat_rise")],
        )
    ]
    agents = MagicMock()
    agents.repository.get = AsyncMock(return_value=run)
    agents.repository.calls = AsyncMock(return_value=[call])
    service = InvestigationService(agents, repository, MagicMock())
    completed = await service.complete_follow_up(item.vehicle_id, item.id)
    assert completed.status is InvestigationStatus.COMPLETED
    assert completed.outcome is not None
    assert completed.outcome.classification == "ASSOCIATION"
    assert completed.hypotheses[0].status is HypothesisStatus.SUPPORTED
    assert (await service.complete_follow_up(item.vehicle_id, item.id)).version == completed.version


async def test_refresh_rejects_cross_vehicle_session_capability() -> None:
    repository = MemoryInvestigations()
    item = plan()
    item.source_adapter = "obd"
    item.source_id = "source"
    item.source_session_id = uuid4()
    item.move(InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED)
    item = await repository.create(item)
    agents = MagicMock()
    envelope = MagicMock()
    envelope.context = {"vehicle_id": str(uuid4())}
    client = MagicMock()
    client.call = AsyncMock(return_value=envelope)

    @asynccontextmanager
    async def client_factory():
        yield client

    agents.client_factory = client_factory
    source = MagicMock()
    source.latest = AsyncMock(return_value=None)
    service = InvestigationService(agents, repository, source)
    with pytest.raises(AgentError, match="incompatible_context"):
        await service.refresh(item.vehicle_id, item.id, item.version)


async def test_cancel_and_reject_are_idempotent_only_at_exact_version() -> None:
    repository = MemoryInvestigations()
    item = await repository.create(plan())
    service = InvestigationService(MagicMock(), repository, MagicMock())
    cancelled = await service.cancel(item.vehicle_id, item.id, item.version)
    repeated = await service.cancel(item.vehicle_id, item.id, cancelled.version)
    assert repeated.version == cancelled.version
    with pytest.raises(AgentError, match="stale_investigation_version"):
        await service.cancel(item.vehicle_id, item.id, item.version)


async def test_registered_source_snapshot_preserves_preflight_provenance() -> None:
    agents = MagicMock()
    source = MagicMock()
    capabilities = DeviceCapabilities(
        "elm327-standard-read-only-v1", {"engine.rpm": Support.SUPPORTED}, 8
    )
    timestamp = datetime.now(UTC)
    preflight_id = uuid4()
    source.register = AsyncMock(
        return_value=SourceCapabilitySnapshot(capabilities, timestamp, preflight_id=preflight_id)
    )
    source.latest = AsyncMock(
        return_value=SourceCapabilitySnapshot(capabilities, timestamp, preflight_id=preflight_id)
    )
    service = InvestigationService(agents, MemoryInvestigations(), source)
    vehicle_id, configuration_id = uuid4(), uuid4()
    report = PreflightRequest(
        adapter="elm327-standard-read-only-v1",
        signals={"engine.rpm": "supported"},
        maximum_requests_per_second=8,
    )
    registered = await service.register_source(
        vehicle_id, configuration_id, "obd", "source", report
    )
    current = await service._source_capabilities(vehicle_id, configuration_id, "obd", "source")
    assert registered.source_preflight_id == preflight_id
    assert current is not None and current.source_preflight_id == preflight_id
    assert current.signals["engine.rpm"] is Support.SUPPORTED


async def test_create_closes_provider_after_invalid_semantic_output() -> None:
    run = insufficient_run("Why is timing missing?")
    agents = MagicMock()
    agents.repository.get = AsyncMock(return_value=run)
    agents.settings = AgentSettings(
        enabled=True, provider="deterministic", mcp_token=SecretStr("local-test-mcp")
    )
    agents.redact.side_effect = lambda text: text
    provider = MagicMock()
    provider.propose = AsyncMock(
        return_value={
            "hypotheses": [],
            "gaps": [{"category": "signal_or_measurement", "signal_roles": ["ecu.flash"]}],
        }
    )
    provider.close = AsyncMock()
    agents.provider_factory.return_value = provider
    service = InvestigationService(agents, MemoryInvestigations(), MagicMock())
    with pytest.raises(AgentError, match="invalid_investigation_proposal"):
        await service.create(run.vehicle_id, run.id, "synthetic", "source")
    provider.close.assert_awaited_once()
    assert service.active == 0


async def test_create_stops_when_existing_evidence_closes_every_gap(monkeypatch) -> None:
    run = insufficient_run("Why is timing missing?")
    agents = MagicMock()
    agents.repository.get = AsyncMock(return_value=run)
    agents.settings = AgentSettings(
        enabled=True, provider="deterministic", mcp_token=SecretStr("local-test-mcp")
    )
    agents.redact.side_effect = lambda text: text
    agents.provider_factory = DeterministicProvider

    @asynccontextmanager
    async def client_factory():
        yield MagicMock()

    agents.client_factory = client_factory

    async def sufficient(_run, gaps, _needs, _client):
        return ExistingEvidence(
            tuple(
                gap.model_copy(update={"status": GapStatus.AVAILABLE_IN_EXISTING_DATA})
                for gap in gaps
            ),
            {},
            0,
        )

    monkeypatch.setattr("vehicle_platform.agents.investigation.service.search_existing", sufficient)
    service = InvestigationService(agents, MemoryInvestigations(), MagicMock())
    with pytest.raises(AgentError, match="existing_evidence_sufficient"):
        await service.create(run.vehicle_id, run.id, "synthetic", "source")
    assert service.active == 0


async def test_reject_repeat_and_link_nonready_plan_return_current_state() -> None:
    repository = MemoryInvestigations()
    item = plan()
    source = DeviceCapabilities(
        "fixture",
        {
            requirement.signal: Support.SUPPORTED
            for requirement in BY_KEY["performance-pull"].requirements
        },
        70,
    )
    item.replace_recipe(plan_recipe([need(SignalRole.BOOST)], source).reference)
    for status in (
        InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED,
        InvestigationStatus.CAPABILITIES_RESOLVED,
        InvestigationStatus.RECIPE_PROPOSED,
        InvestigationStatus.AWAITING_APPROVAL,
    ):
        item.move(status)
    item = await repository.create(item)
    service = InvestigationService(MagicMock(), repository, MagicMock())
    rejected = await service.reject(item.vehicle_id, item.id, item.version)
    repeated = await service.reject(item.vehicle_id, item.id, rejected.version)
    assert repeated.version == rejected.version
    with pytest.raises(AgentError, match="stale_investigation_version"):
        await service.reject(item.vehicle_id, item.id, item.version)
    link_repo = MagicMock()
    link_repo.link_session = AsyncMock(return_value=rejected)
    other_service = InvestigationService(MagicMock(), link_repo, MagicMock())
    assert await other_service.link(item.vehicle_id, item.id, uuid4(), rejected.version) is rejected


async def test_approval_rejects_changed_source_and_resumes_partial_approval() -> None:
    repository = MemoryInvestigations()
    item = plan()
    source = DeviceCapabilities(
        "fixture",
        {
            requirement.signal: Support.SUPPORTED
            for requirement in BY_KEY["performance-pull"].requirements
        },
        70,
    )
    item.replace_recipe(plan_recipe([need(SignalRole.BOOST)], source).reference)
    assert item.recipe is not None
    snapshot = CapabilitySnapshot(
        adapter=source.adapter,
        signals=source.signals,
        maximum_requests_per_second=70,
        observed_at=datetime.now(UTC),
    )
    item.capability_snapshot = snapshot
    item.source_adapter = "obd"
    item.source_id = "source"
    for status in (
        InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED,
        InvestigationStatus.CAPABILITIES_RESOLVED,
        InvestigationStatus.RECIPE_PROPOSED,
        InvestigationStatus.AWAITING_APPROVAL,
    ):
        item.move(status)
    item = await repository.create(item)
    service = InvestigationService(MagicMock(), repository, MagicMock())
    service._source_capabilities = AsyncMock(return_value=None)
    with pytest.raises(AgentError, match="stale_source_capabilities"):
        await service.approve(
            item.vehicle_id, item.id, item.version, item.recipe.configuration_hash, "operator"
        )
    changed = snapshot.model_copy(update={"signals": {"engine.rpm": Support.UNSUPPORTED}})
    service._source_capabilities = AsyncMock(return_value=changed)
    with pytest.raises(AgentError, match="stale_source_capabilities"):
        await service.approve(
            item.vehicle_id, item.id, item.version, item.recipe.configuration_hash, "operator"
        )
    service._source_capabilities = AsyncMock(return_value=snapshot)
    item.approval = Approval(status="APPROVED", recipe_hash=item.recipe.configuration_hash)
    item.move(InvestigationStatus.APPROVED)
    item = await repository.update(item, item.version, "approved")
    resumed = await service.approve(
        item.vehicle_id, item.id, item.version, item.recipe.configuration_hash, "operator"
    )
    assert resumed.status is InvestigationStatus.ACQUISITION_READY


async def test_followup_watcher_reconciles_and_logs_failure_without_leaking() -> None:
    agents = MagicMock()
    service = InvestigationService(agents, MagicMock(), MagicMock())
    vehicle_id, investigation_id = uuid4(), uuid4()
    service.complete_follow_up = AsyncMock()

    async def success():
        return None

    await service._watch(vehicle_id, investigation_id, asyncio.create_task(success()))
    service.complete_follow_up.assert_awaited_once_with(vehicle_id, investigation_id)

    async def failure():
        raise RuntimeError("failure detail must stay out of telemetry")

    await service._watch(vehicle_id, investigation_id, asyncio.create_task(failure()))
    logged = agents.telemetry.log.call_args
    assert logged.kwargs["error_code"] == "RuntimeError"
    assert "failure detail" not in str(logged)


def test_plan_validation_rejects_duplicate_ids_cross_refs_and_unbound_approval() -> None:
    item = plan()
    gap = EvidenceGap(
        id=uuid4(),
        category=GapType.SIGNAL_OR_MEASUREMENT,
        description="Missing measured airflow signal",
        why_it_matters="Needed to compare operating windows",
    )
    item.gaps = [gap, gap]
    with pytest.raises(ValidationError, match="duplicate investigation identifiers"):
        InvestigationPlan.model_validate(item.model_dump())
    item.gaps = [gap]
    hypothesis = Hypothesis(
        id=uuid4(),
        category=HypothesisCategory.AIRFLOW_BOOST,
        statement="Boost may vary across compatible pulls",
        discriminating_goal="Compare measured boost across pulls",
        missing_gap_ids=[uuid4()],
    )
    item.hypotheses = [hypothesis]
    with pytest.raises(ValidationError, match="hypothesis references unknown gap"):
        InvestigationPlan.model_validate(item.model_dump())
    hypothesis.missing_gap_ids = [gap.id]
    signal_need = need(SignalRole.BOOST)
    item.signal_needs = [signal_need]
    with pytest.raises(ValidationError, match="signal need references unknown"):
        InvestigationPlan.model_validate(item.model_dump())
    signal_need.gap_ids = [gap.id]
    item.approval = Approval(status="APPROVED", recipe_hash="a" * 64)
    with pytest.raises(ValidationError, match="approval must bind"):
        InvestigationPlan.model_validate(item.model_dump())


def test_lifecycle_guards_approval_and_reanalysis_inputs() -> None:
    item = plan()
    item.status = InvestigationStatus.RECIPE_PROPOSED
    with pytest.raises(InvestigationError, match="approval requires a recipe"):
        item.move(InvestigationStatus.AWAITING_APPROVAL)
    item.status = InvestigationStatus.AWAITING_APPROVAL
    with pytest.raises(InvestigationError, match="approval requires the exact feasible recipe"):
        item.move(InvestigationStatus.APPROVED)
    item.status = InvestigationStatus.DATA_RECEIVED
    with pytest.raises(InvestigationError, match="linked canonical data"):
        item.move(InvestigationStatus.REANALYZING)


async def test_refresh_invalidates_approval_when_source_snapshot_is_replaced() -> None:
    repository = MemoryInvestigations()
    item = plan()
    item.source_adapter = "obd"
    item.source_id = "local-obd"
    device = DeviceCapabilities(
        "elm327-standard-read-only-v1",
        {
            "engine.rpm": Support.SUPPORTED,
            "vehicle.speed": Support.SUPPORTED,
            "engine.throttle_position": Support.SUPPORTED,
        },
        12,
    )
    item.signal_needs = [need(SignalRole.DATA_QUALITY)]
    planned = plan_recipe(item.signal_needs, device)
    assert planned.reference is not None
    assert planned.reference.feasibility is Feasibility.FEASIBLE
    item.replace_recipe(planned.reference)
    item.capability_snapshot = CapabilitySnapshot(
        adapter=device.adapter,
        signals=device.signals,
        maximum_requests_per_second=device.maximum_requests_per_second,
        observed_at=datetime.now(UTC),
        source_preflight_id=uuid4(),
    )
    item.approval = Approval(
        status="APPROVED",
        recipe_hash=planned.reference.configuration_hash,
        approved_at=datetime.now(UTC),
        actor="operator",
    )
    item.status = InvestigationStatus.ACQUISITION_READY
    item = await repository.create(item)
    source = MagicMock()
    source.latest = AsyncMock(
        return_value=SourceCapabilitySnapshot(
            device, datetime.now(UTC), preflight_id=item.capability_snapshot.source_preflight_id
        )
    )
    service = InvestigationService(MagicMock(), repository, source)
    refreshed = await service.refresh(item.vehicle_id, item.id, item.version)
    assert refreshed.approval.status == "INVALIDATED"
    assert refreshed.status is InvestigationStatus.AWAITING_APPROVAL


async def test_operator_routes_expose_bounded_plan_lifecycle_and_replay() -> None:
    item = plan()
    item.status = InvestigationStatus.COMPLETED
    event = InvestigationEvent(
        investigation_id=item.id,
        sequence=1,
        type="investigation_created",
        status=InvestigationStatus.DRAFT,
    )
    service = MagicMock()
    service.agents.settings.investigation_token = SecretStr("operator-test-secret")
    for method in (
        "create",
        "get",
        "refresh",
        "approve",
        "reject",
        "cancel",
        "link",
        "reanalyze",
        "register_source",
    ):
        setattr(service, method, AsyncMock(return_value=item))
    service.repository.get = AsyncMock(return_value=item)
    service.repository.recent = AsyncMock(return_value=[item])
    service.repository.events = AsyncMock(return_value=[event])
    app = FastAPI()
    app.include_router(investigation_router(service))
    base = f"/api/v1/vehicles/{item.vehicle_id}/investigations"
    headers = {"X-Investigation-Token": "operator-test-secret"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get(base, headers=headers)).status_code == 200
        assert (
            await client.post(
                base,
                headers=headers,
                json={
                    "agent_run_id": str(item.agent_run_id),
                    "adapter": "obd",
                    "source_id": "source",
                },
            )
        ).status_code == 201
        path = f"{base}/{item.id}"
        assert (await client.get(path, headers=headers)).status_code == 200
        assert (await client.get(path + "/events", headers=headers)).json()[0]["sequence"] == 1
        stream = await client.get(path + "/stream", headers=headers)
        assert stream.status_code == 200
        assert "event: investigation_created" in stream.text
        assert (
            await client.post(path + "/refresh", headers=headers, json={"version": 1})
        ).status_code == 200
        assert (
            await client.post(
                path + "/approve", headers=headers, json={"version": 1, "recipe_hash": "a" * 64}
            )
        ).status_code == 200
        for action in ("reject", "cancel"):
            assert (
                await client.post(path + "/" + action, headers=headers, json={"version": 1})
            ).status_code == 200
        link_response = await client.post(
            path + "/sessions",
            headers=headers,
            json={"version": 1, "session_id": str(uuid4())},
        )
        assert link_response.status_code == 200
        assert (await client.post(path + "/reanalyze", headers=headers)).status_code == 200
        denied = await client.get(path, headers={"X-Investigation-Token": "wrong"})
        assert denied.status_code == 401


async def test_operator_route_requires_configured_token() -> None:
    service = MagicMock()
    service.agents.settings.investigation_token = None
    app = FastAPI()
    app.include_router(investigation_router(service))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/v1/vehicles/{uuid4()}/investigations")
    assert response.status_code == 503


async def test_create_reuses_existing_plan_only_for_same_source() -> None:
    run = insufficient_run("Why is timing missing?")
    agents = MagicMock()
    agents.repository.get = AsyncMock(return_value=run)
    agents.settings = AgentSettings(
        enabled=True, provider="deterministic", mcp_token=SecretStr("local-test-mcp")
    )
    agents.redact.side_effect = lambda text: text
    agents.provider_factory = DeterministicProvider

    @asynccontextmanager
    async def client_factory():
        yield MagicMock()

    agents.client_factory = client_factory
    repository = MagicMock()
    persisted = plan()
    persisted.vehicle_id = run.vehicle_id
    persisted.agent_run_id = run.id
    persisted.source_adapter = "synthetic"
    persisted.source_id = "other"
    persisted.status = InvestigationStatus.CANCELLED
    repository.create = AsyncMock(return_value=persisted)
    service = InvestigationService(agents, repository, MagicMock())
    with pytest.raises(AgentError, match="investigation_source_conflict"):
        await service.create(run.vehicle_id, run.id, "synthetic", "source")
    persisted.source_id = "source"
    reused = await service.create(run.vehicle_id, run.id, "synthetic", "source")
    assert reused.id == persisted.id
    assert reused.status is InvestigationStatus.CANCELLED
    assert service.active == 0


async def test_create_timeout_maps_to_bounded_public_error() -> None:
    agents = MagicMock()
    agents.repository.get = AsyncMock(side_effect=TimeoutError)
    service = InvestigationService(agents, MemoryInvestigations(), MagicMock())
    with pytest.raises(AgentError, match="investigation_timeout"):
        await service.create(uuid4(), uuid4(), "obd", "source")
    assert service.active == 0


async def test_refresh_uses_same_vehicle_recorded_signals() -> None:
    repository = MemoryInvestigations()
    item = plan()
    item.source_adapter = "obd"
    item.source_id = "source"
    item.source_session_id = uuid4()
    item.move(InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED)
    item = await repository.create(item)
    agents = MagicMock()
    client = MagicMock()
    envelope = MagicMock()
    envelope.context = {"vehicle_id": str(item.vehicle_id)}
    envelope.data = {"available_signals": ["engine.rpm"]}
    client.call = AsyncMock(return_value=envelope)

    @asynccontextmanager
    async def client_factory():
        yield client

    agents.client_factory = client_factory
    source = MagicMock()
    source.latest = AsyncMock(return_value=None)
    service = InvestigationService(agents, repository, source)
    refreshed = await service.refresh(item.vehicle_id, item.id, item.version)
    assert refreshed.status is InvestigationStatus.CAPABILITIES_RESOLVED
    client.call.assert_awaited_once()


async def test_completed_followup_reloads_after_stale_race() -> None:
    item = plan()
    item.status = InvestigationStatus.REANALYZING
    item.reanalysis_run_id = uuid4()
    item.linked_session_ids = [uuid4()]
    repository = MagicMock()
    repository.get = AsyncMock(return_value=item)
    repository.update = AsyncMock(side_effect=AgentError("stale_investigation_version"))
    agents = MagicMock()
    run = insufficient_run("Why is timing missing?")
    run.id, run.vehicle_id = item.reanalysis_run_id, item.vehicle_id
    run.status = "failed"
    agents.repository.get = AsyncMock(return_value=run)
    service = InvestigationService(agents, repository, MagicMock())
    reloaded = await service.complete_follow_up(item.vehicle_id, item.id)
    assert reloaded is item
    assert repository.get.await_count == 2
