"""Real stdio and HTTP client acceptance, lifecycle, authorization and recovery."""

import asyncio
import json
import os
import secrets
import signal
import socket
import sys
import tempfile
from time import monotonic

import httpx
import httpx2
from evaluate_mcp import evaluate
from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp_fixtures import fingerprint, seed


async def main() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed(url)
    original = await fingerprint(url)
    environment = os.environ | {"DATABASE_URL": url, "ENVIRONMENT": "test"}
    reports = {}
    with tempfile.TemporaryFile(mode="w+") as stderr:
        transport = stdio_client(
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "vehicle_platform.mcp.cli", "--transport", "stdio"],
                env=environment,
            ),
            errlog=stderr,
        )
        async with Client(transport) as client:
            reports["stdio"] = await evaluate(client, fixture)
        stderr.seek(0)
        assert "Bearer" not in stderr.read()
    token = secrets.token_urlsafe(48)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = environment | {
        "VIP_MCP_TRANSPORT": "streamable-http",
        "VIP_MCP_PORT": str(port),
        "VIP_MCP_TOKEN": token,
        "VIP_MCP_RESOURCE_URL": base + "/mcp",
        "VIP_MCP_ISSUER_URL": base,
    }
    with tempfile.TemporaryFile(mode="w+") as stderr:

        async def start(extra=None):
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "vehicle_platform.mcp.cli",
                env=env | (extra or {}),
                stdout=stderr,
                stderr=stderr,
            )
            deadline = monotonic() + 20
            async with httpx.AsyncClient(trust_env=False) as http:
                while monotonic() < deadline and process.returncode is None:
                    try:
                        if (await http.get(base + "/ready")).status_code == 200:
                            return process
                    except httpx.TransportError:
                        pass
                    await asyncio.sleep(0.1)
            if process.returncode is None:
                process.terminate()
            await process.wait()
            stderr.seek(0)
            raise AssertionError(
                "HTTP readiness failed: " + stderr.read().replace(token, "[redacted]")
            )

        async def stop(process):
            if process.returncode is None:
                process.terminate()
            await asyncio.wait_for(process.wait(), 10)
            assert process.returncode in {0, -signal.SIGTERM}

        process = await start()
        try:
            async with httpx.AsyncClient(trust_env=False) as http:
                for headers, status in (
                    ({}, 401),
                    ({"Authorization": "Bearer invalid"}, 401),
                ):
                    result = await http.post(
                        base + "/mcp",
                        headers=headers,
                        json={"jsonrpc": "2.0", "id": 1, "method": "server/discover"},
                    )
                    assert result.status_code == status
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json, text/event-stream",
                }
                bad_origin = await http.post(
                    base + "/mcp",
                    headers=headers | {"Origin": "http://untrusted.invalid"},
                    json={"jsonrpc": "2.0", "id": 1, "method": "server/discover"},
                )
                assert bad_origin.status_code == 403
                oversized = await http.post(
                    base + "/mcp",
                    headers=headers | {"Content-Type": "application/json"},
                    content=b"x" * 65537,
                )
                assert oversized.status_code == 413
            async with (
                httpx2.AsyncClient(
                    headers={"Authorization": f"Bearer {token}"}, trust_env=False
                ) as http,
                Client(
                    streamable_http_client(base + "/mcp", http_client=http)
                ) as client,
            ):
                reports["http"] = await evaluate(client, fixture)
                results = await asyncio.gather(
                    *(
                        client.call_tool(
                            "get_vehicle", {"vehicle_id": fixture["vehicle"]}
                        )
                        for _ in range(4)
                    )
                )
                assert all(not r.is_error for r in results)
        finally:
            await stop(process)
        # Exercise dependency loss/recovery while the MCP process remains alive.
        project = os.environ["MCP_TEST_PROJECT"]

        paused = False

        async def database_command(action):
            nonlocal paused
            if action == "start" and not paused:
                return
            command = [
                "docker",
                "compose",
                "-p",
                project,
                "-f",
                "infra/docker/compose.test.yaml",
            ]
            args = ["pause", "db"] if action == "stop" else ["unpause", "db"]
            child = await asyncio.create_subprocess_exec(*command, *args)
            assert await child.wait() == 0
            paused = action == "stop"

        process = await start()
        try:
            await database_command("stop")
            async with httpx.AsyncClient(trust_env=False, timeout=8) as http:
                started = monotonic()
                assert (await http.get(base + "/ready")).status_code == 503
                assert monotonic() - started < 8
            async with (
                httpx2.AsyncClient(
                    headers={"Authorization": f"Bearer {token}"}, trust_env=False
                ) as http,
                Client(
                    streamable_http_client(base + "/mcp", http_client=http)
                ) as client,
            ):
                failure = await client.call_tool(
                    "get_vehicle", {"vehicle_id": fixture["vehicle"]}
                )
                assert (
                    failure.is_error
                    and "BACKEND_UNAVAILABLE" in failure.content[0].text
                )
                await database_command("start")
                assert not (
                    await client.call_tool(
                        "get_vehicle", {"vehicle_id": fixture["vehicle"]}
                    )
                ).is_error
        finally:
            await database_command("start")
            await stop(process)
        # New process and new client prove reconnect does not depend on retained sessions.
        process = await start()
        try:
            async with (
                httpx2.AsyncClient(
                    headers={"Authorization": f"Bearer {token}"}, trust_env=False
                ) as http,
                Client(
                    streamable_http_client(base + "/mcp", http_client=http)
                ) as client,
            ):
                assert not (
                    await client.call_tool(
                        "get_vehicle", {"vehicle_id": fixture["vehicle"]}
                    )
                ).is_error
        finally:
            await stop(process)
        for extra, expected in (
            ({"VIP_MCP_TOKEN_SCOPE": "other"}, 403),
            ({"VIP_MCP_TOKEN_EXPIRES_AT": "1"}, 401),
        ):
            process = await start(extra)
            try:
                async with httpx.AsyncClient(trust_env=False) as http:
                    response = await http.post(
                        base + "/mcp",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"jsonrpc": "2.0", "id": 1, "method": "server/discover"},
                    )
                    assert response.status_code == expected
            finally:
                await stop(process)
        stderr.seek(0)
        assert token not in stderr.read()
    assert await fingerprint(url) == original
    print(
        json.dumps(
            {
                "mcp_protocol_e2e": "PASS",
                "restart_reconnect": "PASS",
                "backend_recovery": "PASS",
                "auth_negative": "PASS",
                **reports,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
