# Phase 11 acceptance status

**Status: NOT VERIFIED — implementation and acceptance are in progress.**

## Baseline

- Phase 10 PR #64: merged at `bfa491f2818fea9914ae113077ce6704fdb6312f`.
- Required migration: `0020_mlops_control_plane.py` is present on the Phase 11 branch.
- Phase 11 branch at start: `codex/phase-11-agent-evals-red-team`, specification SHA
  `c0fb291bed10d62e1db6cf6cc2b194fda355c644`.
- Latest `origin/main` fetched before implementation: `bfa491f2818fea9914ae113077ce6704fdb6312f`.

## Current evaluator artifact

Suite `phase11-agent-evals-v1` contains 21 predeclared cases. Canonical JSON SHA-256:
`7afdc71361c240d07e27312e0a4107dafe3f22af410e9edb2a328b180439f608` (recompute with
`vehicle-agent-evals list` after any corpus change). It covers six families, Portuguese,
English and mixed language cases, and answer, abstain, refuse and deny behavior. The
expected fact marker `fixture-latest-session` is resolved only from the disposable
canonical `driving_sessions` table by the independent oracle.

The independent receipt checker also resolves required AgentRun IDs, vehicle ownership,
persisted result/findings/evidence, tool-call audit and durable event sequence directly from
the disposable database. Direct MCP authorization probes and plan-only CLI checks explicitly
declare that they do not create AgentRuns.

The actual integration runner calls the existing API and MCP HTTP processes with the
deterministic provider, persists AgentRun/SSE/tool audit evidence, and checks that
Phase 0–10 source rows remain unchanged. It is currently set to exercise the factual
session/event and source-injection flows, a foreign-session denial, missing-sensor and
score-laundering questions, fake capture and Phase 10 MLOps approval requests, harmless
quoted injection text,
an ECU flash refusal probe, and an MCP outage. The MCP outage is recorded as an
infrastructure failure unless the expected dependency failure is observed. Other
manifest cases are explicitly `NOT_RUN`; therefore full coverage and all Phase 11
acceptance gates remain incomplete.

## Validation performed in this implementation step

- `make verify-cloud`: PASS after the persisted-run checker, corpus checksum pin,
  pre-tool governance refusal, benign-quoted-injection regression and sanitized startup
  diagnostic changes. API checks passed 1,558 unit tests, Ruff, formatting, configured
  Mypy gates, 95.74% line coverage and 90.02% branch coverage; web checks passed 140 tests,
  lint, typecheck and production build. Context/contracts, project
  benchmarks, Gitleaks, dependency audit and Trivy also passed.
- `make test-agent-evals`: PASS (38 focused deterministic evaluator tests); governance
  routing and refusal tests pass in the broader API suite.
- `vehicle-agent-evals list` and `plan`: PASS; the frozen 21-case manifest and its checksum
  are reported, and plan output records zero paid calls. The plan command reports the
  current committed HEAD; uncommitted worktree changes are not part of that SHA.
- `uv lock --project apps/api --check`: PASS; lockfile unchanged.
- `bash -n scripts/mcp-validation.sh`: PASS.
- `graphify update .`: PASS; graph refreshed to 9,226 nodes after persisted-run checking,
  frozen-suite checksum enforcement, MLOps attack execution and pre-tool governance refusal.
- Docker availability: `docker` executable is absent locally; database-backed acceptance,
  container builds, Compose startup and full-stack validation are `CI REQUIRED`, not
  locally passed.
- Draft PR #65 targets `main`; it is open and not merged.
- Exact-head run at `26c4f1a00259de899183785920d931500b73eb69`: Phase 11 acceptance FAILED
  after the disposable database stack started, but the API/MCP child process failed before
  readiness and before any corpus case was graded. The new runner change emits selected
  diagnostics after credential redaction so the next exact-head run can identify the
  startup failure. CI, Security, Phase 9G, Phase 9H and Phase 10 passed; canonical full
  validation remains in progress at the latest status read. Full Phase 11 integration
  acceptance has not passed.
- Paid provider calls: 0. Real-provider final-SHA reliability: NOT EVALUATED.

This report is a progress record, not a completion receipt. It must be replaced with
observed case IDs, denominators, outcomes, digests, regression evidence and exact-SHA
CI links before verification can be claimed.
