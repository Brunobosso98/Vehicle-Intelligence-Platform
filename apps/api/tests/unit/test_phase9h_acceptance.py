"""Vehicle scoping rules for the Phase 9H disposable-database oracle."""

import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[4] / "scripts/phase9h_acceptance.py"
spec = importlib.util.spec_from_file_location("phase9h_acceptance", MODULE)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_vehicle_scope_ids_are_sorted_and_unique():
    rows = [
        {"vehicle_id": "vehicle-b"},
        {"vehicle_id": "vehicle-a"},
        {"vehicle_id": "vehicle-b"},
    ]

    assert module._vehicle_scope_ids(rows) == ["vehicle-a", "vehicle-b"]


def test_vehicle_scope_rejects_more_than_operator_allowlist_bound():
    rows = [{"vehicle_id": f"vehicle-{index}"} for index in range(21)]

    with pytest.raises(RuntimeError, match="20-vehicle controlled operator allowlist"):
        module._vehicle_scope_ids(rows)


def test_vehicle_scope_rejects_an_empty_source_set():
    with pytest.raises(RuntimeError, match="no vehicle scopes"):
        module._vehicle_scope_ids([])


@pytest.mark.parametrize(
    ("stored", "response", "matches"),
    [
        ("True", True, True),
        ("False", False, True),
        (None, None, True),
        ("True", False, False),
        (None, True, False),
        ("True", 1, False),
    ],
)
def test_stored_decision_matches_text_column_representation(stored, response, matches):
    assert module._stored_decision_matches(stored, response) is matches


@pytest.mark.parametrize(
    ("left", "right", "matches"),
    [
        (0.25, 0.25, True),
        (0.25, 0.2500000000001, True),
        (0.25, 0.25000000001, False),
        (None, None, True),
        (None, 0.25, False),
        (True, 1, False),
    ],
)
def test_same_number_uses_database_float_tolerance(left, right, matches):
    assert module._same_number(left, right) is matches
