# Graph Report - Vehicle-Intelligence-Platform  (2026-10-14)

## Corpus Check
- 358 files · ~318,614 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: (none) 11, .Dockerfile 2, .example 1)

## Summary
- 3883 nodes · 10537 edges · 219 communities (160 shown, 59 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 2002 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `140d21e2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AnalyticsConfig
- test_acquisition.py
- test_quality_observation_bindings.py
- router
- api/routes.py
- test_collector_heartbeat_interruption_does_not_erase_samples
- acquisition/service.py
- RawTelemetryRecord
- Envelope
- test_investigation.py
- acquisition/cli.py
- Adapter
- AlignedFrame
- sqlalchemy
- datetime
- CATEGORY H — ADVERSARIAL / SECURITY / UNCERTAINTY
- runtime.py
- dataclasses
- MappedCSVTelemetrySource
- Phase 7C — Specialist Agents & Supervisor Orchestration
- web/package.json
- Phase 4 — Streaming & Live Vehicle Acquisition
- live-acquisition.tsx
- Phase 5 — Automotive Analytics
- register_tools
- generated/api.ts
- evaluate_supervisor.py
- test_agent_repository.py
- telemetry/service.py
- Phase 7A — Agent Core & Grounded Orchestration
- Telemetry
- DetectorProfile
- status.test.tsx
- mapping.py
- compilerOptions
- agents/schemas.py
- AnalyticsService
- analytics-workspace.tsx
- InvestigationPlan
- next
- Settings
- Elm327Adapter
- devDependencies
- telemetry.test.tsx
- test_phase7d_grading.py
- DeterministicProvider
- package.json
- ModelInput
- MCP server
- observability-validation.sh
- test_gateway_publisher_classifies_responses
- vehicle-workspace.tsx
- Phase 7B — Investigation & Adaptive Logging
- api/contracts.py
- test_agent_runtime.py
- 97. Phase 7C Definition of Done
- test_agents.py
- pytest
- AgentSettings
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
- capabilities.py
- 73. Definition of Done
- test_database.py
- Phase 7D — Real Model Validation & Agent Reliability Baseline
- Phases 0–5 retrospective hardening
- evaluate_mcp.py
- investigation/service.py
- create_app
- pull_request_template.md
- agent_router
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
- telemetry.py
- Phase 3 event and anomaly engine
- 55. Required test layers
- test_phase7d_harness.py
- ADR 0012: Versioned deterministic session analysis
- ADR 0013: Deterministic evidence-first event architecture
- .run
- Ledger
- mcp/database.py
- Phase 3 events
- 75. API surface
- 85. Unit and contract tests
- server.py
- worker.py
- EventEngine
- Vehicle Intelligence Platform context
- SyntheticTelemetrySource
- Phase 7D real evaluation report
- 94. Failure behavior
- architecture/phase-7b-investigation-adaptive-logging.md
- adr.md
- migrations.md
- definition-of-done.md
- gates.md
- CATEGORY A — FACTUAL / FAST-PATH
- CATEGORY B — PERFORMANCE
- CATEGORY C — THERMAL
- security-policy.py
- prompts/phase-7d-real-model-validation.md
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
- investigation/routes.py
- AgentRun
- ADR 0022: Bounded real-model evaluation and durable spend accounting
- mcp/cli.py
- main.py
- architecture/phase-7c-specialist-agents-supervisor.md
- scripts
- ADR 0018: Read-only MCP application adapter
- ADR 0019: Grounded agent state and evidence
- 98. Phase 7B Definition of Done
- Phase 1 vehicle and telemetry core
- @playwright/test
- httpx
- Phase 7B acceptance
- mcp_client.py
- api/errors.py
- DeviceCapabilities
- SessionAnalysisService
- Phase 2 session and pull analysis
- budgets.py
- test_acquisition_capabilities.py
- 45. Investigation examples
- Observed answers
- Catalog
- ADR 0023: Scoped collection evidence and consistent evidence gaps
- phase-7d-delivery.md
- Phase 4 — Streaming & Live Vehicle Acquisition
- AgentError
- test_investigation_repository.py
- phase7d_eval.py
- core/config.py
- ReplayAdapter
- CaptureProvider
- Phase 6 acceptance evidence
- fixture
- resolve_context
- test_gateway_heartbeat_is_scoped_and_failures_are_explicit
- load_suite
- LiveOBDSource
- seed_performance_recording
- evaluate_agent_grounding.py

## God Nodes (most connected - your core abstractions)
1. `AgentError` - 224 edges
2. `Phase 4 — Streaming & Live Vehicle Acquisition` - 128 edges
3. `router()` - 126 edges
4. `Phase 5 — Automotive Analytics` - 115 edges
5. `Phase 7B — Investigation & Adaptive Logging` - 100 edges
6. `Phase 7C — Specialist Agents & Supervisor Orchestration` - 99 edges
7. `Settings` - 81 edges
8. `Telemetry` - 80 edges
9. `Phase 7A — Agent Core & Grounded Orchestration` - 75 edges
10. `DeterministicProvider` - 67 edges

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

## Communities (219 total, 59 thin omitted)

### Community 0 - "AnalyticsConfig"
Cohesion: 0.09
Nodes (51): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+43 more)

### Community 1 - "test_acquisition.py"
Cohesion: 0.12
Nodes (19): BoundedSpool, test_bounded_spool_replays_and_reports_overflow(), test_collector_health_distinguishes_transport_and_sampling(), test_collector_interruption_preserves_unpublished_partial_batch(), read(), test_collector_rejects_unbounded_configuration(), test_collector_retries_spools_and_replays_without_loss(), available() (+11 more)

### Community 2 - "test_quality_observation_bindings.py"
Cohesion: 0.44
Nodes (7): Finding, quality_observation_bindings(), observation(), test_quality_event_identity_is_not_duplicated(), test_quality_gap_details_preserve_event_identity_and_recorded_values(), test_quality_synthesis_excludes_unsupported_mechanical_details(), test_quality_synthesis_rejects_mechanical_events_and_unrelated_source_tools()

### Community 3 - "router"
Cohesion: 0.10
Nodes (56): router(), analytics_config(), analyze_repeated_pulls(), analyze_session(), analyze_session_events(), assess_session_capabilities(), bearer(), build_vehicle_baseline() (+48 more)

### Community 4 - "api/routes.py"
Cohesion: 0.08
Nodes (36): AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement, AnalysisRequest, AnalyticsRequest, CollectorHealthResponse, ConfigurationCreate, CSVImportPreview (+28 more)

### Community 5 - "test_collector_heartbeat_interruption_does_not_erase_samples"
Cohesion: 0.16
Nodes (7): test_collector_capability_failure_closes_adapter(), test_collector_heartbeat_interruption_does_not_erase_samples(), test_collector_reports_capabilities_bounds_and_graceful_disconnect(), heartbeat(), test_periodic_heartbeat_continues_while_adapter_waits(), read(), publish()

### Community 6 - "acquisition/service.py"
Cohesion: 0.16
Nodes (16): assess_dataset(), collector_health(), SignalQuality, AcquisitionAuthError, AcquisitionError, AcquisitionService, token_hash(), AcquisitionBatch (+8 more)

### Community 7 - "RawTelemetryRecord"
Cohesion: 0.16
Nodes (11): AcquisitionCollector, RawTelemetryMessage, RawTelemetryRecord, test_collector_reports_actual_recovery_metrics_and_payload_free_spans(), unavailable(), test_pending_spool_precedes_new_data_and_overflow_is_visible(), test_spool_replay_retries_and_only_acknowledges_success(), test_stream_contract_and_dataset_capability() (+3 more)

### Community 8 - "Envelope"
Cohesion: 0.18
Nodes (9): Envelope, Warning, Window, test_actual_response_limit_and_unknown_tool(), big(), test_timeout_size_rate_and_spans(), delayed(), large() (+1 more)

### Community 9 - "test_investigation.py"
Cohesion: 0.20
Nodes (31): Support, InvestigationStatus, SignalRole, MemoryInvestigations, need(), plan(), test_approval_rejects_changed_source_and_resumes_partial_approval(), test_approval_rejects_stale_capability_and_unready_plan() (+23 more)

### Community 10 - "acquisition/cli.py"
Cohesion: 0.18
Nodes (14): adapter_for(), AdapterKind, devices(), execute(), _preflight(), preflight_command(), probe(), recipes() (+6 more)

### Community 11 - "Adapter"
Cohesion: 0.07
Nodes (31): Adapter, ReadTokenVerifier, MCPSettings, ReadOnlyDatabase, create_server(), pull(), session(), vehicle() (+23 more)

### Community 12 - "AlignedFrame"
Cohesion: 0.16
Nodes (24): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, EventProfile, PullWindow (+16 more)

### Community 13 - "sqlalchemy"
Cohesion: 0.10
Nodes (9): upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade() (+1 more)

### Community 14 - "datetime"
Cohesion: 0.09
Nodes (7): StandardPid, Case, parse_timestamp(), sample_id(), SignalDefinition, main(), dataset()

### Community 15 - "CATEGORY H — ADVERSARIAL / SECURITY / UNCERTAINTY"
Cohesion: 0.03
Nodes (61): 100. Optional Sol comparison, 101. Real-model grading, 102. Hard blockers / zero-tolerance metrics, 103. Routing quality, 104. Tool efficiency, 105. Grounding, 106. Causal restraint, 107. Diagnosis restraint (+53 more)

### Community 16 - "runtime.py"
Cohesion: 0.06
Nodes (57): accumulate(), Classification, Conflict, Intent, RoutingDecision, RoutingProposal, SpecialistDraft, SpecialistFinding (+49 more)

### Community 17 - "dataclasses"
Cohesion: 0.13
Nodes (14): compute_pull_metrics(), HeuristicSegmentDetector, _mean(), PullDetector, SegmentDetector, _slope(), DetectedPull, DetectedSegment (+6 more)

### Community 18 - "MappedCSVTelemetrySource"
Cohesion: 0.44
Nodes (9): MappedCSVTelemetrySource, mapping(), test_absent_mapping_and_invalid_headers_are_rejected(), test_explicit_identity_sequence_are_preserved(), test_explicit_wide_csv_mapping_preserves_units_time_and_provenance(), test_header_inspection_rejects_missing_ambiguous_or_oversized_csv(), test_invalid_identity_or_sequence_is_rejected(), test_mapped_records_reject_nonfinite_naive_formula_and_bad_shapes() (+1 more)

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
Nodes (20): PlatformError, call(), register_tools(), compare_configurations(), get_cross_session_analytics(), get_event(), get_pull_summary(), get_repeated_pull_analysis() (+12 more)

### Community 25 - "generated/api.ts"
Cohesion: 0.10
Nodes (23): AgentEvent, AgentRun, Audit, AgentRun, Investigation, InvestigationWorkspace(), terminal, Report (+15 more)

### Community 26 - "evaluate_supervisor.py"
Cohesion: 0.26
Nodes (6): finalized_fixture(), evaluate(), score_claims(), fault_scenarios(), follow_up(), score_execution()

### Community 27 - "test_agent_repository.py"
Cohesion: 0.26
Nodes (9): rows(), test_database_errors_are_normalized_and_session_closes(), test_interrupted_run_reconciliation_is_bounded_and_terminal(), test_missing_driver_fails_closed(), test_repository_not_found_and_bounds(), test_repository_run_audit_and_stream_serialization(), test_stale_retrieval_refreshes_reconciled_state(), test_watchdog_bounds_unresponsive_cancellation_cleanup() (+1 more)

### Community 28 - "telemetry/service.py"
Cohesion: 0.18
Nodes (13): ImportResult, TelemetryPoint, TelemetryWindow, DataQuality, NormalizationError, normalize_value(), TelemetrySource, _content_hash() (+5 more)

### Community 29 - "Phase 7A — Agent Core & Grounded Orchestration"
Cohesion: 0.03
Nodes (72): 10. Agent state, 11. AgentRun persistence, 12. ToolCall persistence / audit trail, 13. Evidence model, 14. Claim → Evidence grounding, 15. Unsupported-claim detection, 16. Structured answer contract, 17. Natural-language API (+64 more)

### Community 30 - "Telemetry"
Cohesion: 0.17
Nodes (8): main(), Database, Telemetry, test_non_http_passthrough(), test_phase3_metrics_use_only_bounded_labels(), test_phase4_metrics_use_only_bounded_labels(), telemetry(), main()

### Community 31 - "DetectorProfile"
Cohesion: 0.17
Nodes (21): align_observations(), rolling_median(), HeuristicPullDetector, DetectorProfile, Observation, mixed_drive(), negative_scenario(), SyntheticScenario (+13 more)

### Community 32 - "status.test.tsx"
Cohesion: 0.17
Nodes (15): dynamic, GET(), Home(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready (+7 more)

### Community 33 - "mapping.py"
Cohesion: 0.23
Nodes (3): CSVColumnMapping, CSVSignalColumn, inspect_csv()

### Community 34 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 35 - "agents/schemas.py"
Cohesion: 0.10
Nodes (11): InvestigationInput, InvestigationProposal, ProposedGap, ProposedHypothesis, Answer, SpecialistBudget, ToolCall, specialist_policy() (+3 more)

### Community 36 - "AnalyticsService"
Cohesion: 0.45
Nodes (3): AnalyticsLimitError, AnalyticsService, AnalyticsResultResponse

### Community 37 - "analytics-workspace.tsx"
Cohesion: 0.14
Nodes (13): AnalyticsWorkspace(), history(), Configuration, curveLabels, HistoricalTrend(), NormalizedBin, NormalizedCurves(), Profile (+5 more)

### Community 38 - "InvestigationPlan"
Cohesion: 0.19
Nodes (4): InvestigationEvent, InvestigationPlan, InvestigationInstrumentation, InvestigationRepository

### Community 39 - "next"
Cohesion: 0.18
Nodes (5): config, GET, POST, metadata, next

### Community 40 - "Settings"
Cohesion: 0.09
Nodes (10): AcquisitionPublisher, Settings, test_build_timestamp_normalized_to_utc(), test_empty_optional_container_metadata(), test_invalid_settings(), test_malformed_database_config(), test_required_database(), test_safe_metadata() (+2 more)

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
Cohesion: 0.10
Nodes (31): expected_statement(), grade(), summarize(), temporal_checks(), effective(), timestamp(), Suite, case() (+23 more)

### Community 45 - "DeterministicProvider"
Cohesion: 0.10
Nodes (57): ModelTurn, ToolRequest, Binding, Claim, Draft, Specialist, Sufficiency, DeterministicProvider (+49 more)

### Community 46 - "package.json"
Cohesion: 0.11
Nodes (17): devDependencies, openapi-typescript, prettier, engines, node, name, packageManager, private (+9 more)

### Community 47 - "ModelInput"
Cohesion: 0.12
Nodes (12): draft_schema(), OpenAIProvider, provider_error_category(), turn_data(), ModelInput, RoutingInput, ResponseObserver, ScriptedProvider (+4 more)

### Community 48 - "MCP server"
Cohesion: 0.33
Nodes (6): Docker, Limits and troubleshooting, Local stdio, MCP server, Streamable HTTP, Validation

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

### Community 53 - "api/contracts.py"
Cohesion: 0.33
Nodes (7): ErrorDetail, ErrorResponse, Health, Ready, Version, live(), ready()

### Community 54 - "test_agent_runtime.py"
Cohesion: 0.06
Nodes (39): Ask, failure_category(), provider(), request(), ResponseStream, service_fixture(), call(), event() (+31 more)

### Community 55 - "97. Phase 7C Definition of Done"
Cohesion: 0.14
Nodes (14): 97. Phase 7C Definition of Done, API/UI/SSE, Conflicts, Data quality, Delivery, Evidence, Observability/performance, Parallelism (+6 more)

### Community 56 - "test_agents.py"
Cohesion: 0.09
Nodes (43): canonical_hash(), EvidenceRegistry, facts(), render_binding(), validate(), test_collection_metadata_consumes_evidence_budget(), test_collection_preserves_count_completeness_and_rows(), test_collection_rejects_foreign_record_before_publishing_any_evidence() (+35 more)

### Community 57 - "pytest"
Cohesion: 0.27
Nodes (9): test_routing_wire_errors_are_safe_and_bounded(), test_configuration_time_contract(), test_csv_encoding_missing_cells_and_bad_numeric_input(), test_csv_parser_and_abuse_guards(), test_deterministic_unit_conversion(), test_idempotency_is_stable_and_sensitive_to_identity(), test_nonfinite_measurements_and_conversion_overflow_are_rejected(), test_session_and_modification_times_reject_naive_or_reversed_windows() (+1 more)

### Community 59 - "AgentSettings"
Cohesion: 0.08
Nodes (14): AgentSettings, redact_data(), AgentInstrumentation, Orchestrator, Provider, AgentService, audit(), emit() (+6 more)

### Community 60 - "json"
Cohesion: 0.20
Nodes (11): buffered_points(), canonical_counts(), main(), memory_snapshot(), worker_metrics(), main(), compose(), main() (+3 more)

### Community 61 - "mcp-validation.sh"
Cohesion: 0.25
Nodes (6): DATABASE_URL, ENVIRONMENT, MCP_TEST_PROJECT, mcp-validation.sh script, TEST_DATABASE_URL, TEST_KAFKA_PORT

### Community 63 - "README.md"
Cohesion: 0.07
Nodes (16): Contributing, Phase 6 MCP tool platform, Resources, Safety and errors, System context, Toolchain selection, Local development, Failure handling (+8 more)

### Community 64 - "PHASE 0 COMPLETION REPORT"
Cohesion: 0.06
Nodes (26): Closure, ADRs created, Applications, Architecture, CI/CD, Closure rerun result, Codex context, Database (+18 more)

### Community 65 - "test_phase7d_cli.py"
Cohesion: 0.12
Nodes (14): test_affected_selection_cannot_change_smoke_or_report(), test_first_smoke_request_normalizes_sdk_auth_error_without_key(), test_invalid_affected_selection_sends_no_paid_calls(), test_operator_budget_progress_is_eval_only(), test_operator_budget_progress_preserves_hard_limit_and_explicit_identity(), test_operator_extra_requires_explicit_confirmed_eval_mode(), test_paid_baseline_rejects_mock_or_unverified_endpoint(), test_paid_entrypoint_fails_before_provider_or_docker() (+6 more)

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
Cohesion: 0.20
Nodes (10): 2026-10-09 Go advisory refresh, 2026-10-10 Go HTTP/2 advisory refresh, 2026-10-10 Kafka dependency refresh, Canonical rerun 36952758342, Container scan findings — 2026-10-01, Current disposition, Image-content and coverage status, Narrow residual-risk records (+2 more)

### Community 93 - "126. Final delivery report"
Cohesion: 0.14
Nodes (14): 126. Final delivery report, Architecture, Explicit deferrals, GitHub, Hardware, Live system, Migrations, Observability (+6 more)

### Community 94 - "45. Required synthetic scenarios"
Cohesion: 0.15
Nodes (13): 45. Required synthetic scenarios, A. Identical repeated pulls, B. Progressive IAT accumulation, C. Progressive boost reduction, D. Fuel-pressure degradation pattern, E. Slower normalized acceleration, F. Noisy but unchanged vehicle, G. Different configuration (+5 more)

### Community 95 - "capabilities.py"
Cohesion: 0.29
Nodes (6): AcquisitionCapabilitySource, fresh(), SourceCapabilitySnapshot, validated_report(), PreflightRequest, test_source_snapshot_freshness_is_bounded()

### Community 96 - "73. Definition of Done"
Cohesion: 0.17
Nodes (12): 73. Definition of Done, API/UI, Architecture, Delivery, Grounding, Observability, Orchestration, Performance (+4 more)

### Community 97 - "test_database.py"
Cohesion: 0.24
Nodes (6): DependencyUnavailable, test_extension_required(), test_otlp_configured(), test_real_app_lifespan(), test_real_database_unreachable(), test_sqlalchemy_failure()

### Community 98 - "Phase 7D — Real Model Validation & Agent Reliability Baseline"
Cohesion: 0.13
Nodes (15): 10. No hidden real calls in normal CI, 11. Evaluation dataset design, 12. Suite size, 13. Category distribution, 1. Repository / branch / baseline, 2. Phase 7C closure status, 3. Phase 7D purpose, 4. Primary model choice (+7 more)

### Community 99 - "Phases 0–5 retrospective hardening"
Cohesion: 0.06
Nodes (29): ADR 0014: Kafka durable acquisition stream, Consequences, Context, Decision, ADR 0017: Retrospective evidence and execution identity, Alternatives, Consequences and risks, Context (+21 more)

### Community 100 - "evaluate_mcp.py"
Cohesion: 0.12
Nodes (8): evaluate(), main(), main(), ready_endpoint(), fingerprint(), seed(), main(), database_command()

### Community 101 - "investigation/service.py"
Cohesion: 0.12
Nodes (32): EvidenceGap, GapStatus, GapType, Hypothesis, HypothesisCategory, HypothesisStatus, InvestigationOutcome, ExistingEvidence (+24 more)

### Community 102 - "create_app"
Cohesion: 0.09
Nodes (19): create_app(), test_clean_upgrade_downgrade_reupgrade_and_readiness(), test_expired_acquisition_releases_capacity_without_accepting_its_token(), test_retrospective_signed_csv_duplicates_and_analytics_identity(), test_sequence_overflow_is_dead_lettered_and_valid_edge_persists(), test_stream_poll_is_atomic_replay_safe_and_persists_provisional_findings(), Probe, test_database_error_propagation_cannot_leak_through_parent_spans() (+11 more)

### Community 103 - "pull_request_template.md"
Cohesion: 0.22
Nodes (8): Database/contract impact, Documentation, How it was validated, Observability impact, Risks, Security impact, What changed, Why

### Community 104 - "agent_router"
Cohesion: 0.20
Nodes (4): agent_router(), audit(), stream(), RunAudit

### Community 105 - "investigation/domain.py"
Cohesion: 0.19
Nodes (11): Availability, Feasibility, InvestigationError, RecipeReference, Resolution, SignalNeed, Transition, choose_recipe() (+3 more)

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

### Community 123 - "test_phase7d_harness.py"
Cohesion: 0.18
Nodes (22): Rates, ledger(), receipt(), test_dataset_fails_closed_on_malformed_distribution(), test_each_operator_extra_round_requires_confirmation_and_shares_spend(), test_existing_real_adapter_explicit_config_and_safe_receipts(), test_hard_five_dollar_ceiling(), test_invalid_usage_and_long_context_are_rejected() (+14 more)

### Community 124 - "ADR 0012: Versioned deterministic session analysis"
Cohesion: 0.33
Nodes (5): ADR 0012: Versioned deterministic session analysis, Alternatives, Consequences and risks, Context, Decision

### Community 125 - "ADR 0013: Deterministic evidence-first event architecture"
Cohesion: 0.33
Nodes (5): ADR 0013: Deterministic evidence-first event architecture, Alternatives, Consequences and risks, Context, Decision

### Community 126 - ".run"
Cohesion: 0.16
Nodes (6): ElmTransport, VehicleDataAdapter, report(), report_periodically(), CollectorStats, SamplingPlanItem

### Community 127 - "Ledger"
Cohesion: 0.31
Nodes (3): Ledger, test_interrupted_smoke_is_not_automatically_repeated(), test_receipts_do_not_accept_missing_usage_as_free()

### Community 129 - "Phase 3 events"
Cohesion: 0.22
Nodes (8): Grounded agent, Investigation and adaptive logging, MCP, Observability, Phase 2 analysis, Phase 3 events, Phase 7C supervisor, Retrospective instrumentation checks

### Community 130 - "75. API surface"
Cohesion: 0.33
Nodes (6): 75. API surface, Acquisition, Ingestion, Live client, Logging objectives, Recipes

### Community 131 - "85. Unit and contract tests"
Cohesion: 0.33
Nodes (6): 85. Unit and contract tests, Collector, Live analysis, Recipes, Sampling, Stream

### Community 132 - "server.py"
Cohesion: 0.14
Nodes (4): ErrorCode, tool_error(), Instrumentation, SafeMCPServer

### Community 133 - "worker.py"
Cohesion: 0.20
Nodes (4): DatasetCapability, measure_signal_quality(), StreamConsumer, validate_sequence()

### Community 134 - "EventEngine"
Cohesion: 0.43
Nodes (14): EventEngine, base(), frames(), pull(), test_comparable_pulls(), test_fuel_drop_requires_sustained_observation_not_single_low_spike(), test_low_load_variation_is_not_fuel_or_throttle_event(), test_never_available_channels_do_not_claim_sensor_dropout() (+6 more)

### Community 135 - "Vehicle Intelligence Platform context"
Cohesion: 0.40
Nodes (4): Business Logic & Feature Map, Directory Structure Map, Validation, Vehicle Intelligence Platform context

### Community 136 - "SyntheticTelemetrySource"
Cohesion: 0.50
Nodes (3): SyntheticTelemetrySource, test_synthetic_source_is_deterministic_and_complete(), collect()

### Community 137 - "Phase 7D real evaluation report"
Cohesion: 0.17
Nodes (12): Affected-case round four, Affected-case round ten and next bounded hardening, Completed operator-authorized round three and current hardening, Completed round twelve and current general corrections, Confirmation interruption and reviewable hardening, Current candidate deterministic closure, General fixes prompted by real execution, Observed profile and production decision (+4 more)

### Community 138 - "94. Failure behavior"
Cohesion: 0.40
Nodes (5): 94. Failure behavior, Database unavailable, Device disconnect, One bad signal, Stream unavailable

### Community 139 - "architecture/phase-7b-investigation-adaptive-logging.md"
Cohesion: 0.11
Nodes (14): Component model, CURRENT, FUTURE, Approval and follow-up, Domain and persistence, Phase 7B investigation and adaptive logging, Service boundaries, Phase 3 acceptance (+6 more)

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

### Community 148 - "prompts/phase-7d-real-model-validation.md"
Cohesion: 0.22
Nodes (6): Hardening from partial real observations, Phase 7D real-model validation, Quality, source capability and comparison metadata scope, Registered pull discovery and routing context, Related-domain routing and deterministic selection correction, Strict outputs and affected-case verification

### Community 149 - "15. Required acquisition adapters"
Cohesion: 0.50
Nodes (4): 15. Required acquisition adapters, Real read-only OBD adapter path, Replay adapter, Synthetic live adapter

### Community 151 - "events/synthetic.py"
Cohesion: 0.18
Nodes (15): evaluate_events(), EventClassMetrics, EventEvaluation, _overlaps(), anomaly_scenario(), AnomalyInjection, EventScenario, ExpectedEvent (+7 more)

### Community 152 - "CATEGORY D — FUEL / AIR / BOOST"
Cohesion: 0.18
Nodes (11): 44. D01, 45. D02, 46. D03, 47. D04, 48. D05, 49. D06, 50. D07, 51. D08 (+3 more)

### Community 153 - "101. ADRs"
Cohesion: 0.67
Nodes (3): 101. ADRs, Acquisition lifecycle / recipes, Streaming architecture

### Community 154 - "Phase 7A acceptance"
Cohesion: 0.14
Nodes (12): Boundaries, Context and evidence, Execution and lifecycle, Phase 7A grounded agent, Provider and streaming contracts, Baseline and delivery boundary, Executed checkpoint: `881fcca0bb75acf9369bbbf25854c32d626aa017`, Final receipt requirements (+4 more)

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

### Community 175 - "AgentRun"
Cohesion: 0.19
Nodes (4): AgentRepository, TerminableConnection, AgentRun, StreamEvent

### Community 176 - "ADR 0022: Bounded real-model evaluation and durable spend accounting"
Cohesion: 0.25
Nodes (8): ADR 0022: Bounded real-model evaluation and durable spend accounting, Alternatives, Consequences and risks, Context, Decision, Evidence-driven hardening, Operator instruction to continue within the hard ceiling, Status

### Community 177 - "mcp/cli.py"
Cohesion: 0.15
Nodes (3): main(), HTTPInstrumentation, test_http_trace_context_and_auth_rejections()

### Community 178 - "main.py"
Cohesion: 0.13
Nodes (3): CorrelationMiddleware, PlatformAPI, OfflineProbe

### Community 179 - "architecture/phase-7c-specialist-agents-supervisor.md"
Cohesion: 0.10
Nodes (19): Phase 7C specialist agents and supervisor, Current phase, Phase 7C implementation, Roadmap, Supervisor and specialists, Initial threat model, Original Phase 4 local resource budgets, Phase 4 acquisition threats (+11 more)

### Community 180 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 181 - "ADR 0018: Read-only MCP application adapter"
Cohesion: 0.17
Nodes (10): ADR 0016: Deterministic, immutable automotive analytics, Consequences, Decision, Status, ADR 0018: Read-only MCP application adapter, Alternatives, Consequences and risks, Context (+2 more)

### Community 182 - "ADR 0019: Grounded agent state and evidence"
Cohesion: 0.08
Nodes (22): blocked(), ADR 0015: Versioned recipes and acquisition lifecycle, Consequences, Decision, ADR 0019: Grounded agent state and evidence, Alternatives, Consequences and risks, Context (+14 more)

### Community 183 - "98. Phase 7B Definition of Done"
Cohesion: 0.15
Nodes (13): 98. Phase 7B Definition of Done, Acquisition / follow-up, API / UI, Approval, Delivery, Existing evidence, Investigation domain, Logging plan (+5 more)

### Community 184 - "Phase 1 vehicle and telemetry core"
Cohesion: 0.40
Nodes (4): Canonical import contract, Performance baseline protocol, Phase 1 vehicle and telemetry core, Query and operations

### Community 187 - "httpx"
Cohesion: 0.11
Nodes (15): main(), seed_agent(), main(), main(), ask(), runtime(), main(), main() (+7 more)

### Community 188 - "Phase 7B acceptance"
Cohesion: 0.29
Nodes (5): Benchmark checkpoint, Final receipt requirements, Phase 7B acceptance, Scope and gates, Phase 7B requirement traceability

### Community 189 - "mcp_client.py"
Cohesion: 0.12
Nodes (12): connect(), EvidenceClient, MCPClient, MeteredClient, ToolMeter, source(), test_evaluation_factory_wraps_the_actual_connect_seam(), test_meter_covers_phase7b_reads_and_preserves_safe_hashes() (+4 more)

### Community 190 - "api/errors.py"
Cohesion: 0.16
Nodes (7): register_errors(), agent_error(), http_error(), invalid(), unavailable(), unexpected(), response()

### Community 191 - "DeviceCapabilities"
Cohesion: 0.14
Nodes (21): SyntheticLiveAdapter, DeviceCapabilities, Importance, LoggingRecipe, plan_sampling(), preflight(), PreflightResult, Priority (+13 more)

### Community 192 - "SessionAnalysisService"
Cohesion: 0.35
Nodes (5): AnalysisLimitError, SessionAnalysisService, AnalysisResult, Pull, SessionSegment

### Community 193 - "Phase 2 session and pull analysis"
Cohesion: 0.40
Nodes (4): API and limits, Phase 2 session and pull analysis, Semantics, Synthetic validation

### Community 194 - "budgets.py"
Cohesion: 0.09
Nodes (18): AgentRequestBudgetMiddleware, ResourceBudgetMiddleware, TokenBucket, scope(), test_budget_failures_release_reservation(), test_invalid_budgets(), test_request_cancellation_releases_reservation(), test_request_failure_releases_reservation() (+10 more)

### Community 195 - "test_acquisition_capabilities.py"
Cohesion: 0.50
Nodes (6): query_row(), report(), test_latest_prefers_newer_registered_report(), test_latest_rejects_stale_and_disconnected_reports(), test_latest_uses_connected_collector_snapshot(), test_register_requires_active_configuration_and_limits_source()

### Community 196 - "45. Investigation examples"
Cohesion: 0.50
Nodes (4): 45. Investigation examples, Example A — repeated pull performance loss, Example B — change after intercooler, Example C — missing technical specification

### Community 197 - "Observed answers"
Cohesion: 0.04
Nodes (44): 2:A01:0 — representative, 2:A02:0 — representative, 2:A03:0 — representative, 2:A05:0 — ambiguous, 2:A06:0 — representative, 2:A09:0 — representative, 2:A10:0 — worst, 2:B04:0 — ambiguous (+36 more)

### Community 201 - "ADR 0023: Scoped collection evidence and consistent evidence gaps"
Cohesion: 0.20
Nodes (7): ADR 0023: Scoped collection evidence and consistent evidence gaps, Consequences and verification, Context, Decision, Current full-source evidence: round twelve, Phase 7D traceability ledger, Round-ten affected observation update

### Community 203 - "Phase 4 — Streaming & Live Vehicle Acquisition"
Cohesion: 0.20
Nodes (9): Boundaries and flow, Broker storage and observed worker health, Collector heartbeat and acquisition context, Explicit CSV mapping and live recovery, Failure and security model, Phase 4 — Streaming & Live Vehicle Acquisition, Recipes and quality, Retrospective execution guarantees (+1 more)

### Community 204 - "AgentError"
Cohesion: 0.15
Nodes (13): Approval, CapabilitySnapshot, InvestigationService, AgentError, test_create_closes_provider_after_invalid_semantic_output(), test_create_rejects_invalid_identity_capacity_and_sufficient_answer(), test_create_reuses_existing_plan_only_for_same_source(), test_create_timeout_maps_to_bounded_public_error() (+5 more)

### Community 205 - "test_investigation_repository.py"
Cohesion: 0.27
Nodes (10): approved_plan(), item(), result_with(), storage(), session(), test_claim_reanalysis_is_atomic_and_unique(), test_create_conflict_and_stale_update_fail_closed(), test_create_get_recent_update_and_replay() (+2 more)

### Community 206 - "phase7d_eval.py"
Cohesion: 0.10
Nodes (18): atomic_json(), domain_fingerprint(), database_command(), free_port(), Process, evaluate(), failure_kind(), identity() (+10 more)

### Community 207 - "core/config.py"
Cohesion: 0.13
Nodes (5): run(), run_sync(), test_openapi_schema(), batch_count(), main()

### Community 208 - "ReplayAdapter"
Cohesion: 0.36
Nodes (4): ReplayAdapter, run(), test_replay_is_deterministic(), test_replay_skips_unplanned_signal_without_sleep()

### Community 210 - "Phase 6 acceptance evidence"
Cohesion: 0.33
Nodes (6): Executed acceptance checkpoint, Independent MCP evidence, Limitations and deferred scope, Measured performance and bounds, Phase 6 acceptance evidence, Remote proof and final HEAD identity

### Community 211 - "fixture"
Cohesion: 0.33
Nodes (6): url(), url(), source(), storage(), fixture(), cli()

### Community 212 - "resolve_context"
Cohesion: 0.57
Nodes (4): at(), effective(), resolve_context(), test_temporal_context_removal_and_boundary()

### Community 214 - "load_suite"
Cohesion: 0.25
Nodes (6): load_suite(), test_identity_requires_clean_exact_commit(), test_projection_calibration_requires_full_attempted_schedule(), test_exact_versioned_dataset_and_fixed_schedule(), test_versioned_questions_match_the_authoritative_specification(), observed_role_turns()

### Community 218 - "evaluate_agent_grounding.py"
Cohesion: 0.13
Nodes (13): evaluate(), main(), main(), address(), command(), wait_for_telemetry_backends(), main(), address() (+5 more)

## Knowledge Gaps
- **22 isolated node(s):** `vehicle-platform-api`, `react-dom`, `typescript`, `@types/node`, `@types/react` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1794 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **59 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OpenAIProvider` connect `ModelInput` to `agents/schemas.py`, `create_app`, `AgentError`, `DeterministicProvider`, `phase7d_eval.py`, `runtime.py`, `main.py`, `prompts/phase-7d-real-model-validation.md`, `test_agent_runtime.py`, `AgentSettings`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 127 inferred relationships involving `AgentError` (e.g. with `EvidenceRegistry` and `InvestigationRepository`) actually correct?**
  _`AgentError` has 127 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vehicle-platform-api`, `react-dom`, `typescript` to the rest of the system?**
  _22 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `AnalyticsConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.09228070175438596 - nodes in this community are weakly interconnected._
- **Why does `Phase 7D real-model validation` connect `prompts/phase-7d-real-model-validation.md` to `ModelInput`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `router()` (e.g. with `LoggingRecipe` and `AcquisitionAuthError`) actually correct?**
  _`router()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_acquisition.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11711711711711711 - nodes in this community are weakly interconnected._