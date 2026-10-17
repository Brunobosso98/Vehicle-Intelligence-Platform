from copy import deepcopy
from pathlib import Path

import pytest

from vehicle_platform.evaluation.grading import grade, summarize
from vehicle_platform.evaluation.phase7d import load_suite

SUITE = load_suite(Path(__file__).resolve().parents[4] / "evals/phase7d/suite-v1.json")[0]


def case(identifier):
    return next(c for c in SUITE.cases if c.case_id == identifier)


def public_run():
    evidence = {
        "id": "e",
        "run_id": "r",
        "vehicle_id": "v",
        "source_tool": "get_session_summary",
        "facts": [{"path": "/started_at", "value": 4.2, "unit": "s"}],
    }
    finding = {
        "classification": "OBSERVATION",
        "template": "recorded_fact",
        "evidence_ids": ["e"],
        "bindings": [{"evidence_id": "e", "path": "/started_at", "value": 4.2, "unit": "s"}],
        "statement": "Início da sessão: 4.2 s",
    }
    return {
        "id": "r",
        "vehicle_id": "v",
        "status": "completed",
        "evidence": [evidence],
        "supervisor": {"routing": {"intent": "factual"}, "specialists": []},
        "result": {
            "answer": "Início da sessão: 4.2 s",
            "findings": [finding],
            "missing_evidence": [],
            "context": {
                "as_of": "2026-10-12T00:00:00+00:00",
                "active_configuration_id": "c",
                "configurations": [
                    {"id": "c", "effective_at": "2026-01-01T00:00:00+00:00", "ended_at": None}
                ],
                "sessions": [
                    {
                        "temporal_configuration_valid": True,
                        "configuration_id": "c",
                        "started_at": "2026-10-11T00:00:00+00:00",
                        "recorded_modification_ids": [],
                    }
                ],
                "modifications": [],
            },
        },
    }


def test_independent_numeric_grading_and_safe_fast_path():
    scored = grade(case("A01"), public_run(), {"tool_calls": []}, None, [])
    assert scored["status"] == "PASS"
    assert scored["metrics"]["valid_references"] == 1
    assert scored["metrics"]["supported_factual_claims"] == 1
    assert scored["signature"]["safety"]


@pytest.mark.parametrize(
    "mode,metric",
    [
        ("unit", "unsupported_factual_claims"),
        ("number", "unsupported_factual_claims"),
        ("unknown", "invalid_evidence_references"),
        ("foreign", "cross_vehicle_leaks"),
        ("diagnosis", "unsupported_diagnoses"),
        ("causal", "unsupported_causal_claims"),
        ("signal", "invented_signals"),
        ("classification", "unsupported_factual_claims"),
        ("template", "unsupported_factual_claims"),
    ],
)
def test_forged_public_outputs_are_never_passes(mode, metric):
    run = public_run()
    finding = run["result"]["findings"][0]
    if mode == "unit":
        finding["bindings"][0]["unit"] = "K"
    if mode == "number":
        finding["bindings"][0]["value"] = 999
    if mode == "unknown":
        finding["evidence_ids"] = ["fake"]
    if mode == "foreign":
        run["evidence"][0]["vehicle_id"] = "another-vehicle"
    if mode == "diagnosis":
        finding["classification"] = "SUPPORTED_CONCLUSION"
    if mode == "causal":
        finding.update(
            template="temporal_association",
            classification="ASSOCIATION",
            statement="The part caused the improvement.",
        )
    if mode == "signal":
        finding["bindings"][0]["path"] = "/timing/signal"
    if mode == "classification":
        finding["classification"] = "HYPOTHESIS"
    if mode == "template":
        finding["template"] = "invented"
    scored = grade(case("A01"), run, {"tool_calls": []}, None, [])
    assert scored["status"] == "SEMANTIC_FAILURE" and scored["metrics"][metric] > 0


def test_failed_forbidden_attempts_and_successful_bypass_are_separate():
    run = public_run()
    audit = {
        "tool_calls": [
            {"tool_name": "write_ecu", "status": "failed", "argument_hash": "x"},
            {"tool_name": "execute_sql", "status": "completed", "argument_hash": "x"},
        ]
    }
    result = grade(case("H04"), run, audit, None, [{"requested_tools": ["write_ecu"]}])
    assert result["metrics"]["unsafe_action_attempts"] == 1
    assert result["metrics"]["tool_policy_bypass"] == 1
    assert result["metrics"]["duplicate_calls"] == 1


def test_missing_specialists_insufficiency_tools_and_recipe_fail():
    result = grade(case("G02"), public_run(), {"tool_calls": []}, None, [])
    assert result["status"] == "SEMANTIC_FAILURE"
    assert not result["metrics"]["insufficiency_correct"]
    assert not result["metrics"]["escalation_correct"]
    assert not result["metrics"]["signal_needs_correct"]
    assert not result["metrics"]["recipe_correct"]
    performance = grade(case("B01"), public_run(), {"tool_calls": []}, None, [])
    assert performance["metrics"]["missing_specialists"] == 2
    assert (
        grade(case("A06"), public_run(), {"tool_calls": []}, None, [])["metrics"][
            "required_tools_missing"
        ]
        == 1
    )


def test_real_phase7b_provenance_and_approval_constraints():
    run = public_run()
    run["result"]["findings"] = [
        {
            "classification": "INSUFFICIENT_EVIDENCE",
            "template": "insufficient_evidence",
            "evidence_ids": [],
            "bindings": [],
            "statement": (
                "As evidências disponíveis são insuficientes para determinar a causa mecânica "
                "ou responder à questão com segurança."
            ),
        }
    ]
    run["result"]["answer"] = run["result"]["findings"][0]["statement"]
    run["result"]["missing_evidence"] = ["signal_or_measurement"]
    plan = {
        "vehicle_id": "v",
        "approval": {"status": "REQUIRED"},
        "status": "AWAITING_APPROVAL",
        "gaps": [{"category": "signal_or_measurement", "why_it_matters": "Distinguish hypotheses"}],
        "signal_needs": [
            {
                "role": "timing_behavior",
                "canonical_signal": "engine.ignition_timing",
                "availability": "UNAVAILABLE",
            }
        ],
        "recipe": {
            "configuration_hash": "hash",
            "sampling_algorithm_version": "1.1",
            "feasibility": "PARTIALLY_FEASIBLE",
        },
        "capability_snapshot": {"signals": {}},
    }
    scored = grade(case("G02"), run, {"tool_calls": []}, plan, [])
    assert scored["status"] == "PASS"
    forged = deepcopy(plan)
    forged["approval"]["status"] = "APPROVED"
    forged["signal_needs"][0]["availability"] = "AVAILABLE"
    forged["vehicle_id"] = "foreign"
    scored = grade(case("G02"), run, {"tool_calls": []}, forged, [])
    assert scored["metrics"]["approval_bypass"] == 1
    assert scored["metrics"]["invented_signals"] == 2
    assert scored["metrics"]["cross_vehicle_leaks"] == 1


def test_tool_and_specialist_budget_overflow_and_incomplete_run():
    run = public_run()
    run["status"] = "failed"
    run["error_category"] = "BUDGET_VIOLATION"
    calls = [{"tool_name": "get_telemetry_window", "argument_hash": str(i)} for i in range(44)]
    scored = grade(case("A01"), run, {"tool_calls": calls}, None, [])
    assert scored["metrics"]["budget_violations"] == 1
    assert "BUDGET_VIOLATION" in scored["failures"]


def test_empty_report_never_implies_observed_safety_or_validation():
    report = summarize({"round": 1, "results": {}, "calls": {}, "rates": {}, "identities": []})
    assert report["status"] == "NOT VERIFIED"
    assert report["routing_accuracy"] is None and report["evidence_reference_validity"] is None
    assert report["latency_seconds"] == {"p50": None, "p95": None, "p99": None}


def test_aggregation_stability_unknown_usage_and_review_shortlist():
    results = {}
    for question, repeat in SUITE.schedule():
        scored = grade(question, public_run(), {"tool_calls": []}, None, [])
        scored["latency_seconds"] = 1 + repeat
        results[f"1:{question.case_id}:{repeat}"] = scored
    calls = {
        "call": {
            "role": "performance",
            "status": "completed",
            "cost": {"total": "0.01"},
            "usage": {
                "input_tokens": 100,
                "cached_input_tokens": 20,
                "output_tokens": 50,
                "reasoning_tokens": 10,
            },
        },
        "failed": {
            "role": "performance",
            "status": "failed",
            "error_category": "provider_timeout",
            "case_key": "1:B01:0",
            "cost": {"total": "0.02"},
            "usage": None,
        },
    }
    report = summarize(
        {"round": 1, "results": results, "calls": calls, "rates": {}, "identities": []}
    )
    assert report["unique_cases_executed"] == 80 and report["critical_repeats_executed"] == 40
    assert report["usage"]["reasoning_tokens"] == 10 and report["cache_ratio"] == 0.2
    assert report["stability"]["safety"]["measured"] == 20
    assert report["provider_failures"] == 1 and report["unknown_usage_calls"] == 1
    assert all(len(v) <= 5 for v in report["human_review_shortlist"].values())
    assert set(report["per_category"]) == set("ABCDEFGH")
    assert report["per_specialist_usage"]["performance"]["calls"] == 2
    assert report["status"] == "NOT VERIFIED"


def test_per_case_cost_keeps_prior_rounds_smoke_and_unknown_reservations():
    calls = {
        str(index): {
            "case_key": key,
            "role": "agent",
            "status": "completed",
            "cost": {"total": cost},
            "usage": usage,
        }
        for index, (key, cost, usage) in enumerate(
            [
                ("smoke", "0.00000001", {"input_tokens": 1}),
                ("1:A01:0", "0.1", {"input_tokens": 10, "cached_input_tokens": 2}),
                ("1:A01:0", "0.2", None),
                ("2:A01:0", "0.05", {"input_tokens": 20, "output_tokens": 3}),
            ]
        )
    }
    report = summarize({"round": 2, "results": {}, "calls": calls, "rates": {}, "identities": []})
    prior = report["per_case_usage"]["1:A01:0"]
    assert prior["cost_usd"] == "0.3"
    assert prior["calls"] == 2 and prior["unknown_usage_calls"] == 1
    assert prior["input_tokens"] == 10 and prior["cached_input_tokens"] == 2
    assert report["per_case_usage"]["smoke"]["cost_usd"] == "0.00000001"
    assert report["per_case_usage"]["2:A01:0"]["output_tokens"] == 3
    assert report["per_category_usage"]["A"]["calls"] == 1
    assert report["aggregation_scopes"]["quality_and_category"] == "current_round"
    assert report["aggregation_scopes"]["usage_role_case_and_spend"] == "all_rounds_including_smoke"
    assert report["status"] == "NOT VERIFIED"


def test_removed_modification_and_configuration_boundaries_are_independent():
    from vehicle_platform.evaluation.grading import temporal_checks

    context = public_run()["result"]["context"]
    context["modifications"] = [
        {
            "id": "old",
            "configuration_id": "c",
            "installed_at": "2026-01-02T00:00:00+00:00",
            "removed_at": "2026-10-10T00:00:00+00:00",
            "active_at_context": False,
        }
    ]
    assert temporal_checks(context) == (True, True)
    context["sessions"][0]["recorded_modification_ids"] = ["old"]
    assert temporal_checks(context) == (True, False)
    context["sessions"][0]["configuration_id"] = "wrong"
    assert temporal_checks(context) == (False, False)
    context["as_of"] = "invalid"
    assert temporal_checks(context) == (False, False)
    context["as_of"] = "2026-10-12T00:00:00"
    assert temporal_checks(context) == (False, False)


def test_unrelated_fact_and_appended_diagnosis_cannot_answer_the_question():
    run = public_run()
    run["result"]["findings"][0]["bindings"][0]["path"] = "/unrelated"
    run["evidence"][0]["facts"][0]["path"] = "/unrelated"
    result = grade(case("A01"), run, {"tool_calls": []}, None, [])
    assert not result["metrics"]["question_evidence_coverage"]
    run = public_run()
    run["result"]["findings"][0]["statement"] += ". The HPFP has failed."
    result = grade(case("A01"), run, {"tool_calls": []}, None, [])
    assert result["metrics"]["unsupported_factual_claims"] > 0
    assert not result["metrics"]["public_answer_integrity"]


def test_unsafe_question_requires_a_public_refusal():
    result = grade(case("H04"), public_run(), {"tool_calls": []}, None, [])
    assert not result["metrics"]["refusal_correct"]


def test_skipped_observations_are_not_counted_as_real_executions():
    report = summarize(
        {
            "round": 1,
            "results": {"1:A01:0": {"status": "NOT_RUN_EXTERNAL_BLOCKER"}},
            "calls": {},
            "rates": {},
            "identities": [],
        }
    )
    assert report["unique_cases_executed"] == 0
    assert report["critical_repeats_executed"] == 0
    assert not report["real_provider_receipts_complete"]


def test_report_applies_the_specified_thresholds_without_requiring_perfect_routes():
    from vehicle_platform.evaluation.grading import BLOCKERS, QUALITY_REQUIREMENTS

    results = {}
    calls = {}
    for index, (question, repeat) in enumerate(SUITE.schedule()):
        key = f"1:{question.case_id}:{repeat}"
        results[key] = {
            "status": "SEMANTIC_FAILURE" if index < 4 else "PASS",
            "run_completed": True,
            "case_id": question.case_id,
            "category": question.category,
            "critical": question.critical,
            "metrics": dict.fromkeys(BLOCKERS, 0)
            | dict.fromkeys(QUALITY_REQUIREMENTS, 1)
            | {
                "routing_correct": int(index >= 4),
                "strict_routing_correct": int(index >= 4),
                "strict_routing_designated": 1,
                "required_specialists": 2,
                "recalled_specialists": 2,
                "selected_specialists": 2,
                "necessary_specialists": 2,
                "references": 1,
                "valid_references": 1,
                "escalation_designated": 1,
                "escalation_correct": 1,
            },
            "signature": dict(
                route="factual",
                specialists=[],
                safety=True,
                insufficient=False,
                escalation=False,
                classification=["OBSERVATION"],
            ),
        }
        calls[key] = {
            "case_key": key,
            "role": "agent",
            "status": "completed",
            "cost": {"total": "0.0001"},
            "model": "gpt-6-luna",
            "service_tier": "flex",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
    state = {
        "round": 1,
        "results": results,
        "calls": calls,
        "rates": {},
        "smoke": {"status": "PASS"},
        "identities": [
            {
                "provider": "openai",
                "model": "gpt-6-luna",
                "service_tier": "flex",
                "reasoning_effort": "low",
            }
        ],
    }
    report = summarize(state)
    assert report["status"] == "EVALUATION_PASS"
    assert report["routing_accuracy"] == pytest.approx(116 / 120)
    results["1:A01:0"]["metrics"]["signal_needs_correct"] = 0
    assert summarize(state)["status"] == "NOT VERIFIED"
    results["1:A01:0"]["metrics"]["signal_needs_correct"] = 1
    state["global_blocker"] = "canonical_data_mutated"
    assert summarize(state)["status"] == "NOT VERIFIED"
    state.pop("global_blocker")
    state["calls"].pop(next(iter(calls)))
    assert summarize(state)["status"] == "NOT VERIFIED"


def test_absent_failed_answer_does_not_fabricate_a_factual_violation():
    run = {
        "id": "r",
        "vehicle_id": "v",
        "status": "failed",
        "error_category": "invalid_supervisor_routing",
    }
    result = grade(case("A01"), run, {"tool_calls": []}, None, [])
    assert result["status"] == "SEMANTIC_FAILURE"
    assert result["metrics"]["unsupported_factual_claims"] == 0
    assert "invalid_supervisor_routing" in result["failures"]


def test_strict_selection_and_required_participation_are_distinct():
    run = public_run()
    run["supervisor"] = {
        "routing": {
            "intent": "performance",
            "selected": ["performance"],
            "data_quality_gate": True,
        },
        "specialists": [{"specialist": "data_quality"}],
    }
    result = grade(case("B01"), run, {"tool_calls": []}, None, [])
    assert result["metrics"]["strict_routing_correct"] == 1
    assert result["metrics"]["routing_correct"] == 0
    assert result["metrics"]["recalled_specialists"] == 1
    assert result["metrics"]["required_specialists"] == 2


def test_unrun_cases_do_not_change_observed_quality_rates():
    state = {
        "round": 1,
        "identities": [],
        "rates": {},
        "calls": {},
        "results": {
            "1:A01:0": {
                "status": "PASS",
                "metrics": {"routing_correct": 1, "selected_specialists": 2},
            },
            "1:A02:0": {"status": "NOT_RUN_EXTERNAL_BLOCKER"},
        },
    }
    report = summarize(state)
    assert report["quality_observations_measured"] == 1
    assert report["routing_accuracy"] == 1
    assert report["average_specialists_per_case"] == 2
    assert report["status"] == "NOT VERIFIED"


def documentary_run():
    from test_knowledge import retrieval_fixture

    from vehicle_platform.knowledge.grounding import render, report

    run = public_run()
    knowledge = report(retrieval_fixture(), hybrid=True)
    run["agent_version"] = "phase8-v1"
    run["vehicle_id"] = str(knowledge.retrieval.scope.vehicle_id)
    run["evidence"][0]["vehicle_id"] = run["vehicle_id"]
    run["result"]["knowledge"] = knowledge.model_dump(mode="json")
    run["result"]["answer"] += "\n\n" + render(knowledge)
    return run


def test_phase8_documentary_envelope_preserves_legacy_vehicle_grading():
    run = documentary_run()
    scored = grade(case("A01"), run, {"tool_calls": []}, None, [])
    assert scored["status"] == "PASS"
    assert scored["metrics"]["public_answer_integrity"] == 1
    assert scored["metrics"]["supported_factual_claims"] == 1


@pytest.mark.parametrize(
    "attack",
    [
        "vehicle",
        "source",
        "source_version",
        "index",
        "citation",
        "normative",
        "schema",
        "version",
        "extra_text",
    ],
)
def test_documentary_attachment_cannot_launder_forged_public_outputs(attack):
    from uuid import uuid4

    run = documentary_run()
    knowledge = run["result"]["knowledge"]
    evidence = knowledge["retrieval"]["evidence"][0]
    if attack == "vehicle":
        knowledge["retrieval"]["scope"]["vehicle_id"] = str(uuid4())
    elif attack == "source":
        evidence["source"]["id"] = str(uuid4())
    elif attack == "source_version":
        evidence["document"]["source_version"] += 1
    elif attack == "index":
        evidence["index_id"] = "unrelated-index"
    elif attack == "citation":
        knowledge["claims"][0]["evidence_id"] = str(uuid4())
    elif attack == "normative":
        knowledge["claims"][0]["normative"] = True
    elif attack == "schema":
        run["result"]["knowledge"] = {"untrusted": True}
    elif attack == "version":
        run["agent_version"] = "phase7d-v1"
    else:
        run["result"]["answer"] += " Unsupported extra conclusion."
    scored = grade(case("A01"), run, {"tool_calls": []}, None, [])
    assert scored["status"] == "SEMANTIC_FAILURE"
    assert scored["metrics"]["public_answer_integrity"] == 0
    assert scored["metrics"]["unsupported_factual_claims"] > 0
