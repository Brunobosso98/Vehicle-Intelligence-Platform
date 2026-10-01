#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export BUILDX_CONFIG="${BUILDX_CONFIG:-$PWD/.cache/buildx}"
work="$PWD/.validation/cloud-sources"
mkdir -p "$work/node-dist"
curl -fsSL https://codeload.github.com/postgres/postgres/tar.gz/refs/tags/REL_17_11 -o "$work/postgres.tar.gz"
curl -fsSL https://codeload.github.com/timescale/timescaledb/tar.gz/refs/tags/2.30.2 -o "$work/timescaledb.tar.gz"
curl -fsSL https://nodejs.org/dist/v24.19.0/node-v24.19.0-linux-x64.tar.xz -o "$work/node.tar.xz"
(cd "$work"; printf '%s  %s\n' 8b222af249d957ecec23608fe848d2dce03246121ac9b67bafb081226ea3c535 postgres.tar.gz a7003a70836477dc8d575d95a4c515d8a22ed219d0cb03b3640bb813f04e1b42 timescaledb.tar.gz 14b342e71204f811bde6153be8e04b62aef63c236fef92b55f9c83154b409647 node.tar.xz | sha256sum -c -)
tar --same-permissions --no-same-owner -xJf "$work/node.tar.xz" -C "$work/node-dist" --strip-components=1
cp infra/docker/cloud-validation/database-entrypoint.sh "$work/database-entrypoint.sh"
docker build -f infra/docker/cloud-validation/database.Dockerfile -t vehicle-platform-db:validation "$work"
docker build -f infra/docker/cloud-validation/node.Dockerfile -t vehicle-platform-node:validation "$work"
echo 'Prepared validation-only PG 17.11 / Timescale 2.30.2 and Node 24.19.0 images.'
echo 'Node fallback uses the verified Trixie base and Node 24.19.0; canonical Node image still needs Docker Hub validation.'
echo 'Run: COMPOSE_FILE=compose.yaml:infra/docker/compose.cloud-validation.yaml TEST_DB_IMAGE=vehicle-platform-db:validation make verify'
