import hashlib
import math
import random
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol


class DataQuality(StrEnum):
    VALID = "valid"
    MISSING = "missing"
    MALFORMED = "malformed"
    UNSUPPORTED = "unsupported"
    OUT_OF_RANGE = "out_of_range"
    DUPLICATE = "duplicate"
    SOURCE_ERROR = "source_error"


@dataclass(frozen=True)
class SignalDefinition:
    key: str
    name: str
    category: str
    unit: str
    minimum: float
    maximum: float
    aliases: tuple[str, ...]


SIGNALS = (
    SignalDefinition("engine.rpm", "Engine speed", "engine", "rpm", 0, 9000, ("rpm", "010c")),
    SignalDefinition("vehicle.speed", "Vehicle speed", "vehicle", "m/s", 0, 120, ("speed", "010d")),
    SignalDefinition(
        "engine.boost_pressure", "Boost pressure", "engine", "Pa", -120000, 300000, ("boost",)
    ),
    SignalDefinition(
        "engine.intake_air_temperature",
        "Intake air temperature",
        "thermal",
        "K",
        180,
        430,
        ("iat", "010f"),
    ),
    SignalDefinition(
        "engine.oil_temperature", "Oil temperature", "thermal", "K", 180, 450, ("oil_temp",)
    ),
    SignalDefinition(
        "engine.coolant_temperature",
        "Coolant temperature",
        "thermal",
        "K",
        180,
        430,
        ("coolant_temp", "0105"),
    ),
    SignalDefinition(
        "engine.throttle_position", "Throttle position", "engine", "%", 0, 100, ("throttle", "0111")
    ),
    SignalDefinition(
        "fuel.high_pressure", "High fuel pressure", "fuel", "Pa", 0, 30_000_000, ("hpfp",)
    ),
    SignalDefinition(
        "electrical.battery_voltage",
        "Battery voltage",
        "electrical",
        "V",
        0,
        24,
        ("battery_voltage",),
    ),
    SignalDefinition(
        "environment.ambient_air_temperature",
        "Ambient air temperature",
        "thermal",
        "K",
        180,
        340,
        ("ambient_temp", "0146"),
    ),
    SignalDefinition(
        "fuel.equivalence_ratio",
        "Commanded equivalence ratio",
        "fuel",
        "ratio",
        0.5,
        2.0,
        ("lambda", "0144"),
    ),
    SignalDefinition(
        "fuel.low_pressure", "Low fuel pressure", "fuel", "Pa", 0, 2_000_000, ("lpfp",)
    ),
    SignalDefinition(
        "engine.accelerator_position",
        "Accelerator pedal position",
        "engine",
        "%",
        0,
        100,
        ("pedal", "0149"),
    ),
    SignalDefinition(
        "engine.ignition_timing",
        "Ignition timing advance",
        "engine",
        "deg",
        -90,
        90,
        ("timing", "010e"),
    ),
)
SIGNAL_BY_KEY = {signal.key: signal for signal in SIGNALS}
SIGNAL_BY_ALIAS = {
    alias.lower(): signal for signal in SIGNALS for alias in (signal.key, *signal.aliases)
}


class NormalizationError(ValueError):
    pass


def normalize_value(value: float, unit: str, signal: SignalDefinition) -> tuple[float, DataQuality]:
    normalized_unit = unit.strip().lower()
    target = signal.unit
    conversions = {
        ("km/h", "m/s"): lambda x: x / 3.6,
        ("mph", "m/s"): lambda x: x * 0.44704,
        ("°c", "K"): lambda x: x + 273.15,
        ("c", "K"): lambda x: x + 273.15,
        ("kpa", "Pa"): lambda x: x * 1000,
        ("bar", "Pa"): lambda x: x * 100000,
        ("psi", "Pa"): lambda x: x * 6894.757293168,
    }
    if normalized_unit == target.lower():
        result = value
    elif (normalized_unit, target) in conversions:
        result = conversions[(normalized_unit, target)](value)
    else:
        raise NormalizationError(f"unit {unit!r} cannot represent {signal.key}")
    quality = (
        DataQuality.VALID
        if signal.minimum <= result <= signal.maximum
        else DataQuality.OUT_OF_RANGE
    )
    return result, quality


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NormalizationError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise NormalizationError("timestamp must include a UTC offset")
    return parsed.astimezone(UTC)


def sample_id(
    session_id: str,
    source: str,
    record_id: str,
    observed_at: datetime,
    signal: str,
    sequence: int | None,
) -> str:
    canonical = "\x1f".join(
        (
            session_id,
            source,
            record_id,
            observed_at.astimezone(UTC).isoformat(),
            signal,
            "" if sequence is None else str(sequence),
        )
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class RawTelemetryRecord:
    observed_at: datetime
    signal: str
    value: float
    unit: str
    source_record_id: str
    sequence: int | None = None


class TelemetrySource(Protocol):
    def read(self) -> AsyncIterator[RawTelemetryRecord]: ...


class LiveOBDSource(Protocol):
    """Adapter boundary only: Phase 1 intentionally provides no hardware implementation."""

    def read(self) -> AsyncIterator[RawTelemetryRecord]: ...


class SyntheticTelemetrySource:
    def __init__(self, start: datetime, samples: int = 120, seed: int = 55) -> None:
        if start.tzinfo is None:
            raise NormalizationError("synthetic start must be timezone-aware")
        self.start, self.samples, self.seed = start.astimezone(UTC), samples, seed

    async def read(self) -> AsyncIterator[RawTelemetryRecord]:
        rng = random.Random(self.seed)
        for index in range(self.samples):
            t = index / max(self.samples - 1, 1)
            throttle = 8 + 45 * max(0, math.sin(index / 13))
            speed = min(27, index * 0.32) if t < 0.45 else 22 + 2 * math.sin(index / 18)
            rpm = 750 + speed * 82 + throttle * 15 + rng.uniform(-15, 15)
            values = {
                "engine.rpm": (rpm, "rpm"),
                "vehicle.speed": (speed, "m/s"),
                "engine.boost_pressure": (max(-45000, (throttle - 25) * 3500), "Pa"),
                "engine.throttle_position": (throttle, "%"),
                "engine.intake_air_temperature": (294 + 12 * t, "K"),
                "engine.oil_temperature": (294 + 75 * t, "K"),
                "engine.coolant_temperature": (295 + 65 * t, "K"),
            }
            at = self.start + timedelta(seconds=index)
            for offset, (key, (value, unit)) in enumerate(values.items()):
                yield RawTelemetryRecord(
                    at, key, value, unit, f"{index}:{key}", index * len(values) + offset
                )
