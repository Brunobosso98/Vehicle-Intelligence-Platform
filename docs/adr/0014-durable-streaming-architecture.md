# ADR 0014: Redpanda-compatible durable acquisition stream

Status: accepted for Phase 4

## Context

Live collectors can disconnect, retry, and outpace persistence. Direct database writes couple hardware availability to database availability and cannot provide independent replay or consumer recovery.

## Decision

Use one internal Redpanda broker through the Kafka protocol. Phase 4 contracts use `telemetry.raw.v1`, `acquisition.status.v1`, and `analysis.live-events.v1`; canonical telemetry in TimescaleDB remains the analytical source of truth. Messages include a schema version, UUID message ID, acquisition session, safe source/vehicle references, observed and produced UTC times, sequence, provenance, and payload. Secrets, VINs, raw tokens, and location are forbidden.

Delivery is **at least once**. Producers retry and use a bounded local disk spool. Consumers disable automatic offset commit, persist the canonical sample and receipt transactionally, then commit the offset. Existing deterministic sample identity and database uniqueness make redelivery idempotent. Partitions are keyed by acquisition session; event time, not arrival order, remains authoritative. Broker development retention is bounded while TimescaleDB has no automatic destructive retention.

Redpanda is preferred over a second Kafka distribution because it preserves the Kafka client boundary with a simpler single-binary local topology. Broker endpoints remain internal; no host port is published by default. Operational tradeoffs are an additional stateful dependency, partition/offset monitoring, and explicit recovery testing.

## Consequences

Broker or database interruption is visible and recoverable: uncommitted records remain replayable, the bounded spool prevents unbounded collector memory, and overflow is counted rather than hidden. Exactly-once delivery is not claimed. Live analysis is bounded and provisional; final Phase 2/3 analysis runs from persisted event-time telemetry.
