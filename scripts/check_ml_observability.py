"""Check the Phase 9B acceptance telemetry evidence for required signals."""

import json
from pathlib import Path
from typing import Any

REPORT_PATH = Path(".validation/phase9b/acceptance.json")
REQUIRED_METRICS = {
    "ml_training_runs",
    "ml_candidate_models",
    "ml_model_evaluations",
    "ml_dataset_rows",
    "ml_candidate_training_duration",
    "ml_artifact_size",
    "ml_labels_exclusions",
}
REQUIRED_SPANS = {
    "ml.dataset_materialization",
    "ml.label_generation",
    "ml.temporal_split",
    "ml.leakage_validation",
    "ml.candidate_training",
    "ml.validation_selection",
    "ml.test_evaluation",
    "ml.artifact_staging",
    "ml.model_registration",
}


def main() -> None:
    if not REPORT_PATH.is_file():
        raise FileNotFoundError(
            "run make phase9b-acceptance before the ML observability check"
        )
    report: dict[str, Any] = json.loads(REPORT_PATH.read_text())
    observability = report.get("observability", {})
    metric_samples = set(observability.get("metrics_exported", []))
    metric_families = {sample.split("{", maxsplit=1)[0] for sample in metric_samples}
    spans = set(observability.get("training_trace_spans", []))
    verified_metrics = sorted(
        expected
        for expected in REQUIRED_METRICS
        if any(name.startswith(expected) for name in metric_families)
    )
    missing_metrics = sorted(REQUIRED_METRICS - set(verified_metrics))
    missing_spans = sorted(REQUIRED_SPANS - spans)
    if missing_metrics or missing_spans:
        raise ValueError(
            f"ML telemetry evidence incomplete: metrics={missing_metrics}, spans={missing_spans}"
        )
    if observability.get("entity_ids_in_metric_attributes") is not False:
        raise ValueError("ML metric evidence does not confirm entity-id exclusion")
    if observability.get("sample_content_logged") is not False:
        raise ValueError(
            "ML observability evidence does not confirm sample-content exclusion"
        )
    output = {
        "status": "PASS",
        "metrics_verified": verified_metrics,
        "spans_verified": sorted(spans),
        "entity_id_labels": False,
        "sample_content_logged": False,
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
