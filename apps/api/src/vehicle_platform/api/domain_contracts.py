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
