from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
from vehicle_platform.observability.telemetry import Telemetry


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
    investigation_service = InvestigationService(
        agent_service,
        InvestigationRepository(agent_service.repository, signals),
        AcquisitionCapabilitySource(database or agent_database),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await investigation_service.close()
            await agent_service.close()
            await publisher.close()
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
    app.add_middleware(ResourceBudgetMiddleware)
    app.add_middleware(AgentRequestBudgetMiddleware)
    app.include_router(router(config, dependency, signals))
    app.state.agent_service = agent_service
    app.state.investigation_service = investigation_service
    app.include_router(agent_router(agent_service))
    app.include_router(investigation_router(investigation_service))
    register_errors(app, signals)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(signals.render_metrics(), media_type="text/plain; version=0.0.4")

    return app
