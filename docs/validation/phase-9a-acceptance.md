# Phase 9A acceptance report

## Status

**Local implementation gates: PASS. Exact-head checks: tracked on the current head of PR #41.**
These measurements were collected from the Phase 9A implementation on branch
`codex/phase-9a-feature-engineering-foundation`, based on baseline
`d1e35baba8f11c89f413e54c228a86724605a8f1`. The current source SHA, clean-tree state, PR state,
and exact-head GitHub workflow receipts are available from the linked
[Phase 9A pull request](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/41).

## Feature registry and temporal contract

The trusted registry contains 76 deterministic definitions: thermal 22, boost/air 14, quality 14,
fuel 9, raw context 7, history 5, performance 3 and temporal context 2. Availability is classified
as during-window 48, historical-only 7, post-window 9 and pre-event 12. Definitions carry typed
units, source signals, quality thresholds, algorithm identity, bounds, scope and active state.
Version identity hashes the definitions and generator, schema, selection, quality and temporal
policies. A changed manifest requires a new feature-set version.

Numeric storage uses canonical units: K, Pa, m/s, m/s², seconds, RPM and percentage points. Missing
signals remain null with a reason; invalid observations do not enter physical aggregates. The
generator applies observation cutoffs to telemetry ingestion, source entity creation, configuration
and modification history, events and prior pulls. Historical aggregation is isolated by vehicle,
effective configuration and compatible modifications. Dataset rows include stable identity,
cutoff, selected snapshot, source hashes, missingness and lineage. Splits include chronological and
walk-forward helpers. Export is bounded JSONL plus manifest under the fixed artifact root.

## Independent acceptance

`make phase9a-acceptance` passed against a freshly migrated disposable TimescaleDB. The synthetic
fixture contained 2 vehicles, 3 configurations, 4 sessions, 5 pulls, 2 chronological event cases,
a future-ingested observation, unavailable fuel, a low-quality row and thermal/boost variation.
The evaluator exercised deterministic recompute and concurrent reuse, version separation,
historical configuration, measured thermal/performance/boost values, fuel absence, quality counts,
past-only event/history, future pull/event/sample exclusion, vehicle/configuration isolation,
persisted type/unit/bounds and stable dataset materialization.

| Acceptance metric                                |                       Result |
| ------------------------------------------------ | ---------------------------: |
| Feature definitions                              |                           76 |
| FeatureSets generated                            |                            5 |
| Deterministic comparisons/equalities             |                 1 / 1 (100%) |
| Deliberate leakage violations detected           |                            2 |
| Invalid persisted features                       |                            0 |
| Cross-vehicle leaks                              |                            0 |
| Incompatible cross-configuration leaks           |                            0 |
| Fabricated unavailable sensor values             |                            0 |
| Dataset rows / excluded rows                     |                        4 / 1 |
| Exclusion reason                                 | `minimum_quality_not_met: 1` |
| Dataset checksum stability on controlled fixture |                   1.0 (100%) |

The fixture confirmed IAT delta 4 K, pull duration 4 s and peak boost 108,000 Pa. Unrecorded fuel
pressure remained unavailable; a future-ingested sample was excluded from quality counts; a
late-created event was excluded from prior history; the target pull was rejected when beyond its
observation cutoff. A feature-version change persisted as a distinct FeatureSet. The poor-quality
dataset candidate was excluded with an explicit reason. Run-specific UUIDs make the checksum value
vary across fresh fixture runs; the evaluator compares repeated builds within each controlled run.

The baseline profile for the four-row dataset is summarized in
[the Phase 9A baseline profile](phase-9a-baseline-profile.md). The full local profile and the
feature availability matrix are emitted under `.validation/phase9a/` by the acceptance command.

## Database integration, benchmark and observability

`make test-feature-integration` passed on fresh disposable TimescaleDB: 1 integration test passed.
The suite covers migration 0013, persistence, deterministic identity/reuse, version separation,
cutoff behavior, concurrent generation, history/configuration isolation and dataset checksum.
Generation-run timestamps now record the start of the request; the integration suite asserts that
successful run start times do not fall after their persisted FeatureSet generation times.

`make benchmark-features` measured 100 synthetic pulls and 100 FeatureSets. Generation took
6.4001 s (15.62 pulls/s); dataset materialization produced 100 rows in 0.5884 s (169.95 rows/s).
Peak Python allocation was 21,211,860 bytes; process RSS peaked at 121,163,776 bytes. There were
zero dataset exclusions and zero paid calls. These are synthetic local measurements, not production
capacity or real-vehicle performance claims.

`make feature-observability` passed. It verified generation runs and sets, failures, duration, null
values, leakage rejections, dataset builds/rows/exclusions and build duration. It observed spans for
generation, configuration resolution, telemetry read, feature calculation and dataset build.
Vehicle/entity identifiers were absent from metric labels and the verified span attributes.

## Regression and delivery validation

The full local `make verify` run passed its final `observability-full` target with Docker available
after the generation-run timestamp correction. It included Ruff, formatting, typing, API and web tests, coverage thresholds, contract and
documentation checks, production build, Phase 0–8 deterministic acceptance, disposable database
integration, stack and browser E2Es, stream recovery and live-stream benchmark, cloud and full image
security scans, and the Phase 9A gates. API tests passed 1,062/1,062 with 95.19% line and 90.42%
branch coverage; web tests passed 52/52 with 94.74% line coverage. The general 13-test integration
suite passed, as did the Phase 9A integration case. The generic browser target passed 8 tests and
skipped 5 fixture-specific tests; their dedicated agent, investigation, supervisor and knowledge
browser targets passed separately.

The final Phase 9A acceptance rerun passed: 76 definitions, 5 generated FeatureSets, deterministic
equality 1/1, two deliberate leakage attempts detected, zero invalid persisted values, zero
cross-vehicle or incompatible cross-configuration leakage, zero fabricated unavailable values, and
100% controlled-fixture checksum stability. The benchmark measured 100 synthetic pulls at 14.29
pulls/s, 100 dataset rows at 180.20 rows/s, 7.00 s feature generation, 0.55 s dataset materialization,
121,184,256 bytes maximum process RSS, and 21,211,305 bytes peak Python allocation. These remain
synthetic local measurements, not production capacity claims.

Full image security passed with zero critical findings and no blocked findings; API/Grafana high
findings were within the accepted baseline. Full observability verified the required spans and SQL
and token redaction. The deterministic Phase 7D harness acceptance ran without invoking the paid
Luna suite; its grader outcomes and the prior real-model validation caveat remain documented in the
Phase 7D report. Phase 8 browser and observability regressions reported zero paid calls and used the
synthetic embedding transport. No paid Phase 7D or Phase 8 job was run.

The browser regression uncovered a broad `role=status` locator in the existing agent E2E. The test
now selects the exact “Resposta validada.” status; the focused browser gate and the full canonical
verify both passed after this correction. Local validation is complete. Remote-head equality and
the PR's current-head GitHub check results are verified as part of delivery.

No Phase 9B–9H predictive models, anomaly detection, prediction API, PredictionEvidence, agent
integration or predictive UI is included. A ranked 9B shortlist and the detailed traceability mapping
are in the architecture report and [traceability ledger](phase-9a-traceability-ledger.md).
