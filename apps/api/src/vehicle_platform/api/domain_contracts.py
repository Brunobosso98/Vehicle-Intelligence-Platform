import math
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from vehicle_platform.telemetry.domain import MAX_SEQUENCE
from vehicle_platform.telemetry.mapping import CSVColumnMapping


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

    @model_validator(mode="after")
    def chronological(self) -> "ModificationCreate":
        if self.installed_at.tzinfo is None or (self.removed_at and self.removed_at.tzinfo is None):
            raise ValueError("modification timestamps require timezone offsets")
        if self.removed_at and self.removed_at <= self.installed_at:
            raise ValueError("removed_at must follow installed_at")
        return self


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

    @model_validator(mode="after")
    def chronological(self) -> "SessionCreate":
        if self.started_at.tzinfo is None or (self.ended_at and self.ended_at.tzinfo is None):
            raise ValueError("session timestamps require timezone offsets")
        if self.ended_at and self.ended_at < self.started_at:
            raise ValueError("ended_at must not precede started_at")
        return self


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


class CSVPreviewPoint(BaseModel):
    observed_at: datetime
    raw_signal: str
    signal: str
    value: float
    unit: str
    quality: str


class CSVImportPreview(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    columns: list[str]
    unmapped_columns: list[str]
    requires_mapping: bool
    mapping: CSVColumnMapping | None = None
    mapping_hash: str | None = None
    preview_points: list[CSVPreviewPoint] = Field(default_factory=list, max_length=25)
    preview_truncated: bool = False
    validation_scope: str = "preview only; full records and context validated during import"
    warnings: list[str] = Field(default_factory=list, max_length=25)


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


class EventSummary(BaseModel):
    event_count: int
    by_category: dict[str, int]
    highest_severity: Literal["info", "low", "moderate", "high"] | None


class AnalyticsRequest(BaseModel):
    speed_intervals_kmh: list[tuple[float, float]] = Field(
        default_factory=lambda: [(60.0, 100.0), (80.0, 120.0), (100.0, 150.0)],
        min_length=1,
        max_length=5,
    )

    @model_validator(mode="after")
    def valid_intervals(self) -> "AnalyticsRequest":
        if any(
            not math.isfinite(a) or not math.isfinite(b) or not 0 <= a < b <= 300
            for a, b in self.speed_intervals_kmh
        ):
            raise ValueError("speed intervals must be finite increasing pairs within 0..300 km/h")
        return self

    rpm_bin_size: int = Field(default=250, ge=100, le=1000)
    minimum_bin_samples: int = Field(default=3, ge=2, le=100)
    maximum_gap_seconds: float = Field(default=1.0, gt=0, le=5)
    pull_ids: list[UUID] = Field(default_factory=list, min_length=0, max_length=20)
    recompute: bool = False


class AnalyticsResultResponse(BaseModel):
    id: UUID
    analytics_type: str
    algorithm_name: str
    algorithm_version: str
    configuration_hash: str
    source_fingerprint: str
    vehicle_id: UUID
    configuration_id: UUID | None
    status: Literal["completed", "limited", "insufficient", "failed"]
    warnings: list[str]
    result: dict[str, Any]
    generated_at: datetime
    reused: bool = False


class RecipeSignal(BaseModel):
    signal: str
    importance: Literal["required", "recommended", "optional"]
    reason: str
    minimum_hz: float
    preferred_hz: float
    priority: Literal["critical_for_recipe", "high", "normal", "low"]
    missing_effect: list[str]


class LoggingRecipeResponse(BaseModel):
    key: str
    name: str
    description: str
    objective: str
    version: int
    configuration_hash: str
    vehicle_scope: str
    minimum_duration_seconds: int
    supported_modes: list[str]
    notes: list[str]
    requirements: list[RecipeSignal]


class ObjectiveResponse(BaseModel):
    key: str
    recipe_key: str


class PreflightRequest(BaseModel):
    adapter: str = Field(min_length=1, max_length=80)
    signals: dict[
        str,
        Literal[
            "supported",
            "unsupported",
            "unavailable",
            "unknown",
            "adapter_does_not_support_discovery",
        ],
    ] = Field(max_length=100)
    maximum_requests_per_second: float = Field(gt=0, le=1000)
    discovery_supported: bool = True


class SamplingPlanResponse(BaseModel):
    signal: str
    priority: str
    target_hz: float = Field(ge=0, le=1000, allow_inf_nan=False)
    estimated_hz: float = Field(ge=0, le=1000, allow_inf_nan=False)


class PreflightResponse(BaseModel):
    sampling_algorithm_version: Literal["1.1"] = "1.1"
    readiness: Literal["ready", "degraded", "blocked"]
    required_available: list[str]
    required_missing: list[str]
    recommended_available: list[str]
    optional_available: list[str]
    sampling_plan: list[SamplingPlanResponse]
    expected_capabilities: list[str]
    unavailable_capabilities: list[str]
    warnings: list[str]


class AcquisitionCreate(BaseModel):
    vehicle_id: UUID
    configuration_id: UUID | None = None
    recipe_key: str = Field(min_length=1, max_length=80)
    adapter: Literal["synthetic", "replay", "obd"]
    source_id: str = Field(min_length=1, max_length=80)


class AcquisitionHeartbeat(BaseModel):
    adapter_state: Literal["connected", "disconnected"]
    collection_started_at: datetime
    last_sample_received_at: datetime | None = None
    queue_observations: int = Field(ge=0, le=100000)
    spool_bytes: int = Field(ge=0, le=1073741824)
    dropped_observations: int = Field(ge=0)
    spool_capacity_bytes: int | None = Field(default=None, ge=1, le=1073741824)
    spool_capacity_state: (
        Literal["normal", "warning", "near_capacity", "capacity_reached"] | None
    ) = None
    capability_snapshot: PreflightRequest | None = None
    sampling_plan: list[SamplingPlanResponse] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def aware_times(self) -> "AcquisitionHeartbeat":
        for stamp in (self.collection_started_at, self.last_sample_received_at):
            if stamp is not None and stamp.tzinfo is None:
                raise ValueError("collector timestamps require timezone offsets")
        if (
            self.last_sample_received_at
            and self.last_sample_received_at < self.collection_started_at
        ):
            raise ValueError("sample receipt cannot precede collection start")
        return self


class AcquisitionCreated(BaseModel):
    id: UUID
    driving_session_id: UUID
    state: str
    ingestion_token: str
    token_expires_at: datetime


class StreamObservation(BaseModel):
    message_id: UUID
    observed_at: datetime
    sequence: int | None = Field(default=None, ge=0, le=MAX_SEQUENCE)
    signal: str = Field(min_length=1, max_length=100)
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=24)
    source_record_id: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def event_time(self) -> "StreamObservation":
        if self.observed_at.tzinfo is None:
            raise ValueError("observation timestamp requires timezone offset")
        return self


class AcquisitionBatch(BaseModel):
    schema_version: Literal["1.0"]
    batch_id: UUID
    observations: list[StreamObservation] = Field(min_length=1, max_length=500)


class AcquisitionBatchAccepted(BaseModel):
    batch_id: UUID
    accepted: int
    topic: str = "telemetry.raw.v1"


class AcquisitionStatusResponse(BaseModel):
    id: UUID
    driving_session_id: UUID
    recipe_key: str
    recipe_version: int
    state: str
    adapter: str
    started_at: datetime
    ended_at: datetime | None
    quality: dict[str, Any]


class LiveSignalQuality(BaseModel):
    signal: str
    target_hz: float
    actual_hz: float
    jitter_ms: float | None = None
    stale_ratio: float
    missing_ratio: float


class DatasetCapabilityResponse(BaseModel):
    key: str
    supported: bool
    evidence: list[str]
    unavailable_reason: str | None = None


class DatasetSignalGap(BaseModel):
    count: int = Field(ge=0)
    maximum_seconds: float = Field(ge=0, allow_inf_nan=False)


class DatasetCapabilityReport(BaseModel):
    assessment_version: Literal["1.1.0"]
    recipe_configuration_hash: str = Field(min_length=64, max_length=64)
    duration_seconds: float = Field(ge=0, allow_inf_nan=False)
    observation_count: int = Field(ge=0)
    available_signals: list[str]
    signal_quality: list[LiveSignalQuality]
    gaps_by_signal: dict[str, DatasetSignalGap]
    capabilities: list[DatasetCapabilityResponse]
    recipe_adherence: bool


class AcquisitionFinalized(BaseModel):
    id: UUID
    state: Literal["completed"]
    phase2: AnalysisResult
    phase3: EventAnalysisResult
    capability_report: DatasetCapabilityReport
    reconciliation: dict[str, int]


class ProvisionalFindingResponse(BaseModel):
    id: UUID
    finding_type: str
    category: str
    started_at: datetime
    ended_at: datetime | None
    evidence: dict[str, Any]
    reconciliation_status: str
    canonical_reference: UUID | None = None


class LiveTelemetryPoint(BaseModel):
    signal: str
    value: float = Field(allow_inf_nan=False)
    unit: str
    observed_at: AwareDatetime


class CollectorHealthResponse(BaseModel):
    state: Literal["not_reported", "silent", "disconnected", "stalled", "connected"]
    heartbeat_age_seconds: float | None
    sample_receipt_age_seconds: float | None = None


class CollectorReportedState(AcquisitionHeartbeat):
    received_at: AwareDatetime


class AcquisitionPipelineMeasurement(BaseModel):
    measured_at: AwareDatetime
    publisher_to_persistence_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    broker_consumer_lag: int | None = Field(default=None, ge=0)
    persistence_state: Literal["observations_committed"]


class AcquisitionLiveQuality(BaseModel):
    model_config = ConfigDict(extra="allow")
    signals: list[LiveSignalQuality] = Field(default_factory=list)
    collector: CollectorReportedState | None = None
    collector_health: CollectorHealthResponse
    pipeline: AcquisitionPipelineMeasurement | None = None


class AcquisitionLiveSnapshot(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    state: str
    quality: AcquisitionLiveQuality
    provisional: Literal[True] = True
    window_seconds: Literal[60] = 60
    points: list[LiveTelemetryPoint] = Field(max_length=2000)
    findings: list[ProvisionalFindingResponse] = Field(max_length=20)
