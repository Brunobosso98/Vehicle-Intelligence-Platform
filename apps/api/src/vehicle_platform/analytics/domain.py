import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import cast

from vehicle_platform.analytics.instrumentation import traced

CALCULATION_VERSION = "phase5-analytics-v1.1"


class Sufficiency(StrEnum):
    SUFFICIENT = "sufficient"
    LIMITED = "limited"
    INSUFFICIENT = "insufficient"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class AnalyticsConfig:
    rpm_bin_size: int = 250
    minimum_bin_samples: int = 3
    minimum_rpm_overlap: float = 750
    maximum_gap_seconds: float = 1.0
    minimum_completeness: float = 0.7
    maximum_pulls: int = 20
    minimum_baseline_sessions: int = 3
    minimum_correlation_samples: int = 5
    speed_intervals_kmh: tuple[tuple[float, float], ...] = ((60, 100), (80, 120), (100, 150))

    def __post_init__(self) -> None:
        if not 1 <= len(self.speed_intervals_kmh) <= 5 or any(
            not math.isfinite(a) or not math.isfinite(b) or not 0 <= a < b <= 300
            for a, b in self.speed_intervals_kmh
        ):
            raise ValueError(
                "speed intervals require 1..5 finite increasing pairs within 0..300 km/h"
            )
        if not 100 <= self.rpm_bin_size <= 1000:
            raise ValueError("rpm_bin_size must be between 100 and 1000")
        if not 2 <= self.minimum_bin_samples <= 100:
            raise ValueError("minimum_bin_samples must be between 2 and 100")
        if not 0 < self.maximum_gap_seconds <= 5:
            raise ValueError("maximum_gap_seconds must be in (0, 5]")
        if not 0 < self.minimum_completeness <= 1:
            raise ValueError("minimum_completeness must be in (0, 1]")
        if not math.isfinite(self.minimum_rpm_overlap) or self.minimum_rpm_overlap <= 0:
            raise ValueError("minimum_rpm_overlap must be positive and finite")
        if self.minimum_baseline_sessions < 3 or self.minimum_correlation_samples < 5:
            raise ValueError("history and correlation thresholds cannot weaken default evidence")
        if not 2 <= self.maximum_pulls <= 20:
            raise ValueError("maximum_pulls must be between 2 and 20")

    @property
    def configuration_hash(self) -> str:
        encoded = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True)
class Sample:
    observed_at: datetime
    rpm: float
    values: dict[str, float]


@dataclass(frozen=True)
class PullInput:
    id: str
    session_id: str
    vehicle_id: str
    configuration_id: str | None
    started_at: datetime
    ended_at: datetime
    completeness: float
    samples: tuple[Sample, ...]
    event_ids: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    event_markers: tuple[dict[str, object], ...] = ()


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between zero and one")
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def mad(values: list[float]) -> float | None:
    center = median(values)
    return median([abs(value - center) for value in values]) if center is not None else None


def iqr(values: list[float]) -> float | None:
    p25, p75 = percentile(values, 0.25), percentile(values, 0.75)
    return p75 - p25 if p25 is not None and p75 is not None else None


def relative_delta(value: float | None, baseline: float | None) -> float | None:
    return None if value is None or baseline in (None, 0) else (value - baseline) / abs(baseline)


def coefficient_of_variation(values: list[float]) -> float | None:
    center = sum(values) / len(values) if values else 0
    if len(values) < 2 or center == 0:
        return None
    variance = sum((value - center) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) / abs(center)


def spearman(x: list[float], y: list[float], minimum: int = 5) -> tuple[float | None, Sufficiency]:
    if len(x) != len(y) or len(x) < minimum:
        return None, Sufficiency.INSUFFICIENT

    def ranks(values: list[float]) -> list[float]:
        ordered = sorted((value, index) for index, value in enumerate(values))
        result = [0.0] * len(values)
        cursor = 0
        while cursor < len(ordered):
            end = cursor
            while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[cursor][0]:
                end += 1
            rank = (cursor + end) / 2 + 1
            for position in range(cursor, end + 1):
                result[ordered[position][1]] = rank
            cursor = end + 1
        return result

    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    denominator = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return (
        (numerator / denominator, Sufficiency.SUFFICIENT)
        if denominator
        else (None, Sufficiency.INSUFFICIENT)
    )


@dataclass(frozen=True)
class Comparability:
    overall: float
    dimensions: dict[str, float]
    accepted: bool
    reasons: tuple[str, ...]
    common_rpm_range: tuple[float, float] | None


@traced("analytics.comparability")
def compare_context(left: PullInput, right: PullInput, config: AnalyticsConfig) -> Comparability:
    reasons: list[str] = []
    if left.vehicle_id != right.vehicle_id:
        reasons.append("different_vehicle")
    if not left.configuration_id or left.configuration_id != right.configuration_id:
        reasons.append("different_configuration")
    if not left.samples or not right.samples:
        return Comparability(0, {}, False, tuple(reasons + ["missing_samples"]), None)
    low = max(min(s.rpm for s in left.samples), min(s.rpm for s in right.samples))
    high = min(max(s.rpm for s in left.samples), max(s.rpm for s in right.samples))
    overlap = max(0.0, high - low)
    total = max(max(s.rpm for s in left.samples), max(s.rpm for s in right.samples)) - min(
        min(s.rpm for s in left.samples), min(s.rpm for s in right.samples)
    )
    rpm_score = overlap / total if total else 0
    if overlap < config.minimum_rpm_overlap:
        reasons.append("insufficient_rpm_overlap")
    durations = [(p.ended_at - p.started_at).total_seconds() for p in (left, right)]
    duration_score = min(durations) / max(durations) if max(durations) else 0

    def metric_similarity(signal: str) -> float:
        a = median([s.values[signal] for s in left.samples if signal in s.values])
        b = median([s.values[signal] for s in right.samples if signal in s.values])
        return 0.5 if a is None or b is None else max(0.0, 1 - abs(a - b) / max(abs(a), abs(b), 1))

    throttle = metric_similarity("engine.throttle_position")
    thermal = metric_similarity("engine.intake_air_temperature")
    quality = min(left.completeness, right.completeness)
    dimensions = {
        "rpm_overlap": rpm_score,
        "duration_similarity": duration_score,
        "throttle_similarity": throttle,
        "thermal_similarity": thermal,
        "quality_similarity": quality,
    }
    weights = {
        "rpm_overlap": 0.35,
        "duration_similarity": 0.15,
        "throttle_similarity": 0.2,
        "thermal_similarity": 0.1,
        "quality_similarity": 0.2,
    }
    overall = sum(dimensions[key] * weight for key, weight in weights.items())
    if quality < config.minimum_completeness:
        reasons.append("poor_quality")
    return Comparability(
        round(overall, 6),
        dimensions,
        not reasons and overall >= 0.65,
        tuple(reasons),
        (low, high) if overlap else None,
    )


@traced("analytics.normalization")
def bin_statistics(
    samples: tuple[Sample, ...], signal: str, low: float, high: float, config: AnalyticsConfig
) -> list[dict[str, object]]:
    samples = tuple(sorted(samples, key=lambda sample: sample.observed_at))
    bins: list[dict[str, object]] = []
    start = math.floor(low / config.rpm_bin_size) * config.rpm_bin_size
    while start < high:
        end = start + config.rpm_bin_size
        selected = [
            s for s in samples if max(start, low) <= s.rpm < min(end, high) and signal in s.values
        ]
        values = [s.values[signal] for s in selected]
        gaps = [
            (b.observed_at - a.observed_at).total_seconds()
            for a, b in zip(selected, selected[1:], strict=False)
        ]
        sufficient = len(values) >= config.minimum_bin_samples and not any(
            gap > config.maximum_gap_seconds for gap in gaps
        )
        duration = (
            (selected[-1].observed_at - selected[0].observed_at).total_seconds()
            if len(selected) > 1
            else 0
        )
        bins.append(
            {
                "rpm_start": start,
                "rpm_end": end,
                "count": len(values),
                "time_coverage_seconds": duration,
                "median": median(values) if sufficient else None,
                "mean": sum(values) / len(values) if sufficient else None,
                "minimum": min(values) if sufficient else None,
                "maximum": max(values) if sufficient else None,
                "p10": percentile(values, 0.1) if sufficient and len(values) >= 5 else None,
                "p25": percentile(values, 0.25) if sufficient and len(values) >= 5 else None,
                "p75": percentile(values, 0.75) if sufficient and len(values) >= 5 else None,
                "p90": percentile(values, 0.9) if sufficient and len(values) >= 5 else None,
                "mad": mad(values) if sufficient else None,
                "completeness": min(1.0, len(values) / config.minimum_bin_samples),
                "sufficiency": Sufficiency.SUFFICIENT if sufficient else Sufficiency.INSUFFICIENT,
            }
        )
        start = end
    return bins


def acceleration_interval(
    samples: tuple[Sample, ...], start_speed: float, end_speed: float, config: AnalyticsConfig
) -> dict[str, object]:
    samples = tuple(sorted(samples, key=lambda sample: sample.observed_at))
    points = [(s.observed_at, s.values.get("vehicle.speed")) for s in samples]
    valid = [(at, value) for at, value in points if value is not None]

    def crossing(target: float) -> datetime | None:
        for (a_at, a), (b_at, b) in zip(valid, valid[1:], strict=False):
            gap = (b_at - a_at).total_seconds()
            if a <= target <= b and 0 < gap <= config.maximum_gap_seconds and b != a:
                return a_at + (b_at - a_at) * ((target - a) / (b - a))
        return None

    started, ended = crossing(start_speed), crossing(end_speed)
    # Both boundary crossings alone cannot prove uninterrupted interval coverage.
    interval_points = [
        (at, value) for at, value in valid if started and ended and started <= at <= ended
    ]
    continuous = all(
        0 < (b_at - a_at).total_seconds() <= config.maximum_gap_seconds and b >= a
        for (a_at, a), (b_at, b) in zip(interval_points, interval_points[1:], strict=False)
    )
    if not continuous:
        started = ended = None
    if started is None or ended is None or ended <= started:
        return {
            "start_speed": start_speed,
            "end_speed": end_speed,
            "elapsed_seconds": None,
            "method": "linear_boundary_interpolation",
            "sufficiency": Sufficiency.INSUFFICIENT,
        }
    return {
        "start_speed": start_speed,
        "end_speed": end_speed,
        "elapsed_seconds": (ended - started).total_seconds(),
        "method": "linear_boundary_interpolation",
        "sufficiency": Sufficiency.SUFFICIENT,
    }


SIGNALS = {
    "boost": ("engine.boost_pressure", "Pa"),
    "iat": ("engine.intake_air_temperature", "K"),
    "coolant": ("engine.coolant_temperature", "K"),
    "oil": ("engine.oil_temperature", "K"),
    "fuel": ("fuel.high_pressure", "Pa"),
    "speed": ("vehicle.speed", "m/s"),
    "throttle": ("engine.throttle_position", "%"),
    "acceleration": ("vehicle.acceleration", "m/s^2"),
}


@traced("analytics.pull_metrics")
def pull_profile(pull: PullInput, config: AnalyticsConfig) -> dict[str, object]:
    # Canonical persistence is unique; direct deterministic inputs must also be
    # insensitive to duplicate/reversed observations. Endpoints are event-time based.
    unique = {sample.observed_at: sample for sample in pull.samples}
    pull = replace(pull, samples=tuple(unique[at] for at in sorted(unique)))
    if not pull.samples:
        return {"sufficiency": Sufficiency.INSUFFICIENT, "warnings": ["missing_samples"]}
    derived = []
    for index, sample in enumerate(pull.samples):
        derived_values = dict(sample.values)
        if index:
            previous = pull.samples[index - 1]
            seconds = (sample.observed_at - previous.observed_at).total_seconds()
            if 0 < seconds <= config.maximum_gap_seconds and all(
                "vehicle.speed" in frame.values for frame in (previous, sample)
            ):
                derived_values["vehicle.acceleration"] = (
                    sample.values["vehicle.speed"] - previous.values["vehicle.speed"]
                ) / seconds
        derived.append(replace(sample, values=derived_values))
    original_observations = sum(len(sample.values) for sample in pull.samples)
    pull = replace(pull, samples=tuple(derived))
    low, high = min(s.rpm for s in pull.samples), max(s.rpm for s in pull.samples)
    duration = (pull.samples[-1].observed_at - pull.samples[0].observed_at).total_seconds()
    continuous = all(
        0 < (b.observed_at - a.observed_at).total_seconds() <= config.maximum_gap_seconds
        for a, b in zip(pull.samples, pull.samples[1:], strict=False)
    )
    metrics: dict[str, object] = {}
    curves: dict[str, object] = {}
    for name, (signal, unit) in SIGNALS.items():
        values = [s.values[signal] for s in pull.samples if signal in s.values]
        metrics[name] = (
            None
            if not values
            else {
                "unit": unit,
                "count": len(values),
                "start": values[0],
                "end": values[-1],
                "minimum": min(values),
                "maximum": max(values),
                "median": median(values),
                "mean": sum(values) / len(values),
                "mad": mad(values),
                "delta": values[-1] - values[0],
                "rate_per_second": (values[-1] - values[0]) / duration
                if duration > 0 and continuous and len(values) == len(pull.samples)
                else None,
            }
        )
        curves[name] = bin_statistics(pull.samples, signal, low, high, config) if values else []
    return {
        "sufficiency": Sufficiency.SUFFICIENT
        if pull.completeness >= config.minimum_completeness
        else Sufficiency.LIMITED,
        "source_ids": {"pulls": [pull.id], "sessions": [pull.session_id]},
        "metric_definition": "robust observed pull profile",
        "units": {name: unit for name, (_, unit) in SIGNALS.items()},
        "normalization_method": f"{config.rpm_bin_size}_rpm_half_open_bins",
        "observation_count": original_observations,
        "sample_frame_count": len(pull.samples),
        "common_window_seconds": duration if continuous else None,
        "acceleration_method": "adjacent_observed_speed_difference_over_elapsed_time",
        "pull_count": 1,
        "session_count": 1,
        "comparable_range": [low, high],
        "data_quality_flags": list(pull.quality_flags),
        "completeness": pull.completeness,
        "calculation_version": CALCULATION_VERSION,
        "baseline_source": None,
        "evidence_quality": "observed",
        "metrics": metrics,
        "curves": curves,
        "acceleration_intervals": [
            acceleration_interval(pull.samples, a / 3.6, b / 3.6, config)
            for a, b in config.speed_intervals_kmh
        ],
        "event_ids": list(pull.event_ids),
        "event_markers": [
            marker for marker in pull.event_markers if low <= float(str(marker["rpm"])) <= high
        ],
    }


@traced("analytics.aggregation")
def compare_pulls(pulls: list[PullInput], config: AnalyticsConfig) -> dict[str, object]:
    if not 2 <= len(pulls) <= config.maximum_pulls:
        raise ValueError("pull comparison requires 2..maximum_pulls inputs")
    comparisons = [compare_context(pulls[0], pull, config) for pull in pulls[1:]]
    accepted = all(item.accepted for item in comparisons)
    populated = [pull for pull in pulls if pull.samples]
    common_low = max((min(s.rpm for s in pull.samples) for pull in populated), default=0)
    common_high = min((max(s.rpm for s in pull.samples) for pull in populated), default=0)
    profiles = [
        pull_profile(
            replace(
                pull, samples=tuple(s for s in pull.samples if common_low <= s.rpm < common_high)
            ),
            config,
        )
        for pull in pulls
    ]
    deltas: dict[str, object] = {}
    for metric in SIGNALS:
        values = [
            cast(dict[str, object], profile.get("metrics", {})).get(metric) for profile in profiles
        ]
        medians = [item.get("median") if isinstance(item, dict) else None for item in values]
        baseline = medians[0]
        deltas[metric] = [
            {
                "absolute": None
                if not accepted or value is None or baseline is None
                else value - baseline,
                "relative": relative_delta(value, baseline) if accepted else None,
            }
            for value in medians
        ]
    reasons = sorted({reason for comparison in comparisons for reason in comparison.reasons})
    return {
        "sufficiency": Sufficiency.SUFFICIENT if accepted else Sufficiency.INSUFFICIENT,
        "source_ids": {
            "pulls": [pull.id for pull in pulls],
            "sessions": sorted({pull.session_id for pull in pulls}),
        },
        "comparability": [asdict(item) for item in comparisons],
        "common_rpm_range": [common_low, common_high] if common_high > common_low else None,
        "metric_deltas": deltas,
        "profiles": profiles,
        "limitations": reasons,
        "calculation_version": CALCULATION_VERSION,
        "configuration_hash": config.configuration_hash,
    }


def comparable_groups(pulls: list[PullInput], config: AnalyticsConfig) -> list[list[PullInput]]:
    groups: list[list[PullInput]] = []
    for pull in sorted(pulls, key=lambda item: (item.started_at, item.id)):
        if not pull.samples or pull.completeness < config.minimum_completeness:
            continue
        for group in groups:
            if all(compare_context(member, pull, config).accepted for member in group):
                group.append(pull)
                break
        else:
            groups.append([pull])
    return groups


@traced("analytics.repeated_aggregation")
def repeated_pulls(pulls: list[PullInput], config: AnalyticsConfig) -> dict[str, object]:
    ordered = sorted(pulls, key=lambda pull: (pull.started_at, pull.id))
    comparison = compare_pulls(ordered, config) if len(ordered) >= 2 else None
    rows: list[dict[str, object]] = []
    profiles = cast(list[dict[str, object]], comparison["profiles"]) if comparison else []
    for index, pull in enumerate(ordered, 1):
        full_profile = pull_profile(pull, config)
        profile = profiles[index - 1] if profiles else full_profile
        endpoint_metrics = full_profile.get("metrics", {})
        metrics = profile.get("metrics", {})

        def value(metric: str, field_name: str, source: object = metrics) -> float | None:
            item = source.get(metric) if isinstance(source, dict) else None
            result = item.get(field_name) if isinstance(item, dict) else None
            return float(result) if isinstance(result, (float, int)) else None

        rows.append(
            {
                "index": index,
                "pull_id": pull.id,
                "start_iat": value("iat", "start", endpoint_metrics),
                "end_iat": value("iat", "end", endpoint_metrics),
                "iat_delta": value("iat", "delta", endpoint_metrics),
                "median_boost": value("boost", "median"),
                "minimum_fuel_pressure": value("fuel", "minimum"),
                "median_speed": value("speed", "median"),
                "normalized_acceleration": value("acceleration", "median"),
                "common_window_seconds": profile.get("common_window_seconds"),
                "start_oil": value("oil", "start", endpoint_metrics),
                "end_oil": value("oil", "end", endpoint_metrics),
                "start_coolant": value("coolant", "start", endpoint_metrics),
                "end_coolant": value("coolant", "end", endpoint_metrics),
                "throttle_coverage": pull.completeness,
                "event_count": len(pull.event_ids),
            }
        )

    def series(key: str) -> list[float]:
        values = [row.get(key) for row in rows]
        return [float(item) for item in values if isinstance(item, (int, float))]

    repeatability = {
        key: {
            "median": median(values),
            "mad": mad(values),
            "iqr": iqr(values),
            "coefficient_of_variation": coefficient_of_variation(values),
        }
        for key in ("start_iat", "median_boost", "minimum_fuel_pressure", "median_speed")
        if (values := series(key))
    }
    starts = series("start_iat")
    thermal_increase = (
        median([b - a for a, b in zip(starts, starts[1:], strict=False)])
        if len(starts) > 1
        else None
    )
    paired = [
        (row["start_iat"], row["median_speed"])
        for row in rows
        if isinstance(row["start_iat"], (int, float))
        and isinstance(row["median_speed"], (int, float))
    ]
    comparable = comparison is not None and comparison["sufficiency"] == Sufficiency.SUFFICIENT
    rho, correlation_state = (
        spearman(
            [cast(float, x) for x, _ in paired],
            [cast(float, y) for _, y in paired],
            config.minimum_correlation_samples,
        )
        if comparable
        else (None, Sufficiency.INSUFFICIENT)
    )
    if not comparable:
        repeatability = {}
        thermal_increase = None
    return {
        "sufficiency": Sufficiency.SUFFICIENT
        if comparison and comparison["sufficiency"] == Sufficiency.SUFFICIENT
        else Sufficiency.INSUFFICIENT,
        "sequence": rows,
        "comparison": comparison,
        "repeatability": repeatability,
        "thermal": {
            "median_start_iat_increase": thermal_increase,
            "unit": "K",
            "between_pull_recovery": [
                {
                    "from_pull": a.id,
                    "to_pull": b.id,
                    "elapsed_seconds": (b.started_at - a.ended_at).total_seconds(),
                    "iat_delta": cast(float, rows[index + 1]["start_iat"])
                    - cast(float, rows[index]["end_iat"])
                    if comparable
                    and rows[index + 1]["start_iat"] is not None
                    and rows[index]["end_iat"] is not None
                    else None,
                    "time_to_threshold_seconds": None,
                    "limitation": "observed endpoints only; between-pull trajectory not loaded",
                }
                for index, (a, b) in enumerate(zip(ordered, ordered[1:], strict=False))
                if a.session_id == b.session_id and b.started_at >= a.ended_at
            ],
        },
        "associations": [
            {
                "x": "start_iat",
                "y": "median_speed",
                "method": "spearman",
                "coefficient": rho,
                "sample_size": len(paired) if comparable else 0,
                "sufficiency": correlation_state,
                "interpretation": "observed association; not causal",
            }
        ],
        "calculation_version": CALCULATION_VERSION,
        "configuration_hash": config.configuration_hash,
    }


@traced("analytics.baseline_build")
def baseline(pulls: list[PullInput], config: AnalyticsConfig) -> dict[str, object]:
    eligible = [pull for pull in pulls if pull.completeness >= config.minimum_completeness]
    sessions = sorted({pull.session_id for pull in eligible if pull.samples})
    eligible = [pull for pull in eligible if pull.samples]
    configurations = {pull.configuration_id for pull in eligible}
    if len({pull.vehicle_id for pull in eligible}) > 1:
        return {"sufficiency": Sufficiency.INSUFFICIENT, "limitations": ["mixed_vehicle"]}
    if eligible and (len(configurations) != 1 or None in configurations):
        return {"sufficiency": Sufficiency.INSUFFICIENT, "limitations": ["mixed_configuration"]}
    groups = comparable_groups(eligible, config)
    eligible = max(
        groups, key=lambda group: (len({p.session_id for p in group}), len(group)), default=[]
    )
    sessions = sorted({pull.session_id for pull in eligible})
    state = (
        Sufficiency.SUFFICIENT
        if len(sessions) >= config.minimum_baseline_sessions
        else Sufficiency.INSUFFICIENT
    )
    envelopes: dict[str, list[dict[str, object]]] = {}
    if eligible:
        low = max(min(s.rpm for s in pull.samples) for pull in eligible)
        high = min(max(s.rpm for s in pull.samples) for pull in eligible)
        for name, (signal, unit) in SIGNALS.items():
            # Validate within each pull first. Historical session intervals are
            # unrelated clocks, never a continuous acquisition interval.
            curves = [
                (pull, bin_statistics(pull.samples, signal, low, high, config)) for pull in eligible
            ]
            envelope = []
            for index in range(len(curves[0][1])):
                contributors = [
                    (pull, curve[index])
                    for pull, curve in curves
                    if curve[index]["sufficiency"] == Sufficiency.SUFFICIENT
                ]
                centers = [cast(float, item["median"]) for _, item in contributors]
                session_count = len({pull.session_id for pull, _ in contributors})
                sufficient = session_count >= config.minimum_baseline_sessions
                envelope.append(
                    {
                        "rpm_start": curves[0][1][index]["rpm_start"],
                        "rpm_end": curves[0][1][index]["rpm_end"],
                        "count": sum(cast(int, item["count"]) for _, item in contributors),
                        "pull_count": len(contributors),
                        "session_count": session_count,
                        "unit": unit,
                        "median": median(centers) if sufficient else None,
                        "mad": mad(centers) if sufficient else None,
                        "p10": percentile(centers, 0.1)
                        if sufficient and len(centers) >= 5
                        else None,
                        "p25": percentile(centers, 0.25)
                        if sufficient and len(centers) >= 5
                        else None,
                        "p75": percentile(centers, 0.75)
                        if sufficient and len(centers) >= 5
                        else None,
                        "p90": percentile(centers, 0.9)
                        if sufficient and len(centers) >= 5
                        else None,
                        "sufficiency": Sufficiency.SUFFICIENT
                        if sufficient
                        else Sufficiency.INSUFFICIENT,
                    }
                )
            envelopes[name] = envelope
    current: dict[str, object] | None = None
    sufficient_bins = any(
        item.get("median") is not None for curve in envelopes.values() for item in curve
    )
    if state == Sufficiency.SUFFICIENT and not sufficient_bins:
        state = Sufficiency.INSUFFICIENT
    if eligible and state == Sufficiency.SUFFICIENT:
        latest = max(eligible, key=lambda pull: (pull.started_at, pull.id))
        observed = bin_statistics(latest.samples, "engine.boost_pressure", low, high, config)
        comparison_bins = []
        for reference, measured in zip(envelopes.get("boost", []), observed, strict=True):
            reference_value, measured_value = reference.get("median"), measured.get("median")
            comparison_bins.append(
                {
                    "rpm_start": reference["rpm_start"],
                    "rpm_end": reference["rpm_end"],
                    "observed": measured_value,
                    "historical_median": reference_value,
                    "absolute_delta": measured_value - reference_value
                    if isinstance(measured_value, (float, int))
                    and isinstance(reference_value, (float, int))
                    else None,
                    "unit": "Pa",
                }
            )
        current = {
            "pull_id": latest.id,
            "session_id": latest.session_id,
            "included_in_history": True,
            "boost_bins": comparison_bins,
        }
    return {
        "sufficiency": state,
        "source_ids": {"pulls": [p.id for p in eligible], "sessions": sessions},
        "vehicle_id": eligible[0].vehicle_id if eligible else None,
        "configuration_id": eligible[0].configuration_id if eligible else None,
        "session_count": len(sessions),
        "pull_count": len(eligible),
        "date_range": [min(p.started_at for p in eligible), max(p.ended_at for p in eligible)]
        if eligible
        else None,
        "envelopes": envelopes,
        "current_pull_comparison": current,
        "excluded_pull_count": len(pulls) - len(eligible),
        "limitations": []
        if state == Sufficiency.SUFFICIENT
        else ["insufficient_same_configuration_sessions"],
        "calculation_version": CALCULATION_VERSION,
        "configuration_hash": config.configuration_hash,
    }


@traced("analytics.configuration_comparison")
def configuration_comparison(
    before: list[PullInput], after: list[PullInput], config: AnalyticsConfig
) -> dict[str, object]:
    reasons: list[str] = []
    common: tuple[float, float] | None = None
    contexts: list[Comparability] = []
    if not before or not after:
        reasons.append("missing_configuration_history")
    elif {p.vehicle_id for p in before + after} != {before[0].vehicle_id}:
        reasons.append("different_vehicle")
    elif {p.configuration_id for p in before} == {p.configuration_id for p in after}:
        reasons.append("same_configuration")
    if before and after and not reasons:
        if max(p.ended_at for p in before) >= min(p.started_at for p in after):
            reasons.append("overlapping_or_uncertain_configuration_timeline")
        # Only the explicitly selected before/after operation may compare different
        # configuration identities. All other operating-context guards still apply.
        contexts = [
            compare_context(left, replace(right, configuration_id=left.configuration_id), config)
            for left in before
            for right in after
        ]
        reasons.extend(reason for item in contexts for reason in item.reasons)
        if any(not item.accepted for item in contexts):
            reasons.append("incomparable_operating_context")
        if all(p.samples for p in before + after):
            low = max(min(s.rpm for s in p.samples) for p in before + after)
            high = min(max(s.rpm for s in p.samples) for p in before + after)
            if high - low < config.minimum_rpm_overlap:
                reasons.append("insufficient_rpm_overlap")
            else:
                common = (low, high)

    def clip(pulls: list[PullInput]) -> list[PullInput]:
        return (
            [
                replace(p, samples=tuple(s for s in p.samples if common[0] <= s.rpm < common[1]))
                for p in pulls
            ]
            if common
            else pulls
        )

    before_selected, after_selected = clip(before), clip(after)
    before_baseline, after_baseline = (
        baseline(before_selected, config),
        baseline(after_selected, config),
    )
    sufficient = (
        not reasons
        and before_baseline.get("sufficiency") == Sufficiency.SUFFICIENT
        and after_baseline.get("sufficiency") == Sufficiency.SUFFICIENT
    )

    def metric_center(pulls: list[PullInput], signal: str) -> float | None:
        centers = [
            median([s.values[signal] for s in p.samples if signal in s.values]) for p in pulls
        ]
        return median([value for value in centers if value is not None])

    deltas = {}
    for metric, (signal, unit) in SIGNALS.items():
        left, right = metric_center(before_selected, signal), metric_center(after_selected, signal)
        deltas[metric] = {
            "before": left,
            "after": right,
            "unit": unit,
            "absolute": right - left
            if sufficient and left is not None and right is not None
            else None,
            "relative": relative_delta(right, left) if sufficient else None,
        }
    return {
        "sufficiency": Sufficiency.SUFFICIENT if sufficient else Sufficiency.INSUFFICIENT,
        "language": "Observed before/after difference; association is not root-cause diagnosis.",
        "before": before_baseline,
        "after": after_baseline,
        "sample_sizes": {"before": len(before), "after": len(after)},
        "common_rpm_range": common,
        "comparability": [asdict(item) for item in contexts],
        "metric_deltas": deltas,
        "limitations": sorted(set(reasons)),
        "calculation_version": CALCULATION_VERSION,
        "configuration_hash": config.configuration_hash,
    }


@traced("analytics.trend_aggregation")
def trend(pulls: list[PullInput], metric: str, config: AnalyticsConfig) -> dict[str, object]:
    segments: dict[str, list[dict[str, object]]] = {}
    segment_states: dict[str, dict[str, object]] = {}
    for group in comparable_groups(pulls, config):
        key = group[0].configuration_id or "unassigned"
        sessions = {p.session_id for p in group}
        enough = key != "unassigned" and len(sessions) >= config.minimum_baseline_sessions
        if not enough:
            segment_states[key] = {
                "sufficiency": Sufficiency.INSUFFICIENT,
                "session_count": len(sessions),
            }
            continue
        low = max(min(s.rpm for s in p.samples) for p in group)
        high = min(max(s.rpm for s in p.samples) for p in group)
        for pull in group:
            profile = pull_profile(
                replace(pull, samples=tuple(s for s in pull.samples if low <= s.rpm < high)), config
            )
            item = cast(dict[str, object], profile.get("metrics", {})).get(metric)
            if isinstance(item, dict) and item.get("median") is not None:
                segments.setdefault(key, []).append(
                    {
                        "observed_at": pull.started_at,
                        "value": item["median"],
                        "unit": item["unit"],
                        "pull_id": pull.id,
                        "session_id": pull.session_id,
                        "comparable_rpm_range": [low, high],
                    }
                )
        segment_states[key] = {
            "sufficiency": Sufficiency.SUFFICIENT,
            "session_count": len(sessions),
        }
    count = sum(len(points) for points in segments.values())
    return {
        "sufficiency": Sufficiency.SUFFICIENT if count >= 3 else Sufficiency.INSUFFICIENT,
        "metric": metric,
        "segments_by_configuration": segments,
        "segment_sufficiency": segment_states,
        "point_count": count,
        "excluded_pull_count": len(pulls) - count,
        "limitations": [] if count >= 3 else ["insufficient_comparable_history"],
        "calculation_version": CALCULATION_VERSION,
        "configuration_hash": config.configuration_hash,
    }
