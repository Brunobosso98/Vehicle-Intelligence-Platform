# Graph Report - vehicle-intelligence-platform  (2026-10-09)

## Corpus Check
- 314 files · ~245,784 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: (none) 12, .Dockerfile 2, .example 1)

## Summary
- 3131 nodes · 7797 edges · 204 communities (152 shown, 52 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 1388 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e32fc68c`
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
- Telemetry
- test_investigation.py
- acquisition/cli.py
- test_mcp.py
- AlignedFrame
- sqlalchemy
- json
- benchmark_mcp.py
- Adapter
- datetime
- StreamConsumer
- Envelope
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
- telemetry.py
- Settings
- status.test.tsx
- test_elm_tcp_transport_connects_reads_reuses_and_closes
- compilerOptions
- dataclasses
- AgentRun
- analytics-workspace.tsx
- typing
- next
- main.py
- Elm327Adapter
- devDependencies
- telemetry.test.tsx
- What You Must Do When Invoked
- SessionAnalysisService
- package.json
- provider.py
- budgets.py
- observability-validation.sh
- EventAnalysisService
- contracts.py
- Phase 7B — Investigation & Adaptive Logging
- asyncio
- test_agent_runtime.py
- Catalog
- Orchestrator
- MappedCSVTelemetrySource
- observability-smoke.py
- scripts
- security-policy.py
- mcp-validation.sh
- test_agents.py
- README.md
- PHASE 0 COMPLETION REPORT
- IngestionService
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
- AgentError
- pull_request_template.md
- pytest
- acquisition/domain.py
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
- test_acquisition_capabilities.py
- telemetry/domain.py
- insufficient_run
- Phase 3 events
- 75. API surface
- 85. Unit and contract tests
- investigation/routes.py
- architecture/phase-6-mcp-tool-platform.md
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
- NormalizationError
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
- worker.py
- investigation_router
- ref_next_types_root_params_d_ts
- ref_next_types_routes_d_ts
- resolve_context
- main
- Live acquisition operations and physical validation
- Validation evidence — 2026-10-01
- agents/schemas.py
- architecture/phase-7b-investigation-adaptive-logging.md
- 98. Phase 7B Definition of Done
- InvestigationStatus
- ADR 0017: Retrospective evidence and execution identity
- @playwright/test
- agent_router
- Phase 7B acceptance
- investigation/domain.py
- .export
- Phase 4 — Streaming & Live Vehicle Acquisition
- ADR 0015: Versioned recipes and acquisition lifecycle
- Phase 7A grounded agent
- .__call__
- phase-7a-traceability-ledger.md
- 45. Investigation examples
- check_coverage.py
- investigation/__init__.py
- sample_id
- failure_category
- test_followup_watcher_reconciles_and_logs_failure_without_leaking
- main
- main

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

## Communities (204 total, 52 thin omitted)

### Community 0 - "AnalyticsConfig"
Cohesion: 0.08
Nodes (65): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+57 more)

### Community 1 - "test_acquisition.py"
Cohesion: 0.08
Nodes (31): preflight(), Readiness, FakeElm, capabilities(), parametrize, test_collector_health_distinguishes_transport_and_sampling(), test_collector_reports_actual_recovery_metrics_and_payload_free_spans(), test_collector_retries_spools_and_replays_without_loss() (+23 more)

### Community 2 - "DetectorProfile"
Cohesion: 0.11
Nodes (33): UUID, align_observations(), Align by deterministic last-value carry-forward, expiring at max_gap. Duplicate…, rolling_median(), HeuristicPullDetector, DetectorProfile, Observation, Heuristic defaults, not manufacturer calibration data. (+25 more)

### Community 3 - "router"
Cohesion: 0.11
Nodes (48): APIRouter, router(), analytics_config(), analyze_repeated_pulls(), analyze_session(), analyze_session_events(), build_vehicle_baseline(), compare_configurations() (+40 more)

### Community 4 - "api/routes.py"
Cohesion: 0.10
Nodes (39): AcquisitionBatchAccepted, AcquisitionCreated, AcquisitionHeartbeat, AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement, AnalysisRequest, AnalyticsRequest (+31 more)

### Community 5 - "BoundedSpool"
Cohesion: 0.07
Nodes (22): SyntheticLiveAdapter, BoundedSpool, Path, Single-collector atomic acknowledgement, only after successful publish., Path, test_bounded_spool_replays_and_reports_overflow(), test_collector_capability_failure_closes_adapter(), test_collector_heartbeat_interruption_does_not_erase_samples() (+14 more)

### Community 6 - "acquisition/service.py"
Cohesion: 0.10
Nodes (33): AIOKafkaProducer, assess_dataset(), collector_health(), DatasetCapability, measure_signal_quality(), datetime, Infer transport/sampling freshness only from an authenticated report. Event…, SignalQuality (+25 more)

### Community 7 - "RawTelemetryRecord"
Cohesion: 0.14
Nodes (10): Read-only adapter contract. Deliberately has no command/write operation., VehicleDataAdapter, AcquisitionCollector, report(), report_periodically(), CollectorStats, Hardware-near bounded collector with retry, backpressure, and disk replay., SamplingPlanItem (+2 more)

### Community 8 - "Telemetry"
Cohesion: 0.10
Nodes (17): main(), TelemetryWindow, ASGIApp, Database, AsyncSession, Telemetry, datetime, UUID (+9 more)

### Community 9 - "test_investigation.py"
Cohesion: 0.16
Nodes (34): DeviceCapabilities, Support, Feasibility, SignalRole, plan_recipe(), Keep source support distinct from what a past session happened to record., resolve_needs(), test_preflight_blocks_supported_signals_with_inadequate_poll_budget() (+26 more)

### Community 10 - "acquisition/cli.py"
Cohesion: 0.12
Nodes (25): ReplayAdapter, adapter_for(), AdapterKind, devices(), execute(), _preflight(), preflight_command(), probe() (+17 more)

### Community 11 - "test_mcp.py"
Cohesion: 0.07
Nodes (34): AccessToken, Verify an operator-provisioned opaque token; never issue or forward tokens., ReadTokenVerifier, MCPSettings, BaseSettings, model_validator, BaseException, ReadOnlyDatabase (+26 more)

### Community 12 - "AlignedFrame"
Cohesion: 0.19
Nodes (27): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, PullWindow, StrEnum (+19 more)

### Community 13 - "sqlalchemy"
Cohesion: 0.08
Nodes (8): alembic, run(), run_sync(), upgrade(), Connection, sqlalchemy, sqlalchemy_dialects, sqlalchemy_engine

### Community 14 - "json"
Cohesion: 0.10
Nodes (27): alembic_config, alembic_script, UUID, Requires an explicitly supplied disposable test database. Never skips silently., httpx, httpx2, json, mcp_client_streamable_http (+19 more)

### Community 15 - "benchmark_mcp.py"
Cohesion: 0.09
Nodes (21): connect(), MCPClient, AsyncClient, Client, test_real_database_agent_lifecycle_failure_recovery_and_audit(), connection(), client(), main() (+13 more)

### Community 16 - "Adapter"
Cohesion: 0.23
Nodes (11): Adapter, Any, Entity, UUID, PlatformError, Exception, BaseModel, model_validator (+3 more)

### Community 17 - "datetime"
Cohesion: 0.18
Nodes (20): evaluate_events(), EventClassMetrics, EventEvaluation, _overlaps(), One-to-one deterministic matching by type, pull and temporal overlap., anomaly_scenario(), AnomalyInjection, EventScenario (+12 more)

### Community 18 - "StreamConsumer"
Cohesion: 0.26
Nodes (8): UUID, RawTelemetryMessage, StreamConsumer, test_stream_contract_and_dataset_capability(), parametrize, test_sequence_overflow_rejected_at_every_input_boundary(), test_sequence_valid_edges_remain_compatible(), main()

### Community 19 - "Envelope"
Cohesion: 0.14
Nodes (15): canonical_hash(), facts(), Any, EvidenceClient, Any, Protocol, Envelope, call() (+7 more)

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
Cohesion: 0.09
Nodes (22): MCPServer, register_tools(), compare_configurations(), get_cross_session_analytics(), get_event(), get_pull_summary(), get_repeated_pull_analysis(), get_session_analytics() (+14 more)

### Community 25 - "vehicle-workspace.tsx"
Cohesion: 0.08
Nodes (27): AgentEvent, AgentRun, Audit, AgentRun, Investigation, InvestigationWorkspace(), terminal, DetectedEvent (+19 more)

### Community 26 - "test_gateway_publisher_classifies_responses"
Cohesion: 0.12
Nodes (8): Exception, MonkeyPatch, test_consumer_database_failure_exits_without_sql_inputs(), fail(), test_gateway_publisher_classifies_responses(), test_gateway_transport_errors_enter_retry_spool_path(), test_spool_failed_atomic_ack_preserves_original(), CaptureFixture

### Community 27 - "normalize_value"
Cohesion: 0.23
Nodes (13): DataQuality, normalize_value(), StrEnum, CSVTelemetrySource, parametrize, test_configuration_time_contract(), test_csv_accepts_signed_measurements_and_rejects_broken_structure(), test_csv_encoding_missing_cells_and_bad_numeric_input() (+5 more)

### Community 28 - "evaluate_agent_grounding.py"
Cohesion: 0.20
Nodes (10): mcp_client_stdio, domain_fingerprint(), Any, Aggregate content changes, including updates, in disposable fixture tables., main(), Independent Phase 7A evaluator: actual MCP stdio, real DB/API, fixed golden…, Real stdio and HTTP client acceptance, lifecycle, authorization and recovery., socket (+2 more)

### Community 29 - "Phase 7A — Agent Core & Grounded Orchestration"
Cohesion: 0.03
Nodes (72): 10. Agent state, 11. AgentRun persistence, 12. ToolCall persistence / audit trail, 13. Evidence model, 14. Claim → Evidence grounding, 15. Unsupported-claim detection, 16. Structured answer contract, 17. Natural-language API (+64 more)

### Community 30 - "telemetry.py"
Cohesion: 0.08
Nodes (21): Prevent database driver messages and SQL text from leaving the process., SanitizingExporter, JSONFormatter, Any, test_database_error_propagation_cannot_leak_through_parent_spans(), test_database_trace_export_redacts_driver_inputs(), test_json_logs_do_not_render_exception_secrets(), test_non_http_passthrough() (+13 more)

### Community 31 - "Settings"
Cohesion: 0.07
Nodes (37): AcquisitionPublisher, Application-owned producer; bounded concurrent publication and shutdown., BaseSettings, datetime, model_validator, Settings, create_app(), parametrize (+29 more)

### Community 32 - "status.test.tsx"
Cohesion: 0.17
Nodes (13): dynamic, GET(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready, SystemStatus (+5 more)

### Community 33 - "test_elm_tcp_transport_connects_reads_reuses_and_closes"
Cohesion: 0.15
Nodes (3): ElmTcpTransport, Concrete ELM327 TCP/RFCOMM bridge transport with a strict read-only command…, test_elm_tcp_transport_connects_reads_reuses_and_closes()

### Community 34 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 35 - "dataclasses"
Cohesion: 0.14
Nodes (20): compute_pull_metrics(), HeuristicSegmentDetector, _mean(), PullDetector, Protocol, SegmentDetector, _slope(), DetectedPull (+12 more)

### Community 36 - "AgentRun"
Cohesion: 0.14
Nodes (13): AgentInstrumentation, AgentRepository, AsyncSession, Protocol, UUID, Commit terminal state and stream event together; reconnect cannot race…, Only agent-owned tables. Vehicle existence is resolved through MCP, never SQL., Recover interrupted runs beyond the hard 180s runtime plus cleanup allowance. (+5 more)

### Community 37 - "analytics-workspace.tsx"
Cohesion: 0.13
Nodes (11): AnalyticsWorkspace(), history(), Configuration, curveLabels, NormalizedBin, Profile, Pull, request() (+3 more)

### Community 38 - "typing"
Cohesion: 0.12
Nodes (25): Bounded context repository for records currently owned by HTTP SQL handlers., ErrorCode, StrEnum, ToolError, UUID, tool_error(), Instrumentation, call() (+17 more)

### Community 39 - "next"
Cohesion: 0.18
Nodes (6): config, GET, POST, apps_web_src_app_globals, metadata, next

### Community 40 - "main.py"
Cohesion: 0.08
Nodes (25): CorrelationMiddleware, DatabaseProbe, DependencyUnavailable, Exception, Protocol, Infrastructure failed its bounded readiness check., PlatformAPI, ASGIApp (+17 more)

### Community 41 - "Elm327Adapter"
Cohesion: 0.21
Nodes (4): Elm327Adapter, ElmTransport, Protocol, Generic standard-mode OBD-II reader; no proprietary or write commands.

### Community 42 - "devDependencies"
Cohesion: 0.12
Nodes (16): devDependencies, @axe-core/playwright, eslint, @eslint/compat, eslint-config-next, jsdom, @playwright/test, @testing-library/jest-dom (+8 more)

### Community 43 - "telemetry.test.tsx"
Cohesion: 0.10
Nodes (14): VehicleWorkspace(), FakeEventSource, vehicle, detectedEvent, pull, segment, session, signals (+6 more)

### Community 44 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 45 - "SessionAnalysisService"
Cohesion: 0.35
Nodes (7): AnalysisLimitError, UUID, ValueError, SessionAnalysisService, AnalysisResult, Pull, SessionSegment

### Community 46 - "package.json"
Cohesion: 0.11
Nodes (18): devDependencies, openapi-typescript, prettier, engines, node, name, packageManager, private (+10 more)

### Community 47 - "provider.py"
Cohesion: 0.13
Nodes (25): InvestigationInput, InvestigationProposal, ProposedGap, ProposedHypothesis, model_validator, OpenAIProvider, ModelInput, ModelTurn (+17 more)

### Community 48 - "budgets.py"
Cohesion: 0.06
Nodes (42): AgentRequestBudgetMiddleware, ASGIApp, Receive, Scope, Send, Constant-memory local request budgets for the Phase 4 resource boundaries., Bound admission and body buffering before FastAPI parses an agent question., Per-process budgets, with no unbounded per-client identifier dictionaries. The… (+34 more)

### Community 49 - "observability-validation.sh"
Cohesion: 0.40
Nodes (4): scripts_lib_wait_http_sh, observability-validation.sh script, wait_prometheus_query(), stack-smoke.sh script

### Community 50 - "EventAnalysisService"
Cohesion: 0.60
Nodes (3): DetectedEvent, EventAnalysisService, UUID

### Community 51 - "contracts.py"
Cohesion: 0.33
Nodes (8): ErrorDetail, ErrorResponse, Health, BaseModel, Ready, Version, live(), ready()

### Community 52 - "Phase 7B — Investigation & Adaptive Logging"
Cohesion: 0.02
Nodes (98): 10. Investigation taxonomy, 11. Evidence gap model, 12. Reuse Phase 7A missing-evidence categories, 13. SignalNeed abstraction, 14. No invented channels, 15. Capability resolver, 16. Session capability vs hardware/source capability, 17. Existing-data-first policy (+90 more)

### Community 53 - "asyncio"
Cohesion: 0.13
Nodes (27): asyncio, main(), Dedicated browser gate: controlled real API, authenticated HTTP MCP and…, Independent controlled temporal/configuration fixtures in disposable…, seed_agent(), main(), Actual HTTP MCP/API streaming, cancellation, dependency failure and reconnect…, main() (+19 more)

### Community 54 - "test_agent_runtime.py"
Cohesion: 0.07
Nodes (34): url(), url(), source(), storage(), provider(), parametrize, Provider wire parsing and service lifecycle failure branches (unit doubles…, request() (+26 more)

### Community 55 - "Catalog"
Cohesion: 0.33
Nodes (4): Catalog, Any, Entity, UUID

### Community 56 - "Orchestrator"
Cohesion: 0.18
Nodes (9): accumulate(), Orchestrator, Any, UUID, Provider, Protocol, GraphState, test_usage_unavailable_stays_unavailable() (+1 more)

### Community 57 - "MappedCSVTelemetrySource"
Cohesion: 0.29
Nodes (12): CSVColumnMapping, inspect_csv(), MappedCSVTelemetrySource, mapping(), parametrize, test_absent_mapping_and_invalid_headers_are_rejected(), test_explicit_identity_sequence_are_preserved(), test_explicit_wide_csv_mapping_preserves_units_time_and_provenance() (+4 more)

### Community 59 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 60 - "security-policy.py"
Cohesion: 0.24
Nodes (11): Namespace, Validate local skills, scoped context, declarative YAML and Markdown links., accepted(), load_exceptions(), load_findings(), main(), parse_args(), Any (+3 more)

### Community 61 - "mcp-validation.sh"
Cohesion: 0.25
Nodes (6): DATABASE_URL, ENVIRONMENT, MCP_TEST_PROJECT, mcp-validation.sh script, TEST_DATABASE_URL, TEST_KAFKA_PORT

### Community 62 - "test_agents.py"
Cohesion: 0.14
Nodes (38): AgentSettings, BaseSettings, model_validator, render_binding(), validate(), comparison(), parametrize, test_association_degrades_without_comparable_complete_context() (+30 more)

### Community 63 - "README.md"
Cohesion: 0.09
Nodes (14): Contributing, System context, Toolchain selection, Local development, Closure, Phase 0 task map, Phase 1 outline — Vehicle & Telemetry Core, Failure handling (+6 more)

### Community 64 - "PHASE 0 COMPLETION REPORT"
Cohesion: 0.11
Nodes (19): ADRs created, Applications, Architecture, CI/CD, Closure rerun result, Codex context, Database, Deferred deliberately to Phase 1+ (+11 more)

### Community 65 - "IngestionService"
Cohesion: 0.23
Nodes (8): ImportResult, LiveOBDSource, Protocol, Adapter boundary only: Phase 1 intentionally provides no hardware…, TelemetrySource, _content_hash(), IngestionService, AsyncSession

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
Cohesion: 0.22
Nodes (8): 2026-10-09 Go advisory refresh, Canonical rerun 36952758342, Container scan findings — 2026-10-01, Current disposition, Image-content and coverage status, Narrow residual-risk records, Third-party infrastructure scan, Unique finding inventory

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
Cohesion: 0.09
Nodes (19): Architecture assessment, Delivery state, Exact acceptance and reproducibility, Failure, performance, security and observability, Gaps found and corrections, Limitations and deferred original scope, Per-phase classification, Phases 0–5 retrospective hardening (+11 more)

### Community 100 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 101 - "investigation/service.py"
Cohesion: 0.15
Nodes (33): EvidenceGap, GapStatus, GapType, Hypothesis, HypothesisCategory, HypothesisStatus, InvestigationOutcome, StrEnum (+25 more)

### Community 102 - "AgentError"
Cohesion: 0.15
Nodes (13): Approval, CapabilitySnapshot, InvestigationPlan, model_validator, InvestigationRepository, UUID, Link one finalized Phase 4 acquisition under a row lock, idempotently., Atomically persist a unique follow-up AgentRun and its investigation link. (+5 more)

### Community 103 - "pull_request_template.md"
Cohesion: 0.22
Nodes (8): Database/contract impact, Documentation, How it was validated, Observability impact, Risks, Security impact, What changed, Why

### Community 104 - "pytest"
Cohesion: 0.19
Nodes (13): parametrize, Agent repository SQL/serialization boundaries; real transactions are tested…, rows(), test_database_errors_are_normalized_and_session_closes(), test_interrupted_run_reconciliation_is_bounded_and_terminal(), test_missing_driver_fails_closed(), test_repository_not_found_and_bounds(), test_repository_run_audit_and_stream_serialization() (+5 more)

### Community 105 - "acquisition/domain.py"
Cohesion: 0.26
Nodes (10): Importance, LoggingRecipe, plan_sampling(), PreflightResult, Priority, StrEnum, SignalRequirement, req() (+2 more)

### Community 106 - "Phase 5 automotive analytics"
Cohesion: 0.25
Nodes (7): Comparability and sufficiency, Metrics and normalization, Phase 5 automotive analytics, Pipeline and source of truth, Retrospective calculation identity, Retrospective metric and presentation completeness, Robust statistics and provenance

### Community 107 - "ADR 0018: Read-only MCP application adapter"
Cohesion: 0.17
Nodes (10): ADR 0016: Deterministic, immutable automotive analytics, Consequences, Decision, Status, ADR 0018: Read-only MCP application adapter, Alternatives, Consequences and risks, Context (+2 more)

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

### Community 126 - "test_acquisition_capabilities.py"
Cohesion: 0.50
Nodes (7): query_row(), Source support comes from a current local collector or operator preflight., report(), test_latest_prefers_newer_registered_report(), test_latest_rejects_stale_and_disconnected_reports(), test_latest_uses_connected_collector_snapshot(), test_register_requires_active_configuration_and_limits_source()

### Community 127 - "telemetry/domain.py"
Cohesion: 0.32
Nodes (7): StandardPid, SignalDefinition, Explicit generic CSV mapping; no proprietary exporter assumptions., collections_abc, csv, io, math

### Community 128 - "insufficient_run"
Cohesion: 0.12
Nodes (16): materialize(), Use only exact evidence IDs from the completed source run and fixed public…, investigable(), insufficient_run(), test_completed_followup_reloads_after_stale_race(), test_create_closes_provider_after_invalid_semantic_output(), test_create_rejects_invalid_identity_capacity_and_sufficient_answer(), test_create_reuses_existing_plan_only_for_same_source() (+8 more)

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
Cohesion: 0.13
Nodes (19): AcquisitionCapabilitySource, fresh(), datetime, UUID, Source capability snapshots from the local collector, never inferred from…, Phase 4 owner of source support; a dataset report is not source support., SourceCapabilitySnapshot, validated_report() (+11 more)

### Community 133 - "architecture/phase-6-mcp-tool-platform.md"
Cohesion: 0.17
Nodes (9): Component model, CURRENT, FUTURE, Docker, Limits and troubleshooting, Local stdio, MCP server, Streamable HTTP (+1 more)

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
Cohesion: 0.27
Nodes (16): EventProfile, Development heuristics; these are not factory safety or N55 calibration limits., EventEngine, base(), frames(), pull(), test_comparable_pulls(), test_fuel_drop_requires_sustained_observation_not_single_low_spike() (+8 more)

### Community 149 - "15. Required acquisition adapters"
Cohesion: 0.50
Nodes (4): 15. Required acquisition adapters, Real read-only OBD adapter path, Replay adapter, Synthetic live adapter

### Community 151 - "NormalizationError"
Cohesion: 0.21
Nodes (8): NormalizationError, parse_timestamp(), datetime, ValueError, SyntheticTelemetrySource, test_synthetic_source_is_deterministic_and_complete(), collect(), test_timestamp_requires_offset_and_normalizes_utc()

### Community 153 - "101. ADRs"
Cohesion: 0.67
Nodes (3): 101. ADRs, Acquisition lifecycle / recipes, Streaming architecture

### Community 154 - "Phase 7A acceptance"
Cohesion: 0.18
Nodes (9): Current phase, Roadmap, Baseline and delivery boundary, Executed checkpoint: `881fcca0bb75acf9369bbbf25854c32d626aa017`, Final receipt requirements, Missing-evidence correction: `4df84696ab3ffb5d900399877849975b008fe4cf`, Phase 7A acceptance, Pushed-head full verification checkpoint: `66efbc744ab23c5ba0044cb6029ebd69c56f2206` (+1 more)

### Community 155 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 173 - "worker.py"
Cohesion: 0.20
Nodes (7): aiokafka, validate_sequence(), asyncpg, hashlib, Hash the exact reviewable working tree without printing file contents., signal, subprocess

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

### Community 181 - "agents/schemas.py"
Cohesion: 0.14
Nodes (20): Any, Redact only strings, preserving numeric facts and JSON structure., redact_data(), EvidenceRegistry, UUID, Answer, Ask, Classification (+12 more)

### Community 182 - "architecture/phase-7b-investigation-adaptive-logging.md"
Cohesion: 0.10
Nodes (16): ADR 0019: Grounded agent state and evidence, Alternatives, Consequences and risks, Context, Decision, Status, ADR 0020: Investigation recipe and approval boundary, Alternatives (+8 more)

### Community 183 - "98. Phase 7B Definition of Done"
Cohesion: 0.15
Nodes (13): 98. Phase 7B Definition of Done, Acquisition / follow-up, API / UI, Approval, Delivery, Existing evidence, Investigation domain, Logging plan (+5 more)

### Community 184 - "InvestigationStatus"
Cohesion: 0.27
Nodes (12): InvestigationStatus, approved_plan(), item(), Phase 7B optimistic SQL boundary; disposable PostgreSQL tests cover execution., result_with(), storage(), test_claim_reanalysis_is_atomic_and_unique(), test_create_conflict_and_stale_update_fail_closed() (+4 more)

### Community 185 - "ADR 0017: Retrospective evidence and execution identity"
Cohesion: 0.17
Nodes (10): ADR 0014: Kafka durable acquisition stream, Consequences, Context, Decision, ADR 0017: Retrospective evidence and execution identity, Alternatives, Consequences and risks, Context (+2 more)

### Community 186 - "@playwright/test"
Cohesion: 0.31
Nodes (3): @axe-core/playwright, ref_node_fs, @playwright/test

### Community 187 - "agent_router"
Cohesion: 0.20
Nodes (5): agent_router(), audit(), stream(), APIRouter, RunAudit

### Community 188 - "Phase 7B acceptance"
Cohesion: 0.29
Nodes (5): Benchmark checkpoint, Final receipt requirements, Phase 7B acceptance, Scope and gates, Phase 7B requirement traceability

### Community 189 - "investigation/domain.py"
Cohesion: 0.13
Nodes (16): Availability, InvestigationError, InvestigationEvent, ValueError, Public Phase 7B artifacts and explicit lifecycle rules. These models contain…, A public investigation rule was violated., RecipeReference, SignalNeed (+8 more)

### Community 190 - ".export"
Cohesion: 0.33
Nodes (4): graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), ReadableSpan, SpanExportResult

### Community 191 - "Phase 4 — Streaming & Live Vehicle Acquisition"
Cohesion: 0.20
Nodes (9): Boundaries and flow, Broker storage and observed worker health, Collector heartbeat and acquisition context, Explicit CSV mapping and live recovery, Failure and security model, Phase 4 — Streaming & Live Vehicle Acquisition, Recipes and quality, Retrospective execution guarantees (+1 more)

### Community 192 - "ADR 0015: Versioned recipes and acquisition lifecycle"
Cohesion: 0.40
Nodes (4): blocked(), ADR 0015: Versioned recipes and acquisition lifecycle, Consequences, Decision

### Community 193 - "Phase 7A grounded agent"
Cohesion: 0.40
Nodes (5): Boundaries, Context and evidence, Execution and lifecycle, Phase 7A grounded agent, Provider and streaming contracts

### Community 194 - ".__call__"
Cohesion: 0.40
Nodes (3): Receive, Scope, Send

### Community 196 - "45. Investigation examples"
Cohesion: 0.50
Nodes (4): 45. Investigation examples, Example A — repeated pull performance loss, Example B — change after intercooler, Example C — missing technical specification

### Community 199 - "sample_id"
Cohesion: 0.40
Nodes (4): sample_id(), test_idempotency_is_stable_and_sensitive_to_identity(), main(), Phase 1 parser/normalization/identity acceptance independent of pytest.

### Community 200 - "failure_category"
Cohesion: 0.50
Nodes (4): failure_category(), BaseException, MCP task groups can wrap application errors when their transport exits., test_transport_exception_groups_preserve_safe_categories()

### Community 202 - "main"
Cohesion: 1.00
Nodes (3): main(), address(), command()

### Community 203 - "main"
Cohesion: 1.00
Nodes (3): main(), address(), command()

## Knowledge Gaps
- **941 isolated node(s):** `vehicle-platform-api`, `StandardPid`, `config`, `name`, `version` (+936 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1486 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `register_tools()` connect `register_tools` to `Adapter`, `Envelope`, `test_mcp.py`, `typing`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `AgentError` connect `AgentError` to `insufficient_run`, `test_investigation.py`, `benchmark_mcp.py`, `Envelope`, `AgentRun`, `typing`, `main.py`, `provider.py`, `budgets.py`, `resolve_context`, `agents/schemas.py`, `test_agent_runtime.py`, `InvestigationStatus`, `Orchestrator`, `investigation/domain.py`, `test_agents.py`, `failure_category`, `investigation/service.py`, `pytest`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `Phase 7A — Agent Core & Grounded Orchestration` connect `Phase 7A — Agent Core & Grounded Orchestration` to `73. Definition of Done`, `register_tools`, `55. Required test layers`, `phase-7a-traceability-ledger.md`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 68 inferred relationships involving `AgentError` (e.g. with `EvidenceRegistry` and `InvestigationRepository`) actually correct?**
  _`AgentError` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Are the 45 inferred relationships involving `router()` (e.g. with `LoggingRecipe` and `AcquisitionAuthError`) actually correct?**
  _`router()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vehicle-platform-api`, `StandardPid`, `config` to the rest of the system?**
  _941 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `AnalyticsConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.08205128205128205 - nodes in this community are weakly interconnected._