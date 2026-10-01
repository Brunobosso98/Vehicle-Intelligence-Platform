# API contracts

FastAPI Pydantic models are the source of truth. `make contracts` exports a deterministic
OpenAPI snapshot and generates TypeScript with openapi-typescript. `make contracts-check`
regenerates in memory and fails on drift. Never edit generated files directly.
See docs/architecture/versioning.md for compatibility policy.
