# MCP server

Run `make bootstrap` first. Python 3.12, Node 24 and the locked dependencies are required.

## Local stdio

```sh
DATABASE_URL=postgresql+asyncpg://vehicle:local-development-only@127.0.0.1:5432/vehicle \
  apps/api/.venv/bin/vehicle-mcp --transport stdio
```

Configure a desktop/IDE host to launch that executable with the database environment. Stdout is
reserved for protocol messages; logs go to stderr. The process owner is trusted. No bearer token
is needed. Tools and database access remain read-only and bounded.

## Streamable HTTP

Supply an opaque token of at least 32 characters through secret configuration, never a CLI argument.
The verifier grants `VIP_MCP_TOKEN_SCOPE` (default `mcp:read`) and checks optional
`VIP_MCP_TOKEN_EXPIRES_AT` (Unix seconds). It never issues tokens. Missing/invalid/expired tokens
receive 401; insufficient scope receives 403. Rotate by updating the configured token and restarting.

```sh
export VIP_MCP_TOKEN
VIP_MCP_TOKEN=$(apps/api/.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')
apps/api/.venv/bin/vehicle-mcp --transport streamable-http
```

Default endpoint: `http://127.0.0.1:8001/mcp`. Add `Authorization: Bearer <configured token>`
to the official client's HTTP transport. Origin/Host restrictions prevent DNS rebinding.
Set `VIP_MCP_PORT`, `VIP_MCP_HOST`, `VIP_MCP_RESOURCE_URL`, `VIP_MCP_ISSUER_URL` explicitly
for a deployed resource server. Public issuer/resource URLs require HTTPS; operators provision TLS,
network restrictions and database credentials. Token discovery does not expose the token.
This is one trusted reader capability for all vehicles, not a multi-tenant authorization system.

## Docker

```sh
make containers up
make mcp-up
```

The optional `mcp` Compose profile reuses the API image. `mcp-up` provisions a fresh token when
none is supplied; provide `VIP_MCP_TOKEN` explicitly when a host needs the same known token.
The container binds internally to 0.0.0.0; host publication is loopback only. Filesystem is read-only,
capabilities are dropped and privilege escalation is disabled. `/ready` checks TimescaleDB, rather
than merely an open port. `/metrics` contains aggregate metrics without credentials or entity IDs.

## Limits and troubleshooting

Lists: 100; comparisons: 20 pulls; cross-session: 10 sessions; analytics source: 500k observations.
Telemetry: eight explicit signals, sixty seconds, one thousand samples. Calls: eight simultaneous,
10s execution, 5s statements, 1s locks. HTTP bodies: 64 KiB. Tool results: 512 KiB including both
SDK text and structured content. Oversized requests/results fail visibly. Reduce selection/window
on `RESULT_TOO_LARGE`; narrow historical context for insufficient evidence. No list cursors exist.

On `BACKEND_UNAVAILABLE`, inspect readiness and sanitized logs using the request correlation ID.
Restore database connectivity; a client can retry without modifying canonical state. Reconnect after
server restart; no durable MCP session/audit table is required. Do not reset application volumes.

## Validation

`make test-mcp` runs unit checks. `make phase6-acceptance`, `make test-mcp-e2e` and
`make benchmark-mcp` each provision their own disposable Timescale database, apply migrations,
seed controlled application fixtures and clean only their Compose project. `vehicle_test*` is
mandatory. E2E launches actual stdio and HTTP subprocesses, validates scope/expiry/origin/body limits,
concurrency, backend recovery and restart/reconnect. `make verify` includes the full MCP gates.

After `make observability-up`, `make mcp-observability` starts MCP and invokes
`scripts/observability-mcp.py` with the
runtime token kept in the process environment. It proves an official HTTP client
call reaches Tempo with MCP and database spans and reaches Prometheus with a tool
counter. Sanitized evidence is written under `.validation/observability`.
Disposable MCP acceptance reports and their checkout SHA are under `.validation/mcp`.

The Kafka healthcheck still executes the broker's topic-list protocol operation.
Its 15-second deadline includes cold JVM startup: local WSL measurements took
6.65–8.10 seconds while the Python admin client answered in 33 milliseconds.

HTTP E2E additionally runs `scripts/mcp_container_e2e.py` against the hardened
API/MCP image with an isolated database and ephemeral host port, exercises the
same 22-tool inventory and resources, then restarts the container and reconnects.
