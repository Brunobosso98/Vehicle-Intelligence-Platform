"""Independent Phase 2 acceptance; every scenario is matched before aggregation."""

import json
from dataclasses import asdict

from vehicle_platform.analysis.alignment import align_observations
from vehicle_platform.analysis.detectors import HeuristicPullDetector
from vehicle_platform.analysis.domain import DetectorProfile
from vehicle_platform.analysis.evaluation import evaluate_pulls
from vehicle_platform.analysis.synthetic import mixed_drive, negative_scenario


def main() -> None:
    profile = DetectorProfile()
    scenarios = [(f"mixed-{rate}Hz", mixed_drive(rate_hz=rate)) for rate in (5, 10, 20)]
    scenarios += [
        ("missing-boost", mixed_drive(missing_boost=True)),
        ("irregular-noisy", mixed_drive(irregular=True, noisy=True, seed=8)),
        ("out-of-order", mixed_drive()),
        ("stationary-throttle", negative_scenario("false-positive-throttle")),
        ("short-burst", negative_scenario("short-burst")),
    ]
    reports = []
    for name, scenario in scenarios:
        observations = list(scenario.observations)
        if name == "out-of-order":
            observations.reverse()
        detected = HeuristicPullDetector(profile).detect(
            align_observations(observations, profile)
        )
        result = evaluate_pulls(scenario.ground_truth, detected)
        passed = (
            result.precision >= 0.95 and result.recall >= 0.95 and result.f1 >= 0.95
        )
        passed &= all(
            error is None or error <= 1.5
            for error in (
                result.mean_start_error_seconds,
                result.mean_end_error_seconds,
            )
        )
        reports.append({"scenario": name, **asdict(result), "pass": passed})
    gap = mixed_drive(telemetry_gap=True)
    detected = HeuristicPullDetector(profile).detect(
        align_observations(list(gap.observations), profile)
    )
    # The scripted 103..106 s gap must never be bridged by a candidate.
    origin = gap.observations[0].observed_at
    bridged = any(
        (p.started_at - origin).total_seconds() < 103
        and (p.ended_at - origin).total_seconds() > 106
        for p in detected
    )
    reports.append(
        {"scenario": "telemetry-gap", "bridged": bridged, "pass": not bridged}
    )
    print(json.dumps({"phase": 2, "scenarios": reports}, indent=2))
    if not all(r["pass"] for r in reports):
        raise SystemExit("Phase 2 acceptance failed")


if __name__ == "__main__":
    main()
