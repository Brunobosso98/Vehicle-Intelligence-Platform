"""Explicit generic CSV mapping; no proprietary exporter assumptions."""

import csv
import hashlib
import io
from collections.abc import AsyncIterator

from pydantic import BaseModel, Field, model_validator

from vehicle_platform.telemetry.domain import (
    SIGNAL_BY_KEY,
    RawTelemetryRecord,
    normalize_value,
    parse_timestamp,
)


class CSVSignalColumn(BaseModel):
    column: str = Field(min_length=1, max_length=100)
    signal: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def supported(self) -> "CSVSignalColumn":
        definition = SIGNAL_BY_KEY.get(self.signal)
        if definition is None:
            raise ValueError("mapping requires a supported canonical signal")
        normalize_value(0, self.unit, definition)
        return self


class CSVColumnMapping(BaseModel):
    timestamp_column: str = Field(min_length=1, max_length=100)
    record_id_column: str | None = Field(default=None, min_length=1, max_length=100)
    sequence_column: str | None = Field(default=None, min_length=1, max_length=100)
    signals: list[CSVSignalColumn] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def unambiguous(self) -> "CSVColumnMapping":
        columns = [self.timestamp_column, *[item.column for item in self.signals]]
        columns.extend(c for c in (self.record_id_column, self.sequence_column) if c)
        if len(set(columns)) != len(columns):
            raise ValueError("mapping columns must have distinct roles")
        if len({item.signal for item in self.signals}) != len(self.signals):
            raise ValueError("resolve multiple columns for the same canonical signal explicitly")
        return self

    @property
    def configuration_hash(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


def inspect_csv(content: bytes) -> tuple[str, list[str]]:
    if len(content) > 10_000_000:
        raise ValueError("CSV exceeds 10 MB limit")
    value = content.decode("utf-8-sig")
    headers = list(csv.DictReader(io.StringIO(value, newline="")).fieldnames or [])
    if not headers or len(headers) > 100 or any(not h.strip() or len(h) > 100 for h in headers):
        raise ValueError("CSV requires 1..100 bounded column names")
    if len(set(headers)) != len(headers):
        raise ValueError("duplicate CSV headers require explicit resolution")
    return value, headers


class MappedCSVTelemetrySource:
    def __init__(self, content: bytes, mapping: CSVColumnMapping) -> None:
        self.text, self.headers = inspect_csv(content)
        self.mapping = mapping
        self.mapping_hash = mapping.configuration_hash
        used = {mapping.timestamp_column, *(item.column for item in mapping.signals)}
        used.update(c for c in (mapping.record_id_column, mapping.sequence_column) if c)
        if not used <= set(self.headers):
            raise ValueError("mapped column is absent from CSV")
        self.unmapped_columns = sorted(set(self.headers) - used)

    async def read(self) -> AsyncIterator[RawTelemetryRecord]:
        for index, row in enumerate(csv.DictReader(io.StringIO(self.text, newline=""))):
            if None in row or any(value is None for value in row.values()):
                raise ValueError("malformed mapped CSV record")
            observed = parse_timestamp(row[self.mapping.timestamp_column])
            identity = (
                row[self.mapping.record_id_column] if self.mapping.record_id_column else str(index)
            )
            if not identity or identity.lstrip().startswith(("=", "+", "-", "@")):
                raise ValueError("invalid mapped record identity")
            sequence = (
                int(row[self.mapping.sequence_column]) if self.mapping.sequence_column else index
            )
            if sequence < 0:
                raise ValueError("mapped sequence must be nonnegative")
            for column in self.mapping.signals:
                if len(f"{identity}:{column.column}") > 160:
                    raise ValueError("mapped record identity exceeds 160 characters")
                value = float(row[column.column])
                normalize_value(value, column.unit, SIGNAL_BY_KEY[column.signal])
                yield RawTelemetryRecord(
                    observed,
                    column.signal,
                    value,
                    column.unit,
                    f"{identity}:{column.column}",
                    sequence,
                    raw_signal=column.column,
                    source_metadata={
                        "csv_mapping_version": "1.0",
                        "csv_mapping_hash": self.mapping_hash,
                        "source_column": column.column,
                    },
                )
