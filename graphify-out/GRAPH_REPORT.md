# Graph Report - vehicle-intelligence-platform  (2026-10-07)

## Corpus Check
- 286 files · ~200,078 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: (none) 12, .Dockerfile 2, .example 1)

## Summary
- 2714 nodes · 6428 edges · 177 communities (125 shown, 52 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 1046 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `903caa21`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AnalyticsConfig
- PullWindow
- DetectorProfile
- router
- api/routes.py
- BoundedSpool
- acquisition/service.py
- RawTelemetryRecord
- adapter.py
- preflight
- acquisition/cli.py
- MCPSettings
- AlignedFrame
- alembic
- json
- mcp_protocol_e2e.py
- Adapter
- .read_resource
- Telemetry
- AgentError
- web/package.json
- Phase 4 — Streaming & Live Vehicle Acquisition
- live-acquisition.tsx
- Phase 5 — Automotive Analytics
- register_tools
- vehicle-workspace.tsx
- test_elm_tcp_transport_connects_reads_reuses_and_closes
- normalize_value
- telemetry.py
- Phase 7A — Agent Core & Grounded Orchestration
- EventEngine
- Settings
- status.test.tsx
- check_coverage.py
- compilerOptions
- detectors.py
- AgentRepository
- analytics-workspace.tsx
- mcp/cli.py
- next
- main.py
- test_acquisition.py
- devDependencies
- telemetry.test.tsx
- What You Must Do When Invoked
- SessionAnalysisService
- package.json
- provider.py
- Elm327Adapter
- observability-validation.sh
- events/service.py
- register_errors
- .export
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
- phase-0-completion-report.md
- vehicle-platform-api
- 126. Final delivery report
- 45. Required synthetic scenarios
- agents/schemas.py
- 73. Definition of Done
- agent-workspace.test.tsx
- CSVSignalColumn
- Phases 0–5 retrospective hardening
- graphify reference: extra exports and benchmark
- StreamConsumer
- test_database.py
- pull_request_template.md
- resolve_context
- SyntheticLiveAdapter
- Phase 5 automotive analytics
- Container scan findings — 2026-10-01
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
- evaluate_agent_grounding.py
- ADR 0018: Read-only MCP application adapter
- sqlalchemy_ext_asyncio
- observability/README.md
- 75. API surface
- 85. Unit and contract tests
- Live acquisition operations and physical validation
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
- ADR 0015: Versioned recipes and acquisition lifecycle
- Component model
- 15. Required acquisition adapters
- Vehicle Intelligence Platform / N55 Intelligence Lab
- DatabaseProbe
- graphify reference: GitHub clone and cross-repo merge
- 101. ADRs
- phase-7a-acceptance.md
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
- Terminable
- ref_next_types_root_params_d_ts
- ref_next_types_routes_d_ts

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
- `Execution and lifecycle` --references--> `AgentSettings`  [INFERRED]
  docs/architecture/phase-7a-grounded-agent.md → apps/api/src/vehicle_platform/agents/config.py
- `Comparability and sufficiency` --references--> `insufficient()`  [INFERRED]
  docs/architecture/phase-5-automotive-analytics.md → apps/api/tests/unit/test_agents.py
- `Decision` --references--> `LoggingRecipe`  [INFERRED]
  docs/adr/0015-acquisition-lifecycle-and-recipes.md → apps/api/src/vehicle_platform/acquisition/domain.py

## Import Cycles
- None detected.

## Communities (177 total, 52 thin omitted)

### Community 0 - "AnalyticsConfig"
Cohesion: 0.08
Nodes (65): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+57 more)

### Community 1 - "PullWindow"
Cohesion: 0.13
Nodes (26): PullWindow, evaluate_events(), EventClassMetrics, EventEvaluation, _overlaps(), One-to-one deterministic matching by type, pull and temporal overlap., anomaly_scenario(), AnomalyInjection (+18 more)

### Community 2 - "DetectorProfile"
Cohesion: 0.12
Nodes (33): UUID, align_observations(), Align by deterministic last-value carry-forward, expiring at max_gap. Duplicate…, rolling_median(), HeuristicPullDetector, DetectorProfile, Observation, StrEnum (+25 more)

### Community 3 - "router"
Cohesion: 0.10
Nodes (52): Health, BaseModel, Ready, Version, APIRouter, router(), analytics_config(), analyze_repeated_pulls() (+44 more)

### Community 4 - "api/routes.py"
Cohesion: 0.10
Nodes (41): AcquisitionBatchAccepted, AcquisitionCreate, AcquisitionCreated, AcquisitionHeartbeat, AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement, AnalysisRequest (+33 more)

### Community 5 - "BoundedSpool"
Cohesion: 0.08
Nodes (19): BoundedSpool, Path, Single-collector atomic acknowledgement, only after successful publish., Path, test_bounded_spool_replays_and_reports_overflow(), test_collector_capability_failure_closes_adapter(), test_collector_heartbeat_interruption_does_not_erase_samples(), test_collector_interruption_preserves_unpublished_partial_batch() (+11 more)

### Community 6 - "acquisition/service.py"
Cohesion: 0.13
Nodes (24): aiokafka, AIOKafkaProducer, assess_dataset(), collector_health(), DatasetCapability, measure_signal_quality(), datetime, Infer transport/sampling freshness only from an authenticated report. Event… (+16 more)

### Community 7 - "RawTelemetryRecord"
Cohesion: 0.12
Nodes (15): AcquisitionCollector, report(), report_periodically(), CollectorStats, Hardware-near bounded collector with retry, backpressure, and disk replay., LiveOBDSource, Protocol, Adapter boundary only: Phase 1 intentionally provides no hardware… (+7 more)

### Community 8 - "adapter.py"
Cohesion: 0.10
Nodes (37): Bounded context repository for records currently owned by HTTP SQL handlers., Read-only connection defaults also bound queries before a transaction begins., ErrorCode, PlatformError, Exception, StrEnum, ToolError, UUID (+29 more)

### Community 9 - "preflight"
Cohesion: 0.14
Nodes (18): ReplayAdapter, DeviceCapabilities, Importance, LoggingRecipe, plan_sampling(), preflight(), PreflightResult, Priority (+10 more)

### Community 10 - "acquisition/cli.py"
Cohesion: 0.11
Nodes (25): ElmTcpTransport, Concrete ELM327 TCP/RFCOMM bridge transport with a strict read-only command…, adapter_for(), AdapterKind, devices(), execute(), _preflight(), preflight_command() (+17 more)

### Community 11 - "MCPSettings"
Cohesion: 0.07
Nodes (27): AccessToken, Verify an operator-provisioned opaque token; never issue or forward tokens., ReadTokenVerifier, MCPSettings, BaseSettings, model_validator, BaseException, ReadOnlyDatabase (+19 more)

### Community 12 - "AlignedFrame"
Cohesion: 0.15
Nodes (28): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, EventProfile, StrEnum (+20 more)

### Community 13 - "alembic"
Cohesion: 0.08
Nodes (3): alembic, upgrade(), sqlalchemy_dialects

### Community 14 - "json"
Cohesion: 0.10
Nodes (30): StandardPid, UUID, Constant-memory local request budgets for the Phase 4 resource boundaries., parse_timestamp(), datetime, sample_id(), validate_sequence(), Explicit generic CSV mapping; no proprietary exporter assumptions. (+22 more)

### Community 15 - "mcp_protocol_e2e.py"
Cohesion: 0.11
Nodes (14): httpx2, mcp_client_streamable_http, evaluate(), Any, Client, main(), Official HTTP client exercises the real immutable MCP container and restart., ready_endpoint() (+6 more)

### Community 16 - "Adapter"
Cohesion: 0.15
Nodes (17): Adapter, Any, Entity, UUID, BaseModel, model_validator, Warning, Window (+9 more)

### Community 17 - ".read_resource"
Cohesion: 0.24
Nodes (9): AnyUrl, Any, Exception, ToolError, SafeMCPServer, CallToolResult, Context, InputRequiredResult (+1 more)

### Community 18 - "Telemetry"
Cohesion: 0.11
Nodes (16): main(), TelemetryPoint, Database, AsyncSession, Telemetry, QueryService, telemetry(), importlib_metadata (+8 more)

### Community 19 - "AgentError"
Cohesion: 0.07
Nodes (33): MCPClient, Any, AsyncClient, Client, AgentError, Exception, failure_category(), BaseException (+25 more)

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
Cohesion: 0.11
Nodes (19): MCPServer, register_tools(), get_cross_session_analytics(), get_pull_summary(), get_repeated_pull_analysis(), get_session_analytics(), get_session_capabilities(), get_session_summary() (+11 more)

### Community 25 - "vehicle-workspace.tsx"
Cohesion: 0.11
Nodes (20): AgentEvent, AgentRun, Audit, DetectedEvent, json(), Pull, Segment, Session (+12 more)

### Community 26 - "test_elm_tcp_transport_connects_reads_reuses_and_closes"
Cohesion: 0.08
Nodes (9): Exception, MonkeyPatch, test_consumer_database_failure_exits_without_sql_inputs(), fail(), test_elm_tcp_transport_connects_reads_reuses_and_closes(), test_gateway_publisher_classifies_responses(), test_gateway_transport_errors_enter_retry_spool_path(), test_spool_failed_atomic_ack_preserves_original() (+1 more)

### Community 27 - "normalize_value"
Cohesion: 0.13
Nodes (20): DataQuality, NormalizationError, normalize_value(), StrEnum, ValueError, SignalDefinition, SyntheticTelemetrySource, parametrize (+12 more)

### Community 28 - "telemetry.py"
Cohesion: 0.10
Nodes (16): Prevent database driver messages and SQL text from leaving the process., SanitizingExporter, JSONFormatter, Any, test_database_error_propagation_cannot_leak_through_parent_spans(), test_database_trace_export_redacts_driver_inputs(), test_json_logs_do_not_render_exception_secrets(), test_sql_text_is_removed_from_non_database_successful_spans() (+8 more)

### Community 29 - "Phase 7A — Agent Core & Grounded Orchestration"
Cohesion: 0.03
Nodes (72): 10. Agent state, 11. AgentRun persistence, 12. ToolCall persistence / audit trail, 13. Evidence model, 14. Claim → Evidence grounding, 15. Unsupported-claim detection, 16. Structured answer contract, 17. Natural-language API (+64 more)

### Community 30 - "EventEngine"
Cohesion: 0.43
Nodes (14): EventEngine, base(), frames(), pull(), test_comparable_pulls(), test_fuel_drop_requires_sustained_observation_not_single_low_spike(), test_low_load_variation_is_not_fuel_or_throttle_event(), test_never_available_channels_do_not_claim_sensor_dropout() (+6 more)

### Community 31 - "Settings"
Cohesion: 0.05
Nodes (46): alembic_config, alembic_script, AcquisitionPublisher, Application-owned producer; bounded concurrent publication and shutdown., BaseSettings, datetime, model_validator, Settings (+38 more)

### Community 32 - "status.test.tsx"
Cohesion: 0.18
Nodes (14): dynamic, GET(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready, SystemStatus (+6 more)

### Community 34 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 35 - "detectors.py"
Cohesion: 0.20
Nodes (10): compute_pull_metrics(), HeuristicSegmentDetector, _mean(), PullDetector, Protocol, SegmentDetector, _slope(), DetectedPull (+2 more)

### Community 36 - "AgentRepository"
Cohesion: 0.11
Nodes (23): AgentRepository, AsyncSession, Protocol, UUID, Commit terminal state and stream event together; reconnect cannot race…, Only agent-owned tables. Vehicle existence is resolved through MCP, never SQL., Recover interrupted runs beyond the hard 180s runtime plus cleanup allowance., TerminableConnection (+15 more)

### Community 37 - "analytics-workspace.tsx"
Cohesion: 0.13
Nodes (11): AnalyticsWorkspace(), history(), Configuration, curveLabels, NormalizedBin, Profile, Pull, request() (+3 more)

### Community 38 - "mcp/cli.py"
Cohesion: 0.13
Nodes (10): main(), One registration shared by stdio and authenticated Streamable HTTP., HTTPInstrumentation, ASGI boundary preserving W3C trace context and counting SDK auth rejections., test_http_trace_context_and_auth_rejections(), argparse, mcp_server_transport_security, starlette_middleware_base (+2 more)

### Community 39 - "next"
Cohesion: 0.18
Nodes (6): config, GET, POST, apps_web_src_app_globals, metadata, next

### Community 40 - "main.py"
Cohesion: 0.07
Nodes (24): agent_router(), audit(), stream(), APIRouter, RunAudit, Per-process budgets, with no unbounded per-client identifier dictionaries. The…, ResourceBudgetMiddleware, ErrorDetail (+16 more)

### Community 41 - "test_acquisition.py"
Cohesion: 0.08
Nodes (26): Readiness, capabilities(), FakeElm, parametrize, test_collector_health_distinguishes_transport_and_sampling(), test_elm327_only_uses_allowlisted_read_commands(), test_elm_recovers_timeout_without_reusing_sequence(), immediate() (+18 more)

### Community 42 - "devDependencies"
Cohesion: 0.12
Nodes (16): devDependencies, @axe-core/playwright, eslint, @eslint/compat, eslint-config-next, jsdom, @playwright/test, @testing-library/jest-dom (+8 more)

### Community 43 - "telemetry.test.tsx"
Cohesion: 0.15
Nodes (10): detectedEvent, pull, segment, session, signals, vehicle, window, @testing-library/jest-dom (+2 more)

### Community 44 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (23): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents) (+15 more)

### Community 45 - "SessionAnalysisService"
Cohesion: 0.20
Nodes (12): AnalysisLimitError, UUID, ValueError, SessionAnalysisService, AnalysisResult, Pull, SessionSegment, analyze_session() (+4 more)

### Community 46 - "package.json"
Cohesion: 0.11
Nodes (18): devDependencies, openapi-typescript, prettier, engines, node, name, packageManager, private (+10 more)

### Community 47 - "provider.py"
Cohesion: 0.12
Nodes (27): OpenAIProvider, accumulate(), ModelInput, ModelTurn, ToolRequest, Binding, Claim, Draft (+19 more)

### Community 48 - "Elm327Adapter"
Cohesion: 0.14
Nodes (7): Elm327Adapter, ElmTransport, Protocol, Read-only adapter contract. Deliberately has no command/write operation., Generic standard-mode OBD-II reader; no proprietary or write commands., VehicleDataAdapter, SamplingPlanItem

### Community 49 - "observability-validation.sh"
Cohesion: 0.40
Nodes (4): scripts_lib_wait_http_sh, observability-validation.sh script, wait_prometheus_query(), stack-smoke.sh script

### Community 50 - "events/service.py"
Cohesion: 0.22
Nodes (11): DetectedEvent, EventSummary, analyze_session_events(), get_event(), list_session_events(), list_vehicle_events(), EventAnalysisLimitError, EventAnalysisService (+3 more)

### Community 51 - "register_errors"
Cohesion: 0.06
Nodes (36): AgentRequestBudgetMiddleware, ASGIApp, Receive, Scope, Send, Bound admission and body buffering before FastAPI parses an agent question., TokenBucket, FastAPI (+28 more)

### Community 52 - ".export"
Cohesion: 0.33
Nodes (4): graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), ReadableSpan, SpanExportResult

### Community 53 - "asyncio"
Cohesion: 0.15
Nodes (23): asyncio, httpx, os, pathlib, main(), Dedicated browser gate: controlled real API, authenticated HTTP MCP and…, Independent controlled temporal/configuration fixtures in disposable…, seed_agent() (+15 more)

### Community 54 - "agents/service.py"
Cohesion: 0.09
Nodes (23): AgentSettings, Any, BaseSettings, model_validator, Redact only strings, preserving numeric facts and JSON structure., redact_data(), AgentInstrumentation, connect() (+15 more)

### Community 55 - "Catalog"
Cohesion: 0.33
Nodes (4): Catalog, Any, Entity, UUID

### Community 56 - "Orchestrator"
Cohesion: 0.35
Nodes (5): Orchestrator, Any, UUID, GraphState, TypedDict

### Community 57 - "MappedCSVTelemetrySource"
Cohesion: 0.15
Nodes (19): inspect_csv(), MappedCSVTelemetrySource, mapping(), parametrize, test_absent_mapping_and_invalid_headers_are_rejected(), test_explicit_identity_sequence_are_preserved(), test_explicit_wide_csv_mapping_preserves_units_time_and_provenance(), test_header_inspection_rejects_missing_ambiguous_or_oversized_csv() (+11 more)

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
Cohesion: 0.11
Nodes (45): render_binding(), validate(), Envelope, url(), url(), provider(), comparison(), parametrize (+37 more)

### Community 63 - "README.md"
Cohesion: 0.12
Nodes (7): Contributing, Service boundaries, System context, Toolchain selection, Local development, Security automation, Phase 6 traceability ledger

### Community 64 - "PHASE 0 COMPLETION REPORT"
Cohesion: 0.11
Nodes (19): ADRs created, Applications, Architecture, CI/CD, Closure rerun result, Codex context, Database, Deferred deliberately to Phase 1+ (+11 more)

### Community 65 - "IngestionService"
Cohesion: 0.19
Nodes (12): ImportResult, TelemetryWindow, create_modification(), create_session(), TelemetrySource, _content_hash(), IngestionService, AsyncSession (+4 more)

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

### Community 91 - "phase-0-completion-report.md"
Cohesion: 0.17
Nodes (7): Closure, Phase 0 task map, Phase 1 outline — Vehicle & Telemetry Core, Canonical GitHub workflow run (2026-10-02), Closure rerun (23:33–23:38 UTC), Split-executor implementation, Validation evidence — 2026-10-01

### Community 93 - "126. Final delivery report"
Cohesion: 0.14
Nodes (14): 126. Final delivery report, Architecture, Explicit deferrals, GitHub, Hardware, Live system, Migrations, Observability (+6 more)

### Community 94 - "45. Required synthetic scenarios"
Cohesion: 0.15
Nodes (13): 45. Required synthetic scenarios, A. Identical repeated pulls, B. Progressive IAT accumulation, C. Progressive boost reduction, D. Fuel-pressure degradation pattern, E. Slower normalized acceleration, F. Noisy but unchanged vehicle, G. Different configuration (+5 more)

### Community 95 - "agents/schemas.py"
Cohesion: 0.19
Nodes (17): canonical_hash(), EvidenceRegistry, facts(), Any, UUID, Answer, Ask, Classification (+9 more)

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
Nodes (32): ADR 0014: Kafka durable acquisition stream, Consequences, Context, Decision, ADR 0016: Deterministic, immutable automotive analytics, Consequences, Decision, Status (+24 more)

### Community 100 - "graphify reference: extra exports and benchmark"
Cohesion: 0.25
Nodes (7): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 101 - "StreamConsumer"
Cohesion: 0.31
Nodes (6): RawTelemetryMessage, StreamConsumer, parametrize, test_sequence_overflow_rejected_at_every_input_boundary(), test_sequence_valid_edges_remain_compatible(), main()

### Community 102 - "test_database.py"
Cohesion: 0.20
Nodes (10): DependencyUnavailable, Exception, Infrastructure failed its bounded readiness check., parametrize, test_extension_required(), test_otlp_configured(), test_real_database_unreachable(), test_sqlalchemy_failure() (+2 more)

### Community 103 - "pull_request_template.md"
Cohesion: 0.22
Nodes (8): Database/contract impact, Documentation, How it was validated, Observability impact, Risks, Security impact, What changed, Why

### Community 104 - "resolve_context"
Cohesion: 0.57
Nodes (7): at(), effective(), Any, datetime, UUID, resolve_context(), test_temporal_context_removal_and_boundary()

### Community 105 - "SyntheticLiveAdapter"
Cohesion: 0.15
Nodes (6): SyntheticLiveAdapter, test_collector_reports_actual_recovery_metrics_and_payload_free_spans(), test_collector_retries_spools_and_replays_without_loss(), available(), unavailable(), test_pending_spool_precedes_new_data_and_overflow_is_visible()

### Community 106 - "Phase 5 automotive analytics"
Cohesion: 0.25
Nodes (7): Comparability and sufficiency, Metrics and normalization, Phase 5 automotive analytics, Pipeline and source of truth, Retrospective calculation identity, Retrospective metric and presentation completeness, Robust statistics and provenance

### Community 107 - "Container scan findings — 2026-10-01"
Cohesion: 0.29
Nodes (7): Canonical rerun 36952758342, Container scan findings — 2026-10-01, Current disposition, Image-content and coverage status, Narrow residual-risk records, Third-party infrastructure scan, Unique finding inventory

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

### Community 126 - "evaluate_agent_grounding.py"
Cohesion: 0.22
Nodes (9): mcp_client_stdio, domain_fingerprint(), Any, Aggregate content changes, including updates, in disposable fixture tables., evaluate(), connection(), main(), Independent Phase 7A evaluator: actual MCP stdio, real DB/API, fixed golden… (+1 more)

### Community 127 - "ADR 0018: Read-only MCP application adapter"
Cohesion: 0.10
Nodes (17): ADR 0018: Read-only MCP application adapter, Alternatives, Consequences and risks, Context, Decision, Status, ADR 0019: Grounded agent state and evidence, Alternatives (+9 more)

### Community 128 - "sqlalchemy_ext_asyncio"
Cohesion: 0.40
Nodes (5): run(), run_sync(), Connection, sqlalchemy_engine, sqlalchemy_ext_asyncio

### Community 129 - "observability/README.md"
Cohesion: 0.29
Nodes (6): Grounded agent, MCP, Observability, Phase 2 analysis, Phase 3 events, Retrospective instrumentation checks

### Community 130 - "75. API surface"
Cohesion: 0.33
Nodes (6): 75. API surface, Acquisition, Ingestion, Live client, Logging objectives, Recipes

### Community 131 - "85. Unit and contract tests"
Cohesion: 0.33
Nodes (6): 85. Unit and contract tests, Collector, Live analysis, Recipes, Sampling, Stream

### Community 132 - "Live acquisition operations and physical validation"
Cohesion: 0.33
Nodes (5): Collector CLI guarantees, Live acquisition operations and physical validation, Preserve an older Kafka storage path, Safe physical Vgate validation procedure, Topology and recovery

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

### Community 147 - "ADR 0015: Versioned recipes and acquisition lifecycle"
Cohesion: 0.40
Nodes (4): blocked(), ADR 0015: Versioned recipes and acquisition lifecycle, Consequences, Decision

### Community 148 - "Component model"
Cohesion: 0.50
Nodes (3): Component model, CURRENT, FUTURE

### Community 149 - "15. Required acquisition adapters"
Cohesion: 0.50
Nodes (4): 15. Required acquisition adapters, Real read-only OBD adapter path, Replay adapter, Synthetic live adapter

### Community 153 - "101. ADRs"
Cohesion: 0.67
Nodes (3): 101. ADRs, Acquisition lifecycle / recipes, Streaming architecture

### Community 154 - "phase-7a-acceptance.md"
Cohesion: 0.22
Nodes (5): Current phase, Roadmap, Development evidence (uncommitted tree; not final delivery proof), Phase 7A acceptance, Phase 7A traceability ledger

### Community 155 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

## Knowledge Gaps
- **801 isolated node(s):** `vehicle-platform-api`, `StandardPid`, `config`, `name`, `version` (+796 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1285 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `register_tools()` connect `register_tools` to `adapter.py`, `Adapter`, `MCPSettings`, `test_agents.py`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `Phase 7A — Agent Core & Grounded Orchestration` connect `Phase 7A — Agent Core & Grounded Orchestration` to `73. Definition of Done`, `register_tools`, `phase-7a-acceptance.md`, `55. Required test layers`?**
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
  _801 weakly-connected nodes found - possible documentation gaps or missing edges._