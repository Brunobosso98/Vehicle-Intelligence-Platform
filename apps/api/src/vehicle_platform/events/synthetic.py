import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from vehicle_platform.analysis.domain import AlignedFrame
from vehicle_platform.events.domain import PullWindow

START = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class ExpectedEvent:
    event_type: str
    started_at: datetime
    ended_at: datetime
    pull_index: int | None
    signal: str
    magnitude_band: tuple[float, float] | None = None


@dataclass(frozen=True)
class AnomalyInjection:
    event_type: str
    pull_index: int | None = None
    started_second: float | None = None
    ended_second: float | None = None
    magnitude: float | None = None


@dataclass(frozen=True)
class EventScenario:
    name: str
    frames: tuple[AlignedFrame, ...]
    pulls: tuple[PullWindow, ...]
    ground_truth: tuple[ExpectedEvent, ...]
    injections: tuple[AnomalyInjection, ...]
    seed: int


def _pull_frames(index: int, *, noisy: bool, seed: int) -> list[AlignedFrame]:
    rng = random.Random(seed + index)
    start = 10 + index * 10
    result = []
    for offset in range(6):
        noise = rng.uniform(-500, 500) if noisy else 0
        values: dict[str, float | None] = {
            "engine.rpm": 2200 + offset * 500,
            "vehicle.speed": 18 + offset * 2,
            "engine.throttle_position": 90,
            "engine.boost_pressure": 115_000 + offset * 1_000 + noise,
            "engine.intake_air_temperature": 300 + offset * 0.5,
            "engine.oil_temperature": 365,
            "engine.coolant_temperature": 360,
            "fuel.high_pressure": 19_000_000,
        }
        result.append(AlignedFrame(START + timedelta(seconds=start + offset), values))
    return result


def anomaly_scenario(
    name: str,
    injections: tuple[AnomalyInjection, ...] = (),
    *,
    noisy: bool = False,
    seed: int = 55,
) -> EventScenario:
    """Scripted independent injection fixture, not an N55 calibration or simulation."""
    pull_frames = [_pull_frames(index, noisy=noisy, seed=seed) for index in range(3)]
    extra: list[AlignedFrame] = []
    for second in (*range(16, 20), *range(26, 30), *range(36, 45)):
        extra.append(
            AlignedFrame(
                START + timedelta(seconds=second),
                {
                    "engine.rpm": 2100.0,
                    "vehicle.speed": 20.0,
                    "engine.throttle_position": 20.0,
                    "engine.boost_pressure": 5_000.0,
                    "engine.intake_air_temperature": 301.0,
                    "engine.oil_temperature": 365.0,
                    "engine.coolant_temperature": 360.0,
                    "fuel.high_pressure": 8_000_000.0,
                },
            )
        )
    truth: list[ExpectedEvent] = []
    for injection in injections:
        if injection.event_type == "telemetry_gap":
            before = AlignedFrame(START + timedelta(seconds=45), {"engine.rpm": 2500.0})
            after = AlignedFrame(
                START + timedelta(seconds=48), {"engine.rpm": 2600.0}, gap_before=True
            )
            extra.extend((before, after))
            truth.append(
                ExpectedEvent(
                    "telemetry_gap", before.observed_at, after.observed_at, None, "all", (3, 3)
                )
            )
            continue
        if injection.event_type in {"sensor_dropout", "signal_stuck"}:
            signal = (
                "fuel.high_pressure"
                if injection.event_type == "sensor_dropout"
                else "engine.boost_pressure"
            )
            quality_frames: list[AlignedFrame] = []
            for offset in range(6):
                values: dict[str, float | None] = {
                    "engine.rpm": 2000.0 + offset * 400,
                    "vehicle.speed": 18.0 + offset,
                    "engine.throttle_position": 30.0,
                    "engine.boost_pressure": 50_000.0,
                    "fuel.high_pressure": 18_000_000.0,
                }
                if injection.event_type == "sensor_dropout":
                    values[signal] = None
                quality_frames.append(AlignedFrame(START + timedelta(seconds=50 + offset), values))
            extra.extend(quality_frames)
            truth.append(
                ExpectedEvent(
                    injection.event_type,
                    quality_frames[0].observed_at,
                    quality_frames[-1].observed_at,
                    None,
                    signal,
                )
            )
            continue
        if injection.pull_index is None:
            raise ValueError("pull event injection requires pull_index")
        frames = pull_frames[injection.pull_index]
        band: tuple[float, float]
        if injection.event_type == "boost_drop":
            for frame in frames:
                frame.values["engine.boost_pressure"] = 85_000.0
            signal, band = "engine.boost_pressure", (80_000, 90_000)
        elif injection.event_type == "boost_overshoot":
            for frame in frames:
                frame.values["engine.boost_pressure"] = 170_000.0
            signal, band = "engine.boost_pressure", (165_000, 175_000)
        elif injection.event_type == "iat_rise":
            for offset, frame in enumerate(frames):
                frame.values["engine.intake_air_temperature"] = 314 + offset * 3
            signal, band = "engine.intake_air_temperature", (14, 20)
        elif injection.event_type == "fuel_pressure_drop":
            for offset, frame in enumerate(frames):
                frame.values["fuel.high_pressure"] = 19_000_000 if offset < 2 else 14_000_000
            signal, band = "fuel.high_pressure", (0.2, 0.3)
        elif injection.event_type == "unexpected_throttle_closure":
            for offset, frame in enumerate(frames):
                frame.values["engine.throttle_position"] = 90 if offset < 3 else 45
            signal, band = "engine.throttle_position", (40, 50)
        elif injection.event_type in {
            "intake_temperature_high",
            "oil_temperature_high",
            "coolant_temperature_high",
        }:
            signal, temperature = {
                "intake_temperature_high": ("engine.intake_air_temperature", 340),
                "oil_temperature_high": ("engine.oil_temperature", 410),
                "coolant_temperature_high": ("engine.coolant_temperature", 400),
            }[injection.event_type]
            for frame in frames:
                frame.values[signal] = temperature
            band = (temperature - 2, temperature + 2)
        else:
            raise ValueError(f"unsupported injection: {injection.event_type}")
        truth.append(
            ExpectedEvent(
                injection.event_type,
                frames[0].observed_at,
                frames[-1].observed_at,
                None if injection.event_type.endswith("temperature_high") else injection.pull_index,
                signal,
                band,
            )
        )
    all_frames = sorted(
        (frame for group in pull_frames for frame in group), key=lambda frame: frame.observed_at
    )
    all_frames.extend(extra)
    all_frames.sort(key=lambda frame: frame.observed_at)
    pulls = tuple(
        PullWindow(group[0].observed_at, group[-1].observed_at, tuple(group), str(index))
        for index, group in enumerate(pull_frames)
    )
    # Declare all scripted consequences independently; evaluators must not filter
    # detections to the requested injection class. Constant boost with changing
    # RPM is also stuck-signal evidence, and the appended quality window has a
    # six-second acquisition gap. An overshoot raises the prior-pull reference,
    # so the following normal pull is a factual relative drop (not a diagnosis).
    for injection in injections:
        if injection.event_type in {"boost_drop", "boost_overshoot"}:
            assert injection.pull_index is not None  # noqa: S101
            group = pull_frames[injection.pull_index]
            truth.append(
                ExpectedEvent(
                    "signal_stuck",
                    group[0].observed_at,
                    group[-1].observed_at,
                    None,
                    "engine.boost_pressure",
                )
            )
        if injection.event_type == "boost_overshoot" and injection.pull_index == 1:
            truth.append(
                ExpectedEvent(
                    "boost_drop",
                    START + timedelta(seconds=30),
                    START + timedelta(seconds=35),
                    2,
                    "engine.boost_pressure",
                )
            )
        if injection.event_type == "intake_temperature_high":
            group = pull_frames[injection.pull_index or 0]
            truth.append(
                ExpectedEvent(
                    "iat_rise",
                    group[0].observed_at,
                    group[-1].observed_at,
                    injection.pull_index,
                    "engine.intake_air_temperature",
                )
            )
        if injection.event_type in {"sensor_dropout", "signal_stuck"}:
            truth.append(
                ExpectedEvent(
                    "telemetry_gap",
                    START + timedelta(seconds=44),
                    START + timedelta(seconds=50),
                    None,
                    "all",
                    (6, 6),
                )
            )
            if injection.event_type == "sensor_dropout":
                truth.append(
                    ExpectedEvent(
                        "signal_stuck",
                        START + timedelta(seconds=50),
                        START + timedelta(seconds=55),
                        None,
                        "engine.boost_pressure",
                    )
                )
    return EventScenario(name, tuple(all_frames), pulls, tuple(truth), injections, seed)


def golden_scenarios() -> tuple[EventScenario, ...]:
    single = (
        ("boost-drop", AnomalyInjection("boost_drop", 2)),
        ("boost-overshoot", AnomalyInjection("boost_overshoot", 1)),
        ("iat-rise", AnomalyInjection("iat_rise", 2)),
        ("fuel-pressure-drop", AnomalyInjection("fuel_pressure_drop", 1)),
        ("sensor-dropout", AnomalyInjection("sensor_dropout")),
        ("signal-stuck", AnomalyInjection("signal_stuck")),
        ("telemetry-gap", AnomalyInjection("telemetry_gap")),
        ("throttle-closure", AnomalyInjection("unexpected_throttle_closure", 1)),
        ("intake-temperature-high", AnomalyInjection("intake_temperature_high", 2)),
        ("oil-temperature-high", AnomalyInjection("oil_temperature_high", 2)),
        ("coolant-temperature-high", AnomalyInjection("coolant_temperature_high", 2)),
    )
    scenarios = [
        anomaly_scenario("normal-repeated-pulls"),
        anomaly_scenario("noisy-healthy", noisy=True, seed=77),
    ]
    scenarios.extend(anomaly_scenario(name, (injection,)) for name, injection in single)
    scenarios.append(
        anomaly_scenario(
            "multi-anomaly",
            (
                AnomalyInjection("fuel_pressure_drop", 1),
                AnomalyInjection("boost_drop", 2),
                AnomalyInjection("iat_rise", 2),
                AnomalyInjection("sensor_dropout"),
            ),
        )
    )
    return tuple(scenarios)
