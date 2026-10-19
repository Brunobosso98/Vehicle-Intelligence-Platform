# ADR 0037: Phase 9C immutable registry and trusted artifacts

Status: accepted for Phase 9C.

## Context

Offline scoring needs persistent lineage and replay identity. Detector artifacts use joblib, whose
pickle-based loading is safe only for trusted application-generated files. Findings must not change
when later data is ingested.

## Decision

Additive migration `0015` owns immutable definitions, reference snapshots/rows, detector versions,
detection runs and findings. Database triggers reject update/delete operations. Every reference,
fit, validation threshold, artifact, run and finding has checksum or identity metadata. Write
artifacts atomically under the fixed ignored `apps/api/.artifacts/phase9c/` root with a 50 MiB cap.
Load only by a registered detector-version ID after checking fixed path, checksum, schema, exact
definition and estimator allowlist. Do not accept arbitrary artifact paths or load user-supplied
pickle/joblib files. Scope finding identities to the immutable detection-run identity so overlapping
batches remain separate records, while equivalent repeated runs converge on the same run and
finding IDs.

## Consequences

- Migration upgrades and downgrade/re-upgrade must be validated against a disposable database.
- Artifact bytes need not be identical across library builds; repeated fitted scores and decisions
  must be deterministic within the pinned environment.
- The local CLI is disabled in production and does not create a public endpoint.
- A later serving path needs its own authorization, workload and lifecycle design.

## Alternatives considered

- **Store serialized estimators in PostgreSQL:** rejected; registry metadata belongs in relational
  rows while opaque bytes stay in the application-owned artifact store.
- **Load user-supplied files:** rejected because pickle deserialization can execute code.
- **Mutate findings after new ingestion:** rejected; new evidence requires a new run identity.
