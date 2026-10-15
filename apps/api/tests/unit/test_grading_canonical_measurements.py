import pytest

from vehicle_platform.evaluation.grading import semantic_binding_paths


def paths(
    path, *, tool="get_session_summary", value=2.0, expected=2.0, unit=None, source_unit=None
):
    binding = {"evidence_id": "owned", "path": path, "value": value, "unit": unit}
    source = {
        "source_tool": tool,
        "facts": [{"path": path, "value": expected, "unit": source_unit}],
    }
    return semantic_binding_paths(binding, {"owned": source})


@pytest.mark.parametrize("statistic", ["count", "maximum_seconds"])
def test_canonical_recorded_signal_gap_measurements_are_quality_evidence(statistic):
    assert "quality" in paths(
        f"/gaps_by_signal/engine.rpm/{statistic}", tool="get_session_capabilities"
    )


def test_capability_report_does_not_gain_analytics_measurement_meaning():
    assert "normalized_acceleration" not in paths(
        "/result/metrics/acceleration/mean", tool="get_session_capabilities"
    )


@pytest.mark.parametrize(
    ("signal", "unit", "value"),
    [("engine.throttle_position", "%", 90.0), ("engine.intake_air_temperature", "K", 310.0)],
)
def test_raw_point_measurement_uses_its_canonical_source_channel(signal, unit, value):
    binding = {"evidence_id": "owned", "path": "/points/0/value", "value": value, "unit": unit}
    source = {
        "source_tool": "get_telemetry_window",
        "facts": [
            {"path": "/points/0/value", "value": value, "unit": unit},
            {"path": "/points/0/signal", "value": signal},
        ],
    }
    assert signal in semantic_binding_paths(binding, {"owned": source})
    source["facts"][1]["value"] = "invented.channel"
    assert "invented.channel" not in semantic_binding_paths(binding, {"owned": source})
    source["facts"][1]["value"] = signal
    binding["value"] = value + 1
    assert signal not in semantic_binding_paths(binding, {"owned": source})


@pytest.mark.parametrize("metric", ["actual_hz", "missing_ratio", "stale_ratio"])
def test_indexed_quality_statistic_retains_its_supported_canonical_channel(metric):
    path = f"/signal_quality/0/{metric}"
    binding = {"evidence_id": "owned", "path": path, "value": 0.5, "unit": None}
    source = {
        "source_tool": "get_session_capabilities",
        "facts": [
            {"path": path, "value": 0.5, "unit": None},
            {"path": "/signal_quality/0/signal", "value": "fuel.high_pressure"},
        ],
    }
    assert "fuel.high_pressure" in semantic_binding_paths(binding, {"owned": source})
    source["facts"][1]["value"] = "invented.channel"
    assert "invented.channel" not in semantic_binding_paths(binding, {"owned": source})


@pytest.mark.parametrize(
    ("path", "tool", "value", "expected"),
    [
        ("/sample_count", "get_session_capabilities", 2, 2),
        ("/gaps_by_signal/engine.rpm/count", "get_vehicle", 2, 2),
        ("/gaps_by_signal/not_a_canonical_signal/count", "get_session_capabilities", 2, 2),
        ("/gaps_by_signal/engine.rpm/count", "get_session_capabilities", -2, -2),
        ("/gaps_by_signal/engine.rpm/count", "get_session_capabilities", 2, 3),
    ],
)
def test_unrelated_unsupported_or_invalid_counts_do_not_gain_quality_meaning(
    path, tool, value, expected
):
    assert "quality" not in paths(path, tool=tool, value=value, expected=expected)


@pytest.mark.parametrize(
    "path",
    [
        "/result/metrics/acceleration/mean",
        "/result/metric_deltas/acceleration/0/absolute",
    ],
)
def test_canonical_acceleration_statistics_are_recognized_as_performance_measurements(path):
    assert "normalized_acceleration" in paths(path)


@pytest.mark.parametrize(
    "path",
    [
        "/result/sequence/0/start_coolant",
        "/result/sequence/1/end_oil",
        "/result/metrics/coolant/median",
        "/result/envelopes/oil/0/p90",
    ],
)
def test_canonical_coolant_oil_values_are_recognized_as_temperature_measurements(path):
    assert "temperature" in paths(path)


@pytest.mark.parametrize(
    "changes",
    [
        {"tool": "get_vehicle"},
        {"value": None, "expected": None},
        {"value": True, "expected": True},
        {"value": 3.0},
        {"unit": "wrong"},
    ],
)
def test_unrelated_null_boolean_unsupported_or_wrong_unit_facts_do_not_gain_aliases(changes):
    path = "/result/metrics/acceleration/mean"
    assert paths(path, **changes) == [path]


@pytest.mark.parametrize(
    "path",
    [
        "/result/metrics/acceleration/count",
        "/result/sequence/0/pull_id",
        "/result/envelopes/coolant/0/rpm_start",
        "/result/envelopes/oil/0/session_count",
    ],
)
def test_counts_identifiers_and_rpm_bounds_are_not_acceleration_or_temperature(path):
    assert paths(path) == [path]
