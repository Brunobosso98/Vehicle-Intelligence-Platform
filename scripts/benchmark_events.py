"""Repeatable Phase 3 CPU/allocation benchmark; informational, never a latency gate."""

import json
import time
import tracemalloc
from dataclasses import asdict, replace
from datetime import timedelta

from vehicle_platform.analysis.alignment import align_observations
from vehicle_platform.analysis.detectors import HeuristicPullDetector
from vehicle_platform.analysis.domain import AlignedFrame, DetectorProfile
from vehicle_platform.analysis.synthetic import mixed_drive
from vehicle_platform.events.domain import PullWindow
from vehicle_platform.events.engine import EventEngine, consolidate_events
from vehicle_platform.events.synthetic import golden_scenarios


def timed(
    name: str, frames: list[AlignedFrame], pulls: list[PullWindow], observations: int
) -> dict[str, object]:
    tracemalloc.start()
    started = time.perf_counter()
    # Pull windows are supplied by Phase 2; tuple materialization represents baseline preparation.
    pulls = list(pulls)
    prepared = time.perf_counter()
    engine = EventEngine()
    results = []
    per_detector: dict[str, float] = {}
    for detector in engine.detectors:
        detector_started = time.perf_counter()
        results.append(detector.detect(frames, pulls))
        per_detector[detector.name] = round(time.perf_counter() - detector_started, 4)
    detected = time.perf_counter()
    events = consolidate_events(
        [event for result in results for event in result.events],
        engine.profile.consolidation_gap_seconds,
    )
    consolidated = time.perf_counter()
    # Measures bounded payload preparation; SQL persistence is covered by disposable Timescale tests.
    json.dumps([asdict(event) for event in events], default=str)
    persisted = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "scenario": name,
        "observations": observations,
        "frames": len(frames),
        "detectors": len(results),
        "events": len(events),
        "baseline_preparation_seconds": round(prepared - started, 4),
        "detector_execution_seconds": round(detected - prepared, 4),
        "per_detector_seconds": per_detector,
        "consolidation_seconds": round(consolidated - detected, 4),
        "persistence_payload_seconds": round(persisted - consolidated, 4),
        "total_seconds": round(persisted - started, 4),
        "peak_python_mib": round(peak / 1024 / 1024, 2),
    }


def main() -> None:
    profile = DetectorProfile()
    source = mixed_drive(rate_hz=20).observations
    observations = []
    for repetition in range(5):
        shift = timedelta(seconds=170 * repetition)
        observations.extend(
            replace(
                item,
                observed_at=item.observed_at + shift,
                sample_id=f"{repetition}:{item.sample_id}",
            )
            for item in source
        )
    load_started = time.perf_counter()
    large_frames = align_observations(observations, profile)
    loaded = time.perf_counter()
    detected_pulls = HeuristicPullDetector(profile).detect(large_frames)
    large_pulls = [
        PullWindow(
            pull.started_at,
            pull.ended_at,
            tuple(
                frame
                for frame in large_frames
                if pull.started_at <= frame.observed_at <= pull.ended_at
            ),
        )
        for pull in detected_pulls
    ]
    scenarios = golden_scenarios()
    reports = [
        timed(
            scenarios[0].name,
            list(scenarios[0].frames),
            list(scenarios[0].pulls),
            len(scenarios[0].frames) * 8,
        ),
        timed(
            scenarios[-1].name,
            list(scenarios[-1].frames),
            list(scenarios[-1].pulls),
            len(scenarios[-1].frames) * 8,
        ),
        timed("large-session", large_frames, large_pulls, len(observations)),
    ]
    reports[-1]["telemetry_load_seconds"] = round(loaded - load_started, 4)
    print({"phase": 3, "informational": True, "reports": reports})


if __name__ == "__main__":
    main()
