#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

project="vehicle-platform-phase9e-$$"
export TEST_KAFKA_PORT="${TEST_KAFKA_PORT:-20135}"
export MCP_TEST_PROJECT="$project"
compose=(docker compose -p "$project" -f infra/docker/compose.test.yaml)
cleanup() {
  status=$?
  if [[ "$status" -ne 0 ]]; then "${compose[@]}" logs --no-color db || true; fi
  "${compose[@]}" down -v || true
  exit "$status"
}
trap cleanup EXIT

"${compose[@]}" up -d db --wait
port=$("${compose[@]}" port db 5432 | cut -d: -f2)
export TEST_DATABASE_URL="postgresql+asyncpg://vehicle:test-only@127.0.0.1:${port}/vehicle_test"
export DATABASE_URL="$TEST_DATABASE_URL"
export ENVIRONMENT=test

(cd apps/api && .venv/bin/alembic upgrade 0016)
evidence=.validation/phase9e
mkdir -p "$evidence"
git rev-parse HEAD > "$evidence/commit.txt"
apps/api/.venv/bin/python scripts/evaluate_prediction_evidence.py \
  | tee "$evidence/evaluate_prediction_evidence.log"
