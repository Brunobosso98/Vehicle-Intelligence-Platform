# Model card: next-pull thermal degradation

## Purpose and prohibited use

Predict the binary relative thermal outcome for the next compatible pull. This is an offline
engineering candidate. Do not use it to diagnose overheating, infer component failure, recommend
maintenance, or control the vehicle.

## Label and horizon

`NEXT_PULL`, label version `1.0.0`: positive when the next compatible pull's IAT start is at least
3 K above the current pull's IAT start. This is an explicit relative engineering rule, not an OEM
operating limit. The next pull is the immediate candidate in the same vehicle/configuration,
modification state and session sequence.

## Inputs and dataset

Feature set `phase9a-pull-v2`; task-specific Phase 9A input and outcome datasets are cutoff-versioned
and checksummed. Inputs are current-pull IAT delta/slope, pre-pull IAT and recovery, boost pressure
variation, the 2,500–3,500 RPM interval, and `quality.duplicate_timestamp_count` as an independent
negative control. Target-pull IAT is outcome-only. Identity, future-only and target-source features
are rejected.

The controlled fixture produced 158 rows (88 negative, 70 positive). It had 40 no-next-pull and 1
insufficient-quality exclusion. All evidence is synthetic `ENGINEERING_VALIDATION`.

## Split and model

Chronological session groups: 94 train, 32 validation, 32 test rows. The candidates were dummy,
logistic regression and random forest. Random forest was selected using validation AP with threshold
0.50. Validation AP/F1/BA: dummy 0.406/undefined/0.500, logistic 0.609/0.769/0.806, random forest
0.855/0.769/0.806. Test selected AP/F1/BA: 0.885/0.786/0.810; dummy AP/BA: 0.438/0.500.

Scenario holdout AP/F1/BA was 0.872/0.720/0.766, held-out-vehicle 0.826/0.737/0.753, and
held-out-configuration 0.698/0.836/0.858. The negative-control importance share was 0.8%. Small
synthetic holdouts do not establish generalization.

## Limitations and failure modes

The rule and patterns are synthetic; thresholds do not represent manufacturer limits. Missing or
invalid thermal outcomes reduce support. The label measures start-temperature change only, not
cooling-system health, ambient conditions or mechanical cause. Scores are not calibrated failure
probabilities. Real data, larger independent vehicle/configuration coverage and prospective
evaluation are required before serving or operational use.

Safety boundary: observe and analyze only. No brake, steering, throttle, flashing, coding or ECU
write action is available in this phase.
