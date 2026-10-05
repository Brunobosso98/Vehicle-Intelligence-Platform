import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum


class EventCategory(StrEnum):
    PERFORMANCE = "performance"
    THERMAL = "thermal"
    FUEL = "fuel"
    IGNITION = "ignition"
    COMBUSTION = "combustion"
    MIXTURE = "mixture"
    SENSOR = "sensor"
    TELEMETRY_QUALITY = "telemetry_quality"
    CONTROL_BEHAVIOR = "control_behavior"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class BaselineType(StrEnum):
    SAME_SESSION_PULLS = "same_session_pulls"
    VEHICLE_CONFIGURATION_HISTORY = "vehicle_configuration_history"
    PROFILE_THRESHOLD = "profile_threshold"
    ABSOLUTE_THRESHOLD = "absolute_threshold"
    NO_BASELINE = "no_baseline"


class DetectorState(StrEnum):
    EVENT_DETECTED = "event_detected"
    NO_EVENT = "no_event"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_APPLICABLE = "detector_not_applicable"


@dataclass(frozen=True)
class EventProfile:
    """Development heuristics; these are not factory safety or N55 calibration limits."""

    name: str = "generic-event-v1"
    algorithm_version: str = "1.1.0"
    min_duration_seconds: float = 1.0
    high_load_throttle_pct: float = 70.0
    boost_drop_relative: float = 0.15
    boost_overshoot_pa: float = 150_000.0
    iat_rise_k: float = 12.0
    repeated_pull_iat_rise_k: float = 8.0
    intake_temperature_high_k: float = 333.15
    oil_temperature_high_k: float = 403.15
    coolant_temperature_high_k: float = 393.15
    fuel_drop_relative: float = 0.15
    throttle_closure_delta_pct: float = 25.0
    dropout_seconds: float = 2.0
    telemetry_gap_seconds: float = 2.0
    stuck_seconds: float = 4.0
    consolidation_gap_seconds: float = 0.6

    def __post_init__(self) -> None:
        if self.min_duration_seconds <= 0 or not 0 < self.boost_drop_relative < 1:
            raise ValueError("event duration and relative thresholds must be bounded")
        if not 0 <= self.high_load_throttle_pct <= 100:
            raise ValueError("throttle threshold must be between 0 and 100")

    @property
    def configuration_hash(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class EventCandidate:
    event_type: str
    category: EventCategory
    started_at: datetime
    ended_at: datetime
    severity: Severity
    confidence: float
    algorithm_name: str
    algorithm_version: str
    configuration_hash: str
    baseline_type: BaselineType
    baseline_reference: dict[str, object]
    evidence: dict[str, object]
    quality_flags: tuple[str, ...] = ()
    pull_index: int | None = None


@dataclass(frozen=True)
class DetectorResult:
    detector: str
    state: DetectorState
    events: tuple[EventCandidate, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PullWindow:
    started_at: datetime
    ended_at: datetime
    frames: tuple[object, ...]
    pull_id: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
