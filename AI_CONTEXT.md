# Vehicle Intelligence Platform context

## Directory Structure Map

- `apps/api/src/vehicle_platform/api`: HTTP contracts, middleware and routes.
- `apps/api/src/vehicle_platform/telemetry`: canonical telemetry parsing and bounded queries.
- `apps/api/src/vehicle_platform/analysis`: deterministic pull and segment analysis.
- `apps/api/src/vehicle_platform/events`: factual event detectors and evidence.
- `apps/api/src/vehicle_platform/analytics`: Phase 5 comparisons, baselines and trends.
- `apps/api/src/vehicle_platform/acquisition`: read-only hardware collection and streaming.
- `apps/api/src/vehicle_platform/infrastructure`: database and broker infrastructure.
- `apps/api/src/vehicle_platform/observability`: sanitized logs, metrics and traces.
- `apps/api/src/vehicle_platform/mcp`: shared tool/resource registration, adapters, limits, auth and transport runtime.
- `apps/api/tests`: unit and disposable database integration checks.
- `apps/web`: existing Next.js product interface.
- `packages/contracts`: generated HTTP contracts.
- `infra/docker`, `compose.yaml`: local container runtime and observability.
- `scripts`, `Makefile`: acceptance evaluators and validation entrypoints.
- `scripts/observability-mcp.py`: actual MCP client proof of delivered Tempo traces and Prometheus metrics.
- `infra/docker/compose.mcp-test.yaml`, `scripts/mcp_container_e2e.py`: hardened disposable MCP container and official HTTP client/restart acceptance.
- `docs/architecture`, `docs/adr`, `docs/security`, `docs/validation`: boundaries and evidence.

## Business Logic & Feature Map

Vehicles/configurations/modifications and sessions currently have SQL-backed HTTP handlers.
TelemetryService owns normalization, canonical identity, ingestion and bounded windows.
AnalysisService owns pull detection; EventService owns factual event evidence.
AnalyticsService owns profiles, comparisons, repeated pulls, session summaries, baselines,
configuration comparisons and trends. AcquisitionService owns capability reports and streaming.
MCP Phase 6 adapts these application services through one official tool/resource registry,
read-only transactions, nonpersistent analytics/capability computation, bounded schemas,
SDK bearer authorization and observable stdio/HTTP runtime. See docs/architecture/phase-6-mcp-tool-platform.md.
No diagnosis, vehicle control, LLM, agent or RAG functionality is implemented.

## Validation

Read `AGENTS.md` and scoped instructions. Use `make bootstrap`, `make check-api`,
`make check-web`, `make contracts-check`, `make docs-check`, and `make verify`.
Without a usable Docker daemon, `make verify-cloud` applies and Docker gates are CI REQUIRED.
