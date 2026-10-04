import asyncio
import hashlib
import json
import secrets
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

from aiokafka import (
    AIOKafkaConsumer,
    AIOKafkaProducer,
    TopicPartition,
)
from opentelemetry import propagate
from sqlalchemy import DateTime, bindparam, text

from vehicle_platform.acquisition.adapters import SyntheticLiveAdapter
from vehicle_platform.acquisition.domain import preflight
from vehicle_platform.acquisition.quality import SignalQuality, assess_dataset, collector_health
from vehicle_platform.acquisition.recipes import BY_KEY
from vehicle_platform.analysis.service import SessionAnalysisService
from vehicle_platform.api.domain_contracts import (
    AcquisitionBatch,
    AcquisitionBatchAccepted,
    AcquisitionCreate,
    AcquisitionCreated,
    AcquisitionFinalized,
    AcquisitionHeartbeat,
    AcquisitionStatusResponse,
    DatasetCapabilityReport,
    StreamObservation,
)
from vehicle_platform.core.config import Settings
from vehicle_platform.events.service import EventAnalysisService
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.telemetry.domain import (
    SIGNAL_BY_KEY,
    NormalizationError,
    RawTelemetryRecord,
    normalize_value,
)
from vehicle_platform.telemetry.service import validate_vehicle_context

TOPIC = "telemetry.raw.v1"


class AcquisitionError(ValueError):
    pass


class AcquisitionAuthError(PermissionError):
    pass


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AcquisitionPublisher:
    """Application-owned producer; bounded concurrent publication and shutdown."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.producer: AIOKafkaProducer | None = None
        self.lock = asyncio.Lock()
        self.capacity = asyncio.Semaphore(8)

    async def get(self) -> AIOKafkaProducer:
        async with self.lock:
            if self.producer is None:
                producer = AIOKafkaProducer(
                    bootstrap_servers=self.settings.kafka_bootstrap_servers,
                    acks="all",
                    enable_idempotence=True,
                    request_timeout_ms=5000,
                )
                try:
                    await producer.start()
                except BaseException:
                    await producer.stop()
                    raise
                self.producer = producer
            return self.producer

    async def close(self) -> None:
        if self.producer is not None:
            await self.producer.stop()
            self.producer = None


class AcquisitionService:
    def __init__(
        self,
        database: Database,
        settings: Settings,
        telemetry: Telemetry,
        publisher: AcquisitionPublisher | None = None,
    ) -> None:
        self.database, self.settings, self.telemetry = database, settings, telemetry
        self.publisher = publisher

    async def create(self, payload: AcquisitionCreate) -> AcquisitionCreated:
        recipe = BY_KEY.get(payload.recipe_key)
        if recipe is None:
            raise AcquisitionError("unknown logging recipe")
        token = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) + timedelta(seconds=self.settings.acquisition_token_ttl_seconds)
        async with self.database.session() as db:
            configuration_id = payload.configuration_id
            if configuration_id is None:
                configuration_id = await db.scalar(
                    text(
                        "SELECT id FROM vehicle_configurations WHERE vehicle_id=:vehicle "
                        "AND effective_at<=now() AND (ended_at IS NULL OR ended_at>now()) "
                        "ORDER BY effective_at DESC,id LIMIT 1"
                    ),
                    {"vehicle": payload.vehicle_id},
                )
            try:
                await validate_vehicle_context(
                    db, payload.vehicle_id, configuration_id, datetime.now(UTC)
                )
            except (LookupError, ValueError) as exc:
                raise AcquisitionError("invalid vehicle configuration association") from exc
            await db.execute(text("SELECT pg_advisory_xact_lock(440010)"))
            active = int(
                (
                    await db.execute(
                        text(
                            "SELECT count(*) FROM acquisition_sessions "
                            "WHERE state IN ('created','active','disconnected') "
                            "AND token_expires_at>clock_timestamp()"
                        )
                    )
                ).scalar_one()
            )
            if active >= 10:
                raise AcquisitionError("concurrent acquisition session limit reached")
            driving: UUID = (
                await db.execute(
                    text(
                        """INSERT INTO driving_sessions(vehicle_id,configuration_id,source_type,source_reference,started_at,metadata,status) VALUES(:vehicle_id,:configuration_id,:source_type,:source_reference,now(),CAST(:metadata AS jsonb),'ingesting') RETURNING id"""
                    ),
                    {
                        "vehicle_id": payload.vehicle_id,
                        "configuration_id": configuration_id,
                        "source_type": {"obd": "obd", "replay": "csv", "synthetic": "synthetic"}[
                            payload.adapter
                        ],
                        "source_reference": payload.source_id,
                        "metadata": json.dumps(
                            {"recipe_key": recipe.key, "recipe_version": recipe.version}
                        ),
                    },
                )
            ).scalar_one()
            row = (
                (
                    await db.execute(
                        text(
                            """INSERT INTO acquisition_sessions(driving_session_id,recipe_key,recipe_version,recipe_configuration_hash,adapter,state,token_hash,token_expires_at,quality) VALUES(:driving,:key,:version,:hash,:adapter,'active',:token_hash,:expires,'{}') RETURNING id,started_at"""
                        ),
                        {
                            "driving": driving,
                            "key": recipe.key,
                            "version": recipe.version,
                            "hash": recipe.configuration_hash,
                            "adapter": payload.adapter,
                            "token_hash": token_hash(token),
                            "expires": expires,
                        },
                    )
                )
                .mappings()
                .one()
            )
            await db.commit()
        self.telemetry.acquisition_active.add(1, {"state": "active"})
        return AcquisitionCreated(
            id=row["id"],
            driving_session_id=driving,
            state="active",
            ingestion_token=token,
            token_expires_at=expires,
        )

    async def _authorized(
        self, acquisition_id: UUID, token: str, *, active: bool = True
    ) -> dict[str, object]:
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT a.*,s.vehicle_id,s.configuration_id FROM acquisition_sessions a "
                            "JOIN driving_sessions s ON s.id=a.driving_session_id WHERE a.id=:id"
                        ),
                        {"id": acquisition_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None or not secrets.compare_digest(str(row["token_hash"]), token_hash(token)):
            raise AcquisitionAuthError("invalid acquisition credential")
        if row["token_expires_at"] <= datetime.now(UTC):
            raise AcquisitionAuthError("expired acquisition credential")
        if active and row["state"] != "active":
            raise AcquisitionAuthError("acquisition session is not active")
        return dict(row)

    async def publish(
        self, acquisition_id: UUID, token: str, batch: AcquisitionBatch
    ) -> AcquisitionBatchAccepted:
        if len(batch.observations) > self.settings.acquisition_batch_limit:
            raise AcquisitionError("observation batch exceeds configured limit")
        session = await self._authorized(acquisition_id, token)
        for item in batch.observations:
            definition = SIGNAL_BY_KEY.get(item.signal)
            if definition is None:
                raise AcquisitionError("unknown canonical signal")
            try:
                normalize_value(item.value, item.unit, definition)
            except NormalizationError as exc:
                raise AcquisitionError("invalid telemetry signal or unit") from exc
        now = datetime.now(UTC)
        if any(
            abs((item.observed_at.astimezone(UTC) - now).total_seconds()) > 86400
            for item in batch.observations
        ):
            raise AcquisitionError("observation timestamp outside accepted window")
        publisher = self.publisher or AcquisitionPublisher(self.settings)
        started = perf_counter()
        try:
            async with asyncio.timeout(15), publisher.capacity:
                producer = await publisher.get()
                async with self.database.session() as db:
                    state = await db.scalar(
                        text("SELECT state FROM acquisition_sessions WHERE id=:id FOR UPDATE"),
                        {"id": acquisition_id},
                    )
                    if state != "active":
                        raise AcquisitionAuthError("acquisition session is not active")
                    for observed in (
                        min(item.observed_at for item in batch.observations),
                        max(item.observed_at for item in batch.observations),
                    ):
                        try:
                            await validate_vehicle_context(
                                db,
                                UUID(str(session["vehicle_id"])),
                                UUID(str(session["configuration_id"]))
                                if session["configuration_id"]
                                else None,
                                observed,
                            )
                        except ValueError as exc:
                            raise AcquisitionError(
                                "configuration not effective for observations"
                            ) from exc
                    # Stop takes the same row lock. Its broker snapshot therefore
                    # includes every publication acknowledged before stopping.
                    await self._send_batch(producer, acquisition_id, session, batch, now)
                    await db.commit()
        except Exception:
            self.telemetry.stream_publish_failures.add(1, {"classification": "broker_unavailable"})
            raise
        finally:
            if self.publisher is None:
                await publisher.close()
        self.telemetry.acquisition_observations.add(len(batch.observations), {"source": "gateway"})
        self.telemetry.live_analysis_latency.record(
            perf_counter() - started, {"outcome": "published"}
        )
        return AcquisitionBatchAccepted(batch_id=batch.batch_id, accepted=len(batch.observations))

    async def _send_batch(
        self,
        producer: AIOKafkaProducer,
        acquisition_id: UUID,
        session: dict[str, object],
        batch: AcquisitionBatch,
        now: datetime,
    ) -> None:
        sends = []
        trace_context: dict[str, str] = {}
        propagate.inject(trace_context)
        for item in batch.observations:
            envelope = {
                "schema_version": batch.schema_version,
                "message_id": str(item.message_id),
                "batch_id": str(batch.batch_id),
                "acquisition_session_id": str(acquisition_id),
                "driving_session_id": str(session["driving_session_id"]),
                "source_id": str(session["adapter"]),
                "vehicle_reference": "database-reference",
                "observed_at": item.observed_at.astimezone(UTC).isoformat(),
                "produced_at": now.isoformat(),
                "sequence": item.sequence,
                "provenance": {"gateway": "api-v1", **trace_context},
                "payload": {
                    "signal": item.signal,
                    "value": item.value,
                    "unit": item.unit,
                    "source_record_id": item.source_record_id,
                },
            }
            sends.append(
                producer.send_and_wait(
                    TOPIC,
                    json.dumps(envelope, separators=(",", ":")).encode(),
                    key=str(acquisition_id).encode(),
                )
            )
        started = perf_counter()
        outcome = "failed"
        try:
            await asyncio.gather(*sends)
            outcome = "acknowledged"
        finally:
            self.telemetry.broker_publish_duration.record(
                perf_counter() - started, {"outcome": outcome}
            )

    async def run_synthetic(
        self, acquisition_id: UUID, token: str, scenario: str = "boost_drop"
    ) -> None:
        session = await self._authorized(acquisition_id, token)
        recipe = BY_KEY[str(session["recipe_key"])]
        adapter = SyntheticLiveAdapter(scenario=scenario, samples=300, speed=5)
        await adapter.connect()
        capabilities = await adapter.capabilities()
        plan = preflight(recipe, capabilities).sampling_plan
        collection_started = datetime.now(UTC)
        last_receipt: datetime | None = None

        async def report(state: str) -> None:
            await self.heartbeat(
                acquisition_id,
                token,
                AcquisitionHeartbeat.model_validate(
                    {
                        "adapter_state": state,
                        "collection_started_at": collection_started,
                        "last_sample_received_at": last_receipt,
                        "queue_observations": 0,
                        "spool_bytes": 0,
                        "dropped_observations": 0,
                        "capability_snapshot": asdict(capabilities),
                        "sampling_plan": [asdict(item) for item in plan],
                    }
                ),
            )

        try:
            await report("connected")
            records = []
            async for record in adapter.read(plan):
                last_receipt = datetime.now(UTC)
                records.append(record)
                if len(records) == 100:
                    await self._publish_records(acquisition_id, token, records)
                    await report("connected")
                    records.clear()
            if records:
                await self._publish_records(acquisition_id, token, records)
        except AcquisitionAuthError:
            self.telemetry.logger.info("acquisition.synthetic_stopped")
        finally:
            try:
                await report("disconnected")
            except AcquisitionAuthError:
                pass  # Stop already closed this scoped credential.
            finally:
                await adapter.close()

    async def _publish_records(
        self, acquisition_id: UUID, token: str, records: list[RawTelemetryRecord]
    ) -> None:
        from uuid import uuid4

        batch = AcquisitionBatch(
            schema_version="1.0",
            batch_id=uuid4(),
            observations=[
                StreamObservation(
                    message_id=uuid4(),
                    observed_at=item.observed_at,
                    sequence=item.sequence,
                    signal=item.signal,
                    value=item.value,
                    unit=item.unit,
                    source_record_id=item.source_record_id,
                )
                for item in records
            ],
        )
        await self.publish(acquisition_id, token, batch)

    async def heartbeat(
        self, acquisition_id: UUID, token: str, payload: AcquisitionHeartbeat
    ) -> AcquisitionStatusResponse:
        await self._authorized(acquisition_id, token)
        now = datetime.now(UTC)
        if payload.collection_started_at > now + timedelta(seconds=5) or (
            payload.last_sample_received_at
            and payload.last_sample_received_at > now + timedelta(seconds=5)
        ):
            raise AcquisitionError("collector receipt time is in the future")
        report = payload.model_dump(mode="json") | {"received_at": now.isoformat()}
        async with self.database.session() as db:
            changed = await db.scalar(
                text(
                    "UPDATE acquisition_sessions SET quality=quality || "
                    "jsonb_build_object('collector',CAST(:report AS jsonb)),updated_at=now() "
                    "WHERE id=:id AND state='active' RETURNING id"
                ),
                {"id": acquisition_id, "report": json.dumps(report)},
            )
            if changed is None:
                raise AcquisitionAuthError("acquisition session is not active")
            await db.commit()
        self.telemetry.collector_heartbeats.add(1, {"state": payload.adapter_state})
        return await self.status(acquisition_id)

    async def status(self, acquisition_id: UUID) -> AcquisitionStatusResponse:
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text("SELECT * FROM acquisition_sessions WHERE id=:id"),
                        {"id": acquisition_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise LookupError
        response = AcquisitionStatusResponse.model_validate(row)
        response.quality["collector_health"] = collector_health(response.quality, datetime.now(UTC))
        return response

    async def stop(self, acquisition_id: UUID, token: str) -> AcquisitionStatusResponse:
        await self._authorized(acquisition_id, token)
        async with self.database.session() as db:
            await db.execute(
                text(
                    "UPDATE acquisition_sessions SET state='stopping',ended_at=GREATEST(started_at,clock_timestamp()),updated_at=clock_timestamp(),token_expires_at=clock_timestamp() WHERE id=:id"
                ),
                {"id": acquisition_id},
            )
            await db.commit()
        self.telemetry.acquisition_active.add(-1, {"state": "active"})
        return await self.status(acquisition_id)

    async def finalize(self, acquisition_id: UUID) -> AcquisitionFinalized:
        # Keep the transaction advisory lock on a dedicated connection while
        # canonical services use their own transactions. Retry after a crash is
        # safe; concurrent finalizations cannot execute the pipeline twice.
        async with self.database.session() as guard:
            identity = int.from_bytes(acquisition_id.bytes[:8], "big", signed=True)
            await guard.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": identity})
            status = await self.status(acquisition_id)
            if status.state not in {"stopping", "finalizing", "completed"}:
                raise AcquisitionError("acquisition must be stopped before finalization")
            await self._await_persistence()
            return await self._finalize(acquisition_id)

    async def _await_persistence(self) -> None:
        consumer = AIOKafkaConsumer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id="canonical-telemetry-v1",
            enable_auto_commit=False,
        )
        # Manual assignment loads topic metadata without joining/rebalancing the
        # canonical consumer group; this observer never commits any offsets.
        consumer.assign([TopicPartition(TOPIC, 0)])
        try:
            async with asyncio.timeout(15):
                await consumer.start()
                partitions = consumer.partitions_for_topic(TOPIC)
                if not partitions or len(partitions) > 64:
                    raise AcquisitionError("stream partitions unavailable or outside bounds")
                positions = await consumer.end_offsets(
                    [TopicPartition(TOPIC, partition) for partition in sorted(partitions)]
                )
                while True:
                    committed = await asyncio.gather(
                        *(consumer.committed(partition) for partition in positions)
                    )
                    if all(
                        expected == 0 or (offset is not None and offset >= expected)
                        for offset, expected in zip(committed, positions.values(), strict=True)
                    ):
                        return
                    await asyncio.sleep(0.1)
        except AcquisitionError:
            raise
        except Exception as exc:
            raise AcquisitionError(
                "canonical stream has not drained; restore dependencies and retry finalization"
            ) from exc
        finally:
            await consumer.stop()

    async def _finalize(self, acquisition_id: UUID) -> AcquisitionFinalized:
        started = perf_counter()
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "UPDATE acquisition_sessions SET state='finalizing',updated_at=now() WHERE id=:id AND state IN ('stopping','finalizing','completed') RETURNING *"
                        ),
                        {"id": acquisition_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise AcquisitionError("acquisition must be stopped before finalization")
            await db.commit()
        driving_id = row["driving_session_id"]
        phase2 = await SessionAnalysisService(self.database, self.telemetry).run(
            driving_id, "bmw-f30-n55-heuristic-v1", False
        )
        phase3 = await EventAnalysisService(self.database, self.telemetry).run(driving_id, False)
        report = await self.capability_report(
            driving_id,
            str(row["recipe_key"]),
            configuration_hash=str(row["recipe_configuration_hash"]),
        )
        async with self.database.session() as db:
            provisional_rows = (
                (
                    await db.execute(
                        text(
                            "SELECT id,finding_type,started_at,ended_at FROM provisional_findings WHERE acquisition_session_id=:id AND status='provisional'"
                        ),
                        {"id": acquisition_id},
                    )
                )
                .mappings()
                .all()
            )
            confirmed = 0
            for finding in provisional_rows:
                if not str(finding["finding_type"]).startswith("possible_"):
                    canonical = (
                        await db.execute(
                            text(
                                "SELECT id FROM detected_events WHERE session_id=:sid AND event_type=:type AND started_at<=COALESCE(:ended,:started) AND ended_at>=:started LIMIT 1"
                            ).bindparams(
                                bindparam("started", type_=DateTime(timezone=True)),
                                bindparam("ended", type_=DateTime(timezone=True)),
                            ),
                            {
                                "sid": driving_id,
                                "type": finding["finding_type"],
                                "started": finding["started_at"],
                                "ended": finding["ended_at"],
                            },
                        )
                    ).scalar_one_or_none()
                elif finding["finding_type"] == "possible_pull":
                    canonical = (
                        await db.execute(
                            text(
                                "SELECT id FROM pulls WHERE session_id=:sid AND started_at<=COALESCE(:ended,:started) AND ended_at>=:started LIMIT 1"
                            ).bindparams(
                                bindparam("started", type_=DateTime(timezone=True)),
                                bindparam("ended", type_=DateTime(timezone=True)),
                            ),
                            {
                                "sid": driving_id,
                                "started": finding["started_at"],
                                "ended": finding["ended_at"],
                            },
                        )
                    ).scalar_one_or_none()
                else:
                    canonical = (
                        await db.execute(
                            text(
                                "SELECT id FROM session_segments WHERE session_id=:sid AND segment_type=:type AND started_at<=COALESCE(:ended,:started) AND ended_at>=:started LIMIT 1"
                            ).bindparams(
                                bindparam("started", type_=DateTime(timezone=True)),
                                bindparam("ended", type_=DateTime(timezone=True)),
                            ),
                            {
                                "sid": driving_id,
                                "type": str(finding["finding_type"]).removeprefix("possible_"),
                                "started": finding["started_at"],
                                "ended": finding["ended_at"],
                            },
                        )
                    ).scalar_one_or_none()
                if canonical is not None:
                    confirmed += 1
                    await db.execute(
                        text(
                            "UPDATE provisional_findings SET status='confirmed',canonical_reference=:canonical WHERE id=:id"
                        ),
                        {"canonical": canonical, "id": finding["id"]},
                    )
            await db.execute(
                text(
                    "UPDATE provisional_findings SET status='absent' WHERE acquisition_session_id=:id AND status='provisional'"
                ),
                {"id": acquisition_id},
            )
            await db.execute(
                text(
                    "UPDATE acquisition_sessions SET state='completed',quality=quality || CAST(:quality AS jsonb),updated_at=now() WHERE id=:id"
                ),
                {"id": acquisition_id, "quality": json.dumps(report)},
            )
            await db.execute(
                text(
                    "UPDATE driving_sessions SET status='completed',sample_count=(SELECT count(*) FROM telemetry_samples WHERE session_id=:sid),started_at=COALESCE((SELECT min(observed_at) FROM telemetry_samples WHERE session_id=:sid),started_at),ended_at=COALESCE((SELECT max(observed_at) FROM telemetry_samples WHERE session_id=:sid),GREATEST(started_at,clock_timestamp())),updated_at=clock_timestamp() WHERE id=:sid"
                ),
                {"sid": driving_id},
            )
            await db.commit()
        self.telemetry.finalization_duration.record(
            perf_counter() - started, {"outcome": "completed"}
        )
        return AcquisitionFinalized(
            id=acquisition_id,
            state="completed",
            phase2=phase2,
            phase3=phase3,
            capability_report=DatasetCapabilityReport.model_validate(report),
            reconciliation={"confirmed": confirmed, "absent": len(provisional_rows) - confirmed},
        )

    async def _capability_report(
        self, session_id: UUID, recipe_key: str, config_hash: str
    ) -> dict[str, object]:
        recipe = BY_KEY[recipe_key]
        targets = {item.signal: item.preferred_hz for item in recipe.requirements}
        # PostgreSQL aggregates the indexed session selection. The application
        # receives one row per canonical signal, not an unbounded timestamp array.
        async with self.database.session() as db:
            rows = (
                (
                    await db.execute(
                        text("""WITH times AS (
                        SELECT DISTINCT signal_key,observed_at FROM telemetry_samples
                        WHERE session_id=:id AND quality='valid'
                    ), intervals AS (
                        SELECT signal_key,observed_at,
                          extract(epoch FROM observed_at-lag(observed_at) OVER (
                            PARTITION BY signal_key ORDER BY observed_at)) AS delta,
                          COALESCE((CAST(:targets AS jsonb)->>signal_key)::double precision,1) AS target
                        FROM times
                    ) SELECT signal_key,min(observed_at) AS first_at,max(observed_at) AS last_at,
                      count(*) AS points,max(target) AS target,
                      COALESCE(avg(abs(delta-1/target))*1000,0) AS jitter,
                      count(*) FILTER (WHERE delta>GREATEST(2/target,1)) AS gaps,
                      COALESCE(max(delta),0) AS max_gap
                    FROM intervals GROUP BY signal_key ORDER BY signal_key"""),
                        {"id": session_id, "targets": json.dumps(targets)},
                    )
                )
                .mappings()
                .all()
            )
        async with self.database.session() as db:
            observation_count = int(
                await db.scalar(
                    text("SELECT count(*) FROM telemetry_samples WHERE session_id=:id"),
                    {"id": session_id},
                )
                or 0
            )
        duration = (
            (max(r["last_at"] for r in rows) - min(r["first_at"] for r in rows)).total_seconds()
            if rows
            else 0
        )
        qualities = []
        for row in rows:
            count, target = int(row["points"]), float(row["target"])
            seconds = (row["last_at"] - row["first_at"]).total_seconds()
            expected = seconds * target + 1
            qualities.append(
                SignalQuality(
                    str(row["signal_key"]),
                    target,
                    (count - 1) / seconds if seconds > 0 else 0,
                    float(row["jitter"]),
                    int(row["gaps"]) / (count - 1) if count > 1 else 1,
                    max(0.0, min(1.0, 1 - count / expected)) if count > 1 else 1,
                )
            )
        available = {q.signal: q for q in qualities}
        capabilities = assess_dataset(tuple(qualities), duration)
        return {
            "assessment_version": "1.1.0",
            "recipe_configuration_hash": config_hash,
            "duration_seconds": duration,
            "observation_count": observation_count,
            "available_signals": sorted(available),
            "signal_quality": [q.__dict__ for q in qualities],
            "gaps_by_signal": {
                str(r["signal_key"]): {
                    "count": int(r["gaps"]),
                    "maximum_seconds": float(r["max_gap"]),
                }
                for r in rows
            },
            "capabilities": [c.__dict__ for c in capabilities],
            "recipe_adherence": duration >= recipe.minimum_duration_seconds
            and all(
                r.signal in available
                and available[r.signal].actual_hz >= r.minimum_hz
                and available[r.signal].missing_ratio < 0.5
                for r in recipe.requirements
                if r.importance.value == "required"
            ),
        }

    async def capability_report(
        self, session_id: UUID, recipe_key: str, *, configuration_hash: str | None = None
    ) -> dict[str, object]:
        recipe = BY_KEY.get(recipe_key)
        if recipe is None:
            raise AcquisitionError("unknown logging recipe")
        async with self.database.session() as db:
            if (
                await db.scalar(
                    text("SELECT 1 FROM driving_sessions WHERE id=:id"), {"id": session_id}
                )
                is None
            ):
                raise LookupError("session not found")
        config_hash = configuration_hash or recipe.configuration_hash
        report = await self._capability_report(session_id, recipe_key, config_hash)
        async with self.database.session() as db:
            await db.execute(
                text(
                    """INSERT INTO dataset_capability_reports(driving_session_id,recipe_key,recipe_configuration_hash,duration_seconds,report) VALUES(:session,:recipe,:hash,:duration,CAST(:report AS jsonb)) ON CONFLICT ON CONSTRAINT uq_dataset_capability_recipe DO UPDATE SET duration_seconds=EXCLUDED.duration_seconds,report=EXCLUDED.report,created_at=now()"""
                ),
                {
                    "session": session_id,
                    "recipe": recipe_key,
                    "hash": config_hash,
                    "duration": report["duration_seconds"],
                    "report": json.dumps(report),
                },
            )
            await db.commit()
        return report
