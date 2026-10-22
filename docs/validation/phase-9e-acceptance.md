# Phase 9E acceptance

The authoritative implementation scope is [the 134-section Phase 9E prompt](../prompts/phase-9e-prediction-evidence.md). This report records the focused disposable-database acceptance and its caveats. The final commit SHA, PR state, required exact-head checks and canonical validation artifact are recorded in the [PR #45 handoff and checks](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/45#checks); an earlier SHA is never treated as proof for a later head.

## Focused local result

On 2026-10-22, `bash scripts/phase9e-validation.sh` completed with `status=PASS` in a fresh, isolated TimescaleDB Compose project. The evaluator ran against commit `a8101239e41c0b690c9e094c478b6c99551f913b` and produced 11 evidence bundles: three supervised 9B tasks, four 9C families, three additional abstentions and one same-pull 9B/9C correlation case. The receipt outcome counts are 7 `READY_SCORE` and 4 abstained. Completeness is 4 `COMPLETE`, 3 `PARTIAL` and 4 `ABSTAINED`; 4 bundles meet the evaluator's `eligible` definition (`READY_SCORE`, `COMPLETE`, source integrity `VERIFIED` and independent verification `VERIFIED`). All 11 source and independent verifier outcomes are `VERIFIED`; failing, unsupported-schema and not-verifiable counts are each zero. Tamper-control failures are reported separately from these original bundle outcomes.

The run includes upgrade/downgrade/re-upgrade through migration 0017, actual FastAPI routes, source verification, integrity adversaries, concurrency and observability assertions. `make phase9e-acceptance` was not used because it also reruns the already-passing unit suite; the focused database evaluator script was run directly. No frontend tests were rerun. The ignored machine receipt is `.validation/phase9e/acceptance.json` and records the tested commit SHA. The existing GitHub checks are green on PR head `f82e162078c4077e64e00f46dab7164880369521`; they do not yet apply to this local commit.

The saved receipt also passed the benchmark and observability report checks. Its aggregate bundle outcomes are:

| Measure | Count |
| --- | ---: |
| Original 9D receipts / evidence bundles | 11 |
| `READY_SCORE` / abstained prediction statuses | 7 / 4 |
| `COMPLETE` / `PARTIAL` / `ABSTAINED` completeness | 4 / 3 / 4 |
| Eligible (`READY_SCORE` + complete + both integrity checks verified) | 4 |
| Source integrity / independent verification `VERIFIED` | 11 / 11 |
| Failed source verification / unsupported schema / not verifiable | 0 / 0 / 0 |

All three scored supervised results retain their original 9D score, threshold, decision, FeatureSet and model version:

| 9B task | Receipt | FeatureSet | Model version | Score / threshold / decision | Completeness |
| --- | --- | --- | --- | --- | --- |
| Fuel deviation | `3eeeb805-cc87-4e51-9b65-df59536de60a` | `4aa293b0-7c1e-49d1-b553-e80f625c77a6` | `a020f3d8-0443-41e1-98a3-dc4abbcc893f` | `0.4370848 / 0.40 / true` | COMPLETE |
| Performance degradation | `2c4fa67d-ea07-471f-84e0-93aeeea1a1d0` | `4aa293b0-7c1e-49d1-b553-e80f625c77a6` | `6ab13d1c-0037-4a67-958c-8e84915ad6ee` | `0.8055819 / 0.45 / true` | COMPLETE |
| Thermal degradation | `795771af-d32c-4446-83c1-68da12bf27c8` | `4aa293b0-7c1e-49d1-b553-e80f625c77a6` | `94ac17c0-4bb5-4c87-ac16-8d72f70b4b79` | `0.1572972 / 0.50 / false` | COMPLETE |

The four anomaly families preserve their distinct `AFTER_PULL_OFFLINE` results and frozen 9C chain. They share FeatureSet `e2bf9879-94da-459d-b336-86a115066bb4`, feature version `bd820338-182c-4ae9-b68e-f6b0be305cc8` and `synthetic` source role; each has its own detector, finding, run and reference dataset. The table lists the finding, run and reference IDs from the acceptance receipt; all four chains independently verified against their source rows. The emitted gap-reason tally was `FEATURE_SET_UNAVAILABLE: 2`, `FUEL_PRESSURE_SIGNAL_UNAVAILABLE: 2`, `INPUT_QUALITY_BELOW_SERVING_FLOOR: 2` and `INSUFFICIENT_SIGNAL: 1` (occurrences across gap records, not unique receipts).

| 9C family | Receipt | Detector version | Finding | Run | Reference dataset | Score / threshold / result | Completeness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Boost/air | `13f962c6-9678-4216-a36f-5d3c4bf72034` | `17ec9202-094f-4139-b741-9950d87d5e47` | `d7e164f7-850e-4018-b3e9-a445cd26b932` | `1392e14c-e2d3-41ce-8e11-9aeaa5a54e76` | `d9174835-a879-4c14-b979-850358ce2bdc` | `0.3372454 / 3.5 / INLIER` | PARTIAL |
| Fuel | `117b5c3e-c7c5-493d-a9bc-3c1f540505bb` | `0d46a41e-442f-469b-9db4-8324130fe8aa` | `6284bc32-383b-4942-866e-69142c82a70d` | `7f4571f1-92eb-4e3f-91d6-4670e0cfe6d3` | `e185fc84-5b28-4be4-98f0-082325a26de7` | `1.3489815 / 3.5 / INLIER` | PARTIAL |
| Performance | `6445fb6f-aab2-4803-a727-c05a8883ccb7` | `b174cb8b-b7e7-475f-96ab-c84198d7c4c5` | `e489de58-ff8e-4b23-8f80-c615fc5da1b6` | `262a08f2-fe5d-4d0e-b998-827054477366` | `f81904aa-0e45-4db1-9b08-ef33acad7e9d` | `0.0 / 3.5 / INLIER` | PARTIAL |
| Thermal | `5fb27337-3493-43f9-8df6-dfd02690ea75` | `a2809fef-c1cf-4493-812f-365ced021c10` | `8b3e31bc-4b68-4ea8-9eb9-01b990c5cfb2` | `24f81d9a-87c5-4372-ae7f-1ac6febd82df` | `d99375c8-8dfc-4a53-a2a0-ba47678f1c25` | `no score / 3.5 / ABSTAINED_INSUFFICIENT_SIGNAL` | ABSTAINED |

`git diff --check`, targeted Ruff checks and Python compilation passed for the evaluator changes. Earlier broad local checks remain evidence on their recorded source: `make verify-cloud` (1,216 API tests and 52 Web tests), `make test-integration` (13 passed), `make containers` and `make security`. They were not rerun for this correction. The current local acceptance is not a substitute for exact-final-SHA GitHub checks.

## Scenarios and measured bounds

The evaluator trains and approves the existing 9B/9C fixture versions, creates real 9D receipts, and independently compares source rows, checksums, cutoffs and graph relationships. It exercises:

- `0016 -> 0017 -> 0016 -> 0017`, fresh upgrade and unchanged digests for 27 Phase 0–9D tables;
- three scored `NEXT_PULL` tasks, four 9C anomaly families, low-quality/missing-fuel/missing-FeatureSet abstentions, and a 9B/9C pair that shares one FeatureSet but retains independent receipts, evidence IDs, scores, claims and horizons;
- a target pull beginning after the 9B input cutoff, with 48 observed target measurements after cutoff; target pull and FeatureSet IDs are absent from all supervised evidence;
- late-ingested telemetry with an old observation time and a modification created after cutoff with an earlier effective date; the frozen FeatureSet ID, values and hashes remain unchanged and neither late record enters the same-pull bundles;
- a valid 9C reference row appended after the original cutoff; verification rejects the changed frozen counts with `FAILED_SOURCE_MISMATCH` / `PROVENANCE_MISMATCH`;
- 10 concurrent same-receipt requests with one evidence identity, and a 100-request replay/admission burst with 16 accepted replays and 84 bounded 429 responses;
- source, finding, model/detector artifact, missing artifact, database outage, timeout, immutability, rollback, audit-cap, authentication, peer-scope and safe-projection controls.

The observed graph limits are 32 nodes, 64 edges, 48 facts and 16 gaps; the persisted/HTTP manifest cap is 65,536 bytes. This run measured 122 benchmark samples, a 2,317-byte largest projection, 10 maximum checked-out database sessions, and a 137,988 KiB process RSS increase. The mixed HTTP handler sample reported p50 0.002624 s and p95 2.480912 s; it includes cold materialization, replay and admission paths and is not a build-only SLA. Total evaluator wall time was 415.495 s and Python-process CPU time was 162.394 s (child processes excluded). The 10-way same-receipt run completed in 2.079 s; the 100-request burst completed in 3.867 s with 16 accepted replays, 84 bounded 429 responses and one evidence identity. No production latency or real-world accuracy is claimed.

Metrics and traces are checked for bounded labels and absence of vehicle/evidence identifiers. The report lists the exact metrics and spans. Error, migration, lineage, benchmark and security details are preserved in the acceptance JSON rather than summarized as a generic “confidence” score.

## Boundaries and exact-head result

All fixtures are synthetic. No real-car validation, fleet accuracy, calibration, diagnosis, causal claim or ECU control is established. Optional imported-data smoke (§126) is `NOT RUN` because no sanitized, eligible imported cohort was available; its reference support was not weakened to manufacture one.

The [traceability ledger](phase-9e-traceability-ledger.md) maps all 134 specification sections. Phase 9F agents, 9G calibration and 9H UI remain absent. PR #45 must remain open and unmerged until the user reviews the report and merges manually. Its current body records the exact SHA and direct required-check URLs after those checks finish.

Reproduce the focused database gate with `bash scripts/phase9e-validation.sh` (Docker required). The canonical GitHub `full-validation` workflow also runs the focused unit suite, disposable acceptance, benchmark and observability targets. Do not substitute an older green run for the current PR head.
