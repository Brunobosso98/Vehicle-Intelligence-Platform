import json
import re
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

from mcp.server.auth.settings import AuthSettings
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ResourceNotFoundError, ToolError
from mcp.types import CallToolResult, InputRequiredResult, TextContent
from pydantic import AnyHttpUrl, AnyUrl, ValidationError

from vehicle_platform.core.config import Settings
from vehicle_platform.mcp.adapter import Adapter
from vehicle_platform.mcp.auth import ReadTokenVerifier
from vehicle_platform.mcp.config import MCPSettings
from vehicle_platform.mcp.database import ReadOnlyDatabase
from vehicle_platform.mcp.errors import ErrorCode, tool_error
from vehicle_platform.mcp.instrumentation import Instrumentation
from vehicle_platform.mcp.tools import register_tools
from vehicle_platform.observability.telemetry import Telemetry


class SafeMCPServer(MCPServer[None]):
    result_byte_limit: int = 524288

    @staticmethod
    def public_error(exc: Exception, fallback: ErrorCode) -> ToolError:
        for candidate in (exc, exc.__cause__):
            try:
                message = str(candidate)
                parsed = json.loads(message[message.index("{") :])
                code = ErrorCode(parsed["code"])
                request_id = UUID(parsed["mcp_request_id"])
                if set(parsed) == {"code", "mcp_request_id"}:
                    return tool_error(code, request_id)
            except (ValueError, TypeError, KeyError):
                continue
        return tool_error(fallback, uuid4())

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Context[None, Any] | None = None,
    ) -> CallToolResult | InputRequiredResult:
        try:
            result = await super().call_tool(name, arguments, context)
            if isinstance(result, CallToolResult) and result.structured_content is not None:
                result.content = [
                    TextContent(
                        type="text",
                        text=json.dumps(result.structured_content, separators=(",", ":")),
                    )
                ]
            if len(result.model_dump_json().encode()) > self.result_byte_limit - min(
                1024, self.result_byte_limit // 10
            ):
                raise tool_error(ErrorCode.RESULT_TOO_LARGE, uuid4())
            return result
        except ToolError as exc:
            raise self.public_error(exc, ErrorCode.INVALID_ARGUMENT) from None
        except ValidationError:
            raise tool_error(ErrorCode.INVALID_ARGUMENT, uuid4()) from None

    async def read_resource(
        self,
        uri: AnyUrl | str,
        context: Context[None, Any] | None = None,
    ) -> Iterable[ReadResourceContents] | InputRequiredResult:
        # Validate identifiers before SDK template validation, which logs rejected
        # input values and complete resource URIs on validation failures.
        match = re.fullmatch(r"vehicle://([^/]+)|(?:session|pull)://([^/]+)/([^/]+)", str(uri))
        if match is None:
            raise ResourceError(str(tool_error(ErrorCode.NOT_FOUND, uuid4())))
        try:
            for identifier in match.groups():
                if identifier is not None:
                    UUID(identifier)
        except ValueError:
            raise ResourceError(str(tool_error(ErrorCode.INVALID_ARGUMENT, uuid4()))) from None
        try:
            return await super().read_resource(uri, context)
        except ResourceNotFoundError:
            raise ResourceError(str(tool_error(ErrorCode.NOT_FOUND, uuid4()))) from None
        except (ResourceError, ValidationError) as exc:
            raise ResourceError(str(self.public_error(exc, ErrorCode.INVALID_ARGUMENT))) from None


def create_server(
    adapter: Adapter, telemetry: Telemetry, config: MCPSettings, *, owns_runtime: bool = False
) -> MCPServer[None]:
    @asynccontextmanager
    async def lifespan(server: MCPServer[None]) -> AsyncIterator[None]:
        try:
            yield None
        finally:
            if owns_runtime:
                await adapter.catalog.database.close()
                telemetry.shutdown()

    auth = None
    verifier = None
    if config.transport == "streamable-http":
        auth = AuthSettings(
            issuer_url=AnyHttpUrl(config.issuer_url),
            resource_server_url=AnyHttpUrl(config.resource_url),
            required_scopes=["mcp:read"],
        )
        verifier = ReadTokenVerifier(config, telemetry)
    server = SafeMCPServer(
        "vehicle-platform-mcp",
        version="1.1.0",
        lifespan=lifespan,
        instructions=(
            "Read-only factual automotive evidence. Anomaly detection is not diagnosis. "
            "Observed differences do not establish causation."
        ),
        auth=auth,
        token_verifier=verifier,
    )
    server.result_byte_limit = config.max_result_bytes
    instrumentation = Instrumentation(telemetry, config)
    register_tools(server, adapter, instrumentation)

    @server.resource("vehicle://{vehicle_id}", mime_type="application/json")
    async def vehicle(vehicle_id: UUID) -> str:
        """Snapshot of a factual vehicle context record."""

        async def read_vehicle() -> Any:
            return adapter.envelope(
                await adapter.entity("vehicle", vehicle_id, vehicle_id), {"vehicle_id": vehicle_id}
            )

        return (await instrumentation.wrap(read_vehicle)()).model_dump_json()

    @server.resource("session://{vehicle_id}/{session_id}", mime_type="application/json")
    async def session(vehicle_id: UUID, session_id: UUID) -> str:
        """Snapshot of a session; vehicle context must match."""

        async def read_session() -> Any:
            return adapter.envelope(
                await adapter.entity("session", session_id, vehicle_id),
                {"vehicle_id": vehicle_id, "session_id": session_id},
            )

        return (await instrumentation.wrap(read_session)()).model_dump_json()

    @server.resource("pull://{vehicle_id}/{pull_id}", mime_type="application/json")
    async def pull(vehicle_id: UUID, pull_id: UUID) -> str:
        """Snapshot of a detected factual pull with provenance."""

        async def read_pull() -> Any:
            return adapter.envelope(
                await adapter.pull(vehicle_id, pull_id),
                {"vehicle_id": vehicle_id, "pull_id": pull_id},
            )

        return (await instrumentation.wrap(read_pull)()).model_dump_json()

    return server


def runtime() -> tuple[MCPServer[None], Adapter, Telemetry, MCPSettings]:
    config = MCPSettings()
    settings = Settings()
    database = ReadOnlyDatabase(settings)
    telemetry = Telemetry(settings, database, service_name="vehicle-platform-mcp")
    adapter = Adapter(database, settings, telemetry)
    return create_server(adapter, telemetry, config, owns_runtime=True), adapter, telemetry, config
