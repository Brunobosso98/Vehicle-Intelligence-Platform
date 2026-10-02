#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .validation/security/images .validation/security/policy
export TRIVY_DB_REPOSITORY=ghcr.io/aquasecurity/trivy-db:2

bash scripts/security-cloud.sh

upstream_db_image="timescale/timescaledb:2.30.2-pg17@sha256:b346edcdb51a1fd6020e3965e0bd1c9f3406fa6d5fbce1e28f4852587ef934e2"
trivy image --cache-dir .cache/trivy --scanners vuln --severity HIGH,CRITICAL --exit-code 0 \
  --format json --output .validation/security/images/upstream-timescaledb.json \
  "$upstream_db_image"

apps/api/.venv/bin/python -c 'from pathlib import Path; import yaml; config=yaml.safe_load(Path("compose.yaml").read_text()); print("\n".join(dict.fromkeys(service["image"] for service in config["services"].values())))' > .validation/scan-images.txt

scan_status=0
while IFS= read -r image; do
  artifact=$(printf '%s' "$image" | tr '/:@' '____')
  report=".validation/security/images/${artifact}.json"
  policy_report=".validation/security/policy/${artifact}.json"

  if ! trivy image --cache-dir .cache/trivy --scanners vuln --severity HIGH,CRITICAL --exit-code 0 \
    --format json --output "$report" "$image"; then
    echo "Image scanner execution failed: $image" >&2
    scan_status=1
    continue
  fi

  if ! apps/api/.venv/bin/python scripts/security-policy.py \
    --image "$image" \
    --report "$report" \
    --exceptions docs/security/container-risk-acceptance.yaml \
    --output "$policy_report"; then
    echo "Security policy violation in image: $image" >&2
    scan_status=1
  fi
done < .validation/scan-images.txt

exit "$scan_status"
