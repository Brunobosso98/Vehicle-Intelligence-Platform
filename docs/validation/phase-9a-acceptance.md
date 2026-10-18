# Phase 9A acceptance report

## Status

The focused Phase 9A database acceptance, feature integration, feature observability and 1,000-pull
synthetic benchmark pass locally. The canonical validation result and exact-head GitHub receipts
are tracked for PR #41, which remains open and unmerged.

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
fixture contained 2 vehicles, 3 configurations, 4 sessions and 6 pulls, including a good-quality
pull for the second vehicle and a separate low-quality pull. It also contained a non-boundary
pre-pull thermal observation, a late-ingested sample, two events including a late-created event,
unavailable fuel and a modification whose installation predates the pulls but whose record was
created after the earlier observation cutoffs. The dataset builder now validates each source
against the cutoff of the selected FeatureSet, so a later-recorded active modification cannot
rewrite an earlier dataset row.

| Acceptance metric                                | Result |
| ------------------------------------------------ | -----: |
| Feature definitions                              |     79 |
| FeatureSets generated                            |      6 |
| Deterministic comparisons / equalities           |  1 / 1 |
| Leakage checks passed / undetected deliberate leaks | 7 / 0 |
| Late-modification leaks                          |      0 |
| Invalid persisted features                       |      0 |
| Cross-vehicle / incompatible configuration leaks |  0 / 0 |
| Fabricated unavailable sensor values             |      0 |
| Eligible / excluded dataset rows                 |  5 / 1 |
| Dataset vehicle / configuration coverage         |  2 / 3 |
| Controlled-fixture checksum stability            |   100% |

The evaluator observed a 315 K pre-pull IAT, an IAT recovery delta of −11 K, a 2-second
3,500–4,500 RPM interval, a 4-second pull duration and 108,000 Pa peak boost. A late-ingested
pre-pull observation was excluded at the earlier cutoff. Unavailable fuel stayed null; the future
sample and late-created event stayed out of target quality/history; cross-vehicle and incompatible
configuration histories remained isolated. The low-quality row was excluded with reason
`minimum_quality_not_met` and represented in the profile as a `quality_failure`.

The eligible rows cover both vehicles and all three configurations. Selected IAT delta values are
2, 4, 6 and 8 K; peak boost values are 104,000–116,000 Pa; and rail-pressure means span
13,800,000–16,800,000 Pa across four observed rows. The fifth row has unavailable fuel, which stays
null with its explicit reason. The low-quality candidate is excluded as
`minimum_quality_not_met`. The generated baseline artifact at
`.validation/phase9a/baseline-profile.json` contains the full feature/source capability matrix,
selected feature distributions, source role and quality-failure record. The summary is in the
[baseline profile](phase-9a-baseline-profile.md).

## Integration, observability and benchmark

`make test-feature-integration` passed its disposable PostgreSQL integration test. It covers
immutable persistence, deterministic reuse and concurrency, a non-boundary pre-pull value, an
early observation cutoff that excludes late ingestion, configuration/history isolation, dataset
materialization and nonnegative database-read, compute and persistence timing observations.

`make feature-observability` passed. It verified the generation, configuration, telemetry-read,
compute, persistence and dataset spans; generation, null-value, leakage and dataset metrics; and
absence of entity identifiers from metric labels.

`FEATURE_BENCHMARK_PULLS=1000 make benchmark-features` generated 1,000 synthetic FeatureSets in
148.5127 seconds (6.73 pulls/second). The separately bounded dataset materialization measured 100
rows in 0.9159 seconds (109.18 rows/second), with zero exclusions. Stage totals were 86.1528
seconds for database reads, 33.9186 seconds for feature compute and 22.3899 seconds for
persistence. Peak Python allocation was 27,808,244 bytes; maximum process RSS was 141,742,080
bytes. The dataset benchmark is capped at 100 rows to remain within the builder's 32 MiB source
payload limit. These are synthetic local measurements, not production capacity or real-vehicle
performance claims.

## Canonical validation and delivery

`make verify` is the canonical local full-stack validation command. It covers API and web lint,
typing, tests and coverage; contracts and documentation; production builds; prior Phase 0–8
acceptance; Docker integration and browser E2E; security; and the Phase 9A acceptance, integration,
benchmark and observability gates. The final local result and exact-head GitHub receipts are linked
from PR #41. The PR remains unmerged.

Phase 9A does not train a model, predict vehicle health, issue diagnosis, or add a prediction API,
MCP tool or predictive UI. The ranked Phase 9B candidate shortlist remains in the architecture
report and [traceability ledger](phase-9a-traceability-ledger.md).
