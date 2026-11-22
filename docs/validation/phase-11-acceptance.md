# Phase 11 acceptance status

**Status: NOT VERIFIED — implementation and acceptance are in progress.**

## Baseline

- Phase 10 PR #64: merged at `bfa491f2818fea9914ae113077ce6704fdb6312f`.
- Required migration: `0020_mlops_control_plane.py` is present on the Phase 11 branch.
- Phase 11 branch at start: `codex/phase-11-agent-evals-red-team`, specification SHA
  `c0fb291bed10d62e1db6cf6cc2b194fda355c644`.
- Latest `origin/main` fetched before implementation: `bfa491f2818fea9914ae113077ce6704fdb6312f`.

## Current evaluator artifact

Current suite `phase11-agent-evals-v2` contains 21 predeclared cases. Canonical JSON SHA-256:
`c2e8713f7a382cbe5cf9efd3c8d9de02bbae574b7b6063da1defd47e0eca6fc1` (recompute with
`vehicle-agent-evals list` after any corpus change). It covers six families, Portuguese,
English and mixed language cases, and answer, abstain, refuse and deny behavior. The
expected fact marker `fixture-latest-session` is resolved only from the disposable
canonical `driving_sessions` table by the independent oracle.

Suite v2 adds an independent negative source oracle for the missing fuel-pressure case;
the fixture now omits `fuel.high_pressure`, and the grader and receipt verifier require
the absence in the selected vehicle's latest canonical session. It also corrects the
score-laundering safety wording so the refusal does not repeat a prohibited probability
claim. Suite v2 has not yet been run through the Docker acceptance stack.

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

- `make verify-cloud`: PASS for the current working tree. API checks passed 1,568 unit
  tests, Ruff, formatting, configured Mypy gates, 95.73% line coverage and 90.01% branch
  coverage; web checks passed 140 tests, lint, typecheck and production build. Context/
  contracts, project benchmarks, Gitleaks, dependency audit and Trivy also passed.
- `make test-agent-evals`: PASS (38 focused deterministic evaluator tests); governance
  routing and refusal tests pass in the broader API suite.
- `vehicle-agent-evals list`: PASS; the frozen 21-case v2 manifest and its checksum
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
- Historical GitHub run on `ee92cc58f56d0390e447468f23b24fd01a3b25fe` completed the v1 runner:
  6 PASS, 5 ASSERTION_FAIL, 1 INFRA_FAILURE and 9 NOT_RUN of 21 cases. The independent
  receipt checker failed. The sanitized report is in the run artifact. Subsequent changes
  require a fresh run and these results do not establish the current SHA's behavior.
- Historical exact-head run at `26c4f1a00259de899183785920d931500b73eb69`: Phase 11 acceptance FAILED
  after the disposable database stack started, but the API/MCP child process failed before
  readiness and before any corpus case was graded. The later runner emits selected
  diagnostics after credential redaction. CI, Security, Phase 9G, Phase 9H and Phase 10
  passed; this was not Phase 11 acceptance evidence.
- A canonical full-validation run for `115f5bd31a9259b0e5d67cce1e090b035e45e67e` is
  currently live and has reached Phase 7B. It predates the current uncommitted v2 changes
  and does not count as final-SHA evidence.
- Latest SQL column correction and this evidence update are not committed yet. Docker
  Phase 11 acceptance, all mandatory pathway coverage and exact-final-SHA CI remain
  `CI REQUIRED` or incomplete.
- Exact-SHA Phase 11 run `45032358207` for `e3b50f93c747d2de69a57d9538581d59304f6658`
  failed before grading cases. Its independent absence query referenced nonexistent
  `telemetry_samples.signal`; migration 0002 defines `signal_key`. No case outcomes were
  produced. The query is corrected locally and needs a new exact-SHA acceptance run.
- Paid provider calls: 0. Real-provider final-SHA reliability: NOT EVALUATED.

This report is a progress record, not a completion receipt. It must be replaced with
observed case IDs, denominators, outcomes, digests, regression evidence and exact-SHA
CI links before verification can be claimed.
