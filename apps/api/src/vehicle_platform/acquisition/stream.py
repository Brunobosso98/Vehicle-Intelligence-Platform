import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from vehicle_platform.telemetry.domain import RawTelemetryRecord


@dataclass(frozen=True)
class RawTelemetryMessage:
    schema_version: str
    message_id: str
    acquisition_session_id: str
    source_id: str
    vehicle_reference: str
    observed_at: str
    produced_at: str
    sequence: int | None
    provenance: dict[str, str]
    payload: dict[str, str | float]

    @classmethod
    def from_record(
        cls, session_id: UUID, source_id: str, vehicle_reference: str, record: RawTelemetryRecord
    ) -> "RawTelemetryMessage":
        return cls(
            "1.0",
            str(uuid4()),
            str(session_id),
            source_id,
            vehicle_reference,
            record.observed_at.astimezone(UTC).isoformat(),
            datetime.now(UTC).isoformat(),
            record.sequence,
            {"collector": "vehicle-collector"},
            {
                "signal": record.signal,
                "value": record.value,
                "unit": record.unit,
                "source_record_id": record.source_record_id,
            },
        )

    def encode(self) -> bytes:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()


class BoundedSpool:
    def __init__(self, path: Path, maximum_bytes: int = 10_000_000) -> None:
        self.path, self.maximum_bytes, self.dropped = path, maximum_bytes, 0
        path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, payload: bytes) -> bool:
        current = self.path.stat().st_size if self.path.exists() else 0
        if current + len(payload) + 1 > self.maximum_bytes:
            self.dropped += 1
            return False
        fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(fd, payload + b"\n")
        finally:
            os.close(fd)
        return True

    def drain(self) -> tuple[bytes, ...]:
        if not self.path.exists():
            return ()
        values = tuple(line for line in self.path.read_bytes().splitlines() if line)
        self.path.unlink()
        return values

    @property
    def occupancy_bytes(self) -> int:
        return self.path.stat().st_size if self.path.exists() else 0
