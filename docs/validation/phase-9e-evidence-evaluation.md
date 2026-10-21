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
| Cross-cutting           | replay, tamper, revoke, auth and budgets                     | Deterministic ID, immutable rows, historical read, no unsafe disclosure, bounded metric/span labels   |

The report records actual counts and values for receipts, bundles, nodes, edges, facts, gaps,
completeness, integrity, replay latency/identity, 10- and 100-request behavior, response bytes,
RSS and observed database sessions. It does not convert synthetic fixtures into claims about
real-car reliability. Optional imported-data smoke is reported as `NOT_RUN` unless a sanitized
eligible fixture and same-cohort reference support exist.

## Integrity adversaries

The evaluator mutates one disposable 9A feature value and a registered artifact byte, observes a
source mismatch, restores each source in a `finally` block and verifies recovery. Database checks
exercise update/delete triggers, duplicate logical identity, oversized JSONB, orphan source rows
and transaction rollback after an invalid normalized graph insert. These are destructive only to
the isolated Compose test database and temporary artifact directory.

The expected success rate for source integrity, deterministic replay, cutoff checks, privacy checks
and admission controls is 100%. There is no model-accuracy threshold in Phase 9E. All observed
numbers are emitted in `.validation/phase9e/acceptance.json` and are tied to that report's `git_sha`.
