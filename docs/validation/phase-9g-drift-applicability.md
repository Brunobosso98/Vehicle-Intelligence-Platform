# Phase 9G drift and applicability

The acceptance's synthetic windows were compared with training-only feature and OOD references.
The receipt and independent checker passed at code SHA
`a625be75627a8bd4d8ee5056eb9a287bb58e7898`. Distribution warnings are evidence to review a
feature change; they are not evidence of worsening performance, a mechanical fault, or diagnostic
accuracy.

## Drift and OOD results

The report contains 59 drift observations: 25 median-shift comparisons, 25 PSI comparisons (19
without warning and 6 above the declared warning level), 3 label-prevalence comparisons, 3 concept
change/performance comparisons, and 3 calibration comparisons. The latter supervised comparisons
use only the labeled synthetic windows. No real/imported unlabeled record was used to estimate
error, calibration, failure rate, or prevalence.

| Task                                | Compared OOD features | Warnings at the declared threshold | Interpretation                                                          |
| ----------------------------------- | --------------------: | ---------------------------------: | ----------------------------------------------------------------------- |
| `NEXT_PULL_FUEL_DEVIATION`          |                     8 |                                  0 | No feature crossed the training-only warning threshold in this fixture. |
| `NEXT_PULL_PERFORMANCE_DEGRADATION` |                    10 |                                  0 | No feature crossed the training-only warning threshold in this fixture. |
| `NEXT_PULL_THERMAL_DEGRADATION`     |                     7 |                                  0 | No feature crossed the training-only warning threshold in this fixture. |

These zero warnings do not establish OOD sensitivity. The receipt's fixed PSI and robust-shift
adversaries independently test arithmetic and show that an injected known shift can be surfaced;
they do not turn the small synthetic reference into a validated real-world drift detector. The
training-only fit boundary was checked and the limitation is retained.

## Source roles and applicability

There are 19 versioned applicability assessments:

| Source role / cohort                                     | Assessments | Result                                                                                               |
| -------------------------------------------------------- | ----------: | ---------------------------------------------------------------------------------------------------- |
| Synthetic 9B tasks                                       |           3 | `SYNTHETIC_ONLY`; metrics describe only generated observable next-pull labels.                       |
| Imported fixture 9B tasks                                |           3 | `EVALUATION_INSUFFICIENT`; no independent labeled support.                                           |
| Imported and real-vehicle 9B tasks                       |           6 | `REAL_DATA_UNLABELED`; distribution/availability descriptions only.                                  |
| Synthetic 9C detector families                           |           4 | `EVALUATION_INSUFFICIENT` for general applicability; limited stress results are reported separately. |
| Synthetic 9D receipt, 9E evidence, and 9F agent evidence |           3 | `EVALUATION_INSUFFICIENT`; these outputs are not outcome labels.                                     |

The evaluation manifest contains 1,162 rows (946 labeled and 216 held-out exclusions), 84 sessions,
19 synthetic vehicles, and 34 versioned configurations. It uses source role `synthetic`, source
kind `canonical_9a_plus_9g_heldout_synthetic`, feature version `phase9a-pull-v2`, generator
`phase9g-heldout-v4`, and cutoff `2026-09-01T00:00:00Z`. Vehicle context has six synthetic engine
and modification groups: N55, B58, and S55, each stock and stage 2. Modification records link to
versioned configurations; identities are not exposed. This does not represent cross-brand,
population, sensor, or real-vehicle coverage.

Real and imported telemetry has no verified outcomes in this acceptance. Missing labels and
signals remain absent; the evaluator reports exclusions or detector abstentions and never imputes
a healthy outcome. Real-world predictive validity and calibration are `NOT_ESTABLISHED`;
production use is `PROHIBITED`.

## Synthetic stress, integrity, and serving fence

Nine independent synthetic stress cases include four named positive interventions (boost/air,
fuel, performance, thermal) and clean, boost-fluctuation, missing-fuel, duplicate-quality, and
subtle-multivariate negative/confounder cases. Scenario metadata was excluded from feature inputs;
the oracle was not detector input. Synthetic cases exercise controlled behavior only.

Before/after digest checks covered 40 allowlisted Phase 9A–9F source tables. Their digests were
unchanged during research and 9G persistence. Persistence added only the five Phase 9G append-only
tables; run/report records were immutable and identical replay was idempotent. No serving model,
threshold, approval, PredictionEvidence record, or Phase 9F agent claim was changed or promoted.
The acceptance explicitly verifies all serving-fence fields are false, including automatic
retraining, production calibration, promotion, and public API exposure.
