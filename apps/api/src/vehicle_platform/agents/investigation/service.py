"""One bounded investigation path on top of a completed grounded AgentRun."""

import asyncio
from datetime import UTC, datetime
from time import perf_counter
from typing import Literal
from uuid import UUID, uuid4

from pydantic import ValidationError

from vehicle_platform.acquisition.adapters import SyntheticLiveAdapter
from vehicle_platform.acquisition.capabilities import AcquisitionCapabilitySource
from vehicle_platform.acquisition.domain import DeviceCapabilities
from vehicle_platform.agents.config import redact_data
from vehicle_platform.agents.investigation.domain import (
    Approval,
    Availability,
    CapabilitySnapshot,
    Feasibility,
    GapStatus,
    GapType,
    InvestigationPlan,
    InvestigationStatus,
)
from vehicle_platform.agents.investigation.existing import search_existing
from vehicle_platform.agents.investigation.follow_up import (
    outcome,
    resolve_followup_gaps,
    update_hypotheses,
)
from vehicle_platform.agents.investigation.planning import plan_recipe
from vehicle_platform.agents.investigation.proposal import (
    InvestigationInput,
    InvestigationProposal,
    materialize,
)
from vehicle_platform.agents.investigation.repository import InvestigationRepository
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import AgentRun, Ask, Classification
from vehicle_platform.agents.service import AgentService
from vehicle_platform.api.domain_contracts import PreflightRequest

Adapter = Literal["synthetic", "replay", "obd"]


def investigable(run: AgentRun) -> bool:
    if run.status != "completed" or run.result is None:
        return False
    return bool(
        any(
            finding.classification is Classification.INSUFFICIENT_EVIDENCE
            for finding in run.result.findings
        )
        and set(run.result.missing_evidence)
        & {
            "signal_or_measurement",
            "comparable_history",
            "technical_documentation",
            "data_quality",
            "configuration_context",
        }
    )


class InvestigationService:
    def __init__(
        self,
        agents: AgentService,
        repository: InvestigationRepository,
        source: AcquisitionCapabilitySource,
    ) -> None:
        self.agents = agents
        self.repository = repository
        self.source = source
        self.active = 0
        self.followups: dict[UUID, asyncio.Task[None]] = {}

    async def _source_capabilities(
        self,
        vehicle_id: UUID,
        configuration_id: UUID | None,
        adapter: Adapter,
        source_id: str,
    ) -> CapabilitySnapshot | None:
        if adapter == "synthetic":
            if self.agents.settings.provider != "deterministic":
                raise AgentError("synthetic_investigation_source_disabled")
            capabilities = await SyntheticLiveAdapter(samples=1).capabilities()
            return CapabilitySnapshot(
                adapter=capabilities.adapter,
                signals=capabilities.signals,
                maximum_requests_per_second=capabilities.maximum_requests_per_second,
                observed_at=datetime.now(UTC),
            )
        snapshot = await self.source.latest(vehicle_id, configuration_id, adapter, source_id)
        if snapshot is None:
            return None
        return CapabilitySnapshot(
            adapter=snapshot.capabilities.adapter,
            signals=snapshot.capabilities.signals,
            maximum_requests_per_second=snapshot.capabilities.maximum_requests_per_second,
            observed_at=snapshot.received_at,
            source_acquisition_id=snapshot.acquisition_id,
            source_preflight_id=snapshot.preflight_id,
        )

    async def register_source(
        self,
        vehicle_id: UUID,
        configuration_id: UUID,
        adapter: Literal["obd", "replay"],
        source_id: str,
        report: PreflightRequest,
    ) -> CapabilitySnapshot:
        try:
            snapshot = await self.source.register(
                vehicle_id, configuration_id, adapter, source_id, report
            )
        except ValueError:
            raise AgentError("invalid_source_preflight") from None
        return CapabilitySnapshot(
            adapter=snapshot.capabilities.adapter,
            signals=snapshot.capabilities.signals,
            maximum_requests_per_second=snapshot.capabilities.maximum_requests_per_second,
            observed_at=snapshot.received_at,
            source_preflight_id=snapshot.preflight_id,
        )

    async def create(
        self, vehicle_id: UUID, run_id: UUID, adapter: Adapter, source_id: str
    ) -> InvestigationPlan:
        if not 1 <= len(source_id) <= 80:
            raise AgentError("invalid_source_identity")
        if self.active >= 4:
            raise AgentError("investigation_concurrency_exhausted")
        self.active += 1
        try:
            async with asyncio.timeout(45):
                run = await self.agents.repository.get(vehicle_id, run_id)
                if not investigable(run) or run.result is None:
                    raise AgentError("evidence_not_investigable")
                provider = self.agents.provider_factory()
                planning_started = perf_counter()
                try:
                    proposal = await provider.propose(
                        InvestigationInput(
                            question=self.agents.redact(run.user_question),
                            context=redact_data(
                                run.result.context.model_dump(mode="json"), self.agents.settings
                            ),
                            evidence=redact_data(
                                [item.model_dump(mode="json") for item in run.evidence],
                                self.agents.settings,
                            ),
                            missing_evidence=run.result.missing_evidence,
                        )
                    )
                    try:
                        proposal = InvestigationProposal.model_validate(proposal)
                    except ValidationError:
                        raise AgentError("invalid_investigation_proposal") from None
                finally:
                    await provider.close()
                self.agents.telemetry.log(
                    "investigation.planning.completed",
                    str(run.id),
                    agent_run_id=str(run.id),
                    planning_seconds=perf_counter() - planning_started,
                )
                hypotheses, gaps, needs = materialize(proposal, run)
                try:
                    async with self.agents.client_factory() as client:
                        existing = await search_existing(run, gaps, needs, client)
                except AgentError:
                    raise
                except Exception:
                    raise AgentError("mcp_unavailable") from None
                self.agents.telemetry.log(
                    "investigation.existing_evidence.completed",
                    str(run.id),
                    agent_run_id=str(run.id),
                    mcp_calls=existing.mcp_calls,
                )
                if all(gap.status is GapStatus.AVAILABLE_IN_EXISTING_DATA for gap in existing.gaps):
                    raise AgentError("existing_evidence_sufficient")
                plan = InvestigationPlan(
                    id=uuid4(),
                    agent_run_id=run.id,
                    vehicle_id=run.vehicle_id,
                    question=run.user_question,
                    goal="Resolve the material evidence gaps in the grounded answer",
                    configuration_id=run.result.context.active_configuration_id,
                    source_session_id=(
                        UUID(str(run.result.context.sessions[0]["id"]))
                        if run.result.context.sessions
                        else None
                    ),
                    source_adapter=adapter,
                    source_id=source_id,
                    findings_summary=run.result.answer[:2000],
                    hypotheses=hypotheses,
                    gaps=list(existing.gaps),
                    signal_needs=needs,
                    trace_id=run.trace_id,
                )
                proposed = plan
                plan = await self.repository.create(proposed)
                if plan.id != proposed.id:
                    if plan.source_adapter != adapter or plan.source_id != source_id:
                        raise AgentError("investigation_source_conflict")
                    if plan.status is InvestigationStatus.DRAFT:
                        plan.hypotheses = hypotheses
                        plan.gaps = list(existing.gaps)
                        plan.signal_needs = needs
                if plan.status is not InvestigationStatus.DRAFT:
                    return plan
                version = plan.version
                plan.move(InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED)
                plan = await self.repository.update(plan, version, "evidence_gap_identified")
                return await self.refresh(plan.vehicle_id, plan.id, plan.version)
        except TimeoutError:
            raise AgentError("investigation_timeout") from None
        finally:
            self.active -= 1

    async def refresh(
        self, vehicle_id: UUID, investigation_id: UUID, expected_version: int
    ) -> InvestigationPlan:
        plan = await self.repository.get(vehicle_id, investigation_id)
        if plan.version != expected_version:
            raise AgentError("stale_investigation_version")
        if plan.status not in {
            InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED,
            InvestigationStatus.CAPABILITIES_RESOLVED,
            InvestigationStatus.AWAITING_APPROVAL,
            InvestigationStatus.APPROVED,
            InvestigationStatus.ACQUISITION_READY,
        }:
            raise AgentError("invalid_investigation_state")
        if plan.source_adapter is None:
            raise AgentError("invalid_source_identity")
        snapshot = await self._source_capabilities(
            vehicle_id, plan.configuration_id, plan.source_adapter, plan.source_id
        )
        capabilities = (
            DeviceCapabilities(
                snapshot.adapter,
                snapshot.signals,
                snapshot.maximum_requests_per_second,
            )
            if snapshot
            else None
        )
        source_session_signals: set[str] | None = None
        if plan.source_session_id:
            try:
                async with self.agents.client_factory() as client:
                    envelope = await client.call(
                        "get_session_capabilities",
                        {
                            "vehicle_id": str(vehicle_id),
                            "session_id": str(plan.source_session_id),
                        },
                    )
            except AgentError:
                raise
            except Exception:
                raise AgentError("mcp_unavailable") from None
            if str(envelope.context.get("vehicle_id")) != str(vehicle_id):
                raise AgentError("incompatible_context")
            if isinstance(envelope.data, dict):
                source_session_signals = set(envelope.data.get("available_signals", []))
        recipe_started = perf_counter()
        planned = plan_recipe(plan.signal_needs, capabilities, source_session_signals)
        self.agents.telemetry.log(
            "investigation.recipe_generation.completed",
            str(plan.id),
            investigation_id=str(plan.id),
            recipe_generation_seconds=perf_counter() - recipe_started,
            signal_need_count=len(plan.signal_needs),
        )
        source_changed = plan.capability_snapshot != snapshot
        if plan.source_adapter == "synthetic" and plan.capability_snapshot and snapshot:
            source_changed = (
                plan.capability_snapshot.adapter != snapshot.adapter
                or plan.capability_snapshot.signals != snapshot.signals
                or plan.capability_snapshot.maximum_requests_per_second
                != snapshot.maximum_requests_per_second
            )
        plan.capability_snapshot = snapshot
        plan.signal_needs = list(planned.needs)
        plan.replace_recipe(planned.reference)
        if source_changed and plan.approval.status == "APPROVED":
            plan.approval = Approval(status="INVALIDATED")
            plan.move(InvestigationStatus.AWAITING_APPROVAL)
        unavailable = {
            need.id for need in planned.needs if need.availability is Availability.UNAVAILABLE
        }
        plan.gaps = [
            gap.model_copy(update={"status": GapStatus.UNAVAILABLE_WITH_CURRENT_SOURCE})
            if gap.signal_need_ids
            and set(gap.signal_need_ids) <= unavailable
            and gap.status is GapStatus.NEEDS_NEW_CAPTURE
            else gap
            for gap in plan.gaps
        ]
        if plan.status is InvestigationStatus.EVIDENCE_GAPS_IDENTIFIED:
            plan.move(InvestigationStatus.CAPABILITIES_RESOLVED)
        version = plan.version
        plan = await self.repository.update(plan, version, "capability_resolution_completed")
        if (
            plan.recipe
            and plan.recipe.feasibility
            in {Feasibility.FEASIBLE, Feasibility.FEASIBLE_WITH_DEGRADATION}
            and plan.status is InvestigationStatus.CAPABILITIES_RESOLVED
        ):
            version = plan.version
            plan.move(InvestigationStatus.RECIPE_PROPOSED)
            plan = await self.repository.update(plan, version, "recipe_proposed")
            version = plan.version
            plan.move(InvestigationStatus.AWAITING_APPROVAL)
            plan = await self.repository.update(plan, version, "approval_required")
        elif plan.gaps and all(
            gap.category is GapType.TECHNICAL_DOCUMENTATION for gap in plan.gaps
        ):
            version = plan.version
            plan.move(InvestigationStatus.INCONCLUSIVE)
            plan = await self.repository.update(plan, version, "investigation_inconclusive")
        return plan

    async def approve(
        self,
        vehicle_id: UUID,
        investigation_id: UUID,
        expected_version: int,
        recipe_hash: str,
        actor: str,
    ) -> InvestigationPlan:
        plan = await self.repository.get(vehicle_id, investigation_id)
        if (
            plan.status is InvestigationStatus.ACQUISITION_READY
            and plan.approval.status == "APPROVED"
            and plan.recipe
            and plan.recipe.configuration_hash == recipe_hash
        ):
            return plan
        if plan.version != expected_version:
            raise AgentError("stale_investigation_version")
        if not plan.recipe or plan.recipe.configuration_hash != recipe_hash:
            raise AgentError("stale_recipe_hash")
        if plan.capability_snapshot is None or plan.source_adapter is None:
            raise AgentError("stale_source_capabilities")
        latest = await self._source_capabilities(
            vehicle_id, plan.configuration_id, plan.source_adapter, plan.source_id
        )
        if (
            latest is None
            or latest.adapter != plan.capability_snapshot.adapter
            or latest.signals != plan.capability_snapshot.signals
            or latest.maximum_requests_per_second
            != plan.capability_snapshot.maximum_requests_per_second
            or latest.source_acquisition_id != plan.capability_snapshot.source_acquisition_id
            or latest.source_preflight_id != plan.capability_snapshot.source_preflight_id
            or (
                plan.source_adapter != "synthetic"
                and latest.observed_at != plan.capability_snapshot.observed_at
            )
        ):
            raise AgentError("stale_source_capabilities")
        if plan.status not in {InvestigationStatus.AWAITING_APPROVAL, InvestigationStatus.APPROVED}:
            raise AgentError("invalid_investigation_state")
        if plan.status is InvestigationStatus.AWAITING_APPROVAL:
            plan.approval = Approval(
                status="APPROVED",
                recipe_hash=recipe_hash,
                approved_at=datetime.now(UTC),
                actor=actor[:100],
            )
            version = plan.version
            plan.move(InvestigationStatus.APPROVED)
            plan = await self.repository.update(plan, version, "approved")
        version = plan.version
        plan.move(InvestigationStatus.ACQUISITION_READY)
        return await self.repository.update(plan, version, "acquisition_ready")

    async def reject(
        self, vehicle_id: UUID, investigation_id: UUID, expected_version: int
    ) -> InvestigationPlan:
        plan = await self.repository.get(vehicle_id, investigation_id)
        if plan.version != expected_version:
            raise AgentError("stale_investigation_version")
        if plan.status is InvestigationStatus.REJECTED:
            return plan
        version = plan.version
        plan.approval = Approval(status="REJECTED")
        plan.move(InvestigationStatus.REJECTED)
        return await self.repository.update(plan, version, "investigation_rejected")

    async def cancel(
        self, vehicle_id: UUID, investigation_id: UUID, expected_version: int
    ) -> InvestigationPlan:
        plan = await self.repository.get(vehicle_id, investigation_id)
        if plan.version != expected_version:
            raise AgentError("stale_investigation_version")
        if plan.status is InvestigationStatus.CANCELLED:
            return plan
        version = plan.version
        plan.move(InvestigationStatus.CANCELLED)
        return await self.repository.update(plan, version, "investigation_cancelled")

    async def link(
        self,
        vehicle_id: UUID,
        investigation_id: UUID,
        session_id: UUID,
        expected_version: int,
    ) -> InvestigationPlan:
        plan = await self.repository.link_session(
            vehicle_id, investigation_id, session_id, expected_version
        )
        if plan.status is InvestigationStatus.DATA_RECEIVED:
            return await self.reanalyze(vehicle_id, investigation_id)
        return plan

    async def reanalyze(self, vehicle_id: UUID, investigation_id: UUID) -> InvestigationPlan:
        plan = await self.repository.get(vehicle_id, investigation_id)
        if plan.status not in {
            InvestigationStatus.DATA_RECEIVED,
            InvestigationStatus.REANALYZING,
        }:
            return plan
        if plan.status is InvestigationStatus.DATA_RECEIVED:
            settings = self.agents.settings
            run = AgentRun(
                id=uuid4(),
                vehicle_id=vehicle_id,
                user_question=plan.question,
                status="running",
                provider=settings.provider,
                model=self.agents.redact(settings.model or "scripted-v1"),
                agent_version=settings.agent_version,
                prompt_version=settings.prompt_version,
                started_at=datetime.now(UTC),
            )
            plan = await self.repository.claim_reanalysis(vehicle_id, investigation_id, run)
        if plan.reanalysis_run_id is None or not plan.linked_session_ids:
            raise AgentError("invalid_reanalysis_state")
        context = (
            f"investigation_id={plan.id}; session_id={plan.linked_session_ids[0]}; "
            + "candidate_categories="
            + ",".join(hypothesis.category.value for hypothesis in plan.hypotheses)
        )
        await self.agents.start(
            vehicle_id,
            Ask(
                question=plan.question,
                session_id=plan.linked_session_ids[0],
                previous_run_id=plan.agent_run_id,
            ),
            run_id=plan.reanalysis_run_id,
            follow_up_context=context,
        )
        task = self.agents.tasks.get(plan.reanalysis_run_id)
        if task and investigation_id not in self.followups:
            self.followups[investigation_id] = asyncio.create_task(
                self._watch(vehicle_id, investigation_id, task)
            )
        return plan

    async def _watch(
        self, vehicle_id: UUID, investigation_id: UUID, run_task: asyncio.Task[None]
    ) -> None:
        try:
            await run_task
            await self.complete_follow_up(vehicle_id, investigation_id)
        except Exception as exc:
            # A later authorized read reconciles a durable terminal AgentRun.
            self.agents.telemetry.log(
                "investigation.followup.watch.failed",
                str(investigation_id),
                investigation_id=str(investigation_id),
                error_code=type(exc).__name__,
            )
        finally:
            self.followups.pop(investigation_id, None)

    async def complete_follow_up(
        self, vehicle_id: UUID, investigation_id: UUID
    ) -> InvestigationPlan:
        plan = await self.repository.get(vehicle_id, investigation_id)
        if plan.status is not InvestigationStatus.REANALYZING or plan.reanalysis_run_id is None:
            return plan
        run = await self.agents.repository.get(vehicle_id, plan.reanalysis_run_id)
        if run.status == "running":
            return plan
        version = plan.version
        if run.status != "completed" or run.result is None:
            plan.move(InvestigationStatus.FAILED)
            event = "investigation_failed"
        else:
            plan.gaps = resolve_followup_gaps(plan, run)
            calls = await self.agents.repository.calls(vehicle_id, run.id)
            plan.hypotheses = update_hypotheses(plan, run, calls)
            plan.outcome = outcome(plan, run)
            terminal_status = (
                InvestigationStatus.INCONCLUSIVE
                if plan.outcome.classification == "INCONCLUSIVE"
                else InvestigationStatus.COMPLETED
            )
            plan.move(terminal_status)
            event = (
                "investigation_inconclusive"
                if terminal_status is InvestigationStatus.INCONCLUSIVE
                else "investigation_completed"
            )
        try:
            return await self.repository.update(plan, version, event)
        except AgentError as exc:
            if exc.category != "stale_investigation_version":
                raise
            return await self.repository.get(vehicle_id, investigation_id)

    async def get(self, vehicle_id: UUID, investigation_id: UUID) -> InvestigationPlan:
        plan = await self.repository.get(vehicle_id, investigation_id)
        if plan.status is InvestigationStatus.REANALYZING:
            if investigation_id not in self.followups:
                await self.reanalyze(vehicle_id, investigation_id)
            return await self.complete_follow_up(vehicle_id, investigation_id)
        return plan

    async def close(self) -> None:
        tasks = list(self.followups.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
