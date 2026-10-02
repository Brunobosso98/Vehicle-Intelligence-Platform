import hashlib
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from vehicle_platform.api.domain_contracts import ImportResult, TelemetryPoint, TelemetryWindow
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.telemetry.domain import (
    SIGNAL_BY_ALIAS,
    NormalizationError,
    RawTelemetryRecord,
    TelemetrySource,
    normalize_value,
    sample_id,
)


def _content_hash(record: RawTelemetryRecord, value: float, unit: str) -> str:
    return hashlib.sha256(
        json.dumps(
            [record.signal, record.value, record.unit, value, unit], separators=(",", ":")
        ).encode()
    ).hexdigest()


class IngestionService:
    def __init__(self, database: Database, batch_size: int = 1000) -> None:
        self.database, self.batch_size = database, batch_size

    async def ingest(
        self, session_id: UUID, source_name: str, source: TelemetrySource
    ) -> ImportResult:
        stats = {
            "rows_read": 0,
            "accepted": 0,
            "rejected": 0,
            "duplicates": 0,
            "conflicts": 0,
            "unknown_signals": 0,
            "invalid_units": 0,
            "invalid_timestamps": 0,
        }
        start: datetime | None = None
        end: datetime | None = None
        batch: list[dict[str, object]] = []
        async with self.database.session() as db:
            await db.execute(
                text(
                    "UPDATE driving_sessions SET status='ingesting', updated_at=now() WHERE id=:id"
                ),
                {"id": session_id},
            )
            await db.commit()
            try:
                async for record in source.read():
                    stats["rows_read"] += 1
                    signal = SIGNAL_BY_ALIAS.get(record.signal.lower())
                    if signal is None:
                        stats["unknown_signals"] += 1
                        stats["rejected"] += 1
                        continue
                    try:
                        value, quality = normalize_value(record.value, record.unit, signal)
                    except NormalizationError:
                        stats["invalid_units"] += 1
                        stats["rejected"] += 1
                        continue
                    sid = sample_id(
                        str(session_id),
                        source_name,
                        record.source_record_id,
                        record.observed_at,
                        signal.key,
                        record.sequence,
                    )
                    batch.append(
                        {
                            "sample_id": sid,
                            "vehicle_id": None,
                            "session_id": session_id,
                            "observed_at": record.observed_at,
                            "signal_key": signal.key,
                            "numeric_value": value,
                            "normalized_unit": signal.unit,
                            "raw_signal": record.signal,
                            "raw_value": str(record.value),
                            "source": source_name,
                            "source_record_id": record.source_record_id,
                            "sequence_number": record.sequence,
                            "quality": quality.value,
                            "schema_version": 1,
                            "source_metadata": "{}",
                            "content_hash": _content_hash(record, value, signal.unit),
                        }
                    )
                    start = record.observed_at if start is None else min(start, record.observed_at)
                    end = record.observed_at if end is None else max(end, record.observed_at)
                    if len(batch) >= self.batch_size:
                        await self._persist(db, batch, stats)
                        batch.clear()
                if batch:
                    await self._persist(db, batch, stats)
                await db.execute(
                    text(
                        "UPDATE driving_sessions SET status='completed', sample_count=(SELECT count(*) FROM telemetry_samples WHERE session_id=:id), started_at=COALESCE(started_at,:start), ended_at=GREATEST(ended_at,:end), updated_at=now() WHERE id=:id"
                    ),
                    {"id": session_id, "start": start, "end": end},
                )
                await db.commit()
            except Exception:
                await db.rollback()
                await db.execute(
                    text(
                        "UPDATE driving_sessions SET status='failed', updated_at=now() WHERE id=:id"
                    ),
                    {"id": session_id},
                )
                await db.commit()
                raise
        return ImportResult(
            session_id=session_id, start_observed_at=start, end_observed_at=end, **stats
        )

    async def _persist(
        self, db: AsyncSession, batch: list[dict[str, object]], stats: dict[str, int]
    ) -> None:
        execute = db.execute
        ids = [row["sample_id"] for row in batch]
        existing = (
            await execute(
                text(
                    "SELECT sample_id, content_hash FROM telemetry_samples WHERE sample_id IN :ids"
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": ids},
            )
        ).all()
        known = {row.sample_id: row.content_hash for row in existing}
        fresh = []
        for row in batch:
            previous = known.get(row["sample_id"])
            if previous is None:
                fresh.append(row)
            elif previous == row["content_hash"]:
                stats["duplicates"] += 1
            else:
                stats["conflicts"] += 1
                stats["rejected"] += 1
        if fresh:
            await execute(
                text(
                    """INSERT INTO telemetry_samples (sample_id,vehicle_id,session_id,observed_at,signal_key,numeric_value,normalized_unit,raw_signal,raw_value,source,source_record_id,sequence_number,quality,schema_version,source_metadata,content_hash) SELECT :sample_id,s.vehicle_id,:session_id,:observed_at,:signal_key,:numeric_value,:normalized_unit,:raw_signal,:raw_value,:source,:source_record_id,:sequence_number,:quality,:schema_version,CAST(:source_metadata AS jsonb),:content_hash FROM driving_sessions s WHERE s.id=:session_id ON CONFLICT DO NOTHING"""
                ),
                fresh,
            )
            stats["accepted"] += len(fresh)


class QueryService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def query(
        self,
        session_id: UUID,
        signals: list[str],
        start: datetime | None,
        end: datetime | None,
        limit: int,
    ) -> TelemetryWindow:
        if start and end and start >= end:
            raise ValueError("start must precede end")
        async with self.database.session() as db:
            rows = (
                await db.execute(
                    text(
                        """SELECT sample_id,observed_at,signal_key,numeric_value,normalized_unit,quality,sequence_number FROM telemetry_samples WHERE session_id=:session_id AND signal_key = ANY(:signals) AND (CAST(:start AS timestamptz) IS NULL OR observed_at>=CAST(:start AS timestamptz)) AND (CAST(:end AS timestamptz) IS NULL OR observed_at<CAST(:end AS timestamptz)) ORDER BY observed_at,signal_key,COALESCE(sequence_number,-1),sample_id LIMIT :fetch"""
                    ),
                    {
                        "session_id": session_id,
                        "signals": signals,
                        "start": start,
                        "end": end,
                        "fetch": limit + 1,
                    },
                )
            ).all()
        truncated = len(rows) > limit
        rows = rows[:limit]
        points = [
            TelemetryPoint(
                sample_id=r.sample_id,
                observed_at=r.observed_at,
                signal=r.signal_key,
                value=r.numeric_value,
                unit=r.normalized_unit,
                quality=r.quality,
                sequence=r.sequence_number,
            )
            for r in rows
        ]
        return TelemetryWindow(
            session_id=session_id,
            points=points,
            returned=len(points),
            truncated=truncated,
            start=points[0].observed_at if points else None,
            end=points[-1].observed_at if points else None,
        )
