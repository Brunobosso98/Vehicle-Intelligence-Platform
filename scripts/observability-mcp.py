"""Prove runtime MCP metrics and sanitized spans reach Prometheus and Tempo."""

import asyncio
import json
import os
from pathlib import Path
from time import monotonic
from uuid import uuid4

import httpx
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    token = os.environ["VIP_MCP_TOKEN"]
    trace_id = uuid4().hex
    headers = {
        "Authorization": f"Bearer {token}",
        "traceparent": f"00-{trace_id}-0000000000000001-01",
    }
    async with (
        httpx2.AsyncClient(headers=headers, trust_env=False) as http,
        Client(
            streamable_http_client("http://127.0.0.1:8001/mcp", http_client=http)
        ) as client,
    ):
        result = await client.call_tool("list_vehicles", {"limit": 1})
        assert not result.is_error
    evidence = Path(".validation/observability")
    evidence.mkdir(parents=True, exist_ok=True)
    deadline = monotonic() + 60
    async with httpx.AsyncClient(trust_env=False, timeout=5) as backend:
        while monotonic() < deadline:
            response = await backend.get(f"http://127.0.0.1:3200/api/traces/{trace_id}")
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
                database = any(
                    attribute["key"] in {"db.system", "db.system.name"}
                    for span in spans
                    for attribute in span.get("attributes", [])
                )
                if {"mcp.request", "mcp.tool"} <= names and database:
                    encoded = json.dumps(trace)
                    assert token not in encoded
                    assert (
                        "db.statement" not in encoded and "db.query.text" not in encoded
                    )
                    (evidence / "mcp-trace.json").write_text(encoded)
                    break
            await asyncio.sleep(1)
        else:
            raise AssertionError("MCP spans did not reach Tempo")
        deadline = monotonic() + 60
        while monotonic() < deadline:
            response = await backend.get(
                "http://127.0.0.1:9090/api/v1/query",
                params={"query": 'mcp_tool_calls_total{tool="list_vehicles"}'},
            )
            response.raise_for_status()
            metrics = response.json()
            if metrics["status"] == "success" and metrics["data"]["result"]:
                (evidence / "mcp-prometheus.json").write_text(json.dumps(metrics))
                break
            await asyncio.sleep(1)
        else:
            raise AssertionError("MCP tool metrics did not reach Prometheus")
    print(
        json.dumps(
            {"mcp_observability": "PASS", "trace_id": trace_id, "database_spans": True}
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
