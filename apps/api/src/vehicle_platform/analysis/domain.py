import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum


class SegmentType(StrEnum):
    IDLE = "idle"
    WARM_UP = "warm_up"
    CRUISE = "cruise"
    ACCELERATION = "acceleration"
    PULL = "pull"
    DECELERATION = "deceleration"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DetectorProfile:
    """Heuristic defaults, not manufacturer calibration data."""

    name: str = "generic-v1"
    interval_ms: int = 200
    max_gap_seconds: float = 2.0
    smoothing_window: int = 3
    idle_max_speed: float = 0.8
    idle_rpm_min: float = 450
    idle_rpm_max: float = 1200
    idle_max_throttle: float = 15
    warm_temperature_k: float = 343.15
    acceleration_rpm_slope: float = 100
    acceleration_speed_slope: float = 0.25
    deceleration_speed_slope: float = -0.2
    pull_min_throttle: float = 70
    pull_min_duration_seconds: float = 3.0
    pull_min_rpm_delta: float = 900
    pull_min_speed_delta: float = 3.0
    pull_min_positive_slope_ratio: float = 0.75
    candidate_gap_seconds: float = 0.6

    def __post_init__(self) -> None:
        if self.interval_ms < 50 or self.max_gap_seconds <= self.interval_ms / 1000:
            raise ValueError("interval must be >=50ms and smaller than max gap")
        if not 0 <= self.pull_min_throttle <= 100:
            raise ValueError("pull throttle must be between 0 and 100")
        if self.pull_min_duration_seconds <= 0 or self.smoothing_window < 1:
            raise ValueError("duration and smoothing window must be positive")

    @property
    def configuration_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


N55_REFERENCE_PROFILE = DetectorProfile(
    name="bmw-f30-n55-heuristic-v1",
    idle_rpm_max=1100,
    pull_min_throttle=72,
    pull_min_rpm_delta=1000,
)


@dataclass(frozen=True)
class Observation:
    observed_at: datetime
    signal: str
    value: float
    sample_id: str | None = None


@dataclass(frozen=True)
class AlignedFrame:
    observed_at: datetime
    values: dict[str, float | None]
    source_sample_ids: dict[str, str] = field(default_factory=dict)
    gap_before: bool = False


@dataclass(frozen=True)
class DetectedSegment:
    segment_type: SegmentType
    started_at: datetime
    ended_at: datetime
    confidence: float
    quality_flags: tuple[str, ...] = ()
    evidence: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PullMetrics:
    duration_ms: int
    start_rpm: float | None
    end_rpm: float | None
    min_rpm: float | None
    max_rpm: float | None
    start_speed: float | None
    end_speed: float | None
    max_speed: float | None
    max_boost: float | None
    average_boost: float | None
    start_iat: float | None
    end_iat: float | None
    iat_delta: float | None
    max_oil_temperature: float | None
    max_coolant_temperature: float | None
    average_throttle: float | None
    max_throttle: float | None
    sample_count: int
    data_completeness: float
    available_signals: tuple[str, ...]


@dataclass(frozen=True)
class DetectedPull:
    started_at: datetime
    ended_at: datetime
    confidence: float
    quality_flags: tuple[str, ...]
    evidence: dict[str, object]
    metrics: PullMetrics
