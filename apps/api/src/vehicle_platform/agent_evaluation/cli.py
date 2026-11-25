"""Operator interface for frozen Phase 11 scenarios and independent receipts."""

import argparse
import asyncio
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from vehicle_platform.agent_evaluation.contracts import (
    AgentEvalCase,
    CaseAttempt,
    EvalReceipt,
    OracleFact,
)
from vehicle_platform.agent_evaluation.corpus import CorpusError, load_corpus, summarize
from vehicle_platform.agent_evaluation.journal import verify_attempt_journal
from vehicle_platform.agent_evaluation.phase7d_history import load_phase7d_history
from vehicle_platform.agent_evaluation.receipts import verify_receipt
from vehicle_platform.agent_evaluation.source_oracle import (
    agent_run_count_for_question,
    is_disposable_database_url,
    persisted_agent_run,
    persisted_investigation_state,
    resolve_case_facts,
    resolve_prediction_evidence_facts,
    schema_revision,
    source_digest,
    source_signal_present,
)
from vehicle_platform.agent_evaluation.thresholds import load_threshold_policy, score_thresholds

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SUITE = ROOT / "evals/phase11/suite-v46.json"
GIT = shutil.which("git")


def _json(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 2_000_000:
        raise ValueError("receipt_too_large")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("receipt must be an object")
    return value


def _latest_receipt() -> Path | None:
    directory = ROOT / ".validation/phase11/receipts"
    receipts = sorted(directory.glob("*.json"), key=lambda path: path.stat().st_mtime_ns)
    return receipts[-1] if receipts else None


async def _source_presence_mismatches(
    attempts: list[dict[str, Any]], cases: tuple[Any, ...], database_url: str
) -> list[str]:
    case_by_id = {case.case_id: case for case in cases}
    mismatches: list[str] = []
    for attempt in attempts:
        case = case_by_id.get(attempt.get("case_id"))
        if case is None or not case.expected_absent_signals:
            continue
        vehicle_id = attempt.get("selected_vehicle_id")
        if not vehicle_id:
            mismatches.extend(
                f"{case.case_id}:{signal}:vehicle_missing"
                for signal in case.expected_absent_signals
            )
            continue
        for signal in case.expected_absent_signals:
            if await source_signal_present(database_url, vehicle_id, signal):
                mismatches.append(f"{case.case_id}:{signal}")
    return mismatches


def _receipt_argument(
    parser: argparse.ArgumentParser, args: Any
) -> tuple[dict[str, Any], EvalReceipt]:
    path = args.receipt or _latest_receipt()
    if path is None:
        parser.error(f"{args.command} requires --receipt or a saved Phase 11 receipt")
    try:
        raw = _json(path)
        receipt = EvalReceipt.model_validate(raw)
    except Exception as exc:
        parser.error(f"invalid receipt: {exc}")
    return raw, receipt


def _coverage_outcomes(
    cases: tuple[AgentEvalCase, ...], attempts: list[dict[str, Any]]
) -> dict[str, Any]:
    attempt_by_id = {
        str(item.get("case_id")): item
        for item in attempts
        if isinstance(item, dict) and isinstance(item.get("case_id"), str)
    }
    dimensions: dict[str, Callable[[AgentEvalCase], str]] = {
        "family": lambda case: case.family.value,
        "severity": lambda case: case.severity.value,
        "language": lambda case: case.language,
        "source_surface": lambda case: case.source_surface,
        "attack_family": lambda case: case.attack_family or "none",
        "route": lambda case: case.expected_route or "none",
        "source_role": lambda case: case.source_role,
    }
    output: dict[str, Any] = {}
    for dimension, value_for in dimensions.items():
        dimension_buckets: dict[str, dict[str, Any]] = {}
        for case in cases:
            category = value_for(case)
            bucket = dimension_buckets.setdefault(
                category, {"cases": 0, "status_counts": Counter()}
            )
            bucket["cases"] += 1
            attempt = attempt_by_id.get(case.case_id)
            status = str(attempt.get("status", "NOT_RUN")) if attempt else "NOT_RUN"
            bucket["status_counts"][status] += 1
        output[dimension] = {
            category: {
                "cases": bucket["cases"],
                "status_counts": dict(sorted(bucket["status_counts"].items())),
            }
            for category, bucket in sorted(dimension_buckets.items())
        }
    observed_routes: dict[str, Counter[str]] = {}
    for case in cases:
        attempt = attempt_by_id.get(case.case_id)
        route = str(attempt.get("observed_route") or "unobserved") if attempt else "unobserved"
        bucket = observed_routes.setdefault(route, Counter())
        bucket[str(attempt.get("status", "NOT_RUN")) if attempt else "NOT_RUN"] += 1
    output["observed_route"] = {
        route: {"status_counts": dict(sorted(counts.items()))}
        for route, counts in sorted(observed_routes.items())
    }

    def membership_coverage(
        dimension: str,
        values_for_case: Callable[[AgentEvalCase], tuple[str, ...]],
    ) -> None:
        membership_buckets: dict[str, dict[str, Any]] = {}
        for case in cases:
            attempt = attempt_by_id.get(case.case_id)
            status = str(attempt.get("status", "NOT_RUN")) if attempt else "NOT_RUN"
            categories = values_for_case(case) or ("none",)
            for category in categories:
                bucket = membership_buckets.setdefault(
                    category, {"cases": 0, "status_counts": Counter()}
                )
                bucket["cases"] += 1
                bucket["status_counts"][status] += 1
        output[dimension] = {
            category: {
                "cases": bucket["cases"],
                "status_counts": dict(sorted(bucket["status_counts"].items())),
            }
            for category, bucket in sorted(membership_buckets.items())
        }

    membership_coverage("allowed_tool_scope", lambda case: case.allowed_tools)
    membership_coverage("required_tool_scope", lambda case: case.required_tools)
    membership_coverage("forbidden_tool_scope", lambda case: case.forbidden_tools)

    for dimension, key in (
        ("observed_tool", "observed_tools"),
        ("observed_specialist", "observed_specialists"),
    ):
        observed_buckets: dict[str, Counter[str]] = {}
        for case in cases:
            attempt = attempt_by_id.get(case.case_id)
            status = str(attempt.get("status", "NOT_RUN")) if attempt else "NOT_RUN"
            observed = attempt.get(key) if attempt else None
            if not isinstance(observed, (list, tuple)):
                categories: tuple[str, ...] = ("unobserved",)
            else:
                categories = tuple(sorted({str(value) for value in observed})) or ("none",)
            for category in categories:
                observed_buckets.setdefault(category, Counter())[status] += 1
        output[dimension] = {
            category: {"status_counts": dict(sorted(counts.items()))}
            for category, counts in sorted(observed_buckets.items())
        }
    return output


def _attack_attribution_summary(
    cases: tuple[AgentEvalCase, ...], attempts: list[dict[str, Any]]
) -> dict[str, dict[str, int]]:
    """Report measured defense outcomes while keeping missing evidence visible."""
    attempt_by_id = {
        str(item.get("case_id")): item
        for item in attempts
        if isinstance(item, dict) and isinstance(item.get("case_id"), str)
    }
    summary: dict[str, dict[str, int]] = {}
    for case in cases:
        if case.attack_family is None:
            continue
        bucket = summary.setdefault(
            case.attack_family,
            {
                "cases": 0,
                "attempted": 0,
                "unclassified": 0,
                "successful_compromises": 0,
                "provider_intent_observed": 0,
                "tool_schema_blocked": 0,
                "tool_schema_unmeasured": 0,
                "mcp_auth_blocked": 0,
                "mcp_auth_unmeasured": 0,
                "grounding_blocked": 0,
                "grounding_unmeasured": 0,
            },
        )
        bucket["cases"] += 1
        attempt = attempt_by_id.get(case.case_id)
        result = attempt.get("attack_result") if attempt else None
        if not isinstance(result, dict):
            bucket["unclassified"] += 1
            continue
        bucket["attempted"] += bool(result.get("attempted"))
        bucket["successful_compromises"] += bool(result.get("successful_compromise"))
        bucket["provider_intent_observed"] += result.get("provider_intent_generated") is True
        for signal in ("tool_schema", "mcp_auth", "grounding"):
            value = result.get(f"{signal}_blocked")
            bucket[f"{signal}_blocked"] += value is True
            bucket[f"{signal}_unmeasured"] += value is None
    return {family: dict(sorted(counts.items())) for family, counts in sorted(summary.items())}


def _grading_accounting(
    cases: tuple[AgentEvalCase, ...], attempts: list[dict[str, Any]]
) -> dict[str, Any]:
    """Expose coverage denominators without treating skipped or failed work as a pass."""
    attempt_groups: dict[str, list[dict[str, Any]]] = {}
    known_ids = {case.case_id for case in cases}
    unknown_attempts = 0
    for attempt in attempts:
        case_id = attempt.get("case_id")
        if not isinstance(case_id, str) or case_id not in known_ids:
            unknown_attempts += 1
            continue
        attempt_groups.setdefault(case_id, []).append(attempt)

    fully_graded_statuses = {"PASS", "ASSERTION_FAIL", "UNSAFE_ACTION_BLOCKED"}
    execution_failure_statuses = {"INFRA_FAILURE", "PROVIDER_FAILURE", "TIMED_OUT"}
    executed_statuses = (
        fully_graded_statuses
        | execution_failure_statuses
        | {
            "INCOMPLETE",
            "INSUFFICIENT_ORACLE",
        }
    )
    grouped: dict[str, dict[str, Any]] = {}
    critical: Counter[str] = Counter()
    duplicates = 0
    for case in cases:
        group = attempt_groups.get(case.case_id, [])
        if len(group) > 1:
            duplicates += len(group) - 1
            status = "DUPLICATE_ATTEMPT"
        elif not group:
            status = "NOT_RUN"
        else:
            status = str(group[0].get("status", "INCOMPLETE"))
        bucket = grouped.setdefault(
            case.severity.value,
            {
                "cases": 0,
                "attempted": 0,
                "executed": 0,
                "fully_graded": 0,
                "infrastructure_or_provider_failure": 0,
                "blocked_by_budget": 0,
                "not_run": 0,
                "incomplete_or_ungraded": 0,
                "status_counts": Counter(),
            },
        )
        bucket["cases"] += 1
        bucket["status_counts"][status] += 1
        if status != "NOT_RUN":
            bucket["attempted"] += 1
        if status in executed_statuses or any(
            str(item.get("status")) in executed_statuses
            or item.get("run_id") is not None
            or item.get("direct_probe") is not None
            for item in group
        ):
            bucket["executed"] += 1
        if status in fully_graded_statuses:
            bucket["fully_graded"] += 1
        if status in execution_failure_statuses:
            bucket["infrastructure_or_provider_failure"] += 1
        if status == "SKIPPED_BUDGET":
            bucket["blocked_by_budget"] += 1
        if status == "NOT_RUN":
            bucket["not_run"] += 1
        if status in {"INCOMPLETE", "INSUFFICIENT_ORACLE", "DUPLICATE_ATTEMPT"}:
            bucket["incomplete_or_ungraded"] += 1
        if case.severity.value == "critical":
            critical[status] += 1

    by_severity = {
        severity: {
            "cases": values["cases"],
            "attempted": values["attempted"],
            "executed": values["executed"],
            "fully_graded": values["fully_graded"],
            "infrastructure_or_provider_failure": values["infrastructure_or_provider_failure"],
            "blocked_by_budget": values["blocked_by_budget"],
            "not_run": values["not_run"],
            "incomplete_or_ungraded": values["incomplete_or_ungraded"],
            "status_counts": dict(sorted(values["status_counts"].items())),
        }
        for severity, values in sorted(grouped.items())
    }
    return {
        "suite_cases": len(cases),
        "attempt_records": len(attempts),
        "attempted": sum(value["attempted"] for value in grouped.values()),
        "executed": sum(value["executed"] for value in grouped.values()),
        "fully_graded": sum(value["fully_graded"] for value in grouped.values()),
        "infrastructure_or_provider_failures": sum(
            value["infrastructure_or_provider_failure"] for value in grouped.values()
        ),
        "blocked_by_budget": sum(value["blocked_by_budget"] for value in grouped.values()),
        "not_run": sum(value["not_run"] for value in grouped.values()),
        "incomplete_or_ungraded": sum(
            value["incomplete_or_ungraded"] for value in grouped.values()
        ),
        "duplicate_case_attempts": duplicates,
        "unknown_attempt_records": unknown_attempts,
        "critical_status_counts": dict(sorted(critical.items())),
        "by_severity": by_severity,
    }


def _latency_summary(values: list[int]) -> dict[str, int | None]:
    ordered = sorted(values)
    p95_index = max(0, (len(ordered) * 95 + 99) // 100 - 1)
    return {
        "measured_cases": len(ordered),
        "p50": ordered[(len(ordered) - 1) // 2] if ordered else None,
        "p95": ordered[p95_index] if ordered else None,
        "max": ordered[-1] if ordered else None,
    }


def _stage_latency_summaries(
    attempts: tuple[CaseAttempt, ...],
) -> dict[str, dict[str, int | None]]:
    measurements = {
        "routing": "routing_ms",
        "specialist_work": "specialist_work_ms",
        "tool_work": "tool_work_ms",
        "rag_tool_work": "rag_tool_work_ms",
    }
    return {
        stage: _latency_summary(
            [getattr(attempt, field) for attempt in attempts if getattr(attempt, field) is not None]
        )
        for stage, field in measurements.items()
    }


def _clustered_pass_rate_interval(
    cases: tuple[AgentEvalCase, ...],
    attempts: list[dict[str, Any]],
    *,
    resamples: int = 2000,
) -> dict[str, Any]:
    """Bootstrap case-group means so near-duplicate scenarios are not independent samples."""
    if resamples < 200:
        raise ValueError("cluster bootstrap requires at least 200 resamples")
    attempt_groups: dict[str, list[dict[str, Any]]] = {}
    for attempt in attempts:
        case_id = attempt.get("case_id")
        if isinstance(case_id, str):
            attempt_groups.setdefault(case_id, []).append(attempt)

    cluster_outcomes: dict[str, list[int]] = {}
    graded_cases = 0
    for case in cases:
        group = attempt_groups.get(case.case_id, [])
        if len(group) != 1:
            continue
        status = str(group[0].get("status", "INCOMPLETE"))
        if status not in {"PASS", "ASSERTION_FAIL", "UNSAFE_ACTION_BLOCKED"}:
            continue
        graded_cases += 1
        group_name = case.attack_family or f"{case.family.value}:{case.intent}"
        cluster_key = f"{group_name}:{case.vehicle_fixture}"
        cluster_outcomes.setdefault(cluster_key, []).append(int(status == "PASS"))

    cluster_rates = [
        sum(outcomes) / len(outcomes) for _cluster, outcomes in sorted(cluster_outcomes.items())
    ]
    result: dict[str, Any] = {
        "method": "percentile_cluster_bootstrap",
        "confidence_level": 0.95,
        "replicates": resamples,
        "cluster_unit": "attack_family_or_family_intent_by_vehicle_fixture",
        "cases_graded": graded_cases,
        "independent_clusters": len(cluster_rates),
        "success_definition": "independent_grader_status_PASS",
        "interpretation": "descriptive_open_corpus_only_not_stochastic_provider_reliability",
    }
    if graded_cases == 0:
        return {**result, "status": "UNDEFINED", "reason": "no_fully_graded_cases"}
    if len(cluster_rates) < 2:
        return {**result, "status": "UNDEFINED", "reason": "fewer_than_two_independent_clusters"}

    result["status"] = "DEFINED"
    result["clustered_pass_rate"] = sum(cluster_rates) / len(cluster_rates)
    rng = random.Random(0)  # noqa: S311 - deterministic statistical resampling, not cryptography
    bootstrap_rates = sorted(
        sum(rng.choice(cluster_rates) for _ in cluster_rates) / len(cluster_rates)
        for _ in range(resamples)
    )
    lower_index = max(0, (len(bootstrap_rates) * 25) // 1000)
    upper_index = min(len(bootstrap_rates) - 1, (len(bootstrap_rates) * 975) // 1000)
    result["interval_95"] = [bootstrap_rates[lower_index], bootstrap_rates[upper_index]]
    return result


def _provider_usage_summary(
    attempts: tuple[CaseAttempt, ...],
) -> dict[str, dict[str, int | float]]:
    totals: dict[str, dict[str, int | float]] = {}
    for attempt in attempts:
        for stage, usage in attempt.provider_usage.items():
            output = totals.setdefault(stage, {})
            for field in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "total_tokens",
                "estimated_cost",
            ):
                value = getattr(usage, field)
                if value is not None:
                    output[field] = output.get(field, 0) + value
    return {stage: values for stage, values in sorted(totals.items())}


def _defense_control_counts(
    cases: tuple[AgentEvalCase, ...], attempts: tuple[CaseAttempt, ...]
) -> dict[tuple[str, str, str, str], int]:
    """Count finite defense-layer labels without exporting attempt content or IDs."""
    case_by_id = {case.case_id: case for case in cases}
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for attempt in attempts:
        case = case_by_id.get(attempt.case_id)
        result = attempt.attack_result
        if case is None or case.attack_family is None or result is None:
            continue
        if result.attack_family != case.attack_family:
            continue
        for control_layer, blocked in (
            ("tool_schema", result.tool_schema_blocked),
            ("mcp_auth", result.mcp_auth_blocked),
            ("grounding", result.grounding_blocked),
        ):
            outcome = "unmeasured" if blocked is None else "blocked" if blocked else "not_blocked"
            counts[(case.attack_family, control_layer, outcome, attempt.status.value)] += 1
    return dict(counts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vehicle-agent-evals")
    parser.add_argument(
        "command",
        choices=(
            "list",
            "inspect",
            "plan",
            "run",
            "verify",
            "compare",
            "report",
            "benchmark",
            "observability",
            "history-7d",
        ),
    )
    parser.add_argument("case_id", nargs="?")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--against", type=Path)
    args = parser.parse_args(argv)
    try:
        document, cases, digest = load_corpus(args.suite)
    except CorpusError as exc:
        print(json.dumps({"status": "INVALID", "reason": str(exc)}))
        return 2
    if args.command == "history-7d":
        try:
            history = load_phase7d_history()
        except ValueError as exc:
            print(json.dumps({"status": "INVALID", "reason": str(exc)}))
            return 2
        if args.case_id is not None:
            mapping = next(
                (
                    item
                    for item in history["case_mappings"]
                    if item["legacy_case_id"] == args.case_id
                ),
                None,
            )
            if mapping is None:
                print(json.dumps({"status": "NOT_FOUND", "legacy_case_id": args.case_id}))
                return 2
            print(json.dumps({"status": "HISTORICAL_CASE_MAPPING", **mapping}, indent=2))
            return 0
        print(
            json.dumps(
                {
                    "status": "HISTORICAL_BASELINE",
                    "mapping_version": history["mapping_version"],
                    "source_suite": history["source_suite"],
                    "source_suite_sha256": history["source_suite_sha256"],
                    "case_count": len(history["case_mappings"]),
                    "scheduled_slots": history["historical_observations"]["scheduled_slots"],
                    "historical_observations": history["historical_observations"],
                    "comparison_policy": history["comparison_policy"],
                },
                indent=2,
            )
        )
        return 0
    if args.command == "list":
        print(
            json.dumps(
                summarize(document["suite_version"], cases, digest).model_dump(mode="json"),
                indent=2,
            )
        )
        return 0
    if args.command == "inspect":
        case = next((item for item in cases if item.case_id == args.case_id), None)
        if case is None:
            print(json.dumps({"status": "NOT_FOUND", "case_id": args.case_id}))
            return 2
        print(case.model_dump_json(indent=2))
        return 0
    if args.command == "plan":
        if GIT is None:
            print(json.dumps({"status": "INVALID", "reason": "git_unavailable"}))
            return 2
        sha = subprocess.run(  # noqa: S603 - fixed git query, no shell or user input
            [GIT, "rev-parse", "HEAD"],  # noqa: S607 - executable resolved from PATH
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        commit = sha.stdout.strip() if sha.returncode == 0 else "UNAVAILABLE"
        threshold_policy, threshold_policy_sha = load_threshold_policy()
        print(
            json.dumps(
                {
                    "status": "PLAN_ONLY",
                    "evaluation_scope": "implementation_visible_open_corpus",
                    "phase11_status": "NOT_VERIFIED",
                    "independent_holdout_status": "ABSENT_PENDING_INDEPENDENT_ACCEPTANCE",
                    "repository_sha": commit,
                    "suite_version": document["suite_version"],
                    "suite_sha256": digest,
                    "case_count": len(cases),
                    "threshold_policy_version": threshold_policy.policy_version,
                    "threshold_policy_sha256": threshold_policy_sha,
                    "scoring_thresholds": {
                        "minimum_benign_usefulness_rate": (
                            threshold_policy.minimum_benign_usefulness_rate
                        ),
                        "minimum_expected_route_accuracy": (
                            threshold_policy.minimum_expected_route_accuracy
                        ),
                        "minimum_grounded_fact_accuracy": (
                            threshold_policy.minimum_grounded_fact_accuracy
                        ),
                        "maximum_critical_compromises": (
                            threshold_policy.maximum_critical_compromises
                        ),
                    },
                    "paid_provider_calls": 0,
                    "provider_cost_usd": 0,
                    "requires_disposable_database": True,
                    "launch_command": "make phase11-acceptance",
                },
                indent=2,
            )
        )
        return 0
    if args.command == "run":
        if args.suite.resolve() != DEFAULT_SUITE.resolve():
            parser.error("integration run only accepts the frozen default suite")
        if os.environ.get("ENVIRONMENT") not in {"test", "development"}:
            parser.error("run requires ENVIRONMENT=test or development")
        database_url = os.environ.get("TEST_DATABASE_URL")
        if database_url is None:
            parser.error("run requires a disposable vehicle_test database URL")
        if not is_disposable_database_url(database_url):
            parser.error("run requires a disposable vehicle_test database URL")
        env = os.environ.copy() | {"TEST_DATABASE_URL": database_url}
        if GIT is not None:
            revision = subprocess.run(  # noqa: S603 - fixed git query
                [GIT, "rev-parse", "HEAD"],  # noqa: S603 - fixed git query
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if revision.returncode == 0:
                env["GIT_SHA"] = revision.stdout.strip()
        completed = subprocess.run(  # noqa: S603 - fixed Python script path, no shell
            [sys.executable, str(ROOT / "scripts/evaluate_agent_red_team.py")],
            cwd=ROOT,
            env=env,
            check=False,
        )
        return completed.returncode
    if args.command == "report":
        raw_receipt, parsed_receipt = _receipt_argument(parser, args)
        receipt_data = raw_receipt
        attempts = receipt_data.get("attempts", [])
        threshold_policy, threshold_policy_sha = load_threshold_policy()
        case_map = {case.case_id: case for case in cases}
        by_status = Counter(item.get("status", "UNKNOWN") for item in attempts)
        latency = sorted(
            item["elapsed_ms"]
            for item in attempts
            if isinstance(item.get("elapsed_ms"), int) and item["elapsed_ms"] >= 0
        )
        latency_p95 = latency[max(0, (len(latency) * 95 + 99) // 100 - 1)] if latency else None
        first_event_latency = sorted(
            item["first_sse_event_ms"]
            for item in attempts
            if isinstance(item.get("first_sse_event_ms"), int) and item["first_sse_event_ms"] >= 0
        )
        first_event_p95 = (
            first_event_latency[max(0, (len(first_event_latency) * 95 + 99) // 100 - 1)]
            if first_event_latency
            else None
        )
        pass_counts = {
            behavior.value: sum(
                item.get("status") == "PASS"
                and case_map.get(item.get("case_id")) is not None
                and case_map[item["case_id"]].expected_behavior == behavior
                for item in attempts
            )
            for behavior in sorted(
                {case.expected_behavior for case in cases}, key=lambda item: item.value
            )
        }
        print(
            json.dumps(
                {
                    "status": "UNVERIFIED_SUMMARY",
                    "evaluation_scope": "implementation_visible_open_corpus",
                    "phase11_status": "NOT_VERIFIED",
                    "independent_holdout_status": "ABSENT_PENDING_INDEPENDENT_ACCEPTANCE",
                    "repository_sha": receipt_data.get("repository_sha"),
                    "suite_sha256": receipt_data.get("suite_sha256"),
                    "suite_cases": len(cases),
                    "attempts": len(attempts),
                    "statuses": dict(sorted(by_status.items())),
                    "cases_not_run": by_status.get("NOT_RUN", 0),
                    "all_cases_passed": len(attempts) == len(cases)
                    and by_status == {"PASS": len(cases)},
                    "passed_by_expected_behavior": pass_counts,
                    "coverage_outcomes": _coverage_outcomes(cases, attempts),
                    "attack_attribution": _attack_attribution_summary(cases, attempts),
                    "grading_accounting": _grading_accounting(cases, attempts),
                    "scoring_thresholds": score_thresholds(
                        cases,
                        parsed_receipt.attempts,
                        independently_graded={
                            attempt.case_id: attempt.status for attempt in parsed_receipt.attempts
                        },
                        policy=threshold_policy,
                    ),
                    "threshold_policy_receipt_match": (
                        parsed_receipt.threshold_policy_version == threshold_policy.policy_version
                        and parsed_receipt.threshold_policy_sha256 == threshold_policy_sha
                    ),
                    "latency_ms": {
                        "measured_cases": len(latency),
                        "p50": latency[(len(latency) - 1) // 2] if latency else None,
                        "p95": latency_p95,
                        "max": latency[-1] if latency else None,
                    },
                    "first_sse_event_latency_ms": {
                        "measured_cases": len(first_event_latency),
                        "p50": (
                            first_event_latency[(len(first_event_latency) - 1) // 2]
                            if first_event_latency
                            else None
                        ),
                        "p95": first_event_p95,
                        "max": first_event_latency[-1] if first_event_latency else None,
                    },
                    "stage_latency_ms": _stage_latency_summaries(parsed_receipt.attempts),
                    "statistical_uncertainty": _clustered_pass_rate_interval(
                        cases,
                        [attempt.model_dump(mode="json") for attempt in parsed_receipt.attempts],
                    ),
                    "provider_usage_by_stage": _provider_usage_summary(parsed_receipt.attempts),
                    "paid_provider_calls": receipt_data.get("paid_provider_calls"),
                    "provider_cost_usd": receipt_data.get("provider_cost_usd"),
                    "resource_measurement": receipt_data.get("resource_measurement"),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "benchmark":
        _, parsed_receipt = _receipt_argument(parser, args)
        elapsed = sorted(
            attempt.elapsed_ms
            for attempt in parsed_receipt.attempts
            if attempt.elapsed_ms is not None
        )
        first_event_elapsed = sorted(
            attempt.first_sse_event_ms
            for attempt in parsed_receipt.attempts
            if attempt.first_sse_event_ms is not None
        )
        print(
            json.dumps(
                {
                    "status": "UNVERIFIED_BENCHMARK",
                    "repository_sha": parsed_receipt.repository_sha,
                    "suite_sha256": parsed_receipt.suite_sha256,
                    "measured_cases": len(elapsed),
                    "latency_ms": {
                        "p50": elapsed[(len(elapsed) - 1) // 2] if elapsed else None,
                        "p95": elapsed[max(0, (len(elapsed) * 95 + 99) // 100 - 1)]
                        if elapsed
                        else None,
                        "max": elapsed[-1] if elapsed else None,
                    },
                    "first_sse_event_latency_ms": {
                        "measured_cases": len(first_event_elapsed),
                        "p50": (
                            first_event_elapsed[(len(first_event_elapsed) - 1) // 2]
                            if first_event_elapsed
                            else None
                        ),
                        "p95": first_event_elapsed[
                            max(0, (len(first_event_elapsed) * 95 + 99) // 100 - 1)
                        ]
                        if first_event_elapsed
                        else None,
                        "max": first_event_elapsed[-1] if first_event_elapsed else None,
                    },
                    "stage_latency_ms": _stage_latency_summaries(parsed_receipt.attempts),
                    "statistical_uncertainty": _clustered_pass_rate_interval(
                        cases,
                        [attempt.model_dump(mode="json") for attempt in parsed_receipt.attempts],
                    ),
                    "provider_usage_by_stage": _provider_usage_summary(parsed_receipt.attempts),
                    "max_tool_calls": max(
                        (attempt.mcp_call_count for attempt in parsed_receipt.attempts), default=0
                    ),
                    "paid_provider_calls": parsed_receipt.paid_provider_calls,
                    "provider_cost_usd": parsed_receipt.provider_cost_usd,
                    "resource_measurement": (
                        parsed_receipt.resource_measurement.model_dump(mode="json")
                        if parsed_receipt.resource_measurement is not None
                        else None
                    ),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "observability":
        _, parsed_receipt = _receipt_argument(parser, args)
        case_map = {case.case_id: case for case in cases}
        counts = Counter(
            (
                case_map[attempt.case_id].family.value,
                attempt.status.value,
            )
            for attempt in parsed_receipt.attempts
            if attempt.case_id in case_map
        )
        attack_counts = Counter(
            (case_map[attempt.case_id].attack_family or "none", attempt.status.value)
            for attempt in parsed_receipt.attempts
            if attempt.case_id in case_map
        )
        control_counts = _defense_control_counts(cases, parsed_receipt.attempts)
        print("# HELP vehicle_agent_eval_case_attempts Phase 11 cases by family and status")
        print("# TYPE vehicle_agent_eval_case_attempts counter")
        for (family, status), count in sorted(counts.items()):
            print(
                f'vehicle_agent_eval_case_attempts{{family="{family}",status="{status}"}} {count}'
            )
        print(
            "# HELP vehicle_agent_eval_attack_attempts Phase 11 attack cases by family and status"
        )
        print("# TYPE vehicle_agent_eval_attack_attempts counter")
        for (attack_family, status), count in sorted(attack_counts.items()):
            print(
                "vehicle_agent_eval_attack_attempts"
                f'{{attack_family="{attack_family}",status="{status}"}} {count}'
            )
        print("# HELP vehicle_agent_eval_defense_controls Evaluated defense layer outcomes")
        print("# TYPE vehicle_agent_eval_defense_controls counter")
        for (attack_family, control_layer, outcome, status), count in sorted(
            control_counts.items()
        ):
            print(
                "vehicle_agent_eval_defense_controls"
                f'{{attack_family="{attack_family}",control_layer="{control_layer}",'
                f'outcome="{outcome}",status="{status}"}} {count}'
            )
        latencies = [
            attempt.elapsed_ms
            for attempt in parsed_receipt.attempts
            if attempt.elapsed_ms is not None
        ]
        print("# HELP vehicle_agent_eval_case_latency_ms Observed case latency in milliseconds")
        print("# TYPE vehicle_agent_eval_case_latency_ms histogram")
        for upper_bound in (100, 250, 500, 1000, 2500, 5000, 10000):
            count = sum(latency <= upper_bound for latency in latencies)
            print(f'vehicle_agent_eval_case_latency_ms_bucket{{le="{upper_bound}"}} {count}')
        print(f'vehicle_agent_eval_case_latency_ms_bucket{{le="+Inf"}} {len(latencies)}')
        print(f"vehicle_agent_eval_case_latency_ms_count {len(latencies)}")
        print(f"vehicle_agent_eval_case_latency_ms_sum {sum(latencies)}")
        print("# HELP vehicle_agent_eval_stage_latency_ms Phase 11 stage work in milliseconds")
        print("# TYPE vehicle_agent_eval_stage_latency_ms histogram")
        for stage, field in (
            ("routing", "routing_ms"),
            ("specialist_work", "specialist_work_ms"),
            ("tool_work", "tool_work_ms"),
            ("rag_tool_work", "rag_tool_work_ms"),
        ):
            values = [
                value
                for attempt in parsed_receipt.attempts
                if (value := getattr(attempt, field)) is not None
            ]
            for upper_bound in (10, 25, 50, 100, 250, 500, 1000, 2500, 5000):
                count = sum(value <= upper_bound for value in values)
                print(
                    "vehicle_agent_eval_stage_latency_ms_bucket"
                    f'{{stage="{stage}",le="{upper_bound}"}} {count}'
                )
            print(
                "vehicle_agent_eval_stage_latency_ms_bucket"
                f'{{stage="{stage}",le="+Inf"}} {len(values)}'
            )
            print(f'vehicle_agent_eval_stage_latency_ms_count{{stage="{stage}"}} {len(values)}')
            print(f'vehicle_agent_eval_stage_latency_ms_sum{{stage="{stage}"}} {sum(values)}')
        print("# HELP vehicle_agent_eval_paid_provider_calls Paid provider calls in receipt")
        print("# TYPE vehicle_agent_eval_paid_provider_calls gauge")
        print(f"vehicle_agent_eval_paid_provider_calls {parsed_receipt.paid_provider_calls}")
        provider_class = (
            parsed_receipt.provider
            if parsed_receipt.provider in {"deterministic", "openai"}
            else "other"
        )
        print("# HELP vehicle_agent_eval_provider_class Receipt provider class")
        print("# TYPE vehicle_agent_eval_provider_class gauge")
        print(f'vehicle_agent_eval_provider_class{{provider="{provider_class}"}} 1')
        print("# HELP vehicle_agent_eval_receipt_verified Receipt has independent DB verification")
        print("# TYPE vehicle_agent_eval_receipt_verified gauge")
        print("vehicle_agent_eval_receipt_verified 0")
        return 0
    if args.command == "compare":
        if args.receipt is None or args.against is None:
            parser.error("compare requires --receipt and --against")
        current, previous = _json(args.receipt), _json(args.against)
        left = {item["case_id"]: item.get("status") for item in current.get("attempts", [])}
        right = {item["case_id"]: item.get("status") for item in previous.get("attempts", [])}
        print(
            json.dumps(
                {
                    "current_sha": current.get("repository_sha"),
                    "previous_sha": previous.get("repository_sha"),
                    "changed_cases": {
                        key: {"previous": right.get(key), "current": left.get(key)}
                        for key in sorted(left.keys() | right.keys())
                        if left.get(key) != right.get(key)
                    },
                },
                indent=2,
            )
        )
        return 0
    if args.receipt is None:
        parser.error("verify requires --receipt")
    raw = _json(args.receipt)
    database_url = os.environ.get("TEST_DATABASE_URL")
    if os.environ.get("ENVIRONMENT") not in {"test", "development"}:
        parser.error("verify requires ENVIRONMENT=test or development")
    if database_url is None or not is_disposable_database_url(database_url):
        parser.error("verify requires a disposable vehicle_test database URL")
    database_url = database_url or ""
    if GIT is None:
        print(json.dumps({"status": "INVALID", "reason": "git_unavailable"}))
        return 2
    sha = subprocess.run(  # noqa: S603 - fixed git query, no shell or user input
        [GIT, "rev-parse", "HEAD"],  # noqa: S607 - executable resolved from PATH
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    case_by_id = {case.case_id: case for case in cases}
    fact_map: dict[str, tuple[OracleFact, ...]] = {}
    for attempt in raw.get("attempts", []):
        case_id = attempt.get("case_id")
        selected_vehicle_id = attempt.get("selected_vehicle_id")
        case = case_by_id.get(case_id)
        if case is None or not selected_vehicle_id:
            continue
        if case.intent == "source_change" and case.version >= 2:
            # The mutable fixture is restored before receipt verification; use the
            # predeclared metamorphic value and verify it against persisted run evidence.
            fact_map[case_id] = case.expected_facts
        elif case.source_surface == "prediction_evidence":
            evidence_ids = {
                str(item.get("id"))
                for item in attempt.get("evidence", [])
                if isinstance(item, dict)
                and item.get("source_tool") == "get_prediction_evidence"
                and item.get("id")
            }
            if len(evidence_ids) != 1:
                print(
                    json.dumps(
                        {
                            "status": "FAIL",
                            "reasons": ["prediction_evidence_source_bundle_count_invalid"],
                        }
                    )
                )
                return 1
            try:
                fact_map[case_id] = asyncio.run(
                    resolve_prediction_evidence_facts(
                        database_url, next(iter(evidence_ids)), selected_vehicle_id
                    )
                )
            except ValueError:
                print(
                    json.dumps(
                        {
                            "status": "FAIL",
                            "reasons": ["independent_prediction_oracle_rejected"],
                        }
                    )
                )
                return 1
        else:
            fact_map[case_id] = asyncio.run(
                resolve_case_facts(database_url, case, selected_vehicle_id)
            )
    persisted_runs: dict[str, dict[str, Any]] = {}
    persisted_investigations: dict[str, dict[str, Any]] = {}
    non_persisted_run_counts: dict[str, int] = {}
    case_ids = {case.case_id for case in cases}
    case_by_id = {case.case_id: case for case in cases}
    for attempt in raw.get("attempts", []):
        case_id = attempt.get("case_id")
        if case_id not in case_ids:
            continue
        case = case_by_id[case_id]
        if attempt.get("status") != "NOT_RUN" and case.source_surface == "api_input_boundary":
            selected_vehicle = attempt.get("selected_vehicle_id")
            if not isinstance(selected_vehicle, str):
                print(
                    json.dumps(
                        {"status": "FAIL", "reasons": ["non_persisted_probe_vehicle_missing"]}
                    )
                )
                return 1
            question = "x" * 2001 if case.intent == "oversized_agent_question" else case.question
            non_persisted_run_counts[case_id] = asyncio.run(
                agent_run_count_for_question(database_url, selected_vehicle, question)
            )
        if run_id := attempt.get("run_id"):
            if persisted := asyncio.run(persisted_agent_run(database_url, run_id)):
                persisted_runs[case_id] = persisted
        if case_id == "P11-RED-011":
            probe = attempt.get("direct_probe")
            summary = probe.get("output_summary", {}) if isinstance(probe, dict) else {}
            investigation_id = summary.get("investigation_id")
            selected_vehicle = attempt.get("selected_vehicle_id")
            if isinstance(investigation_id, str) and isinstance(selected_vehicle, str):
                if state := asyncio.run(
                    persisted_investigation_state(database_url, investigation_id, selected_vehicle)
                ):
                    persisted_investigations[case_id] = state
        probe = attempt.get("direct_probe")
        summary = probe.get("output_summary", {}) if isinstance(probe, dict) else {}
        if isinstance(summary, dict) and (baseline_id := summary.get("baseline_run_id")):
            if persisted := asyncio.run(persisted_agent_run(database_url, str(baseline_id))):
                persisted_runs[f"{case_id}:baseline"] = persisted
        if isinstance(summary, dict) and (replacement_id := summary.get("replacement_run_id")):
            if persisted := asyncio.run(persisted_agent_run(database_url, str(replacement_id))):
                persisted_runs[f"{case_id}:replacement"] = persisted
    presence_mismatches = asyncio.run(
        _source_presence_mismatches(raw.get("attempts", []), cases, database_url)
    )
    current_source_sha = asyncio.run(source_digest(database_url))
    dependency_manifest_sha = hashlib.sha256((ROOT / "apps/api/uv.lock").read_bytes()).hexdigest()
    prompt_manifest_sha = hashlib.sha256(
        (ROOT / "apps/api/src/vehicle_platform/agents/prompts.py").read_bytes()
    ).hexdigest()
    tool_catalog_sha = hashlib.sha256(
        b"".join(
            path.read_bytes()
            for path in (
                ROOT / "apps/api/src/vehicle_platform/mcp/catalog.py",
                ROOT / "apps/api/src/vehicle_platform/mcp/tools.py",
                ROOT / "apps/api/src/vehicle_platform/mcp/server.py",
            )
        )
    ).hexdigest()
    threshold_policy, threshold_policy_sha = load_threshold_policy()
    ok, reasons = verify_receipt(
        raw,
        cases,
        expected_sha=sha.stdout.strip() if sha.returncode == 0 else "",
        suite_sha=digest,
        suite_version=document["suite_version"],
        oracle_facts=fact_map,
        expected_source_sha=current_source_sha,
        persisted_runs=persisted_runs,
        non_persisted_run_counts=non_persisted_run_counts,
        persisted_investigations=persisted_investigations,
        expected_dependency_manifest_sha256=dependency_manifest_sha,
        expected_prompt_manifest_sha256=prompt_manifest_sha,
        expected_tool_catalog_sha256=tool_catalog_sha,
        expected_schema_revision=asyncio.run(schema_revision(database_url)),
        expected_environment=os.environ.get("ENVIRONMENT"),
        expected_provider="deterministic",
        expected_model="scripted-v1",
        require_resource_measurement=True,
        require_attack_attribution=True,
        expected_threshold_policy=threshold_policy,
        expected_threshold_policy_sha256=threshold_policy_sha,
    )
    journal_fields = (
        raw.get("attempt_journal_run_id"),
        raw.get("attempt_journal_path"),
        raw.get("attempt_journal_sha256"),
        raw.get("attempt_journal_entries"),
    )
    journal_required = (
        sha.returncode == 0
        and raw.get("repository_sha") == sha.stdout.strip()
        and raw.get("suite_sha256") == digest
    )
    if any(value is not None for value in journal_fields):
        if not all(value is not None for value in journal_fields):
            reasons = tuple(reasons) + ("attempt_journal_reference_incomplete",)
            ok = False
        else:
            relative_path = Path(str(raw["attempt_journal_path"]))
            journal_path = (ROOT / relative_path).resolve()
            try:
                journal_path.relative_to(ROOT.resolve())
            except ValueError:
                reasons = tuple(reasons) + ("attempt_journal_path_outside_repository",)
                ok = False
            else:
                journal_ok, journal_reasons = verify_attempt_journal(
                    journal_path,
                    expected_run_id=str(raw["attempt_journal_run_id"]),
                    expected_repository_sha=str(raw["repository_sha"]),
                    expected_suite_sha256=str(raw["suite_sha256"]),
                    expected_sha256=str(raw["attempt_journal_sha256"]),
                    expected_entries=int(raw["attempt_journal_entries"]),
                )
                if not journal_ok:
                    reasons = tuple(reasons) + journal_reasons
                    ok = False
    elif journal_required:
        reasons = tuple(reasons) + ("attempt_journal_reference_missing",)
        ok = False
    if presence_mismatches:
        reasons = tuple(reasons) + ("expected_absent_source_signal_present",)
        ok = False
    print(
        json.dumps(
            {
                "status": "PASS" if ok else "FAIL",
                "evaluation_scope": "implementation_visible_open_corpus",
                "phase11_status": "NOT_VERIFIED",
                "independent_holdout_status": "ABSENT_PENDING_INDEPENDENT_ACCEPTANCE",
                "reasons": reasons,
            },
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
