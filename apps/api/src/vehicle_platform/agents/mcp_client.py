from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from opentelemetry.propagate import inject

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.mcp.schemas import Envelope
from vehicle_platform.mcp.tools import TOOL_NAMES


class EvidenceClient(Protocol):
    async def discover(self) -> list[dict[str, Any]]: ...
    async def call(self, name: str, arguments: dict[str, Any]) -> Envelope: ...


class MCPClient:
    def __init__(self, client: Client, http: httpx2.AsyncClient | None = None) -> None:
        self.client = client
        self.http = http

    async def discover(self) -> list[dict[str, Any]]:
        inventory = await self.client.list_tools()
        tools = []
        for tool in inventory.tools:
            annotations = tool.annotations
            if (
                tool.name not in TOOL_NAMES
                or not annotations
                or annotations.read_only_hint is not True
                or annotations.destructive_hint is not False
                or annotations.open_world_hint is not False
            ):
                raise AgentError("unsafe_tool_inventory")
            # list_vehicles would reveal unrelated vehicle records to the selected context.
            if tool.name == "list_vehicles":
                continue
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                }
            )
        return tools

    async def call(self, name: str, arguments: dict[str, Any]) -> Envelope:
        if self.http is not None:
            headers: dict[str, str] = {}
            inject(headers)
            self.http.headers.update(headers)
        result = await self.client.call_tool(name, arguments)
        if result.is_error:
            raise AgentError("mcp_tool_error")
        if result.structured_content is None:
            raise AgentError("invalid_tool_result")
        return Envelope.model_validate(result.structured_content)


@asynccontextmanager
async def connect(settings: AgentSettings) -> AsyncIterator[EvidenceClient]:
    headers: dict[str, str] = {}
    inject(headers)
    if settings.mcp_token:
        headers["Authorization"] = "Bearer " + settings.mcp_token.get_secret_value()
    async with (
        httpx2.AsyncClient(headers=headers, trust_env=False) as http,
        Client(streamable_http_client(settings.mcp_url, http_client=http)) as client,
    ):
        yield MCPClient(client, http)
