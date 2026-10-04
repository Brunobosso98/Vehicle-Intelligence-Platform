from datetime import UTC, datetime, timedelta

import pytest

from vehicle_platform.analytics.domain import (
    AnalyticsConfig,
    PullInput,
    Sample,
    Sufficiency,
    acceleration_interval,
    baseline,
    bin_statistics,
    coefficient_of_variation,
    compare_context,
    compare_pulls,
    configuration_comparison,
    iqr,
    mad,
    median,
    percentile,
    pull_profile,
    repeated_pulls,
    spearman,
    trend,
)

START = datetime(2025, 1, 1, tzinfo=UTC)


def make_pull(
    name: str,
    *,
    session: str = "session-1",
    configuration: str = "config-a",
    offset: float = 0,
    completeness: float = 1,
    rpm_start: float = 3000,
) -> PullInput:
    samples = tuple(
        Sample(
            START + timedelta(seconds=i / 5),
            rpm_start + i * 50,
            {
                "engine.rpm": rpm_start + i * 50,
                "vehicle.speed": 15 + i * 0.5,
                "engine.boost_pressure": 100000 + offset + i * 100,
                "engine.intake_air_temperature": 310 + offset / 10000 + i * 0.1,
                "engine.coolant_temperature": 360 + i * 0.02,
                "engine.oil_temperature": 365 + i * 0.02,
                "fuel.high_pressure": 15000000 - i * 1000,
                "engine.throttle_position": 90,
            },
        )
        for i in range(41)
    )
    return PullInput(
        name,
        session,
        "vehicle-1",
        configuration,
        START,
        START + timedelta(seconds=8),
        completeness,
        samples,
        (f"event-{name}",),
    )


def test_robust_statistics_and_guards() -> None:
    assert median([9, 1, 3, 5]) == 4
    assert percentile([0, 10], 0.25) == 2.5
    assert mad([1, 2, 100]) == 1
    assert iqr([0, 10, 20, 30, 40]) == 20
    assert coefficient_of_variation([0, 0]) is None
    assert spearman([1, 2, 3], [1, 2, 3])[1] == Sufficiency.INSUFFICIENT
    assert spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])[0] == -1


def test_config_hash_is_deterministic_and_bounded() -> None:
    assert AnalyticsConfig().configuration_hash == AnalyticsConfig().configuration_hash
    with pytest.raises(ValueError):
        AnalyticsConfig(rpm_bin_size=1)
    with pytest.raises(ValueError):
        AnalyticsConfig(maximum_pulls=1000)


def test_comparability_exposes_dimensions_and_rejections() -> None:
    config = AnalyticsConfig()
    result = compare_context(make_pull("a"), make_pull("b", offset=1000), config)
    assert result.accepted and result.common_rpm_range == (3000, 5000)
    assert set(result.dimensions) == {
        "rpm_overlap",
        "duration_similarity",
        "throttle_similarity",
        "thermal_similarity",
        "quality_similarity",
    }
    rejected = compare_context(make_pull("a"), make_pull("b", configuration="config-b"), config)
    assert not rejected.accepted and "different_configuration" in rejected.reasons
    assert not compare_context(make_pull("a"), make_pull("b", rpm_start=6000), config).accepted


def test_bins_do_not_bridge_gaps_and_require_samples() -> None:
    pull = make_pull("a")
    bins = bin_statistics(pull.samples, "engine.boost_pressure", 3000, 5000, AnalyticsConfig())
    assert bins[0]["median"] == 100200
    sparse = tuple((pull.samples[0], pull.samples[-1]))
    assert (
        bin_statistics(sparse, "engine.boost_pressure", 3000, 5000, AnalyticsConfig())[0]["median"]
        is None
    )


def test_pull_metrics_units_curves_events_and_intervals() -> None:
    profile = pull_profile(make_pull("a"), AnalyticsConfig())
    assert profile["sufficiency"] == Sufficiency.SUFFICIENT
    assert profile["metrics"]["boost"]["unit"] == "Pa"  # type: ignore[index]
    assert profile["metrics"]["fuel"]["minimum"] == 14_960_000  # type: ignore[index]
    assert profile["metrics"]["iat"]["delta"] == pytest.approx(4)  # type: ignore[index]
    assert profile["event_ids"] == ["event-a"]
    interval = acceleration_interval(make_pull("a").samples, 16, 24, AnalyticsConfig())
    assert interval["elapsed_seconds"] == pytest.approx(3.2)
    assert (
        acceleration_interval(make_pull("a").samples, 1, 50, AnalyticsConfig())["sufficiency"]
        == Sufficiency.INSUFFICIENT
    )


def test_comparison_repeatability_and_correlation_are_evidence_first() -> None:
    pulls = [make_pull(str(i), offset=i * 1000) for i in range(6)]
    compared = compare_pulls(pulls, AnalyticsConfig())
    assert compared["sufficiency"] == Sufficiency.SUFFICIENT
    assert compared["common_rpm_range"] == [3000, 5000]
    repeated = repeated_pulls(pulls, AnalyticsConfig())
    assert len(repeated["sequence"]) == 6
    assert repeated["repeatability"]["median_boost"]["mad"] == 1500  # type: ignore[index]
    assert repeated["associations"][0]["sample_size"] == 6  # type: ignore[index]
    assert "not causal" in repeated["associations"][0]["interpretation"]  # type: ignore[index]


def test_baseline_quality_configuration_trend_and_before_after() -> None:
    pulls = [make_pull(str(i), session=f"session-{i}") for i in range(3)]
    result = baseline(
        pulls + [make_pull("poor", session="poor", completeness=0.2)], AnalyticsConfig()
    )
    assert result["sufficiency"] == Sufficiency.SUFFICIENT
    assert result["session_count"] == 3 and result["excluded_pull_count"] == 1
    mixed = baseline(pulls + [make_pull("other", configuration="config-b")], AnalyticsConfig())
    assert mixed["limitations"] == ["mixed_configuration"]
    trends = trend(pulls + [make_pull("new", configuration="config-b")], "boost", AnalyticsConfig())
    assert len(trends["segments_by_configuration"]) == 2
    after = [
        make_pull(f"b{i}", session=f"b-session-{i}", configuration="config-b") for i in range(3)
    ]
    comparison = configuration_comparison(pulls, after, AnalyticsConfig())
    assert comparison["sufficiency"] == Sufficiency.SUFFICIENT
    assert "not root-cause" in comparison["language"]


def test_analytics_negative_and_boundary_paths() -> None:
    with pytest.raises(ValueError):
        AnalyticsConfig(minimum_bin_samples=1)
    with pytest.raises(ValueError):
        AnalyticsConfig(maximum_gap_seconds=0)
    assert percentile([], 0.5) is None
    with pytest.raises(ValueError):
        percentile([1], 2)
    assert coefficient_of_variation([1]) is None
    empty = PullInput(
        "empty",
        "session",
        "vehicle-1",
        "config-a",
        START,
        START + timedelta(seconds=1),
        1,
        (),
    )
    assert (
        compare_context(empty, make_pull("a"), AnalyticsConfig()).reasons[-1] == "missing_samples"
    )
    assert (
        "poor_quality"
        in compare_context(
            make_pull("a", completeness=0.1), make_pull("b"), AnalyticsConfig()
        ).reasons
    )
    assert pull_profile(empty, AnalyticsConfig())["sufficiency"] == Sufficiency.INSUFFICIENT
    assert (
        pull_profile(make_pull("limited", completeness=0.5), AnalyticsConfig())["sufficiency"]
        == Sufficiency.LIMITED
    )
    with pytest.raises(ValueError):
        compare_pulls([make_pull("a")], AnalyticsConfig())
    assert baseline([make_pull("a")], AnalyticsConfig())["sufficiency"] == Sufficiency.INSUFFICIENT
    assert baseline([], AnalyticsConfig())["sufficiency"] == Sufficiency.INSUFFICIENT
    assert trend([make_pull("a")], "boost", AnalyticsConfig())["limitations"] == [
        "insufficient_comparable_history"
    ]
