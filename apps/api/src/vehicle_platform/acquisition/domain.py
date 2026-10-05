import hashlib
import json
import math
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

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.maximum_requests_per_second)
            or self.maximum_requests_per_second < 0
        ):
            raise ValueError("adapter throughput must be finite and nonnegative")


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
    sampling_algorithm_version: str = "1.1"


def plan_sampling(
    recipe: LoggingRecipe, capabilities: DeviceCapabilities
) -> tuple[SamplingPlanItem, ...]:
    supported = [
        r for r in recipe.requirements if capabilities.signals.get(r.signal) is Support.SUPPORTED
    ]
    budget = capabilities.maximum_requests_per_second
    required = [r for r in supported if r.importance is Importance.REQUIRED]
    minimum_budget = sum(r.minimum_hz for r in required)
    fraction = min(1.0, budget / minimum_budget) if minimum_budget else 1.0
    rates = {r.signal: r.minimum_hz * fraction for r in required}
    remaining = max(0.0, budget - sum(rates.values()))
    ordered = sorted(supported, key=lambda r: list(Priority).index(r.priority))
    for requirement in ordered:
        allocated = rates.get(requirement.signal, 0.0)
        extra = min(max(0.0, requirement.preferred_hz - allocated), remaining)
        rates[requirement.signal] = allocated + extra
        remaining = max(0.0, remaining - extra)
    return tuple(
        SamplingPlanItem(r.signal, r.priority, r.preferred_hz, rates[r.signal]) for r in ordered
    )


def preflight(recipe: LoggingRecipe, capabilities: DeviceCapabilities) -> PreflightResult:
    available = {k for k, state in capabilities.signals.items() if state is Support.SUPPORTED}
    required = {r.signal for r in recipe.requirements if r.importance is Importance.REQUIRED}
    recommended = {r.signal for r in recipe.requirements if r.importance is Importance.RECOMMENDED}
    optional = {r.signal for r in recipe.requirements if r.importance is Importance.OPTIONAL}
    missing = required - available
    plan = plan_sampling(recipe, capabilities)
    rates = {p.signal: p.estimated_hz for p in plan}
    unavailable = tuple(
        sorted(
            {
                effect
                for r in recipe.requirements
                if r.signal not in available or rates.get(r.signal, 0) < r.minimum_hz
                for effect in r.missing_effect
            }
        )
    )
    warnings = []
    minimums = {
        r.signal: r.minimum_hz for r in recipe.requirements if r.importance is Importance.REQUIRED
    }
    required_rate_missing = any(
        p.estimated_hz < minimums[p.signal] for p in plan if p.signal in minimums
    )
    if required_rate_missing:
        warnings.append("Required signal sampling rate cannot be met by adapter throughput")
    if unavailable:
        warnings.append(
            "Some analyses are unavailable because signals are absent or sampled below minimum rate"
        )
    if sum(item.target_hz for item in plan) > capabilities.maximum_requests_per_second:
        warnings.append("Adapter throughput reduced lower-priority sampling")
    readiness = (
        Readiness.BLOCKED
        if missing or required_rate_missing
        else (Readiness.DEGRADED if unavailable else Readiness.READY)
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
                ({"temporal_segmentation", "data_quality"} - set(unavailable))
                | (
                    {"boost_analysis"}
                    if "engine.boost_pressure" in available and "boost_analysis" not in unavailable
                    else set()
                )
            )
        ),
        unavailable,
        tuple(warnings),
    )
