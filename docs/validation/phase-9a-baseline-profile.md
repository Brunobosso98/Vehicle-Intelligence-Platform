# Phase 9A baseline profile

This profile summarizes the 4 eligible rows in the controlled synthetic acceptance dataset. The
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

Mean pull completeness was 0.9625. All four rows were synthetic and passed the dataset's quality
filter. The profiling routine also reports quantiles, dispersion, category counts, time/configuration
and vehicle distributions, missingness and possible extremes. It flags possible extremes for review
without removing or clamping observations. Run `make phase9a-acceptance` to regenerate the full
availability matrix and profile under `.validation/phase9a/baseline-profile.json`.
