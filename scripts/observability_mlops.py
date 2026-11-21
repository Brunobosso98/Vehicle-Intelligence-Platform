#!/usr/bin/env python3
"""Validate Phase 10 trace and metric receipts without exposing entity labels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / ".validation" / "phase10" / "acceptance.json"
OUTPUT = ROOT / ".validation" / "phase10" / "observability.json"
REQUIRED_SPANS = {"mlops.pipeline.run", "mlops.monitor"}
REQUIRED_METRICS = {
    "mlops_pipeline_runs_total",
    "mlops_pipeline_stage_events_total",
    "mlops_monitor_duration_seconds",
}
FORBIDDEN_LABELS = {
    "run_id",
    "artifact_id",
    "candidate_id",
    "vehicle_id",
    "session_id",
    "pull_id",
    "feature_key",
    "checksum",
    "vin",
    "secret",
    "token",
    "path",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    _require(
        report.get("status") == "PASS",
        "observability requires a passing acceptance receipt",
    )
    evidence = report.get("observability", {})
    spans = set(evidence.get("spans", []))
    metrics = set(evidence.get("metric_names", []))
    labels = set(evidence.get("metric_label_names", []))
    span_attributes = set(evidence.get("span_attribute_names", []))
    _require(REQUIRED_SPANS.issubset(spans), "required Phase 10 spans are absent")
    _require(REQUIRED_METRICS.issubset(metrics), "required Phase 10 metrics are absent")
    _require(
        not FORBIDDEN_LABELS.intersection(labels),
        "entity identifiers appear in metric labels",
    )
    _require(
        not FORBIDDEN_LABELS.intersection(span_attributes),
        "sensitive entity attributes appear in spans",
    )
    _require(
        evidence.get("entity_ids_in_metric_labels") is False,
        "entity label policy failed",
    )
    output: dict[str, Any] = {
        "schema_version": "phase10-observability-v1",
        "git_sha": report["git_sha"],
        "acceptance_checksum": report["acceptance_checksum"],
        "status": "PASS",
        "spans": sorted(spans),
        "metrics": sorted(metrics),
        "metric_label_names": sorted(labels),
        "span_attribute_names": sorted(span_attributes),
        "entity_or_secret_identifiers_emitted": False,
        "serving_action": "NONE",
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS", "git_sha": output["git_sha"]}, sort_keys=True))


if __name__ == "__main__":
    main()
