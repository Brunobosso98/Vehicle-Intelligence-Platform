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

## Investigation and adaptive logging

Committed transitions emit `investigations.total`, `investigations.completed`,
`investigations.inconclusive`, `investigations.failures`, `investigations.hypotheses`,
`investigations.evidence_gaps`, `investigations.unavailable_signal_needs`,
`investigations.recipes_proposed`, `investigations.recipes_feasible`,
`investigations.recipes_degraded`, `investigations.approvals`, `investigations.reanalyses`
and `investigations.duration`. Prometheus normalizes names as usual. Counters have no vehicle,
session, investigation, question or source labels. A committed transition creates a bounded
`investigation.<event>` span under the request context and a structured
`investigation.transition` record with plan/run IDs, counts, state, recipe version/hash,
feasibility, approval state, linked session count and duration. Logs omit source reports,
telemetry payloads, provider keys, operator tokens and private reasoning. The follow-up AgentRun
retains the Phase 7A MCP/domain/database instrumentation.

The API also logs bounded `investigation.planning.completed`,
`investigation.existing_evidence.completed` and
`investigation.recipe_generation.completed` timing/count events. They carry only run or
investigation identifiers, elapsed seconds and bounded counts; questions, credentials and
provider text are excluded. The deterministic benchmark reads these process-local events to
separate provider planning and Phase 4 recipe selection from total HTTP latency.

## Phase 7C supervisor

Spans add `agent.supervisor`, `supervisor.routing`, sibling `supervisor.specialist` and nested
`specialist.model_turn`. Actual MCP requests continue propagating the same trace into deterministic
domain reads and SQL. Public role results retain the trace ID, version, duration and nullable usage.
The final Phase 7A synthesis has its own usage subtotal; parent usage sums routing, specialists and
synthesis. Deterministic known token counts are zero; unknown monetary cost stays null.

Counters add `supervisor.runs`, `supervisor.routing`, `specialist.runs`, `specialist.failures`,
`specialist.tool.calls`, `supervisor.conflicts`, `supervisor.insufficient`,
`supervisor.phase7b.proposals`, `supervisor.evidence.cache.hits` and
`specialist.tool.policy.rejections`. Histograms add `supervisor.specialists.selected` and
`specialist.duration`. Labels are bounded role, intent, status, sufficiency and error values.
Identifiers, tool arguments and questions never become metric labels.

## Phase 9F agent prediction evidence

The agent records `agent.prediction_evidence.operations` and
`agent.prediction_evidence.duration` with only the bounded `outcome=success|error` label. They
contain no vehicle, configuration, session, pull, source evidence, receipt, feature-set, score,
question or model-hash attributes. The `agent.mcp_tool` trace retains the bounded tool name; the
source verifier spans carry no source identifiers. `make prediction-agent-observability` checks
the exported metric names and inspects metric/span attributes from the actual disposable
AgentService + MCP run. Acceptance records fixture measurements and redaction results under the
ignored `.validation/phase9f/acceptance.json`; it is not a production service-level objective.

Structured routing, sufficiency and specialist completion records contain run/trace IDs, selected
and skipped roles, state, counts, outcome, duration and the Phase 7B recommendation. They omit
raw telemetry, credentials and private reasoning. `make supervisor-observability` queries actual
Tempo/Prometheus delivery and checks sibling trace parents plus redaction; artifacts belong to
`.validation/supervisor/observability`. Delivery is not verified until the command succeeds.

## Phase 8 knowledge retrieval (implementation checkpoint)

The knowledge service emits `retrieval_requests_total`, `retrieval_latency_seconds`,
`retrieval_candidates_total`, `retrieval_knowledge_gap_total`,
`retrieval_wrong_platform_rejections_total` and `retrieval_cache_hits_total` through the application
OTel provider. Spans currently cover `knowledge.retrieval`, candidate lexical/vector selection and
fusion/reranking. Structured retrieval summaries record bounded operational metadata without query
text, chunk bodies, source URLs, API keys or SQL. Vehicle/document IDs must never become metric labels.

SQL engine/platform exclusions happen before candidate return; the rejection counter currently counts
only incompatibilities rejected by application reranking, so it is not a count of all SQL exclusions.
Cache hits still produce independent retrieval/evidence IDs and audits. A candidate-cache revision
checks source versions, current documents, conflicts and active index before reuse.

Embedding usage/cost/cache/reservations are durably recorded by the local ledger and paid-command
receipt. Ingestion emits `knowledge_ingestion_total`, `knowledge_ingestion_failures_total` and
`knowledge_chunks_total` after transaction completion. Idempotent replays count completed operations,
not unique documents. Embedding instrumentation counts attempted endpoint calls, successfully
accounted tokens/cost, and cache reuse; uncertain failed reservations remain visible in the ledger.
Metrics never carry source, vehicle, document, query or credential labels.

The October 16 `make knowledge-observability` checkpoint delivered retrieval, ingestion and embedding
metrics to Prometheus and spans to Tempo, including intent, combined SQL lexical/vector selection,
fusion/reranking, evidence and grounded synthesis. The operator probe executes real repository
ingestion and the actual SDK/embedder boundary with a network-disabled synthetic HTTP transport and
an isolated fixture ledger. It proves instrumentation delivery, not OpenAI quality or paid usage.
Its internal-only metrics listener runs in the disposable test container; production gains no new
ingestion endpoint. `.validation/knowledge/observability/` contains backend-queryable proof and
redaction checks; final committed-head delivery must still be repeated.

## Phase 9A feature pipeline

The feature pipeline exports bounded counters for generation runs, generated/reused FeatureSets,
generation failures, null reasons by feature category, leakage rejections, dataset builds, dataset
rows and excluded rows. Histograms record generation and dataset-build duration. Labels use only
bounded outcome, error, feature-category, missing-reason and leakage-reason values; vehicle,
configuration, session, pull, sample IDs, raw values, source text and SQL never become labels.

Traces cover `features.generate`, configuration resolution, telemetry/history reads, computation
and dataset build. Span attributes contain versions and aggregate counts only. `make
feature-observability` performs real generation, a deliberate cutoff rejection and dataset build in
a fresh disposable database, then asserts rendered metric series, expected spans and the absence
of entity identifiers. It does not rely on configuration-only instrumentation claims.

## Phase 9B offline model pipeline

The model pipeline exports bounded training-run and failure counters, label exclusions, candidate
and evaluation counts, dataset-row histograms, candidate-training duration and artifact-size
histograms. Labels contain only task, candidate family, model state and bounded reason categories;
dataset/model identifiers, checksums, VINs, vehicle/configuration/session/pull IDs, feature values,
raw samples and credentials are excluded. Traces cover dataset materialization, label generation,
temporal splitting, leakage validation, candidate training, validation selection, final test
evaluation, artifact staging and model registration. `make model-observability` runs the disposable
acceptance and checks rendered metrics, observed spans and entity-ID exclusion. Evidence is written
to ignored `.validation/phase9b/acceptance.json`.

## Phase 9C offline anomaly pipeline

The anomaly service records bounded fit/run state and duration, eligible reference rows and
exclusions by reason, finding counts by family/method/status, score/threshold distributions and
artifact bytes. Traces separate reference materialization and eligibility, fit, artifact staging
and validation, validation threshold selection, target materialization, observation scoring and
finding persistence. Labels use fixed family, method, lifecycle, status and reason vocabularies;
they never contain vehicle, VIN, configuration, session, pull, FeatureSet or artifact IDs. The
independent disposable evaluator verifies actual span capture, rendered anomaly metrics and entity-ID
absence. Evidence is written beneath ignored `.validation/phase9c/`.

## Phase 9D controlled prediction service

The serving boundary records bounded request/receipt counts, admission denials, in-flight work,
approval transitions, artifact-load duration and request duration. Labels use only endpoint,
result kind, status and reason categories. Spans cover admission, binding resolution, FeatureSet
lookup, artifact verification, supervised/anomaly scoring and receipt persistence. Logs include
bounded categorical request context only; tokens, VINs, entity IDs, feature values, source or
provenance hashes, and artifact paths are excluded. The independent HTTP evaluator checks actual
spans and rendered metrics and measures latency/RSS as observations, not fixed cross-machine SLAs.
Evidence is written beneath ignored `.validation/phase9d/`.

## Phase 9E prediction evidence

The evidence service measures `prediction_evidence.operations`, `prediction_evidence.replays`,
`prediction_evidence.gaps`, `prediction_evidence.duration` and
`prediction_evidence.graph_size`. Labels use only operation/outcome, bounded gap reason and graph
dimension. Spans cover source resolution, claim construction, canonical hashing, immutable
persistence, safe projection, independent verification and audit append. IDs, VINs, checksums,
artifact paths and feature values are excluded from metric labels and span attributes.

`make prediction-evidence-observability` checks the actual 9E HTTP acceptance metrics and spans
captured in `.validation/phase9e/acceptance.json`, including redaction. This check requires the
preceding disposable-DB acceptance; a declared instrument or empty metrics endpoint is not proof of
delivery.

## Phase 9G evaluation and calibration

The offline evaluator emits `evaluation.runs`, `evaluation.failures`, `evaluation.duration`,
`evaluation.dataset.rows`, `evaluation.dataset.sessions`, `evaluation.calibration.candidates`,
`evaluation.abstentions`, `evaluation.abstention.reasons`, `evaluation.integrity.violations`,
`evaluation.research_artifact.bytes`, and `evaluation.drift.features`. Labels are bounded protocol
values for source role, run status, candidate method/status, abstention reason, integrity reason, and
canonical feature family. Vehicle/configuration/session/pull IDs, VINs, feature values, paths,
checksums, row identities, and credentials never become metric labels. Spans record aggregate
counts and bounded phase/task names only. `make predictive-reliability-observability` verifies the
actual metrics and spans in the exact-SHA disposable acceptance receipt; this is fixture evidence,
not a production SLO or a claim of real-world predictive validity.
