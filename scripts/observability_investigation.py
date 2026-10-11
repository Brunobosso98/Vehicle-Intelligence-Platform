"""Verify delivered Phase 7B metrics, trace spans and sanitized logs."""

import asyncio
import json
import os
import secrets
from pathlib import Path
from time import monotonic

import httpx
from agent_fixtures import seed_agent
from agent_runtime import ask

ARTIFACTS = Path(".validation/investigation/observability")


async def main() -> None:
    fixture = await seed_agent(os.environ["TEST_DATABASE_URL"])
    project = os.environ["MCP_TEST_PROJECT"]
    assert project.startswith("vehicle-platform-mcp-tests-")
    token = secrets.token_urlsafe(48)
    sentinel = "investigation-redaction-" + secrets.token_urlsafe(24)
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

    async def command(*args: str) -> str:
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

    async def address(service: str, port: int) -> str:
        mapped = (await command("port", service, str(port))).strip().rsplit(":", 1)[1]
        return f"http://127.0.0.1:{mapped}"

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    try:
        await command(
            "up", "-d", "--no-build", "--wait", "agent-api", "prometheus", "tempo"
        )
        api_url = await address("agent-api", 8000)
        tempo_url = await address("tempo", 3200)
        prom_url = await address("prometheus", 9090)
        async with httpx.AsyncClient(
            base_url=api_url, timeout=100, trust_env=False
        ) as api:
            run = await ask(
                api,
                fixture["vehicle"],
                "Why did the third pull get slower with timing missing?",
            )
            assert run["status"] == "completed" and sentinel not in json.dumps(run)
            path = f"/api/v1/vehicles/{fixture['vehicle']}/investigations"
            headers = {"X-Investigation-Token": token}
            created = await api.post(
                path,
                headers=headers,
                json={
                    "agent_run_id": run["id"],
                    "adapter": "synthetic",
                    "source_id": "observability-source",
                },
            )
            created.raise_for_status()
            plan = created.json()
            assert plan["status"] == "AWAITING_APPROVAL"
            approved = await api.post(
                f"{path}/{plan['id']}/approve",
                headers=headers,
                json={
                    "version": plan["version"],
                    "recipe_hash": plan["recipe"]["configuration_hash"],
                },
            )
            approved.raise_for_status()
            assert approved.json()["status"] == "ACQUISITION_READY"
            assert token not in approved.text and sentinel not in approved.text

        trace_id = ""
        async with httpx.AsyncClient(timeout=5, trust_env=False) as backend:
            deadline = monotonic() + 90
            while monotonic() < deadline:
                logs = await command("logs", "--no-color", "agent-api", "mcp")
                assert token not in logs and sentinel not in logs
                rows = []
                for line in logs.splitlines():
                    if "investigation.transition" not in line or "{" not in line:
                        continue
                    try:
                        rows.append(json.loads(line[line.find("{") :]))
                    except json.JSONDecodeError:
                        continue
                traces = [
                    row.get("trace_id", "")
                    for row in rows
                    if row.get("transition") == "investigation_created"
                ]
                if traces:
                    trace_id = traces[-1]
                    break
                await asyncio.sleep(1)
            assert len(trace_id) == 32 and int(trace_id, 16) != 0
            (ARTIFACTS / "sanitized.log").write_text(
                "\n".join(
                    line
                    for line in logs.splitlines()
                    if "investigation.transition" in line
                )
            )
            deadline = monotonic() + 90
            while monotonic() < deadline:
                response = await backend.get(f"{tempo_url}/api/traces/{trace_id}")
                if response.status_code == 200:
                    trace = response.json()
                    spans = [
                        span
                        for batch in trace.get("batches", [])
                        for scope in batch.get(
                            "scopeSpans", batch.get("instrumentationLibrarySpans", [])
                        )
                        for span in scope["spans"]
                    ]
                    names = {span["name"] for span in spans}
                    if {
                        "investigation.investigation_created",
                        "investigation.evidence_gap_identified",
                        "investigation.capability_resolution_completed",
                        "mcp.tool",
                    } <= names:
                        encoded = json.dumps(trace)
                        assert token not in encoded and sentinel not in encoded
                        assert (
                            "db.statement" not in encoded
                            and "db.query.text" not in encoded
                        )
                        (ARTIFACTS / "investigation-trace.json").write_text(encoded)
                        break
                await asyncio.sleep(1)
            else:
                raise AssertionError("Investigation/MCP spans did not reach Tempo")

            for metric in (
                "investigations_total",
                "investigations_approvals_total",
                "investigations_recipes_proposed_total",
            ):
                deadline = monotonic() + 90
                while monotonic() < deadline:
                    response = await backend.get(
                        prom_url + "/api/v1/query", params={"query": metric}
                    )
                    response.raise_for_status()
                    measured = response.json()
                    if measured["data"]["result"]:
                        encoded = json.dumps(measured)
                        assert token not in encoded and sentinel not in encoded
                        (ARTIFACTS / f"{metric}.json").write_text(encoded)
                        break
                    await asyncio.sleep(1)
                else:
                    raise AssertionError(
                        "Investigation metric did not reach Prometheus: " + metric
                    )
        print(
            json.dumps(
                {
                    "investigation_observability": "PASS",
                    "trace_id": trace_id,
                    "delivered_metrics": 3,
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
        (ARTIFACTS / "failure.log").write_text(
            logs.replace(token, "[redacted]").replace(sentinel, "[redacted]")
        )
        raise
    finally:
        await command("down", "-v")


if __name__ == "__main__":
    asyncio.run(main())
