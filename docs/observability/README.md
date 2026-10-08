# Observability

Phase 0 uses OTel SDK traces and metrics. Correlation middleware extracts W3C trace context,
validates or generates X-Request-ID, starts a SERVER span, attaches request.id and returns the same
ID. SQLAlchemy uses the same tracer provider. Metrics expose count, latency/status distribution and
readiness failures at /metrics. Only route templates enter metric labels; request IDs never do.
Outbound HTTP is currently in the Next.js status proxy; backend outbound HTTP does not exist yet.
JSON stdout logs contain UTC timestamp, level, service, environment, event, request_id and trace_id.
Exceptions log classification only; driver messages/SQL/connection strings are intentionally excluded.

`make observability-up` starts Collector, Prometheus, Tempo and provisioned Grafana at
http://localhost:3001. Dashboard Foundation shows rate and p95 duration; Explore Tempo finds traces
by service.name=vehicle-platform-api. Generate traffic with `make observability-check`, inspect
`docker compose logs api` for observability-smoke and match request.id to the trace's trace ID.
Prometheus at http://localhost:9090 queries http_server_requests_total and service_readiness_failures_total.

The canonical CI check is `make observability-full`. It injects unique request/trace IDs, requires
matching structured logs and a queryable Tempo trace, queries request/duration/readiness metrics from
Prometheus, checks Collector/Tempo/Prometheus/Grafana health, verifies API survival while the
Collector is stopped, and requires a second queryable trace after recovery. Evidence is written to
`.validation/observability` and uploaded by `full-validation`.

No Loki is installed: structured logs are directly readable with Compose and are sufficient for Phase 0.
Collector failure must not affect request outcomes: bounded asynchronous exporter, optional endpoint,
no startup dependency. Export failures remain visible in SDK diagnostics. Unit tests capture a real
request span and assert its trace ID equals the structured log trace ID; a live export check is separate.
The profile is local-only and unauthenticated; never publish its ports to public interfaces.

# Phase 2 analysis

Analysis traces separate telemetry loading, alignment, segmentation, pull detection, metrics and
persistence. Counters/histograms use only detector profile, version and outcome labels; IDs, VINs
and raw telemetry arrays are forbidden labels/log fields. Operational summaries include counts,
elapsed time and quality warnings.

# Phase 3 events

Event analysis emits bounded-label run, detector-duration, category production, unavailable,
insufficient-data, consolidation and failure metrics. Labels contain only detector, category, outcome,
event-type class or failure class—never vehicle/session/pull/event IDs, VIN, or raw evidence. Trace
spans separate telemetry load, baseline construction, detector execution, consolidation and
persistence. Integration through the canonical observability stack validates export alongside the
existing HTTP/SQL path; unit validation asserts the metric surface and prohibited-label absence.

## Retrospective instrumentation checks

Analytics uses the application request provider. Actual source selection, telemetry load,
comparability, RPM normalization, pull metrics, aggregation, historical build and persistence
produce bounded spans; identifiers, measurements and arrays are not span attributes. Persisted
execution emits runs/duration/insufficiency, comparison rejection, baseline contributors and
trend counters. Database exporter removes SQL text, exception events and driver status messages,
retaining operation spans and `database_error` status. No connection credentials are exported.

Unknown consumer lag, spool occupancy and duplicate counts are null in quality snapshots.
Recovery and throughput evaluators explicitly distinguish measured counts from unavailable
measurements. Configuration files alone are not acceptance evidence: run `make observability-full`
and inspect the backend-queryable traces/metrics plus failure and collector-recovery artifacts.

Retrospective runtime acceptance also performs actual CSV ingestion/query and Phase 2 analysis.
Declared instruments are insufficient evidence: import outcomes/rows, batch/query duration/points,
analysis runs/windows/segments/pulls and low-confidence output counters now follow executed services.
Delivered stage spans cover load/alignment/detection/persistence as well as analytics. Exception
redaction applies to application parent spans because database driver text can propagate there.

Retrospective runtime instrumentation records actual import/query and deterministic analysis spans,
completed/failed execution counters, accepted/rejected/duplicate input counts and batch durations.
`acquisition.broker.publish.duration` measures acknowledgement of the Kafka batch separately from
HTTP handling; the worker exposes `acquisition_consumer_buffered_points` for actual retained windows
(maximum 10 × 2,000). Labels use bounded source/outcome/profile categories, never vehicle/session IDs.

## MCP

`vehicle-platform-mcp` exports `mcp.tool.calls`, `mcp.tool.errors`, `mcp.tool.duration`,
`mcp.active.calls`, `mcp.result.items`, `mcp.truncated.results`, `mcp.auth.failures`.
Prometheus normalizes dots to underscores and appends counter/histogram suffixes. Labels are
closed tool names, transport, status and error/reason codes; no entity IDs or raw arguments.
`mcp.call.completed` JSON records request ID, trace ID, tool, outcome, duration and result count.
MCP spans parent domain selection/calculation spans and SQLAlchemy spans. SanitizingExporter
removes query text and exception events. Acceptance inspects delivered spans. Docker's `/metrics`
endpoint is scraped as job `mcp`; `mcp-up` enables the existing OTLP collector destination.

## Grounded agent

Spans: `agent.run`, `agent.context`, `agent.model_turn`, `agent.mcp_tool`, `agent.grounding`.
Each actual HTTP MCP call propagates its current trace parent to the server/domain/SQL spans.
Metrics include runs/errors/duration, MCP calls/errors/duration, grounding failures, budget
exhaustions, known token counts and active runs. Labels contain only bounded provider/tool/status
or error categories. Model names, prompts, question text, identities and keys are not metric labels.
`agent.run.completed` logs run/trace IDs, versions through persisted runs, provider/model, outcome,
duration and nullable token counters. No model reasoning or raw SQL enters telemetry.

`make agent-observability` uses the isolated agent test Compose overlay. It queries actual Tempo
and Prometheus backends, verifies successful and failing agent/MCP/database paths and checks a
secret sentinel against delivered traces, metrics, public results and logs. Evidence is stored in
`.validation/agent/observability`; configuration or a mocked exporter alone does not prove delivery.
