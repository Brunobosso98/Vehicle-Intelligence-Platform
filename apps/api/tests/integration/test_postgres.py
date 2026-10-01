"""Requires an explicitly supplied disposable test database. Never skips silently."""

import asyncio
import os
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from vehicle_platform.core.config import Settings
from vehicle_platform.main import create_app

pytestmark = pytest.mark.integration
api = Path(__file__).resolve().parents[2]


@pytest.fixture
def url() -> str:
    value = os.environ.get("TEST_DATABASE_URL")
    if not value or not value.rsplit("/", 1)[-1].startswith("vehicle_test"):
        pytest.fail("TEST_DATABASE_URL must explicitly target a disposable vehicle_test* database")
    return value


async def test_clean_upgrade_downgrade_reupgrade_and_readiness(url: str) -> None:
    engine = create_async_engine(url)
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT to_regclass('alembic_version')")) is None
    env = os.environ | {"DATABASE_URL": url, "ENVIRONMENT": "test"}
    for target in ["head", "base", "head", "head"]:
        command = "downgrade" if target == "base" else "upgrade"
        process = await asyncio.create_subprocess_exec(
            str(api / ".venv/bin/alembic"),
            command,
            target,
            cwd=api,
            env=env,
        )
        assert await process.wait() == 0

    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
        assert await connection.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname='timescaledb'")
        )
        tables = (
            (
                await connection.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
                )
            )
            .scalars()
            .all()
        )
        assert tables == ["alembic_version"]
    app = create_app(Settings(database_url=url, environment="test"))
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        assert (await client.get("/health/ready")).status_code == 200
    await engine.dispose()
