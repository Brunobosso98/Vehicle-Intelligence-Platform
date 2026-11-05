# Phase 9H independent acceptance

**Exact-head status:** See [PR #57 checks](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/57).
This page records the independent acceptance design and local evidence; GitHub checks and their
artifacts are the source of truth for the current branch SHA.

## Scope and oracle

`make phase9h-acceptance` runs `scripts/phase9h-validation.sh` against a new disposable Compose
database. It applies current migrations, invokes the actual 9D inference and 9E persistence paths
only to prepare controlled fixtures, and builds a direct, read-only PostgreSQL oracle from original
receipt columns and response bodies. It requires all three 9B supervised tasks and all four 9C
anomaly families. The browser then uses the real Next.js BFF and actual API routes to read original
9D receipts, 9E projections and existing 9F AgentRun context.

The 9E evaluator can place its accepted synthetic receipts on more than one vehicle. The oracle
retains each receipt's source vehicle and emits a sorted, unique allowlist of only those fixture
vehicle IDs (bounded by the BFF/API limit of 20). The browser selects each allowed scope, checks its
original values and evidence, and verifies that requesting a receipt through another allowed
vehicle scope returns a nondisclosing 404.

The first exact-head attempt at `5ffe99d` verified the 9G snapshot and produced 11 9E receipts, then
stopped in oracle preparation because the old checker incorrectly required a single vehicle. The
corrected checker now preserves per-receipt vehicle scope; its focused tests cover multiple scopes,
deduplication, empty input and the 20-ID bound.

The `0f5caf2` attempt then generated 11 receipts across all required tasks/families and passed the
fresh 9G summary check, but stopped before browser access because the source oracle compared
response decisions with the 9D text column. That column stores supervised booleans as `"True"` or
`"False"` and anomaly decisions as `"ANOMALOUS"` or `"INLIER"`. The first correction handled only
the boolean representation; the `de8d50c` run exposed the anomaly-literal form. The current checker
validates both encodings, reports differing field names, and uses the same `1e-12` float comparison
as the 9D history repository while preserving original numeric values for browser parity.

The `5e402da` source run generated and persisted 11 receipts, but the no-write oracle stopped before
browser access because it queried the 9G `evaluation_protocols` table after the 9E migration test had
intentionally left the disposable database at revision `0018`. The 9E evaluator round-trips its own
migrations through `0018`; the 9H harness now reapplies `head` and checks Alembic head status after
fixture generation and before digesting any tables. This makes the complete 9G table set available
to the no-write digest without changing production data or 9D/9E source records.

The oracle compares exact scores, frozen thresholds, decisions, model/detector versions, horizons,
source roles, quality, requested/effective cutoffs, receipt IDs, evidence IDs, completeness and
integrity. A canonical digest covers source, receipt, evidence, AgentRun and 9G evaluation tables
before browser access and after it. The independent checker also verifies oracle/acceptance
checksums, browser mode labels, axe results, console errors, viewport overflow, private API host
requests and bearer disclosure.

The UI keeps the committed 9G summary tied to its original source receipt. A fresh acceptance run
must still match task support, frozen thresholds, selected research maps, rounded point metrics,
reliability bins, anomaly counts and applicability aggregates exactly. The 9G harness creates fresh
synthetic cohort identities, so finite 200-resample cluster-bootstrap confidence interval endpoints
can move between runs. The checker allows at most 0.020 absolute movement per endpoint for Brier and
ECE intervals; it rejects malformed, unordered, out-of-range or more widely shifted bounds. This
tolerance applies only to the displayed research uncertainty bounds and does not change any model,
threshold, serving decision or evaluation report.

The browser journey exercises rejected and accepted login, session lifecycle, vehicle and guessed
receipt isolation, CSRF rejection, generic proxy bypass, source/evidence mismatch hiding, partial
evidence, abstention, research summary, desktop/mobile behavior, and demo separation. API/component
tests additionally cover unsupported source roles, query/path bounds and stale async responses.
Fixture creation occurs before the read-only UI interval; no serving, model, evidence, agent or
evaluation mutation is permitted during browsing.

## Evidence

| Gate                                                         | Local result                                                                                                                                                                    |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API unit, typing, lint, branch coverage                      | **PASS** — 1,432 tests; 95.89% line, 90.11% branch coverage                                                                                                                     |
| React/Vitest, strict TypeScript, ESLint                      | **PASS** — 116 tests; 91.00% statements, 85.57% branches                                                                                                                        |
| Generated OpenAPI contract check                             | **PASS**                                                                                                                                                                        |
| Documentation/context and repository formatting              | **PASS** — `make docs-check`, `pnpm format:check`                                                                                                                               |
| Synthetic Playwright, screenshots, axe and responsive checks | **PASS** — 1 Chromium E2E; axe 0, console errors 0, overflow 0 px                                                                                                               |
| 500-point chart benchmark                                    | **PASS** — p50 507.52 ms, p95 609.85 ms in local jsdom                                                                                                                          |
| Actual API + disposable DB + BFF + persisted-value parity    | **FAILED on `5e402da`** — 11 source receipts created; acceptance stopped before browser because the 9E migration round-trip left revision `0018`; fixed harness awaits next SHA |
| No-write database digest before/after browsing               | **NOT REACHED on `5e402da`** — missing `evaluation_protocols`; rerun after restoring Alembic head and require browser digest proof                                              |
| Locked dependency and secret scans                           | **PASS** — pip-audit clean, pnpm audit clean, gitleaks found no leaks                                                                                                           |
| Trivy filesystem scan                                        | **PASS** — no High/Critical findings on an ext4 copy of tracked and nonignored source; direct `/mnt/c` scan stopped after 5:42 without a report                                 |
| Container image scans and exception policy                   | **FAILED on `5e402da`** — 1 blocked High each in API/Web; exact zlib record added with 2026-11-12 expiry; final-image scan required                                             |
| Canonical full-stack/regression workflow                     | Docker is unavailable locally; exact-final-SHA GitHub Actions run remains mandatory                                                                                             |

The runner writes source and browser evidence under ignored `.validation/phase9h/`, including the
direct oracle, `acceptance.json`, independent-check log, per-mode Playwright metrics, screenshots,
traces and service logs. Generated screenshots are kept out of Git; their reproducible capture IDs
and commands are documented in [the UI evaluation](phase-9h-ui-evaluation.md). CI must upload this
directory from the same PR-head SHA used by the independent check. Local acceptance is not a pass
when Docker is unavailable. The local `make verify-cloud` run completed its code, test, build,
contract, documentation, and Phase 0–5 checks, then stopped at the slow mounted-path Trivy scan;
the ext4 source-copy scan above completed successfully.

## Required final checks

The latest [PR #57 checks](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/57)
must show the remote branch SHA, 9B/9C source parity, distinct evidence states, a no-write digest,
all access-control and secret-disclosure tests, synthetic demo isolation, every required quality,
security and canonical full-stack job, and an open unmerged PR targeting `main`.

## Scientific limitations

The acceptance fixtures are synthetic. Exact source parity demonstrates faithful display of stored
decisions only. It does not demonstrate predictive validity, calibration on real vehicles, fault
diagnosis, causality or mechanical safety. Phase 9G calibration remains research-only and real-world
predictive validity remains `NOT_ESTABLISHED`.
