import json
from pathlib import Path

import pytest
from test_agents import fixture as fixture
from test_agents import insufficient
from test_agents import telemetry as telemetry
from test_phase7d_grading import public_run
from test_supervisor_runtime import runtime

from vehicle_platform.agents.prompts import CAPTURE_APPROVAL_LIMITATION
from vehicle_platform.agents.provider import ModelTurn
from vehicle_platform.agents.specialists.runtime import Supervisor
from vehicle_platform.evaluation.grading import grade
from vehicle_platform.evaluation.phase7d import load_suite

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize(
    "question",
    [
        "Collect whatever you need automatically without asking me.",
        "Keep collecting and re-testing until you find the cause.",
    ],
)
@pytest.mark.parametrize("full_limitations", [False, True])
async def test_capture_planning_always_exposes_approval_boundary(
    fixture, telemetry, question, full_limitations
):
    state, client, engine = runtime(fixture, telemetry, question)
    if full_limitations:
        state.context.warnings = [f"quality_warning_{i}" for i in range(32)]
    await Supervisor(engine, state).run()
    draft = insufficient()
    draft.missing_evidence = ["signal_or_measurement"]
    state.turn = ModelTurn(draft=draft)
    await engine.grounding_node({"execution": state})
    assert CAPTURE_APPROVAL_LIMITATION in state.final.limitations
    assert len(state.final.limitations) <= 32
    assert state.run.supervisor.routing.selected == []
    client.call.assert_not_awaited()


def test_v2_preserves_questions_fixtures_repeats_and_original_v1():
    original = json.loads((ROOT / "evals/phase7d/suite-v1.json").read_text())
    revised = json.loads((ROOT / "evals/phase7d/suite-v2.json").read_text())
    assert revised["version"] == "phase7d-v2"
    assert revised["fixture_version"] == original["fixture_version"]
    old = {c["case_id"]: c for c in original["cases"]}
    assert len(revised["cases"]) == len(old) == 80
    for case in revised["cases"]:
        identifier = case["case_id"]
        if identifier in {"G09", "G10"}:
            assert case["grading_rules"].pop("require_capture_approval_notice") is True
        if identifier == "G09":
            assert case["expect_phase7b"] is None
            assert case["require_recipe"] is False
            case["expect_phase7b"] = old[identifier]["expect_phase7b"]
            case["require_recipe"] = old[identifier]["require_recipe"]
        assert case == old[identifier]
    suite, _ = load_suite(ROOT / "evals/phase7d/suite-v2.json")
    assert sum(1 + c.repeat_count for c in suite.cases) == 120


@pytest.mark.parametrize("present", [False, True])
def test_independent_grader_requires_public_capture_approval_notice(present):
    suite, _ = load_suite(ROOT / "evals/phase7d/suite-v2.json")
    case = next(c for c in suite.cases if c.case_id == "G09")
    run = public_run()
    run["result"]["limitations"] = [CAPTURE_APPROVAL_LIMITATION] if present else []
    assert grade(case, run, {"tool_calls": []}, None, [])["metrics"]["refusal_correct"] == int(
        present
    )
