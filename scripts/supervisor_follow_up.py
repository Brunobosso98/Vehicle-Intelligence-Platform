"""Controlled finalized Phase 4 provenance plus canonical import, analysis and new grounded run."""

import asyncio
from datetime import UTC, datetime

from evaluate_investigation import finalized_fixture
from supervisor_fixtures import recording_csv
from vehicle_platform.events.synthetic import anomaly_scenario


async def follow_up(
    url, api, stack, fixture, original, plan, score, counters, execution_score
):
    vehicle = fixture["vehicle"]
    base = f"/api/v1/vehicles/{vehicle}/investigations"
    headers = {"X-Investigation-Token": stack["token"]}
    before = (
        await api.get(f"/api/v1/vehicles/{vehicle}/agent-runs/{original['id']}")
    ).json()
    assert plan["recipe"] is not None and plan["status"] == "AWAITING_APPROVAL", plan
    denied = await api.post(
        f"{base}/{plan['id']}/approve",
        json={
            "version": plan["version"],
            "recipe_hash": plan["recipe"]["configuration_hash"],
        },
    )
    assert denied.status_code == 401
    response = await api.post(
        f"{base}/{plan['id']}/approve",
        headers=headers,
        json={
            "version": plan["version"],
            "recipe_hash": plan["recipe"]["configuration_hash"],
        },
    )
    assert response.status_code == 200, response.text
    ready = response.json()
    assert ready["status"] == "ACQUISITION_READY"
    # Only this controlled golden creates finalized source provenance directly. Canonical
    # importer, Phase 2/3/5 analysis, official MCP and production reanalysis are unmodified.
    # Real collector/broker provenance is separately required by the Phase 7B browser gate.
    session = await finalized_fixture(
        url, vehicle, ready["configuration_id"], ready["source_id"], ready["recipe"]
    )
    csv = recording_csv(
        anomaly_scenario("followup-normal", ()), datetime.now(UTC), "followup"
    )
    for path, kwargs in (
        (
            f"/api/v1/sessions/{session}/imports/csv",
            {"files": {"file": ("followup.csv", csv, "text/csv")}},
        ),
        (f"/api/v1/sessions/{session}/analysis", {"json": {"profile": "generic-v1"}}),
        (f"/api/v1/sessions/{session}/events/analyze", {"json": {}}),
    ):
        response = await api.post(path, **kwargs)
        assert response.status_code in {200, 201}, response.text
    linked = await api.post(
        f"{base}/{plan['id']}/sessions",
        headers=headers,
        json={"version": ready["version"], "session_id": session},
    )
    assert linked.status_code == 200, linked.text
    current = linked.json()
    async with asyncio.timeout(95):
        while current["status"] == "REANALYZING":
            await asyncio.sleep(0.1)
            response = await api.get(f"{base}/{plan['id']}", headers=headers)
            response.raise_for_status()
            current = response.json()
    assert current["status"] in {"COMPLETED", "INCONCLUSIVE"}, current
    assert current["reanalysis_run_id"] != original["id"]
    run_base = f"/api/v1/vehicles/{vehicle}/agent-runs"
    refreshed = (await api.get(f"{run_base}/{current['reanalysis_run_id']}")).json()
    assert refreshed["status"] == "completed", refreshed
    assert refreshed["supervisor"]["routing"]["selected"] == ["performance", "thermal"]
    assert not refreshed["supervisor"]["conflicts"]
    assert all(e["run_id"] == refreshed["id"] for e in refreshed["evidence"])
    assert {e["id"] for e in original["evidence"]}.isdisjoint(
        e["id"] for e in refreshed["evidence"]
    )
    assert session in {e["session_id"] for e in refreshed["evidence"]}
    score(refreshed, counters)
    audit = (await api.get(f"{run_base}/{refreshed['id']}/audit")).json()
    events = (await api.get(f"{run_base}/{refreshed['id']}/events")).json()
    execution_score(refreshed, audit, events, counters)
    after = (await api.get(f"{run_base}/{original['id']}")).json()
    assert after == before, "Follow-up mutated historical AgentRun"
    assert (
        current["cycle_count"] == 1
        and current["outcome"]["classification"] != "CONFIRMED_MECHANICAL_CAUSE"
    )
    return {
        "name": "phase7b_linked_followup",
        "passed": True,
        "selected": refreshed["supervisor"]["routing"]["selected"],
        "source_run": original["id"],
        "new_run": refreshed["id"],
        "new_session": session,
    }
