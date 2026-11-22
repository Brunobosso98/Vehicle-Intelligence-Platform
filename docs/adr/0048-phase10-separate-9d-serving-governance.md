# ADR 0048: Separate MLOps governance from Phase 9D serving

- Status: Accepted
- Date: 2026-11-21
- Decision owners: Vehicle Intelligence Platform maintainers

## Context

A successful offline fit or review could otherwise be confused with serving
approval. Phase 9D already owns candidate approval, binding activation,
revocation and rollback with its own operator authorization and event history.

## Decision

Phase 10 writes candidates through the existing 9B/9C registration paths,
then creates immutable evaluation dossiers and explicit human review records.
The Phase 10 CLI never calls the 9D approval, activation or rollback methods.
Rollback output is a plan bound to the exact reviewed proposal, target artifact
and current binding. A separate authorized Phase 9D command is required to
make a serving transition.

## Consequences

An accepted MLOps proposal remains APPROVED_FOR_CONTROLLED_REVIEW, not a live
model. CI has no serving credentials. A later 9D action can be reconciled
read-only against its own event receipt.

## Proof

The Phase 10 evaluator snapshots 9D/9E/9F/9G source digests around comparison,
monitoring and review, then records separately the explicit test-only 9D
transition. The independent checker verifies the source digests and action
boundary.
