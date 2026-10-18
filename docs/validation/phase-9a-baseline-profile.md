# Phase 9A baseline profile

This profile summarizes the 5 eligible rows in the controlled synthetic acceptance dataset for
`phase9a-pull-v2`. Rows cover 2 vehicles and all 3 configurations. One low-quality candidate is
excluded by the dataset quality policy. These measurements are a 9B planning baseline, not a
claim about fleet coverage or real-vehicle distributions.

| Feature                                  | Unit      | Availability    | Null rate | Min        | Mean         | Max        |
| ---------------------------------------- | --------- | --------------- | --------: | ---------: | -----------: | ---------: |
| `boost_air.pressure_max`                 | Pa        | during-window   |        0% |    104,000 |      110,000 |    116,000 |
| `fuel.rail_pressure_mean`                | Pa        | during-window   |       20% | 13,800,000 |   15,175,000 | 16,800,000 |
| `history.prior_boost_mean_pa`            | Pa        | historical-only |       60% |    100,000 |      101,500 |    103,000 |
| `history.prior_event_count`              | count     | historical-only |        0% |          0 |          0.2 |          1 |
| `performance.pull_duration_s`            | s         | post-window     |        0% |          4 |            4 |          4 |
| `performance.rpm_3500_4500_s_per_1000rpm` | s/1000rpm | post-window     |        0% |          2 |            2 |          2 |
| `quality.observation_count`              | count     | during-window   |        0% |         35 |           39 |         40 |
| `thermal.iat_delta_k`                    | K         | during-window   |        0% |          2 |          4.8 |          8 |
| `thermal.pre_pull_iat_k`                 | K         | pre-event       |       40% |        302 |          307 |        315 |

Categorical features: `raw_context.configuration_stage` has 4 `stock` and 1 `stage2` rows;
`raw_context.engine_code` has 5 `N55` rows. Both have zero nulls.

Mean pull completeness was 0.97. The quality filter excludes one candidate with reason
`minimum_quality_not_met`; the profile retains that record as a `quality_failure`. Unavailable fuel
is kept null with its explicit reason. The eligible IAT deltas vary across 2, 4, 6 and 8 K; peak
boost spans 104,000–116,000 Pa; and the four observed rail-pressure means span 13,800,000–16,800,000
Pa.

The machine-readable capability matrix covers all 79 definitions: 15 CORE, 28 OPTIONAL and 36
SOURCE_SPECIFIC. It records signal compatibility for the synthetic generator, mapped CSV replay,
generic OBD-II (including the need for a live preflight) and a richer future source that must provide
its own capability report. These statuses do not promise runtime signal availability. The matrix and
profile are emitted under `.validation/phase9a/baseline-profile.json` by `make phase9a-acceptance`.

Numeric outliers remain in dataset rows. Synthetic extremes are labeled `synthetic_boundary`;
real or imported extremes are labeled `possible_real_extreme` for review. The profile also reports
quality exclusions without silently dropping or clamping valid extremes.
