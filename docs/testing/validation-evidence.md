# Validation evidence — 2026-10-01

## Split-executor implementation

Codex Cloud ran `make verify-cloud` after the split-executor implementation. It returned **0** and
covered Ruff lint/format, strict Mypy, 34 API units and coverage thresholds, ESLint, strict
TypeScript, 9 Web units and coverage thresholds, contracts/generated synchronization,
documentation/shell/YAML checks, Prettier, the Next.js production build, Gitleaks, locked Python and
Node production audits, and Trivy filesystem/IaC. The security outputs are machine-readable files
under ignored `.validation/security`.

Docker-dependent checks are now **CI REQUIRED** in this environment: canonical API/Web builds,
Compose stack behavior, disposable database/migrations, integration, Playwright E2E, all image
scans and the complete Collector/Tempo/Prometheus/Grafana path. They have not been reclassified as
passed. `.github/workflows/full-validation.yml` now owns that canonical execution and must run
successfully for Phase 0 completion.

Workflow/configuration checks also passed: `make docs-check`, `git diff --check`, Bash syntax for
every repository shell script, PyYAML parsing of Compose/Collector/workflow files, and
`go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7
.github/workflows/full-validation.yml`. A synthetic summary run mapped successful, failed and skipped
step outcomes to `PASS`, `FAIL` and `NOT RUN` while keeping the aggregate full gate failed.

## Closure rerun (23:33–23:38 UTC)

This rerun began from clean Git status at commit `99b5356`. Raw local logs are ignored workspace
artifacts named `.validation-clean-bootstrap.log`, `.validation-clean-verify-local.log`,
`.validation-make-verify.log`, `.validation-python-audit.log` and `.validation-node-audit.log`.

| Status  | Command / conditions                                                                                                                                         | Exit | Evidence                                                                                                                                                                                                                                                                     |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PASS    | `make bootstrap` in detached worktree `/tmp/vip-phase0-clean` with new, initially empty `/tmp/vip-uv-cache`, `/tmp/vip-pnpm-store`, and `/tmp/vip-xdg-cache` |    0 | uv downloaded and installed 83 locked packages; pnpm downloaded and installed 448 locked packages with frozen lockfile. Cache file counts after installation were 5,499 and 22,788 respectively.                                                                             |
| PASS    | `rm -rf apps/web/.next apps/api/build apps/api/dist && make verify-local` in that detached worktree                                                          |    0 | No application build output was reused. API lint/format/types and 34 units passed (99.63% line, 96.88% branch); Web lint/types and 9 units passed (100%); contracts/docs/Prettier and Next production build passed.                                                          |
| FAIL    | `make verify` in the primary worktree                                                                                                                        |    2 | Every `verify-local` stage passed again, including the production build. The canonical gate then stopped at `docker compose build`: `/bin/bash: docker: command not found` (Make target exit 127). This is a local-tooling limitation, not a registry failure.               |
| PASS    | `uv export ... --frozen ...` then `pip-audit -r .validation/requirements.txt --require-hashes --disable-pip`                                                 |    0 | Current locked Python production graph: `No known vulnerabilities found`.                                                                                                                                                                                                    |
| PASS    | `pnpm audit --prod --audit-level high`                                                                                                                       |    0 | Current locked Node production graph: `No known vulnerabilities found`.                                                                                                                                                                                                      |
| NOT RUN | Canonical API/Web image build, metadata inspection and runtime content/UID checks                                                                            |    — | Docker CLI is absent. No previously patched image is claimed as proof.                                                                                                                                                                                                       |
| NOT RUN | Compose DB/API/Web health, disposable migrations, E2E and observability profile                                                                              |    — | All require Docker in the supported path. No arbitrary sleeps or substitute services were used.                                                                                                                                                                              |
| NOT RUN | Fresh trace/log/Tempo/Grafana query, Prometheus backend query and Collector-failure recovery                                                                 |    — | The official profile cannot start without Docker. Prior Collector-only evidence remains historical and is not enough for completion.                                                                                                                                         |
| PASS    | `gitleaks dir . --redact --config .gitleaks.toml` through `make security`                                                                                    |    0 | Scanned 670.82 KB after the documentation changes; no leaks found.                                                                                                                                                                                                           |
| PASS    | Trivy filesystem vulnerability/IaC step through `make security`                                                                                              |    0 | Current DB: zero High/Critical lockfile vulnerabilities and zero Dockerfile misconfigurations.                                                                                                                                                                               |
| FAIL    | `make security`                                                                                                                                              |    2 | Earlier steps passed. The first third-party image, `timescale/timescaledb:2.30.2-pg17`, failed on a fixed Alpine High plus Critical/High bundled-Go findings, including Critical CVE-2025-68121 (`gosu`) and CVE-2026-33815 (`timescaledb-parallel-copy`). The loop stopped. |

The clean bootstrap is genuine dependency-cache isolation: both named dependency caches did not
exist immediately before the command, the detached worktree began at committed source, and `.next`,
`node_modules`, the API virtual environment and build/dist outputs did not pre-exist. Node 24.19.0
itself was installed and checksum-verified from nodejs.org immediately beforehand; that runtime
download is not an application dependency cache. The first Corepack attempt encountered direct
`ENETUNREACH` to npm IPv4/IPv6 addresses because Node proxy support was not enabled; a direct curl
through the configured proxy returned HTTP 200. The successful attempt set `NODE_USE_ENV_PROXY=1`
and used the already installed pinned pnpm executable, then downloaded every locked package into the
new isolated store. This distinguishes proxy configuration from upstream unavailability.

The source and CI command comparison remains aligned: CI uses `make bootstrap verify-local`,
`make bootstrap test-integration up`, E2E/observability checks, and `make bootstrap containers`
plus `make security`. Locally, `make verify` composes those same checks into the stricter single
gate. No mismatch requiring CI redesign was found.

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

## Canonical GitHub workflow run (2026-10-02)

Executing pull request 13 published the implementation as head commit `570aab1` and triggered
[`Phase 0 full validation` run 36945217453](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/36945217453).
The workflow completed **FAIL**. Cloud validation, both canonical application builds, disposable
database/migrations, stack behavior, and Playwright E2E completed successfully. Stack-log capture,
summary generation, and artifact upload also completed. The uploaded canonical summary records both
container security and observability as **FAIL**; the observability artifact nevertheless confirms
log correlation, the initial Tempo trace, Prometheus request/duration/readiness metrics, and Grafana
health before a later one-shot health request returned HTTP 503.

The image-security command failed policy, and the final enforcement step correctly kept the job
red. The uploaded artifact is named
`phase-0-full-validation-3d374adca803e3e1e48985627bd3a837685cda53`; `3d374adc` is GitHub's PR
merge commit, while `570aab1` is the reviewed head commit. Public run/check metadata was inspected
through GitHub's API. Artifact contents and step logs require an authenticated GitHub session and
were not available to this execution shell, so their contents are not claimed here.

A fresh local Trivy scan of the exact current database image digest
`timescale/timescaledb:2.30.2-pg17@sha256:b346edcdb51a1fd6020e3965e0bd1c9f3406fa6d5fbce1e28f4852587ef934e2`
confirmed **70 High/Critical occurrences across 39 unique CVEs**, including three Critical findings:
CVE-2025-68121 in the Go standard library embedded in `gosu`, plus CVE-2026-33815 and
CVE-2026-33816 in pgx embedded in `timescaledb-parallel-copy`. Every Critical has a published fixed
version. Docker Hub reports that `2.30.2-pg17` is also the current `latest-pg17` digest, so there is
no newer compatible official TimescaleDB tag to adopt at this time.

The image scan driver was changed after this run to scan every declared image and accumulate a
failing result instead of stopping at the first vulnerable image. This does not ignore or suppress
findings: any image policy violation still makes `make security` return non-zero, while producing
complete per-image JSON evidence for diagnosis.

The observability validator now uses bounded polling for component health, Tempo propagation,
Prometheus query results, API readiness after database recovery, and Collector recovery. HTTP 404
during trace propagation and transient recovery responses remain intermediate retry states; expiry
of any bounded window remains a hard failure. A new canonical run is required before either fixed
stage can be recorded as PASS.
