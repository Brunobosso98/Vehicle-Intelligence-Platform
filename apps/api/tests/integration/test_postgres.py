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
            "provisional_findings",
            "dataset_capability_reports",
            "stream_dead_letters",
            "analytics_runs",
        }
        assert await connection.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM timescaledb_information.hypertables "
                "WHERE hypertable_name='telemetry_samples')"
            )
        )

    # Phase 5 semantic boundary: discover the current head and direct parent rather than
    # duplicating a stale revision literal in migration guards.
    head_revision = script.get_revision(expected_head)
    assert head_revision is not None and head_revision.down_revision is not None
    phase5_parent = str(head_revision.down_revision)
    # Seed earlier-phase data before crossing the Phase 5 boundary. Table names
    # alone cannot establish that a downgrade preserves actual canonical history.
    async with engine.begin() as connection:
        retained_vehicle = await connection.scalar(
            text(
                "INSERT INTO vehicles(manufacturer,model) "
                "VALUES('fixture','migration-boundary') RETURNING id"
            )
        )
        retained_session = await connection.scalar(
            text(
                "INSERT INTO driving_sessions(vehicle_id,source_type,started_at) "
                "VALUES(:vehicle,'synthetic','2026-01-01T00:00:00Z') RETURNING id"
            ),
            {"vehicle": retained_vehicle},
        )
        await connection.execute(
            text(
                "INSERT INTO telemetry_samples(sample_id,vehicle_id,session_id,observed_at,"
                "signal_key,numeric_value,normalized_unit,raw_signal,source,source_record_id,"
                "quality,schema_version,content_hash) VALUES(:sample,:vehicle,:session,"
                "'2026-01-01T00:00:00Z','engine.rpm',900,'rpm','rpm','synthetic',"
                "'boundary','valid',1,:sample)"
            ),
            {"sample": "f" * 64, "vehicle": retained_vehicle, "session": retained_session},
        )
    phase5_downgrade = await asyncio.create_subprocess_exec(
        str(api / ".venv/bin/alembic"), "downgrade", phase5_parent, cwd=api, env=env
    )
    assert await phase5_downgrade.wait() == 0
    async with engine.connect() as connection:
        assert (
            await connection.scalar(text("SELECT version_num FROM alembic_version"))
            == phase5_parent
        )
        assert await connection.scalar(text("SELECT to_regclass('analytics_runs')")) is None
        assert (
            await connection.scalar(
                text("SELECT numeric_value FROM telemetry_samples WHERE sample_id=:sample"),
                {"sample": "f" * 64},
            )
            == 900
        )
        assert (
            await connection.scalar(
                text("SELECT vehicle_id FROM driving_sessions WHERE id=:id"),
                {"id": retained_session},
            )
            == retained_vehicle
        )
        for retained in (
            "acquisition_sessions",
            "stream_receipts",
            "provisional_findings",
            "dataset_capability_reports",
            "stream_dead_letters",
            "detected_events",
            "event_analysis_runs",
            "pulls",
            "telemetry_samples",
        ):
            assert (
                await connection.scalar(text("SELECT to_regclass(:table)"), {"table": retained})
                == retained
            )
        assert await connection.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname='timescaledb'")
        )
        assert await connection.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM timescaledb_information.hypertables "
                "WHERE hypertable_name='telemetry_samples')"
            )
        )
    phase5_reupgrade = await asyncio.create_subprocess_exec(
        str(api / ".venv/bin/alembic"), "upgrade", expected_head, cwd=api, env=env
    )
    assert await phase5_reupgrade.wait() == 0
    async with engine.connect() as connection:
        assert (
            await connection.scalar(text("SELECT version_num FROM alembic_version"))
            == expected_head
        )
        assert (
            await connection.scalar(text("SELECT to_regclass('analytics_runs')"))
            == "analytics_runs"
        )
        assert (
            await connection.scalar(text("SELECT to_regclass('acquisition_sessions')"))
            == "acquisition_sessions"
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
        phase5_pulls = (await client.get(f"/api/v1/sessions/{multi_session['id']}/pulls")).json()
        pull_ids = [pull["id"] for pull in phase5_pulls]
        analytics = await client.post(
            "/api/v1/analytics/pulls/repeated", json={"pull_ids": pull_ids}
        )
        assert analytics.status_code == 200
        payload = analytics.json()
        assert payload["algorithm_version"] == "1.1.0"
        assert len(payload["configuration_hash"]) == 64
        assert payload["result"]["sequence"]
        markers = [
            marker
            for profile in payload["result"]["comparison"]["profiles"]
            for marker in profile["event_markers"]
        ]
        assert any(
            marker["event_type"] == "boost_drop"
            and marker["id"] in {event["id"] for event in after}
            for marker in markers
        )
        reused = await client.post("/api/v1/analytics/pulls/repeated", json={"pull_ids": pull_ids})
        assert reused.json()["id"] == payload["id"] and reused.json()["reused"] is True
        recomputed = await client.post(
            "/api/v1/analytics/pulls/repeated",
            json={"pull_ids": pull_ids, "recompute": True},
        )
        assert recomputed.status_code == 200 and recomputed.json()["id"] != payload["id"]
        async with engine.connect() as connection:
            persisted = await connection.scalar(
                text("SELECT count(*) FROM analytics_runs WHERE analytics_type='repeated_pulls'")
            )
            assert persisted == 2
        configuration_a = (
            await client.post(
                f"/api/v1/vehicles/{vehicle['id']}/configurations",
                json={
                    "effective_at": "2020-01-01T00:00:00Z",
                    "description": "A",
                    "provenance": "phase5-integration",
                },
            )
        ).json()
        configuration_b = (
            await client.post(
                f"/api/v1/vehicles/{vehicle['id']}/configurations",
                json={
                    "effective_at": "2025-01-01T00:00:00Z",
                    "description": "B",
                    "provenance": "phase5-integration",
                },
            )
        ).json()
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE driving_sessions SET configuration_id=:configuration WHERE id=:session"
                ),
                {"configuration": configuration_a["id"], "session": multi_session["id"]},
            )
            await connection.execute(
                text("UPDATE pulls SET configuration_id=:configuration WHERE session_id=:session"),
                {"configuration": configuration_a["id"], "session": multi_session["id"]},
            )

        sessions_by_configuration: dict[str, list[str]] = {
            configuration_a["id"]: [multi_session["id"]],
            configuration_b["id"]: [],
        }
        pulls_by_configuration: dict[str, list[str]] = {
            configuration_a["id"]: pull_ids,
            configuration_b["id"]: [],
        }
        for history_index, configuration in enumerate(
            (
                configuration_a,
                configuration_a,
                configuration_b,
                configuration_b,
                configuration_b,
            )
        ):
            from datetime import datetime, timedelta

            shift = timedelta(days=(1, 2, 30, 31, 32)[history_index])
            history_lines = [lines[0]]
            for line in lines[1:]:
                stamp, rest = line.split(",", 1)
                history_lines.append(
                    f"{(datetime.fromisoformat(stamp) + shift).isoformat()},{rest}"
                )
            created = (
                await client.post(
                    "/api/v1/sessions",
                    json={
                        "vehicle_id": vehicle["id"],
                        "configuration_id": configuration["id"],
                        "source_type": "csv",
                        "started_at": (scenario.frames[0].observed_at + shift).isoformat(),
                    },
                )
            ).json()
            assert (
                await client.post(
                    f"/api/v1/sessions/{created['id']}/imports/csv",
                    files={"file": ("history.csv", "\n".join(history_lines), "text/csv")},
                )
            ).status_code == 200
            assert (
                await client.post(
                    f"/api/v1/sessions/{created['id']}/analysis", json={"profile": "generic-v1"}
                )
            ).status_code == 200
            sessions_by_configuration[configuration["id"]].append(created["id"])
            history_pulls = (await client.get(f"/api/v1/sessions/{created['id']}/pulls")).json()
            pulls_by_configuration[configuration["id"]].extend(pull["id"] for pull in history_pulls)

        scoped = await client.get(
            "/api/v1/pulls",
            params={
                "vehicle_id": vehicle["id"],
                "configuration_id": configuration_a["id"],
                "limit": 20,
            },
        )
        assert scoped.status_code == 200
        assert {pull["id"] for pull in scoped.json()} == set(
            pulls_by_configuration[configuration_a["id"]]
        )
        assert all(pull["configuration_id"] == configuration_a["id"] for pull in scoped.json())
        comparison = await client.post(
            "/api/v1/analytics/pulls/compare",
            json={"pull_ids": pulls_by_configuration[configuration_a["id"]][:2]},
        )
        assert comparison.status_code == 200 and comparison.json()["result"]["common_rpm_range"]
        session_result = await client.post(
            f"/api/v1/sessions/{sessions_by_configuration[configuration_a['id']][1]}/analytics",
            json={},
        )
        assert session_result.status_code == 200
        cross = await client.post(
            "/api/v1/analytics/sessions/compare",
            params=[
                ("session_ids", item)
                for item in sessions_by_configuration[configuration_a["id"]][:2]
            ],
            json={},
        )
        assert cross.status_code == 200
        baseline_a = await client.post(
            f"/api/v1/vehicles/{vehicle['id']}/configurations/{configuration_a['id']}/baseline",
            json={},
        )
        assert baseline_a.status_code == 200 and baseline_a.json()["result"]["session_count"] >= 3
        rebuilt = await client.post(
            f"/api/v1/vehicles/{vehicle['id']}/configurations/{configuration_a['id']}/baseline",
            json={"recompute": True},
        )
        assert rebuilt.json()["id"] != baseline_a.json()["id"]
        trend_result = await client.post(f"/api/v1/vehicles/{vehicle['id']}/trends/boost", json={})
        assert set(trend_result.json()["result"]["segments_by_configuration"]) == {
            configuration_a["id"],
            configuration_b["id"],
        }
        query = [
            ("after_pull_ids", item) for item in pulls_by_configuration[configuration_b["id"]][::3]
        ]
        before_after = await client.post(
            "/api/v1/analytics/configurations/compare",
            params=query,
            json={"pull_ids": pulls_by_configuration[configuration_a["id"]][::3]},
        )
        assert before_after.status_code == 200 and before_after.json()["result"][
            "sample_sizes"
        ] == {"before": 3, "after": 3}
        assert before_after.json()["result"]["sufficiency"] == "sufficient"
        assert before_after.json()["result"]["metric_deltas"]["boost"]["absolute"] == 0
        isolated = await client.post(
            "/api/v1/analytics/pulls/compare",
            json={
                "pull_ids": [
                    pulls_by_configuration[configuration_a["id"]][0],
                    pulls_by_configuration[configuration_b["id"]][0],
                ]
            },
        )
        assert isolated.json()["result"]["sufficiency"] == "insufficient"
    await engine.dispose()


@pytest.mark.parametrize("with_speed", [True, False])
async def test_stream_poll_is_atomic_replay_safe_and_persists_provisional_findings(
    url: str,
    with_speed: bool,
) -> None:
    from datetime import UTC, datetime, timedelta
    from uuid import UUID, uuid4

    from sqlalchemy.exc import IntegrityError

    from vehicle_platform.acquisition.service import AcquisitionService
    from vehicle_platform.acquisition.worker import StreamConsumer
    from vehicle_platform.infrastructure.database import Database

    env = os.environ | {"DATABASE_URL": url, "ENVIRONMENT": "test"}
    process = await asyncio.create_subprocess_exec(
        str(api / ".venv/bin/alembic"), "upgrade", "head", cwd=api, env=env
    )
    assert await process.wait() == 0
    settings = Settings(database_url=url, environment="test")
    app = create_app(settings)
    database = Database(settings)
    worker = StreamConsumer(database, settings)
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            worker.telemetry = app.state.telemetry
            vehicle = await client.post(
                "/api/v1/vehicles",
                json={
                    "manufacturer": "BMW",
                    "model": "335i",
                    "generation": "F30",
                    "model_year": 2015,
                    "engine_code": "N55",
                    "nickname": "Stream regression",
                },
            )
            assert vehicle.status_code == 201
            configuration = await client.post(
                f"/api/v1/vehicles/{vehicle.json()['id']}/configurations",
                json={
                    "effective_at": "2020-01-01T00:00:00Z",
                    "description": "active stream context",
                    "provenance": "integration-fixture",
                },
            )
            assert configuration.status_code == 201
            response = await client.post(
                "/api/v1/acquisitions",
                json={
                    "vehicle_id": vehicle.json()["id"],
                    "recipe_key": "general-health",
                    "adapter": "synthetic",
                    "source_id": "disposable-stream-regression",
                },
            )
            assert response.status_code == 201
            acquisition = response.json()
            driving_session = await client.get(
                f"/api/v1/sessions/{acquisition['driving_session_id']}"
            )
            assert driving_session.json()["configuration_id"] == configuration.json()["id"]
            heartbeat_payload = {
                "adapter_state": "connected",
                "collection_started_at": datetime.now(UTC).isoformat(),
                "capability_snapshot": {
                    "adapter": "test-read-only",
                    "signals": {"engine.rpm": "supported"},
                    "maximum_requests_per_second": 70,
                },
                "sampling_plan": [
                    {
                        "signal": "engine.rpm",
                        "priority": "critical_for_recipe",
                        "target_hz": 5,
                        "estimated_hz": 5,
                    }
                ],
                "queue_observations": 0,
                "spool_bytes": 0,
                "dropped_observations": 0,
            }
            heartbeat_path = f"/api/v1/acquisitions/{acquisition['id']}/heartbeat"
            invalid_heartbeat = await client.post(heartbeat_path, json=heartbeat_payload)
            assert invalid_heartbeat.status_code == 401
            reported_heartbeat = await client.post(
                heartbeat_path,
                json=heartbeat_payload,
                headers={"Authorization": f"Bearer {acquisition['ingestion_token']}"},
            )
            assert reported_heartbeat.status_code == 200
            assert reported_heartbeat.json()["quality"]["collector_health"]["state"] == "connected"
            acquisition_id = UUID(acquisition["id"])
            session_id = UUID(acquisition["driving_session_id"])
            started = datetime(2026, 1, 1, tzinfo=UTC)
            envelopes: list[dict[str, object]] = []
            for index in range(500):
                speed = with_speed and index % 2 == 1
                envelopes.append(
                    {
                        "schema_version": "1.0",
                        "message_id": str(uuid4()),
                        "acquisition_session_id": str(acquisition_id),
                        "driving_session_id": str(session_id),
                        "source_id": "synthetic",
                        "observed_at": (
                            started + timedelta(milliseconds=(index // 2) * 100)
                        ).isoformat(),
                        "produced_at": started.isoformat(),
                        "batch_id": str(uuid4()),
                        "sequence": index,
                        "payload": {
                            "signal": "vehicle.speed" if speed else "engine.rpm",
                            "value": 0 if speed else 900,
                            "unit": "m/s" if speed else "rpm",
                            "source_record_id": str(index),
                        },
                    }
                )
            assert await worker.persist_batch(envelopes) == 500
            assert await worker.persist_batch(envelopes) == 0
            assert await worker.persist_batch([envelopes[0], envelopes[0]]) == 0
            # A new message ID with the same canonical sample is receipted once,
            # but must not increment the durable canonical sample count.
            duplicate_sample = envelopes[0] | {"message_id": str(uuid4())}
            assert await worker.persist(duplicate_sample)
            measured = (await client.get("/metrics")).text
            from prometheus_client.parser import text_string_to_metric_families

            samples = [
                sample
                for family in text_string_to_metric_families(measured)
                for sample in family.samples
            ]
            assert (
                sum(
                    sample.value
                    for sample in samples
                    if sample.name == "acquisition_observations_persisted_total"
                )
                == 500
            )
            assert (
                sum(
                    sample.value
                    for sample in samples
                    if sample.name == "acquisition_observations_duplicate_total"
                )
                == 503
            )
            assert all(
                not {"vehicle_id", "session_id", "vin"} & sample.labels.keys() for sample in samples
            )
            async with database.session() as db:
                assert (
                    await db.scalar(
                        text("SELECT sample_count FROM driving_sessions WHERE id=:id"),
                        {"id": session_id},
                    )
                    == 500
                )
                assert (
                    await db.scalar(
                        text(
                            "SELECT count(*) FROM stream_receipts WHERE acquisition_session_id=:id"
                        ),
                        {"id": acquisition_id},
                    )
                    == 501
                )
                findings = (
                    await db.execute(
                        text(
                            "SELECT finding_type,category,evidence FROM provisional_findings "
                            "WHERE acquisition_session_id=:id"
                        ),
                        {"id": acquisition_id},
                    )
                ).all()
                if with_speed:
                    assert any(row.finding_type == "possible_idle" for row in findings)
                else:
                    # Missing speed cannot support a factual idle classification.
                    assert findings == []
                assert all(
                    row.category == "performance" and row.evidence["provisional"]
                    for row in findings
                )
            # A foreign-key failure rolls back the entire poll, including receipts.
            valid = envelopes[0] | {
                "message_id": str(uuid4()),
                "sequence": 501,
                "payload": {
                    "signal": "engine.rpm",
                    "value": 900,
                    "unit": "rpm",
                    "source_record_id": "rollback-valid",
                },
            }
            invalid = valid | {"message_id": str(uuid4()), "acquisition_session_id": str(uuid4())}
            with pytest.raises(IntegrityError):
                await worker.persist_batch([valid, invalid])
            assert await worker.persist(valid)
            assert not await worker.persist(valid)
            async with database.session() as db:
                assert (
                    await db.scalar(
                        text("SELECT sample_count FROM driving_sessions WHERE id=:id"),
                        {"id": session_id},
                    )
                    == 501
                )
            # Repeated provisional evaluation must not create duplicate findings.
            await worker._provisional(acquisition_id)
            async with database.session() as db:
                assert await db.scalar(
                    text(
                        "SELECT count(*) FROM provisional_findings WHERE acquisition_session_id=:id"
                    ),
                    {"id": acquisition_id},
                ) == len(findings)
                # Nullable provisional boundaries must reconcile against canonical
                # timestamps with typed binds, even when no pull/event confirms them.
                for finding_type in ("possible_pull", "boost_drop"):
                    await db.execute(
                        text(
                            "INSERT INTO provisional_findings(acquisition_session_id,"
                            "finding_type,category,started_at,ended_at,evidence) "
                            "VALUES(:id,:type,'performance',:started,NULL,'{}'::jsonb)"
                        ),
                        {"id": acquisition_id, "type": finding_type, "started": started},
                    )
                await db.commit()
            stopped = await client.post(
                f"/api/v1/acquisitions/{acquisition_id}/stop",
                headers={"Authorization": f"Bearer {acquisition['ingestion_token']}"},
            )
            assert stopped.status_code == 200
            assert stopped.json()["quality"]["collector"]["adapter_state"] == "connected"
            assert stopped.json()["quality"]["collector"]["capability_snapshot"]["signals"] == {
                "engine.rpm": "supported"
            }
            assert stopped.json()["quality"]["collector"]["sampling_plan"][0]["target_hz"] == 5
            closed_heartbeat = await client.post(
                heartbeat_path,
                json=heartbeat_payload,
                headers={"Authorization": f"Bearer {acquisition['ingestion_token']}"},
            )
            assert closed_heartbeat.status_code == 401
            await AcquisitionService(database, settings, app.state.telemetry)._await_persistence()
            finalized = await client.post(f"/api/v1/acquisitions/{acquisition_id}/finalize")
            assert finalized.status_code == 200, finalized.text
            assert finalized.json()["state"] == "completed"
            async with database.session() as db:
                stored_report = await db.scalar(
                    text(
                        "SELECT report FROM dataset_capability_reports "
                        "WHERE driving_session_id=:session"
                    ),
                    {"session": acquisition["driving_session_id"]},
                )
                assert stored_report == finalized.json()["capability_report"]
            reconciled = await client.get(f"/api/v1/acquisitions/{acquisition_id}/findings")
            assert reconciled.status_code == 200
            assert len(reconciled.json()) == len(findings) + 2
            by_type = {item["finding_type"]: item for item in reconciled.json()}
            assert by_type["possible_pull"]["reconciliation_status"] == "absent"
            assert by_type["boost_drop"]["reconciliation_status"] == "absent"
            if with_speed:
                assert by_type["possible_idle"]["reconciliation_status"] == "confirmed"
                assert by_type["possible_idle"]["canonical_reference"] is not None
                assert finalized.json()["reconciliation"]["confirmed"] >= 1
            else:
                assert finalized.json()["reconciliation"]["confirmed"] == 0
            # Completed acquisition streams terminate after their real snapshot.
            live = await client.get(f"/api/v1/acquisitions/{acquisition_id}/live")
            assert live.status_code == 200
            assert live.headers["content-type"].startswith("text/event-stream")
            assert '"schema_version":"1.0"' in live.text
            assert '"publisher_to_persistence_seconds":' in live.text
            assert '"persistence_state":"observations_committed"' in live.text
            assert '"reconciliation_status":"absent"' in live.text
            streams = await asyncio.gather(
                *(client.get(f"/api/v1/acquisitions/{acquisition_id}/live") for _ in range(11))
            )
            assert sum(item.status_code == 200 for item in streams) == 10
            assert sum(item.status_code == 429 for item in streams) == 1
            limited = next(item for item in streams if item.status_code == 429)
            assert limited.headers["retry-after"] == "1"
            assert limited.json()["error"]["code"] == "RESOURCE_BUDGET_EXCEEDED"
            recovered_stream = await client.get(f"/api/v1/acquisitions/{acquisition_id}/live")
            assert recovered_stream.status_code == 200

    finally:
        await database.close()


async def test_sequence_overflow_is_dead_lettered_and_valid_edge_persists(url: str) -> None:
    import hashlib
    import json
    from datetime import UTC, datetime
    from uuid import UUID, uuid4

    from aiokafka import AIOKafkaProducer

    from vehicle_platform.acquisition.worker import StreamConsumer
    from vehicle_platform.infrastructure.database import Database
    from vehicle_platform.telemetry.domain import MAX_SEQUENCE

    settings = Settings(database_url=url, environment="test")
    app = create_app(settings)
    database = Database(settings)
    worker = StreamConsumer(database, settings, app.state.telemetry)
    task = None
    vehicle_id = None
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            vehicle_response = await client.post(
                "/api/v1/vehicles", json={"manufacturer": "fixture", "model": "sequence"}
            )
            assert vehicle_response.status_code == 201
            vehicle_id = UUID(vehicle_response.json()["id"])
            created = await client.post(
                "/api/v1/acquisitions",
                json={
                    "vehicle_id": str(vehicle_id),
                    "recipe_key": "general-health",
                    "adapter": "synthetic",
                    "source_id": "disposable-sequence-fixture",
                },
            )
            assert created.status_code == 201
            acquisition = created.json()
            observed = datetime.now(UTC).isoformat()
            batch = {
                "schema_version": "1.0",
                "batch_id": str(uuid4()),
                "observations": [
                    {
                        "message_id": str(uuid4()),
                        "observed_at": observed,
                        "sequence": MAX_SEQUENCE + 1,
                        "signal": "vehicle.speed",
                        "value": 36,
                        "unit": "km/h",
                        "source_record_id": "edge",
                    }
                ],
            }
            headers = {"authorization": f"Bearer {acquisition['ingestion_token']}"}
            rejected = await client.post(
                f"/api/v1/acquisitions/{acquisition['id']}/batches", json=batch, headers=headers
            )
            assert rejected.status_code == 422
            task = asyncio.create_task(worker.run())
            poisoned = json.dumps(
                {
                    "schema_version": "1.0",
                    "batch_id": str(uuid4()),
                    "message_id": str(uuid4()),
                    "observed_at": observed,
                    "produced_at": observed,
                    "acquisition_session_id": acquisition["id"],
                    "driving_session_id": acquisition["driving_session_id"],
                    "source_id": "fixture",
                    "sequence": MAX_SEQUENCE + 1,
                    "payload": {
                        "signal": "engine.rpm",
                        "value": 900,
                        "unit": "rpm",
                        "source_record_id": "poisoned-edge",
                    },
                }
            ).encode()
            producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
            await producer.start()
            try:
                await producer.send_and_wait("telemetry.raw.v1", poisoned)
            finally:
                await producer.stop()
            batch["observations"][0]["sequence"] = MAX_SEQUENCE
            accepted = await client.post(
                f"/api/v1/acquisitions/{acquisition['id']}/batches", json=batch, headers=headers
            )
            assert accepted.status_code == 202
            async with asyncio.timeout(20):
                while True:
                    if task.done():
                        await task
                        pytest.fail("consumer exited before valid-edge persistence")
                    async with database.session() as db:
                        sample = (
                            (
                                await db.execute(
                                    text(
                                        "SELECT sequence_number,numeric_value,normalized_unit,"
                                        "raw_value,source_metadata FROM telemetry_samples "
                                        "WHERE session_id=:id"
                                    ),
                                    {"id": UUID(acquisition["driving_session_id"])},
                                )
                            )
                            .mappings()
                            .one_or_none()
                        )
                        category = await db.scalar(
                            text(
                                "SELECT error_category FROM stream_dead_letters "
                                "WHERE message_id=:id"
                            ),
                            {"id": hashlib.sha256(poisoned).hexdigest()},
                        )
                    if sample is not None and category is not None:
                        assert sample["sequence_number"] == MAX_SEQUENCE
                        assert sample["numeric_value"] == 10
                        assert sample["normalized_unit"] == "m/s"
                        assert float(sample["raw_value"]) == 36
                        assert sample["source_metadata"]["source_unit"] == "km/h"
                        assert category == "invalid_stream_contract"
                        break
                    await asyncio.sleep(0.02)
    finally:
        worker.running = False
        if task is not None:
            async with asyncio.timeout(10):
                await task
        async with database.session() as db:
            if vehicle_id is not None:
                await db.execute(
                    text(
                        "UPDATE acquisition_sessions SET state='failed' WHERE driving_session_id "
                        "IN (SELECT id FROM driving_sessions WHERE vehicle_id=:id)"
                    ),
                    {"id": vehicle_id},
                )
                await db.commit()
        await database.close()


async def test_retrospective_signed_csv_duplicates_and_analytics_identity(url: str) -> None:
    app = create_app(Settings(database_url=url, environment="test"))
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        created = await client.post(
            "/api/v1/vehicles",
            json={
                "manufacturer": "BMW",
                "model": "335i",
                "generation": "F30",
                "model_year": 2015,
                "engine_code": "N55",
                "nickname": "hardening",
            },
        )
        assert created.status_code == 201
        vehicle = created.json()
        session_response = await client.post(
            "/api/v1/sessions",
            json={
                "vehicle_id": vehicle["id"],
                "source_type": "csv",
                "source_reference": "signed-duplicate",
                "started_at": "2026-01-01T00:00:00Z",
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()
        header = b"timestamp,signal,value,unit,record_id,sequence\n"
        row = b"2026-01-01T00:00:00Z,boost,-0.3,bar,negative,1\n"
        imported = await client.post(
            f"/api/v1/sessions/{session['id']}/imports/csv",
            files={"file": ("signed.csv", header + row + row, "text/csv")},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["accepted"] == 1
        assert imported.json()["duplicates"] == 1
        window = await client.get(
            f"/api/v1/sessions/{session['id']}/telemetry",
            params={"signal": "engine.boost_pressure"},
        )
        assert window.status_code == 200
        assert window.json()["points"][0]["value"] == -30000
        for endpoint in ("telemetry", "events"):
            params = {"start": "2026-01-01T00:00:00"}
            if endpoint == "telemetry":
                params["signal"] = "engine.boost_pressure"
            invalid_time = await client.get(
                f"/api/v1/sessions/{session['id']}/{endpoint}", params=params
            )
            assert invalid_time.status_code == 422
        missing_capability = await client.get(
            f"/api/v1/sessions/{__import__('uuid').uuid4()}/capabilities"
        )
        assert missing_capability.status_code == 404
        missing_window = await client.get(
            f"/api/v1/sessions/{__import__('uuid').uuid4()}/telemetry",
            params={"signal": "engine.rpm"},
        )
        assert missing_window.status_code == 404
        conflict = await client.post(
            f"/api/v1/sessions/{session['id']}/imports/csv",
            files={"file": ("conflict.csv", header + row.replace(b"-0.3", b"-0.2"), "text/csv")},
        )
        assert conflict.json()["conflicts"] == 1
        assert conflict.json()["accepted"] == 0
        session_analytics = await client.post(
            f"/api/v1/sessions/{session['id']}/analytics", json={}
        )
        assert session_analytics.status_code == 200
        assert session_analytics.json()["status"] == "insufficient"
        assert (
            session_analytics.json()["result"]["session_summary"]["telemetry_observation_count"]
            == 1
        )
        mapped_session_response = await client.post(
            "/api/v1/sessions",
            json={
                "vehicle_id": vehicle["id"],
                "source_type": "csv",
                "source_reference": "explicit-wide-csv",
                "started_at": "2026-01-01T00:00:00Z",
            },
        )
        assert mapped_session_response.status_code == 201
        mapped_id = mapped_session_response.json()["id"]
        mapping_json = __import__("json").dumps(
            {
                "timestamp_column": "Time",
                "record_id_column": "ID",
                "sequence_column": "Sequence",
                "signals": [
                    {"column": "Pressure", "signal": "engine.boost_pressure", "unit": "bar"}
                ],
            }
        )
        wide_csv = b"Time,Pressure,ID,Sequence,Notes\n2026-01-01T00:00:00Z,-0.3,p1,7,ignored\n"
        wide_file = {"file": ("wide.csv", wide_csv, "text/csv")}
        mapping_required = await client.post(
            f"/api/v1/sessions/{mapped_id}/imports/csv/preview",
            files=wide_file,
        )
        assert mapping_required.status_code == 200
        assert mapping_required.json()["requires_mapping"] is True
        mapped_preview = await client.post(
            f"/api/v1/sessions/{mapped_id}/imports/csv/preview",
            files=wide_file,
            data={"mapping": mapping_json},
        )
        assert mapped_preview.status_code == 200, mapped_preview.text
        assert mapped_preview.json()["unmapped_columns"] == ["Notes"]
        assert mapped_preview.json()["preview_points"][0]["value"] == -30000
        before_import = await client.get(
            f"/api/v1/sessions/{mapped_id}/telemetry",
            params={"signal": "engine.boost_pressure"},
        )
        assert before_import.json()["points"] == []
        for expected_accepted, expected_duplicates in [(1, 0), (0, 1)]:
            mapped_import = await client.post(
                f"/api/v1/sessions/{mapped_id}/imports/csv",
                files=wide_file,
                data={"mapping": mapping_json},
            )
            assert mapped_import.status_code == 200, mapped_import.text
            assert mapped_import.json()["accepted"] == expected_accepted
            assert mapped_import.json()["duplicates"] == expected_duplicates
        mapped_engine = create_async_engine(url)
        async with mapped_engine.connect() as connection:
            mapped_row = (
                (
                    await connection.execute(
                        text(
                            "SELECT raw_signal,raw_value,source_record_id,"
                            "sequence_number,source_metadata "
                            "FROM telemetry_samples WHERE session_id=:id"
                        ),
                        {"id": mapped_id},
                    )
                )
                .mappings()
                .one()
            )
        await mapped_engine.dispose()
        assert mapped_row["raw_signal"] == "Pressure"
        assert mapped_row["raw_value"] == "-0.3"
        assert mapped_row["source_record_id"] == "p1:Pressure"
        assert mapped_row["sequence_number"] == 7
        assert (
            mapped_row["source_metadata"]["csv_mapping_hash"]
            == mapped_preview.json()["mapping_hash"]
        )
        assert mapped_row["source_metadata"]["csv_mapping_version"] == "1.0"
        assert mapped_row["source_metadata"]["source_unit"] == "bar"
        trend_a = await client.post(f"/api/v1/vehicles/{vehicle['id']}/trends/boost", json={})
        trend_b = await client.post(f"/api/v1/vehicles/{vehicle['id']}/trends/iat", json={})
        assert trend_a.status_code == trend_b.status_code == 200
        assert trend_a.json()["id"] != trend_b.json()["id"]
        assert trend_a.json()["result"]["metric"] == "boost"
        assert trend_b.json()["result"]["metric"] == "iat"
        concurrent = await asyncio.gather(
            *(
                client.post(f"/api/v1/vehicles/{vehicle['id']}/trends/fuel", json={})
                for _ in range(3)
            )
        )
        assert all(r.status_code == 200 for r in concurrent)
        assert len({r.json()["id"] for r in concurrent}) == 1
        assert "analytics_runs_total" in (await client.get("/metrics")).text
        from uuid import UUID

        from vehicle_platform.acquisition.service import AcquisitionService
        from vehicle_platform.infrastructure.database import Database

        assessment_settings = Settings(database_url=url, environment="test")
        assessment_database = Database(assessment_settings)
        try:
            assessment = await AcquisitionService(
                assessment_database, assessment_settings, app.state.telemetry
            ).capability_report(UUID(session["id"]), "performance-pull")
        finally:
            await assessment_database.close()
        assert assessment["assessment_version"] == "1.1.0"
        assert assessment["recipe_adherence"] is False
        assert assessment["duration_seconds"] == 0
        assert assessment["observation_count"] == 1
        assert assessment["available_signals"] == ["engine.boost_pressure"]
        assert not any(item["supported"] for item in assessment["capabilities"])
        from uuid import uuid4

        for endpoint in ("/api/v1/analytics/pulls/repeated", "/api/v1/analytics/pulls/compare"):
            response = await client.post(endpoint, json={"pull_ids": [str(uuid4()), str(uuid4())]})
            assert response.status_code == 404
            assert response.json()["error"]["request_id"]


async def test_expired_acquisition_releases_capacity_without_accepting_its_token(url: str) -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from vehicle_platform.acquisition.service import AcquisitionError, AcquisitionService
    from vehicle_platform.api.domain_contracts import AcquisitionCreate
    from vehicle_platform.infrastructure.database import Database

    settings = Settings(database_url=url, environment="test")
    app = create_app(settings)
    database = Database(settings)
    vehicle_id = uuid4()
    try:
        async with database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO vehicles(id,manufacturer,model) VALUES(:id,'fixture','capacity')"
                ),
                {"id": vehicle_id},
            )
            await db.commit()
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            service = AcquisitionService(database, settings, app.state.telemetry)
            payload = AcquisitionCreate(
                vehicle_id=vehicle_id,
                recipe_key="general-health",
                adapter="synthetic",
                source_id="disposable-capacity-fixture",
            )
            acquisitions = [await service.create(payload) for _ in range(10)]
            with pytest.raises(AcquisitionError, match="concurrent acquisition session limit"):
                await service.create(payload)
            async with database.session() as db:
                await db.execute(
                    text(
                        "UPDATE acquisition_sessions "
                        "SET token_expires_at=now()-interval '1 second' "
                        "WHERE id=:id"
                    ),
                    {"id": acquisitions[0].id},
                )
                await db.commit()
            replacement = await service.create(payload)
            assert replacement.id not in {item.id for item in acquisitions}
            with pytest.raises(AcquisitionError, match="concurrent acquisition session limit"):
                await service.create(payload)
            rejected = await client.post(
                f"/api/v1/acquisitions/{acquisitions[0].id}/batches",
                headers={"authorization": f"Bearer {acquisitions[0].ingestion_token}"},
                json={
                    "schema_version": "1.0",
                    "batch_id": str(uuid4()),
                    "observations": [
                        {
                            "message_id": str(uuid4()),
                            "observed_at": datetime.now(UTC).isoformat(),
                            "signal": "engine.rpm",
                            "value": 900,
                            "unit": "rpm",
                            "source_record_id": "expired-record",
                        }
                    ],
                },
            )
            assert rejected.status_code == 401
            missing = await client.get(f"/api/v1/acquisitions/{uuid4()}/live")
            assert missing.status_code == 404
            assert missing.json()["error"]["request_id"]
            async with database.session() as db:
                assert (
                    await db.scalar(
                        text("SELECT sample_count FROM driving_sessions WHERE id=:id"),
                        {"id": acquisitions[0].driving_session_id},
                    )
                    == 0
                )
    finally:
        async with database.session() as db:
            await db.execute(
                text(
                    "UPDATE acquisition_sessions SET state='failed' "
                    "WHERE driving_session_id IN "
                    "(SELECT id FROM driving_sessions WHERE vehicle_id=:id)"
                ),
                {"id": vehicle_id},
            )
            await db.commit()
        await database.close()
