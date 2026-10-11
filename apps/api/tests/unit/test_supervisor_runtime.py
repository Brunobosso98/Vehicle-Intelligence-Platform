import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from test_agents import execution
from test_agents import fixture as fixture
from test_agents import telemetry as telemetry
from test_supervisor_contracts import request_for

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.instrumentation import AgentInstrumentation
from vehicle_platform.agents.orchestration import Orchestrator
from vehicle_platform.agents.provider import AgentError, ModelTurn, ToolRequest
from vehicle_platform.agents.schemas import Specialist, Sufficiency
from vehicle_platform.agents.scripted_provider import DeterministicProvider
from vehicle_platform.agents.specialists.runtime import Supervisor
from vehicle_platform.mcp.schemas import Envelope


def runtime(fixture, telemetry, question, provider=None, events=None):
    state = execution(fixture)
    state.ask.question = question
    vehicle = state.run.vehicle_id
    session = UUID(fixture["sessions"][0]["id"])
    config = fixture["configurations"][0]["id"]
    report = {"signal_quality": [{"signal": "engine.rpm", "actual_hz": 10, "missing_ratio": 0}]}
    state.context.capabilities[str(session)] = report
    state.registry.add(
        "get_session_capabilities",
        uuid4(),
        Envelope(data=report, context={"vehicle_id": vehicle, "session_id": session}),
    )
    results = {
        "get_session_summary": {
            "result": {
                "sufficiency": "sufficient",
                "thermal": {"iat": {"mean": 310, "unit": "K"}},
                "duration": {"value": 4, "unit": "s"},
                "boost": {"mean": 117500, "unit": "Pa"},
            }
        },
        "list_session_events": [{"id": str(uuid4()), "event_type": e} for e in (events or [])],
        "list_session_pulls": [
            {
                "id": str(uuid4()),
                "vehicle_id": str(vehicle),
                "session_id": str(session),
                "configuration_id": config,
            }
            for _ in range(3)
        ],
        "get_repeated_pull_analysis": {
            "result": {
                "sufficiency": "sufficient",
                "duration": {"delta": 0.2, "unit": "s"},
            }
        },
        "get_vehicle": fixture["vehicle"],
    }
    client = AsyncMock()

    async def call(name, args):
        return Envelope(data=results[name], context={"vehicle_id": vehicle, "session_id": session})

    client.call.side_effect = call
    state.tools = [
        {
            "name": name,
            "description": "read-only",
            "parameters": {
                "type": "object",
                "required": ["vehicle_id"],
                "properties": {"vehicle_id": {"type": "string"}},
            },
        }
        for name in results
    ]
    engine = Orchestrator(AgentSettings(), provider or DeterministicProvider(), client, telemetry)
    return state, client, engine


async def test_simple_path_has_no_model_routing_or_specialists(fixture, telemetry):
    state, client, engine = runtime(fixture, telemetry, "What was my last session?")
    await Supervisor(engine, state).run()
    assert state.steps == 0
    assert state.run.supervisor.routing.selected == []
    assert state.run.supervisor.specialists == []
    client.call.assert_not_awaited()


async def test_quality_gate_checks_historical_comparison_capabilities(fixture, telemetry):
    state, _, engine = runtime(fixture, telemetry, "Did performance change after configuration?")
    state.context.capabilities[str(uuid4())] = {
        "signal_quality": [{"signal": "engine.rpm", "actual_hz": 0, "missing_ratio": 0.9}]
    }
    await Supervisor(engine, state).run()
    report = state.run.supervisor
    assert report.sufficiency is Sufficiency.UNRELIABLE_DATA
    assert [r.specialist for r in report.specialists] == [Specialist.DATA_QUALITY]
    assert "engine_speed_dropout" in report.specialists[0].data_quality_warnings


async def test_repeated_degradation_dispatches_only_relevant_specialists(fixture, telemetry):
    state, _, engine = runtime(
        fixture, telemetry, "Why did performance degrade after repeated pulls?"
    )
    await Supervisor(engine, state).run()
    report = state.run.supervisor
    assert report.routing.selected == [Specialist.PERFORMANCE, Specialist.THERMAL]
    assert [r.specialist for r in report.specialists] == [
        Specialist.DATA_QUALITY,
        Specialist.PERFORMANCE,
        Specialist.THERMAL,
    ]
    assert all(r.status == "completed" for r in report.specialists)
    assert all(
        e.run_id == state.run.id and e.vehicle_id == state.run.vehicle_id
        for e in state.registry.items.values()
    )
    assert all(f.evidence_ids for r in report.specialists for f in r.findings)


async def test_quality_dropout_blocks_deeper_interpretation(fixture, telemetry):
    state, client, engine = runtime(
        fixture, telemetry, "Why did boost fall?", events=["sensor_dropout"]
    )
    await Supervisor(engine, state).run()
    report = state.run.supervisor
    assert report.sufficiency is Sufficiency.UNRELIABLE_DATA
    assert [r.specialist for r in report.specialists] == [Specialist.DATA_QUALITY]
    assert report.investigation_recommended
    assert state.final.missing_evidence == ["data_quality"]
    assert client.call.await_count == 2


@pytest.mark.parametrize("failing", [Specialist.DATA_QUALITY, Specialist.THERMAL])
async def test_specialist_failure_isolated_and_quality_fails_closed(fixture, telemetry, failing):
    class Failing(DeterministicProvider):
        async def turn(self, request):
            if request.specialist and request.specialist.specialist is failing:
                raise AgentError("provider_unavailable")
            return await super().turn(request)

    state, _, engine = runtime(
        fixture, telemetry, "Why did performance degrade after repeated pulls?", Failing()
    )
    await Supervisor(engine, state).run()
    report = state.run.supervisor
    result = next(r for r in report.specialists if r.specialist is failing)
    assert result.status == "failed" and not result.findings
    if failing is Specialist.DATA_QUALITY:
        assert report.sufficiency is Sufficiency.UNRELIABLE_DATA and len(report.specialists) == 1
    else:
        assert report.sufficiency is Sufficiency.PARTIALLY_SUFFICIENT
        assert (
            next(r for r in report.specialists if r.specialist is Specialist.PERFORMANCE).status
            == "completed"
        )


async def test_tool_escalation_fails_before_mcp(fixture, telemetry):
    class Escalating(DeterministicProvider):
        async def turn(self, request):
            return ModelTurn(
                tool_calls=[
                    ToolRequest(
                        call_id="escalation",
                        name="compare_configurations",
                        arguments={"vehicle_id": request.context["vehicle_id"]},
                    )
                ]
            )

    state, client, engine = runtime(fixture, telemetry, "Is heat soak increasing?", Escalating())
    await Supervisor(engine, state).run()
    assert state.run.supervisor.specialists[0].error_category == "specialist_tool_policy_violation"
    assert all(call.args[0] != "compare_configurations" for call in client.call.await_args_list)


async def test_parallel_siblings_and_parent_cancellation_are_drained(fixture, telemetry):
    started = set()
    both_started = asyncio.Event()
    release = asyncio.Event()
    cancelled = set()

    class Blocking(DeterministicProvider):
        async def turn(self, request):
            if request.specialist and request.specialist.specialist is not Specialist.DATA_QUALITY:
                specialist = request.specialist.specialist
                started.add(specialist)
                if len(started) == 2:
                    both_started.set()
                try:
                    await release.wait()
                except asyncio.CancelledError:
                    cancelled.add(specialist)
                    raise
            return await super().turn(request)

    state, _, engine = runtime(
        fixture, telemetry, "Why did performance degrade after repeated pulls?", Blocking()
    )
    task = asyncio.create_task(Supervisor(engine, state).run())
    async with asyncio.timeout(2):
        await both_started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert cancelled == {Specialist.PERFORMANCE, Specialist.THERMAL}
    assert [r.status for r in state.run.supervisor.specialists] == [
        "completed",
        "cancelled",
        "cancelled",
    ]


async def test_concurrent_identical_mcp_calls_reuse_single_result(fixture, telemetry):
    state, client, engine = runtime(fixture, telemetry, "What was my last session?")
    args = {"vehicle_id": str(state.run.vehicle_id)}
    results = await asyncio.gather(
        engine.call(state, "get_vehicle", args), engine.call(state, "get_vehicle", args)
    )
    assert results[0] == results[1]
    assert client.call.await_count == 1 and len(state.tool_calls) == 1


async def test_multimechanism_conflict_routes_existing_investigation(fixture, telemetry):
    state, _, engine = runtime(
        fixture,
        telemetry,
        "Why did performance degrade after repeated pulls?",
        events=["iat_rise", "fuel_pressure_drop"],
    )
    await Supervisor(engine, state).run()
    report = state.run.supervisor
    assert report.routing.selected == [
        Specialist.PERFORMANCE,
        Specialist.THERMAL,
        Specialist.FUEL_AIR_BOOST,
    ]
    assert report.conflicts and report.conflicts[0].type == "competing_hypotheses"
    assert report.sufficiency is Sufficiency.INSUFFICIENT and report.investigation_recommended
    assert any(
        c.args[0] == "investigation_proposed" and c.args[1]["workflow"] == "phase7b"
        for c in state.emit.await_args_list
    )


@pytest.mark.parametrize(
    "mode,warning",
    [
        ("no_session", "no_recorded_session"),
        ("no_report", "recorded_signal_quality_unavailable"),
        ("no_rpm", "engine_speed_quality_unavailable"),
        ("bad_hz", "engine_speed_sampling_unverified"),
        ("missing", "engine_speed_dropout"),
        ("truncated", "quality_evidence_truncated"),
    ],
)
async def test_quality_gate_does_not_accept_unverified_recording(fixture, telemetry, mode, warning):
    state, _, engine = runtime(fixture, telemetry, "Is heat soak increasing?")
    sid = str(state.context.sessions[0]["id"])
    if mode == "no_session":
        state.context.sessions = []
    elif mode == "no_report":
        state.context.capabilities = {}
    elif mode == "no_rpm":
        state.context.capabilities[sid]["signal_quality"][0]["signal"] = "unknown"
    elif mode == "bad_hz":
        state.context.capabilities[sid]["signal_quality"][0]["actual_hz"] = None
    elif mode == "missing":
        state.context.capabilities[sid]["signal_quality"][0]["missing_ratio"] = 0.9
    else:
        next(iter(state.registry.items.values())).truncated = True
    await Supervisor(engine, state).run()
    assert warning in state.run.supervisor.specialists[0].data_quality_warnings
    assert state.run.supervisor.sufficiency is Sufficiency.UNRELIABLE_DATA


async def test_regular_five_hz_recording_is_downgraded_not_mislabeled_as_dropout(
    fixture, telemetry
):
    state, _, engine = runtime(fixture, telemetry, "Is heat soak increasing?")
    report = next(iter(state.context.capabilities.values()))
    report["signal_quality"][0].update(
        {"actual_hz": 5, "target_hz": 10, "missing_ratio": 0.49, "stale_ratio": 0}
    )
    await Supervisor(engine, state).run()
    quality = state.run.supervisor.specialists[0]
    assert quality.data_quality_warnings == ["recorded_sampling_below_recipe_target"]
    assert not quality.blocks_interpretation
    assert [r.specialist for r in state.run.supervisor.specialists] == [
        Specialist.DATA_QUALITY,
        Specialist.THERMAL,
    ]
    assert state.run.supervisor.sufficiency is Sufficiency.PARTIALLY_SUFFICIENT


async def test_unrelated_stuck_boost_does_not_block_recorded_temperature(fixture, telemetry):
    state, client, engine = runtime(fixture, telemetry, "Is heat soak increasing?")
    original = client.call.side_effect

    async def call(name, args):
        if name == "list_session_events":
            return Envelope(
                data=[
                    {
                        "id": str(uuid4()),
                        "event_type": "signal_stuck",
                        "evidence": {"signal": "engine.boost_pressure"},
                    }
                ],
                context={
                    "vehicle_id": state.run.vehicle_id,
                    "session_id": UUID(args["session_id"]),
                },
            )
        return await original(name, args)

    client.call.side_effect = call
    await Supervisor(engine, state).run()
    quality = state.run.supervisor.specialists[0]
    assert quality.data_quality_warnings == ["unrelated_signal_quality_event"]
    assert not quality.blocks_interpretation
    assert state.run.supervisor.specialists[-1].status == "completed"


@pytest.mark.parametrize(
    "mode", ["timeout", "malformed", "cross_run", "exception", "steps", "input"]
)
async def test_specialist_errors_are_bounded_and_no_findings_escape(fixture, telemetry, mode):
    class Invalid(DeterministicProvider):
        async def turn(self, request):
            if mode == "timeout":
                raise TimeoutError()
            if mode == "malformed":
                return ModelTurn()
            if mode == "exception":
                raise RuntimeError("private provider diagnostic")
            turn = await super().turn(request)
            if mode == "cross_run":
                turn.draft.claims[0].evidence_ids = [uuid4()]
            return turn

    state, _, engine = runtime(fixture, telemetry, "Is heat soak increasing?", Invalid())
    if mode == "steps":
        engine.settings.max_steps = 2
        state.steps = 1
    if mode == "input":
        engine.settings.max_input_bytes = 4096
        state.context.vehicle["untrusted"] = "x" * 5000
    if mode == "input":
        with pytest.raises(AgentError, match="model_input_budget_exhausted"):
            await Supervisor(engine, state).run()
        return
    await Supervisor(engine, state).run()
    result = state.run.supervisor.specialists[0]
    assert result.status in {"failed", "timed_out"} and not result.findings
    assert "private" not in result.model_dump_json()
    assert state.run.supervisor.sufficiency is Sufficiency.UNRELIABLE_DATA


def test_missing_context_does_not_dispatch(fixture, telemetry):
    state, _, engine = runtime(fixture, telemetry, "Is heat soak increasing?")
    state.context = None
    supervisor = Supervisor(engine, state)
    with pytest.raises(AgentError, match="context_missing"):
        supervisor.synthesize_unreliable()


@pytest.mark.parametrize(
    "field",
    [
        "session_id",
        "session_ids",
        "pull_id",
        "pull_ids",
        "before_pull_ids",
        "after_pull_ids",
        "event_id",
    ],
)
def test_specialist_cannot_read_unresolved_context_ids(fixture, telemetry, field):
    state, _, engine = runtime(fixture, telemetry, "Is heat soak increasing?")
    request = request_for(fixture, state.registry)
    identifier = str(uuid4())
    value = [identifier] if field.endswith("ids") else identifier
    with pytest.raises(AgentError, match="incompatible_specialist_context"):
        Supervisor(engine, state).enforce_scope(request, {field: value})


@pytest.mark.parametrize("mode", ["calls", "telemetry", "reuse", "turn_size"])
async def test_specialist_budgets_and_reuse_are_enforced_in_production_dispatch(
    fixture, telemetry, mode
):
    class Requesting(DeterministicProvider):
        async def turn(self, request):
            if request.specialist.specialist is Specialist.DATA_QUALITY:
                return await super().turn(request)
            executed = [m for m in request.messages if m.get("type") == "function_call"]
            if mode == "reuse" and executed:
                return await super().turn(request)
            name = "get_telemetry_window" if mode == "telemetry" else "get_session_summary"
            count = (
                5
                if mode == "turn_size"
                else 2
                if mode == "telemetry"
                else 4
                if mode == "calls"
                else 1
            )
            return ModelTurn(
                tool_calls=[
                    ToolRequest(
                        call_id=f"request-{len(executed)}-{i}",
                        name=name,
                        arguments={
                            "vehicle_id": request.context["vehicle_id"],
                            "session_id": request.context["sessions"][0]["id"],
                        },
                    )
                    for i in range(count)
                ]
            )

    state, client, engine = runtime(fixture, telemetry, "Is heat soak increasing?", Requesting())
    original = client.call.side_effect

    async def call(name, args):
        if name == "get_telemetry_window":
            return Envelope(data={"iat": 310}, context={"vehicle_id": state.run.vehicle_id})
        return await original(name, args)

    client.call.side_effect = call
    state.tools.append(
        {"name": "get_telemetry_window", "description": "bounded", "parameters": {"type": "object"}}
    )
    await Supervisor(engine, state).run()
    result = next(r for r in state.run.supervisor.specialists if r.specialist is Specialist.THERMAL)
    if mode == "reuse":
        assert result.status == "completed" and result.cache_hits == 1
        assert state.run.supervisor.cache_hits == 1
    else:
        assert result.status == "failed" and result.findings == []
        assert (
            result.error_category
            == {
                "calls": "specialist_tool_budget_exhausted",
                "telemetry": "specialist_telemetry_budget_exhausted",
                "turn_size": "invalid_specialist_result",
            }[mode]
        )


@pytest.mark.parametrize("mode", ["success", "failure", "policy", "budget"])
async def test_supervisor_metrics_use_bounded_labels(fixture, telemetry, mode):
    state, _, engine = runtime(
        fixture, telemetry, "Why did performance degrade after repeated pulls?"
    )
    await Supervisor(engine, state).run()
    run = state.run
    run.status = "completed"
    report = run.supervisor
    if mode != "success":
        report.investigation_recommended = True
        report.specialists[-1].status = "failed"
        report.specialists[-1].error_category = {
            "failure": "provider_unavailable",
            "policy": "specialist_tool_policy_violation",
            "budget": "specialist_tool_budget_exhausted",
        }[mode]
    signals = AgentInstrumentation(telemetry)
    signals.specialists = MagicMock()
    signals.policy_rejections = MagicMock()
    signals.budgets = MagicMock()
    signals.completed(run)
    assert signals.specialists.add.call_count == 3
    for call in signals.specialists.add.call_args_list:
        assert set(call.args[1]) == {"specialist", "status"}
        assert str(run.id) not in str(call.args[1])
    assert sum(call.args[0] for call in signals.policy_rejections.add.call_args_list) == int(
        mode == "policy"
    )
    assert signals.budgets.add.call_count == int(mode == "budget")


@pytest.mark.parametrize(
    "signal,hz,missing,stale,blocking,warning",
    [
        ("engine.intake_air_temperature", 0, 0, 0, True, "relevant_signal_sampling_unverified"),
        ("engine.intake_air_temperature", 10, 0.6, 0, True, "relevant_signal_dropout"),
        (
            "engine.intake_air_temperature",
            5,
            0.4,
            0,
            False,
            "recorded_sampling_below_recipe_target",
        ),
        ("engine.intake_air_temperature", 10, 0, 0.5, True, "relevant_signal_stale"),
        ("engine.intake_air_temperature", None, None, None, True, "relevant_signal_dropout"),
        ("engine.rpm", 10, 0, 0.5, True, "engine_speed_stale"),
        ("engine.rpm", 10, 0, None, True, "engine_speed_stale"),
    ],
)
async def test_quality_gate_checks_relevant_recorded_signals(
    fixture, telemetry, signal, hz, missing, stale, blocking, warning
):
    state, _, engine = runtime(fixture, telemetry, "Is heat soak increasing?")
    await Supervisor(engine, state).run()
    session = str(state.context.sessions[0]["id"])
    quality = state.context.capabilities[session]["signal_quality"]
    if signal == "engine.rpm":
        quality.clear()
    quality.append(
        {"signal": signal, "actual_hz": hz, "missing_ratio": missing, "stale_ratio": stale}
    )
    warnings, blocked = Supervisor(engine, state).quality_warnings()
    assert blocked is blocking and warning in warnings


async def test_missing_requested_signal_downgrades_without_inventing_values(fixture, telemetry):
    state, _, engine = runtime(fixture, telemetry, "Is lambda changing?")
    session = str(state.context.sessions[0]["id"])
    state.context.capabilities[session]["available_signals"] = ["engine.rpm"]
    await Supervisor(engine, state).run()
    quality = state.run.supervisor.specialists[0]
    assert quality.evidence_gaps == ["signal_or_measurement"]
    assert "requested_signal_unavailable" in quality.data_quality_warnings
    assert not quality.blocks_interpretation
    assert state.run.supervisor.investigation_recommended
    assert all(
        "lambda" not in binding.path
        for result in state.run.supervisor.specialists
        for finding in result.findings
        for binding in finding.bindings
    )


async def test_policy_hash_and_effective_limits_are_persistable(fixture, telemetry):
    first, _, engine = runtime(fixture, telemetry, "Is heat soak increasing?")
    await Supervisor(engine, first).run()
    second, _, other = runtime(fixture, telemetry, "Did boost change?")
    await Supervisor(other, second).run()
    assert first.run.supervisor.configuration_hash == second.run.supervisor.configuration_hash
    assert len(first.run.supervisor.configuration_hash) == 64
    assert first.run.supervisor.limits.model_turns == engine.settings.max_steps
    assert all(r.budget is not None for r in first.run.supervisor.specialists)
    other.settings.max_concurrent_specialists = 1
    changed, _, other = runtime(fixture, telemetry, "Is heat soak increasing?")
    other.settings.max_concurrent_specialists = 1
    await Supervisor(other, changed).run()
    assert changed.run.supervisor.configuration_hash != first.run.supervisor.configuration_hash


async def test_interrupted_paid_turn_preserves_unknown_usage_in_parent(fixture, telemetry):
    class Interrupted(DeterministicProvider):
        async def turn(self, request):
            if request.specialist.specialist is Specialist.THERMAL:
                raise TimeoutError
            return await super().turn(request)

    state, _, engine = runtime(
        fixture, telemetry, "Why did performance degrade after repeated pulls?", Interrupted()
    )
    assert engine.settings.provider == "openai"
    await Supervisor(engine, state).run()
    thermal = next(
        r for r in state.run.supervisor.specialists if r.specialist is Specialist.THERMAL
    )
    assert thermal.usage.total_tokens is None
    assert state.run.usage.total_tokens is None and state.run.usage.estimated_cost is None
