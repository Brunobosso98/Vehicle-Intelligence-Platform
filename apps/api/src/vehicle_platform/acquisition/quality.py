import statistics
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SignalQuality:
    signal: str
    target_hz: float
    actual_hz: float
    jitter_ms: float
    stale_ratio: float
    missing_ratio: float


def measure_signal_quality(
    signal: str, observed: tuple[datetime, ...], target_hz: float
) -> SignalQuality:
    if len(observed) < 2:
        return SignalQuality(signal, target_hz, 0, 0, 1, 1)
    ordered = sorted(observed)
    deltas = [
        (right - left).total_seconds() for left, right in zip(ordered, ordered[1:], strict=False)
    ]
    duration = (ordered[-1] - ordered[0]).total_seconds()
    actual = (len(ordered) - 1) / duration if duration > 0 else 0
    expected = 1 / target_hz if target_hz else 0
    jitter = statistics.fmean(abs(item - expected) for item in deltas) * 1000
    stale = sum(item > max(expected * 2, 1) for item in deltas) / len(deltas)
    expected_count = duration * target_hz + 1
    missing = max(0.0, min(1.0, 1 - len(observed) / expected_count)) if expected_count else 0
    return SignalQuality(signal, target_hz, actual, jitter, stale, missing)


@dataclass(frozen=True)
class DatasetCapability:
    key: str
    supported: bool
    evidence: tuple[str, ...]
    unavailable_reason: str | None = None


def assess_dataset(
    qualities: tuple[SignalQuality, ...], duration_seconds: float
) -> tuple[DatasetCapability, ...]:
    usable = {item.signal for item in qualities if item.actual_hz > 0 and item.missing_ratio < 0.5}
    definitions = {
        "pull_detection": {"engine.rpm", "vehicle.speed", "engine.throttle_position"},
        "boost_analysis": {"engine.rpm", "engine.throttle_position", "engine.boost_pressure"},
        "thermal_analysis": {"engine.rpm", "engine.intake_air_temperature"},
        "fuel_pressure_analysis": {"engine.rpm", "fuel.high_pressure"},
    }
    result = []
    for key, required in definitions.items():
        missing = required - usable
        supported = not missing and duration_seconds > 0
        result.append(
            DatasetCapability(
                key,
                supported,
                tuple(sorted(required & usable)),
                None if supported else "missing usable signals: " + ", ".join(sorted(missing)),
            )
        )
    return tuple(result)
