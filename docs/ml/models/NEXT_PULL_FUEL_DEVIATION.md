# Model card: next-pull fuel deviation

## Purpose and prohibited use

Predict a relative high-pressure fuel observation on the next compatible pull when measured fuel
signals and sufficient compatible history exist. This is not an HPFP diagnosis, injector diagnosis,
maintenance instruction or component failure probability.

## Label and horizon

`NEXT_PULL`, label version `1.0.0`: positive when target-pull minimum high-pressure fuel is at most
88% of the compatible recorded history mean. At least two prior pulls are required. The threshold is
relative to that history and is not a universal pressure limit.

## Inputs and dataset

Feature set `phase9a-pull-v2`; task-specific Phase 9A input and outcome datasets are cutoff-versioned
and checksummed. Inputs include current-pull rail pressure mean/delta/variation/drop rate, boost
pressure, a non-target RPM interval and `quality.duplicate_timestamp_count` as an independent
negative control. Target minimum pressure is outcome-only. Missing sensor data remains unavailable;
no pressure is inferred from documentation or configuration metadata.

The controlled fixture produced 141 rows (74 negative, 67 positive). It recorded 17 missing-fuel
outcomes, 40 no-next-pull cases and 1 insufficient-quality exclusion. Evidence is synthetic
`ENGINEERING_VALIDATION`.

## Split and model

Chronological session groups: 83 train, 28 validation, 30 test rows. Candidates were dummy,
logistic regression and random forest. Random forest was selected by validation AP with threshold
0.40. Validation AP/F1/BA: dummy 0.500/undefined/0.500, logistic 0.761/0.720/0.750, random forest
0.889/0.828/0.821. Test selected AP/F1/BA: 0.889/0.759/0.776; dummy AP/BA: 0.433/0.500.

Scenario holdout AP/F1/BA was 0.761/0.692/0.720, held-out-vehicle 0.882/0.714/0.792, and
held-out-configuration 0.752/0.700/0.682. The negative-control importance share was 2.4%. These
are small controlled synthetic holds, not real source-generalization evidence.

## Limitations and failure modes

Source availability is the primary constraint; missing, invalid, incompatible or insufficient
history prevents a label. Rail-pressure sensors and signal scaling vary by source/vehicle. The
relative 0.88 ratio is an engineering label, not an OEM operating band. Scores are not calibrated
failure probabilities. Real-data coverage, validated sensor semantics and independent prospective
evaluation are required before any later serving phase.

Safety boundary: observe and analyze only. The model cannot actuate the vehicle or write the ECU.
