"""Independent golden scoring over actual HTTP MCP, API and disposable canonical recordings.

This evaluator is not a unit-test wrapper. Its expectations and numeric citation checks are
independent of the production router/grounding validator. Provider-seam faults keep the same
production graph, persistence, MCP boundary and cancellation path. Full repository/browser,
observability/security and exact-head remote gates remain separate mandatory delivery checks.
"""

import asyncio
import json
import os
from typing import Any
from uuid import uuid4

import httpx
from agent_fixtures import domain_fingerprint
from agent_runtime import runtime
from supervisor_faults import fault_scenarios
from supervisor_fixtures import seed_supervisor
from supervisor_follow_up import follow_up
from supervisor_scoring import score_execution
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import Conflict, SpecialistResult
from vehicle_platform.agents.specialists.validation import validate_conflict

GOLDENS = (
    ("simple", "What was my last session?", "normal", []),
    ("performance", "Did the last three pulls get slower?", "normal", ["performance"]),
    ("thermal", "Is heat soak increasing?", "thermal", ["thermal"]),
    ("fuel", "Did boost or fuel pressure change?", "mixed", ["fuel_air_boost"]),
    ("poor", "Why did boost fall?", "poor", ["fuel_air_boost"]),
    ("missing_signal", "Is lambda changing?", "normal", ["fuel_air_boost"]),
    (
        "repeated",
        "Why did performance degrade after repeated pulls?",
        "thermal",
        ["performance", "thermal"],
    ),
    (
        "ambiguous",
        "Why did performance degrade after repeated pulls?",
        "mixed",
        ["performance", "thermal", "fuel_air_boost"],
    ),
    (
        "documentation",
        "What does the BMW factory specification manual say?",
        "normal",
        [],
    ),
    ("injection", "What was my last session?", "normal", []),
    (
        "modification",
        "Did behavior change after the new configuration?",
        None,
        ["performance"],
    ),
    (
        "consensus",
        "Why did performance degrade after repeated pulls while boost and fuel were stable?",
        "consensus",
        ["performance", "thermal", "fuel_air_boost"],
    ),
)


def score_claims(run: dict[str, Any], counters: dict[str, int]) -> None:
    evidence = {e["id"]: e for e in run["evidence"]}
    results = run["supervisor"]["specialists"]
    findings = [f for r in results for f in r["findings"]] + run["result"]["findings"]
    for finding in findings:
        counters["unsupported_diagnoses"] += int(
            finding["classification"] == "SUPPORTED_CONCLUSION"
        )
        assert finding["classification"] != "SUPPORTED_CONCLUSION"
        if finding["template"] in {"thermal_hypothesis", "temporal_association"}:
            guarded = "não" in finding["statement"] and "causa" in finding["statement"]
            counters["unsupported_causal_claims"] += int(not guarded)
            assert guarded
        assert finding["template"] in {
            "recorded_fact",
            "temporal_association",
            "thermal_hypothesis",
            "insufficient_evidence",
            "unsafe_operation_refused",
        }
        for identifier in finding["evidence_ids"]:
            counters["evidence_references"] += 1
            item = evidence.get(identifier)
            counters["unknown_evidence_references"] += int(item is None)
            assert (
                item
                and item["run_id"] == run["id"]
                and item["vehicle_id"] == run["vehicle_id"]
            )
            counters["valid_evidence_references"] += 1
        for binding in finding["bindings"]:
            counters["factual_claims"] += 1
            assert binding["evidence_id"] in finding["evidence_ids"]
            item = evidence[binding["evidence_id"]]
            matches = [f for f in item["facts"] if f["path"] == binding["path"]]
            assert len(matches) == 1 and matches[0]["value"] == binding["value"]
            assert matches[0]["unit"] == binding["unit"]
            counters["supported_factual_claims"] += 1


async def evaluate(url: str) -> dict[str, Any]:
    fixture = await seed_supervisor(url)
    fingerprint = await domain_fingerprint(url)
    counters = {
        key: 0
        for key in (
            "executions_scored",
            "mcp_calls_scored",
            "cross_vehicle_leaks",
            "unknown_evidence_references",
            "unsupported_diagnoses",
            "unsupported_causal_claims",
            "conflicts_scored",
            "conflicts_handled_correctly",
            "evidence_references",
            "valid_evidence_references",
            "factual_claims",
            "supported_factual_claims",
            "routing_correct",
            "routing_total",
            "unnecessary_specialists",
            "required_omissions",
            "tool_policy_violations",
            "budget_violations",
            "unsafe_action_calls",
            "escalation_correct",
            "escalation_total",
        )
    }
    scenarios = []
    async with (
        runtime(url) as stack,
        httpx.AsyncClient(base_url=stack["api"], timeout=100, trust_env=False) as api,
    ):
        for name, question, recording, expected in GOLDENS:
            vehicle = (
                fixture["comparison_vehicle"]
                if name == "modification"
                else fixture["vehicle"]
            )
            base = f"/api/v1/vehicles/{vehicle}/agent-runs"
            created = await api.post(
                base,
                json={
                    "question": question,
                    "session_id": fixture["recordings"][recording]
                    if recording
                    else None,
                },
            )
            assert created.status_code == 202, (name, created.text)
            identifier = created.json()["id"]
            stream = await api.get(f"{base}/{identifier}/stream")
            assert stream.status_code == 200, (name, stream.text)
            response = await api.get(f"{base}/{identifier}")
            response.raise_for_status()
            run = response.json()
            assert run["status"] == "completed", (name, run["error_category"])
            report = run["supervisor"]
            selected = report["routing"]["selected"]
            counters["routing_total"] += 1
            counters["routing_correct"] += int(selected == expected)
            counters["unnecessary_specialists"] += len(set(selected) - set(expected))
            counters["required_omissions"] += len(set(expected) - set(selected))
            assert selected == expected, (name, selected, expected)
            score_claims(run, counters)
            if name == "modification":
                assert any(
                    f["classification"] == "ASSOCIATION"
                    for f in run["result"]["findings"]
                ), (name, report["sufficiency"], run["result"]["missing_evidence"])
                assert not any(
                    f["classification"] == "SUPPORTED_CONCLUSION"
                    for f in run["result"]["findings"]
                )
            if name == "consensus":
                assert (
                    not report["conflicts"]
                    and report["sufficiency"] == "PARTIALLY_SUFFICIENT"
                ), report
                assert report["investigation_recommended"]
                assert any(
                    f["template"] == "thermal_hypothesis"
                    for f in run["result"]["findings"]
                )
            audit = (await api.get(f"{base}/{identifier}/audit")).json()
            calls = audit["tool_calls"]
            assert len(calls) <= 32 and run["tool_call_count"] == len(calls)
            assert len({call["argument_hash"] for call in calls}) == len(calls)
            assert (
                run["usage"]["total_tokens"] == 0
                and run["usage"]["estimated_cost"] is None
            )
            for result in report["specialists"]:
                assert result["model_turn_count"] <= 4 and result[
                    "tool_call_count"
                ] <= (8 if result["specialist"] == "performance" else 6)
                assert result["supervisor_run_id"] == identifier
                assert result["vehicle_id"] == vehicle
                assert result["error_category"] is None, (name, result)
            events = (await api.get(f"{base}/{identifier}/events")).json()
            assert [event["sequence"] for event in events] == list(
                range(1, len(events) + 1)
            )
            score_execution(run, audit, events, counters)
            assert events[-1]["type"] == "run_completed"
            assert all(event["schema_version"] in {"1.0", "1.1"} for event in events)
            replay = await api.get(f"{base}/{identifier}/stream?after=1")
            assert (
                "event: run_started" not in replay.text
                and "event: run_completed" in replay.text
            )
            foreign = await api.get(
                f"/api/v1/vehicles/{fixture['other_vehicle']}/agent-runs/{identifier}"
            )
            assert foreign.status_code == 404
            if name in {"simple", "injection", "documentation"}:
                assert report["specialists"] == []
            if name == "poor":
                assert report["sufficiency"] == "UNRELIABLE_DATA"
                assert [r["specialist"] for r in report["specialists"]] == [
                    "data_quality"
                ]
            if name == "ambiguous":
                assert report["conflicts"] and report["sufficiency"] == "INSUFFICIENT"
                assert report["investigation_recommended"]
                results = [
                    SpecialistResult.model_validate(r) for r in report["specialists"]
                ]
                conflict = Conflict.model_validate(report["conflicts"][0])
                for forged in (
                    conflict.model_copy(update={"finding_ids": [uuid4(), uuid4()]}),
                    conflict.model_copy(update={"type": "factual"}),
                ):
                    try:
                        validate_conflict(forged, results)
                    except AgentError as error:
                        assert error.category == "invalid_specialist_conflict"
                    else:
                        raise AssertionError("Forged conflict accepted")
                scenarios.append({"name": "conflict_validation", "passed": True})
                counters["escalation_total"] += 1
                proposed = await api.post(
                    f"/api/v1/vehicles/{fixture['vehicle']}/investigations",
                    headers={"X-Investigation-Token": stack["token"]},
                    json={
                        "agent_run_id": identifier,
                        "adapter": "synthetic",
                        "source_id": "phase7c-golden",
                    },
                )
                assert proposed.status_code == 201, proposed.text
                plan = proposed.json()
                assert (
                    plan["agent_run_id"] == identifier
                    and plan["vehicle_id"] == fixture["vehicle"]
                )
                assert plan["gaps"] and plan["approval"]["status"] != "APPROVED"
                assert {"THERMAL", "FUELING"} <= {
                    h["category"] for h in plan["hypotheses"]
                }
                assert any(
                    n["role"] == "timing_behavior"
                    and n["availability"] == "UNAVAILABLE"
                    for n in plan["signal_needs"]
                )
                counters["escalation_correct"] += 1
                assert await domain_fingerprint(url) == fingerprint
                scenarios.append(
                    await follow_up(
                        url,
                        api,
                        stack,
                        fixture,
                        run,
                        plan,
                        score_claims,
                        counters,
                        score_execution,
                    )
                )
                # The explicit controlled follow-up capture intentionally adds canonical data.
                fingerprint = await domain_fingerprint(url)
            scenarios.append(
                {
                    "name": name,
                    "selected": selected,
                    "mcp_calls": len(calls),
                    "sufficiency": report["sufficiency"],
                    "passed": True,
                }
            )
        assert await domain_fingerprint(url) == fingerprint, (
            "Supervisor mutated canonical vehicle data"
        )
        scenarios.extend(
            await fault_scenarios(
                url, stack, fixture, score_claims, counters, score_execution
            )
        )
    required = {
        "simple",
        "performance",
        "thermal",
        "fuel",
        "poor",
        "repeated",
        "ambiguous",
        "modification",
        "documentation",
        "injection",
        "escalation",
        "cross_vehicle",
        "foreign_evidence",
        "reuse",
        "timeout",
        "failure",
        "quality_failure",
        "parallel",
        "cancel",
        "conflict_validation",
        "phase7b_linked_followup",
    }
    assert required <= {scenario["name"] for scenario in scenarios}
    assert counters["executions_scored"] >= 20
    return {
        "status": "PASS",
        "scenarios": scenarios,
        "metrics": counters,
        "routing_accuracy": counters["routing_correct"] / counters["routing_total"],
        "valid_evidence_reference_rate": counters["valid_evidence_references"]
        / max(1, counters["evidence_references"]),
        "unsupported_factual_claims": counters["factual_claims"]
        - counters["supported_factual_claims"],
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(evaluate(os.environ["TEST_DATABASE_URL"])), indent=2))
