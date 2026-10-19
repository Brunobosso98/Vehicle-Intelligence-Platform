"""Summarize measured Phase 9B training and offline inference performance."""

import json
from pathlib import Path
from typing import Any

REPORT_PATH = Path(".validation/phase9b/acceptance.json")
OUTPUT_PATH = Path(".validation/phase9b/benchmark.json")
EXPECTED_TASKS = {
    "NEXT_PULL_THERMAL_DEGRADATION",
    "NEXT_PULL_PERFORMANCE_DEGRADATION",
    "NEXT_PULL_FUEL_DEVIATION",
}


def main() -> None:
    if not REPORT_PATH.is_file():
        raise FileNotFoundError(
            "run make phase9b-acceptance before the predictive-model benchmark"
        )
    report: dict[str, Any] = json.loads(REPORT_PATH.read_text())
    tasks = report.get("tasks")
    if not isinstance(tasks, dict) or set(tasks) != EXPECTED_TASKS:
        raise ValueError("acceptance report does not contain all three required tasks")
    summaries: dict[str, Any] = {}
    for task_name, task in tasks.items():
        inference = task.get("offline_inference", {})
        predictions = int(inference.get("throughput_predictions", 0))
        throughput = float(inference.get("throughput_predictions_per_second", 0.0))
        elapsed = float(task.get("elapsed_seconds", 0.0))
        if predictions < 1000 or throughput <= 0 or elapsed <= 0:
            raise ValueError(f"{task_name} lacks valid timing measurements")
        summaries[task_name] = {
            "dataset_rows": int(task.get("row_count", 0)),
            "training_and_registration_seconds": elapsed,
            "offline_predictions_measured": predictions,
            "offline_predictions_per_second": throughput,
            "selected_family": task["selected_model"]["family"],
            "status": task["state"],
        }
    output = {
        "status": "MEASURED_SYNTHETIC_ONLY",
        "source_report": str(REPORT_PATH),
        "real_world_performance_claimed": False,
        "tasks": summaries,
        "paid_calls": 0,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
