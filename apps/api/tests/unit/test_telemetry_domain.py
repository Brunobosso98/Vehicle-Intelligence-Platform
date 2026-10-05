from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from vehicle_platform.api.domain_contracts import ConfigurationCreate
from vehicle_platform.telemetry.domain import (
    SIGNAL_BY_KEY,
    DataQuality,
    NormalizationError,
    SyntheticTelemetrySource,
    normalize_value,
    parse_timestamp,
    sample_id,
)
from vehicle_platform.telemetry.sources import CSVTelemetrySource


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [(36, "km/h", 10), (1, "bar", 100000), (32, "°C", 305.15), (1, "psi", 6894.757293168)],
)
def test_deterministic_unit_conversion(value: float, unit: str, expected: float) -> None:
    signal = (
        SIGNAL_BY_KEY["vehicle.speed"]
        if unit == "km/h"
        else SIGNAL_BY_KEY["engine.intake_air_temperature"]
        if unit == "°C"
        else SIGNAL_BY_KEY["engine.boost_pressure"]
    )
    result, quality = normalize_value(value, unit, signal)
    assert result == pytest.approx(expected)
    assert quality == DataQuality.VALID


def test_units_and_ranges_are_explicit() -> None:
    _, quality = normalize_value(10000, "rpm", SIGNAL_BY_KEY["engine.rpm"])
    assert quality == DataQuality.OUT_OF_RANGE
    with pytest.raises(NormalizationError, match="cannot represent"):
        normalize_value(1, "mystery", SIGNAL_BY_KEY["engine.rpm"])


def test_timestamp_requires_offset_and_normalizes_utc() -> None:
    assert parse_timestamp("2026-01-01T01:00:00+01:00") == datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(NormalizationError):
        parse_timestamp("2026-01-01T00:00:00")
    with pytest.raises(NormalizationError):
        parse_timestamp("broken")


def test_idempotency_is_stable_and_sensitive_to_identity() -> None:
    at = datetime(2026, 1, 1, tzinfo=UTC)
    first = sample_id("s", "csv", "r", at, "engine.rpm", 1)
    assert first == sample_id("s", "csv", "r", at, "engine.rpm", 1)
    assert first != sample_id("s", "csv", "r", at, "engine.rpm", 2)


async def test_synthetic_source_is_deterministic_and_complete() -> None:
    async def collect(seed: int):
        return [
            record
            async for record in SyntheticTelemetrySource(
                datetime(2026, 1, 1, tzinfo=UTC), 3, seed
            ).read()
        ]

    assert await collect(55) == await collect(55)
    assert await collect(55) != await collect(56)
    assert {r.signal for r in await collect(55)} >= {
        "engine.rpm",
        "vehicle.speed",
        "engine.boost_pressure",
        "engine.throttle_position",
        "engine.intake_air_temperature",
        "engine.oil_temperature",
        "engine.coolant_temperature",
    }


async def test_csv_parser_and_abuse_guards() -> None:
    data = b"timestamp,signal,value,unit,record_id,sequence\n2026-01-01T00:00:00Z,rpm,900,rpm,a,1\n"
    rows = [row async for row in CSVTelemetrySource(data).read()]
    assert rows[0].value == 900 and rows[0].sequence == 1
    with pytest.raises(ValueError, match="empty"):
        CSVTelemetrySource(b"")
    with pytest.raises(ValueError, match="size"):
        CSVTelemetrySource(b"abc", maximum_bytes=2)
    with pytest.raises(ValueError, match="columns"):
        [row async for row in CSVTelemetrySource(b"wrong\nvalue\n").read()]
    with pytest.raises(ValueError, match="formula"):
        [row async for row in CSVTelemetrySource(data.replace(b"900", b"=1+1")).read()]


def test_configuration_time_contract() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        ConfigurationCreate(
            effective_at=datetime(2026, 1, 1), description="stock", provenance="owner"
        )
    with pytest.raises(ValidationError, match="must follow"):
        ConfigurationCreate(
            effective_at=datetime(2026, 1, 2, tzinfo=UTC),
            ended_at=datetime(2026, 1, 1, tzinfo=UTC),
            description="stock",
            provenance="owner",
        )


async def test_csv_accepts_signed_measurements_and_rejects_broken_structure() -> None:
    header = b"timestamp,signal,value,unit,record_id,sequence\n"
    row = b"2026-01-01T00:00:00Z,boost,-30000,Pa,a,1\n"
    parsed = [record async for record in CSVTelemetrySource(header + row).read()]
    assert parsed[0].value == -30000
    assert normalize_value(parsed[0].value, "Pa", SIGNAL_BY_KEY["engine.boost_pressure"]) == (
        -30000,
        DataQuality.VALID,
    )
    for broken in (
        header + row.replace(b",a,1", b",a"),
        header + row.replace(b",a,1", b",a,1,extra"),
        header.replace(b"sequence", b"sequence,value") + row,
    ):
        with pytest.raises(ValueError):
            [record async for record in CSVTelemetrySource(broken).read()]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 1e308])
def test_nonfinite_measurements_and_conversion_overflow_are_rejected(value: float) -> None:
    with pytest.raises(NormalizationError, match="finite"):
        normalize_value(value, "bar", SIGNAL_BY_KEY["engine.boost_pressure"])


@pytest.mark.parametrize("kind", ["session", "modification"])
def test_session_and_modification_times_reject_naive_or_reversed_windows(kind: str) -> None:
    from uuid import uuid4

    from vehicle_platform.api.domain_contracts import ModificationCreate, SessionCreate

    if kind == "session":
        factory = SessionCreate
        fields = {"vehicle_id": uuid4(), "source_type": "csv"}
        beginning, ending = "started_at", "ended_at"
    else:
        factory = ModificationCreate
        fields = {"category": "intake"}
        beginning, ending = "installed_at", "removed_at"
    for start, end in (
        (datetime(2026, 1, 1), None),
        (datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2)),
        (datetime(2026, 1, 2, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)),
    ):
        with pytest.raises(ValidationError):
            factory(**fields, **{beginning: start, ending: end})
    factory(
        **fields,
        **{beginning: datetime(2026, 1, 1, tzinfo=UTC), ending: datetime(2026, 1, 2, tzinfo=UTC)},
    )


async def test_csv_encoding_missing_cells_and_bad_numeric_input() -> None:
    with pytest.raises(ValueError, match="UTF-8"):
        CSVTelemetrySource(b"\xff")
    header = b"timestamp,signal,value,unit,record_id,sequence\n"
    for row in (
        b"2026-01-01T00:00:00Z,rpm,invalid,rpm,a,1\n",
        b"2026-01-01T00:00:00Z,rpm,1000,rpm,a,invalid\n",
        b"2026-01-01T00:00:00Z,rpm,1000,rpm,=formula,1\n",
    ):
        with pytest.raises(ValueError):
            [record async for record in CSVTelemetrySource(header + row).read()]
