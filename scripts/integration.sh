#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Isolated Compose project; no production volumes and no destructive application-db resets.
project="vehicle-platform-tests-$$"
cleanup() {
  status=$?
  if [[ "$status" -ne 0 ]]; then docker compose -p "$project" -f infra/docker/compose.test.yaml logs --no-color; fi
  docker compose -p "$project" -f infra/docker/compose.test.yaml down -v
  exit "$status"
}
trap cleanup EXIT
docker compose -p "$project" -f infra/docker/compose.test.yaml up -d --wait
port=$(docker compose -p "$project" -f infra/docker/compose.test.yaml port db 5432)
TEST_DATABASE_URL="postgresql+asyncpg://vehicle:test-only@${port}/vehicle_test" \
  apps/api/.venv/bin/pytest apps/api/tests/integration -v
