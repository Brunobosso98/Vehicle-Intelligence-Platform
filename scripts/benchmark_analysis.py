"""Repeatable CPU/memory baseline for the pure Phase 2 analysis pipeline."""

import time
import tracemalloc
from dataclasses import replace
from datetime import timedelta

from vehicle_platform.analysis.alignment import align_observations
from vehicle_platform.analysis.detectors import (
    HeuristicPullDetector,
    HeuristicSegmentDetector,
)
from vehicle_platform.analysis.domain import DetectorProfile
from vehicle_platform.analysis.synthetic import mixed_drive


def main() -> None:
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
    profile = DetectorProfile()
    tracemalloc.start()
    started = time.perf_counter()
    aligned = align_observations(observations, profile)
    aligned_at = time.perf_counter()
    segments = HeuristicSegmentDetector(profile).detect(aligned)
    segmented_at = time.perf_counter()
    pulls = HeuristicPullDetector(profile).detect(aligned)
    completed = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    print(
        {
            "observations": len(observations),
            "frames": len(aligned),
            "segments": len(segments),
            "pulls": len(pulls),
            "alignment_seconds": round(aligned_at - started, 4),
            "segmentation_seconds": round(segmented_at - aligned_at, 4),
            "pull_detection_seconds": round(completed - segmented_at, 4),
            "total_seconds": round(completed - started, 4),
            "peak_mib": round(peak / 1024 / 1024, 2),
            "profile": profile.name,
        }
    )


if __name__ == "__main__":
    main()
