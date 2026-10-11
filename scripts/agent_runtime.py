"""Bounded local HTTP processes for disposable Phase 7A acceptance only."""

import asyncio
import os
import secrets
import socket
import sys
import tempfile
from contextlib import ExitStack, asynccontextmanager
from pathlib import Path
from typing import Any

import httpx


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


class Process:
    def __init__(self, args: list[str], env: dict[str, str], ready: str) -> None:
        self.args, self.env, self.ready = args, env, ready
        self.resources = ExitStack()
        # Owned by ExitStack across process restarts and closed by runtime's finally block.
        self.log = self.resources.enter_context(tempfile.TemporaryFile(mode="w+"))  # noqa: SIM115
        self.child: asyncio.subprocess.Process | None = None

    async def start(self) -> None:
        self.child = await asyncio.create_subprocess_exec(
            *self.args,
            env=self.env,
            stdout=self.log,
            stderr=self.log,
        )
        try:
            async with (
                asyncio.timeout(120),
                httpx.AsyncClient(timeout=2, trust_env=False) as http,
            ):
                while self.child.returncode is None:
                    try:
                        if (await http.get(self.ready)).status_code == 200:
                            return
                    except httpx.TransportError:
                        pass
                    await asyncio.sleep(0.2)
                raise AssertionError("Acceptance process exited before readiness")
        except BaseException:
            await self.stop()
            raise

    async def stop(self) -> None:
        if self.child and self.child.returncode is None:
            self.child.terminate()
            try:
                await asyncio.wait_for(self.child.wait(), 10)
            except TimeoutError:
                self.child.kill()
                await self.child.wait()

    def close(self) -> None:
        self.resources.close()


@asynccontextmanager
async def runtime(
    url: str, *, web: bool = False, real: bool = False, worker: bool = False
):
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise AssertionError(
            "Phase 7A acceptance requires disposable vehicle_test* database"
        )
    token = secrets.token_urlsafe(48)
    mcp_port, api_port, web_port = free_port(), free_port(), free_port()
    mcp_base, api_base = f"http://127.0.0.1:{mcp_port}", f"http://127.0.0.1:{api_port}"
    env = os.environ | {
        "DATABASE_URL": url,
        "ENVIRONMENT": "test",
        "VIP_MCP_TOKEN": token,
        "VIP_MCP_TRANSPORT": "streamable-http",
        "VIP_MCP_PORT": str(mcp_port),
        "VIP_MCP_RESOURCE_URL": mcp_base + "/mcp",
        "VIP_MCP_ISSUER_URL": mcp_base,
        "VIP_AGENT_ENABLED": "true",
        "VIP_AGENT_PROVIDER": "openai" if real else "deterministic",
        "VIP_AGENT_MCP_URL": mcp_base + "/mcp",
        "VIP_AGENT_MCP_TOKEN": token,
        "VIP_AGENT_INVESTIGATION_TOKEN": token,
        "API_BASE_URL": api_base,
    }
    processes = [
        Process(
            [sys.executable, "-m", "vehicle_platform.mcp.cli"], env, mcp_base + "/ready"
        ),
        Process(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "vehicle_platform.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
                "--no-access-log",
            ],
            env,
            api_base + "/health/ready",
        ),
    ]
    if worker:
        processes.append(
            Process(
                [sys.executable, "-m", "vehicle_platform.acquisition.worker"],
                env | {"WORKER_METRICS_HOST": "127.0.0.2"},
                "http://127.0.0.2:8001/metrics",
            )
        )
    if web:
        processes.append(
            Process(
                [
                    "node",
                    "apps/web/node_modules/next/dist/bin/next",
                    "start",
                    "apps/web",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    str(web_port),
                ],
                env,
                f"http://127.0.0.1:{web_port}",
            )
        )
    try:
        for process in processes:
            await process.start()
        yield {
            "api": api_base,
            "web": f"http://127.0.0.1:{web_port}",
            "mcp": processes[0],
            "token": token,
            "processes": processes,
        }
    except BaseException:
        for index, process in enumerate(processes):
            process.log.seek(0)
            operational = [
                line
                for line in process.log.read().splitlines()
                if line.startswith('{"timestamp"')
            ]
            safe = "\n".join(operational).replace(token, "[redacted]")
            if env.get("VIP_AGENT_API_KEY"):
                safe = safe.replace(env["VIP_AGENT_API_KEY"], "[redacted]")
            directory = Path(".validation/agent")
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"runtime-{index}-failure.log").write_text(safe)
            diagnostics = process.log
            diagnostics.seek(0)
            diagnostic = diagnostics.read().replace(url, "[redacted-database]")
            for key, value in env.items():
                if value and key.endswith(("TOKEN", "KEY", "PASSWORD")):
                    diagnostic = diagnostic.replace(value, "[redacted]")
            (directory / f"runtime-{index}-diagnostic.log").write_text(
                diagnostic[-20000:]
            )
        raise
    finally:
        for process in reversed(processes):
            await process.stop()
            process.close()


async def ask(api: httpx.AsyncClient, vehicle: str, question: str) -> dict[str, Any]:
    path = f"/api/v1/vehicles/{vehicle}/agent-runs"
    response = await api.post(path, json={"question": question})
    response.raise_for_status()
    identifier = response.json()["id"]
    stream = await api.get(f"{path}/{identifier}/stream")
    assert stream.status_code == 200, stream.text
    response = await api.get(f"{path}/{identifier}")
    response.raise_for_status()
    return response.json() | {"stream": stream.text}
