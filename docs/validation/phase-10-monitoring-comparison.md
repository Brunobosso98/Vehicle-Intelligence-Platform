# Phase 10 monitoring and comparison

## Monitoring actual persisted prediction receipts

The acceptance queried persisted Phase 9D prediction records from the disposable test database; it did not infer predictions or create Phase 9E evidence. Baseline and comparison windows were disjoint, scoped to the controlled binding, vehicle/configuration, source role, model version and feature schema. The report conserves each receipt once and reports counts, missingness, quality exclusion, abstention and independent session support.

| Window     | Receipts | Scored | Abstained | Sessions | Details                                                                                 |
| ---------- | -------: | -----: | --------: | -------: | --------------------------------------------------------------------------------------- |
| Baseline   |       10 |      0 |        10 |        2 | `NO_OBSERVATIONS` for required signal; all source role synthetic                        |
| Comparison |       30 |     26 |         4 |        2 | 2 insufficient-signal abstentions, 2 low-quality abstentions; all source role synthetic |

The fixture's baseline has no scored observations. It is reported as `NO_OBSERVATIONS`, not as zero performance. The comparison feature distribution triggered `WARNING`; source-role drift and missingness had `NO_PREDECLARED_WARNING`. Score-distribution shift was `INSUFFICIENT_SUPPORT`. Performance and calibration were `UNKNOWN` because the persisted receipts had no verified outcomes. The monitor's source digest check passed.

This acceptance is synthetic and bounded. It demonstrates pipeline behavior and denominator accounting; it does not establish a real fleet baseline or a production drift threshold. Source/covariate shift is distinct from score shift, and both differ from true label-verified performance drift. Unlabeled telemetry cannot establish accuracy, recall or calibration.

## Champion/challenger comparison

The evaluator loaded the current compatible Phase 9D binding and registered 9B/9C candidate, froze the same eligible held-out rows and checked schema, task/family, source role, cutoff and cohort. All seven matched comparisons completed with zero metric deltas. A deliberately incompatible candidate was rejected as `NOT_COMPARABLE`; it was not ranked. Detector scores on different scales were not compared.

Monitoring and comparisons are read-only over prior Phase 9D/9E/9F/9G records. Four before/after digest snapshots spanning 19 source tables matched. The separate operator review and rollback-readiness proposal also left source records and active binding unchanged. Phase 9D remains the only serving-transition authority.

## Review and rollback boundaries

The human review proposal reached `APPROVED_FOR_CONTROLLED_REVIEW`, while invalid reviewer authorization was denied. The proposal records no serving action (`NONE`) and is not a serving permission. Rollback planning found the prior binding `READY_FOR_SEPARATE_9D_REVIEW`, with no rollback performed. A stale artifact is rejected. Any actual transition requires a separate explicit authorized action through Phase 9D approval/activation/revocation/rollback controls.

Real-world mechanical failure predictive reliability remains **NOT_ESTABLISHED**. Synthetic calibration is not real-world validation; Phase 9B scores are not mechanical failure probabilities; Phase 9C anomaly scores are not engine-health percentages or confirmed diagnoses.
