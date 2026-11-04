# Phase 9H security and accessibility validation

**Status: NOT VERIFIED.** API, web and synthetic-browser local gates pass. Persisted-session browser
tests, disposable-database no-write proof, the final filesystem scan and container-image policy
remain incomplete or pending exact-head CI.

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

| Threat                                    | Check surface                                                                              | Evidence/status                                                                |
| ----------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| Unauthorized, expired or revoked session  | API route, component and browser                                                           | API/BFF/component tests pass; live protected browser **CI REQUIRED**           |
| Cross-vehicle and guessed-receipt IDOR    | Vehicle-scoped query and BFF allowlist                                                     | Unit/API tests pass; live source isolation **CI REQUIRED**                     |
| CSRF and cross-origin requests            | Origin/Referer, fetch-site and session CSRF token                                          | Auth/server tests pass; persisted browser **CI REQUIRED**                      |
| SSRF or arbitrary upstream path           | Fixed origin/host, route grammar, no client URL, redirect rejection                        | Server tests pass; Docker acceptance **CI REQUIRED**                           |
| Generic proxy bypass                      | Normalized predictive alias denylist                                                       | Web unit tests pass; persisted browser **CI REQUIRED**                         |
| Credential disclosure                     | Server-only environment, no-store responses, browser trace                                 | Synthetic browser has no secrets; persisted trace **CI REQUIRED**              |
| Resource exhaustion                       | Five login attempts/minute, 60 reads/minute, four concurrent reads, 8 s timeout, 1 MiB cap | Server tests pass; runtime acceptance **CI REQUIRED**                          |
| Source/evidence mismatch                  | Fail-closed scope comparison                                                               | API/component mismatch tests pass; persisted oracle **CI REQUIRED**            |
| Stale async response after vehicle change | Abort old scoped fetch and ignore late response                                            | Component stale-response test passes                                           |
| Unintended data writes                    | Read-only SQL and before/after digests                                                     | Disposable DB **CI REQUIRED** locally                                          |
| Dependency/container exposure             | Locked audits, fresh Trivy and image policy                                                | Python/Node audits and gitleaks pass; Trivy timed out; image policy unresolved |

## Accessibility and responsive acceptance

Playwright synthetic Chromium runs axe with WCAG 2.2 AA-related tags and checks keyboard focus on
the skip link: **0 violations** and **0 page errors**. Charts have accessible names/descriptions
and source tables remain available for exact values. The UI supports reduced motion, visible focus,
semantic labels/headings, responsive type and overflow-safe history. Measured overflow is **0 px**
at 1440, 768 and 390 px. Persisted browser accessibility, bearer-disclosure and API-host request
metrics remain **CI REQUIRED** because the disposable DB/BFF flow could not start without Docker.
