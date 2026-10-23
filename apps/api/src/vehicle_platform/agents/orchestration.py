import asyncio
import hmac
import json
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph

from vehicle_platform.agents.config import AgentSettings, redact_data
from vehicle_platform.agents.context import resolve_context
from vehicle_platform.agents.evidence import canonical_hash
from vehicle_platform.agents.grounding import validate
from vehicle_platform.agents.mcp_client import RECOVERABLE_TOOL_ERRORS, EvidenceClient
from vehicle_platform.agents.prompts import CAPTURE_APPROVAL_LIMITATION
from vehicle_platform.agents.provider import AgentError, ModelInput, Provider
from vehicle_platform.agents.schemas import Answer, ToolCall, Usage
from vehicle_platform.agents.specialists.routing import prediction_request_intent
from vehicle_platform.agents.state import Execution, GraphState
from vehicle_platform.knowledge.context import knowledge_scope
from vehicle_platform.knowledge.grounding import render as render_knowledge
from vehicle_platform.knowledge.grounding import report as knowledge_report
from vehicle_platform.knowledge.retrieval import KnowledgeService
from vehicle_platform.knowledge.tools import KnowledgeTools, RequestType, plan
from vehicle_platform.observability.telemetry import Telemetry

MEASURED_TOOLS = frozenset(
    {
        "get_session_summary",
        "get_session_analytics",
        "get_pull_summary",
        "compare_pulls",
        "get_repeated_pull_analysis",
        "get_vehicle_baseline",
        "get_vehicle_trend",
        "compare_configurations",
        "get_cross_session_analytics",
        "get_telemetry_window",
    }
)


class Orchestrator:
    def __init__(
        self,
        settings: AgentSettings,
        provider: Provider,
        client: EvidenceClient,
        telemetry: Telemetry,
        knowledge: KnowledgeService | None = None,
        *,
        prediction_capability: str | None = None,
    ) -> None:
        self.settings, self.provider, self.client, self.telemetry = (
            settings,
            provider,
            client,
            telemetry,
        )
        self.prediction_capability = prediction_capability
        self.knowledge = knowledge
        graph = StateGraph(GraphState)
        self.grounding_failures = telemetry.metrics.get_meter(
            "vehicle_platform.agents"
        ).create_counter("agent.grounding.failures")
        graph.add_node("context", RunnableLambda(self.context_node))
        graph.add_node("knowledge", RunnableLambda(self.knowledge_node))
        graph.add_node("supervisor", RunnableLambda(self.supervisor_node))
        graph.add_node("model", RunnableLambda(self.model_node))
        graph.add_node("tools", RunnableLambda(self.tools_node))
        graph.add_node("grounding", RunnableLambda(self.grounding_node))
        graph.add_edge(START, "context")
        graph.add_edge("context", "knowledge")
        graph.add_edge("knowledge", "supervisor")
        graph.add_conditional_edges(
            "supervisor", self.after_grounding, {"model": "model", "end": END}
        )
        graph.add_conditional_edges(
            "model", self.after_model, {"tools": "tools", "grounding": "grounding"}
        )
        graph.add_edge("tools", "model")
        graph.add_conditional_edges(
            "grounding", self.after_grounding, {"model": "model", "end": END}
        )
        self.graph = graph.compile()

    async def execute(self, execution: Execution) -> Answer:
        async with asyncio.timeout(self.settings.run_timeout):
            await self.graph.ainvoke(
                {"execution": execution}, {"recursion_limit": self.settings.max_steps * 3 + 4}
            )
        if execution.final is None:
            raise AgentError("invalid_model_response")
        if (
            execution.knowledge_tools
            and execution.knowledge_tools.results
            and not execution.final.knowledge
        ):
            result = execution.knowledge_tools.results[0]
            with self.telemetry.tracer.start_as_current_span(
                "knowledge.grounding_synthesis",
                record_exception=False,
                set_status_on_exception=False,
            ):
                attached = knowledge_report(
                    result,
                    hybrid=True,
                    vehicle_evidence_available=bool(
                        execution.context and execution.context.sessions
                    )
                    and not (
                        execution.run.supervisor
                        and execution.run.supervisor.sufficiency == "UNRELIABLE_DATA"
                    ),
                )
                execution.final.knowledge = attached
                excerpt = render_knowledge(attached)
                execution.final.answer = (execution.final.answer + "\n\n" + excerpt)[:48000]
            if attached.request_type == "VEHICLE_EVIDENCE_INSUFFICIENT":
                execution.final.confidence = "low"
            if result.knowledge_gaps:
                execution.final.missing_evidence = list(
                    dict.fromkeys(["technical_documentation", *execution.final.missing_evidence])
                )[:4]
                execution.final.confidence = "low"
        return execution.final

    async def knowledge_node(self, graph: GraphState) -> dict[str, Any]:
        with self.telemetry.tracer.start_as_current_span(
            "knowledge.intent", record_exception=False, set_status_on_exception=False
        ):
            return await self._knowledge_node(graph)

    async def _knowledge_node(self, graph: GraphState) -> dict[str, Any]:
        from vehicle_platform.agents.schemas import Intent
        from vehicle_platform.agents.specialists.routing import hints_for

        state = graph["execution"]
        if self.knowledge is None or state.context is None:
            return {}
        if hints_for(state.ask.question, state.registry.ordered()).intent == Intent.UNSAFE:
            return {}
        requested = plan(state.ask.question)
        if requested.intent is None:
            return {}
        session_id = state.ask.session_id
        if requested.request_type == RequestType.HYBRID_COMPARISON and session_id is None:
            session_id = (
                UUID(str(state.context.sessions[0]["id"])) if state.context.sessions else None
            )
        scope = knowledge_scope(state.context, session_id)
        state.knowledge_tools = KnowledgeTools(self.knowledge, scope)
        result = await state.knowledge_tools.search_technical_knowledge(
            requested.intent, "supervisor"
        )
        if requested.request_type == RequestType.KNOWLEDGE_FACT:
            attached = knowledge_report(result, hybrid=False)
            state.final = Answer(
                answer=render_knowledge(attached)
                or "A referência técnica aplicável está indisponível.",
                confidence="low" if result.knowledge_gaps else "moderate",
                findings=[],
                evidence=state.registry.ordered(),
                uncertainties=list(result.knowledge_gaps),
                limitations=["Referências documentais não substituem medições do veículo."],
                missing_evidence=["technical_documentation"] if result.knowledge_gaps else [],
                context=state.context,
                knowledge=attached,
            )
        elif session_id is not None:
            await self.call(
                state,
                "get_session_summary",
                {"vehicle_id": str(state.run.vehicle_id), "session_id": str(session_id)},
            )
            if requested.intent.topic == "fuel" and scope.configuration_id is not None:
                await self.call(
                    state,
                    "get_vehicle_baseline",
                    {
                        "vehicle_id": str(state.run.vehicle_id),
                        "configuration_id": str(scope.configuration_id),
                    },
                )
            if requested.intent.topic in {"fuel", "boost"}:
                await self.knowledge_operating_sample(state, session_id)
        return {}

    async def knowledge_operating_sample(self, state: Execution, session_id: UUID) -> None:
        """Preserve a bounded co-recorded sample alongside the full MCP session summary.

        It illustrates recorded operating context, never a normative target or an entire pull.
        Signals without recorded samples remain explicit MCP gaps; no target/load is invented.
        """
        try:
            pulls = await self.call(
                state,
                "list_session_pulls",
                {
                    "vehicle_id": str(state.run.vehicle_id),
                    "session_id": str(session_id),
                    "limit": 1,
                },
            )
            records = pulls.get("data")
            if not isinstance(records, list) or not records:
                return
            start = datetime.fromisoformat(records[0]["started_at"].replace("Z", "+00:00"))
            end = min(
                start + timedelta(milliseconds=200),
                datetime.fromisoformat(records[0]["ended_at"].replace("Z", "+00:00")),
            )
            if end <= start:
                return
            await self.call(
                state,
                "get_telemetry_window",
                {
                    "vehicle_id": str(state.run.vehicle_id),
                    "session_id": str(session_id),
                    "signals": [
                        "fuel.high_pressure",
                        "engine.rpm",
                        "engine.throttle_position",
                        "engine.boost_pressure",
                    ],
                    "window": {"start": start.isoformat(), "end": end.isoformat()},
                    "max_samples": 16,
                },
            )
        except AgentError as exc:
            if exc.category not in RECOVERABLE_TOOL_ERRORS:
                raise

    async def supervisor_node(self, graph: GraphState) -> dict[str, Any]:
        from vehicle_platform.agents.specialists.runtime import Supervisor

        with self.telemetry.tracer.start_as_current_span(
            "agent.supervisor", record_exception=False, set_status_on_exception=False
        ):
            execution = graph["execution"]
            await Supervisor(self, execution).run(
                documentation_only=bool(execution.final and execution.final.knowledge)
            )
        return {}

    async def call(self, state: Execution, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async with state.tool_lock:
            return await self.call_locked(state, name, arguments)

    async def call_locked(
        self, state: Execution, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        names = {t["name"] for t in state.tools}
        if name not in names or str(arguments.get("vehicle_id")) != str(state.run.vehicle_id):
            raise AgentError("tool_policy_violation")
        definition = next(t for t in state.tools if t["name"] == name)
        if len(json.dumps(arguments).encode()) > 8192:
            raise AgentError("tool_argument_budget_exhausted")
        if not Draft202012Validator(definition["parameters"]).is_valid(arguments):
            raise AgentError("invalid_tool_arguments")
        identity_value: dict[str, Any] = {"tool": name, "arguments": arguments}
        if name == "get_prediction_evidence":
            selected_id = arguments.get("evidence_id")
            if (
                not state.ask.include_prediction_evidence
                or selected_id is None
                or str(selected_id) not in {str(item) for item in state.ask.prediction_evidence_ids}
            ):
                raise AgentError("prediction_capability_required")
            if state.prediction_reads >= self.settings.max_prediction_evidence_reads:
                raise AgentError("prediction_evidence_budget_exhausted")
            configured_capability = self.settings.prediction_capability_token
            if (
                not self.settings.prediction_evidence_enabled
                or not self.settings.prediction_service_enabled
                or self.settings.environment not in {"development", "test"}
                or configured_capability is None
                or self.prediction_capability is None
                or not hmac.compare_digest(
                    self.prediction_capability.encode(),
                    configured_capability.get_secret_value().encode(),
                )
                or state.run.vehicle_id not in self.settings.prediction_vehicle_ids
            ):
                self.telemetry.agent_prediction_evidence_authorizations.add(
                    1, {"outcome": "denied"}
                )
                raise AgentError("prediction_capability_revoked")
            identity_value.update(
                {
                    "run_id": str(state.run.id),
                    "capability_scope": "controlled_prediction_evidence_read",
                    "projection_version": "prediction-agent-summary-v1",
                    "verification_policy": "pure-read-time-source-check-v1",
                }
            )
        identity = canonical_hash(identity_value)
        if identity in state.cache:
            return state.cache[identity]
        if len(state.tool_calls) >= self.settings.max_tool_calls:
            raise AgentError("tool_budget_exhausted")
        if name == "get_telemetry_window":
            if state.telemetry_calls >= self.settings.max_telemetry_calls or not state.context:
                raise AgentError("telemetry_budget_exhausted")
            if not any(
                e.source_tool in MEASURED_TOOLS - {name} for e in state.registry.items.values()
            ):
                raise AgentError("progressive_disclosure_required")
            state.telemetry_calls += 1
        if name in {"compare_pulls", "compare_configurations", "get_cross_session_analytics"}:
            if state.comparisons >= self.settings.max_comparisons:
                raise AgentError("comparison_budget_exhausted")
            state.comparisons += 1
        call = ToolCall(
            id=uuid4(),
            run_id=state.run.id,
            tool_name=name,
            started_at=datetime.now(UTC),
            argument_hash=identity,
        )
        state.tool_calls.append(call)
        if name == "get_prediction_evidence":
            state.prediction_reads += 1
        await state.audit(call)
        await state.emit("tool_started", {"tool_call_id": str(call.id), "tool_name": name})
        started = perf_counter()
        prediction_dimensions = {
            "result_type": "unknown",
            "horizon": "unknown",
            "source_role": "unknown",
            "integrity": "unknown",
            "completeness": "unknown",
            "status": "unknown",
        }
        try:
            with self.telemetry.tracer.start_as_current_span(
                "agent.mcp_tool",
                record_exception=False,
                set_status_on_exception=False,
                attributes={"tool": name},
            ):
                async with asyncio.timeout(self.settings.tool_timeout):
                    result = await self.client.call(name, arguments)
            if len(result.model_dump_json().encode()) > self.settings.max_result_bytes:
                raise AgentError("tool_result_budget_exhausted")
            if name == "get_prediction_evidence":
                from vehicle_platform.mcp.schemas import PredictionEvidenceMCPProjection

                if not isinstance(result.data, dict):
                    raise AgentError("invalid_tool_result")
                projection = PredictionEvidenceMCPProjection.model_validate_json(
                    json.dumps(result.data)
                )
                prediction_dimensions.update(
                    {
                        "result_type": projection.result_type.value,
                        "horizon": projection.horizon.value,
                        "source_role": projection.source_role.value,
                        "integrity": projection.integrity.value,
                        "completeness": projection.completeness.value,
                        "status": projection.status,
                    }
                )
                expected = prediction_request_intent(state.ask.question)
                if projection.evidence_id != UUID(str(arguments["evidence_id"])) or (
                    expected is not None
                    and projection.horizon.value
                    != ("NEXT_PULL" if expected.value == "prediction" else "AFTER_PULL_OFFLINE")
                ):
                    raise AgentError("prediction_horizon_mismatch")
            if name == "get_prediction_evidence":
                with self.telemetry.tracer.start_as_current_span(
                    "agent.prediction_evidence.projection",
                    record_exception=False,
                    set_status_on_exception=False,
                    attributes={
                        "projection_version": "prediction-agent-summary-v1",
                        "result_type": prediction_dimensions["result_type"],
                        "horizon": prediction_dimensions["horizon"],
                    },
                ):
                    evidence = state.registry.add(name, call.id, result)
            else:
                evidence = state.registry.add(name, call.id, result)
            call.evidence_ids = [e.id for e in evidence]
            call.returned, call.truncated, call.mcp_request_id = (
                result.returned,
                result.truncated,
                result.mcp_request_id,
            )
            call.status = "completed"
            for item in evidence:
                await state.emit(
                    "evidence_added", {"evidence_id": str(item.id), "source_tool": name}
                )
            dumped = result.model_dump(mode="json")
            state.cache[identity] = dumped
            return dumped
        except asyncio.CancelledError:
            call.status, call.error_category = "failed", "cancelled"
            raise
        except AgentError as exc:
            call.status, call.error_category = "failed", exc.category
            raise
        except TimeoutError:
            call.status, call.error_category = "failed", "tool_timeout"
            raise AgentError("tool_timeout") from None
        except Exception:
            call.status, call.error_category = "failed", "mcp_unavailable"
            raise AgentError("mcp_unavailable") from None
        finally:
            call.completed_at = datetime.now(UTC)
            call.duration_seconds = perf_counter() - started
            if name == "get_prediction_evidence":
                if call.status != "completed":
                    self.telemetry.agent_prediction_evidence_authorizations.add(
                        1, {"outcome": "denied"}
                    )
                outcome = "success" if call.status == "completed" else "error"
                self.telemetry.agent_prediction_evidence_operations.add(
                    1, {"outcome": outcome, **prediction_dimensions}
                )
                self.telemetry.agent_prediction_evidence_duration.record(
                    call.duration_seconds, {"outcome": outcome, **prediction_dimensions}
                )
            await state.audit(call)
            await state.emit("tool_completed", call.model_dump(mode="json"))

    async def context_node(self, graph: GraphState) -> dict[str, Any]:
        state = graph["execution"]
        with self.telemetry.tracer.start_as_current_span(
            "agent.mcp_discovery",
            record_exception=False,
            set_status_on_exception=False,
            attributes={
                "capability": "prediction" if state.ask.include_prediction_evidence else "read"
            },
        ):
            state.tools = await self.client.discover()
        vehicle_args = {"vehicle_id": str(state.run.vehicle_id)}
        with self.telemetry.tracer.start_as_current_span(
            "agent.context", record_exception=False, set_status_on_exception=False
        ):
            vehicle = (await self.call(state, "get_vehicle", vehicle_args))["data"]
            configs = (
                await self.call(state, "list_vehicle_configurations", vehicle_args | {"limit": 20})
            )["data"]
            mods = (
                await self.call(state, "list_vehicle_modifications", vehicle_args | {"limit": 20})
            )["data"]
            selected_pull: dict[str, Any] | None = None
            selected_session_id = state.ask.session_id
            if state.ask.pull_id:
                selected_pull = (
                    await self.call(
                        state,
                        "get_pull",
                        vehicle_args | {"pull_id": str(state.ask.pull_id)},
                    )
                )["data"]
                pull_session_id = UUID(str(selected_pull["session_id"]))
                if selected_session_id and selected_session_id != pull_session_id:
                    raise AgentError("incompatible_context")
                selected_session_id = pull_session_id
            if selected_session_id:
                sessions = [
                    (
                        await self.call(
                            state,
                            "get_session",
                            vehicle_args | {"session_id": str(selected_session_id)},
                        )
                    )["data"]
                ]
            else:
                sessions = (await self.call(state, "list_sessions", vehicle_args | {"limit": 10}))[
                    "data"
                ]
            state.context = resolve_context(state.run.vehicle_id, vehicle, configs, mods, sessions)
            for result in state.cache.values():
                if result.get("truncated"):
                    state.context.warnings.append("context_history_truncated")
            if sessions:
                await self.capabilities(state, UUID(sessions[0]["id"]))
            if state.ask.include_prediction_evidence:
                for evidence_id in state.ask.prediction_evidence_ids:
                    try:
                        await self.call(
                            state,
                            "get_prediction_evidence",
                            vehicle_args
                            | {
                                "evidence_id": str(evidence_id),
                                "session_id": str(selected_session_id)
                                if selected_session_id
                                else None,
                                "pull_id": str(state.ask.pull_id) if state.ask.pull_id else None,
                            },
                        )
                    except AgentError as exc:
                        state.prediction_error = exc.category
                        break
        await state.emit("context_resolved", state.context.model_dump(mode="json"))
        return {}

    async def capabilities(self, state: Execution, session_id: UUID) -> None:
        if state.context is None:
            raise AgentError("context_missing")
        key = str(session_id)
        args = {"vehicle_id": str(state.run.vehicle_id), "session_id": key}
        if key not in {str(s["id"]) for s in state.context.sessions}:
            if len(state.context.sessions) >= 10:
                raise AgentError("context_budget_exhausted")
            session = (await self.call(state, "get_session", args))["data"]
            state.context = resolve_context(
                state.run.vehicle_id,
                state.context.vehicle,
                state.context.configurations,
                state.context.modifications,
                state.context.sessions + [session],
                state.context.as_of,
            )
        if key not in state.context.capabilities:
            result = await self.call(state, "get_session_capabilities", args)
            state.context.capabilities[key] = result["data"]

    async def model_node(self, graph: GraphState) -> dict[str, Any]:
        state = graph["execution"]
        if state.steps >= self.settings.max_steps or state.context is None:
            raise AgentError("step_budget_exhausted")
        state.steps += 1
        state.synthesis_turns += 1
        if state.run.supervisor:
            state.run.supervisor.model_turn_count = state.steps
        request = ModelInput(
            question=redact_data(state.ask.question, self.settings),
            tools=[tool for tool in state.tools if tool["name"] != "get_prediction_evidence"],
            context=redact_data(state.context.model_dump(mode="json"), self.settings),
            evidence=redact_data(
                [e.model_dump(mode="json") for e in state.registry.ordered()], self.settings
            ),
            messages=redact_data(state.messages, self.settings),
            correction=state.correction,
            knowledge=[
                e.model_dump(mode="json")
                for e in state.knowledge_tools.for_specialist("supervisor")
            ]
            if state.knowledge_tools
            else [],
            supervisor=(
                state.run.supervisor.model_dump(mode="json") if state.run.supervisor else None
            ),
        )
        if len(json.dumps(request.__dict__, default=str).encode()) > self.settings.max_input_bytes:
            raise AgentError("model_input_budget_exhausted")
        with self.telemetry.tracer.start_as_current_span(
            "agent.model_turn", record_exception=False, set_status_on_exception=False
        ):
            while True:
                try:
                    async with asyncio.timeout(self.settings.model_timeout):
                        state.turn = await self.provider.turn(request)
                    break
                except AgentError as exc:
                    if (
                        exc.category not in {"provider_rate_limit", "provider_unavailable"}
                        or state.provider_retries >= self.settings.max_provider_retries
                    ):
                        raise
                    state.provider_retries += 1
                    if state.run.supervisor:
                        state.run.supervisor.retry_count = state.provider_retries
                except TimeoutError:
                    raise AgentError("provider_timeout") from None
        if state.turn is None:
            raise AgentError("invalid_model_response")
        if len(state.turn.tool_calls) > 4 or (state.turn.tool_calls and state.turn.draft):
            raise AgentError("invalid_model_response")
        state.run.usage = accumulate(state.run.usage, state.turn.usage, state.steps == 1)
        if state.run.supervisor:
            state.run.supervisor.synthesis_usage = accumulate(
                state.run.supervisor.synthesis_usage,
                state.turn.usage,
                state.synthesis_turns == 1,
            )
        return {}

    @staticmethod
    def after_model(graph: GraphState) -> str:
        turn = graph["execution"].turn
        return "tools" if turn and turn.tool_calls else "grounding"

    async def tools_node(self, graph: GraphState) -> dict[str, Any]:
        state = graph["execution"]
        if not state.turn:
            raise AgentError("invalid_model_response")
        for requested in state.turn.tool_calls:
            if requested.name == "get_prediction_evidence":
                raise AgentError("tool_policy_violation")
            if requested.name not in {t["name"] for t in state.tools} or str(
                requested.arguments.get("vehicle_id")
            ) != str(state.run.vehicle_id):
                raise AgentError("tool_policy_violation")
            definition = next(t for t in state.tools if t["name"] == requested.name)
            if len(json.dumps(requested.arguments).encode()) > 8192 or not Draft202012Validator(
                definition["parameters"]
            ).is_valid(requested.arguments):
                raise AgentError("invalid_tool_arguments")
            if requested.name in MEASURED_TOOLS:
                sessions = set()
                if requested.arguments.get("session_id"):
                    sessions.add(UUID(str(requested.arguments["session_id"])))
                for key in ("session_ids",):
                    sessions.update(UUID(str(s)) for s in requested.arguments.get(key, []))
                pull_ids = list(requested.arguments.get("pull_ids", []))
                pull_ids += list(requested.arguments.get("before_pull_ids", [])) + list(
                    requested.arguments.get("after_pull_ids", [])
                )
                if requested.arguments.get("pull_id"):
                    pull_ids.append(requested.arguments["pull_id"])
                for pull in pull_ids:
                    known = next(
                        (
                            e
                            for e in state.registry.items.values()
                            if e.source_tool in {"get_pull", "list_session_pulls"}
                            and str(e.entity_id) == str(pull)
                            and e.session_id
                        ),
                        None,
                    )
                    if known and known.session_id:
                        sessions.add(known.session_id)
                        continue
                    data = (
                        await self.call(
                            state,
                            "get_pull",
                            {"vehicle_id": str(state.run.vehicle_id), "pull_id": str(pull)},
                        )
                    )["data"]
                    sessions.add(UUID(str(data["session_id"])))
                for session_id in sessions:
                    await self.capabilities(state, session_id)
            try:
                result = await self.call(state, requested.name, requested.arguments)
                # Provide normalized evidence only, never a raw telemetry blob or provider object.
                output = {
                    "status": "completed",
                    "mcp_request_id": result.get("mcp_request_id"),
                    "evidence_ids": [
                        str(e.id)
                        for e in state.registry.items.values()
                        if e.source_tool == requested.name
                    ],
                }
            except AgentError as exc:
                if exc.category not in RECOVERABLE_TOOL_ERRORS:
                    raise
                output = {"status": "failed", "error_category": exc.category}
            state.messages.extend(
                [
                    {
                        "type": "function_call",
                        "call_id": requested.call_id,
                        "name": requested.name,
                        "arguments": json.dumps(requested.arguments),
                    },
                    {
                        "type": "function_call_output",
                        "call_id": requested.call_id,
                        "output": json.dumps(output),
                    },
                ]
            )
        return {}

    async def grounding_node(self, graph: GraphState) -> dict[str, Any]:
        state = graph["execution"]
        if not state.turn or not state.turn.draft or not state.context:
            raise AgentError("invalid_model_response")
        if state.turn.draft.missing_evidence:
            from vehicle_platform.agents.schemas import Claim, Classification

            proposed = state.turn.draft.model_copy(deep=True)
            if not any(
                claim.classification is Classification.INSUFFICIENT_EVIDENCE
                for claim in proposed.claims
            ):
                proposed.claims = proposed.claims[:15] + [
                    Claim(
                        classification=Classification.INSUFFICIENT_EVIDENCE,
                        template="insufficient_evidence",
                        bindings=[],
                        evidence_ids=[],
                    )
                ]
            proposed.confidence = "low"
            state.turn.draft = proposed
        report = state.run.supervisor
        if (
            report
            and (report.routing.data_quality_gate or report.routing.selected)
            and state.turn.draft.missing_evidence
            and not report.investigation_recommended
        ):
            from vehicle_platform.agents.schemas import Sufficiency
            from vehicle_platform.agents.specialists.runtime import Supervisor

            report.sufficiency = Sufficiency.PARTIALLY_SUFFICIENT
            report.investigation_recommended = True
            await Supervisor(self, state).evaluate()
        if report and report.investigation_recommended:
            from vehicle_platform.agents.schemas import Claim, Classification

            proposed = state.turn.draft.model_copy(deep=True)
            if not any(
                c.classification == Classification.INSUFFICIENT_EVIDENCE for c in proposed.claims
            ):
                proposed.claims = proposed.claims[:15] + [
                    Claim(
                        classification=Classification.INSUFFICIENT_EVIDENCE,
                        template="insufficient_evidence",
                        bindings=[],
                        evidence_ids=[],
                    )
                ]
            proposed.missing_evidence = list(
                dict.fromkeys(
                    [
                        *proposed.missing_evidence,
                        *(gap for r in report.specialists for gap in r.evidence_gaps),
                        "signal_or_measurement",
                    ]
                )
            )[:4]
            proposed.confidence = "low"
            state.turn.draft = proposed
        with self.telemetry.tracer.start_as_current_span(
            "agent.grounding", record_exception=False, set_status_on_exception=False
        ):
            try:
                state.final = validate(state.turn.draft, state.registry, state.context)
                if state.ask.include_prediction_evidence:
                    self.telemetry.agent_prediction_evidence_grounding.add(
                        1, {"outcome": "accepted"}
                    )
                if report and "capture_requires_approval" in report.routing.hints:
                    state.final.limitations = list(
                        dict.fromkeys([CAPTURE_APPROVAL_LIMITATION, *state.final.limitations])
                    )[:32]
                if report and not report.routing.data_quality_gate and not report.routing.selected:
                    from vehicle_platform.agents.schemas import Sufficiency

                    report.sufficiency = (
                        Sufficiency.INSUFFICIENT
                        if state.final.missing_evidence
                        else Sufficiency.SUFFICIENT
                    )
                    report.investigation_recommended = bool(state.final.missing_evidence)
                if state.run.supervisor:
                    state.final.limitations = list(
                        dict.fromkeys(
                            [
                                *state.final.limitations,
                                *(
                                    w
                                    for r in state.run.supervisor.specialists
                                    for w in r.data_quality_warnings
                                ),
                            ]
                        )
                    )[:32]
            except AgentError as exc:
                if state.ask.include_prediction_evidence:
                    self.telemetry.agent_prediction_evidence_grounding.add(
                        1, {"outcome": "rejected"}
                    )
                self.grounding_failures.add(1, {"category": exc.category})
                self.telemetry.log(
                    "agent.grounding.rejected", str(state.run.id), error_code=exc.category
                )
                if state.corrections >= self.settings.max_grounding_retries:
                    raise AgentError("grounding_failed") from None
                state.corrections += 1
                state.correction = exc.category
        return {}

    @staticmethod
    def after_grounding(graph: GraphState) -> str:
        return "end" if graph["execution"].final else "model"


def accumulate(total: Usage, added: Usage, first: bool) -> Usage:
    values: dict[str, int | None] = {}
    for name in ("input_tokens", "output_tokens", "cached_input_tokens", "total_tokens"):
        previous, current = getattr(total, name), getattr(added, name)
        values[name] = (
            current
            if first
            else previous + current
            if previous is not None and current is not None
            else None
        )
    return Usage(
        input_tokens=values["input_tokens"],
        output_tokens=values["output_tokens"],
        cached_input_tokens=values["cached_input_tokens"],
        total_tokens=values["total_tokens"],
    )
