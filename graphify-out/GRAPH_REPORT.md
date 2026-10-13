# Graph Report - Vehicle-Intelligence-Platform  (2026-10-13)

## Corpus Check
- 353 files · ~311,181 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: (none) 11, .Dockerfile 2, .example 1)

## Summary
- 3817 nodes · 10321 edges · 214 communities (154 shown, 60 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 1936 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6b228dac`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AnalyticsConfig
- BoundedSpool
- ErrorCode
- router
- api/routes.py
- SyntheticLiveAdapter
- acquisition/service.py
- RawTelemetryRecord
- Catalog
- test_investigation.py
- acquisition/cli.py
- MCPSettings
- AlignedFrame
- sqlalchemy
- register_errors
- CATEGORY H — ADVERSARIAL / SECURITY / UNCERTAINTY
- runtime.py
- dataclasses
- telemetry/domain.py
- Phase 7C — Specialist Agents & Supervisor Orchestration
- web/package.json
- Phase 4 — Streaming & Live Vehicle Acquisition
- live-acquisition.tsx
- Phase 5 — Automotive Analytics
- register_tools
- generated/api.ts
- Adapter
- AgentSettings
- validate_vehicle_context
- Phase 7A — Agent Core & Grounded Orchestration
- CorrelationMiddleware
- worker.py
- status.test.tsx
- test_gateway_publisher_classifies_responses
- compilerOptions
- agents/schemas.py
- DeviceCapabilities
- analytics-workspace.tsx
- AgentError
- next
- InvestigationService
- Elm327Adapter
- devDependencies
- telemetry.test.tsx
- test_phase7d_grading.py
- Supervisor
- package.json
- DeterministicProvider
- architecture/phase-6-mcp-tool-platform.md
- observability-validation.sh
- test_acquisition.py
- vehicle-workspace.tsx
- Phase 7B — Investigation & Adaptive Logging
- DependencyUnavailable
- test_agent_runtime.py
- 97. Phase 7C Definition of Done
- test_agents.py
- Settings
- Orchestrator
- json
- mcp-validation.sh
- phase-7a-traceability-ledger.md
- README.md
- PHASE 0 COMPLETION REPORT
- test_phase7d_cli.py
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
- StrictModel
- 73. Definition of Done
- mapping.py
- Phase 7D — Real Model Validation & Agent Reliability Baseline
- Phases 0–5 retrospective hardening
- evaluate_agent_grounding.py
- investigation/service.py
- create_app
- pull_request_template.md
- evaluate_supervisor.py
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
- SanitizingExporter
- Phase 3 event and anomaly engine
- 55. Required test layers
- pytest
- ADR 0012: Versioned deterministic session analysis
- ADR 0013: Deterministic evidence-first event architecture
- .run
- datetime
- test_agent_repository.py
- Phase 3 events
- 75. API surface
- 85. Unit and contract tests
- typing
- SessionAnalysisService
- EventEngine
- Vehicle Intelligence Platform context
- Telemetry
- test_mcp.py
- 94. Failure behavior
- strategy.md
- adr.md
- migrations.md
- definition-of-done.md
- gates.md
- CATEGORY A — FACTUAL / FAST-PATH
- CATEGORY B — PERFORMANCE
- CATEGORY C — THERMAL
- security-policy.py
- Envelope
- 15. Required acquisition adapters
- Vehicle Intelligence Platform / N55 Intelligence Lab
- events/synthetic.py
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
- test_elm_tcp_transport_connects_reads_reuses_and_closes
- infra/AGENTS.md
- contracts/AGENTS.md
- contracts/README.md
- SECURITY.md
- CATEGORY G — PHASE 7B / INSUFFICIENT EVIDENCE / ADAPTIVE LOGGING
- investigation_router
- AgentRepository
- prompts/phase-7d-real-model-validation.md
- mcp/instrumentation.py
- AgentService
- Phase 4 acquisition threats
- scripts
- test_acquisition_capabilities.py
- ADR 0019: Grounded agent state and evidence
- 98. Phase 7B Definition of Done
- Phase 1 vehicle and telemetry core
- @playwright/test
- os
- Phase 7B acceptance
- Phase 6 acceptance evidence
- AcquisitionPublisher
- httpx
- ADR 0018: Read-only MCP application adapter
- Phase 2 session and pull analysis
- main.py
- events/service.py
- 45. Investigation examples
- Observed answers
- Phase 7A grounded agent
- phase-7d-traceability-ledger.md
- phase-7d-delivery.md
- Phase 4 — Streaming & Live Vehicle Acquisition
- Support
- test_investigation_repository.py
- phase7d_eval.py
- main
- Grounded agent operation
- Phase 7C acceptance
- CaptureProvider
- compute_pull_metrics
- Terminable

## God Nodes (most connected - your core abstractions)
1. `AgentError` - 220 edges
2. `Phase 4 — Streaming & Live Vehicle Acquisition` - 128 edges
3. `router()` - 126 edges
4. `Phase 5 — Automotive Analytics` - 115 edges
5. `Phase 7B — Investigation & Adaptive Logging` - 100 edges
6. `Phase 7C — Specialist Agents & Supervisor Orchestration` - 99 edges
7. `Settings` - 81 edges
8. `Telemetry` - 80 edges
9. `Phase 7A — Agent Core & Grounded Orchestration` - 75 edges
10. `DeterministicProvider` - 65 edges

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

## Communities (214 total, 60 thin omitted)

### Community 0 - "AnalyticsConfig"
Cohesion: 0.08
Nodes (54): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+46 more)

### Community 1 - "BoundedSpool"
Cohesion: 0.16
Nodes (12): BoundedSpool, test_bounded_spool_replays_and_reports_overflow(), test_collector_interruption_preserves_unpublished_partial_batch(), read(), test_collector_rejects_unbounded_configuration(), test_collector_retries_spools_and_replays_without_loss(), test_spool_acknowledges_only_after_publish_and_recovers_in_same_run(), test_spool_atomic_acknowledgement_preserves_remaining_records() (+4 more)

### Community 2 - "ErrorCode"
Cohesion: 0.16
Nodes (3): ErrorCode, tool_error(), SafeMCPServer

### Community 3 - "router"
Cohesion: 0.10
Nodes (52): Health, Ready, Version, router(), analytics_config(), analyze_repeated_pulls(), assess_session_capabilities(), bearer() (+44 more)

### Community 4 - "api/routes.py"
Cohesion: 0.10
Nodes (34): AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement, AnalysisRequest, AnalyticsRequest, CollectorHealthResponse, ConfigurationCreate, CSVImportPreview (+26 more)

### Community 5 - "SyntheticLiveAdapter"
Cohesion: 0.16
Nodes (12): SyntheticLiveAdapter, report(), test_collector_capability_failure_closes_adapter(), test_collector_heartbeat_interruption_does_not_erase_samples(), test_collector_reports_capabilities_bounds_and_graceful_disconnect(), heartbeat(), test_extended_synthetic_modes_have_measured_behavior(), test_golden_synthetic_scenarios() (+4 more)

### Community 6 - "acquisition/service.py"
Cohesion: 0.13
Nodes (20): assess_dataset(), collector_health(), DatasetCapability, measure_signal_quality(), SignalQuality, AcquisitionAuthError, AcquisitionError, AcquisitionService (+12 more)

### Community 7 - "RawTelemetryRecord"
Cohesion: 0.21
Nodes (8): AcquisitionCollector, RawTelemetryRecord, test_collector_reports_actual_recovery_metrics_and_payload_free_spans(), available(), unavailable(), test_pending_spool_precedes_new_data_and_overflow_is_visible(), test_spool_replay_retries_and_only_acknowledges_success(), DenseSource

### Community 9 - "test_investigation.py"
Cohesion: 0.16
Nodes (30): InvestigationStatus, insufficient_run(), MemoryInvestigations, plan(), test_approval_rejects_changed_source_and_resumes_partial_approval(), test_approval_rejects_stale_capability_and_unready_plan(), test_cancel_and_reject_are_idempotent_only_at_exact_version(), test_completed_followup_reloads_after_stale_race() (+22 more)

### Community 10 - "acquisition/cli.py"
Cohesion: 0.19
Nodes (14): adapter_for(), AdapterKind, devices(), execute(), _preflight(), preflight_command(), probe(), recipes() (+6 more)

### Community 11 - "MCPSettings"
Cohesion: 0.09
Nodes (19): ReadTokenVerifier, MCPSettings, Instrumentation, create_server(), pull(), session(), vehicle(), runtime() (+11 more)

### Community 12 - "AlignedFrame"
Cohesion: 0.19
Nodes (23): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, PullWindow, Severity (+15 more)

### Community 13 - "sqlalchemy"
Cohesion: 0.09
Nodes (11): run(), run_sync(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade() (+3 more)

### Community 14 - "register_errors"
Cohesion: 0.06
Nodes (24): AgentRequestBudgetMiddleware, TokenBucket, register_errors(), agent_error(), http_error(), invalid(), unavailable(), unexpected() (+16 more)

### Community 15 - "CATEGORY H — ADVERSARIAL / SECURITY / UNCERTAINTY"
Cohesion: 0.03
Nodes (61): 100. Optional Sol comparison, 101. Real-model grading, 102. Hard blockers / zero-tolerance metrics, 103. Routing quality, 104. Tool efficiency, 105. Grounding, 106. Causal restraint, 107. Diagnosis restraint (+53 more)

### Community 16 - "runtime.py"
Cohesion: 0.07
Nodes (42): EvidenceRegistry, accumulate(), Classification, Conflict, RoutingProposal, SpecialistBudget, SpecialistDraft, SpecialistRequest (+34 more)

### Community 17 - "dataclasses"
Cohesion: 0.12
Nodes (28): align_observations(), rolling_median(), HeuristicPullDetector, PullDetector, DetectedPull, DetectorProfile, Observation, PullMetrics (+20 more)

### Community 18 - "telemetry/domain.py"
Cohesion: 0.08
Nodes (27): StandardPid, RawTelemetryMessage, import_csv(), DataQuality, NormalizationError, normalize_value(), parse_timestamp(), sample_id() (+19 more)

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
Cohesion: 0.09
Nodes (22): register_tools(), get_cross_session_analytics(), get_pull_summary(), get_repeated_pull_analysis(), get_session_analytics(), get_session_capabilities(), get_session_summary(), get_telemetry_window() (+14 more)

### Community 25 - "generated/api.ts"
Cohesion: 0.10
Nodes (23): AgentEvent, AgentRun, Audit, AgentRun, Investigation, InvestigationWorkspace(), terminal, Report (+15 more)

### Community 26 - "Adapter"
Cohesion: 0.31
Nodes (5): Adapter, PlatformError, Warning, compare_configurations(), get_event()

### Community 27 - "AgentSettings"
Cohesion: 0.13
Nodes (12): AgentSettings, AgentInstrumentation, connect(), EvidenceClient, MeteredClient, ToolMeter, source(), test_evaluation_factory_wraps_the_actual_connect_seam() (+4 more)

### Community 28 - "validate_vehicle_context"
Cohesion: 0.16
Nodes (7): ImportResult, TelemetryWindow, create_modification(), create_session(), LiveOBDSource, TelemetrySource, validate_vehicle_context()

### Community 29 - "Phase 7A — Agent Core & Grounded Orchestration"
Cohesion: 0.03
Nodes (72): 10. Agent state, 11. AgentRun persistence, 12. ToolCall persistence / audit trail, 13. Evidence model, 14. Claim → Evidence grounding, 15. Unsupported-claim detection, 16. Structured answer contract, 17. Natural-language API (+64 more)

### Community 30 - "CorrelationMiddleware"
Cohesion: 0.13
Nodes (3): CorrelationMiddleware, PlatformAPI, test_non_http_passthrough()

### Community 31 - "worker.py"
Cohesion: 0.15
Nodes (5): StreamConsumer, HeuristicSegmentDetector, SegmentDetector, DetectedSegment, test_provisional_window_is_event_time_bounded_without_discarding_canonical_input()

### Community 32 - "status.test.tsx"
Cohesion: 0.17
Nodes (15): dynamic, GET(), Home(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready (+7 more)

### Community 33 - "test_gateway_publisher_classifies_responses"
Cohesion: 0.13
Nodes (4): test_consumer_database_failure_exits_without_sql_inputs(), fail(), test_gateway_publisher_classifies_responses(), test_gateway_transport_errors_enter_retry_spool_path()

### Community 34 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 35 - "agents/schemas.py"
Cohesion: 0.16
Nodes (8): at(), effective(), resolve_context(), Provider, Answer, Finding, SpecialistFinding, VehicleContext

### Community 36 - "DeviceCapabilities"
Cohesion: 0.21
Nodes (17): DeviceCapabilities, RecipeReference, SignalNeed, SignalRole, choose_recipe(), plan_recipe(), PlannedRecipe, resolve_needs() (+9 more)

### Community 37 - "analytics-workspace.tsx"
Cohesion: 0.14
Nodes (13): AnalyticsWorkspace(), history(), Configuration, curveLabels, HistoricalTrend(), NormalizedBin, NormalizedCurves(), Profile (+5 more)

### Community 38 - "AgentError"
Cohesion: 0.27
Nodes (3): InvestigationEvent, InvestigationRepository, AgentError

### Community 39 - "next"
Cohesion: 0.18
Nodes (5): config, GET, POST, metadata, next

### Community 40 - "InvestigationService"
Cohesion: 0.15
Nodes (7): Approval, InvestigationError, InvestigationPlan, InvestigationService, test_create_timeout_maps_to_bounded_public_error(), test_followup_watcher_reconciles_and_logs_failure_without_leaking(), test_link_get_and_close_reconcile_followup()

### Community 41 - "Elm327Adapter"
Cohesion: 0.22
Nodes (8): Elm327Adapter, FakeElm, test_elm327_only_uses_allowlisted_read_commands(), test_elm_recovers_timeout_without_reusing_sequence(), immediate(), request(), test_unavailable_optional_pid_preserves_other_reads(), request()

### Community 42 - "devDependencies"
Cohesion: 0.12
Nodes (16): devDependencies, @axe-core/playwright, eslint, @eslint/compat, eslint-config-next, jsdom, @playwright/test, @testing-library/jest-dom (+8 more)

### Community 43 - "telemetry.test.tsx"
Cohesion: 0.09
Nodes (13): audit, result, Stream, detectedEvent, pull, segment, session, signals (+5 more)

### Community 44 - "test_phase7d_grading.py"
Cohesion: 0.12
Nodes (30): expected_statement(), grade(), summarize(), temporal_checks(), effective(), timestamp(), case(), public_run() (+22 more)

### Community 45 - "Supervisor"
Cohesion: 0.19
Nodes (30): Specialist, Sufficiency, Supervisor, runtime(), call(), test_concurrent_identical_mcp_calls_reuse_single_result(), test_final_synthesis_preserves_remaining_question_gaps(), test_interrupted_paid_turn_preserves_unknown_usage_in_parent() (+22 more)

### Community 46 - "package.json"
Cohesion: 0.11
Nodes (17): devDependencies, openapi-typescript, prettier, engines, node, name, packageManager, private (+9 more)

### Community 47 - "DeterministicProvider"
Cohesion: 0.11
Nodes (31): draft_schema(), OpenAIProvider, turn_data(), ModelInput, ModelTurn, RoutingInput, ToolRequest, Binding (+23 more)

### Community 48 - "architecture/phase-6-mcp-tool-platform.md"
Cohesion: 0.14
Nodes (10): Component model, CURRENT, FUTURE, Service boundaries, Docker, Limits and troubleshooting, Local stdio, MCP server (+2 more)

### Community 49 - "observability-validation.sh"
Cohesion: 0.40
Nodes (3): observability-validation.sh script, wait_prometheus_query(), stack-smoke.sh script

### Community 50 - "test_acquisition.py"
Cohesion: 0.12
Nodes (16): ReplayAdapter, run(), Readiness, capabilities(), test_collector_health_distinguishes_transport_and_sampling(), test_gateway_heartbeat_is_scoped_and_failures_are_explicit(), post(), test_heartbeat_rejects_naive_or_prestart_sample_receipt() (+8 more)

### Community 51 - "vehicle-workspace.tsx"
Cohesion: 0.16
Nodes (15): AgentWorkspace(), loadRun(), observe(), submit(), DetectedEvent, json(), Pull, Segment (+7 more)

### Community 52 - "Phase 7B — Investigation & Adaptive Logging"
Cohesion: 0.02
Nodes (98): 10. Investigation taxonomy, 11. Evidence gap model, 12. Reuse Phase 7A missing-evidence categories, 13. SignalNeed abstraction, 14. No invented channels, 15. Capability resolver, 16. Session capability vs hardware/source capability, 17. Existing-data-first policy (+90 more)

### Community 53 - "DependencyUnavailable"
Cohesion: 0.36
Nodes (4): DependencyUnavailable, test_extension_required(), test_real_database_unreachable(), test_sqlalchemy_failure()

### Community 54 - "test_agent_runtime.py"
Cohesion: 0.13
Nodes (19): Ask, service_fixture(), call(), event(), finish(), get(), replay(), save() (+11 more)

### Community 55 - "97. Phase 7C Definition of Done"
Cohesion: 0.14
Nodes (14): 97. Phase 7C Definition of Done, API/UI/SSE, Conflicts, Data quality, Delivery, Evidence, Observability/performance, Parallelism (+6 more)

### Community 56 - "test_agents.py"
Cohesion: 0.12
Nodes (37): canonical_hash(), facts(), render_binding(), validate(), comparison(), test_association_degrades_without_comparable_complete_context(), test_association_uses_actual_selected_pull_configuration_and_timeline(), test_comparison_reports_measured_change_before_unchanged_metrics() (+29 more)

### Community 57 - "Settings"
Cohesion: 0.12
Nodes (9): Settings, test_build_timestamp_normalized_to_utc(), test_empty_optional_container_metadata(), test_invalid_settings(), test_malformed_database_config(), test_required_database(), test_safe_metadata(), test_tls_mode_must_match_exactly() (+1 more)

### Community 59 - "Orchestrator"
Cohesion: 0.17
Nodes (12): Orchestrator, Execution, GraphState, test_context_and_capability_bounds(), test_measured_tool_reuses_validated_pull_but_loads_missing_capability(), execution(), test_call_budgets_before_mcp(), test_call_failures_are_audited() (+4 more)

### Community 60 - "json"
Cohesion: 0.12
Nodes (13): main(), buffered_points(), canonical_counts(), main(), memory_snapshot(), worker_metrics(), main(), main() (+5 more)

### Community 61 - "mcp-validation.sh"
Cohesion: 0.25
Nodes (6): DATABASE_URL, ENVIRONMENT, MCP_TEST_PROJECT, mcp-validation.sh script, TEST_DATABASE_URL, TEST_KAFKA_PORT

### Community 63 - "README.md"
Cohesion: 0.08
Nodes (17): Contributing, Phase 7C specialist agents and supervisor, System context, Toolchain selection, Local development, Current phase, Phase 7C implementation, Roadmap (+9 more)

### Community 64 - "PHASE 0 COMPLETION REPORT"
Cohesion: 0.11
Nodes (19): ADRs created, Applications, Architecture, CI/CD, Closure rerun result, Codex context, Database, Deferred deliberately to Phase 1+ (+11 more)

### Community 65 - "test_phase7d_cli.py"
Cohesion: 0.06
Nodes (26): Ledger, load_suite(), Rates, Suite, test_affected_selection_cannot_change_smoke_or_report(), test_exactly_one_smoke_exercises_real_adapter_without_network(), test_first_smoke_request_normalizes_sdk_auth_error_without_key(), test_identity_requires_clean_exact_commit() (+18 more)

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

### Community 95 - "StrictModel"
Cohesion: 0.13
Nodes (16): CapabilitySnapshot, Transition, InvestigationInput, InvestigationProposal, ProposedGap, ProposedHypothesis, ApprovalRequest, CreateInvestigation (+8 more)

### Community 96 - "73. Definition of Done"
Cohesion: 0.17
Nodes (12): 73. Definition of Done, API/UI, Architecture, Delivery, Grounding, Observability, Orchestration, Performance (+4 more)

### Community 97 - "mapping.py"
Cohesion: 0.17
Nodes (13): preview_csv_import(), CSVColumnMapping, CSVSignalColumn, inspect_csv(), MappedCSVTelemetrySource, mapping(), test_absent_mapping_and_invalid_headers_are_rejected(), test_explicit_identity_sequence_are_preserved() (+5 more)

### Community 98 - "Phase 7D — Real Model Validation & Agent Reliability Baseline"
Cohesion: 0.13
Nodes (15): 10. No hidden real calls in normal CI, 11. Evaluation dataset design, 12. Suite size, 13. Category distribution, 1. Repository / branch / baseline, 2. Phase 7C closure status, 3. Phase 7D purpose, 4. Primary model choice (+7 more)

### Community 99 - "Phases 0–5 retrospective hardening"
Cohesion: 0.06
Nodes (29): ADR 0014: Kafka durable acquisition stream, Consequences, Context, Decision, ADR 0017: Retrospective evidence and execution identity, Alternatives, Consequences and risks, Context (+21 more)

### Community 100 - "evaluate_agent_grounding.py"
Cohesion: 0.10
Nodes (11): evaluate(), main(), evaluate(), main(), main(), ready_endpoint(), fingerprint(), seed() (+3 more)

### Community 101 - "investigation/service.py"
Cohesion: 0.13
Nodes (29): Availability, EvidenceGap, Feasibility, GapStatus, GapType, Hypothesis, HypothesisCategory, HypothesisStatus (+21 more)

### Community 102 - "create_app"
Cohesion: 0.12
Nodes (17): create_app(), test_expired_acquisition_releases_capacity_without_accepting_its_token(), Probe, test_database_error_propagation_cannot_leak_through_parent_spans(), test_database_trace_export_redacts_driver_inputs(), test_json_logs_do_not_render_exception_secrets(), test_live_independent_and_ready(), test_logging_recipe_and_preflight_contracts() (+9 more)

### Community 103 - "pull_request_template.md"
Cohesion: 0.22
Nodes (8): Database/contract impact, Documentation, How it was validated, Observability impact, Risks, Security impact, What changed, Why

### Community 104 - "evaluate_supervisor.py"
Cohesion: 0.13
Nodes (11): evaluate(), score_claims(), main(), address(), command(), wait_for_telemetry_backends(), main(), fault_scenarios() (+3 more)

### Community 105 - "preflight"
Cohesion: 0.25
Nodes (9): Importance, LoggingRecipe, plan_sampling(), preflight(), PreflightResult, Priority, SignalRequirement, req() (+1 more)

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

### Community 121 - "Phase 3 event and anomaly engine"
Cohesion: 0.29
Nodes (6): Baselines and comparability, Evaluation, troubleshooting, and boundaries, Phase 3 event and anomaly engine, Pipeline and limits, Retrospective detector review, Taxonomy and detectors

### Community 122 - "55. Required test layers"
Cohesion: 0.29
Nodes (7): 55. Required test layers, Acceptance, Browser E2E, Integration, Observability, Security, Unit

### Community 123 - "pytest"
Cohesion: 0.09
Nodes (43): Intent, url(), url(), source(), storage(), provider(), request(), ResponseStream (+35 more)

### Community 124 - "ADR 0012: Versioned deterministic session analysis"
Cohesion: 0.33
Nodes (5): ADR 0012: Versioned deterministic session analysis, Alternatives, Consequences and risks, Context, Decision

### Community 125 - "ADR 0013: Deterministic evidence-first event architecture"
Cohesion: 0.33
Nodes (5): ADR 0013: Deterministic evidence-first event architecture, Alternatives, Consequences and risks, Context, Decision

### Community 126 - ".run"
Cohesion: 0.16
Nodes (6): ElmTransport, VehicleDataAdapter, report(), report_periodically(), CollectorStats, SamplingPlanItem

### Community 128 - "test_agent_repository.py"
Cohesion: 0.26
Nodes (9): rows(), test_database_errors_are_normalized_and_session_closes(), test_interrupted_run_reconciliation_is_bounded_and_terminal(), test_missing_driver_fails_closed(), test_repository_not_found_and_bounds(), test_repository_run_audit_and_stream_serialization(), test_stale_retrieval_refreshes_reconciled_state(), test_watchdog_bounds_unresponsive_cancellation_cleanup() (+1 more)

### Community 129 - "Phase 3 events"
Cohesion: 0.22
Nodes (8): Grounded agent, Investigation and adaptive logging, MCP, Observability, Phase 2 analysis, Phase 3 events, Phase 7C supervisor, Retrospective instrumentation checks

### Community 130 - "75. API surface"
Cohesion: 0.33
Nodes (6): 75. API surface, Acquisition, Ingestion, Live client, Logging objectives, Recipes

### Community 131 - "85. Unit and contract tests"
Cohesion: 0.33
Nodes (6): 85. Unit and contract tests, Collector, Live analysis, Recipes, Sampling, Stream

### Community 133 - "SessionAnalysisService"
Cohesion: 0.22
Nodes (8): AnalysisLimitError, SessionAnalysisService, AnalysisResult, Pull, analyze_session(), get_pull(), list_session_pulls(), list_session_segments()

### Community 134 - "EventEngine"
Cohesion: 0.26
Nodes (15): EventProfile, EventEngine, base(), frames(), pull(), test_comparable_pulls(), test_fuel_drop_requires_sustained_observation_not_single_low_spike(), test_low_load_variation_is_not_fuel_or_throttle_event() (+7 more)

### Community 135 - "Vehicle Intelligence Platform context"
Cohesion: 0.40
Nodes (4): Business Logic & Feature Map, Directory Structure Map, Validation, Vehicle Intelligence Platform context

### Community 136 - "Telemetry"
Cohesion: 0.15
Nodes (12): main(), Database, Telemetry, IngestionService, QueryService, telemetry(), test_phase3_metrics_use_only_bounded_labels(), test_phase4_metrics_use_only_bounded_labels() (+4 more)

### Community 137 - "test_mcp.py"
Cohesion: 0.12
Nodes (12): ReadOnlyDatabase, Window, test_adapter_isolation_and_envelope(), test_analytics_selection_reports_truncation(), test_database_abort_invalidated_connection(), test_http_requires_token(), test_limited_quality_does_not_claim_missing_history(), test_network_config_rejected() (+4 more)

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

### Community 147 - "security-policy.py"
Cohesion: 0.24
Nodes (5): accepted(), load_exceptions(), load_findings(), main(), parse_args()

### Community 148 - "Envelope"
Cohesion: 0.12
Nodes (12): MCPClient, call(), Envelope, test_actual_response_limit_and_unknown_tool(), big(), test_timeout_size_rate_and_spans(), delayed(), large() (+4 more)

### Community 149 - "15. Required acquisition adapters"
Cohesion: 0.50
Nodes (4): 15. Required acquisition adapters, Real read-only OBD adapter path, Replay adapter, Synthetic live adapter

### Community 151 - "events/synthetic.py"
Cohesion: 0.21
Nodes (15): evaluate_events(), EventClassMetrics, EventEvaluation, _overlaps(), anomaly_scenario(), AnomalyInjection, EventScenario, ExpectedEvent (+7 more)

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

### Community 173 - "CATEGORY G — PHASE 7B / INSUFFICIENT EVIDENCE / ADAPTIVE LOGGING"
Cohesion: 0.18
Nodes (11): 74. G01, 75. G02, 76. G03, 77. G04, 78. G05, 79. G06, 80. G07, 81. G08 (+3 more)

### Community 174 - "investigation_router"
Cohesion: 0.11
Nodes (4): investigation_router(), stream(), test_investigation_api_requires_operator_token(), test_operator_route_requires_configured_token()

### Community 175 - "AgentRepository"
Cohesion: 0.18
Nodes (4): AgentRepository, TerminableConnection, StreamEvent, ToolCall

### Community 176 - "prompts/phase-7d-real-model-validation.md"
Cohesion: 0.13
Nodes (12): ADR 0022: Bounded real-model evaluation and durable spend accounting, Alternatives, Consequences and risks, Context, Decision, Evidence-driven hardening, Operator instruction to continue within the hard ceiling, Status (+4 more)

### Community 177 - "mcp/instrumentation.py"
Cohesion: 0.17
Nodes (3): main(), HTTPInstrumentation, test_http_trace_context_and_auth_rejections()

### Community 178 - "AgentService"
Cohesion: 0.16
Nodes (7): redact_data(), AgentService, audit(), emit(), failure_category(), test_redaction_preserves_numeric_json_and_escaped_strings(), test_transport_exception_groups_preserve_safe_categories()

### Community 179 - "Phase 4 acquisition threats"
Cohesion: 0.33
Nodes (6): Original Phase 4 local resource budgets, Phase 4 acquisition threats, Phase 6 MCP boundary, Phase 7A agent boundary, Phase 7B investigation and adaptive logging, Phase 7C supervisor and specialists

### Community 180 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 181 - "test_acquisition_capabilities.py"
Cohesion: 0.50
Nodes (6): query_row(), report(), test_latest_prefers_newer_registered_report(), test_latest_rejects_stale_and_disconnected_reports(), test_latest_uses_connected_collector_snapshot(), test_register_requires_active_configuration_and_limits_source()

### Community 182 - "ADR 0019: Grounded agent state and evidence"
Cohesion: 0.08
Nodes (22): blocked(), ADR 0015: Versioned recipes and acquisition lifecycle, Consequences, Decision, ADR 0019: Grounded agent state and evidence, Alternatives, Consequences and risks, Context (+14 more)

### Community 183 - "98. Phase 7B Definition of Done"
Cohesion: 0.15
Nodes (13): 98. Phase 7B Definition of Done, Acquisition / follow-up, API / UI, Approval, Delivery, Existing evidence, Investigation domain, Logging plan (+5 more)

### Community 184 - "Phase 1 vehicle and telemetry core"
Cohesion: 0.40
Nodes (4): Canonical import contract, Performance baseline protocol, Phase 1 vehicle and telemetry core, Query and operations

### Community 187 - "os"
Cohesion: 0.10
Nodes (15): main(), seed_agent(), main(), main(), ask(), free_port(), runtime(), main() (+7 more)

### Community 188 - "Phase 7B acceptance"
Cohesion: 0.29
Nodes (5): Benchmark checkpoint, Final receipt requirements, Phase 7B acceptance, Scope and gates, Phase 7B requirement traceability

### Community 189 - "Phase 6 acceptance evidence"
Cohesion: 0.20
Nodes (7): Executed acceptance checkpoint, Independent MCP evidence, Limitations and deferred scope, Measured performance and bounds, Phase 6 acceptance evidence, Remote proof and final HEAD identity, Phase 6 traceability ledger

### Community 191 - "httpx"
Cohesion: 0.22
Nodes (7): test_clean_upgrade_downgrade_reupgrade_and_readiness(), test_retrospective_signed_csv_duplicates_and_analytics_identity(), test_sequence_overflow_is_dead_lettered_and_valid_edge_persists(), test_stream_poll_is_atomic_replay_safe_and_persists_provisional_findings(), main(), address(), command()

### Community 192 - "ADR 0018: Read-only MCP application adapter"
Cohesion: 0.17
Nodes (10): ADR 0016: Deterministic, immutable automotive analytics, Consequences, Decision, Status, ADR 0018: Read-only MCP application adapter, Alternatives, Consequences and risks, Context (+2 more)

### Community 193 - "Phase 2 session and pull analysis"
Cohesion: 0.40
Nodes (4): API and limits, Phase 2 session and pull analysis, Semantics, Synthetic validation

### Community 194 - "main.py"
Cohesion: 0.09
Nodes (10): agent_router(), audit(), stream(), RunAudit, ResourceBudgetMiddleware, ErrorDetail, ErrorResponse, DatabaseProbe (+2 more)

### Community 195 - "events/service.py"
Cohesion: 0.30
Nodes (5): DetectedEvent, EventSummary, analyze_session_events(), EventAnalysisLimitError, EventAnalysisService

### Community 196 - "45. Investigation examples"
Cohesion: 0.50
Nodes (4): 45. Investigation examples, Example A — repeated pull performance loss, Example B — change after intercooler, Example C — missing technical specification

### Community 197 - "Observed answers"
Cohesion: 0.05
Nodes (40): 2:A01:0 — representative, 2:A02:0 — representative, 2:A03:0 — representative, 2:A05:0 — ambiguous, 2:A06:0 — representative, 2:A09:0 — representative, 2:A10:0 — worst, 2:B04:0 — ambiguous (+32 more)

### Community 200 - "Phase 7A grounded agent"
Cohesion: 0.40
Nodes (5): Boundaries, Context and evidence, Execution and lifecycle, Phase 7A grounded agent, Provider and streaming contracts

### Community 203 - "Phase 4 — Streaming & Live Vehicle Acquisition"
Cohesion: 0.22
Nodes (8): Boundaries and flow, Broker storage and observed worker health, Explicit CSV mapping and live recovery, Failure and security model, Phase 4 — Streaming & Live Vehicle Acquisition, Recipes and quality, Retrospective execution guarantees, Safety and hardware status

### Community 204 - "Support"
Cohesion: 0.17
Nodes (11): AcquisitionCapabilitySource, fresh(), SourceCapabilitySnapshot, validated_report(), Support, PreflightRequest, test_preflight_blocks_supported_signals_with_inadequate_poll_budget(), test_registered_source_snapshot_preserves_preflight_provenance() (+3 more)

### Community 205 - "test_investigation_repository.py"
Cohesion: 0.36
Nodes (8): approved_plan(), item(), result_with(), test_claim_reanalysis_is_atomic_and_unique(), test_create_conflict_and_stale_update_fail_closed(), test_create_get_recent_update_and_replay(), test_session_link_context_guards_and_idempotence(), claim()

### Community 206 - "phase7d_eval.py"
Cohesion: 0.10
Nodes (17): atomic_json(), domain_fingerprint(), database_command(), Process, evaluate(), failure_kind(), identity(), main() (+9 more)

### Community 207 - "main"
Cohesion: 0.83
Nodes (4): main(), address(), command(), wait_for_telemetry_backends()

### Community 208 - "Grounded agent operation"
Cohesion: 0.50
Nodes (4): Failure handling, Grounded agent operation, Local configuration, Validation commands

### Community 209 - "Phase 7C acceptance"
Cohesion: 0.50
Nodes (4): Local and canonical validation, Phase 7C acceptance, Phase 7C receipts, Result

### Community 211 - "compute_pull_metrics"
Cohesion: 0.40
Nodes (3): compute_pull_metrics(), _mean(), _slope()

## Knowledge Gaps
- **22 isolated node(s):** `vehicle-platform-api`, `react-dom`, `typescript`, `@types/node`, `@types/react` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1769 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **60 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OpenAIProvider` connect `DeterministicProvider` to `main.py`, `AgentError`, `create_app`, `pytest`, `phase7d_eval.py`, `runtime.py`, `prompts/phase-7d-real-model-validation.md`, `test_agent_runtime.py`, `AgentSettings`, `datetime`, `StrictModel`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Are the 123 inferred relationships involving `AgentError` (e.g. with `EvidenceRegistry` and `InvestigationRepository`) actually correct?**
  _`AgentError` has 123 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vehicle-platform-api`, `react-dom`, `typescript` to the rest of the system?**
  _22 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `AnalyticsConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.08289536550406115 - nodes in this community are weakly interconnected._
- **Why does `Phase 7D real-model validation` connect `prompts/phase-7d-real-model-validation.md` to `DeterministicProvider`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `router()` (e.g. with `LoggingRecipe` and `AcquisitionAuthError`) actually correct?**
  _`router()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Should `router` be split into smaller, more focused modules?**
  _Cohesion score 0.09696969696969697 - nodes in this community are weakly interconnected._