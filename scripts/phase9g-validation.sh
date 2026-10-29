#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

project="vehicle-platform-phase9g-$$"
export MCP_TEST_PROJECT="$project"
export TEST_KAFKA_PORT="${TEST_KAFKA_PORT:-20135}"
export PHASE9G_BASE_SHA="327c63f35b4e7bc0eba31bbec81d20206be8afa2"
actual_sha="$(git rev-parse HEAD)"
expected_sha="${GIT_SHA:-$actual_sha}"
if [[ "$actual_sha" != "$expected_sha" ]]; then
  echo "Expected checkout $expected_sha but found $actual_sha" >&2
  exit 1
fi
export GIT_COMMIT_SHA="$expected_sha"
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
  .venv/bin/alembic upgrade 0018 && \
  .venv/bin/alembic upgrade head && \
  .venv/bin/alembic downgrade 0018 && \
  .venv/bin/alembic upgrade head)

evidence=.validation/phase9g
mkdir -p "$evidence"
printf '%s\n' "$GIT_COMMIT_SHA" > "$evidence/commit.txt"
apps/api/.venv/bin/python scripts/evaluate_predictive_reliability.py \
  --output "$evidence/acceptance.json" \
  | tee "$evidence/evaluation.log"
apps/api/.venv/bin/python scripts/check_predictive_reliability.py \
  "$evidence/acceptance.json" \
  --expected-sha "$GIT_COMMIT_SHA" \
  | tee "$evidence/independent-check.log"
