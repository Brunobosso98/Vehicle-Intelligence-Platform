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
    start: datetime = START,
) -> PullInput:
    samples = tuple(
        Sample(
            start + timedelta(seconds=i / 5),
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
        start,
        start + timedelta(seconds=8),
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
    trends = trend(
        pulls
        + [make_pull(f"new-{i}", session=f"new-s{i}", configuration="config-b") for i in range(3)],
        "boost",
        AnalyticsConfig(),
    )
    assert len(trends["segments_by_configuration"]) == 2
    after = [
        make_pull(
            f"b{i}",
            session=f"b-session-{i}",
            configuration="config-b",
            start=START + timedelta(days=30),
            offset=2000,
        )
        for i in range(3)
    ]
    comparison = configuration_comparison(pulls, after, AnalyticsConfig())
    assert comparison["sufficiency"] == Sufficiency.SUFFICIENT
    assert "not root-cause" in comparison["language"]
    assert comparison["metric_deltas"]["boost"]["absolute"] == 2000
    reversed_comparison = configuration_comparison(after, pulls[:3], AnalyticsConfig())
    assert reversed_comparison["sufficiency"] == Sufficiency.INSUFFICIENT
    assert reversed_comparison["metric_deltas"]["boost"]["absolute"] is None


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
    empty = baseline([], AnalyticsConfig())
    assert empty["sufficiency"] == Sufficiency.INSUFFICIENT
    assert empty["limitations"] == ["insufficient_same_configuration_sessions"]
    assert empty["session_count"] == empty["pull_count"] == 0
    assert empty["source_ids"] == {"pulls": [], "sessions": []}
    assert trend([make_pull("a")], "boost", AnalyticsConfig())["limitations"] == [
        "insufficient_comparable_history"
    ]


def test_event_time_order_duplicates_and_empty_comparisons() -> None:
    from dataclasses import replace

    pull = make_pull("ordered")
    reversed_input = replace(pull, samples=tuple(reversed(pull.samples)) + (pull.samples[0],))
    assert pull_profile(reversed_input, AnalyticsConfig()) == pull_profile(pull, AnalyticsConfig())
    empty = replace(pull, id="empty", samples=())
    compared = compare_pulls([empty, replace(empty, id="second")], AnalyticsConfig())
    assert compared["sufficiency"] == Sufficiency.INSUFFICIENT
    assert compared["common_rpm_range"] is None
    assert compared["metric_deltas"]["boost"][1]["absolute"] is None


def test_comparison_uses_only_shared_rpm_measurements() -> None:
    from dataclasses import replace

    left = make_pull("a")
    right = make_pull("b", rpm_start=4000)
    # The common 4000..5000 RPM range gives 103000 Pa left, 101000 Pa
    # right. Full-pull medians are both 102000 and would falsely report zero.
    compared = compare_pulls([left, right], AnalyticsConfig())
    assert compared["common_rpm_range"] == [4000, 5000]
    assert compared["metric_deltas"]["boost"][1]["absolute"] == -2000
    incompatible = replace(right, configuration_id="other")
    rejected = compare_pulls([left, incompatible], AnalyticsConfig())
    assert rejected["sufficiency"] == Sufficiency.INSUFFICIENT
    assert rejected["metric_deltas"]["boost"][1]["absolute"] is None


def test_acceleration_rejects_gap_between_valid_crossings() -> None:
    samples = tuple(
        Sample(START + timedelta(seconds=t), 3000 + t * 100, {"vehicle.speed": v})
        for t, v in [(0, 10), (0.5, 12), (4, 18), (4.5, 20)]
    )
    assert acceleration_interval(samples, 11, 19, AnalyticsConfig())["elapsed_seconds"] is None


def test_baseline_sessions_do_not_form_one_continuous_acquisition() -> None:
    from dataclasses import replace

    pulls = []
    for index in range(3):
        pull = make_pull(str(index), session=f"s{index}", offset=index * 1000)
        shift = timedelta(days=index)
        pulls.append(
            replace(
                pull,
                started_at=pull.started_at + shift,
                ended_at=pull.ended_at + shift,
                samples=tuple(replace(s, observed_at=s.observed_at + shift) for s in pull.samples),
            )
        )
    result = baseline(pulls, AnalyticsConfig())
    first_bin = result["envelopes"]["boost"][0]
    assert first_bin["sufficiency"] == Sufficiency.SUFFICIENT
    assert first_bin["median"] == 101200
    assert first_bin["mad"] == 1000
    assert first_bin["session_count"] == 3
    assert first_bin["p90"] is None  # Three pull centers do not justify a percentile envelope.
    assert (
        baseline([replace(p, samples=()) for p in pulls], AnalyticsConfig())["sufficiency"]
        == Sufficiency.INSUFFICIENT
    )


def test_configuration_comparison_rejects_other_vehicle_or_operating_range() -> None:
    from dataclasses import replace

    before = [make_pull(str(i), session=f"s{i}") for i in range(3)]
    after = [
        make_pull(f"b{i}", session=f"b{i}", configuration="B", rpm_start=6000) for i in range(3)
    ]
    assert (
        configuration_comparison(before, after, AnalyticsConfig())["sufficiency"]
        == Sufficiency.INSUFFICIENT
    )
    after = [replace(p, vehicle_id="another") for p in before]
    assert configuration_comparison(before, after, AnalyticsConfig())["limitations"] == [
        "different_vehicle"
    ]
    assert spearman([1] * 5, [2] * 5)[1] == Sufficiency.INSUFFICIENT


@pytest.mark.parametrize(
    "fields",
    [
        {"minimum_completeness": 0},
        {"minimum_completeness": 2},
        {"minimum_rpm_overlap": float("nan")},
        {"minimum_rpm_overlap": -1},
        {"minimum_baseline_sessions": 2},
        {"minimum_correlation_samples": 4},
    ],
)
def test_evidence_threshold_configuration_cannot_be_weakened(fields: dict) -> None:
    with pytest.raises(ValueError):
        AnalyticsConfig(**fields)


def test_history_empty_and_cross_vehicle_guardrails() -> None:
    from dataclasses import replace

    pulls = [make_pull(str(i), session=f"s{i}") for i in range(3)]
    mixed = baseline(pulls + [replace(pulls[0], vehicle_id="another")], AnalyticsConfig())
    assert mixed["limitations"] == ["mixed_vehicle"]
    assert (
        configuration_comparison([], pulls, AnalyticsConfig())["sufficiency"]
        == Sufficiency.INSUFFICIENT
    )
    assert configuration_comparison(pulls, pulls, AnalyticsConfig())["limitations"] == [
        "same_configuration"
    ]


def test_trends_and_correlations_require_comparable_history() -> None:
    from dataclasses import replace

    pulls = [make_pull(str(i)) for i in range(6)]
    assert trend(pulls, "boost", AnalyticsConfig())["sufficiency"] == Sufficiency.INSUFFICIENT
    incompatible = [replace(p, configuration_id=f"config-{i}") for i, p in enumerate(pulls)]
    result = repeated_pulls(incompatible, AnalyticsConfig())
    assert result["repeatability"] == {}
    assert result["associations"][0]["coefficient"] is None
    assert result["associations"][0]["sample_size"] == 0
    missing = replace(
        pulls[0], samples=tuple(replace(s, values={"engine.rpm": s.rpm}) for s in pulls[0].samples)
    )
    assert trend([missing], "boost", AnalyticsConfig())["point_count"] == 0


def test_analytics_spans_use_request_provider_and_do_not_export_payloads() -> None:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from vehicle_platform.analytics.instrumentation import CURRENT_TRACER, traced

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    token = CURRENT_TRACER.set(provider.get_tracer("test"))
    try:

        @traced("analytics.normalization")
        def calculate(value: int) -> int:
            return value * 2

        assert calculate(21) == 42
        spans = exporter.get_finished_spans()
        assert [s.name for s in spans] == ["analytics.normalization"]
        assert not spans[0].attributes
    finally:
        CURRENT_TRACER.reset(token)
        provider.shutdown()


def test_profiles_preserve_canonical_event_markers_in_common_window() -> None:
    from dataclasses import replace

    first = replace(
        make_pull("a"),
        event_markers=(
            {"id": "canonical", "event_type": "boost_drop", "rpm": 3500},
            {"id": "outside", "event_type": "iat_rise", "rpm": 2000},
        ),
    )
    result = compare_pulls([first, make_pull("b")], AnalyticsConfig())
    assert result["profiles"][0]["event_markers"] == [
        {"id": "canonical", "event_type": "boost_drop", "rpm": 3500}
    ]
    assert result["profiles"][0]["event_ids"] == ["event-a"]


def test_observed_acceleration_thermal_rate_and_interval_configuration() -> None:
    profile = pull_profile(make_pull("rates"), AnalyticsConfig(speed_intervals_kmh=((60, 100),)))
    # 0.5 m/s each 0.2 seconds and 0.1 K each 0.2 seconds.
    assert profile["metrics"]["acceleration"]["median"] == pytest.approx(2.5)
    assert profile["metrics"]["iat"]["rate_per_second"] == pytest.approx(0.5)
    assert len(profile["acceleration_intervals"]) == 1
    assert profile["observation_count"] == 41 * 8
    assert (
        AnalyticsConfig(speed_intervals_kmh=((60, 100),)).configuration_hash
        != AnalyticsConfig().configuration_hash
    )
    for intervals in ((), ((100, 60),), ((0, float("inf")),), ((0, 301),)):
        with pytest.raises(ValueError):
            AnalyticsConfig(speed_intervals_kmh=intervals)


def test_thermal_recovery_reports_only_observed_endpoints_without_invented_threshold_time() -> None:
    first = make_pull("a", start=START)
    second = make_pull("b", offset=10000, start=START + timedelta(seconds=20))
    result = repeated_pulls([first, second], AnalyticsConfig())
    recovery = result["thermal"]["between_pull_recovery"][0]
    assert recovery["elapsed_seconds"] == 12
    assert recovery["iat_delta"] == pytest.approx(-3)
    assert recovery["time_to_threshold_seconds"] is None
