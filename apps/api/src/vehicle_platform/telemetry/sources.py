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
        if (
            reader.fieldnames is None
            or len(reader.fieldnames) != len(REQUIRED_COLUMNS) + 1
            or set(reader.fieldnames) != REQUIRED_COLUMNS | {"sequence"}
        ):
            raise ValueError("CSV columns must be timestamp,signal,value,unit,record_id,sequence")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("malformed CSV record")
            if any(
                str(value).lstrip().startswith(("=", "+", "-", "@"))
                for key, value in row.items()
                if key != "value"
                if value
            ):
                raise ValueError("formula-like CSV cells are not accepted")
            if (
                not row["record_id"]
                or len(row["record_id"]) > 160
                or not row["signal"]
                or len(row["signal"]) > 100
                or not row["unit"]
                or len(row["unit"]) > 24
            ):
                raise ValueError("CSV identity, signal and unit must be bounded and nonempty")
            try:
                numeric_value = float(row["value"])
            except (TypeError, ValueError) as exc:
                if row["value"].lstrip().startswith(("=", "+", "-", "@")):
                    raise ValueError("formula-like CSV cells are not accepted") from exc
                raise ValueError("malformed CSV record") from exc
            try:
                sequence = int(row["sequence"]) if row["sequence"] else None
                yield RawTelemetryRecord(
                    parse_timestamp(row["timestamp"]),
                    row["signal"],
                    numeric_value,
                    row["unit"],
                    row["record_id"],
                    sequence,
                )
            except (TypeError, ValueError) as exc:
                raise ValueError("malformed CSV record") from exc
