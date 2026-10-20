# Phase 9D acceptance record

Status: Phase 9D is **VERIFIED** on the final exact PR head recorded in the [PR #44 description and checks](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/44). The required canonical full-validation, quality, integration, security, CodeQL and dependency-review checks passed on that same SHA. PR #44 targets `main`, remains open and unmerged, and has no auto-merge request. The PR description records the final head SHA and direct check URLs.

## Delivery and scope

- Branch: `codex/phase-9d-prediction-service`; base: `main` at the merged Phase 9C baseline `7fc4c59f63a7be64e4ece5ab77bf61b09fc98bc0`.
- PR: [#44](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/44), open and intentionally unmerged.
- Migration: additive revision `0016_prediction_service`, after `0015_anomaly_detection`.
- Scope: authenticated, bounded development/test HTTP serving for explicitly approved 9B `NEXT_PULL` models and 9C `AFTER_PULL_OFFLINE` detectors, with append-only approval events and immutable receipts.
- Not included: Phases 9E–9H, public tenancy, production serving, training-on-request, arbitrary feature input, diagnoses, maintenance decisions, or ECU control.

## Data model and approval lifecycle

Revision `0016` adds `prediction_serving_bindings`, `prediction_serving_events`, and `prediction_receipts`. A binding pins one exact model or detector version, source role, environment and controlled scope, plus artifact, FeatureSet and schema checksums. Events append approval, activation, revocation, supersession and rollback history. Receipts pin the binding/event snapshot, request fingerprint, result status, quality and safe lineage. Database constraints and mutation-rejection triggers protect the append-only records. Downgrade removes only these three Phase 9D tables.

The final disposable PostgreSQL evaluator started at `0015`, upgraded to `0016`, downgraded to `0015`, and upgraded again. Digests for all 17 legacy tables remained unchanged; before/after counts for the existing vehicle and model data also matched. The evaluator created 8 approvals and recorded 8 `APPROVED`, 8 `ACTIVATED`, 2 `REVOKED`, 2 `SUPERSEDED` and 1 `ROLLED_BACK` events. It exercised replacement and rollback, and confirmed revocation is resolved before receipt replay. A request already in flight retained its captured binding snapshot through a concurrent revocation.

## Operator enablement and access boundary

Serving defaults off. It rejects production enablement and accepts only the controlled `development` or `test` environments. The operator CLI checks environment and explicit confirmation before state changes; approval requires candidate inspection, trusted artifact verification, a reason, operator identity and review reference. Synthetic approvals must name their synthetic scope. No HTTP approval endpoint exists.

HTTP access requires a high-entropy bearer token and a configured trusted private/loopback peer CIDR. Authentication and network checks happen before request-body parsing; query, cookie and body credentials are rejected. The boundary checks passed for invalid/missing tokens, untrusted peers, oversized bodies, rate overflow, vehicle isolation, hidden wrong-vehicle pulls, mixed/invalid source roles, revoked approvals, changed artifacts, and production enablement. Request limits exercised include 4,096-byte bodies, a 2-second body wait, an 8-second handler timeout, eight in-flight requests and two CPU workers. The service does not trust forwarded client IP headers.

## Inference results and evidence boundaries

All scores below came from the controlled deterministic synthetic engineering fixture. The three supervised results matched the direct offline `offline_predict` score, threshold and decision; each test also confirmed concurrent identical replay returned one receipt:

| 9B task                             |               Score | Threshold | Decision | Direct offline equality |
| ----------------------------------- | ------------------: | --------: | -------- | ----------------------- |
| `NEXT_PULL_FUEL_DEVIATION`          | 0.43708480469450384 |       0.4 | true     | Pass                    |
| `NEXT_PULL_PERFORMANCE_DEGRADATION` |  0.8055818793149994 |      0.45 | true     | Pass                    |
| `NEXT_PULL_THERMAL_DEGRADATION`     | 0.15729718872208986 |       0.5 | false    | Pass                    |

Each of the four 9C families matched the canonical `AnomalyService.score_detector_version` finding, run, score/threshold and status. The robust-MAD validation threshold was 3.5 for each family:

| 9C family     |              Score | Status                          | Result                        |
| ------------- | -----------------: | ------------------------------- | ----------------------------- |
| `boost_air`   | 0.3372453797382976 | `INLIER`                        | Direct 9C equality            |
| `fuel`        | 1.3489815189531904 | `INLIER`                        | Direct 9C equality            |
| `performance` |                0.0 | `INLIER`                        | Direct 9C equality            |
| `thermal`     |        unavailable | `ABSTAINED_INSUFFICIENT_SIGNAL` | Direct 9C abstention equality |

Coverage was 5/5 scored for every eligible supervised task, 5/5 for `boost_air`, 4/4 for fuel anomaly and 5/5 for performance anomaly. Thermal anomaly had 5/5 authorized and admitted requests and abstained on all five for insufficient signal. Separate missing-fuel, missing-as-of-FeatureSet and low-quality cases abstained. No eligible request failed in the coverage set.

The evaluator bound requests to synthetic source-role provenance and the exact vehicle configuration and FeatureSet snapshot. It rejected mixed roles and cross-vehicle references; proved that a cutoff before pull completion is rejected; and checked both late FeatureSet/cutoff isolation and late-ingestion invariance. After late observations and metadata were added, source hash, provenance hash, FeatureSet ID and historical receipt ID stayed unchanged. Feature-schema adversaries, incompatible configuration, artifact/model/detector tampering and implicit feature generation were also denied. Approved bindings pin exact artifact and FeatureSet checksums; serving revalidates the trusted registered artifacts and does not train or generate features on request.

## API contract, idempotency and persistence

The authenticated routes are `GET /api/v1/prediction-service/versions`, `POST /next-pull`, `POST /anomalies`, and `GET /runs/{receipt_id}` under `/api/v1/prediction-service`. The typed versioned response separates `NEXT_PULL` from `AFTER_PULL_OFFLINE`, carries explicit status/abstention reason, fixed `score_is_probability=false`, quality and minimal lineage, and excludes raw telemetry and artifact paths. The evaluator confirmed receipt retrieval returned 200 and unauthorized receipt access did not reveal vehicle history.

Request fingerprints bind the request kind, subject, active binding and event, exact version/checksum, pull, source role, effective cutoff and FeatureSet provenance. Idempotency keys are stored only as hashes. Replays return the same immutable receipt; reusing a key with changed input conflicts. Concurrent identical requests shared one receipt. Injected receipt-write failure returned a sanitized error without a partial receipt; retry then succeeded. Database mutation attempts against immutable records and oversized payload cases were rejected.

## Resource, benchmark and observability results

The final exact-head evaluator measured 42 calls: p50 0.670610 s, p95 2.461566 s and p99 2.481882 s. These fixture measurements are observations, not an SLA. A 10-request burst produced eight 200 responses and two bounded 429 responses; peak admitted concurrency was eight with two CPU workers. Maximum pull batch size was one. Fifteen artifact files totaled 363,460 bytes; the largest was 133,058 bytes (configured artifact limit 52,428,800 bytes). RSS was 388,984 KiB before and 391,836 KiB after serving. Configured request timeout was eight seconds and body wait was two seconds.

Metrics and traces covered request admission/denial, binding resolution, FeatureSet lookup, artifact verification, model/anomaly scoring, 9C finding persistence and receipt persistence. Evaluator assertions confirmed entity IDs and operator tokens were excluded from metrics. Cardinality uses bounded kind/status/reason labels; logs omit VINs, telemetry, feature values, tokens, checksums and artifact paths.

## Validation evidence

The final exact-head GitHub check set is linked from the [PR checks view](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/44#checks); the PR description includes the final head SHA and direct job URLs. The canonical Docker/full-stack workflow reported all 28 steps successful, including cloud validation, container builds, database/migrations, canonical stack, E2E, 100k live stream, container security, observability, Phases 6–9C and the Phase 9D evaluator. The exact-head quality, integration E2E, security, Python and JavaScript/TypeScript CodeQL and dependency-review checks also passed. The attached commit-tied acceptance artifact reports `full_gate=PASS` and Phase 9D `execution_state=PASS` on its recorded SHA.

The acceptance artifact records 49 receipts and 8 approval bindings. The workflow re-runs `make test-prediction-service phase9d-acceptance`, including unit and disposable database/real-HTTP integration coverage. The broader canonical gate includes prior-phase regression targets; cloud-compatible checks, browser suites, production builds, observability and security scans were included in the full result. The local `make verify` wrapper had an environment-specific port/proxy/browser setup failure as one invocation; the ordered targets completed, and the canonical exact-head GitHub full gate is the authoritative full-stack result.

## Limits and reproducibility

The fixture is synthetic and controlled. It validates integration, persistence, access boundaries, deterministic equality and resource behavior; it does not establish real-vehicle accuracy, calibration, fault prediction, diagnosis or mechanical condition. No sanitized imported real-data compatibility smoke was available (`NOT RUN`), and no paid provider or external inference service was used. No public production deployment or ECU interaction occurred.

Reproduce the disposable-database acceptance with `make phase9d-acceptance`; Docker is required. Use the canonical GitHub `full-validation` workflow when Docker is unavailable. Full section-to-evidence mapping is in the [traceability ledger](phase-9d-traceability-ledger.md); operator procedure is in the [runbook](../runbooks/prediction-service.md).
