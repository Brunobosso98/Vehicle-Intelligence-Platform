from datetime import UTC, datetime, timedelta

import pytest

from vehicle_platform.analysis.domain import AlignedFrame
from vehicle_platform.events.domain import EventProfile, PullWindow, Severity
from vehicle_platform.events.engine import (
    EventEngine,
    comparable_pull_score,
    median_absolute_deviation,
    score_confidence,
    score_severity,
)

START = datetime(2025, 1, 1, tzinfo=UTC)


def frames(
    values: list[dict[str, float | None]], *, gap: set[int] | None = None
) -> list[AlignedFrame]:
    return [
        AlignedFrame(START + timedelta(seconds=index), value, gap_before=index in (gap or set()))
        for index, value in enumerate(values)
    ]


def pull(data: list[AlignedFrame]) -> PullWindow:
    return PullWindow(data[0].observed_at, data[-1].observed_at, tuple(data))


def base(
    boost: float = 100_000, iat: float = 300, fuel: float = 19_000_000, throttle: float = 90
) -> dict[str, float]:
    return {
        "engine.rpm": 2500,
        "vehicle.speed": 20,
        "engine.throttle_position": throttle,
        "engine.boost_pressure": boost,
        "engine.intake_air_temperature": iat,
        "engine.oil_temperature": 360,
        "engine.coolant_temperature": 365,
        "fuel.high_pressure": fuel,
    }


def types(result: tuple[list[object], object]) -> set[str]:
    return {event.event_type for event in result[0]}


def test_statistics_scoring_and_profile_hash() -> None:
    assert median_absolute_deviation([1, 2, 2, 100]) == 0.5
    assert median_absolute_deviation([]) is None
    assert score_severity(0.6, 2) is Severity.HIGH
    assert score_confidence(1, 1, 1) == 0.99
    assert EventProfile().configuration_hash == EventProfile().configuration_hash
    with pytest.raises(ValueError):
        EventProfile(high_load_throttle_pct=101)


def test_comparable_pulls() -> None:
    one = frames([{**base(), "engine.rpm": 2000 + i * 500} for i in range(5)])
    two = frames([{**base(), "engine.rpm": 2100 + i * 500} for i in range(5)])
    assert comparable_pull_score(pull(one), pull(two)) > 0.7


def test_normal_and_missing_pulls_have_no_vehicle_anomaly() -> None:
    healthy = frames(
        [{**base(boost=100_000 + i * 3000), "engine.rpm": 2000 + i * 500} for i in range(6)]
    )
    events, results = EventEngine().analyze(healthy, [pull(healthy)])
    assert not {event.event_type for event in events} & {
        "boost_drop",
        "boost_overshoot",
        "fuel_pressure_drop",
        "unexpected_throttle_closure",
    }
    assert EventEngine().analyze([], [])[0] == []
    assert results


def test_pull_anomalies_are_factual() -> None:
    first = frames(
        [{**base(boost=120_000, iat=300), "engine.rpm": 2000 + i * 500} for i in range(6)]
    )
    second = frames(
        [
            {
                **base(boost=95_000, iat=311 + i * 3, fuel=19_000_000 if i < 2 else 14_000_000),
                "engine.rpm": 2100 + i * 500,
                "engine.throttle_position": 90 if i < 3 else 50,
            }
            for i in range(6)
        ]
    )
    events, _ = EventEngine().analyze(first + second, [pull(first), pull(second)])
    found = {event.event_type for event in events}
    assert {"boost_drop", "iat_rise", "fuel_pressure_drop", "unexpected_throttle_closure"} <= found
    assert all("failure" not in str(event.evidence).lower() for event in events)


def test_overshoot_and_high_temperatures() -> None:
    data = frames(
        [
            {
                **base(boost=170_000),
                "engine.rpm": 2000 + i * 500,
                "engine.intake_air_temperature": 340,
                "engine.oil_temperature": 410,
                "engine.coolant_temperature": 400,
            }
            for i in range(5)
        ]
    )
    found = types(EventEngine().analyze(data, [pull(data)]))
    assert {
        "boost_overshoot",
        "intake_temperature_high",
        "oil_temperature_high",
        "coolant_temperature_high",
    } <= found


def test_quality_events_and_consolidation() -> None:
    data = frames(
        [
            {
                "engine.rpm": 2000 + i * 500,
                "vehicle.speed": 20,
                "engine.throttle_position": 80,
                "engine.boost_pressure": 50_000,
                "fuel.high_pressure": 18_000_000 if i == 0 else None,
            }
            for i in range(7)
        ],
        gap={4},
    )
    found = types(EventEngine().analyze(data, [pull(data)]))
    assert {"telemetry_gap", "sensor_dropout"} <= found
    assert "signal_stuck" not in found
    continuous = frames(
        [
            {
                "engine.rpm": 2000 + i * 500,
                "vehicle.speed": 20,
                "engine.throttle_position": 80,
                "engine.boost_pressure": 50_000,
                "fuel.high_pressure": 18_000_000,
            }
            for i in range(7)
        ]
    )
    assert "signal_stuck" in types(EventEngine().analyze(continuous, [pull(continuous)]))


def test_low_load_variation_is_not_fuel_or_throttle_event() -> None:
    data = frames(
        [
            {
                **base(fuel=19_000_000 if i < 2 else 10_000_000, throttle=20),
                "engine.rpm": 2000 - i * 100,
            }
            for i in range(5)
        ]
    )
    found = types(EventEngine().analyze(data, []))
    assert "fuel_pressure_drop" not in found
    assert "unexpected_throttle_closure" not in found


def test_threshold_events_do_not_bridge_isolated_spikes_or_gaps() -> None:
    from vehicle_platform.events.engine import PullBehaviorDetector, TemperatureDetector

    isolated = frames(
        [
            {
                **base(),
                "engine.boost_pressure": 170_000 if i in (0, 4) else 100_000,
                "engine.oil_temperature": 410 if i in (0, 4) else 360,
            }
            for i in range(6)
        ]
    )
    assert not TemperatureDetector(EventProfile()).detect(isolated, []).events
    assert not PullBehaviorDetector(EventProfile()).detect(isolated, [pull(isolated)]).events
    discontinuous = [
        isolated[0],
        AlignedFrame(START + timedelta(seconds=10), isolated[0].values, gap_before=True),
    ]
    assert not TemperatureDetector(EventProfile()).detect(discontinuous, []).events
    sustained = frames([{**base(), "engine.oil_temperature": 410} for _ in range(3)])
    assert len(TemperatureDetector(EventProfile()).detect(sustained, []).events) == 1
    assert (
        EventProfile(algorithm_version="1.0.0").configuration_hash
        != EventProfile().configuration_hash
    )


def test_fuel_drop_requires_sustained_observation_not_single_low_spike() -> None:
    from vehicle_platform.events.engine import PullBehaviorDetector

    data = frames(
        [{**base(), "fuel.high_pressure": 14_000_000 if i == 4 else 19_000_000} for i in range(7)]
    )
    assert not PullBehaviorDetector(EventProfile()).detect(data, [pull(data)]).events
    data = frames(
        [{**base(), "fuel.high_pressure": 14_000_000 if i >= 4 else 19_000_000} for i in range(7)]
    )
    assert "fuel_pressure_drop" in {
        event.event_type
        for event in PullBehaviorDetector(EventProfile()).detect(data, [pull(data)]).events
    }


def test_never_available_channels_do_not_claim_sensor_dropout() -> None:
    data = frames([{"engine.rpm": 900} for _ in range(6)])
    events, _ = EventEngine().analyze(data, [])
    assert "sensor_dropout" not in {event.event_type for event in events}
