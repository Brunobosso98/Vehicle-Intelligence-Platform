# Phase 7A acceptance

Phase 7A is implemented. Executed checkpoint evidence is recorded below. Final delivery
requires local and remote receipts for the **same final pushed PR HEAD**, a clean working
tree and an open, unmerged PR. An older green run does not certify a later commit.

The final delivery receipt is maintained in [PR #21](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/21):
its body records the full SHA, local commands/results, fresh-state repeats, required check
URLs and the 46-item delivery report. The Checks tab and canonical workflow artifact are
independent remote evidence. Keeping this receipt outside the commit it validates avoids
changing the validated SHA just to record its own SHA. This document is a checkpoint
record and gate definition, not a claim that an unobserved future check passed.

## Baseline and delivery boundary

- Branch: `codex/phase-7a-agent-core-grounded-orchestration`.
- Initial synchronized HEAD: `903caa213c5e2afd93bc41ea5fefce95a105d59a`.
- Base main: `3d925a455fd2cf8df835fb21e4a1f845d8551463`.
- Phase 6 merge ancestry was checked successfully; Docker CLI and daemon are available.
- Pre-existing root/web package-lock edits were preserved in a named Git stash before
  implementation began with a clean tree. They are not part of the Phase 7A changes.
- Existing branch history is preserved. No force push, main modification or PR merge.
- The authoritative specification received whitespace formatting only; a comparison with
  whitespace removed confirmed that its content is unchanged.

## Executed checkpoint: `881fcca0bb75acf9369bbbf25854c32d626aa017`

Remote checks passed for this exact SHA:

| Gate                                                                                   | Result | Receipt                                                                                                                   |
| -------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------- |
| CI quality and integration/E2E                                                         | PASS   | [CI run 37659177635](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/37659177635)              |
| Security, Python/TypeScript CodeQL, dependency review                                  | PASS   | [Security run 37659177621](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/37659177621)        |
| Canonical Docker/full-stack, including agent gates and fresh acceptance/browser repeat | PASS   | [Full-validation run 37659177637](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/37659177637) |

The native Linux validation worktree checked out this committed SHA without source edits.
`make bootstrap` passed with frozen Python and pnpm locks. Local full verification is
recorded in the checkpoint receipt after terminal completion; individual executed results:

- `make check-api`: **396 passed**; line coverage **96.37%**, branch coverage **91.23%**.
  Ruff and strict mypy passed (79 checked source files).
- `make check-web`: lint, TypeScript and unit tests passed; line coverage **97.22%**,
  branch coverage **86.21%**. Production build, contracts, docs and formatting passed.
- `make test-integration`: **8 passed** with real disposable TimescaleDB, direct Phase 6
  to 7A migration, agent persistence/audit and abandoned-run reconciliation.
- Phase 0–6 deterministic gates passed. Phase 6 actual stdio/HTTP/container transports,
  restart/dependency recovery, read-only database enforcement, large-result bounds and
  delivered MCP traces/metrics passed. The catalog contains 23 tools.
- Agent golden: **11 controlled scenarios passed** at this checkpoint. All factual support,
  valid-reference and correct-configuration rates were **1.0**. Unsupported claims,
  cross-vehicle leaks, unsafe calls and budget violations were **0**. Domain fingerprints
  remained unchanged outside intentional owned fixture quality mutations.
- Agent authenticated HTTP lifecycle, explicit cancellation, stream disconnect/replay,
  actual stopped-MCP recovery and paused-database recovery passed. After unpausing the
  database, the first new execution must succeed; no recovery retry masks a failure.
- Dedicated Chromium agent E2E passed: actual measured **−10 K IAT association**, installed
  and removed parts, before/after configuration, insufficient causal evidence and Axe
  accessibility assertions through the real built web/API/authenticated MCP path.
- Remote canonical agent benchmark and observability passed, including four active runs
  and fifth-request rejection, success/failure traces delivered to Tempo, HTTP → agent →
  MCP → database continuity, exported Prometheus metrics and credential redaction.
- Cloud security passed locally; all canonical security/image gates passed remotely.

These are checkpoint receipts. The final HEAD is revalidated after all source/documentation
commits; its results and local full-verification exit status belong to the PR delivery receipt.

## Pushed-head full verification checkpoint: `66efbc744ab23c5ba0044cb6029ebd69c56f2206`

The Linux validation worktree was clean at this exact pushed SHA and `make verify` exited **0**.
The command completed all local gates, including a fresh full-stack run and fresh disposable
database/MCP projects. The canonical workflow artifact independently reports all ten gates
PASS for this same commit: [run 37674751426](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/37674751426).
Its `validation-summary.json` records `full_gate: PASS` and commit
`66efbc744ab23c5ba0044cb6029ebd69c56f2206`.

- API unit suite: **401 passed**; coverage **96.37% line / 91.23% branch**. Acquisition suite:
  **71 passed**. Web suite: **37 passed**, coverage **97.22% line / 86.21% branch**; lint,
  TypeScript, builds, contract checks, formatting and documentation checks passed.
- Disposable database integration: **8 passed**, including clean upgrade/downgrade/re-upgrade
  and agent lifecycle/recovery. Live stream benchmark: **100,000 produced, accepted and
  persisted; zero loss or duplicate canonical rows**. Analytics benchmark: 600,600
  observations; 5.38 MB peak traced Python allocation.
- Phase 6 acceptance: **23 tools**, **38 tool spans**, **9 domain spans** and **300 database
  spans**. Large MCP result: **100,002 canonical samples**, **1,000 returned**, truncation
  explicit, **439,310 result bytes**, **2,783,849 peak traced bytes**; write attempt rejected.
  Protocol/restart/reconnect, hardened container, benchmark and MCP observability passed.
- Phase 7A grounding: all **12 controlled scenarios** passed; factual support, evidence
  reference and configuration context rates **1.0**; unsupported claims, cross-vehicle leaks,
  unsafe action calls and budget violations **0**. HTTP cancellation, disconnect/replay and
  MCP/database failure recovery passed. Dedicated Chromium agent E2E passed in 1.8 minutes.
  The regular 9-test browser suite passed **8**, with its opt-in agent case skipped because the
  dedicated authenticated-MCP agent E2E ran separately and passed.
- Agent benchmark: four scenarios used **5/6/7/17 MCP calls**, four concurrent runs completed,
  excess admission returned **429**. Database deltas were measured; LLM latency was not
  claimed. Agent success/failure traces, MCP continuity, metrics and redaction passed.
- Secret, dependency and filesystem scans passed. Image policy reported zero critical findings
  and zero blocked findings; accepted high findings were API **44**, web **43**, Tempo **12**
  and Grafana **2**, with zero accepted high findings in the other scanned images.
- Phase 0–6 regressions, full observability path, recovery and stack checks passed. The final
  local `make verify` command exited **0**. Logs and generated evidence are in ignored
  `.validation/` paths in the native validation worktree.

At `66efbc7`, GitHub CI quality/integration, Security, Python and JavaScript CodeQL,
dependency review, aggregate CodeQL and canonical Docker/full-stack all succeeded. Exact
check details are linked from PR #21. This remains a checkpoint: the documentation commit
that records this receipt must itself be pushed and revalidated before the PR delivery receipt
can certify the final HEAD.

## Missing-evidence correction: `4df84696ab3ffb5d900399877849975b008fe4cf`

Questions about absent signals, unavailable technical manuals and absent comparable history
now identify the appropriate missing-evidence category. Unsafe-operation refusal requests no
evidence implying that the forbidden action could become available.

- Provider/service runtime suite: **38 passed**; Ruff and focused strict mypy passed.
- Independent golden: **12 scenarios passed**, including the additional technical-document
  question and explicit signal/refusal category checks. Support/reference/context rates
  remain **1.0**; unsupported claims, cross-vehicle leaks, unsafe calls and budget violations
  remain **0**. This focused execution supplements, rather than replaces, final full gates.

## Final receipt requirements

The delivery audit must show all of the following for the final PR head:

1. `make bootstrap` and complete `make verify` exit successfully at the committed SHA.
2. Fresh disposable projects/databases repeat agent acceptance, real MCP-backed browser E2E
   and observability; full verification is repeated after a green local checkpoint.
3. The benchmark records 5/6/7/17 MCP calls for context/one-summary/multi-tool/comparison
   scenarios, result/event byte bounds, process RSS, four concurrent completed runs, fifth
   request 429 and aggregate database counters. Deterministic latency is not LLM latency.
4. CI quality/integration-E2E, Security, both CodeQL languages, dependency review and
   canonical full-stack are successful at that same SHA. Pending, cancelled or unexpectedly
   skipped mandatory gates do not count as PASS.
5. PR head, origin branch and local validated HEAD match; git status is clean; main remains
   untouched; the PR is OPEN with no merge timestamp.
6. The [74-section ledger](phase-7a-traceability-ledger.md) and 46-item final report are reviewed
   against the actual execution receipts before using the VERIFIED completion footer.

Local logs and security/test/observability artifacts live in ignored `.validation/` paths.
Canonical CI uploads commit-tied `phase-0-full-validation-<SHA>` artifacts with the enforced
agent step in its validation summary. Native filesystem dependencies/security caches improve
validation I/O while preserving the frozen lockfiles and the source SHA under test.

## Real provider and practical limits

Real-provider smoke is **not executed**: `VIP_AGENT_API_KEY` and `VIP_AGENT_MODEL` are not
configured. The optional real Responses smoke command is implemented. No credential was
borrowed from the Codex session. Deterministic proof does not establish real-model
interpretation, availability, token billing or latency.

- LangGraph **1.2.14**, official OpenAI Python SDK **3.26.0**, operator-selected Responses
  model; the deterministic provider exercises the same graph/MCP/validator.
- One API worker and per-process concurrency/admission limits; no distributed admission,
  durable graph continuation or automatic resume. Interrupted persisted runs fail safely.
- Fixed validated answer templates; bounded history/evidence/results and explicit quality/
  truncation warnings. Missing data remains unavailable, never invented as zero.
- Vehicle reads are MCP-only. SQL writes are limited to the three agent-owned tables.
  Own agent SQL statements are not individually traced; MCP database spans prove the
  required delivered trace continuity.
- Benchmark database counters include background work and are not exact per-run SQL counts.
  Actual provider token fields may be unavailable; deterministic usage is genuinely zero.
  No fabricated pricing or billing estimate is reported.
- Trusted operator deployment follows the existing application boundary; no new tenant
  authorization layer is claimed. No ECU control/write, shell/SQL/arbitrary-HTTP tool,
  unsupported diagnosis or mechanical causal conclusion is available.
- Phase 7B adaptive investigation/logging, Phase 7C specialists and Phase 8 technical RAG
  remain deferred. Only the bounded missing-evidence and typed orchestration interfaces
  provide foundations for future work.
