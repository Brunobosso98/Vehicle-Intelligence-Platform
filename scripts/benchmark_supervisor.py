"""Deterministic HTTP/MCP supervisor measurements; no real-model latency or cost claim."""

import asyncio
import json
import os
from pathlib import Path
from time import perf_counter

import httpx
from agent_runtime import runtime
from supervisor_fixtures import seed_supervisor


async def main():
    url = os.environ["TEST_DATABASE_URL"]
    specialist_timeout_seconds = float(
        os.environ.get("VIP_AGENT_SPECIALIST_TIMEOUT", "25")
    )
    fixture = await seed_supervisor(url)
    measurements = []
    async with (
        runtime(url) as stack,
        httpx.AsyncClient(base_url=stack["api"], timeout=100, trust_env=False) as api,
    ):

        async def measured(name, question, session, vehicle=None):
            vehicle = vehicle or fixture["vehicle"]
            base = f"/api/v1/vehicles/{vehicle}/agent-runs"
            started = perf_counter()
            response = await api.post(
                base, json={"question": question, "session_id": session}
            )
            assert response.status_code == 202, response.text
            identifier = response.json()["id"]
            stream = await api.get(f"{base}/{identifier}/stream")
            response = await api.get(f"{base}/{identifier}")
            response.raise_for_status()
            run = response.json()
            assert run["status"] == "completed", (name, run["error_category"])
            report = run["supervisor"]
            assert all(
                e["run_id"] == identifier and e["vehicle_id"] == vehicle
                for e in run["evidence"]
            )
            rss = []
            for process in stack["processes"]:
                status = Path(f"/proc/{process.child.pid}/status").read_text()
                rss.append(
                    int(
                        next(
                            line.split()[1]
                            for line in status.splitlines()
                            if line.startswith("VmRSS:")
                        )
                    )
                )
            result = {
                "name": name,
                "elapsed_seconds": perf_counter() - started,
                "routing_seconds": report["routing_seconds"],
                "specialist_seconds": {
                    r["specialist"]: r["duration_seconds"]
                    for r in report["specialists"]
                },
                "selected": report["routing"]["selected"],
                "mcp_calls": run["tool_call_count"],
                "cache_hits": report["cache_hits"],
                "result_bytes": len(response.content),
                "stream_bytes": len(stream.content),
                "process_rss_kib": rss,
                "sufficiency": report["sufficiency"],
                "run_id": identifier,
                "evidence_ids": {e["id"] for e in run["evidence"]},
            }
            assert result["result_bytes"] < 1048576 and result["mcp_calls"] <= 32
            assert (
                run["usage"]["total_tokens"] == 0
                and run["usage"]["estimated_cost"] is None
            )
            if name == "conflict_escalation":
                proposed = await api.post(
                    f"/api/v1/vehicles/{vehicle}/investigations",
                    headers={"X-Investigation-Token": stack["token"]},
                    json={
                        "agent_run_id": identifier,
                        "adapter": "synthetic",
                        "source_id": "supervisor-benchmark",
                    },
                )
                assert proposed.status_code == 201, proposed.text
                result["investigation_id"] = proposed.json()["id"]
            return result

        for name, question, recording in (
            ("zero", "What was my last session?", "normal"),
            ("one", "Did the last three pulls get slower?", "normal"),
            (
                "two_parallel",
                "Why did performance degrade after repeated pulls?",
                "thermal",
            ),
            ("three", "Why did performance degrade after repeated pulls?", "mixed"),
            (
                "conflict_escalation",
                "Why did performance degrade after repeated pulls?",
                "mixed",
            ),
        ):
            measurements.append(
                await measured(name, question, fixture["recordings"][recording])
            )
        concurrent = await asyncio.gather(
            *(
                measured(
                    f"concurrent_{i}",
                    "Why did performance degrade after repeated pulls?",
                    fixture["recordings"]["thermal"],
                )
                for i in range(3)
            ),
            measured(
                "other_vehicle",
                "What was my last session?",
                None,
                fixture["other_vehicle"],
            ),
        )
        for i, left in enumerate(concurrent):
            for right in concurrent[i + 1 :]:
                assert (
                    left["run_id"] != right["run_id"]
                    and not left["evidence_ids"] & right["evidence_ids"]
                )
        measurements.extend(concurrent)
    for item in measurements:
        del item["evidence_ids"]
    print(
        json.dumps(
            {
                "supervisor_benchmark": "PASS",
                "provider": "deterministic",
                "concurrent_runs": 4,
                "specialist_timeout_seconds": specialist_timeout_seconds,
                "memory_method": "Linux /proc/PID/status VmRSS snapshot for API and MCP, not peak or per-request allocation",
                "real_model_latency_measured": False,
                "real_cost": None,
                "measurements": measurements,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
