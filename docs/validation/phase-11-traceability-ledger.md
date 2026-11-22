# Phase 11 requirement traceability ledger

This ledger maps all 155 specification requirements to current artifacts and records
the evidence state. `Partial` means an artifact or starting control exists but the
specified coverage has not been independently executed. No requirement is marked
complete merely because a scenario is present in JSON.

| Requirement(s) | Implementation/evidence mapping                                                                                                          | State                                                                                                                                                                                                   |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1–4            | Branch/baseline/spec audit; `docs/prompts/phase-11-agent-evals-red-team.md`; `docs/architecture/phase-11-agent-evals-red-team.md`        | Partial: baseline and source reconnaissance done; broader source audit continues                                                                                                                        |
| 5              | `docs/validation/phase-7d-real-evaluation.md`; `docs/validation/phase-11-provider-caveats.md`                                            | Specified; preserve historical mixed-SHA caveat                                                                                                                                                         |
| 6              | Existing `agents/evidence.py`, `agents/grounding.py`; new `agent_evaluation/grader.py`                                                   | Partial: independent persisted-claim checks implemented; real DB run pending                                                                                                                            |
| 7–13           | Existing investigation, 9F, MLOps, 9H controls; Phase 11 security/architecture docs                                                      | Partial: existing boundaries inspected; adversarial integration pending                                                                                                                                 |
| 14–16          | Suite families and `docs/security/phase-11-agent-red-team.md`                                                                            | Partial: threat categories authored; effectiveness not measured                                                                                                                                         |
| 17–20          | `agent_evaluation/contracts.py`, `evals/phase11/suite-v2.json`                                                                           | Partial: immutable bounded case/attempt/receipt contracts; not every protocol contract exists; v1 retained unchanged for prior receipts                                                                 |
| 21–23          | Frozen suite; `agent_evaluation/source_oracle.py`                                                                                        | Partial: 21 cases and read-only canonical digest/latest-session/event queries; broader fixture/source derivation pending                                                                                |
| 24–30          | `agent_evaluation/grader.py`; expected-fact corpus entries                                                                               | Partial: exact values, units, run/vehicle ownership, citation and abstention checks; negative measurement oracle added; full temporal/RAG matrix pending                                                |
| 31–37          | Existing safety/authorization code and critical cases                                                                                    | Partial: cases authored; predictions, fake approvals, serving and rollback attacks not integrated                                                                                                       |
| 38–42          | Existing specialist runtime and 7C budgets; case corpus                                                                                  | Not run: intent routing, conflict and concurrency cases remain                                                                                                                                          |
| 43–50          | Phase 8 retrieval code; synthetic approved/inapplicable/low-trust corpus in `scripts/evaluate_agent_red_team.py`; hidden-tool HTTP probe | Partial: RAG poison case is wired to real disposable ingestion/retrieval and a persisted retrieval-summary check; exact-SHA execution pending                                                           |
| 51–58          | Existing MCP schemas/auth and provider; attack/fault cases                                                                               | Not run: parameter fuzz, network isolation, canaries, exhaustion, retry and provider modes remain                                                                                                       |
| 59–68          | Metamorphic cases; existing grounding/source cutoff contracts                                                                            | Partial: case identities authored; transform execution, cache isolation, rendering and confidence grading remain                                                                                        |
| 69–73          | Independent grader and outcome enums                                                                                                     | Partial: usefulness and abstention distinction exists; ambiguity adjudication and broad routing metrics remain                                                                                          |
| 74–78          | Suite `suite-v2.json` (suite v6); report summary CLI                                                                                     | Partial: 21 cases, 3 language modes and family counts; holdout, historical mapping and complete coverage report absent                                                                                  |
| 79–87          | Receipt contracts and provider caveat report                                                                                             | Partial: zero paid calls enforced for deterministic receipts; paid exact-SHA harness and failure taxonomy incomplete                                                                                    |
| 88–94          | `scripts/agent_runtime.py`, `scripts/evaluate_agent_red_team.py`, existing 7B/8/9F/10 acceptance scripts                                 | Partial: runner uses actual API/MCP HTTP/LangGraph path for limited scenarios; required pathways not all exercised together                                                                             |
| 95–98          | Receipt privacy and `agent_evaluation` package                                                                                           | Partial: no hidden reasoning; source snapshot/grader/receipt exist; persistence and OTel adapter absent                                                                                                 |
| 99–104         | Static JSON corpus; independent receipt digest/checker                                                                                   | Partial: static inert cases, tamper checks and an independently rechecked absent-signal assertion exist; full negative-control suite pending                                                            |
| 105–108        | `source_oracle.py`; runner; `receipts.py`; API SSE/persistence                                                                           | Partial: replay/resume now exercised through API helper and independently bound to persisted event bytes; focused tamper tests pass, exact disposable CI, cancellation and complete auth matrix pending |
| 109–114        | CLI plan/run fences; existing agent budgets                                                                                              | Partial: local disposable DB guard and default zero cost; concurrency/resource/latency measurements pending                                                                                             |
| 115–126        | `suite-v2.json`; security and reliability reports                                                                                        | Partial: mandatory case families represented; most cases are not yet executed; observability labels/monitor isolation pending                                                                           |
| 127–132        | `EvalReceipt`, CLI, disposable wrapper                                                                                                   | Partial: SHA/suite/source/provider fields and plan/run/verify commands; manifest completeness, signed history and DB migration decision recorded; no migration added                                    |
| 133–138        | Tests, suite, architecture/security/acceptance/runbook docs, ADR 0051                                                                    | Partial: requested artifacts started; acceptance/reliability/provider/traceability docs state current gaps; sequential ADR set not complete                                                             |
| 139–140        | `README.md`, `AI_CONTEXT.md`, roadmap, provider caveat doc                                                                               | Partial: Phase 10 merged state and Phase 11 in progress recorded; full historical cross-reference audit pending                                                                                         |
| 141–145        | Make targets, reports, receipt checker                                                                                                   | Partial: targets exist, but canonical CI integration and adversarial scientific controls are incomplete                                                                                                 |
| 146–148        | Reliability report, source snapshot helper, existing Makefile gates                                                                      | Partial: local deterministic project benchmarks passed; disposable-stack reliability and Phase 0–10 integration regressions require Docker/canonical CI                                                 |
| 149–150        | Existing Phase 11 branch and PR #65                                                                                                      | Partial: implementation committed and pushed; draft PR targets main, acceptance remains incomplete                                                                                                      |
| 151–155        | Definition of Done and final report spec                                                                                                 | Not achieved: full corpus execution, independent acceptance, exact-head CI and review-ready PR remain required                                                                                          |

## Current evidence

- Latest `make verify-cloud`: all 1,573 API unit tests passed; line coverage 95.73%, branch
  coverage 90.07%. It also passed 140 web tests, production build, contracts, formatting,
  context checks, project benchmarks, Gitleaks, dependency audit and Trivy.
- Latest `make test-agent-evals`: 60 focused evaluator tests passed, including expected-fault,
  direct MCP probe, attempted/unattempted receipt, structured abstention, and present/absent signal checks.
- Exact-SHA run `45037890073` for `2f0663ad616e8cf7c4490da145f3c3a867c90553` failed: 15/21
  PASS, three assertion failures (`RED-003/004/005`), three NOT_RUN (`RED-007`, `FAULT-002/003`).
  Current local follow-up adds unsupported-source abstention policy, real Phase 8 poison
  ingestion/retrieval, and a persisted malformed-provider-output run. `make check-api` passes
  1,581 tests at 95.70% line / 90.02% branch coverage; 58 focused tests and Ruff pass. Exact-SHA
  validation of the new runner paths is pending; full corpus/pathway requirements remain incomplete.
- `make verify-cloud` passes on the current worktree, including 1,581 API tests, 140 web tests,
  production build, contracts/context/format, project benchmarks, Gitleaks, dependency audit
  and Trivy. Docker-dependent exact-SHA disposable acceptance remains CI REQUIRED.
- Latest local `make verify-cloud`: PASS with 1,583 API tests, 95.70% line / 90.02% branch
  coverage, 140 web tests, web lint/typecheck/build, contracts, context/format, deterministic
  Phases 0–5 gates, Gitleaks, dependency audit and Trivy. Strict Mypy for the Phase 11 runner
  and runtime/fixture helpers also passes. Suite v6 uses the versioned 21-case corpus and
  preserves suite v5 unchanged. Docker-backed Phase 11 execution remains CI REQUIRED.
- Exact-SHA Phase 11 run `45042245872` on `39c193e2b4bbc440bcdafc39e7c7e15f3a45d905`
  failed before grading: replacement MCP token entropy validation prevented process startup.
  Sanitized receipt recorded `runtime_process_startup_failure`, zero paid calls, and no case
  verdicts. Runner now uses a 48-byte URL-safe random replacement token; exact-SHA retry pending.
- Exact-SHA run `45042676186` on `1feff7e4da0e0fa0d48dcf94b1da36f716923a9a` failed with
  `evaluation_runner_failure` before verdicts because the MCP SDK rejected stale-token session
  negotiation before `tools/call`. Current code probes the stale-token JSON-RPC HTTP call
  directly and requires HTTP 401; exact-SHA validation pending.
- Exact-SHA suite-v6 run `45043159578` on `7382e6ef4c2306b20c2036f164798573114aafbf` passed
  all 21/21 cases and independent receipt verification. Family counts: 2 benign, 1 critical,
  12 red team, 2 metamorphic, 3 fault injection and 1 provider compatibility. Runtime 78.588s;
  source fixture SHA `6cdbd90f9a4f2c526eab4d346d9858e24ae2f2671fdcfc27daa1f2612987eac5`, schema
  revision `0020`, paid calls/cost 0. This satisfies the current 21-case acceptance run only;
  it does not complete all 155 requirements or replace pending exact-head Phase 0–11 CI.
- Ruff on the new evaluation package, tests and scripts passed after the focused fix.
- Docker is unavailable locally. All disposable DB/MCP/API, full-stack and other
  Docker-dependent checks are `CI REQUIRED` until exact-SHA GitHub Actions evidence
  exists.
- PR #65 is open as a draft. The latest exact Phase 11 run `45036858295` graded 12/21 (12 PASS,
  9 NOT_RUN) and failed the completeness gate. Earlier behavioral failures are recorded in
  `phase-11-acceptance.md`. Full integration acceptance and final-SHA checks are incomplete;
  no performance or real-provider receipt is claimed.
- Continuation change adds replay-from-zero and terminal-resume probes on persisted API AgentRuns,
  checks persisted run/tool audit snapshots for stability, and makes the independent checker
  reconstruct expected SSE bytes from the persisted event table. The focused evaluator suite now
  passes 61 tests; Ruff and configured strict Mypy pass. Exact disposable-stack validation remains
  pending; no end-to-end replay PASS is claimed.
