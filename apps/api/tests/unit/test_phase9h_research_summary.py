"""Research snapshot tolerates only bounded bootstrap interval resampling jitter."""

import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[4] / "scripts/check_phase9h_research_summary.py"
spec = importlib.util.spec_from_file_location("phase9h_research_summary", MODULE)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_current_fresh_source_bootstrap_intervals_are_within_documented_tolerance():
    module._check_bootstrap_interval(
        "NEXT_PULL_FUEL_DEVIATION",
        "brierCi",
        [0.10648, 0.17281],
        [0.10591, 0.17544],
    )
    module._check_bootstrap_interval(
        "NEXT_PULL_FUEL_DEVIATION",
        "eceCi",
        [0.05945, 0.16806],
        [0.05760, 0.18301],
    )
    module._check_bootstrap_interval(
        "NEXT_PULL_THERMAL_DEGRADATION",
        "eceCi",
        [0.05937, 0.20237],
        [0.06007, 0.17933],
    )


def test_bootstrap_interval_outside_tolerance_fails():
    with pytest.raises(ValueError, match="endpoint delta exceeds 0.030"):
        module._check_bootstrap_interval(
            "NEXT_PULL_FUEL_DEVIATION",
            "eceCi",
            [0.05945, 0.16806],
            [0.05760, 0.19809],
        )


@pytest.mark.parametrize(
    "interval",
    ([0.2], [0.7, 0.3], [float("nan"), 0.8]),
)
def test_malformed_bootstrap_interval_fails(interval):
    with pytest.raises(ValueError, match="ordered finite interval"):
        module._check_bootstrap_interval("TASK", "brierCi", interval, [0.2, 0.8])
