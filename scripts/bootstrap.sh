#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v node >/dev/null
command -v uv >/dev/null
command -v pnpm >/dev/null
[[ "$(node -p 'process.versions.node.split(".")[0]')" == 24 ]] || { echo 'Node 24 LTS required'; exit 1; }
[[ "$(pnpm --version)" == 11.19.0 ]] || { echo 'pnpm 11.19.0 required'; exit 1; }
if [[ ! -f .env ]]; then cp .env.example .env; fi
uv sync --project apps/api --frozen
pnpm install --frozen-lockfile
