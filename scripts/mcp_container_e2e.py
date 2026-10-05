"""Official HTTP client exercises the real immutable MCP container and restart."""

import asyncio
import json
import os
import secrets

import httpx2
from evaluate_mcp import evaluate
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp_fixtures import fingerprint, seed


async def ready_endpoint(address: str) -> str:
    from time import monotonic

    deadline = monotonic() + 30
    async with httpx2.AsyncClient(trust_env=False, timeout=5) as http:
        while monotonic() < deadline:
            try:
                if (await http.get(f"http://{address}/ready")).status_code == 200:
                    return f"http://{address}/mcp"
            except httpx2.TransportError:
                pass
            await asyncio.sleep(0.1)
    raise AssertionError("MCP container host forwarding did not become ready")


async def main() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed(url)
    original = await fingerprint(url)
    token = secrets.token_urlsafe(48)
    environment = os.environ | {"VIP_MCP_TOKEN": token}
    command = [
        "docker",
        "compose",
        "-p",
        os.environ["MCP_TEST_PROJECT"],
        "-f",
        "infra/docker/compose.test.yaml",
        "-f",
        "infra/docker/compose.mcp-test.yaml",
    ]

    async def compose(*arguments):
        child = await asyncio.create_subprocess_exec(
            *command,
            *arguments,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await child.communicate()
        assert child.returncode == 0, stderr.decode().replace(token, "[redacted]")
        return stdout.decode().strip()

    try:
        await compose("up", "-d", "--no-build", "--wait", "mcp")
        address = await compose("port", "mcp", "8001")
        endpoint = await ready_endpoint(address)
        headers = {"Authorization": f"Bearer {token}"}
        async with (
            httpx2.AsyncClient(headers=headers, trust_env=False) as http,
            Client(streamable_http_client(endpoint, http_client=http)) as client,
        ):
            report = await evaluate(client, fixture)
            results = await asyncio.gather(
                *(
                    client.call_tool(
                        "get_pull",
                        {
                            "vehicle_id": fixture["vehicle"],
                            "pull_id": fixture["pulls"][0][0],
                        },
                    )
                    for _ in range(4)
                )
            )
            assert all(not result.is_error for result in results)
        await compose("stop", "mcp")
        await compose("up", "-d", "--no-build", "--wait", "mcp")
        # Docker may assign a new disposable host port after stop/start.
        endpoint = await ready_endpoint(await compose("port", "mcp", "8001"))
        async with (
            httpx2.AsyncClient(headers=headers, trust_env=False) as http,
            Client(streamable_http_client(endpoint, http_client=http)) as client,
        ):
            result = await client.call_tool(
                "get_vehicle", {"vehicle_id": fixture["vehicle"]}
            )
            assert (
                not result.is_error
                and result.structured_content["data"]["id"] == fixture["vehicle"]
            )
        assert token not in await compose("logs", "--no-color", "mcp")
        assert await fingerprint(url) == original
        print(
            json.dumps(
                {
                    "mcp_container_e2e": "PASS",
                    "restart_reconnect": "PASS",
                    "concurrent_calls": 4,
                    **report,
                }
            )
        )
    finally:
        await compose("rm", "-s", "-f", "mcp")


if __name__ == "__main__":
    asyncio.run(main())
