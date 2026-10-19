# Phase 9C acceptance

## Scope and status

Phase 9C implements offline anomaly scoring over canonical Phase 9A FeatureSets. The disposable
database acceptance completed with `PASS` against all predeclared fixture floors. This is controlled
engineering evidence, not real-car accuracy or diagnostic validation.

The implementation lives on branch `codex/phase-9c-anomaly-detection`, based on required Phase 9A/9B
ancestor `105ef5a12f055558c55d87204f3ea5a91af73a13`. Schema change `0015_anomaly_detection` is
additive. The acceptance wrapper upgraded from `0014` to head, downgraded to `0014`, and re-upgraded
to head in a disposable TimescaleDB before evaluation.

| Check                             | Result                                                                                |
| --------------------------------- | ------------------------------------------------------------------------------------- |
| Focused Phase 9C unit suite       | Pending full local regression command below                                           |
| `make phase9c-acceptance`         | PASS; migration round trip and independent evaluator completed                        |
| Imported-data compatibility smoke | PASS; 264 features generated; eight fits explicitly rejected for insufficient support |
| `make verify`                     | Pending                                                                               |
| Exact PR-head GitHub checks       | Pending push and PR creation                                                          |

The latest Phase 9C acceptance produced `.validation/phase9c/acceptance.json` locally. The JSON is
ignored build evidence; the summarized metrics are in the [model evaluation report](phase-9c-model-evaluation.md).
Final delivery records the tested commit and exact PR-head checks separately so a dirty-worktree
run is not presented as a commit-tied receipt.

## Implemented checks

- Four separate families: thermal, boost/air, performance and fuel.
- Robust MAD and bounded Isolation Forest candidates; method and threshold are selected from
  validation sessions only.
- Exact vehicle/configuration/modification/source cohorts, strict temporal cutoffs, quality and
  signal gating, explicit abstentions, immutable findings and deterministic replay identity.
- Artifact checksum/path validation, tampering rejection, metric-label cardinality checks and all
  expected anomaly spans.
- Session-level holdout with a later expanding-window validation/test fold.
- Clean-control false positives are measured separately from cross-family injection alarms.
- 1,000 direct offline scores per method; database reads and finding persistence are timed
  separately.
- No paid Phase 7D provider evaluation or Phase 8 embedding operation was invoked.

The acceptance recorded all predeclared recall, clean-control false-positive, coverage and
temporal-fold floors as met. The selected method was Robust MAD for every family. Replay identity,
artifact tampering, immutable finding, anchor/configuration/vehicle context, missing-fuel and
quality-control checks passed. The evaluator observed zero checked-out database connections
before engine close.

## Regression and handoff status

The full local regression result and final commit are added after `make verify` completes. The
canonical GitHub `full-validation` workflow is the Docker/full-stack executor; its receipt must
match the final pushed SHA. The PR targets `main` and remains unmerged for the user.

See the [traceability ledger](phase-9c-traceability-ledger.md) for section-by-section coverage.
