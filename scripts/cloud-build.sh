#!/usr/bin/env bash
# Managed cloud CA is supplied transiently; do not copy it into images.
set -euo pipefail
cd "$(dirname "$0")/.."
export BUILDX_CONFIG="${BUILDX_CONFIG:-$PWD/.cache/buildx}"
ca_bundle=/etc/ssl/certs/ca-certificates.crt
docker build --secret "id=proxy_ca,src=$ca_bundle" -f apps/api/Dockerfile -t vehicle-platform-api:local .
docker build --secret "id=proxy_ca,src=$ca_bundle" -f apps/web/Dockerfile -t vehicle-platform-web:local .
