# Graph Report - Vehicle-Intelligence-Platform  (2026-10-12)

## Corpus Check
- 352 files · ~300,566 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: (none) 11, .Dockerfile 2, .example 1)

## Summary
- 3729 nodes · 10102 edges · 198 communities (139 shown, 59 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 1891 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `967c7d0d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AnalyticsConfig
- BoundedSpool
- dataclasses
- router
- api/routes.py
- test_acquisition.py
- acquisition/service.py
- RawTelemetryRecord
- Telemetry
- test_investigation.py
- acquisition/cli.py
- MCPSettings
- AlignedFrame
- main.py
- evaluate_mcp.py
- CATEGORY H — ADVERSARIAL / SECURITY / UNCERTAINTY
- server.py
- events/synthetic.py
- worker.py
- Phase 7C — Specialist Agents & Supervisor Orchestration
- web/package.json
- Phase 4 — Streaming & Live Vehicle Acquisition
- live-acquisition.tsx
- Phase 5 — Automotive Analytics
- register_tools
- generated/api.ts
- ReplayAdapter
- ToolMeter
- datetime
- Phase 7A — Agent Core & Grounded Orchestration
- Settings
- status.test.tsx
- test_elm_tcp_transport_connects_reads_reuses_and_closes
- compilerOptions
- detectors.py
- Orchestrator
- analytics-workspace.tsx
- InvestigationPlan
- next
- StreamConsumer
- Elm327Adapter
- devDependencies
- telemetry.test.tsx
- Ledger
- Supervisor
- package.json
- DeterministicProvider
- ADR 0018: Read-only MCP application adapter
- observability-validation.sh
- test_gateway_publisher_classifies_responses
- vehicle-workspace.tsx
- Phase 7B — Investigation & Adaptive Logging
- test_gateway_heartbeat_is_scoped_and_failures_are_explicit
- AgentError
- 97. Phase 7C Definition of Done
- pytest
- MappedCSVTelemetrySource
- StrictModel
- security-policy.py
- mcp-validation.sh
- agents/schemas.py
- README.md
- PHASE 0 COMPLETION REPORT
- telemetry/service.py
- integration.sh
- retrospective-validation.sh
- 113. Final delivery report
- cloud-build.sh
- cloud-validation.sh
- wait-http.sh
- mcp-up.sh
- security.sh
- security-cloud.sh
- database-entrypoint.sh
- bootstrap.sh
- install-security-tools.sh
- Container scan findings — 2026-10-01
- vehicle-platform-api
- 126. Final delivery report
- 45. Required synthetic scenarios
- Envelope
- 73. Definition of Done
- Phase 6 acceptance evidence
- Phase 7D — Real Model Validation & Agent Reliability Baseline
- Phases 0–5 retrospective hardening
- test_periodic_heartbeat_continues_while_adapter_waits
- investigation/service.py
- Adapter
- pull_request_template.md
- InvestigationError
- investigation/domain.py
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
- Grounded agent operation
- Phase 3 event and anomaly engine
- 55. Required test layers
- Phase 1 vehicle and telemetry core
- ADR 0012: Versioned deterministic session analysis
- ADR 0013: Deterministic evidence-first event architecture
- api/errors.py
- Phase 7A grounded agent
- prompts/phase-7d-real-model-validation.md
- Phase 3 events
- 75. API surface
- 85. Unit and contract tests
- capabilities.py
- architecture/phase-6-mcp-tool-platform.md
- main
- Vehicle Intelligence Platform context
- Phase 7C traceability ledger
- test_agent_budgets.py
- 94. Failure behavior
- strategy.md
- adr.md
- migrations.md
- definition-of-done.md
- gates.md
- CATEGORY A — FACTUAL / FAST-PATH
- CATEGORY B — PERFORMANCE
- CATEGORY C — THERMAL
- mcp/instrumentation.py
- EventEngine
- 15. Required acquisition adapters
- Vehicle Intelligence Platform / N55 Intelligence Lab
- phase-7a-traceability-ledger.md
- CATEGORY D — FUEL / AIR / BOOST
- 101. ADRs
- Phase 7A acceptance
- CATEGORY E — DATA QUALITY
- api/AGENTS.md
- web/AGENTS.md
- CATEGORY F — MULTI-SPECIALIST
- data-principles.md
- quality-attributes.md
- versioning.md
- github.md
- database-not-ready.md
- local-stack-not-starting.md
- migration-failure.md
- phase-2-baseline.md
- provider.py
- infra/AGENTS.md
- contracts/AGENTS.md
- contracts/README.md
- SECURITY.md
- CATEGORY G — PHASE 7B / INSUFFICIENT EVIDENCE / ADAPTIVE LOGGING
- investigation_router
- test_agent_repository.py
- ADR 0022: Bounded real-model evaluation and durable spend accounting
- tool_error
- telemetry.py
- Phase 4 acquisition threats
- scripts
- ADR 0019: Grounded agent state and evidence
- 98. Phase 7B Definition of Done
- @playwright/test
- json
- Phase 7B acceptance
- Phase 4 — Streaming & Live Vehicle Acquisition
- Phase 2 session and pull analysis
- 45. Investigation examples
- SessionAnalysisService
- phase-7d-traceability-ledger.md
- phase-7d-delivery.md
- InvestigationService
- Phase 7C acceptance

## God Nodes (most connected - your core abstractions)
1. `AgentError` - 206 edges
2. `Phase 4 — Streaming & Live Vehicle Acquisition` - 128 edges
3. `router()` - 126 edges
4. `Phase 5 — Automotive Analytics` - 115 edges
5. `Phase 7B — Investigation & Adaptive Logging` - 100 edges
6. `Phase 7C — Specialist Agents & Supervisor Orchestration` - 99 edges
7. `Settings` - 81 edges
8. `Telemetry` - 80 edges
9. `Phase 7A — Agent Core & Grounded Orchestration` - 75 edges
10. `InvestigationService` - 62 edges

## Surprising Connections (you probably didn't know these)
- `Boundaries and flow` --references--> `VehicleDataAdapter`  [INFERRED]
  docs/architecture/phase-4-live-acquisition.md → apps/api/src/vehicle_platform/acquisition/adapters.py
- `Behavioral requirements` --references--> `devices()`  [INFERRED]
  docs/validation/phases-0-5-traceability-ledger.md → apps/api/src/vehicle_platform/acquisition/cli.py
- `Execution and lifecycle` --references--> `AgentSettings`  [INFERRED]
  docs/architecture/phase-7a-grounded-agent.md → apps/api/src/vehicle_platform/agents/config.py
- `Domain and persistence` --references--> `InvestigationPlan`  [INFERRED]
  docs/architecture/phase-7b-investigation-adaptive-logging.md → apps/api/src/vehicle_platform/agents/investigation/domain.py
- `Phase 7C specialist agents and supervisor` --references--> `investigable()`  [INFERRED]
  docs/architecture/phase-7c-specialist-agents-supervisor.md → apps/api/src/vehicle_platform/agents/investigation/service.py

## Import Cycles
- None detected.

## Communities (198 total, 59 thin omitted)

### Community 0 - "AnalyticsConfig"
Cohesion: 0.08
Nodes (54): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+46 more)

### Community 1 - "BoundedSpool"
Cohesion: 0.16
Nodes (11): BoundedSpool, test_bounded_spool_replays_and_reports_overflow(), test_collector_interruption_preserves_unpublished_partial_batch(), read(), test_collector_rejects_unbounded_configuration(), test_spool_acknowledges_only_after_publish_and_recovers_in_same_run(), test_spool_atomic_acknowledgement_preserves_remaining_records(), test_spool_capacity_states_are_measured() (+3 more)

### Community 2 - "dataclasses"
Cohesion: 0.12
Nodes (27): align_observations(), rolling_median(), HeuristicPullDetector, DetectedPull, DetectorProfile, Observation, SegmentType, evaluate_pulls() (+19 more)

### Community 3 - "router"
Cohesion: 0.08
Nodes (62): Health, Ready, Version, router(), analytics_config(), analyze_repeated_pulls(), analyze_session(), analyze_session_events() (+54 more)

### Community 4 - "api/routes.py"
Cohesion: 0.08
Nodes (41): AcquisitionBatchAccepted, AcquisitionCreate, AcquisitionCreated, AcquisitionHeartbeat, AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement, AnalysisRequest (+33 more)

### Community 5 - "test_acquisition.py"
Cohesion: 0.14
Nodes (20): SyntheticLiveAdapter, preflight(), report(), capabilities(), test_collector_health_distinguishes_transport_and_sampling(), test_collector_heartbeat_interruption_does_not_erase_samples(), test_collector_reports_capabilities_bounds_and_graceful_disconnect(), heartbeat() (+12 more)

### Community 6 - "acquisition/service.py"
Cohesion: 0.12
Nodes (15): assess_dataset(), collector_health(), DatasetCapability, measure_signal_quality(), SignalQuality, AcquisitionAuthError, AcquisitionError, AcquisitionPublisher (+7 more)

### Community 7 - "RawTelemetryRecord"
Cohesion: 0.15
Nodes (12): VehicleDataAdapter, AcquisitionCollector, CollectorStats, SamplingPlanItem, RawTelemetryRecord, test_collector_reports_actual_recovery_metrics_and_payload_free_spans(), test_collector_retries_spools_and_replays_without_loss(), available() (+4 more)

### Community 8 - "Telemetry"
Cohesion: 0.08
Nodes (13): main(), Database, DependencyUnavailable, Telemetry, test_non_http_passthrough(), test_phase3_metrics_use_only_bounded_labels(), test_phase4_metrics_use_only_bounded_labels(), test_extension_required() (+5 more)

### Community 9 - "test_investigation.py"
Cohesion: 0.16
Nodes (29): Approval, InvestigationStatus, investigable(), insufficient_run(), MemoryInvestigations, plan(), test_approval_rejects_changed_source_and_resumes_partial_approval(), test_approval_rejects_stale_capability_and_unready_plan() (+21 more)

### Community 10 - "acquisition/cli.py"
Cohesion: 0.19
Nodes (14): adapter_for(), AdapterKind, devices(), execute(), _preflight(), preflight_command(), probe(), recipes() (+6 more)

### Community 11 - "MCPSettings"
Cohesion: 0.11
Nodes (19): MCPSettings, ReadOnlyDatabase, Instrumentation, create_server(), pull(), session(), vehicle(), runtime() (+11 more)

### Community 12 - "AlignedFrame"
Cohesion: 0.19
Nodes (23): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, PullWindow, Severity (+15 more)

### Community 13 - "main.py"
Cohesion: 0.05
Nodes (17): run(), run_sync(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade() (+9 more)

### Community 14 - "evaluate_mcp.py"
Cohesion: 0.09
Nodes (11): evaluate(), main(), evaluate(), error(), main(), ready_endpoint(), fingerprint(), seed() (+3 more)

### Community 15 - "CATEGORY H — ADVERSARIAL / SECURITY / UNCERTAINTY"
Cohesion: 0.03
Nodes (61): 100. Optional Sol comparison, 101. Real-model grading, 102. Hard blockers / zero-tolerance metrics, 103. Routing quality, 104. Tool efficiency, 105. Grounding, 106. Causal restraint, 107. Diagnosis restraint (+53 more)

### Community 16 - "server.py"
Cohesion: 0.09
Nodes (11): ReadTokenVerifier, test_analytics_selection_reports_truncation(), test_auth(), test_http_requires_token(), test_instrumented_errors(), test_limited_quality_does_not_claim_missing_history(), test_network_config_rejected(), test_read_only_database_setup() (+3 more)

### Community 17 - "events/synthetic.py"
Cohesion: 0.18
Nodes (15): evaluate_events(), EventClassMetrics, EventEvaluation, _overlaps(), anomaly_scenario(), AnomalyInjection, EventScenario, ExpectedEvent (+7 more)

### Community 18 - "worker.py"
Cohesion: 0.07
Nodes (28): StandardPid, RawTelemetryMessage, StreamObservation, DataQuality, NormalizationError, normalize_value(), parse_timestamp(), sample_id() (+20 more)

### Community 19 - "Phase 7C — Specialist Agents & Supervisor Orchestration"
Cohesion: 0.02
Nodes (97): 10. Specialist naming and contracts, 11. Specialist finding schema, 12. Shared evidence registry, 13. Evidence deduplication, 15. Tool policy enforcement, 16. Supervisor routing, 17. No forced all-specialist fan-out, 18. Data Quality routing priority (+89 more)

### Community 20 - "web/package.json"
Cohesion: 0.11
Nodes (18): dependencies, next, react, react-dom, name, private, type, version (+10 more)

### Community 21 - "Phase 4 — Streaming & Live Vehicle Acquisition"
Cohesion: 0.02
Nodes (122): 100. BimmerLink status, 102. Repository context and reusable workflows, 103. Make targets and regression gates, 104. Migration guard in CI, 105. Canonical Docker validation, 106. Golden live scenarios, 107. Acceptance — loss and duplication, 108. Acceptance — recipes (+114 more)

### Community 22 - "live-acquisition.tsx"
Cohesion: 0.08
Nodes (16): Acquisition, CollectorReport, Finalized, LiveAcquisition(), LiveFinding, LivePoint, LiveSignalChart(), LiveSnapshot (+8 more)

### Community 23 - "Phase 5 — Automotive Analytics"
Cohesion: 0.02
Nodes (113): 100. ADR, 101. AGENTS.md / repository workflow, 102. Make targets, 103. CI regression protection, 104. Push early, 105. Pull request, 106. GitHub workflow behavior, 107. Do not repeat the premature Phase 4 completion behavior (+105 more)

### Community 24 - "register_tools"
Cohesion: 0.11
Nodes (18): register_tools(), compare_configurations(), get_cross_session_analytics(), get_event(), get_pull_summary(), get_repeated_pull_analysis(), get_session_analytics(), get_session_capabilities() (+10 more)

### Community 25 - "generated/api.ts"
Cohesion: 0.10
Nodes (23): AgentEvent, AgentRun, Audit, AgentRun, Investigation, InvestigationWorkspace(), terminal, Report (+15 more)

### Community 26 - "ReplayAdapter"
Cohesion: 0.42
Nodes (4): ReplayAdapter, run(), test_replay_is_deterministic(), test_replay_skips_unplanned_signal_without_sleep()

### Community 27 - "ToolMeter"
Cohesion: 0.27
Nodes (8): MeteredClient, ToolMeter, source(), test_evaluation_factory_wraps_the_actual_connect_seam(), test_meter_covers_phase7b_reads_and_preserves_safe_hashes(), test_single_telemetry_window_and_failed_reads_are_measured(), test_total_cap_includes_phase7b_and_resets_only_for_next_case(), test_unsafe_or_foreign_requests_never_reach_mcp()

### Community 28 - "datetime"
Cohesion: 0.06
Nodes (29): atomic_json(), load_suite(), test_identity_requires_clean_exact_commit(), test_exact_versioned_dataset_and_fixed_schedule(), test_versioned_questions_match_the_authoritative_specification(), domain_fingerprint(), database_command(), free_port() (+21 more)

### Community 29 - "Phase 7A — Agent Core & Grounded Orchestration"
Cohesion: 0.03
Nodes (72): 10. Agent state, 11. AgentRun persistence, 12. ToolCall persistence / audit trail, 13. Evidence model, 14. Claim → Evidence grounding, 15. Unsupported-claim detection, 16. Structured answer contract, 17. Natural-language API (+64 more)

### Community 31 - "Settings"
Cohesion: 0.06
Nodes (30): Settings, create_app(), JSONFormatter, test_clean_upgrade_downgrade_reupgrade_and_readiness(), test_expired_acquisition_releases_capacity_without_accepting_its_token(), test_retrospective_signed_csv_duplicates_and_analytics_identity(), test_sequence_overflow_is_dead_lettered_and_valid_edge_persists(), test_stream_poll_is_atomic_replay_safe_and_persists_provisional_findings() (+22 more)

### Community 32 - "status.test.tsx"
Cohesion: 0.17
Nodes (15): dynamic, GET(), Home(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready (+7 more)

### Community 34 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 35 - "detectors.py"
Cohesion: 0.19
Nodes (8): compute_pull_metrics(), HeuristicSegmentDetector, _mean(), PullDetector, SegmentDetector, _slope(), DetectedSegment, PullMetrics

### Community 36 - "Orchestrator"
Cohesion: 0.18
Nodes (8): at(), effective(), resolve_context(), Orchestrator, VehicleContext, Execution, GraphState, test_provider_retry_and_grounding_correction_are_bounded()

### Community 37 - "analytics-workspace.tsx"
Cohesion: 0.14
Nodes (13): AnalyticsWorkspace(), history(), Configuration, curveLabels, HistoricalTrend(), NormalizedBin, NormalizedCurves(), Profile (+5 more)

### Community 38 - "InvestigationPlan"
Cohesion: 0.18
Nodes (6): InvestigationEvent, InvestigationPlan, InvestigationInstrumentation, InvestigationRepository, item(), claim()

### Community 39 - "next"
Cohesion: 0.18
Nodes (5): config, GET, POST, metadata, next

### Community 41 - "Elm327Adapter"
Cohesion: 0.15
Nodes (9): Elm327Adapter, ElmTransport, FakeElm, test_elm327_only_uses_allowlisted_read_commands(), test_elm_recovers_timeout_without_reusing_sequence(), immediate(), request(), test_unavailable_optional_pid_preserves_other_reads() (+1 more)

### Community 42 - "devDependencies"
Cohesion: 0.12
Nodes (16): devDependencies, @axe-core/playwright, eslint, @eslint/compat, eslint-config-next, jsdom, @playwright/test, @testing-library/jest-dom (+8 more)

### Community 43 - "telemetry.test.tsx"
Cohesion: 0.09
Nodes (13): audit, result, Stream, detectedEvent, pull, segment, session, signals (+5 more)

### Community 44 - "Ledger"
Cohesion: 0.08
Nodes (31): expected_statement(), grade(), summarize(), temporal_checks(), effective(), timestamp(), Case, Ledger (+23 more)

### Community 45 - "Supervisor"
Cohesion: 0.16
Nodes (33): Specialist, Sufficiency, Supervisor, runtime(), call(), test_concurrent_identical_mcp_calls_reuse_single_result(), test_final_synthesis_preserves_remaining_question_gaps(), test_interrupted_paid_turn_preserves_unknown_usage_in_parent() (+25 more)

### Community 46 - "package.json"
Cohesion: 0.11
Nodes (17): devDependencies, openapi-typescript, prettier, engines, node, name, packageManager, private (+9 more)

### Community 47 - "DeterministicProvider"
Cohesion: 0.09
Nodes (27): HypothesisCategory, InvestigationInput, InvestigationProposal, ProposedGap, ProposedHypothesis, OpenAIProvider, ModelInput, ModelTurn (+19 more)

### Community 48 - "ADR 0018: Read-only MCP application adapter"
Cohesion: 0.17
Nodes (10): ADR 0016: Deterministic, immutable automotive analytics, Consequences, Decision, Status, ADR 0018: Read-only MCP application adapter, Alternatives, Consequences and risks, Context (+2 more)

### Community 49 - "observability-validation.sh"
Cohesion: 0.40
Nodes (3): observability-validation.sh script, wait_prometheus_query(), stack-smoke.sh script

### Community 50 - "test_gateway_publisher_classifies_responses"
Cohesion: 0.13
Nodes (4): test_consumer_database_failure_exits_without_sql_inputs(), fail(), test_gateway_publisher_classifies_responses(), test_gateway_transport_errors_enter_retry_spool_path()

### Community 51 - "vehicle-workspace.tsx"
Cohesion: 0.16
Nodes (15): AgentWorkspace(), loadRun(), observe(), submit(), DetectedEvent, json(), Pull, Segment (+7 more)

### Community 52 - "Phase 7B — Investigation & Adaptive Logging"
Cohesion: 0.02
Nodes (98): 10. Investigation taxonomy, 11. Evidence gap model, 12. Reuse Phase 7A missing-evidence categories, 13. SignalNeed abstraction, 14. No invented channels, 15. Capability resolver, 16. Session capability vs hardware/source capability, 17. Existing-data-first policy (+90 more)

### Community 53 - "test_gateway_heartbeat_is_scoped_and_failures_are_explicit"
Cohesion: 0.25
Nodes (4): report(), report_periodically(), test_gateway_heartbeat_is_scoped_and_failures_are_explicit(), post()

### Community 54 - "AgentError"
Cohesion: 0.05
Nodes (62): materialize(), AgentError, Rates, url(), url(), storage(), provider(), request() (+54 more)

### Community 55 - "97. Phase 7C Definition of Done"
Cohesion: 0.14
Nodes (14): 97. Phase 7C Definition of Done, API/UI/SSE, Conflicts, Data quality, Delivery, Evidence, Observability/performance, Parallelism (+6 more)

### Community 56 - "pytest"
Cohesion: 0.10
Nodes (47): canonical_hash(), EvidenceRegistry, facts(), render_binding(), validate(), comparison(), test_association_degrades_without_comparable_complete_context(), test_association_uses_actual_selected_pull_configuration_and_timeline() (+39 more)

### Community 57 - "MappedCSVTelemetrySource"
Cohesion: 0.21
Nodes (11): CSVColumnMapping, CSVSignalColumn, MappedCSVTelemetrySource, mapping(), test_absent_mapping_and_invalid_headers_are_rejected(), test_explicit_identity_sequence_are_preserved(), test_explicit_wide_csv_mapping_preserves_units_time_and_provenance(), test_header_inspection_rejects_missing_ambiguous_or_oversized_csv() (+3 more)

### Community 59 - "StrictModel"
Cohesion: 0.07
Nodes (26): AgentInstrumentation, Hypothesis, HypothesisStatus, InvestigationOutcome, _event_type(), outcome(), _quality_evidence(), update_hypotheses() (+18 more)

### Community 60 - "security-policy.py"
Cohesion: 0.24
Nodes (5): accepted(), load_exceptions(), load_findings(), main(), parse_args()

### Community 61 - "mcp-validation.sh"
Cohesion: 0.25
Nodes (6): DATABASE_URL, ENVIRONMENT, MCP_TEST_PROJECT, mcp-validation.sh script, TEST_DATABASE_URL, TEST_KAFKA_PORT

### Community 62 - "agents/schemas.py"
Cohesion: 0.07
Nodes (48): accumulate(), Answer, Classification, Conflict, Finding, Intent, RoutingDecision, RoutingProposal (+40 more)

### Community 63 - "README.md"
Cohesion: 0.10
Nodes (13): Contributing, Phase 7C specialist agents and supervisor, System context, Toolchain selection, Local development, Current phase, Phase 7C implementation, Roadmap (+5 more)

### Community 64 - "PHASE 0 COMPLETION REPORT"
Cohesion: 0.11
Nodes (19): ADRs created, Applications, Architecture, CI/CD, Closure rerun result, Codex context, Database, Deferred deliberately to Phase 1+ (+11 more)

### Community 65 - "telemetry/service.py"
Cohesion: 0.14
Nodes (10): ImportResult, TelemetryPoint, TelemetryWindow, LiveOBDSource, TelemetrySource, _content_hash(), IngestionService, QueryService (+2 more)

### Community 66 - "integration.sh"
Cohesion: 0.40
Nodes (3): KAFKA_BOOTSTRAP_SERVERS, integration.sh script, TEST_DATABASE_URL

### Community 67 - "retrospective-validation.sh"
Cohesion: 0.40
Nodes (3): COMPOSE_PROJECT_NAME, GIT_SHA, retrospective-validation.sh script

### Community 69 - "113. Final delivery report"
Cohesion: 0.12
Nodes (17): 113. Final delivery report, API, Architecture, Benchmark, Data sufficiency / false conclusions, Explicit deferrals, Frontend, GitHub (+9 more)

### Community 91 - "Container scan findings — 2026-10-01"
Cohesion: 0.09
Nodes (17): Closure, Phase 0 task map, Phase 1 outline — Vehicle & Telemetry Core, 2026-10-09 Go advisory refresh, 2026-10-10 Go HTTP/2 advisory refresh, 2026-10-10 Kafka dependency refresh, Canonical rerun 36952758342, Container scan findings — 2026-10-01 (+9 more)

### Community 93 - "126. Final delivery report"
Cohesion: 0.14
Nodes (14): 126. Final delivery report, Architecture, Explicit deferrals, GitHub, Hardware, Live system, Migrations, Observability (+6 more)

### Community 94 - "45. Required synthetic scenarios"
Cohesion: 0.15
Nodes (13): 45. Required synthetic scenarios, A. Identical repeated pulls, B. Progressive IAT accumulation, C. Progressive boost reduction, D. Fuel-pressure degradation pattern, E. Slower normalized acceleration, F. Noisy but unchanged vehicle, G. Different configuration (+5 more)

### Community 95 - "Envelope"
Cohesion: 0.13
Nodes (11): MCPClient, call(), Envelope, call(), test_actual_response_limit_and_unknown_tool(), big(), test_timeout_size_rate_and_spans(), delayed() (+3 more)

### Community 96 - "73. Definition of Done"
Cohesion: 0.17
Nodes (12): 73. Definition of Done, API/UI, Architecture, Delivery, Grounding, Observability, Orchestration, Performance (+4 more)

### Community 97 - "Phase 6 acceptance evidence"
Cohesion: 0.20
Nodes (7): Executed acceptance checkpoint, Independent MCP evidence, Limitations and deferred scope, Measured performance and bounds, Phase 6 acceptance evidence, Remote proof and final HEAD identity, Phase 6 traceability ledger

### Community 98 - "Phase 7D — Real Model Validation & Agent Reliability Baseline"
Cohesion: 0.13
Nodes (15): 10. No hidden real calls in normal CI, 11. Evaluation dataset design, 12. Suite size, 13. Category distribution, 1. Repository / branch / baseline, 2. Phase 7C closure status, 3. Phase 7D purpose, 4. Primary model choice (+7 more)

### Community 99 - "Phases 0–5 retrospective hardening"
Cohesion: 0.06
Nodes (29): ADR 0014: Kafka durable acquisition stream, Consequences, Context, Decision, ADR 0017: Retrospective evidence and execution identity, Alternatives, Consequences and risks, Context (+21 more)

### Community 100 - "test_periodic_heartbeat_continues_while_adapter_waits"
Cohesion: 0.25
Nodes (4): test_collector_capability_failure_closes_adapter(), test_periodic_heartbeat_continues_while_adapter_waits(), read(), publish()

### Community 101 - "investigation/service.py"
Cohesion: 0.21
Nodes (15): Availability, EvidenceGap, Feasibility, GapStatus, GapType, ExistingEvidence, _good_signals(), search_existing() (+7 more)

### Community 102 - "Adapter"
Cohesion: 0.14
Nodes (8): Adapter, Catalog, ErrorCode, PlatformError, Warning, Window, test_adapter_isolation_and_envelope(), test_resource_errors_are_safe()

### Community 103 - "pull_request_template.md"
Cohesion: 0.22
Nodes (8): Database/contract impact, Documentation, How it was validated, Observability impact, Risks, Security impact, What changed, Why

### Community 105 - "investigation/domain.py"
Cohesion: 0.13
Nodes (31): validated_report(), DeviceCapabilities, Importance, LoggingRecipe, plan_sampling(), PreflightResult, Priority, Readiness (+23 more)

### Community 106 - "Phase 5 automotive analytics"
Cohesion: 0.25
Nodes (7): Comparability and sufficiency, Metrics and normalization, Phase 5 automotive analytics, Pipeline and source of truth, Retrospective calculation identity, Retrospective metric and presentation completeness, Robust statistics and provenance

### Community 107 - "14. Specialist tool allowlists"
Cohesion: 0.40
Nodes (5): 14. Specialist tool allowlists, Data Quality candidate tools, Fuel/Air/Boost candidate tools, Performance candidate tools, Thermal candidate tools

### Community 108 - "N55 Intelligence Lab"
Cohesion: 0.17
Nodes (12): Arquitetura e continuidade, Desenvolvimento e testes, Estado atual, N55 Intelligence Lab, Observabilidade, Phase 6 MCP, Phase 7A grounded agent, Phase 7B investigation and adaptive logging (+4 more)

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

### Community 120 - "Grounded agent operation"
Cohesion: 0.50
Nodes (4): Failure handling, Grounded agent operation, Local configuration, Validation commands

### Community 121 - "Phase 3 event and anomaly engine"
Cohesion: 0.29
Nodes (6): Baselines and comparability, Evaluation, troubleshooting, and boundaries, Phase 3 event and anomaly engine, Pipeline and limits, Retrospective detector review, Taxonomy and detectors

### Community 122 - "55. Required test layers"
Cohesion: 0.29
Nodes (7): 55. Required test layers, Acceptance, Browser E2E, Integration, Observability, Security, Unit

### Community 123 - "Phase 1 vehicle and telemetry core"
Cohesion: 0.40
Nodes (4): Canonical import contract, Performance baseline protocol, Phase 1 vehicle and telemetry core, Query and operations

### Community 124 - "ADR 0012: Versioned deterministic session analysis"
Cohesion: 0.33
Nodes (5): ADR 0012: Versioned deterministic session analysis, Alternatives, Consequences and risks, Context, Decision

### Community 125 - "ADR 0013: Deterministic evidence-first event architecture"
Cohesion: 0.33
Nodes (5): ADR 0013: Deterministic evidence-first event architecture, Alternatives, Consequences and risks, Context, Decision

### Community 126 - "api/errors.py"
Cohesion: 0.09
Nodes (18): ResourceBudgetMiddleware, ErrorDetail, ErrorResponse, register_errors(), agent_error(), http_error(), invalid(), unavailable() (+10 more)

### Community 127 - "Phase 7A grounded agent"
Cohesion: 0.40
Nodes (5): Boundaries, Context and evidence, Execution and lifecycle, Phase 7A grounded agent, Provider and streaming contracts

### Community 129 - "Phase 3 events"
Cohesion: 0.22
Nodes (8): Grounded agent, Investigation and adaptive logging, MCP, Observability, Phase 2 analysis, Phase 3 events, Phase 7C supervisor, Retrospective instrumentation checks

### Community 130 - "75. API surface"
Cohesion: 0.33
Nodes (6): 75. API surface, Acquisition, Ingestion, Live client, Logging objectives, Recipes

### Community 131 - "85. Unit and contract tests"
Cohesion: 0.33
Nodes (6): 85. Unit and contract tests, Collector, Live analysis, Recipes, Sampling, Stream

### Community 132 - "capabilities.py"
Cohesion: 0.16
Nodes (11): AcquisitionCapabilitySource, fresh(), SourceCapabilitySnapshot, query_row(), report(), source(), test_latest_prefers_newer_registered_report(), test_latest_rejects_stale_and_disconnected_reports() (+3 more)

### Community 133 - "architecture/phase-6-mcp-tool-platform.md"
Cohesion: 0.10
Nodes (16): Component model, CURRENT, FUTURE, Phase 6 MCP tool platform, Resources, Safety and errors, Approval and follow-up, Domain and persistence (+8 more)

### Community 134 - "main"
Cohesion: 0.83
Nodes (4): main(), address(), command(), wait_for_telemetry_backends()

### Community 135 - "Vehicle Intelligence Platform context"
Cohesion: 0.40
Nodes (4): Business Logic & Feature Map, Directory Structure Map, Validation, Vehicle Intelligence Platform context

### Community 136 - "Phase 7C traceability ledger"
Cohesion: 0.67
Nodes (3): Evidence references, Phase 7C traceability ledger, Requirement matrix

### Community 137 - "test_agent_budgets.py"
Cohesion: 0.12
Nodes (9): AgentRequestBudgetMiddleware, TokenBucket, scope(), test_budget_failures_release_reservation(), test_invalid_budgets(), test_request_cancellation_releases_reservation(), test_request_failure_releases_reservation(), test_request_passthrough_and_bounded_body() (+1 more)

### Community 138 - "94. Failure behavior"
Cohesion: 0.40
Nodes (5): 94. Failure behavior, Database unavailable, Device disconnect, One bad signal, Stream unavailable

### Community 139 - "strategy.md"
Cohesion: 0.25
Nodes (7): Phase 3 acceptance, Phase 6 acceptance, Phase 7A acceptance, Phase 7B acceptance, Phase 7C acceptance, Retrospective phase gates, Testing strategy

### Community 144 - "CATEGORY A — FACTUAL / FAST-PATH"
Cohesion: 0.18
Nodes (11): 14. A01 — last session, 15. A02 — active configuration, 16. A03 — installed modifications, 17. A04 — last pull count, 18. A05 — strongest pull, 19. A06 — session capabilities, 20. A07 — event lookup, 21. A08 — current vs historical configuration identity (+3 more)

### Community 145 - "CATEGORY B — PERFORMANCE"
Cohesion: 0.18
Nodes (11): 24. B01, 25. B02, 26. B03, 27. B04, 28. B05, 29. B06, 30. B07, 31. B08 (+3 more)

### Community 146 - "CATEGORY C — THERMAL"
Cohesion: 0.18
Nodes (11): 34. C01, 35. C02, 36. C03, 37. C04, 38. C05, 39. C06, 40. C07, 41. C08 (+3 more)

### Community 147 - "mcp/instrumentation.py"
Cohesion: 0.17
Nodes (3): main(), HTTPInstrumentation, test_http_trace_context_and_auth_rejections()

### Community 148 - "EventEngine"
Cohesion: 0.27
Nodes (15): EventProfile, EventEngine, base(), frames(), pull(), test_comparable_pulls(), test_fuel_drop_requires_sustained_observation_not_single_low_spike(), test_low_load_variation_is_not_fuel_or_throttle_event() (+7 more)

### Community 149 - "15. Required acquisition adapters"
Cohesion: 0.50
Nodes (4): 15. Required acquisition adapters, Real read-only OBD adapter path, Replay adapter, Synthetic live adapter

### Community 152 - "CATEGORY D — FUEL / AIR / BOOST"
Cohesion: 0.18
Nodes (11): 44. D01, 45. D02, 46. D03, 47. D04, 48. D05, 49. D06, 50. D07, 51. D08 (+3 more)

### Community 153 - "101. ADRs"
Cohesion: 0.67
Nodes (3): 101. ADRs, Acquisition lifecycle / recipes, Streaming architecture

### Community 154 - "Phase 7A acceptance"
Cohesion: 0.29
Nodes (7): Baseline and delivery boundary, Executed checkpoint: `881fcca0bb75acf9369bbbf25854c32d626aa017`, Final receipt requirements, Missing-evidence correction: `4df84696ab3ffb5d900399877849975b008fe4cf`, Phase 7A acceptance, Pushed-head full verification checkpoint: `66efbc744ab23c5ba0044cb6029ebd69c56f2206`, Real provider and practical limits

### Community 155 - "CATEGORY E — DATA QUALITY"
Cohesion: 0.18
Nodes (11): 54. E01, 55. E02, 56. E03, 57. E04, 58. E05, 59. E06, 60. E07, 61. E08 (+3 more)

### Community 159 - "CATEGORY F — MULTI-SPECIALIST"
Cohesion: 0.18
Nodes (11): 64. F01, 65. F02, 66. F03, 67. F04, 68. F05, 69. F06, 70. F07, 71. F08 (+3 more)

### Community 168 - "provider.py"
Cohesion: 0.08
Nodes (11): AgentSettings, redact_data(), connect(), EvidenceClient, Provider, ResponseObserver, audit(), emit() (+3 more)

### Community 173 - "CATEGORY G — PHASE 7B / INSUFFICIENT EVIDENCE / ADAPTIVE LOGGING"
Cohesion: 0.18
Nodes (11): 74. G01, 75. G02, 76. G03, 77. G04, 78. G05, 79. G06, 80. G07, 81. G08 (+3 more)

### Community 174 - "investigation_router"
Cohesion: 0.11
Nodes (4): investigation_router(), stream(), test_investigation_api_requires_operator_token(), test_operator_route_requires_configured_token()

### Community 175 - "test_agent_repository.py"
Cohesion: 0.23
Nodes (9): rows(), test_database_errors_are_normalized_and_session_closes(), test_interrupted_run_reconciliation_is_bounded_and_terminal(), test_missing_driver_fails_closed(), test_repository_not_found_and_bounds(), test_repository_run_audit_and_stream_serialization(), test_stale_retrieval_refreshes_reconciled_state(), test_watchdog_bounds_unresponsive_cancellation_cleanup() (+1 more)

### Community 176 - "ADR 0022: Bounded real-model evaluation and durable spend accounting"
Cohesion: 0.22
Nodes (7): ADR 0022: Bounded real-model evaluation and durable spend accounting, Alternatives, Consequences and risks, Context, Decision, Status, Phase 7D real-model validation

### Community 178 - "telemetry.py"
Cohesion: 0.11
Nodes (3): SanitizingExporter, test_database_error_propagation_cannot_leak_through_parent_spans(), test_sql_text_is_removed_from_non_database_successful_spans()

### Community 179 - "Phase 4 acquisition threats"
Cohesion: 0.33
Nodes (6): Original Phase 4 local resource budgets, Phase 4 acquisition threats, Phase 6 MCP boundary, Phase 7A agent boundary, Phase 7B investigation and adaptive logging, Phase 7C supervisor and specialists

### Community 180 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 182 - "ADR 0019: Grounded agent state and evidence"
Cohesion: 0.08
Nodes (22): blocked(), ADR 0015: Versioned recipes and acquisition lifecycle, Consequences, Decision, ADR 0019: Grounded agent state and evidence, Alternatives, Consequences and risks, Context (+14 more)

### Community 183 - "98. Phase 7B Definition of Done"
Cohesion: 0.15
Nodes (13): 98. Phase 7B Definition of Done, Acquisition / follow-up, API / UI, Approval, Delivery, Existing evidence, Investigation domain, Logging plan (+5 more)

### Community 187 - "json"
Cohesion: 0.07
Nodes (30): main(), seed_agent(), main(), main(), ask(), runtime(), main(), main() (+22 more)

### Community 188 - "Phase 7B acceptance"
Cohesion: 0.29
Nodes (5): Benchmark checkpoint, Final receipt requirements, Phase 7B acceptance, Scope and gates, Phase 7B requirement traceability

### Community 191 - "Phase 4 — Streaming & Live Vehicle Acquisition"
Cohesion: 0.22
Nodes (8): Boundaries and flow, Broker storage and observed worker health, Explicit CSV mapping and live recovery, Failure and security model, Phase 4 — Streaming & Live Vehicle Acquisition, Recipes and quality, Retrospective execution guarantees, Safety and hardware status

### Community 192 - "Phase 2 session and pull analysis"
Cohesion: 0.40
Nodes (4): API and limits, Phase 2 session and pull analysis, Semantics, Synthetic validation

### Community 196 - "45. Investigation examples"
Cohesion: 0.50
Nodes (4): 45. Investigation examples, Example A — repeated pull performance loss, Example B — change after intercooler, Example C — missing technical specification

### Community 204 - "InvestigationService"
Cohesion: 0.14
Nodes (13): CapabilitySnapshot, ApprovalRequest, CreateInvestigation, LinkSessionRequest, RegisterSourcePreflight, VersionRequest, InvestigationService, PreflightRequest (+5 more)

### Community 205 - "Phase 7C acceptance"
Cohesion: 0.50
Nodes (4): Local and canonical validation, Phase 7C acceptance, Phase 7C receipts, Result

## Knowledge Gaps
- **22 isolated node(s):** `vehicle-platform-api`, `react-dom`, `typescript`, `@types/node`, `@types/react` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1725 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **59 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OpenAIProvider` connect `DeterministicProvider` to `provider.py`, `main.py`, `ADR 0022: Bounded real-model evaluation and durable spend accounting`, `AgentError`, `datetime`, `agents/schemas.py`, `Settings`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 111 inferred relationships involving `AgentError` (e.g. with `EvidenceRegistry` and `InvestigationRepository`) actually correct?**
  _`AgentError` has 111 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vehicle-platform-api`, `react-dom`, `typescript` to the rest of the system?**
  _22 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `AnalyticsConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.08289536550406115 - nodes in this community are weakly interconnected._
- **Why does `Phase 7D real-model validation` connect `ADR 0022: Bounded real-model evaluation and durable spend accounting` to `DeterministicProvider`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `router()` (e.g. with `LoggingRecipe` and `AcquisitionAuthError`) actually correct?**
  _`router()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Should `dataclasses` be split into smaller, more focused modules?**
  _Cohesion score 0.11538461538461539 - nodes in this community are weakly interconnected._