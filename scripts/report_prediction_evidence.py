"""Validate and print measured Phase 9E benchmark or observability evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast


def _report() -> dict[str, Any]:
    path = Path(".validation/phase9e/acceptance.json")
    if not path.is_file():
        raise SystemExit(
            "Phase 9E acceptance report is missing; run phase9e-acceptance first"
        )
    report = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if report.get("status") != "PASS":
        raise SystemExit("Phase 9E acceptance report is not PASS")
    return report


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"benchmark", "observability"}:
        raise SystemExit(
            "usage: report_prediction_evidence.py {benchmark|observability}"
        )
    report = _report()
    if sys.argv[1] == "benchmark":
        benchmark = report.get("benchmarks", {})
        burst = benchmark.get("concurrent_100", {})
        if (
            benchmark.get("sample_count", 0) < 1
            or benchmark.get("projection_bytes_max", 65_537) > 65_536
            or benchmark.get("concurrent_10_elapsed_seconds", 0) <= 0
            or burst.get("request_count") != 100
            or burst.get("accepted_replays", 0) < 1
            or burst.get("identity_count") != 1
        ):
            raise SystemExit(
                "Phase 9E benchmark receipt is incomplete or outside declared bounds"
            )
        result = {
            "git_sha": report.get("git_sha"),
            "status": "PASS",
            "benchmarks": benchmark,
        }
    else:
        observability = report.get("observability", {})
        metric_names = set(observability.get("metric_names", []))
        span_names = set(observability.get("trace_names", []))
        required_metrics = {
            "prediction_evidence_operations_total",
            "prediction_evidence_duration_seconds",
            "prediction_evidence_graph_size",
            "prediction_evidence_replays_total",
        }
        required_spans = {
            "prediction.evidence.source.resolve",
            "prediction.evidence.claim_construction",
            "prediction.evidence.canonical_hash",
            "prediction.evidence.immutable_persist",
            "prediction.evidence.read_projection",
            "prediction.evidence.independent_verify",
            "prediction.evidence.audit_append",
        }
        if (
            observability.get("status") != "PASS"
            or observability.get("bounded_labels_only") is not True
            or observability.get("vehicle_or_evidence_ids_present") is not False
            or not required_metrics.issubset(metric_names)
            or not required_spans.issubset(span_names)
        ):
            raise SystemExit("Phase 9E observability receipt is incomplete")
        result = {
            "git_sha": report.get("git_sha"),
            "status": "PASS",
            "observability": observability,
        }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
