#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

actual_sha="$(git rev-parse HEAD)"
expected_sha="${GIT_SHA:-$actual_sha}"
if [[ "$actual_sha" != "$expected_sha" ]]; then
  echo "Expected checkout $expected_sha but found $actual_sha" >&2
  exit 1
fi
if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
  echo "Phase 10 acceptance requires a clean exact-SHA checkout" >&2
  exit 1
fi
export GIT_SHA="$expected_sha"
export GIT_COMMIT_SHA="$expected_sha"
export ENVIRONMENT=test
export MCP_TEST_PROJECT="vehicle-platform-phase10-$$"
export TEST_KAFKA_PORT="$((20000 + ($$ % 40000)))"

project="vehicle-platform-phase10-$$"
compose=(docker compose -p "$project" -f infra/docker/compose.test.yaml)
evidence=.validation/phase10
mkdir -p "$evidence"
cleanup() {
  status=$?
  if [[ "$status" -ne 0 ]]; then "${compose[@]}" logs --no-color db || true; fi
  "${compose[@]}" down -v || true
  exit "$status"
}
trap cleanup EXIT

"${compose[@]}" up -d db --wait
port="$("${compose[@]}" port db 5432 | cut -d: -f2)"
export TEST_DATABASE_URL="postgresql+asyncpg://vehicle:test-only@127.0.0.1:${port}/vehicle_test"
export DATABASE_URL="$TEST_DATABASE_URL"

# Exercise the additive Phase 10 migration both forward and backward on an empty
# disposable database before any Phase 0-9 fixture data is created.
(cd apps/api && \
  .venv/bin/alembic upgrade 0019 && \
  .venv/bin/alembic upgrade head && \
  .venv/bin/alembic downgrade 0019 && \
  .venv/bin/alembic upgrade head && \
  .venv/bin/alembic current --check-heads)

apps/api/.venv/bin/pytest apps/api/tests/unit/test_mlops.py -q \
  | tee "$evidence/unit-tests.log"
apps/api/.venv/bin/pytest apps/api/tests/integration/test_mlops_control_plane.py -q \
  | tee "$evidence/database-tests.log"

# The database test owns its migration lifecycle and returns the disposable DB to
# base; restore the head schema before generating the Phase 9A/9B source fixtures.
(cd apps/api && .venv/bin/alembic upgrade head)

# Rebuild the Phase 9A/9B fixtures in this disposable database. The Phase 9G
# evaluator runs the canonical 9C evaluator once on this database, then Phase 10
# consumes those registered source artifacts.
apps/api/.venv/bin/python scripts/evaluate_features.py \
  | tee "$evidence/phase9a-prerequisite.log"
apps/api/.venv/bin/python scripts/evaluate_predictive_models.py \
  | tee "$evidence/phase9b-prerequisite.log"

apps/api/.venv/bin/python scripts/evaluate_mlops.py \
  | tee "$evidence/evaluator.log"
apps/api/.venv/bin/python scripts/check_mlops.py \
  --expected-sha "$expected_sha" \
  | tee "$evidence/independent-check.log"
apps/api/.venv/bin/python scripts/benchmark_mlops.py \
  | tee "$evidence/benchmark.log"
apps/api/.venv/bin/python scripts/observability_mlops.py \
  | tee "$evidence/observability.log"

printf '%s\n' "Phase 10 disposable acceptance completed for $expected_sha"
