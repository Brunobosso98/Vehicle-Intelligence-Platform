#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Isolated Compose project; no production volumes and no destructive application-db resets.
project="vehicle-platform-tests-$$"
export TEST_KAFKA_PORT
TEST_KAFKA_PORT=$(apps/api/.venv/bin/python - <<'PYPORT'
import os
import socket
import subprocess
import time

# WSL's free Linux ephemeral port is not necessarily publishable by Docker Desktop.
# Verify the actual host forwarding boundary before advertising the Kafka port.
requested = os.environ.get("TEST_KAFKA_PORT")
candidates = [int(requested)] if requested else range(20001, 20033)
deadline = time.monotonic() + 60
for port in candidates:
    if not 1024 <= port <= 65535:
        raise SystemExit("TEST_KAFKA_PORT must be an unprivileged TCP port")
    try:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))
    except OSError:
        continue
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise SystemExit("Docker host forwarding setup exceeded its bounded deadline")
    probe = subprocess.run(
        ["docker", "run", "--rm", "-p", f"127.0.0.1:{port}:9094",
         "--entrypoint", "/bin/true", "vehicle-platform-kafka:local"],
        capture_output=True, text=True, timeout=remaining,
    )
    if probe.returncode == 0:
        print(port)
        break
    if "ports are not available" not in probe.stderr:
        raise SystemExit("Docker host port probe failed: " + probe.stderr)
    if time.monotonic() >= deadline:
        raise SystemExit("Docker host forwarding did not provide a usable test port")
else:
    raise SystemExit("No publishable disposable Kafka port; set TEST_KAFKA_PORT explicitly")
PYPORT
)
export KAFKA_BOOTSTRAP_SERVERS="127.0.0.1:${TEST_KAFKA_PORT}"
cleanup() {
  status=$?
  if [[ "$status" -ne 0 ]]; then docker compose -p "$project" -f infra/docker/compose.test.yaml logs --no-color; fi
  docker compose -p "$project" -f infra/docker/compose.test.yaml down -v
  exit "$status"
}
trap cleanup EXIT
docker compose -p "$project" -f infra/docker/compose.test.yaml up -d --wait
apps/api/.venv/bin/python - <<'PYBROKER'
import asyncio
import os
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import KafkaConnectionError, NodeNotReadyError

async def initialize():
    async with asyncio.timeout(60):
        while True:
            admin = AIOKafkaAdminClient(bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"])
            try:
                await admin.start()
                await admin.create_topics([NewTopic("telemetry.raw.v1", 3, 1)])
                return
            except (KafkaConnectionError, NodeNotReadyError):
                await asyncio.sleep(0.2)
            finally:
                await admin.close()
asyncio.run(initialize())
PYBROKER
port=$(docker compose -p "$project" -f infra/docker/compose.test.yaml port db 5432)
export TEST_DATABASE_URL="postgresql+asyncpg://vehicle:test-only@${port}/vehicle_test"
apps/api/.venv/bin/pytest apps/api/tests/integration -v
apps/api/.venv/bin/python scripts/benchmark_telemetry.py
