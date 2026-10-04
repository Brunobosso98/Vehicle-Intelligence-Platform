# ADR 0017: Retrospective evidence and execution identity

## Status

Accepted. Extends [ADR 0016](0016-deterministic-versioned-automotive-analytics.md) and
[ADR 0014](0014-durable-streaming-architecture.md).

## Context

Retrospective inspection found that green gates could hide unexpected events and that analytics
reuse identified only pull IDs. A different trend metric or a reversed before/after selection could
reuse the wrong result. The collector deleted its spool before successful publication and HTTP
connection exceptions escaped its retry path. The API created a Kafka producer for every batch.

## Decision

Evaluate each independent golden scenario before aggregation, count every detection, and fail
acceptance on quality or boundary violations. Declare incidental scripted consequences in ground
truth rather than filtering detections by the requested injection. Golden numerical expectations
must inspect computed results, including order-sensitive thermal endpoints and acceleration.

Analytics version 1.1.0 hashes the canonical inputs and semantic selection (trend metric and
before/after membership) in addition to the algorithm and configuration. A transaction advisory lock
serializes requests for the same identity. Immutable recomputation and older runs remain auditable.
Comparisons use the shared RPM window; incompatible contexts suppress factual delta conclusions.
Historical envelopes aggregate eligible pull-bin centers, validating acquisition gaps within each
pull rather than interpreting intervals between historical sessions as acquisition gaps.

The API owns one lazy Kafka producer through its lifespan, limits concurrent publish work to eight
batches, and bounds a publish request to fifteen seconds. Shutdown closes the producer. Transport
still uses acknowledged at-least-once delivery with canonical identity deduplication. Stream schema
1.0 and logging recipe hashes do not change.

Publication and stop serialize on the acquisition row. Finalization observes broker end offsets
using manual assignment without joining the canonical consumer group, then requires committed
persistence offsets. An undrained stream returns a retryable conflict. A dedicated transaction
advisory lock serializes finalization; persisted `finalizing` state can recover after a crash.

Before/after results require chronological, comparable operating contexts and report numerical
common-window differences. Session summaries include actual canonical counts, segments and events.
Empty history remains explicit insufficient evidence. Calculation stages use request-scoped trace
providers; a sanitized database exporter omits SQL text and driver exception detail.

Collector replay peeks at bounded durable records and acknowledges them atomically after publish.
An interruption preserves pending records, allowing duplicate delivery rather than silent loss.
Filesystem writes execute outside the async event loop. A spool has one collector owner.
Kafka's explicit log directory matches its named persistent volume; acceptance recreates the
broker with undrained acknowledged messages. Existing misplaced logs require preserved migration.
Worker readiness requires a recent real poll. Metrics count committed records and new findings;
W3C trace context crosses the unchanged v1 envelope's optional provenance map.

Normalized comparison charts share axes. Canonical event markers are references to persisted facts.
Observed acceleration and thermal rates require continuous measured input; configurable speed
intervals are bounded and hashed. Unobserved recovery-threshold timing remains explicitly absent.

## Alternatives

Keeping pull-ID-only reuse would preserve stale evidence. Disabling reuse would remove an original
requirement. A new cache service or infrastructure is unnecessary for this local modular system.
Deleting a spool before replay cannot establish the original zero-loss reconnect guarantee.

## Consequences and risks

Fingerprinting costs scale with the bounded selected inputs. Advisory locks can serialize expensive
identical requests; they do not lock telemetry tables. A producer timeout has an ambiguous outcome,
so retry may duplicate envelopes; canonical IDs remain the deduplication boundary. Atomic spool
acknowledgement rewrites bounded pending bytes, trading I/O for recovery safety. Power-loss guarantees
and multiple-process access to one spool still require explicit evaluation. Physical OBD hardware
remains pending; no proprietary signals or vehicle controls are introduced.
