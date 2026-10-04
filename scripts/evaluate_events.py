"""Print deterministic Phase 3 golden-scenario acceptance evidence."""

import json
from collections import Counter
from dataclasses import asdict, replace
from datetime import timedelta

from vehicle_platform.events.engine import EventEngine
from vehicle_platform.events.evaluation import evaluate_events
from vehicle_platform.events.synthetic import golden_scenarios


def main() -> None:
    expected = []
    detected = []
    healthy: dict[str, int] = {}
    scenario_reports = []
    for scenario_index, scenario in enumerate(golden_scenarios()):
        events, _ = EventEngine().analyze(scenario.frames, scenario.pulls)
        if not scenario.ground_truth:
            healthy[scenario.name] = len(events)
        scenario_result = evaluate_events(scenario.ground_truth, events)
        shift = timedelta(days=scenario_index)
        expected.extend(
            replace(e, started_at=e.started_at + shift, ended_at=e.ended_at + shift)
            for e in scenario.ground_truth
        )
        # Each fixture uses its own event-time origin. Match per scenario to avoid
        # allowing one scenario's detection to satisfy another's missing event.
        detected.extend(
            replace(e, started_at=e.started_at + shift, ended_at=e.ended_at + shift)
            for e in events
        )
        scenario_reports.append(
            {
                "scenario": scenario.name,
                "expected": len(scenario.ground_truth),
                "detected": len(events),
                "metrics": asdict(scenario_result),
            }
        )
    result = evaluate_events(tuple(expected), detected)
    payload = {
        "scenario_count": len(golden_scenarios()),
        "scenarios": scenario_reports,
        "expected_by_type": Counter(item.event_type for item in expected),
        "detected_by_type": Counter(item.event_type for item in detected),
        "healthy_false_positives": healthy,
        "aggregate": {
            key: value for key, value in asdict(result).items() if key != "by_type"
        },
        "by_type": {key: asdict(value) for key, value in result.by_type.items()},
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    for report in scenario_reports:
        metrics = report["metrics"]
        if any(metrics[key] < 0.95 for key in ("precision", "recall", "f1")):
            raise SystemExit("Phase 3 scenario acceptance failed")
        if any(
            metrics[key] is not None and metrics[key] > 0.25
            for key in ("mean_start_error_seconds", "mean_end_error_seconds")
        ):
            raise SystemExit("Phase 3 boundary acceptance failed")
    if any(healthy.values()):
        raise SystemExit("Phase 3 healthy false positives")


if __name__ == "__main__":
    main()
