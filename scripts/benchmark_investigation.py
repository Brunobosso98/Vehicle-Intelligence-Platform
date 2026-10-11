"""Measure deterministic Phase 7B HTTP workflows on a disposable real stack."""

import asyncio
import json
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx
from agent_fixtures import seed_agent
from agent_runtime import ask, runtime
from evaluate_investigation import finalized_fixture
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed_agent(url)
    engine = create_async_engine(url)
    measurements: list[dict[str, object]] = []
    try:
        async with (
            runtime(url) as stack,
            httpx.AsyncClient(
                base_url=stack["api"], timeout=100, trust_env=False
            ) as api,
        ):
            vehicle = fixture["vehicle"]
            base = f"/api/v1/vehicles/{vehicle}/investigations"
            headers = {"X-Investigation-Token": stack["token"]}

            async def db_counters() -> dict[str, int]:
                async with engine.connect() as connection:
                    row = (
                        (
                            await connection.execute(
                                text(
                                    "SELECT xact_commit,xact_rollback,tup_fetched FROM pg_stat_database "
                                    "WHERE datname=current_database()"
                                )
                            )
                        )
                        .mappings()
                        .one()
                    )
                    return {key: int(row[key]) for key in row}

            async def rss() -> list[int]:
                values = []
                for process in stack["processes"]:
                    assert process.child is not None
                    status = await asyncio.to_thread(
                        Path(f"/proc/{process.child.pid}/status").read_text
                    )
                    values.append(
                        int(
                            next(
                                line.split()[1]
                                for line in status.splitlines()
                                if line.startswith("VmRSS:")
                            )
                        )
                    )
                return values

            beginning = await db_counters()
            sufficient = await ask(
                api, vehicle, "A IAT piorou nas puxadas consecutivas?"
            )
            started = perf_counter()
            response = await api.post(
                base,
                headers=headers,
                json={
                    "agent_run_id": sufficient["id"],
                    "adapter": "synthetic",
                    "source_id": "benchmark",
                },
            )
            elapsed = perf_counter() - started
            assert response.status_code in {409, 422}, response.text
            measurements.append(
                {
                    "scenario": "existing_evidence_sufficient",
                    "seconds": elapsed,
                    "status": response.status_code,
                    "result_bytes": len(response.content),
                }
            )

            insufficient = await ask(
                api, vehicle, "Why did the third pull get slower with timing missing?"
            )
            started = perf_counter()
            response = await api.post(
                base,
                headers=headers,
                json={
                    "agent_run_id": insufficient["id"],
                    "adapter": "synthetic",
                    "source_id": "benchmark",
                },
            )
            elapsed = perf_counter() - started
            assert response.status_code == 201, response.text
            plan = response.json()
            assert len(plan["hypotheses"]) == 3
            assert plan["recipe"]["configuration_hash"]
            api_process = stack["processes"][1].child
            assert api_process is not None
            api_log = Path(f"/proc/{api_process.pid}/fd/1").read_text()
            events = [
                json.loads(line)
                for line in api_log.splitlines()
                if line.startswith('{"timestamp"')
            ]
            planning = next(
                event
                for event in events
                if event.get("event") == "investigation.planning.completed"
                and event.get("agent_run_id") == insufficient["id"]
            )
            existing = next(
                event
                for event in events
                if event.get("event") == "investigation.existing_evidence.completed"
                and event.get("agent_run_id") == insufficient["id"]
            )
            recipe = next(
                event
                for event in events
                if event.get("event") == "investigation.recipe_generation.completed"
                and event.get("investigation_id") == plan["id"]
            )
            measurements.append(
                {
                    "scenario": "three_hypotheses_capability_recipe",
                    "seconds": elapsed,
                    "planner_calls": 1,
                    "planning_seconds": planning["planning_seconds"],
                    "existing_search_mcp_calls": existing["mcp_calls"],
                    "recipe_generation_seconds": recipe["recipe_generation_seconds"],
                    "hypotheses": len(plan["hypotheses"]),
                    "gaps": len(plan["gaps"]),
                    "signals": len(plan["signal_needs"]),
                    "result_bytes": len(response.content),
                }
            )

            approved = await api.post(
                f"{base}/{plan['id']}/approve",
                headers=headers,
                json={
                    "version": plan["version"],
                    "recipe_hash": plan["recipe"]["configuration_hash"],
                },
            )
            assert approved.status_code == 200, approved.text
            ready = approved.json()
            session_id = await finalized_fixture(
                url, vehicle, fixture["configurations"][1], "benchmark", ready["recipe"]
            )
            started = perf_counter()
            linked = await api.post(
                f"{base}/{plan['id']}/sessions",
                headers=headers,
                json={"version": ready["version"], "session_id": session_id},
            )
            assert linked.status_code == 200, linked.text
            for _ in range(100):
                current = await api.get(f"{base}/{plan['id']}", headers=headers)
                assert current.status_code == 200
                if current.json()["status"] in {"COMPLETED", "INCONCLUSIVE", "FAILED"}:
                    break
                await asyncio.sleep(0.2)
            elapsed = perf_counter() - started
            final = current.json()
            assert final["status"] in {"COMPLETED", "INCONCLUSIVE"}, final
            followup_id = final["reanalysis_run_id"]
            audit = await api.get(
                f"/api/v1/vehicles/{vehicle}/agent-runs/{followup_id}/audit"
            )
            assert audit.status_code == 200
            tool_calls = audit.json()["tool_calls"]
            measurements.append(
                {
                    "scenario": "linked_session_reanalysis",
                    "seconds": elapsed,
                    "mcp_calls": len(tool_calls),
                    "mcp_seconds": sum(call["duration_seconds"] for call in tool_calls),
                    "result_bytes": len(current.content),
                }
            )

            async def create_on_vehicle(other_vehicle: str) -> tuple[int, float]:
                run = await ask(
                    api,
                    other_vehicle,
                    "Why did the third pull get slower with timing missing?",
                )
                started = perf_counter()
                result = await api.post(
                    f"/api/v1/vehicles/{other_vehicle}/investigations",
                    headers=headers,
                    json={
                        "agent_run_id": run["id"],
                        "adapter": "synthetic",
                        "source_id": f"benchmark-{uuid4().hex[:8]}",
                    },
                )
                return result.status_code, perf_counter() - started

            concurrent = await asyncio.gather(
                create_on_vehicle(vehicle),
                create_on_vehicle(fixture["other_vehicle"]),
            )
            assert all(status == 201 for status, _ in concurrent), concurrent
            measurements.append(
                {
                    "scenario": "concurrent_investigations",
                    "count": len(concurrent),
                    "seconds_each": [duration for _, duration in concurrent],
                }
            )
            await asyncio.sleep(
                1.1
            )  # PostgreSQL publishes aggregate counters asynchronously.
            ending = await db_counters()
            print(
                json.dumps(
                    {
                        "investigation_benchmark": "PASS",
                        "provider": "deterministic",
                        "measurements": measurements,
                        "process_rss_kib": await rss(),
                        "database_counter_deltas": {
                            key: ending[key] - beginning[key] for key in beginning
                        },
                        "database_counter_scope": "disposable DB aggregate, includes background activity",
                        "planning_and_recipe_scope": "API monotonic spans inside the plan POST; deterministic provider only",
                        "database_calls_scope": "exact per-request SQL count unavailable; aggregate transaction and tuple counters reported",
                        "memory_scope": "current process RSS at end, not peak or allocated bytes",
                        "external_llm_latency_measured": False,
                    },
                    indent=2,
                )
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
