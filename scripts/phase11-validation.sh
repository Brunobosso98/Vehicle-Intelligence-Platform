#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

project="vehicle-platform-phase11-$$"
export TEST_KAFKA_PORT="${TEST_KAFKA_PORT:-20136}"
export MCP_TEST_PROJECT="$project"
compose=(docker compose -p "$project" -f infra/docker/compose.test.yaml)
firewall_privilege=()
if [[ "$EUID" -ne 0 ]]; then
  command -v sudo >/dev/null 2>&1 || {
    echo "Phase 11 network fence requires root or sudo" >&2
    exit 1
  }
  sudo -n true || {
    echo "Phase 11 network fence requires non-interactive sudo" >&2
    exit 1
  }
  firewall_privilege=(sudo -n)
fi
firewall_chain="P11E$$"
firewall_v4_created=0
firewall_v6_created=0
cleanup() {
  status=$?
  if [[ "$firewall_v6_created" -eq 1 ]]; then
    "${firewall_privilege[@]}" ip6tables -D OUTPUT -j "$firewall_chain" 2>/dev/null || true
    "${firewall_privilege[@]}" ip6tables -F "$firewall_chain" 2>/dev/null || true
    "${firewall_privilege[@]}" ip6tables -X "$firewall_chain" 2>/dev/null || true
  fi
  if [[ "$firewall_v4_created" -eq 1 ]]; then
    "${firewall_privilege[@]}" iptables -D OUTPUT -j "$firewall_chain" 2>/dev/null || true
    "${firewall_privilege[@]}" iptables -F "$firewall_chain" 2>/dev/null || true
    "${firewall_privilege[@]}" iptables -X "$firewall_chain" 2>/dev/null || true
  fi
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
for firewall_tool in iptables ip6tables; do
  command -v "$firewall_tool" >/dev/null 2>&1 || {
    echo "Phase 11 network fence unavailable: $firewall_tool is missing" >&2
    exit 1
  }
done
"${firewall_privilege[@]}" iptables -N "$firewall_chain"
firewall_v4_created=1
"${firewall_privilege[@]}" iptables -A "$firewall_chain" -o lo -j ACCEPT
# Docker DNATs the disposable PostgreSQL loopback-published port onto its bridge.
# Match the original destination so the fence permits only this database socket.
"${firewall_privilege[@]}" iptables -A "$firewall_chain" \
  -p tcp -m conntrack --ctstate NEW,ESTABLISHED \
  --ctorigdst 127.0.0.1/32 --ctorigdstport "$port" -j ACCEPT
"${firewall_privilege[@]}" iptables -A "$firewall_chain" -j REJECT
"${firewall_privilege[@]}" iptables -I OUTPUT 1 -j "$firewall_chain"
"${firewall_privilege[@]}" ip6tables -N "$firewall_chain"
firewall_v6_created=1
"${firewall_privilege[@]}" ip6tables -A "$firewall_chain" -o lo -j ACCEPT
"${firewall_privilege[@]}" ip6tables -A "$firewall_chain" -j REJECT
"${firewall_privilege[@]}" ip6tables -I OUTPUT 1 -j "$firewall_chain"
echo "Phase 11 deterministic acceptance egress is restricted to loopback."
apps/api/.venv/bin/python scripts/evaluate_agent_red_team.py \
  | tee "$evidence/evaluate_agent_red_team.log"
