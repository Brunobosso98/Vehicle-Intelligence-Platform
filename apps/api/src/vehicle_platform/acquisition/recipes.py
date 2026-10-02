from vehicle_platform.acquisition.domain import (
    Importance,
    LoggingRecipe,
    Priority,
    SignalRequirement,
)


def req(
    signal: str,
    importance: Importance,
    reason: str,
    minimum: float,
    preferred: float,
    missing: str = "",
) -> SignalRequirement:
    priority = (
        Priority.CRITICAL
        if importance is Importance.REQUIRED
        else (Priority.HIGH if importance is Importance.RECOMMENDED else Priority.LOW)
    )
    return SignalRequirement(
        signal, importance, reason, minimum, preferred, priority, (missing,) if missing else ()
    )


BASE = (
    req(
        "engine.rpm", Importance.REQUIRED, "anchors engine operating state", 5, 10, "pull_detection"
    ),
    req(
        "vehicle.speed",
        Importance.REQUIRED,
        "distinguishes motion states",
        2,
        5,
        "temporal_segmentation",
    ),
    req(
        "engine.throttle_position",
        Importance.REQUIRED,
        "identifies driver demand",
        5,
        10,
        "pull_detection",
    ),
)
RECIPES = (
    LoggingRecipe(
        "general-health",
        "General Health",
        "Balanced low-risk observational coverage.",
        "general_health",
        1,
        BASE
        + (
            req(
                "engine.coolant_temperature",
                Importance.RECOMMENDED,
                "thermal context",
                1,
                2,
                "coolant_analysis",
            ),
            req("electrical.battery_voltage", Importance.OPTIONAL, "electrical context", 0.5, 1),
        ),
        60,
    ),
    LoggingRecipe(
        "performance-pull",
        "Performance Pull",
        "Factual controlled acceleration acquisition.",
        "performance_pull",
        1,
        BASE
        + (
            req(
                "engine.boost_pressure",
                Importance.RECOMMENDED,
                "boost behavior",
                5,
                10,
                "boost_analysis",
            ),
            req(
                "engine.intake_air_temperature",
                Importance.RECOMMENDED,
                "charge temperature context",
                2,
                5,
                "thermal_analysis",
            ),
            req(
                "fuel.high_pressure",
                Importance.OPTIONAL,
                "fuel-pressure behavior",
                2,
                5,
                "fuel_pressure_analysis",
            ),
            req("engine.oil_temperature", Importance.OPTIONAL, "engine thermal context", 1, 2),
        ),
        15,
        notes=(
            "Use only on a dyno or lawful closed course; the platform never commands the vehicle.",
        ),
    ),
    LoggingRecipe(
        "thermal-behavior",
        "Thermal Behavior",
        "Compare factual temperature behavior across comparable windows.",
        "thermal_behavior",
        1,
        BASE
        + (
            req(
                "engine.intake_air_temperature",
                Importance.RECOMMENDED,
                "intake temperature trend",
                2,
                5,
                "thermal_analysis",
            ),
            req("engine.oil_temperature", Importance.RECOMMENDED, "oil temperature trend", 1, 2),
            req(
                "engine.coolant_temperature",
                Importance.RECOMMENDED,
                "coolant temperature trend",
                1,
                2,
            ),
            req(
                "environment.ambient_air_temperature",
                Importance.OPTIONAL,
                "ambient context",
                0.2,
                1,
            ),
        ),
        180,
    ),
    LoggingRecipe(
        "fuel-delivery",
        "Fuel Delivery",
        "Collect factual fuel-pressure and mixture evidence.",
        "fuel_delivery",
        1,
        BASE
        + (
            req(
                "fuel.high_pressure",
                Importance.RECOMMENDED,
                "rail-pressure behavior",
                5,
                10,
                "fuel_pressure_analysis",
            ),
            req("fuel.low_pressure", Importance.OPTIONAL, "feed-pressure context", 2, 5),
            req(
                "fuel.equivalence_ratio",
                Importance.OPTIONAL,
                "mixture context",
                2,
                5,
                "mixture_analysis",
            ),
        ),
        30,
    ),
    LoggingRecipe(
        "boost-behavior",
        "Boost Behavior",
        "Observe boost behavior without diagnosis.",
        "boost_behavior",
        1,
        BASE
        + (
            req(
                "engine.boost_pressure",
                Importance.REQUIRED,
                "boost observation",
                5,
                10,
                "boost_analysis",
            ),
            req(
                "engine.intake_air_temperature",
                Importance.RECOMMENDED,
                "charge temperature context",
                2,
                5,
            ),
        ),
        20,
    ),
    LoggingRecipe(
        "data-quality-validation",
        "Data Quality Validation",
        "Measure source rates, gaps, jitter, and staleness.",
        "data_quality_validation",
        1,
        BASE,
        30,
    ),
)
BY_KEY = {recipe.key: recipe for recipe in RECIPES}
BY_OBJECTIVE = {recipe.objective: recipe for recipe in RECIPES}
