#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .validation
export TRIVY_DB_REPOSITORY=ghcr.io/aquasecurity/trivy-db:2
for command in gitleaks trivy; do
  command -v "$command" >/dev/null || { echo "$command required; see docs/security/automation.md" >&2; exit 1; }
done
gitleaks dir . --redact --config .gitleaks.toml
uv export --project apps/api --frozen --no-dev --no-emit-project --format requirements-txt --output-file .validation/requirements.txt
apps/api/.venv/bin/pip-audit -r .validation/requirements.txt --require-hashes --disable-pip
pnpm audit --prod --audit-level high
trivy fs --cache-dir .cache/trivy --scanners vuln,misconfig --severity HIGH,CRITICAL --exit-code 1 --skip-dirs .git,node_modules,apps/api/.venv,.cache,.validation .
apps/api/.venv/bin/python -c 'from pathlib import Path; import yaml; config=yaml.safe_load(Path("compose.yaml").read_text()); print("\n".join(dict.fromkeys(service["image"] for service in config["services"].values())))' > .validation/scan-images.txt
while IFS= read -r image; do
  trivy image --cache-dir .cache/trivy --severity HIGH,CRITICAL --exit-code 1 "$image"
done < .validation/scan-images.txt
