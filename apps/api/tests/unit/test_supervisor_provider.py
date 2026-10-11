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
    instructions = provider.client.responses.create.call_args.kwargs["instructions"]
    assert specialist_policy(Specialist.THERMAL) in instructions
    assert "thermal-v1" in instructions and "No private reasoning" in instructions


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
    assert "grounded-v1" in instructions and "supervisor-v1" in instructions
