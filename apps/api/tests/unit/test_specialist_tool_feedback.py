import json

import pytest
from test_agents import fixture as fixture
from test_agents import insufficient
from test_agents import telemetry as telemetry
from test_supervisor_runtime import runtime

from vehicle_platform.agents.provider import AgentError, ModelTurn, ToolRequest
from vehicle_platform.agents.schemas import Specialist
from vehicle_platform.agents.scripted_provider import ScriptedProvider
from vehicle_platform.agents.specialists.runtime import Supervisor
from vehicle_platform.mcp.schemas import Envelope


@pytest.mark.parametrize("category", ["mcp_tool_error", "tool_result_budget_exhausted"])
async def test_specialist_gets_bounded_failure_feedback_without_publishing_evidence(
    fixture, telemetry, category
):
    state, client, engine = runtime(fixture, telemetry, "Compare intake temperatures.")
    initial_ids = set(state.registry.items)

    def after_failure(request):
        feedback = json.loads(request.messages[-1]["output"])
        assert feedback == {"status": "failed", "error_category": category}
        assert {item["id"] for item in request.evidence} == {str(i) for i in initial_ids}
        draft = insufficient()
        draft.missing_evidence = ["signal_or_measurement"]
        return ModelTurn(draft=draft)

    engine.provider = ScriptedProvider(
        [
            ModelTurn(
                tool_calls=[
                    ToolRequest(
                        call_id="bounded-read",
                        name="get_session_summary",
                        arguments={"vehicle_id": str(state.run.vehicle_id)},
                    )
                ]
            ),
            after_failure,
        ]
    )
    if category == "mcp_tool_error":
        client.call.side_effect = AgentError(category)
    else:
        client.call.side_effect = None
        client.call.return_value = Envelope(
            data={"oversized": "x" * (engine.settings.max_result_bytes + 1)},
            context={"vehicle_id": state.run.vehicle_id},
        )
    result = await Supervisor(engine, state).execute_specialist(Specialist.THERMAL)
    assert result.status == "completed"
    assert result.evidence_gaps == ["signal_or_measurement"]
    assert result.evidence_ids == []
    assert result.model_turn_count == 2
    assert result.tool_call_count == 1
    assert result.cache_hits == 0
    assert set(state.registry.items) == initial_ids
    assert not state.cache
    assert len(state.tool_calls) == 1
    assert state.tool_calls[0].status == "failed"
    assert state.tool_calls[0].error_category == category


async def test_specialist_unavailable_transport_still_fails(fixture, telemetry):
    state, client, engine = runtime(fixture, telemetry, "Compare intake temperatures.")
    engine.provider = ScriptedProvider(
        [
            ModelTurn(
                tool_calls=[
                    ToolRequest(
                        call_id="failed-read",
                        name="get_session_summary",
                        arguments={"vehicle_id": str(state.run.vehicle_id)},
                    )
                ]
            )
        ]
    )
    client.call.side_effect = RuntimeError("private transport detail")
    result = await Supervisor(engine, state).execute_specialist(Specialist.THERMAL)
    assert result.status == "failed"
    assert result.error_category == "mcp_unavailable"
    assert result.model_turn_count == 1
    assert result.findings == []


async def test_last_specialist_turn_reserves_a_draft_with_existing_budgets(fixture, telemetry):
    state, client, engine = runtime(fixture, telemetry, "Compare intake temperatures.")
    turns = []

    def respond(request):
        turns.append(request)
        if request.tools:
            return ModelTurn(
                tool_calls=[
                    ToolRequest(
                        call_id=f"read-{len(turns)}",
                        name="get_session_summary",
                        arguments={"vehicle_id": str(state.run.vehicle_id)},
                    )
                ]
            )
        return ModelTurn(draft=insufficient())

    engine.provider = ScriptedProvider([respond] * 4)
    result = await Supervisor(engine, state).execute_specialist(Specialist.THERMAL)
    assert result.status == "completed"
    assert result.model_turn_count == result.budget.model_turns == 4
    assert result.tool_call_count == 3
    assert result.cache_hits == 2
    assert len(state.tool_calls) == 1
    assert client.call.await_count == 1
    assert len(turns) == 4
    assert all(t.tools for t in turns[:3])
    assert turns[-1].tools == []
