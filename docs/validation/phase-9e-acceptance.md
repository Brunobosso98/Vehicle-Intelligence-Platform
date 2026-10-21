# Phase 9E acceptance

The authoritative implementation scope is [the 134-section Phase 9E prompt](../prompts/phase-9e-prediction-evidence.md). This report records the focused disposable-database acceptance and its caveats. The final commit SHA, PR state, required exact-head checks and canonical validation artifact are recorded in the [PR #45 handoff and checks](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/45#checks); an earlier SHA is never treated as proof for a later head.

## Focused local result

On 2026-10-21, `bash scripts/phase9e-validation.sh` completed successfully in a fresh, isolated TimescaleDB Compose project. The evaluator emitted `status=PASS` for 11 evidence receipts: three supervised 9B tasks, four 9C families, three additional abstentions and one same-pull 9B/9C correlation case. Seven bundles retained `READY_SCORE`; four retained abstention. The run includes upgrade/downgrade/re-upgrade through migration 0017, actual FastAPI routes, source verification, integrity adversaries, concurrency and observability assertions.

The ignored local receipt is `.validation/phase9e/acceptance.json`. Its `git_sha` is `09ca5a480b8d14176bb7e8f51ecb1b503020315f`, the checkout HEAD recorded while the tested working tree contained uncommitted changes. Treat this as focused working-tree evidence, not exact-commit proof. The final canonical workflow runs the same evaluator against the pushed SHA and uploads its commit-bound artifact. We did not restart the already-passing broad local suites for this correction.

`git diff --check` and targeted Ruff checks for the modified Python files passed. Earlier local checks remain historical evidence on their recorded source: `make verify-cloud` (1,216 API tests and 52 Web tests), `make test-integration` (13 passed), `make containers`, and `make security`. They were not rerun after the Phase 9E changes. Exact final-head regression and security status must be read from PR #45.

## Scenarios and measured bounds

The evaluator trains and approves the existing 9B/9C fixture versions, creates real 9D receipts, and independently compares source rows, checksums, cutoffs and graph relationships. It exercises:

- `0016 -> 0017 -> 0016 -> 0017`, fresh upgrade and unchanged digests for 27 Phase 0–9D tables;
- three scored `NEXT_PULL` tasks, four 9C anomaly families, low-quality/missing-fuel/missing-FeatureSet abstentions, and a 9B/9C pair that shares one FeatureSet but retains independent receipts, evidence IDs, scores, claims and horizons;
- a target pull beginning after the 9B input cutoff, with 48 observed target measurements after cutoff; target pull and FeatureSet IDs are absent from all supervised evidence;
- late-ingested telemetry with an old observation time and a modification created after cutoff with an earlier effective date; the frozen FeatureSet ID, values and hashes remain unchanged and neither late record enters the same-pull bundles;
- a valid 9C reference row appended after the original cutoff; verification rejects the changed frozen counts with `FAILED_SOURCE_MISMATCH` / `PROVENANCE_MISMATCH`;
- 10 concurrent same-receipt requests with one evidence identity, and a 100-request replay/admission burst with 16 accepted replays and 84 bounded 429 responses;
- source, finding, model/detector artifact, missing artifact, database outage, timeout, immutability, rollback, audit-cap, authentication, peer-scope and safe-projection controls.

The observed graph limits are 32 nodes, 64 edges, 48 facts and 16 gaps; the persisted/HTTP manifest cap is 65,536 bytes. The run's largest projection was 2,317 bytes, maximum checked-out database sessions were 10, and observed RSS delta was 138,228 KiB. The mixed HTTP handler sample reported p50 0.00291 s and p95 2.38745 s; it includes cold materialization, replay and admission paths and is not a build-only SLA. No production latency or real-world accuracy is claimed.

Metrics and traces are checked for bounded labels and absence of vehicle/evidence identifiers. The report lists the exact metrics and spans. Error, migration, lineage, benchmark and security details are preserved in the acceptance JSON rather than summarized as a generic “confidence” score.

## Boundaries and exact-head result

All fixtures are synthetic. No real-car validation, fleet accuracy, calibration, diagnosis, causal claim or ECU control is established. Optional imported-data smoke (§126) is `NOT RUN` because no sanitized, eligible imported cohort was available; its reference support was not weakened to manufacture one.

The [traceability ledger](phase-9e-traceability-ledger.md) maps all 134 specification sections. Phase 9F agents, 9G calibration and 9H UI remain absent. PR #45 must remain open and unmerged until the user reviews the report and merges manually. Its current body records the exact SHA and direct required-check URLs after those checks finish.

Reproduce the focused database gate with `bash scripts/phase9e-validation.sh` (Docker required). The canonical GitHub `full-validation` workflow also runs the focused unit suite, disposable acceptance, benchmark and observability targets. Do not substitute an older green run for the current PR head.
