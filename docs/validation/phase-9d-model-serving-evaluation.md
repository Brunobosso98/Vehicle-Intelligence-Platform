# Phase 9D model-serving evaluation

Status: the local disposable-database evaluator passed on the working tree based on
`e438bc1fc8c30acc940f0368fe42d8037a298b0e`. Exact final-PR-head CI evidence is pending.

## Evaluation design

The independent evaluator trains and registers the three existing Phase 9B task models with the
canonical pipeline, and creates accepted candidates for all four Phase 9C detector families using
the existing 9C evaluator. A second explicit Phase 9D approval and activation is then required for
each exact artifact version. The service handles a real HTTP request and loads the registered
artifact through the trusted loader.

For each supervised task it compares the response score, frozen threshold, and decision with
`offline_predict` over the exact persisted FeatureSet snapshot. For each anomaly family it compares
score, threshold, status and finding identity with `AnomalyService.score_detector_version`. Tests
cover missing-signal and low-quality abstention, source-role and vehicle isolation, configuration
compatibility, future/late telemetry and metadata, artifact tampering, revoked bindings, replay,
receipt failure recovery, concurrency and resource limits.

The benchmark captures a predeclared bounded burst, HTTP latency percentiles only when at least 30
observations exist, peak admitted requests, configured CPU-worker count, artifact sizes and process
RSS where available. Latency and RSS remain observations, not universal SLAs. The evaluator
captures real request metrics and spans and asserts that labels/attributes omit identifiers,
hashes, raw data, tokens and artifact paths.

## Results

The saved machine report is `.validation/phase9d/acceptance.json` (`execution_state=PASS`). All
three supervised tasks produced 5/5 eligible scores, each matching the canonical `offline_predict`
score, threshold and decision within the configured `1e-12` comparison tolerance. Four anomaly
families matched their 9C finding and threshold; thermal returned the expected insufficient-signal
abstention for all five coverage requests. Separate missing-fuel and low-quality cases abstained.
The complete evaluator produced 49 immutable receipts and passed late-ingestion invariance, artifact
tampering, idempotent replay, revocation, migration preservation, auth and observability checks.

The 42-call measurement set recorded p50 1.605 s, p95 4.818 s and p99 4.839 s. A 10-request burst
returned 8 successes and 2 bounded 429 responses; peak admitted concurrency was 8 with 2 numerical
workers. Artifact files totaled 363,452 bytes (maximum single file 133,054 bytes). Process RSS was
399,776 KiB before serving and 402,848 KiB after. These are local controlled-fixture observations,
not latency or resource SLAs.

There is no labeled real-vehicle outcome set. These synthetic results do not establish real-world
accuracy, calibration or mechanical condition. The real-data compatibility smoke is **NOT RUN**.
No paid provider or external inference service was used.

## Reproduce

```bash
make phase9d-acceptance
```

The target creates an isolated disposable TimescaleDB project, starts at migration `0015`, executes
the evaluator's downgrade/re-upgrade digest comparison, and stores the machine report and logs in
ignored `.validation/phase9d/`. Docker is required. Use the canonical GitHub Actions full-validation
job when a local Docker daemon is unavailable.
