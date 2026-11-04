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
