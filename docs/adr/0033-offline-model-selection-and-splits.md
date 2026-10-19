# ADR 0033: Offline model selection and temporal splits

Status: accepted for Phase 9B.

## Context

Pull rows from one session overlap in time and share vehicle/configuration context. Random row
splits could leak nearby outcomes into evaluation. Phase 9B needs a small, reviewable candidate set
and must keep the final test partition out of model and threshold selection.

## Decision

Use chronological blocks of whole session groups for train, validation and test. Merge temporal
blocks whose input/target windows overlap. Add expanding walk-forward and separate scenario,
held-out-vehicle and held-out-configuration evaluations. Compare a class-prior dummy baseline,
logistic regression and a bounded random forest. Fit imputation, missingness indicators and
scaling only inside training partitions. Select the candidate using validation average precision
subject to predeclared F1, balanced-accuracy and lift floors; resolve near ties in favor of the
simpler eligible family. Choose the operating threshold from validation only, then evaluate the
selected candidate and dummy baseline on test once.

## Consequences

- Evaluation respects chronology and session boundaries but does not prove fleet generalization.
- Small fixtures produce noisy metrics; minimum row/class support and explicit undefined reasons
  prevent false precision.
- Model selection is deterministic under a recorded seed and fixed dependency versions.
- Feature importance is reported as association, never causation.

## Alternatives considered

- **Random row splitting:** rejected because neighboring pulls and session windows can cross folds.
- **Large automated hyperparameter search:** rejected because the initial dataset is small and the
  phase needs bounded, interpretable comparisons.
- **Test-driven selection:** rejected because it would turn the test set into validation data.
