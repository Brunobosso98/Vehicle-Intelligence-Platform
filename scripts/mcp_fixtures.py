"""Controlled fixtures built through existing application routes in a disposable DB."""

from datetime import timedelta
from typing import Any

import httpx
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from vehicle_platform.core.config import Settings
from vehicle_platform.events.synthetic import AnomalyInjection, anomaly_scenario
from vehicle_platform.main import create_app


async def seed(
    url: str,
    *,
    sample_hz: int = 5,
    omit_signals: frozenset[str] = frozenset(),
    include_other_vehicle_sessions: bool = False,
) -> dict[str, Any]:
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError("MCP validation requires a disposable vehicle_test* database")
    if sample_hz not in {5, 10}:
        raise ValueError("Fixture sampling must be 5 or 10 Hz")
    app = create_app(Settings(database_url=SecretStr(url), environment="test"))
    scenario = anomaly_scenario("phase6", (AnomalyInjection("boost_drop", 1),))
    fixture: dict[str, Any] = {"sessions": [], "pulls": [], "configurations": []}
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://fixture"
        ) as client,
    ):

        async def post(path: str, **kwargs: Any) -> Any:
            response = await client.post(path, **kwargs)
            if response.status_code not in {200, 201}:
                raise AssertionError((path, response.text))
            return response.json()

        vehicle = await post(
            "/api/v1/vehicles", json={"manufacturer": "fixture", "model": "phase6"}
        )
        other = await post(
            "/api/v1/vehicles", json={"manufacturer": "fixture", "model": "isolated"}
        )
        fixture["vehicle"] = vehicle["id"]
        fixture["other_vehicle"] = other["id"]
        for name in ("A", "B", "empty"):
            configuration = await post(
                f"/api/v1/vehicles/{vehicle['id']}/configurations",
                json={
                    "effective_at": "2020-01-01T00:00:00Z",
                    "description": name,
                    "provenance": "phase6-disposable-fixture",
                },
            )
            fixture["configurations"].append(configuration["id"])
        for index in range(6):
            config = fixture["configurations"][index // 3]
            shift = timedelta(days=index)
            session = await post(
                "/api/v1/sessions",
                json={
                    "vehicle_id": vehicle["id"],
                    "configuration_id": config,
                    "source_type": "csv",
                    "started_at": (scenario.frames[0].observed_at + shift).isoformat(),
                },
            )
            lines = ["timestamp,signal,value,unit,record_id,sequence"]
            units = {
                "engine.rpm": "rpm",
                "vehicle.speed": "m/s",
                "engine.throttle_position": "%",
                "engine.boost_pressure": "Pa",
                "engine.intake_air_temperature": "K",
                "engine.oil_temperature": "K",
                "engine.coolant_temperature": "K",
                "fuel.high_pressure": "Pa",
            }
            for n, frame in enumerate(scenario.frames):
                for subdivision in range(sample_hz):
                    at = (
                        frame.observed_at
                        + shift
                        + timedelta(seconds=subdivision / sample_hz)
                    )
                    for signal, raw_value in frame.values.items():
                        if raw_value is not None and signal not in omit_signals:
                            value = raw_value
                            if sample_hz == 10 and signal in {
                                "engine.boost_pressure",
                                "fuel.high_pressure",
                            }:
                                # The higher-rate knowledge fixture models a varying sensor,
                                # retaining the boost drop without creating a frozen-signal event.
                                value += subdivision * 250
                            if (
                                frame.values.get("engine.throttle_position") or 0
                            ) >= 70:
                                if signal == "engine.rpm":
                                    value += subdivision * 500 / sample_hz
                                elif signal == "vehicle.speed":
                                    value += subdivision * 2 / sample_hz
                            lines.append(
                                f"{at.isoformat()},{signal},{value},{units[signal]},"
                                f"{n}:{subdivision}:{signal},"
                            )
            imported = await post(
                f"/api/v1/sessions/{session['id']}/imports/csv",
                files={"file": ("phase6.csv", "\n".join(lines), "text/csv")},
            )
            analyzed = await post(
                f"/api/v1/sessions/{session['id']}/analysis",
                json={"profile": "generic-v1"},
            )
            if analyzed["pull_count"] != 3:
                raise AssertionError("fixture_analysis_pull_count_mismatch")
            await post(f"/api/v1/sessions/{session['id']}/events/analyze", json={})
            pulls = (await client.get(f"/api/v1/sessions/{session['id']}/pulls")).json()
            fixture["sessions"].append(session["id"])
            fixture["pulls"].append([p["id"] for p in pulls])
            if index == 0:
                fixture["observation_count"] = imported["accepted"]
                fixture["start"] = scenario.frames[0].observed_at.isoformat()
                fixture["end"] = (
                    scenario.frames[-1].observed_at + timedelta(seconds=1)
                ).isoformat()
                events = (
                    await client.get(f"/api/v1/sessions/{session['id']}/events")
                ).json()
                fixture["event"] = next(
                    e["id"] for e in events if e["event_type"] == "boost_drop"
                )
        if include_other_vehicle_sessions:
            other_configuration = await post(
                f"/api/v1/vehicles/{fixture['other_vehicle']}/configurations",
                json={
                    "effective_at": "2020-01-01T00:00:00Z",
                    "description": "isolated concurrent B58 fixture",
                    "provenance": "phase11-disposable-fixture",
                },
            )
            fixture["other_configuration"] = other_configuration["id"]
            for index in range(2):
                session = await post(
                    "/api/v1/sessions",
                    json={
                        "vehicle_id": fixture["other_vehicle"],
                        "configuration_id": other_configuration["id"],
                        "source_type": "csv",
                        "started_at": (
                            scenario.frames[0].observed_at + timedelta(days=20 + index)
                        ).isoformat(),
                    },
                )
                fixture.setdefault("other_sessions", []).append(session["id"])
    return fixture


async def fingerprint(url: str) -> dict[str, int]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            result = {}
            for table in (
                "vehicles",
                "driving_sessions",
                "telemetry_samples",
                "pulls",
                "detected_events",
                "analytics_runs",
                "dataset_capability_reports",
            ):
                result[table] = int(
                    await connection.scalar(text(f"SELECT count(*) FROM {table}"))
                )
            return result
    finally:
        await engine.dispose()
