# Graph Report - phase7a-validation  (2026-10-07)

## Corpus Check
- 286 files · ~202,911 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 21 file(s) not represented in the graph (top: (none) 13, .Dockerfile 2, .example 1)

## Summary
- 2720 nodes · 6437 edges · 184 communities (133 shown, 51 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 1048 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0cdd7e51`
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
- AcquisitionCollector
- main.py
- acquisition/domain.py
- replay
- MCPSettings
- AlignedFrame
- alembic
- json
- telemetry.py
- Adapter
- datetime
- Telemetry
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
- Settings
- status.test.tsx
- test_elm_tcp_transport_connects_reads_reuses_and_closes
- compilerOptions
- detectors.py
- AgentService
- analytics-workspace.tsx
- server.py
- next
- CorrelationMiddleware
- SyntheticLiveAdapter
- devDependencies
- telemetry.test.tsx
- What You Must Do When Invoked
- SessionAnalysisService
- package.json
- AgentSettings
- test_agent_budgets.py
- observability-validation.sh
- events/service.py
- api/errors.py
- GatewayPublisher
- asyncio
- agents/service.py
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
- RawTelemetryRecord
- SanitizingExporter
- pull_request_template.md
- test_agent_repository.py
- test_postgres.py
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
- threat-model.md
- Phase 3 event and anomaly engine
- 55. Required test layers
- benchmark_stream_live.py
- ADR 0012: Versioned deterministic session analysis
- ADR 0013: Deterministic evidence-first event architecture
- test_config.py
- ADR 0019: Grounded agent state and evidence
- contracts.py
- observability/README.md
- 75. API surface
- 85. Unit and contract tests
- test_database.py
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
- HTTPInstrumentation
- field_validator
- 15. Required acquisition adapters
- Vehicle Intelligence Platform / N55 Intelligence Lab
- AcquisitionPublisher
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
- pathlib
- Terminable
- ref_next_types_root_params_d_ts
- ref_next_types_routes_d_ts
- resolve_context
- evaluate_stream_recovery.py
- Live acquisition operations and physical validation
- Validation evidence — 2026-10-01
- TerminableConnection
- Component model
- .production

## God Nodes (most connected - your core abstractions)
1. `Phase 4 — Streaming & Live Vehicle Acquisition` - 128 edges
2. `router()` - 126 edges
3. `Phase 5 — Automotive Analytics` - 115 edges
4. `AgentError` - 79 edges
5. `Settings` - 76 edges
6. `Phase 7A — Agent Core & Grounded Orchestration` - 75 edges
7. `Telemetry` - 74 edges
8. `RawTelemetryRecord` - 59 edges
9. `Database` - 54 edges
10. `AcquisitionService` - 50 edges

## Surprising Connections (you probably didn't know these)
- `Boundaries and flow` --references--> `VehicleDataAdapter`  [INFERRED]
  docs/architecture/phase-4-live-acquisition.md → apps/api/src/vehicle_platform/acquisition/adapters.py
- `Collector CLI guarantees` --references--> `preflight()`  [INFERRED]
  docs/runbooks/live-acquisition.md → apps/api/src/vehicle_platform/acquisition/domain.py
- `Collector heartbeat and acquisition context` --references--> `collector_health()`  [INFERRED]
  docs/architecture/phase-4-live-acquisition.md → apps/api/src/vehicle_platform/acquisition/quality.py
- `Execution and lifecycle` --references--> `AgentSettings`  [INFERRED]
  docs/architecture/phase-7a-grounded-agent.md → apps/api/src/vehicle_platform/agents/config.py
- `Comparability and sufficiency` --references--> `insufficient()`  [INFERRED]
  docs/architecture/phase-5-automotive-analytics.md → apps/api/tests/unit/test_agents.py

## Import Cycles
- None detected.

## Communities (184 total, 51 thin omitted)

### Community 0 - "AnalyticsConfig"
Cohesion: 0.08
Nodes (65): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+57 more)

### Community 1 - "test_acquisition.py"
Cohesion: 0.11
Nodes (27): preflight(), PreflightResult, capabilities(), FakeElm, parametrize, test_collector_health_distinguishes_transport_and_sampling(), test_elm327_only_uses_allowlisted_read_commands(), test_elm_recovers_timeout_without_reusing_sequence() (+19 more)

### Community 2 - "DetectorProfile"
Cohesion: 0.18
Nodes (22): UUID, align_observations(), Align by deterministic last-value carry-forward, expiring at max_gap. Duplicate…, rolling_median(), HeuristicPullDetector, DetectorProfile, Heuristic defaults, not manufacturer calibration data., mixed_drive() (+14 more)

### Community 3 - "router"
Cohesion: 0.13
Nodes (47): AcquisitionService, APIRouter, router(), analytics_config(), analyze_repeated_pulls(), analyze_session(), assess_session_capabilities(), bearer() (+39 more)

### Community 4 - "api/routes.py"
Cohesion: 0.09
Nodes (44): AcquisitionBatchAccepted, AcquisitionCreate, AcquisitionCreated, AcquisitionHeartbeat, AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement, AnalysisRequest (+36 more)

### Community 5 - "BoundedSpool"
Cohesion: 0.08
Nodes (19): BoundedSpool, Path, Single-collector atomic acknowledgement, only after successful publish., Path, test_bounded_spool_replays_and_reports_overflow(), test_collector_capability_failure_closes_adapter(), test_collector_heartbeat_interruption_does_not_erase_samples(), test_collector_interruption_preserves_unpublished_partial_batch() (+11 more)

### Community 6 - "acquisition/service.py"
Cohesion: 0.14
Nodes (18): assess_dataset(), collector_health(), DatasetCapability, measure_signal_quality(), datetime, Infer transport/sampling freshness only from an authenticated report. Event…, SignalQuality, AcquisitionAuthError (+10 more)

### Community 7 - "AcquisitionCollector"
Cohesion: 0.16
Nodes (10): AcquisitionCollector, report(), report_periodically(), CollectorStats, Hardware-near bounded collector with retry, backpressure, and disk replay., test_collector_reports_actual_recovery_metrics_and_payload_free_spans(), test_collector_retries_spools_and_replays_without_loss(), available() (+2 more)

### Community 8 - "main.py"
Cohesion: 0.10
Nodes (19): DatabaseProbe, Protocol, Read-only connection defaults also bound queries before a transaction begins., Agent-owned persistence over disposable TimescaleDB and actual MCP protocol., contextlib, importlib_metadata, platform, prometheus_client_parser (+11 more)

### Community 9 - "acquisition/domain.py"
Cohesion: 0.17
Nodes (15): Importance, LoggingRecipe, plan_sampling(), Priority, StrEnum, Readiness, SignalRequirement, Support (+7 more)

### Community 10 - "replay"
Cohesion: 0.17
Nodes (17): adapter_for(), AdapterKind, execute(), _preflight(), preflight_command(), probe(), Path, StrEnum (+9 more)

### Community 11 - "MCPSettings"
Cohesion: 0.09
Nodes (24): AccessToken, Verify an operator-provisioned opaque token; never issue or forward tokens., ReadTokenVerifier, MCPSettings, BaseSettings, model_validator, BaseException, ReadOnlyDatabase (+16 more)

### Community 12 - "AlignedFrame"
Cohesion: 0.08
Nodes (65): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, EventProfile, PullWindow (+57 more)

### Community 13 - "alembic"
Cohesion: 0.08
Nodes (3): alembic, upgrade(), sqlalchemy_dialects

### Community 14 - "json"
Cohesion: 0.12
Nodes (26): aiokafka, StandardPid, Constant-memory local request budgets for the Phase 4 resource boundaries., datetime, sample_id(), Explicit generic CSV mapping; no proprietary exporter assumptions., _content_hash(), asyncpg (+18 more)

### Community 15 - "telemetry.py"
Cohesion: 0.08
Nodes (25): Prevent database driver messages and SQL text from leaving the process., hmac, mcp, mcp_server_auth_provider, opentelemetry_exporter_otlp_proto_http_trace_exporter, opentelemetry_exporter_prometheus, opentelemetry_instrumentation_sqlalchemy, opentelemetry_sdk_metrics (+17 more)

### Community 16 - "Adapter"
Cohesion: 0.17
Nodes (19): Adapter, Any, Entity, UUID, PlatformError, Exception, Instrumentation, call() (+11 more)

### Community 17 - "datetime"
Cohesion: 0.18
Nodes (16): Observation, evaluate_pulls(), EvaluationResult, GroundTruthEvent, negative_scenario(), datetime, SyntheticScenario, collections (+8 more)

### Community 18 - "Telemetry"
Cohesion: 0.11
Nodes (13): main(), StreamConsumer, Database, AsyncSession, Telemetry, QueryService, parametrize, test_stream_poll_is_atomic_replay_safe_and_persists_provisional_findings() (+5 more)

### Community 19 - "AgentError"
Cohesion: 0.06
Nodes (40): EvidenceClient, MCPClient, Any, AsyncClient, Client, Protocol, AgentError, Exception (+32 more)

### Community 20 - "web/package.json"
Cohesion: 0.08
Nodes (21): dependencies, next, react, react-dom, name, private, type, version (+13 more)

### Community 21 - "Phase 4 — Streaming & Live Vehicle Acquisition"
Cohesion: 0.02
Nodes (122): 100. BimmerLink status, 102. Repository context and reusable workflows, 103. Make targets and regression gates, 104. Migration guard in CI, 105. Canonical Docker validation, 106. Golden live scenarios, 107. Acceptance — loss and duplication, 108. Acceptance — recipes (+114 more)

### Community 22 - "live-acquisition.tsx"
Cohesion: 0.08
Nodes (15): Acquisition, CollectorReport, Finalized, LiveAcquisition(), LiveFinding, LivePoint, LiveSnapshot, Pipeline (+7 more)

### Community 23 - "Phase 5 — Automotive Analytics"
Cohesion: 0.02
Nodes (113): 100. ADR, 101. AGENTS.md / repository workflow, 102. Make targets, 103. CI regression protection, 104. Push early, 105. Pull request, 106. GitHub workflow behavior, 107. Do not repeat the premature Phase 4 completion behavior (+105 more)

### Community 24 - "register_tools"
Cohesion: 0.10
Nodes (21): MCPServer, register_tools(), compare_configurations(), get_cross_session_analytics(), get_event(), get_pull_summary(), get_repeated_pull_analysis(), get_session_analytics() (+13 more)

### Community 25 - "vehicle-workspace.tsx"
Cohesion: 0.11
Nodes (20): AgentEvent, AgentRun, Audit, DetectedEvent, json(), Pull, Segment, Session (+12 more)

### Community 26 - "test_gateway_publisher_classifies_responses"
Cohesion: 0.12
Nodes (8): Exception, MonkeyPatch, test_consumer_database_failure_exits_without_sql_inputs(), fail(), test_gateway_publisher_classifies_responses(), test_gateway_transport_errors_enter_retry_spool_path(), test_spool_failed_atomic_ack_preserves_original(), CaptureFixture

### Community 27 - "normalize_value"
Cohesion: 0.12
Nodes (22): DataQuality, NormalizationError, normalize_value(), parse_timestamp(), StrEnum, ValueError, SignalDefinition, SyntheticTelemetrySource (+14 more)

### Community 28 - "evaluate_agent_grounding.py"
Cohesion: 0.12
Nodes (17): httpx2, mcp_client_stdio, mcp_client_streamable_http, domain_fingerprint(), Any, Aggregate content changes, including updates, in disposable fixture tables., evaluate(), connection() (+9 more)

### Community 29 - "Phase 7A — Agent Core & Grounded Orchestration"
Cohesion: 0.03
Nodes (72): 10. Agent state, 11. AgentRun persistence, 12. ToolCall persistence / audit trail, 13. Evidence model, 14. Claim → Evidence grounding, 15. Unsupported-claim detection, 16. Structured answer contract, 17. Natural-language API (+64 more)

### Community 30 - "test_mcp.py"
Cohesion: 0.17
Nodes (13): parametrize, test_actual_response_limit_and_unknown_tool(), big(), test_analytics_selection_reports_truncation(), test_auth(), test_http_requires_token(), test_instrumented_errors(), test_limited_quality_does_not_claim_missing_history() (+5 more)

### Community 31 - "Settings"
Cohesion: 0.11
Nodes (27): BaseSettings, Settings, create_app(), test_clean_upgrade_downgrade_reupgrade_and_readiness(), test_expired_acquisition_releases_capacity_without_accepting_its_token(), test_retrospective_signed_csv_duplicates_and_analytics_identity(), test_sequence_overflow_is_dead_lettered_and_valid_edge_persists(), Probe (+19 more)

### Community 32 - "status.test.tsx"
Cohesion: 0.18
Nodes (14): dynamic, GET(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready, SystemStatus (+6 more)

### Community 33 - "test_elm_tcp_transport_connects_reads_reuses_and_closes"
Cohesion: 0.15
Nodes (3): ElmTcpTransport, Concrete ELM327 TCP/RFCOMM bridge transport with a strict read-only command…, test_elm_tcp_transport_connects_reads_reuses_and_closes()

### Community 34 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 35 - "detectors.py"
Cohesion: 0.18
Nodes (12): compute_pull_metrics(), HeuristicSegmentDetector, _mean(), PullDetector, Protocol, SegmentDetector, _slope(), DetectedPull (+4 more)

### Community 36 - "AgentService"
Cohesion: 0.07
Nodes (28): Any, Redact only strings, preserving numeric facts and JSON structure., redact_data(), AgentInstrumentation, connect(), AgentRepository, AsyncSession, UUID (+20 more)

### Community 37 - "analytics-workspace.tsx"
Cohesion: 0.13
Nodes (11): AnalyticsWorkspace(), history(), Configuration, curveLabels, NormalizedBin, Profile, Pull, request() (+3 more)

### Community 38 - "server.py"
Cohesion: 0.12
Nodes (20): One registration shared by stdio and authenticated Streamable HTTP., ErrorCode, StrEnum, ToolError, UUID, tool_error(), argparse, mcp_server_auth_settings (+12 more)

### Community 39 - "next"
Cohesion: 0.18
Nodes (6): config, GET, POST, apps_web_src_app_globals, metadata, next

### Community 40 - "CorrelationMiddleware"
Cohesion: 0.13
Nodes (9): CorrelationMiddleware, ASGIApp, Receive, Scope, Send, PlatformAPI, ASGIApp, FastAPI (+1 more)

### Community 41 - "SyntheticLiveAdapter"
Cohesion: 0.09
Nodes (11): Elm327Adapter, ElmTransport, Protocol, Read-only adapter contract. Deliberately has no command/write operation., Generic standard-mode OBD-II reader; no proprietary or write commands., ReplayAdapter, SyntheticLiveAdapter, VehicleDataAdapter (+3 more)

### Community 42 - "devDependencies"
Cohesion: 0.12
Nodes (16): devDependencies, @axe-core/playwright, eslint, @eslint/compat, eslint-config-next, jsdom, @playwright/test, @testing-library/jest-dom (+8 more)

### Community 43 - "telemetry.test.tsx"
Cohesion: 0.15
Nodes (10): detectedEvent, pull, segment, session, signals, vehicle, window, @testing-library/jest-dom (+2 more)

### Community 44 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 45 - "SessionAnalysisService"
Cohesion: 0.35
Nodes (7): AnalysisLimitError, UUID, ValueError, SessionAnalysisService, AnalysisResult, Pull, SessionSegment

### Community 46 - "package.json"
Cohesion: 0.11
Nodes (18): devDependencies, openapi-typescript, prettier, engines, node, name, packageManager, private (+10 more)

### Community 47 - "AgentSettings"
Cohesion: 0.13
Nodes (21): AgentSettings, BaseSettings, model_validator, OpenAIProvider, ModelInput, ModelTurn, Provider, Protocol (+13 more)

### Community 48 - "test_agent_budgets.py"
Cohesion: 0.07
Nodes (29): AgentRequestBudgetMiddleware, ASGIApp, Receive, Scope, Send, Bound admission and body buffering before FastAPI parses an agent question., Per-process budgets, with no unbounded per-client identifier dictionaries. The…, ResourceBudgetMiddleware (+21 more)

### Community 49 - "observability-validation.sh"
Cohesion: 0.40
Nodes (4): scripts_lib_wait_http_sh, observability-validation.sh script, wait_prometheus_query(), stack-smoke.sh script

### Community 50 - "events/service.py"
Cohesion: 0.20
Nodes (13): DetectedEvent, EventAnalysisResult, EventSummary, analyze_session_events(), get_event(), list_session_events(), list_vehicle_events(), summarize_session_events() (+5 more)

### Community 51 - "api/errors.py"
Cohesion: 0.21
Nodes (13): FastAPI, register_errors(), agent_error(), http_error(), invalid(), unavailable(), unexpected(), response() (+5 more)

### Community 52 - "GatewayPublisher"
Cohesion: 0.15
Nodes (5): run(), GatewayPublisher, UUID, test_gateway_heartbeat_is_scoped_and_failures_are_explicit(), main()

### Community 53 - "asyncio"
Cohesion: 0.17
Nodes (21): asyncio, httpx, os, main(), Dedicated browser gate: controlled real API, authenticated HTTP MCP and…, Independent controlled temporal/configuration fixtures in disposable…, seed_agent(), main() (+13 more)

### Community 54 - "agents/service.py"
Cohesion: 0.13
Nodes (29): accumulate(), ToolRequest, Answer, Binding, Claim, Classification, Draft, Evidence (+21 more)

### Community 55 - "Catalog"
Cohesion: 0.33
Nodes (4): Catalog, Any, Entity, UUID

### Community 56 - "Orchestrator"
Cohesion: 0.24
Nodes (7): Orchestrator, Any, UUID, Execution, GraphState, test_real_protocol_graph_with_duplicate_call(), TypedDict

### Community 57 - "MappedCSVTelemetrySource"
Cohesion: 0.16
Nodes (19): MappedCSVTelemetrySource, mapping(), parametrize, test_absent_mapping_and_invalid_headers_are_rejected(), test_explicit_identity_sequence_are_preserved(), test_explicit_wide_csv_mapping_preserves_units_time_and_provenance(), test_header_inspection_rejects_missing_ambiguous_or_oversized_csv(), test_invalid_identity_or_sequence_is_rejected() (+11 more)

### Community 59 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 60 - "security-policy.py"
Cohesion: 0.36
Nodes (9): Namespace, accepted(), load_exceptions(), load_findings(), main(), parse_args(), Any, Path (+1 more)

### Community 61 - "mcp-validation.sh"
Cohesion: 0.25
Nodes (6): DATABASE_URL, ENVIRONMENT, MCP_TEST_PROJECT, mcp-validation.sh script, TEST_DATABASE_URL, TEST_KAFKA_PORT

### Community 62 - "test_agents.py"
Cohesion: 0.13
Nodes (39): canonical_hash(), EvidenceRegistry, facts(), Any, UUID, render_binding(), validate(), comparison() (+31 more)

### Community 63 - "README.md"
Cohesion: 0.12
Nodes (7): Contributing, Service boundaries, System context, Toolchain selection, Local development, Security automation, Phase 6 traceability ledger

### Community 64 - "PHASE 0 COMPLETION REPORT"
Cohesion: 0.08
Nodes (22): Closure, ADRs created, Applications, Architecture, CI/CD, Closure rerun result, Codex context, Database (+14 more)

### Community 65 - "IngestionService"
Cohesion: 0.21
Nodes (11): ImportResult, TelemetryWindow, create_modification(), create_session(), import_csv(), TelemetrySource, IngestionService, AsyncSession (+3 more)

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
Cohesion: 0.29
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
Cohesion: 0.06
Nodes (30): devices(), ADR 0014: Kafka durable acquisition stream, Consequences, Context, Decision, ADR 0017: Retrospective evidence and execution identity, Alternatives, Consequences and risks (+22 more)

### Community 100 - "graphify reference: extra exports and benchmark"
Cohesion: 0.25
Nodes (7): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 101 - "RawTelemetryRecord"
Cohesion: 0.18
Nodes (13): UUID, RawTelemetryMessage, LiveOBDSource, Protocol, Adapter boundary only: Phase 1 intentionally provides no hardware…, RawTelemetryRecord, validate_sequence(), test_stream_contract_and_dataset_capability() (+5 more)

### Community 102 - "SanitizingExporter"
Cohesion: 0.20
Nodes (5): SanitizingExporter, JSONFormatter, Any, LogRecord, SpanExporter

### Community 103 - "pull_request_template.md"
Cohesion: 0.22
Nodes (8): Database/contract impact, Documentation, How it was validated, Observability impact, Risks, Security impact, What changed, Why

### Community 104 - "test_agent_repository.py"
Cohesion: 0.26
Nodes (11): parametrize, Agent repository SQL/serialization boundaries; real transactions are tested…, rows(), test_database_errors_are_normalized_and_session_closes(), test_interrupted_run_reconciliation_is_bounded_and_terminal(), test_missing_driver_fails_closed(), test_repository_not_found_and_bounds(), test_repository_run_audit_and_stream_serialization() (+3 more)

### Community 105 - "test_postgres.py"
Cohesion: 0.22
Nodes (8): alembic_config, alembic_script, run(), run_sync(), Requires an explicitly supplied disposable test database. Never skips silently., Connection, sqlalchemy_engine, sqlalchemy_ext_asyncio

### Community 106 - "Phase 5 automotive analytics"
Cohesion: 0.25
Nodes (7): Comparability and sufficiency, Metrics and normalization, Phase 5 automotive analytics, Pipeline and source of truth, Retrospective calculation identity, Retrospective metric and presentation completeness, Robust statistics and provenance

### Community 107 - "ADR 0018: Read-only MCP application adapter"
Cohesion: 0.17
Nodes (10): ADR 0016: Deterministic, immutable automotive analytics, Consequences, Decision, Status, ADR 0018: Read-only MCP application adapter, Alternatives, Consequences and risks, Context (+2 more)

### Community 108 - "N55 Intelligence Lab"
Cohesion: 0.22
Nodes (9): Arquitetura e continuidade, Desenvolvimento e testes, Estado atual, N55 Intelligence Lab, Observabilidade, Phase 6 MCP, Phase 7A grounded agent, Quick start (+1 more)

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

### Community 120 - "threat-model.md"
Cohesion: 0.18
Nodes (9): Failure handling, Grounded agent operation, Local configuration, Validation commands, Initial threat model, Original Phase 4 local resource budgets, Phase 4 acquisition threats, Phase 6 MCP boundary (+1 more)

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

### Community 126 - "test_config.py"
Cohesion: 0.22
Nodes (10): MonkeyPatch, parametrize, test_build_timestamp_normalized_to_utc(), test_empty_optional_container_metadata(), test_invalid_settings(), test_malformed_database_config(), test_required_database(), test_safe_metadata() (+2 more)

### Community 127 - "ADR 0019: Grounded agent state and evidence"
Cohesion: 0.15
Nodes (11): ADR 0019: Grounded agent state and evidence, Alternatives, Consequences and risks, Context, Decision, Status, Boundaries, Context and evidence (+3 more)

### Community 128 - "contracts.py"
Cohesion: 0.29
Nodes (9): ErrorDetail, ErrorResponse, Health, BaseModel, Ready, Version, live(), ready() (+1 more)

### Community 129 - "observability/README.md"
Cohesion: 0.29
Nodes (6): Grounded agent, MCP, Observability, Phase 2 analysis, Phase 3 events, Retrospective instrumentation checks

### Community 130 - "75. API surface"
Cohesion: 0.33
Nodes (6): 75. API surface, Acquisition, Ingestion, Live client, Logging objectives, Recipes

### Community 131 - "85. Unit and contract tests"
Cohesion: 0.33
Nodes (6): 85. Unit and contract tests, Collector, Live analysis, Recipes, Sampling, Stream

### Community 132 - "test_database.py"
Cohesion: 0.24
Nodes (8): DependencyUnavailable, Exception, Infrastructure failed its bounded readiness check., parametrize, test_extension_required(), test_otlp_configured(), test_real_database_unreachable(), test_sqlalchemy_failure()

### Community 133 - "MCP server"
Cohesion: 0.33
Nodes (6): Docker, Limits and troubleshooting, Local stdio, MCP server, Streamable HTTP, Validation

### Community 134 - "Phase 6 acceptance evidence"
Cohesion: 0.33
Nodes (6): Executed acceptance checkpoint, Independent MCP evidence, Limitations and deferred scope, Measured performance and bounds, Phase 6 acceptance evidence, Remote proof and final HEAD identity

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
Cohesion: 0.33
Nodes (5): Phase 3 acceptance, Phase 6 acceptance, Phase 7A acceptance, Retrospective phase gates, Testing strategy

### Community 144 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 145 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 146 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 147 - "HTTPInstrumentation"
Cohesion: 0.22
Nodes (4): main(), HTTPInstrumentation, ASGI boundary preserving W3C trace context and counting SDK auth rejections., test_http_trace_context_and_auth_rejections()

### Community 148 - "field_validator"
Cohesion: 0.29
Nodes (3): datetime, field_validator, SecretStr

### Community 149 - "15. Required acquisition adapters"
Cohesion: 0.50
Nodes (4): 15. Required acquisition adapters, Real read-only OBD adapter path, Replay adapter, Synthetic live adapter

### Community 151 - "AcquisitionPublisher"
Cohesion: 0.29
Nodes (3): AIOKafkaProducer, AcquisitionPublisher, Application-owned producer; bounded concurrent publication and shutdown.

### Community 153 - "101. ADRs"
Cohesion: 0.67
Nodes (3): 101. ADRs, Acquisition lifecycle / recipes, Streaming architecture

### Community 154 - "Phase 7A acceptance"
Cohesion: 0.14
Nodes (10): Current phase, Roadmap, Baseline and delivery boundary, Executed checkpoint: `881fcca0bb75acf9369bbbf25854c32d626aa017`, Final receipt requirements, Missing-evidence correction: `4df84696ab3ffb5d900399877849975b008fe4cf`, Phase 7A acceptance, Real provider and practical limits (+2 more)

### Community 155 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 173 - "pathlib"
Cohesion: 0.15
Nodes (8): pathlib, Validate local skills, scoped context, declarative YAML and Markdown links., Enforce separate line and branch thresholds for the generated local coverage…, Hash the exact reviewable working tree without printing file contents., Write canonical CI validation summaries without converting failures into passes., subprocess, xml_etree, yaml

### Community 177 - "resolve_context"
Cohesion: 0.71
Nodes (6): at(), effective(), Any, datetime, UUID, resolve_context()

### Community 178 - "evaluate_stream_recovery.py"
Cohesion: 0.38
Nodes (5): compose(), main(), Real-stack Phase 4 recovery; owns fixtures, never deletes application volumes., Wait until the real Next.js status and domain proxies recover too., wait_for_browser_proxies()

### Community 179 - "Live acquisition operations and physical validation"
Cohesion: 0.33
Nodes (5): Collector CLI guarantees, Live acquisition operations and physical validation, Preserve an older Kafka storage path, Safe physical Vgate validation procedure, Topology and recovery

### Community 180 - "Validation evidence — 2026-10-01"
Cohesion: 0.40
Nodes (4): Canonical GitHub workflow run (2026-10-02), Closure rerun (23:33–23:38 UTC), Split-executor implementation, Validation evidence — 2026-10-01

### Community 182 - "Component model"
Cohesion: 0.50
Nodes (3): Component model, CURRENT, FUTURE

## Knowledge Gaps
- **805 isolated node(s):** `vehicle-platform-api`, `StandardPid`, `config`, `name`, `version` (+800 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1289 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `register_tools()` connect `register_tools` to `Adapter`, `MCPSettings`, `server.py`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `Phase 7A — Agent Core & Grounded Orchestration` connect `Phase 7A — Agent Core & Grounded Orchestration` to `73. Definition of Done`, `register_tools`, `Phase 7A acceptance`, `55. Required test layers`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `8. Vehicle Context Resolver — mandatory` connect `register_tools` to `Phase 7A — Agent Core & Grounded Orchestration`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `router()` (e.g. with `LoggingRecipe` and `AcquisitionAuthError`) actually correct?**
  _`router()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `AgentError` (e.g. with `EvidenceRegistry` and `MCPClient`) actually correct?**
  _`AgentError` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `Settings` (e.g. with `run()` and `AcquisitionPublisher`) actually correct?**
  _`Settings` has 50 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vehicle-platform-api`, `StandardPid`, `config` to the rest of the system?**
  _805 weakly-connected nodes found - possible documentation gaps or missing edges._