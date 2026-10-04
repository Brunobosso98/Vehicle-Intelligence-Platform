#!/usr/bin/env python3
"""Independent deterministic Phase 5 golden evaluator (not a unit-test runner)."""

import json
from datetime import UTC, datetime, timedelta

from vehicle_platform.analytics.domain import (
    AnalyticsConfig,
    PullInput,
    Sample,
    acceleration_interval,
    baseline,
    compare_context,
    configuration_comparison,
    pull_profile,
    repeated_pulls,
    trend,
)

START = datetime(2026, 1, 1, tzinfo=UTC)
CFG = AnalyticsConfig()


def pull(
    name: str,
    session: str,
    config: str,
    *,
    iat: float = 300,
    boost: float = 120_000,
    fuel: float = 19_000_000,
    speed_step: float = 0.5,
    rate: int = 5,
    quality: float = 1,
    rpm0: float = 3000,
    reverse: bool = False,
) -> PullInput:
    origin = (
        START + timedelta(days=30)
        if config.lower() in {"b", "configuration-b", "config-b"}
        else START
    )
    points = [
        Sample(
            origin + timedelta(seconds=i / rate),
            rpm0 + i * (2000 / (8 * rate)),
            {
                "engine.rpm": rpm0 + i * (2000 / (8 * rate)),
                "vehicle.speed": 15 + i * speed_step / rate,
                "engine.boost_pressure": boost,
                "engine.intake_air_temperature": iat + i * 0.02,
                "fuel.high_pressure": fuel,
                "engine.throttle_position": 90,
            },
        )
        for i in range(8 * rate + 1)
    ]
    if reverse:
        points = list(reversed(points))
    return PullInput(
        name,
        session,
        "vehicle",
        config,
        origin,
        origin + timedelta(seconds=8),
        quality,
        tuple(points),
    )


def check(
    name: str, expected: object, actual: object, *, tolerance: float = 0
) -> dict[str, object]:
    numeric = isinstance(expected, (int, float)) and isinstance(actual, (int, float))
    absolute = abs(float(actual) - float(expected)) if numeric else None
    relative = absolute / abs(float(expected)) if numeric and expected else None
    passed = absolute <= tolerance if numeric else actual == expected
    return {
        "scenario": name,
        "expected": expected,
        "actual": actual,
        "absolute_error": absolute,
        "relative_error": relative,
        "tolerance": tolerance,
        "pass": passed,
    }


def main() -> None:
    identical = [pull(f"identical-{i}", f"s{i}", "A") for i in range(3)]
    thermal = [
        pull(
            f"thermal-{i}",
            "thermal",
            "A",
            iat=300 + i * 5,
            boost=120_000 - i * 4_000,
            fuel=19_000_000 - i * 250_000,
            speed_step=0.5 - i * 0.04,
        )
        for i in range(6)
    ]
    noisy = [
        pull("noise-a", "noise", "A", boost=119_500),
        pull("noise-b", "noise", "A", boost=120_500, rate=10),
    ]
    other = [pull(f"other-{i}", f"o{i}", "B", boost=130_000) for i in range(3)]
    sparse = pull("sparse", "poor", "A", quality=0.2)
    non_overlap = pull("non-overlap", "n", "A", rpm0=6000)
    reports = [
        check(
            "identical boost MAD",
            0,
            repeated_pulls(identical, CFG)["repeatability"]["median_boost"]["mad"],
        ),
        check(
            "IAT accumulation K",
            5,
            repeated_pulls(thermal, CFG)["thermal"]["median_start_iat_increase"],
            tolerance=0.01,
        ),
        check(
            "progressive boost final median Pa",
            100_000,
            pull_profile(thermal[-1], CFG)["metrics"]["boost"]["median"],
        ),
        check(
            "fuel degradation final minimum Pa",
            17_750_000,
            pull_profile(thermal[-1], CFG)["metrics"]["fuel"]["minimum"],
        ),
        check(
            "normalized acceleration initial seconds",
            3,
            acceleration_interval(thermal[0].samples, 15.5, 17, CFG)["elapsed_seconds"],
            tolerance=1e-6,
        ),
        check(
            "normalized acceleration final seconds",
            5,
            acceleration_interval(thermal[-1].samples, 15.5, 17, CFG)[
                "elapsed_seconds"
            ],
            tolerance=1e-6,
        ),
        check("noisy unchanged accepted", True, compare_context(*noisy, CFG).accepted),
        check(
            "different configuration isolated",
            False,
            compare_context(identical[0], other[0], CFG).accepted,
        ),
        check(
            "before-after sufficiency",
            "sufficient",
            configuration_comparison(identical, other, CFG)["sufficiency"],
        ),
        check(
            "poor quality excluded",
            1,
            baseline(identical + [sparse], CFG)["excluded_pull_count"],
        ),
        check(
            "non-overlap rejected",
            False,
            compare_context(identical[0], non_overlap, CFG).accepted,
        ),
        check(
            "different sample rates accepted",
            True,
            compare_context(noisy[0], noisy[1], CFG).accepted,
        ),
        check(
            "duplicate/out-of-order deterministic",
            {"start": 300, "end": 300.8, "median": 300.4},
            {
                key: pull_profile(pull("ordered", "s", "A", reverse=True), CFG)[
                    "metrics"
                ]["iat"][key]
                for key in ("start", "end", "median")
            },
        ),
        check(
            "configuration trend membership",
            ["A", "B"],
            sorted(trend(identical + other, "boost", CFG)["segments_by_configuration"]),
        ),
    ]
    report = {
        "phase": 5,
        "dataset": {"configurations": 2, "sessions": 11, "pulls": 18},
        "scenarios": reports,
        "passed": sum(bool(r["pass"]) for r in reports),
        "total": len(reports),
    }
    print(json.dumps(report, indent=2, default=str))
    if report["passed"] != report["total"]:
        raise SystemExit("Phase 5 golden acceptance failed")


if __name__ == "__main__":
    main()
