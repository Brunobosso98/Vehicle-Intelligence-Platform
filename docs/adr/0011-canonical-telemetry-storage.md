# ADR 0011: Canonical telemetry storage and retry identity

## Status
Accepted — 2026-10-02.

## Context
Phase 1 needs extensible, high-volume observations without a column migration for every PID. Imports may be retried, reordered, or conflict. Query load is primarily session/signal/time and vehicle/time.

## Decision
Store one normalized numeric observation per row in a Timescale hypertable partitioned daily on `observed_at`. Keep canonical signal key/unit beside raw name/value, source identity, event and ingestion times, sequence, quality, schema version, metadata, and a content hash. Index session+signal+time and vehicle+time. A SHA-256 sample identity covers session, source, source record ID, UTC observation timestamp, canonical signal, and optional sequence. Equal identity/content is a measured duplicate; equal identity/different content is rejected and never overwritten.

Canonical physical storage uses SI-oriented Pa, K and m/s, while RPM, percent and volts remain domain-standard. Missing or ambiguous units are rejected, not guessed. Naive timestamps are rejected; aware timestamps normalize to UTC. No destructive retention policy is installed.

## Alternatives considered
One wide table per logger; JSON-only samples; ingestion order as event order; last-write-wins; an external signal service; immediate compression/retention.

## Consequences and risks
New signals are catalog changes rather than table changes. Row volume is higher than a wide shape, but multi-signal sparsity and provenance remain explicit. Catalog/conversion changes require versioning and tests. Compression and retention require measured, separately reviewed rollout evidence.
