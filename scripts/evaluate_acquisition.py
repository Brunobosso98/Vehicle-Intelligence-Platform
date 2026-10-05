"""Independent recipe readiness and bounded planner acceptance."""

import json

from vehicle_platform.acquisition.domain import (
    DeviceCapabilities,
    Importance,
    Support,
    preflight,
)
from vehicle_platform.acquisition.recipes import RECIPES


def main() -> None:
    reports = []
    for recipe in RECIPES:
        signals = {r.signal: Support.SUPPORTED for r in recipe.requirements}
        healthy = preflight(recipe, DeviceCapabilities("acceptance", signals, 1000))
        blocked = preflight(recipe, DeviceCapabilities("acceptance", {}, 1000))
        constrained = preflight(recipe, DeviceCapabilities("acceptance", signals, 0))
        required = [
            r.signal for r in recipe.requirements if r.importance is Importance.REQUIRED
        ]
        minimum_budget = sum(
            r.minimum_hz
            for r in recipe.requirements
            if r.importance is Importance.REQUIRED
        )
        feasible = preflight(
            recipe, DeviceCapabilities("acceptance", signals, minimum_budget)
        )
        feasible_rates = {
            item.signal: item.estimated_hz for item in feasible.sampling_plan
        }
        passed = (
            healthy.readiness == "ready"
            and blocked.readiness == "blocked"
            and constrained.readiness == "blocked"
        )
        passed &= bool(required) and all(
            r.reason and r.minimum_hz <= r.preferred_hz for r in recipe.requirements
        )
        passed &= sum(item.estimated_hz for item in constrained.sampling_plan) == 0
        passed &= feasible.readiness != "blocked" and all(
            feasible_rates.get(r.signal, 0) >= r.minimum_hz
            for r in recipe.requirements
            if r.importance is Importance.REQUIRED
        )
        passed &= sum(feasible_rates.values()) <= minimum_budget

        reports.append(
            {
                "recipe": recipe.key,
                "healthy": str(healthy.readiness),
                "missing_required": str(blocked.readiness),
                "zero_budget": str(constrained.readiness),
                "minimum_required_budget": minimum_budget,
                "feasible_required_rates": {
                    key: feasible_rates[key] for key in required
                },
                "sampling_algorithm_version": feasible.sampling_algorithm_version,
                "pass": passed,
            }
        )
    print(
        json.dumps(
            {
                "phase": 4,
                "recipes": reports,
                "real_stack": "make phase4-stack-acceptance required",
            },
            indent=2,
        )
    )
    if not all(r["pass"] for r in reports):
        raise SystemExit("Phase 4 recipe acceptance failed")


if __name__ == "__main__":
    main()
