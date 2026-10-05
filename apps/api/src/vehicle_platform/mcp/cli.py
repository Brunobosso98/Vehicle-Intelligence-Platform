"""One registration shared by stdio and authenticated Streamable HTTP."""

import argparse
import os

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from vehicle_platform.mcp.instrumentation import HTTPInstrumentation
from vehicle_platform.mcp.server import runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Vehicle Platform MCP")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default=None)
    arguments = parser.parse_args()
    if arguments.transport:
        os.environ["VIP_MCP_TRANSPORT"] = arguments.transport
    server, adapter, telemetry, config = runtime()
    if config.transport == "stdio":
        server.run(transport="stdio")
        return

    @server.custom_route("/ready", methods=["GET"])  # type: ignore[untyped-decorator]
    async def ready(request: Request) -> Response:
        try:
            await adapter.catalog.database.check()
            return Response(
                ' {"status":"ready","schema_version":"1.0"}', media_type="application/json"
            )
        except Exception:
            return Response(
                '{"status":"unavailable"}', status_code=503, media_type="application/json"
            )

    @server.custom_route("/metrics", methods=["GET"])  # type: ignore[untyped-decorator]
    async def metrics(request: Request) -> Response:
        return Response(telemetry.render_metrics(), media_type="text/plain")

    from urllib.parse import urlparse

    authority = urlparse(config.resource_url).netloc
    app = server.streamable_http_app(
        json_response=True,
        stateless_http=True,
        max_request_body_size=65536,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[authority, "localhost:*", "127.0.0.1:*"],
            allowed_origins=[config.resource_url.rsplit("/", 1)[0]],
        ),
    )
    app.add_middleware(BaseHTTPMiddleware, dispatch=HTTPInstrumentation(telemetry).dispatch)
    uvicorn.run(app, host=config.host, port=config.port, access_log=False)


if __name__ == "__main__":
    main()
