# Offline model training runbook

Phase 9B training is an operator-only offline workflow. It produces engineering-validation evidence
or a rejected training run. It does not make a diagnosis, serve a prediction, or control the vehicle.

## Before training

- Confirm migrations are current (`make db-migrate`) and the database has Phase 9A feature snapshots.
- Use a read-only copy or disposable database for evaluation. The CLI refuses a production
  environment, but it still writes versioned dataset/model/training records to the configured DB.
- Choose one task, an explicit timezone-aware observation cutoff and source role. Never mix
  synthetic evidence with real vehicle evidence without declaring `mixed`.
- Confirm the task's required outcome signals are present. Fuel deviation is source-limited and
  requires at least two compatible prior pulls.

## Train

```bash
make phase9b-train PHASE9B_ARGS="--task NEXT_PULL_THERMAL_DEGRADATION --observation-cutoff 2026-10-01T00:00:00Z --source-role real_vehicle"
```

The supported tasks are `NEXT_PULL_THERMAL_DEGRADATION`,
`NEXT_PULL_PERFORMANCE_DEGRADATION`, and `NEXT_PULL_FUEL_DEVIATION`; supported source roles are
`synthetic`, `real_vehicle`, `imported`, `imported_fixture`, and `mixed`. The command applies the
registered feature version, builds separate input/outcome snapshots, records exclusions, trains
fixed baselines/candidates and writes the artifact and registry receipt. It prints a bounded JSON
summary; inspect the persisted `TrainingRun`, dataset manifests and model version for the full
lineage.

Rows below the declared total/class minimums, a missing class in a temporal partition, missing
target signals or failed acceptance criteria produce a rejected run and no usable model version.
Correct source coverage or collect more compatible observations; do not weaken task thresholds to
force a candidate.

## Review and offline inference

Review all candidate validation metrics, selected threshold, dummy comparison, final test metrics,
walk-forward folds, scenario holdout, held-out vehicle/configuration results, overfit warnings and
feature associations. The test partition is evaluated after selection and must not influence model
or threshold choice. A result marked `CANDIDATE` is an offline engineering candidate only.

The Python offline inference helper accepts only a registered model/version and its exact feature
schema, units, missingness and quality map. Its `engineering_validation_score` is not calibrated as
a failure probability. Joblib artifacts are trusted internal files; do not load or copy in external
pickle/joblib files.

## Validation commands

```bash
make test-models
make phase9b-acceptance
make benchmark-models
make model-observability
```

The acceptance command creates and destroys a fresh disposable TimescaleDB. It runs the canonical
Phase 9A feature generator, all three task pipelines, artifact registration/loading, leakage and
boundary sentinels, repeated training, and holdout checks. Benchmark and observability commands
summarize the measured acceptance evidence. `.validation/phase9b/` holds ignored local evidence;
the committed validation report records the reviewed results and caveats.
