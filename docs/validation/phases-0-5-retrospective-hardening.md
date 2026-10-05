# Phases 0–5 retrospective hardening

Audit date: 2026-10-04. Branch: `codex/pre-phase6-retrospective-hardening`.
Merged Phase 5 baseline: `6282982483c99d2500a446dc82c747dd2ea81606`.

**Local status: Phases 0–5 VERIFIED by a clean isolated run of `make verify` against the committed HEAD. Pull-request CI is the remaining external acceptance gate.**

## Repository SHA and execution evidence

The exact validated repository SHA is recorded in the generated commit-tied report and
`manifest.json` under `.validation/retrospective/runs/<isolated-project>/`. Generate these using
`bash scripts/retrospective-validation.sh committed` after logical commits and with a clean tree.
That report includes the complete text of this tracked report with the actual SHA, date, command
results and artifact/log digests. A Git commit cannot embed its own content-derived SHA; this tracked document
specifies the report/attestation location rather than falsely claiming an older SHA was validated.
The PR and final delivery must cite the same attested HEAD. The latest clean isolated committed-state PASS manifest and its checksummed artifacts are retained under `.validation/retrospective/runs/`.

## Architecture assessment

The implementation remains a local modular application: read-only acquisition → bounded Kafka
transport → canonical Timescale telemetry → deterministic temporal analysis → factual events →
versioned automotive analytics. It provides no diagnosis, vehicle control, ECU write, MCP, agent,
RAG or learned inference. Context, timestamps, canonical units, sample identity and immutable run
provenance must agree at every boundary. Generic ELM327 support is distinct from physical BMW/Vgate
capability and cannot prove proprietary channels.

Persistence uses one linear Alembic graph through Phase 5. Applied revisions 0001–0008 are unchanged.
Retrospective behavior corrections require algorithm/version identities, not a new database schema.
Existing earlier-phase data and immutable historical analytics remain auditable. SQLAlchemy is pinned
and locked to 2.0.54 because the pinned OTel SQLAlchemy integration excludes 2.1.

See [traceability ledger](phases-0-5-traceability-ledger.md),
[ADR 0017](../adr/0017-retrospective-evidence-and-execution-identity.md), and the
[API operation inventory](phases-0-5-api-inventory.md).

## Per-phase classification

| Phase                      | Local classification | Evidence in the exact committed-state run                                             |
| -------------------------- | -------------------- | ------------------------------------------------------------------------------------- |
| 0 — engineering foundation | VERIFIED             | `make verify`, locked bootstrap, security, accessibility, readiness and observability |
| 1 — telemetry core         | VERIFIED             | canonical import/query acceptance, integration, contract and browser coverage         |
| 2 — sessions and pulls     | VERIFIED             | independent 5/10/20 Hz evaluator, benchmark and persisted/browser flows               |
| 3 — factual events         | VERIFIED             | all 14 positive/negative scenarios, ground-truth scoring and browser coverage         |
| 4 — live acquisition       | VERIFIED             | real broker/consumer/database/API recovery, spool replay, E2E and 100k benchmark      |
| 5 — automotive analytics   | VERIFIED             | numerical/history acceptance, persisted recompute, browser flows and trace coverage   |

## Gaps found and corrections

- The mypy Makefile invocation did not load the declared strict configuration. Explicit config
  selection now checks all API sources and real-stack benchmark scripts, with no typing relaxation;
  unused ignores, the SSE iterator annotation and typed benchmark/query results were corrected.
- The original Phase 1 measured ingestion protocol had no executable baseline. Disposable integration
  now ingests/replays 100,002 observations, verifies measured 1,000-row batches and canonical counts,
  and records actual query/truncation, analyzed buffers/plan, CPU/RSS and versions.
- CSV parser accepted malformed columns and failed input with accidental server errors; finite
  normalization, strict parsing, signed numeric values, context/resource checks and atomic identity
  accounting now cover replay, corruption and configuration-at-observation validation.
- Pull detection split increasing physical pulls at carried-forward sampling plateaus. Detection 1.1
  preserves deterministic physical growth gates and rejects idle/cruise/short/noisy negatives.
- Event evaluation hid unexpected detections. Acceptance now scores every detection per scenario,
  includes declared incidental synthetic consequences and temperature cases, and fails quality/boundary
  regressions. Sustained event rules no longer combine separated spikes across gaps.
- Collector spool entries were deleted before publication. Ordered durable peek/ack, atomic fsync,
  bounded retry, HTTP transport handling and cancellation preservation now keep pending records.
- Each HTTP batch created a broker producer. Application-owned acknowledged publication is bounded;
  stop/publication serialize, and finalization waits for committed offsets without joining the worker
  group. Finalization state can recover after a crash. Segment/event findings reconcile to canonical IDs.
- Kafka wrote outside its named volume. The explicit log path and non-root owned image directory now
  match the mount. Existing logs were preserved before migration; acceptance must recreate the broker
  with acknowledged undrained messages, which simple process restart cannot prove.
- Finalized dataset capability was returned without a historical report row. Finalization now persists
  the exact report and pinned recipe hash; real integration compares the stored and returned JSON.
- Ingestion/analysis/worker/collector metrics and calculation spans were declared without sufficient measured coverage.
  Actual publication, committed persistence, duplicates, lag, new findings, queue/spool and duration
  are now instrumented. W3C context links collector/API/consumer. Database export removes SQL and driver
  exception details; unknown quality counters remain unavailable rather than fabricated zeros.
- Collector heartbeats were absent, and acquisitions could omit an existing active configuration.
  Authenticated bounded reports now preserve capability/plan and actual receipt freshness; status/SSE
  distinguish silent, stalled and disconnected collection. Creation selects active context when omitted.
  Explicit error statuses are now declared in OpenAPI alongside runtime rejection tests.
- Analytics reuse ignored changing measurements and selection roles. Full input/context fingerprints,
  semantic selectors, version 1.1 and identity locks preserve immutable recomputation.
- Normalization, paired statistics, historical envelopes, configuration isolation and before/after
  chronology could produce misleading evidence. Shared windows, per-pull center envelopes, sufficient
  configuration-specific history and explicit rejection now govern conclusions.
- Missing session summaries, live charts and factual before/after deltas were exposed. Comparison
  curves now share axes, preserve gaps, display units/coverage and canonical event references; multiple
  signals and observed acceleration are selectable. Baseline dates/contributors/latest-relative values
  and segmented history expose measured evidence.
- Thermal rate, observed acceleration and configurable speed intervals were incomplete. Continuous
  measured inputs now support them. Between-pull recovery reports observed endpoint delta/elapsed time;
  unobserved threshold timing remains explicitly unavailable.
- Generic wide CSV mapping and bounded preview were missing. Explicit canonical column/unit roles,
  mapping hashes, ignored-column disclosure and raw-column provenance now preserve auditable imports.
- Sampling budget allocation could starve a required channel despite sufficient total capacity.
  Algorithm 1.1 reserves required minima; the synthetic adapter now honors per-signal rates. A failed
  standard PID marks only that channel unavailable. Heartbeats refresh capabilities and measured
  queue/spool/drop state; spool capacity warnings have deterministic thresholds.
- Live SSE lacked an explicit version and generated payload contract. Typed version 1.0 snapshots
  retain existing fields and correct the OpenAPI media type. Global vehicle selection now scopes all
  panels consistently, and finalization can recover from failure without repeating a closed stop.
- Original Phase 4 frequency, simultaneous SSE and total calculation budgets were absent. Constant-
  memory local request/creation token buckets and bounded live/request/analysis counters now return
  correlated 429 with Retry-After, releasing reservations on completion, disconnect and cancellation.
- Earlier E2E relied on retained history and headings. Tests own deterministic history and assert actual
  numeric deltas, contributors, canonical counts, insufficiency and live-to-final state transitions.
- Recovery started the consumer using base Compose and replaced its enabled OTLP configuration.
  Stopped dependency containers now recover without recreation, preserving their runtime overlays;
  the broker still undergoes actual container recreation. Delivered consumer spans remain mandatory.
  The focused recovery and delivered-trace proof passed after this correction. Observability waits
  for all actual fixture rows before finalization, since Kafka acknowledgement does not imply that
  the recovering worker has finished persistence. Native driver startup failures now also exit with
  the structured safe error, without exporting exception text or telemetry inputs.
- Sparse observations could require iterating years of empty alignment ticks. Empty expired grid
  positions now jump to the next observation while preserving grid origin, expiry and gap flags.
  Spool replay uses bounded record reads and streaming atomic acknowledgement rather than loading
  the whole pending file; measured allocation and partial-write cases verify those bounds.

## Test and migration evidence

The successful isolated committed-state run covers 219 backend cases and 32 frontend cases. API line coverage
is 98.65%, branch 93.20%; frontend statement coverage 95.90%, branch 86.34%, function 97.32%,
line 97.19%. Six disposable Timescale/Postgres integration cases passed, including explicit CSV
mapping preview/no-write, provenance, idempotent replay, expired-token capacity/rejection, and
real Kafka malformed-sequence dead-letter/recovery with valid BIGINT-edge persistence. All six passed in the clean isolated committed-state run.

An earlier full attempt failed the delivered Phase 1–5 trace check after recovery replaced consumer
configuration. Recovery now preserves the enabled OTLP overlay, and the successful clean committed-state
run passed delivery checks. Earlier failed attempt logs remain local evidence only and never count
as acceptance.

Disposable real Timescale/Postgres integration discovers the single migration head/direct parent,
executes clean base→head, meaningful Phase 3/4 and Phase 4/5 rollback boundaries, full base rollback,
re-upgrade and repeated head. It checks actual earlier telemetry values, relational rows, Timescale
extension, hypertable and Phase 5 restoration/use. All six disposable migration/integration cases passed in the clean isolated committed-state run.

Independent gates cover Phase 1 CSV/canonical identity; Phase 2 positive/negative pulls at 5/10/20 Hz;
Phase 3 all 14 scenarios without type filtering; Phase 4 all six recipes; Phase 5 numerical values,
chronology, insufficiency and configuration membership. Exact latest numeric results belong to the
final command logs/manifest. Prior candidate failures remain in ignored local evidence; none are
expected-failure substitutes or reasons to lower thresholds.

## Failure, performance, security and observability

The complete clean isolated committed-state `make verify` passed. Mandatory runtime evidence includes broker restart/recreation,
consumer restart, database interruption, API transport interruption, bounded spool/replay, canonical
identity/loss counts, streamed gap event, browser disconnect/recovery and canonical reconciliation.
The live stream benchmark queries actual receipts and canonical identities at 100,000 observations;
analysis/event/analytics benchmarks measure substantive calculation paths and identify memory scope.
The stream benchmark samples actual container memory and bounded consumer windows at 25k intervals
and measures broker acknowledgement latency separately from gateway HTTP latency.

Security must run the unchanged complete scanner/policy gate. An earlier initial full scan passed
its reviewed image policy, including previously accepted High findings; that is not a claim of zero
vulnerabilities in every image. No new exception or security threshold relaxation is authorized.
Manual review covers read-only OBD allowlists, bearer hash/expiry/session scope, finite/aware uploads,
SQL binds, bounded requests, loopback exposure and privacy-safe errors/logs/traces.

`observability-full` verifies actual log correlation, Prometheus results, Tempo delivery, dependency
failure and collector recovery, then exercises Phase 1–5 measured paths and checks source/calculation/
normalization/aggregation/persistence and collector/worker spans, services and SQL/token redaction.
Configuration files alone never establish delivery.

The prior full run's accessibility timeout was traced to axe's recursive partial-frame mode on a page with no iframes. The smoke test now runs axe's complete page analysis (44 rules, zero violations in a 587 ms diagnostic); the subsequent isolated run passed all eight E2E cases. No accessibility rules were disabled and no timeout was raised.

## Exact acceptance and reproducibility

Use the repository's pinned Node/Python tooling:

```sh
make bootstrap
make phases-0-5-acceptance
make test-integration
make up
make stack-check
make phase4-stack-acceptance
make test-e2e
make live-stream-benchmark
make security
make observability-up
make observability-full
make verify
bash scripts/retrospective-validation.sh committed
```

`verify` includes API/web lint, types, coverage, contract/docs/format checks, production frontend build,
independent acceptance/evaluation and benchmarks, security-cloud, containers, disposable migrations/
integration, real stack/recovery/browser/100k streaming, full security and delivered observability.
The clean-state script creates a new isolated Compose project, stops the prior project without
removing its volumes, runs locked bootstrap plus complete verify, deletes only its own disposable
volumes and restores prior running services. Build caches remain content-addressed; new containers,
Kafka data, DB schema/data and observability state are fresh. This is not a cold public-registry claim.

## Limitations and deferred original scope

Physical Vgate/vLinker and real BimmerLink export compatibility remain PENDING by original scope.
Proprietary BMW signals, ignition/misfire/lambda diagnosis, uncertain installation-time inference,
ECU control, ML/MCP/agents/RAG and managed production infrastructure are excluded. Authentication,
TLS/accounts/managed deployment for Internet production belong to later roadmap scope; passing a
local engineering gate cannot establish that deployment. In-memory collector batching has a bounded
abrupt-process/power-loss window until durable spooling; durable acknowledged spool recovery is the
measured guarantee. No unobserved recovery trajectory or device health may be invented.

## Delivery state

Three logical commits are present on the hardening branch. Exact committed-state local acceptance passed. The branch and PR are review-only; final delivery also reports the remote CI result. This work does not merge main.
