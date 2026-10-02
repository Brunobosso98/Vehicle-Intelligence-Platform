# Phase 1 vehicle and telemetry core

The modular API owns Vehicles, historically effective VehicleConfigurations, Modifications, manually/imported DrivingSessions, a canonical signal catalog, adapters, ingestion and bounded query services. It remains one deployable service. Live OBD is an interface only: no ECU write, actuator, flash or physical-connection claim exists.

## Canonical import contract

CSV is UTF-8 and has exactly `timestamp,signal,value,unit,record_id,sequence`. Timestamp is ISO 8601 with an explicit offset. Sequence may be blank. Inputs use a catalog key or alias. Formula-prefixed cells, unknown columns/signals, unknown units, naive/malformed timestamps and uploads over 10 MB are rejected or counted. Raw uploads and VINs are not logged. Compressed uploads are unsupported.

Canonical units are Pa, K and m/s plus rpm, %, and V. Supported conversions include kPa/bar/psi to Pa, °C to K, and km/h/mph to m/s. Range failure preserves the value with `out_of_range` quality. Validity vocabulary is valid, missing, malformed, unsupported, out_of_range, duplicate, and source_error.

Event time is distinct from UTC ingestion time. Arrival may be out of order; queries sort by event time, signal, sequence and sample ID. Naive timestamps are rejected. Original timezone context belongs in session/source metadata.

## Query and operations

`GET /api/v1/sessions/{id}/telemetry` requires canonical signals, allows a half-open window, defaults to 2,000 points and cannot exceed 10,000. `truncated` tells callers to narrow the window. No retention policy or continuous aggregate exists. Troubleshooting: 415 means wrong media type; 400 means structural/encoding/size/parser failure; counters identify row-level issues; 422 means request/window/signal validation.

The seeded synthetic normal-driving adapter creates plausible correlated idle/acceleration/cruise, throttle, boost and thermal ramps. It is test data, not a calibrated N55 simulation, and performs no Phase 2 detection or diagnosis.

## Performance baseline protocol

Generate at least 100,000 synthetic observations, ingest in 1,000-row batches into disposable TimescaleDB, and record CPU/RAM, versions, elapsed time, observations/second and query plan. No unmeasured SLO is claimed and benchmark timing is not a CI gate.
