#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .validation/security/images
export TRIVY_DB_REPOSITORY=ghcr.io/aquasecurity/trivy-db:2
bash scripts/security-cloud.sh
apps/api/.venv/bin/python -c 'from pathlib import Path; import yaml; config=yaml.safe_load(Path("compose.yaml").read_text()); print("\n".join(dict.fromkeys(service["image"] for service in config["services"].values())))' > .validation/scan-images.txt
while IFS= read -r image; do
  artifact=$(printf '%s' "$image" | tr '/:@' '____')
  trivy image --cache-dir .cache/trivy --severity HIGH,CRITICAL --exit-code 1 \
    --format json --output ".validation/security/images/${artifact}.json" "$image"
done < .validation/scan-images.txt
