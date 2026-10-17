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
apps/api/.venv/bin/python scripts/check_knowledge_security.py
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "Local credential file must never be tracked in Git." >&2
  exit 1
fi
gitleaks dir . --redact --config .gitleaks.toml --report-format json \
  --report-path .validation/security/gitleaks.json
uv export --project apps/api --frozen --no-dev --no-emit-project \
  --format requirements-txt --output-file .validation/security/requirements.txt
apps/api/.venv/bin/pip-audit -r .validation/security/requirements.txt \
  --require-hashes --disable-pip --format=json \
  --output=.validation/security/python-audit.json
pnpm audit --prod --audit-level high --json > .validation/security/node-audit.json
scan_args=(fs --scanners vuln,misconfig --severity HIGH,CRITICAL --exit-code 1 --no-progress
  --skip-dirs '.git,**/node_modules,**/.venv,**/.next,**/coverage,**/test-results,**/playwright-report,.cache,.validation,.kilo,.impeccable'
  --format json)
if [[ "${TRIVY_FS_IN_CONTAINER:-0}" == 1 ]]; then
  # Go-git's worktree status can traverse ignored Windows dependency caches before Trivy's
  # exclusions apply. Mask only .git (already outside scan scope); read the SAME source files.
  docker info >/dev/null
  scanner_cache="${TRIVY_CACHE_DIR:-$PWD/.cache/trivy}"
  mkdir -p "$scanner_cache" .cache/trivy-empty-git
  git rev-parse HEAD > .validation/security/filesystem-commit.txt
  docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
    --tmpfs /tmp:mode=1777 \
    --mount "type=bind,source=$PWD,target=/workspace,readonly" \
    --mount "type=bind,source=$PWD/.cache/trivy-empty-git,target=/workspace/.git,readonly" \
    --mount "type=bind,source=$(command -v trivy),target=/usr/local/bin/trivy,readonly" \
    --mount "type=bind,source=$scanner_cache,target=/scanner-cache" \
    --mount "type=bind,source=$PWD/.validation/security,target=/reports" \
    --workdir /workspace --entrypoint /usr/local/bin/trivy vehicle-platform-api:local \
    "${scan_args[@]}" --cache-dir /scanner-cache --output /reports/filesystem.json .
else
  trivy "${scan_args[@]}" --cache-dir "${TRIVY_CACHE_DIR:-.cache/trivy}" \
    --output .validation/security/filesystem.json .
fi
echo "Cloud security checks passed."
