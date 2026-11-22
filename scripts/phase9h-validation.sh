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
web_container=""
web_env_file=""
deny_env_files=()
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
  [[ -z "$web_container" ]] || docker rm -f "$web_container" >/dev/null 2>&1 || true
  for env_file in "${deny_env_files[@]}"; do rm -f "$env_file"; done
  [[ -z "$api_pid" ]] || kill "$api_pid" 2>/dev/null || true
  [[ -z "$api_pid" ]] || wait "$api_pid" 2>/dev/null || true
  [[ -z "$web_env_file" ]] || rm -f "$web_env_file" "$web_env_file.production"
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
export PREDICTIVE_UI_ORIGIN="http://localhost:${web_port}"
export PREDICTIVE_UI_OPERATOR_SECRET="$ui_secret"
export PREDICTIVE_UI_SESSION_SECRET="$session_secret"
export PREDICTIVE_UI_REQUESTS_PER_MINUTE=120
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

# Exercise the packaged standalone image itself. Its fixed NODE_ENV=production is
# part of the regression; authorization remains controlled by ENVIRONMENT=test.
docker build \
  --build-arg "GIT_SHA=$expected_sha" \
  --build-arg "BUILD_TIMESTAMP=$(git show -s --format=%cI "$expected_sha")" \
  --tag vehicle-platform-web:phase9h-validation \
  --file apps/web/Dockerfile . > "$evidence/docker-build.log" 2>&1
web_env_file="$(mktemp "$evidence/standalone-env.XXXXXX")"
chmod 600 "$web_env_file"
cat > "$web_env_file" <<EOF
NODE_ENV=production
ENVIRONMENT=test
HOSTNAME=127.0.0.1
PORT=$web_port
API_BASE_URL=http://127.0.0.1:$api_port
PREDICTION_SERVICE_ENABLED=true
PREDICTION_OPERATOR_TOKEN=$api_secret
PREDICTIVE_UI_ENABLED=true
PREDICTIVE_UI_ORIGIN=http://localhost:$web_port
PREDICTIVE_UI_OPERATOR_SECRET=$ui_secret
PREDICTIVE_UI_SESSION_SECRET=$session_secret
PREDICTIVE_UI_ALLOWED_VEHICLE_IDS=$vehicle_scope
PREDICTIVE_UI_API_ALLOWED_HOSTS=127.0.0.1
PREDICTIVE_UI_DEMO_ENABLED=true
PREDICTIVE_UI_COOKIE_SECURE=false
EOF
web_container="vip-phase9h-$RANDOM-$$"
docker run --detach --name "$web_container" --network host --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop ALL \
  --security-opt no-new-privileges:true --env-file "$web_env_file" \
  vehicle-platform-web:phase9h-validation > "$evidence/container-id.txt"
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

# Missing authorization inputs and an untrusted API peer must fail closed in
# the same packaged NODE_ENV=production runtime used by the positive browser test.
expect_standalone_denied() {
  local scenario="$1"
  local env_path="$2"
  local response_file="$evidence/${scenario}-session.json"
  [[ -z "$web_container" ]] || docker rm -f "$web_container" >/dev/null 2>&1 || true
  web_container="vip-phase9h-${scenario}-$RANDOM-$$"
  docker run --detach --name "$web_container" --network host --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop ALL \
    --security-opt no-new-privileges:true --env-file "$env_path" \
    vehicle-platform-web:phase9h-validation > "$evidence/${scenario}-container-id.txt"
  for _ in $(seq 1 120); do
    status="$(curl --silent --show-error --output "$response_file" \
      --write-out '%{http_code}' "$PREDICTIVE_UI_ORIGIN/api/predictive/session" || true)"
    if [[ "$status" == "200" ]]; then break; fi
    sleep 1
  done
  [[ "$status" == "200" ]] || {
    echo "$scenario standalone session returned HTTP $status" >&2
    return 1
  }
  apps/api/.venv/bin/python -c \
    'import json,sys; value=json.load(open(sys.argv[1])); assert value == {"enabled":False,"authenticated":False,"demoEnabled":False}, value' \
    "$response_file"
  docker rm -f "$web_container" >/dev/null
  web_container=""
}

for scenario in \
  missing-api-credential \
  missing-ui-credential \
  missing-session-credential \
  prediction-service-flag-disabled \
  predictive-ui-flag-disabled \
  vehicle-scope-missing; do
  deny_file="$evidence/${scenario}.env"
  case "$scenario" in
    missing-api-credential)
      sed '/^PREDICTION_OPERATOR_TOKEN=/d' "$web_env_file" > "$deny_file"
      ;;
    missing-ui-credential)
      sed '/^PREDICTIVE_UI_OPERATOR_SECRET=/d' "$web_env_file" > "$deny_file"
      ;;
    missing-session-credential)
      sed '/^PREDICTIVE_UI_SESSION_SECRET=/d' "$web_env_file" > "$deny_file"
      ;;
    prediction-service-flag-disabled)
      sed 's/^PREDICTION_SERVICE_ENABLED=true$/PREDICTION_SERVICE_ENABLED=false/' \
        "$web_env_file" > "$deny_file"
      ;;
    predictive-ui-flag-disabled)
      sed 's/^PREDICTIVE_UI_ENABLED=true$/PREDICTIVE_UI_ENABLED=false/' \
        "$web_env_file" > "$deny_file"
      ;;
    vehicle-scope-missing)
      sed '/^PREDICTIVE_UI_ALLOWED_VEHICLE_IDS=/d' "$web_env_file" > "$deny_file"
      ;;
  esac
  sed -i 's/^PREDICTIVE_UI_DEMO_ENABLED=true$/PREDICTIVE_UI_DEMO_ENABLED=false/' "$deny_file"
  chmod 600 "$deny_file"
  deny_env_files+=("$deny_file")
  expect_standalone_denied "$scenario" "$deny_file"
done

# The trusted-peer gate is enforced by the API against the socket peer. Start
# the API with a disjoint private network and prove loopback receives a denial.
kill "$api_pid"
wait "$api_pid" 2>/dev/null || true
api_pid=""
export PREDICTION_TRUSTED_NETWORKS="10.0.0.0/8"
(cd apps/api && .venv/bin/uvicorn vehicle_platform.main:create_app --factory \
  --host 127.0.0.1 --port "$api_port" --no-access-log) \
  > "$evidence/api-untrusted-peer.log" 2>&1 &
api_pid=$!
for _ in $(seq 1 90); do
  if curl --silent --fail "http://127.0.0.1:${api_port}/health/live" >/dev/null; then break; fi
  sleep 1
done
peer_status="$(curl --silent --show-error --output "$evidence/untrusted-peer.json" \
  --write-out '%{http_code}' -H "Authorization: Bearer $api_secret" \
  "http://127.0.0.1:${api_port}/api/v1/prediction-service/versions")"
[[ "$peer_status" == "403" ]]
apps/api/.venv/bin/python -c \
  'import json; assert json.load(open(".validation/phase9h/untrusted-peer.json"))["error"]["code"] == "PREDICTION_NETWORK_DENIED"'

# Production is fail-closed even when the standalone image has every explicit
# operator credential and flag. The protected BFF must disclose no capability.
[[ -z "$web_container" ]] || docker rm -f "$web_container" >/dev/null
web_container="vip-phase9h-production-$RANDOM-$$"
sed 's/^ENVIRONMENT=test$/ENVIRONMENT=production/' "$web_env_file" \
  | sed 's/^PREDICTIVE_UI_DEMO_ENABLED=true$/PREDICTIVE_UI_DEMO_ENABLED=false/' \
  > "$web_env_file.production"
chmod 600 "$web_env_file.production"
docker run --detach --name "$web_container" --network host --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop ALL \
  --security-opt no-new-privileges:true --env-file "$web_env_file.production" \
  vehicle-platform-web:phase9h-validation > "$evidence/production-container-id.txt"
for _ in $(seq 1 120); do
  if curl --silent --fail "$PREDICTIVE_UI_ORIGIN/predictive" >/dev/null; then break; fi
  sleep 1
done
curl --silent --fail "$PREDICTIVE_UI_ORIGIN/predictive" >/dev/null
production_session="$(curl --silent --show-error "$PREDICTIVE_UI_ORIGIN/api/predictive/session")"
printf '%s\n' "$production_session" > "$evidence/production-session.json"
apps/api/.venv/bin/python -c 'import json,sys; value=json.loads(sys.stdin.read()); assert value == {"enabled": False, "authenticated": False, "demoEnabled": False}, value' \
  <<< "$production_session"
docker rm -f "$web_container" >/dev/null
web_container=""
rm -f "$web_env_file.production"
printf '%s\n' 'NODE_ENV=production/ENVIRONMENT=test controlled flow and ENVIRONMENT=production deny verified in the standalone Docker image.' \
  > "$evidence/standalone-runtime-check.txt"
