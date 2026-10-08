"""Deterministic HTTP agent resource measurements; these do not measure LLM latency."""

import asyncio
import json
import os
from pathlib import Path
from time import perf_counter

import httpx
from agent_fixtures import seed_agent
from agent_runtime import ask, runtime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed_agent(url)
    engine = create_async_engine(url)

    async def database_stats():
        async with engine.connect() as db:
            return dict(
                (
                    await db.execute(
                        text(
                            "SELECT xact_commit,xact_rollback,tup_fetched FROM pg_stat_database "
                            "WHERE datname=current_database()"
                        )
                    )
                )
                .mappings()
                .one()
            )

    reports = []
    try:
        async with (
            runtime(url) as stack,
            httpx.AsyncClient(
                base_url=stack["api"],
                timeout=100,
                trust_env=False,
            ) as api,
        ):
            start_stats = await database_stats()
            for name, question in (
                ("simple_context_lookup", "Qual foi minha última sessão?"),
                ("one_analytic_tool", "Qual o sinal indisponível de timing?"),
                ("multi_tool", "Como foram as últimas puxadas?"),
                (
                    "evidence_heavy",
                    "O comportamento mudou depois da configuração nova?",
                ),
            ):
                started = perf_counter()
                run = await ask(api, fixture["vehicle"], question)
                elapsed = perf_counter() - started
                assert run["status"] == "completed", (name, run["error_category"])
                path = f"/api/v1/vehicles/{fixture['vehicle']}/agent-runs/{run['id']}"
                calls = (await api.get(path + "/audit")).json()["tool_calls"]
                mcp_seconds = sum(c["duration_seconds"] for c in calls)
                public = {k: v for k, v in run.items() if k != "stream"}
                event_bytes = len(run["stream"].encode())
                result_bytes = len(json.dumps(public).encode())
                assert (
                    len(calls) <= 32
                    and result_bytes < 1048576
                    and event_bytes < 1048576
                )
                rss = []
                for process in stack["processes"]:
                    status = await asyncio.to_thread(
                        Path(f"/proc/{process.child.pid}/status").read_text
                    )
                    rss.append(
                        int(
                            next(
                                line.split()[1]
                                for line in status.splitlines()
                                if line.startswith("VmRSS:")
                            )
                        )
                    )
                reports.append(
                    {
                        "scenario": name,
                        "end_to_end_seconds": elapsed,
                        "mcp_seconds": mcp_seconds,
                        "non_mcp_elapsed_seconds": max(0, elapsed - mcp_seconds),
                        "tool_count": len(calls),
                        "event_bytes": event_bytes,
                        "result_bytes": result_bytes,
                        "process_rss_kib": rss,
                    }
                )
            path = f"/api/v1/vehicles/{fixture['vehicle']}/agent-runs"
            responses = await asyncio.gather(
                *(
                    api.post(path, json={"question": "Como foram as últimas puxadas?"})
                    for _ in range(4)
                )
            )
            assert all(response.status_code == 202 for response in responses)
            overflow = await api.post(path, json={"question": "IAT?"})
            assert overflow.status_code == 429, overflow.text
            identifiers = [response.json()["id"] for response in responses]
            await asyncio.gather(
                *(api.get(f"{path}/{identifier}/stream") for identifier in identifiers)
            )
            for identifier in identifiers:
                run = (await api.get(f"{path}/{identifier}")).json()
                assert run["status"] == "completed"
                assert all(
                    e["run_id"] == identifier and e["vehicle_id"] == fixture["vehicle"]
                    for e in run["evidence"]
                )
            # PostgreSQL publishes these cumulative counters asynchronously; background work is included.
            await asyncio.sleep(1.1)
            end_stats = await database_stats()
            print(
                json.dumps(
                    {
                        "agent_benchmark": "PASS",
                        "provider": "deterministic",
                        "measurements": reports,
                        "concurrent_runs": 4,
                        "overflow_status": 429,
                        "database_counter_deltas": {
                            key: end_stats[key] - start_stats[key]
                            for key in start_stats
                        },
                        "database_counter_scope": "disposable DB aggregate, including background activity",
                        "overhead_scope": "elapsed minus MCP calls; includes API, persistence and stream polling",
                        "simple_lookup_note": "mandatory context uses five reads; one_analytic_tool adds one summary",
                        "llm_latency_measured": False,
                    },
                    indent=2,
                )
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
