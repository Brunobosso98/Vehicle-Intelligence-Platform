# ADR 0049: Immutable candidate and experiment lineage

- Status: Accepted
- Date: 2026-11-21
- Decision owners: Vehicle Intelligence Platform maintainers

## Context

Candidate results are only reviewable when their source, labels, features,
cutoffs, artifact bytes and evaluation identity can be reproduced. Rewriting a
prior 9B/9C model or storing a second mutable artifact catalog would weaken the
existing provenance chain.

## Decision

Use canonical immutable pipeline definitions, exact source/dataset/feature/
label fingerprints, explicit cutoffs and seeds, existing 9B/9C version
foreign keys, private bounded artifact reads and content-addressed evaluation
reports. Store a concise candidate dossier inside the immutable review proposal
and verify its own checksum and field-level lineage before accepting a run.
All generated research artifacts remain outside serving namespaces.

## Consequences

Every proposal identifies one registered artifact and one exact evaluation.
Tampering or changed source lineage blocks the dossier. Review artifacts can be
re-exported from the immutable database body without duplicating model bytes.

## Proof

See the mlops_definitions, mlops_runs, mlops_proposals and event tables in
migration 0020, the CandidateDossier contract, repository validation and
independent dossier/artifact checks in scripts/check_mlops.py.
