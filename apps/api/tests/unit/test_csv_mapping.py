from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from vehicle_platform.telemetry.mapping import (
    CSVColumnMapping,
    MappedCSVTelemetrySource,
    inspect_csv,
)


def mapping(**changes):
    return CSVColumnMapping.model_validate(
        {
            "timestamp_column": "Time",
            "signals": [{"column": "Pressure", "signal": "engine.boost_pressure", "unit": "bar"}],
            **changes,
        }
    )


async def test_explicit_wide_csv_mapping_preserves_units_time_and_provenance() -> None:
    source = MappedCSVTelemetrySource(
        b"Time,Pressure,Notes\n2026-01-01T00:00:00Z,-0.3,ignored\n", mapping()
    )
    records = [record async for record in source.read()]
    assert source.unmapped_columns == ["Notes"]
    assert len(records) == 1
    assert records[0].observed_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert records[0].value == -0.3 and records[0].unit == "bar"
    assert records[0].signal == "engine.boost_pressure"
    assert records[0].raw_signal == "Pressure"
    assert records[0].source_metadata["csv_mapping_hash"] == mapping().configuration_hash
    repeated = [record async for record in source.read()]
    assert repeated == records


@pytest.mark.parametrize(
    "signals",
    [
        [{"column": "Pressure", "signal": "engine.boost_pressure", "unit": "rpm"}],
        [{"column": "Pressure", "signal": "unknown.proprietary", "unit": "bar"}],
        [{"column": "Time", "signal": "engine.boost_pressure", "unit": "bar"}],
        [
            {"column": "Pressure", "signal": "engine.boost_pressure", "unit": "bar"},
            {"column": "Second", "signal": "engine.boost_pressure", "unit": "bar"},
        ],
    ],
)
def test_mapping_requires_supported_units_and_unambiguous_columns(signals) -> None:
    with pytest.raises(ValidationError):
        mapping(signals=signals)


@pytest.mark.parametrize("content", [b"", b"Time,Time\n", b"a" * 10_000_001])
def test_header_inspection_rejects_missing_ambiguous_or_oversized_csv(content: bytes) -> None:
    with pytest.raises(ValueError):
        inspect_csv(content)


@pytest.mark.parametrize(
    "row",
    [
        "2026-01-01T00:00:00Z,nan",
        "2026-01-01T00:00:00,1",
        "2026-01-01T00:00:00Z,=1+2",
        "2026-01-01T00:00:00Z",
        "2026-01-01T00:00:00Z,1,extra",
    ],
)
async def test_mapped_records_reject_nonfinite_naive_formula_and_bad_shapes(row: str) -> None:
    source = MappedCSVTelemetrySource(("Time,Pressure\n" + row + "\n").encode(), mapping())
    with pytest.raises(ValueError):
        _ = [record async for record in source.read()]


async def test_explicit_identity_sequence_are_preserved() -> None:
    source = MappedCSVTelemetrySource(
        b"Time,Pressure,ID,Sequence\n2026-01-01T00:00:00Z,1,p1,7\n",
        mapping(record_id_column="ID", sequence_column="Sequence"),
    )
    record = [record async for record in source.read()][0]
    assert record.source_record_id == "p1:Pressure"
    assert record.sequence == 7


@pytest.mark.parametrize(
    "identity,sequence", [("", "0"), ("=1", "0"), ("x" * 160, "0"), ("ok", "-1")]
)
async def test_invalid_identity_or_sequence_is_rejected(identity: str, sequence: str) -> None:
    source = MappedCSVTelemetrySource(
        f"Time,Pressure,ID,Sequence\n2026-01-01T00:00:00Z,1,{identity},{sequence}\n".encode(),
        mapping(record_id_column="ID", sequence_column="Sequence"),
    )
    with pytest.raises(ValueError):
        _ = [record async for record in source.read()]


@pytest.mark.parametrize("content", [b"Time,Other\n", b"Time,\n", b"\xff", ("x" * 101).encode()])
def test_absent_mapping_and_invalid_headers_are_rejected(content: bytes) -> None:
    with pytest.raises(ValueError):
        MappedCSVTelemetrySource(content, mapping())
