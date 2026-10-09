# Graph Report - vehicle-intelligence-platform  (2026-10-09)

## Corpus Check
- 314 files · ~245,271 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: (none) 12, .Dockerfile 2, .example 1)

## Summary
- 3130 nodes · 7796 edges · 199 communities (145 shown, 54 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 1388 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9d547ece`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AnalyticsConfig
- test_acquisition.py
- DetectorProfile
- router
- api/routes.py
- BoundedSpool
- acquisition/service.py
- RawTelemetryRecord
- DatabaseProbe
- DeviceCapabilities
- acquisition/cli.py
- Adapter
- AlignedFrame
- alembic
- json
- core/config.py
- PlatformError
- events/synthetic.py
- StreamConsumer
- AgentError
- web/package.json
- Phase 4 — Streaming & Live Vehicle Acquisition
- live-acquisition.tsx
- Phase 5 — Automotive Analytics
- register_tools
- vehicle-workspace.tsx
- test_gateway_publisher_classifies_responses
- normalize_value
- evaluate_agent_grounding.py
- Phase 7A — Agent Core & Grounded Orchestration
- test_mcp.py
- Telemetry
- status.test.tsx
- test_elm_tcp_transport_connects_reads_reuses_and_closes
- compilerOptions
- detectors.py
- main.py
- analytics-workspace.tsx
- server.py
- next
- CorrelationMiddleware
- Elm327Adapter
- devDependencies
- telemetry.test.tsx
- What You Must Do When Invoked
- ._run
- package.json
- AgentSettings
- budgets.py
- observability-validation.sh
- UUID
- api/errors.py
- Phase 7B — Investigation & Adaptive Logging
- asyncio
- test_agent_runtime.py
- Catalog
- orchestration.py
- MappedCSVTelemetrySource
- observability-smoke.py
- scripts
- security-policy.py
- mcp-validation.sh
- test_agents.py
- README.md
- PHASE 0 COMPLETION REPORT
- telemetry/service.py
- integration.sh
- retrospective-validation.sh
- next-env.d.ts
- 113. Final delivery report
- cloud-build.sh
- cloud-validation.sh
- wait-http.sh
- mcp-up.sh
- security.sh
- security-cloud.sh
- acquisition/__init__.py
- analysis/__init__.py
- analytics/__init__.py
- events/__init__.py
- infrastructure/__init__.py
- vehicle_platform/__init__.py
- mcp/__init__.py
- observability/__init__.py
- telemetry/__init__.py
- database-entrypoint.sh
- bootstrap.sh
- install-security-tools.sh
- Container scan findings — 2026-10-01
- vehicle-platform-api
- 126. Final delivery report
- 45. Required synthetic scenarios
- .read_resource
- 73. Definition of Done
- agent-workspace.test.tsx
- CSVSignalColumn
- Phases 0–5 retrospective hardening
- graphify reference: extra exports and benchmark
- investigation/service.py
- InvestigationPlan
- pull_request_template.md
- test_agent_repository.py
- env.py
- Phase 5 automotive analytics
- ADR 0018: Read-only MCP application adapter
- N55 Intelligence Lab
- ADR 0001: Modular monolith first
- ADR 0002: Polyglot toolchain
- ADR 0003: TimescaleDB foundation
- ADR 0004: OpenTelemetry observability
- ADR 0005: Generated versioned contracts
- ADR 0006: Codex context and skills
- ADR 0007: Trunk-based development
- ADR 0008: ESLint 10 compatibility bridge
- ADR 0009: Runtime base security and cloud validation
- ADR 0010: Harden the pinned TimescaleDB runtime
- ADR 0011: Canonical telemetry storage and retry identity
- Phase 4 acquisition threats
- Phase 3 event and anomaly engine
- 55. Required test layers
- benchmark_stream_live.py
- ADR 0012: Versioned deterministic session analysis
- ADR 0013: Deterministic evidence-first event architecture
- pytest
- ADR 0019: Grounded agent state and evidence
- test_investigation.py
- Phase 3 events
- 75. API surface
- 85. Unit and contract tests
- investigation/routes.py
- MCP server
- Phase 6 acceptance evidence
- Vehicle Intelligence Platform context
- Phase 1 vehicle and telemetry core
- Phase 2 session and pull analysis
- 94. Failure behavior
- strategy.md
- adr.md
- migrations.md
- definition-of-done.md
- gates.md
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- mcp/cli.py
- EventEngine
- 15. Required acquisition adapters
- Vehicle Intelligence Platform / N55 Intelligence Lab
- SyntheticLiveAdapter
- graphify reference: GitHub clone and cross-repo merge
- 101. ADRs
- Phase 7A acceptance
- graphify reference: query, path, explain
- api/AGENTS.md
- agents/__init__.py
- web/AGENTS.md
- extraction-spec.md
- data-principles.md
- quality-attributes.md
- versioning.md
- github.md
- database-not-ready.md
- local-stack-not-starting.md
- migration-failure.md
- phase-2-baseline.md
- Process
- infra/AGENTS.md
- contracts/AGENTS.md
- contracts/README.md
- SECURITY.md
- validation_fingerprint.py
- investigation_router
- ref_next_types_root_params_d_ts
- ref_next_types_routes_d_ts
- resolve_context
- main
- Live acquisition operations and physical validation
- Validation evidence — 2026-10-01
- service_fixture
- architecture/phase-6-mcp-tool-platform.md
- 98. Phase 7B Definition of Done
- test_investigation_repository.py
- auth.py
- @playwright/test
- ReadOnlyDatabase
- Phase 7B acceptance
- InvestigationError
- .export
- ADR 0020: Investigation recipe and approval boundary
- ADR 0015: Versioned recipes and acquisition lifecycle
- Phase 7A grounded agent
- test_timeout_size_rate_and_spans
- phase-7a-traceability-ledger.md
- 45. Investigation examples
- check_coverage.py
- investigation/__init__.py

## God Nodes (most connected - your core abstractions)
1. `AgentError` - 132 edges
2. `Phase 4 — Streaming & Live Vehicle Acquisition` - 128 edges
3. `router()` - 126 edges
4. `Phase 5 — Automotive Analytics` - 115 edges
5. `Phase 7B — Investigation & Adaptive Logging` - 100 edges
6. `Telemetry` - 80 edges
7. `Settings` - 76 edges
8. `Phase 7A — Agent Core & Grounded Orchestration` - 75 edges
9. `InvestigationService` - 62 edges
10. `RawTelemetryRecord` - 59 edges

## Surprising Connections (you probably didn't know these)
- `Boundaries and flow` --references--> `VehicleDataAdapter`  [INFERRED]
  docs/architecture/phase-4-live-acquisition.md → apps/api/src/vehicle_platform/acquisition/adapters.py
- `Collector CLI guarantees` --references--> `preflight()`  [INFERRED]
  docs/runbooks/live-acquisition.md → apps/api/src/vehicle_platform/acquisition/domain.py
- `Collector heartbeat and acquisition context` --references--> `collector_health()`  [INFERRED]
  docs/architecture/phase-4-live-acquisition.md → apps/api/src/vehicle_platform/acquisition/quality.py
- `Execution and lifecycle` --references--> `AgentSettings`  [INFERRED]
  docs/architecture/phase-7a-grounded-agent.md → apps/api/src/vehicle_platform/agents/config.py
- `Domain and persistence` --references--> `InvestigationPlan`  [INFERRED]
  docs/architecture/phase-7b-investigation-adaptive-logging.md → apps/api/src/vehicle_platform/agents/investigation/domain.py

## Import Cycles
- None detected.

## Communities (199 total, 54 thin omitted)

### Community 0 - "AnalyticsConfig"
Cohesion: 0.08
Nodes (65): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+57 more)

### Community 1 - "test_acquisition.py"
Cohesion: 0.12
Nodes (19): capabilities(), parametrize, test_collector_health_distinguishes_transport_and_sampling(), test_extended_synthetic_modes_have_measured_behavior(), test_gateway_heartbeat_is_scoped_and_failures_are_explicit(), post(), test_golden_synthetic_scenarios(), test_heartbeat_rejects_naive_or_prestart_sample_receipt() (+11 more)

### Community 2 - "DetectorProfile"
Cohesion: 0.11
Nodes (35): align_observations(), Align by deterministic last-value carry-forward, expiring at max_gap. Duplicate…, rolling_median(), HeuristicSegmentDetector, DetectorProfile, Observation, StrEnum, Heuristic defaults, not manufacturer calibration data. (+27 more)

### Community 3 - "router"
Cohesion: 0.11
Nodes (53): SessionAnalysisService, APIRouter, router(), analytics_config(), analyze_repeated_pulls(), analyze_session(), analyze_session_events(), assess_session_capabilities() (+45 more)

### Community 4 - "api/routes.py"
Cohesion: 0.09
Nodes (42): AcquisitionHeartbeat, AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement, AnalysisRequest, AnalyticsRequest, CollectorHealthResponse, CollectorReportedState (+34 more)

### Community 5 - "BoundedSpool"
Cohesion: 0.10
Nodes (15): BoundedSpool, Path, Single-collector atomic acknowledgement, only after successful publish., Path, test_bounded_spool_replays_and_reports_overflow(), test_collector_rejects_unbounded_configuration(), test_collector_reports_actual_recovery_metrics_and_payload_free_spans(), test_collector_retries_spools_and_replays_without_loss() (+7 more)

### Community 6 - "acquisition/service.py"
Cohesion: 0.14
Nodes (24): assess_dataset(), collector_health(), DatasetCapability, measure_signal_quality(), datetime, Infer transport/sampling freshness only from an authenticated report. Event…, SignalQuality, AcquisitionAuthError (+16 more)

### Community 7 - "RawTelemetryRecord"
Cohesion: 0.09
Nodes (19): Read-only adapter contract. Deliberately has no command/write operation., ReplayAdapter, VehicleDataAdapter, AcquisitionCollector, report(), report_periodically(), CollectorStats, Hardware-near bounded collector with retry, backpressure, and disk replay. (+11 more)

### Community 9 - "DeviceCapabilities"
Cohesion: 0.13
Nodes (42): DeviceCapabilities, Importance, LoggingRecipe, plan_sampling(), preflight(), PreflightResult, Priority, StrEnum (+34 more)

### Community 10 - "acquisition/cli.py"
Cohesion: 0.14
Nodes (23): adapter_for(), AdapterKind, devices(), execute(), _preflight(), preflight_command(), probe(), Path (+15 more)

### Community 11 - "Adapter"
Cohesion: 0.15
Nodes (19): Adapter, MCPSettings, BaseSettings, model_validator, create_server(), pull(), session(), vehicle() (+11 more)

### Community 12 - "AlignedFrame"
Cohesion: 0.19
Nodes (27): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, PullWindow, StrEnum (+19 more)

### Community 13 - "alembic"
Cohesion: 0.08
Nodes (3): alembic, upgrade(), sqlalchemy_dialects

### Community 14 - "json"
Cohesion: 0.10
Nodes (31): aiokafka, StandardPid, Prevent database driver messages and SQL text from leaving the process., validate_sequence(), Explicit generic CSV mapping; no proprietary exporter assumptions., asyncpg, collections_abc, csv (+23 more)

### Community 15 - "core/config.py"
Cohesion: 0.07
Nodes (28): Protocol, Read-only connection defaults also bound queries before a transaction begins., Terminable, httpx2, mcp, mcp_client_streamable_http, Representative MCP reads measured through the SDK against disposable canonical…, evaluate() (+20 more)

### Community 16 - "PlatformError"
Cohesion: 0.21
Nodes (10): Any, Entity, UUID, PlatformError, Exception, BaseModel, Warning, compare_configurations() (+2 more)

### Community 17 - "events/synthetic.py"
Cohesion: 0.17
Nodes (21): evaluate_events(), EventClassMetrics, EventEvaluation, _overlaps(), One-to-one deterministic matching by type, pull and temporal overlap., anomaly_scenario(), AnomalyInjection, EventScenario (+13 more)

### Community 18 - "StreamConsumer"
Cohesion: 0.39
Nodes (3): UUID, StreamConsumer, test_provisional_window_is_event_time_bounded_without_discarding_canonical_input()

### Community 19 - "AgentError"
Cohesion: 0.12
Nodes (19): canonical_hash(), EvidenceRegistry, facts(), Any, UUID, MCPClient, Any, AsyncClient (+11 more)

### Community 20 - "web/package.json"
Cohesion: 0.11
Nodes (18): dependencies, next, react, react-dom, name, private, type, version (+10 more)

### Community 21 - "Phase 4 — Streaming & Live Vehicle Acquisition"
Cohesion: 0.02
Nodes (122): 100. BimmerLink status, 102. Repository context and reusable workflows, 103. Make targets and regression gates, 104. Migration guard in CI, 105. Canonical Docker validation, 106. Golden live scenarios, 107. Acceptance — loss and duplication, 108. Acceptance — recipes (+114 more)

### Community 22 - "live-acquisition.tsx"
Cohesion: 0.10
Nodes (13): Acquisition, CollectorReport, Finalized, LiveAcquisition(), LiveFinding, LivePoint, LiveSnapshot, Pipeline (+5 more)

### Community 23 - "Phase 5 — Automotive Analytics"
Cohesion: 0.02
Nodes (113): 100. ADR, 101. AGENTS.md / repository workflow, 102. Make targets, 103. CI regression protection, 104. Push early, 105. Pull request, 106. GitHub workflow behavior, 107. Do not repeat the premature Phase 4 completion behavior (+105 more)

### Community 24 - "register_tools"
Cohesion: 0.10
Nodes (19): MCPServer, register_tools(), get_pull_summary(), get_repeated_pull_analysis(), get_session_analytics(), get_session_capabilities(), get_session_summary(), get_telemetry_window() (+11 more)

### Community 25 - "vehicle-workspace.tsx"
Cohesion: 0.08
Nodes (27): AgentEvent, AgentRun, Audit, AgentRun, Investigation, InvestigationWorkspace(), terminal, DetectedEvent (+19 more)

### Community 26 - "test_gateway_publisher_classifies_responses"
Cohesion: 0.12
Nodes (8): Exception, MonkeyPatch, test_consumer_database_failure_exits_without_sql_inputs(), fail(), test_gateway_publisher_classifies_responses(), test_gateway_transport_errors_enter_retry_spool_path(), test_spool_failed_atomic_ack_preserves_original(), CaptureFixture

### Community 27 - "normalize_value"
Cohesion: 0.09
Nodes (32): UUID, RawTelemetryMessage, DataQuality, NormalizationError, normalize_value(), parse_timestamp(), datetime, StrEnum (+24 more)

### Community 28 - "evaluate_agent_grounding.py"
Cohesion: 0.20
Nodes (10): mcp_client_stdio, domain_fingerprint(), Any, Aggregate content changes, including updates, in disposable fixture tables., evaluate(), connection(), main(), Independent Phase 7A evaluator: actual MCP stdio, real DB/API, fixed golden… (+2 more)

### Community 29 - "Phase 7A — Agent Core & Grounded Orchestration"
Cohesion: 0.03
Nodes (72): 10. Agent state, 11. AgentRun persistence, 12. ToolCall persistence / audit trail, 13. Evidence model, 14. Claim → Evidence grounding, 15. Unsupported-claim detection, 16. Structured answer contract, 17. Natural-language API (+64 more)

### Community 30 - "test_mcp.py"
Cohesion: 0.16
Nodes (15): model_validator, Window, parametrize, test_actual_response_limit_and_unknown_tool(), big(), test_adapter_isolation_and_envelope(), test_analytics_selection_reports_truncation(), test_http_requires_token() (+7 more)

### Community 31 - "Telemetry"
Cohesion: 0.04
Nodes (61): AIOKafkaProducer, AcquisitionPublisher, Application-owned producer; bounded concurrent publication and shutdown., main(), BaseSettings, datetime, model_validator, Settings (+53 more)

### Community 32 - "status.test.tsx"
Cohesion: 0.17
Nodes (13): dynamic, GET(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready, SystemStatus (+5 more)

### Community 33 - "test_elm_tcp_transport_connects_reads_reuses_and_closes"
Cohesion: 0.15
Nodes (3): ElmTcpTransport, Concrete ELM327 TCP/RFCOMM bridge transport with a strict read-only command…, test_elm_tcp_transport_connects_reads_reuses_and_closes()

### Community 34 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 35 - "detectors.py"
Cohesion: 0.21
Nodes (10): compute_pull_metrics(), HeuristicPullDetector, _mean(), PullDetector, Protocol, SegmentDetector, _slope(), DetectedPull (+2 more)

### Community 36 - "main.py"
Cohesion: 0.08
Nodes (26): AgentInstrumentation, connect(), AgentRepository, AsyncSession, Protocol, UUID, Commit terminal state and stream event together; reconnect cannot race…, Only agent-owned tables. Vehicle existence is resolved through MCP, never SQL. (+18 more)

### Community 37 - "analytics-workspace.tsx"
Cohesion: 0.13
Nodes (11): AnalyticsWorkspace(), history(), Configuration, curveLabels, NormalizedBin, Profile, Pull, request() (+3 more)

### Community 38 - "server.py"
Cohesion: 0.21
Nodes (13): ErrorCode, StrEnum, ToolError, UUID, tool_error(), Instrumentation, call(), P (+5 more)

### Community 39 - "next"
Cohesion: 0.18
Nodes (6): config, GET, POST, apps_web_src_app_globals, metadata, next

### Community 40 - "CorrelationMiddleware"
Cohesion: 0.18
Nodes (8): CorrelationMiddleware, ASGIApp, Receive, Scope, Send, PlatformAPI, ASGIApp, FastAPI

### Community 41 - "Elm327Adapter"
Cohesion: 0.11
Nodes (11): Elm327Adapter, ElmTransport, Protocol, Generic standard-mode OBD-II reader; no proprietary or write commands., FakeElm, test_elm327_only_uses_allowlisted_read_commands(), test_elm_recovers_timeout_without_reusing_sequence(), immediate() (+3 more)

### Community 42 - "devDependencies"
Cohesion: 0.12
Nodes (16): devDependencies, @axe-core/playwright, eslint, @eslint/compat, eslint-config-next, jsdom, @playwright/test, @testing-library/jest-dom (+8 more)

### Community 43 - "telemetry.test.tsx"
Cohesion: 0.10
Nodes (14): VehicleWorkspace(), FakeEventSource, vehicle, detectedEvent, pull, segment, session, signals (+6 more)

### Community 44 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 45 - "._run"
Cohesion: 0.27
Nodes (5): AnalysisLimitError, UUID, ValueError, AnalysisResult, Pull

### Community 46 - "package.json"
Cohesion: 0.11
Nodes (18): devDependencies, openapi-typescript, prettier, engines, node, name, packageManager, private (+10 more)

### Community 47 - "AgentSettings"
Cohesion: 0.12
Nodes (26): AgentSettings, BaseSettings, model_validator, OpenAIProvider, ModelInput, ModelTurn, ToolRequest, Usage (+18 more)

### Community 48 - "budgets.py"
Cohesion: 0.12
Nodes (17): ASGIApp, Constant-memory local request budgets for the Phase 4 resource boundaries., Per-process budgets, with no unbounded per-client identifier dictionaries. The…, ResourceBudgetMiddleware, TokenBucket, parametrize, Scope, request_scope() (+9 more)

### Community 49 - "observability-validation.sh"
Cohesion: 0.40
Nodes (4): scripts_lib_wait_http_sh, observability-validation.sh script, wait_prometheus_query(), stack-smoke.sh script

### Community 51 - "api/errors.py"
Cohesion: 0.14
Nodes (21): ErrorDetail, ErrorResponse, Health, BaseModel, Ready, Version, FastAPI, register_errors() (+13 more)

### Community 52 - "Phase 7B — Investigation & Adaptive Logging"
Cohesion: 0.02
Nodes (98): 10. Investigation taxonomy, 11. Evidence gap model, 12. Reuse Phase 7A missing-evidence categories, 13. SignalNeed abstraction, 14. No invented channels, 15. Capability resolver, 16. Session capability vs hardware/source capability, 17. Existing-data-first policy (+90 more)

### Community 53 - "asyncio"
Cohesion: 0.09
Nodes (43): alembic_config, alembic_script, Requires an explicitly supplied disposable test database. Never skips silently., asyncio, httpx, os, pathlib, main() (+35 more)

### Community 54 - "test_agent_runtime.py"
Cohesion: 0.08
Nodes (30): InvestigationInput, InvestigationProposal, ProposedGap, ProposedHypothesis, model_validator, Validate provider semantic proposals before creating public artifacts., DeterministicProvider, Deterministic provider adapter; the production orchestrator and grounding are… (+22 more)

### Community 55 - "Catalog"
Cohesion: 0.33
Nodes (4): Catalog, Any, Entity, UUID

### Community 56 - "orchestration.py"
Cohesion: 0.11
Nodes (21): Any, Redact only strings, preserving numeric facts and JSON structure., redact_data(), EvidenceClient, Protocol, accumulate(), Orchestrator, Any (+13 more)

### Community 57 - "MappedCSVTelemetrySource"
Cohesion: 0.16
Nodes (19): MappedCSVTelemetrySource, mapping(), parametrize, test_absent_mapping_and_invalid_headers_are_rejected(), test_explicit_identity_sequence_are_preserved(), test_explicit_wide_csv_mapping_preserves_units_time_and_provenance(), test_header_inspection_rejects_missing_ambiguous_or_oversized_csv(), test_invalid_identity_or_sequence_is_rejected() (+11 more)

### Community 59 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 60 - "security-policy.py"
Cohesion: 0.22
Nodes (12): Namespace, re, Validate local skills, scoped context, declarative YAML and Markdown links., accepted(), load_exceptions(), load_findings(), main(), parse_args() (+4 more)

### Community 61 - "mcp-validation.sh"
Cohesion: 0.25
Nodes (6): DATABASE_URL, ENVIRONMENT, MCP_TEST_PROJECT, mcp-validation.sh script, TEST_DATABASE_URL, TEST_KAFKA_PORT

### Community 62 - "test_agents.py"
Cohesion: 0.15
Nodes (38): render_binding(), validate(), Answer, Binding, Claim, Classification, Draft, Finding (+30 more)

### Community 63 - "README.md"
Cohesion: 0.09
Nodes (14): Contributing, System context, Toolchain selection, Local development, Closure, Phase 0 task map, Phase 1 outline — Vehicle & Telemetry Core, Failure handling (+6 more)

### Community 64 - "PHASE 0 COMPLETION REPORT"
Cohesion: 0.11
Nodes (19): ADRs created, Applications, Architecture, CI/CD, Closure rerun result, Codex context, Database, Deferred deliberately to Phase 1+ (+11 more)

### Community 65 - "telemetry/service.py"
Cohesion: 0.21
Nodes (14): ImportResult, TelemetryPoint, TelemetryWindow, create_modification(), create_session(), query_telemetry(), TelemetrySource, _content_hash() (+6 more)

### Community 66 - "integration.sh"
Cohesion: 0.40
Nodes (3): KAFKA_BOOTSTRAP_SERVERS, integration.sh script, TEST_DATABASE_URL

### Community 67 - "retrospective-validation.sh"
Cohesion: 0.40
Nodes (3): COMPOSE_PROJECT_NAME, GIT_SHA, retrospective-validation.sh script

### Community 68 - "next-env.d.ts"
Cohesion: 0.50
Nodes (3): NOTE: This file should not be edited, apps_web_next_types_root_params_d, apps_web_next_types_routes_d

### Community 69 - "113. Final delivery report"
Cohesion: 0.12
Nodes (17): 113. Final delivery report, API, Architecture, Benchmark, Data sufficiency / false conclusions, Explicit deferrals, Frontend, GitHub (+9 more)

### Community 91 - "Container scan findings — 2026-10-01"
Cohesion: 0.25
Nodes (7): Canonical rerun 36952758342, Container scan findings — 2026-10-01, Current disposition, Image-content and coverage status, Narrow residual-risk records, Third-party infrastructure scan, Unique finding inventory

### Community 93 - "126. Final delivery report"
Cohesion: 0.14
Nodes (14): 126. Final delivery report, Architecture, Explicit deferrals, GitHub, Hardware, Live system, Migrations, Observability (+6 more)

### Community 94 - "45. Required synthetic scenarios"
Cohesion: 0.15
Nodes (13): 45. Required synthetic scenarios, A. Identical repeated pulls, B. Progressive IAT accumulation, C. Progressive boost reduction, D. Fuel-pressure degradation pattern, E. Slower normalized acceleration, F. Noisy but unchanged vehicle, G. Different configuration (+5 more)

### Community 95 - ".read_resource"
Cohesion: 0.24
Nodes (9): AnyUrl, Any, Exception, ToolError, SafeMCPServer, CallToolResult, Context, InputRequiredResult (+1 more)

### Community 96 - "73. Definition of Done"
Cohesion: 0.17
Nodes (12): 73. Definition of Done, API/UI, Architecture, Delivery, Grounding, Observability, Orchestration, Performance (+4 more)

### Community 97 - "agent-workspace.test.tsx"
Cohesion: 0.18
Nodes (7): AgentWorkspace(), loadRun(), observe(), submit(), audit, result, Stream

### Community 98 - "CSVSignalColumn"
Cohesion: 0.40
Nodes (3): CSVSignalColumn, BaseModel, model_validator

### Community 99 - "Phases 0–5 retrospective hardening"
Cohesion: 0.05
Nodes (33): ADR 0014: Kafka durable acquisition stream, Consequences, Context, Decision, ADR 0016: Deterministic, immutable automotive analytics, Consequences, Decision, Status (+25 more)

### Community 100 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 101 - "investigation/service.py"
Cohesion: 0.14
Nodes (36): EvidenceGap, GapStatus, GapType, Hypothesis, HypothesisCategory, HypothesisStatus, InvestigationOutcome, Public Phase 7B artifacts and explicit lifecycle rules. These models contain… (+28 more)

### Community 102 - "InvestigationPlan"
Cohesion: 0.11
Nodes (15): Approval, InvestigationEvent, InvestigationPlan, model_validator, InvestigationInstrumentation, Bounded investigation telemetry without entity labels on metrics., InvestigationRepository, UUID (+7 more)

### Community 103 - "pull_request_template.md"
Cohesion: 0.22
Nodes (8): Database/contract impact, Documentation, How it was validated, Observability impact, Risks, Security impact, What changed, Why

### Community 104 - "test_agent_repository.py"
Cohesion: 0.14
Nodes (18): url(), url(), source(), parametrize, Agent repository SQL/serialization boundaries; real transactions are tested…, rows(), storage(), test_database_errors_are_normalized_and_session_closes() (+10 more)

### Community 105 - "env.py"
Cohesion: 0.50
Nodes (4): run(), run_sync(), Connection, sqlalchemy_engine

### Community 106 - "Phase 5 automotive analytics"
Cohesion: 0.25
Nodes (7): Comparability and sufficiency, Metrics and normalization, Phase 5 automotive analytics, Pipeline and source of truth, Retrospective calculation identity, Retrospective metric and presentation completeness, Robust statistics and provenance

### Community 107 - "ADR 0018: Read-only MCP application adapter"
Cohesion: 0.33
Nodes (6): ADR 0018: Read-only MCP application adapter, Alternatives, Consequences and risks, Context, Decision, Status

### Community 108 - "N55 Intelligence Lab"
Cohesion: 0.20
Nodes (10): Arquitetura e continuidade, Desenvolvimento e testes, Estado atual, N55 Intelligence Lab, Observabilidade, Phase 6 MCP, Phase 7A grounded agent, Phase 7B investigation and adaptive logging (+2 more)

### Community 109 - "ADR 0001: Modular monolith first"
Cohesion: 0.29
Nodes (6): ADR 0001: Modular monolith first, Alternatives considered, Consequences, Context, Decision, Status

### Community 110 - "ADR 0002: Polyglot toolchain"
Cohesion: 0.29
Nodes (6): ADR 0002: Polyglot toolchain, Alternatives considered, Consequences, Context, Decision, Status

### Community 111 - "ADR 0003: TimescaleDB foundation"
Cohesion: 0.29
Nodes (6): ADR 0003: TimescaleDB foundation, Alternatives considered, Consequences, Context, Decision, Status

### Community 112 - "ADR 0004: OpenTelemetry observability"
Cohesion: 0.29
Nodes (6): ADR 0004: OpenTelemetry observability, Alternatives considered, Consequences, Context, Decision, Status

### Community 113 - "ADR 0005: Generated versioned contracts"
Cohesion: 0.29
Nodes (6): ADR 0005: Generated versioned contracts, Alternatives considered, Consequences, Context, Decision, Status

### Community 114 - "ADR 0006: Codex context and skills"
Cohesion: 0.29
Nodes (6): ADR 0006: Codex context and skills, Alternatives considered, Consequences, Context, Decision, Status

### Community 115 - "ADR 0007: Trunk-based development"
Cohesion: 0.29
Nodes (6): ADR 0007: Trunk-based development, Alternatives considered, Consequences, Context, Decision, Status

### Community 116 - "ADR 0008: ESLint 10 compatibility bridge"
Cohesion: 0.29
Nodes (6): ADR 0008: ESLint 10 compatibility bridge, Alternatives considered, Consequences, Context, Decision, Status

### Community 117 - "ADR 0009: Runtime base security and cloud validation"
Cohesion: 0.29
Nodes (6): ADR 0009: Runtime base security and cloud validation, Alternatives considered, Consequences, Context, Decision, Status

### Community 118 - "ADR 0010: Harden the pinned TimescaleDB runtime"
Cohesion: 0.29
Nodes (6): ADR 0010: Harden the pinned TimescaleDB runtime, Alternatives considered, Consequences and risks, Context, Decision, Status

### Community 119 - "ADR 0011: Canonical telemetry storage and retry identity"
Cohesion: 0.29
Nodes (6): ADR 0011: Canonical telemetry storage and retry identity, Alternatives considered, Consequences and risks, Context, Decision, Status

### Community 120 - "Phase 4 acquisition threats"
Cohesion: 0.40
Nodes (5): Original Phase 4 local resource budgets, Phase 4 acquisition threats, Phase 6 MCP boundary, Phase 7A agent boundary, Phase 7B investigation and adaptive logging

### Community 121 - "Phase 3 event and anomaly engine"
Cohesion: 0.29
Nodes (6): Baselines and comparability, Evaluation, troubleshooting, and boundaries, Phase 3 event and anomaly engine, Pipeline and limits, Retrospective detector review, Taxonomy and detectors

### Community 122 - "55. Required test layers"
Cohesion: 0.29
Nodes (7): 55. Required test layers, Acceptance, Browser E2E, Integration, Observability, Security, Unit

### Community 123 - "benchmark_stream_live.py"
Cohesion: 0.48
Nodes (5): buffered_points(), canonical_counts(), main(), memory_snapshot(), worker_metrics()

### Community 124 - "ADR 0012: Versioned deterministic session analysis"
Cohesion: 0.33
Nodes (5): ADR 0012: Versioned deterministic session analysis, Alternatives, Consequences and risks, Context, Decision

### Community 125 - "ADR 0013: Deterministic evidence-first event architecture"
Cohesion: 0.33
Nodes (5): ADR 0013: Deterministic evidence-first event architecture, Alternatives, Consequences and risks, Context, Decision

### Community 126 - "pytest"
Cohesion: 0.08
Nodes (32): AgentRequestBudgetMiddleware, Receive, Scope, Send, Bound admission and body buffering before FastAPI parses an agent question., query_row(), Source support comes from a current local collector or operator preflight., report() (+24 more)

### Community 127 - "ADR 0019: Grounded agent state and evidence"
Cohesion: 0.33
Nodes (6): ADR 0019: Grounded agent state and evidence, Alternatives, Consequences and risks, Context, Decision, Status

### Community 128 - "test_investigation.py"
Cohesion: 0.13
Nodes (29): InvestigationStatus, InvestigationService, insufficient_run(), MemoryInvestigations, plan(), test_cancel_and_reject_are_idempotent_only_at_exact_version(), test_completed_followup_reloads_after_stale_race(), test_create_closes_provider_after_invalid_semantic_output() (+21 more)

### Community 129 - "Phase 3 events"
Cohesion: 0.25
Nodes (7): Grounded agent, Investigation and adaptive logging, MCP, Observability, Phase 2 analysis, Phase 3 events, Retrospective instrumentation checks

### Community 130 - "75. API surface"
Cohesion: 0.33
Nodes (6): 75. API surface, Acquisition, Ingestion, Live client, Logging objectives, Recipes

### Community 131 - "85. Unit and contract tests"
Cohesion: 0.33
Nodes (6): 85. Unit and contract tests, Collector, Live analysis, Recipes, Sampling, Stream

### Community 132 - "investigation/routes.py"
Cohesion: 0.12
Nodes (19): AcquisitionCapabilitySource, fresh(), datetime, UUID, Source capability snapshots from the local collector, never inferred from…, Phase 4 owner of source support; a dataset report is not source support., SourceCapabilitySnapshot, validated_report() (+11 more)

### Community 133 - "MCP server"
Cohesion: 0.33
Nodes (6): Docker, Limits and troubleshooting, Local stdio, MCP server, Streamable HTTP, Validation

### Community 134 - "Phase 6 acceptance evidence"
Cohesion: 0.20
Nodes (7): Executed acceptance checkpoint, Independent MCP evidence, Limitations and deferred scope, Measured performance and bounds, Phase 6 acceptance evidence, Remote proof and final HEAD identity, Phase 6 traceability ledger

### Community 135 - "Vehicle Intelligence Platform context"
Cohesion: 0.40
Nodes (4): Business Logic & Feature Map, Directory Structure Map, Validation, Vehicle Intelligence Platform context

### Community 136 - "Phase 1 vehicle and telemetry core"
Cohesion: 0.40
Nodes (4): Canonical import contract, Performance baseline protocol, Phase 1 vehicle and telemetry core, Query and operations

### Community 137 - "Phase 2 session and pull analysis"
Cohesion: 0.40
Nodes (4): API and limits, Phase 2 session and pull analysis, Semantics, Synthetic validation

### Community 138 - "94. Failure behavior"
Cohesion: 0.40
Nodes (5): 94. Failure behavior, Database unavailable, Device disconnect, One bad signal, Stream unavailable

### Community 139 - "strategy.md"
Cohesion: 0.29
Nodes (6): Phase 3 acceptance, Phase 6 acceptance, Phase 7A acceptance, Phase 7B acceptance, Retrospective phase gates, Testing strategy

### Community 144 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 145 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 146 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 147 - "mcp/cli.py"
Cohesion: 0.13
Nodes (10): main(), One registration shared by stdio and authenticated Streamable HTTP., HTTPInstrumentation, ASGI boundary preserving W3C trace context and counting SDK auth rejections., test_http_trace_context_and_auth_rejections(), argparse, mcp_server_transport_security, starlette_middleware_base (+2 more)

### Community 148 - "EventEngine"
Cohesion: 0.26
Nodes (16): EventProfile, Development heuristics; these are not factory safety or N55 calibration limits., EventEngine, base(), frames(), pull(), test_comparable_pulls(), test_fuel_drop_requires_sustained_observation_not_single_low_spike() (+8 more)

### Community 149 - "15. Required acquisition adapters"
Cohesion: 0.50
Nodes (4): 15. Required acquisition adapters, Real read-only OBD adapter path, Replay adapter, Synthetic live adapter

### Community 151 - "SyntheticLiveAdapter"
Cohesion: 0.13
Nodes (8): SyntheticLiveAdapter, test_collector_capability_failure_closes_adapter(), test_collector_heartbeat_interruption_does_not_erase_samples(), test_collector_reports_capabilities_bounds_and_graceful_disconnect(), heartbeat(), test_periodic_heartbeat_continues_while_adapter_waits(), read(), publish()

### Community 153 - "101. ADRs"
Cohesion: 0.67
Nodes (3): 101. ADRs, Acquisition lifecycle / recipes, Streaming architecture

### Community 154 - "Phase 7A acceptance"
Cohesion: 0.18
Nodes (9): Current phase, Roadmap, Baseline and delivery boundary, Executed checkpoint: `881fcca0bb75acf9369bbbf25854c32d626aa017`, Final receipt requirements, Missing-evidence correction: `4df84696ab3ffb5d900399877849975b008fe4cf`, Phase 7A acceptance, Pushed-head full verification checkpoint: `66efbc744ab23c5ba0044cb6029ebd69c56f2206` (+1 more)

### Community 155 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 174 - "investigation_router"
Cohesion: 0.11
Nodes (5): investigation_router(), stream(), APIRouter, test_investigation_api_requires_operator_token(), test_operator_route_requires_configured_token()

### Community 177 - "resolve_context"
Cohesion: 0.47
Nodes (8): at(), effective(), Any, datetime, UUID, resolve_context(), test_context_cross_vehicle_rejected(), test_temporal_context_removal_and_boundary()

### Community 178 - "main"
Cohesion: 0.40
Nodes (4): compose(), main(), Wait until the real Next.js status and domain proxies recover too., wait_for_browser_proxies()

### Community 179 - "Live acquisition operations and physical validation"
Cohesion: 0.33
Nodes (5): Collector CLI guarantees, Live acquisition operations and physical validation, Preserve an older Kafka storage path, Safe physical Vgate validation procedure, Topology and recovery

### Community 180 - "Validation evidence — 2026-10-01"
Cohesion: 0.40
Nodes (4): Canonical GitHub workflow run (2026-10-02), Closure rerun (23:33–23:38 UTC), Split-executor implementation, Validation evidence — 2026-10-01

### Community 181 - "service_fixture"
Cohesion: 0.18
Nodes (12): Ask, service_fixture(), event(), finish(), get(), replay(), save(), test_run_deadline_includes_validated_answer_publication() (+4 more)

### Community 182 - "architecture/phase-6-mcp-tool-platform.md"
Cohesion: 0.16
Nodes (7): Component model, CURRENT, FUTURE, Approval and follow-up, Domain and persistence, Phase 7B investigation and adaptive logging, Service boundaries

### Community 183 - "98. Phase 7B Definition of Done"
Cohesion: 0.15
Nodes (13): 98. Phase 7B Definition of Done, Acquisition / follow-up, API / UI, Approval, Delivery, Existing evidence, Investigation domain, Logging plan (+5 more)

### Community 184 - "test_investigation_repository.py"
Cohesion: 0.29
Nodes (9): approved_plan(), item(), Phase 7B optimistic SQL boundary; disposable PostgreSQL tests cover execution., result_with(), storage(), test_create_conflict_and_stale_update_fail_closed(), test_create_get_recent_update_and_replay(), test_session_link_context_guards_and_idempotence() (+1 more)

### Community 185 - "auth.py"
Cohesion: 0.22
Nodes (6): AccessToken, Verify an operator-provisioned opaque token; never issue or forward tokens., ReadTokenVerifier, test_auth(), hmac, mcp_server_auth_provider

### Community 186 - "@playwright/test"
Cohesion: 0.31
Nodes (3): @axe-core/playwright, ref_node_fs, @playwright/test

### Community 187 - "ReadOnlyDatabase"
Cohesion: 0.33
Nodes (4): BaseException, ReadOnlyDatabase, test_database_abort_invalidated_connection(), test_read_only_database_setup()

### Community 188 - "Phase 7B acceptance"
Cohesion: 0.29
Nodes (5): Benchmark checkpoint, Final receipt requirements, Phase 7B acceptance, Scope and gates, Phase 7B requirement traceability

### Community 189 - "InvestigationError"
Cohesion: 0.40
Nodes (4): InvestigationError, ValueError, A public investigation rule was violated., Transition

### Community 190 - ".export"
Cohesion: 0.33
Nodes (4): graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), ReadableSpan, SpanExportResult

### Community 191 - "ADR 0020: Investigation recipe and approval boundary"
Cohesion: 0.33
Nodes (6): ADR 0020: Investigation recipe and approval boundary, Alternatives, Consequences and risks, Context, Decision, Status

### Community 192 - "ADR 0015: Versioned recipes and acquisition lifecycle"
Cohesion: 0.40
Nodes (4): blocked(), ADR 0015: Versioned recipes and acquisition lifecycle, Consequences, Decision

### Community 193 - "Phase 7A grounded agent"
Cohesion: 0.40
Nodes (5): Boundaries, Context and evidence, Execution and lifecycle, Phase 7A grounded agent, Provider and streaming contracts

### Community 194 - "test_timeout_size_rate_and_spans"
Cohesion: 0.50
Nodes (4): test_timeout_size_rate_and_spans(), delayed(), large(), success()

### Community 196 - "45. Investigation examples"
Cohesion: 0.50
Nodes (4): 45. Investigation examples, Example A — repeated pull performance loss, Example B — change after intercooler, Example C — missing technical specification

## Knowledge Gaps
- **940 isolated node(s):** `vehicle-platform-api`, `StandardPid`, `config`, `name`, `version` (+935 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1485 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **54 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `register_tools()` connect `register_tools` to `server.py`, `Adapter`, `PlatformError`, `AgentError`, `test_mcp.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `AgentError` connect `AgentError` to `test_investigation.py`, `investigation/routes.py`, `investigation/service.py`, `InvestigationPlan`, `main.py`, `test_agent_repository.py`, `DeviceCapabilities`, `AgentSettings`, `resolve_context`, `api/errors.py`, `service_fixture`, `test_agent_runtime.py`, `test_investigation_repository.py`, `orchestration.py`, `test_agents.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `Phase 7A — Agent Core & Grounded Orchestration` connect `Phase 7A — Agent Core & Grounded Orchestration` to `73. Definition of Done`, `register_tools`, `55. Required test layers`, `phase-7a-traceability-ledger.md`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 68 inferred relationships involving `AgentError` (e.g. with `EvidenceRegistry` and `InvestigationRepository`) actually correct?**
  _`AgentError` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Are the 45 inferred relationships involving `router()` (e.g. with `LoggingRecipe` and `AcquisitionAuthError`) actually correct?**
  _`router()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vehicle-platform-api`, `StandardPid`, `config` to the rest of the system?**
  _940 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `AnalyticsConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.08205128205128205 - nodes in this community are weakly interconnected._