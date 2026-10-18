# Phase 9A baseline profile

This profile summarizes the 4 eligible rows in the controlled synthetic acceptance dataset for
`phase9a-pull-v2`. The
dataset includes 2 vehicles in its source fixture; the selected four rows belong to one vehicle so
that the other vehicle can serve as an isolation case. One low-quality candidate is excluded by the
dataset quality policy. These measurements are a 9B planning baseline, not a claim about fleet
coverage or real-vehicle distributions.

| Feature                     | Unit        | Availability    | Null rate | Min |  Mean | Max |
| --------------------------- | ----------- | --------------- | --------: | --: | ----: | --: |
| `history.prior_event_count` | count       | historical-only |        0% |   0 |  0.25 |   1 |
| `quality.observation_count` | count       | during-window   |        0% |  35 | 38.75 |  40 |
| `raw_context.engine_code`   | categorical | pre-event       |        0% | N55 |   N55 | N55 |
| `thermal.iat_delta_k`       | K           | during-window   |        0% |   4 |     4 |   4 |

Mean pull completeness was 0.9625. All four included rows were synthetic and passed the dataset's
quality filter; one low-quality candidate is recorded in the profile as a `quality_failure` with
reason `minimum_quality_not_met`.

The machine-readable capability matrix covers all 79 definitions: 15 CORE, 28 OPTIONAL and 36
SOURCE_SPECIFIC. It records signal compatibility for the synthetic generator, mapped CSV replay,
generic OBD-II (including the need for a live preflight) and a richer future source that must provide
its own capability report. These statuses do not promise runtime signal availability. The matrix and
profile are emitted under `.validation/phase9a/baseline-profile.json` by `make phase9a-acceptance`.

Numeric outliers remain in dataset rows. Synthetic extremes are labeled `synthetic_boundary`;
real or imported extremes are labeled `possible_real_extreme` for review. The profile also reports
quality exclusions without silently dropping or clamping valid extremes.
