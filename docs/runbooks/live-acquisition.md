# Live acquisition operations and physical validation

## Topology and recovery

The collector sends authenticated batches to the gateway; Kafka retains acknowledged `telemetry.raw.v1` records for development replay; `stream-consumer` commits offsets only after the stream receipt and canonical sample transaction commits. TimescaleDB, not Kafka or the bounded browser window, is the analytical source of truth. Inspect `docker compose ps`, broker topic description, consumer logs, gateway publish-failure metrics, consumer lag, and collector spool occupancy without printing tokens or telemetry arrays.

If Kafka is unavailable, the collector retries with bounded exponential delay and writes mode-0600 records to its bounded spool. It replays the spool before new adapter readings after reconnect. Full spool rejects new records visibly and increments the dropped count. If the database is unavailable, the consumer does not commit the affected offset. Restarting either broker or consumer is safe because stream receipts and canonical sample identity reject duplicates. Out-of-order observations retain collector event time; final analysis sorts by event time.

## Safe physical Vgate validation procedure

Physical Vgate vLinker validation is **PENDING**. Do not claim compatibility until this procedure is recorded with real hardware:

1. Park securely in a ventilated, lawful location and connect the adapter.
2. Run `vehicle-collector devices`, then `vehicle-collector probe`; retain only sanitized diagnostics.
3. Inspect standard Mode 01 capability discovery. Unknown and unsupported PIDs must remain explicit.
4. Select General Health and run preflight. Do not introduce BMW proprietary commands.
5. Perform stationary/non-performance acquisition first and compare target with measured rates.
6. Verify reconnect, bounded spool replay, clean stop, and adapter disconnect.
7. Capture adapter/firmware version, safe counts, rates, and error categories—never VIN, token, location, or raw secrets.

Performance pulls are separate and belong only on a dyno or lawful closed course. The platform observes; it never instructs or commands the driver or vehicle. A real BimmerLink export is required before first-class BimmerLink schema compatibility is claimed.
