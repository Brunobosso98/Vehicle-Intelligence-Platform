import asyncio
import json
from datetime import UTC, datetime
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
from vehicle_platform.agents.mcp_client import EvidenceClient
from vehicle_platform.agents.provider import AgentError, ModelInput, Provider
from vehicle_platform.agents.schemas import Answer, ToolCall, Usage
from vehicle_platform.agents.state import Execution, GraphState
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
    ) -> None:
        self.settings, self.provider, self.client, self.telemetry = (
            settings,
            provider,
            client,
            telemetry,
        )
        graph = StateGraph(GraphState)
        self.grounding_failures = telemetry.metrics.get_meter(
            "vehicle_platform.agents"
        ).create_counter("agent.grounding.failures")
        graph.add_node("context", RunnableLambda(self.context_node))
        graph.add_node("model", RunnableLambda(self.model_node))
        graph.add_node("tools", RunnableLambda(self.tools_node))
        graph.add_node("grounding", RunnableLambda(self.grounding_node))
        graph.add_edge(START, "context")
        graph.add_edge("context", "model")
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
        return execution.final

    async def call(self, state: Execution, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        names = {t["name"] for t in state.tools}
        if name not in names or str(arguments.get("vehicle_id")) != str(state.run.vehicle_id):
            raise AgentError("tool_policy_violation")
        definition = next(t for t in state.tools if t["name"] == name)
        if len(json.dumps(arguments).encode()) > 8192:
            raise AgentError("tool_argument_budget_exhausted")
        if not Draft202012Validator(definition["parameters"]).is_valid(arguments):
            raise AgentError("invalid_tool_arguments")
        identity = canonical_hash({"tool": name, "arguments": arguments})
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
        await state.audit(call)
        await state.emit("tool_started", {"tool_call_id": str(call.id), "tool_name": name})
        started = perf_counter()
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
            await state.audit(call)
            await state.emit("tool_completed", call.model_dump(mode="json"))

    async def context_node(self, graph: GraphState) -> dict[str, Any]:
        state = graph["execution"]
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
            if state.ask.session_id:
                sessions = [
                    (
                        await self.call(
                            state,
                            "get_session",
                            vehicle_args | {"session_id": str(state.ask.session_id)},
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
        request = ModelInput(
            question=redact_data(state.ask.question, self.settings),
            tools=state.tools,
            context=redact_data(state.context.model_dump(mode="json"), self.settings),
            evidence=redact_data(
                [e.model_dump(mode="json") for e in state.registry.items.values()], self.settings
            ),
            messages=redact_data(state.messages, self.settings),
            correction=state.correction,
        )
        if len(json.dumps(request.__dict__).encode()) > self.settings.max_input_bytes:
            raise AgentError("model_input_budget_exhausted")
        with self.telemetry.tracer.start_as_current_span(
            "agent.model_turn", record_exception=False, set_status_on_exception=False
        ):
            for attempt in range(self.settings.max_provider_retries + 1):
                try:
                    async with asyncio.timeout(self.settings.model_timeout):
                        state.turn = await self.provider.turn(request)
                    break
                except AgentError as exc:
                    if (
                        exc.category not in {"provider_rate_limit", "provider_unavailable"}
                        or attempt == self.settings.max_provider_retries
                    ):
                        raise
                except TimeoutError:
                    raise AgentError("provider_timeout") from None
        if state.turn is None:
            raise AgentError("invalid_model_response")
        if len(state.turn.tool_calls) > 4 or (state.turn.tool_calls and state.turn.draft):
            raise AgentError("invalid_model_response")
        state.run.usage = accumulate(state.run.usage, state.turn.usage, state.steps == 1)
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
                if exc.category != "mcp_tool_error":
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
        with self.telemetry.tracer.start_as_current_span(
            "agent.grounding", record_exception=False, set_status_on_exception=False
        ):
            try:
                state.final = validate(state.turn.draft, state.registry, state.context)
            except AgentError as exc:
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
