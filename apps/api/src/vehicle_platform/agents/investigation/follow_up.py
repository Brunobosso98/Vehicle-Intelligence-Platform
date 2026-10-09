"""Conservative hypothesis updates from a new grounded AgentRun."""

from datetime import UTC, datetime
from uuid import UUID

from vehicle_platform.agents.investigation.domain import (
    EvidenceGap,
    GapStatus,
    GapType,
    Hypothesis,
    HypothesisCategory,
    HypothesisStatus,
    InvestigationOutcome,
    InvestigationPlan,
)
from vehicle_platform.agents.investigation.planning import ROLE_TO_SIGNAL
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import AgentRun, Evidence, ToolCall

EVENTS: dict[HypothesisCategory, frozenset[str]] = {
    HypothesisCategory.THERMAL: frozenset({"iat_rise", "intake_temperature_high"}),
    HypothesisCategory.AIRFLOW_BOOST: frozenset({"boost_drop", "boost_overshoot"}),
    HypothesisCategory.FUELING: frozenset({"fuel_pressure_drop"}),
    HypothesisCategory.THROTTLE_TORQUE_INTERVENTION: frozenset({"unexpected_throttle_closure"}),
    HypothesisCategory.DATA_QUALITY: frozenset({"telemetry_gap", "sensor_dropout", "signal_stuck"}),
}
SIGNALS: dict[HypothesisCategory, str] = {
    HypothesisCategory.THERMAL: "engine.intake_air_temperature",
    HypothesisCategory.AIRFLOW_BOOST: "engine.boost_pressure",
    HypothesisCategory.FUELING: "fuel.high_pressure",
    HypothesisCategory.THROTTLE_TORQUE_INTERVENTION: "engine.throttle_position",
    HypothesisCategory.DATA_QUALITY: "engine.rpm",
}


def _event_type(evidence: Evidence) -> str | None:
    if evidence.source_tool != "list_session_events" or evidence.warnings or evidence.truncated:
        return None
    return next(
        (
            str(fact.value)
            for fact in evidence.facts
            if fact.path == "/event_type" and isinstance(fact.value, str)
        ),
        None,
    )


def _quality_evidence(run: AgentRun, session_id: UUID, signal: str) -> UUID | None:
    if run.result is None:
        return None
    report = run.result.context.capabilities.get(str(session_id), {})
    for quality in report.get("signal_quality", []):
        if (
            isinstance(quality, dict)
            and quality.get("signal") == signal
            and isinstance(quality.get("actual_hz"), (int, float))
            and quality["actual_hz"] > 0
            and isinstance(quality.get("missing_ratio"), (int, float))
            and quality["missing_ratio"] <= 0.2
        ):
            return next(
                (
                    evidence.id
                    for evidence in run.evidence
                    if evidence.source_tool == "get_session_capabilities"
                    and evidence.session_id == session_id
                    and not evidence.warnings
                    and not evidence.truncated
                ),
                None,
            )
    return None


def update_hypotheses(
    plan: InvestigationPlan, run: AgentRun, calls: list[ToolCall]
) -> list[Hypothesis]:
    if (
        run.status != "completed"
        or run.result is None
        or run.vehicle_id != plan.vehicle_id
        or run.id != plan.reanalysis_run_id
        or len(plan.linked_session_ids) != 1
    ):
        raise AgentError("invalid_reanalysis_context")
    session_id = plan.linked_session_ids[0]
    complete_event_read = any(
        call.run_id == run.id
        and call.tool_name == "list_session_events"
        and call.status == "completed"
        and not call.truncated
        for call in calls
    )
    events = [
        evidence
        for evidence in run.evidence
        if evidence.run_id == run.id
        and evidence.vehicle_id == plan.vehicle_id
        and evidence.session_id == session_id
    ]
    resolved = {gap.id for gap in plan.gaps if gap.status is GapStatus.RESOLVED}
    updated: list[Hypothesis] = []
    for source in plan.hypotheses:
        item = source.model_copy(deep=True)
        event_types = EVENTS.get(item.category)
        if event_types:
            positive = [evidence.id for evidence in events if _event_type(evidence) in event_types]
            if positive:
                item.status = HypothesisStatus.SUPPORTED
                item.support_level = "factual_event_association"
                item.evidence_for = list(dict.fromkeys([*item.evidence_for, *positive]))[:8]
            elif complete_event_read and (
                quality_id := _quality_evidence(run, session_id, SIGNALS[item.category])
            ):
                item.status = HypothesisStatus.WEAKENED
                item.support_level = "no_matching_event_in_quality_checked_session"
                item.evidence_against = list(dict.fromkeys([*item.evidence_against, quality_id]))[
                    :8
                ]
            else:
                item.status = HypothesisStatus.UNRESOLVED
                item.support_level = "insufficient_new_evidence"
        else:
            item.status = HypothesisStatus.UNRESOLVED
            item.support_level = "no_deterministic_discriminator"
        item.missing_gap_ids = [gap_id for gap_id in item.missing_gap_ids if gap_id not in resolved]
        item.updated_at = datetime.now(UTC)
        updated.append(item)
    return updated


def resolve_followup_gaps(plan: InvestigationPlan, run: AgentRun) -> list[EvidenceGap]:
    if run.result is None or len(plan.linked_session_ids) != 1:
        raise AgentError("invalid_reanalysis_context")
    session_id = plan.linked_session_ids[0]
    needs = {need.id: need for need in plan.signal_needs}
    resolved: list[EvidenceGap] = []
    for source in plan.gaps:
        gap = source.model_copy(deep=True)
        if gap.status is GapStatus.AVAILABLE_IN_EXISTING_DATA:
            gap.status = GapStatus.RESOLVED
        elif gap.category in {GapType.SIGNAL_OR_MEASUREMENT, GapType.DATA_QUALITY}:
            required_signals = {
                signal
                for identifier in gap.signal_need_ids
                if needs[identifier].required
                if (signal := ROLE_TO_SIGNAL[needs[identifier].role]) is not None
            }
            if required_signals and all(
                _quality_evidence(run, session_id, signal) is not None
                for signal in required_signals
            ):
                gap.status = GapStatus.RESOLVED
                gap.resolution_source = "grounded_reanalysis_session_capabilities"
            elif gap.category is GapType.DATA_QUALITY and _quality_evidence(
                run, session_id, "engine.rpm"
            ):
                gap.status = GapStatus.RESOLVED
                gap.resolution_source = "grounded_reanalysis_session_quality"
        elif gap.category in {GapType.COMPARABLE_HISTORY, GapType.CONFIGURATION_CONTEXT}:
            if any(
                evidence.source_tool
                in {"get_cross_session_analytics", "compare_configurations", "compare_pulls"}
                and evidence.run_id == run.id
                and evidence.vehicle_id == plan.vehicle_id
                and not evidence.warnings
                and not evidence.truncated
                and any(
                    fact.path.endswith("/sufficiency") and fact.value == "sufficient"
                    for fact in evidence.facts
                )
                for evidence in run.evidence
            ):
                gap.status = GapStatus.RESOLVED
                gap.resolution_source = "grounded_reanalysis_comparison"
        resolved.append(gap)
    return resolved


def outcome(plan: InvestigationPlan, run: AgentRun) -> InvestigationOutcome:
    if run.result is None:
        raise AgentError("invalid_reanalysis_context")
    resolved = [gap.id for gap in plan.gaps if gap.status is GapStatus.RESOLVED]
    unresolved = [gap.id for gap in plan.gaps if gap.status is not GapStatus.RESOLVED]
    supported = [item.id for item in plan.hypotheses if item.status is HypothesisStatus.SUPPORTED]
    weakened = [
        item.id
        for item in plan.hypotheses
        if item.status in {HypothesisStatus.WEAKENED, HypothesisStatus.NOT_SUPPORTED}
    ]
    required_unresolved = any(
        gap.required and gap.status is not GapStatus.RESOLVED for gap in plan.gaps
    )
    classification = "INCONCLUSIVE" if required_unresolved or not supported else "ASSOCIATION"
    return InvestigationOutcome(
        conclusion=run.result.answer[:2000],
        classification=classification,
        confidence="low" if classification == "INCONCLUSIVE" else "moderate",
        evidence_summary=[finding.statement[:300] for finding in run.result.findings[:8]],
        resolved_gap_ids=resolved,
        unresolved_gap_ids=unresolved,
        supported_hypothesis_ids=supported,
        weakened_hypothesis_ids=weakened,
        limitations=[
            "Hypotheses remain associations; mechanical cause and failed components "
            "are not established",
            *run.result.limitations[:15],
        ],
        follow_up=(
            "Current evidence remains insufficient; further capture requires a new explicit plan"
            if classification == "INCONCLUSIVE"
            else None
        ),
    )
