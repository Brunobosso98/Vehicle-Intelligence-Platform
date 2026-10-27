import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError
from test_agent_runtime import ResponseStream, request
from test_agent_runtime import provider as provider
from test_agents import draft, insufficient, registry
from test_agents import fixture as fixture
from test_supervisor_contracts import request_for

from vehicle_platform.agents.investigation.domain import GapType
from vehicle_platform.agents.investigation.proposal import (
    InvestigationInput,
    InvestigationProposal,
    ProposedGap,
)
from vehicle_platform.agents.provider import AgentError, ModelInput, RoutingInput
from vehicle_platform.agents.schemas import Intent, RoutingProposal, Specialist
from vehicle_platform.agents.scripted_provider import DeterministicProvider
from vehicle_platform.agents.specialists.policy import specialist_policy


def routing_input():
    return RoutingInput(
        question="Recorded temperatures changed?",
        context={},
        evidence=[],
        candidates=["thermal"],
        hints=[],
    )


@pytest.mark.parametrize(
    "mode",
    ["supported", "conflict", "warning", "truncated", "stable", "cooling", "missing", "wrong_tool"],
)
async def test_deterministic_thermal_synthesis_requires_measured_consensus(mode):
    source = {
        "id": str(uuid4()),
        "source_tool": "get_repeated_pull_analysis",
        "warnings": ["limited"] if mode == "warning" else [],
        "truncated": mode == "truncated",
        "facts": [
            {"path": "/result/sequence/0/end_iat", "value": 300, "unit": "K"},
            {
                "path": "/result/sequence/1/end_iat",
                "value": 290 if mode == "cooling" else 330,
                "unit": "K",
            },
            {"path": "/result/sequence/0/normalized_acceleration", "value": 2, "unit": "m/s^2"},
            {
                "path": "/result/sequence/1/normalized_acceleration",
                "value": 2 if mode == "stable" else 1.8,
                "unit": "m/s^2",
            },
        ],
    }
    if mode == "missing":
        source["facts"] = source["facts"][:2]
    if mode == "wrong_tool":
        source["source_tool"] = "get_session_summary"
    turn = await DeterministicProvider().turn(
        ModelInput(
            question="Why did repeated pulls degrade?",
            tools=[],
            context={"vehicle_id": str(uuid4()), "sessions": []},
            evidence=[source],
            messages=[],
            supervisor={"conflicts": ["unresolved"] if mode == "conflict" else []},
        )
    )
    hypotheses = [c for c in turn.draft.claims if c.template == "thermal_hypothesis"]
    assert bool(hypotheses) is (mode == "supported")
    if hypotheses:
        assert len(hypotheses[0].bindings) == 4


@pytest.mark.parametrize("known_usage", [True, False])
async def test_real_adapter_routing_uses_typed_schema_without_tools(provider, known_usage):
    usage = (
        SimpleNamespace(
            input_tokens=12,
            output_tokens=7,
            total_tokens=19,
            input_tokens_details=SimpleNamespace(cached_tokens=2),
        )
        if known_usage
        else None
    )
    provider.client.responses.create.return_value = SimpleNamespace(
        output_text=RoutingProposal(
            intent=Intent.THERMAL, specialists=[Specialist.THERMAL]
        ).model_dump_json(),
        usage=usage,
    )
    result = await provider.route(routing_input())
    assert result.specialists == [Specialist.THERMAL]
    assert result.usage.total_tokens == (19 if known_usage else None)
    kwargs = provider.client.responses.create.call_args.kwargs
    assert kwargs["store"] is False and "tools" not in kwargs
    assert kwargs["text"]["format"]["name"] == "supervisor_routing"
    assert "sentinel-private-key" not in json.dumps(kwargs)


@pytest.mark.parametrize(
    "mode,category",
    [
        ("input", "model_input_budget_exhausted"),
        ("output", "model_output_budget_exhausted"),
        ("json", "invalid_supervisor_routing"),
        ("identity", "invalid_supervisor_routing"),
        ("authentication", "provider_authentication"),
        ("rate", "provider_rate_limit"),
        ("connection", "provider_unavailable"),
        ("timeout", "provider_timeout"),
    ],
)
async def test_routing_wire_errors_are_safe_and_bounded(provider, mode, category):
    payload = RoutingProposal(intent=Intent.THERMAL).model_dump_json()
    if mode == "input":
        provider.settings.max_input_bytes = 1
    elif mode == "output":
        payload = "x" * 32769
    elif mode == "json":
        payload = "{"
    elif mode == "identity":
        payload = '{"intent":"thermal","specialists":["supervisor"]}'
    else:
        wire_request = httpx.Request("POST", "https://example.invalid")
        provider.client.responses.create.side_effect = {
            "authentication": AuthenticationError(
                "private", response=httpx.Response(401, request=wire_request), body=None
            ),
            "rate": RateLimitError(
                "private", response=httpx.Response(429, request=wire_request), body=None
            ),
            "connection": APIConnectionError(request=wire_request),
            "timeout": APITimeoutError(request=wire_request),
        }[mode]
    provider.client.responses.create.return_value = SimpleNamespace(output_text=payload, usage=None)
    with pytest.raises(AgentError, match=category):
        await provider.route(routing_input())


async def test_specialist_system_policy_is_assigned_by_application(provider, fixture):
    evidence = registry(fixture)
    scope = request_for(fixture, evidence)
    model_input = request()
    model_input.specialist = scope
    model_input.context = scope.context.model_dump(mode="json")
    provider.client.responses.create.return_value = ResponseStream(
        [
            SimpleNamespace(
                type="response.completed",
                response=SimpleNamespace(
                    output=[],
                    output_text=draft(evidence).model_dump_json(),
                    usage=None,
                ),
            ),
        ]
    )
    await provider.turn(model_input)
    kwargs = provider.client.responses.create.call_args.kwargs
    instructions = kwargs["instructions"]
    assert specialist_policy(Specialist.THERMAL) in instructions
    assert "thermal-v7" in instructions and "No private reasoning" in instructions
    assert kwargs["text"]["format"]["strict"] is True
    assert kwargs["text"]["format"]["schema"]["properties"]["claims"]["maxItems"] == 8
    data = json.loads(kwargs["input"][1]["content"].split("\n", 1)[1])
    assert data["vehicle_context"] == scope.context.model_dump(mode="json")
    assert "context" not in data["specialist_scope"] and "question" not in data["specialist_scope"]
    assert data["specialist_scope"] == scope.model_dump(
        mode="json", exclude={"context", "question"}
    )
    assert kwargs["input"][0]["content"] == model_input.question


async def test_supervisor_synthesis_retains_grounding_policy(provider):
    model_input = request()
    model_input.supervisor = {"specialists": [], "sufficiency": "INSUFFICIENT"}
    provider.client.responses.create.return_value = ResponseStream(
        [
            SimpleNamespace(
                type="response.completed",
                response=SimpleNamespace(
                    output=[],
                    output_text=insufficient().model_dump_json(),
                    usage=None,
                ),
            ),
        ]
    )
    await provider.turn(model_input)
    instructions = provider.client.responses.create.call_args.kwargs["instructions"]
    assert "grounded-v6" in instructions and "supervisor-v3" in instructions


async def test_real_planning_adapter_receives_structured_supervisor_report(provider):
    report = {
        "specialists": [],
        "conflicts": [{"type": "competing_hypotheses"}],
        "sufficiency": "INSUFFICIENT",
    }
    provider.client.responses.create.return_value = SimpleNamespace(
        output_text=InvestigationProposal(
            gaps=[ProposedGap(category=GapType.COMPARABLE_HISTORY)]
        ).model_dump_json()
    )
    await provider.propose(
        InvestigationInput(
            question="Why did performance degrade?",
            context={},
            evidence=[],
            missing_evidence=["signal_or_measurement"],
            supervisor=report,
        )
    )
    content = provider.client.responses.create.call_args.kwargs["input"][0]["content"]
    payload = json.loads(content.split("\n", 1)[1])
    assert payload["supervisor"] == report
    assert payload["proposal_constraints"]["maximum_signal_needs"] == 16
    format_ = provider.client.responses.create.call_args.kwargs["text"]["format"]
    assert format_["strict"] is True
    for model in format_["schema"]["$defs"].values():
        if model.get("type") == "object":
            assert set(model["required"]) == set(model["properties"])
            assert model["additionalProperties"] is False


@pytest.mark.parametrize("poor_quality", [True, False])
async def test_repeated_pull_planning_preserves_competing_mechanisms(poor_quality):
    result = await DeterministicProvider().propose(
        InvestigationInput(
            question="Why did performance degrade after repeated pulls?",
            context={},
            evidence=[],
            missing_evidence=["signal_or_measurement", "data_quality"]
            if poor_quality
            else ["signal_or_measurement"],
            supervisor={"conflicts": []},
        )
    )
    assert {"THERMAL", "FUELING"} <= {h.category.value for h in result.hypotheses}
    assert any(g.category is GapType.DATA_QUALITY for g in result.gaps) is poor_quality


@pytest.mark.parametrize(
    ("question", "category"),
    [
        ("Why did performance change after intercooler?", "CONFIGURATION_ASSOCIATION"),
        ("Why did boost change?", "AIRFLOW_BOOST"),
        ("Why is fuel pressure missing during a pull?", "FUELING"),
    ],
)
async def test_quality_prerequisite_preserves_domain_investigation(question, category):
    result = await DeterministicProvider().propose(
        InvestigationInput(
            question=question,
            context={},
            evidence=[],
            missing_evidence=["data_quality", "signal_or_measurement"],
        )
    )
    assert {category, "DATA_QUALITY"} == {h.category.value for h in result.hypotheses}
    assert result.gaps[0].category is GapType.DATA_QUALITY
    assert result.gaps[0].hypothesis_indexes == [1]
    assert any(g.category is GapType.SIGNAL_OR_MEASUREMENT for g in result.gaps)


async def test_quality_only_investigation_has_a_valid_discriminating_gap():
    result = await DeterministicProvider().propose(
        InvestigationInput(
            question="Why is data quality low after dropout?",
            context={},
            evidence=[],
            missing_evidence=["data_quality", "signal_or_measurement"],
        )
    )
    assert [h.category.value for h in result.hypotheses] == ["DATA_QUALITY"]
    assert result.gaps[0].hypothesis_indexes == [0]
    assert InvestigationProposal.model_validate(result.model_dump()) == result


@pytest.mark.parametrize("specialist", [False, True])
@pytest.mark.parametrize("scoped", [False, True])
async def test_deterministic_pull_selection_is_unique_and_session_scoped(
    fixture, specialist, scoped
):
    evidence = registry(fixture)
    scope = request_for(fixture, evidence, Specialist.PERFORMANCE)
    context = scope.context.model_dump(mode="json")
    session_id = context["sessions"][0]["id"]
    first, second = str(uuid4()), str(uuid4())
    records = [
        {
            "id": str(uuid4()),
            "source_tool": "list_session_pulls",
            "entity_id": identifier,
            "session_id": owner,
        }
        for identifier, owner in [
            (str(uuid4()), str(uuid4())),
            (first, session_id if scoped else str(uuid4())),
            (first, session_id if scoped else str(uuid4())),
            (second, session_id if scoped else str(uuid4())),
        ]
    ]
    request = ModelInput(
        question="Como foram as últimas puxadas?",
        tools=[],
        context=context,
        evidence=records,
        messages=[],
        specialist=scope if specialist else None,
    )
    provider = DeterministicProvider()
    turn = await (provider.specialist_turn(request) if specialist else provider.turn(request))
    call = turn.tool_calls[0]
    if scoped:
        assert call.name == "get_repeated_pull_analysis"
        assert call.arguments["pull_ids"] == [first, second]
    else:
        assert call.name == "list_session_pulls"
        assert call.arguments["session_id"] == session_id


async def test_deterministic_configuration_comparison_deduplicates_pull_entities(fixture):
    scope = request_for(fixture, registry(fixture), Specialist.PERFORMANCE)
    context = scope.context.model_dump(mode="json")
    sessions = context["sessions"]
    configs = context["configurations"]
    configs.append(configs[0] | {"id": str(uuid4()), "effective_at": "2026-02-01T00:00:00Z"})
    sessions.append(sessions[0] | {"id": str(uuid4()), "configuration_id": configs[-1]["id"]})
    records = []
    expected = []
    for config in sorted(configs, key=lambda c: c["effective_at"]):
        ids = [str(uuid4()), str(uuid4())]
        expected.append(ids)
        session = next(s for s in sessions if s["configuration_id"] == config["id"])
        for identifier in [ids[0], ids[0], ids[1]]:
            records.append(
                {
                    "id": str(uuid4()),
                    "entity_id": identifier,
                    "source_tool": "list_session_pulls",
                    "configuration_id": config["id"],
                    "session_id": session["id"],
                }
            )
    request = ModelInput(
        question="O comportamento mudou depois da configuração?",
        tools=[],
        context=context,
        evidence=records,
        messages=[],
    )
    turn = await DeterministicProvider().turn(request)
    call = turn.tool_calls[0]
    assert call.name == "compare_configurations"
    assert call.arguments["before_pull_ids"] == expected[0]
    assert call.arguments["after_pull_ids"] == expected[-1]


async def test_rejected_proposal_logs_only_safe_rule_not_model_content(provider, caplog):
    roles = [
        "engine_speed_context",
        "vehicle_speed_context",
        "throttle_opening_behavior",
        "boost_pressure_behavior",
        "intake_temperature_behavior",
        "high_fuel_pressure_behavior",
    ]
    gaps = [{"category": "signal_or_measurement", "signal_roles": roles} for _ in range(3)]
    provider.client.responses.create.return_value = SimpleNamespace(
        output_text=json.dumps({"hypotheses": [], "gaps": gaps})
    )
    with pytest.raises(AgentError, match="invalid_investigation_proposal"):
        await provider.propose(
            InvestigationInput(
                question="private-user-sentinel", context={}, evidence=[], missing_evidence=[]
            )
        )
    records = [
        r for r in caplog.records if getattr(r, "event", None) == "investigation.proposal.rejected"
    ]
    assert len(records) == 1 and records[0].error_code == "signal_need_budget"
    assert "signal_need_budget" in records[0].getMessage()
    assert "private-user-sentinel" not in caplog.text
    assert "engine_speed_context" not in caplog.text
    assert provider.client.responses.create.call_count == 1


@pytest.mark.parametrize("category", list(GapType))
def test_proposal_wire_schema_rejects_signals_on_nonmeasurement_gaps(category):
    from jsonschema import Draft202012Validator

    from vehicle_platform.agents.investigation.proposal import InvestigationProposal
    from vehicle_platform.agents.openai_provider import investigation_schema

    validator = Draft202012Validator(investigation_schema())
    proposal = InvestigationProposal(gaps=[ProposedGap(category=category)]).model_dump(mode="json")
    assert validator.is_valid(proposal)
    proposal["gaps"][0]["signal_roles"] = ["engine_speed_context"]
    assert validator.is_valid(proposal) == (
        category in {GapType.SIGNAL_OR_MEASUREMENT, GapType.DATA_QUALITY}
    )
