# Vehicle Intelligence Platform context

## Directory Structure Map

- `apps/api/src/vehicle_platform/api`: HTTP contracts, middleware and routes.
  `budgets.py` also bounds agent admission and request bodies before JSON decoding.
- `apps/api/src/vehicle_platform/telemetry`: canonical telemetry parsing and bounded queries.
- `apps/api/src/vehicle_platform/analysis`: deterministic pull and segment analysis.
- `apps/api/src/vehicle_platform/events`: factual event detectors and evidence.
- `apps/api/src/vehicle_platform/analytics`: Phase 5 comparisons, baselines and trends.
- `apps/api/src/vehicle_platform/acquisition`: read-only hardware collection and streaming.
  `capabilities.py` reads authenticated collector capability snapshots or operator-attested
  local preflight reports for the same vehicle/configuration/source; a recorded session alone
  never establishes source support.
- `apps/api/src/vehicle_platform/infrastructure`: database and broker infrastructure.
- `apps/api/src/vehicle_platform/observability`: sanitized logs, metrics and traces.
- `apps/api/src/vehicle_platform/mcp`: shared tool/resource registration, adapters, limits, auth and transport runtime.
- `apps/api/src/vehicle_platform/agents`: Phase 7A typed state/provider contracts, LangGraph
  orchestration through the official MCP client, temporal context, evidence/claim validation,
  agent-owned persistence, API/SSE and instrumentation.
  Persistence owns per-session connections without reuse and bounded driver cancellation cleanup.
- `apps/api/src/vehicle_platform/agents/investigation`: Phase 7B public investigation types,
  lifecycle rules, semantic provider proposals, MCP-backed existing-evidence search, Phase 4
  recipe/preflight selection, explicit approval, operator-authorized API/SSE, deterministic
  session linking, follow-up AgentRun, bounded telemetry and agent-owned optimistic persistence.
- `apps/api/migrations/versions/0009_grounded_agent.py`: additive agent run, MCP audit and
  bounded public stream event tables.
- `apps/api/migrations/versions/0010_investigation.py`: additive source preflight,
  investigation plan, session-link and replay event tables.
- `apps/api/tests`: unit and disposable database integration checks.
- `apps/web`: existing Next.js product interface.
- `apps/web/src/components/agent-workspace.tsx`: minimal vehicle agent question workspace,
  progress/SSE, grounded results, context/evidence and tool timeline, extended with the
  investigation entry point and follow-up answer navigation.
- `apps/web/src/components/investigation-workspace.tsx`: operator credential entry, candidate
  hypotheses and gaps, source/recipe review, explicit approval, session link and follow-up UI.
- `scripts/agent_fixtures.py`, `scripts/evaluate_agent_grounding.py`: controlled temporal
  fixtures and independent MCP-backed golden evaluation (12 controlled scenarios).
- `scripts/agent_runtime.py`, `scripts/agent_http_acceptance.py`,
  `scripts/agent_browser_e2e.py`: bounded local HTTP runtime and actual MCP/API/browser gates.
- `scripts/evaluate_investigation.py`: independent disposable database HTTP/MCP golden
  investigation and follow-up evaluator, including an explicit finalized-session fixture.
- `scripts/investigation_browser_e2e.py`, `apps/web/tests/e2e/investigation.spec.ts`:
  browser journey for review, explicit approval, real Phase 4 synthetic capture through
  Kafka and the stream consumer, finalized session linkage, grounded follow-up, evidence
  drilldown, and a documentation-only gap.
- `scripts/observability_investigation.py`: disposable Compose gate for delivered Phase 7B
  transition traces, Prometheus metrics and credential redaction.
- `scripts/benchmark_investigation.py`: deterministic fresh-stack plan, source, reanalysis,
  concurrency, timing, RSS and database-counter measurements.
- `scripts/benchmark_agent.py`, `scripts/agent_real_smoke.py`,
  `scripts/observability_agent.py`: deterministic resource measurements, optional real-provider
  smoke and delivered trace/metric/redaction validation.
- `infra/docker/compose.agent-test.yaml`: isolated agent/MCP/observability test stack.
- `docs/architecture/phase-7a-grounded-agent.md`, `docs/runbooks/grounded-agent.md`:
  orchestration/evidence boundaries, budgets, security boundary and operational recovery.
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
Phase 7A implements one grounded agent. Vehicle reasoning is constrained to MCP evidence;
agent-owned persistence is separate. Temporal associations never establish mechanical causation.
No vehicle control, unsupported diagnosis or RAG functionality is implemented.
Phase 7B implements a bounded investigation workflow. Its semantic needs resolve only through
known canonical signals and existing Phase 4 recipe/preflight contracts. Approval precedes
acquisition readiness; finalized session linkage creates a separate grounded follow-up run.
Phase 7C specialists and Phase 8 RAG remain deferred. Final-SHA validation evidence belongs
in docs/validation/phase-7b-acceptance.md and its traceability ledger.
See docs/validation/phase-7a-acceptance.md for checkpoint evidence and final PR-head receipts.

## Validation

Read `AGENTS.md` and scoped instructions. Use `make bootstrap`, `make check-api`,
`make check-web`, `make contracts-check`, `make docs-check`, and `make verify`.
Without a usable Docker daemon, `make verify-cloud` applies and Docker gates are CI REQUIRED.
