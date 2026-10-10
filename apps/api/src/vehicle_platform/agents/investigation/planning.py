"""Deterministic Phase 7B mapping into Phase 4 recipes and sampling preflight."""

from dataclasses import dataclass

from vehicle_platform.acquisition.domain import (
    DeviceCapabilities,
    LoggingRecipe,
    PreflightResult,
    Readiness,
    Support,
    preflight,
)
from vehicle_platform.acquisition.recipes import RECIPES
from vehicle_platform.agents.investigation.domain import (
    Availability,
    Feasibility,
    RecipeReference,
    Resolution,
    SignalNeed,
    SignalRole,
)
from vehicle_platform.telemetry.domain import SIGNAL_BY_KEY

# This is semantic intent only. Every mapped key must exist in both canonical
# telemetry and the Phase 4 recipe catalog; no PID or provider string enters it.
ROLE_TO_SIGNAL: dict[SignalRole, str | None] = {
    SignalRole.ENGINE_SPEED: "engine.rpm",
    SignalRole.VEHICLE_SPEED: "vehicle.speed",
    SignalRole.THROTTLE: "engine.throttle_position",
    SignalRole.BOOST: "engine.boost_pressure",
    SignalRole.INTAKE_TEMPERATURE: "engine.intake_air_temperature",
    SignalRole.COOLANT_TEMPERATURE: "engine.coolant_temperature",
    SignalRole.OIL_TEMPERATURE: "engine.oil_temperature",
    SignalRole.HIGH_FUEL_PRESSURE: "fuel.high_pressure",
    SignalRole.LOW_FUEL_PRESSURE: "fuel.low_pressure",
    SignalRole.LAMBDA: "fuel.equivalence_ratio",
    SignalRole.TIMING: "engine.ignition_timing",
    SignalRole.DATA_QUALITY: None,
}
CATALOG_SIGNALS = frozenset(
    requirement.signal for recipe in RECIPES for requirement in recipe.requirements
)
if not {signal for signal in ROLE_TO_SIGNAL.values() if signal} <= set(SIGNAL_BY_KEY):
    raise RuntimeError("investigation signal mapping diverged from canonical telemetry")


@dataclass(frozen=True)
class PlannedRecipe:
    recipe: LoggingRecipe | None
    preflight: PreflightResult | None
    reference: RecipeReference | None
    needs: tuple[SignalNeed, ...]


def resolve_needs(
    needs: list[SignalNeed],
    source: DeviceCapabilities | None,
    recorded_signals: set[str] | None = None,
) -> tuple[SignalNeed, ...]:
    """Keep source support distinct from what a past session happened to record."""
    resolved: list[SignalNeed] = []
    for need in needs:
        signal = ROLE_TO_SIGNAL[need.role]
        reason: str | None
        recorded = (
            None if recorded_signals is None or signal is None else signal in recorded_signals
        )
        if need.role is SignalRole.DATA_QUALITY:
            availability, reason, provenance = (
                Availability.NOT_APPLICABLE,
                "Timestamp and sequence quality are assessed from captured records, not a sensor",
                "canonical_record_quality",
            )
        elif signal is None or signal not in CATALOG_SIGNALS:
            availability, reason, provenance = (
                Availability.UNAVAILABLE,
                "No verified Phase 4 canonical acquisition mapping exists for this evidence need",
                "phase4_recipe_catalog",
            )
        elif source is None:
            availability, reason, provenance = (
                Availability.UNKNOWN,
                "Current source capabilities require a trusted read-only preflight",
                "source_not_preflighted",
            )
        else:
            support = source.signals.get(signal, Support.UNKNOWN)
            availability = (
                Availability.AVAILABLE
                if support is Support.SUPPORTED
                else Availability.UNAVAILABLE
                if support in {Support.UNSUPPORTED, Support.UNAVAILABLE}
                else Availability.UNKNOWN
            )
            reason = (
                None
                if availability is Availability.AVAILABLE
                else f"Source reports {support.value} for this canonical signal"
            )
            provenance = f"trusted_source_preflight:{source.adapter}"
        resolved.append(
            need.model_copy(
                update={
                    "canonical_signal": signal,
                    "availability": availability,
                    "source_support": availability,
                    "recorded_in_session": recorded,
                    "provenance": provenance,
                    "unavailable_reason": reason,
                }
            )
        )
    return tuple(resolved)


def choose_recipe(needs: tuple[SignalNeed, ...]) -> LoggingRecipe | None:
    """Choose a canonical Phase 4 recipe by bounded semantic coverage."""
    wanted = {
        need.canonical_signal
        for need in needs
        if need.canonical_signal in CATALOG_SIGNALS
        and need.availability is not Availability.NOT_APPLICABLE
    }
    if not wanted:
        return (
            next(
                (recipe for recipe in RECIPES if recipe.key == "data-quality-validation"),
                None,
            )
            if any(need.role is SignalRole.DATA_QUALITY for need in needs)
            else None
        )
    candidates = [
        recipe
        for recipe in RECIPES
        if wanted <= {requirement.signal for requirement in recipe.requirements}
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda recipe: (len(recipe.requirements), recipe.minimum_duration_seconds, recipe.key),
    )


def plan_recipe(
    needs: list[SignalNeed],
    source: DeviceCapabilities | None,
    recorded_signals: set[str] | None = None,
) -> PlannedRecipe:
    resolved = resolve_needs(needs, source, recorded_signals)
    recipe = choose_recipe(resolved)
    if recipe is None:
        return PlannedRecipe(None, None, None, resolved)
    # An unknown source can still yield a proposal, but never an approval-ready
    # claim. The actual Phase 4 preflight runs once capability data is available.
    capabilities = source or DeviceCapabilities("unverified-source", {}, 0)
    result = preflight(recipe, capabilities)
    rates = {item.signal: item for item in result.sampling_plan}
    updated: list[SignalNeed] = []
    rate_compromises: list[str] = []
    for need in resolved:
        item = rates.get(need.canonical_signal or "")
        if item and need.availability is Availability.AVAILABLE:
            # Semantic high/medium/low intent is checked against the Phase 4
            # preferred rate; the agent never supplies an arbitrary Hz value.
            fraction = {
                Resolution.HIGH: 1.0,
                Resolution.MEDIUM: 0.5,
                Resolution.LOW: 0.2,
                Resolution.EVENT_CONTEXT: 0.0,
            }[need.resolution]
            if item.estimated_hz + 1e-9 < item.target_hz * fraction:
                need = need.model_copy(update={"availability": Availability.AVAILABLE_DEGRADED})
                rate_compromises.append(item.signal)
        updated.append(need)
    missing_required = [
        need
        for need in updated
        if need.required
        and need.availability not in {Availability.AVAILABLE, Availability.NOT_APPLICABLE}
    ]
    unavailable = [
        need
        for need in updated
        if need.availability in {Availability.UNAVAILABLE, Availability.UNKNOWN}
    ]
    if source is None or result.readiness is Readiness.BLOCKED:
        feasibility = Feasibility.NOT_FEASIBLE
    elif missing_required:
        feasibility = Feasibility.PARTIALLY_FEASIBLE
    elif rate_compromises or result.readiness is Readiness.DEGRADED or unavailable:
        feasibility = Feasibility.FEASIBLE_WITH_DEGRADATION
    else:
        feasibility = Feasibility.FEASIBLE
    reference = RecipeReference(
        key=recipe.key,
        version=recipe.version,
        configuration_hash=recipe.configuration_hash,
        minimum_duration_seconds=recipe.minimum_duration_seconds,
        vehicle_scope=recipe.vehicle_scope,
        supported_modes=list(recipe.supported_modes),
        sampling_algorithm_version=result.sampling_algorithm_version,
        feasibility=feasibility,
        required_missing=[need.canonical_signal or need.role.value for need in missing_required],
        dropped_signals=[need.canonical_signal or need.role.value for need in unavailable],
        rate_compromises=rate_compromises,
        rationale=[*result.warnings, "Selected from the versioned Phase 4 recipe catalog"],
        source=capabilities.adapter,
    )
    return PlannedRecipe(recipe, result, reference, tuple(updated))
