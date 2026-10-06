# Graph Report - Vehicle-Intelligence-Platform  (2026-10-06)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1283 nodes · 3497 edges · 76 communities (53 shown, 23 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 567 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `480e89ac`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 70
- Community 71
- Community 72
- Community 75

## God Nodes (most connected - your core abstractions)
1. `router()` - 126 edges
2. `Settings` - 60 edges
3. `RawTelemetryRecord` - 57 edges
4. `AcquisitionService` - 47 edges
5. `AnalyticsConfig` - 46 edges
6. `Telemetry` - 46 edges
7. `store()` - 44 edges
8. `Database` - 42 edges
9. `AlignedFrame` - 40 edges
10. `BoundedSpool` - 36 edges

## Surprising Connections (you probably didn't know these)
- `main()` --uses--> `AcquisitionCollector`  [INFERRED]
  scripts/evaluate_stream_recovery.py → apps/api/src/vehicle_platform/acquisition/collector.py
- `main()` --uses--> `AcquisitionCollector`  [INFERRED]
  scripts/observability-phases.py → apps/api/src/vehicle_platform/acquisition/collector.py
- `main()` --uses--> `GatewayPublisher`  [INFERRED]
  scripts/evaluate_stream_recovery.py → apps/api/src/vehicle_platform/acquisition/collector.py
- `main()` --uses--> `GatewayPublisher`  [INFERRED]
  scripts/observability-phases.py → apps/api/src/vehicle_platform/acquisition/collector.py
- `main()` --uses--> `BoundedSpool`  [INFERRED]
  scripts/evaluate_stream_recovery.py → apps/api/src/vehicle_platform/acquisition/stream.py

## Import Cycles
- None detected.

## Communities (76 total, 23 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (66): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+58 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (67): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, EventProfile, PullWindow (+59 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (49): UUID, align_observations(), Align by deterministic last-value carry-forward, expiring at max_gap. Duplicate…, rolling_median(), compute_pull_metrics(), HeuristicPullDetector, HeuristicSegmentDetector, _mean() (+41 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (55): APIRouter, router(), analytics_config(), analyze_repeated_pulls(), analyze_session(), analyze_session_events(), assess_session_capabilities(), bearer() (+47 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (43): AcquisitionBatchAccepted, AcquisitionCreate, AcquisitionCreated, AcquisitionHeartbeat, AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement, AnalysisRequest (+35 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (20): SyntheticLiveAdapter, BoundedSpool, Path, Single-collector atomic acknowledgement, only after successful publish., Path, test_bounded_spool_replays_and_reports_overflow(), test_collector_capability_failure_closes_adapter(), test_collector_heartbeat_interruption_does_not_erase_samples() (+12 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (22): aiokafka, assess_dataset(), collector_health(), DatasetCapability, measure_signal_quality(), datetime, Infer transport/sampling freshness only from an authenticated report. Event…, SignalQuality (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (26): DataQuality, NormalizationError, normalize_value(), parse_timestamp(), datetime, StrEnum, ValueError, sample_id() (+18 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (26): alembic_config, alembic_script, run(), run_sync(), fixture, Requires an explicitly supplied disposable test database. Never skips silently., url(), asyncio (+18 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (27): DeviceCapabilities, Importance, LoggingRecipe, plan_sampling(), preflight(), PreflightResult, Priority, StrEnum (+19 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (22): ElmTcpTransport, Concrete ELM327 TCP/RFCOMM bridge transport with a strict read-only command…, adapter_for(), AdapterKind, devices(), execute(), _preflight(), preflight_command() (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.10
Nodes (21): create_app(), test_expired_acquisition_releases_capacity_without_accepting_its_token(), test_retrospective_signed_csv_duplicates_and_analytics_identity(), test_sequence_overflow_is_dead_lettered_and_valid_edge_persists(), Probe, Exception, parametrize, test_database_error_propagation_cannot_leak_through_parent_spans() (+13 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (16): FakeElm, Exception, parametrize, test_collector_health_distinguishes_transport_and_sampling(), test_elm327_only_uses_allowlisted_read_commands(), test_extended_synthetic_modes_have_measured_behavior(), test_gateway_heartbeat_is_scoped_and_failures_are_explicit(), test_gateway_publisher_classifies_responses() (+8 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (3): alembic, upgrade(), sqlalchemy_dialects

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (17): UUID, RawTelemetryMessage, validate_sequence(), test_stream_contract_and_dataset_capability(), parametrize, test_sequence_overflow_rejected_at_every_input_boundary(), test_sequence_valid_edges_remain_compatible(), datetime (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (10): Read-only adapter contract. Deliberately has no command/write operation., VehicleDataAdapter, AcquisitionCollector, report(), report_periodically(), CollectorStats, Hardware-near bounded collector with retry, backpressure, and disk replay., SamplingPlanItem (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.10
Nodes (18): ASGIApp, Receive, Scope, Send, Per-process budgets, with no unbounded per-client identifier dictionaries. The…, ResourceBudgetMiddleware, TokenBucket, parametrize (+10 more)

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (20): dependencies, next, react, react-dom, name, private, type, version (+12 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (10): main(), StreamConsumer, Database, AsyncSession, Telemetry, parametrize, test_stream_poll_is_atomic_replay_safe_and_persists_provisional_findings(), test_provisional_window_is_event_time_bounded_without_discarding_canonical_input() (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (21): ErrorDetail, ErrorResponse, Health, BaseModel, Ready, Version, FastAPI, register_errors() (+13 more)

### Community 20 - "Community 20"
Cohesion: 0.12
Nodes (17): DetectedEvent, json(), Pull, Segment, Session, Signal, TelemetryDashboard(), Vehicle (+9 more)

### Community 21 - "Community 21"
Cohesion: 0.14
Nodes (16): datetime, model_validator, Settings, MonkeyPatch, parametrize, test_build_timestamp_normalized_to_utc(), test_empty_optional_container_metadata(), test_invalid_settings() (+8 more)

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (13): Acquisition, CollectorReport, Finalized, LiveAcquisition(), LiveFinding, LivePoint, LiveSnapshot, Pipeline (+5 more)

### Community 23 - "Community 23"
Cohesion: 0.13
Nodes (11): CorrelationMiddleware, ASGIApp, DatabaseProbe, Protocol, PlatformAPI, ASGIApp, FastAPI, test_non_http_passthrough() (+3 more)

### Community 24 - "Community 24"
Cohesion: 0.19
Nodes (13): dynamic, GET(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready, SystemStatus (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.11
Nodes (7): MonkeyPatch, test_consumer_database_failure_exits_without_sql_inputs(), fail(), test_elm_tcp_transport_connects_reads_reuses_and_closes(), test_gateway_transport_errors_enter_retry_spool_path(), test_spool_failed_atomic_ack_preserves_original(), CaptureFixture

### Community 26 - "Community 26"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (12): StandardPid, Constant-memory local request budgets for the Phase 4 resource boundaries., CSVSignalColumn, BaseModel, model_validator, Explicit generic CSV mapping; no proprietary exporter assumptions., collections_abc, csv (+4 more)

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (14): Prevent database driver messages and SQL text from leaving the process., logging, opentelemetry, opentelemetry_exporter_otlp_proto_http_trace_exporter, opentelemetry_exporter_prometheus, opentelemetry_instrumentation_sqlalchemy, opentelemetry_sdk_metrics, opentelemetry_sdk_resources (+6 more)

### Community 29 - "Community 29"
Cohesion: 0.15
Nodes (8): SanitizingExporter, JSONFormatter, Any, test_real_trace_metric_and_log_correlation(), LogRecord, ReadableSpan, SpanExporter, SpanExportResult

### Community 30 - "Community 30"
Cohesion: 0.12
Nodes (16): devDependencies, @axe-core/playwright, eslint, @eslint/compat, eslint-config-next, jsdom, @playwright/test, @testing-library/jest-dom (+8 more)

### Community 31 - "Community 31"
Cohesion: 0.21
Nodes (8): ImportResult, LiveOBDSource, Protocol, Adapter boundary only: Phase 1 intentionally provides no hardware…, TelemetrySource, _content_hash(), IngestionService, AsyncSession

### Community 32 - "Community 32"
Cohesion: 0.15
Nodes (10): AnalyticsWorkspace(), history(), Configuration, curveLabels, NormalizedBin, Profile, Pull, request() (+2 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (10): os, pathlib, re, Validate local skills, scoped context, declarative YAML and Markdown links., Enforce separate line and branch thresholds for the generated local coverage…, Hash the exact reviewable working tree without printing file contents., Write canonical CI validation summaries without converting failures into passes., subprocess (+2 more)

### Community 34 - "Community 34"
Cohesion: 0.32
Nodes (12): preview_csv_import(), inspect_csv(), MappedCSVTelemetrySource, mapping(), parametrize, test_absent_mapping_and_invalid_headers_are_rejected(), test_explicit_identity_sequence_are_preserved(), test_explicit_wide_csv_mapping_preserves_units_time_and_provenance() (+4 more)

### Community 35 - "Community 35"
Cohesion: 0.21
Nodes (4): Elm327Adapter, ElmTransport, Protocol, Generic standard-mode OBD-II reader; no proprietary or write commands.

### Community 36 - "Community 36"
Cohesion: 0.20
Nodes (10): DependencyUnavailable, Exception, Infrastructure failed its bounded readiness check., parametrize, test_extension_required(), test_otlp_configured(), test_real_app_lifespan(), test_real_database_unreachable() (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.20
Nodes (6): configs, FakeEventSource, vehicle, @testing-library/jest-dom, @testing-library/react, vitest

### Community 38 - "Community 38"
Cohesion: 0.27
Nodes (11): argparse, Namespace, accepted(), load_exceptions(), load_findings(), main(), parse_args(), Any (+3 more)

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (6): config, GET, POST, apps_web_src_app_globals, metadata, next

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (8): detectedEvent, pull, segment, session, signals, vehicle, window, @testing-library/user-event

### Community 41 - "Community 41"
Cohesion: 0.42
Nodes (5): UUID, SessionAnalysisService, AnalysisResult, Pull, SessionSegment

### Community 42 - "Community 42"
Cohesion: 0.42
Nodes (6): TelemetryPoint, TelemetryWindow, datetime, UUID, QueryService, validate_vehicle_context()

### Community 43 - "Community 43"
Cohesion: 0.29
Nodes (5): test_collector_reports_actual_recovery_metrics_and_payload_free_spans(), test_collector_retries_spools_and_replays_without_loss(), available(), unavailable(), test_pending_spool_precedes_new_data_and_overflow_is_visible()

### Community 44 - "Community 44"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 45 - "Community 45"
Cohesion: 0.29
Nodes (3): AIOKafkaProducer, AcquisitionPublisher, Application-owned producer; bounded concurrent publication and shutdown.

### Community 46 - "Community 46"
Cohesion: 0.29
Nodes (6): ref_node_child_process, ref_node_fs, ref_openapi_typescript, ref_prettier, raw, schema

### Community 47 - "Community 47"
Cohesion: 0.48
Nodes (5): buffered_points(), canonical_counts(), main(), memory_snapshot(), worker_metrics()

### Community 49 - "Community 49"
Cohesion: 0.40
Nodes (4): scripts_lib_wait_http_sh, observability-validation.sh script, wait_prometheus_query(), stack-smoke.sh script

### Community 50 - "Community 50"
Cohesion: 0.40
Nodes (3): Receive, Scope, Send

### Community 52 - "Community 52"
Cohesion: 0.40
Nodes (4): compose(), main(), Wait until the real Next.js status and domain proxies recover too., wait_for_browser_proxies()

### Community 53 - "Community 53"
Cohesion: 0.40
Nodes (3): KAFKA_BOOTSTRAP_SERVERS, integration.sh script, TEST_DATABASE_URL

### Community 54 - "Community 54"
Cohesion: 0.40
Nodes (3): COMPOSE_PROJECT_NAME, GIT_SHA, retrospective-validation.sh script

## Knowledge Gaps
- **126 isolated node(s):** `vehicle-platform-api`, `StandardPid`, `config`, `name`, `version` (+121 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 420 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `router()` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 34`, `Community 4`, `Community 6`, `Community 7`, `Community 9`, `Community 41`, `Community 42`, `Community 11`, `Community 18`, `Community 19`, `Community 21`, `Community 23`, `Community 31`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `Settings` connect `Community 21` to `Community 1`, `Community 3`, `Community 4`, `Community 36`, `Community 6`, `Community 8`, `Community 11`, `Community 45`, `Community 18`, `Community 23`, `Community 28`, `Community 29`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `RawTelemetryRecord` connect `Community 15` to `Community 34`, `Community 35`, `Community 5`, `Community 6`, `Community 7`, `Community 10`, `Community 43`, `Community 12`, `Community 14`, `Community 48`, `Community 52`, `Community 25`, `Community 27`, `Community 28`, `Community 31`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `router()` (e.g. with `LoggingRecipe` and `AcquisitionAuthError`) actually correct?**
  _`router()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Are the 40 inferred relationships involving `Settings` (e.g. with `run()` and `AcquisitionPublisher`) actually correct?**
  _`Settings` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `RawTelemetryRecord` (e.g. with `Elm327Adapter` and `ReplayAdapter`) actually correct?**
  _`RawTelemetryRecord` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `AcquisitionService` (e.g. with `SyntheticLiveAdapter` and `SignalQuality`) actually correct?**
  _`AcquisitionService` has 21 INFERRED edges - model-reasoned connections that need verification._