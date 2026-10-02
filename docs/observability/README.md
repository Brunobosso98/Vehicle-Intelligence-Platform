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
