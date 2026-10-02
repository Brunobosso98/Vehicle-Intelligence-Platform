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
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
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
        assert set(tables) == {
            "alembic_version",
            "vehicles",
            "vehicle_configurations",
            "modifications",
            "driving_sessions",
            "telemetry_samples",
            "session_segments",
            "pulls",
        }
        assert await connection.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM timescaledb_information.hypertables "
                "WHERE hypertable_name='telemetry_samples')"
            )
        )
    app = create_app(Settings(database_url=url, environment="test"))
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        assert (await client.get("/health/ready")).status_code == 200
        vehicle = (
            await client.post(
                "/api/v1/vehicles",
                json={
                    "manufacturer": "BMW",
                    "model": "335i",
                    "generation": "F30",
                    "model_year": 2015,
                    "engine_code": "N55",
                    "nickname": "Reference",
                },
            )
        ).json()
        session = (
            await client.post(
                "/api/v1/sessions",
                json={
                    "vehicle_id": vehicle["id"],
                    "source_type": "csv",
                    "started_at": "2026-01-01T00:00:00Z",
                },
            )
        ).json()
        csv = (
            "timestamp,signal,value,unit,record_id,sequence\n"
            "2026-01-01T00:00:02Z,rpm,1200,rpm,b,2\n"
            "2026-01-01T00:00:01Z,rpm,1000,rpm,a,1\n"
        )
        first = await client.post(
            f"/api/v1/sessions/{session['id']}/imports/csv",
            files={"file": ("drive.csv", csv, "text/csv")},
        )
        assert first.status_code == 200 and first.json()["accepted"] == 2
        replay = await client.post(
            f"/api/v1/sessions/{session['id']}/imports/csv",
            files={"file": ("drive.csv", csv, "text/csv")},
        )
        assert replay.json()["duplicates"] == 2
        points = (
            await client.get(
                f"/api/v1/sessions/{session['id']}/telemetry", params={"signal": "engine.rpm"}
            )
        ).json()["points"]
        assert [point["value"] for point in points] == [1000, 1200]
        analysis = await client.post(
            f"/api/v1/sessions/{session['id']}/analysis", json={"profile": "generic-v1"}
        )
        assert analysis.status_code == 200
        assert analysis.json()["configuration_hash"]
        replay_analysis = await client.post(
            f"/api/v1/sessions/{session['id']}/analysis", json={"profile": "generic-v1"}
        )
        assert replay_analysis.status_code == 200
        assert await client.get(f"/api/v1/sessions/{session['id']}/segments")
        assert await client.get(f"/api/v1/sessions/{session['id']}/pulls")
    await engine.dispose()
