from fastapi import APIRouter, Request

from vehicle_platform.api.contracts import ErrorResponse, Health, Ready, Version
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import DatabaseProbe


def router(settings: Settings, database: DatabaseProbe) -> APIRouter:
    routes = APIRouter()

    @routes.get("/health/live", response_model=Health, operation_id="health_live")
    async def live() -> Health:
        return Health()

    @routes.get(
        "/health/ready",
        response_model=Ready,
        operation_id="health_ready",
        responses={503: {"model": ErrorResponse}},
    )
    async def ready(request: Request) -> Ready:
        await database.check()
        return Ready()

    @routes.get("/version", response_model=Version, operation_id="version")
    async def version() -> Version:
        return Version(
            version=settings.app_version,
            git_sha=settings.git_sha,
            build_timestamp=settings.build_timestamp,
            environment=settings.environment,
        )

    return routes
