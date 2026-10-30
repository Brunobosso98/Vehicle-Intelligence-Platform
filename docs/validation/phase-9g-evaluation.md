# Phase 9G evaluation report

This is the scientific and engineering summary for Phase 9G. The versioned protocol and full
metrics are detailed in the linked supervised, anomaly, applicability, and acceptance reports.
The authoritative receipt is the exact-SHA machine artifact, checked independently before any
result is treated as evidence.

## Protocol and provenance

- Protocol: `phase9g-protocol-v2`; report schema: `phase9g-evaluation-v1`.
- Source role and source kind: `synthetic` and `canonical_9a_plus_9g_heldout_synthetic`.
- Canonical feature version: `phase9a-pull-v2`; held-out generator: `phase9g-heldout-v4`;
  known-at policy: `input_available_before_next_pull_target_v1`.
- Dataset: 1,162 records (946 labeled, 216 held-out exclusions), 84 sessions, 19 synthetic
  vehicles, and 34 configurations; cutoff `2026-09-01T00:00:00Z`.
- Training, calibration, validation, and test use strictly chronological whole-session folds.
  Pull, session, vehicle, and configuration fingerprints are disjoint; model training vehicles
  and configurations are held out from evaluation.
- 9B candidate maps fit only calibration rows; validation Brier chooses a candidate; test labels
  remain untouched until scoring. Registered 9B models and thresholds stay frozen.
- Four 9C detector families use original registered references and thresholds. Clean, target,
  cross-family, quality, signal-gap, and named confounder cases are reported separately.
- Uncertainty is a 200-resample session-cluster percentile interval. Bins below 20 independent
  sessions have no interval and are marked descriptive. Missing labels/signals remain missing.

## Findings

Validation selected identity for fuel deviation, sigmoid for performance degradation, and identity
for thermal degradation. Isotonic was ineligible because each calibration set had only 20
independent sessions against the declared 30-session floor. Held-out results are mixed: the
performance task's sigmoid candidate improved test Brier over identity (0.13446 vs 0.16277), the
fuel task's identity was better (0.13996 vs 0.14758), and thermal Brier was essentially unchanged
(0.12577 vs 0.12616), despite lower sigmoid ECE. No threshold or holdout was tuned after seeing
test results. Exact denominators, confidence intervals, reliability-bin support, decisions, and
selective-risk numbers are in the [supervised report](phase-9g-model-calibration.md).

Across the 9C stress matrix, clean false alarms ranged from 0/8 to 4/8, cross-family alarms from
0/12 to 6/12, and same-family synthetic detections from 3/4 to 4/4. Two thermal clean rows
abstained for missing thermal signals; missing fuel capability and duplicate-quality controls
also abstained without alarms. Reference-size stability varied by detector. These small synthetic
case counts cannot estimate real-world diagnostic reliability. Full numerators and denominators
are in the [anomaly report](phase-9g-anomaly-reliability.md).

There were 59 drift observations, with six PSI warnings. No task's training-only OOD summary
crossed its declared warning threshold in this fixture. This does not establish real-world OOD
detection power. The [applicability report](phase-9g-drift-applicability.md) records source roles,
missingness, stress scenarios, vehicle/configuration context, and source integrity.

## Scientific readiness

Engineering pipeline status is `PASS` on the locally accepted implementation SHA. Synthetic
calibration is `SYNTHETIC_ONLY`; real-world calibration and real-world predictive validity remain
`NOT_ESTABLISHED`, because there are no verified real mechanical-failure labels or post-outcome
vehicle observations. No 9B score is a mechanical-failure probability. No 9C anomaly score is an
engine-health percentage. Production use and production calibration are `PROHIBITED`.

The locally accepted code SHA is `a625be75627a8bd4d8ee5056eb9a287bb58e7898` (base
`327c63f35b4e7bc0eba31bbec81d20206be8afa2`), report checksum
`94afae0799f2df77ad17209d51930d24b4162e644a32b63ab7db409c935ae2dc`. The final branch SHA, PR,
canonical Docker/full-stack result, and required exact-SHA GitHub checks are recorded in the
[acceptance report](phase-9g-acceptance.md) before delivery is declared.
