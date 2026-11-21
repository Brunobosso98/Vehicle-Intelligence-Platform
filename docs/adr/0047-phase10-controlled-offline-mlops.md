# ADR 0047: Controlled offline MLOps lifecycle

- Status: Accepted
- Date: 2026-11-21
- Decision owners: Vehicle Intelligence Platform maintainers

## Context

Phases 9A–9G already provide versioned features and datasets, trusted 9B/9C
registries, a controlled 9D serving lifecycle and immutable 9G scientific
evaluation. Phase 10 needs durable orchestration and review without creating a
second source of model truth or bypassing those boundaries.

## Decision

Implement an operator-only MLOps control plane inside the existing API package
and PostgreSQL database. Use fixed versioned JSON contracts, a fixed stage DAG,
database leases/fencing, append-only run and review events, and existing 9B,
9C and 9G execution paths. Keep model binaries in their existing trusted
registries and store checksummed proposals and dossiers as bounded JSON.
Execution is dry-run by default and only enabled in development/test.

Do not add Kubeflow, MLflow tracking server or another heavyweight service.
The existing database and artifact registries already provide the required
durable identity and provenance; the required Phase 10 scope is a bounded
single-platform operator workflow, not a multi-tenant/cloud training fleet.

## Consequences

MLOps state is durable, auditable and small, while prior registries remain
authoritative. Runs can be replayed or recovered with explicit fencing.
Scientific reports remain offline and source-role-bound. The fixed local model
catalog trades extensibility for an auditable execution surface.

## Proof

See migration 0020, vehicle_platform.mlops, the Phase 10 disposable acceptance
and its independent receipt checker. Docker/database and exact-head results are
only claimed from their final GitHub Actions receipts.
