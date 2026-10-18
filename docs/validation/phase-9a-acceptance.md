# Phase 9A acceptance report

## Status

Phase 9A database acceptance, feature integration, feature observability and the 1,000-pull
synthetic benchmark pass on the revised implementation. The canonical `make verify` completed
successfully on 2026-10-18 with Docker available. Exact-head GitHub receipts will be recorded after
the final commit is pushed. PR #41 remains open and unmerged.

The Phase 7D harness in the canonical run passed with the deterministic provider and reported
`real_model_validated: false`. The existing operator-accepted caveat remains: all 120 scheduled
slots have PASS observations across multiple rounds, but all 120 were not re-executed together on
the final code because API balance was insufficient. This does not represent a real-model Phase 9A
validation claim.

The work is on `codex/phase-9a-feature-engineering-foundation`, based on
`d1e35baba8f11c89f413e54c228a86724605a8f1`. The governing specification is
[Phase 9A Feature Engineering Foundation](../prompts/phase-9a-feature-engineering-foundation.md).

## Registry and temporal contract

The trusted registry contains 79 deterministic definitions: thermal 22, boost/air 14, quality 14,
fuel 9, raw context 7, history 5, performance 6 and temporal context 2. Availability is classified
as during-window 48, historical-only 7, post-window 12 and pre-event 12. Each versioned definition
records source dependencies and an acquisition class: 15 CORE, 28 OPTIONAL and 36
SOURCE_SPECIFIC. The machine-readable feature-by-source matrix covers the synthetic generator,
mapped CSV replay, generic OBD-II with a preflight requirement, and a richer future source that must
provide a capability report. These are signal-set compatibility results, not runtime availability
claims.

The current feature version is `phase9a-pull-v2`, with generator
`phase9a-feature-generator-v2` and source snapshot schema `canonical-telemetry-v2`. The persisted
`phase9a-pull-v1` manifest and snapshots remain immutable. Formula, dependency, acquisition-class
and temporal-policy changes are represented by the new version checksum.

Three post-window performance features report seconds per 1,000 RPM for the 2,500–3,500,
3,500–4,500 and 4,500–5,500 RPM bands. They use bounded linear crossings and require a continuous
monotonic interval. Missing boundaries, excessive gaps or a reversal before the upper boundary
produce an explicit insufficient-coverage value.

Pre-pull thermal features use the latest vehicle IAT, oil and coolant observations strictly before
the pull start within a five-minute lookback. Both sample timestamps and the owning session must be
known by the observation cutoff. Pre-pull rows are included in source hashes and kept outside
current-pull quality aggregates. A latest invalid sample remains invalid; an older good value is
not substituted. No matching observation produces an unavailable feature.

All persisted physical measurements use recorded canonical units. Missing signals remain null with
a reason, invalid samples do not enter physical aggregates, and historical context remains scoped to
vehicle, effective configuration and compatible modifications. Feature values include declared
dependencies plus the actual sample signals used for provenance.

## Disposable database acceptance

`make phase9a-acceptance` passed against a freshly migrated disposable TimescaleDB. Its controlled
fixture contained 2 vehicles, 3 configurations, 4 sessions, 5 pulls, a non-boundary pre-pull
thermal observation, a late-ingested sample, two events including a late-created event, unavailable
fuel, and a low-quality pull.

| Acceptance metric                                | Result |
| ------------------------------------------------ | -----: |
| Feature definitions                              |     79 |
| FeatureSets generated                            |      5 |
| Deterministic comparisons / equalities           |  1 / 1 |
| Deliberate leakage rejections                    |      2 |
| Invalid persisted features                       |      0 |
| Cross-vehicle / incompatible configuration leaks |  0 / 0 |
| Fabricated unavailable sensor values             |      0 |
| Eligible / excluded dataset rows                 |  4 / 1 |
| Controlled-fixture checksum stability            |   100% |

The evaluator observed a 315 K pre-pull IAT, an IAT recovery delta of −11 K, a 2-second
3,500–4,500 RPM interval, a 4-second pull duration and 108,000 Pa peak boost. A late-ingested
pre-pull observation was excluded at the earlier cutoff. Unavailable fuel stayed null; the future
sample and late-created event stayed out of target quality/history; cross-vehicle and incompatible
configuration histories remained isolated. The low-quality row was excluded with reason
`minimum_quality_not_met` and represented in the profile as a `quality_failure`.

The generated baseline artifact at `.validation/phase9a/baseline-profile.json` contains the full
feature/source capability matrix, selected feature distributions, source role, and quality-failure
record. The summary is in the [baseline profile](phase-9a-baseline-profile.md).

## Integration, observability and benchmark

`make test-feature-integration` passed its disposable PostgreSQL integration test. It covers
immutable persistence, deterministic reuse and concurrency, a non-boundary pre-pull value, an
early observation cutoff that excludes late ingestion, configuration/history isolation, dataset
materialization and nonnegative database-read, compute and persistence timing observations.

`make feature-observability` passed. It verified the generation, configuration, telemetry-read,
compute, persistence and dataset spans; bounded metrics; and absence of entity identifiers from
metric labels.

`FEATURE_BENCHMARK_PULLS=1000 make benchmark-features` generated 1,000 synthetic FeatureSets in
152.2842 seconds (6.57 pulls/second). The separately bounded dataset materialization measured 100
rows in 0.6473 seconds (154.48 rows/second), with zero exclusions. Stage totals were 88.5317
seconds for database reads, 34.9031 seconds for feature compute and 22.6605 seconds for
persistence. Peak Python allocation was 24,666,559 bytes; maximum process RSS was 135,868,416
bytes. The dataset benchmark is capped at 100 rows to remain within the builder's 32 MiB source
payload limit. These are synthetic local measurements, not production capacity or real-vehicle
performance claims.

## Canonical validation and delivery

The revised implementation's canonical `make verify` passed locally on 2026-10-18. It checked API
and web lint, typing, tests and coverage; contracts and documentation; production builds; prior
Phase 0–8 acceptance; Docker integration and browser E2E; security; and all Phase 9A acceptance,
integration, benchmark and observability targets. Results included 1,067 passing API unit tests
with 95.15% line and 90.36% branch coverage, 52 passing web unit tests, 13 passing full-stack
integration tests, and a passing Phase 9A disposable-database integration test. The aggregate
Playwright target passed 8 tests and skipped 5 fixture-specific tests; the dedicated agent,
investigation, knowledge and supervisor browser targets passed separately.

After this verified tree is committed and pushed, PR #41's body will record the final head SHA and
the exact-SHA GitHub workflow receipts. The PR will remain unmerged.

Phase 9A does not train a model, predict vehicle health, issue diagnosis, or add a prediction API,
MCP tool or predictive UI. The ranked Phase 9B candidate shortlist remains in the architecture
report and [traceability ledger](phase-9a-traceability-ledger.md).
