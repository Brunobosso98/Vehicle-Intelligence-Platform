import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from vehicle_platform.acquisition.stream import RawTelemetryMessage
from vehicle_platform.acquisition.worker import StreamConsumer
from vehicle_platform.api.domain_contracts import StreamObservation
from vehicle_platform.telemetry.domain import MAX_SEQUENCE, RawTelemetryRecord
from vehicle_platform.telemetry.mapping import CSVColumnMapping, MappedCSVTelemetrySource
from vehicle_platform.telemetry.sources import CSVTelemetrySource


@pytest.mark.parametrize("sequence", [-1, MAX_SEQUENCE + 1])
async def test_sequence_overflow_rejected_at_every_input_boundary(sequence: int) -> None:
    observed = datetime.now(UTC)
    with pytest.raises(ValueError, match="64-bit"):
        RawTelemetryRecord(observed, "engine.rpm", 900, "rpm", "one", sequence)
    with pytest.raises(ValidationError):
        StreamObservation(
            message_id=uuid4(),
            observed_at=observed,
            signal="engine.rpm",
            value=900,
            unit="rpm",
            source_record_id="one",
            sequence=sequence,
        )
    csv = (
        "timestamp,signal,value,unit,record_id,sequence\n"
        f"{observed.isoformat()},rpm,900,rpm,one,{sequence}\n"
    ).encode()
    with pytest.raises(ValueError):
        [record async for record in CSVTelemetrySource(csv).read()]
    mapping = CSVColumnMapping.model_validate(
        {
            "timestamp_column": "Time",
            "sequence_column": "Sequence",
            "signals": [{"column": "RPM", "signal": "engine.rpm", "unit": "rpm"}],
        }
    )
    mapped = f"Time,Sequence,RPM\n{observed.isoformat()},{sequence},900\n".encode()
    with pytest.raises(ValueError):
        [record async for record in MappedCSVTelemetrySource(mapped, mapping).read()]
    envelope = json.loads(
        RawTelemetryMessage.from_record(
            uuid4(),
            "fixture",
            "fixture",
            RawTelemetryRecord(observed, "engine.rpm", 900, "rpm", "one", 0),
        ).encode()
    )
    envelope["driving_session_id"] = str(uuid4())
    envelope["batch_id"] = str(uuid4())
    envelope["sequence"] = sequence
    with pytest.raises(ValueError, match="64-bit"):
        StreamConsumer._prepare(envelope)


@pytest.mark.parametrize("sequence", [None, 0, MAX_SEQUENCE])
def test_sequence_valid_edges_remain_compatible(sequence: int | None) -> None:
    record = RawTelemetryRecord(datetime.now(UTC), "engine.rpm", 900, "rpm", "one", sequence)
    envelope = json.loads(
        RawTelemetryMessage.from_record(uuid4(), "fixture", "fixture", record).encode()
    )
    envelope["driving_session_id"] = str(uuid4())
    envelope["batch_id"] = str(uuid4())
    assert StreamConsumer._prepare(envelope)["sequence"] == sequence
    assert (
        StreamObservation(
            message_id=uuid4(),
            observed_at=record.observed_at,
            signal="engine.rpm",
            value=900,
            unit="rpm",
            source_record_id="one",
            sequence=sequence,
        ).sequence
        == sequence
    )
