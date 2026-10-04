from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from vehicle_platform.analysis.alignment import align_observations, rolling_median
from vehicle_platform.analysis.detectors import HeuristicPullDetector, HeuristicSegmentDetector
from vehicle_platform.analysis.domain import DetectorProfile, Observation, SegmentType
from vehicle_platform.analysis.evaluation import evaluate_pulls
from vehicle_platform.analysis.synthetic import mixed_drive, negative_scenario


def test_profile_hash_is_stable_and_validated() -> None:
    first = DetectorProfile()
    assert first.configuration_hash == DetectorProfile().configuration_hash
    assert first.configuration_hash != replace(first, pull_min_throttle=75).configuration_hash
    with pytest.raises(ValueError):
        DetectorProfile(interval_ms=10)
    with pytest.raises(ValueError):
        DetectorProfile(pull_min_throttle=101)


def test_alignment_orders_deduplicates_expires_and_smooths() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    observations = [
        Observation(start + timedelta(seconds=3), "engine.rpm", 900, "c"),
        Observation(start, "engine.rpm", 700, "a"),
        Observation(start, "engine.rpm", 710, "b"),
        Observation(start, "vehicle.speed", 0, "d"),
    ]
    frames = align_observations(
        observations, DetectorProfile(interval_ms=1000, max_gap_seconds=2, smoothing_window=1)
    )
    assert frames[0].values["engine.rpm"] == 710
    assert frames[2].values["engine.rpm"] == 710
    assert frames[3].values["vehicle.speed"] is None
    assert rolling_median([1, 100, 2], 3) == [50.5, 2.0, 51.0]


@pytest.mark.parametrize("gap", [timedelta(seconds=10), timedelta(days=365)])
def test_expired_alignment_gap_preserves_grid_and_does_not_expand_empty_time(gap) -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    observed = start + gap + timedelta(milliseconds=50)
    frames = align_observations(
        [Observation(observed, "engine.rpm", 3000), Observation(start, "engine.rpm", 900)],
        DetectorProfile(interval_ms=100, max_gap_seconds=2, smoothing_window=1),
    )
    assert len(frames) == 21
    assert frames[0].observed_at == start
    assert frames[-1].observed_at == start + timedelta(seconds=2)
    # Add another observation to extend the final grid through the late sample.
    frames = align_observations(
        [
            Observation(observed, "engine.rpm", 3000),
            Observation(start, "engine.rpm", 900),
            Observation(observed + timedelta(milliseconds=100), "engine.rpm", 3100),
        ],
        DetectorProfile(interval_ms=100, max_gap_seconds=2, smoothing_window=1),
    )
    assert len(frames) == 22
    assert frames[-1].observed_at == start + gap + timedelta(milliseconds=100)
    assert frames[-1].values["engine.rpm"] == 3000
    assert frames[-1].gap_before


@pytest.mark.parametrize("rate", [5, 10, 20])
def test_golden_mixed_drive_detects_all_pulls(rate: int) -> None:
    scenario = mixed_drive(rate_hz=rate)
    frames = align_observations(list(scenario.observations), DetectorProfile())
    pulls = HeuristicPullDetector(DetectorProfile()).detect(frames)
    result = evaluate_pulls(scenario.ground_truth, pulls)
    assert result.true_positives == 3
    assert result.false_positives == result.false_negatives == 0
    assert result.precision >= 0.95 and result.recall >= 0.95
    assert result.mean_start_error_seconds is not None and result.mean_start_error_seconds <= 1.5


@pytest.mark.parametrize("kind", ["false-positive-throttle", "short-burst"])
def test_negative_scenarios_resist_false_positives(kind: str) -> None:
    scenario = negative_scenario(kind)
    frames = align_observations(list(scenario.observations), DetectorProfile())
    assert HeuristicPullDetector(DetectorProfile()).detect(frames) == []


def test_missing_boost_preserves_pull_with_quality_flag() -> None:
    scenario = mixed_drive(missing_boost=True)
    pulls = HeuristicPullDetector(DetectorProfile()).detect(
        align_observations(list(scenario.observations), DetectorProfile())
    )
    assert len(pulls) == 3
    result = evaluate_pulls(scenario.ground_truth, pulls)
    assert result.false_positives == result.false_negatives == 0
    assert result.f1 >= 0.95
    assert all("missing_boost" in pull.quality_flags for pull in pulls)
    assert all(pull.metrics.max_boost is None for pull in pulls)


def test_gap_is_not_bridged_and_out_of_order_is_equivalent() -> None:
    scenario = mixed_drive(telemetry_gap=True)
    frames = align_observations(list(reversed(scenario.observations)), DetectorProfile())
    pulls = HeuristicPullDetector(DetectorProfile()).detect(frames)
    assert all(not (pull.started_at.second < 43 and pull.ended_at.second > 46) for pull in pulls)


def test_segments_cover_states_and_expose_evidence() -> None:
    scenario = mixed_drive()
    segments = HeuristicSegmentDetector(DetectorProfile()).detect(
        align_observations(list(scenario.observations), DetectorProfile())
    )
    kinds = {segment.segment_type for segment in segments}
    assert {
        SegmentType.IDLE,
        SegmentType.WARM_UP,
        SegmentType.CRUISE,
        SegmentType.PULL,
        SegmentType.DECELERATION,
    } <= kinds
    assert all(
        0 <= segment.confidence <= 1 and "signal_coverage" in segment.evidence
        for segment in segments
    )


def test_generator_is_deterministic_and_noisy_irregular_remains_detectable() -> None:
    assert mixed_drive(seed=7).observations == mixed_drive(seed=7).observations
    scenario = mixed_drive(seed=8, noisy=True, irregular=True)
    pulls = HeuristicPullDetector(DetectorProfile()).detect(
        align_observations(list(scenario.observations), DetectorProfile())
    )
    assert len(pulls) == 3
