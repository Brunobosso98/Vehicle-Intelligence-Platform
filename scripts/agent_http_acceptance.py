"""Actual HTTP MCP/API streaming, cancellation, dependency failure and reconnect gate."""

import asyncio
import json
import os
from time import perf_counter

import httpx
from agent_fixtures import seed_agent
from agent_runtime import ask, runtime


async def main() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed_agent(url)
    async with (
        runtime(url) as stack,
        httpx.AsyncClient(base_url=stack["api"], timeout=100, trust_env=False) as api,
    ):
        first = await ask(
            api, fixture["vehicle"], "A IAT piorou nas puxadas consecutivas?"
        )
        assert first["status"] == "completed" and first["result"]["evidence"]
        assert all(
            "event: " + kind in first["stream"]
            for kind in (
                "run_started",
                "context_resolved",
                "tool_started",
                "tool_completed",
                "evidence_added",
                "answer_chunk",
                "run_completed",
            )
        )
        path = f"/api/v1/vehicles/{fixture['vehicle']}/agent-runs"
        created = await api.post(
            path,
            json={"question": "O comportamento mudou depois da configuração nova?"},
        )
        identifier = created.json()["id"]
        async with api.stream("GET", f"{path}/{identifier}/stream") as stream:
            async for line in stream.aiter_lines():
                if line.startswith("id: "):
                    cursor = int(line.split(": ", 1)[1])
                    break
        cancelled = await api.post(f"{path}/{identifier}/cancel")
        assert (
            cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
        )
        replay = await api.get(f"{path}/{identifier}/stream?after={cursor}")
        assert (
            "event: run_cancelled" in replay.text
            and "event: run_started" not in replay.text
        )
        assert (await api.get(f"{path}/{identifier}")).json()["result"] is None
        await stack["mcp"].stop()
        started = perf_counter()
        failed = await ask(api, fixture["vehicle"], "Qual foi minha última sessão?")
        assert failed["status"] == "failed" and failed["result"] is None
        assert perf_counter() - started < 95
        assert "event: run_failed" in failed["stream"]
        assert failed["error_category"] in {
            "dependency_unavailable",
            "mcp_unavailable",
            "run_timeout",
        }
        await stack["mcp"].start()
        recovered = await ask(api, fixture["vehicle"], "Teve boost drop?")
        assert recovered["status"] == "completed"
        assert any(
            binding["value"] == "boost_drop"
            for finding in recovered["result"]["findings"]
            for binding in finding["bindings"]
        )
        project = os.environ["MCP_TEST_PROJECT"]
        assert project.startswith("vehicle-platform-mcp-tests-")

        async def database_command(*arguments):
            child = await asyncio.create_subprocess_exec(
                "docker",
                "compose",
                "-p",
                project,
                "-f",
                "infra/docker/compose.test.yaml",
                *arguments,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                async with asyncio.timeout(60):
                    assert await child.wait() == 0
            except BaseException:
                if child.returncode is None:
                    child.kill()
                    await child.wait()
                raise

        try:
            await database_command("pause", "db")
            started = perf_counter()
            unavailable = await api.post(
                path, json={"question": "Qual a última sessão?"}
            )
            assert unavailable.status_code == 503
            assert unavailable.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
            assert perf_counter() - started < 8
        finally:
            await database_command("unpause", "db")
        restored = await ask(api, fixture["vehicle"], "Qual foi minha última sessão?")
        assert restored["status"] == "completed" and restored["result"]["evidence"]
        for process in stack["processes"]:
            process.log.seek(0)
            assert stack["token"] not in process.log.read()
        print(
            json.dumps(
                {
                    "agent_http_acceptance": "PASS",
                    "disconnect_replay": True,
                    "cancellation": True,
                    "mcp_failure_recovery": True,
                    "database_failure_recovery": True,
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
