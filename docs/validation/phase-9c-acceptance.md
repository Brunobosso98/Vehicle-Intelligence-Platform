# Phase 9C acceptance

## Scope and status

Phase 9C implements offline anomaly scoring over canonical Phase 9A FeatureSets. The disposable
database acceptance completed with `PASS` against all predeclared fixture floors. This is controlled
engineering evidence, not real-car accuracy or diagnostic validation.

The implementation lives on branch `codex/phase-9c-anomaly-detection`, based on required Phase 9A/9B
ancestor `105ef5a12f055558c55d87204f3ea5a91af73a13`. Schema change `0015_anomaly_detection` is
additive. The acceptance wrapper upgraded from `0014` to head, downgraded to `0014`, and re-upgraded
to head in a disposable TimescaleDB before evaluation.

| Check                             | Result                                                                                         |
| --------------------------------- | ---------------------------------------------------------------------------------------------- |
| Focused Phase 9C unit suite       | PASS; 31 anomaly tests in the exact-head `quality` job                                         |
| Disposable DB and evaluator       | PASS; migration round trip, synthetic floors, leakage, artifact, replay and persistence checks |
| Imported-data compatibility smoke | PASS locally; 264 features generated; eight fits explicitly rejected for insufficient support  |
| Canonical full validation         | PASS on implementation SHA `c4da7f5`; Docker/full-stack and Phase 0–9C gates                   |
| CI and Security                   | PASS on implementation SHA `c4da7f5`; quality, E2E, CodeQL, dependency review and Security     |

The authoritative exact-head receipt is the GitHub Actions artifact from `full-validation` run
[39311720740](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/39311720740),
artifact `phase-0-full-validation-c4da7f5df85f6a91e7add628e41c03885bd5f049` (artifact ID
`12218816453`). It records commit `c4da7f5df85f6a91e7add628e41c03885bd5f049`, `execution_state=PASS`,
153 FeatureSets, 37 detection runs and 581 findings. The artifact summary marks the full gate,
database/migrations, E2E, security, observability and Phase 9A/9B/9C pipelines `PASS`.

PR [#43](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/43) targets `main`,
is open and unmerged. Exact-head CI run
[39311720209](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/39311720209)
passed `quality` and `integration-e2e`; Security run
[39311720627](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/39311720627)
passed Security, both CodeQL analyses and dependency review. The canonical full-validation run
took 36m56s. These checks are tied to the exact implementation SHA above; the documentation-only PR update
will receive its own GitHub checks.

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

The first local `make verify` run passed through Phase 9A and stopped at Phase 9B because the
validation wrapper did not export the recorded Git SHA. The wrapper was corrected and
`make phase9b-acceptance` passed in isolation. The remaining gates were then resumed individually:
anomaly tests, Phase 9C acceptance, stream recovery, stack and E2E checks, live-stream benchmark,
security, observability and documentation all passed. Earlier gates through Phase 9A had already
passed in the first run. This is completed gate-by-gate coverage; a single uninterrupted `make verify`
run is not claimed. The local receipts were created from a dirty worktree and therefore
are not represented as commit-tied evidence.

The canonical GitHub `full-validation` workflow is the Docker/full-stack executor and passed on the
recorded head. The PR targets `main` and remains unmerged for the user.

See the [traceability ledger](phase-9c-traceability-ledger.md) for section-by-section coverage.
