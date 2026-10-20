#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

entrypoint="${1:-scripts/evaluate_predictive_models.py}"
shift || true
project="vehicle-platform-phase9b-$$"
export TEST_KAFKA_PORT="${TEST_KAFKA_PORT:-20134}"
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
(cd apps/api && \
  .venv/bin/alembic upgrade 0013 && \
  .venv/bin/alembic upgrade head && \
  .venv/bin/alembic downgrade 0013 && \
  .venv/bin/alembic upgrade head)
evidence=.validation/phase9b
mkdir -p "$evidence"
export GIT_COMMIT_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$GIT_COMMIT_SHA" > "$evidence/commit.txt"
if [[ "$entrypoint" == "pytest" ]]; then
  apps/api/.venv/bin/pytest "$@" | tee "$evidence/integration.log"
else
  apps/api/.venv/bin/python "$entrypoint" "$@" | tee "$evidence/$(basename "$entrypoint" .py).log"
fi
