#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

project="vehicle-platform-phase11-$$"
export TEST_KAFKA_PORT="${TEST_KAFKA_PORT:-20136}"
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
export GIT_SHA="$(git rev-parse HEAD)"

evidence=.validation/phase11
mkdir -p "$evidence"
chmod 700 "$evidence"
artifact_root="$evidence/artifacts"
mkdir -p "$artifact_root"
chmod 700 "$artifact_root"
export PHASE9E_ARTIFACT_ROOT="$artifact_root"
export PREDICTION_MODEL_ARTIFACT_ROOT="$artifact_root/phase9b"
export PREDICTION_ANOMALY_ARTIFACT_ROOT="$artifact_root/phase9c"
export PHASE11_AGENT_PREDICTION_FIXTURE="$evidence/accepted-9e-agent-fixture.json"

(cd apps/api && .venv/bin/alembic upgrade 0016)
apps/api/.venv/bin/python scripts/evaluate_prediction_evidence.py \
  | tee "$evidence/phase9e-agent-fixture.log"
(cd apps/api && .venv/bin/alembic upgrade head)
git rev-parse HEAD > "$evidence/commit.txt"
apps/api/.venv/bin/python scripts/evaluate_agent_red_team.py \
  | tee "$evidence/evaluate_agent_red_team.log"
