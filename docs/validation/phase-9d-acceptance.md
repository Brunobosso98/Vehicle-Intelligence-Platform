# Phase 9D acceptance record

Status: local Phase 9D and full ordered acceptance targets passed on the working tree based on
`e438bc1fc8c30acc940f0368fe42d8037a298b0e`. The final commit, exact-head CI, required PR checks
and open-PR state remain pending; Phase 9D is **not yet verified**.

## Scope and baseline

- Required branch: `codex/phase-9d-prediction-service`.
- Required merged Phase 9C baseline: `7fc4c59f63a7be64e4ece5ab77bf61b09fc98bc0`.
- Migration: `0016_prediction_service`, additive to revision `0015`.
- Scope: controlled authenticated serving for approved 9B `NEXT_PULL` results and 9C
  `AFTER_PULL_OFFLINE` anomaly results, with immutable serving receipts.
- Explicitly excluded: 9E–9H, Phase 10/12 infrastructure, public tenancy, production serving,
  diagnosis, maintenance actions, and ECU interaction.

## Evidence policy

No result below is a PASS until its command or exact-head CI job has completed. The independent
`scripts/evaluate_prediction_service.py` uses real persisted 9A FeatureSets, registered 9B models,
accepted 9C detectors and the actual FastAPI routes. It compares serving output with the canonical
offline inference helpers, performs a 0015 → 0016 → 0015 → 0016 compatibility round trip, and
checks auth, approvals, temporal boundaries, artifact tampering, idempotency, immutable receipts,
resource bounds and observability.

| Gate                                     | Required evidence                | State                                                             |
| ---------------------------------------- | -------------------------------- | ----------------------------------------------------------------- |
| Focused unit suite                       | `make test-prediction-service`   | PASS locally; 35 tests                                            |
| API quality/type/coverage                | `make check-api`                 | PASS locally; 1,192 tests, 95.24% line, 90.16% branch coverage    |
| Generated contract consistency           | `make contracts-check`           | PASS locally                                                      |
| Disposable database evaluator            | `make phase9d-acceptance`        | PASS locally; exact-head CI pending                               |
| Cloud-compatible prior-phase regressions | `make verify-cloud`              | PASS locally                                                      |
| Ordered Docker/full-stack/security suite | `make verify` targets            | PASS locally as ordered targets; wrapper caveat below; CI pending |
| CodeQL/dependency review                 | Required PR checks               | CI REQUIRED; exact-head run pending                               |
| PR state                                 | PR open, target `main`, unmerged | Pending                                                           |

Local evaluator receipt: `.validation/phase9d/acceptance.json` (`execution_state=PASS`, 49 receipts,
8 approved bindings). The run preserved digests for all 17 legacy tables through
0015 → 0016 → 0015 → 0016. All three supervised tasks matched `offline_predict`; all four anomaly
families matched the canonical 9C result, including thermal insufficient-signal abstention.
Approval events: 8 approved, 8 activated, 2 revoked, 2 superseded and 1 rollback. The test burst
admitted 8 requests and returned 429 for 2 over-limit requests. Across 42 measured calls, p50 was
1.605 s, p95 4.818 s and p99 4.839 s; these are fixture observations, not SLAs. Peak admitted
concurrency was 8 with 2 CPU workers. Process RSS was 399,776 KiB before and 402,848 KiB after
serving. The run changed no legacy database row counts.

## Synthetic fixture and real-data limits

The acceptance fixture is controlled synthetic data generated through the existing 9A pipeline;
9B models and 9C detectors are trained/evaluated using their existing canonical workflows. It
measures integration correctness, numeric equivalence, cutoff and isolation rules, not real-vehicle
accuracy or failure prediction. A sanitized imported dataset is not available in the disposable
acceptance environment, so a real-data compatibility smoke is `NOT RUN`; this is not a scored-model
claim. No paid provider or external inference service is used.

The evaluator uses only controlled synthetic input. Its performance measurements and successful
scores do not establish real-vehicle accuracy, calibration or mechanical-condition claims. No
sanitized imported dataset was available, so the real-data compatibility smoke is **NOT RUN**.
No paid provider or external inference service was used.

## Local verification record

The complete ordered acceptance sequence passed on the working tree: API/web quality, contracts,
documentation, formatting and production build; `make verify-cloud`; disposable PostgreSQL
integration (13 passed); Docker image builds and isolated stack health; Phase 6 through Phase 9D
acceptance, browser, benchmark and observability targets; both stack smoke runs; Phase 4 broker,
consumer, database and spool recovery; security scans; and full observability recovery. The Phase
9D report above records 49 receipts and 8 approved bindings. The live-stream benchmark persisted
all 100,000 generated observations with zero losses or duplicates. The broad web E2E command
reported 8 passed and 5 skipped; those five agent, investigation, knowledge and supervisor browser
scenarios were run separately and passed in their dedicated acceptance targets.

The top-level `make verify` command did not exit successfully as a single local invocation because
this WSL environment first lacked `.env`, then required a clean Docker CLI config for the public
BuildKit frontend, and the pre-existing development stack occupied port 8000. After creating an
ignored local `.env`, using an anonymous Docker config, and isolating the Compose project, the
ordered targets were completed. Phase 4 recovery was rerun with loopback added to `NO_PROXY` after
the inherited proxy returned 403 for a local request. The final exact-head GitHub workflow remains
required and is the authoritative full-validation result.

Update this report with the final commit SHA, PR URL/state, command receipts, exact-head workflow
URLs and every blocked gate after those checks finish.
