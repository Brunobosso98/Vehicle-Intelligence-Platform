# Graph Report - Vehicle-Intelligence-Platform  (2026-10-13)

## Corpus Check
- 353 files · ~308,729 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: (none) 11, .Dockerfile 2, .example 1)

## Summary
- 3800 nodes · 10250 edges · 210 communities (150 shown, 60 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 1913 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d6bf6487`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AnalyticsConfig
- BoundedSpool
- dataclasses
- router
- api/routes.py
- SyntheticLiveAdapter
- acquisition/service.py
- RawTelemetryRecord
- Adapter
- test_investigation.py
- acquisition/cli.py
- MCPSettings
- AlignedFrame
- sqlalchemy
- register_errors
- CATEGORY H — ADVERSARIAL / SECURITY / UNCERTAINTY
- runtime.py
- seed_performance_recording
- datetime
- Phase 7C — Specialist Agents & Supervisor Orchestration
- web/package.json
- Phase 4 — Streaming & Live Vehicle Acquisition
- live-acquisition.tsx
- Phase 5 — Automotive Analytics
- register_tools
- generated/api.ts
- server.py
- metering.py
- telemetry/service.py
- Phase 7A — Agent Core & Grounded Orchestration
- CorrelationMiddleware
- agents/schemas.py
- status.test.tsx
- test_acquisition.py
- compilerOptions
- AgentError
- investigation/domain.py
- analytics-workspace.tsx
- InvestigationPlan
- next
- InvestigationService
- Elm327Adapter
- devDependencies
- telemetry.test.tsx
- test_phase7d_grading.py
- Supervisor
- package.json
- DeterministicProvider
- ADR 0018: Read-only MCP application adapter
- observability-validation.sh
- ReplayAdapter
- vehicle-workspace.tsx
- Phase 7B — Investigation & Adaptive Logging
- Telemetry
- test_agent_runtime.py
- 97. Phase 7C Definition of Done
- test_agents.py
- MappedCSVTelemetrySource
- test_phase7d_cli.py
- asyncio
- mcp-validation.sh
- Ledger
- README.md
- PHASE 0 COMPLETION REPORT
- MCPClient
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
- Observed answers
- 73. Definition of Done
- budgets.py
- Phase 7D — Real Model Validation & Agent Reliability Baseline
- Phases 0–5 retrospective hardening
- evaluate_mcp.py
- investigation/service.py
- Settings
- pull_request_template.md
- httpx
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
- Grounded agent operation
- Phase 3 event and anomaly engine
- 55. Required test layers
- pytest
- ADR 0012: Versioned deterministic session analysis
- ADR 0013: Deterministic evidence-first event architecture
- collector.py
- Envelope
- architecture/phase-6-mcp-tool-platform.md
- Phase 3 events
- 75. API surface
- 85. Unit and contract tests
- test_api.py
- SessionAnalysisService
- ResponseObserver
- Vehicle Intelligence Platform context
- SanitizingExporter
- phase7d.py
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
- temporal_checks
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
- test_elm_tcp_transport_connects_reads_reuses_and_closes
- infra/AGENTS.md
- contracts/AGENTS.md
- contracts/README.md
- SECURITY.md
- CATEGORY G — PHASE 7B / INSUFFICIENT EVIDENCE / ADAPTIVE LOGGING
- investigation/routes.py
- AgentRepository
- prompts/phase-7d-real-model-validation.md
- mcp/instrumentation.py
- ErrorCode
- Phase 4 acquisition threats
- scripts
- test_investigation_repository.py
- ADR 0019: Grounded agent state and evidence
- 98. Phase 7B Definition of Done
- Phase 1 vehicle and telemetry core
- @playwright/test
- json
- Phase 7B acceptance
- Phase 6 acceptance evidence
- Phase 7A grounded agent
- Catalog
- Phase 2 session and pull analysis
- load_suite
- .shutdown
- test_real_trace_metric_and_log_correlation
- 45. Investigation examples
- AcquisitionPublisher
- summarize
- phase-7d-traceability-ledger.md
- phase-7d-delivery.md
- create_app
- capabilities.py
- Phase 7C acceptance
- phase7d_eval.py
- main
- test_agent_repository.py

## God Nodes (most connected - your core abstractions)
1. `AgentError` - 217 edges
2. `Phase 4 — Streaming & Live Vehicle Acquisition` - 128 edges
3. `router()` - 126 edges
4. `Phase 5 — Automotive Analytics` - 115 edges
5. `Phase 7B — Investigation & Adaptive Logging` - 100 edges
6. `Phase 7C — Specialist Agents & Supervisor Orchestration` - 99 edges
7. `Settings` - 81 edges
8. `Telemetry` - 80 edges
9. `Phase 7A — Agent Core & Grounded Orchestration` - 75 edges
10. `DeterministicProvider` - 63 edges

## Surprising Connections (you probably didn't know these)
- `Boundaries and flow` --references--> `VehicleDataAdapter`  [INFERRED]
  docs/architecture/phase-4-live-acquisition.md → apps/api/src/vehicle_platform/acquisition/adapters.py
- `Behavioral requirements` --references--> `devices()`  [INFERRED]
  docs/validation/phases-0-5-traceability-ledger.md → apps/api/src/vehicle_platform/acquisition/cli.py
- `Collector heartbeat and acquisition context` --references--> `collector_health()`  [INFERRED]
  docs/architecture/phase-4-live-acquisition.md → apps/api/src/vehicle_platform/acquisition/quality.py
- `Execution and lifecycle` --references--> `AgentSettings`  [INFERRED]
  docs/architecture/phase-7a-grounded-agent.md → apps/api/src/vehicle_platform/agents/config.py
- `Domain and persistence` --references--> `InvestigationPlan`  [INFERRED]
  docs/architecture/phase-7b-investigation-adaptive-logging.md → apps/api/src/vehicle_platform/agents/investigation/domain.py

## Import Cycles
- None detected.

## Communities (210 total, 60 thin omitted)

### Community 0 - "AnalyticsConfig"
Cohesion: 0.08
Nodes (54): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+46 more)

### Community 1 - "BoundedSpool"
Cohesion: 0.15
Nodes (13): BoundedSpool, test_bounded_spool_replays_and_reports_overflow(), test_collector_interruption_preserves_unpublished_partial_batch(), read(), test_collector_rejects_unbounded_configuration(), test_collector_retries_spools_and_replays_without_loss(), available(), test_spool_acknowledges_only_after_publish_and_recovers_in_same_run() (+5 more)

### Community 2 - "dataclasses"
Cohesion: 0.08
Nodes (33): align_observations(), rolling_median(), compute_pull_metrics(), HeuristicPullDetector, HeuristicSegmentDetector, _mean(), PullDetector, SegmentDetector (+25 more)

### Community 3 - "router"
Cohesion: 0.08
Nodes (61): ErrorDetail, ErrorResponse, Health, Ready, Version, router(), analytics_config(), analyze_repeated_pulls() (+53 more)

### Community 4 - "api/routes.py"
Cohesion: 0.08
Nodes (43): AcquisitionBatchAccepted, AcquisitionCreate, AcquisitionCreated, AcquisitionFinalized, AcquisitionHeartbeat, AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement (+35 more)

### Community 5 - "SyntheticLiveAdapter"
Cohesion: 0.17
Nodes (11): SyntheticLiveAdapter, test_collector_capability_failure_closes_adapter(), test_collector_heartbeat_interruption_does_not_erase_samples(), test_collector_reports_capabilities_bounds_and_graceful_disconnect(), heartbeat(), test_extended_synthetic_modes_have_measured_behavior(), test_golden_synthetic_scenarios(), test_periodic_heartbeat_continues_while_adapter_waits() (+3 more)

### Community 6 - "acquisition/service.py"
Cohesion: 0.15
Nodes (13): assess_dataset(), collector_health(), DatasetCapability, measure_signal_quality(), SignalQuality, AcquisitionAuthError, AcquisitionError, AcquisitionService (+5 more)

### Community 7 - "RawTelemetryRecord"
Cohesion: 0.16
Nodes (10): AcquisitionCollector, RawTelemetryRecord, test_collector_reports_actual_recovery_metrics_and_payload_free_spans(), unavailable(), test_pending_spool_precedes_new_data_and_overflow_is_visible(), test_spool_replay_retries_and_only_acknowledges_success(), compose(), main() (+2 more)

### Community 8 - "Adapter"
Cohesion: 0.28
Nodes (5): Adapter, PlatformError, Warning, compare_configurations(), get_event()

### Community 9 - "test_investigation.py"
Cohesion: 0.19
Nodes (29): InvestigationStatus, SignalRole, MemoryInvestigations, need(), plan(), test_approval_rejects_changed_source_and_resumes_partial_approval(), test_approval_rejects_stale_capability_and_unready_plan(), test_cancel_and_reject_are_idempotent_only_at_exact_version() (+21 more)

### Community 10 - "acquisition/cli.py"
Cohesion: 0.22
Nodes (13): adapter_for(), AdapterKind, devices(), execute(), _preflight(), preflight_command(), probe(), recipes() (+5 more)

### Community 11 - "MCPSettings"
Cohesion: 0.12
Nodes (12): ReadTokenVerifier, MCPSettings, create_server(), pull(), session(), vehicle(), runtime(), test_all_tools_with_service_adapters() (+4 more)

### Community 12 - "AlignedFrame"
Cohesion: 0.08
Nodes (54): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, EventProfile, PullWindow (+46 more)

### Community 13 - "sqlalchemy"
Cohesion: 0.09
Nodes (11): run(), run_sync(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade() (+3 more)

### Community 14 - "register_errors"
Cohesion: 0.11
Nodes (14): AgentRequestBudgetMiddleware, register_errors(), agent_error(), http_error(), invalid(), unavailable(), unexpected(), response() (+6 more)

### Community 15 - "CATEGORY H — ADVERSARIAL / SECURITY / UNCERTAINTY"
Cohesion: 0.03
Nodes (61): 100. Optional Sol comparison, 101. Real-model grading, 102. Hard blockers / zero-tolerance metrics, 103. Routing quality, 104. Tool efficiency, 105. Grounding, 106. Causal restraint, 107. Diagnosis restraint (+53 more)

### Community 16 - "runtime.py"
Cohesion: 0.10
Nodes (39): Classification, Conflict, Intent, RoutingProposal, SpecialistDraft, SpecialistRequest, SpecialistResult, SupervisorReport (+31 more)

### Community 18 - "datetime"
Cohesion: 0.06
Nodes (33): StandardPid, RawTelemetryMessage, main(), StreamConsumer, StreamObservation, preview_csv_import(), DataQuality, NormalizationError (+25 more)

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
Cohesion: 0.12
Nodes (16): register_tools(), get_cross_session_analytics(), get_pull_summary(), get_repeated_pull_analysis(), get_session_analytics(), get_session_capabilities(), get_session_summary(), get_telemetry_window() (+8 more)

### Community 25 - "generated/api.ts"
Cohesion: 0.10
Nodes (23): AgentEvent, AgentRun, Audit, AgentRun, Investigation, InvestigationWorkspace(), terminal, Report (+15 more)

### Community 26 - "server.py"
Cohesion: 0.11
Nodes (11): Window, test_adapter_isolation_and_envelope(), test_analytics_selection_reports_truncation(), test_http_requires_token(), test_instrumented_errors(), test_limited_quality_does_not_claim_missing_history(), test_network_config_rejected(), test_read_only_database_setup() (+3 more)

### Community 27 - "metering.py"
Cohesion: 0.22
Nodes (10): connect(), EvidenceClient, MeteredClient, ToolMeter, source(), test_evaluation_factory_wraps_the_actual_connect_seam(), test_meter_covers_phase7b_reads_and_preserves_safe_hashes(), test_single_telemetry_window_and_failed_reads_are_measured() (+2 more)

### Community 28 - "telemetry/service.py"
Cohesion: 0.21
Nodes (6): ImportResult, LiveOBDSource, TelemetrySource, _content_hash(), IngestionService, validate_vehicle_context()

### Community 29 - "Phase 7A — Agent Core & Grounded Orchestration"
Cohesion: 0.03
Nodes (72): 10. Agent state, 11. AgentRun persistence, 12. ToolCall persistence / audit trail, 13. Evidence model, 14. Claim → Evidence grounding, 15. Unsupported-claim detection, 16. Structured answer contract, 17. Natural-language API (+64 more)

### Community 31 - "agents/schemas.py"
Cohesion: 0.06
Nodes (28): redact_data(), EvidenceRegistry, AgentInstrumentation, Provider, TerminableConnection, agent_router(), audit(), stream() (+20 more)

### Community 32 - "status.test.tsx"
Cohesion: 0.17
Nodes (15): dynamic, GET(), Home(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready (+7 more)

### Community 33 - "test_acquisition.py"
Cohesion: 0.08
Nodes (13): test_collector_health_distinguishes_transport_and_sampling(), test_consumer_database_failure_exits_without_sql_inputs(), fail(), test_gateway_heartbeat_is_scoped_and_failures_are_explicit(), post(), test_gateway_publisher_classifies_responses(), test_gateway_transport_errors_enter_retry_spool_path(), test_heartbeat_rejects_naive_or_prestart_sample_receipt() (+5 more)

### Community 34 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 35 - "AgentError"
Cohesion: 0.14
Nodes (15): AgentSettings, Orchestrator, AgentError, ScriptedProvider, GraphState, test_provider_missing_configuration(), test_context_and_capability_bounds(), test_measured_tool_reuses_validated_pull_but_loads_missing_capability() (+7 more)

### Community 36 - "investigation/domain.py"
Cohesion: 0.15
Nodes (18): validated_report(), DeviceCapabilities, Support, Availability, Feasibility, InvestigationError, RecipeReference, Resolution (+10 more)

### Community 37 - "analytics-workspace.tsx"
Cohesion: 0.14
Nodes (13): AnalyticsWorkspace(), history(), Configuration, curveLabels, HistoricalTrend(), NormalizedBin, NormalizedCurves(), Profile (+5 more)

### Community 38 - "InvestigationPlan"
Cohesion: 0.20
Nodes (4): InvestigationEvent, InvestigationPlan, InvestigationInstrumentation, InvestigationRepository

### Community 39 - "next"
Cohesion: 0.18
Nodes (5): config, GET, POST, metadata, next

### Community 40 - "InvestigationService"
Cohesion: 0.16
Nodes (12): Approval, CapabilitySnapshot, InvestigationService, PreflightRequest, test_create_closes_provider_after_invalid_semantic_output(), test_create_rejects_invalid_identity_capacity_and_sufficient_answer(), test_create_timeout_maps_to_bounded_public_error(), test_followup_watcher_reconciles_and_logs_failure_without_leaking() (+4 more)

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
Cohesion: 0.33
Nodes (14): grade(), case(), public_run(), test_absent_failed_answer_does_not_fabricate_a_factual_violation(), test_failed_forbidden_attempts_and_successful_bypass_are_separate(), test_forged_public_outputs_are_never_passes(), test_independent_numeric_grading_and_safe_fast_path(), test_missing_specialists_insufficiency_tools_and_recipe_fail() (+6 more)

### Community 45 - "Supervisor"
Cohesion: 0.11
Nodes (38): accumulate(), Specialist, Sufficiency, Usage, Supervisor, test_usage_unavailable_stays_unavailable(), runtime(), call() (+30 more)

### Community 46 - "package.json"
Cohesion: 0.11
Nodes (17): devDependencies, openapi-typescript, prettier, engines, node, name, packageManager, private (+9 more)

### Community 47 - "DeterministicProvider"
Cohesion: 0.09
Nodes (25): InvestigationProposal, ProposedGap, ProposedHypothesis, draft_schema(), OpenAIProvider, turn_data(), ModelInput, ModelTurn (+17 more)

### Community 48 - "ADR 0018: Read-only MCP application adapter"
Cohesion: 0.17
Nodes (10): ADR 0016: Deterministic, immutable automotive analytics, Consequences, Decision, Status, ADR 0018: Read-only MCP application adapter, Alternatives, Consequences and risks, Context (+2 more)

### Community 49 - "observability-validation.sh"
Cohesion: 0.40
Nodes (3): observability-validation.sh script, wait_prometheus_query(), stack-smoke.sh script

### Community 50 - "ReplayAdapter"
Cohesion: 0.22
Nodes (7): ReplayAdapter, run(), GatewayPublisher, test_replay_is_deterministic(), test_replay_skips_unplanned_signal_without_sleep(), dataset(), main()

### Community 51 - "vehicle-workspace.tsx"
Cohesion: 0.16
Nodes (15): AgentWorkspace(), loadRun(), observe(), submit(), DetectedEvent, json(), Pull, Segment (+7 more)

### Community 52 - "Phase 7B — Investigation & Adaptive Logging"
Cohesion: 0.02
Nodes (98): 10. Investigation taxonomy, 11. Evidence gap model, 12. Reuse Phase 7A missing-evidence categories, 13. SignalNeed abstraction, 14. No invented channels, 15. Capability resolver, 16. Session capability vs hardware/source capability, 17. Existing-data-first policy (+90 more)

### Community 53 - "Telemetry"
Cohesion: 0.06
Nodes (14): Database, DatabaseProbe, DependencyUnavailable, Terminable, Telemetry, QueryService, test_extension_required(), test_otlp_configured() (+6 more)

### Community 54 - "test_agent_runtime.py"
Cohesion: 0.08
Nodes (25): failure_category(), request(), ResponseStream, service_fixture(), event(), finish(), get(), replay() (+17 more)

### Community 55 - "97. Phase 7C Definition of Done"
Cohesion: 0.14
Nodes (14): 97. Phase 7C Definition of Done, API/UI/SSE, Conflicts, Data quality, Delivery, Evidence, Observability/performance, Parallelism (+6 more)

### Community 56 - "test_agents.py"
Cohesion: 0.12
Nodes (34): at(), effective(), resolve_context(), canonical_hash(), facts(), render_binding(), validate(), comparison() (+26 more)

### Community 57 - "MappedCSVTelemetrySource"
Cohesion: 0.17
Nodes (18): MappedCSVTelemetrySource, mapping(), test_absent_mapping_and_invalid_headers_are_rejected(), test_explicit_identity_sequence_are_preserved(), test_explicit_wide_csv_mapping_preserves_units_time_and_provenance(), test_header_inspection_rejects_missing_ambiguous_or_oversized_csv(), test_invalid_identity_or_sequence_is_rejected(), test_mapped_records_reject_nonfinite_naive_formula_and_bad_shapes() (+10 more)

### Community 59 - "test_phase7d_cli.py"
Cohesion: 0.13
Nodes (13): Rates, cli(), test_affected_selection_cannot_change_smoke_or_report(), test_exactly_one_smoke_exercises_real_adapter_without_network(), test_first_smoke_request_normalizes_sdk_auth_error_without_key(), test_interrupted_smoke_is_not_automatically_repeated(), test_invalid_affected_selection_sends_no_paid_calls(), test_operator_extra_requires_explicit_confirmed_eval_mode() (+5 more)

### Community 60 - "asyncio"
Cohesion: 0.19
Nodes (8): main(), buffered_points(), canonical_counts(), main(), memory_snapshot(), worker_metrics(), main(), main()

### Community 61 - "mcp-validation.sh"
Cohesion: 0.25
Nodes (6): DATABASE_URL, ENVIRONMENT, MCP_TEST_PROJECT, mcp-validation.sh script, TEST_DATABASE_URL, TEST_KAFKA_PORT

### Community 62 - "Ledger"
Cohesion: 0.32
Nodes (3): atomic_json(), Ledger, test_receipts_do_not_accept_missing_usage_as_free()

### Community 63 - "README.md"
Cohesion: 0.09
Nodes (16): Contributing, Phase 7C specialist agents and supervisor, System context, Toolchain selection, Local development, Current phase, Phase 7C implementation, Roadmap (+8 more)

### Community 64 - "PHASE 0 COMPLETION REPORT"
Cohesion: 0.11
Nodes (19): ADRs created, Applications, Architecture, CI/CD, Closure rerun result, Codex context, Database, Deferred deliberately to Phase 1+ (+11 more)

### Community 65 - "MCPClient"
Cohesion: 0.14
Nodes (9): MCPClient, ReadOnlyDatabase, test_real_database_agent_lifecycle_failure_recovery_and_audit(), connection(), test_supervisor_snapshot_versions_and_durable_events(), connection(), client(), test_database_abort_invalidated_connection() (+1 more)

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

### Community 95 - "Observed answers"
Cohesion: 0.05
Nodes (39): 2:A01:0 — representative, 2:A02:0 — representative, 2:A03:0 — representative, 2:A05:0 — ambiguous, 2:A06:0 — representative, 2:A09:0 — representative, 2:A10:0 — worst, 2:B04:0 — ambiguous (+31 more)

### Community 96 - "73. Definition of Done"
Cohesion: 0.17
Nodes (12): 73. Definition of Done, API/UI, Architecture, Delivery, Grounding, Observability, Orchestration, Performance (+4 more)

### Community 97 - "budgets.py"
Cohesion: 0.12
Nodes (11): ResourceBudgetMiddleware, TokenBucket, request_scope(), test_bucket_burst_refill_and_long_idle_never_exceed_capacity(), test_concurrency_bounds_require_positive_limits(), test_concurrency_rejects_excess_and_releases_after_cancel(), app(), receive() (+3 more)

### Community 98 - "Phase 7D — Real Model Validation & Agent Reliability Baseline"
Cohesion: 0.13
Nodes (15): 10. No hidden real calls in normal CI, 11. Evaluation dataset design, 12. Suite size, 13. Category distribution, 1. Repository / branch / baseline, 2. Phase 7C closure status, 3. Phase 7D purpose, 4. Primary model choice (+7 more)

### Community 99 - "Phases 0–5 retrospective hardening"
Cohesion: 0.06
Nodes (29): ADR 0014: Kafka durable acquisition stream, Consequences, Context, Decision, ADR 0017: Retrospective evidence and execution identity, Alternatives, Consequences and risks, Context (+21 more)

### Community 100 - "evaluate_mcp.py"
Cohesion: 0.10
Nodes (10): evaluate(), main(), evaluate(), error(), main(), main(), ready_endpoint(), fingerprint() (+2 more)

### Community 101 - "investigation/service.py"
Cohesion: 0.13
Nodes (31): EvidenceGap, GapStatus, GapType, Hypothesis, HypothesisCategory, HypothesisStatus, InvestigationOutcome, ExistingEvidence (+23 more)

### Community 102 - "Settings"
Cohesion: 0.12
Nodes (9): Settings, test_build_timestamp_normalized_to_utc(), test_empty_optional_container_metadata(), test_invalid_settings(), test_malformed_database_config(), test_required_database(), test_safe_metadata(), test_tls_mode_must_match_exactly() (+1 more)

### Community 103 - "pull_request_template.md"
Cohesion: 0.22
Nodes (8): Database/contract impact, Documentation, How it was validated, Observability impact, Risks, Security impact, What changed, Why

### Community 104 - "httpx"
Cohesion: 0.14
Nodes (12): main(), finalized_fixture(), evaluate(), score_claims(), main(), address(), command(), wait_for_telemetry_backends() (+4 more)

### Community 105 - "preflight"
Cohesion: 0.20
Nodes (13): Importance, LoggingRecipe, plan_sampling(), preflight(), PreflightResult, Priority, Readiness, SignalRequirement (+5 more)

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

### Community 123 - "pytest"
Cohesion: 0.09
Nodes (39): InvestigationInput, enforce_tool(), SpecialistPolicy, tools_for(), url(), url(), storage(), provider() (+31 more)

### Community 124 - "ADR 0012: Versioned deterministic session analysis"
Cohesion: 0.33
Nodes (5): ADR 0012: Versioned deterministic session analysis, Alternatives, Consequences and risks, Context, Decision

### Community 125 - "ADR 0013: Deterministic evidence-first event architecture"
Cohesion: 0.33
Nodes (5): ADR 0013: Deterministic evidence-first event architecture, Alternatives, Consequences and risks, Context, Decision

### Community 126 - "collector.py"
Cohesion: 0.12
Nodes (6): ElmTransport, VehicleDataAdapter, report(), report_periodically(), CollectorStats, SamplingPlanItem

### Community 127 - "Envelope"
Cohesion: 0.27
Nodes (9): Instrumentation, Envelope, call(), test_actual_response_limit_and_unknown_tool(), big(), test_timeout_size_rate_and_spans(), delayed(), large() (+1 more)

### Community 128 - "architecture/phase-6-mcp-tool-platform.md"
Cohesion: 0.10
Nodes (16): Component model, CURRENT, FUTURE, Phase 6 MCP tool platform, Resources, Safety and errors, Approval and follow-up, Domain and persistence (+8 more)

### Community 129 - "Phase 3 events"
Cohesion: 0.22
Nodes (8): Grounded agent, Investigation and adaptive logging, MCP, Observability, Phase 2 analysis, Phase 3 events, Phase 7C supervisor, Retrospective instrumentation checks

### Community 130 - "75. API surface"
Cohesion: 0.33
Nodes (6): 75. API surface, Acquisition, Ingestion, Live client, Logging objectives, Recipes

### Community 131 - "85. Unit and contract tests"
Cohesion: 0.33
Nodes (6): 85. Unit and contract tests, Collector, Live analysis, Recipes, Sampling, Stream

### Community 132 - "test_api.py"
Cohesion: 0.18
Nodes (8): Probe, test_live_independent_and_ready(), test_logging_recipe_and_preflight_contracts(), test_non_ascii_correlation_header_is_regenerated(), test_otlp_http_delivers_real_request_span(), test_unexpected_exception_sanitized(), test_unknown_methods_do_not_expand_metric_cardinality(), test_validation_handler()

### Community 133 - "SessionAnalysisService"
Cohesion: 0.35
Nodes (5): AnalysisLimitError, SessionAnalysisService, AnalysisResult, Pull, SessionSegment

### Community 135 - "Vehicle Intelligence Platform context"
Cohesion: 0.40
Nodes (4): Business Logic & Feature Map, Directory Structure Map, Validation, Vehicle Intelligence Platform context

### Community 136 - "SanitizingExporter"
Cohesion: 0.18
Nodes (4): SanitizingExporter, test_database_error_propagation_cannot_leak_through_parent_spans(), test_database_trace_export_redacts_driver_inputs(), test_sql_text_is_removed_from_non_database_successful_spans()

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
Cohesion: 0.30
Nodes (5): accepted(), load_exceptions(), load_findings(), main(), parse_args()

### Community 148 - "temporal_checks"
Cohesion: 0.20
Nodes (9): expected_statement(), temporal_checks(), effective(), timestamp(), Collector CLI guarantees, Live acquisition operations and physical validation, Preserve an older Kafka storage path, Safe physical Vgate validation procedure (+1 more)

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

### Community 173 - "CATEGORY G — PHASE 7B / INSUFFICIENT EVIDENCE / ADAPTIVE LOGGING"
Cohesion: 0.18
Nodes (11): 74. G01, 75. G02, 76. G03, 77. G04, 78. G05, 79. G06, 80. G07, 81. G08 (+3 more)

### Community 174 - "investigation/routes.py"
Cohesion: 0.08
Nodes (9): ApprovalRequest, CreateInvestigation, investigation_router(), stream(), LinkSessionRequest, RegisterSourcePreflight, VersionRequest, test_investigation_api_requires_operator_token() (+1 more)

### Community 176 - "prompts/phase-7d-real-model-validation.md"
Cohesion: 0.15
Nodes (10): ADR 0022: Bounded real-model evaluation and durable spend accounting, Alternatives, Consequences and risks, Context, Decision, Evidence-driven hardening, Status, Hardening from partial real observations (+2 more)

### Community 177 - "mcp/instrumentation.py"
Cohesion: 0.17
Nodes (3): main(), HTTPInstrumentation, test_http_trace_context_and_auth_rejections()

### Community 178 - "ErrorCode"
Cohesion: 0.16
Nodes (4): ErrorCode, tool_error(), call(), SafeMCPServer

### Community 179 - "Phase 4 acquisition threats"
Cohesion: 0.33
Nodes (6): Original Phase 4 local resource budgets, Phase 4 acquisition threats, Phase 6 MCP boundary, Phase 7A agent boundary, Phase 7B investigation and adaptive logging, Phase 7C supervisor and specialists

### Community 180 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 181 - "test_investigation_repository.py"
Cohesion: 0.27
Nodes (10): approved_plan(), item(), result_with(), storage(), session(), test_claim_reanalysis_is_atomic_and_unique(), test_create_conflict_and_stale_update_fail_closed(), test_create_get_recent_update_and_replay() (+2 more)

### Community 182 - "ADR 0019: Grounded agent state and evidence"
Cohesion: 0.08
Nodes (22): blocked(), ADR 0015: Versioned recipes and acquisition lifecycle, Consequences, Decision, ADR 0019: Grounded agent state and evidence, Alternatives, Consequences and risks, Context (+14 more)

### Community 183 - "98. Phase 7B Definition of Done"
Cohesion: 0.15
Nodes (13): 98. Phase 7B Definition of Done, Acquisition / follow-up, API / UI, Approval, Delivery, Existing evidence, Investigation domain, Logging plan (+5 more)

### Community 184 - "Phase 1 vehicle and telemetry core"
Cohesion: 0.40
Nodes (4): Canonical import contract, Performance baseline protocol, Phase 1 vehicle and telemetry core, Query and operations

### Community 187 - "json"
Cohesion: 0.11
Nodes (16): main(), seed_agent(), main(), main(), ask(), runtime(), main(), main() (+8 more)

### Community 188 - "Phase 7B acceptance"
Cohesion: 0.29
Nodes (5): Benchmark checkpoint, Final receipt requirements, Phase 7B acceptance, Scope and gates, Phase 7B requirement traceability

### Community 189 - "Phase 6 acceptance evidence"
Cohesion: 0.20
Nodes (7): Executed acceptance checkpoint, Independent MCP evidence, Limitations and deferred scope, Measured performance and bounds, Phase 6 acceptance evidence, Remote proof and final HEAD identity, Phase 6 traceability ledger

### Community 190 - "Phase 7A grounded agent"
Cohesion: 0.40
Nodes (5): Boundaries, Context and evidence, Execution and lifecycle, Phase 7A grounded agent, Provider and streaming contracts

### Community 192 - "Phase 2 session and pull analysis"
Cohesion: 0.40
Nodes (4): API and limits, Phase 2 session and pull analysis, Semantics, Synthetic validation

### Community 193 - "load_suite"
Cohesion: 0.29
Nodes (6): load_suite(), test_identity_requires_clean_exact_commit(), test_projection_calibration_requires_full_attempted_schedule(), test_exact_versioned_dataset_and_fixed_schedule(), test_versioned_questions_match_the_authoritative_specification(), observed_role_turns()

### Community 194 - ".shutdown"
Cohesion: 0.25
Nodes (4): test_non_http_passthrough(), test_phase3_metrics_use_only_bounded_labels(), test_phase4_metrics_use_only_bounded_labels(), telemetry()

### Community 195 - "test_real_trace_metric_and_log_correlation"
Cohesion: 0.28
Nodes (3): JSONFormatter, test_json_logs_do_not_render_exception_secrets(), test_real_trace_metric_and_log_correlation()

### Community 196 - "45. Investigation examples"
Cohesion: 0.50
Nodes (4): 45. Investigation examples, Example A — repeated pull performance loss, Example B — change after intercooler, Example C — missing technical specification

### Community 200 - "summarize"
Cohesion: 0.25
Nodes (7): summarize(), test_aggregation_stability_unknown_usage_and_review_shortlist(), test_empty_report_never_implies_observed_safety_or_validation(), test_per_case_cost_keeps_prior_rounds_smoke_and_unknown_reservations(), test_report_applies_the_specified_thresholds_without_requiring_perfect_routes(), test_skipped_observations_are_not_counted_as_real_executions(), test_unrun_cases_do_not_change_observed_quality_rates()

### Community 203 - "create_app"
Cohesion: 0.17
Nodes (8): create_app(), test_clean_upgrade_downgrade_reupgrade_and_readiness(), test_expired_acquisition_releases_capacity_without_accepting_its_token(), test_retrospective_signed_csv_duplicates_and_analytics_identity(), test_sequence_overflow_is_dead_lettered_and_valid_edge_persists(), test_stream_poll_is_atomic_replay_safe_and_persists_provisional_findings(), test_openapi_schema(), test_real_app_lifespan()

### Community 204 - "capabilities.py"
Cohesion: 0.15
Nodes (11): AcquisitionCapabilitySource, fresh(), SourceCapabilitySnapshot, query_row(), report(), source(), test_latest_prefers_newer_registered_report(), test_latest_rejects_stale_and_disconnected_reports() (+3 more)

### Community 205 - "Phase 7C acceptance"
Cohesion: 0.50
Nodes (4): Local and canonical validation, Phase 7C acceptance, Phase 7C receipts, Result

### Community 206 - "phase7d_eval.py"
Cohesion: 0.09
Nodes (18): domain_fingerprint(), database_command(), free_port(), Process, database_command(), evaluate(), failure_kind(), identity() (+10 more)

### Community 207 - "main"
Cohesion: 0.83
Nodes (4): main(), address(), command(), wait_for_telemetry_backends()

### Community 213 - "test_agent_repository.py"
Cohesion: 0.23
Nodes (9): rows(), test_database_errors_are_normalized_and_session_closes(), test_interrupted_run_reconciliation_is_bounded_and_terminal(), test_missing_driver_fails_closed(), test_repository_not_found_and_bounds(), test_repository_run_audit_and_stream_serialization(), test_stale_retrieval_refreshes_reconciled_state(), test_watchdog_bounds_unresponsive_cancellation_cleanup() (+1 more)

## Knowledge Gaps
- **22 isolated node(s):** `vehicle-platform-api`, `react-dom`, `typescript`, `@types/node`, `@types/react` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1766 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **60 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentError` connect `AgentError` to `test_investigation.py`, `phase7d.py`, `register_errors`, `runtime.py`, `metering.py`, `agents/schemas.py`, `InvestigationPlan`, `InvestigationService`, `Supervisor`, `DeterministicProvider`, `AgentRepository`, `Telemetry`, `test_agent_runtime.py`, `test_investigation_repository.py`, `test_agents.py`, `test_phase7d_cli.py`, `Ledger`, `MCPClient`, `load_suite`, `phase7d_eval.py`, `test_agent_repository.py`, `investigation/service.py`, `httpx`, `pytest`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 121 inferred relationships involving `AgentError` (e.g. with `EvidenceRegistry` and `InvestigationRepository`) actually correct?**
  _`AgentError` has 121 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vehicle-platform-api`, `react-dom`, `typescript` to the rest of the system?**
  _22 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `AnalyticsConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.08289536550406115 - nodes in this community are weakly interconnected._
- **Why does `OpenAIProvider` connect `DeterministicProvider` to `AgentError`, `ResponseObserver`, `create_app`, `Supervisor`, `phase7d_eval.py`, `runtime.py`, `prompts/phase-7d-real-model-validation.md`, `Telemetry`, `pytest`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `router()` (e.g. with `LoggingRecipe` and `AcquisitionAuthError`) actually correct?**
  _`router()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Should `BoundedSpool` be split into smaller, more focused modules?**
  _Cohesion score 0.14814814814814814 - nodes in this community are weakly interconnected._