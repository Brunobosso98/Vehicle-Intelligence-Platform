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
Agents, RAG, ML, diagnosis and production identity/infrastructure remain deferred.
See [Phase 6](phase-6-mcp-tool-platform.md).
