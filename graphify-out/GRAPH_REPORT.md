# Graph Report - vehicle-intelligence-graphify-sync  (2026-10-06)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1524 nodes · 4214 edges · 93 communities (66 shown, 27 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 718 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `eeb9c8ed`
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
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 86
- Community 87
- Community 88
- Community 91
- Community 92

## God Nodes (most connected - your core abstractions)
1. `router()` - 126 edges
2. `Settings` - 74 edges
3. `Telemetry` - 64 edges
4. `RawTelemetryRecord` - 59 edges
5. `Database` - 51 edges
6. `AcquisitionService` - 50 edges
7. `AnalyticsConfig` - 50 edges
8. `store()` - 44 edges
9. `AlignedFrame` - 40 edges
10. `Adapter` - 39 edges

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

## Communities (93 total, 27 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (68): acceleration_interval(), AnalyticsConfig, baseline(), bin_statistics(), coefficient_of_variation(), Comparability, comparable_groups(), compare_context() (+60 more)

### Community 1 - "Community 1"
Cohesion: 0.19
Nodes (19): evaluate_events(), EventClassMetrics, EventEvaluation, _overlaps(), One-to-one deterministic matching by type, pull and temporal overlap., anomaly_scenario(), AnomalyInjection, EventScenario (+11 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (35): UUID, align_observations(), Align by deterministic last-value carry-forward, expiring at max_gap. Duplicate…, rolling_median(), HeuristicPullDetector, DetectorProfile, Observation, StrEnum (+27 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (54): APIRouter, router(), analytics_config(), analyze_repeated_pulls(), analyze_session(), analyze_session_events(), assess_session_capabilities(), bearer() (+46 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (46): AcquisitionBatchAccepted, AcquisitionCreate, AcquisitionCreated, AcquisitionHeartbeat, AcquisitionLiveQuality, AcquisitionLiveSnapshot, AcquisitionPipelineMeasurement, AnalysisRequest (+38 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (27): BoundedSpool, Path, Single-collector atomic acknowledgement, only after successful publish., parametrize, Path, test_bounded_spool_replays_and_reports_overflow(), test_collector_health_distinguishes_transport_and_sampling(), test_collector_rejects_unbounded_configuration() (+19 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (22): aiokafka, assess_dataset(), collector_health(), DatasetCapability, measure_signal_quality(), datetime, Infer transport/sampling freshness only from an authenticated report. Event…, SignalQuality (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (18): Read-only adapter contract. Deliberately has no command/write operation., VehicleDataAdapter, AcquisitionCollector, report(), report_periodically(), CollectorStats, Hardware-near bounded collector with retry, backpressure, and disk replay., SamplingPlanItem (+10 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (25): run(), run_sync(), Protocol, Read-only connection defaults also bound queries before a transaction begins., Terminable, Connection, contextlib, importlib_metadata (+17 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (27): ReplayAdapter, DeviceCapabilities, Importance, LoggingRecipe, plan_sampling(), preflight(), PreflightResult, Priority (+19 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (20): adapter_for(), AdapterKind, devices(), execute(), _preflight(), preflight_command(), probe(), Path (+12 more)

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (35): AccessToken, Verify an operator-provisioned opaque token; never issue or forward tokens., ReadTokenVerifier, MCPSettings, BaseSettings, model_validator, ReadOnlyDatabase, create_server() (+27 more)

### Community 12 - "Community 12"
Cohesion: 0.19
Nodes (27): AlignedFrame, BaselineType, DetectorResult, DetectorState, EventCandidate, EventCategory, PullWindow, StrEnum (+19 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (3): alembic, upgrade(), sqlalchemy_dialects

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (32): datetime, sample_id(), validate_sequence(), asyncio, asyncpg, datetime, httpx, json (+24 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (24): Client, httpx2, mcp, mcp_client_stdio, mcp_client_streamable_http, main(), Representative MCP reads measured through the SDK against disposable canonical…, evaluate() (+16 more)

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (20): Adapter, Any, Entity, UUID, PlatformError, Exception, call(), P (+12 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (22): AnyUrl, Bounded context repository for records currently owned by HTTP SQL handlers., ErrorCode, StrEnum, ToolError, UUID, tool_error(), Instrumentation (+14 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (9): main(), StreamConsumer, Database, AsyncSession, Telemetry, test_phase3_metrics_use_only_bounded_labels(), test_phase4_metrics_use_only_bounded_labels(), batch_count() (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.22
Nodes (12): FastAPI, register_errors(), http_error(), invalid(), unavailable(), unexpected(), response(), fastapi_exceptions (+4 more)

### Community 20 - "Community 20"
Cohesion: 0.09
Nodes (20): dependencies, next, react, react-dom, name, private, type, version (+12 more)

### Community 22 - "Community 22"
Cohesion: 0.08
Nodes (15): Acquisition, CollectorReport, Finalized, LiveAcquisition(), LiveFinding, LivePoint, LiveSnapshot, Pipeline (+7 more)

### Community 23 - "Community 23"
Cohesion: 0.19
Nodes (8): Constant-memory local request budgets for the Phase 4 resource boundaries., TokenBucket, parametrize, test_bucket_burst_refill_and_long_idle_never_exceed_capacity(), test_invalid_bucket_bounds_fail(), math, pytest, starlette_types

### Community 24 - "Community 24"
Cohesion: 0.09
Nodes (7): MCPServer, register_tools(), compare_configurations(), get_cross_session_analytics(), get_event(), get_session_analytics(), get_session_summary()

### Community 25 - "Community 25"
Cohesion: 0.12
Nodes (17): DetectedEvent, json(), Pull, Segment, Session, Signal, TelemetryDashboard(), Vehicle (+9 more)

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (7): ElmTcpTransport, Concrete ELM327 TCP/RFCOMM bridge transport with a strict read-only command…, FakeElm, test_elm327_only_uses_allowlisted_read_commands(), request(), test_elm_tcp_transport_connects_reads_reuses_and_closes(), request()

### Community 27 - "Community 27"
Cohesion: 0.07
Nodes (38): StandardPid, DataQuality, NormalizationError, normalize_value(), parse_timestamp(), StrEnum, ValueError, SignalDefinition (+30 more)

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (11): Prevent database driver messages and SQL text from leaving the process., logging, opentelemetry_exporter_otlp_proto_http_trace_exporter, opentelemetry_exporter_prometheus, opentelemetry_instrumentation_sqlalchemy, opentelemetry_propagate, opentelemetry_sdk_metrics, opentelemetry_sdk_resources (+3 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (9): SyntheticLiveAdapter, test_collector_capability_failure_closes_adapter(), test_collector_heartbeat_interruption_does_not_erase_samples(), test_collector_reports_capabilities_bounds_and_graceful_disconnect(), heartbeat(), test_periodic_heartbeat_continues_while_adapter_waits(), read(), publish() (+1 more)

### Community 30 - "Community 30"
Cohesion: 0.27
Nodes (16): EventProfile, Development heuristics; these are not factory safety or N55 calibration limits., EventEngine, base(), frames(), pull(), test_comparable_pulls(), test_fuel_drop_requires_sustained_observation_not_single_low_spike() (+8 more)

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (12): create_app(), Probe, Exception, parametrize, test_live_independent_and_ready(), test_logging_recipe_and_preflight_contracts(), test_non_ascii_correlation_header_is_regenerated(), test_otlp_http_delivers_real_request_span() (+4 more)

### Community 32 - "Community 32"
Cohesion: 0.19
Nodes (13): dynamic, GET(), SystemStatusPanel(), register(), getSystemStatus(), isSystemStatus(), Ready, SystemStatus (+5 more)

### Community 34 - "Community 34"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 35 - "Community 35"
Cohesion: 0.20
Nodes (10): compute_pull_metrics(), HeuristicSegmentDetector, _mean(), PullDetector, Protocol, SegmentDetector, _slope(), DetectedPull (+2 more)

### Community 36 - "Community 36"
Cohesion: 0.09
Nodes (26): BaseSettings, datetime, model_validator, Settings, DependencyUnavailable, Exception, Infrastructure failed its bounded readiness check., MonkeyPatch (+18 more)

### Community 37 - "Community 37"
Cohesion: 0.13
Nodes (11): AnalyticsWorkspace(), history(), Configuration, curveLabels, NormalizedBin, Profile, Pull, request() (+3 more)

### Community 38 - "Community 38"
Cohesion: 0.13
Nodes (10): main(), One registration shared by stdio and authenticated Streamable HTTP., HTTPInstrumentation, ASGI boundary preserving W3C trace context and counting SDK auth rejections., test_http_trace_context_and_auth_rejections(), argparse, mcp_server_transport_security, starlette_middleware_base (+2 more)

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (6): config, GET, POST, apps_web_src_app_globals, metadata, next

### Community 40 - "Community 40"
Cohesion: 0.14
Nodes (9): CorrelationMiddleware, ASGIApp, DatabaseProbe, Protocol, PlatformAPI, ASGIApp, FastAPI, test_non_http_passthrough() (+1 more)

### Community 41 - "Community 41"
Cohesion: 0.12
Nodes (8): Exception, MonkeyPatch, test_consumer_database_failure_exits_without_sql_inputs(), fail(), test_gateway_publisher_classifies_responses(), test_gateway_transport_errors_enter_retry_spool_path(), test_spool_failed_atomic_ack_preserves_original(), CaptureFixture

### Community 42 - "Community 42"
Cohesion: 0.12
Nodes (16): devDependencies, @axe-core/playwright, eslint, @eslint/compat, eslint-config-next, jsdom, @playwright/test, @testing-library/jest-dom (+8 more)

### Community 43 - "Community 43"
Cohesion: 0.14
Nodes (11): detectedEvent, pull, segment, session, signals, vehicle, window, @testing-library/jest-dom (+3 more)

### Community 44 - "Community 44"
Cohesion: 0.21
Nodes (7): LiveOBDSource, Protocol, Adapter boundary only: Phase 1 intentionally provides no hardware…, TelemetrySource, _content_hash(), IngestionService, AsyncSession

### Community 45 - "Community 45"
Cohesion: 0.35
Nodes (7): AnalysisLimitError, UUID, ValueError, SessionAnalysisService, AnalysisResult, Pull, SessionSegment

### Community 46 - "Community 46"
Cohesion: 0.10
Nodes (19): devDependencies, openapi-typescript, prettier, engines, node, name, packageManager, private (+11 more)

### Community 47 - "Community 47"
Cohesion: 0.17
Nodes (11): alembic_config, alembic_script, fixture, parametrize, Requires an explicitly supplied disposable test database. Never skips silently., test_clean_upgrade_downgrade_reupgrade_and_readiness(), test_expired_acquisition_releases_capacity_without_accepting_its_token(), test_retrospective_signed_csv_duplicates_and_analytics_identity() (+3 more)

### Community 48 - "Community 48"
Cohesion: 0.21
Nodes (4): Elm327Adapter, ElmTransport, Protocol, Generic standard-mode OBD-II reader; no proprietary or write commands.

### Community 49 - "Community 49"
Cohesion: 0.40
Nodes (4): scripts_lib_wait_http_sh, observability-validation.sh script, wait_prometheus_query(), stack-smoke.sh script

### Community 50 - "Community 50"
Cohesion: 0.32
Nodes (8): DetectedEvent, EventAnalysisResult, EventSummary, EventAnalysisLimitError, EventAnalysisService, datetime, UUID, ValueError

### Community 51 - "Community 51"
Cohesion: 0.21
Nodes (8): Scope, request_scope(), test_concurrency_bounds_require_positive_limits(), test_concurrency_rejects_excess_and_releases_after_cancel(), app(), receive(), send(), test_creation_and_acquisition_frequency_bounds_preserve_other_routes()

### Community 52 - "Community 52"
Cohesion: 0.20
Nodes (7): SanitizingExporter, test_database_error_propagation_cannot_leak_through_parent_spans(), test_database_trace_export_redacts_driver_inputs(), test_sql_text_is_removed_from_non_database_successful_spans(), ReadableSpan, SpanExporter, SpanExportResult

### Community 53 - "Community 53"
Cohesion: 0.29
Nodes (9): ErrorDetail, ErrorResponse, Health, BaseModel, Ready, Version, live(), ready() (+1 more)

### Community 54 - "Community 54"
Cohesion: 0.42
Nodes (6): TelemetryPoint, TelemetryWindow, datetime, UUID, QueryService, validate_vehicle_context()

### Community 55 - "Community 55"
Cohesion: 0.39
Nodes (4): Catalog, Any, Entity, UUID

### Community 56 - "Community 56"
Cohesion: 0.25
Nodes (6): ASGIApp, Receive, Scope, Send, Per-process budgets, with no unbounded per-client identifier dictionaries. The…, ResourceBudgetMiddleware

### Community 57 - "Community 57"
Cohesion: 0.29
Nodes (4): JSONFormatter, Any, test_json_logs_do_not_render_exception_secrets(), LogRecord

### Community 59 - "Community 59"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 60 - "Community 60"
Cohesion: 0.36
Nodes (8): Namespace, accepted(), load_exceptions(), load_findings(), main(), parse_args(), Any, Path

### Community 61 - "Community 61"
Cohesion: 0.25
Nodes (6): DATABASE_URL, ENVIRONMENT, MCP_TEST_PROJECT, mcp-validation.sh script, TEST_DATABASE_URL, TEST_KAFKA_PORT

### Community 62 - "Community 62"
Cohesion: 0.29
Nodes (3): AIOKafkaProducer, AcquisitionPublisher, Application-owned producer; bounded concurrent publication and shutdown.

### Community 63 - "Community 63"
Cohesion: 0.40
Nodes (3): Receive, Scope, Send

### Community 65 - "Community 65"
Cohesion: 0.40
Nodes (4): compose(), main(), Wait until the real Next.js status and domain proxies recover too., wait_for_browser_proxies()

### Community 66 - "Community 66"
Cohesion: 0.40
Nodes (3): KAFKA_BOOTSTRAP_SERVERS, integration.sh script, TEST_DATABASE_URL

### Community 67 - "Community 67"
Cohesion: 0.40
Nodes (3): COMPOSE_PROJECT_NAME, GIT_SHA, retrospective-validation.sh script

### Community 68 - "Community 68"
Cohesion: 0.50
Nodes (3): NOTE: This file should not be edited, ref_next_types_root_params_d_ts, ref_next_types_routes_d_ts

### Community 69 - "Community 69"
Cohesion: 0.67
Nodes (3): main(), Repeatable Phase 3 CPU/allocation benchmark; informational, never a latency…, timed()

## Knowledge Gaps
- **141 isolated node(s):** `vehicle-platform-api`, `StandardPid`, `config`, `name`, `version` (+136 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 514 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `router()` connect `Community 3` to `Community 0`, `Community 4`, `Community 36`, `Community 6`, `Community 40`, `Community 9`, `Community 44`, `Community 45`, `Community 50`, `Community 18`, `Community 53`, `Community 54`, `Community 27`, `Community 31`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `Telemetry` connect `Community 18` to `Community 0`, `Community 3`, `Community 4`, `Community 6`, `Community 8`, `Community 11`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 19`, `Community 28`, `Community 31`, `Community 36`, `Community 38`, `Community 40`, `Community 44`, `Community 45`, `Community 50`, `Community 52`, `Community 54`, `Community 57`, `Community 62`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `Settings` connect `Community 36` to `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 40`, `Community 11`, `Community 14`, `Community 47`, `Community 16`, `Community 17`, `Community 18`, `Community 15`, `Community 54`, `Community 57`, `Community 28`, `Community 62`, `Community 31`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `router()` (e.g. with `LoggingRecipe` and `AcquisitionAuthError`) actually correct?**
  _`router()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Are the 48 inferred relationships involving `Settings` (e.g. with `run()` and `AcquisitionPublisher`) actually correct?**
  _`Settings` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `Telemetry` (e.g. with `AcquisitionService` and `StreamConsumer`) actually correct?**
  _`Telemetry` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `RawTelemetryRecord` (e.g. with `Elm327Adapter` and `ReplayAdapter`) actually correct?**
  _`RawTelemetryRecord` has 30 INFERRED edges - model-reasoned connections that need verification._