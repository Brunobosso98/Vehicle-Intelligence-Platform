# Phase 9D model-serving evaluation

Status: the independent disposable PostgreSQL and real-HTTP evaluator passed on the exact PR head recorded in the [PR #44 description and checks](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/44). The PR description lists the current SHA and direct exact-head CI URLs. The evaluator uses only controlled deterministic synthetic engineering fixtures; no real-vehicle accuracy claim is made.

## Evaluation design

The evaluator builds and registers the three existing Phase 9B task models through their canonical pipeline, and creates accepted candidates for all four Phase 9C detector families using the existing 9C evaluator. A separate Phase 9D approval and activation is required for each exact artifact. The service handles real HTTP requests and loads registered artifacts through the trusted loader.

For each supervised task, the evaluator compares the served score, frozen threshold and decision against `offline_predict` for the exact persisted FeatureSet. For each anomaly family, it compares score, threshold, status, finding and run identity with `AnomalyService.score_detector_version`. It exercises missing-signal and low-quality abstention, source-role/configuration/vehicle isolation, pre-pull and future cutoffs, late telemetry and metadata, schema adversaries, artifact tampering, revoked bindings, idempotency, immutable receipts, failed-write recovery, concurrent replay, request limits and observability.

The evaluator executes a real route-level auth matrix, including missing/invalid credentials, unsupported credential channels, untrusted network peers and unauthenticated malformed-body ordering. It captures bounded request latency percentiles only when at least 30 calls exist, a burst near the in-flight cap, CPU worker count, artifact sizes and process RSS where available. It asserts that metrics and trace attributes omit identifiers, hashes, raw data, tokens and artifact paths.

## Results

The final machine report is `validation-artifacts/phase9d/acceptance.json` from the canonical workflow (`execution_state=PASS`, schema `phase9d-acceptance-v1`). It records 49 receipts and 8 approval bindings. Migration `0015 → 0016 → 0015 → 0016` preserved digests for all 17 pre-existing tables, and all observed pre/post legacy database table counts matched.

All three supervised tasks matched direct offline inference; concurrent identical replay returned the same receipt:

| Task | Score | Threshold | Decision | Direct equality |
| --- | ---: | ---: | --- | --- |
| `NEXT_PULL_FUEL_DEVIATION` | 0.43708480469450384 | 0.4 | true | Pass |
| `NEXT_PULL_PERFORMANCE_DEGRADATION` | 0.8055818793149994 | 0.45 | true | Pass |
| `NEXT_PULL_THERMAL_DEGRADATION` | 0.15729718872208986 | 0.5 | false | Pass |

All four anomaly families matched direct 9C output. Threshold was 3.5 for each robust-MAD detector; `boost_air`, `fuel` and `performance` returned `INLIER` scores 0.3372453797382976, 1.3489815189531904 and 0.0 respectively. `thermal` returned no score and `ABSTAINED_INSUFFICIENT_SIGNAL`, matching the canonical 9C result. Coverage was 5/5 for each supervised task, 5/5 for boost-air anomaly, 4/4 for fuel anomaly, 5/5 for performance anomaly and 0/5 scored for thermal anomaly (all five abstained for insufficient signal). Separate missing-fuel, missing-as-of-FeatureSet and low-quality examples abstained.

Source and temporal adversaries passed: `MIXED` roles and incompatible contexts were rejected; cross-vehicle references and wrong-vehicle pull access were isolated; cutoffs before pull completion were rejected; late FeatureSet data, post-cutoff metadata and late-ingested observations did not change the selected historical FeatureSet hashes or receipt. Schema adversaries and model/detector artifact tampering were rejected. The service did not generate missing features. Revocation took precedence over replay, while an in-flight request retained its pre-revocation binding snapshot. A failed receipt persistence left no partial receipt and a retry succeeded.

The 42-call benchmark recorded p50 0.564905 s, p95 2.058472 s and p99 2.146723 s; these are controlled-fixture observations, not service-level objectives. A 10-request burst produced eight 200 responses and two 429 responses. Peak in-flight requests were eight, with two CPU workers. Fifteen artifacts totaled 363,460 bytes and the largest was 133,058 bytes. RSS changed from 388,984 KiB to 391,836 KiB in the measured run. Configured bounds were 4,096-byte request bodies, two-second body wait, eight-second request timeout, eight in-flight requests and two CPU workers.

The observability assertions confirmed entity IDs and operator tokens were absent from metrics. Traces covered admission/denial, binding resolution, feature lookup, artifact verification, supervised/anomaly scoring, canonical 9C persistence and receipt persistence. Logs and telemetry do not expose tokens, raw telemetry, VINs, feature values, hashes or artifact paths.

## Interpretation and limits

These tests measure integration correctness, deterministic equivalence, persistence, safety boundaries and bounded resource behavior. There is no labeled real-vehicle outcome set; results do not establish real-world accuracy, calibration, fault prediction or mechanical condition. The real-data compatibility smoke is **NOT RUN**. No paid provider or external inference service was used. The service remains disabled by default, limited to development/test and unavailable for production enablement.

## Reproduce

```bash
make phase9d-acceptance
```

The target creates an isolated disposable TimescaleDB project, starts at migration `0015`, executes the evaluator's downgrade/re-upgrade digest comparison and writes the machine report and logs under ignored `.validation/phase9d/`. Docker is required locally. Use the canonical GitHub `full-validation` workflow when a local Docker daemon is unavailable. Exact-head CI status is linked from the [PR checks view](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/44#checks).
