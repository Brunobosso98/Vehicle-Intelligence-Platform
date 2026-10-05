#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# A fresh local opaque token; output contains no credentials. No retained data is reset.
export VIP_MCP_TOKEN
VIP_MCP_TOKEN=${VIP_MCP_TOKEN:-$(apps/api/.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')}
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
docker compose --profile mcp up -d --no-build --wait mcp
if [[ "${1:-}" == "--validate-observability" ]]; then
  apps/api/.venv/bin/python scripts/observability-mcp.py
fi
