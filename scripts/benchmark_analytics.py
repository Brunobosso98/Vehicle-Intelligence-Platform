#!/usr/bin/env python3
import time
import tracemalloc
from datetime import UTC, datetime, timedelta

from vehicle_platform.analytics.domain import (
    AnalyticsConfig,
    PullInput,
    Sample,
    baseline,
    compare_pulls,
    pull_profile,
    repeated_pulls,
    trend,
)


def main() -> None:
    config, start = AnalyticsConfig(), datetime(2025, 1, 1, tzinfo=UTC)
    pulls: list[PullInput] = []
    for pull_index in range(100):
        samples = tuple(
            Sample(
                start + timedelta(minutes=pull_index, milliseconds=index * 20),
                2500 + index * 2,
                {
                    "engine.rpm": 2500 + index * 2,
                    "vehicle.speed": 15 + index / 50,
                    "engine.boost_pressure": 90000 + index * 10,
                    "engine.intake_air_temperature": 305 + pull_index / 10,
                    "fuel.high_pressure": 15_000_000 - index * 10,
                    "engine.throttle_position": 90,
                },
            )
            for index in range(1001)
        )
        pulls.append(
            PullInput(
                str(pull_index),
                f"session-{pull_index // 4}",
                "vehicle",
                "config-a",
                samples[0].observed_at,
                samples[-1].observed_at,
                1,
                samples,
            )
        )
    tracemalloc.start()
    timings: dict[str, float] = {}
    then = time.perf_counter()
    profiles = [pull_profile(pull, config) for pull in pulls]
    timings["normalization_and_pull"] = time.perf_counter() - then
    for name, operation in (
        ("repeated", lambda: repeated_pulls(pulls[:20], config)),
        ("baseline", lambda: baseline(pulls, config)),
        ("comparison", lambda: compare_pulls(pulls[:3], config)),
        ("trend", lambda: trend(pulls, "boost", config)),
    ):
        then = time.perf_counter()
        operation()
        timings[name] = time.perf_counter() - then
    _, peak = tracemalloc.get_traced_memory()
    print(
        {
            "observations": 100100,
            "sessions": 25,
            "pulls": len(pulls),
            "bin_count": sum(len(p["curves"]["boost"]) for p in profiles),
            "timings_seconds": timings,
            "total_seconds": sum(timings.values()),
            "peak_python_bytes": peak,
        }
    )


if __name__ == "__main__":
    main()
