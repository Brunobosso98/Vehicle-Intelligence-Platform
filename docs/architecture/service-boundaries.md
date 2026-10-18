# Service boundaries

The core remains a modular monolith; Next.js runs separately. HTTP routes validate contracts and
call domain services. Telemetry owns canonical parsing, normalization, identity, ingestion and query.
Analysis owns deterministic segmentation and pulls; events owns factual anomaly evidence; analytics
owns normalized comparisons, historical baselines and configuration-segmented trends. Dependencies
flow from these services to typed domain models and database infrastructure, never to UI components.

Acquisition separates hardware adapters/recipes/collector from the authenticated gateway, Kafka
transport and consumer process. Canonical samples in TimescaleDB remain the source of truth.
Provisional windows and Kafka retention do not replace canonical storage. OpenAPI and generated
TypeScript own HTTP contract synchronization; stream messages carry explicit version 1.0.

ADRs 0011–0017 record these boundaries and delivery identities. Extraction requires demonstrated
scaling, process isolation, security or deployment needs. MCP is a read-only adapter over application services with a shared protocol registry and separate
process runtime. Its nonpersistent analytics/capability paths cannot change stored evidence.
Phase 7A owns grounded agent runs, MCP audit and public answer events. Phase 7B owns only
investigation plans, replay events, source capability reports and links to canonical sessions.
Phase 4 still owns hardware adapters, recipe hashes, sampling preflight and the collector;
Phase 6 remains read-only. The agent provider proposes semantic needs but cannot create a PID,
change a sampling rate, start a collector or mutate canonical telemetry. An operator token gates
every investigation route, while approval and session linkage use version/hash/context checks.
See [Phase 7B](phase-7b-investigation-adaptive-logging.md) and [ADR 0020](../adr/0020-investigation-recipe-and-approval-boundary.md).

Phase 9A's `features` package is a read-only consumer of canonical telemetry, sessions, pulls,
events and effective vehicle/configuration/modification context. It owns immutable feature
versions, pull FeatureSets, generation receipts and dataset definitions/build receipts. It cannot
write source evidence or invoke MCP/agents. Bounded operator CLIs perform generation and local
JSONL export; no public API or model/prediction service exists. See
[Phase 9A architecture](phase-9a-feature-engineering.md) and
[ADR 0031](../adr/0031-versioned-feature-engineering-and-temporal-datasets.md).

Specialist agents and RAG are implemented in later phases; predictive models, diagnosis and
production identity/infrastructure remain deferred.
See [Phase 6](phase-6-mcp-tool-platform.md).
