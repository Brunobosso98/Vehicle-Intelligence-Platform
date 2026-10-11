# Graph Report - Vehicle-Intelligence-Platform  (2026-10-11)

## Corpus Check
- 340 files · ~282,896 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: (none) 12, .Dockerfile 2, .example 1)

## Summary
- 3470 nodes · 8885 edges · 198 communities (144 shown, 54 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 1573 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a0b8987a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AnalyticsConfig
- test_acquisition.py
- DetectorProfile
- router
- api/routes.py
- SyntheticLiveAdapter
- acquisition/service.py
- RawTelemetryRecord
- Telemetry
- DeviceCapabilities
- acquisition/cli.py
- Adapter
- AlignedFrame
- sqlalchemy
- json
- evaluate
- Envelope
- events/synthetic.py
- StreamConsumer
- Phase 7C — Specialist Agents & Supervisor Orchestration
- web/package.json
- Phase 4 — Streaming & Live Vehicle Acquisition
- live-acquisition.tsx
- Phase 5 — Automotive Analytics
- register_tools
- generated/api.ts
- test_gateway_publisher_classifies_responses
- normalize_value
- evaluate_supervisor.py
- Phase 7A — Agent Core & Grounded Orchestration
- telemetry.py
- Settings
- status.test.tsx
- test_elm_tcp_transport_connects_reads_reuses_and_closes
- compilerOptions
- detectors.py
- AgentError
- analytics-workspace.tsx
- typing
- next
- main.py
- adapters.py
- devDependencies
- telemetry.test.tsx
- What You Must Do When Invoked
- Supervisor
- package.json
- DeterministicProvider
- pytest
- observability-validation.sh
- UUID
- vehicle-workspace.tsx
- Phase 7B — Investigation & Adaptive Logging
- seed_agent
- test_agent_runtime.py
- 97. Phase 7C Definition of Done
- orchestration.py
- MappedCSVTelemetrySource
- observability-smoke.py
- InvestigationProposal
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
- policy.py
- Phases 0–5 retrospective hardening
- graphify reference: extra exports and benchmark
- investigation/service.py
- InvestigationService
- pull_request_template.md
- os
- preflight
- Phase 5 automotive analytics
- 14. Specialist tool allowlists
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
- Grounded agent operation
- telemetry/domain.py
- test_investigation.py
- Phase 3 events
- 75. API surface
- 85. Unit and contract tests
- capabilities.py
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
- Phase 7C acceptance
- graphify reference: GitHub clone and cross-repo merge
- 101. ADRs
- Phase 7A acceptance
- benchmark_events.py
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
- Terminable
- investigation/routes.py
- ref_next_types_root_params_d_ts
- ref_next_types_routes_d_ts
- resolve_context
- main
- Phase 7C traceability ledger
- phase-0-completion-report.md
- agents/schemas.py
- ADR 0019: Grounded agent state and evidence
- 98. Phase 7B Definition of Done
- InvestigationStatus
- specialists/__init__.py
- @playwright/test
- Phase 7B acceptance
- .export
- quality.py
- Phase 7A grounded agent
- .__call__
- phase-7a-traceability-ledger.md
- 45. Investigation examples
- pathlib
- investigation/__init__.py
- main
- main

## God Nodes (most connected - your core abstractions)
1. `AgentError` - 168 edges
2. `Phase 4 — Streaming & Live Vehicle Acquisition` - 128 edges
3. `router()` - 126 edges
4. `Phase 5 — Automotive Analytics` - 115 edges
5. `Phase 7B — Investigation & Adaptive Logging` - 100 edges
6. `Phase 7C — Specialist Agents & Supervisor Orchestration` - 99 edges
7. `Telemetry` - 80 edges
8. `Settings` - 79 edges
9. `Phase 7A — Agent Core & Grounded Orchestration` - 75 edges
10. `InvestigationService` - 62 edges

## Surprising Connections (you probably didn't know these)
- `Boundaries and flow` --references--> `VehicleDataAdapter`  [INFERRED]
  docs/architecture/phase-4-live-acquisition.md → apps/api/src/vehicle_platform/acquisition/adapters.py
- `Execution and lifecycle` --references--> `AgentSettings`  [INFERRED]
  docs/architecture/phase-7a-grounded-agent.md → apps/api/src/vehicle_platform/agents/config.py
- `Domain and persistence` --references--> `InvestigationPlan`  [INFERRED]
  docs/architecture/phase-7b-investigation-adaptive-logging.md → apps/api/src/vehicle_platform/agents/investigation/domain.py
- `Explicit CSV mapping and live recovery` --references--> `mapping()`  [INFERRED]
  docs/architecture/phase-4-live-acquisition.md → apps/api/tests/unit/test_csv_mapping.py
- `Behavioral requirements` --references--> `devices()`  [INFERRED]
  docs/validation/phases-0-5-traceability-ledger.md → apps/api/src/vehicle_platform/acquisition/cli.py

## Import Cycles
- None detected.

## Communities (198 total, 54 thin omitted)

### Community 0 - "AnalyticsConfig"
Cohesion: 0.07
Nodes (67): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+59 more)

### Community 1 - "test_acquisition.py"
Cohesion: 0.07
Nodes (29): BoundedSpool, Path, Single-collector atomic acknowledgement, only after successful publish., parametrize, Path, test_bounded_spool_replays_and_reports_overflow(), test_collector_health_distinguishes_transport_and_sampling(), test_collector_rejects_unbounded_configuration() (+21 more)

### Community 2 - "DetectorProfile"
Cohesion: 0.13
Nodes (32): align_observations(), Align by deterministic last-value carry-forward, expiring at max_gap. Duplicate…, rolling_median(), HeuristicPullDetector, DetectorProfile, Observation, Heuristic defaults, not manufacturer calibration data., evaluate_pulls() (+24 more)

### Community 3 - "router"
Cohesion: 0.10
Nodes (57): SessionAnalysisService, AnalyticsService, APIRouter, router(), analytics_config(), analyze_repeated_pulls(), analyze_session(), analyze_session_events() (+49 more)

### Community 4 - "api/routes.py"
Cohesion: 0.09
Nodes (44): AnalysisLimitError, UUID, ValueError, AcquisitionBatchAccepted, AcquisitionHeartbeat, AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement (+36 more)

### Community 5 - "SyntheticLiveAdapter"
Cohesion: 0.13
Nodes (8): SyntheticLiveAdapter, test_collector_capability_failure_closes_adapter(), test_collector_heartbeat_interruption_does_not_erase_samples(), test_collector_reports_capabilities_bounds_and_graceful_disconnect(), heartbeat(), test_periodic_heartbeat_continues_while_adapter_waits(), read(), publish()

### Community 6 - "acquisition/service.py"
Cohesion: 0.17
Nodes (17): aiokafka, AIOKafkaProducer, AcquisitionAuthError, AcquisitionError, AcquisitionService, report(), datetime, UUID (+9 more)

### Community 7 - "RawTelemetryRecord"
Cohesion: 0.15
Nodes (14): AcquisitionCollector, report(), report_periodically(), CollectorStats, Hardware-near bounded collector with retry, backpressure, and disk replay., RawTelemetryMessage, RawTelemetryRecord, test_collector_interruption_preserves_unpublished_partial_batch() (+6 more)

### Community 8 - "Telemetry"
Cohesion: 0.07
Nodes (23): InvestigationInstrumentation, Bounded investigation telemetry without entity labels on metrics., Database, DependencyUnavailable, AsyncSession, Exception, Infrastructure failed its bounded readiness check., Instrumentation (+15 more)

### Community 9 - "DeviceCapabilities"
Cohesion: 0.16
Nodes (31): DeviceCapabilities, LoggingRecipe, Support, Feasibility, RecipeReference, SignalNeed, SignalRole, choose_recipe() (+23 more)

### Community 10 - "acquisition/cli.py"
Cohesion: 0.17
Nodes (22): adapter_for(), AdapterKind, devices(), execute(), _preflight(), preflight_command(), probe(), Path (+14 more)

### Community 11 - "Adapter"
Cohesion: 0.06
Nodes (49): AccessToken, connect(), MCPClient, AsyncClient, Client, Adapter, Verify an operator-provisioned opaque token; never issue or forward tokens., ReadTokenVerifier (+41 more)

### Community 12 - "AlignedFrame"
Cohesion: 0.19
Nodes (27): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, PullWindow, StrEnum (+19 more)

### Community 13 - "sqlalchemy"
Cohesion: 0.08
Nodes (8): alembic, run(), run_sync(), upgrade(), Connection, sqlalchemy, sqlalchemy_dialects, sqlalchemy_engine

### Community 14 - "json"
Cohesion: 0.12
Nodes (25): asyncio, asyncpg, datetime, httpx, httpx2, json, mcp_client_stdio, mcp_client_streamable_http (+17 more)

### Community 15 - "evaluate"
Cohesion: 0.17
Nodes (7): evaluate(), Any, Client, main(), ready_endpoint(), fingerprint(), main()

### Community 16 - "Envelope"
Cohesion: 0.08
Nodes (25): main(), Any, Any, Entity, UUID, Catalog, Any, Entity (+17 more)

### Community 17 - "events/synthetic.py"
Cohesion: 0.18
Nodes (20): evaluate_events(), EventClassMetrics, EventEvaluation, _overlaps(), One-to-one deterministic matching by type, pull and temporal overlap., anomaly_scenario(), AnomalyInjection, EventScenario (+12 more)

### Community 19 - "Phase 7C — Specialist Agents & Supervisor Orchestration"
Cohesion: 0.02
Nodes (97): 10. Specialist naming and contracts, 11. Specialist finding schema, 12. Shared evidence registry, 13. Evidence deduplication, 15. Tool policy enforcement, 16. Supervisor routing, 17. No forced all-specialist fan-out, 18. Data Quality routing priority (+89 more)

### Community 20 - "web/package.json"
Cohesion: 0.08
Nodes (26): dependencies, next, react, react-dom, name, private, scripts, build (+18 more)

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
Cohesion: 0.08
Nodes (25): MCPServer, register_tools(), compare_configurations(), get_cross_session_analytics(), get_event(), get_pull_summary(), get_repeated_pull_analysis(), get_session_analytics() (+17 more)

### Community 25 - "generated/api.ts"
Cohesion: 0.10
Nodes (22): AgentEvent, AgentRun, Audit, AgentRun, Investigation, InvestigationWorkspace(), terminal, Report (+14 more)

### Community 26 - "test_gateway_publisher_classifies_responses"
Cohesion: 0.12
Nodes (8): Exception, MonkeyPatch, test_consumer_database_failure_exits_without_sql_inputs(), fail(), test_gateway_publisher_classifies_responses(), test_gateway_transport_errors_enter_retry_spool_path(), test_spool_failed_atomic_ack_preserves_original(), CaptureFixture

### Community 27 - "normalize_value"
Cohesion: 0.09
Nodes (29): import_csv(), DataQuality, NormalizationError, normalize_value(), parse_timestamp(), datetime, StrEnum, ValueError (+21 more)

### Community 28 - "evaluate_supervisor.py"
Cohesion: 0.27
Nodes (9): domain_fingerprint(), Any, Aggregate content changes, including updates, in disposable fixture tables., evaluate(), Any, Independent golden scoring over actual HTTP MCP, API and disposable canonical…, score_claims(), Independent acceptance oracle: closed permissions, public counters and exact… (+1 more)

### Community 29 - "Phase 7A — Agent Core & Grounded Orchestration"
Cohesion: 0.03
Nodes (72): 10. Agent state, 11. AgentRun persistence, 12. ToolCall persistence / audit trail, 13. Evidence model, 14. Claim → Evidence grounding, 15. Unsupported-claim detection, 16. Structured answer contract, 17. Natural-language API (+64 more)

### Community 30 - "telemetry.py"
Cohesion: 0.09
Nodes (17): Prevent database driver messages and SQL text from leaving the process., SanitizingExporter, JSONFormatter, Any, hmac, logging, LogRecord, mcp_server_auth_provider (+9 more)

### Community 31 - "Settings"
Cohesion: 0.05
Nodes (45): AcquisitionPublisher, Application-owned producer; bounded concurrent publication and shutdown., BaseSettings, datetime, model_validator, Settings, create_app(), parametrize (+37 more)

### Community 32 - "status.test.tsx"
Cohesion: 0.16
Nodes (14): dynamic, GET(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready, SystemStatus (+6 more)

### Community 33 - "test_elm_tcp_transport_connects_reads_reuses_and_closes"
Cohesion: 0.15
Nodes (3): ElmTcpTransport, Concrete ELM327 TCP/RFCOMM bridge transport with a strict read-only command…, test_elm_tcp_transport_connects_reads_reuses_and_closes()

### Community 34 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 35 - "detectors.py"
Cohesion: 0.17
Nodes (13): compute_pull_metrics(), HeuristicSegmentDetector, _mean(), PullDetector, Protocol, SegmentDetector, _slope(), DetectedPull (+5 more)

### Community 36 - "AgentError"
Cohesion: 0.06
Nodes (45): AgentInstrumentation, AgentError, Exception, AgentRepository, AsyncSession, Protocol, UUID, Commit terminal state and stream event together; reconnect cannot race… (+37 more)

### Community 37 - "analytics-workspace.tsx"
Cohesion: 0.13
Nodes (11): AnalyticsWorkspace(), history(), Configuration, curveLabels, NormalizedBin, Profile, Pull, request() (+3 more)

### Community 38 - "typing"
Cohesion: 0.10
Nodes (33): Bounded context repository for records currently owned by HTTP SQL handlers., Read-only connection defaults also bound queries before a transaction begins., ErrorCode, StrEnum, ToolError, UUID, tool_error(), model_validator (+25 more)

### Community 39 - "next"
Cohesion: 0.18
Nodes (6): config, GET, POST, apps_web_src_app_globals, metadata, next

### Community 40 - "main.py"
Cohesion: 0.09
Nodes (24): Constant-memory local request budgets for the Phase 4 resource boundaries., Per-process budgets, with no unbounded per-client identifier dictionaries. The…, ResourceBudgetMiddleware, ErrorDetail, ErrorResponse, Health, BaseModel, Ready (+16 more)

### Community 41 - "adapters.py"
Cohesion: 0.13
Nodes (9): Elm327Adapter, ElmTransport, Protocol, Read-only adapter contract. Deliberately has no command/write operation., Generic standard-mode OBD-II reader; no proprietary or write commands., ReplayAdapter, StandardPid, VehicleDataAdapter (+1 more)

### Community 42 - "devDependencies"
Cohesion: 0.12
Nodes (16): devDependencies, @axe-core/playwright, eslint, @eslint/compat, eslint-config-next, jsdom, @playwright/test, @testing-library/jest-dom (+8 more)

### Community 43 - "telemetry.test.tsx"
Cohesion: 0.15
Nodes (10): detectedEvent, pull, segment, session, signals, vehicle, window, @testing-library/jest-dom (+2 more)

### Community 44 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 45 - "Supervisor"
Cohesion: 0.13
Nodes (35): accumulate(), StrEnum, Specialist, Sufficiency, Any, Supervisor, test_usage_unavailable_stays_unavailable(), parametrize (+27 more)

### Community 46 - "package.json"
Cohesion: 0.11
Nodes (18): devDependencies, openapi-typescript, prettier, engines, node, name, packageManager, private (+10 more)

### Community 47 - "DeterministicProvider"
Cohesion: 0.10
Nodes (31): OpenAIProvider, ModelInput, ModelTurn, Provider, Protocol, RoutingInput, ToolRequest, Binding (+23 more)

### Community 48 - "pytest"
Cohesion: 0.05
Nodes (44): AgentRequestBudgetMiddleware, ASGIApp, Receive, Scope, Send, Bound admission and body buffering before FastAPI parses an agent question., TokenBucket, FastAPI (+36 more)

### Community 49 - "observability-validation.sh"
Cohesion: 0.40
Nodes (4): scripts_lib_wait_http_sh, observability-validation.sh script, wait_prometheus_query(), stack-smoke.sh script

### Community 51 - "vehicle-workspace.tsx"
Cohesion: 0.18
Nodes (11): DetectedEvent, json(), Pull, Segment, Session, Signal, TelemetryDashboard(), Vehicle (+3 more)

### Community 52 - "Phase 7B — Investigation & Adaptive Logging"
Cohesion: 0.02
Nodes (98): 10. Investigation taxonomy, 11. Evidence gap model, 12. Reuse Phase 7A missing-evidence categories, 13. SignalNeed abstraction, 14. No invented channels, 15. Capability resolver, 16. Session capability vs hardware/source capability, 17. Existing-data-first policy (+90 more)

### Community 53 - "seed_agent"
Cohesion: 0.12
Nodes (26): main(), Dedicated browser gate: controlled real API, authenticated HTTP MCP and…, Independent controlled temporal/configuration fixtures in disposable…, seed_agent(), main(), main(), Opt-in billable smoke against controlled fixtures through the real Responses…, ask() (+18 more)

### Community 54 - "test_agent_runtime.py"
Cohesion: 0.07
Nodes (37): url(), url(), source(), provider(), parametrize, Provider wire parsing and service lifecycle failure branches (unit doubles…, request(), ResponseStream (+29 more)

### Community 55 - "97. Phase 7C Definition of Done"
Cohesion: 0.14
Nodes (14): 97. Phase 7C Definition of Done, API/UI/SSE, Conflicts, Data quality, Delivery, Evidence, Observability/performance, Parallelism (+6 more)

### Community 56 - "orchestration.py"
Cohesion: 0.09
Nodes (29): AgentSettings, Any, BaseSettings, model_validator, Redact only strings, preserving numeric facts and JSON structure., redact_data(), EvidenceClient, Protocol (+21 more)

### Community 57 - "MappedCSVTelemetrySource"
Cohesion: 0.18
Nodes (16): preview_csv_import(), CSVColumnMapping, CSVSignalColumn, inspect_csv(), MappedCSVTelemetrySource, BaseModel, model_validator, mapping() (+8 more)

### Community 59 - "InvestigationProposal"
Cohesion: 0.29
Nodes (7): InvestigationInput, InvestigationProposal, ProposedGap, ProposedHypothesis, model_validator, test_quality_only_investigation_has_a_valid_discriminating_gap(), test_real_planning_adapter_receives_structured_supervisor_report()

### Community 60 - "security-policy.py"
Cohesion: 0.31
Nodes (10): Namespace, accepted(), load_exceptions(), load_findings(), main(), parse_args(), Any, Path (+2 more)

### Community 61 - "mcp-validation.sh"
Cohesion: 0.25
Nodes (6): DATABASE_URL, ENVIRONMENT, MCP_TEST_PROJECT, mcp-validation.sh script, TEST_DATABASE_URL, TEST_KAFKA_PORT

### Community 62 - "test_agents.py"
Cohesion: 0.10
Nodes (51): canonical_hash(), facts(), Any, sufficiency_for(), comparison(), parametrize, test_association_degrades_without_comparable_complete_context(), test_association_uses_actual_selected_pull_configuration_and_timeline() (+43 more)

### Community 63 - "README.md"
Cohesion: 0.10
Nodes (13): investigable(), Contributing, Phase 7C specialist agents and supervisor, System context, Toolchain selection, Local development, Current phase, Phase 7C implementation (+5 more)

### Community 64 - "PHASE 0 COMPLETION REPORT"
Cohesion: 0.11
Nodes (19): ADRs created, Applications, Architecture, CI/CD, Closure rerun result, Codex context, Database, Deferred deliberately to Phase 1+ (+11 more)

### Community 65 - "telemetry/service.py"
Cohesion: 0.15
Nodes (17): ImportResult, TelemetryPoint, TelemetryWindow, TelemetrySource, _content_hash(), IngestionService, AsyncSession, datetime (+9 more)

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
Cohesion: 0.20
Nodes (10): 2026-10-09 Go advisory refresh, 2026-10-10 Go HTTP/2 advisory refresh, 2026-10-10 Kafka dependency refresh, Canonical rerun 36952758342, Container scan findings — 2026-10-01, Current disposition, Image-content and coverage status, Narrow residual-risk records (+2 more)

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

### Community 98 - "policy.py"
Cohesion: 0.24
Nodes (9): enforce_tool(), Any, Specialist, Application-owned permissions; provider and metadata cannot extend these…, specialist_policy(), SpecialistPolicy, tools_for(), test_allowlists_are_explicit_and_cannot_be_mutated() (+1 more)

### Community 99 - "Phases 0–5 retrospective hardening"
Cohesion: 0.04
Nodes (39): ADR 0014: Kafka durable acquisition stream, Consequences, Context, Decision, ADR 0016: Deterministic, immutable automotive analytics, Consequences, Decision, Status (+31 more)

### Community 100 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 101 - "investigation/service.py"
Cohesion: 0.14
Nodes (35): Availability, EvidenceGap, GapStatus, GapType, Hypothesis, HypothesisCategory, HypothesisStatus, InvestigationOutcome (+27 more)

### Community 102 - "InvestigationService"
Cohesion: 0.13
Nodes (10): Approval, InvestigationPlan, model_validator, InvestigationRepository, UUID, Link one finalized Phase 4 acquisition under a row lock, idempotently., Atomically persist a unique follow-up AgentRun and its investigation link., InvestigationService (+2 more)

### Community 103 - "pull_request_template.md"
Cohesion: 0.22
Nodes (8): Database/contract impact, Documentation, How it was validated, Observability impact, Risks, Security impact, What changed, Why

### Community 104 - "os"
Cohesion: 0.22
Nodes (6): alembic_config, alembic_script, Requires an explicitly supplied disposable test database. Never skips silently., os, Validate local skills, scoped context, declarative YAML and Markdown links., Write canonical CI validation summaries without converting failures into passes.

### Community 105 - "preflight"
Cohesion: 0.08
Nodes (29): Importance, plan_sampling(), preflight(), PreflightResult, Priority, StrEnum, Readiness, SignalRequirement (+21 more)

### Community 106 - "Phase 5 automotive analytics"
Cohesion: 0.29
Nodes (6): Metrics and normalization, Phase 5 automotive analytics, Pipeline and source of truth, Retrospective calculation identity, Retrospective metric and presentation completeness, Robust statistics and provenance

### Community 107 - "14. Specialist tool allowlists"
Cohesion: 0.40
Nodes (5): 14. Specialist tool allowlists, Data Quality candidate tools, Fuel/Air/Boost candidate tools, Performance candidate tools, Thermal candidate tools

### Community 108 - "N55 Intelligence Lab"
Cohesion: 0.18
Nodes (11): Arquitetura e continuidade, Desenvolvimento e testes, Estado atual, N55 Intelligence Lab, Observabilidade, Phase 6 MCP, Phase 7A grounded agent, Phase 7B investigation and adaptive logging (+3 more)

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
Cohesion: 0.33
Nodes (6): Original Phase 4 local resource budgets, Phase 4 acquisition threats, Phase 6 MCP boundary, Phase 7A agent boundary, Phase 7B investigation and adaptive logging, Phase 7C supervisor and specialists

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

### Community 126 - "Grounded agent operation"
Cohesion: 0.50
Nodes (4): Failure handling, Grounded agent operation, Local configuration, Validation commands

### Community 127 - "telemetry/domain.py"
Cohesion: 0.12
Nodes (16): UUID, UUID, LiveOBDSource, Protocol, Adapter boundary only: Phase 1 intentionally provides no hardware…, validate_sequence(), dataclasses, enum (+8 more)

### Community 128 - "test_investigation.py"
Cohesion: 0.12
Nodes (25): insufficient_run(), MemoryInvestigations, parametrize, test_cancel_and_reject_are_idempotent_only_at_exact_version(), test_completed_followup_reloads_after_stale_race(), test_create_closes_provider_after_invalid_semantic_output(), test_create_rejects_invalid_identity_capacity_and_sufficient_answer(), test_create_reuses_existing_plan_only_for_same_source() (+17 more)

### Community 129 - "Phase 3 events"
Cohesion: 0.20
Nodes (8): Grounded agent, Investigation and adaptive logging, MCP, Observability, Phase 2 analysis, Phase 3 events, Phase 7C supervisor, Retrospective instrumentation checks

### Community 130 - "75. API surface"
Cohesion: 0.33
Nodes (6): 75. API surface, Acquisition, Ingestion, Live client, Logging objectives, Recipes

### Community 131 - "85. Unit and contract tests"
Cohesion: 0.33
Nodes (6): 85. Unit and contract tests, Collector, Live analysis, Recipes, Sampling, Stream

### Community 132 - "capabilities.py"
Cohesion: 0.23
Nodes (10): AcquisitionCapabilitySource, fresh(), datetime, UUID, Source capability snapshots from the local collector, never inferred from…, Phase 4 owner of source support; a dataset report is not source support., SourceCapabilitySnapshot, validated_report() (+2 more)

### Community 133 - "architecture/phase-6-mcp-tool-platform.md"
Cohesion: 0.14
Nodes (10): Component model, CURRENT, FUTURE, Service boundaries, Docker, Limits and troubleshooting, Local stdio, MCP server (+2 more)

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
Cohesion: 0.25
Nodes (7): Phase 3 acceptance, Phase 6 acceptance, Phase 7A acceptance, Phase 7B acceptance, Phase 7C acceptance, Retrospective phase gates, Testing strategy

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
Cohesion: 0.15
Nodes (9): main(), One registration shared by stdio and authenticated Streamable HTTP., HTTPInstrumentation, ASGI boundary preserving W3C trace context and counting SDK auth rejections., argparse, mcp_server_transport_security, starlette_middleware_base, starlette_requests (+1 more)

### Community 148 - "EventEngine"
Cohesion: 0.27
Nodes (16): EventProfile, Development heuristics; these are not factory safety or N55 calibration limits., EventEngine, base(), frames(), pull(), test_comparable_pulls(), test_fuel_drop_requires_sustained_observation_not_single_low_spike() (+8 more)

### Community 149 - "15. Required acquisition adapters"
Cohesion: 0.50
Nodes (4): 15. Required acquisition adapters, Real read-only OBD adapter path, Replay adapter, Synthetic live adapter

### Community 151 - "Phase 7C acceptance"
Cohesion: 0.50
Nodes (4): Local and canonical validation, Phase 7C acceptance, Phase 7C receipts, Result

### Community 153 - "101. ADRs"
Cohesion: 0.67
Nodes (3): 101. ADRs, Acquisition lifecycle / recipes, Streaming architecture

### Community 154 - "Phase 7A acceptance"
Cohesion: 0.29
Nodes (7): Baseline and delivery boundary, Executed checkpoint: `881fcca0bb75acf9369bbbf25854c32d626aa017`, Final receipt requirements, Missing-evidence correction: `4df84696ab3ffb5d900399877849975b008fe4cf`, Phase 7A acceptance, Pushed-head full verification checkpoint: `66efbc744ab23c5ba0044cb6029ebd69c56f2206`, Real provider and practical limits

### Community 155 - "benchmark_events.py"
Cohesion: 0.67
Nodes (3): main(), Repeatable Phase 3 CPU/allocation benchmark; informational, never a latency…, timed()

### Community 174 - "investigation/routes.py"
Cohesion: 0.08
Nodes (16): CapabilitySnapshot, InvestigationEvent, ApprovalRequest, CreateInvestigation, investigation_router(), stream(), LinkSessionRequest, APIRouter (+8 more)

### Community 177 - "resolve_context"
Cohesion: 0.57
Nodes (7): at(), effective(), Any, datetime, UUID, resolve_context(), test_temporal_context_removal_and_boundary()

### Community 178 - "main"
Cohesion: 0.40
Nodes (4): compose(), main(), Wait until the real Next.js status and domain proxies recover too., wait_for_browser_proxies()

### Community 179 - "Phase 7C traceability ledger"
Cohesion: 0.67
Nodes (3): Evidence references, Phase 7C traceability ledger, Requirement matrix

### Community 180 - "phase-0-completion-report.md"
Cohesion: 0.17
Nodes (7): Closure, Phase 0 task map, Phase 1 outline — Vehicle & Telemetry Core, Canonical GitHub workflow run (2026-10-02), Closure rerun (23:33–23:38 UTC), Split-executor implementation, Validation evidence — 2026-10-01

### Community 181 - "agents/schemas.py"
Cohesion: 0.12
Nodes (37): EvidenceRegistry, UUID, Merge independent reads by tool/selection, preserving each MCP result's row…, render_binding(), validate(), Answer, Classification, Conflict (+29 more)

### Community 182 - "ADR 0019: Grounded agent state and evidence"
Cohesion: 0.08
Nodes (22): blocked(), ADR 0015: Versioned recipes and acquisition lifecycle, Consequences, Decision, ADR 0019: Grounded agent state and evidence, Alternatives, Consequences and risks, Context (+14 more)

### Community 183 - "98. Phase 7B Definition of Done"
Cohesion: 0.15
Nodes (13): 98. Phase 7B Definition of Done, Acquisition / follow-up, API / UI, Approval, Delivery, Existing evidence, Investigation domain, Logging plan (+5 more)

### Community 184 - "InvestigationStatus"
Cohesion: 0.15
Nodes (20): InvestigationError, InvestigationStatus, ValueError, A public investigation rule was violated., Investigation-owned persistence with optimistic updates and bounded replay., approved_plan(), item(), Phase 7B optimistic SQL boundary; disposable PostgreSQL tests cover execution. (+12 more)

### Community 186 - "@playwright/test"
Cohesion: 0.31
Nodes (3): @axe-core/playwright, ref_node_fs, @playwright/test

### Community 188 - "Phase 7B acceptance"
Cohesion: 0.29
Nodes (5): Benchmark checkpoint, Final receipt requirements, Phase 7B acceptance, Scope and gates, Phase 7B requirement traceability

### Community 190 - ".export"
Cohesion: 0.33
Nodes (4): graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), ReadableSpan, SpanExportResult

### Community 191 - "quality.py"
Cohesion: 0.14
Nodes (17): assess_dataset(), collector_health(), DatasetCapability, measure_signal_quality(), datetime, Infer transport/sampling freshness only from an authenticated report. Event…, SignalQuality, test_stream_contract_and_dataset_capability() (+9 more)

### Community 193 - "Phase 7A grounded agent"
Cohesion: 0.40
Nodes (5): Boundaries, Context and evidence, Execution and lifecycle, Phase 7A grounded agent, Provider and streaming contracts

### Community 194 - ".__call__"
Cohesion: 0.40
Nodes (3): Receive, Scope, Send

### Community 196 - "45. Investigation examples"
Cohesion: 0.50
Nodes (4): 45. Investigation examples, Example A — repeated pull performance loss, Example B — change after intercooler, Example C — missing technical specification

### Community 197 - "pathlib"
Cohesion: 0.11
Nodes (20): pathlib, main(), Deterministic HTTP/MCP supervisor measurements; no real-model latency or cost…, Enforce separate line and branch thresholds for the generated local coverage…, main(), address(), command(), wait_for_telemetry_backends() (+12 more)

### Community 202 - "main"
Cohesion: 0.83
Nodes (4): main(), address(), command(), wait_for_telemetry_backends()

### Community 203 - "main"
Cohesion: 1.00
Nodes (3): main(), address(), command()

## Knowledge Gaps
- **1074 isolated node(s):** `vehicle-platform-api`, `StandardPid`, `config`, `name`, `version` (+1069 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1646 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **54 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `investigable()` connect `README.md` to `test_investigation.py`, `AgentError`, `investigation/service.py`, `InvestigationService`, `agents/schemas.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `Phase 7C — Specialist Agents & Supervisor Orchestration` connect `Phase 7C — Specialist Agents & Supervisor Orchestration` to `14. Specialist tool allowlists`, `97. Phase 7C Definition of Done`, `README.md`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 84 inferred relationships involving `AgentError` (e.g. with `EvidenceRegistry` and `InvestigationRepository`) actually correct?**
  _`AgentError` has 84 INFERRED edges - model-reasoned connections that need verification._
- **Are the 45 inferred relationships involving `router()` (e.g. with `LoggingRecipe` and `AcquisitionAuthError`) actually correct?**
  _`router()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vehicle-platform-api`, `StandardPid`, `config` to the rest of the system?**
  _1074 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `AnalyticsConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.07301231802911534 - nodes in this community are weakly interconnected._
- **Should `test_acquisition.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06845513413506013 - nodes in this community are weakly interconnected._