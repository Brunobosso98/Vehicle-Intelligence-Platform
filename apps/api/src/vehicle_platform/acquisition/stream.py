import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from vehicle_platform.telemetry.domain import RawTelemetryRecord

MAX_SPOOL_RECORD_BYTES = 65536


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
        if not 1 <= maximum_bytes <= 1073741824:
            raise ValueError("spool capacity must be between one byte and 1 GiB")
        self.path, self.maximum_bytes, self.dropped = path, maximum_bytes, 0
        path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, payload: bytes) -> bool:
        current = self.path.stat().st_size if self.path.exists() else 0
        if len(payload) > MAX_SPOOL_RECORD_BYTES or current + len(payload) + 1 > self.maximum_bytes:
            self.dropped += 1
            return False
        fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            pending = memoryview(payload + b"\n")
            offset = 0
            while offset < len(pending):
                written = os.write(fd, pending[offset:])
                if written <= 0:
                    raise OSError("spool write made no progress")
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        return True

    def drain(self) -> tuple[bytes, ...]:
        if not self.path.exists():
            return ()
        values = tuple(line for line in self.path.read_bytes().splitlines() if line)
        self.path.unlink()
        return values

    def peek(self, limit: int) -> tuple[bytes, ...]:
        if limit < 0:
            raise ValueError("spool read limit must be nonnegative")
        if not self.path.exists():
            return ()
        if self.path.stat().st_size > self.maximum_bytes:
            raise ValueError("existing spool exceeds configured capacity")
        with self.path.open("rb") as spool:
            values = []
            for _ in range(limit):
                line = spool.readline(MAX_SPOOL_RECORD_BYTES + 2)
                if not line:
                    break
                if len(line) > MAX_SPOOL_RECORD_BYTES + 1:
                    raise ValueError("spool record exceeds bounded message size")
                values.append(line.rstrip(b"\n"))
            return tuple(values)

    def acknowledge(self, count: int) -> None:
        """Single-collector atomic acknowledgement, only after successful publish."""
        if count < 0:
            raise ValueError("spool acknowledgement must be nonnegative")
        if not self.path.exists():
            return
        if self.path.stat().st_size > self.maximum_bytes:
            raise ValueError("existing spool exceeds configured capacity")
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".spool-ack-")
        try:
            with os.fdopen(fd, "wb") as replacement, self.path.open("rb") as spool:
                for _ in range(count):
                    line = spool.readline(MAX_SPOOL_RECORD_BYTES + 2)
                    if len(line) > MAX_SPOOL_RECORD_BYTES + 1:
                        raise ValueError("spool record exceeds bounded message size")
                    if not line:
                        break
                shutil.copyfileobj(spool, replacement, length=65536)
                replacement.flush()
                os.fsync(replacement.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    @property
    def occupancy_bytes(self) -> int:
        return self.path.stat().st_size if self.path.exists() else 0

    @property
    def capacity_state(self) -> str:
        ratio = self.occupancy_bytes / self.maximum_bytes
        return (
            "capacity_reached"
            if ratio >= 1
            else "near_capacity"
            if ratio >= 0.9
            else "warning"
            if ratio >= 0.7
            else "normal"
        )
