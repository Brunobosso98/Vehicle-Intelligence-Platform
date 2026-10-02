import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from vehicle_platform.analysis.domain import Observation, SegmentType


@dataclass(frozen=True)
class GroundTruthEvent:
    event_id: str
    segment_type: SegmentType
    started_at: datetime
    ended_at: datetime
    expected_rpm_range: tuple[float, float] | None = None


@dataclass(frozen=True)
class SyntheticScenario:
    name: str
    observations: tuple[Observation, ...]
    ground_truth: tuple[GroundTruthEvent, ...]


def mixed_drive(
    start: datetime = datetime(2025, 1, 1, tzinfo=UTC),
    rate_hz: int = 5,
    seed: int = 55,
    *,
    missing_boost: bool = False,
    noisy: bool = False,
    irregular: bool = False,
    telemetry_gap: bool = False,
) -> SyntheticScenario:
    """Deterministic scripted drive; values are plausible fixtures, not an N55 simulation."""
    if rate_hz not in {5, 10, 20}:
        raise ValueError("synthetic rate must be 5, 10, or 20 Hz")
    rng = random.Random(seed)
    pulls = (
        (60.0, 67.0, 2100.0, 5100.0),
        (100.0, 108.0, 2400.0, 5600.0),
        (140.0, 148.0, 2600.0, 5700.0),
    )
    observations: list[Observation] = []
    step = 1 / rate_hz
    total = int(170 * rate_hz)
    for index in range(total):
        second = index * step
        if telemetry_gap and 103 < second < 106:
            continue
        pull = next((item for item in pulls if item[0] <= second < item[1]), None)
        if second < 20:
            rpm, speed, throttle, boost = 720.0, 0.0, 7.0, -30000.0
        elif second < 45:
            rpm, speed, throttle, boost = (
                1300 + second * 12,
                5 + (second - 20) * 0.25,
                23.0,
                -5000.0,
            )
        elif pull:
            fraction = (second - pull[0]) / (pull[1] - pull[0])
            rpm = pull[2] + (pull[3] - pull[2]) * fraction
            speed = 16 + (second - pull[0]) * 1.8 + (pull[0] - 60) * 0.04
            throttle, boost = 92.0, 90000 + fraction * 35000
        elif any(end <= second < end + 10 for _, end, _, _ in pulls):
            rpm, speed, throttle, boost = (
                2800 - (second % 10) * 80,
                27 - (second % 10) * 0.35,
                8.0,
                -15000.0,
            )
        else:
            rpm, speed, throttle, boost = (
                2200 + math.sin(second / 4) * 30,
                19 + math.sin(second / 7) * 0.25,
                19.0,
                5000.0,
            )
        noise = rng.uniform(-30, 30) if noisy else rng.uniform(-3, 3)
        timestamp = start + timedelta(
            seconds=second + (rng.uniform(-0.025, 0.025) if irregular else 0)
        )
        values = {
            "engine.rpm": rpm + noise,
            "vehicle.speed": max(0, speed + noise / 300),
            "engine.throttle_position": throttle,
            "engine.intake_air_temperature": 296 + second * 0.025,
            "engine.oil_temperature": 325 + second * 0.35,
            "engine.coolant_temperature": 330 + second * 0.4,
        }
        if not missing_boost:
            values["engine.boost_pressure"] = boost
        for signal, value in values.items():
            observations.append(Observation(timestamp, signal, value, f"{index}:{signal}"))
    truth = tuple(
        GroundTruthEvent(
            f"pull-{i + 1}",
            SegmentType.PULL,
            start + timedelta(seconds=item[0]),
            start + timedelta(seconds=item[1]),
            (item[2], item[3]),
        )
        for i, item in enumerate(pulls)
    )
    return SyntheticScenario("normal-mixed-drive", tuple(observations), truth)


def negative_scenario(
    kind: str, start: datetime = datetime(2025, 1, 1, tzinfo=UTC)
) -> SyntheticScenario:
    if kind not in {"false-positive-throttle", "short-burst"}:
        raise ValueError("unknown negative scenario")
    observations: list[Observation] = []
    for index in range(200):
        second = index / 10
        active = 8 <= second < (9.5 if kind == "short-burst" else 14)
        values = {
            "engine.rpm": 2000 + ((second - 8) * 300 if active and kind == "short-burst" else 0),
            "vehicle.speed": 15 + ((second - 8) if active and kind == "short-burst" else 0),
            "engine.throttle_position": 95 if active else 20,
        }
        for signal, value in values.items():
            observations.append(
                Observation(start + timedelta(seconds=second), signal, value, f"{index}:{signal}")
            )
    return SyntheticScenario(kind, tuple(observations), ())
