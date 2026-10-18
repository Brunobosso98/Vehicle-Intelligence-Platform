# Model card: next-pull performance degradation

## Purpose and prohibited use

Predict a relative slowdown through one normalized RPM interval on the next compatible pull. This
is not a horsepower estimate, dyno result, component diagnosis, maintenance recommendation or
vehicle-control signal.

## Label and horizon

`NEXT_PULL`, label version `1.0.0`: positive when target-pull Phase 5 3,500–4,500 RPM interval time
per 1,000 RPM is at least 8% slower than the current pull. The interval must be continuous and
monotonic under Phase 5's existing maximum-gap policy. No target interval enters the model vector.

## Inputs and dataset

Feature set `phase9a-pull-v2`; task-specific Phase 9A input and outcome datasets are cutoff-versioned
and checksummed. Inputs include the other normalized RPM intervals, prior compatible performance
mean/variance, boost max/variation, current IAT start/delta and sample-interval quality. Identity,
future-only and target-source features are rejected.

The controlled fixture produced 158 rows (106 negative, 52 positive), with 40 no-next-pull and 1
insufficient-quality exclusion. Evidence is synthetic `ENGINEERING_VALIDATION`.

## Split and model

Chronological session groups: 94 train, 32 validation, 32 test rows. Candidates were dummy,
logistic regression and random forest. Random forest was selected by validation AP with threshold
0.55. Validation AP/F1/BA: dummy 0.344/undefined/0.500, logistic 0.734/0.815/0.881, random forest
0.790/0.727/0.792. Test selected AP/F1/BA: 0.757/0.588/0.705; dummy AP/BA: 0.312/0.500.

Scenario holdout AP/F1/BA was 0.847/0.712/0.802, held-out-vehicle 0.820/0.500/0.646, and
held-out-configuration 0.720/0.691/0.811. Final test and vehicle-holdout F1 are weak. The result
passes only the predeclared synthetic engineering gate and should not be treated as a deployable
predictor.

## Limitations and failure modes

The fixture uses controlled timing differences and injected confounders; it is not real performance
data. Road grade, load, gear, environment, tire behavior, driver input and sensor quality can change
interval times. Missing RPM boundaries or excessive gaps make the outcome unavailable and exclude
the row. The 8% threshold is not an OEM specification. Scores are not failure probabilities and do
not represent power loss or component condition.

Safety boundary: observe and analyze only. No actuation, ECU writes or vehicle-control path exists.
