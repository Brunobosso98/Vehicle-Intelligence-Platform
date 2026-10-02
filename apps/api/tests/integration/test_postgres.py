"""Requires an explicitly supplied disposable test database. Never skips silently."""

import asyncio
import os
from pathlib import Path

import httpx
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
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
    script = ScriptDirectory.from_config(Config(api / "alembic.ini"))
    heads = script.get_heads()
    assert len(heads) == 1
    expected_head = heads[0]
    engine = create_async_engine(url)
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT to_regclass('alembic_version')")) is None
    env = os.environ | {"DATABASE_URL": url, "ENVIRONMENT": "test"}
    # Clean upgrade, one-revision rollback preserving the Phase 2 schema, re-upgrade,
    # idempotent head, full rollback, and final clean upgrade exercise both boundaries.
    for command, target in [
        ("upgrade", "head"),
        ("downgrade", "0004"),
        ("upgrade", "head"),
        ("upgrade", "head"),
        ("downgrade", "base"),
        ("upgrade", "head"),
    ]:
        process = await asyncio.create_subprocess_exec(
            str(api / ".venv/bin/alembic"),
            command,
            target,
            cwd=api,
            env=env,
        )
        assert await process.wait() == 0

    rollback = await asyncio.create_subprocess_exec(
        str(api / ".venv/bin/alembic"), "downgrade", "0004", cwd=api, env=env
    )
    assert await rollback.wait() == 0
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "0004"
        assert await connection.scalar(text("SELECT to_regclass('pulls')")) == "pulls"
        assert (
            await connection.scalar(text("SELECT to_regclass('detected_events')"))
            == "detected_events"
        )
        assert await connection.scalar(text("SELECT to_regclass('acquisition_sessions')")) is None
    reupgrade = await asyncio.create_subprocess_exec(
        str(api / ".venv/bin/alembic"), "upgrade", "head", cwd=api, env=env
    )
    assert await reupgrade.wait() == 0

    async with engine.connect() as connection:
        assert (
            await connection.scalar(text("SELECT version_num FROM alembic_version"))
            == expected_head
        )
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
            "event_analysis_runs",
            "detected_events",
            "acquisition_sessions",
            "stream_receipts",
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

        # A real persisted multi-anomaly session validates Phase 2 -> Phase 3 ordering,
        # same-session baselines, filters, details, replacement and repeated-run reuse.
        from vehicle_platform.events.synthetic import golden_scenarios

        scenario = golden_scenarios()[-1]
        multi_session = (
            await client.post(
                "/api/v1/sessions",
                json={
                    "vehicle_id": vehicle["id"],
                    "source_type": "csv",
                    "started_at": scenario.frames[0].observed_at.isoformat(),
                },
            )
        ).json()
        aliases = {
            "engine.rpm": ("rpm", "rpm"),
            "vehicle.speed": ("speed", "m/s"),
            "engine.throttle_position": ("throttle", "%"),
            "engine.boost_pressure": ("boost", "Pa"),
            "engine.intake_air_temperature": ("iat", "K"),
            "engine.oil_temperature": ("oil_temp", "K"),
            "engine.coolant_temperature": ("coolant_temp", "K"),
            "fuel.high_pressure": ("hpfp", "Pa"),
        }
        lines = ["timestamp,signal,value,unit,record_id,sequence"]
        sequence = 0
        for frame in reversed(
            scenario.frames
        ):  # ingestion order must not affect event-time analysis
            for subdivision in reversed(range(5)):
                observed_at = frame.observed_at + __import__("datetime").timedelta(
                    seconds=subdivision / 5
                )
                for signal_key, raw_value in frame.values.items():
                    if raw_value is None or signal_key not in aliases:
                        continue
                    value = raw_value
                    if (frame.values.get("engine.throttle_position") or 0) >= 70:
                        if signal_key == "engine.rpm":
                            value += subdivision * 100
                        elif signal_key == "vehicle.speed":
                            value += subdivision * 0.4
                    alias, unit = aliases[signal_key]
                    lines.append(
                        f"{observed_at.isoformat()},{alias},{value},{unit},{sequence},{sequence}"
                    )
                    sequence += 1
        imported = await client.post(
            f"/api/v1/sessions/{multi_session['id']}/imports/csv",
            files={"file": ("multi.csv", "\n".join(lines), "text/csv")},
        )
        assert imported.status_code == 200
        phase_two = await client.post(
            f"/api/v1/sessions/{multi_session['id']}/analysis",
            json={"profile": "generic-v1"},
        )
        assert phase_two.status_code == 200 and phase_two.json()["pull_count"] == 3
        event_run = await client.post(
            f"/api/v1/sessions/{multi_session['id']}/events/analyze", json={}
        )
        assert event_run.status_code == 200 and event_run.json()["event_count"] >= 3
        repeated = await client.post(
            f"/api/v1/sessions/{multi_session['id']}/events/analyze", json={}
        )
        assert repeated.json()["reused"] is True
        events = (
            await client.get(
                f"/api/v1/sessions/{multi_session['id']}/events",
                params={"category": "performance", "severity": "high"},
            )
        ).json()
        assert any(event["event_type"] == "boost_drop" for event in events)
        detail = await client.get(f"/api/v1/events/{events[0]['id']}")
        assert detail.status_code == 200 and detail.json()["evidence"]
        summary = await client.get(f"/api/v1/sessions/{multi_session['id']}/events/summary")
        assert summary.status_code == 200
        assert summary.json()["event_count"] == event_run.json()["event_count"]
        assert summary.json()["highest_severity"] in {"low", "moderate", "high"}
        replacement = await client.post(
            f"/api/v1/sessions/{multi_session['id']}/events/analyze", json={"replace": True}
        )
        assert replacement.status_code == 200 and replacement.json()["reused"] is False
        after = (await client.get(f"/api/v1/sessions/{multi_session['id']}/events")).json()
        identities = {
            (event["event_type"], event["algorithm_name"], event["started_at"], event["ended_at"])
            for event in after
        }
        assert len(identities) == len(after)
    await engine.dispose()
