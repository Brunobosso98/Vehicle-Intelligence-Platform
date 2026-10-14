"""One supervisor; bounded siblings share only current-run evidence and MCP calls."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import TYPE_CHECKING, Any
from uuid import UUID

from vehicle_platform.agents.config import redact_data
from vehicle_platform.agents.evidence import EvidenceRegistry, canonical_hash
from vehicle_platform.agents.mcp_client import RECOVERABLE_TOOL_ERRORS
from vehicle_platform.agents.provider import AgentError, ModelInput, ModelTurn, RoutingInput
from vehicle_platform.agents.schemas import (
    Binding,
    Claim,
    Classification,
    Draft,
    Finding,
    RoutingProposal,
    Specialist,
    SpecialistDraft,
    SpecialistRequest,
    SpecialistResult,
    Sufficiency,
    SupervisorLimits,
    SupervisorReport,
    Usage,
)
from vehicle_platform.agents.specialists.policy import REGISTRY, enforce_tool, tools_for
from vehicle_platform.agents.specialists.routing import (
    QUALITY_EVENTS,
    decide,
    event_types,
    hints_for,
)
from vehicle_platform.agents.specialists.tool_scope import scoped_tool_definitions
from vehicle_platform.agents.specialists.validation import (
    conflicts_for,
    materialize,
    sufficiency_for,
    validate_result,
)
from vehicle_platform.agents.state import Execution

if TYPE_CHECKING:
    from vehicle_platform.agents.orchestration import Orchestrator


ZERO_USAGE = Usage(input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0)


def quality_observation_bindings(finding: Finding, registry: EvidenceRegistry) -> list[Binding]:
    bindings: dict[tuple[UUID, str], Binding] = {}
    event_paths = {
        "/event_type",
        "/evidence/signal",
        "/duration_ms",
        "/severity",
        "/started_at",
        "/ended_at",
        "/evidence/gap_seconds",
        "/evidence/analysis_confidence_reduced",
    }
    for binding in finding.bindings:
        source = registry.items[binding.evidence_id]
        event_type = next(
            (
                fact
                for fact in source.facts
                if fact.path == "/event_type" and fact.value in QUALITY_EVENTS
            ),
            None,
        )
        quality_event = (
            source.source_tool
            in {
                "list_session_events",
                "list_pull_events",
                "get_event",
            }
            and event_type is not None
        )
        if source.source_tool == "get_session_capabilities" or (
            quality_event and binding.path in event_paths
        ):
            if quality_event and event_type is not None:
                bindings[(source.id, event_type.path)] = Binding(
                    evidence_id=source.id,
                    path=event_type.path,
                    value=event_type.value,
                    unit=event_type.unit,
                )
            bindings[(binding.evidence_id, binding.path)] = binding
    return list(bindings.values())[:8]


def performance_discovery_sessions(request: SpecialistRequest) -> list[dict[str, Any]]:
    allowed = {str(i) for i in request.session_ids}
    sessions = [s for s in request.context.sessions if str(s["id"]) in allowed]
    selected = sessions[:2]
    comparison = any(
        word in request.question.casefold()
        for word in ("configur", "modific", "replacement", "intercooler")
    )
    if not comparison or not sessions:
        return selected
    first = sessions[0]
    if not first.get("configuration_id") or not first.get("temporal_configuration_valid"):
        return selected
    contrast = next(
        (
            s
            for s in sessions[1:]
            if s.get("temporal_configuration_valid")
            and s.get("configuration_id")
            and str(s["configuration_id"]) != str(first["configuration_id"])
        ),
        None,
    )
    return [first, contrast] if contrast is not None else selected


class Supervisor:
    def __init__(self, engine: "Orchestrator", state: Execution) -> None:
        self.engine, self.state = engine, state
        self.settings = engine.settings
        self.semaphore = asyncio.Semaphore(self.settings.max_concurrent_specialists)
        self.shared_ids: tuple[UUID, ...] | None = None

    def reserve_turn(self) -> None:
        if self.state.steps >= self.settings.max_steps:
            raise AgentError("step_budget_exhausted")
        self.state.steps += 1
        if self.state.run.supervisor:
            self.state.run.supervisor.model_turn_count = self.state.steps

    def add_usage(self, usage: Usage) -> None:
        from vehicle_platform.agents.orchestration import accumulate

        self.state.run.usage = accumulate(self.state.run.usage, usage, self.state.steps == 1)

    def enforce_scope(self, request: SpecialistRequest, arguments: dict[str, Any]) -> None:
        sessions = {str(i) for i in request.session_ids}
        requested_sessions = list(arguments.get("session_ids", []))
        if arguments.get("session_id"):
            requested_sessions.append(arguments["session_id"])
        if any(str(i) not in sessions for i in requested_sessions):
            raise AgentError("incompatible_specialist_context")
        pulls = list(arguments.get("pull_ids", []))
        pulls += list(arguments.get("before_pull_ids", []))
        pulls += list(arguments.get("after_pull_ids", []))
        if arguments.get("pull_id"):
            pulls.append(arguments["pull_id"])
        known = {
            str(e.pull_id)
            for e in self.state.registry.items.values()
            if e.pull_id and str(e.session_id) in sessions
        }
        if any(str(i) not in known for i in pulls):
            raise AgentError("incompatible_specialist_context")
        if arguments.get("event_id") and str(arguments["event_id"]) not in {
            str(e.event_id)
            for e in self.state.registry.items.values()
            if e.event_id and str(e.session_id) in sessions
        }:
            raise AgentError("incompatible_specialist_context")

    async def discover_performance_pulls(
        self, request: SpecialistRequest, result: SpecialistResult, owned_ids: set[UUID]
    ) -> None:
        """Resolve bounded, owned pull IDs before a performance model can compare them."""
        if request.specialist is not Specialist.PERFORMANCE:
            return
        state = self.state
        for session in performance_discovery_sessions(request):
            session_id = str(session["id"])
            if any(
                e.id in owned_ids
                and e.source_tool == "list_session_pulls"
                and str(e.session_id) == session_id
                for e in state.registry.items.values()
            ):
                continue
            arguments = {
                "vehicle_id": str(request.vehicle_id),
                "session_id": session_id,
                "limit": 20,
            }
            enforce_tool(request.specialist, "list_session_pulls")
            self.enforce_scope(request, arguments)
            if result.tool_call_count >= request.budget.mcp_calls:
                raise AgentError("specialist_tool_budget_exhausted")
            result.tool_call_count += 1
            identity = canonical_hash({"tool": "list_session_pulls", "arguments": arguments})
            await state.emit(
                "specialist_tool_started",
                {"specialist": request.specialist.value, "tool": "list_session_pulls"},
            )
            async with state.tool_lock:
                hit = identity in state.cache
                await self.engine.call_locked(state, "list_session_pulls", arguments)
                owned_ids.update(
                    i
                    for call in state.tool_calls
                    if call.argument_hash == identity
                    for i in call.evidence_ids
                )
            result.cache_hits += int(hit)
            await state.emit(
                "specialist_tool_completed",
                {
                    "specialist": request.specialist.value,
                    "tool": "list_session_pulls",
                    "cache_hit": hit,
                },
            )
        sessions = set(request.session_ids)
        request.pull_ids = list(
            dict.fromkeys(
                e.pull_id
                for e in state.registry.items.values()
                if e.id in owned_ids and e.pull_id and e.session_id in sessions
            )
        )[:20]

    async def run(self) -> None:
        state = self.state
        if state.context is None:
            raise AgentError("context_missing")
        await state.emit("supervisor_started", {"prompt_version": "supervisor-v3"})
        started = perf_counter()
        initial = hints_for(state.ask.question, list(state.registry.items.values()))
        if initial.candidates and state.context.sessions:
            args = {
                "vehicle_id": str(state.run.vehicle_id),
                "session_id": str(state.context.sessions[0]["id"]),
            }
            await self.engine.call(state, "get_session_summary", args)
            await self.engine.call(state, "list_session_events", args | {"limit": 20})
        hints = hints_for(state.ask.question, list(state.registry.items.values()))
        with self.engine.telemetry.tracer.start_as_current_span(
            "supervisor.routing", record_exception=False, set_status_on_exception=False
        ):
            if hints.candidates:
                self.reserve_turn()
                request = RoutingInput(
                    question=state.ask.question,
                    context=state.context.model_dump(mode="json"),
                    evidence=[e.model_dump(mode="json") for e in state.registry.items.values()],
                    candidates=[s.value for s in hints.candidates],
                    hints=list(hints.hints),
                )
                request = RoutingInput(**redact_data(request.__dict__, self.settings))
                if len(json.dumps(request.__dict__).encode()) > self.settings.max_input_bytes:
                    raise AgentError("model_input_budget_exhausted")
                async with asyncio.timeout(self.settings.model_timeout):
                    proposal = await self.engine.provider.route(request)
                proposal = RoutingProposal.model_validate(proposal)
                self.add_usage(proposal.usage)
            else:
                from vehicle_platform.agents.schemas import Intent

                proposal = RoutingProposal(intent=hints.intent or Intent.FACTUAL, usage=ZERO_USAGE)
            decision = decide(hints, proposal, state.context, self.settings.max_specialists)
        report = SupervisorReport(
            routing=decision,
            routing_usage=proposal.usage,
            routing_seconds=perf_counter() - started,
            model_turn_count=state.steps,
            limits=SupervisorLimits(
                specialists=self.settings.max_specialists,
                concurrent_specialists=self.settings.max_concurrent_specialists,
                model_turns=self.settings.max_steps,
                mcp_calls=self.settings.max_tool_calls,
                telemetry_windows=self.settings.max_telemetry_calls,
                retries=self.settings.max_provider_retries,
                timeout_seconds=self.settings.run_timeout,
                evidence_items=self.settings.max_evidence,
                input_bytes=self.settings.max_input_bytes,
                tool_result_bytes=self.settings.max_result_bytes,
            ),
        )
        report.configuration_hash = canonical_hash(
            {
                "version": report.prompt_version,
                "grounded_synthesis": "grounded-v6",
                "routing_hints": "1.5",
                "mcp_context_instructions": "1.0",
                "tool_error_feedback": "1.0",
                "scoped_tool_schemas": "1.0",
                "specialist_terminal_draft": "1.0",
                "quality_blocked_role_records": "1.0",
                "quality_observation_projection": "1.1",
                "evidence_collection_projection": "agent-collection-v1",
                "performance_pull_discovery": {"version": "1.1", "sessions": 2, "limit": 20},
                "limits": report.limits.model_dump() if report.limits else {},
                "roles": {
                    s.value: {
                        "version": p.prompt_version,
                        "tools": sorted(p.allowed_tools),
                        "budget": p.budget().model_dump(),
                    }
                    for s, p in REGISTRY.items()
                },
            }
        )
        state.run.supervisor = report
        self.engine.telemetry.log(
            "supervisor.routing.completed",
            str(state.run.id),
            agent_run_id=str(state.run.id),
            supervisor_state="routing_completed",
            selected=[s.value for s in decision.selected],
            skipped=[s.value for s in decision.skipped],
            duration_seconds=report.routing_seconds,
        )
        await state.emit("routing_completed", decision.model_dump(mode="json"))
        if not decision.data_quality_gate and not decision.selected:
            return
        if decision.data_quality_gate:
            quality = await self.execute_specialist(Specialist.DATA_QUALITY)
            if sufficiency_for([quality], [], quality_required=True) is Sufficiency.UNRELIABLE_DATA:
                report.sufficiency = Sufficiency.UNRELIABLE_DATA
                report.investigation_recommended = True
                for specialist in decision.selected:
                    skipped = SpecialistResult(
                        specialist=specialist,
                        supervisor_run_id=state.run.id,
                        vehicle_id=state.run.vehicle_id,
                        status="skipped",
                        prompt_version=REGISTRY[specialist].prompt_version,
                        evidence_gaps=["data_quality"],
                        data_quality_warnings=["quality_gate_blocked"],
                        error_category="quality_gate_blocked",
                        usage=ZERO_USAGE,
                        budget=REGISTRY[specialist]
                        .budget()
                        .model_copy(update={"timeout_seconds": self.settings.specialist_timeout}),
                    )
                    report.specialists.append(skipped)
                    await state.emit("specialist_completed", skipped.model_dump(mode="json"))
                await self.evaluate()
                self.synthesize_unreliable()
                return
        self.shared_ids = tuple(state.registry.items)[:50]
        tasks = [asyncio.create_task(self.execute_specialist(s)) for s in decision.selected]
        try:
            # gather preserves routing order despite completion order. Cancellation drains siblings.
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        if decision.data_quality_gate:
            quality.data_quality_warnings, quality.blocks_interpretation = self.quality_warnings()
            if quality.blocks_interpretation:
                quality.evidence_gaps = ["data_quality"]
        report.conflicts = conflicts_for(report.specialists, decision.intent)
        for conflict in report.conflicts:
            await state.emit("conflict_detected", conflict.model_dump(mode="json"))
        report.sufficiency = sufficiency_for(
            report.specialists, report.conflicts, quality_required=decision.data_quality_gate
        )
        report.investigation_recommended = report.sufficiency in {
            Sufficiency.INSUFFICIENT,
            Sufficiency.UNRELIABLE_DATA,
        } or any(
            r.status != "completed"
            or r.evidence_gaps
            or any(
                f.classification in {Classification.INSUFFICIENT_EVIDENCE, Classification.UNKNOWN}
                for f in r.findings
            )
            for r in report.specialists
        )
        await self.evaluate()
        if report.sufficiency is Sufficiency.UNRELIABLE_DATA:
            self.synthesize_unreliable()
            return
        await state.emit("synthesis_started", {"sufficiency": report.sufficiency.value})

    async def evaluate(self) -> None:
        with self.engine.telemetry.tracer.start_as_current_span(
            "supervisor.sufficiency", record_exception=False, set_status_on_exception=False
        ):
            await self.evaluate_scoped()

    async def evaluate_scoped(self) -> None:
        report = self.state.run.supervisor
        if report is None:
            raise AgentError("invalid_supervisor_state")
        await self.state.emit("sufficiency_evaluated", {"sufficiency": report.sufficiency.value})
        self.engine.telemetry.log(
            "supervisor.sufficiency.evaluated",
            str(self.state.run.id),
            agent_run_id=str(self.state.run.id),
            supervisor_state="sufficiency_evaluated",
            conflict_count=len(report.conflicts),
            sufficiency=report.sufficiency.value,
            phase7b_proposed=report.investigation_recommended,
        )
        if report.investigation_recommended:
            await self.state.emit(
                "investigation_proposed",
                {"workflow": "phase7b", "agent_run_id": str(self.state.run.id)},
            )

    def synthesize_unreliable(self) -> None:
        from vehicle_platform.agents.grounding import validate

        if self.state.context is None:
            raise AgentError("context_missing")
        quality_claims: list[Claim] = []
        report = self.state.run.supervisor
        for result in report.specialists if report else []:
            if result.specialist is not Specialist.DATA_QUALITY or result.status != "completed":
                continue
            for finding in result.findings:
                if (
                    finding.template != "recorded_fact"
                    or finding.classification is not Classification.OBSERVATION
                ):
                    continue
                bindings = quality_observation_bindings(finding, self.state.registry)
                if bindings and len(quality_claims) < 8:
                    quality_claims.append(
                        Claim(
                            classification=Classification.OBSERVATION,
                            template="recorded_fact",
                            bindings=bindings,
                            evidence_ids=list(dict.fromkeys(b.evidence_id for b in bindings)),
                        )
                    )
        proposed = Draft(
            confidence="low",
            claims=[
                *quality_claims,
                Claim(
                    classification=Classification.INSUFFICIENT_EVIDENCE,
                    template="insufficient_evidence",
                    evidence_ids=[],
                    bindings=[],
                ),
            ],
            missing_evidence=["data_quality", "signal_or_measurement"],
        )
        self.state.final = validate(proposed, self.state.registry, self.state.context)
        self.state.final.limitations.append(
            "Telemetry quality was not verified; deeper analysis blocked."
        )

    def quality_warnings(self) -> tuple[list[str], bool]:
        state = self.state
        if state.context is None or not state.context.sessions:
            return ["no_recorded_session"], True
        session_ids = list(state.context.capabilities) or [str(state.context.sessions[0]["id"])]
        warnings: list[str] = []
        blocked = False
        for sid in session_ids:
            current, blocking = self.session_quality_warnings(sid)
            warnings.extend(current)
            blocked |= blocking
        return list(dict.fromkeys(warnings)), blocked

    def session_quality_warnings(self, sid: str) -> tuple[list[str], bool]:
        state = self.state
        if state.context is None:
            return ["no_recorded_session"], True
        report = state.context.capabilities.get(sid)
        if not report or not report.get("signal_quality"):
            return ["recorded_signal_quality_unavailable"], True
        warnings: list[str] = []
        blocking = False
        quality = report["signal_quality"]
        rpm = next((q for q in quality if q.get("signal") == "engine.rpm"), None)
        if not rpm:
            warnings.append("engine_speed_quality_unavailable")
            blocking = True
        for q in quality:
            if q.get("signal") != "engine.rpm":
                continue
            hz, missing = q.get("actual_hz"), q.get("missing_ratio")
            if not isinstance(hz, (int, float)) or hz <= 0:
                warnings.append("engine_speed_sampling_unverified")
                blocking = True
            stale = q.get("stale_ratio", 0)
            if not isinstance(stale, (int, float)) or stale > 0.2:
                warnings.append("engine_speed_stale")
                blocking = True
            if not isinstance(missing, (int, float)) or missing > 0.2:
                if (
                    isinstance(hz, (int, float))
                    and hz >= 5
                    and isinstance(missing, (int, float))
                    and missing < 0.5
                    and q.get("stale_ratio") == 0
                ):
                    warnings.append("recorded_sampling_below_recipe_target")
                else:
                    warnings.append("engine_speed_dropout")
                    blocking = True
        recorded = [e for e in state.registry.items.values() if str(e.session_id) == sid]
        families = {
            Specialist.PERFORMANCE: {"engine.rpm", "vehicle.speed", "engine.throttle_position"},
            Specialist.THERMAL: {
                "engine.rpm",
                "engine.intake_air_temperature",
                "engine.oil_temperature",
                "engine.coolant_temperature",
            },
            Specialist.FUEL_AIR_BOOST: {
                "engine.rpm",
                "engine.throttle_position",
                "engine.boost_pressure",
                "fuel.high_pressure",
                "fuel.low_pressure",
                "fuel.equivalence_ratio",
            },
        }
        selected = state.run.supervisor.routing.selected if state.run.supervisor else []
        relevant = (
            set().union(*(families[s] for s in selected))
            if selected
            else set().union(*families.values())
        )
        for q in quality:
            signal = q.get("signal")
            if signal == "engine.rpm" or signal not in relevant:
                continue
            hz, missing, stale = q.get("actual_hz"), q.get("missing_ratio"), q.get("stale_ratio", 0)
            if not isinstance(hz, (int, float)) or hz <= 0:
                warnings.append("relevant_signal_sampling_unverified")
                blocking = True
            if not isinstance(missing, (int, float)) or missing > 0.2:
                if (
                    isinstance(hz, (int, float))
                    and hz >= 5
                    and isinstance(missing, (int, float))
                    and missing < 0.5
                    and stale == 0
                ):
                    warnings.append("recorded_sampling_below_recipe_target")
                else:
                    warnings.append("relevant_signal_dropout")
                    blocking = True
            if not isinstance(stale, (int, float)) or stale > 0.2:
                warnings.append("relevant_signal_stale")
                blocking = True
        for event in recorded:
            if not event_types([event]) & QUALITY_EVENTS:
                continue
            signal = next((f.value for f in event.facts if f.path == "/evidence/signal"), None)
            if signal is None or signal == "all" or signal in relevant:
                warnings.append("recorded_quality_anomaly")
                blocking = True
            else:
                warnings.append("unrelated_signal_quality_event")
        requested = {
            "boost": "engine.boost_pressure",
            "lambda": "fuel.equivalence_ratio",
            "hpfp": "fuel.high_pressure",
            "fuel pressure": "fuel.high_pressure",
            "iat": "engine.intake_air_temperature",
            "coolant": "engine.coolant_temperature",
            "oil temperature": "engine.oil_temperature",
        }
        if "available_signals" in report and any(
            word in state.ask.question.casefold() and signal not in report["available_signals"]
            for word, signal in requested.items()
        ):
            warnings.append("requested_signal_unavailable")
        if any(e.truncated for e in recorded if e.source_tool == "get_session_capabilities"):
            warnings.append("quality_evidence_truncated")
            blocking = True
        return list(dict.fromkeys(warnings)), blocking

    async def execute_specialist(self, specialist: Specialist) -> SpecialistResult:
        async with self.semaphore:
            return await self.execute_scoped(specialist)

    async def execute_scoped(self, specialist: Specialist) -> SpecialistResult:
        from vehicle_platform.agents.orchestration import accumulate

        state = self.state
        if state.context is None:
            raise AgentError("context_missing")
        policy = REGISTRY[specialist]
        request = SpecialistRequest(
            specialist=specialist,
            supervisor_run_id=state.run.id,
            vehicle_id=state.run.vehicle_id,
            context=state.context.model_copy(deep=True),
            question=state.ask.question,
            scoped_objective=policy.objective,
            evidence_ids=list(self.shared_ids or tuple(state.registry.items)[:50]),
            session_ids=[UUID(str(s["id"])) for s in state.context.sessions],
            allowed_tools=sorted(policy.allowed_tools),
            budget=policy.budget().model_copy(
                update={"timeout_seconds": self.settings.specialist_timeout}
            ),
            deadline=datetime.now(UTC) + timedelta(seconds=self.settings.specialist_timeout),
            prompt_version=policy.prompt_version,
        )
        result = SpecialistResult(
            specialist=specialist,
            supervisor_run_id=state.run.id,
            vehicle_id=state.run.vehicle_id,
            status="failed",
            prompt_version=policy.prompt_version,
            budget=request.budget,
            usage=ZERO_USAGE,
        )
        if specialist is Specialist.DATA_QUALITY:
            result.data_quality_warnings, result.blocks_interpretation = self.quality_warnings()
        await state.emit("specialist_started", {"specialist": specialist.value})
        started = perf_counter()
        messages: list[dict[str, Any]] = []
        owned_ids = set(request.evidence_ids)
        turn_pending = False
        with self.engine.telemetry.tracer.start_as_current_span(
            "supervisor.specialist",
            record_exception=False,
            set_status_on_exception=False,
            attributes={"specialist": specialist.value},
        ) as span:
            result.trace_id = f"{span.get_span_context().trace_id:032x}"
            try:
                async with asyncio.timeout(request.budget.timeout_seconds):
                    await self.discover_performance_pulls(request, result, owned_ids)
                    for _ in range(request.budget.model_turns):
                        self.reserve_turn()
                        result.model_turn_count += 1
                        model_input = ModelInput(
                            question=request.question,
                            tools=(
                                scoped_tool_definitions(
                                    request,
                                    tools_for(specialist, state.tools),
                                    [e for i, e in state.registry.items.items() if i in owned_ids],
                                )
                                if result.model_turn_count < request.budget.model_turns
                                else []
                            ),
                            context=request.context.model_dump(mode="json"),
                            evidence=[
                                e.model_dump(mode="json")
                                for e in state.registry.ordered()
                                if e.id in owned_ids
                            ],
                            messages=messages,
                            specialist=request,
                        )
                        sanitized = redact_data(model_input.__dict__, self.settings)
                        sanitized["specialist"] = SpecialistRequest.model_validate(
                            redact_data(request.model_dump(mode="json"), self.settings)
                        )
                        model_input = ModelInput(**sanitized)
                        if (
                            len(
                                json.dumps(
                                    sanitized | {"specialist": request.model_dump(mode="json")}
                                ).encode()
                            )
                            > self.settings.max_input_bytes
                        ):
                            raise AgentError("model_input_budget_exhausted")
                        with self.engine.telemetry.tracer.start_as_current_span(
                            "specialist.model_turn",
                            record_exception=False,
                            set_status_on_exception=False,
                            attributes={"specialist": specialist.value},
                        ):
                            async with asyncio.timeout(self.settings.model_timeout):
                                turn_pending = True
                                turn = await self.engine.provider.turn(model_input)
                                turn_pending = False
                        if isinstance(turn, ModelTurn):
                            self.add_usage(turn.usage)
                            result.usage = accumulate(
                                result.usage, turn.usage, result.model_turn_count == 1
                            )
                        if (
                            not isinstance(turn, ModelTurn)
                            or bool(turn.tool_calls) == bool(turn.draft)
                            or len(turn.tool_calls) > 4
                        ):
                            raise AgentError("invalid_specialist_result")
                        if turn.draft:
                            cited = {i for c in turn.draft.claims for i in c.evidence_ids}
                            if not cited <= owned_ids:
                                raise AgentError("unknown_evidence")
                            result.findings = materialize(
                                SpecialistDraft(
                                    specialist=specialist,
                                    supervisor_run_id=state.run.id,
                                    vehicle_id=state.run.vehicle_id,
                                    draft=turn.draft,
                                ),
                                request,
                                state.registry,
                            )
                            result.evidence_ids = sorted(cited, key=str)
                            result.evidence_gaps = list(turn.draft.missing_evidence)
                            result.confidence = min(
                                (f.strength for f in result.findings),
                                key={"low": 0, "moderate": 1, "high": 2}.__getitem__,
                            )
                            result.status = "completed"
                            break
                        for tool in turn.tool_calls:
                            enforce_tool(specialist, tool.name)
                            self.enforce_scope(request, tool.arguments)
                            from vehicle_platform.agents.orchestration import MEASURED_TOOLS

                            if tool.name in MEASURED_TOOLS:
                                session_ids = list(tool.arguments.get("session_ids", []))
                                if tool.arguments.get("session_id"):
                                    session_ids.append(tool.arguments["session_id"])
                                pull_ids = set(
                                    str(i)
                                    for key in ("pull_ids", "before_pull_ids", "after_pull_ids")
                                    for i in tool.arguments.get(key, [])
                                )
                                if tool.arguments.get("pull_id"):
                                    pull_ids.add(str(tool.arguments["pull_id"]))
                                session_ids.extend(
                                    str(e.session_id)
                                    for e in state.registry.items.values()
                                    if e.session_id and str(e.pull_id) in pull_ids
                                )
                                for sid in sorted(set(session_ids)):
                                    await self.engine.capabilities(state, UUID(sid))
                                if (
                                    specialist is not Specialist.DATA_QUALITY
                                    and self.quality_warnings()[1]
                                ):
                                    raise AgentError("unreliable_specialist_data")
                            if result.tool_call_count >= request.budget.mcp_calls:
                                raise AgentError("specialist_tool_budget_exhausted")
                            result.tool_call_count += 1
                            if tool.name == "get_telemetry_window":
                                if result.telemetry_call_count >= request.budget.telemetry_windows:
                                    raise AgentError("specialist_telemetry_budget_exhausted")
                                result.telemetry_call_count += 1
                            identity = canonical_hash(
                                {"tool": tool.name, "arguments": tool.arguments}
                            )
                            await state.emit(
                                "specialist_tool_started",
                                {"specialist": specialist.value, "tool": tool.name},
                            )
                            output: dict[str, Any]
                            async with state.tool_lock:
                                hit = identity in state.cache
                                try:
                                    await self.engine.call_locked(state, tool.name, tool.arguments)
                                except AgentError as exc:
                                    if exc.category not in RECOVERABLE_TOOL_ERRORS:
                                        raise
                                    ids = []
                                    output = {"status": "failed", "error_category": exc.category}
                                else:
                                    ids = [
                                        i
                                        for call in state.tool_calls
                                        if call.argument_hash == identity
                                        for i in call.evidence_ids
                                    ]
                                    output = {
                                        "status": "completed",
                                        "evidence_ids": [str(i) for i in ids],
                                    }
                            result.cache_hits += int(hit)
                            owned_ids.update(ids)
                            messages.extend(
                                [
                                    {
                                        "type": "function_call",
                                        "call_id": tool.call_id,
                                        "name": tool.name,
                                        "arguments": json.dumps(tool.arguments),
                                    },
                                    {
                                        "type": "function_call_output",
                                        "call_id": tool.call_id,
                                        "output": json.dumps(output),
                                    },
                                ]
                            )
                            await state.emit(
                                "specialist_tool_completed",
                                {
                                    "specialist": specialist.value,
                                    "tool": tool.name,
                                    "cache_hit": hit,
                                },
                            )
                    else:
                        raise AgentError("specialist_step_budget_exhausted")
                    if specialist is Specialist.DATA_QUALITY:
                        result.data_quality_warnings, result.blocks_interpretation = (
                            self.quality_warnings()
                        )
                        if result.blocks_interpretation:
                            result.evidence_gaps = ["data_quality"]
                        elif "requested_signal_unavailable" in result.data_quality_warnings:
                            result.evidence_gaps = ["signal_or_measurement"]
                        else:
                            # The application owns the blocking quality decision.
                            # An unsupported model category cannot contradict verified metadata.
                            result.evidence_gaps = [
                                gap for gap in result.evidence_gaps if gap != "data_quality"
                            ]
                    validate_result(result, request, state.registry)
            except asyncio.CancelledError:
                result.status, result.error_category = "cancelled", "cancelled"
                raise
            except TimeoutError:
                result.status, result.error_category = "timed_out", "specialist_timeout"
            except AgentError as exc:
                result.status, result.error_category = "failed", exc.category
            except Exception:
                result.status, result.error_category = "failed", "specialist_unavailable"
            finally:
                if turn_pending and self.settings.provider != "deterministic":
                    # An interrupted paid request can have unknown billed usage. Preserve
                    # that uncertainty in both role and parent aggregates.
                    result.usage = accumulate(result.usage, Usage(), False)
                    self.add_usage(Usage())
                result.duration_seconds = perf_counter() - started
                if result.status != "completed":
                    result.findings, result.evidence_ids = [], []
                report = state.run.supervisor
                if report:
                    report.specialists.append(result)
                    order = list(Specialist)
                    report.specialists.sort(key=lambda item: order.index(item.specialist))
                    report.cache_hits += result.cache_hits
                    for identifier in result.evidence_ids:
                        consumers = report.evidence_consumers.setdefault(str(identifier), [])
                        if specialist not in consumers:
                            consumers.append(specialist)
                            consumers.sort(key=order.index)
                await state.emit(
                    "specialist_completed" if result.status == "completed" else "specialist_failed",
                    result.model_dump(mode="json"),
                )
        return result
