# Data principles (future telemetry)

Raw telemetry is immutable; transformations produce derived versions with provenance.
Use timezone-aware UTC timestamps and keep original timestamp/source timezone when normalizing.
Separate event time and ingestion time. Preserve source ordering and detect out-of-order arrivals.
Canonical units will use SI: pressure Pa, temperature K, speed m/s, mass kg and time s.
Display conversions must preserve original values and transformation history.

Missing is not zero. Record sensor quality, uncertainty and source sampling limitations.
Every important observation identifies vehicle, session, source/sensor, timestamp, schema version,
raw value and meaningful transformation history. Imports require explicit idempotency keys and
duplicate handling in Phase 1. Reproducible analysis records source dataset hashes, code/schema/model
versions and parameters. No ingestion or telemetry schemas are implemented in Phase 0.
