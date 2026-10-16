"""Delivered knowledge/MCP/database instrumentation; synthetic embedding transport, no API spend."""

import asyncio
import json
import os
import secrets
from pathlib import Path
from time import monotonic

import httpx
from agent_fixtures import seed_agent
from evaluate_knowledge import seed_knowledge
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.knowledge.repository import KnowledgeRepository

ARTIFACTS = Path(".validation/knowledge/observability")


async def main():
    url = os.environ["TEST_DATABASE_URL"]
    assert url.rsplit("/", 1)[-1].startswith("vehicle_test")
    fixture = await seed_agent(url)
    database = Database(Settings(database_url=url, environment="test"))
    try:
        await seed_knowledge(KnowledgeRepository(database))
    finally:
        await database.close()
    project = os.environ["MCP_TEST_PROJECT"]
    assert project.startswith("vehicle-platform-mcp-tests-")
    token, sentinel = (
        secrets.token_urlsafe(48),
        "knowledge-redaction-" + secrets.token_urlsafe(24),
    )
    env = os.environ | {
        "VIP_MCP_TOKEN": token,
        "AGENT_REDACTION_SENTINEL": sentinel,
        "KNOWLEDGE_PROMETHEUS_CONFIG": "./observability/prometheus-knowledge.yaml",
    }
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

    async def command(*args, input_bytes=None):
        child = await asyncio.create_subprocess_exec(
            *compose,
            *args,
            env=env,
            stdin=asyncio.subprocess.PIPE if input_bytes is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        async with asyncio.timeout(180):
            output, errors = await child.communicate(input_bytes)
        if child.returncode:
            raise AssertionError(
                errors.decode()
                .replace(token, "[redacted]")
                .replace(sentinel, "[redacted]")
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
        await command(
            "exec",
            "-T",
            "agent-api",
            "python",
            "-c",
            "import sys; from pathlib import Path; "
            "Path('/tmp/knowledge-ingestion-probe.py').write_bytes(sys.stdin.buffer.read())",
            input_bytes=Path("scripts/knowledge_ingestion_probe.py").read_bytes(),
        )
        await command(
            "exec",
            "-T",
            "-d",
            "-e",
            "KNOWLEDGE_FREE_PROBE=yes",
            "agent-api",
            "python",
            "/tmp/knowledge-ingestion-probe.py",
        )
        async with httpx.AsyncClient(timeout=120, trust_env=False) as http:
            runs = []
            for question in (
                "How does the N55 high pressure fuel system regulate pressure?",
                "Is the observed HPFP behavior expected for this vehicle?",
            ):
                path = f"{api_url}/api/v1/vehicles/{fixture['vehicle']}/agent-runs"
                created = await http.post(path, json={"question": question})
                created.raise_for_status()
                identifier = created.json()["id"]
                streamed = await http.get(f"{path}/{identifier}/stream")
                streamed.raise_for_status()
                current = (await http.get(f"{path}/{identifier}")).json()
                assert current["status"] == "completed", current["error_category"]
                assert current["result"]["knowledge"]["retrieval"]["evidence"]
                runs.append(current)
            for current in runs:
                deadline = monotonic() + 60
                while monotonic() < deadline:
                    response = await http.get(
                        f"{tempo_url}/api/traces/{current['trace_id']}"
                    )
                    if response.status_code == 200:
                        trace = response.json()
                        spans = [
                            span
                            for batch in trace.get("batches", [])
                            for scope in batch.get(
                                "scopeSpans",
                                batch.get("instrumentationLibrarySpans", []),
                            )
                            for span in scope["spans"]
                        ]
                        expected = {
                            "agent.run",
                            "agent.context",
                            "agent.mcp_tool",
                            "mcp.request",
                            "mcp.tool",
                            "knowledge.retrieval",
                            "knowledge.lexical_vector",
                            "knowledge.intent",
                            "knowledge.fusion_rerank",
                            "knowledge.evidence",
                        }
                        if (
                            current["result"]["knowledge"]["request_type"]
                            != "KNOWLEDGE_FACT"
                        ):
                            expected.add("knowledge.grounding_synthesis")
                        if expected <= {span["name"] for span in spans} and any(
                            a["key"] in {"db.system", "db.system.name"}
                            for span in spans
                            for a in span.get("attributes", [])
                        ):
                            encoded = json.dumps(trace)
                            assert sentinel not in encoded and token not in encoded
                            assert (
                                "db.statement" not in encoded
                                and "db.query.text" not in encoded
                            )
                            (ARTIFACTS / f"{current['id']}-trace.json").write_text(
                                encoded
                            )
                            break
                    await asyncio.sleep(1)
                else:
                    raise AssertionError(
                        "Knowledge/MCP/database spans did not reach Tempo"
                    )
            for metric in (
                "knowledge_ingestion_total",
                "knowledge_ingestion_failures_total",
                "knowledge_chunks_total",
                "embedding_requests_total",
                "embedding_tokens_total",
                "embedding_estimated_cost_usd_total",
                "embedding_cache_hits_total",
                "retrieval_requests_total",
                "retrieval_latency_seconds_count",
                "retrieval_candidates_total",
                "retrieval_knowledge_gap_total",
            ):
                deadline = monotonic() + 60
                while monotonic() < deadline:
                    response = await http.get(
                        prom_url + "/api/v1/query", params={"query": metric}
                    )
                    response.raise_for_status()
                    measured = response.json()
                    values = measured["data"]["result"]
                    if values and sum(float(row["value"][1]) for row in values) > 0:
                        encoded = json.dumps(measured)
                        assert sentinel not in encoded and token not in encoded
                        for row in values:
                            assert (
                                not {
                                    "vehicle_id",
                                    "session_id",
                                    "document_id",
                                    "url",
                                    "query",
                                }
                                & row["metric"].keys()
                            )
                        (ARTIFACTS / f"{metric}.json").write_text(encoded)
                        break
                    await asyncio.sleep(1)
                else:
                    raise AssertionError("Knowledge metric not delivered: " + metric)
            probe = json.loads(
                await command(
                    "exec",
                    "-T",
                    "agent-api",
                    "cat",
                    "/tmp/knowledge-probe-receipt.json",
                )
            )
            assert (
                probe["paid_calls"] == 0
                and probe["embedding_transport"] == "synthetic-mock"
            )
            deadline = monotonic() + 60
            while monotonic() < deadline:
                response = await http.get(f"{tempo_url}/api/traces/{probe['trace_id']}")
                if response.status_code == 200:
                    trace = response.json()
                    names = {
                        span["name"]
                        for batch in trace.get("batches", [])
                        for scope in batch.get(
                            "scopeSpans", batch.get("instrumentationLibrarySpans", [])
                        )
                        for span in scope["spans"]
                    }
                    if {
                        "knowledge.operator_probe",
                        "knowledge.ingestion",
                        "knowledge.embedding",
                    } <= names:
                        encoded = json.dumps(trace)
                        assert sentinel not in encoded and token not in encoded
                        assert "synthetic-no-network-probe" not in encoded
                        (ARTIFACTS / "ingestion-embedding-trace.json").write_text(
                            encoded
                        )
                        break
                await asyncio.sleep(1)
            else:
                raise AssertionError("Ingestion/embedding spans did not reach Tempo")
        logs = await command("logs", "--no-color", "agent-api", "mcp")
        assert sentinel not in logs and token not in logs
        assert "knowledge.retrieved" in logs and "mcp.call.completed" in logs
        (ARTIFACTS / "sanitized.log").write_text(logs)
        print(
            json.dumps(
                {
                    "knowledge_retrieval_observability": "PASS",
                    "paid_calls": 0,
                    "embedding_transport": "synthetic-mock, no network",
                }
            )
        )
    finally:
        await command("down", "-v")


if __name__ == "__main__":
    asyncio.run(main())
