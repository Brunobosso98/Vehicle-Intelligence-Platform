import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent
from opentelemetry.propagate import inject

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.mcp.errors import ErrorCode
from vehicle_platform.mcp.schemas import Envelope
from vehicle_platform.mcp.tools import TOOL_NAMES

RECOVERABLE_TOOL_ERRORS = frozenset({"mcp_tool_error", "tool_result_budget_exhausted"})
PREDICTION_TOOL_ERRORS = {
    ErrorCode.NOT_FOUND: "prediction_evidence_unavailable",
    ErrorCode.FORBIDDEN: "prediction_evidence_not_verified",
    ErrorCode.UNSUPPORTED_CAPABILITY: "prediction_source_schema_unsupported",
    ErrorCode.CAPABILITY_REQUIRED: "prediction_capability_required",
    ErrorCode.PREDICTION_DISABLED: "prediction_disabled",
    ErrorCode.EVIDENCE_NOT_IN_SCOPE: "prediction_evidence_not_in_scope",
    ErrorCode.EVIDENCE_NOT_VERIFIED: "prediction_evidence_not_verified",
    ErrorCode.ABSTAINED: "prediction_abstained",
    ErrorCode.LOW_QUALITY: "prediction_low_quality",
    ErrorCode.UNAVAILABLE: "prediction_evidence_unavailable",
    ErrorCode.BUDGET_EXCEEDED: "prediction_evidence_budget_exhausted",
    ErrorCode.SOURCE_SCHEMA_UNSUPPORTED: "prediction_source_schema_unsupported",
    ErrorCode.BACKEND_UNAVAILABLE: "prediction_evidence_unavailable",
}


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
            if name == "get_prediction_evidence":
                for item in result.content:
                    if not isinstance(item, TextContent):
                        continue
                    try:
                        parsed = json.loads(item.text)
                        category = PREDICTION_TOOL_ERRORS.get(ErrorCode(parsed.get("code")))
                    except (ValueError, TypeError, AttributeError):
                        continue
                    if category:
                        raise AgentError(category)
            raise AgentError("mcp_tool_error")
        if result.structured_content is None:
            raise AgentError("invalid_tool_result")
        return Envelope.model_validate(result.structured_content)


@asynccontextmanager
async def connect(
    settings: AgentSettings, *, prediction_access: bool = False
) -> AsyncIterator[EvidenceClient]:
    headers: dict[str, str] = {}
    inject(headers)
    token = settings.prediction_mcp_token if prediction_access else settings.mcp_token
    if prediction_access and token is None:
        raise AgentError("prediction_capability_required")
    if token:
        headers["Authorization"] = "Bearer " + token.get_secret_value()
    async with (
        httpx2.AsyncClient(headers=headers, trust_env=False) as http,
        Client(streamable_http_client(settings.mcp_url, http_client=http)) as client,
    ):
        yield MCPClient(client, http)
