# Phase 0 task map

Status as validated on 2026-10-01. **Phase 0 remains open.** See
[completion report](phase-0-completion-report.md) for evidence and environment limitations.
"Implemented" alone does not mean its acceptance gate passed.

| ID     | Work                            | Status                                                                                                                   |
| ------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| F0-001 | Repository/toolchain foundation | Locks created; bootstrap passed in original workspace; empty-cache clone blocked by HTTP 503                             |
| F0-002 | Codex context architecture      | Five scoped AGENTS implemented; static validation recorded in report                                                     |
| F0-003 | Repository skills               | Four skills implemented; static validation recorded in report                                                            |
| F0-004 | Documentation architecture      | Architecture docs and ten ADRs implemented; link/YAML checks recorded in report                                          |
| F0-005 | Backend foundation              | Unit/types/lint/build and real live/ready behavior validated; final clean rebuild blocked by network                     |
| F0-006 | Database foundation             | Clean upgrade/downgrade/re-upgrade/readiness passed on source-built PG17.11/Timescale2.30.2; upstream image pull blocked |
| F0-007 | API contracts                   | OpenAPI model tests and generated drift gate passed                                                                      |
| F0-008 | Frontend foundation             | Unit/types/lint/production build and real E2E passed                                                                     |
| F0-009 | Docker environment              | API/web runtime and health passed with documented fallback; canonical full rebuild blocked                               |
| F0-010 | Observability                   | Real Collector trace, metric and JSON-log correlation validated; full Tempo/Grafana profile blocked by registry          |
| F0-011 | Unit testing                    | Passed; coverage recorded in report                                                                                      |
| F0-012 | Integration testing             | Passed on disposable real PostgreSQL/Timescale database                                                                  |
| F0-013 | E2E testing                     | Two Playwright tests passed using local Chromium 151                                                                     |
| F0-014 | Security baseline               | Secret/initial dependency scans passed; filesystem scan passed; zero Critical final images; 44 High/image unresolved     |
| F0-015 | GitHub CI                       | Workflows configured; YAML validated locally; remote jobs not executed                                                   |
| F0-016 | Dependency automation           | Dependabot configuration implemented; remote scheduling not verified                                                     |
| F0-017 | Developer experience            | Make targets and local instructions implemented; cold bootstrap blocked by public registry HTTP 503                      |
| F0-018 | Documentation/runbooks          | Implemented for actual foundation behavior only                                                                          |
| F0-019 | Final validation                | Blocked: canonical make verify non-zero, full profile/clean bootstrap/network and security findings                      |
