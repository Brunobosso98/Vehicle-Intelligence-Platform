# Contracts

Pydantic/OpenAPI is authoritative. Never edit generated/api.ts or schemas/openapi.json directly.
Run `make contracts` then `make contracts-check`. Breaking changes need explicit versioning and review.
Contract tests validate real routes and error models; do not invent telemetry models before Phase 1.
