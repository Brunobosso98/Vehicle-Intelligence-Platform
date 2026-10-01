from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.responses import Response
from starlette.types import ASGIApp

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
    config = settings or Settings()  # type: ignore[call-arg]  # BaseSettings loads required env.
    database = Database(config) if probe is None else None
    dependency = probe if probe is not None else database
    if dependency is None:
        raise RuntimeError("Database dependency not initialized")
    signals = telemetry or Telemetry(config, database)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if database is not None:
                await database.close()
            signals.shutdown()

    app = PlatformAPI(
        title="Vehicle Intelligence Platform",
        version=config.app_version,
        lifespan=lifespan,
        responses={500: {"model": ErrorResponse}},
    )
    app.state.telemetry = signals
    app.include_router(router(config, dependency))
    register_errors(app, signals)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(signals.render_metrics(), media_type="text/plain; version=0.0.4")

    return app
