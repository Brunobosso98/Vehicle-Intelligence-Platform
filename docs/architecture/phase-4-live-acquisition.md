# Phase 4 — Streaming & Live Vehicle Acquisition

## Boundaries and flow

`VehicleDataAdapter` is read-only. The hardware-near `vehicle-collector` discovers standard capabilities, resolves a versioned recipe into a bounded sampling plan, timestamps and sequences readings, measures actual quality, and writes failures to a bounded mode-0600 spool. The acquisition gateway authenticates scoped expiring tokens before publishing versioned messages to the internal Kafka-compatible broker. A consumer persists canonical telemetry idempotently; TimescaleDB remains the durable analytical source.

Browser updates use a bounded live window rather than repeatedly querying full history. Live idle/acceleration/pull/deceleration and factual event feedback is **provisional** and may change with late data. Final Phase 2 and Phase 3 run only after persistence/finalization and are canonical, reproducible, event-time based results. Neither path diagnoses root cause.

## Recipes and quality

The six initial objectives are `general_health`, `performance_pull`, `thermal_behavior`, `fuel_delivery`, `boost_behavior`, and `data_quality_validation`. Requirements carry importance, priority, rationale, minimum/preferred Hz, and missing effects. Required absence blocks acquisition; missing recommended information degrades named capabilities. Adapter throughput reduces optional work first.

Quality is multidimensional: connection/latency, throughput, per-signal target and actual Hz, jitter, staleness/missing ratios, queue/consumer lag, spool occupancy, duplicates, reconnects, and drops. No opaque score substitutes for these measurements. Clock skew preserves both collector observation and server receive time.

## Safety and hardware status

Only standard read-only OBD-II discovery and allowlisted Mode 01 polling are implemented. No ECU writes, coding, flashing, actuator tests, proprietary BMW mappings, GPS, or control surfaces exist. Physical Vgate vLinker validation is **PENDING**. A real BimmerLink export is required before first-class parser compatibility can be claimed.

Initial hardware validation must be stationary: connect, probe, inspect capabilities, select General Health, verify actual rates, capture sanitized diagnostic logs, then stop cleanly. Performance pulls belong only on a dyno or lawful closed course; the platform observes and never commands a driver or vehicle.

## Failure and security model

Tokens are high-entropy, hashed at rest, scoped, expiring, revocable, never logged, and never carried in query strings. Batch bytes/count, sessions, clients, recipe sizes, queues, retries, and spool are bounded. Malformed/oversized/timestamp-abusive data is rejected. Broker ports are internal. Database failures do not acknowledge offsets; broker failures activate visible bounded spooling; disconnect never implies engine failure; a bad signal degrades independently.

Broker retention supports transport replay and is distinct from non-destructive canonical storage. Troubleshooting starts with collector state/spool occupancy, gateway rejection category, broker health/lag, consumer retry state, and database readiness—in that order, without dumping tokens or raw arrays.

## Retrospective execution guarantees

The shared gateway producer limits publication to eight batches and a 15-second deadline.
Publication and stop serialize on the acquisition row. Finalization captures broker partition
end offsets after stop and waits for the canonical consumer group's committed offsets.
An undrained stream returns 409 and can be retried after dependency recovery. Transaction
advisory locks serialize finalization; retries also recover a persisted `finalizing` state.

Spool replay reads bounded batches, publishes, and atomically acknowledges only successful
publication. Both new publication and replay use the same bounded retry/backoff policy.
Exhausted replay leaves pending records intact, and cancelled replay propagates cancellation.
Recovery acceptance fails fast only during intentional outages and restores the configured
retry policy while dependencies recover. Failed or cancelled publication leaves pending records on disk. Spool appends
and replacement files are fsynced; this is a single collector process guarantee and does not
claim filesystem/hardware power-loss durability or support concurrent spool writers.

Replay reads only the requested records, and acknowledgement copies remaining bytes in 64 KiB
chunks before atomic replacement. Raw spool records are capped at 64 KiB; oversized append is an
explicit counted drop, while an oversized existing record fails replay without deleting data.
The memory acceptance case measures peak allocations below 1 MB while replaying an 8 MB file.

Sequences fit nonnegative signed 64-bit integers at CSV/raw, HTTP and broker boundaries. This
matches the existing PostgreSQL BIGINT schema without a migration. An independent real Kafka
case sends a malformed over-range sequence, verifies its dead-letter classification, and then
persists the largest valid sequence through the same worker. Valid stream 1.0 messages remain
compatible; over-range messages could never satisfy the canonical persistence contract.

The worker retains the original stream payload unit in `source_metadata.source_unit` alongside
raw value, produced time and batch identity. Real integration verifies 36 km/h → 10 m/s with
original value/unit preserved, in addition to the same guarantee for direct CSV ingestion.

Consumer memory retains at most ten acquisition windows of 2,000 observations. Eviction
affects provisional feedback only. Before alignment, provisional analysis selects the latest
60 seconds of event time, including the cutoff and accepting out-of-order observations within
that window. This prevents a sparse historical gap from expanding the alignment loop; canonical
persistence and final analysis retain the complete source. The browser proxy propagates request
cancellation upstream so disconnected SSE clients release the API connection budget.
Unmeasured lag, duplicate and spool metrics in consumer
quality snapshots are null, rather than fabricated zero counts. Recovery acceptance measures
canonical identities independently. Stream version remains 1.0: valid messages are compatible;
naive timestamps, non-finite values and unsupported versions are invalid and rejected.
Recipe versions and hashes remain unchanged: availability and throughput enforcement changed,
not recipe signal requirements.

## Broker storage and observed worker health

Kafka `log.dirs` explicitly names `/tmp/kraft-combined-logs`, the persisted Compose volume,
and the image prepares that directory for its non-root runtime user. Stopping a container alone
cannot validate this boundary; recovery acceptance recreates the broker with acknowledged records
still pending and checks canonical identities after consumer restart. Existing older stacks must
preserve `/tmp/kafka-logs` before recreating the broker; see the acquisition runbook.

Recovery starts stopped database/consumer containers with `--no-recreate`, retaining their
existing configuration, including enabled observability overlays. Only the broker recreation
scenario replaces its container. A base-Compose recovery must not remove the worker's OTLP
exporter; the delivered Phase 1–5 trace gate verifies consumer stages after recovery.

The worker exports actual committed observation/duplicate counts, DB batch duration, broker lag,
provisional execution duration and newly persisted findings by actual bounded category. Its health
check requires a recent connected consumer poll, not only a living PID. Collector metrics are
exposed through an optional loopback-only CLI port. Distributed traces carry W3C context in optional
v1 provenance fields and connect collector, gateway, consumer, persistence and live analysis.

## Collector heartbeat and acquisition context

The scoped `POST /api/v1/acquisitions/{id}/heartbeat` reports adapter connection, local sample
receipt time, bounded queue/spool occupancy, explicit dropped count, discovered capabilities and
selected sampling plan. The collector sends at connection, every five seconds while collecting,
and on graceful disconnect. A failed heartbeat does not delete pending telemetry. Gateway failure
is logged with a safe category and normal spool/replay behavior remains in effect.

The server timestamps receipt and stores the report in the existing acquisition quality JSON.
Worker quality updates and canonical finalization merge their fields, preserving that report.
GET status and SSE derive `collector_health`: `not_reported` until measured, `silent` after more
than 15 seconds without heartbeat, `disconnected` when explicitly reported, and `stalled` after
more than 15 seconds without a local sample receipt while heartbeats continue. These describe
collection freshness, not vehicle health; historical/replayed event timestamps do not mark a
currently connected collector stale. The live UI shows collector state separately from browser SSE.
Future receipt times beyond five seconds, naive times, invalid credentials and closed sessions fail
explicitly. Limits preserve bounded payloads and metric labels use connection state only.

When configuration is omitted at creation, the current effective configuration for that vehicle
is selected, when one exists. Explicit configuration and every observation still undergo owner
and effective-date validation. Finalization persists the dataset capability report with the
acquisition's pinned recipe hash; returning a JSON report alone is insufficient historical evidence.

## Explicit CSV mapping and live recovery

Generic wide CSV imports require an explicit mapping; no proprietary exporter format is inferred.
`POST /api/v1/sessions/{id}/imports/csv/preview` accepts a CSV and optional multipart `mapping`
JSON with `timestamp_column`, optional identity/sequence columns and canonical `signals`
(`column`, `signal`, original `unit`). Without a mapping, noncanonical headers request one.
Preview normalizes at most 25 observations, lists ignored columns, and explicitly does not
validate the entire import or persist observations. Full import validates every record.
Supported canonical units, aware timestamps, distinct roles and bounded nonempty identities
are mandatory. Mapping version 1.0 and its SHA-256, original column and original value persist
in existing telemetry provenance fields. Retrying the same mapping preserves canonical identity.
Unsupported proprietary identifiers need verified mappings; BimmerLink parsing remains deferred.

Sampling algorithm 1.1 reserves every required minimum before distributing extra budget in
priority order. Insufficient required rates block collection; optional under-rate channels degrade
capabilities. Synthetic adapters honor each selected rate. Standard OBD-II malformed/NO DATA reads
mark that channel unavailable while other channels continue; subsequent valid reads restore it.
Periodic authenticated heartbeats refresh the capability snapshot without issuing extra PID reads.

The spool reports measured normal (<70%), warning (70–<90%), near-capacity (90–<100%) and
capacity-reached (100%) states. Rejected append attempts still increment explicit dropped counts
and log capacity rejection even when remaining space cannot fit a full record. Queue capacity is
bounded at 100,000 observations and spool capacity at 1 GiB; defaults remain 1,000 and 10 MB.

SSE `telemetry` snapshots now include additive `schema_version: "1.0"`; existing fields retain
meaning and older clients may ignore the added field. OpenAPI declares `text/event-stream`,
not a JSON response. Snapshots are bounded views of canonical persisted observations; reconnect
replays the current view rather than generating new ingestion records. Integration exercises
completed streams, reconciliation, schema version and media type; ingestion replay tests cover
canonical idempotency. Browser/device states remain distinct. The UI displays authenticated
collector queue/spool/drop measurements when present and preserves unavailable values otherwise.
Finalization can be retried after a dependency failure without repeating the already acknowledged
stop. Starting a replacement collection or changing vehicle remains disabled until final results.
A missing-recommended-signal simulation uses the same actual preflight API and collector scenario,
with a real browser acceptance assertion for degraded readiness and unavailable boost analysis.

Acquisition HTTP work has explicit local token-bucket bounds (100-request burst, 100/second;
creation burst ten, ten/minute), at most 64 simultaneous requests, ten SSE clients and four
expensive deterministic analysis requests. Correlated HTTP 429 includes `Retry-After` and does
not close an existing acquisition. Limits require constant memory and release reservations on
client disconnect/cancellation. The local single-process scope is explicit in the threat model;
Phase 6+ distributed infrastructure is not introduced.

The serialized ten-session limit counts collecting states with unexpired credentials. Expired
credentials remain rejected and canonical records remain preserved. Stopped/finalizing sessions
retain retryable finalization without consuming a collector slot. Finalization shares the
four-request expensive-analysis budget. A missing live
resource returns the correlated HTTP 404 envelope before opening SSE; disappearance during an
existing stream retains its in-stream error. Browser offline events close the upstream stream,
display disconnection immediately, and reconnect on the browser online event.

The persisted live quality checkpoint includes the gateway publication-to-canonical-commit
latency for the latest accepted observation and the real broker high-watermark remaining count
after its poll. These are timestamped measurements, not an assertion that a previously healthy
component is still connected. Negative latency from clock disagreement remains unavailable.
Direct persistence fixtures have no actual broker poll and preserve a null lag. Pipeline state
is evicted with its ten bounded acquisition windows; no identity-labelled metrics are introduced.
The UI exposes the measured checkpoint, explicit unavailable values, observed collection elapsed
time and final canonical observation/gap counts. These additive optional fields preserve SSE 1.0
compatibility and share the generated Pydantic/OpenAPI/TypeScript contract.
