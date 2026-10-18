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
mean/variance, current-pull sample-interval variability, boost max/variation, current IAT start/delta
and `quality.duplicate_timestamp_count` as an independent negative control. The sample-interval
feature is a timing input derived from the current pull, not the irrelevant control. Identity,
future-only and target-source features are rejected.

The controlled fixture produced 158 rows (106 negative, 52 positive), with 40 no-next-pull and 1
insufficient-quality exclusion. Evidence is synthetic `ENGINEERING_VALIDATION`.

## Split and model

Chronological session groups: 94 train, 32 validation, 32 test rows. Candidates were dummy,
logistic regression and random forest. Logistic regression was selected by validation AP with
threshold 0.45. Validation AP/F1/BA: dummy 0.344/undefined/0.500, logistic 0.773/0.786/0.857,
random forest 0.749/0.762/0.816. Test selected AP/F1/BA: 0.788/0.643/0.745; dummy AP/BA:
0.313/0.500.

Scenario holdout AP/F1/BA was 0.855/0.677/0.767, held-out-vehicle 0.931/0.737/0.771, and
held-out-configuration 0.789/0.680/0.792. The negative-control importance share was 2.7%. Test F1
is lower than validation F1. This result passes only the predeclared synthetic engineering gate and
should not be treated as a deployable predictor.

## Limitations and failure modes

The fixture uses controlled timing differences and injected confounders; it is not real performance
data. Road grade, load, gear, environment, tire behavior, driver input and sensor quality can change
interval times. Missing RPM boundaries or excessive gaps make the outcome unavailable and exclude
the row. The 8% threshold is not an OEM specification. Scores are not failure probabilities and do
not represent power loss or component condition.

Safety boundary: observe and analyze only. No actuation, ECU writes or vehicle-control path exists.
