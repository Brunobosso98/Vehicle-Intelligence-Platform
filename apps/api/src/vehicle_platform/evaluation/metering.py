"""Case-wide MCP receipts, including the existing Phase 7B search/refresh calls."""

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.mcp_client import EvidenceClient, connect
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.mcp.schemas import Envelope
from vehicle_platform.mcp.tools import TOOL_NAMES


class ToolMeter:
    # Parent 32 + Phase 7B ten session reads + one recorded-capability refresh.
    limit = 43

    def __init__(self) -> None:
        self.case_key: str | None = None
        self.vehicle_id: str | None = None
        self.calls: dict[str, list[dict[str, Any]]] = {}

    def start(self, case_key: str, vehicle_id: str) -> None:
        self.case_key, self.vehicle_id = case_key, vehicle_id
        self.calls.setdefault(case_key, [])

    @asynccontextmanager
    async def client(self, settings: AgentSettings) -> AsyncIterator[EvidenceClient]:
        async with connect(settings) as client:
            yield MeteredClient(client, self)


class MeteredClient:
    def __init__(self, client: EvidenceClient, meter: ToolMeter) -> None:
        self.source, self.meter = client, meter

    async def discover(self) -> list[dict[str, Any]]:
        return await self.source.discover()

    async def call(self, name: str, arguments: dict[str, Any]) -> Envelope:
        meter = self.meter
        if meter.case_key is None:
            return await self.source.call(name, arguments)
        if name not in TOOL_NAMES or name == "list_vehicles":
            raise AgentError("forbidden_tool")
        if str(arguments.get("vehicle_id")) != meter.vehicle_id:
            raise AgentError("incompatible_context")
        calls = meter.calls[meter.case_key]
        if len(calls) >= meter.limit:
            raise AgentError("BUDGET_VIOLATION")
        if name == "get_telemetry_window" and any(c["tool_name"] == name for c in calls):
            raise AgentError("BUDGET_VIOLATION")
        entry: dict[str, Any] = {
            "tool_name": name,
            "argument_hash": hashlib.sha256(
                json.dumps(arguments, sort_keys=True).encode()
            ).hexdigest(),
            "status": "running",
        }
        calls.append(entry)
        started = perf_counter()
        try:
            result = await self.source.call(name, arguments)
            if str(result.context.get("vehicle_id")) != meter.vehicle_id:
                raise AgentError("incompatible_context")
            entry["status"] = "completed"
            return result
        except BaseException:
            entry["status"] = "failed"
            raise
        finally:
            entry["duration_seconds"] = perf_counter() - started
