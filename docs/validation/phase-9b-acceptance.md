# Phase 9B acceptance report

## Status and scope

The focused disposable-database Phase 9B acceptance passed with a seeded fixture of 200 pulls,
40 sessions, 8 vehicles and 16 configurations. The evaluator used the canonical
`FeatureGenerationService.generate_session` path, persisted all three supervised datasets and
model versions, repeated deterministic training, staged and loaded each artifact, and checked
offline inference against in-process predictions. This is `ENGINEERING_VALIDATION` on controlled
synthetic data. It is not real-world validation, a mechanical diagnosis, or a failure probability.
The disposable database upgraded through revision `0013` to head, downgraded to `0013`, and
re-upgraded through head before the acceptance fixture ran.

The Phase 9B candidate consumes the merged Phase 9A mainline code. Exact-head validation and
GitHub check status are recorded in PR #42; this report records local acceptance evidence, not a
merge or deployment.

## Label and dataset evidence

All tasks use `NEXT_PULL`, pair with the immediate compatible candidate pull, and keep input
features separate from target outcome measurements. Same vehicle, configuration, active
modifications and session sequence are required. Missing/ineligible next outcomes remain explicit
exclusions. The model input schema rejects target-source keys, future-only values and identity-like
features.

| Task                    | Rows | Negative / positive | Main exclusions                                                                       |
| ----------------------- | ---: | ------------------: | ------------------------------------------------------------------------------------- |
| Thermal degradation     |  158 |             88 / 70 | 40 no compatible next pull; 1 insufficient outcome quality                            |
| Performance degradation |  158 |            106 / 52 | 40 no compatible next pull; 1 insufficient outcome quality                            |
| Fuel deviation          |  141 |             74 / 67 | 40 no compatible next pull; 17 missing outcome signal; 1 insufficient outcome quality |

Input and outcome snapshots use `phase9a-pull-v2` and task-specific cutoff-versioned dataset
definitions. Supervised dataset manifests retain the input/outcome checksums, label/model-spec
checksums, ordered input keys, row identities, target provenance, source role, quality and
exclusions. Fixture identities are intentionally not copied into this report.

## Model evaluation

Each family was fit on train data and compared on validation. The threshold came from validation.
The final test set was evaluated only after family selection; only the selected family and dummy
baseline were scored there. Average precision (AP), F1 and balanced accuracy (BA) are shown; an
undefined dummy F1 means it predicted no positives.

| Task        | Candidate           | Validation AP | Validation F1 | Validation BA |
| ----------- | ------------------- | ------------: | ------------: | ------------: |
| Thermal     | Dummy               |         0.406 |     undefined |         0.500 |
| Thermal     | Logistic regression |         0.609 |         0.769 |         0.806 |
| Thermal     | Random forest       |         0.855 |         0.769 |         0.806 |
| Performance | Dummy               |         0.344 |     undefined |         0.500 |
| Performance | Logistic regression |         0.773 |         0.786 |         0.857 |
| Performance | Random forest       |         0.749 |         0.762 |         0.816 |
| Fuel        | Dummy               |         0.500 |     undefined |         0.500 |
| Fuel        | Logistic regression |         0.761 |         0.720 |         0.750 |
| Fuel        | Random forest       |         0.889 |         0.828 |         0.821 |

| Task        | Selected family / threshold | Test AP | Test F1 | Test BA |             Test support |
| ----------- | --------------------------- | ------: | ------: | ------: | -----------------------: |
| Thermal     | Random forest / 0.50        |   0.885 |   0.786 |   0.810 | 18 negative, 14 positive |
| Performance | Logistic regression / 0.45  |   0.788 |   0.643 |   0.745 | 22 negative, 10 positive |
| Fuel        | Random forest / 0.40        |   0.889 |   0.759 |   0.776 | 17 negative, 13 positive |

All three candidates met the predeclared synthetic engineering acceptance rules. Performance was
selected as logistic regression because it had the highest validation AP. Its test F1 is 0.643,
below the validation F1 of 0.786, while its vehicle-holdout F1 is 0.737. The weaker test result is
retained as a limitation. Holdout metrics are reported separately and are not used to tune the
selected model:

| Task        | Scenario holdout AP / F1 / BA | Vehicle holdout AP / F1 / BA | Configuration holdout AP / F1 / BA |
| ----------- | ----------------------------- | ---------------------------- | ---------------------------------- |
| Thermal     | 0.872 / 0.720 / 0.766         | 0.826 / 0.737 / 0.753        | 0.698 / 0.836 / 0.858              |
| Performance | 0.855 / 0.677 / 0.767         | 0.931 / 0.737 / 0.771        | 0.789 / 0.680 / 0.792              |
| Fuel        | 0.761 / 0.692 / 0.720         | 0.882 / 0.714 / 0.792        | 0.752 / 0.700 / 0.682              |

The independent negative control is `quality.duplicate_timestamp_count`, populated by a
deterministic hash-based duplicate `vehicle.speed` observation in about one quarter of synthetic
pulls. Its validation permutation-importance shares were 0.8% thermal, 2.7% performance and 2.4%
fuel; acceptance rejects a control carrying at least half of total importance. The current-pull
`quality.sample_interval_stddev_s` remains a performance input because it derives from RPM timing;
it is not labeled as an irrelevant control.

The fixture also retained cross-task confounder examples: 65 high-IAT rows without performance
degradation, 22 performance-degradation rows with stable IAT delta, 36 fuel-deviation rows with
normal boost, and 106 rows with boost variation but no performance degradation. These are
controlled negative/positive examples, not a claim that the same relationships hold in real data.

There are three expanding walk-forward folds per task; the small fold support is summarized with
undefined metrics and warnings where applicable. Scores and reliability summaries are engineering
observations only. No calibration claim is made.

## Reproducibility, artifact and resource evidence

For each task, repeated training produced identical split IDs, selected family, predictions within
`1e-12` and metrics. Artifact byte determinism is not claimed. Each selected artifact was written
atomically, smoke-tested before registration, loaded by registered version/checksum and produced
the same offline score as in-process inference. Each task measured 1,000 offline predictions at
about 178–794 predictions/s on this workstation. The full acceptance took about 48 seconds and
observed about 264 MiB peak process RSS; these values are machine-specific synthetic benchmarks.

All tasks reached `CANDIDATE` state, with 3 labels, 3 models, 3 supervised datasets, 3 model
versions and 3 training runs. Observed metrics covered training, candidate evaluation, dataset rows,
artifact size and exclusions. Required training spans were observed; metric/span evidence excludes
vehicle, session, pull, VIN, feature values and sample content.

## Imported-data compatibility smoke

A copied local development database contained 74 CSV-source sessions. On the disposable copy,
canonical Phase 9A feature generation completed for all 204 imported pulls with no generation
errors. All three task dataset and training paths were exercised, but no eligible outcome rows were
available: task outcome features were unavailable or pairs failed signal, compatibility and
next-pull checks. The training path stopped before fitting because it could not form chronological
groups. No real-data predictive metrics are reported, and this smoke does not support an accuracy
claim.

## Safety and limitations

- The fixture is synthetic and intentionally controlled; its feature/label relationships are not
  evidence of real vehicle behavior or fleet generalization.
- The thermal 3 K, performance 8%, and fuel ratio 0.88 rules are relative engineering labels, not
  OEM thresholds. Fuel results require recorded compatible history and real target pressure.
- A model score is not a probability of component failure, a diagnosis, maintenance instruction or
  reason to change vehicle operation.
- Synthetic sample sizes, including the held-out vehicle and temporal folds, are small. Real-data
  acceptance requires source-coverage review and sufficient independent support.
- Joblib artifacts use pickle semantics. Only registry-backed, application-created artifacts under
  the fixed internal root may be loaded.

The full machine-readable report is generated at ignored `.validation/phase9b/acceptance.json` by
`make phase9b-acceptance`. See the [traceability ledger](phase-9b-traceability-ledger.md),
[model cards](../ml/models/), and [training runbook](../runbooks/model-training.md).
