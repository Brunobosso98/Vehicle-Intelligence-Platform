# ADR 0041: Phase 9D minimal immutable prediction receipts

Status: accepted for Phase 9D.

## Context

HTTP retries and operator audit need durable, deterministic results. The richer cross-tool and
causal provenance contract belongs to Phase 9E and must not be claimed by this service.

## Decision

Persist a bounded typed response with canonical request fingerprint, optional hashed client
idempotency key, cutoff, active binding/event, exact version and artifact checksum, source role,
FeatureSet identity/checksums, quality, score/threshold/decision or abstention, and creation time.
Make receipts append-only. Same-key/same-request replays return the same receipt; changed reuse
conflicts. Check current authorization and revocation before replay. Keep raw telemetry, complete
feature matrices, VINs, secrets and artifact paths out of receipts returned through HTTP.

## Consequences

- A failed receipt write returns a sanitized error and leaves no partially committed receipt.
- A response can be retrieved exactly by receipt ID and replayed without recalculation.
- The response contains minimal service lineage only; Phase 9E still owns a future shared evidence
  contract.

## Alternatives considered

- **Return only an ephemeral score:** rejected; retries and audit would be ambiguous.
- **Implement the full PredictionEvidence graph now:** rejected; it crosses the declared 9E phase
  boundary.
- **Mutate a prior response when data changes:** rejected; new data must not rewrite a historical
  cutoff result.
