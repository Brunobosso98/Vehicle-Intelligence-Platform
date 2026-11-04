# Phase 9H independent acceptance

**Status: NOT VERIFIED.** Implementation and the independent acceptance harness are present. This
record must be tied to the final branch SHA and completed by exact-head GitHub Actions before Phase
9H can be declared verified.

## Scope and oracle

`make phase9h-acceptance` runs `scripts/phase9h-validation.sh` against a new disposable Compose
database. It applies current migrations, invokes the actual 9D inference and 9E persistence paths
only to prepare controlled fixtures, and builds a direct, read-only PostgreSQL oracle from original
receipt columns and response bodies. It requires all three 9B supervised tasks and all four 9C
anomaly families. The browser then uses the real Next.js BFF and actual API routes to read original
9D receipts, 9E projections and existing 9F AgentRun context.

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

| Gate                                                         | Local result                                                               | Exact-head result |
| ------------------------------------------------------------ | -------------------------------------------------------------------------- | ----------------- |
| API unit, typing, lint, branch coverage                      | **PASS** — 1,413 tests; 95.89% line, 90.11% branch coverage                | Pending           |
| React/Vitest, strict TypeScript, ESLint                      | **PASS** — 116 tests; 91.00% statements, 85.57% branches                   | Pending           |
| Generated OpenAPI contract check                             | **PASS**                                                                   | Pending           |
| Documentation/context and repository formatting              | **PASS** — `make docs-check`, `pnpm format:check`                          | Pending           |
| Synthetic Playwright, screenshots, axe and responsive checks | **PASS** — 1 Chromium E2E; axe 0, console errors 0, overflow 0 px          | Pending           |
| 500-point chart benchmark                                    | **PASS** — p50 507.52 ms, p95 609.85 ms in local jsdom                     | Pending           |
| Actual API + disposable DB + BFF + persisted-value parity    | Harness stopped at missing Docker CLI; **CI REQUIRED**                     | Pending           |
| No-write database digest before/after browsing               | Not executed without disposable PostgreSQL: **CI REQUIRED**                | Pending           |
| Locked dependency and secret scans                           | **PASS** — pip-audit clean, pnpm audit clean, gitleaks found no leaks      | Pending           |
| Trivy filesystem scan                                        | **INCOMPLETE** — Helm config scan hit context deadline; no clean result    | Pending           |
| Container image scans and expired exception policy           | See [security review](../security/phase-9h-security-review.md); unresolved | Pending           |
| Canonical full-stack/regression workflow                     | **CI REQUIRED** for Docker-backed gates                                    | Pending           |
| Required GitHub Actions on exact final SHA                   | Final SHA pending                                                          | Pending           |
| PR to `main`, open and unmerged                              | Pending                                                                    | Pending           |

The runner writes source and browser evidence under ignored `.validation/phase9h/`, including the
direct oracle, `acceptance.json`, independent-check log, per-mode Playwright metrics, screenshots,
traces and service logs. Generated screenshots are kept out of Git; their reproducible capture IDs
and commands are documented in [the UI evaluation](phase-9h-ui-evaluation.md). CI must upload this
directory from the same PR-head SHA used by the independent check. Local acceptance is not a pass
when Docker is unavailable.

## Required final checks

- [ ] Remote branch SHA equals the final implementation SHA.
- [ ] Three 9B tasks and four 9C families match direct original rows and response payloads.
- [ ] Complete, partial, abstained and unverifiable evidence remain distinct.
- [ ] UI browsing changes none of the digested 9A–9G source, prediction, evidence, agent or
      evaluation tables.
- [ ] Login, expiry, logout, cross-vehicle, guessed IDs, CSRF, SSRF/configured-origin, generic-proxy
      bypass, source-role mismatch, stale async state and secret disclosure are checked.
- [ ] Synthetic demo is isolated and never used to hide unavailable persisted data.
- [ ] Quality, Integration E2E, canonical full-stack, Security, Dependency Review, CodeQL Python,
      CodeQL JavaScript/TypeScript and Phase 9H independent UI acceptance pass on this exact SHA.
- [ ] PR targets `main`, remains open and is not merged.

## Scientific limitations

The acceptance fixtures are synthetic. Exact source parity demonstrates faithful display of stored
decisions only. It does not demonstrate predictive validity, calibration on real vehicles, fault
diagnosis, causality or mechanical safety. Phase 9G calibration remains research-only and real-world
predictive validity remains `NOT_ESTABLISHED`.
