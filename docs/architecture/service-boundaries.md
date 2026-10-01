# Service boundaries

The core is a modular monolith; web is a separate UI runtime. HTTP code depends on contracts,
configuration and infrastructure through a DatabaseProbe interface. Infrastructure never depends
on UI. Contracts are generated from the running application's models, not another hand-written API.
There is no domain module until actual Phase 1 domain behavior exists.

Future modules own ingestion/source adapters, session reconstruction, event detection, analytics,
maintenance and agent/MCP interfaces. Extraction requires evidence of independent scaling,
process isolation, security boundaries or independent deployment cadence. Specify contract ownership,
idempotency, delivery guarantees, failure handling and observability before extraction.
Streaming technology is undecided until Phase 4; no Kafka-versus-Redpanda selection is implied.
