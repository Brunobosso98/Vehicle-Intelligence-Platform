"""Bounded metadata/citation API; ingestion stays an explicit operator CLI operation."""

import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import Field

from vehicle_platform.agents.context import resolve_context
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.service import AgentService
from vehicle_platform.knowledge.context import knowledge_scope
from vehicle_platform.knowledge.domain import (
    DocumentVersion,
    KnowledgeIndexVersion,
    KnowledgeSource,
    Model,
    RetrievalIntent,
    RetrievalResult,
)
from vehicle_platform.knowledge.retrieval import KnowledgeService


class IndexStatus(Model):
    snapshot: KnowledgeIndexVersion
    active: bool


class KnowledgeCatalog(Model):
    sources: list[KnowledgeSource] = Field(max_length=100)
    documents: list[DocumentVersion] = Field(max_length=100)
    indexes: list[IndexStatus] = Field(max_length=20)
    chunks: int = Field(ge=0)
    embeddings: int = Field(ge=0)


class KnowledgeQuery(Model):
    intent: RetrievalIntent
    session_id: UUID | None = None


def record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AgentError("invalid_tool_result")
    return value


def records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(r, dict) for r in value):
        raise AgentError("invalid_tool_result")
    return value


def knowledge_router(service: KnowledgeService, agents: AgentService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["knowledge"])
    active = 0

    @router.get("/knowledge", response_model=KnowledgeCatalog)
    async def catalog() -> KnowledgeCatalog:
        return KnowledgeCatalog.model_validate_json(
            service.redact(json.dumps(await service.repository.catalog()))
        )

    @router.post("/vehicles/{vehicle_id}/knowledge/query", response_model=RetrievalResult)
    async def search(vehicle_id: UUID, body: KnowledgeQuery) -> RetrievalResult:
        nonlocal active
        if active >= 4:
            raise HTTPException(status_code=429)
        active += 1
        try:
            async with asyncio.timeout(20), agents.client_factory() as client:
                args = {"vehicle_id": str(vehicle_id)}
                vehicle = await client.call("get_vehicle", args)
                configurations = await client.call(
                    "list_vehicle_configurations", args | {"limit": 20}
                )
                modifications = await client.call(
                    "list_vehicle_modifications", args | {"limit": 20}
                )
                if body.session_id:
                    result = await client.call(
                        "get_session", args | {"session_id": str(body.session_id)}
                    )
                    sessions = [record(result.data)]
                else:
                    sessions = []
                context = resolve_context(
                    vehicle_id,
                    record(vehicle.data),
                    records(configurations.data),
                    records(modifications.data),
                    sessions,
                )
                if configurations.truncated or modifications.truncated:
                    context.warnings.append("context_history_truncated")
                scope = knowledge_scope(context, body.session_id)
                return await service.search(body.intent, scope)
        except TimeoutError:
            raise HTTPException(status_code=503) from None
        finally:
            active -= 1

    @router.get(
        "/vehicles/{vehicle_id}/knowledge/retrievals/{retrieval_id}", response_model=RetrievalResult
    )
    async def retrieval(vehicle_id: UUID, retrieval_id: UUID) -> RetrievalResult:
        result = await service.repository.get_retrieval(vehicle_id, retrieval_id)
        if result is None:
            raise HTTPException(status_code=404)
        return RetrievalResult.model_validate_json(service.redact(result.model_dump_json()))

    return router
