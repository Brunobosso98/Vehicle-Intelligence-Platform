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

| Gate                                                         | Local result                                                                                                                                    |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| API unit, typing, lint, branch coverage                      | **PASS** — 1,416 tests; 95.89% line, 90.11% branch coverage                                                                                     |
| React/Vitest, strict TypeScript, ESLint                      | **PASS** — 116 tests; 91.00% statements, 85.57% branches                                                                                        |
| Generated OpenAPI contract check                             | **PASS**                                                                                                                                        |
| Documentation/context and repository formatting              | **PASS** — `make docs-check`, `pnpm format:check`                                                                                               |
| Synthetic Playwright, screenshots, axe and responsive checks | **PASS** — 1 Chromium E2E; axe 0, console errors 0, overflow 0 px                                                                               |
| 500-point chart benchmark                                    | **PASS** — p50 507.52 ms, p95 609.85 ms in local jsdom                                                                                          |
| Actual API + disposable DB + BFF + persisted-value parity    | Docker CLI exists, but the daemon is unavailable; **CI REQUIRED**                                                                               |
| No-write database digest before/after browsing               | Not executed without disposable PostgreSQL: **CI REQUIRED**                                                                                     |
| Locked dependency and secret scans                           | **PASS** — pip-audit clean, pnpm audit clean, gitleaks found no leaks                                                                           |
| Trivy filesystem scan                                        | **PASS** — no High/Critical findings on an ext4 copy of tracked and nonignored source; direct `/mnt/c` scan stopped after 5:42 without a report |
| Container image scans and exception policy                   | **PASS** on prior head `5ffe99d` in Security run `41906643193`: 93 accepted High, 0 Critical, 0 blocked; final-head result is on PR #57         |
| Canonical full-stack/regression workflow                     | **CI REQUIRED** for Docker-backed gates                                                                                                         |

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
