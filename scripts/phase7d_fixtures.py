"""Canonical Phase 7D fixtures, including the explicitly insufficient G06 history."""

from datetime import UTC, datetime, timedelta

import httpx
from supervisor_fixtures import recording_csv, seed_supervisor
from vehicle_platform.core.config import Settings
from vehicle_platform.events.synthetic import anomaly_scenario
from vehicle_platform.main import create_app


async def seed_phase7d(url):
    fixture = await seed_supervisor(url)
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError("Disposable fixture database required")
    app = create_app(Settings(database_url=url, environment="test"))
    boundary = datetime(2020, 1, 3, tzinfo=UTC)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://controlled-fixture"
        ) as api,
    ):

        async def post(path, **kwargs):
            response = await api.post(path, **kwargs)
            if response.status_code not in {200, 201}:
                raise ValueError("Canonical fixture creation failed")
            return response.json()

        vehicle = await post(
            "/api/v1/vehicles",
            json={"manufacturer": "fixture", "model": "phase7d-sparse-history"},
        )
        configurations = []
        for index in range(2):
            configuration = await post(
                f"/api/v1/vehicles/{vehicle['id']}/configurations",
                json={
                    "effective_at": (
                        boundary + timedelta(days=-2 if index == 0 else 0)
                    ).isoformat(),
                    "ended_at": boundary.isoformat() if index == 0 else None,
                    "description": "controlled-before"
                    if index == 0
                    else "controlled-after",
                    "provenance": "phase7d-canonical-v1",
                },
            )
            configurations.append(configuration["id"])
        await post(
            f"/api/v1/vehicles/{vehicle['id']}/modifications",
            json={
                "configuration_id": configurations[1],
                "category": "intake",
                "product": "controlled intercooler",
                "installed_at": boundary.isoformat(),
                "notes": "Controlled temporal boundary; no causal ground truth.",
            },
        )
        sessions = []
        scenario = anomaly_scenario("phase7d-sparse", ())
        for index, configuration in enumerate(configurations):
            start = boundary + timedelta(days=-1 if index == 0 else 1)
            session = await post(
                "/api/v1/sessions",
                json={
                    "vehicle_id": vehicle["id"],
                    "configuration_id": configuration,
                    "source_type": "csv",
                    "started_at": start.isoformat(),
                },
            )
            await post(
                f"/api/v1/sessions/{session['id']}/imports/csv",
                files={
                    "file": (
                        "controlled.csv",
                        recording_csv(scenario, start, "normal"),
                        "text/csv",
                    )
                },
            )
            await post(
                f"/api/v1/sessions/{session['id']}/analysis",
                json={"profile": "generic-v1"},
            )
            await post(f"/api/v1/sessions/{session['id']}/events/analyze", json={})
            sessions.append(session["id"])
    fixture["sparse_comparison_vehicle"] = vehicle["id"]
    fixture["sparse_comparison_configurations"] = configurations
    fixture["sparse_comparison_sessions"] = sessions
    return fixture


def vehicle_for(fixture, case):
    if case.fixture == "comparison":
        return fixture["comparison_vehicle"]
    if case.fixture == "sparse_comparison":
        return fixture["sparse_comparison_vehicle"]
    return fixture["vehicle"]
