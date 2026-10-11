import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, cast
from uuid import UUID, uuid4

from opentelemetry.trace import StatusCode
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from vehicle_platform.agents.config import AgentSettings, redact_data
from vehicle_platform.agents.evidence import EvidenceRegistry
from vehicle_platform.agents.instrumentation import AgentInstrumentation
from vehicle_platform.agents.mcp_client import EvidenceClient, connect
from vehicle_platform.agents.orchestration import Orchestrator
from vehicle_platform.agents.provider import AgentError, Provider
from vehicle_platform.agents.repository import AgentRepository
from vehicle_platform.agents.schemas import AgentRun, Ask, Evidence, StreamEvent, ToolCall
from vehicle_platform.agents.state import Execution
from vehicle_platform.observability.telemetry import Telemetry

ClientFactory = Callable[[], AbstractAsyncContextManager[EvidenceClient]]
ProviderFactory = Callable[[], Provider]


def failure_category(exc: BaseException) -> str:
    """MCP task groups can wrap application errors when their transport exits."""
    if isinstance(exc, BaseExceptionGroup):
        categories = {failure_category(child) for child in exc.exceptions}
        return categories.pop() if len(categories) == 1 else "dependency_unavailable"
    if isinstance(exc, AgentError):
        return exc.category
    if isinstance(exc, TimeoutError):
        return "run_timeout"
    if isinstance(exc, SQLAlchemyError):
        return "database_unavailable"
    return "dependency_unavailable"


class AgentService:
    def __init__(
        self,
        repository: AgentRepository,
        settings: AgentSettings,
        telemetry: Telemetry,
        provider_factory: ProviderFactory,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.repository, self.settings, self.telemetry = repository, settings, telemetry
        self.provider_factory = provider_factory
        self.client_factory = client_factory or (lambda: connect(settings))
        self.signals = AgentInstrumentation(telemetry)
        self.tasks: dict[UUID, asyncio.Task[None]] = {}
        self.active = 0
        self.streams = 0

    async def start(
        self,
        vehicle_id: UUID,
        ask: Ask,
        *,
        run_id: UUID | None = None,
        follow_up_context: str | None = None,
    ) -> AgentRun:
        if not self.settings.enabled:
            raise AgentError("agent_disabled")
        if self.active >= self.settings.max_concurrent_runs:
            raise AgentError("concurrency_exhausted")
        # Reserve before the first await, including run creation and context ownership checks.
        self.active += 1
        self.signals.active.add(1)
        try:
            prior: AgentRun | None = None
            if ask.previous_run_id:
                prior = await self.repository.get(vehicle_id, ask.previous_run_id)
                if prior.status != "completed":
                    raise AgentError("invalid_follow_up")
            if run_id is not None:
                try:
                    existing = await self.repository.get(vehicle_id, run_id)
                except AgentError as exc:
                    if exc.category != "run_not_found":
                        raise
                else:
                    if existing.status == "running" and run_id not in self.tasks:
                        self.tasks[run_id] = asyncio.create_task(
                            self.execute(existing, ask, prior, follow_up_context)
                        )
                        return existing
                    self.active -= 1
                    self.signals.active.add(-1)
                    return existing
            run = AgentRun(
                id=run_id or uuid4(),
                vehicle_id=vehicle_id,
                user_question=self.redact(ask.question),
                status="running",
                provider=self.settings.provider,
                model=self.redact(self.settings.model or "scripted-v1"),
                agent_version=self.settings.agent_version,
                prompt_version=self.settings.prompt_version,
                started_at=datetime.now(UTC),
            )
            await self.repository.create(run)
            self.tasks[run.id] = asyncio.create_task(
                self.execute(run, ask, prior, follow_up_context)
            )
            return run
        except BaseException as exc:
            self.active -= 1
            self.signals.active.add(-1)
            if isinstance(exc, IntegrityError) and getattr(exc.orig, "sqlstate", None) == "23503":
                raise AgentError("vehicle_not_found") from None
            if isinstance(exc, (SQLAlchemyError, OSError, TimeoutError)):
                raise AgentError("database_unavailable") from None
            raise

    def redact(self, value: str) -> str:
        return cast(str, redact_data(value, self.settings))

    async def execute(
        self,
        run: AgentRun,
        ask: Ask,
        prior: AgentRun | None,
        follow_up_context: str | None = None,
    ) -> None:
        sequence = 0
        started = perf_counter()
        provider: Provider | None = None

        async def emit(kind: str, data: dict[str, Any]) -> None:
            nonlocal sequence
            sequence += 1
            sanitized = cast(dict[str, Any], redact_data(data, self.settings))
            event = StreamEvent.model_validate(
                {"sequence": sequence, "run_id": run.id, "type": kind, "data": sanitized}
            )
            await self.repository.event(event)

        async def audit(call: ToolCall) -> None:
            await self.repository.audit(call)
            if call.status != "running":
                run.evidence = [
                    Evidence.model_validate(redact_data(e.model_dump(mode="json"), self.settings))
                    for e in state.registry.items.values()
                ]
                await self.repository.save(run)
                self.signals.tools.add(1, {"tool": call.tool_name, "status": call.status})
                self.signals.tool_duration.record(
                    call.duration_seconds or 0, {"tool": call.tool_name}
                )
                if call.error_category:
                    self.signals.tool_errors.add(
                        1, {"tool": call.tool_name, "category": call.error_category}
                    )

        state = Execution(
            run=run,
            ask=ask,
            registry=EvidenceRegistry(run.id, run.vehicle_id, self.settings.max_evidence),
            emit=emit,
            audit=audit,
        )
        if prior:
            state.messages.append(
                {
                    "role": "user",
                    "content": "Bounded previous question (facts must be re-read in this run): "
                    + prior.user_question[:2000],
                }
            )
        if follow_up_context:
            state.messages.append(
                {
                    "role": "developer",
                    "content": "Investigation follow-up context (bounded public IDs/categories): "
                    + follow_up_context[:1000],
                }
            )
        with self.telemetry.tracer.start_as_current_span(
            "agent.run", record_exception=False, set_status_on_exception=False
        ) as span:
            run.trace_id = f"{span.get_span_context().trace_id:032x}"
            try:
                async with asyncio.timeout(self.settings.run_timeout):
                    await emit("run_started", {"vehicle_id": str(run.vehicle_id)})
                    provider = self.provider_factory()
                    async with self.client_factory() as client:
                        run.result = await Orchestrator(
                            self.settings, provider, client, self.telemetry
                        ).execute(state)
                    # Publish validated public prose in bounded chunks.
                    run.result = type(run.result).model_validate(
                        redact_data(run.result.model_dump(mode="json"), self.settings)
                    )
                    if len(run.result.model_dump_json().encode()) > self.settings.max_input_bytes:
                        raise AgentError("answer_budget_exhausted")
                    for cursor in range(0, len(run.result.answer), 256):
                        await emit(
                            "answer_chunk", {"text": run.result.answer[cursor : cursor + 256]}
                        )
                    run.status = "completed"
            except asyncio.CancelledError:
                run.status, run.error_category = "cancelled", "cancelled"
            except AgentError as exc:
                run.status, run.error_category = "failed", exc.category
            except TimeoutError:
                run.status, run.error_category = "failed", "run_timeout"
            except SQLAlchemyError:
                run.status, run.error_category = "failed", "database_unavailable"
            except Exception as exc:
                run.status, run.error_category = "failed", failure_category(exc)
            finally:
                run.completed_at, run.duration_seconds = datetime.now(UTC), perf_counter() - started
                run.tool_call_count = len(state.tool_calls)
                run.evidence = [
                    Evidence.model_validate(redact_data(e.model_dump(mode="json"), self.settings))
                    for e in state.registry.items.values()
                ]
                if run.status != "completed":
                    run.result = None
                    span.set_status(StatusCode.ERROR)
                    span.set_attribute("agent.error_category", run.error_category or "unknown")
                try:
                    terminal = (
                        "run_completed"
                        if run.status == "completed"
                        else "run_cancelled"
                        if run.status == "cancelled"
                        else "run_failed"
                    )
                    sequence += 1
                    event = StreamEvent.model_validate(
                        {
                            "run_id": run.id,
                            "sequence": sequence,
                            "type": terminal,
                            "data": {"status": run.status, "error_category": run.error_category},
                        }
                    )
                    await self.repository.finish(run, event)
                except (AgentError, SQLAlchemyError, OSError, TimeoutError):
                    # A dependency recovery sweep reconciles stale runs.
                    run.status, run.result = "failed", None
                    run.error_category = "database_unavailable"
                    span.set_status(StatusCode.ERROR)
                    span.set_attribute("agent.error_category", run.error_category)
                finally:
                    self.signals.completed(run)
                    self.active -= 1
                    self.signals.active.add(-1)
                    self.tasks.pop(run.id, None)
                    if provider:
                        try:
                            async with asyncio.timeout(2):
                                await provider.close()
                        except Exception:
                            self.telemetry.log(
                                "agent.provider.close_failed",
                                str(run.id),
                                error_code="provider_unavailable",
                            )

    async def stream(
        self, vehicle_id: UUID, run_id: UUID, after: int = 0
    ) -> AsyncIterator[StreamEvent]:
        if self.streams >= 10:
            raise AgentError("stream_concurrency_exhausted")
        self.streams += 1
        try:
            async with asyncio.timeout(self.settings.run_timeout + 5):
                while True:
                    events = await self.repository.events(vehicle_id, run_id, after)
                    for event in events:
                        yield event
                        after = event.sequence
                    run = await self.repository.get(vehicle_id, run_id)
                    if run.status != "running":
                        # Final status may be committed immediately before the terminal event.
                        for event in await self.repository.events(vehicle_id, run_id, after):
                            yield event
                        return
                    await asyncio.sleep(0.1)
        finally:
            self.streams -= 1

    async def cancel(self, vehicle_id: UUID, run_id: UUID) -> AgentRun:
        await self.repository.get(vehicle_id, run_id)
        task = self.tasks.get(run_id)
        if task:
            # Let a freshly scheduled task enter its cleanup scope before cancelling it.
            await asyncio.sleep(0)
            task.cancel()
            await task
        return await self.repository.get(vehicle_id, run_id)

    async def close(self) -> None:
        tasks = list(self.tasks.values())
        await asyncio.sleep(0)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
