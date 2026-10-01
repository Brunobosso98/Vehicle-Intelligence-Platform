# Validation evidence — 2026-10-01

The table is a record of executed checks, not a future checklist. Environment reports are local;
remote CI execution is not claimed. Full raw logs are under ignored .validation in this workspace.

| Command / probe                                                    | Observed result                                                                                                                      |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| make bootstrap (original working tree)                             | Passed; frozen locks installed, no secrets required                                                                                  |
| make verify-local                                                  | Final local gate passed after edits; Python/TS checks, contracts, docs and Next build                                                |
| make check-api                                                     | 34 unit tests passed; 99.63% lines, 96.88% branches; both >=90% enforced                                                             |
| make check-web                                                     | Unit/lint/types passed; 9 unit tests, 100% each coverage dimension                                                                   |
| make contracts-check                                               | Passed; generated TS and OpenAPI synchronized                                                                                        |
| make build                                                         | Next production build passed                                                                                                         |
| make test-integration TEST_DB_IMAGE=vehicle-platform-db:validation | 1 real integration passed; clean upgrade/downgrade/re-upgrade/head, ready=200                                                        |
| PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium make test-e2e     | 2 passed; real status, keyboard, axe, unreachable/retry                                                                              |
| Actual docker compose stop db + HTTP probes + restart              | live=200, ready=503, matching request ID/error; failure metric present; restored ready=200                                           |
| make observability-check                                           | Passed response correlation and real request metric                                                                                  |
| Real Collector 0.146.1 + actual API HTTP request                   | Exported trace/request ID matched JSON logs                                                                                          |
| Gitleaks dir with config/redaction                                 | No leaks found                                                                                                                       |
| Initial pip-audit and pnpm audit --prod                            | No known vulnerabilities found                                                                                                       |
| Final make security                                                | Failed: public-registry HTTP 503; no success claim                                                                                   |
| Trivy filesystem/IaC                                               | Zero High/Critical findings after fixes                                                                                              |
| Trivy final API image                                              | 0 Critical, 44 High, zero available fixes                                                                                            |
| Trivy final repaired web image                                     | 0 Critical, 44 High, zero available fixes                                                                                            |
| Canonical make verify                                              | Non-zero: canonical Node 24.19.0 Trixie metadata returned HTTP 429 (Docker Hub rate limit); earlier build also failed HTTP 503       |
| Full observability profile                                         | Non-zero: Grafana registry HTTP 503, Tempo not validated                                                                             |
| Fresh working tree bootstrap with empty cache                      | Failed: public PyPI wheel download HTTP 503 after retries                                                                            |
| Fresh working tree with verified cached dependencies               | Passed in a clean working tree with explicitly configured verified package cache; initial uncached PyPI/npm requests failed HTTP 503 |
| Playwright managed-browser download                                | Denied by policy (cdn.playwright.dev, Domain forbidden); system Chromium 151 used                                                    |
| git diff --check                                                   | Passed; repository began empty, files are untracked additions pending review                                                         |

Actual network trace: request_id=phase0-real-trace, trace_id=dbc674760edd910fc1416a590e1d8fba,
HTTP GET /health/ready = 200. Structured log fields included UTC timestamp, level, service,
environment, event, request_id and trace_id; Collector debug exporter showed request.id with the
same trace ID. This is distinct from a full Tempo/Grafana visualization check.

API/web runtime images accepted UID 10001. Docker Hub failure was not bypassed with credentials,
TLS disabling or an unapproved network route. Official allowed GHCR/Quay mirrors and checksum-
verified public upstream archives were used as explicitly documented validation alternatives.

Final static validation: YAML syntax, all local Markdown links, five scoped AGENTS files,
four skill frontmatter definitions and every shell script syntax passed via make docs-check.
Whitespace diff checking also validated every new first-party file against an empty baseline.
Initial working-tree bootstrap and a separate cached clean-tree bootstrap both passed.
The cached clean tree used an explicit temporary .npmrc with offline=true and a previously verified
pnpm store; this is a cached installation proof, not an empty-cache network-bootstrap success.

Follow-up recheck on 2026-10-01: HTTP requests to PyPI (PyYAML metadata), npm (Next metadata)
and GitHub (uv README) returned 200. Docker Hub's unauthenticated `/v2/` returned the expected
401 challenge, and `docker manifest inspect node:24.19.0-trixie-slim` succeeded (exit 0).
`pip-audit -r .validation/requirements.txt --require-hashes --disable-pip`, with the writable
workspace XDG cache, and `pnpm audit --prod --audit-level high` both returned exit 0 and
"No known vulnerabilities found". Logs: `.validation/node-manifest-recheck.log`,
`.validation/python-audit-recheck.log`, `.validation/node-audit-recheck.log`.
These checks do not establish that full image downloads/builds, an empty-cache bootstrap,
or the complete security/observability gates have passed. Historical network failures remain
recorded above; their cause was not isolated between upstream services and the environment proxy.
