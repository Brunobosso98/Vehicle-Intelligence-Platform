#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .validation/security
export TRIVY_DB_REPOSITORY=ghcr.io/aquasecurity/trivy-db:2
for command in gitleaks trivy; do
  command -v "$command" >/dev/null || {
    echo "$command required; run bash scripts/install-security-tools.sh" >&2
    exit 1
  }
done
gitleaks dir . --redact --config .gitleaks.toml --report-format json \
  --report-path .validation/security/gitleaks.json
uv export --project apps/api --frozen --no-dev --no-emit-project \
  --format requirements-txt --output-file .validation/security/requirements.txt
apps/api/.venv/bin/pip-audit -r .validation/security/requirements.txt \
  --require-hashes --disable-pip --format=json \
  --output=.validation/security/python-audit.json
pnpm audit --prod --audit-level high --json > .validation/security/node-audit.json
trivy fs --cache-dir .cache/trivy --scanners vuln,misconfig --severity HIGH,CRITICAL \
  --exit-code 1 --skip-dirs .git,node_modules,apps/api/.venv,.cache,.validation \
  --format json --output .validation/security/filesystem.json .
echo "Cloud security checks passed."
