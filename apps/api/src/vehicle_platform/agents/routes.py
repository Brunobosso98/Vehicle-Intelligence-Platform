from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from starlette.responses import StreamingResponse

from vehicle_platform.agents.schemas import AgentRun, Ask, RunAudit, StreamEvent
from vehicle_platform.agents.service import AgentService
from vehicle_platform.api.contracts import ErrorResponse


def agent_router(service: AgentService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/vehicles/{vehicle_id}/agent-runs", tags=["agent"])

    @router.post(
        "",
        response_model=AgentRun,
        status_code=202,
        responses={408: {"model": ErrorResponse}, 413: {"model": ErrorResponse}},
    )
    async def ask(vehicle_id: UUID, body: Ask) -> AgentRun:
        return await service.start(vehicle_id, body)

    @router.get("", response_model=list[AgentRun])
    async def recent(
        vehicle_id: UUID, limit: Annotated[int, Query(ge=1, le=20)] = 10
    ) -> list[AgentRun]:
        return await service.repository.recent(vehicle_id, limit)

    @router.get("/{run_id}", response_model=AgentRun)
    async def get(vehicle_id: UUID, run_id: UUID) -> AgentRun:
        return await service.repository.get(vehicle_id, run_id)

    @router.get("/{run_id}/audit", response_model=RunAudit)
    async def audit(vehicle_id: UUID, run_id: UUID) -> RunAudit:
        run = await service.repository.get(vehicle_id, run_id)
        return RunAudit(
            run_id=run_id,
            tool_calls=await service.repository.calls(vehicle_id, run_id),
            evidence=run.evidence,
        )

    @router.get("/{run_id}/events", response_model=list[StreamEvent])
    async def events(
        vehicle_id: UUID,
        run_id: UUID,
        after: Annotated[int, Query(ge=0, le=400)] = 0,
    ) -> list[StreamEvent]:
        return await service.repository.events(vehicle_id, run_id, after)

    @router.get("/{run_id}/stream")
    async def stream(
        vehicle_id: UUID, run_id: UUID, after: Annotated[int, Query(ge=0, le=400)] = 0
    ) -> StreamingResponse:
        await service.repository.get(vehicle_id, run_id)

        async def events() -> AsyncIterator[str]:
            async for event in service.stream(vehicle_id, run_id, after):
                yield (
                    f"id: {event.sequence}\nevent: {event.type}\n"
                    f"data: {event.model_dump_json()}\n\n"
                )

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @router.post("/{run_id}/cancel", response_model=AgentRun)
    async def cancel(vehicle_id: UUID, run_id: UUID) -> AgentRun:
        return await service.cancel(vehicle_id, run_id)

    return router
