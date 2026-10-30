# Phase 9G anomaly reliability

The acceptance evaluated the four frozen Phase 9C families (boost/air, fuel, performance, and
thermal) using the registered robust MAD and Isolation Forest implementations. The official local
receipt is at code SHA `a625be75627a8bd4d8ee5056eb9a287bb58e7898`; its independent checker passed.
The [acceptance record](phase-9g-acceptance.md) records its report checksum and exact-head CI
status.

The test matrix has 30 cases per family/method: 8 clean controls, 4 target-family interventions,
12 other-family interventions, 2 low-quality duplicate cases, and named missing-signal, context,
and subtle multivariate controls. Oracle labels are held outside detector inputs and fit. Thresholds
and registered references are preserved. Numerators and denominators below are raw case counts;
these small synthetic samples do not support a vehicle-level error-rate claim.

| Family | Method | Clean false alarms | Other-family alarms | Target detections | Quality/signal abstentions | Total alarms | Scored / 30 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Boost/air | Isolation Forest | 1/8 (12.5%) | 4/12 (33.3%) | 3/4 (75%) | 2/2 | 10 | 28 |
| Boost/air | Robust MAD | 0/8 (0%) | 4/12 (33.3%) | 4/4 (100%) | 2/2 | 10 | 28 |
| Fuel | Isolation Forest | 1/8 (12.5%) | 2/12 (16.7%) | 4/4 (100%) | 4/4 | 8 | 26 |
| Fuel | Robust MAD | 0/8 (0%) | 4/12 (33.3%) | 4/4 (100%) | 4/4 | 10 | 26 |
| Performance | Isolation Forest | 2/8 (25%) | 3/12 (25%) | 4/4 (100%) | 2/2 | 11 | 28 |
| Performance | Robust MAD | 0/8 (0%) | 0/12 (0%) | 4/4 (100%) | 2/2 | 5 | 28 |
| Thermal | Isolation Forest | 4/8 eligible (50%); 4/6 scored (66.7%) | 5/12 (41.7%) | 4/4 (100%) | 4/4 | 14 | 26 |
| Thermal | Robust MAD | 0/8 eligible and 0/6 scored | 6/12 (50%) | 4/4 (100%) | 4/4 | 11 | 26 |

Thermal had two clean cases that abstained for insufficient thermal signal, so the clean false
alarm denominator is also shown among the six scored clean controls. Across thermal's 30 cases,
the four abstentions include those two signal gaps and two low-quality duplicate cases. Fuel's four
abstentions include two duplicate cases and two missing-fuel-capability cases. The other families
abstain on the two duplicate cases. Quality/capability abstentions generated no alarms. The oracle
was not read by the detector.

Alarm totals count case-level findings. Repeated findings in the same detector family and
session were separately summarized for research; this did not modify persisted Phase 9C findings.
Target detections on controlled synthetic changes do not mean that the detector identifies a
mechanical fault. Scores are neither probabilities nor health percentages, and their scales cannot
be compared across methods.

## Reference-size sensitivity and stability

The untouched 30-case matrix was replayed with 5, 6, and 8 reference sessions (25, 30, and 40
reference rows). The original registered thresholds and artifacts were not mutated; sensitivity
fits and thresholds were confined to the local research calculation. Frozen-artifact score-rank
Spearman correlations varied by family and method:

| Family | Isolation Forest range | Robust MAD range |
| --- | ---: | ---: |
| Boost/air | -0.142 to 0.084 | 0.114 to 0.120 |
| Fuel | 0.070 to 0.167 | -0.094 to -0.094 |
| Performance | -0.029 to -0.029 | 0.066 to 0.066 |
| Thermal | 0.680 to 0.748 | 0.896 to 1.000 |

Several alarm counts also changed by reference size. These are results from the specific
registered artifacts and test cases, not a broad stability guarantee.

The machine receipt contains all 30 observations per run, frozen detector versions and artifact
checksums, clean/cross-family/target numerators, abstentions, alarm deduplication, reference
fingerprints, and sensitivity outcomes. Four positive interventions and named negative/confounder
cases were checked. These are independent synthetic stress scenarios and do not establish real
diagnostic performance.
