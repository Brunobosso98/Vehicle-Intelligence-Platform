# Phase 9E evidence evaluation

The acceptance evaluator is `scripts/evaluate_prediction_evidence.py`. It consumes controlled
synthetic records created by the existing Phase 9A feature service, Phase 9B training pipeline,
Phase 9C detector pipeline and Phase 9D approval/serving service. It then uses protected HTTP
requests to materialize and verify 9E bundles. The independent assertions query PostgreSQL source
rows and compare their canonical row checksums, IDs, thresholds, output status, cutoff, feature
values/units, label definitions, anomaly finding/run and frozen reference context.

## Fixture matrix

| Source path             | Required cases                                               | Independent assertions                                                                                |
| ----------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| 9B `NEXT_PULL`          | Thermal degradation, performance degradation, fuel deviation | Exact task/version, score, threshold, decision, eligible FeatureSet and label rule; no target outcome |
| 9B abstentions          | Missing fuel, low quality, missing FeatureSet                | Original abstention preserved; score remains null; gap and completeness remain explicit               |
| 9C `AFTER_PULL_OFFLINE` | Thermal, boost/air, performance and fuel families            | Exact detector/finding/run/reference, family, method, threshold, reference cohort and cutoff          |
| Same-pull cross-source  | One 9B performance result and one 9C performance result      | Shared FeatureSet but different receipt/evidence IDs, source graphs, score, claims and horizons       |
| Cross-cutting           | replay, tamper, revoke, auth and budgets                     | Deterministic ID, immutable rows, historical read, no unsafe disclosure, bounded metric/span labels   |

## Temporal and correlation sentinels

The 9B input cutoff is taken from the recorded input-availability timestamp for a training row;
the corresponding target pull starts later and has measured telemetry after that cutoff. The
evaluator verifies all three supervised bundles omit the target pull and FeatureSet identifiers,
and that no target outcome is included in their facts.

For the same-pull pair, 9B `NEXT_PULL` and 9C `AFTER_PULL_OFFLINE` share the exact 9A FeatureSet.
They retain distinct receipts, evidence IDs, model/detector lineage and claim scopes. The acceptance
does not produce a consensus score or count the shared source as independent corroboration.

After the original source snapshot is captured, the evaluator inserts a telemetry sample with an
old observation time but ingestion time after the request cutoff, and a modification with an
effective installation date before the pull but creation time after the cutoff. The 9A snapshot ID,
values and hashes remain unchanged; neither inserted record appears in the 9B or 9C evidence.
Separately, a valid 9C reference row is appended with a post-cutoff availability timestamp. Its
updated observed row/session counts differ from the frozen parent manifest, and independent 9E
verification must return `FAILED_SOURCE_MISMATCH` with `PROVENANCE_MISMATCH`. Phase 9F runs before
this sentinel is appended so its reads use the pristine shared fixtures. The sentinel remains in
the disposable database until teardown because the 9C reference rows are immutable.

The report records each materialized receipt's evidence and source IDs, prediction status,
completeness, integrity, quality coverage and gap codes, along with aggregate completeness,
integrity and prediction-status counts.
An `eligible` bundle requires an original `READY_SCORE`, `COMPLETE` completeness and both source
and independent verification integrity `VERIFIED`. It distinguishes those bundles from partial
bundles, abstained explanations, failed source verification, unsupported schemas and
unavailable-artifact snapshots. Source verification adversaries are counted separately from the
materialized bundle outcomes.

Benchmark output includes total evaluator wall time and Python-process CPU time; the CPU figure
excludes child processes. The configured CPU concurrency limit is two. The report also records
receipts, nodes, edges, facts, gaps, replay latency/identity, 10- and 100-request behavior, response
bytes, RSS and observed database sessions. It does not convert synthetic fixtures into claims about
real-car reliability. Optional imported-data smoke is reported as `NOT_RUN` unless a sanitized
eligible fixture and same-cohort reference support exist.

## Integrity adversaries

The evaluator mutates one disposable 9A feature value, a persisted 9C finding value, and registered
model/detector artifact bytes; it observes mismatches, restores the mutable test fixtures in
`finally` blocks and verifies recovery. Missing artifact state is reported as
`VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE`. The post-cutoff reference-row case is detected after
Phase 9F completes; the immutable sentinel remains only for the lifetime of the disposable Compose
database. Database checks exercise update/delete triggers, duplicate logical identity, oversized
JSONB, orphan source rows and transaction rollback after an invalid normalized graph insert. These
operations are confined to the isolated Compose test database and temporary artifact directory.

The expected success rate for source integrity, deterministic replay, cutoff checks, privacy checks
and admission controls is 100%. There is no model-accuracy threshold in Phase 9E. All observed
numbers are emitted in `.validation/phase9e/acceptance.json` and are tied to that report's `git_sha`.
