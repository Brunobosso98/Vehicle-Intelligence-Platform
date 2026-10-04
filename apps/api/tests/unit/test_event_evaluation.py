from dataclasses import replace

import pytest

from vehicle_platform.events.domain import EventProfile
from vehicle_platform.events.engine import EventEngine
from vehicle_platform.events.evaluation import evaluate_events
from vehicle_platform.events.synthetic import AnomalyInjection, anomaly_scenario, golden_scenarios


def test_golden_scenarios_meet_phase_3_acceptance() -> None:
    expected = []
    detected = []
    healthy_false_positives = {}
    for scenario in golden_scenarios():
        actual, _ = EventEngine().analyze(scenario.frames, scenario.pulls)
        relevant = actual
        scenario_result = evaluate_events(scenario.ground_truth, actual)
        assert scenario_result.false_positives == scenario_result.false_negatives == 0
        if not scenario.ground_truth:
            healthy_false_positives[scenario.name] = len(relevant)
        expected.extend(scenario.ground_truth)
        detected.extend(relevant)
    result = evaluate_events(tuple(expected), detected)
    assert len(golden_scenarios()) == 14
    assert healthy_false_positives == {"normal-repeated-pulls": 0, "noisy-healthy": 0}
    assert result.false_positives == result.false_negatives == 0
    assert result.precision >= 0.95
    assert result.recall >= 0.95
    assert result.f1 >= 0.95
    assert result.mean_start_error_seconds == 0
    assert result.mean_end_error_seconds == 0
    for metrics in result.by_type.values():
        assert metrics.precision == metrics.recall == metrics.f1 == 1


def test_matching_is_one_to_one_and_reports_boundary_error() -> None:
    scenario = anomaly_scenario("boost", (AnomalyInjection("boost_drop", 2),))
    events, _ = EventEngine().analyze(scenario.frames, scenario.pulls)
    event = next(item for item in events if item.event_type == "boost_drop")
    shifted = replace(event, started_at=event.started_at.replace(microsecond=200_000))
    result = evaluate_events(scenario.ground_truth, [shifted, shifted])
    assert result.true_positives == 1
    assert result.false_positives == 1
    assert result.mean_start_error_seconds == pytest.approx(0.2)


def test_event_ground_truth_is_independent_and_generator_deterministic() -> None:
    injections = (AnomalyInjection("fuel_pressure_drop", 1),)
    first = anomaly_scenario("fuel", injections, seed=9)
    second = anomaly_scenario("fuel", injections, seed=9)
    assert first == second
    assert first.ground_truth[0].signal == "fuel.high_pressure"
    assert first.ground_truth[0].magnitude_band == (0.2, 0.3)
    assert first.ground_truth[0].event_type != EventProfile().name


def test_unsupported_injection_is_rejected() -> None:
    with pytest.raises(ValueError, match="requires pull_index"):
        anomaly_scenario("bad", (AnomalyInjection("boost_drop"),))
    with pytest.raises(ValueError, match="unsupported injection"):
        anomaly_scenario("bad", (AnomalyInjection("unknown", 1),))
