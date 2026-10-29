# Vehicle Intelligence Platform context

## Directory Structure Map

- `apps/api/src/vehicle_platform/api`: HTTP contracts, middleware and routes.
  `budgets.py` also bounds agent admission and request bodies before JSON decoding.
- `apps/api/src/vehicle_platform/telemetry`: canonical telemetry parsing and bounded queries.
- `apps/api/src/vehicle_platform/analysis`: deterministic pull and segment analysis.
- `apps/api/src/vehicle_platform/events`: factual event detectors and evidence.
- `apps/api/src/vehicle_platform/analytics`: Phase 5 comparisons, baselines and trends.
- `apps/api/src/vehicle_platform/features`: Phase 9A versioned canonical feature generation,
  provenance, cutoffs, dataset materialization, profiling and export.
- `apps/api/src/vehicle_platform/ml`: Phase 9B supervised next-pull labels, splits, training,
  trusted artifacts and offline model registry.
- `apps/api/src/vehicle_platform/anomalies`: Phase 9C detector definitions, eligible reference
  cohorts, offline fitting/scoring, artifact validation and immutable findings.
- `apps/api/src/vehicle_platform/predictions`: Phase 9D controlled HTTP inference, explicit
  serving approvals, request budgets, trusted 9B/9C adapters and immutable response receipts.
- `apps/api/src/vehicle_platform/prediction_evidence`: Phase 9E typed evidence graph, canonical
  fingerprints, bounded safe projection, immutable receipt lineage and independent verification.
- `apps/api/src/vehicle_platform/evaluation`: Phase 9G immutable offline evaluation contracts,
  chronological calibration splits, reliability/anomaly/drift metrics, source applicability,
  bounded research artifacts, and source-integrity verification. No serving wiring exists.
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
  Phase 9F adds controlled run-scoped reads of selected 9E evidence, private lineage mapping and
  deterministic structural claim rendering.
  Persistence owns per-session connections without reuse and bounded driver cancellation cleanup.
- `apps/api/src/vehicle_platform/agents/investigation`: Phase 7B public investigation types,
  lifecycle rules, semantic provider proposals, MCP-backed existing-evidence search, Phase 4
  recipe/preflight selection, explicit approval, operator-authorized API/SSE, deterministic
  session linking, follow-up AgentRun, bounded telemetry and agent-owned optimistic persistence.
- `apps/api/migrations/versions/0009_grounded_agent.py`: additive agent run, MCP audit and
  bounded public stream event tables.
- `apps/api/migrations/versions/0010_investigation.py`: additive source preflight,
  investigation plan, session-link and replay event tables.
- `apps/api/migrations/versions/0013_feature_engineering.py`,
  `0014_predictive_models.py`, and `0015_anomaly_detection.py`: additive Phase 9A/9B/9C
  persistence. Phase 9C findings and reference rows are immutable.
- `apps/api/migrations/versions/0016_prediction_service.py`: additive immutable Phase 9D serving
  bindings, lifecycle events and minimal prediction receipts.
- `apps/api/migrations/versions/0017_prediction_evidence.py`: additive Phase 9E evidence bundles,
  normalized lineage/facts/gaps and append-only verification audits.
- `apps/api/migrations/versions/0018_agent_prediction_lineage.py`: additive private mapping from
  run-local Phase 9F evidence IDs to exact 9E source and receipt lineage.
- `apps/api/migrations/versions/0019_predictive_reliability.py`: additive Phase 9G protocol/run/
  metric/candidate/applicability registry with database-enforced immutability.
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
- `scripts/evaluate_anomaly_detection.py`, `scripts/phase9c-validation.sh`: independent
  disposable-DB Phase 9C evaluator and upgrade/downgrade/re-upgrade wrapper.
- `scripts/evaluate_prediction_service.py`, `scripts/phase9d-validation.sh`: independent
  disposable-DB Phase 9D real-HTTP evaluator, migration round trip and serving-boundary checks.
- `scripts/evaluate_prediction_evidence.py`, `scripts/phase9e-validation.sh`: independent
  disposable-DB Phase 9E source/HTTP evaluator, migration round trip, immutability and budgets.
- `scripts/evaluate_agent_prediction.py`: Phase 9F integration acceptance over synthetic 9B/9C/9D/9E
  records inside the disposable Phase 9E database run.
- `scripts/evaluate_predictive_reliability.py`, `scripts/check_predictive_reliability.py`,
  `scripts/phase9g-validation.sh`: Phase 9G canonical offline evaluation, independent arithmetic/
  provenance/leakage checker, and disposable migration/database acceptance.
- `scripts/report_agent_prediction.py`: renders benchmark and observability views from the
  exact-head Phase 9F receipt without deriving measurements.
- `apps/api/tests/unit/test_anomalies.py`: focused Phase 9C detector, cutoff, abstention,
  artifact, threshold and bounded-input unit tests.
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
Phase 7C and Phase 8 are complete; Phase 7D retains its operator-accepted unified-final-suite
caveat. Evidence is in their validation reports. Phase 9A, 9B and 9C are merged; Phase 9C at
`c4da7f5` passed canonical full-validation and all CI/Security checks before PR #43 merged into
baseline `7fc4c59`. Phase 9C owns statistical deviation scoring only and does not replace Phase 3
factual events or Phase 9B next-pull labels. Phase 9D is merged and verified; historical exact-head
receipts are in its acceptance record.
Phase 9E adds immutable cutoff-aware provenance for 9D receipts and preserves 9B `NEXT_PULL`
and 9C `AFTER_PULL_OFFLINE` semantics. It adds no diagnosis, agent, MCP, UI, calibration or
ECU-control path. It is merged at baseline `466ce900988bd81e1d968eb319e970955b4011d7`; its
acceptance report and 134-section ledger record historical Phase 9E proof.
Phase 9F adds an explicitly selected, development/test-only agent read of verified 9E summaries
through a dedicated MCP capability. It preserves the 9B/9C horizons, uses low-confidence fixed
renderers and keeps exact source lineage out of provider input and public AgentRun snapshots.
See docs/validation/phase-7a-acceptance.md for checkpoint evidence and final PR-head receipts.
Phase 9G adds offline research evaluation only. It preserves 9B/9C artifacts and thresholds, 9D
serving approvals, 9E evidence, and 9F agent claims. It cannot expose calibrated values through
HTTP/MCP/agents; synthetic calibration does not establish real-world calibration or mechanical
failure probability. See the Phase 9G architecture, runbook, acceptance/evaluation reports,
traceability ledger, and ADR 0045 under `docs/`.

## Validation

Read `AGENTS.md` and scoped instructions. Use `make bootstrap`, `make check-api`,
`make check-web`, `make contracts-check`, `make docs-check`, and `make verify`.
Without a usable Docker daemon, `make verify-cloud` applies and Docker gates are CI REQUIRED.
The canonical GitHub `full-validation` workflow covers completed Phase 7/8/9A/9B/9C/9D gates and
the Phase 9E/9F disposable database evaluators;
Phase 9C adds `make test-anomalies` and `make phase9c-acceptance`. Phase 9D adds
`make test-prediction-service` and `make phase9d-acceptance`; its acceptance and canonical
Docker/full-stack checks require the Docker runner. Historical exact-head receipts are in the 9D
acceptance report.
Phase 9E adds `make test-prediction-evidence`, `make phase9e-acceptance`,
`make benchmark-prediction-evidence` and `make prediction-evidence-observability`; the database
acceptance requires the Docker runner.
Phase 9F adds `make test-prediction-agent-integration`, `make phase9f-acceptance`,
`make benchmark-prediction-agent-integration` and `make prediction-agent-observability`. Acceptance
runs in the Phase 9E disposable database and requires Docker. Its exact-head report is separate from
the 9E evaluation result.
Do not claim a gate passed without its executed receipt.
Phase 9G adds `make test-evaluation-calibration`, `make phase9g-acceptance`,
`make benchmark-predictive-reliability`, and `make predictive-reliability-observability`. The
disposable acceptance round-trips migration 0019 and verifies all three 9B tasks, four 9C families,
immutable lineage, source-table digests, artifact checks, and an independent numerical checker.
Docker-dependent results remain `CI REQUIRED` until the canonical exact-head workflow passes.

## Current implementation map

- Phase 8 knowledge retrieval lives in `apps/api/src/vehicle_platform/knowledge`; its source
  documents and local index remain separate from observed vehicle facts.
- Phase 9A features and datasets live in `features`; Phase 9B supervised labels and training live
  in `ml`. Both are merged offline foundations.
- Phase 9C anomalies reads only canonical 9A FeatureSets, keeps one vehicle/configuration/
  modification/source cohort, and persists statistical findings without fault diagnosis. No 9C
  agent, MCP, API, streaming, production promotion, or predictive UI integration exists.
- Phase 9C architecture, ADRs 0035–0038, runbook, acceptance report, evaluation report, model
  cards and traceability ledger live under `docs/architecture`, `docs/adr`, `docs/runbooks`,
  `docs/validation` and `docs/ml/anomaly-detectors`.
- Phase 9D serves approved 9B/9C versions through disabled-by-default controlled routes. It has no
  production enablement, public tenancy, arbitrary feature inputs, training, agent, MCP or UI path.
  Architecture, ADRs 0039–0042, runbook, acceptance/evaluation reports and traceability ledger are
  documented under `docs/architecture`, `docs/adr`, `docs/runbooks` and `docs/validation`. Phase 9D
  is merged and verified; historical exact-head receipts are in its acceptance report.
- Phase 9E adds migration 0017 with immutable bundles, normalized lineage and verification audits.
  It is merged at the Phase 9F baseline; see the 134-section ledger and acceptance report for its
  historical result.
- Phase 9F adds a controlled agent read of selected 9E summaries through a dedicated MCP scope,
  deterministic intent routing, structural claim validation and private lineage in migration 0018.
  It adds no production enablement, diagnosis, collection or vehicle control. See the Phase 9F
  architecture, runbook, ADR 0044, acceptance/evaluation records and 137-section traceability
  ledger under `docs/`.
- Phase 9G adds evaluation contracts, metrics, calibration, anomaly accounting, drift, and source
  applicability; migration 0019 stores immutable research evidence only. Its runner and independent
  checker live in `scripts/`; its report and 175-section ledger live under `docs/validation/`.
- Phase 9H remains planned.
