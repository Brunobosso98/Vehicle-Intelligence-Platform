# Phase 7B acceptance

This document records the Phase 7B gate design and executed checkpoint evidence. The final
delivery receipt must identify the exact pushed PR HEAD and attach local and GitHub results for
that same SHA. A previous green run does not certify a later commit.

## Scope and gates

The implementation adds one bounded investigation to a completed, grounded Phase 7A AgentRun.
It searches existing MCP evidence, maps semantic needs to the canonical signal registry, resolves
actual source capability, proposes a versioned Phase 4 recipe, requires operator approval, links
one compatible finalized acquisition session, and creates a separate grounded follow-up run.
The outcome remains an association or inconclusive; mechanical diagnosis and ECU write/control
are outside scope. Phase 7C specialists and Phase 8 RAG are deferred.

| Gate                                | Command                                 | Checkpoint                                                  |
| ----------------------------------- | --------------------------------------- | ----------------------------------------------------------- |
| API typing, lint, unit and coverage | `make check-api`                        | PASS: 455 tests; 95.59% line, 90.09% branch coverage        |
| Web lint, typing and unit           | `make check-web`                        | PASS: 41 tests, 85.53% branch coverage                      |
| Contracts and build                 | `make contracts-check`; `make build`    | Build passed at implementation checkpoint                   |
| Real database migration/integration | `make test-integration`                 | PASS: 8 tests, including clean upgrade/downgrade/re-upgrade |
| Independent golden suite            | `make phase7b-acceptance`               | 61 assertions passed on fresh real DB/MCP/API stack         |
| Real browser journey                | `make test-investigation-e2e`           | PASS: 2 Chromium cases on disposable DB/MCP/Kafka/consumer  |
| Deterministic benchmark             | `make benchmark-investigation`          | Passed on fresh disposable stack; measurements below        |
| Delivered observability             | `make investigation-observability`      | PASS: Tempo trace, 3 Prometheus metrics and redaction       |
| Canonical local regression          | `make verify`                           | Pending final committed SHA                                 |
| Remote CI/security/full validation  | GitHub required checks at final PR HEAD | Pending push/PR                                             |

The independent evaluator uses a fresh disposable TimescaleDB, the actual MCP server and HTTP
API. Its finalized capture fixture writes only to that disposable database and verifies the
session-link boundary. The browser gate runs an actual Phase 4 synthetic capture through Kafka
and the canonical stream consumer, finalizes it, links the resulting session, and opens the
grounded follow-up with evidence drilldown. Its second case confirms a technical-documentation
gap produces no telemetry recipe.
The evaluator reports every observed scenario and the safety metrics in its JSON output; no
unexpected result is removed from scoring.

The expanded golden checkpoint passed all **61** HTTP/MCP/database assertions. It covered
sufficient evidence without a new plan, thermal and fueling needs, unavailable timing, data
quality, before/after configuration, documentation-only gaps, malicious provider signal and
modification text, cross-vehicle isolation, stale/hash approval, source change invalidation,
explicit approval, session link and separate reanalysis, duplicate link, inconclusive outcome,
cancellation, ordered SSE replay/reconnect without duplicate events, streamed failed and
cancelled states, dependency outage and recovery. Scored counters were **0** invented signals,
unknown recipe signals, recipe provenance errors, cross-vehicle leaks, approval bypasses and
unsupported diagnoses, unsafe action calls, budget violations and causal overclaims. Decision,
hypothesis, gap, capability, recipe, link and inconclusive update metrics were all **1.0** on
their scored controlled cases. The follow-up unit suite separately checks supported, weakened and
unresolved hypothesis updates from new evidence; the real-stack fixture remained inconclusive
because its critical timing channel was unavailable.

## Benchmark checkpoint

The deterministic provider benchmark on a fresh disposable stack measured:

| Scenario                                                   | Observed result                                                               |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Existing evidence sufficient                               | 0.244 s; plan rejected with 422                                               |
| Three hypotheses, capability resolution and Phase 4 recipe | 3.239 s; 3 hypotheses, 2 gaps, 4 signal needs, 7,041 response bytes           |
| Linked session and separate grounded reanalysis            | 20.370 s; 7 MCP calls, 3.855 s cumulative MCP call time, 8,347 response bytes |
| Concurrent investigations                                  | 2 successful plans; 2.222 s and 2.997 s                                       |

The end-of-run MCP/API process RSS values were 116,816 and 166,444 KiB. The disposable database
aggregate counters changed by 842 commits, 470 rollbacks and 209,960 fetched tuples, including
fixture and background activity. In the plan POST, the deterministic provider took 0.022 s,
existing-evidence search made 3 MCP calls and recipe generation took 0.001 s. Exact per-request
SQL count, external LLM latency and peak memory allocation remain unmeasured.

## Final receipt requirements

The final PR receipt must show a clean tree at the validated commit, `make bootstrap`, complete
`make verify`, a fresh repeat of Phase 7B acceptance, Phase 4 acquisition integration, MCP-backed
agent and investigation browser journeys, delivered observability, benchmark and the required
CI, Security, CodeQL, dependency review and canonical Docker/full-stack checks. The origin branch,
local SHA and PR HEAD must match; the PR must remain open and unmerged. The
[traceability ledger](phase-7b-traceability-ledger.md) records requirement-level evidence and
status. Optional real-provider smoke remains NOT RUN when no operator-provided credentials exist.
