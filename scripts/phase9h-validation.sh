#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

actual_sha="$(git rev-parse HEAD)"
expected_sha="${GIT_SHA:-$actual_sha}"
if [[ "$actual_sha" != "$expected_sha" ]]; then
  echo "Expected checkout $expected_sha but found $actual_sha" >&2
  exit 1
fi
export GIT_SHA="$expected_sha"
export TEST_KAFKA_PORT="$((20000 + ($$ % 40000)))"
project="vehicle-platform-phase9h-$$"
compose=(docker compose -p "$project" -f infra/docker/compose.test.yaml)
api_pid=""
web_pid=""
evidence=.validation/phase9h
mkdir -p "$evidence/playwright" "$evidence/screenshots"
if [[ ! -f .validation/phase9g/acceptance.json ]]; then
  make phase9g-acceptance
fi
apps/api/.venv/bin/python scripts/check_phase9h_research_summary.py \
  --report .validation/phase9g/acceptance.json \
  | tee "$evidence/research-check.log"

cleanup() {
  status=$?
  [[ -z "$web_pid" ]] || kill "$web_pid" 2>/dev/null || true
  [[ -z "$api_pid" ]] || kill "$api_pid" 2>/dev/null || true
  [[ -z "$web_pid" ]] || wait "$web_pid" 2>/dev/null || true
  [[ -z "$api_pid" ]] || wait "$api_pid" 2>/dev/null || true
  if [[ "$status" -ne 0 ]]; then "${compose[@]}" logs --no-color db || true; fi
  "${compose[@]}" down -v || true
  exit "$status"
}
trap cleanup EXIT

"${compose[@]}" up -d db --wait
db_port="$("${compose[@]}" port db 5432 | cut -d: -f2)"
export DATABASE_URL="postgresql+asyncpg://vehicle:test-only@127.0.0.1:${db_port}/vehicle_test"
export TEST_DATABASE_URL="$DATABASE_URL"
export ENVIRONMENT=test
(cd apps/api && .venv/bin/alembic upgrade head)

# This acceptance uses the real 9D serving and 9E persistence paths and creates all
# authorized synthetic receipts before the read-only browser session starts.
apps/api/.venv/bin/python scripts/evaluate_prediction_evidence.py \
  | tee "$evidence/phase9e-source-run.log"
# The 9E migration round-trip intentionally ends at 0018. Restore the current
# schema before the 9H oracle snapshots every protected table, including 9G.
(cd apps/api && .venv/bin/alembic upgrade head && .venv/bin/alembic current --check-heads)
apps/api/.venv/bin/python scripts/phase9h_acceptance.py prepare --expected-sha "$expected_sha" \
  | tee "$evidence/oracle-preparation.log"
vehicle_id="$(apps/api/.venv/bin/python -c 'import json; print(json.load(open(".validation/phase9h/source-oracle.json"))["vehicle_id"])')"
vehicle_scope="$(apps/api/.venv/bin/python -c 'import json; print(",".join(json.load(open(".validation/phase9h/source-oracle.json"))["vehicle_ids"]))')"

api_port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
web_port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
api_secret="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
ui_secret="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
session_secret="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
export PREDICTION_SERVICE_ENABLED=true
export PREDICTION_OPERATOR_TOKEN="$api_secret"
export PREDICTION_OPERATOR_VEHICLE_IDS="$vehicle_scope"
export PREDICTION_TRUSTED_NETWORKS="127.0.0.1/32,::1/128"
export PREDICTION_REQUESTS_PER_MINUTE=120
export API_BASE_URL="http://127.0.0.1:${api_port}"
export PREDICTIVE_UI_ENABLED=true
export PREDICTIVE_UI_ORIGIN="http://127.0.0.1:${web_port}"
export PREDICTIVE_UI_OPERATOR_SECRET="$ui_secret"
export PREDICTIVE_UI_SESSION_SECRET="$session_secret"
export PREDICTIVE_UI_ALLOWED_VEHICLE_IDS="$vehicle_scope"
export PREDICTIVE_UI_API_ALLOWED_HOSTS=127.0.0.1
export PREDICTIVE_UI_DEMO_ENABLED=true
export PREDICTIVE_UI_COOKIE_SECURE=false

(cd apps/api && .venv/bin/uvicorn vehicle_platform.main:create_app --factory \
  --host 127.0.0.1 --port "$api_port" --no-access-log) \
  > "$evidence/api.log" 2>&1 &
api_pid=$!
for _ in $(seq 1 90); do
  if curl --silent --fail "http://127.0.0.1:${api_port}/health/live" >/dev/null; then break; fi
  sleep 1
done
curl --silent --fail "http://127.0.0.1:${api_port}/health/ready" >/dev/null

export NODE_ENV=development
(pnpm --filter @vehicle-platform/web exec next dev --webpack --hostname 127.0.0.1 --port "$web_port") \
  > "$evidence/web.log" 2>&1 &
web_pid=$!
for _ in $(seq 1 120); do
  if curl --silent --fail "$PREDICTIVE_UI_ORIGIN/predictive" >/dev/null; then break; fi
  sleep 1
done
curl --silent --fail "$PREDICTIVE_UI_ORIGIN/predictive" >/dev/null

export WEB_BASE_URL="$PREDICTIVE_UI_ORIGIN"
export PHASE9H_ORACLE="$PWD/$evidence/source-oracle.json"
export PHASE9H_SCREENSHOT_DIR="$PWD/$evidence/screenshots"
export PHASE9H_ARTIFACT_DIR="$PWD/$evidence/playwright"
pnpm --filter @vehicle-platform/web exec playwright test predictive.spec.ts \
  --project chromium --reporter=list
apps/api/.venv/bin/python scripts/phase9h_acceptance.py verify --expected-sha "$expected_sha" \
  | tee "$evidence/independent-check.log"
