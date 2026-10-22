import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from sqlalchemy.pool import NullPool
from starlette.responses import Response
from starlette.types import ASGIApp

from vehicle_platform.acquisition.capabilities import AcquisitionCapabilitySource
from vehicle_platform.acquisition.service import AcquisitionPublisher
from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.investigation.repository import InvestigationRepository
from vehicle_platform.agents.investigation.routes import investigation_router
from vehicle_platform.agents.investigation.service import InvestigationService
from vehicle_platform.agents.provider import Provider
from vehicle_platform.agents.repository import AgentRepository
from vehicle_platform.agents.routes import agent_router
from vehicle_platform.agents.service import AgentService
from vehicle_platform.api.budgets import AgentRequestBudgetMiddleware, ResourceBudgetMiddleware
from vehicle_platform.api.contracts import ErrorResponse
from vehicle_platform.api.errors import register_errors
from vehicle_platform.api.middleware import CorrelationMiddleware
from vehicle_platform.api.routes import router
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database, DatabaseProbe
from vehicle_platform.knowledge.embeddings import EmbeddingSettings
from vehicle_platform.knowledge.queries import QueryEmbeddingEncoder
from vehicle_platform.knowledge.repository import KnowledgeRepository
from vehicle_platform.knowledge.retrieval import KnowledgeService
from vehicle_platform.knowledge.routes import knowledge_router
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.prediction_evidence.service import PredictionEvidenceService
from vehicle_platform.predictions.budgets import (
    PredictionBudgetState,
    PredictionRequestBudgetMiddleware,
)
from vehicle_platform.predictions.routes import prediction_router
from vehicle_platform.predictions.service import PredictionService


class PlatformAPI(FastAPI):
    def build_middleware_stack(self) -> ASGIApp:
        return CorrelationMiddleware(super().build_middleware_stack(), self.state.telemetry)


def create_app(
    settings: Settings | None = None,
    probe: DatabaseProbe | None = None,
    telemetry: Telemetry | None = None,
) -> FastAPI:
    config = settings or Settings()
    database = Database(config) if probe is None else None
    dependency = probe if probe is not None else database
    if dependency is None:
        raise RuntimeError("Database dependency not initialized")
    signals = telemetry or Telemetry(config, database)
    publisher = AcquisitionPublisher(config)
    agent_config = AgentSettings()
    agent_database = Database(config, command_timeout=3, pool_pre_ping=False, poolclass=NullPool)
    prediction_database = (
        Database(
            config,
            command_timeout=config.prediction_request_timeout_seconds,
            pool_pre_ping=False,
            poolclass=NullPool,
        )
        if config.prediction_service_enabled
        else None
    )
    if config.environment == "production" and agent_config.provider == "deterministic":
        raise ValueError("Deterministic agent provider is restricted to development/test")

    def provider_factory() -> Provider:
        if agent_config.provider == "deterministic":
            from vehicle_platform.agents.scripted_provider import DeterministicProvider

            return DeterministicProvider()
        from vehicle_platform.agents.openai_provider import OpenAIProvider

        return OpenAIProvider(agent_config)

    agent_service = AgentService(
        AgentRepository(agent_database), agent_config, signals, provider_factory
    )
    knowledge_repository = KnowledgeRepository(database or agent_database, signals)
    embedding_config = EmbeddingSettings(_env_file=".env")

    def redact_knowledge(value: str) -> str:
        value = agent_service.redact(value)
        key = embedding_config.agent_api_key
        return (
            value.replace(key.get_secret_value(), "[redacted]")
            if key and key.get_secret_value()
            else value
        )

    query_encoder = QueryEmbeddingEncoder(
        knowledge_repository,
        embedding_config,
        signals,
        confirmed=os.environ.get("VIP_8_CONFIRM_EMBEDDING_SPEND") == "yes",
        allow_paid=config.environment != "test",
    )
    knowledge_service = KnowledgeService(
        knowledge_repository, signals, query_encoder, redact_knowledge
    )
    agent_service.knowledge = knowledge_service
    investigation_service = InvestigationService(
        agent_service,
        InvestigationRepository(agent_service.repository, signals),
        AcquisitionCapabilitySource(database or agent_database),
    )
    # The disabled service is unreachable behind admission middleware; retaining its router
    # keeps the OpenAPI contract stable without opening a second database pool.
    prediction_service = PredictionService(
        config,
        prediction_database if prediction_database is not None else cast(Database, dependency),
        telemetry=signals,
    )
    prediction_evidence_service = PredictionEvidenceService(
        prediction_database if prediction_database is not None else cast(Database, dependency),
        model_artifacts=prediction_service.model_artifacts,
        anomaly_artifacts=prediction_service.anomaly_artifacts,
        telemetry=signals,
        timeout_seconds=min(config.prediction_request_timeout_seconds, 6.0),
    )
    prediction_budget_state = PredictionBudgetState()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await investigation_service.close()
            await agent_service.close()
            await query_encoder.close()
            await publisher.close()
            await prediction_service.close()
            if prediction_database is not None:
                await prediction_database.close()
            if database is not None:
                await database.close()
            await agent_database.close()
            signals.shutdown()

    app = PlatformAPI(
        title="Vehicle Intelligence Platform",
        version=config.app_version,
        lifespan=lifespan,
        responses={status: {"model": ErrorResponse} for status in (422, 429, 500, 503)},
    )
    app.state.telemetry = signals
    app.state.acquisition_publisher = publisher
    app.state.prediction_service = prediction_service
    app.state.prediction_evidence_service = prediction_evidence_service
    app.state.prediction_budget_state = prediction_budget_state
    app.add_middleware(ResourceBudgetMiddleware)
    app.add_middleware(AgentRequestBudgetMiddleware)
    app.add_middleware(
        PredictionRequestBudgetMiddleware,
        settings=config,
        telemetry=signals,
        state=prediction_budget_state,
    )
    app.include_router(router(config, dependency, signals))
    app.include_router(prediction_router(prediction_service, prediction_evidence_service))
    app.state.knowledge_service = knowledge_service
    app.include_router(knowledge_router(knowledge_service, agent_service))
    app.state.agent_service = agent_service
    app.state.investigation_service = investigation_service
    app.include_router(agent_router(agent_service))
    app.include_router(investigation_router(investigation_service))
    register_errors(app, signals)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(signals.render_metrics(), media_type="text/plain; version=0.0.4")

    return app
