#!/usr/bin/env bash
# Clean disposable full-stack validation; retain existing application volumes.
set -euo pipefail
cd "$(dirname "$0")/.."
mode=${1:-committed}
[[ "$mode" == committed || "$mode" == working ]] || { echo 'Use committed or working' >&2; exit 2; }
sha=$(git rev-parse HEAD)
fingerprint=$(apps/api/.venv/bin/python scripts/validation_fingerprint.py)
export VALIDATION_STARTED_TIME
VALIDATION_STARTED_TIME=$(date +%s)
if [[ "$mode" == committed && -n "$(git status --porcelain)" ]]; then
  echo 'Committed validation requires a clean working tree' >&2
  exit 1
fi
original_project=${COMPOSE_PROJECT_NAME:-vehicle-platform}
project="vip-retrospective-${sha:0:12}-$(date -u +%Y%m%d%H%M%S)-$$"
evidence="$PWD/.validation/retrospective/runs/$project"
mkdir -p "$evidence"
original_compose=(docker compose -p "$original_project" -f compose.yaml -f infra/docker/observability/compose.yaml --profile observability)
mapfile -t running_services < <("${original_compose[@]}" ps --status running --services)
# Never use down -v against the existing application project.
"${original_compose[@]}" down > "$evidence/original-stack-stop.log" 2>&1
export COMPOSE_PROJECT_NAME=$project
export GIT_SHA=$sha
export BUILD_TIMESTAMP
BUILD_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
cleanup() {
  status=$?
  trap - EXIT
  if [[ "$status" != 0 ]]; then
    docker compose -f compose.yaml -f infra/docker/observability/compose.yaml --profile observability logs --no-color > "$evidence/failed-stack.log" 2>&1 || true
  fi
  docker compose -f compose.yaml -f infra/docker/observability/compose.yaml --profile observability down -v > "$evidence/disposable-cleanup.log" 2>&1 || status=1
  if ((${#running_services[@]})); then
    "${original_compose[@]}" up -d --no-build --wait "${running_services[@]}" > "$evidence/original-stack-restore.log" 2>&1 || status=1
  fi
  if [[ "$status" == 0 ]]; then
    if ! VALIDATION_EVIDENCE="$evidence" VALIDATION_MODE="$mode" VALIDATION_FINGERPRINT="$fingerprint" apps/api/.venv/bin/python - <<'PY'
import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path(os.environ['VALIDATION_EVIDENCE'])
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
mode = os.environ['VALIDATION_MODE']
assert mode != 'committed' or not subprocess.check_output(['git', 'status', '--porcelain'], text=True)
started = float(os.environ['VALIDATION_STARTED_TIME'])
for source in (Path('.validation/security'), Path('.validation/observability'),
               Path('.validation/summary'), Path('apps/web/test-results')):
    if not source.is_dir():
        continue
    for artifact in source.rglob('*'):
        if (artifact.is_file() and artifact.stat().st_mtime >= started
                and artifact.suffix in {'.json', '.txt', '.log', '.png', '.yaml'}):
            target = root / 'artifacts' / source.name / artifact.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(artifact, target)
manifest = {'repository_sha': sha, 'date': datetime.now(UTC).isoformat(), 'mode': mode,
            'working_tree_fingerprint': os.environ['VALIDATION_FINGERPRINT'], 'result': 'PASS', 'commands': ['make bootstrap', 'make verify'],
            'runtime': 'fresh isolated Compose project; preexisting volumes preserved',
            'files': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in root.rglob('*') if p.is_file()}}
(root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
report = Path('docs/validation/phases-0-5-retrospective-hardening.md').read_text()
(root / 'phases-0-5-retrospective-hardening.md').write_text(f'Repository SHA: `{sha}`\n\nAcceptance mode: **{mode} / PASS**\n\n' + report)
print(f'Validation evidence: {root}')
PY
    then
      status=1
    fi
  fi
  printf '%s\n' "$status" > "$evidence/exit-code.txt"
  exit "$status"
}
trap cleanup EXIT
printf 'Repository SHA: %s\nMode: %s\nProject: %s\n' "$sha" "$mode" "$project" > "$evidence/context.txt"
make bootstrap > "$evidence/bootstrap.log" 2>&1
printf 'Locked bootstrap passed; starting canonical make verify for %s\n' "$project"
make verify > "$evidence/verify.log" 2>&1
[[ "$(git rev-parse HEAD)" == "$sha" ]] || { echo 'HEAD changed during validation' >&2; exit 1; }

[[ "$(apps/api/.venv/bin/python scripts/validation_fingerprint.py)" == "$fingerprint" ]] || { echo "Working tree changed during validation" >&2; exit 1; }
