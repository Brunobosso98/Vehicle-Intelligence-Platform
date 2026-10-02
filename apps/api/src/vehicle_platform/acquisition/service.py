import asyncio
import hashlib
import json
import secrets
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

from aiokafka import AIOKafkaProducer  # type: ignore[import-untyped]
from sqlalchemy import text

from vehicle_platform.acquisition.adapters import SyntheticLiveAdapter
from vehicle_platform.acquisition.domain import preflight
from vehicle_platform.acquisition.quality import assess_dataset, measure_signal_quality
from vehicle_platform.acquisition.recipes import BY_KEY
from vehicle_platform.analysis.service import SessionAnalysisService
from vehicle_platform.api.domain_contracts import (
    AcquisitionBatch,
    AcquisitionBatchAccepted,
    AcquisitionCreate,
    AcquisitionCreated,
    AcquisitionFinalized,
    AcquisitionStatusResponse,
    StreamObservation,
)
from vehicle_platform.core.config import Settings
from vehicle_platform.events.service import EventAnalysisService
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.telemetry.domain import RawTelemetryRecord

TOPIC = "telemetry.raw.v1"


class AcquisitionError(ValueError):
    pass


class AcquisitionAuthError(PermissionError):
    pass


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AcquisitionService:
    def __init__(self, database: Database, settings: Settings, telemetry: Telemetry) -> None:
        self.database, self.settings, self.telemetry = database, settings, telemetry

    async def create(self, payload: AcquisitionCreate) -> AcquisitionCreated:
        recipe = BY_KEY.get(payload.recipe_key)
        if recipe is None:
            raise AcquisitionError("unknown logging recipe")
        token = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) + timedelta(seconds=self.settings.acquisition_token_ttl_seconds)
        async with self.database.session() as db:
            active = int(
                (
                    await db.execute(
                        text(
                            "SELECT count(*) FROM acquisition_sessions WHERE state IN ('created','active','disconnected','stopping','finalizing')"
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
                        "configuration_id": payload.configuration_id,
                        "source_type": "obd" if payload.adapter == "obd" else "synthetic",
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
                        text("SELECT * FROM acquisition_sessions WHERE id=:id"),
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
        now = datetime.now(UTC)
        if any(
            abs((item.observed_at.astimezone(UTC) - now).total_seconds()) > 86400
            for item in batch.observations
        ):
            raise AcquisitionError("observation timestamp outside accepted window")
        producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            acks="all",
            enable_idempotence=True,
            request_timeout_ms=5000,
        )
        started = perf_counter()
        try:
            await producer.start()
            sends = []
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
                    "provenance": {"gateway": "api-v1"},
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
            await asyncio.gather(*sends)
        except Exception:
            self.telemetry.stream_publish_failures.add(1, {"classification": "broker_unavailable"})
            raise
        finally:
            await producer.stop()
        self.telemetry.acquisition_observations.add(len(batch.observations), {"source": "gateway"})
        self.telemetry.live_analysis_latency.record(
            perf_counter() - started, {"outcome": "published"}
        )
        return AcquisitionBatchAccepted(batch_id=batch.batch_id, accepted=len(batch.observations))

    async def run_synthetic(
        self, acquisition_id: UUID, token: str, scenario: str = "boost_drop"
    ) -> None:
        session = await self._authorized(acquisition_id, token)
        recipe = BY_KEY[str(session["recipe_key"])]
        adapter = SyntheticLiveAdapter(scenario=scenario, samples=120, speed=5)
        await adapter.connect()
        plan = preflight(recipe, await adapter.capabilities()).sampling_plan
        records = []
        async for record in adapter.read(plan):
            records.append(record)
            if len(records) == 100:
                await self._publish_records(acquisition_id, token, records)
                records.clear()
        if records:
            await self._publish_records(acquisition_id, token, records)
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
        return AcquisitionStatusResponse.model_validate(row)

    async def stop(self, acquisition_id: UUID, token: str) -> AcquisitionStatusResponse:
        await self._authorized(acquisition_id, token)
        async with self.database.session() as db:
            await db.execute(
                text(
                    "UPDATE acquisition_sessions SET state='stopping',ended_at=now(),updated_at=now(),token_expires_at=now() WHERE id=:id"
                ),
                {"id": acquisition_id},
            )
            await db.commit()
        self.telemetry.acquisition_active.add(-1, {"state": "active"})
        return await self.status(acquisition_id)

    async def finalize(self, acquisition_id: UUID) -> AcquisitionFinalized:
        started = perf_counter()
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "UPDATE acquisition_sessions SET state='finalizing',updated_at=now() WHERE id=:id AND state='stopping' RETURNING *"
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
        phase2 = await SessionAnalysisService(self.database).run(
            driving_id, "bmw-f30-n55-heuristic-v1", False
        )
        phase3 = await EventAnalysisService(self.database, self.telemetry).run(driving_id, False)
        report = await self._capability_report(
            driving_id, str(row["recipe_key"]), str(row["recipe_configuration_hash"])
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
                if finding["finding_type"] == "boost_drop":
                    canonical = (
                        await db.execute(
                            text(
                                "SELECT id FROM detected_events WHERE session_id=:sid AND event_type='boost_drop' AND started_at<=COALESCE(:ended,:started) AND ended_at>=:started LIMIT 1"
                            ),
                            {
                                "sid": driving_id,
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
                            ),
                            {
                                "sid": driving_id,
                                "started": finding["started_at"],
                                "ended": finding["ended_at"],
                            },
                        )
                    ).scalar_one_or_none()
                else:
                    canonical = None
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
                    "UPDATE acquisition_sessions SET state='completed',quality=CAST(:quality AS jsonb),updated_at=now() WHERE id=:id"
                ),
                {"id": acquisition_id, "quality": json.dumps(report)},
            )
            await db.execute(
                text(
                    "UPDATE driving_sessions SET status='completed',sample_count=(SELECT count(*) FROM telemetry_samples WHERE session_id=:sid),ended_at=COALESCE(ended_at,now()),updated_at=now() WHERE id=:sid"
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
            capability_report=report,
            reconciliation={"confirmed": confirmed, "absent": len(provisional_rows) - confirmed},
        )

    async def _capability_report(
        self, session_id: UUID, recipe_key: str, config_hash: str
    ) -> dict[str, object]:
        async with self.database.session() as db:
            rows = (
                await db.execute(
                    text(
                        "SELECT signal_key,observed_at FROM telemetry_samples WHERE session_id=:id ORDER BY observed_at"
                    ),
                    {"id": session_id},
                )
            ).all()
        grouped: dict[str, list[datetime]] = defaultdict(list)
        for signal, observed in rows:
            grouped[signal].append(observed)
        duration = (
            (
                max((r.observed_at for r in rows), default=datetime.now(UTC))
                - min((r.observed_at for r in rows), default=datetime.now(UTC))
            ).total_seconds()
            if rows
            else 0
        )
        recipe = BY_KEY[recipe_key]
        targets = {item.signal: item.preferred_hz for item in recipe.requirements}
        qualities = tuple(
            measure_signal_quality(signal, tuple(times), targets.get(signal, 1))
            for signal, times in grouped.items()
        )
        capabilities = assess_dataset(qualities, duration)
        return {
            "duration_seconds": duration,
            "available_signals": sorted(grouped),
            "signal_quality": [q.__dict__ for q in qualities],
            "capabilities": [c.__dict__ for c in capabilities],
            "recipe_adherence": not any(
                r.importance.value == "required" and r.signal not in grouped
                for r in recipe.requirements
            ),
        }

    async def capability_report(self, session_id: UUID, recipe_key: str) -> dict[str, object]:
        recipe = BY_KEY.get(recipe_key)
        if recipe is None:
            raise AcquisitionError("unknown logging recipe")
        report = await self._capability_report(session_id, recipe_key, recipe.configuration_hash)
        async with self.database.session() as db:
            await db.execute(
                text(
                    """INSERT INTO dataset_capability_reports(driving_session_id,recipe_key,recipe_configuration_hash,duration_seconds,report) VALUES(:session,:recipe,:hash,:duration,CAST(:report AS jsonb)) ON CONFLICT ON CONSTRAINT uq_dataset_capability_recipe DO UPDATE SET duration_seconds=EXCLUDED.duration_seconds,report=EXCLUDED.report,created_at=now()"""
                ),
                {
                    "session": session_id,
                    "recipe": recipe_key,
                    "hash": recipe.configuration_hash,
                    "duration": report["duration_seconds"],
                    "report": json.dumps(report),
                },
            )
            await db.commit()
        return report
