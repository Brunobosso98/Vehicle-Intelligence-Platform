# Phase 9H security and accessibility validation

**Protected browser security and accessibility: use the current exact-head [PR #57 checks](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/57/checks).**
The disposable-database, live API and protected Next.js BFF matrix passed on
`ddee2eefe75ec2b91e1ee112fd35b4cd4f51cb04` in [Phase 9H run 42252152633](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/42252152633).
It records the chart-bounds assertion, zero axe violations, zero browser API-host requests, zero secret
disclosures, and the complete adversarial access matrix. The final documentation commit must pass its
own exact-head run.

## Protected boundary

The real-data page is private by default and disabled in production. Its server-only BFF accepts
fixed read routes and a configured API origin, does not forward browser authorization headers, and
sends the 9D operator bearer only from the server. Sessions use a separate high-entropy operator
credential, short TTL, HttpOnly/SameSite-Strict path-scoped cookie, server-side registry and
constant-time MAC comparison. Session-changing actions require exact-origin and CSRF checks. Vehicle
UUIDs must be present in both the web and API allowlists. Responses are bounded, rate/concurrency
limited, abortable, `no-store`, and reject redirects. The general domain proxy rejects predictive
service aliases.

The read projection checks vehicle, receipt, horizon, source role, schema, exact score/threshold,
cutoff and status consistency. It redacts sensitive evidence keys and omits private lineage and
fingerprints. UI browsing never calls model, evidence materialization, evidence verification,
agent-start or calibration-promotion endpoints.

## Adversarial and privacy checks

| Threat                                    | Check surface                                                                                                        | Evidence/status                                                                 |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Unauthorized, expired or revoked session  | API route, component and browser                                                                                     | PASS — unauthenticated 401, invalid login, expiry/session and logout coverage   |
| Cross-vehicle and guessed-receipt IDOR    | Vehicle-scoped query and BFF allowlist                                                                               | PASS — foreign scope and guessed receipt return nondisclosing 404               |
| CSRF and cross-origin requests            | Origin/Referer, fetch-site and session CSRF token                                                                    | PASS — browser logout with wrong CSRF token returns 403                         |
| SSRF or arbitrary upstream path           | Fixed origin/host, route grammar, no client URL, redirect rejection                                                  | PASS — server tests cover origin/path/redirect bounds; no browser API-host call |
| Generic proxy bypass                      | Normalized predictive alias denylist                                                                                 | PASS — direct `/api/domain/prediction-service` bypass returns 404               |
| Credential disclosure                     | Server-only environment, no-store responses, browser trace                                                           | PASS — 0 bearer/secret disclosures and 0 private API-host browser requests      |
| Resource exhaustion                       | Five login attempts/minute, 60 reads/minute by default (hard cap 120), four concurrent reads, 8 s timeout, 1 MiB cap | PASS — bounded server tests; acceptance budget matches the 9D cap               |
| Source/evidence mismatch                  | Fail-closed scope comparison                                                                                         | PASS — mismatched receipt hides the evidence projection                         |
| Stale async response after vehicle change | Abort old scoped fetch and ignore late response                                                                      | PASS — component stale-response test                                            |
| Unintended data writes                    | Read-only SQL and before/after digests                                                                               | PASS — all captured table digests matched; no mutated tables                    |
| Dependency/container exposure             | Locked audits, fresh Trivy and image policy                                                                          | PASS by policy — no lockfile/filesystem High/Critical; image Highs are accepted |

## Accessibility and responsive acceptance

Playwright Chromium runs axe with WCAG 2.2 AA-related tags and checks keyboard focus on the skip
link: **0 violations** and **0 page errors** in synthetic and persisted modes. Charts have accessible
names/descriptions, with tables available for exact values. The UI supports reduced motion, visible
focus, semantic labels/headings, responsive type and overflow-safe history. Measured overflow is
**0 px** at synthetic 1440, 768 and 390 px and persisted 390 px. See the captured metrics and
screenshots in [the visual evaluation](phase-9h-ui-evaluation.md). The current browser acceptance
also checks every SVG chart-axis label against its viewBox bounds.

## Environment limits and exact-head status

The local `make verify-cloud` suite passed API/web, typing, build, contract, documentation, format
and Phase 0–5 checks before its mounted-path Trivy traversal was interrupted after 30 minutes with
no report. The ext4-source scan and exact-head GitHub Security workflow passed. This interrupted
local command is not counted as an overall pass. Docker-dependent acceptance is supplied by the
GitHub runner. The canonical full-stack and exact-head Security results are linked from
[PR #57 checks](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/57/checks).
