from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

from vehicle_platform.features.domain import (
    FeatureDefinition,
    FeatureQuality,
    FeatureValue,
    MissingReason,
)


@dataclass(frozen=True)
class TelemetryFeatureSample:
    sample_id: str
    observed_at: datetime
    ingested_at: datetime
    signal: str
    value: float
    unit: str
    quality: str
    content_hash: str
    sequence_number: int | None = None

    @property
    def available_at(self) -> datetime:
        return max(self.observed_at, self.ingested_at)


@dataclass(frozen=True)
class HistoricalPull:
    row: dict[str, Any]
    samples: tuple[TelemetryFeatureSample, ...]
    effective_configuration_id: str | None
    modifications: tuple[dict[str, Any], ...] = ()

    @property
    def id(self) -> str:
        return str(self.row["id"])


@dataclass(frozen=True)
class FeatureContext:
    pull: dict[str, Any]
    session: dict[str, Any]
    vehicle: dict[str, Any]
    configuration: dict[str, Any] | None
    modifications: tuple[dict[str, Any], ...]
    raw_samples: tuple[TelemetryFeatureSample, ...]
    valid_samples: tuple[TelemetryFeatureSample, ...]
    prior_pulls: tuple[HistoricalPull, ...]
    prior_pull_count: int
    repeated_pull_index: int
    events: tuple[dict[str, Any], ...]
    observation_cutoff: datetime
    effective_configuration_id: str | None
    context_available_at: datetime
    configuration_available_at: datetime
    signal_coverage: dict[str, float]
    frame_count: int
    quality_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def pull_id(self) -> str:
        return str(self.pull["id"])

    @property
    def session_id(self) -> str:
        return str(self.pull["session_id"])

    @property
    def vehicle_id(self) -> str:
        return str(self.pull["vehicle_id"])

    @property
    def start(self) -> datetime:
        return cast(datetime, self.pull["started_at"])

    @property
    def end(self) -> datetime:
        return cast(datetime, self.pull["ended_at"])

    def for_signal(
        self, signal: str, *, valid_only: bool = True
    ) -> tuple[TelemetryFeatureSample, ...]:
        source = self.valid_samples if valid_only else self.raw_samples
        return tuple(item for item in source if item.signal == signal)

    def make_value(
        self,
        definition: FeatureDefinition,
        value: Any,
        *,
        samples: tuple[TelemetryFeatureSample, ...] = (),
        source_entities: tuple[str, ...] | None = None,
        details: dict[str, Any] | None = None,
        available_at: datetime | None = None,
        source_window_start: datetime | None = None,
        source_window_end: datetime | None = None,
        quality: FeatureQuality = FeatureQuality.VALID,
    ) -> FeatureValue:
        selected = tuple(
            sorted(samples, key=lambda item: (item.observed_at, item.signal, item.sample_id))
        )
        starts = [item.observed_at for item in selected]
        availability = max(
            (item.available_at for item in selected), default=self.context_available_at
        )
        if available_at is not None:
            availability = max(availability, available_at)
        return FeatureValue(
            value=value,
            unit=definition.unit,
            quality=quality,
            missing_reason=None,
            available_at=availability,
            source_window_start=source_window_start or (min(starts) if starts else None),
            source_window_end=source_window_end or (max(starts) if starts else None),
            source_signals=definition.required_signals + definition.optional_signals,
            source_entities=tuple(
                dict.fromkeys((self.pull_id,) if source_entities is None else source_entities)
            ),
            details=details or {},
        )

    def missing(
        self,
        definition: FeatureDefinition,
        reason: MissingReason,
        *,
        details: dict[str, Any] | None = None,
        source_entities: tuple[str, ...] | None = None,
    ) -> FeatureValue:
        return FeatureValue(
            value=None,
            unit=definition.unit,
            quality=(
                FeatureQuality.INVALID
                if reason in {MissingReason.INVALID_QUALITY, MissingReason.COMPUTATION_ERROR}
                else FeatureQuality.UNAVAILABLE
            ),
            missing_reason=reason,
            available_at=None,
            source_window_start=None,
            source_window_end=None,
            source_signals=definition.required_signals + definition.optional_signals,
            source_entities=tuple(
                dict.fromkeys((self.pull_id,) if source_entities is None else source_entities)
            ),
            details=details or {},
        )
