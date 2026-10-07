"""Representative MCP reads measured through the SDK against disposable canonical data."""

import asyncio
import json
import os
import statistics
import tracemalloc
from time import perf_counter

from mcp import Client
from mcp_fixtures import seed
from pydantic import SecretStr
from vehicle_platform.core.config import Settings
from vehicle_platform.mcp.adapter import Adapter
from vehicle_platform.mcp.config import MCPSettings
from vehicle_platform.mcp.database import ReadOnlyDatabase
from vehicle_platform.mcp.server import create_server
from vehicle_platform.observability.telemetry import Telemetry


async def main() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed(url)
    settings = Settings(database_url=SecretStr(url), environment="test")
    database = ReadOnlyDatabase(settings)
    telemetry = Telemetry(settings, database, service_name="vehicle-platform-mcp")
    latencies, sizes = [], []
    errors = 0
    try:
        async with Client(
            create_server(
                Adapter(database, settings, telemetry), telemetry, MCPSettings()
            )
        ) as client:
            operations = (
                (
                    "get_session_summary",
                    {
                        "vehicle_id": fixture["vehicle"],
                        "session_id": fixture["sessions"][0],
                    },
                ),
                (
                    "get_pull_summary",
                    {
                        "vehicle_id": fixture["vehicle"],
                        "pull_id": fixture["pulls"][0][0],
                    },
                ),
                (
                    "get_vehicle_baseline",
                    {
                        "vehicle_id": fixture["vehicle"],
                        "configuration_id": fixture["configurations"][0],
                    },
                ),
            )
            for name, arguments in operations:
                await client.call_tool(name, arguments)
            tracemalloc.start()
            started = perf_counter()
            for _ in range(10):
                for name, arguments in operations:
                    begin = perf_counter()
                    result = await client.call_tool(name, arguments)
                    latencies.append(perf_counter() - begin)
                    sizes.append(len(result.model_dump_json().encode()))
                    errors += int(result.is_error)
            concurrent = await asyncio.gather(
                *(
                    client.call_tool("get_vehicle", {"vehicle_id": fixture["vehicle"]})
                    for _ in range(4)
                )
            )
            errors += sum(int(result.is_error) for result in concurrent)
            elapsed = perf_counter() - started
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        ordered = sorted(latencies)
        count = len(latencies) + len(concurrent)
        report = {
            "requests": count,
            "successes": count - errors,
            "errors": errors,
            "latency_seconds": {
                "p50": statistics.median(ordered),
                "p95": ordered[int(len(ordered) * 0.95) - 1],
                "p99": ordered[-1],
            },
            "throughput_per_second": count / elapsed,
            "python_traced_memory_bytes": {"current": current, "peak": peak},
            "max_result_bytes": max(sizes),
            "max_active_concurrency": 4,
            "fixture": "six sessions / eighteen canonical pulls; SDK in-process, real database",
        }
        print(json.dumps(report))
        if errors or max(sizes) > 524288:
            raise SystemExit("MCP benchmark correctness/result bounds failed")
    finally:
        await database.close()
        telemetry.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
