# ADR 0036: Phase 9C detector families and validation selection

Status: accepted for Phase 9C.

## Context

The system needs a transparent baseline and a bounded nonlinear comparison. A score needs consistent
orientation and an operating cutoff without claiming probability calibration. Labeled synthetic
injections are evaluation metadata, not training inputs.

## Decision

Implement a median/MAD baseline with IQR fallback and constant-feature exclusion, plus a fixed-seed,
single-threaded Isolation Forest candidate with allowlisted constructor parameters. Fit all
preprocessing from eligible reference rows. Larger transformed scores mean more unusual; scores are
not probabilities. Use the reference 95th percentile only as the initial candidate threshold.
Choose method and threshold on a predeclared, session-held validation fold using injection recall,
clean false-positive and eligible-coverage floors. Clean-control false-positive rates exclude other
family injections; cross-family alarms are reported separately. A robust baseline wins exact
validation ties. Two clean sessions separate the first validation injections from its later test.
An expanding-window evaluation freezes a first model before scoring session 12, then uses that past
session as validation for a second version whose untouched test is session 13. Each version is
frozen before its own test. Feature contributions are descriptive robust deviations, not causal
attributions.

Boost/air detector definition `2.0.0` omits `boost_air.history_deviation_pa`: the Phase 9A feature
is already a rolling comparison and can shift when recent history includes an unusual pull.
Comparing that derived value to a second detector baseline made immediately subsequent clean
pressure pulls look anomalous in a disposable development run. The 9A feature definition remains
unchanged.

## Consequences

- The robust detector remains usable when the minimum support for Isolation Forest is not met.
- Synthetic thresholds show controlled-fixture behavior only; real vehicle calibration remains
  deferred to a later evidence program.
- Synthetic scenario labels must never appear in reference features or detector inputs.
- Test metrics are reporting-only and cannot revise model or threshold selection.

## Alternatives considered

- **Treating `contamination` or training quantiles as calibrated risk:** rejected; they describe a
  relative detector score and do not estimate a defect probability.
- **Selecting the more complex method by default:** rejected; use the robust method on a tie.
- **Per-feature causal explanation of Isolation Forest:** rejected; contributions are independent
  reference comparisons only.
