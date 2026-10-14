from test_agents import fixture as fixture
from test_agents import insufficient
from test_agents import telemetry as telemetry
from test_supervisor_runtime import runtime

from vehicle_platform.agents.provider import ModelTurn, ToolRequest
from vehicle_platform.agents.schemas import Specialist
from vehicle_platform.agents.scripted_provider import ScriptedProvider
from vehicle_platform.agents.specialists.runtime import Supervisor


async def test_quality_role_can_read_summary_without_interpreting_unreliable_measurements(
    fixture, telemetry
):
    state, client, engine = runtime(fixture, telemetry, "Check recorded signal quality.")
    identifier = next(iter(state.context.capabilities))
    state.context.capabilities[identifier]["signal_quality"][0]["missing_ratio"] = 0.95
    engine.provider = ScriptedProvider(
        [
            ModelTurn(
                tool_calls=[
                    ToolRequest(
                        call_id="quality-summary",
                        name="get_session_summary",
                        arguments={"vehicle_id": str(state.run.vehicle_id)},
                    )
                ]
            ),
            ModelTurn(draft=insufficient()),
        ]
    )
    result = await Supervisor(engine, state).execute_specialist(Specialist.DATA_QUALITY)
    assert result.status == "completed"
    assert result.blocks_interpretation
    assert result.evidence_gaps == ["data_quality"]
    assert result.model_turn_count == 2
    client.call.assert_awaited_once()


async def test_quality_gate_refreshes_metadata_after_its_own_reads(fixture, telemetry):
    state, client, engine = runtime(fixture, telemetry, "Check recorded signal quality.")
    original = client.call.side_effect
    identifier = next(iter(state.context.capabilities))

    async def read(name, arguments):
        result = await original(name, arguments)
        state.context.capabilities[identifier]["signal_quality"][0]["missing_ratio"] = 0.95
        return result

    client.call.side_effect = read
    engine.provider = ScriptedProvider(
        [
            ModelTurn(
                tool_calls=[
                    ToolRequest(
                        call_id="quality-refresh",
                        name="get_session_summary",
                        arguments={"vehicle_id": str(state.run.vehicle_id)},
                    )
                ]
            ),
            ModelTurn(draft=insufficient()),
        ]
    )
    result = await Supervisor(engine, state).execute_specialist(Specialist.DATA_QUALITY)
    assert result.status == "completed"
    assert result.blocks_interpretation
    assert "engine_speed_dropout" in result.data_quality_warnings
    assert result.evidence_gaps == ["data_quality"]
