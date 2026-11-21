#!/usr/bin/env python3
"""Record bounded Phase 10 acceptance timings and artifact sizes."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / ".validation" / "phase10" / "acceptance.json"
OUTPUT = ROOT / ".validation" / "phase10" / "benchmark.json"
MAX_ARTIFACT_BYTES = 50 * 1024 * 1024
MAX_RSS_BYTES = 8 * 1024 * 1024 * 1024
MAX_TOTAL_SECONDS = 60 * 60


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _write(value: dict[str, Any]) -> None:
    OUTPUT.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    _require(
        report.get("status") == "PASS",
        "benchmark requires a passing acceptance receipt",
    )
    performance = report.get("performance", {})
    _require(
        0 < performance.get("elapsed_seconds", 0) < MAX_TOTAL_SECONDS,
        "acceptance exceeded wall-time bound",
    )
    _require(
        0 < performance.get("peak_rss_bytes", 0) <= MAX_RSS_BYTES,
        "acceptance exceeded memory bound",
    )
    runs = [*report["supervised"].values(), *report["anomaly"].values()]
    runs.append(report["deterministic_reproduction"]["reproduction"])
    _require(
        len(runs) == 8,
        "benchmark expected seven family/task jobs plus one reproduction",
    )
    sizes = [int(item["artifact_size_bytes"]) for item in runs]
    _require(
        all(0 < size <= MAX_ARTIFACT_BYTES for size in sizes),
        "artifact exceeded the 50 MiB budget",
    )
    planning = [float(item["planning_seconds"]) for item in runs]
    execution = [float(item["execution_seconds"]) for item in runs]
    _require(
        all(value >= 0 for value in (*planning, *execution)), "negative timing value"
    )
    output = {
        "schema_version": "phase10-benchmark-v1",
        "git_sha": report["git_sha"],
        "acceptance_checksum": report["acceptance_checksum"],
        "scope": "bounded synthetic disposable database acceptance; no production capacity claim",
        "jobs": len(runs),
        "artifact_bytes": {
            "maximum": max(sizes),
            "median": statistics.median(sizes),
            "total": sum(sizes),
            "budget": MAX_ARTIFACT_BYTES,
        },
        "planning_seconds": {
            "maximum": max(planning),
            "median": statistics.median(planning),
            "total": sum(planning),
        },
        "execution_seconds": {
            "maximum": max(execution),
            "median": statistics.median(execution),
            "total": sum(execution),
        },
        "acceptance": {
            "wall_seconds": performance["elapsed_seconds"],
            "cpu_seconds": performance["cpu_seconds"],
            "peak_rss_bytes": performance["peak_rss_bytes"],
            "wall_budget_seconds": MAX_TOTAL_SECONDS,
            "memory_budget_bytes": MAX_RSS_BYTES,
        },
    }
    _write(output)
    print(
        json.dumps(
            {"status": "PASS", "jobs": len(runs), "git_sha": output["git_sha"]},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
