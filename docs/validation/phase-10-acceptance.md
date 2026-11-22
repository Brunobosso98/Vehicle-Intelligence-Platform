# Phase 10 acceptance status

Status: **NOT VERIFIED.** The isolated Phase 10 acceptance rerun passed on SHA `04c6c49b82f51b3e1dc900c60db232f4065e1a9a`. The canonical Docker/full-stack workflow did not run on that SHA (its run was canceled before the focused retry completed); it must pass, along with all required exact-head checks, on the final report SHA.

PR: [#64](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/64), open, targeting `main`; do not merge. Phase 9H PR #57 is in the merged baseline `3085c5227a46c3c327249d0f2e982631d919b5a4`.

## Exact-SHA receipts on implementation SHA 439e099

| Gate                                                                 | Run                                                                                                   | Result                                                                                                        |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Phase 10 independent acceptance                                      | [44980758277](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44980758277) | PASS                                                                                                          |
| Quality and Integration E2E                                          | [44980758361](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44980758361) | PASS                                                                                                          |
| Security, Dependency Review, CodeQL Python and JavaScript/TypeScript | [44980758292](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44980758292) | PASS                                                                                                          |
| Phase 9G regression                                                  | [44980758263](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44980758263) | PASS                                                                                                          |
| Phase 9H regression                                                  | [44980758362](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44980758362) | PASS                                                                                                          |
| Canonical Docker/full-stack Phase 0–10                               | [44980758294](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44980758294) | FAIL on 439e099: Phase 10 artifact lookup; corrected and isolated point rerun on 04c; canonical rerun pending |

The table above records SHA `439e099f7e7c1b832db8b7f3d39be004a15f30a7`. Its canonical Phase 0–10 run failed in Phase 10 because the registry artifact lookup found multiple files with the same relative path. The code now selects bytes only when they match the immutable registry checksum and size, and rejects absent or conflicting verified content. The isolated acceptance rerun passed on `04c6c49b82f51b3e1dc900c60db232f4065e1a9a` ([run 44987560592](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44987560592)); its focused Phase 10 unit suite passed 56 tests. On that SHA, Quality/Integration, Security, Phase 9G and Phase 9H also passed ([CI 44987560590](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44987560590), [Security 44987560635](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44987560635), [9G 44987560568](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44987560568), [9H 44987560494](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44987560494)). The canonical workflow triggered on 04c was canceled before completion; it is not a pass. This report update will create a new SHA and all required gates, including canonical full-stack, must run on that exact SHA.

The independent `acceptance.json` receipt passed its checker with checksum `b574e0cb79b45c7e6f03d3680d7a5a368389fc5985d9a58d6fb21d8ed6f16f38`.

## Implementation and acceptance evidence

The platform adds versioned pipeline definitions and durable run, stage, checkpoint, lease/fencing, and event records through additive Alembic revision 0020. Execution reuses Phase 9A feature and dataset lineage, Phase 9B supervised trainers and registry, Phase 9C detector fitters and registry, and Phase 9G evaluation protocols. Artifacts, labels/oracles, cutoffs, source role, cohort and report checksums are frozen into provenance. The independent checker reconstructs selected lineage and artifact state from the database and filesystem; it is separate from the evaluator's PASS receipt.

On SHA 439e099, and again in the isolated acceptance rerun on 04c6c49, the disposable-database evaluator exercised all three 9B tasks and all four 9C families, registered seven candidate artifacts, completed seven candidate runs, independently checked the receipt and dossiers, reproduced an experiment byte-for-byte, compared matched champion/challenger cohorts, rejected incompatible candidates, checked source and temporal leakage, monitored persisted 9D prediction receipts, exercised proposal and rollback review boundaries, and verified concurrency, crash recovery, idempotent replay and artifact/source tampering cases. Four snapshots covering 19 source tables were unchanged through compare/monitor/review. Phase 9D serving transitions remained separate and explicit.

The matching exact measurements and support are in [pipeline evaluation](phase-10-pipeline-evaluation.md); monitoring windows, abstention, drift and unknown-label results are in [monitoring comparison](phase-10-monitoring-comparison.md). [Security and reproducibility](phase-10-security-reproducibility.md) records current findings and dates. The 158-row requirement mapping is in [the traceability ledger](phase-10-traceability-ledger.md).

## Durability, packaged runtime, performance and observability

Migration 0020 passed disposable-database roundtrip and integration acceptance. Concurrent create/claim, fenced lease ownership, immutable event history, stage transitions, checkpoint resume, crash recovery and idempotent replay passed. Seven replay requests returned the existing results without duplicate runs. The independent evaluator verified source-table digests across four snapshots (19 source tables per snapshot); comparison, monitoring, review and rollback planning did not alter immutable 9D/9E/9F/9G data or the active binding.

The Phase 9H standalone Docker browser regression passed on this SHA: `NODE_ENV=production` with controlled `ENVIRONMENT=test` and explicit authorization allowed the private operator flow; `ENVIRONMENT=production` denied protected predictive features. Missing credentials, feature flags, trusted peer or vehicle scope denied access. The protected BFF read persisted Phase 9D/9E receipts; browser output contained no bearer token or private API host. Hashes across 43 source tables were unchanged.

The bounded Phase 10 benchmark recorded seven pipeline runs, 588.01 seconds wall time, 307.34 CPU seconds, 978,411,520-byte peak RSS (~933 MiB), 249.13 seconds aggregate pipeline execution and 19.07 seconds planning. Largest artifact was 32,105 bytes; total artifact bytes were 92,254 against a 50 MiB budget. This is a bounded synthetic disposable-database benchmark, not a production capacity claim. Observability evidence included run/stage counters, histogram bucket/count/sum series, `mlops.pipeline.run` and `mlops.monitor` spans, bounded labels and no sensitive identifier in exported metrics.

## Scientific and serving boundary

All accepted model/detector candidates have scientific readiness `SYNTHETIC_ONLY` and production use `PROHIBITED`. Synthetic calibration does not establish real-world predictive validity. Phase 9B supervised scores are not mechanical failure probabilities; Phase 9C anomaly scores are not engine-health percentages or diagnoses. Unlabeled real telemetry cannot establish accuracy, recall or calibration. Real-world mechanical failure predictive reliability remains **NOT_ESTABLISHED**.

MLOps comparisons, monitoring and proposals are read-only review artifacts. They do not train automatically, activate, deploy, replace, revoke or roll back serving bindings. Phase 9D controls remain authoritative; any serving transition requires a separate explicit authorized 9D action.

## Remaining acceptance work

1. Commit and push the final evidence/report update to the existing branch; confirm local HEAD equals `origin/codex/phase-10-mlops-platform` and PR #64 remains open.
2. Run and inspect Quality, Integration E2E, canonical Phase 0–10, Security, Dependency Review, both CodeQL jobs, Phase 9G, Phase 9H and Phase 10 independent acceptance on that exact final SHA. If any point fails, rerun that point first, fix its cause, then rerun the complete workflow.

Until all mandatory exact-final-SHA gates pass, this phase is **NOT VERIFIED**.
