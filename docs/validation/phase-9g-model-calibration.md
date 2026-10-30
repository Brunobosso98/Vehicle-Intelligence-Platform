# Phase 9G supervised calibration

This report covers the three frozen Phase 9B `NEXT_PULL` observable-label tasks. The official
local acceptance receipt was generated at code SHA
`a625be75627a8bd4d8ee5056eb9a287bb58e7898`, based on `327c63f35b4e7bc0eba31bbec81d20206be8afa2`.
The receipt checksum is
`94afae0799f2df77ad17209d51930d24b4162e644a32b63ab7db409c935ae2dc`; its independent checker
passed. The exact final branch SHA still requires the PR workflows recorded in
[the acceptance record](phase-9g-acceptance.md).

## Protocol and support

Protocol `phase9g-protocol-v2` uses chronological whole-session partitions. The model artifacts,
model versions, feature definitions, and frozen operating thresholds are loaded from Phase 9B and
remain unchanged. Candidate maps are fitted on calibration rows, selected only by validation
Brier score, and scored once on later test rows. The synthetic generator is `phase9g-heldout-v4`;
the canonical feature version is `phase9a-pull-v2`.

| Task | Train rows (pos/neg; sessions) | Calibration (pos/neg; sessions) | Validation (pos/neg; sessions) | Test (pos/neg; sessions) | Frozen threshold |
| --- | ---: | ---: | ---: | ---: | ---: |
| `NEXT_PULL_FUEL_DEVIATION` | 83 (40/43; 24) | 69 (33/36; 20) | 69 (35/34; 20) | 69 (36/33; 20) | 0.40 |
| `NEXT_PULL_PERFORMANCE_DEGRADATION` | 94 (31/63; 24) | 78 (28/50; 20) | 78 (23/55; 20) | 78 (25/53; 20) | 0.45 |
| `NEXT_PULL_THERMAL_DEGRADATION` | 94 (43/51; 24) | 78 (34/44; 20) | 78 (35/43; 20) | 78 (33/45; 20) | 0.50 |

Evaluation folds have disjoint pull, session, vehicle, and configuration fingerprints. The model's
training vehicles/configurations are held out from evaluation. Calibration and test populations
are separate; validation is used for method choice. Each calibration/test metric denominator is
the labeled scored row count shown above. No missing label was replaced with a fabricated outcome.

## Candidate selection and held-out test results

Identity is the uncalibrated score. Sigmoid and isotonic are research-only candidates. The
predeclared isotonic independent-session floor is 30; only 20 calibration sessions were available,
so isotonic was `INSUFFICIENT_SUPPORT` for all tasks. Validation Brier selected identity for fuel
and thermal and sigmoid for performance. `not_for_serving=true` is recorded for each candidate.

| Task | Validation Brier: identity / sigmoid | Selected | Test Brier (95% CI) | Log loss (95% CI) | ECE (95% CI) | AUROC (95% CI) | Average precision (95% CI) |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| Fuel deviation | 0.13666 / 0.14434 | Identity | 0.13996 (0.10648–0.17281) | 0.44191 (0.36764–0.52163) | 0.07380 (0.05945–0.16806) | 0.88973 (0.81987–0.94844) | 0.91013 (0.83711–0.96846) |
| Performance degradation | 0.18169 / 0.14171 | Sigmoid | 0.13446 (0.08872–0.19061) | 0.39082 (0.28731–0.52286) | 0.08927 (0.04813–0.20846) | 0.89359 (0.81685–0.95090) | 0.81345 (0.69683–0.92518) |
| Thermal degradation | 0.14075 / 0.14175 | Identity | 0.12577 (0.08157–0.16913) | 0.40475 (0.28961–0.54793) | 0.10799 (0.06007–0.17933) | 0.91077 (0.82351–0.97111) | 0.89948 (0.78690–0.96465) |

Intervals use 200 deterministic session-cluster percentile bootstrap resamples over 20 independent
test sessions. ECE uses five fixed-width bins. Every reliability-bin rate had fewer than 20
independent sessions, so its bin interval is explicitly `NONINDEPENDENT_DESCRIPTIVE`; aggregate
metric intervals do not change that limitation. The complete bin counts, means, observed rates,
and support states remain in the checksummed machine receipt.

Selected-candidate reliability curves are shown as mean score versus observed synthetic-label
rate. Counts are rows / independent sessions per bin; the protocol's 0.2-wide bins are fixed in
advance. The session support is insufficient for bin-level confidence intervals in every row.

| Task | Score bin | Mean score | Observed label rate | Rows / sessions |
| --- | ---: | ---: | ---: | ---: |
| Fuel deviation | 0.0–0.2 | 0.1094 | 0.0000 | 10 / 9 |
| Fuel deviation | 0.2–0.4 | 0.2910 | 0.2727 | 22 / 15 |
| Fuel deviation | 0.4–0.6 | 0.4958 | 0.6000 | 5 / 5 |
| Fuel deviation | 0.6–0.8 | 0.6827 | 0.7500 | 20 / 14 |
| Fuel deviation | 0.8–1.0 | 0.8559 | 1.0000 | 12 / 12 |
| Performance degradation | 0.0–0.2 | 0.0631 | 0.0769 | 39 / 19 |
| Performance degradation | 0.2–0.4 | 0.2692 | 0.3333 | 9 / 7 |
| Performance degradation | 0.4–0.6 | 0.5019 | 0.6667 | 3 / 3 |
| Performance degradation | 0.6–0.8 | 0.7190 | 0.4000 | 15 / 11 |
| Performance degradation | 0.8–1.0 | 0.8694 | 0.9167 | 12 / 12 |
| Thermal degradation | 0.0–0.2 | 0.1324 | 0.0588 | 34 / 16 |
| Thermal degradation | 0.2–0.4 | 0.3320 | 0.2857 | 7 / 7 |
| Thermal degradation | 0.4–0.6 | 0.4380 | 1.0000 | 3 / 3 |
| Thermal degradation | 0.6–0.8 | 0.7189 | 0.5000 | 12 / 10 |
| Thermal degradation | 0.8–1.0 | 0.8507 | 0.9091 | 22 / 12 |

The test comparison did not force a uniform improvement. For fuel, identity versus sigmoid Brier
was 0.13996 versus 0.14758; log loss 0.44191 versus 0.46521; ECE 0.07380 versus 0.10699. For
performance the values were 0.16277 versus 0.13446, 0.47908 versus 0.39082, and 0.17962 versus
0.08927. For thermal they were 0.12577 versus 0.12616, 0.40475 versus 0.40185, and 0.10799 versus
0.07938. Candidate choice was made on validation only; the mixed thermal test result is retained.

## Frozen-threshold decisions and selective risk

| Task | TP / FP / FN / TN | Precision | Recall | Specificity | Balanced accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fuel deviation | 30 / 7 / 6 / 26 | 0.811 | 0.833 | 0.788 | 0.811 |
| Performance degradation | 19 / 11 / 6 / 42 | 0.633 | 0.760 | 0.792 | 0.776 |
| Thermal degradation | 26 / 8 / 7 / 37 | 0.765 | 0.788 | 0.822 | 0.805 |

Selective risk orders examples by distance from the uncalibrated score 0.5. This is descriptive
coverage analysis, not a deployment abstention policy. Retained examples / selective error were:

| Retained test rows | Fuel (n=69) | Performance (n=78) | Thermal (n=78) |
| ---: | ---: | ---: | ---: |
| 100% | 69 / 0.1739 | 78 / 0.2436 | 78 / 0.1923 |
| ~91% | 63 / 0.1746 | 71 / 0.1690 | 71 / 0.1408 |
| ~81% | 56 / 0.1429 | 63 / 0.0952 | 63 / 0.1111 |
| ~61% | 42 / 0.0952 | 47 / 0.0638 | 47 / 0.0426 |
| ~41% | 28 / 0.0714 | 32 / 0.0000 | 32 / 0.0625 |

The ECE, Brier score, log loss, discrimination scores, and test prevalence describe only these
synthetic observable next-pull labels. They do not estimate mechanical-failure probability. Real
vehicle labels/outcomes are absent; real-world calibration and predictive validity remain
`NOT_ESTABLISHED`, and production calibration is prohibited.
