from collections.abc import Sequence
from statistics import fmean
from typing import Protocol

from vehicle_platform.analysis.domain import (
    AlignedFrame,
    DetectedPull,
    DetectedSegment,
    DetectorProfile,
    PullMetrics,
    SegmentType,
)


def _slope(current: float | None, previous: float | None, seconds: float) -> float | None:
    return None if current is None or previous is None else (current - previous) / seconds


def _mean(values: list[float]) -> float | None:
    return fmean(values) if values else None


class SegmentDetector(Protocol):
    def detect(self, telemetry: Sequence[AlignedFrame]) -> list[DetectedSegment]: ...


class PullDetector(Protocol):
    def detect(self, telemetry: Sequence[AlignedFrame]) -> list[DetectedPull]: ...


class HeuristicSegmentDetector:
    algorithm_version = "segmenter-v1.1"

    def __init__(self, profile: DetectorProfile) -> None:
        self.profile = profile

    def _classify(self, current: AlignedFrame, previous: AlignedFrame | None) -> SegmentType:
        value = current.values
        rpm, speed, throttle = (
            value.get("engine.rpm"),
            value.get("vehicle.speed"),
            value.get("engine.throttle_position"),
        )
        if rpm is None or speed is None:
            return SegmentType.UNKNOWN
        if (
            speed <= self.profile.idle_max_speed
            and self.profile.idle_rpm_min <= rpm <= self.profile.idle_rpm_max
            and (throttle is None or throttle <= self.profile.idle_max_throttle)
        ):
            return SegmentType.IDLE
        temp = value.get("engine.coolant_temperature") or value.get("engine.oil_temperature")
        if temp is not None and temp < self.profile.warm_temperature_k:
            return SegmentType.WARM_UP
        if previous is None or current.gap_before:
            return SegmentType.UNKNOWN
        seconds = (current.observed_at - previous.observed_at).total_seconds()
        rpm_slope = _slope(rpm, previous.values.get("engine.rpm"), seconds)
        speed_slope = _slope(speed, previous.values.get("vehicle.speed"), seconds)
        if (
            speed_slope is not None
            and speed_slope <= self.profile.deceleration_speed_slope
            and (throttle is None or throttle < 25)
        ):
            return SegmentType.DECELERATION
        if (
            rpm_slope is not None
            and speed_slope is not None
            and rpm_slope >= self.profile.acceleration_rpm_slope
            and speed_slope >= self.profile.acceleration_speed_slope
        ):
            return (
                SegmentType.PULL
                if throttle is not None and throttle >= self.profile.pull_min_throttle
                else SegmentType.ACCELERATION
            )
        if speed > self.profile.idle_max_speed and (
            throttle is None or throttle < self.profile.pull_min_throttle
        ):
            return SegmentType.CRUISE
        return SegmentType.UNKNOWN

    def detect(self, telemetry: Sequence[AlignedFrame]) -> list[DetectedSegment]:
        if not telemetry:
            return []
        classified = [
            self._classify(frame, telemetry[index - 1] if index else None)
            for index, frame in enumerate(telemetry)
        ]
        result: list[DetectedSegment] = []
        start = 0
        for index in range(1, len(telemetry) + 1):
            boundary = (
                index == len(telemetry)
                or classified[index] != classified[start]
                or telemetry[index].gap_before
            )
            if boundary:
                frames = telemetry[start:index]
                coverage = sum(v is not None for f in frames for v in f.values.values()) / max(
                    1, sum(len(f.values) for f in frames)
                )
                flags = ("telemetry_gap",) if start and telemetry[start].gap_before else ()
                result.append(
                    DetectedSegment(
                        classified[start],
                        frames[0].observed_at,
                        frames[-1].observed_at
                        + __import__("datetime").timedelta(milliseconds=self.profile.interval_ms),
                        round(min(0.99, 0.55 + coverage * 0.4), 3),
                        flags,
                        {"frame_count": len(frames), "signal_coverage": round(coverage, 3)},
                    )
                )
                start = index
        return result


def compute_pull_metrics(frames: Sequence[AlignedFrame]) -> PullMetrics:
    def series(signal: str) -> list[float]:
        return [value for frame in frames if (value := frame.values.get(signal)) is not None]

    rpm, speed, boost, throttle = (
        series("engine.rpm"),
        series("vehicle.speed"),
        series("engine.boost_pressure"),
        series("engine.throttle_position"),
    )
    iat, oil, coolant = (
        series("engine.intake_air_temperature"),
        series("engine.oil_temperature"),
        series("engine.coolant_temperature"),
    )
    available = (
        tuple(
            sorted(
                key
                for key in frames[0].values
                if any(frame.values.get(key) is not None for frame in frames)
            )
        )
        if frames
        else ()
    )
    expected = len(frames) * 4
    present = sum(
        frame.values.get(key) is not None
        for frame in frames
        for key in (
            "engine.rpm",
            "vehicle.speed",
            "engine.throttle_position",
            "engine.boost_pressure",
        )
    )
    return PullMetrics(
        duration_ms=int((frames[-1].observed_at - frames[0].observed_at).total_seconds() * 1000)
        if frames
        else 0,
        start_rpm=rpm[0] if rpm else None,
        end_rpm=rpm[-1] if rpm else None,
        min_rpm=min(rpm) if rpm else None,
        max_rpm=max(rpm) if rpm else None,
        start_speed=speed[0] if speed else None,
        end_speed=speed[-1] if speed else None,
        max_speed=max(speed) if speed else None,
        max_boost=max(boost) if boost else None,
        average_boost=_mean(boost),
        start_iat=iat[0] if iat else None,
        end_iat=iat[-1] if iat else None,
        iat_delta=iat[-1] - iat[0] if iat else None,
        max_oil_temperature=max(oil) if oil else None,
        max_coolant_temperature=max(coolant) if coolant else None,
        average_throttle=_mean(throttle),
        max_throttle=max(throttle) if throttle else None,
        sample_count=len(frames),
        data_completeness=round(present / expected, 3) if expected else 0,
        available_signals=available,
    )


class HeuristicPullDetector:
    algorithm_version = "pull-detector-v1.1"

    def __init__(self, profile: DetectorProfile) -> None:
        self.profile = profile

    def detect(self, telemetry: Sequence[AlignedFrame]) -> list[DetectedPull]:
        candidates: list[list[AlignedFrame]] = []
        current: list[AlignedFrame] = []
        for index, frame in enumerate(telemetry):
            throttle = frame.values.get("engine.throttle_position")
            if (
                index
                and not frame.gap_before
                and throttle is not None
                and throttle >= self.profile.pull_min_throttle
            ):
                rpm_slope = _slope(
                    frame.values.get("engine.rpm"),
                    telemetry[index - 1].values.get("engine.rpm"),
                    (frame.observed_at - telemetry[index - 1].observed_at).total_seconds(),
                )
                speed_slope = _slope(
                    frame.values.get("vehicle.speed"),
                    telemetry[index - 1].values.get("vehicle.speed"),
                    (frame.observed_at - telemetry[index - 1].observed_at).total_seconds(),
                )
                if (
                    rpm_slope is not None
                    and speed_slope is not None
                    and rpm_slope >= 0
                    and speed_slope >= 0
                ):
                    current.append(frame)
                    continue
            if current:
                candidates.append(current)
                current = []
        if current:
            candidates.append(current)
        result: list[DetectedPull] = []
        for frames in candidates:
            metrics = compute_pull_metrics(frames)
            rpm_delta = (metrics.end_rpm or 0) - (metrics.start_rpm or 0)
            speed_delta = (metrics.end_speed or 0) - (metrics.start_speed or 0)
            duration = metrics.duration_ms / 1000
            if (
                duration < self.profile.pull_min_duration_seconds
                or rpm_delta < self.profile.pull_min_rpm_delta
                or speed_delta < self.profile.pull_min_speed_delta
            ):
                continue
            flags = []
            if "engine.boost_pressure" not in metrics.available_signals:
                flags.append("missing_boost")
            if metrics.data_completeness < 0.7:
                flags.append("insufficient_signal_coverage")
            confidence = min(
                0.99,
                0.45
                + 0.15 * min(1, duration / 6)
                + 0.15 * min(1, rpm_delta / 2500)
                + 0.15 * min(1, speed_delta / 12)
                + (0.1 if not flags else 0),
            )
            result.append(
                DetectedPull(
                    frames[0].observed_at,
                    frames[-1].observed_at,
                    round(confidence, 3),
                    tuple(flags),
                    {
                        "rpm_delta": round(rpm_delta, 2),
                        "speed_delta": round(speed_delta, 2),
                        "duration_seconds": round(duration, 3),
                        "mean_throttle_pct": metrics.average_throttle,
                        "boost_available": "engine.boost_pressure" in metrics.available_signals,
                        "signal_coverage": metrics.data_completeness,
                    },
                    metrics,
                )
            )
        return result
