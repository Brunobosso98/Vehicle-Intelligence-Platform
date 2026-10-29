# ADR 0045: Immutable offline evaluation and research-only calibration

Status: accepted for implementation on the Phase 9G branch; exact-head verification is recorded in
the Phase 9G acceptance report.

## Context

Phases 9B–9F provide registered prediction artifacts, anomaly references, controlled serving,
immutable evidence, and bounded agent summaries. They do not establish calibration or real-world
predictive validity. Evaluation must preserve original score semantics and cannot silently alter
serving or agent confidence.

## Decision

- Add an offline, versioned protocol and immutable evaluation registry after Alembic revision 0018.
- Require chronological, whole-session, vehicle, and configuration holdouts. Fit candidate maps
  only on calibration rows, select only on validation rows, and reserve test rows for final scoring.
- Keep fitted calibration maps bounded, checksummed JSON with complete task, label, model, source,
  and dependency lineage. Mark each map research-only and not for serving.
- Use an independent checker to recompute metric arithmetic, uncertainty, denominators, calibration
  selection, alarm burden, source manifests, and serving/source-immutability boundaries.
- Preserve 9B/9C artifacts and thresholds, 9D approvals, 9E bundles, and 9F claims. Add no public
  route, model promotion, automatic retraining, production calibration, or UI.
- Report real-world predictive validity and calibration as not established without verified,
  independently adjudicated real outcomes.

## Consequences

The repository gains a durable audit trail for repeatable offline experiments and an explicit
engineering/science status split. Researchers can compare calibration candidates without changing
serving behavior. The schema adds five bounded immutable tables and a disposable-database migration
round trip. Synthetic metrics remain scoped to their generator and label definition.

## Alternatives considered

- **Write fitted maps into the Phase 9D model registry:** rejected because a research fit must not
  change serving approvals or become available to inference.
- **Use the held-out test set for map fitting or selection:** rejected because it contaminates the
  final estimate.
- **Report an engine-health percentage from 9C scores:** rejected because Phase 9C has no verified
  mechanical outcome labels.
- **Store only a mutable local report:** rejected because reproducibility, replay, and operator
  audit require a versioned protocol and database-enforced immutable provenance.
