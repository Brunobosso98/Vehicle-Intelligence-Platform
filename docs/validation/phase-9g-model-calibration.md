# Phase 9G supervised calibration

This report covers only the three frozen Phase 9B `NEXT_PULL` observable-label tasks. Candidate
maps are research artifacts fitted on session-disjoint calibration rows, method selection uses
validation Brier score, and final metrics use a later untouched test partition. Identity is the
uncalibrated baseline; sigmoid and isotonic candidates are reported only when their predeclared
class, row, and independent-session support floors are met. The registered 9B artifacts and
thresholds remain unchanged.

The evaluator reports Brier score, clipped log loss, five-bin ECE and reliability counts, AUROC,
average precision, threshold decisions, risk/coverage, missing-label exclusions, subgroup support,
and deterministic session-cluster intervals where support permits. It never interprets a 9B score
as mechanical-failure probability. Synthetic prevalence and scenario labels apply only to the
versioned engineering fixture.

## Exact-SHA results

Per-task denominators, candidate states, reliability bins, and test metrics are copied here from
the exact-SHA acceptance JSON only after the independent checker passes. The machine-readable
acceptance artifact is authoritative for every value and records `NOT_ESTABLISHED` for real-world
calibration and predictive validity unless verified post-outcome vehicle labels exist.
