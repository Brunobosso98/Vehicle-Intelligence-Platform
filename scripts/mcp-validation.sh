#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
project="vehicle-platform-mcp-tests-$$"
export TEST_KAFKA_PORT=20032
export MCP_TEST_PROJECT="$project"
cleanup() {
  status=$?
  if [[ "$status" -ne 0 ]]; then docker compose -p "$project" -f infra/docker/compose.test.yaml logs --no-color db; fi
  docker compose -p "$project" -f infra/docker/compose.test.yaml down -v
  exit "$status"
}
trap cleanup EXIT
services=(db)
if [[ "${1:-}" == "scripts/investigation_browser_e2e.py" ]]; then
  services+=(broker)
fi
docker compose -p "$project" -f infra/docker/compose.test.yaml up -d "${services[@]}" --wait
if [[ "${1:-}" == "scripts/investigation_browser_e2e.py" ]]; then
  docker compose -p "$project" -f infra/docker/compose.test.yaml exec -T broker /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --if-not-exists --topic telemetry.raw.v1 --partitions 3 --replication-factor 1
  export KAFKA_BOOTSTRAP_SERVERS="127.0.0.1:${TEST_KAFKA_PORT}"
fi
port=$(docker compose -p "$project" -f infra/docker/compose.test.yaml port db 5432 | cut -d: -f2)
export TEST_DATABASE_URL="postgresql+asyncpg://vehicle:test-only@127.0.0.1:${port}/vehicle_test"
export DATABASE_URL="$TEST_DATABASE_URL"
export ENVIRONMENT=test
(cd apps/api && .venv/bin/alembic upgrade head)
entrypoint="${1:-scripts/evaluate_mcp.py}"
evidence=.validation/mcp
case "$entrypoint" in
  scripts/*agent*|scripts/*grounding*) evidence=.validation/agent ;;
  scripts/*investigation*) evidence=.validation/investigation ;;
esac
mkdir -p "$evidence"
git rev-parse HEAD > "$evidence/commit.txt"
apps/api/.venv/bin/python "$entrypoint" | tee "$evidence/$(basename "$entrypoint" .py).log"
