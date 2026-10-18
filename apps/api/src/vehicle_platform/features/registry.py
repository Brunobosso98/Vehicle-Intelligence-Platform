import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from vehicle_platform.analytics.domain import (
    AnalyticsConfig,
    PullInput,
    Sample,
    acceleration_interval,
)
from vehicle_platform.features.context import FeatureContext, TelemetryFeatureSample
from vehicle_platform.features.domain import (
    EntityScope,
    FeatureCategory,
    FeatureDefinition,
    FeatureDType,
    FeatureValue,
    MissingReason,
    TemporalAvailability,
)
from vehicle_platform.telemetry.domain import SIGNAL_BY_KEY

FeatureCalculator = Callable[[FeatureContext, FeatureDefinition], FeatureValue]


@dataclass(frozen=True)
class FeatureRegistry:
    definitions: tuple[FeatureDefinition, ...]
    calculators: dict[str, FeatureCalculator]

    def __post_init__(self) -> None:
        keys = [definition.key for definition in self.definitions]
        if len(keys) != len(set(keys)):
            raise ValueError("feature registry contains duplicate keys")
        if set(keys) != set(self.calculators):
            raise ValueError("each registered definition must have exactly one trusted calculator")
        self.validate_dependencies()

    def register(
        self, definition: FeatureDefinition, calculator: FeatureCalculator
    ) -> "FeatureRegistry":
        if definition.key in {item.key for item in self.definitions}:
            raise ValueError("feature key is already registered")
        return FeatureRegistry(
            self.definitions + (definition,), self.calculators | {definition.key: calculator}
        )

    def list(self, *, active_only: bool = True) -> tuple[FeatureDefinition, ...]:
        return tuple(item for item in self.definitions if item.active or not active_only)

    def resolve(self, key: str) -> FeatureDefinition:
        for definition in self.definitions:
            if definition.key == key and definition.active:
                return definition
        raise KeyError(f"unknown active feature: {key}")

    def validate_dependencies(self) -> None:
        for definition in self.definitions:
            missing = set(definition.required_signals + definition.optional_signals) - set(
                SIGNAL_BY_KEY
            )
            if missing:
                raise ValueError(f"{definition.key} references unknown telemetry signals")
            if (
                definition.dtype in {FeatureDType.FLOAT, FeatureDType.INTEGER}
                and not definition.unit
            ):
                raise ValueError(f"{definition.key} has no unit")

    def compute(
        self, context: FeatureContext, selected: Iterable[str] | None = None
    ) -> dict[str, FeatureValue]:
        definitions = (
            tuple(self.resolve(key) for key in selected) if selected is not None else self.list()
        )
        values: dict[str, FeatureValue] = {}
        for definition in definitions:
            try:
                value = self.calculators[definition.key](context, definition)
                values[definition.key] = validate_value(definition, value)
            except (ArithmeticError, TypeError, ValueError, OverflowError):
                values[definition.key] = context.missing(
                    definition, MissingReason.COMPUTATION_ERROR
                )
        return values


def validate_value(definition: FeatureDefinition, value: FeatureValue) -> FeatureValue:
    if not isinstance(value, FeatureValue):
        raise ValueError("calculator must return a FeatureValue")
    raw = value.value
    if raw is None:
        if not definition.nullable:
            raise ValueError("non-nullable feature is missing")
        return value
    if definition.dtype is FeatureDType.FLOAT:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
            raise ValueError("float feature must be finite")
    elif definition.dtype is FeatureDType.INTEGER:
        if type(raw) is not int:
            raise ValueError("integer feature must be an integer")
    elif definition.dtype is FeatureDType.BOOLEAN:
        if type(raw) is not bool:
            raise ValueError("boolean feature must be boolean")
    elif definition.dtype is FeatureDType.CATEGORICAL and not isinstance(raw, str):
        raise ValueError("categorical feature must be a string")
    elif definition.dtype is FeatureDType.CATEGORICAL_LIST and not isinstance(raw, list):
        raise ValueError("feature value has the wrong type")
    if value.unit != definition.unit:
        raise ValueError("feature unit differs from its definition")
    if definition.bounds and isinstance(raw, (int, float)):
        lower, upper = definition.bounds
        if (lower is not None and raw < lower) or (upper is not None and raw > upper):
            raise ValueError("feature value is outside deterministic bounds")
    return value


def _valid_rows(context: FeatureContext, signal: str) -> tuple[TelemetryFeatureSample, ...]:
    return context.for_signal(signal)


def _signal_value(
    context: FeatureContext,
    definition: FeatureDefinition,
    signal: str,
    statistic: str,
) -> FeatureValue:
    rows = _valid_rows(context, signal)
    if not rows:
        return context.missing(
            definition, MissingReason.UNAVAILABLE_SIGNAL, details={"signal": signal}
        )
    coverage = context.signal_coverage.get(signal, 0.0)
    completeness = float(context.pull.get("data_completeness") or 0.0)
    if coverage < definition.minimum_quality or completeness < definition.minimum_quality:
        return context.missing(
            definition,
            MissingReason.INSUFFICIENT_COVERAGE,
            details={
                "signal": signal,
                "signal_coverage": coverage,
                "pull_completeness": completeness,
                "minimum_quality": definition.minimum_quality,
            },
        )
    numbers = [sample.value for sample in rows]
    first, last = rows[0], rows[-1]
    sources: tuple[TelemetryFeatureSample, ...]
    if statistic == "start":
        result, sources = first.value, (first,)
    elif statistic == "end":
        result, sources = last.value, (last,)
    elif statistic == "min":
        selected = min(
            rows, key=lambda sample: (sample.value, sample.observed_at, sample.sample_id)
        )
        result, sources = selected.value, tuple(rows)
    elif statistic == "max":
        selected = max(rows, key=lambda sample: (sample.value, -sample.observed_at.timestamp()))
        result, sources = selected.value, tuple(rows)
    elif statistic == "mean":
        result, sources = math.fsum(numbers) / len(numbers), tuple(rows)
    elif statistic == "delta":
        result, sources = last.value - first.value, (first, last)
    elif statistic == "slope":
        seconds = (last.observed_at - first.observed_at).total_seconds()
        if seconds <= 0 or len(rows) < 2:
            return context.missing(
                definition, MissingReason.INSUFFICIENT_COVERAGE, details={"signal": signal}
            )
        result, sources = (last.value - first.value) / seconds, (first, last)
    elif statistic == "stddev":
        if len(numbers) < 2:
            return context.missing(
                definition, MissingReason.INSUFFICIENT_COVERAGE, details={"signal": signal}
            )
        mean = math.fsum(numbers) / len(numbers)
        result, sources = (
            math.sqrt(math.fsum((item - mean) ** 2 for item in numbers) / len(numbers)),
            tuple(rows),
        )
    else:
        raise ValueError("unknown telemetry statistic")
    return context.make_value(
        definition,
        float(result),
        samples=sources,
        details={"signal_coverage": coverage, "sample_count": len(rows), "statistic": statistic},
    )


def _configuration_value(
    context: FeatureContext, definition: FeatureDefinition, key: str
) -> FeatureValue:
    configuration = context.configuration
    if configuration is None:
        return context.missing(definition, MissingReason.NOT_APPLICABLE)
    metadata = configuration.get("metadata") or {}
    value: Any
    if key == "configuration_label":
        value = configuration.get("description")
    elif key == "configuration_stage":
        value = metadata.get("stage")
    elif key == "tune_version":
        value = metadata.get("tune_version") or metadata.get("map_version") or "UNKNOWN"
    elif key == "fuel_type":
        value = metadata.get("fuel_type")
    elif key == "active_modification_categories":
        value = sorted({str(modification["category"]) for modification in context.modifications})
    elif key == "active_modification_count":
        value = len(context.modifications)
    else:
        raise ValueError("unknown configuration feature")
    if value is None:
        return context.missing(definition, MissingReason.UNAVAILABLE_SIGNAL)
    if isinstance(value, str):
        value = value.strip() or None
    if value is None:
        return context.missing(definition, MissingReason.UNAVAILABLE_SIGNAL)
    return context.make_value(
        definition,
        value,
        source_entities=(str(configuration["id"]),),
        available_at=context.configuration_available_at,
        source_window_start=configuration["effective_at"],
        source_window_end=context.start,
        details={"metadata_keys_used": [key] if key != "configuration_label" else []},
    )


def _vehicle_value(
    context: FeatureContext, definition: FeatureDefinition, key: str
) -> FeatureValue:
    value = context.vehicle.get(key)
    if value is None:
        return context.missing(definition, MissingReason.UNAVAILABLE_SIGNAL)
    return context.make_value(
        definition,
        str(value),
        source_entities=(context.vehicle_id,),
        available_at=context.vehicle["created_at"],
        source_window_start=context.vehicle["created_at"],
        source_window_end=context.vehicle["created_at"],
    )


def _engine_code_calculator(context: FeatureContext, definition: FeatureDefinition) -> FeatureValue:
    return _vehicle_value(context, definition, "engine_code")


def _stat_calculator(signal: str, statistic: str) -> FeatureCalculator:
    return lambda context, definition: _signal_value(context, definition, signal, statistic)


def _simple_calculator(key: str) -> FeatureCalculator:
    def calculate(context: FeatureContext, definition: FeatureDefinition) -> FeatureValue:
        if key.startswith("raw_context."):
            return _configuration_value(context, definition, key.removeprefix("raw_context."))
        if key == "temporal_context.pull_order_index":
            return context.make_value(
                definition,
                context.repeated_pull_index,
                source_entities=tuple(item.id for item in context.prior_pulls),
                available_at=context.context_available_at,
                source_window_start=context.start,
                source_window_end=context.start,
            )
        if key == "temporal_context.prior_pull_count":
            return context.make_value(
                definition,
                context.prior_pull_count,
                source_entities=tuple(item.id for item in context.prior_pulls),
                available_at=context.context_available_at,
                source_window_start=(
                    min((item.row["started_at"] for item in context.prior_pulls), default=None)
                ),
                source_window_end=(
                    max((item.row["ended_at"] for item in context.prior_pulls), default=None)
                ),
                details={"history_window_count": context.prior_pull_count},
            )
        if key == "thermal.pre_pull_iat_k":
            return _prior_or_pre_value(
                context, definition, "engine.intake_air_temperature", pre=True
            )
        if key == "thermal.pull_to_pull_iat_delta_k":
            return _pull_to_pull_iat_delta(context, definition)
        if key.startswith("thermal.recovery_") or key.endswith("_recovery_delta_k"):
            return _thermal_recovery(context, definition, key)
        if key == "performance.pull_duration_s":
            if context.observation_cutoff < context.end:
                return context.missing(definition, MissingReason.NOT_OBSERVED_YET)
            value = (context.end - context.start).total_seconds()
            return context.make_value(
                definition,
                value,
                available_at=max(context.end, context.pull["created_at"]),
                source_window_start=context.start,
                source_window_end=context.end,
                details={"boundary_semantics": "[started_at, ended_at]", "source": "pulls"},
            )
        if key == "performance.speed_60_100_kmh_s":
            return _speed_interval(context, definition)
        if key == "performance.relative_to_prior_mean_pct":
            return _performance_relative(context, definition)
        if key.startswith("boost_air.throttle_closure_fraction"):
            return _throttle_closure(context, definition)
        if key.startswith("boost_air.history_deviation"):
            return _history_deviation(context, definition, "engine.boost_pressure")
        if key.startswith("fuel.history_deviation"):
            return _history_deviation(context, definition, "fuel.high_pressure")
        if key == "quality.observation_count":
            return context.make_value(
                definition,
                len(context.raw_samples),
                samples=context.raw_samples,
                details={"quality_rows_included": True},
            )
        if key == "quality.valid_observation_count":
            return context.make_value(
                definition, len(context.valid_samples), samples=context.valid_samples
            )
        if key == "quality.invalid_observation_count":
            return context.make_value(
                definition,
                sum(sample.quality != "valid" for sample in context.raw_samples),
                samples=context.raw_samples,
            )
        if key == "quality.duplicate_timestamp_count":
            return context.make_value(
                definition,
                int(context.quality_metadata.get("duplicate_timestamp_count", 0)),
                samples=context.raw_samples,
                details={"deduplication": "highest sequence then stable sample ID"},
            )
        if key == "quality.signal_coverage_ratio":
            if not context.frame_count:
                return context.missing(definition, MissingReason.INSUFFICIENT_COVERAGE)
            return context.make_value(
                definition,
                sum(context.signal_coverage.values()) / max(1, len(context.signal_coverage)),
                samples=context.raw_samples,
                details={"definition": "mean per-signal valid samples / observed timestamp frames"},
            )
        if key == "quality.missing_sample_count":
            missing = sum(
                max(0, context.frame_count - len(context.for_signal(signal)))
                for signal in context.signal_coverage
            )
            return context.make_value(definition, missing, samples=context.raw_samples)
        if key == "quality.max_gap_s":
            gaps = [
                (right.observed_at - left.observed_at).total_seconds()
                for signal in context.signal_coverage
                for left, right in zip(
                    context.for_signal(signal), context.for_signal(signal)[1:], strict=False
                )
            ]
            return context.make_value(
                definition,
                max(gaps, default=0.0),
                samples=context.valid_samples,
                details={"signal_count": len(context.signal_coverage)},
            )
        if key in {"quality.median_sample_interval_s", "quality.sample_interval_stddev_s"}:
            timestamps = sorted({sample.observed_at for sample in context.valid_samples})
            intervals = [
                (right - left).total_seconds()
                for left, right in zip(timestamps, timestamps[1:], strict=False)
                if right > left
            ]
            if not intervals:
                return context.missing(definition, MissingReason.INSUFFICIENT_COVERAGE)
            if key == "quality.median_sample_interval_s":
                result = _median(intervals)
            else:
                mean = math.fsum(intervals) / len(intervals)
                result = math.sqrt(
                    math.fsum((item - mean) ** 2 for item in intervals) / len(intervals)
                )
            return context.make_value(definition, result, samples=context.valid_samples)
        if key == "quality.stuck_signal_count":
            stuck = 0
            for signal in context.signal_coverage:
                rows = context.for_signal(signal)
                run = 1
                found = False
                for previous, current in zip(rows, rows[1:], strict=False):
                    run = run + 1 if current.value == previous.value else 1
                    found = found or run >= 3
                stuck += int(found)
            return context.make_value(definition, stuck, samples=context.valid_samples)
        if key == "quality.dropout_event_count":
            event_times = [event["created_at"] for event in context.events]
            event_ends = [event["ended_at"] for event in context.events]
            return context.make_value(
                definition,
                sum(
                    event["event_type"] in {"telemetry_gap", "sensor_dropout"}
                    for event in context.events
                ),
                source_entities=tuple(str(event["id"]) for event in context.events),
                available_at=max([context.context_available_at, *event_times]),
                source_window_end=max(event_ends) if event_ends else None,
                details={"event_policy": "event and created time at or before observation cutoff"},
            )
        if key == "quality.truncated":
            marker = (context.session.get("metadata") or {}).get("truncated")
            if not isinstance(marker, bool):
                return context.missing(definition, MissingReason.NOT_APPLICABLE)
            return context.make_value(
                definition,
                marker,
                available_at=context.session["created_at"],
                source_entities=(context.session_id,),
            )
        if key == "quality.available_signals":
            return context.make_value(
                definition,
                sorted(signal for signal, ratio in context.signal_coverage.items() if ratio > 0),
                samples=context.valid_samples,
            )
        if key == "quality.expected_coverage_ratio":
            expected = context.quality_metadata.get("expected_coverage_ratio")
            if expected is None:
                return context.missing(definition, MissingReason.NOT_APPLICABLE)
            return context.make_value(definition, float(expected), samples=context.raw_samples)
        if key == "raw_context.engine_code":
            return _vehicle_value(context, definition, "engine_code")
        if key.startswith("history."):
            return _history_stat(context, definition, key)
        raise ValueError("no calculator for feature")

    return calculate


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _prior_or_pre_value(
    context: FeatureContext, definition: FeatureDefinition, signal: str, *, pre: bool
) -> FeatureValue:
    rows = context.for_signal(signal)
    if pre:
        rows = tuple(item for item in rows if item.observed_at <= context.start)
    if rows:
        selected = rows[-1]
        return context.make_value(
            definition,
            selected.value,
            samples=(selected,),
            source_window_start=selected.observed_at,
            source_window_end=selected.observed_at,
        )
    return _prior_end_value(context, definition, signal)


def _prior_end_value(
    context: FeatureContext, definition: FeatureDefinition, signal: str
) -> FeatureValue:
    prior = context.prior_pulls[0] if context.prior_pulls else None
    if prior is None:
        return context.missing(definition, MissingReason.NOT_APPLICABLE)
    rows = tuple(
        item for item in prior.samples if item.signal == signal and item.quality == "valid"
    )
    if not rows:
        return context.missing(
            definition, MissingReason.UNAVAILABLE_SIGNAL, source_entities=(prior.id,)
        )
    selected = rows[-1]
    return context.make_value(
        definition,
        selected.value,
        samples=(selected,),
        source_entities=(prior.id,),
        available_at=max(selected.available_at, prior.row["created_at"]),
        source_window_start=selected.observed_at,
        source_window_end=selected.observed_at,
        details={"source_pull_id": prior.id},
    )


def _thermal_recovery(
    context: FeatureContext, definition: FeatureDefinition, key: str
) -> FeatureValue:
    if not context.prior_pulls:
        return context.missing(definition, MissingReason.NOT_APPLICABLE)
    prior = context.prior_pulls[0]
    if key == "thermal.recovery_elapsed_s":
        elapsed = (context.start - prior.row["ended_at"]).total_seconds()
        return context.make_value(
            definition,
            elapsed,
            source_entities=(prior.id,),
            available_at=max(context.context_available_at, prior.row["created_at"]),
            source_window_start=prior.row["ended_at"],
            source_window_end=context.start,
        )
    signal = (
        "engine.intake_air_temperature"
        if key == "thermal.iat_recovery_delta_k"
        else "engine.oil_temperature"
    )
    prior_rows = tuple(
        item for item in prior.samples if item.signal == signal and item.quality == "valid"
    )
    current_rows = tuple(
        item for item in context.for_signal(signal) if item.observed_at <= context.start
    )
    if not prior_rows or not current_rows:
        return context.missing(
            definition, MissingReason.UNAVAILABLE_SIGNAL, source_entities=(prior.id,)
        )
    before, after = prior_rows[-1], current_rows[-1]
    return context.make_value(
        definition,
        before.value - after.value,
        samples=(before, after),
        source_entities=(prior.id,),
        available_at=max(before.available_at, after.available_at, prior.row["created_at"]),
        source_window_start=before.observed_at,
        source_window_end=after.observed_at,
        details={"positive_means_temperature_fell_between_pulls": True},
    )


def _pull_to_pull_iat_delta(context: FeatureContext, definition: FeatureDefinition) -> FeatureValue:
    if not context.prior_pulls:
        return context.missing(definition, MissingReason.NOT_APPLICABLE)
    current = context.for_signal("engine.intake_air_temperature")
    previous = tuple(
        item
        for item in context.prior_pulls[0].samples
        if item.signal == "engine.intake_air_temperature" and item.quality == "valid"
    )
    if not current or not previous:
        return context.missing(
            definition,
            MissingReason.UNAVAILABLE_SIGNAL,
            source_entities=(context.prior_pulls[0].id,),
        )
    before, after = previous[-1], current[-1]
    return context.make_value(
        definition,
        after.value - before.value,
        samples=(before, after),
        source_entities=(context.prior_pulls[0].id,),
        available_at=max(context.end, context.pull["created_at"]),
        source_window_start=before.observed_at,
        source_window_end=after.observed_at,
        details={"source": "current pull end minus prior compatible pull end"},
    )


def _pull_input(
    row: dict[str, Any], samples: tuple[TelemetryFeatureSample, ...]
) -> PullInput | None:
    frames: dict[Any, dict[str, float]] = {}
    for sample in samples:
        frames.setdefault(sample.observed_at, {})[sample.signal] = sample.value
    selected = tuple(
        Sample(at, values["engine.rpm"], values)
        for at, values in sorted(frames.items())
        if "engine.rpm" in values
    )
    if len(selected) < 2:
        return None
    return PullInput(
        str(row["id"]),
        str(row["session_id"]),
        str(row["vehicle_id"]),
        str(row.get("effective_configuration_id") or row.get("configuration_id") or "") or None,
        row["started_at"],
        row["ended_at"],
        float(row.get("data_completeness") or 0.0),
        selected,
    )


def _speed_interval(context: FeatureContext, definition: FeatureDefinition) -> FeatureValue:
    samples = _pull_input(context.pull, context.valid_samples)
    if samples is None:
        return context.missing(definition, MissingReason.INSUFFICIENT_COVERAGE)
    result = acceleration_interval(samples.samples, 60 / 3.6, 100 / 3.6, AnalyticsConfig())
    seconds = result.get("elapsed_seconds")
    if not isinstance(seconds, (float, int)):
        return context.missing(
            definition,
            MissingReason.INSUFFICIENT_COVERAGE,
            details={"sufficiency": result.get("sufficiency")},
        )
    return context.make_value(
        definition,
        float(seconds),
        samples=context.valid_samples,
        available_at=max(context.end, context.pull["created_at"]),
        source_window_start=context.start,
        source_window_end=context.end,
        details={"calculation": "Phase 5 acceleration_interval", "speed_bounds_kmh": [60, 100]},
    )


def _performance_relative(context: FeatureContext, definition: FeatureDefinition) -> FeatureValue:
    current = _speed_interval(context, definition)
    previous = _historical_performance(context)
    if (
        not isinstance(current.value, (int, float))
        or isinstance(current.value, bool)
        or previous is None
        or previous == 0
    ):
        return context.missing(definition, MissingReason.INSUFFICIENT_COVERAGE)
    return context.make_value(
        definition,
        (float(current.value) - previous) / abs(previous),
        samples=context.valid_samples,
        source_entities=tuple(item.id for item in context.prior_pulls),
        available_at=max(context.end, context.pull["created_at"]),
        source_window_start=context.start,
        source_window_end=context.end,
        details={
            "baseline": "mean compatible prior pull 60-100 km/h interval",
            "prior_count": len(context.prior_pulls),
        },
    )


def _historical_performance(context: FeatureContext) -> float | None:
    values: list[float] = []
    for prior in context.prior_pulls:
        pull_input = _pull_input(prior.row, prior.samples)
        if pull_input is None:
            continue
        metric = acceleration_interval(pull_input.samples, 60 / 3.6, 100 / 3.6, AnalyticsConfig())
        value = metric.get("elapsed_seconds")
        if isinstance(value, (int, float)) and math.isfinite(value):
            values.append(float(value))
    return math.fsum(values) / len(values) if values else None


def _history_stat(context: FeatureContext, definition: FeatureDefinition, key: str) -> FeatureValue:
    if key in {"history.prior_performance_mean_s", "history.prior_performance_variance_s2"}:
        values: list[float] = []
        for prior in context.prior_pulls:
            pull_input = _pull_input(prior.row, prior.samples)
            if pull_input is None:
                continue
            metric = acceleration_interval(
                pull_input.samples, 60 / 3.6, 100 / 3.6, AnalyticsConfig()
            )
            value = metric.get("elapsed_seconds")
            if isinstance(value, (float, int)) and math.isfinite(value):
                values.append(float(value))
        if not values:
            return context.missing(definition, MissingReason.NOT_APPLICABLE)
        mean = math.fsum(values) / len(values)
        result = (
            mean
            if key.endswith("mean_s")
            else math.fsum((item - mean) ** 2 for item in values) / len(values)
        )
    elif key in {"history.prior_boost_mean_pa", "history.prior_fuel_mean_pa"}:
        signal = "engine.boost_pressure" if "boost" in key else "fuel.high_pressure"
        rows = [
            sample.value
            for prior in context.prior_pulls
            for sample in prior.samples
            if sample.signal == signal and sample.quality == "valid"
        ]
        if not rows:
            return context.missing(definition, MissingReason.UNAVAILABLE_SIGNAL)
        result = math.fsum(rows) / len(rows)
    elif key == "history.prior_event_count":
        event_times = [event["created_at"] for event in context.events]
        event_ends = [event["ended_at"] for event in context.events]
        return context.make_value(
            definition,
            len(context.events),
            source_entities=tuple(str(event["id"]) for event in context.events),
            available_at=max([context.context_available_at, *event_times]),
            source_window_end=max(event_ends) if event_ends else None,
            details={"event_types": sorted({str(event["event_type"]) for event in context.events})},
        )
    else:
        raise ValueError("unknown history feature")
    prior_ids = tuple(item.id for item in context.prior_pulls)
    available = max(
        (item.row["created_at"] for item in context.prior_pulls),
        default=context.context_available_at,
    )
    end = max((item.row["ended_at"] for item in context.prior_pulls), default=None)
    start = min((item.row["started_at"] for item in context.prior_pulls), default=None)
    return context.make_value(
        definition,
        float(result),
        source_entities=prior_ids,
        available_at=available,
        source_window_start=start,
        source_window_end=end,
        details={"history_count": len(prior_ids), "strictly_before_current_pull": True},
    )


def _throttle_closure(context: FeatureContext, definition: FeatureDefinition) -> FeatureValue:
    rows = _valid_rows(context, "engine.throttle_position")
    if not rows:
        return context.missing(definition, MissingReason.UNAVAILABLE_SIGNAL)
    coverage = context.signal_coverage.get("engine.throttle_position", 0.0)
    if coverage < definition.minimum_quality:
        return context.missing(definition, MissingReason.INSUFFICIENT_COVERAGE)
    maximum = max(row.value for row in rows)
    if maximum <= 0:
        return context.missing(definition, MissingReason.INVALID_QUALITY)
    return context.make_value(
        definition,
        sum(row.value < maximum * 0.9 for row in rows) / len(rows),
        samples=rows,
        details={"rule": "fraction below 90% of observed pull maximum"},
    )


def _history_deviation(
    context: FeatureContext, definition: FeatureDefinition, signal: str
) -> FeatureValue:
    current_rows = context.for_signal(signal)
    past = [
        sample.value
        for prior in context.prior_pulls
        for sample in prior.samples
        if sample.signal == signal and sample.quality == "valid"
    ]
    if not current_rows or not past:
        return context.missing(definition, MissingReason.UNAVAILABLE_SIGNAL)
    current_mean = math.fsum(row.value for row in current_rows) / len(current_rows)
    previous_mean = math.fsum(past) / len(past)
    return context.make_value(
        definition,
        current_mean - previous_mean,
        samples=current_rows,
        source_entities=tuple(item.id for item in context.prior_pulls),
        available_at=max(context.end, context.pull["created_at"]),
        source_window_start=context.start,
        source_window_end=context.end,
        details={"prior_mean": previous_mean, "prior_count": len(context.prior_pulls)},
    )


def _definition(
    key: str,
    category: FeatureCategory,
    dtype: FeatureDType,
    unit: str | None,
    *,
    scope: EntityScope = EntityScope.PULL,
    signal: str | None = None,
    availability: TemporalAvailability = TemporalAvailability.DURING_WINDOW,
    minimum_quality: float = 0.0,
    bounds: tuple[float | None, float | None] | None = None,
    optional_signal: bool = False,
) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=key.replace(".", " ").replace("_", " ").title(),
        description=f"Deterministic {key.replace('.', ' ')} feature from canonical source context.",
        category=category,
        unit=unit,
        dtype=dtype,
        scope=scope,
        required_signals=() if signal is None or optional_signal else (signal,),
        optional_signals=(signal,) if signal is not None and optional_signal else (),
        minimum_quality=minimum_quality,
        algorithm_id=f"vehicle-platform.{key}",
        algorithm_version="1",
        availability=availability,
        bounds=bounds,
        tags=("phase9a",),
    )


def _registry_entries() -> tuple[tuple[FeatureDefinition, FeatureCalculator], ...]:
    entries: list[tuple[FeatureDefinition, FeatureCalculator]] = []
    stats = (("start", "start"), ("end", "end"), ("min", "min"), ("max", "max"), ("mean", "mean"))
    for key, signal in (
        ("engine.intake_air_temperature", "thermal.iat"),
        ("engine.oil_temperature", "thermal.oil_temperature"),
        ("engine.coolant_temperature", "thermal.coolant_temperature"),
        ("engine.boost_pressure", "boost_air.pressure"),
        ("engine.throttle_position", "boost_air.throttle"),
        ("fuel.high_pressure", "fuel.rail_pressure"),
    ):
        category = (
            FeatureCategory.THERMAL
            if signal.startswith("thermal.")
            else FeatureCategory.BOOST_AIR
            if signal.startswith("boost_air.")
            else FeatureCategory.FUEL
        )
        signal_unit = SIGNAL_BY_KEY[key].unit
        for suffix, statistic in stats:
            feature_key = f"{signal}_{suffix}"
            entries.append(
                (
                    _definition(
                        feature_key,
                        category,
                        FeatureDType.FLOAT,
                        signal_unit,
                        signal=key,
                        minimum_quality=0.5,
                    ),
                    _stat_calculator(key, statistic),
                )
            )
    for feature_key, signal, feature_unit in (
        ("thermal.iat_delta_k", "engine.intake_air_temperature", "K"),
        ("thermal.iat_slope_k_per_s", "engine.intake_air_temperature", "K/s"),
        ("boost_air.pressure_rise_rate_pa_per_s", "engine.boost_pressure", "Pa/s"),
        ("boost_air.pressure_stddev_pa", "engine.boost_pressure", "Pa"),
        ("fuel.rail_pressure_delta_pa", "fuel.high_pressure", "Pa"),
        ("fuel.rail_pressure_drop_rate_pa_per_s", "fuel.high_pressure", "Pa/s"),
        ("fuel.rail_pressure_stddev_pa", "fuel.high_pressure", "Pa"),
    ):
        statistic = {
            "thermal.iat_delta_k": "delta",
            "thermal.iat_slope_k_per_s": "slope",
            "boost_air.pressure_rise_rate_pa_per_s": "slope",
            "boost_air.pressure_stddev_pa": "stddev",
            "fuel.rail_pressure_delta_pa": "delta",
            "fuel.rail_pressure_drop_rate_pa_per_s": "slope",
            "fuel.rail_pressure_stddev_pa": "stddev",
        }[feature_key]
        category = (
            FeatureCategory.THERMAL
            if feature_key.startswith("thermal.")
            else FeatureCategory.FUEL
            if feature_key.startswith("fuel.")
            else FeatureCategory.BOOST_AIR
        )
        entries.append(
            (
                _definition(
                    feature_key,
                    category,
                    FeatureDType.FLOAT,
                    feature_unit,
                    signal=signal,
                    minimum_quality=0.5,
                ),
                _stat_calculator(signal, statistic),
            )
        )
    for key, dtype, context_unit, category, scope, availability, bounds in (
        (
            "raw_context.configuration_label",
            FeatureDType.CATEGORICAL,
            None,
            FeatureCategory.RAW_CONTEXT,
            EntityScope.CONFIGURATION,
            TemporalAvailability.PRE_EVENT,
            None,
        ),
        (
            "raw_context.configuration_stage",
            FeatureDType.CATEGORICAL,
            None,
            FeatureCategory.RAW_CONTEXT,
            EntityScope.CONFIGURATION,
            TemporalAvailability.PRE_EVENT,
            None,
        ),
        (
            "raw_context.tune_version",
            FeatureDType.CATEGORICAL,
            None,
            FeatureCategory.RAW_CONTEXT,
            EntityScope.CONFIGURATION,
            TemporalAvailability.PRE_EVENT,
            None,
        ),
        (
            "raw_context.fuel_type",
            FeatureDType.CATEGORICAL,
            None,
            FeatureCategory.RAW_CONTEXT,
            EntityScope.CONFIGURATION,
            TemporalAvailability.PRE_EVENT,
            None,
        ),
        (
            "raw_context.active_modification_count",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.RAW_CONTEXT,
            EntityScope.CONFIGURATION,
            TemporalAvailability.PRE_EVENT,
            (0, None),
        ),
        (
            "raw_context.active_modification_categories",
            FeatureDType.CATEGORICAL_LIST,
            None,
            FeatureCategory.RAW_CONTEXT,
            EntityScope.CONFIGURATION,
            TemporalAvailability.PRE_EVENT,
            None,
        ),
        (
            "raw_context.engine_code",
            FeatureDType.CATEGORICAL,
            None,
            FeatureCategory.RAW_CONTEXT,
            EntityScope.VEHICLE,
            TemporalAvailability.PRE_EVENT,
            None,
        ),
        (
            "performance.pull_duration_s",
            FeatureDType.FLOAT,
            "s",
            FeatureCategory.PERFORMANCE,
            EntityScope.PULL,
            TemporalAvailability.POST_WINDOW,
            (0, None),
        ),
        (
            "performance.speed_60_100_kmh_s",
            FeatureDType.FLOAT,
            "s",
            FeatureCategory.PERFORMANCE,
            EntityScope.PULL,
            TemporalAvailability.POST_WINDOW,
            (0, None),
        ),
        (
            "performance.relative_to_prior_mean_pct",
            FeatureDType.FLOAT,
            "ratio",
            FeatureCategory.PERFORMANCE,
            EntityScope.PULL,
            TemporalAvailability.POST_WINDOW,
            None,
        ),
        (
            "thermal.pre_pull_iat_k",
            FeatureDType.FLOAT,
            "K",
            FeatureCategory.THERMAL,
            EntityScope.PULL,
            TemporalAvailability.PRE_EVENT,
            None,
        ),
        (
            "thermal.pull_to_pull_iat_delta_k",
            FeatureDType.FLOAT,
            "K",
            FeatureCategory.THERMAL,
            EntityScope.PULL,
            TemporalAvailability.POST_WINDOW,
            None,
        ),
        (
            "thermal.recovery_elapsed_s",
            FeatureDType.FLOAT,
            "s",
            FeatureCategory.THERMAL,
            EntityScope.PULL,
            TemporalAvailability.PRE_EVENT,
            (0, None),
        ),
        (
            "thermal.iat_recovery_delta_k",
            FeatureDType.FLOAT,
            "K",
            FeatureCategory.THERMAL,
            EntityScope.PULL,
            TemporalAvailability.PRE_EVENT,
            None,
        ),
        (
            "thermal.oil_recovery_delta_k",
            FeatureDType.FLOAT,
            "K",
            FeatureCategory.THERMAL,
            EntityScope.PULL,
            TemporalAvailability.PRE_EVENT,
            None,
        ),
        (
            "temporal_context.pull_order_index",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.TEMPORAL_CONTEXT,
            EntityScope.PULL,
            TemporalAvailability.PRE_EVENT,
            (1, None),
        ),
        (
            "temporal_context.prior_pull_count",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.TEMPORAL_CONTEXT,
            EntityScope.PULL,
            TemporalAvailability.HISTORICAL_ONLY,
            (0, None),
        ),
        (
            "history.prior_performance_mean_s",
            FeatureDType.FLOAT,
            "s",
            FeatureCategory.HISTORY,
            EntityScope.PULL,
            TemporalAvailability.HISTORICAL_ONLY,
            (0, None),
        ),
        (
            "history.prior_performance_variance_s2",
            FeatureDType.FLOAT,
            "s^2",
            FeatureCategory.HISTORY,
            EntityScope.PULL,
            TemporalAvailability.HISTORICAL_ONLY,
            (0, None),
        ),
        (
            "history.prior_boost_mean_pa",
            FeatureDType.FLOAT,
            "Pa",
            FeatureCategory.HISTORY,
            EntityScope.PULL,
            TemporalAvailability.HISTORICAL_ONLY,
            None,
        ),
        (
            "history.prior_fuel_mean_pa",
            FeatureDType.FLOAT,
            "Pa",
            FeatureCategory.HISTORY,
            EntityScope.PULL,
            TemporalAvailability.HISTORICAL_ONLY,
            None,
        ),
        (
            "history.prior_event_count",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.HISTORY,
            EntityScope.PULL,
            TemporalAvailability.HISTORICAL_ONLY,
            (0, None),
        ),
        (
            "boost_air.throttle_closure_fraction",
            FeatureDType.FLOAT,
            "ratio",
            FeatureCategory.BOOST_AIR,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            (0, 1),
        ),
        (
            "boost_air.history_deviation_pa",
            FeatureDType.FLOAT,
            "Pa",
            FeatureCategory.BOOST_AIR,
            EntityScope.PULL,
            TemporalAvailability.POST_WINDOW,
            None,
        ),
        (
            "fuel.history_deviation_pa",
            FeatureDType.FLOAT,
            "Pa",
            FeatureCategory.FUEL,
            EntityScope.PULL,
            TemporalAvailability.POST_WINDOW,
            None,
        ),
        (
            "quality.observation_count",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            (0, None),
        ),
        (
            "quality.valid_observation_count",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            (0, None),
        ),
        (
            "quality.invalid_observation_count",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            (0, None),
        ),
        (
            "quality.duplicate_timestamp_count",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            (0, None),
        ),
        (
            "quality.signal_coverage_ratio",
            FeatureDType.FLOAT,
            "ratio",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            (0, 1),
        ),
        (
            "quality.missing_sample_count",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            (0, None),
        ),
        (
            "quality.max_gap_s",
            FeatureDType.FLOAT,
            "s",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            (0, None),
        ),
        (
            "quality.median_sample_interval_s",
            FeatureDType.FLOAT,
            "s",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            (0, None),
        ),
        (
            "quality.sample_interval_stddev_s",
            FeatureDType.FLOAT,
            "s",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            (0, None),
        ),
        (
            "quality.stuck_signal_count",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.POST_WINDOW,
            (0, None),
        ),
        (
            "quality.dropout_event_count",
            FeatureDType.INTEGER,
            "count",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.HISTORICAL_ONLY,
            (0, None),
        ),
        (
            "quality.truncated",
            FeatureDType.BOOLEAN,
            None,
            FeatureCategory.QUALITY,
            EntityScope.SESSION,
            TemporalAvailability.POST_WINDOW,
            None,
        ),
        (
            "quality.available_signals",
            FeatureDType.CATEGORICAL_LIST,
            None,
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.DURING_WINDOW,
            None,
        ),
        (
            "quality.expected_coverage_ratio",
            FeatureDType.FLOAT,
            "ratio",
            FeatureCategory.QUALITY,
            EntityScope.PULL,
            TemporalAvailability.POST_WINDOW,
            (0, 1),
        ),
    ):
        calc = (
            _engine_code_calculator if key == "raw_context.engine_code" else _simple_calculator(key)
        )
        entries.append(
            (
                FeatureDefinition(
                    key=key,
                    name=key.replace(".", " ").replace("_", " ").title(),
                    description=(
                        f"Deterministic {key.replace('.', ' ')} from canonical source context."
                    ),
                    category=category,
                    unit=context_unit,
                    dtype=dtype,
                    scope=scope,
                    minimum_quality=0.0,
                    algorithm_id=f"vehicle-platform.{key}",
                    algorithm_version="1",
                    availability=availability,
                    bounds=bounds,
                    tags=("phase9a",),
                ),
                calc,
            )
        )
    return tuple(entries)


_ENTRIES = _registry_entries()
DEFAULT_REGISTRY = FeatureRegistry(
    tuple(item[0] for item in _ENTRIES), {item[0].key: item[1] for item in _ENTRIES}
)
