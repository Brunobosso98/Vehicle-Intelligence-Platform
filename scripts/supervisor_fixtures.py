"""Independent controlled Phase 7C recordings through canonical import/analysis/event APIs."""

from datetime import datetime, timedelta
from typing import Any

import httpx
from agent_fixtures import seed_agent
from vehicle_platform.core.config import Settings
from vehicle_platform.events.synthetic import AnomalyInjection, anomaly_scenario
from vehicle_platform.main import create_app


def recording_csv(scenario, start: datetime, name: str) -> str:
    """Ten Hz independent canonical inputs; no signals or proprietary channels are invented."""
    shift = start - scenario.frames[0].observed_at
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
    lines = ["timestamp,signal,value,unit,record_id,sequence"]
    for index, frame in enumerate(scenario.frames):
        # Ten recorded frames per second avoids assuming an undersampled general-health
        # recipe is a true dropout. Raw inputs remain controlled, not simulated N55 data.
        for subdivision in range(10):
            timestamp = frame.observed_at + shift + timedelta(seconds=subdivision / 10)
            for signal, raw in frame.values.items():
                if raw is None:
                    continue
                value = raw
                if (frame.values.get("engine.throttle_position") or 0) >= 70:
                    if signal == "engine.rpm":
                        value += subdivision * 50
                    elif signal == "vehicle.speed":
                        value += subdivision * 0.2
                        if name == "consensus":
                            pull_index = int(
                                (
                                    frame.observed_at - scenario.frames[0].observed_at
                                ).total_seconds()
                                // 10
                            )
                            value = 18 + (value - 18) * 0.95**pull_index
                lines.append(
                    f"{timestamp.isoformat()},{signal},{value},{units[signal]},"
                    f"{name}:{index}:{subdivision}:{signal},"
                )
    return "\n".join(lines)


async def seed_supervisor(url: str) -> dict[str, Any]:
    fixture = await seed_agent(url)
    comparison = await seed_agent(url)
    fixture["comparison_vehicle"] = comparison["vehicle"]
    app = create_app(Settings(database_url=url, environment="test"))
    recordings: dict[str, str] = {}
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://fixture"
        ) as api,
    ):
        for offset, (name, injections) in enumerate(
            (
                ("normal", ()),
                ("thermal", (AnomalyInjection("iat_rise", 2),)),
                ("consensus", (AnomalyInjection("iat_rise", 2),)),
                (
                    "mixed",
                    (
                        AnomalyInjection("iat_rise", 2),
                        AnomalyInjection("fuel_pressure_drop", 1),
                    ),
                ),
                ("poor", (AnomalyInjection("sensor_dropout"),)),
            )
        ):
            scenario = anomaly_scenario("phase7c-" + name, injections)
            offset = {"poor": 0, "thermal": 1, "mixed": 2, "consensus": 2, "normal": 3}[
                name
            ]
            start = datetime.fromisoformat(fixture["as_of"]) + timedelta(days=offset)
            response = await api.post(
                "/api/v1/sessions",
                json={
                    "vehicle_id": fixture["vehicle"],
                    "configuration_id": fixture["configurations"][1],
                    "source_type": "csv",
                    "started_at": start.isoformat(),
                },
            )
            assert response.status_code == 201, response.text
            session = response.json()["id"]
            csv = recording_csv(scenario, start, name)
            for path, kwargs in (
                (
                    f"/api/v1/sessions/{session}/imports/csv",
                    {
                        "files": {"file": ("phase7c.csv", csv, "text/csv")},
                    },
                ),
                (
                    f"/api/v1/sessions/{session}/analysis",
                    {"json": {"profile": "generic-v1"}},
                ),
                (f"/api/v1/sessions/{session}/events/analyze", {"json": {}}),
            ):
                response = await api.post(path, **kwargs)
                assert response.status_code in {200, 201}, (path, response.text)
            recordings[name] = session
    return fixture | {"recordings": recordings}
