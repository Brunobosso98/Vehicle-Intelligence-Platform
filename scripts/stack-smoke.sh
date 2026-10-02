#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .validation/summary
curl -fsS http://127.0.0.1:8000/health/live > .validation/summary/api-live.json
curl -fsS http://127.0.0.1:8000/health/ready > .validation/summary/api-ready.json
curl -fsS http://127.0.0.1:3000/ > .validation/summary/web.html
curl -fsS http://127.0.0.1:3000/api/status > .validation/summary/web-api-status.json
apps/api/.venv/bin/python - <<'PY'
import json
from pathlib import Path

assert json.loads(Path(".validation/summary/api-ready.json").read_text())["database"] == "ready"
web = json.loads(Path(".validation/summary/web-api-status.json").read_text())
assert web["kind"] == "healthy" and web["ready"]["database"] == "ready"
PY
docker compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > .validation/summary/database-health.txt

# Existing contract: liveness remains available while readiness reports a DB dependency failure.
docker compose stop db
test "$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health/live)" = 200
test "$(curl -sS -o .validation/summary/readiness-db-down.json -w '%{http_code}' \
  http://127.0.0.1:8000/health/ready)" = 503
docker compose up -d --wait db
curl -fsS http://127.0.0.1:8000/health/ready > .validation/summary/api-ready-restored.json
echo "Canonical stack and dependency-failure behavior verified."
