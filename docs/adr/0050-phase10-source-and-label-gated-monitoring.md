# ADR 0050: Source- and label-gated MLOps monitoring

- Status: Accepted
- Date: 2026-11-21
- Decision owners: Vehicle Intelligence Platform maintainers

## Context

Existing 9D receipts provide scores and abstentions, but unlabeled telemetry
cannot establish accuracy, recall or calibration. Feature availability and
source distribution can shift independently of actual predictive performance.

## Decision

Monitor only persisted 9D receipts through explicit immutable protocols and
read-only bounded queries. Report source drift, feature shift, missingness,
score shift, coverage and abstentions separately. Keep performance/calibration
unknown until an independently verified timestamp-aware label join has eligible
support. Report no rows as NO_OBSERVATIONS; never turn missing labels into
zero error or a synthetic substitute.

## Consequences

Monitoring can produce a review proposal but cannot generate new predictions,
labels or serving actions. Synthetic calibration remains scoped to its named
synthetic cohort.

## Proof

See mlops/monitoring.py, its protocol and source-digest checks, and the
independent Phase 10 receipt. Real-world mechanical failure predictive
reliability remains NOT_ESTABLISHED.
