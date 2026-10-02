import csv
import io
from collections.abc import AsyncIterator

from vehicle_platform.telemetry.domain import RawTelemetryRecord, parse_timestamp

REQUIRED_COLUMNS = {"timestamp", "signal", "value", "unit", "record_id"}


class CSVTelemetrySource:
    def __init__(self, content: bytes, maximum_bytes: int = 10_000_000) -> None:
        if not content:
            raise ValueError("empty import")
        if len(content) > maximum_bytes:
            raise ValueError("import exceeds maximum size")
        try:
            self.text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV must be UTF-8") from exc

    async def read(self) -> AsyncIterator[RawTelemetryRecord]:
        reader = csv.DictReader(io.StringIO(self.text, newline=""))
        if reader.fieldnames is None or set(reader.fieldnames) != REQUIRED_COLUMNS | {"sequence"}:
            raise ValueError("CSV columns must be timestamp,signal,value,unit,record_id,sequence")
        for row in reader:
            if any(
                str(value).lstrip().startswith(("=", "+", "-", "@"))
                for value in row.values()
                if value
            ):
                raise ValueError("formula-like CSV cells are not accepted")
            try:
                sequence = int(row["sequence"]) if row["sequence"] else None
                yield RawTelemetryRecord(
                    parse_timestamp(row["timestamp"]),
                    row["signal"],
                    float(row["value"]),
                    row["unit"],
                    row["record_id"],
                    sequence,
                )
            except (TypeError, ValueError) as exc:
                raise ValueError("malformed CSV record") from exc
