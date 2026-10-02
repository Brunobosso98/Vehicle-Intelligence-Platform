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
