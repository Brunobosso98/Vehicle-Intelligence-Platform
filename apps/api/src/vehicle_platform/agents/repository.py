import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from vehicle_platform.agents.evidence import PredictionEvidenceLink
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import AgentRun, StreamEvent, ToolCall
from vehicle_platform.infrastructure.database import Database

DATABASE_TIMEOUT = 5.0


class TerminableConnection(Protocol):
    def terminate(self) -> None: ...


class AgentRepository:
    """Only agent-owned tables. Vehicle existence is resolved through MCP, never SQL."""

    def __init__(self, database: Database) -> None:
        self.database = database

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + DATABASE_TIMEOUT
        watchdog: asyncio.TimerHandle | None = None
        driver: TerminableConnection | None = None
        try:
            async with asyncio.timeout_at(deadline), self.database.session() as db:
                connection = await db.connection()
                raw = await connection.get_raw_connection()
                raw_driver = raw.driver_connection
                if raw_driver is None:
                    raise AgentError("database_unavailable")
                driver = cast(TerminableConnection, raw_driver)
                # Cancellation cleanup can wait for an unavailable PostgreSQL server.
                # Abort this owned driver's transport if cleanup outlives the deadline.
                watchdog = loop.call_at(deadline + 0.05, driver.terminate)
                yield db
        except IntegrityError:
            raise
        except asyncio.CancelledError:
            if driver is not None:
                driver.terminate()
            raise
        except (SQLAlchemyError, OSError, TimeoutError):
            raise AgentError("database_unavailable") from None
        finally:
            if watchdog is not None:
                watchdog.cancel()

    async def reconcile(self, vehicle_id: UUID) -> None:
        """Recover interrupted runs beyond the hard 180s runtime plus cleanup allowance."""
        async with self.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT snapshot FROM agent_runs WHERE vehicle_id=:vehicle "
                            "AND status='running' AND started_at<:cutoff "
                            "ORDER BY started_at LIMIT 20 FOR UPDATE SKIP LOCKED"
                        ),
                        {
                            "vehicle": vehicle_id,
                            "cutoff": datetime.now(UTC) - timedelta(seconds=190),
                        },
                    )
                )
                .scalars()
                .all()
            )
            for snapshot in rows:
                run = AgentRun.model_validate(snapshot)
                run.status, run.error_category = "failed", "execution_interrupted"
                run.completed_at = datetime.now(UTC)
                run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
                last = await db.scalar(
                    text(
                        "SELECT COALESCE(max(sequence),0) "
                        "FROM agent_stream_events WHERE agent_run_id=:run"
                    ),
                    {"run": run.id},
                )
                await db.execute(
                    text(
                        "UPDATE agent_runs SET status='failed', "
                        "snapshot=CAST(:snapshot AS jsonb) WHERE id=:run"
                    ),
                    {"run": run.id, "snapshot": run.model_dump_json()},
                )
                await db.execute(
                    text(
                        "UPDATE agent_tool_calls SET snapshot = "
                        "snapshot || jsonb_build_object('status','failed','error_category',"
                        "'execution_interrupted','completed_at',CAST(:completed AS text)) "
                        "WHERE agent_run_id=:run AND snapshot->>'status'='running'"
                    ),
                    {"run": run.id, "completed": run.completed_at.isoformat()},
                )
                if int(last or 0) < 400:
                    event = StreamEvent(
                        sequence=int(last or 0) + 1,
                        run_id=run.id,
                        type="run_failed",
                        data={"status": "failed", "error_category": "execution_interrupted"},
                    )
                    await db.execute(
                        text(
                            "INSERT INTO agent_stream_events "
                            "(agent_run_id,sequence,snapshot) VALUES "
                            "(:run,:sequence,CAST(:snapshot AS jsonb))"
                        ),
                        {
                            "run": run.id,
                            "sequence": event.sequence,
                            "snapshot": event.model_dump_json(),
                        },
                    )
            await db.commit()

    async def create(self, run: AgentRun) -> None:
        async with self.session() as db:
            await db.execute(
                text(
                    "INSERT INTO agent_runs(id,vehicle_id,status,started_at,snapshot) "
                    "VALUES (:id,:vehicle,:status,:started,CAST(:snapshot AS jsonb))"
                ),
                {
                    "id": run.id,
                    "vehicle": run.vehicle_id,
                    "status": run.status,
                    "started": run.started_at,
                    "snapshot": run.model_dump_json(),
                },
            )
            await db.commit()

    async def save(
        self,
        run: AgentRun,
        *,
        prediction_links: list[PredictionEvidenceLink] | None = None,
    ) -> None:
        if prediction_links is not None and len(prediction_links) > 4:
            raise AgentError("prediction_evidence_budget_exhausted")
        async with self.session() as db:
            await db.execute(
                text(
                    "UPDATE agent_runs SET status=:status,snapshot=CAST(:snapshot AS jsonb) "
                    "WHERE id=:id AND status='running'"
                ),
                {"id": run.id, "status": run.status, "snapshot": run.model_dump_json()},
            )
            for link in prediction_links or []:
                await db.execute(
                    text(
                        "INSERT INTO agent_prediction_evidence_links "
                        "(agent_run_id,run_evidence_id,source_evidence_id,receipt_id,"
                        "source_vehicle_id,source_session_id,source_pull_id,"
                        "source_configuration_id,source_feature_set_id,result_type,horizon,task,family,"
                        "model_version,model_algorithm,detector_version,detector_algorithm_version,"
                        "detector_method,source_role,effective_cutoff,integrity,completeness,"
                        "artifact_availability,projection_version) VALUES "
                        "(:run,:run_evidence,:source_evidence,:receipt,:vehicle,:session,:pull,"
                        ":configuration,:feature_set,:result_type,:horizon,:task,:family,"
                        ":model_version,:model_algorithm,:detector_version,:detector_algorithm_version,"
                        ":detector_method,:role,:cutoff,"
                        ":integrity,:completeness,:artifact_availability,:projection) "
                        "ON CONFLICT (agent_run_id,run_evidence_id) DO NOTHING"
                    ),
                    {
                        "run": run.id,
                        "run_evidence": link.run_evidence_id,
                        "source_evidence": link.source_evidence_id,
                        "receipt": link.receipt_id,
                        "vehicle": link.source_vehicle_id,
                        "session": link.source_session_id,
                        "pull": link.source_pull_id,
                        "configuration": link.source_configuration_id,
                        "feature_set": link.source_feature_set_id,
                        "result_type": link.result_type,
                        "horizon": link.horizon,
                        "task": link.task,
                        "family": link.family,
                        "model_version": link.model_version,
                        "model_algorithm": link.model_algorithm,
                        "detector_version": link.detector_version,
                        "detector_algorithm_version": link.detector_algorithm_version,
                        "detector_method": link.detector_method,
                        "role": link.source_role,
                        "cutoff": link.effective_cutoff,
                        "integrity": link.integrity,
                        "completeness": link.completeness,
                        "artifact_availability": link.artifact_availability,
                        "projection": link.projection_version,
                    },
                )
            await db.commit()

    async def finish(self, run: AgentRun, event: StreamEvent) -> None:
        """Commit terminal state and stream event together; reconnect cannot race completion."""
        async with self.session() as db:
            await db.execute(
                text(
                    "UPDATE agent_runs SET status=:status,snapshot=CAST(:snapshot AS jsonb) "
                    "WHERE id=:id AND status='running'"
                ),
                {"id": run.id, "status": run.status, "snapshot": run.model_dump_json()},
            )
            await db.execute(
                text(
                    "INSERT INTO agent_stream_events(agent_run_id,sequence,snapshot) "
                    "VALUES (:run,:sequence,CAST(:snapshot AS jsonb))"
                ),
                {"run": run.id, "sequence": event.sequence, "snapshot": event.model_dump_json()},
            )
            await db.commit()

    async def get(self, vehicle_id: UUID, run_id: UUID) -> AgentRun:
        async with self.session() as db:
            value = await db.scalar(
                text("SELECT snapshot FROM agent_runs WHERE vehicle_id=:vehicle AND id=:id"),
                {"vehicle": vehicle_id, "id": run_id},
            )
        if value is None:
            raise AgentError("run_not_found")
        run = AgentRun.model_validate(value)
        if run.status == "running" and run.started_at < datetime.now(UTC) - timedelta(seconds=190):
            await self.reconcile(vehicle_id)
            async with self.session() as db:
                value = await db.scalar(
                    text("SELECT snapshot FROM agent_runs WHERE vehicle_id=:vehicle AND id=:id"),
                    {"vehicle": vehicle_id, "id": run_id},
                )
            return AgentRun.model_validate(value)
        return run

    async def recent(self, vehicle_id: UUID, limit: int) -> list[AgentRun]:
        if not 1 <= limit <= 20:
            raise AgentError("invalid_limit")
        await self.reconcile(vehicle_id)
        async with self.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT snapshot FROM agent_runs WHERE vehicle_id=:vehicle "
                            "ORDER BY started_at DESC,id LIMIT :limit"
                        ),
                        {"vehicle": vehicle_id, "limit": limit},
                    )
                )
                .scalars()
                .all()
            )
        return [AgentRun.model_validate(row) for row in rows]

    async def audit(self, call: ToolCall) -> None:
        async with self.session() as db:
            await db.execute(
                text(
                    "INSERT INTO agent_tool_calls(id,agent_run_id,started_at,snapshot) "
                    "VALUES (:id,:run,:started,CAST(:snapshot AS jsonb)) "
                    "ON CONFLICT(id) DO UPDATE SET snapshot=EXCLUDED.snapshot "
                    "WHERE agent_tool_calls.snapshot->>'status'='running'"
                ),
                {
                    "id": call.id,
                    "run": call.run_id,
                    "started": call.started_at,
                    "snapshot": call.model_dump_json(),
                },
            )
            await db.commit()

    async def calls(self, vehicle_id: UUID, run_id: UUID) -> list[ToolCall]:
        await self.get(vehicle_id, run_id)
        async with self.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT snapshot FROM agent_tool_calls WHERE agent_run_id=:run "
                            "ORDER BY started_at,id LIMIT 32"
                        ),
                        {"run": run_id},
                    )
                )
                .scalars()
                .all()
            )
        return [ToolCall.model_validate(row) for row in rows]

    async def event(self, event: StreamEvent) -> None:
        if event.sequence > 400 or len(event.model_dump_json().encode()) > 131072:
            raise AgentError("stream_budget_exhausted")
        async with self.session() as db:
            await db.execute(
                text(
                    "INSERT INTO agent_stream_events(agent_run_id,sequence,snapshot) "
                    "VALUES (:run,:sequence,CAST(:snapshot AS jsonb))"
                ),
                {
                    "run": event.run_id,
                    "sequence": event.sequence,
                    "snapshot": event.model_dump_json(),
                },
            )
            await db.commit()

    async def events(self, vehicle_id: UUID, run_id: UUID, after: int) -> list[StreamEvent]:
        await self.get(vehicle_id, run_id)
        async with self.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT snapshot FROM agent_stream_events "
                            "WHERE agent_run_id=:run AND sequence>:after "
                            "ORDER BY sequence LIMIT 400"
                        ),
                        {"run": run_id, "after": after},
                    )
                )
                .scalars()
                .all()
            )
        return [StreamEvent.model_validate(row) for row in rows]
