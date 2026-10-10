"""Bounded investigation telemetry without entity labels on metrics."""

from vehicle_platform.agents.investigation.domain import (
    Availability,
    Feasibility,
    InvestigationPlan,
    InvestigationStatus,
)
from vehicle_platform.observability.telemetry import Telemetry


class InvestigationInstrumentation:
    def __init__(self, telemetry: Telemetry) -> None:
        self.telemetry = telemetry
        meter = telemetry.metrics.get_meter("vehicle_platform.agents.investigation")
        self.investigations = meter.create_counter("investigations.total")
        self.completed = meter.create_counter("investigations.completed")
        self.inconclusive = meter.create_counter("investigations.inconclusive")
        self.failures = meter.create_counter("investigations.failures")
        self.hypotheses = meter.create_counter("investigations.hypotheses")
        self.gaps = meter.create_counter("investigations.evidence_gaps")
        self.unavailable = meter.create_counter("investigations.unavailable_signal_needs")
        self.recipes = meter.create_counter("investigations.recipes_proposed")
        self.feasible = meter.create_counter("investigations.recipes_feasible")
        self.degraded = meter.create_counter("investigations.recipes_degraded")
        self.approvals = meter.create_counter("investigations.approvals")
        self.reanalyses = meter.create_counter("investigations.reanalyses")
        self.duration = meter.create_histogram("investigations.duration", unit="s")

    def transition(self, plan: InvestigationPlan, event: str) -> None:
        if event == "investigation_created":
            self.investigations.add(1)
        elif event == "evidence_gap_identified":
            self.hypotheses.add(len(plan.hypotheses))
            self.gaps.add(len(plan.gaps))
        elif event == "capability_resolution_completed":
            self.unavailable.add(
                sum(need.availability is Availability.UNAVAILABLE for need in plan.signal_needs)
            )
        elif event == "recipe_proposed":
            self.recipes.add(1)
            if plan.recipe and plan.recipe.feasibility is Feasibility.FEASIBLE:
                self.feasible.add(1)
            elif plan.recipe and plan.recipe.feasibility is Feasibility.FEASIBLE_WITH_DEGRADATION:
                self.degraded.add(1)
        elif event == "approved":
            self.approvals.add(1)
        elif event == "reanalysis_started":
            self.reanalyses.add(1)

        if plan.status in {
            InvestigationStatus.COMPLETED,
            InvestigationStatus.INCONCLUSIVE,
            InvestigationStatus.FAILED,
        }:
            counter = {
                InvestigationStatus.COMPLETED: self.completed,
                InvestigationStatus.INCONCLUSIVE: self.inconclusive,
                InvestigationStatus.FAILED: self.failures,
            }[plan.status]
            counter.add(1)
            self.duration.record((plan.updated_at - plan.created_at).total_seconds())

        self.telemetry.log(
            "investigation.transition",
            str(plan.id),
            investigation_id=str(plan.id),
            agent_run_id=str(plan.agent_run_id),
            transition=event,
            hypothesis_count=len(plan.hypotheses),
            gap_count=len(plan.gaps),
            signal_need_count=len(plan.signal_needs),
            recipe_version=plan.recipe.version if plan.recipe else None,
            recipe_hash=plan.recipe.configuration_hash if plan.recipe else None,
            feasibility=plan.recipe.feasibility.value if plan.recipe else None,
            approval_state=plan.approval.status,
            linked_session_count=len(plan.linked_session_ids),
            status=plan.status.value,
            duration_seconds=(plan.updated_at - plan.created_at).total_seconds(),
        )
