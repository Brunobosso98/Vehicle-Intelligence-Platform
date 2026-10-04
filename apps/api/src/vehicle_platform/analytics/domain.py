import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import cast


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

    def __post_init__(self) -> None:
        if not 100 <= self.rpm_bin_size <= 1000:
            raise ValueError("rpm_bin_size must be between 100 and 1000")
        if not 2 <= self.minimum_bin_samples <= 100:
            raise ValueError("minimum_bin_samples must be between 2 and 100")
        if not 0 < self.maximum_gap_seconds <= 5:
            raise ValueError("maximum_gap_seconds must be in (0, 5]")
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
    return (numerator / denominator if denominator else None), Sufficiency.SUFFICIENT


@dataclass(frozen=True)
class Comparability:
    overall: float
    dimensions: dict[str, float]
    accepted: bool
    reasons: tuple[str, ...]
    common_rpm_range: tuple[float, float] | None


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


def bin_statistics(
    samples: tuple[Sample, ...], signal: str, low: float, high: float, config: AnalyticsConfig
) -> list[dict[str, object]]:
    bins: list[dict[str, object]] = []
    start = math.floor(low / config.rpm_bin_size) * config.rpm_bin_size
    while start < high:
        end = start + config.rpm_bin_size
        selected = [s for s in samples if start <= s.rpm < end and signal in s.values]
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
    points = [(s.observed_at, s.values.get("vehicle.speed")) for s in samples]
    valid = [(at, value) for at, value in points if value is not None]

    def crossing(target: float) -> datetime | None:
        for (a_at, a), (b_at, b) in zip(valid, valid[1:], strict=False):
            gap = (b_at - a_at).total_seconds()
            if a <= target <= b and gap <= config.maximum_gap_seconds and b != a:
                return a_at + (b_at - a_at) * ((target - a) / (b - a))
        return None

    started, ended = crossing(start_speed), crossing(end_speed)
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
}


def pull_profile(pull: PullInput, config: AnalyticsConfig) -> dict[str, object]:
    if not pull.samples:
        return {"sufficiency": Sufficiency.INSUFFICIENT, "warnings": ["missing_samples"]}
    low, high = min(s.rpm for s in pull.samples), max(s.rpm for s in pull.samples)
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
        "observation_count": len(pull.samples),
        "pull_count": 1,
        "session_count": 1,
        "comparable_range": [low, high],
        "data_quality_flags": list(pull.quality_flags),
        "completeness": pull.completeness,
        "calculation_version": "phase5-analytics-v1",
        "baseline_source": None,
        "evidence_quality": "observed",
        "metrics": metrics,
        "curves": curves,
        "acceleration_intervals": [
            acceleration_interval(pull.samples, a / 3.6, b / 3.6, config)
            for a, b in ((60, 100), (80, 120), (100, 150))
        ],
        "event_ids": list(pull.event_ids),
    }


def compare_pulls(pulls: list[PullInput], config: AnalyticsConfig) -> dict[str, object]:
    if not 2 <= len(pulls) <= config.maximum_pulls:
        raise ValueError("pull comparison requires 2..maximum_pulls inputs")
    comparisons = [compare_context(pulls[0], pull, config) for pull in pulls[1:]]
    accepted = all(item.accepted for item in comparisons)
    common_low = max(min(s.rpm for s in pull.samples) for pull in pulls if pull.samples)
    common_high = min(max(s.rpm for s in pull.samples) for pull in pulls if pull.samples)
    profiles = [pull_profile(pull, config) for pull in pulls]
    deltas: dict[str, object] = {}
    for metric in SIGNALS:
        values = [
            cast(dict[str, object], profile.get("metrics", {})).get(metric) for profile in profiles
        ]
        medians = [item.get("median") if isinstance(item, dict) else None for item in values]
        baseline = medians[0]
        deltas[metric] = [
            {
                "absolute": None if value is None or baseline is None else value - baseline,
                "relative": relative_delta(value, baseline),
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
        "calculation_version": "phase5-analytics-v1",
        "configuration_hash": config.configuration_hash,
    }


def repeated_pulls(pulls: list[PullInput], config: AnalyticsConfig) -> dict[str, object]:
    ordered = sorted(pulls, key=lambda pull: (pull.started_at, pull.id))
    comparison = compare_pulls(ordered, config) if len(ordered) >= 2 else None
    rows: list[dict[str, object]] = []
    for index, pull in enumerate(ordered, 1):
        profile = pull_profile(pull, config)
        metrics = profile.get("metrics", {})

        def value(metric: str, field_name: str, source: object = metrics) -> float | None:
            item = source.get(metric) if isinstance(source, dict) else None
            result = item.get(field_name) if isinstance(item, dict) else None
            return float(result) if isinstance(result, (float, int)) else None

        rows.append(
            {
                "index": index,
                "pull_id": pull.id,
                "start_iat": value("iat", "start"),
                "end_iat": value("iat", "end"),
                "iat_delta": value("iat", "delta"),
                "median_boost": value("boost", "median"),
                "minimum_fuel_pressure": value("fuel", "minimum"),
                "median_speed": value("speed", "median"),
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
    rho, correlation_state = spearman(
        starts, series("median_speed"), config.minimum_correlation_samples
    )
    return {
        "sufficiency": Sufficiency.SUFFICIENT
        if comparison and comparison["sufficiency"] == Sufficiency.SUFFICIENT
        else Sufficiency.INSUFFICIENT,
        "sequence": rows,
        "comparison": comparison,
        "repeatability": repeatability,
        "thermal": {"median_start_iat_increase": thermal_increase, "unit": "K"},
        "associations": [
            {
                "x": "start_iat",
                "y": "median_speed",
                "method": "spearman",
                "coefficient": rho,
                "sample_size": min(len(starts), len(series("median_speed"))),
                "sufficiency": correlation_state,
                "interpretation": "observed association; not causal",
            }
        ],
        "calculation_version": "phase5-analytics-v1",
        "configuration_hash": config.configuration_hash,
    }


def baseline(pulls: list[PullInput], config: AnalyticsConfig) -> dict[str, object]:
    eligible = [pull for pull in pulls if pull.completeness >= config.minimum_completeness]
    sessions = sorted({pull.session_id for pull in eligible})
    configurations = {pull.configuration_id for pull in eligible}
    if len(configurations) != 1:
        return {"sufficiency": Sufficiency.INSUFFICIENT, "limitations": ["mixed_configuration"]}
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
            combined: list[Sample] = [sample for pull in eligible for sample in pull.samples]
            curve = bin_statistics(tuple(combined), signal, low, high, config)
            envelopes[name] = [{**item, "unit": unit} for item in curve]
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
        "excluded_pull_count": len(pulls) - len(eligible),
        "limitations": []
        if state == Sufficiency.SUFFICIENT
        else ["insufficient_same_configuration_sessions"],
        "calculation_version": "phase5-analytics-v1",
        "configuration_hash": config.configuration_hash,
    }


def configuration_comparison(
    before: list[PullInput], after: list[PullInput], config: AnalyticsConfig
) -> dict[str, object]:
    before_baseline, after_baseline = baseline(before, config), baseline(after, config)
    sufficient = (
        before_baseline.get("sufficiency") == Sufficiency.SUFFICIENT
        and after_baseline.get("sufficiency") == Sufficiency.SUFFICIENT
    )
    return {
        "sufficiency": Sufficiency.SUFFICIENT if sufficient else Sufficiency.INSUFFICIENT,
        "language": "Observed before/after difference; association is not root-cause diagnosis.",
        "before": before_baseline,
        "after": after_baseline,
        "sample_sizes": {"before": len(before), "after": len(after)},
        "calculation_version": "phase5-analytics-v1",
        "configuration_hash": config.configuration_hash,
    }


def trend(pulls: list[PullInput], metric: str, config: AnalyticsConfig) -> dict[str, object]:
    segments: dict[str, list[dict[str, object]]] = {}
    for pull in sorted(pulls, key=lambda item: (item.started_at, item.id)):
        profile = pull_profile(pull, config)
        item = cast(dict[str, object], profile.get("metrics", {})).get(metric)
        if isinstance(item, dict) and item.get("median") is not None:
            segments.setdefault(pull.configuration_id or "unassigned", []).append(
                {
                    "observed_at": pull.started_at,
                    "value": item["median"],
                    "unit": item["unit"],
                    "pull_id": pull.id,
                }
            )
    count = sum(len(points) for points in segments.values())
    return {
        "sufficiency": Sufficiency.SUFFICIENT if count >= 3 else Sufficiency.INSUFFICIENT,
        "metric": metric,
        "segments_by_configuration": segments,
        "point_count": count,
        "limitations": [] if count >= 3 else ["insufficient_comparable_history"],
        "calculation_version": "phase5-analytics-v1",
        "configuration_hash": config.configuration_hash,
    }
