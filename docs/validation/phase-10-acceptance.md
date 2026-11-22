# Phase 10 acceptance status

Status: **NOT VERIFIED on the current report candidate until its exact-SHA suite passes.** The implementation and all mandatory gates passed on SHA `c5114e07972456a9922f7d06f8c1925129adc351`. On report SHA `e5a4093ffdf7bb6491a2408253b3966484119246`, Quality, Integration E2E, Security/Dependency Review/CodeQL, Phase 9G, Phase 9H and independent Phase 10 acceptance passed. Its 90-minute canonical run completed all preceding stages but hit the job timeout during the Phase 10 step. The workflow timeout is raised to 180 minutes for this final rerun. PR [#64](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/64) remains open against `main` and is not merged.

## Exact-SHA receipts

| Gate                                                                 | Run                                                                                                   | Result                                                                                    |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Canonical Docker/full-stack Phase 0–10                               | [44988810960](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44988810960) | PASS, 55m56s                                                                              |
| Phase 10 independent acceptance                                      | [44988810979](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44988810979) | PASS; receipt checksum `4318df4eb6b54cd205aa4a65fc55968f10dd321b29822efa33e5a2eddc6f46a1` |
| Quality and Integration E2E                                          | [44988810959](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44988810959) | Both PASS                                                                                 |
| Security, Dependency Review, CodeQL Python and JavaScript/TypeScript | [44988811008](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44988811008) | All PASS                                                                                  |
| Phase 9G regression                                                  | [44988810964](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44988810964) | PASS                                                                                      |
| Phase 9H standalone/BFF regression                                   | [44988811046](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44988811046) | PASS                                                                                      |

The canonical run exercises the Docker stack, disposable database and migrations, browser E2E, observability, security scans, and deterministic regressions from Phase 0 through Phase 10. The exact run and independent receipt artifacts are attached to the linked workflows.

The timed-out canonical run on `e5a4093` is [44993465000](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44993465000). All phases through 9H succeeded; the Phase 10 step was canceled when the workflow's 90-minute job timeout elapsed. The same SHA's independent Phase 10 disposable acceptance passed in [44993464930](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44993464930). The timeout change does not skip or relax any validation step.

## Implementation and independent acceptance

The platform adds versioned pipeline definitions and durable run, stage, checkpoint, lease/fencing and event records through additive Alembic revision 0020. Execution reuses Phase 9A feature/dataset lineage, Phase 9B model training and registry, Phase 9C detector fitters and registry, and Phase 9G evaluation protocols. The independent checker verifies persisted state, lineage, immutable artifact bytes and source-table digests independently from the evaluator's receipt.

On the accepted disposable database, all three supervised tasks and four anomaly families ran end to end, registered seven artifacts and completed seven runs. Evaluation reproduced a candidate byte-for-byte; champion/challenger cohorts were matched; incompatible candidates, source spoofing and temporal/source leakage were rejected. Concurrent execution, checkpoints, crash recovery, idempotent replay, unsafe serialization, tampering and stale artifacts were exercised. Seven replay requests returned existing runs; seven artifact-tamper attempts were rejected.

Monitoring read persisted Phase 9D receipts. Across four snapshots, all 19 protected Phase 9D/9E/9F/9G tables remained identical during comparison, monitoring and human review. A separate explicit Phase 9D action was exercised in the rollback scenario; MLOps itself recorded no serving action. See the detailed [pipeline evaluation](phase-10-pipeline-evaluation.md) and [monitoring comparison](phase-10-monitoring-comparison.md).

The packaged Phase 9H regression ran the actual standalone Next.js runtime with `NODE_ENV=production`. Authorized controlled `ENVIRONMENT=test` operator access worked; `ENVIRONMENT=production` denied protected predictive features. Missing credentials, flags, trusted peer or vehicle scope denied access. The protected browser BFF read persisted 9D/9E receipts, and hashes across 43 source tables remained unchanged.

## Performance, security and scientific limits

The bounded synthetic acceptance ran seven pipelines in 436.24 seconds wall time, used 235.11 CPU seconds and peaked at 986,628,096 bytes RSS (~941 MiB). Aggregate pipeline execution was 187.52 seconds; planning was 14.16 seconds. Eight measured artifacts totaled 92,256 bytes, with a maximum of 32,105 bytes against a 50 MiB budget. These are disposable-fixture measurements, not production capacity claims. Bounded metrics, histograms and spans were observed without entity identifiers in metric labels.

All candidates retain Phase 9G `SYNTHETIC_ONLY` readiness and `PROHIBITED` production applicability. Synthetic calibration does not establish real-world predictive validity. Phase 9B scores are not mechanical failure probabilities; Phase 9C anomaly scores are not engine-health percentages or diagnoses. Unlabeled real telemetry cannot establish accuracy, recall or calibration. Real-world mechanical failure predictive reliability remains **NOT_ESTABLISHED**.

MLOps proposals are human-review artifacts, not serving permissions. Activation, deployment, replacement, retraining and rollback are not automated. Phase 9D remains the only authority for a separate, explicit, authorized serving transition. Current container findings and dated exceptions are recorded in [container security findings](../security/container-findings.md).

The 158-row requirement mapping is in the [traceability ledger](phase-10-traceability-ledger.md). Full metrics and SHA-256 lineage are in the linked evaluation reports.
