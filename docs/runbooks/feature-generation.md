# Feature generation runbook

Feature generation is a local operator job over existing canonical data. It is bounded to one
session and at most 100 pulls per invocation. It never calls an external model and has no ECU,
brake, steering or throttle control path.

## Preview and run

Set `DATABASE_URL` to the application's configured PostgreSQL asyncpg URL, then inspect a session
without writing a feature version or FeatureSet:

```bash
apps/api/.venv/bin/python scripts/generate_features.py \
  --session 00000000-0000-0000-0000-000000000000 \
  --max-pulls 100 \
  --dry-run
```

The preview reports candidate pulls, reusable snapshots, expected new snapshots, version and
whether the session exceeds the chosen limit. It is read-only. Run the same bounded session with
an optional timezone-aware observation cutoff:

```bash
apps/api/.venv/bin/python scripts/generate_features.py \
  --session 00000000-0000-0000-0000-000000000000 \
  --observation-cutoff 2026-10-18T12:00:00Z \
  --max-pulls 100
```

If no cutoff is supplied, each pull uses the later of its source creation and end timestamps.
For prediction-oriented datasets, choose a cutoff that represents when the information was
available; do not use a later retrospective timestamp to make information appear pre-event.

## Results and retries

The command prints counts and bounded error categories. Each successful pull commits separately;
a failure on one pull does not roll back other completed pulls. Rerun the session after correcting
the source or restoring database availability. Identical inputs reuse an immutable FeatureSet.
Changed source content creates a new source-hash identity. A version checksum conflict means the
definition/policy changed under an existing name; do not edit stored history—bump the feature-set
version and review its manifest.

The generator caps pull observations at 50,000, history candidates at 1,000, prior events at
1,000, historical pulls per target at 20, and batch size at 100. Database commands time out after
60 seconds; a dry run has a 30-second job timeout and a generation job has a five-minute timeout.
A cutoff that predates the target
pull or its entity context is rejected. Error output omits exception text and database contents.

## Validation

`make test-features` exercises pure calculations and invariants. `make phase9a-acceptance` runs the
independent evaluator against freshly migrated disposable TimescaleDB. `make
test-feature-integration` verifies actual SQL persistence, history, idempotency and cutoff behavior.
