from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import timedelta
from statistics import median
from typing import Protocol

from vehicle_platform.analysis.domain import AlignedFrame
from vehicle_platform.events.domain import (
    BaselineType,
    DetectorResult,
    DetectorState,
    EventCandidate,
    EventCategory,
    EventProfile,
    PullWindow,
    Severity,
)


def median_absolute_deviation(values: Sequence[float]) -> float | None:
    if not values:
        return None
    center = median(values)
    return median(abs(value - center) for value in values)


def comparable_pull_score(left: PullWindow, right: PullWindow) -> float:
    """Deterministic score from duration and overlapping RPM range."""
    lf, rf = left.frames, right.frames
    if not lf or not rf:
        return 0.0
    duration_ratio = min(len(lf), len(rf)) / max(len(lf), len(rf))

    def rpm_range(frames: tuple[object, ...]) -> tuple[float, float] | None:
        values = [f.values.get("engine.rpm") for f in frames if isinstance(f, AlignedFrame)]
        present = [value for value in values if value is not None]
        return (min(present), max(present)) if present else None

    lr, rr = rpm_range(lf), rpm_range(rf)
    if lr is None or rr is None:
        return round(duration_ratio * 0.4, 3)
    overlap = max(0.0, min(lr[1], rr[1]) - max(lr[0], rr[0]))
    span = max(lr[1], rr[1]) - min(lr[0], rr[0])
    return round(0.4 * duration_ratio + 0.6 * (overlap / span if span else 1.0), 3)


def score_severity(magnitude_ratio: float, duration_seconds: float) -> Severity:
    score = max(0.0, magnitude_ratio) * min(2.0, max(0.5, duration_seconds / 2))
    if score >= 0.5:
        return Severity.HIGH
    if score >= 0.25:
        return Severity.MODERATE
    return Severity.LOW if score >= 0.1 else Severity.INFO


def score_confidence(completeness: float, baseline_quality: float, strength: float) -> float:
    """Heuristic evidence score, deliberately not a calibrated probability."""
    return round(
        max(0.0, min(0.99, 0.2 + 0.35 * completeness + 0.25 * baseline_quality + 0.2 * strength)), 3
    )


class EventDetector(Protocol):
    name: str
    version: str

    def detect(
        self, frames: Sequence[AlignedFrame], pulls: Sequence[PullWindow]
    ) -> DetectorResult: ...


class BaseDetector:
    name = "base"
    version = "1.0.0"

    def __init__(self, profile: EventProfile) -> None:
        self.profile = profile

    def candidate(
        self,
        event_type: str,
        category: EventCategory,
        frames: Sequence[AlignedFrame],
        *,
        severity: Severity,
        confidence: float,
        baseline: BaselineType,
        reference: dict[str, object],
        evidence: dict[str, object],
        pull_index: int | None = None,
        flags: tuple[str, ...] = (),
    ) -> EventCandidate:
        return EventCandidate(
            event_type,
            category,
            frames[0].observed_at,
            frames[-1].observed_at,
            severity,
            confidence,
            self.name,
            self.version,
            self.profile.configuration_hash,
            baseline,
            reference,
            evidence,
            flags,
            pull_index,
        )


def _series(frames: Sequence[AlignedFrame], signal: str) -> list[float]:
    return [value for frame in frames if (value := frame.values.get(signal)) is not None]


def _contiguous_runs(
    frames: Sequence[AlignedFrame], predicate: Callable[[AlignedFrame], bool], max_step: float
) -> list[list[AlignedFrame]]:
    runs: list[list[AlignedFrame]] = []
    current: list[AlignedFrame] = []
    for frame in frames:
        contiguous = not current or (
            not frame.gap_before
            and (frame.observed_at - current[-1].observed_at).total_seconds() <= max_step
        )
        if predicate(frame) and contiguous:
            current.append(frame)
        else:
            if current:
                runs.append(current)
            current = [frame] if predicate(frame) else []
    if current:
        runs.append(current)
    return runs


class PullBehaviorDetector(BaseDetector):
    name = "pull-behavior-detector"

    def detect(self, frames: Sequence[AlignedFrame], pulls: Sequence[PullWindow]) -> DetectorResult:
        events: list[EventCandidate] = []
        prior_boost: list[float] = []
        prior_iat: list[float] = []
        for index, pull in enumerate(pulls):
            pf = [f for f in pull.frames if isinstance(f, AlignedFrame)]
            boost, iat, fuel = (
                _series(pf, "engine.boost_pressure"),
                _series(pf, "engine.intake_air_temperature"),
                _series(pf, "fuel.high_pressure"),
            )
            duration = (pull.ended_at - pull.started_at).total_seconds()
            comparable = [p for p in pulls[:index] if comparable_pull_score(p, pull) >= 0.7]
            comparable_count = len(comparable)
            if boost:
                observed = median(boost)
                reference = median(prior_boost) if comparable_count and prior_boost else None
                if reference and observed <= reference * (1 - self.profile.boost_drop_relative):
                    ratio = (reference - observed) / reference
                    events.append(
                        self.candidate(
                            "boost_drop",
                            EventCategory.PERFORMANCE,
                            pf,
                            severity=score_severity(ratio, duration),
                            confidence=score_confidence(
                                1,
                                min(1, comparable_count / 2),
                                min(1, ratio / self.profile.boost_drop_relative),
                            ),
                            baseline=BaselineType.SAME_SESSION_PULLS,
                            reference={
                                "pull_count": comparable_count,
                                "median_boost_pa": reference,
                            },
                            evidence={
                                "signal": "engine.boost_pressure",
                                "observed_median_pa": observed,
                                "reference_median_pa": reference,
                                "relative_delta": round(-ratio, 4),
                                "duration_seconds": duration,
                            },
                            pull_index=index,
                        )
                    )
                sustained = [
                    f
                    for f in pf
                    if (f.values.get("engine.boost_pressure") or 0)
                    > self.profile.boost_overshoot_pa
                    and (f.values.get("engine.throttle_position") or 0)
                    >= self.profile.high_load_throttle_pct
                ]
                if (
                    len(sustained) >= 2
                    and (sustained[-1].observed_at - sustained[0].observed_at).total_seconds()
                    >= self.profile.min_duration_seconds
                ):
                    magnitude = (
                        max(boost) - self.profile.boost_overshoot_pa
                    ) / self.profile.boost_overshoot_pa
                    events.append(
                        self.candidate(
                            "boost_overshoot",
                            EventCategory.PERFORMANCE,
                            sustained,
                            severity=score_severity(magnitude, duration),
                            confidence=score_confidence(1, 0.6, min(1, magnitude * 4)),
                            baseline=BaselineType.PROFILE_THRESHOLD,
                            reference={"threshold_pa": self.profile.boost_overshoot_pa},
                            evidence={
                                "signal": "engine.boost_pressure",
                                "peak_pa": max(boost),
                                "duration_seconds": (
                                    sustained[-1].observed_at - sustained[0].observed_at
                                ).total_seconds(),
                            },
                            pull_index=index,
                        )
                    )
                prior_boost.append(observed)
            if len(iat) >= 2:
                delta = iat[-1] - iat[0]
                repeated = (
                    prior_iat
                    and iat[0] - median(prior_iat) >= self.profile.repeated_pull_iat_rise_k
                )
                if delta >= self.profile.iat_rise_k or repeated:
                    events.append(
                        self.candidate(
                            "iat_rise",
                            EventCategory.THERMAL,
                            pf,
                            severity=score_severity(
                                max(delta, iat[0] - median(prior_iat) if prior_iat else 0) / 20,
                                duration,
                            ),
                            confidence=score_confidence(
                                1,
                                0.8 if prior_iat else 0.5,
                                min(1, max(delta, 0) / self.profile.iat_rise_k),
                            ),
                            baseline=BaselineType.SAME_SESSION_PULLS
                            if repeated
                            else BaselineType.PROFILE_THRESHOLD,
                            reference={"prior_pull_start_median_k": median(prior_iat)}
                            if prior_iat
                            else {"delta_threshold_k": self.profile.iat_rise_k},
                            evidence={
                                "signal": "engine.intake_air_temperature",
                                "start_k": iat[0],
                                "end_k": iat[-1],
                                "delta_k": delta,
                            },
                            pull_index=index,
                        )
                    )
                prior_iat.append(iat[0])
            if len(fuel) >= 2:
                start = median(fuel[: max(2, len(fuel) // 4)])
                minimum = min(fuel[len(fuel) // 3 :])
                ratio = (start - minimum) / start if start else 0
                if ratio >= self.profile.fuel_drop_relative:
                    events.append(
                        self.candidate(
                            "fuel_pressure_drop",
                            EventCategory.FUEL,
                            pf,
                            severity=score_severity(ratio, duration),
                            confidence=score_confidence(
                                1, 0.6, min(1, ratio / self.profile.fuel_drop_relative)
                            ),
                            baseline=BaselineType.PROFILE_THRESHOLD,
                            reference={"relative_drop_threshold": self.profile.fuel_drop_relative},
                            evidence={
                                "signal": "fuel.high_pressure",
                                "starting_pressure_pa": start,
                                "minimum_pressure_pa": minimum,
                                "relative_drop": round(ratio, 4),
                                "duration_seconds": duration,
                            },
                            pull_index=index,
                        )
                    )
            throttles = _series(pf, "engine.throttle_position")
            if len(throttles) >= 3:
                peak = max(throttles[:-1])
                low = min(throttles[1:])
                if (
                    peak >= self.profile.high_load_throttle_pct
                    and peak - low >= self.profile.throttle_closure_delta_pct
                ):
                    events.append(
                        self.candidate(
                            "unexpected_throttle_closure",
                            EventCategory.CONTROL_BEHAVIOR,
                            pf,
                            severity=score_severity((peak - low) / 100, duration),
                            confidence=score_confidence(1, 0.4, 0.8),
                            baseline=BaselineType.PROFILE_THRESHOLD,
                            reference={
                                "closure_delta_pct": self.profile.throttle_closure_delta_pct
                            },
                            evidence={
                                "signal": "engine.throttle_position",
                                "peak_pct": peak,
                                "minimum_pct": low,
                                "delta_pct": peak - low,
                                "accelerator_signal_available": False,
                            },
                            pull_index=index,
                            flags=("missing_accelerator_pedal",),
                        )
                    )
        state = (
            DetectorState.EVENT_DETECTED
            if events
            else (DetectorState.INSUFFICIENT_DATA if not pulls else DetectorState.NO_EVENT)
        )
        return DetectorResult(self.name, state, tuple(events))


class TemperatureDetector(BaseDetector):
    name = "temperature-threshold-detector"

    def detect(self, frames: Sequence[AlignedFrame], pulls: Sequence[PullWindow]) -> DetectorResult:
        events: list[EventCandidate] = []
        definitions = (
            (
                "engine.intake_air_temperature",
                "intake_temperature_high",
                self.profile.intake_temperature_high_k,
            ),
            ("engine.oil_temperature", "oil_temperature_high", self.profile.oil_temperature_high_k),
            (
                "engine.coolant_temperature",
                "coolant_temperature_high",
                self.profile.coolant_temperature_high_k,
            ),
        )
        for signal, event_type, threshold in definitions:
            active = [f for f in frames if (f.values.get(signal) or float("-inf")) >= threshold]
            if (
                len(active) >= 2
                and (active[-1].observed_at - active[0].observed_at).total_seconds()
                >= self.profile.min_duration_seconds
            ):
                peak = max(_series(active, signal))
                events.append(
                    self.candidate(
                        event_type,
                        EventCategory.THERMAL,
                        active,
                        severity=score_severity(
                            (peak - threshold) / 20,
                            (active[-1].observed_at - active[0].observed_at).total_seconds(),
                        ),
                        confidence=score_confidence(1, 0.7, 0.8),
                        baseline=BaselineType.PROFILE_THRESHOLD,
                        reference={"threshold_k": threshold, "profile": self.profile.name},
                        evidence={"signal": signal, "peak_k": peak, "heuristic_threshold": True},
                    )
                )
        return DetectorResult(
            self.name,
            DetectorState.EVENT_DETECTED if events else DetectorState.NO_EVENT,
            tuple(events),
        )


class QualityDetector(BaseDetector):
    name = "telemetry-quality-detector"
    watched = (
        "engine.rpm",
        "vehicle.speed",
        "engine.throttle_position",
        "engine.boost_pressure",
        "fuel.high_pressure",
    )

    def detect(self, frames: Sequence[AlignedFrame], pulls: Sequence[PullWindow]) -> DetectorResult:
        if len(frames) < 2:
            return DetectorResult(
                self.name, DetectorState.INSUFFICIENT_DATA, warnings=("fewer_than_two_frames",)
            )
        events: list[EventCandidate] = []
        for before, after in zip(frames, frames[1:], strict=False):
            gap = (after.observed_at - before.observed_at).total_seconds()
            if after.gap_before or gap >= self.profile.telemetry_gap_seconds:
                events.append(
                    self.candidate(
                        "telemetry_gap",
                        EventCategory.TELEMETRY_QUALITY,
                        [before, after],
                        severity=score_severity(gap / 10, gap),
                        confidence=0.99,
                        baseline=BaselineType.ABSOLUTE_THRESHOLD,
                        reference={"gap_threshold_seconds": self.profile.telemetry_gap_seconds},
                        evidence={"gap_seconds": gap, "analysis_confidence_reduced": True},
                    )
                )
        for signal in self.watched:

            def signal_missing(frame: AlignedFrame, watched_signal: str = signal) -> bool:
                return (
                    frame.values.get(watched_signal) is None
                    and frame.values.get("engine.rpm") is not None
                )

            missing_runs = _contiguous_runs(
                frames,
                signal_missing,
                self.profile.dropout_seconds,
            )
            for missing in missing_runs:
                if (missing[-1].observed_at - missing[0].observed_at).total_seconds() < (
                    self.profile.dropout_seconds
                ):
                    continue
                events.append(
                    self.candidate(
                        "sensor_dropout",
                        EventCategory.SENSOR,
                        missing,
                        severity=Severity.LOW,
                        confidence=0.85,
                        baseline=BaselineType.ABSOLUTE_THRESHOLD,
                        reference={"absence_threshold_seconds": self.profile.dropout_seconds},
                        evidence={
                            "signal": signal,
                            "duration_seconds": (
                                missing[-1].observed_at - missing[0].observed_at
                            ).total_seconds(),
                        },
                    )
                )
        for signal, related in (
            ("engine.boost_pressure", "engine.rpm"),
            ("vehicle.speed", "engine.rpm"),
        ):
            present = [frame for frame in frames if frame.values.get(signal) is not None]
            runs = _contiguous_runs(
                present,
                lambda frame: True,
                self.profile.dropout_seconds,
            )
            constant_runs: list[list[AlignedFrame]] = []
            for run in runs:
                start = 0
                for index in range(1, len(run) + 1):
                    if index == len(run) or run[index].values.get(signal) != run[start].values.get(
                        signal
                    ):
                        constant_runs.append(run[start:index])
                        start = index
            for stuck in constant_runs:
                values = _series(stuck, signal)
                relatives = _series(stuck, related)
                duration = (stuck[-1].observed_at - stuck[0].observed_at).total_seconds()
                if not (
                    len(values) >= 3
                    and duration >= self.profile.stuck_seconds
                    and relatives
                    and max(relatives) - min(relatives) > 300
                ):
                    continue
                events.append(
                    self.candidate(
                        "signal_stuck",
                        EventCategory.SENSOR,
                        stuck,
                        severity=Severity.LOW,
                        confidence=0.88,
                        baseline=BaselineType.PROFILE_THRESHOLD,
                        reference={"minimum_duration_seconds": self.profile.stuck_seconds},
                        evidence={
                            "signal": signal,
                            "constant_value": values[0],
                            "related_signal": related,
                            "related_delta": max(relatives) - min(relatives),
                        },
                    )
                )
        return DetectorResult(
            self.name,
            DetectorState.EVENT_DETECTED if events else DetectorState.NO_EVENT,
            tuple(events),
        )


def consolidate_events(
    events: Sequence[EventCandidate], gap_seconds: float
) -> list[EventCandidate]:
    ordered = sorted(
        events,
        key=lambda e: (
            e.event_type,
            e.algorithm_name,
            e.pull_index if e.pull_index is not None else -1,
            e.started_at,
        ),
    )
    result: list[EventCandidate] = []
    for event in ordered:
        if (
            result
            and (previous := result[-1]).event_type == event.event_type
            and previous.algorithm_name == event.algorithm_name
            and previous.pull_index == event.pull_index
            and event.started_at - previous.ended_at <= timedelta(seconds=gap_seconds)
        ):
            prior_count = previous.evidence.get("consolidated_count", 1)
            consolidated_count = prior_count if isinstance(prior_count, int) else 1
            result[-1] = replace(
                previous,
                ended_at=max(previous.ended_at, event.ended_at),
                severity=max(
                    previous.severity, event.severity, key=lambda s: list(Severity).index(s)
                ),
                confidence=max(previous.confidence, event.confidence),
                evidence={
                    **previous.evidence,
                    "consolidated_count": consolidated_count + 1,
                },
            )
        else:
            result.append(event)
    return result


class EventEngine:
    def __init__(
        self,
        profile: EventProfile | None = None,
        detectors: Sequence[EventDetector] | None = None,
    ) -> None:
        profile = profile or EventProfile()
        self.profile = profile
        self.detectors = tuple(
            detectors
            or (
                PullBehaviorDetector(profile),
                TemperatureDetector(profile),
                QualityDetector(profile),
            )
        )

    def analyze(
        self, frames: Sequence[AlignedFrame], pulls: Sequence[PullWindow]
    ) -> tuple[list[EventCandidate], tuple[DetectorResult, ...]]:
        results = tuple(detector.detect(frames, pulls) for detector in self.detectors)
        return consolidate_events(
            [event for result in results for event in result.events],
            self.profile.consolidation_gap_seconds,
        ), results
