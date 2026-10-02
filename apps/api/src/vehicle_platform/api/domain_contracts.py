from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class VehicleCreate(BaseModel):
    vin: str | None = Field(default=None, min_length=11, max_length=17)
    manufacturer: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    generation: str | None = Field(default=None, max_length=40)
    model_year: int | None = Field(default=None, ge=1886, le=2200)
    engine_code: str | None = Field(default=None, max_length=40)
    transmission: str | None = Field(default=None, max_length=80)
    nickname: str | None = Field(default=None, max_length=80)


class VehicleUpdate(BaseModel):
    nickname: str | None = Field(default=None, max_length=80)
    transmission: str | None = Field(default=None, max_length=80)


class Vehicle(VehicleCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ConfigurationCreate(BaseModel):
    effective_at: datetime
    ended_at: datetime | None = None
    description: str = Field(min_length=1, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def chronological(self) -> "ConfigurationCreate":
        if self.effective_at.tzinfo is None or (self.ended_at and self.ended_at.tzinfo is None):
            raise ValueError("configuration timestamps require timezone offsets")
        if self.ended_at and self.ended_at <= self.effective_at:
            raise ValueError("ended_at must follow effective_at")
        return self


class VehicleConfiguration(ConfigurationCreate):
    id: UUID
    vehicle_id: UUID
    created_at: datetime


class ModificationCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    manufacturer: str | None = Field(default=None, max_length=80)
    product: str | None = Field(default=None, max_length=120)
    installed_at: datetime
    removed_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)
    configuration_id: UUID | None = None


class Modification(ModificationCreate):
    id: UUID
    vehicle_id: UUID
    created_at: datetime


class SessionCreate(BaseModel):
    vehicle_id: UUID
    configuration_id: UUID | None = None
    source_type: Literal["csv", "synthetic", "obd"]
    source_reference: str | None = Field(default=None, max_length=255)
    started_at: datetime
    ended_at: datetime | None = None
    source_timezone: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DrivingSession(SessionCreate):
    id: UUID
    sample_count: int
    status: Literal["pending", "ingesting", "completed", "failed"]
    created_at: datetime
    updated_at: datetime


class ImportResult(BaseModel):
    session_id: UUID
    rows_read: int
    accepted: int
    rejected: int
    duplicates: int
    conflicts: int
    unknown_signals: int
    invalid_units: int
    invalid_timestamps: int
    start_observed_at: datetime | None
    end_observed_at: datetime | None


class TelemetryPoint(BaseModel):
    sample_id: str
    observed_at: datetime
    signal: str
    value: float
    unit: str
    quality: str
    sequence: int | None


class TelemetryWindow(BaseModel):
    session_id: UUID
    points: list[TelemetryPoint]
    returned: int
    truncated: bool
    start: datetime | None
    end: datetime | None


class Signal(BaseModel):
    key: str
    name: str
    category: str
    unit: str
    minimum: float
    maximum: float
    aliases: list[str]


SegmentKind = Literal[
    "idle", "warm_up", "cruise", "acceleration", "pull", "deceleration", "unknown"
]


class AnalysisRequest(BaseModel):
    profile: Literal["generic-v1", "bmw-f30-n55-heuristic-v1"] = "generic-v1"
    replace: bool = False


class SessionSegment(BaseModel):
    id: UUID
    session_id: UUID
    segment_type: SegmentKind
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    confidence: float
    detector_name: str
    algorithm_version: str
    configuration_hash: str
    quality_flags: list[str]
    metadata: dict[str, Any]
    created_at: datetime


class Pull(BaseModel):
    id: UUID
    session_id: UUID
    segment_id: UUID | None
    vehicle_id: UUID
    configuration_id: UUID | None
    started_at: datetime
    ended_at: datetime
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
    confidence: float
    detector_name: str
    algorithm_version: str
    configuration_hash: str
    quality_flags: list[str]
    metadata: dict[str, Any]
    created_at: datetime


class AnalysisResult(BaseModel):
    session_id: UUID
    profile: str
    algorithm_version: str
    configuration_hash: str
    segment_count: int
    pull_count: int
    reused: bool


class EventAnalysisRequest(BaseModel):
    replace: bool = False


class EventAnalysisResult(BaseModel):
    session_id: UUID
    analysis_run_id: UUID
    profile: str
    configuration_hash: str
    event_count: int
    reused: bool


class DetectedEvent(BaseModel):
    id: UUID
    vehicle_id: UUID
    session_id: UUID
    segment_id: UUID | None
    pull_id: UUID | None
    analysis_run_id: UUID
    event_type: str
    category: Literal[
        "performance",
        "thermal",
        "fuel",
        "ignition",
        "combustion",
        "mixture",
        "sensor",
        "telemetry_quality",
        "control_behavior",
    ]
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    severity: Literal["info", "low", "moderate", "high"]
    confidence: float = Field(ge=0, le=1)
    algorithm_name: str
    algorithm_version: str
    configuration_hash: str
    baseline_type: Literal[
        "same_session_pulls",
        "vehicle_configuration_history",
        "profile_threshold",
        "absolute_threshold",
        "no_baseline",
    ]
    baseline_reference: dict[str, Any]
    evidence: dict[str, Any]
    quality_flags: list[str]
    created_at: datetime
