"""Investigation-owned persistence with optimistic updates and bounded replay."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from vehicle_platform.agents.investigation.domain import (
    InvestigationEvent,
    InvestigationPlan,
    InvestigationStatus,
)
from vehicle_platform.agents.investigation.instrumentation import InvestigationInstrumentation
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.repository import AgentRepository
from vehicle_platform.agents.schemas import AgentRun
from vehicle_platform.observability.telemetry import Telemetry


class InvestigationRepository:
    def __init__(self, agents: AgentRepository, telemetry: Telemetry | None = None) -> None:
        self.agents = agents
        self.signals = InvestigationInstrumentation(telemetry) if telemetry else None

    def _record(self, plan: InvestigationPlan, event: str) -> None:
        if self.signals:
            with self.signals.telemetry.tracer.start_as_current_span(
                f"investigation.{event}", record_exception=False, set_status_on_exception=False
            ) as span:
                span.set_attribute("investigation.status", plan.status.value)
                span.set_attribute("investigation.version", plan.version)
                self.signals.transition(plan, event)

    async def create(self, plan: InvestigationPlan) -> InvestigationPlan:
        if len(plan.model_dump_json().encode()) > 262144:
            raise AgentError("investigation_budget_exhausted")
        event = InvestigationEvent(
            investigation_id=plan.id,
            sequence=1,
            type="investigation_created",
            status=plan.status,
        )
        try:
            async with self.agents.session() as db:
                result = await db.execute(
                    text(
                        "INSERT INTO investigation_plans "
                        "(id,vehicle_id,agent_run_id,status,version,recipe_hash,"
                        "created_at,updated_at,snapshot) "
                        "SELECT :id,:vehicle,:run,:status,1,NULL,:created,:updated,"
                        "CAST(:snapshot AS jsonb) "
                        "FROM agent_runs WHERE id=:run AND vehicle_id=:vehicle "
                        "AND status='completed' "
                        "ON CONFLICT(agent_run_id) DO NOTHING RETURNING id"
                    ),
                    {
                        "id": plan.id,
                        "vehicle": plan.vehicle_id,
                        "run": plan.agent_run_id,
                        "status": plan.status.value,
                        "created": plan.created_at,
                        "updated": plan.updated_at,
                        "snapshot": plan.model_dump_json(),
                    },
                )
                if result.scalar_one_or_none() is None:
                    existing = await db.scalar(
                        text(
                            "SELECT snapshot FROM investigation_plans "
                            "WHERE vehicle_id=:vehicle AND agent_run_id=:run"
                        ),
                        {"vehicle": plan.vehicle_id, "run": plan.agent_run_id},
                    )
                    if existing is None:
                        raise AgentError("invalid_investigation_run")
                    return InvestigationPlan.model_validate(existing)
                await db.execute(
                    text(
                        "INSERT INTO investigation_events(investigation_id,sequence,snapshot) "
                        "VALUES (:id,1,CAST(:snapshot AS jsonb))"
                    ),
                    {"id": plan.id, "snapshot": event.model_dump_json()},
                )
                await db.commit()
        except IntegrityError:
            raise AgentError("invalid_investigation_context") from None
        self._record(plan, "investigation_created")
        return plan

    async def get(self, vehicle_id: UUID, investigation_id: UUID) -> InvestigationPlan:
        async with self.agents.session() as db:
            value = await db.scalar(
                text(
                    "SELECT snapshot FROM investigation_plans WHERE vehicle_id=:vehicle AND id=:id"
                ),
                {"vehicle": vehicle_id, "id": investigation_id},
            )
        if value is None:
            raise AgentError("investigation_not_found")
        return InvestigationPlan.model_validate(value)

    async def recent(self, vehicle_id: UUID, limit: int = 10) -> list[InvestigationPlan]:
        if not 1 <= limit <= 20:
            raise AgentError("invalid_limit")
        async with self.agents.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT snapshot FROM investigation_plans WHERE vehicle_id=:vehicle "
                            "ORDER BY created_at DESC,id LIMIT :limit"
                        ),
                        {"vehicle": vehicle_id, "limit": limit},
                    )
                )
                .scalars()
                .all()
            )
        return [InvestigationPlan.model_validate(row) for row in rows]

    async def update(
        self,
        plan: InvestigationPlan,
        expected_version: int,
        event_type: str,
        detail: str | None = None,
    ) -> InvestigationPlan:
        if expected_version >= 100:
            raise AgentError("investigation_budget_exhausted")
        updated = plan.model_copy(update={"version": expected_version + 1})
        if len(updated.model_dump_json().encode()) > 262144:
            raise AgentError("investigation_budget_exhausted")
        event = InvestigationEvent(
            investigation_id=plan.id,
            sequence=updated.version,
            type=event_type,
            at=datetime.now(UTC),
            status=updated.status,
            detail=detail,
        )
        async with self.agents.session() as db:
            result = await db.execute(
                text(
                    "UPDATE investigation_plans SET status=:status,version=:new_version,"
                    "recipe_hash=:recipe_hash,reanalysis_run_id=:reanalysis,updated_at=:updated,"
                    "snapshot=CAST(:snapshot AS jsonb) "
                    "WHERE id=:id AND vehicle_id=:vehicle AND version=:old_version RETURNING id"
                ),
                {
                    "id": updated.id,
                    "vehicle": updated.vehicle_id,
                    "old_version": expected_version,
                    "new_version": updated.version,
                    "status": updated.status.value,
                    "recipe_hash": updated.recipe.configuration_hash if updated.recipe else None,
                    "reanalysis": updated.reanalysis_run_id,
                    "updated": updated.updated_at,
                    "snapshot": updated.model_dump_json(),
                },
            )
            if result.scalar_one_or_none() is None:
                raise AgentError("stale_investigation_version")
            await db.execute(
                text(
                    "INSERT INTO investigation_events(investigation_id,sequence,snapshot) "
                    "VALUES (:id,:sequence,CAST(:snapshot AS jsonb))"
                ),
                {
                    "id": updated.id,
                    "sequence": event.sequence,
                    "snapshot": event.model_dump_json(),
                },
            )
            await db.commit()
        self._record(updated, event_type)
        return updated

    async def events(
        self, vehicle_id: UUID, investigation_id: UUID, after: int = 0
    ) -> list[InvestigationEvent]:
        if not 0 <= after <= 100:
            raise AgentError("invalid_cursor")
        await self.get(vehicle_id, investigation_id)
        async with self.agents.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT snapshot FROM investigation_events "
                            "WHERE investigation_id=:id AND sequence>:after "
                            "ORDER BY sequence LIMIT 100"
                        ),
                        {"id": investigation_id, "after": after},
                    )
                )
                .scalars()
                .all()
            )
        return [InvestigationEvent.model_validate(row) for row in rows]

    async def link_session(
        self,
        vehicle_id: UUID,
        investigation_id: UUID,
        session_id: UUID,
        expected_version: int,
    ) -> InvestigationPlan:
        """Link one finalized Phase 4 acquisition under a row lock, idempotently."""
        async with self.agents.session() as db:
            value = await db.scalar(
                text(
                    "SELECT snapshot FROM investigation_plans "
                    "WHERE id=:id AND vehicle_id=:vehicle FOR UPDATE"
                ),
                {"id": investigation_id, "vehicle": vehicle_id},
            )
            if value is None:
                raise AgentError("investigation_not_found")
            plan = InvestigationPlan.model_validate(value)
            if session_id in plan.linked_session_ids:
                return plan
            if plan.version != expected_version:
                raise AgentError("stale_investigation_version")
            if (
                plan.status
                not in {
                    InvestigationStatus.ACQUISITION_READY,
                    InvestigationStatus.AWAITING_DATA,
                }
                or plan.approval.status != "APPROVED"
                or plan.recipe is None
                or plan.approval.recipe_hash != plan.recipe.configuration_hash
                or plan.approval.approved_at is None
                or plan.configuration_id is None
                or plan.cycle_count >= 1
            ):
                raise AgentError("investigation_not_acquisition_ready")
            acquisition = (
                (
                    await db.execute(
                        text(
                            "SELECT s.vehicle_id,s.configuration_id,s.source_reference,"
                            "s.status AS session_status,a.adapter,a.state,a.started_at,"
                            "a.recipe_key,a.recipe_version,a.recipe_configuration_hash "
                            "FROM driving_sessions s JOIN acquisition_sessions a "
                            "ON a.driving_session_id=s.id WHERE s.id=:session"
                        ),
                        {"session": session_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if (
                acquisition is None
                or acquisition["vehicle_id"] != plan.vehicle_id
                or acquisition["configuration_id"] != plan.configuration_id
                or acquisition["source_reference"] != plan.source_id
                or acquisition["adapter"] != plan.source_adapter
                or acquisition["session_status"] != "completed"
                or acquisition["state"] != "completed"
                or acquisition["started_at"] < plan.approval.approved_at
                or acquisition["recipe_key"] != plan.recipe.key
                or acquisition["recipe_version"] != plan.recipe.version
                or acquisition["recipe_configuration_hash"] != plan.recipe.configuration_hash
            ):
                raise AgentError("incompatible_investigation_session")
            await db.execute(
                text(
                    "INSERT INTO investigation_session_links "
                    "(investigation_id,session_id,recipe_hash,linked_at) "
                    "VALUES (:investigation,:session,:hash,:at)"
                ),
                {
                    "investigation": plan.id,
                    "session": session_id,
                    "hash": plan.recipe.configuration_hash,
                    "at": datetime.now(UTC),
                },
            )
            if plan.status is InvestigationStatus.ACQUISITION_READY:
                plan.move(InvestigationStatus.AWAITING_DATA)
            plan.linked_session_ids.append(session_id)
            plan.cycle_count = 1
            plan.move(InvestigationStatus.DATA_RECEIVED)
            plan.version += 1
            if plan.version > 100:
                raise AgentError("investigation_budget_exhausted")
            await db.execute(
                text(
                    "UPDATE investigation_plans SET status=:status,version=:version,"
                    "updated_at=:updated,snapshot=CAST(:snapshot AS jsonb) WHERE id=:id"
                ),
                {
                    "status": plan.status.value,
                    "version": plan.version,
                    "updated": plan.updated_at,
                    "snapshot": plan.model_dump_json(),
                    "id": plan.id,
                },
            )
            event = InvestigationEvent(
                investigation_id=plan.id,
                sequence=plan.version,
                type="session_linked",
                status=plan.status,
                detail=str(session_id),
            )
            await db.execute(
                text(
                    "INSERT INTO investigation_events(investigation_id,sequence,snapshot) "
                    "VALUES (:id,:sequence,CAST(:snapshot AS jsonb))"
                ),
                {"id": plan.id, "sequence": plan.version, "snapshot": event.model_dump_json()},
            )
            await db.commit()
        self._record(plan, "session_linked")
        return plan

    async def claim_reanalysis(
        self, vehicle_id: UUID, investigation_id: UUID, run: AgentRun
    ) -> InvestigationPlan:
        """Atomically persist a unique follow-up AgentRun and its investigation link."""
        async with self.agents.session() as db:
            value = await db.scalar(
                text(
                    "SELECT snapshot FROM investigation_plans "
                    "WHERE id=:id AND vehicle_id=:vehicle FOR UPDATE"
                ),
                {"id": investigation_id, "vehicle": vehicle_id},
            )
            if value is None:
                raise AgentError("investigation_not_found")
            plan = InvestigationPlan.model_validate(value)
            if plan.status is InvestigationStatus.REANALYZING and plan.reanalysis_run_id:
                return plan
            if (
                plan.status is not InvestigationStatus.DATA_RECEIVED
                or not plan.linked_session_ids
                or run.vehicle_id != vehicle_id
                or run.user_question != plan.question
                or plan.cycle_count != 1
            ):
                raise AgentError("invalid_reanalysis_state")
            await db.execute(
                text(
                    "INSERT INTO agent_runs(id,vehicle_id,status,started_at,snapshot) "
                    "VALUES (:id,:vehicle,'running',:started,CAST(:snapshot AS jsonb))"
                ),
                {
                    "id": run.id,
                    "vehicle": run.vehicle_id,
                    "started": run.started_at,
                    "snapshot": run.model_dump_json(),
                },
            )
            plan.reanalysis_run_id = run.id
            plan.move(InvestigationStatus.REANALYZING)
            plan.version += 1
            if plan.version > 100:
                raise AgentError("investigation_budget_exhausted")
            await db.execute(
                text(
                    "UPDATE investigation_plans SET status='REANALYZING',"
                    "version=:version,reanalysis_run_id=:run,updated_at=:updated,"
                    "snapshot=CAST(:snapshot AS jsonb) WHERE id=:id"
                ),
                {
                    "version": plan.version,
                    "run": run.id,
                    "updated": plan.updated_at,
                    "snapshot": plan.model_dump_json(),
                    "id": plan.id,
                },
            )
            event = InvestigationEvent(
                investigation_id=plan.id,
                sequence=plan.version,
                type="reanalysis_started",
                status=plan.status,
                detail=str(run.id),
            )
            await db.execute(
                text(
                    "INSERT INTO investigation_events(investigation_id,sequence,snapshot) "
                    "VALUES (:id,:sequence,CAST(:snapshot AS jsonb))"
                ),
                {"id": plan.id, "sequence": plan.version, "snapshot": event.model_dump_json()},
            )
            await db.commit()
        self._record(plan, "reanalysis_started")
        return plan
