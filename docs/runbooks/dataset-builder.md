# Feature dataset builder runbook

The dataset builder runs as an operator CLI against registered Phase 9A feature snapshots. It is
not a public HTTP export and accepts no SQL, expressions or unbounded output paths.

```bash
apps/api/.venv/bin/python scripts/build_feature_dataset.py \
  --name n55-next-pull-baseline \
  --version v1 \
  --feature-version phase9a-pull-v2 \
  --features raw_context.engine_code,thermal.iat_delta_k,quality.signal_coverage_ratio \
  --cutoff 2026-10-18T12:00:00Z \
  --cutoff-policy row_end \
  --minimum-quality 0.5 \
  --allow-configuration-mixing \
  --source real_vehicle \
  --export-name n55-next-pull-baseline-v1
```

Feature keys are resolved against the active trusted registry; unknown, duplicate or label-source
overlap is rejected. Dataset name/version is immutable: a different definition under an existing
identity fails and requires a new dataset version. Row cutoff may be `row_start`, `row_end` or
`global`. The default prediction horizon is next pull. The builder chooses only snapshots available
by the row cutoff and applies ownership, vehicle/configuration/modification, quality, history and
temporal-lineage checks.

The command writes `<export-name>.jsonl` and `<export-name>.manifest.json` beneath
`apps/api/.artifacts/phase9a/`. JSONL rows contain stable row IDs, entity/time identity, feature
values, explicit missing reasons, quality and lineage hashes. The manifest includes the dataset
definition checksum, feature version, row count, profiles, exclusions and dataset checksum. Writes
are atomic and limited to 64 MiB total. Database commands time out after 60 seconds and a build job
has a five-minute deadline. The artifact directory is ignored by Git; review and
transfer exports through the operator's approved data handling process.

Build queries are capped at 100,000 pulls, 32 MiB of source feature payload and 200,000 lineage
entities. Exclusion reasons are stored in the build manifest. Repeating an unchanged build produces
the same dataset checksum. A failed validation does not publish a completed dataset manifest or
export.

`make phase9a-acceptance` records a synthetic baseline profile and reproducibility receipt under
`.validation/phase9a/`. `make benchmark-features` records actual generation and materialization
performance over at least 100 synthetic pulls. These artifacts are local validation evidence, not
vehicle predictions or model performance claims.
