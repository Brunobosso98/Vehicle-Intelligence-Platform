"""Print deterministic Phase 3 golden-scenario acceptance evidence."""

import json
from collections import Counter
from dataclasses import asdict

from vehicle_platform.events.engine import EventEngine
from vehicle_platform.events.evaluation import evaluate_events
from vehicle_platform.events.synthetic import golden_scenarios


def main() -> None:
    expected = []
    detected = []
    healthy: dict[str, int] = {}
    scenario_reports = []
    for scenario in golden_scenarios():
        events, _ = EventEngine().analyze(scenario.frames, scenario.pulls)
        expected_types = {truth.event_type for truth in scenario.ground_truth}
        relevant = [
            event
            for event in events
            if event.event_type in expected_types or not expected_types
        ]
        if not expected_types:
            healthy[scenario.name] = len(relevant)
        expected.extend(scenario.ground_truth)
        detected.extend(relevant)
        scenario_reports.append(
            {
                "scenario": scenario.name,
                "expected": len(scenario.ground_truth),
                "detected": len(relevant),
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


if __name__ == "__main__":
    main()
