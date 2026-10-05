# Toolchain selection

Inspected 2026-10-01: host Node 24.19.0 (LTS), Python 3.12.14 (supported security branch),
uv 0.12.19, pnpm 11.19.0, Docker 28.4.0 and Compose 2.40.3.
Direct requirements are exact pins; transitive Python/Node versions are in uv.lock/pnpm-lock.yaml.
Python 3.12 is supported through 2028; no preview interpreter is required.

| Component                | Pin         | Reason                                                  |
| ------------------------ | ----------- | ------------------------------------------------------- |
| Next.js                  | 16.3.8      | stable App Router                                       |
| React                    | 19.3.0      | stable release                                          |
| TypeScript               | 5.9.3       | mature strict ecosystem                                 |
| ESLint                   | 10.11.0     | current stable; official compatibility bridge, ADR 0008 |
| Vitest                   | 5.0.3       | unit/component tests                                    |
| Playwright               | 1.63.0      | real browser E2E                                        |
| FastAPI                  | 0.142.2     | typed async HTTP                                        |
| Pydantic settings        | 2.15.0      | early validated configuration                           |
| SQLAlchemy               | 2.0.54      | async; compatible with pinned OTel instrumentation      |
| Alembic                  | 1.20.0      | versioned migration management                          |
| asyncpg                  | 0.31.0      | async PostgreSQL driver                                 |
| Mypy                     | 2.3.1       | strict mature Python type checker                       |
| Ruff                     | 0.16.10     | lint/format                                             |
| OTel SDK                 | 1.45.0      | stable tracing/metrics core                             |
| PostgreSQL / TimescaleDB | 17 / 2.30.2 | supported relational time-series foundation             |

OTel canonical contrib packages retain beta suffixes. ADR 0004 explicitly justifies that limited
exception to the default no-preview rule; no beta application framework is used. Dockerfiles use
version tags (uv has a verified digest); future registry digest refreshes belong to dependency updates.
The canonical API base is official GHCR uv/Python 3.12.14 on Debian Trixie, pinned by verified digest.
Runtime OS security updates are applied; the optional source-built DB/Node fallback is recorded separately.
No benchmarks are inferred from version selection. Minimize production dependencies and document
non-obvious new requirements in the PR; prefer maintained packages and frozen installs.

Build backend: Hatchling 1.32.4 (exact pin, verified in installed build cache).

Retrospective review on 2026-10-04 found that SQLAlchemy 2.1.1 was outside the pinned
OpenTelemetry SQLAlchemy instrumentor dependency range. The exact requirement and uv lock
now pin 2.0.54; runtime integration must verify database spans instead of accepting a
startup dependency-conflict warning. No instrumentation or security gate is disabled.
