"""Operator interface for frozen Phase 11 scenarios and independent receipts."""

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from vehicle_platform.agent_evaluation.contracts import AgentEvalCase, EvalReceipt
from vehicle_platform.agent_evaluation.corpus import CorpusError, load_corpus, summarize
from vehicle_platform.agent_evaluation.receipts import verify_receipt
from vehicle_platform.agent_evaluation.source_oracle import (
    is_disposable_database_url,
    persisted_agent_run,
    resolve_case_facts,
    schema_revision,
    source_digest,
    source_signal_present,
)

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SUITE = ROOT / "evals/phase11/suite-v2.json"
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
        buckets: dict[str, dict[str, Any]] = {}
        for case in cases:
            category = value_for(case)
            bucket = buckets.setdefault(category, {"cases": 0, "status_counts": Counter()})
            bucket["cases"] += 1
            attempt = attempt_by_id.get(case.case_id)
            status = str(attempt.get("status", "NOT_RUN")) if attempt else "NOT_RUN"
            bucket["status_counts"][status] += 1
        output[dimension] = {
            category: {
                "cases": bucket["cases"],
                "status_counts": dict(sorted(bucket["status_counts"].items())),
            }
            for category, bucket in sorted(buckets.items())
        }
    return output


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
        print(
            json.dumps(
                {
                    "status": "PLAN_ONLY",
                    "repository_sha": commit,
                    "suite_version": document["suite_version"],
                    "suite_sha256": digest,
                    "case_count": len(cases),
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
        raw_receipt, _ = _receipt_argument(parser, args)
        receipt_data = raw_receipt
        attempts = receipt_data.get("attempts", [])
        case_map = {case.case_id: case for case in cases}
        by_status = Counter(item.get("status", "UNKNOWN") for item in attempts)
        latency = sorted(
            item["elapsed_ms"]
            for item in attempts
            if isinstance(item.get("elapsed_ms"), int) and item["elapsed_ms"] >= 0
        )
        latency_p95 = latency[max(0, (len(latency) * 95 + 99) // 100 - 1)] if latency else None
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
                    "latency_ms": {
                        "measured_cases": len(latency),
                        "p50": latency[(len(latency) - 1) // 2] if latency else None,
                        "p95": latency_p95,
                        "max": latency[-1] if latency else None,
                    },
                    "paid_provider_calls": receipt_data.get("paid_provider_calls"),
                    "provider_cost_usd": receipt_data.get("provider_cost_usd"),
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
                    "max_tool_calls": max(
                        (attempt.mcp_call_count for attempt in parsed_receipt.attempts), default=0
                    ),
                    "paid_provider_calls": parsed_receipt.paid_provider_calls,
                    "provider_cost_usd": parsed_receipt.provider_cost_usd,
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
        print("# HELP vehicle_agent_eval_case_attempts Phase 11 cases by family and status")
        print("# TYPE vehicle_agent_eval_case_attempts counter")
        for (family, status), count in sorted(counts.items()):
            print(
                f'vehicle_agent_eval_case_attempts{{family="{family}",status="{status}"}} {count}'
            )
        latencies = [
            attempt.elapsed_ms
            for attempt in parsed_receipt.attempts
            if attempt.elapsed_ms is not None
        ]
        print("# HELP vehicle_agent_eval_case_latency_ms Observed case latency in milliseconds")
        print("# TYPE vehicle_agent_eval_case_latency_ms summary")
        print(f"vehicle_agent_eval_case_latency_ms_count {len(latencies)}")
        print(f"vehicle_agent_eval_case_latency_ms_sum {sum(latencies)}")
        print("# HELP vehicle_agent_eval_paid_provider_calls Paid provider calls in receipt")
        print("# TYPE vehicle_agent_eval_paid_provider_calls gauge")
        print(f"vehicle_agent_eval_paid_provider_calls {parsed_receipt.paid_provider_calls}")
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
    fact_map = {
        attempt["case_id"]: asyncio.run(
            resolve_case_facts(
                database_url,
                next(case for case in cases if case.case_id == attempt["case_id"]),
                attempt["selected_vehicle_id"],
            )
        )
        for attempt in raw.get("attempts", [])
        if attempt.get("selected_vehicle_id")
        and attempt["case_id"] in {case.case_id for case in cases}
    }
    persisted_runs = {
        attempt["case_id"]: persisted
        for attempt in raw.get("attempts", [])
        if attempt.get("run_id") and attempt["case_id"] in {case.case_id for case in cases}
        if (persisted := asyncio.run(persisted_agent_run(database_url, attempt["run_id"])))
        is not None
    }
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
    ok, reasons = verify_receipt(
        raw,
        cases,
        expected_sha=sha.stdout.strip() if sha.returncode == 0 else "",
        suite_sha=digest,
        suite_version=document["suite_version"],
        oracle_facts=fact_map,
        expected_source_sha=current_source_sha,
        persisted_runs=persisted_runs,
        expected_dependency_manifest_sha256=dependency_manifest_sha,
        expected_prompt_manifest_sha256=prompt_manifest_sha,
        expected_tool_catalog_sha256=tool_catalog_sha,
        expected_schema_revision=asyncio.run(schema_revision(database_url)),
        expected_environment=os.environ.get("ENVIRONMENT"),
        expected_provider="deterministic",
        expected_model="scripted-v1",
    )
    if presence_mismatches:
        reasons = tuple(reasons) + ("expected_absent_source_signal_present",)
        ok = False
    print(json.dumps({"status": "PASS" if ok else "FAIL", "reasons": reasons}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
