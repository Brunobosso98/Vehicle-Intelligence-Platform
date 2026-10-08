from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from test_agents import NOW, context, draft, execution, registry
from test_agents import fixture as fixture
from test_agents import telemetry as telemetry

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.evidence import EvidenceRegistry, facts
from vehicle_platform.agents.grounding import render_binding, validate
from vehicle_platform.agents.orchestration import Orchestrator
from vehicle_platform.agents.provider import AgentError, ModelInput, ModelTurn, ToolRequest
from vehicle_platform.agents.schemas import Binding, Claim, Draft
from vehicle_platform.agents.scripted_provider import DeterministicProvider, ScriptedProvider
from vehicle_platform.mcp.schemas import Envelope


def comparison(fixture):
    original = fixture["configurations"][0]
    original["ended_at"] = NOW.isoformat()
    fixture["sessions"][0]["started_at"] = (NOW - timedelta(days=1)).isoformat()
    replacement = original | {"id": str(uuid4()), "effective_at": NOW.isoformat(), "ended_at": None}
    fixture["configurations"].append(replacement)
    fixture["sessions"].append(
        fixture["sessions"][0]
        | {"id": str(uuid4()), "started_at": NOW.isoformat(), "configuration_id": replacement["id"]}
    )
    vehicle = UUID(fixture["vehicle"]["id"])
    evidence = EvidenceRegistry(uuid4(), vehicle, 80)
    configurations = evidence.add(
        "list_vehicle_configurations",
        uuid4(),
        Envelope(context={"vehicle_id": vehicle}, data=fixture["configurations"]),
    )
    pulls = []
    for session in fixture["sessions"]:
        pull = {
            "id": str(uuid4()),
            "session_id": session["id"],
            "vehicle_id": str(vehicle),
            "configuration_id": session["configuration_id"],
        }
        pulls.append(pull)
    evidence.add(
        "list_session_pulls", uuid4(), Envelope(context={"vehicle_id": vehicle}, data=pulls)
    )
    source = evidence.add(
        "compare_configurations",
        uuid4(),
        Envelope(
            context={"vehicle_id": vehicle, "pull_ids": [UUID(p["id"]) for p in pulls]},
            data={
                "result": {
                    "sufficiency": "sufficient",
                    "metric_deltas": {"iat": {"absolute": -10, "unit": "K"}},
                }
            },
        ),
    )[0]
    claim = Claim(
        classification="ASSOCIATION",
        template="temporal_association",
        evidence_ids=[source.id] + [e.id for e in configurations],
        bindings=[
            Binding(
                evidence_id=source.id,
                path="/result/metric_deltas/iat/absolute",
                value=-10,
                unit="K",
            )
        ],
    )
    return evidence, source, Draft(confidence="moderate", claims=[claim], missing_evidence=[])


def test_association_uses_actual_selected_pull_configuration_and_timeline(fixture):
    evidence, _, proposed = comparison(fixture)
    result = validate(proposed, evidence, context(fixture))
    assert "-10 K" in result.answer and "não provam causalidade" in result.answer
    assert result.findings[0].classification == "ASSOCIATION"


def test_other_valid_session_does_not_mask_selected_pull_temporal_mismatch(fixture):
    evidence, _, proposed = comparison(fixture)
    fixture["sessions"].append(fixture["sessions"][1] | {"id": str(uuid4())})
    fixture["sessions"][1]["started_at"] = (NOW - timedelta(days=2)).isoformat()
    with pytest.raises(AgentError, match="unsupported_association"):
        validate(proposed, evidence, context(fixture))


@pytest.mark.parametrize(
    "mode",
    ["warning", "truncated", "insufficient", "unknown_pull", "wrong_timeline", "pull_quality"],
)
def test_association_degrades_without_comparable_complete_context(fixture, mode):
    evidence, source, proposed = comparison(fixture)
    if mode == "warning":
        source.warnings = ["missing_signal"]
    if mode == "truncated":
        source.truncated = True
    if mode == "insufficient":
        source.facts[0].value = "insufficient"
    if mode == "unknown_pull":
        source.provenance["selection"]["pull_ids"] = [str(uuid4())]
    if mode == "wrong_timeline":
        fixture["sessions"][1]["started_at"] = (NOW - timedelta(days=2)).isoformat()
    if mode == "pull_quality":
        next(e for e in evidence.items.values() if e.pull_id).warnings = ["source_incomplete"]
    with pytest.raises(AgentError, match="unsupported_association"):
        validate(proposed, evidence, context(fixture))


@pytest.mark.parametrize("mode", ["flags", "completeness", "sufficiency"])
def test_source_quality_becomes_grounding_warning(fixture, mode):
    result = {"sufficiency": "sufficient", "completeness": 1.0}
    if mode == "flags":
        result["data_quality_flags"] = ["telemetry_gap"]
    if mode == "completeness":
        result["completeness"] = 0.3
    if mode == "sufficiency":
        result["sufficiency"] = "insufficient"
    evidence = EvidenceRegistry(uuid4(), UUID(fixture["vehicle"]["id"]), 10)
    item = evidence.add(
        "get_session_summary",
        uuid4(),
        Envelope(data={"result": result}, context={"vehicle_id": evidence.vehicle_id}),
    )[0]
    assert len(item.warnings) == 1


def test_unsafe_operation_is_explicitly_refused_without_bindings(fixture):
    evidence = registry(fixture)
    proposed = Draft(
        confidence="high",
        missing_evidence=[],
        claims=[
            Claim(
                classification="INSUFFICIENT_EVIDENCE",
                template="unsafe_operation_refused",
                bindings=[],
                evidence_ids=[],
            )
        ],
    )
    result = validate(proposed, evidence, context(fixture))
    assert "Recuso executar controle" in result.answer and result.confidence == "low"


async def test_comparison_reports_measured_change_before_unchanged_metrics(fixture):
    evidence, source, _ = comparison(fixture)
    source.facts = facts(
        {
            "result": {
                "sufficiency": "sufficient",
                "metric_deltas": {
                    "boost": {
                        "before": 117500,
                        "after": 117500,
                        "absolute": 0,
                        "relative": 0,
                        "unit": "Pa",
                    },
                    "iat": {"absolute": -10, "unit": "K"},
                },
            }
        }
    )
    turn = await DeterministicProvider().turn(
        ModelInput(
            question="O comportamento mudou depois da configuração nova?",
            tools=[],
            context=context(fixture).model_dump(mode="json"),
            evidence=[e.model_dump(mode="json") for e in evidence.items.values()],
            messages=[{"type": "function_call", "name": "compare_configurations"}],
        )
    )
    assert turn.draft.claims[0].bindings[0].value == -10
    assert "-10 K" in validate(turn.draft, evidence, context(fixture)).answer


@pytest.mark.parametrize("mode", ["valid", "warning", "no_thermal", "non_numeric"])
def test_thermal_hypothesis_needs_numeric_complete_measured_domains(fixture, mode):
    evidence = registry(fixture)
    source = next(iter(evidence.items.values()))
    source.facts = facts(
        {"iat": {"value": 310, "unit": "K"}, "duration": {"value": 5, "unit": "s"}}
    )
    selected = [f for f in source.facts if f.path.endswith("/value")]
    if mode == "warning":
        source.warnings = ["partial_window"]
    if mode == "no_thermal":
        selected = selected[1:]
    if mode == "non_numeric":
        selected[0].value = "unknown"
    proposed = Draft(
        confidence="moderate",
        missing_evidence=[],
        claims=[
            Claim(
                classification="HYPOTHESIS",
                template="thermal_hypothesis",
                evidence_ids=[source.id],
                bindings=[Binding(evidence_id=source.id, **f.model_dump()) for f in selected],
            )
        ],
    )
    if mode == "valid":
        assert "permanece hipótese" in validate(proposed, evidence, context(fixture)).answer
    else:
        with pytest.raises(AgentError, match="unsupported_hypothesis"):
            validate(proposed, evidence, context(fixture))


def test_projection_boundaries_and_empty_answer(fixture):
    assert facts("x" * 501) == []
    assert facts({"value": 1}, depth=13) == []
    assert len(facts(list(range(100)))) == 20
    assert len(facts({str(i): i for i in range(1000)})) == 161
    assert render_binding("/iat", None, "K") == "iat: não disponível"
    evidence = registry(fixture)
    source = next(iter(evidence.items.values()))
    source.truncated = True
    assert (
        "bounded_evidence_is_incomplete"
        in validate(draft(evidence), evidence, context(fixture)).limitations
    )
    with pytest.raises(AgentError, match="empty_answer"):
        validate(
            Draft(confidence="low", claims=[], missing_evidence=[]), evidence, context(fixture)
        )
    with pytest.raises(AgentError, match="invalid_tool_result"):
        evidence.check_ownership({}, depth=17)
    with pytest.raises(AgentError, match="incompatible_context"):
        evidence.add("get_vehicle", uuid4(), Envelope(data={}, context={"vehicle_id": uuid4()}))


@pytest.mark.parametrize(
    "name,key", [("get_event", "event_id"), ("get_pull", "pull_id"), ("get_session", "session_id")]
)
def test_evidence_entity_identity(fixture, name, key):
    evidence = registry(fixture)
    identifier = uuid4()
    added = evidence.add(
        name,
        uuid4(),
        Envelope(data={"id": str(identifier)}, context={"vehicle_id": evidence.vehicle_id}),
    )[0]
    assert getattr(added, key) == identifier and added.entity_id == identifier


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Teve boost drop?", "list_session_events"),
        ("Como foram as puxadas?", "list_session_pulls"),
        ("Qual causa exata?", "get_session_summary"),
        ("O comportamento mudou depois da configuração?", "list_session_pulls"),
    ],
)
async def test_deterministic_planning_uses_permitted_mcp_calls(fixture, question, expected):
    request = ModelInput(
        question=question,
        tools=[],
        context=context(fixture).model_dump(mode="json"),
        evidence=[],
        messages=[],
    )
    result = await DeterministicProvider().turn(request)
    assert result.tool_calls[0].name == expected
    assert result.tool_calls[0].arguments["vehicle_id"] == fixture["vehicle"]["id"]


@pytest.mark.parametrize(
    "question,source",
    [
        ("Teve boost drop?", "list_session_events"),
        ("A IAT piorou nas puxadas?", "get_repeated_pull_analysis"),
        ("O comportamento mudou depois da configuração?", "compare_configurations"),
    ],
)
async def test_deterministic_provider_renders_existing_facts_and_downgrades_bad_comparison(
    fixture, question, source
):
    evidence = registry(fixture)
    item = next(iter(evidence.items.values()))
    item.source_tool = source
    item.facts = facts(
        {"event_type": "boost_drop", "result": {"sufficiency": "insufficient", "iat": 310}}
    )
    request = ModelInput(
        question=question,
        tools=[],
        context=context(fixture).model_dump(mode="json"),
        evidence=[item.model_dump(mode="json")],
        messages=[{"type": "function_call", "name": source}],
    )
    turn = await DeterministicProvider().turn(request)
    assert turn.draft.claims[0].classification == "OBSERVATION"
    if source == "compare_configurations":
        assert turn.draft.claims[-1].classification == "INSUFFICIENT_EVIDENCE"


async def test_measured_tool_reuses_validated_pull_but_loads_missing_capability(fixture, telemetry):
    state = execution(fixture)
    pull = uuid4()
    session = UUID(fixture["sessions"][0]["id"])
    state.registry.add(
        "list_session_pulls",
        uuid4(),
        Envelope(
            data={"id": str(pull), "session_id": str(session)},
            context={"vehicle_id": state.run.vehicle_id},
        ),
    )
    engine = Orchestrator(AgentSettings(), ScriptedProvider([]), MagicMock(), telemetry)
    engine.call = AsyncMock(return_value={"data": {}, "mcp_request_id": str(uuid4())})
    state.turn = ModelTurn(
        tool_calls=[
            ToolRequest(
                call_id="x",
                name="compare_pulls",
                arguments={"vehicle_id": str(state.run.vehicle_id), "pull_ids": [str(pull)]},
            )
        ]
    )
    await engine.tools_node({"execution": state})
    assert "get_pull" not in [c.args[1] for c in engine.call.call_args_list]
    assert str(session) in state.context.capabilities


async def test_context_and_capability_bounds(fixture, telemetry):
    state = execution(fixture)
    engine = Orchestrator(AgentSettings(), ScriptedProvider([]), MagicMock(), telemetry)
    state.context = None
    with pytest.raises(AgentError, match="context_missing"):
        await engine.capabilities(state, uuid4())
    state.context = context(fixture)
    state.context.sessions *= 10
    with pytest.raises(AgentError, match="context_budget_exhausted"):
        await engine.capabilities(state, uuid4())
    state.turn = None
    with pytest.raises(AgentError, match="invalid_model_response"):
        await engine.tools_node({"execution": state})
    with pytest.raises(AgentError, match="invalid_model_response"):
        await engine.grounding_node({"execution": state})
