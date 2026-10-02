#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .validation/observability
request_id="phase0-full-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
trace_id=$(printf '%032x' "${GITHUB_RUN_ID:-$RANDOM}")
span_id=$(printf '%016x' "${GITHUB_RUN_ATTEMPT:-1}")
curl -fsS -H "X-Request-ID: ${request_id}" \
  -H "traceparent: 00-${trace_id}-${span_id}-01" \
  http://127.0.0.1:8000/health/ready > .validation/observability/request.json

for attempt in {1..30}; do
  logs=$(docker compose -f compose.yaml -f infra/docker/observability/compose.yaml \
    --profile observability logs --no-color api)
  if grep -F "\"request_id\": \"${request_id}\"" <<<"$logs" | \
    grep -F "\"trace_id\": \"${trace_id}\"" \
      > .validation/observability/correlated-log.json; then break; fi
  sleep 1
done
test -s .validation/observability/correlated-log.json

for attempt in {1..30}; do
  if curl -fsS "http://127.0.0.1:3200/api/traces/${trace_id}" \
    > .validation/observability/tempo-trace.json; then break; fi
  sleep 1
done
apps/api/.venv/bin/python - <<'PY'
import json
from pathlib import Path

path = Path(".validation/observability/tempo-trace.json")
assert path.exists() and json.loads(path.read_text())["batches"]
PY

docker compose stop db
test "$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health/ready)" = 503
docker compose up -d --wait db
for query in http_server_requests_total http_server_duration_seconds_count service_readiness_failures_total; do
  curl -fsSG --data-urlencode "query=${query}" http://127.0.0.1:9090/api/v1/query \
    > ".validation/observability/prometheus-${query}.json"
done
apps/api/.venv/bin/python - <<'PY'
import json
from pathlib import Path

for path in Path(".validation/observability").glob("prometheus-*.json"):
    payload = json.loads(path.read_text())
    assert payload["status"] == "success" and payload["data"]["result"], path
PY
curl -fsS http://127.0.0.1:3001/api/health > .validation/observability/grafana-health.json
curl -fsS http://127.0.0.1:9090/-/healthy > .validation/observability/prometheus-health.txt
curl -fsS http://127.0.0.1:3200/ready > .validation/observability/tempo-health.txt
curl -fsS http://127.0.0.1:13133/ > .validation/observability/collector-health.txt

docker compose -f compose.yaml -f infra/docker/observability/compose.yaml \
  --profile observability stop otel-collector
curl -fsS http://127.0.0.1:8000/health/live > .validation/observability/api-without-collector.json
docker compose -f compose.yaml -f infra/docker/observability/compose.yaml \
  --profile observability up -d --wait otel-collector
recovery_request="${request_id}-recovered"
recovery_trace_id=$(printf '%032x' "$(( ${GITHUB_RUN_ID:-$RANDOM} + 1 ))")
curl -fsS -H "X-Request-ID: ${recovery_request}" \
  -H "traceparent: 00-${recovery_trace_id}-${span_id}-01" \
  http://127.0.0.1:8000/health/live \
  > .validation/observability/recovery-request.json
for attempt in {1..30}; do
  if curl -fsS "http://127.0.0.1:3200/api/traces/${recovery_trace_id}" \
    > .validation/observability/recovery-tempo-trace.json; then break; fi
  sleep 1
done
apps/api/.venv/bin/python - <<'PY'
import json
from pathlib import Path

path = Path(".validation/observability/recovery-tempo-trace.json")
assert path.exists() and json.loads(path.read_text())["batches"]
PY
printf 'request_id: %s\ntrace_id: %s\ncollector_recovery_request_id: %s\ncollector_recovery_trace_id: %s\n' \
  "$request_id" "$trace_id" "$recovery_request" "$recovery_trace_id" \
  > .validation/observability/evidence.yaml
echo "Full observability path verified for trace ${trace_id} and request ${request_id}."
