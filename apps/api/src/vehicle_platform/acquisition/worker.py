import asyncio
import hashlib
import json
import os
import signal
import sys
from collections import Counter, defaultdict, deque
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

from aiokafka import AIOKafkaConsumer

# asyncpg ships no PEP 561 metadata; only its runtime exception class is used.
from asyncpg import PostgresError  # type: ignore[import-untyped]
from opentelemetry import propagate
from prometheus_client import Gauge, start_http_server
from sqlalchemy import DateTime, String, bindparam, text
from sqlalchemy.engine import Result
from sqlalchemy.exc import SQLAlchemyError

from vehicle_platform.acquisition.quality import measure_signal_quality
from vehicle_platform.acquisition.recipes import BY_KEY
from vehicle_platform.analysis.alignment import align_observations
from vehicle_platform.analysis.detectors import HeuristicPullDetector, HeuristicSegmentDetector
from vehicle_platform.analysis.domain import DetectorProfile, Observation
from vehicle_platform.core.config import Settings
from vehicle_platform.events.domain import PullWindow
from vehicle_platform.events.engine import EventEngine
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.telemetry.domain import (
    SIGNAL_BY_KEY,
    normalize_value,
    parse_timestamp,
    sample_id,
    validate_sequence,
)


class StreamConsumer:
    def __init__(
        self, database: Database, settings: Settings, telemetry: Telemetry | None = None
    ) -> None:
        self.database, self.settings, self.running = database, settings, True
        self.telemetry = telemetry
        self.connected = False
        self.last_poll = 0.0
        self.windows: dict[UUID, deque[Observation]] = defaultdict(lambda: deque(maxlen=2000))
        self.counts: dict[UUID, int] = defaultdict(int)
        self.pipeline: dict[UUID, dict[str, object]] = {}

    @staticmethod
    def _prepare(envelope: dict[str, object]) -> dict[str, object]:
        if envelope.get("schema_version") != "1.0":
            raise ValueError("unsupported stream schema version")
        payload = envelope["payload"]
        if not isinstance(payload, dict):
            raise ValueError("stream payload must be an object")
        signal_key = str(payload["signal"])
        definition = SIGNAL_BY_KEY.get(signal_key)
        if definition is None:
            raise ValueError("unknown canonical signal")
        observed = parse_timestamp(str(envelope["observed_at"]))
        parse_timestamp(str(envelope["produced_at"]))
        value, quality = normalize_value(float(payload["value"]), str(payload["unit"]), definition)
        session_id = UUID(str(envelope["driving_session_id"]))
        source_id = str(envelope["source_id"])
        source_record_id = str(payload["source_record_id"])
        sequence_value = envelope.get("sequence")
        sequence = int(str(sequence_value)) if sequence_value is not None else None
        validate_sequence(sequence)
        sid = sample_id(
            str(session_id), source_id, source_record_id, observed, signal_key, sequence
        )
        return {
            "message_id": str(UUID(str(envelope["message_id"]))),
            "trace_context": envelope.get("provenance", {}),
            "acquisition_id": str(UUID(str(envelope["acquisition_session_id"]))),
            "session_id": str(session_id),
            "sample_id": sid,
            "observed_at": observed.isoformat(),
            "signal_key": signal_key,
            "value": value,
            "unit": definition.unit,
            "raw_value": str(payload["value"]),
            "source": source_id,
            "record_id": source_record_id,
            "sequence": sequence,
            "quality": quality.value,
            "metadata": {
                "produced_at": envelope["produced_at"],
                "batch_id": envelope["batch_id"],
                "source_unit": str(payload["unit"]),
            },
            "content_hash": hashlib.sha256(
                json.dumps([signal_key, value, definition.unit], separators=(",", ":")).encode()
            ).hexdigest(),
        }

    async def persist(self, envelope: dict[str, object]) -> bool:
        return bool(await self.persist_batch([envelope]))

    async def persist_batch(self, envelopes: list[dict[str, object]]) -> int:
        if len(envelopes) > 500:
            raise ValueError("consumer batch exceeds 500 observations")
        with (
            self.telemetry.tracer.start_as_current_span("acquisition.consumer.batch")
            if self.telemetry
            else nullcontext()
        ):
            return await self._persist_records([self._prepare(envelope) for envelope in envelopes])

    async def _persist_records(self, records: list[dict[str, object]]) -> int:
        if not records:
            return 0
        # A single bounded poll transaction avoids one fsync and several round trips
        # per observation. Receipts, samples and durable counters remain atomic.
        received_count = len(records)
        started = perf_counter()
        unique: dict[str, dict[str, object]] = {}
        for record in records:
            unique.setdefault(str(record["message_id"]), record)
        records = list(unique.values())
        async with self.database.session() as db:
            result: Result[tuple[UUID, int]] = await db.execute(
                text(
                    """WITH incoming AS (
                        SELECT * FROM jsonb_to_recordset(CAST(:records AS jsonb)) AS r(
                            message_id uuid, acquisition_id uuid, session_id uuid,
                            sample_id varchar, observed_at timestamptz, signal_key varchar,
                            value double precision, unit varchar, raw_value varchar,
                            source varchar, record_id varchar, sequence bigint,
                            quality varchar, metadata jsonb, content_hash varchar
                        )
                    ), receipts AS (
                        INSERT INTO stream_receipts(message_id,acquisition_session_id,topic)
                        SELECT message_id,acquisition_id,'telemetry.raw.v1' FROM incoming
                        ON CONFLICT DO NOTHING RETURNING message_id
                    ), samples AS (
                        INSERT INTO telemetry_samples(
                            sample_id,vehicle_id,session_id,observed_at,signal_key,numeric_value,
                            normalized_unit,raw_signal,raw_value,source,source_record_id,
                            sequence_number,quality,schema_version,source_metadata,content_hash
                        )
                        SELECT r.sample_id,s.vehicle_id,r.session_id,r.observed_at,r.signal_key,
                            r.value,r.unit,r.signal_key,r.raw_value,r.source,r.record_id,
                            r.sequence,r.quality,1,r.metadata,r.content_hash
                        FROM incoming r JOIN receipts USING(message_id)
                        JOIN driving_sessions s ON s.id=r.session_id
                        ON CONFLICT DO NOTHING RETURNING session_id
                    ), session_counts AS (
                        UPDATE driving_sessions s
                        SET sample_count=s.sample_count+c.added,updated_at=now()
                        FROM (SELECT session_id,count(*) AS added FROM samples
                              GROUP BY session_id) c
                        WHERE s.id=c.session_id
                    ), acquisition_sequences AS (
                        UPDATE acquisition_sessions a
                        SET last_sequence=GREATEST(COALESCE(a.last_sequence,-1),c.sequence),
                            updated_at=now()
                        FROM (SELECT acquisition_id,COALESCE(max(sequence),-1) AS sequence
                              FROM incoming JOIN receipts USING(message_id)
                              GROUP BY acquisition_id) c
                        WHERE a.id=c.acquisition_id
                    ) SELECT message_id,(SELECT count(*) FROM samples) AS added FROM receipts"""
                ),
                {"records": json.dumps(records)},
            )
            received = result.all()
            added = int(received[0][1]) if received else 0
            accepted = {str(row[0]) for row in received}
            await db.commit()
        if self.telemetry:
            self.telemetry.acquisition_persisted.add(added)
            self.telemetry.acquisition_duplicates.add(received_count - added)
            self.telemetry.db_batch_duration.record(perf_counter() - started, {"source": "stream"})
        for record in records:
            if str(record["message_id"]) not in accepted:
                continue
            acquisition_id = UUID(str(record["acquisition_id"]))
            if acquisition_id not in self.windows and len(self.windows) >= 10:
                # Retain only ten acquisition windows; canonical persistence is
                # unaffected by eviction of provisional in-memory state.
                oldest = next(iter(self.windows))
                self.windows.pop(oldest)
                self.counts.pop(oldest, None)
                self.pipeline.pop(oldest, None)
            measured_at = datetime.now(UTC)
            metadata = record["metadata"]
            if not isinstance(metadata, dict):
                raise ValueError("stream metadata must be an object")
            latency = (measured_at - parse_timestamp(str(metadata["produced_at"]))).total_seconds()
            self.pipeline[acquisition_id] = {
                "measured_at": measured_at.isoformat(),
                "publisher_to_persistence_seconds": latency if latency >= 0 else None,
                "broker_consumer_lag": record.get("broker_consumer_lag"),
                "persistence_state": "observations_committed",
            }
            self.windows[acquisition_id].append(
                Observation(
                    datetime.fromisoformat(str(record["observed_at"])),
                    str(record["signal_key"]),
                    float(str(record["value"])),
                    str(record["sample_id"]),
                )
            )
            self.counts[acquisition_id] += 1
            count = self.counts[acquisition_id]
            # Preserve existing event-time windows and provisional evaluation points.
            if count % 500 == 0 or count == 900:
                with (
                    self.telemetry.tracer.start_as_current_span("acquisition.live_analysis")
                    if self.telemetry
                    else nullcontext()
                ):
                    await self._provisional(acquisition_id)
        return len(accepted)

    def _live_window(self, acquisition_id: UUID) -> list[Observation]:
        observations = list(self.windows[acquisition_id])
        if not observations:
            return []
        cutoff = max(item.observed_at for item in observations) - timedelta(seconds=60)
        return [item for item in observations if item.observed_at >= cutoff]

    async def _provisional(self, acquisition_id: UUID) -> None:
        provisional_started = perf_counter()
        observations = self._live_window(acquisition_id)
        if not observations:
            return
        profile = DetectorProfile()
        frames = align_observations(observations, profile)
        segments = HeuristicSegmentDetector(profile).detect(frames)
        pulls = HeuristicPullDetector(profile).detect(frames)
        findings: list[tuple[str, str, datetime, datetime | None, dict[str, object]]] = []
        for segment in segments[-4:]:
            if segment.segment_type.value in {"idle", "acceleration", "pull", "deceleration"}:
                findings.append(
                    (
                        f"possible_{segment.segment_type.value}",
                        "performance",
                        segment.started_at,
                        segment.ended_at,
                        {
                            "confidence": segment.confidence,
                            "provisional": True,
                            "window_points": len(observations),
                        },
                    )
                )
        for pull in pulls[-2:]:
            if (
                pull.metrics.max_throttle
                and pull.metrics.max_throttle >= 70
                and pull.metrics.max_boost is not None
                and pull.metrics.max_boost < 80_000
            ):
                findings.append(
                    (
                        "boost_drop",
                        "performance",
                        pull.started_at,
                        pull.ended_at,
                        {
                            "max_boost": pull.metrics.max_boost,
                            "provisional": True,
                            "semantics": "factual low boost during detected pull; no diagnosis",
                        },
                    )
                )
        event_pulls = [
            PullWindow(
                pull.started_at,
                pull.ended_at,
                tuple(
                    frame
                    for frame in frames
                    if pull.started_at <= frame.observed_at <= pull.ended_at
                ),
            )
            for pull in pulls
        ]
        events, _states = EventEngine().analyze(frames, event_pulls)
        for event in events:
            findings.append(
                (
                    event.event_type,
                    event.category.value,
                    event.started_at,
                    event.ended_at,
                    {
                        **event.evidence,
                        "provisional": True,
                        "algorithm_name": event.algorithm_name,
                        "algorithm_version": event.algorithm_version,
                        "configuration_hash": event.configuration_hash,
                    },
                )
            )
        grouped: dict[str, list[datetime]] = defaultdict(list)
        for observation in observations:
            grouped[observation.signal].append(observation.observed_at)
        async with self.database.session() as db:
            recipe_key = str(
                (
                    await db.execute(
                        text("SELECT recipe_key FROM acquisition_sessions WHERE id=:id"),
                        {"id": acquisition_id},
                    )
                ).scalar_one()
            )
            targets = {item.signal: item.preferred_hz for item in BY_KEY[recipe_key].requirements}
            quality = {
                "adapter_connection_state": "not_reported",
                "persistence_state": "observations_committed",
                "pipeline": self.pipeline.get(acquisition_id),
                "observations_persisted": self.counts[acquisition_id],
                "duplicate_count": None,
                "dropped_sample_count": None,
                "queue_lag": None,
                "broker_consumer_lag": None,
                "local_spool_occupancy": None,
                "signals": [
                    measure_signal_quality(key, tuple(times), targets.get(key, 1)).__dict__
                    for key, times in grouped.items()
                ],
            }
            produced: Counter[str] = Counter()
            for finding_type, category, started, ended, evidence in findings:
                inserted = await db.execute(
                    text(
                        """INSERT INTO provisional_findings(acquisition_session_id,finding_type,category,started_at,ended_at,evidence) SELECT :id,:type,:category,:started,:ended,CAST(:evidence AS jsonb) WHERE NOT EXISTS (SELECT 1 FROM provisional_findings WHERE acquisition_session_id=:id AND finding_type=:type AND started_at=:started) RETURNING category"""
                    ).bindparams(
                        bindparam("type", type_=String()),
                        bindparam("category", type_=String()),
                        bindparam("started", type_=DateTime(timezone=True)),
                        bindparam("ended", type_=DateTime(timezone=True)),
                    ),
                    {
                        "id": acquisition_id,
                        "type": finding_type,
                        "category": category,
                        "started": started,
                        "ended": ended,
                        "evidence": json.dumps(evidence),
                    },
                )
                produced.update(inserted.scalars().all())
            await db.execute(
                text(
                    "UPDATE acquisition_sessions SET quality=quality || CAST(:quality AS jsonb),updated_at=now() WHERE id=:id"
                ),
                {"id": acquisition_id, "quality": json.dumps(quality)},
            )
            await db.commit()
        if self.telemetry:
            self.telemetry.live_analysis_latency.record(
                perf_counter() - provisional_started, {"outcome": "provisional"}
            )
            for category, count in produced.items():
                self.telemetry.provisional_events.add(count, {"category": category})

    async def run(self) -> None:
        consumer = AIOKafkaConsumer(
            "telemetry.raw.v1",
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id="canonical-telemetry-v1",
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            max_poll_records=500,
        )
        await consumer.start()
        self.connected = True
        try:
            while self.running:
                records = await consumer.getmany(timeout_ms=1000, max_records=500)
                self.last_poll = perf_counter()
                prepared: list[dict[str, object]] = []
                for partition, messages in records.items():
                    highwater = consumer.highwater(partition)
                    if self.telemetry and messages and highwater is not None:
                        self.telemetry.consumer_lag.record(
                            max(0, highwater - messages[-1].offset - 1)
                        )
                    for message in messages:
                        try:
                            prepared_record = self._prepare(json.loads(message.value))
                            prepared_record["broker_consumer_lag"] = (
                                max(0, highwater - messages[-1].offset - 1)
                                if highwater is not None
                                else None
                            )
                            prepared.append(prepared_record)
                        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                            category = (
                                "malformed_json"
                                if isinstance(exc, json.JSONDecodeError)
                                else "invalid_stream_contract"
                            )
                            if self.telemetry:
                                self.telemetry.acquisition_dropped.add(1, {"reason": category})
                            message_id = hashlib.sha256(message.value).hexdigest()
                            async with self.database.session() as db:
                                await db.execute(
                                    text(
                                        "INSERT INTO stream_dead_letters(message_id,topic,error_category) VALUES(:id,:topic,:category) ON CONFLICT DO NOTHING"
                                    ),
                                    {
                                        "id": message_id,
                                        "topic": "telemetry.raw.v1",
                                        "category": category,
                                    },
                                )
                                await db.commit()
                carrier = prepared[0].get("trace_context") if prepared else None
                context = propagate.extract(carrier) if isinstance(carrier, dict) else None
                with (
                    self.telemetry.tracer.start_as_current_span(
                        "acquisition.consumer.persistence", context=context
                    )
                    if self.telemetry
                    else nullcontext()
                ):
                    await self._persist_records(prepared)
                if records:
                    await consumer.commit()
        finally:
            self.connected = False
            await consumer.stop()
            await self.database.close()


async def main() -> None:
    settings = Settings()
    database = Database(settings)
    telemetry = Telemetry(settings, database, "vehicle-platform-stream-consumer")
    worker = StreamConsumer(database, settings, telemetry)
    healthy = Gauge(
        "acquisition_consumer_ready",
        "Connected consumer with recent successful poll",
        registry=telemetry.registry,
    )
    healthy.set_function(lambda: int(worker.connected and perf_counter() - worker.last_poll < 30))
    buffered = Gauge(
        "acquisition_consumer_buffered_points",
        "Actual observations retained across bounded analysis windows",
        registry=telemetry.registry,
    )
    buffered.set_function(lambda: sum(len(window) for window in worker.windows.values()))
    start_http_server(
        8001, addr=os.environ.get("WORKER_METRICS_HOST", "127.0.0.1"), registry=telemetry.registry
    )
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, setattr, worker, "running", False)
    try:
        await worker.run()
    finally:
        telemetry.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (SQLAlchemyError, PostgresError):
        # Driver exception strings can contain SQL parameters or credentials.
        # Fail visibly and let the process restart without committing offsets.
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": "ERROR",
                    "service": "vehicle-platform-stream-consumer",
                    "event": "stream.persistence_failed",
                    "error_category": "database_error",
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
