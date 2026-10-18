# ADR 0031: Versioned feature engineering and temporal datasets

Status: accepted for Phase 9A.

## Context

Later predictive phases need a stable input contract with deterministic feature meaning, units,
quality, source lineage, vehicle/configuration ownership, temporal availability and reproducibility.
Canonical telemetry, sessions, pulls, events, analytics and configuration history already have
separate owners. A feature foundation must read these sources without rewriting or duplicating
their domain behavior. A database-backed vector store or online feature service would add
infrastructure and serving semantics that Phase 9A does not need.

## Decision

Add a `vehicle_platform.features` package with immutable typed definitions, a trusted deterministic
calculator registry, version checksums, cutoff-aware generation, persisted per-pull FeatureSets,
and a dataset builder. Store vectors and lineage as bounded JSONB in relational records so a
FeatureSet is reviewable beside its entity identity and queryable from the current PostgreSQL
stack. Source and provenance hashes define idempotent identity; new formulas/policies require a
new feature-set version.

The dataset builder materializes pull-scoped rows at a declared cutoff/horizon. It validates
feature availability, source ownership, effective configuration/modifications, quality, history,
lineage and deterministic row identity before producing a JSONL export and manifest checksum.
Chronological and walk-forward split helpers are included. Generation/export are bounded local
operator CLIs; no public API, MCP tool, prediction endpoint, model training, feature-store SaaS or
frontend is introduced.

## Consequences

- Phase 9B receives a versioned offline data contract without committing to a model/runtime stack.
- Feature formulas cannot be supplied as executable user/database text.
- Missing sensor values remain explicit nulls with reasons and units; no sensor is inferred from
  documentary knowledge or an operating-stage label.
- Historical outputs are retained when source content changes; version/checksum conflicts fail
  closed.
- Dataset builds are bounded and inspectable but do not yet scale as a distributed job system.
- A remote administrative feature API, authentication scope and online serving require a later
  separately reviewed decision.

## Alternatives considered

- **Add model training or prediction now:** rejected; model selection and calibration belong to
  Phases 9B and 9G.
- **Use formulas configured as SQL/Python expressions:** rejected because untrusted formulas
  would widen execution and safety boundaries.
- **Add a separate feature-store product or online cache:** rejected because the current batch
  foundation needs immutable offline snapshots, not low-latency serving.
- **Expose generation through existing vehicle APIs/MCP:** rejected because those surfaces lack a
  Phase 9A operator authorization and lifecycle contract; the local CLI is bounded and uses
  configured database access.

## Validation

The 9A evaluator and disposable integration gate exercise migration, deterministic recompute,
version separation, future sample/event/pull cutoffs, vehicle/configuration history isolation,
missing sensor semantics, dataset checksums, exclusions and concurrent idempotency. See the
[acceptance report](../validation/phase-9a-acceptance.md).
