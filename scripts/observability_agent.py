"""Prove agent HTTP→MCP→database trace continuity, exported metrics and redaction."""

import asyncio
import json
import os
import secrets
from pathlib import Path
from time import monotonic

import httpx
from agent_fixtures import seed_agent
from agent_runtime import ask

ARTIFACTS = Path(".validation/agent/observability")


async def main() -> None:
    fixture = await seed_agent(os.environ["TEST_DATABASE_URL"])
    project = os.environ["MCP_TEST_PROJECT"]
    assert project.startswith("vehicle-platform-mcp-tests-")
    token, sentinel = (
        secrets.token_urlsafe(48),
        "redaction-sentinel-" + secrets.token_urlsafe(24),
    )
    env = os.environ | {"VIP_MCP_TOKEN": token, "AGENT_REDACTION_SENTINEL": sentinel}
    compose = [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        "infra/docker/compose.test.yaml",
        "-f",
        "infra/docker/compose.mcp-test.yaml",
        "-f",
        "infra/docker/compose.agent-test.yaml",
    ]

    async def command(*args):
        child = await asyncio.create_subprocess_exec(
            *compose,
            *args,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        async with asyncio.timeout(180):
            output, errors = await child.communicate()
        assert child.returncode == 0, (
            errors.decode().replace(token, "[redacted]").replace(sentinel, "[redacted]")
        )
        return output.decode()

    async def address(service, port):
        mapped = (await command("port", service, str(port))).strip().rsplit(":", 1)[1]
        return f"http://127.0.0.1:{mapped}"

    try:
        await command(
            "up", "-d", "--no-build", "--wait", "agent-api", "prometheus", "tempo"
        )
        api_url, tempo_url, prom_url = (
            await address("agent-api", 8000),
            await address("tempo", 3200),
            await address("prometheus", 9090),
        )
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(
            base_url=api_url, timeout=100, trust_env=False
        ) as api:
            run = await ask(
                api, fixture["vehicle"], "Qual foi minha última sessão? " + sentinel
            )
            assert run["status"] == "completed", run["error_category"]
            assert sentinel not in json.dumps(run) and token not in json.dumps(run)
            path = f"/api/v1/vehicles/{fixture['other_vehicle']}/agent-runs"
            created = await api.post(
                path, json={"question": "IAT?", "session_id": fixture["latest_session"]}
            )
            failed_id = created.json()["id"]
            await api.get(f"{path}/{failed_id}/stream")
            failed = (await api.get(f"{path}/{failed_id}")).json()
            assert failed["status"] == "failed"
        async with httpx.AsyncClient(timeout=5, trust_env=False) as backend:
            for current in (run, failed):
                deadline = monotonic() + 60
                while monotonic() < deadline:
                    response = await backend.get(
                        f"{tempo_url}/api/traces/{current['trace_id']}"
                    )
                    if response.status_code == 200:
                        trace = response.json()
                        spans = [
                            s
                            for batch in trace.get("batches", [])
                            for scope in batch.get(
                                "scopeSpans",
                                batch.get("instrumentationLibrarySpans", []),
                            )
                            for s in scope["spans"]
                        ]
                        names = {s["name"] for s in spans}
                        expected = {
                            "agent.run",
                            "agent.context",
                            "agent.mcp_tool",
                            "mcp.request",
                            "mcp.tool",
                        }
                        if current["status"] == "completed":
                            expected |= {"agent.model_turn", "agent.grounding"}
                        if expected <= names and any(
                            a["key"] in {"db.system", "db.system.name"}
                            for s in spans
                            for a in s.get("attributes", [])
                        ):
                            encoded = json.dumps(trace)
                            assert token not in encoded and sentinel not in encoded
                            assert (
                                "db.statement" not in encoded
                                and "db.query.text" not in encoded
                            )
                            (ARTIFACTS / f"{current['status']}-trace.json").write_text(
                                encoded
                            )
                            break
                    await asyncio.sleep(1)
                else:
                    raise AssertionError("Agent/MCP/database spans did not reach Tempo")
            for metric in (
                "agent_runs_total",
                "agent_tool_calls_total",
                "agent_run_errors_total",
                "agent_tool_errors_total",
                "agent_run_duration_seconds_count",
            ):
                deadline = monotonic() + 60
                while monotonic() < deadline:
                    response = await backend.get(
                        prom_url + "/api/v1/query", params={"query": metric}
                    )
                    response.raise_for_status()
                    measured = response.json()
                    if measured["data"]["result"]:
                        encoded = json.dumps(measured)
                        assert sentinel not in encoded and token not in encoded
                        (ARTIFACTS / f"{metric}.json").write_text(encoded)
                        break
                    await asyncio.sleep(1)
                else:
                    raise AssertionError(
                        "Agent metrics did not reach Prometheus: " + metric
                    )
        logs = await command("logs", "--no-color", "agent-api", "mcp")
        assert sentinel not in logs and token not in logs
        assert "agent.run.completed" in logs and "mcp.call.completed" in logs
        (ARTIFACTS / "sanitized.log").write_text(logs)
        print(
            json.dumps(
                {
                    "agent_observability": "PASS",
                    "successful_and_failed_traces": True,
                    "mcp_trace_continuity": True,
                    "metrics_exported": True,
                    "redaction": True,
                }
            )
        )
    except BaseException:
        logs = await command(
            "logs",
            "--no-color",
            "tempo",
            "prometheus",
            "otel-collector",
            "agent-api",
            "mcp",
        )
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "failure.log").write_text(
            logs.replace(token, "[redacted]").replace(sentinel, "[redacted]")
        )
        raise
    finally:
        await command("down", "-v")


if __name__ == "__main__":
    asyncio.run(main())
