import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class Importance(StrEnum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class Priority(StrEnum):
    CRITICAL = "critical_for_recipe"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class Support(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    DISCOVERY_UNAVAILABLE = "adapter_does_not_support_discovery"


class Readiness(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class SignalRequirement:
    signal: str
    importance: Importance
    reason: str
    minimum_hz: float
    preferred_hz: float
    priority: Priority
    missing_effect: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoggingRecipe:
    key: str
    name: str
    description: str
    objective: str
    version: int
    requirements: tuple[SignalRequirement, ...]
    minimum_duration_seconds: int
    supported_modes: tuple[str, ...] = ("synthetic", "replay", "obd")
    vehicle_scope: str = "generic-obd-ii"
    notes: tuple[str, ...] = ()

    @property
    def configuration_hash(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class DeviceCapabilities:
    adapter: str
    signals: dict[str, Support]
    maximum_requests_per_second: float
    discovery_supported: bool = True


@dataclass(frozen=True)
class SamplingPlanItem:
    signal: str
    priority: Priority
    target_hz: float
    estimated_hz: float


@dataclass(frozen=True)
class PreflightResult:
    readiness: Readiness
    required_available: tuple[str, ...]
    required_missing: tuple[str, ...]
    recommended_available: tuple[str, ...]
    optional_available: tuple[str, ...]
    sampling_plan: tuple[SamplingPlanItem, ...]
    expected_capabilities: tuple[str, ...]
    unavailable_capabilities: tuple[str, ...]
    warnings: tuple[str, ...]


def plan_sampling(
    recipe: LoggingRecipe, capabilities: DeviceCapabilities
) -> tuple[SamplingPlanItem, ...]:
    supported = [
        r for r in recipe.requirements if capabilities.signals.get(r.signal) is Support.SUPPORTED
    ]
    desired = sum(r.preferred_hz for r in supported)
    budget = max(capabilities.maximum_requests_per_second, 0.0)
    remaining = budget
    result: list[SamplingPlanItem] = []
    for requirement in sorted(supported, key=lambda r: list(Priority).index(r.priority)):
        fair = (
            requirement.preferred_hz
            if desired <= budget
            else min(requirement.preferred_hz, remaining)
        )
        if requirement.importance is Importance.REQUIRED:
            fair = min(requirement.preferred_hz, max(requirement.minimum_hz, fair))
        estimated = max(0.0, min(fair, remaining))
        remaining = max(0.0, remaining - estimated)
        result.append(SamplingPlanItem(requirement.signal, requirement.priority, fair, estimated))
    return tuple(result)


def preflight(recipe: LoggingRecipe, capabilities: DeviceCapabilities) -> PreflightResult:
    available = {k for k, state in capabilities.signals.items() if state is Support.SUPPORTED}
    required = {r.signal for r in recipe.requirements if r.importance is Importance.REQUIRED}
    recommended = {r.signal for r in recipe.requirements if r.importance is Importance.RECOMMENDED}
    optional = {r.signal for r in recipe.requirements if r.importance is Importance.OPTIONAL}
    missing = required - available
    unavailable = tuple(
        sorted(
            {
                effect
                for r in recipe.requirements
                if r.signal not in available
                for effect in r.missing_effect
            }
        )
    )
    plan = plan_sampling(recipe, capabilities)
    warnings = []
    if unavailable:
        warnings.append("Some analyses are unavailable because signals are absent")
    if sum(item.target_hz for item in plan) > capabilities.maximum_requests_per_second:
        warnings.append("Adapter throughput reduced lower-priority sampling")
    readiness = (
        Readiness.BLOCKED if missing else (Readiness.DEGRADED if unavailable else Readiness.READY)
    )
    return PreflightResult(
        readiness,
        tuple(sorted(required & available)),
        tuple(sorted(missing)),
        tuple(sorted(recommended & available)),
        tuple(sorted(optional & available)),
        plan,
        tuple(
            sorted(
                {"temporal_segmentation", "data_quality"}
                | ({"boost_analysis"} if "engine.boost_pressure" in available else set())
            )
        ),
        unavailable,
        tuple(warnings),
    )
