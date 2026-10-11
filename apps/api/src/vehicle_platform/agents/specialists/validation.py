"""Grounded specialist output, deterministic conflicts and evidence sufficiency."""

from uuid import UUID, uuid4

from vehicle_platform.agents.evidence import EvidenceRegistry
from vehicle_platform.agents.grounding import validate
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import Claim, Classification, Draft
from vehicle_platform.agents.specialists.contracts import (
    Conflict,
    Intent,
    Specialist,
    SpecialistDraft,
    SpecialistFinding,
    SpecialistRequest,
    SpecialistResult,
    Sufficiency,
)


def validate_source_context(
    identifiers: list[UUID], request: SpecialistRequest, registry: EvidenceRegistry
) -> None:
    sessions = {str(s["id"]): s for s in request.context.sessions}
    configurations = {str(c["id"]) for c in request.context.configurations}
    for identifier in identifiers:
        source = registry.items.get(identifier)
        if source is None:
            raise AgentError("unknown_evidence")
        if source.configuration_id and str(source.configuration_id) not in configurations:
            raise AgentError("incompatible_specialist_context")
        if source.session_id:
            session = sessions.get(str(source.session_id))
            if (
                not session
                or not session.get("temporal_configuration_valid")
                or (
                    source.configuration_id
                    and str(source.configuration_id) != str(session.get("configuration_id"))
                )
            ):
                raise AgentError("incompatible_specialist_context")


def materialize(
    response: SpecialistDraft, request: SpecialistRequest, registry: EvidenceRegistry
) -> list[SpecialistFinding]:
    if (
        response.specialist != request.specialist
        or response.supervisor_run_id != request.supervisor_run_id
        or response.vehicle_id != request.vehicle_id
        or registry.run_id != request.supervisor_run_id
        or registry.vehicle_id != request.vehicle_id
    ):
        raise AgentError("specialist_identity_violation")
    if len(response.draft.claims) > 8:
        raise AgentError("specialist_result_budget_exhausted")
    for claim in response.draft.claims:
        validate_source_context(claim.evidence_ids, request, registry)
    answer = validate(response.draft, registry, request.context)
    results: list[SpecialistFinding] = []
    for finding in answer.findings:
        sources = [registry.items[identifier] for identifier in finding.evidence_ids]
        results.append(
            SpecialistFinding(
                **finding.model_dump(),
                finding_id=uuid4(),
                specialist=request.specialist,
                strength=answer.confidence,
                limitations=answer.limitations[:16],
                session_ids=list(dict.fromkeys(e.session_id for e in sources if e.session_id)),
                configuration_ids=list(
                    dict.fromkeys(e.configuration_id for e in sources if e.configuration_id)
                ),
            )
        )
    return results


def validate_result(
    result: SpecialistResult, request: SpecialistRequest, registry: EvidenceRegistry
) -> None:
    if (
        result.specialist != request.specialist
        or result.supervisor_run_id != request.supervisor_run_id
        or result.vehicle_id != request.vehicle_id
        or result.prompt_version != request.prompt_version
        or (result.budget is not None and result.budget != request.budget)
    ):
        raise AgentError("specialist_identity_violation")
    if (
        result.tool_call_count > request.budget.mcp_calls
        or result.model_turn_count > request.budget.model_turns
        or result.telemetry_call_count > request.budget.telemetry_windows
        or len(result.evidence_ids) > request.budget.evidence_items
        or len(result.model_dump_json().encode()) > request.budget.result_bytes
    ):
        raise AgentError("specialist_result_budget_exhausted")
    if result.status != "completed" and result.findings:
        raise AgentError("invalid_specialist_result")
    for identifier in result.evidence_ids:
        source = registry.items.get(identifier)
        if (
            not source
            or source.run_id != request.supervisor_run_id
            or source.vehicle_id != request.vehicle_id
        ):
            raise AgentError("unknown_evidence")
    if len({f.finding_id for f in result.findings}) != len(result.findings):
        raise AgentError("invalid_specialist_result")
    claims: list[Claim] = []
    for finding in result.findings:
        validate_source_context(finding.evidence_ids, request, registry)
        if finding.specialist != request.specialist or not set(finding.evidence_ids) <= set(
            result.evidence_ids
        ):
            raise AgentError("specialist_identity_violation")
        claims.append(Claim(**finding.model_dump(include=set(Claim.model_fields))))
    if claims:
        grounded = validate(
            Draft(confidence=result.confidence, claims=claims, missing_evidence=[]),
            registry,
            request.context,
        )
        for supplied, rendered in zip(result.findings, grounded.findings, strict=True):
            if supplied.statement != rendered.statement:
                raise AgentError("invalid_specialist_statement")
            sources = [registry.items[i] for i in supplied.evidence_ids]
            if set(supplied.session_ids) != {e.session_id for e in sources if e.session_id} or set(
                supplied.configuration_ids
            ) != {e.configuration_id for e in sources if e.configuration_id}:
                raise AgentError("incompatible_specialist_context")
        strengths = {"low": 0, "moderate": 1, "high": 2}
        if any(strengths[f.strength] > strengths[grounded.confidence] for f in result.findings):
            raise AgentError("invalid_specialist_confidence")


def validate_conflict(conflict: Conflict, results: list[SpecialistResult]) -> None:
    findings = {
        f.finding_id: f
        for result in results
        if result.status == "completed"
        for f in result.findings
    }
    if len(set(conflict.finding_ids)) < 2 or any(
        identifier not in findings for identifier in conflict.finding_ids
    ):
        raise AgentError("invalid_specialist_conflict")
    if len({findings[i].specialist for i in conflict.finding_ids}) < 2:
        raise AgentError("invalid_specialist_conflict")
    selected = [findings[i] for i in conflict.finding_ids]
    if conflict.type == "factual":
        disagreement = any(
            (a.evidence_id, a.path) == (b.evidence_id, b.path)
            and (a.value != b.value or a.unit != b.unit)
            for left in selected
            for right in selected
            if left.specialist != right.specialist
            for a in left.bindings
            for b in right.bindings
        )
        valid = (
            disagreement and conflict.severity == "critical" and not conflict.requires_investigation
        )
    elif conflict.type == "competing_hypotheses":
        thermal = any(
            f.specialist is Specialist.THERMAL
            and not f.limitations
            and (
                f.classification is Classification.HYPOTHESIS
                or any(
                    b.path == "/event_type" and b.value in {"iat_rise", "intake_temperature_high"}
                    for b in f.bindings
                )
            )
            for f in selected
        )
        fuel = any(
            f.specialist is Specialist.FUEL_AIR_BOOST
            and not f.limitations
            and any(
                b.path == "/event_type" and b.value in {"boost_drop", "fuel_pressure_drop"}
                for b in f.bindings
            )
            for f in selected
        )
        valid = (
            thermal
            and fuel
            and conflict.requires_investigation
            and not conflict.resolvable_with_existing_evidence
        )
    else:
        # No provider-created temporal/sufficiency conflict is accepted without an
        # application evaluator that proves that relationship from grounded findings.
        valid = False
    if not valid:
        raise AgentError("invalid_specialist_conflict")


def conflicts_for(results: list[SpecialistResult], intent: Intent) -> list[Conflict]:
    findings = [f for r in results if r.status == "completed" for f in r.findings]
    conflicts: list[Conflict] = []
    # A valid fact must exactly match registry data. Any disagreeing bindings to the same
    # source/path are nevertheless rejected before synthesis if this layer is called alone.
    seen: dict[tuple[UUID, str], SpecialistFinding] = {}
    for finding in findings:
        for binding in finding.bindings:
            key = (binding.evidence_id, binding.path)
            previous = seen.get(key)
            if previous and previous.specialist != finding.specialist:
                prior = next(b for b in previous.bindings if (b.evidence_id, b.path) == key)
                if prior.value != binding.value or prior.unit != binding.unit:
                    conflict = Conflict(
                        conflict_id=uuid4(),
                        finding_ids=[previous.finding_id, finding.finding_id],
                        type="factual",
                        severity="critical",
                        explanation="Bindings disagree for one evidence path; synthesis blocked.",
                        resolvable_with_existing_evidence=True,
                        requires_investigation=False,
                    )
                    validate_conflict(conflict, results)
                    conflicts.append(conflict)
            seen[key] = finding
    if intent in {Intent.MULTI_MECHANISM, Intent.REPEATED_DEGRADATION}:
        # Only measured candidate mechanisms create a conflict. Merely selecting specialists
        # does not establish competing hypotheses, nor does missing evidence fabricate one.
        thermal = [
            f
            for f in findings
            if f.specialist is Specialist.THERMAL and f.bindings and not f.limitations
        ]
        fuel = [
            f
            for f in findings
            if f.specialist is Specialist.FUEL_AIR_BOOST and f.bindings and not f.limitations
        ]
        fuel_anomaly = [
            f
            for f in fuel
            if any(
                b.path == "/event_type" and b.value in {"boost_drop", "fuel_pressure_drop"}
                for b in f.bindings
            )
        ]
        thermal_anomaly = [
            f
            for f in thermal
            if f.classification is Classification.HYPOTHESIS
            or any(
                b.path == "/event_type" and b.value in {"iat_rise", "intake_temperature_high"}
                for b in f.bindings
            )
        ]
        if thermal_anomaly and fuel_anomaly:
            conflict = Conflict(
                conflict_id=uuid4(),
                finding_ids=[thermal_anomaly[0].finding_id, fuel_anomaly[0].finding_id],
                type="competing_hypotheses",
                severity="warning",
                explanation=(
                    "Recorded thermal and fuel/boost anomalies coexist; "
                    "evidence does not isolate a cause."
                ),
                resolvable_with_existing_evidence=False,
                requires_investigation=True,
            )
            validate_conflict(conflict, results)
            conflicts.append(conflict)
    return conflicts[:8]


def sufficiency_for(
    results: list[SpecialistResult], conflicts: list[Conflict], *, quality_required: bool
) -> Sufficiency:
    quality = next((r for r in results if r.specialist is Specialist.DATA_QUALITY), None)
    if quality_required and (
        quality is None
        or quality.status != "completed"
        or quality.blocks_interpretation
        or "data_quality" in quality.evidence_gaps
    ):
        return Sufficiency.UNRELIABLE_DATA
    if any(c.severity == "critical" or c.requires_investigation for c in conflicts):
        return Sufficiency.INSUFFICIENT
    completed = [
        r
        for r in results
        if r.status == "completed" and r.specialist is not Specialist.DATA_QUALITY
    ]
    factual = [
        f
        for r in completed
        for f in r.findings
        if f.classification not in {Classification.INSUFFICIENT_EVIDENCE, Classification.UNKNOWN}
        and f.bindings
    ]
    if not factual:
        return Sufficiency.INSUFFICIENT
    if any(
        r.status != "completed"
        or r.evidence_gaps
        or r.data_quality_warnings
        or any(
            f.classification in {Classification.INSUFFICIENT_EVIDENCE, Classification.UNKNOWN}
            or bool(f.limitations)
            for f in r.findings
        )
        for r in results
    ):
        return (
            Sufficiency.PARTIALLY_SUFFICIENT
            if any(r.findings for r in completed)
            else Sufficiency.INSUFFICIENT
        )
    return Sufficiency.SUFFICIENT
