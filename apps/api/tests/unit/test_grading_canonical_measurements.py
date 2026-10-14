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
