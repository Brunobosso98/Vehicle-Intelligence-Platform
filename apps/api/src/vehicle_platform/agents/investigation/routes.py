"""Operator-authorized public investigation API and replayable SSE."""

import asyncio
import secrets
from collections.abc import AsyncIterator
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import Field
from starlette.responses import StreamingResponse

from vehicle_platform.agents.investigation.domain import (
    TERMINAL,
    CapabilitySnapshot,
    InvestigationEvent,
    InvestigationPlan,
)
from vehicle_platform.agents.investigation.service import InvestigationService
from vehicle_platform.agents.schemas import StrictModel
from vehicle_platform.api.domain_contracts import PreflightRequest


class CreateInvestigation(StrictModel):
    agent_run_id: UUID
    adapter: Literal["synthetic", "replay", "obd"]
    source_id: str = Field(min_length=1, max_length=80)


class ApprovalRequest(StrictModel):
    version: int = Field(ge=1, le=100)
    recipe_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class VersionRequest(StrictModel):
    version: int = Field(ge=1, le=100)


class LinkSessionRequest(VersionRequest):
    session_id: UUID


class RegisterSourcePreflight(StrictModel):
    configuration_id: UUID
    adapter: Literal["obd", "replay"]
    source_id: str = Field(min_length=1, max_length=80)
    capability_snapshot: PreflightRequest


def investigation_router(service: InvestigationService) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/vehicles/{vehicle_id}/investigations", tags=["investigation"]
    )
    streams = 0

    def operator(x_investigation_token: Annotated[str | None, Header()] = None) -> str:
        expected = service.agents.settings.investigation_token
        if expected is None or not expected.get_secret_value():
            raise HTTPException(503, "investigation operator token is not configured")
        if not x_investigation_token or not secrets.compare_digest(
            x_investigation_token, expected.get_secret_value()
        ):
            raise HTTPException(401, "investigation operator credential required")
        return "operator"

    @router.post("", response_model=InvestigationPlan, status_code=201)
    async def create(
        vehicle_id: UUID,
        body: CreateInvestigation,
        actor: Annotated[str, Depends(operator)],
    ) -> InvestigationPlan:
        return await service.create(vehicle_id, body.agent_run_id, body.adapter, body.source_id)

    @router.post("/source-preflight", response_model=CapabilitySnapshot)
    async def source_preflight(
        vehicle_id: UUID,
        body: RegisterSourcePreflight,
        actor: Annotated[str, Depends(operator)],
    ) -> CapabilitySnapshot:
        return await service.register_source(
            vehicle_id,
            body.configuration_id,
            body.adapter,
            body.source_id,
            body.capability_snapshot,
        )

    @router.get("", response_model=list[InvestigationPlan])
    async def recent(
        vehicle_id: UUID,
        actor: Annotated[str, Depends(operator)],
        limit: Annotated[int, Query(ge=1, le=20)] = 10,
    ) -> list[InvestigationPlan]:
        return await service.repository.recent(vehicle_id, limit)

    @router.get("/{investigation_id}", response_model=InvestigationPlan)
    async def get(
        vehicle_id: UUID,
        investigation_id: UUID,
        actor: Annotated[str, Depends(operator)],
    ) -> InvestigationPlan:
        return await service.get(vehicle_id, investigation_id)

    @router.get("/{investigation_id}/events", response_model=list[InvestigationEvent])
    async def events(
        vehicle_id: UUID,
        investigation_id: UUID,
        actor: Annotated[str, Depends(operator)],
        after: Annotated[int, Query(ge=0, le=100)] = 0,
    ) -> list[InvestigationEvent]:
        return await service.repository.events(vehicle_id, investigation_id, after)

    @router.get("/{investigation_id}/stream")
    async def stream(
        vehicle_id: UUID,
        investigation_id: UUID,
        actor: Annotated[str, Depends(operator)],
        after: Annotated[int, Query(ge=0, le=100)] = 0,
    ) -> StreamingResponse:
        nonlocal streams
        await service.repository.get(vehicle_id, investigation_id)
        if streams >= 10:
            raise HTTPException(429, "investigation stream budget exhausted")
        streams += 1

        async def replay() -> AsyncIterator[str]:
            nonlocal streams
            cursor = after
            try:
                async with asyncio.timeout(45):
                    while True:
                        records = await service.repository.events(
                            vehicle_id, investigation_id, cursor
                        )
                        for event in records:
                            yield (
                                f"id: {event.sequence}\nevent: {event.type}\n"
                                f"data: {event.model_dump_json()}\n\n"
                            )
                            cursor = event.sequence
                        plan = await service.get(vehicle_id, investigation_id)
                        if plan.status in TERMINAL:
                            return
                        await asyncio.sleep(0.25)
            except TimeoutError:
                return
            finally:
                streams -= 1

        return StreamingResponse(
            replay(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @router.post("/{investigation_id}/refresh", response_model=InvestigationPlan)
    async def refresh(
        vehicle_id: UUID,
        investigation_id: UUID,
        body: VersionRequest,
        actor: Annotated[str, Depends(operator)],
    ) -> InvestigationPlan:
        return await service.refresh(vehicle_id, investigation_id, body.version)

    @router.post("/{investigation_id}/approve", response_model=InvestigationPlan)
    async def approve(
        vehicle_id: UUID,
        investigation_id: UUID,
        body: ApprovalRequest,
        actor: Annotated[str, Depends(operator)],
    ) -> InvestigationPlan:
        return await service.approve(
            vehicle_id, investigation_id, body.version, body.recipe_hash, actor
        )

    @router.post("/{investigation_id}/reject", response_model=InvestigationPlan)
    async def reject(
        vehicle_id: UUID,
        investigation_id: UUID,
        body: VersionRequest,
        actor: Annotated[str, Depends(operator)],
    ) -> InvestigationPlan:
        return await service.reject(vehicle_id, investigation_id, body.version)

    @router.post("/{investigation_id}/cancel", response_model=InvestigationPlan)
    async def cancel(
        vehicle_id: UUID,
        investigation_id: UUID,
        body: VersionRequest,
        actor: Annotated[str, Depends(operator)],
    ) -> InvestigationPlan:
        return await service.cancel(vehicle_id, investigation_id, body.version)

    @router.post("/{investigation_id}/sessions", response_model=InvestigationPlan)
    async def link_session(
        vehicle_id: UUID,
        investigation_id: UUID,
        body: LinkSessionRequest,
        actor: Annotated[str, Depends(operator)],
    ) -> InvestigationPlan:
        return await service.link(vehicle_id, investigation_id, body.session_id, body.version)

    @router.post("/{investigation_id}/reanalyze", response_model=InvestigationPlan)
    async def reanalyze(
        vehicle_id: UUID,
        investigation_id: UUID,
        actor: Annotated[str, Depends(operator)],
    ) -> InvestigationPlan:
        return await service.reanalyze(vehicle_id, investigation_id)

    return router
