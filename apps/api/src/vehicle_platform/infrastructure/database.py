import asyncio
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vehicle_platform.core.config import Settings


class DependencyUnavailable(Exception):
    """Infrastructure failed its bounded readiness check."""


class DatabaseProbe(Protocol):
    async def check(self) -> None: ...


class Database:
    def __init__(
        self,
        settings: Settings,
        *,
        command_timeout: float | None = None,
        server_settings: dict[str, str] | None = None,
    ) -> None:
        connect_args: dict[str, object] = {
            "timeout": settings.readiness_timeout,
            "command_timeout": command_timeout,
        }
        if server_settings is not None:
            connect_args["server_settings"] = server_settings
        self.engine: AsyncEngine = create_async_engine(
            settings.database_url.get_secret_value(),
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self.timeout = settings.readiness_timeout
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    def session(self) -> AsyncSession:
        return self.sessions()

    async def check(self) -> None:
        try:
            async with asyncio.timeout(self.timeout), self.engine.connect() as connection:
                enabled = await connection.scalar(
                    text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')")
                )
                if not enabled:
                    raise DependencyUnavailable("Required extension missing")
        except (SQLAlchemyError, OSError, TimeoutError) as exc:
            raise DependencyUnavailable("Database check failed") from exc

    async def close(self) -> None:
        await self.engine.dispose()
