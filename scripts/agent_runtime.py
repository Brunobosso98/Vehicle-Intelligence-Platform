"""Bounded local HTTP processes for disposable Phase 7A acceptance only."""

import asyncio
import hashlib
import json
import os
import platform
import resource
import secrets
import socket
import sys
import tempfile
from collections.abc import AsyncIterator
from contextlib import ExitStack, asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from vehicle_platform.agent_evaluation.privacy import redact_runtime_secrets

_runtime_child_process_count = 0


def begin_resource_measurement() -> resource.struct_rusage:
    """Start a run-scoped measurement of direct child CPU and peak resident memory."""
    global _runtime_child_process_count
    _runtime_child_process_count = 0
    return resource.getrusage(resource.RUSAGE_CHILDREN)


def resource_measurement_since(
    baseline: resource.struct_rusage,
) -> dict[str, str | int]:
    """Return bounded OS measurements for child processes started by this runner."""
    current = resource.getrusage(resource.RUSAGE_CHILDREN)
    system = platform.system().casefold()
    if system not in {"linux", "darwin"}:
        raise RuntimeError("phase11_resource_measurement_platform_unsupported")
    rss_multiplier = 1024 if system == "linux" else 1
    peak_rss = int(current.ru_maxrss * rss_multiplier)
    if peak_rss <= 0 or _runtime_child_process_count <= 0:
        raise RuntimeError("phase11_child_resource_measurement_missing")
    return {
        "platform": system,
        "child_process_count": _runtime_child_process_count,
        "peak_child_rss_bytes": peak_rss,
        "child_cpu_user_ms": max(
            0, round((current.ru_utime - baseline.ru_utime) * 1000)
        ),
        "child_cpu_system_ms": max(
            0, round((current.ru_stime - baseline.ru_stime) * 1000)
        ),
    }


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
        global _runtime_child_process_count
        self.child = await asyncio.create_subprocess_exec(
            *self.args,
            env=self.env,
            stdout=self.log,
            stderr=self.log,
        )
        _runtime_child_process_count += 1
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
        except BaseException as exc:
            await self.stop()
            self.log.flush()
            self.log.seek(0)
            diagnostic = redact_runtime_secrets(self.log.read(), self.env)
            relevant = [
                line
                for line in diagnostic.splitlines()
                if any(
                    marker in line.casefold()
                    for marker in (
                        "traceback",
                        "error",
                        "critical",
                        "exception",
                    )
                )
            ]
            excerpt = "\n".join(relevant[-12:])[-6000:]
            if len(relevant) < 2:
                excerpt = "\n".join(diagnostic.splitlines()[-24:])[-6000:]
            if excerpt:
                raise AssertionError(
                    f"Acceptance process for {self.ready} failed before readiness; "
                    f"sanitized diagnostics:\n{excerpt}"
                ) from exc
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
    url: str,
    *,
    web: bool = False,
    real: bool = False,
    worker: bool = False,
    failure_log_directory: str | Path = ".validation/agent",
    enable_prediction_evidence: bool = False,
    prediction_artifacts_unavailable: bool = False,
    prediction_vehicle_id: str | None = None,
    mcp_disconnect_once: bool = False,
    provider_fault: str | None = None,
    agent_max_concurrent_runs: int | None = None,
    model_timeout_seconds: float | None = None,
    specialist_timeout_seconds: float | None = None,
) -> AsyncIterator[dict[str, Any]]:
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise AssertionError(
            "Phase 7A acceptance requires disposable vehicle_test* database"
        )
    token = secrets.token_urlsafe(48)
    provider_canary = (
        secrets.token_urlsafe(32) if provider_fault == "provider_canary" else None
    )
    prediction_token = secrets.token_urlsafe(48) if enable_prediction_evidence else None
    prediction_operator_token = (
        secrets.token_urlsafe(48) if enable_prediction_evidence else None
    )
    if enable_prediction_evidence and prediction_vehicle_id is None:
        raise ValueError(
            "prediction capability fixture requires an explicit vehicle id"
        )
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
    if mcp_disconnect_once:
        env["PHASE11_MCP_TRANSPORT_FAULT"] = "disconnect_once"
    artifact_root_temp: tempfile.TemporaryDirectory[str] | None = None
    if prediction_artifacts_unavailable:
        if not enable_prediction_evidence:
            raise ValueError(
                "missing-artifact fixture requires prediction evidence capability"
            )
        artifact_root_temp = tempfile.TemporaryDirectory(
            prefix="phase11-empty-artifacts-"
        )
        artifact_root = Path(artifact_root_temp.name)
        env["PREDICTION_MODEL_ARTIFACT_ROOT"] = str(artifact_root / "phase9b")
        env["PREDICTION_ANOMALY_ARTIFACT_ROOT"] = str(artifact_root / "phase9c")
    if agent_max_concurrent_runs is not None:
        if not 1 <= agent_max_concurrent_runs <= 8:
            raise ValueError("agent concurrency fixture must be between 1 and 8")
        env["VIP_AGENT_MAX_CONCURRENT_RUNS"] = str(agent_max_concurrent_runs)
    if model_timeout_seconds is not None:
        if not 0 < model_timeout_seconds <= 60:
            raise ValueError("model timeout fixture must be between 0 and 60 seconds")
        env["VIP_AGENT_MODEL_TIMEOUT"] = str(model_timeout_seconds)
    if specialist_timeout_seconds is not None:
        if not 0 < specialist_timeout_seconds <= 45:
            raise ValueError(
                "specialist timeout fixture must be between 0 and 45 seconds"
            )
        env["VIP_AGENT_SPECIALIST_TIMEOUT"] = str(specialist_timeout_seconds)
    env.pop("VIP_AGENT_TEST_PROVIDER_FAULT", None)
    if provider_fault is not None:
        if provider_fault not in {
            "malformed_json",
            "forged_citation",
            "conflicting_unit",
            "wait_after_tool",
            "provider_canary",
            "provider_retry_once",
            "provider_retry_rate_limit_and_unavailable",
            "provider_timeout_once",
            "specialist_timeout",
        }:
            raise ValueError("Unsupported test provider fault")
        env["VIP_AGENT_TEST_PROVIDER_FAULT"] = provider_fault
    if provider_canary is not None:
        env["VIP_AGENT_TEST_SECRET_CANARY"] = provider_canary
    if prediction_token is not None and prediction_vehicle_id is not None:
        env |= {
            "PREDICTION_SERVICE_ENABLED": "true",
            "PREDICTION_OPERATOR_TOKEN": prediction_operator_token or "",
            "VIP_MCP_PREDICTION_EVIDENCE_ENABLED": "true",
            "VIP_MCP_PREDICTION_TOKEN": prediction_token,
            "VIP_MCP_PREDICTION_VEHICLE_IDS": json.dumps([prediction_vehicle_id]),
            "VIP_AGENT_PREDICTION_SERVICE_ENABLED": "true",
            "VIP_AGENT_PREDICTION_EVIDENCE_ENABLED": "true",
            "VIP_AGENT_PREDICTION_CAPABILITY_TOKEN": prediction_operator_token or "",
            "VIP_AGENT_PREDICTION_MCP_TOKEN": prediction_token,
            "VIP_AGENT_PREDICTION_VEHICLE_IDS": json.dumps([prediction_vehicle_id]),
        }
    api_env = {
        key: value for key, value in env.items() if not key.startswith("VIP_MCP_")
    }
    mcp_env = env.copy()
    mcp_env.pop("VIP_AGENT_TEST_SECRET_CANARY", None)
    processes = [
        Process(
            [sys.executable, "-m", "vehicle_platform.mcp.cli"],
            mcp_env,
            mcp_base + "/ready",
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
            api_env,
            api_base + "/health/ready",
        ),
    ]
    if worker:
        processes.append(
            Process(
                [sys.executable, "-m", "vehicle_platform.acquisition.worker"],
                api_env | {"WORKER_METRICS_HOST": "127.0.0.2"},
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
                api_env,
                f"http://127.0.0.1:{web_port}",
            )
        )
    try:
        for process in processes:
            await process.start()
        yield {
            "api": api_base,
            "web": f"http://127.0.0.1:{web_port}",
            "mcp_url": mcp_base + "/mcp",
            "mcp": processes[0],
            "token": token,
            "secret_values": tuple(
                value
                for value in (
                    token,
                    prediction_token,
                    prediction_operator_token,
                    provider_canary,
                )
                if value is not None
            ),
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
            safe = redact_runtime_secrets(safe, env)
            directory = Path(failure_log_directory)
            await asyncio.to_thread(
                directory.mkdir, parents=True, exist_ok=True, mode=0o700
            )
            os.chmod(directory, 0o700)
            failure_log = directory / f"runtime-{index}-failure.log"
            failure_log.write_text(safe)
            os.chmod(failure_log, 0o600)
            diagnostics = process.log
            diagnostics.seek(0)
            diagnostic = redact_runtime_secrets(diagnostics.read(), env)
            diagnostic_path = directory / f"runtime-{index}-diagnostic.log"
            diagnostic_path.write_text(diagnostic[-20000:])
            os.chmod(diagnostic_path, 0o600)
        raise
    finally:
        for process in reversed(processes):
            await process.stop()
            process.close()
        if artifact_root_temp is not None:
            artifact_root_temp.cleanup()


async def ask(
    api: httpx.AsyncClient,
    vehicle: str,
    question: str,
    *,
    session_id: str | None = None,
    prediction_evidence_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    started = perf_counter()
    path = f"/api/v1/vehicles/{vehicle}/agent-runs"
    request_body: dict[str, Any] = {"question": question}
    if session_id is not None:
        request_body["session_id"] = session_id
    if prediction_evidence_ids:
        request_body["include_prediction_evidence"] = True
        request_body["prediction_evidence_ids"] = list(prediction_evidence_ids)
    response = await api.post(path, json=request_body)
    response.raise_for_status()
    identifier = response.json()["id"]
    stream_started = perf_counter()
    stream_chunks: list[bytes] = []
    first_event_ms: int | None = None
    response_bytes = 0
    event_marker_tail = b""
    async with api.stream("GET", f"{path}/{identifier}/stream") as stream:
        if stream.status_code != 200:
            raise AssertionError(
                f"agent_run_stream_request_failed:{stream.status_code}"
            )
        async for chunk in stream.aiter_bytes():
            response_bytes += len(chunk)
            if response_bytes > 1_048_576:
                raise AssertionError("agent_run_stream_size_limit_exceeded")
            stream_chunks.append(chunk)
            if first_event_ms is None:
                marker_window = event_marker_tail + chunk
                if b"event: " in marker_window:
                    first_event_ms = int((perf_counter() - stream_started) * 1000)
                event_marker_tail = marker_window[-7:]
    if first_event_ms is None:
        raise AssertionError("agent_run_stream_has_no_first_sse_event")
    stream_content = b"".join(stream_chunks)
    stream_text = stream_content.decode("utf-8")
    event_ids = [
        int(line[4:])
        for line in stream_text.splitlines()
        if line.startswith("id: ") and line[4:].isdigit()
    ]
    if not event_ids:
        raise AssertionError("agent_run_stream_has_no_persisted_event_ids")
    replay = await api.get(f"{path}/{identifier}/stream?after=0")
    terminal_tail = await api.get(f"{path}/{identifier}/stream?after={max(event_ids)}")
    run_before_replay = await api.get(f"{path}/{identifier}")
    run_after_replay = await api.get(f"{path}/{identifier}")
    audit_before_replay = await api.get(f"{path}/{identifier}/audit")
    audit_after_replay = await api.get(f"{path}/{identifier}/audit")
    replay_state_unchanged = (
        run_before_replay.status_code == run_after_replay.status_code == 200
        and run_after_replay.json() == run_before_replay.json()
        and audit_before_replay.status_code == audit_after_replay.status_code == 200
        and audit_before_replay.json() == audit_after_replay.json()
    )
    replay_verified = (
        replay.status_code == 200
        and terminal_tail.status_code == 200
        and replay.content == stream_content
        and not terminal_tail.content
        and replay_state_unchanged
    )
    response = await api.get(f"{path}/{identifier}")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError("agent run response must be a JSON object")
    return payload | {
        "stream": stream_text,
        "first_sse_event_ms": first_event_ms,
        "sse_replay": {
            "verified": replay_verified,
            "event_count": len(event_ids),
            "stream_sha256": hashlib.sha256(stream_content).hexdigest(),
            "repeat_sha256": hashlib.sha256(replay.content).hexdigest(),
            "empty_after_terminal": not terminal_tail.content,
            "tool_count_unchanged": replay_state_unchanged,
        },
        "elapsed_ms": int((perf_counter() - started) * 1000),
    }
