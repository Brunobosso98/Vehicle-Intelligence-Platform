# Phase 6 acceptance evidence

Base main: `480e89acdecb6deecd2678389eab3f98fb7f3837` (Phase 0–5 hardening).
Branch: `codex/phase-6-mcp-tool-platform`.
[Pull request #20](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/20)
is open against main; merging is reserved for the user.

## Executed acceptance checkpoint

Checkpoint SHA: `3474678b5f35d1bc1798b622f3ee9c71130b3ab2`, 2026-10-05.
`make verify` passed with a clean working tree, usable Docker and no skipped Docker gates.
GitHub CI, Security and the canonical Docker/full-stack workflow also passed for this SHA.

| Gate                    | Executed evidence                                                                        |
| ----------------------- | ---------------------------------------------------------------------------------------- |
| API                     | 247 unit tests; line coverage 96.58%, branches 92.10%; strict typing/lint PASS           |
| Web                     | 32 unit tests; line coverage 97.19%, branches 86.34%; build/lint PASS                    |
| Contracts/documentation | generation drift, formatting and documentation checks PASS                               |
| Earlier phases          | All Phase 0–5 independent acceptance and benchmarks PASS                                 |
| Database                | Six disposable integration tests, upgrade/downgrade/reupgrade and replay PASS            |
| MCP acceptance          | 36 scenarios; all 22 tools and three resource templates PASS                             |
| Protocol E2E            | Actual stdio and Streamable HTTP subprocess clients PASS                                 |
| Container E2E           | Hardened MCP container, four concurrent calls, stop/start/reconnect PASS                 |
| Dependency recovery     | Bounded readiness/tool failures during actual database pause, recovery PASS              |
| Browser/stack           | Eight Playwright tests; broker/consumer/database/API interruption recovery PASS          |
| Live streaming          | 100,000/100,000 persisted; zero loss or duplicate canonical rows                         |
| Security                | Locked dependency, secret and all eight image policy gates PASS; no new exceptions       |
| Observability           | Delivered Tempo traces and Prometheus metrics, SQL/token redaction PASS                  |
| Clean state             | Each MCP evaluator uses a fresh disposable database; canonical CI repeats acceptance/E2E |

Coverage thresholds, migration history, frontend selectors and existing security risk exceptions
were retained. No automotive calculation was duplicated, and no schema migration was needed.

## Independent MCP evidence

The official SDK `mcp==2.0.0` client negotiated protocol `2026-07-28` automatically.
Fixtures use application routes: two vehicles, three configurations, six sessions, eighteen
canonical pulls and factual boost-drop events. Acceptance checks actual identifiers, numeric
comparisons, sufficient/insufficient histories, configuration segmentation, ownership negatives,
safe validation errors, missing signals, partial windows and every tool/resource family.

Table-count fingerprints before/after calls are identical, including analytics and capability
report tables. Actual read-only transactions reject UPDATE. Transient calculation identities
retain existing algorithm/configuration/source hashes without persisting new analysis runs.
Sanitized delivered evidence contains 36 MCP spans, nine analytics selection spans and 292
database spans. SQL text, bearer tokens and exception details are absent.

Both real transports exercise authorization/scope/expiry negatives, origins, request limits,
concurrent reads, restart/reconnect and actual backend failure/recovery. Container acceptance
uses the built application image with a read-only filesystem, dropped capabilities and a new
client after restart. Truncated telemetry uses `partial_window` when a requested signal is
absent only from the returned subset; quality/configuration limits do not invent missing history.

## Measured performance and bounds

| Measure                        | Local WSL checkpoint          | Canonical GitHub checkpoint   |
| ------------------------------ | ----------------------------- | ----------------------------- |
| Representative MCP requests    | 34/34 success, zero errors    | 34/34 success, zero errors    |
| p50 / p95 / p99                | 0.608 / 1.054 / 1.133 seconds | 0.226 / 0.348 / 0.491 seconds |
| Throughput                     | 1.880 requests/s              | 5.050 requests/s              |
| Peak traced Python allocations | 1,984,055 bytes               | 1,987,045 bytes               |
| Maximum benchmark wire result  | 173,166 bytes                 | 173,166 bytes                 |
| Maximum exercised concurrency  | Four calls                    | Four calls                    |

Large acceptance ingests 100,002 canonical samples and 102 sessions, returns 1,000 ordered
points with explicit truncation, and rejects database writes. The complete tool wire result is
439,310 bytes; peak traced allocations are 2,822,487 bytes locally and 2,810,940 bytes in CI.
These measured quantiles describe a small sample, not an SLA; Python allocation tracing does
not measure total process/container RSS. Limits are enforced separately: 512 KiB whole tool
results, 64 KiB HTTP bodies, eight active calls, ten-second execution, five-second SQL statements,
one-second lock waits, lists ≤100, comparisons ≤20 pulls, cross-session ≤10 sessions and
telemetry ≤8 signals / 60 seconds / 1,000 points.

## Remote proof and final HEAD identity

Checkpoint runs: [CI](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/37354020469),
[Security](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/37354020124),
[canonical full validation](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/37354020332).
The downloaded artifact `phase-0-full-validation-3474678b5f35d1bc1798b622f3ee9c71130b3ab2`
contains `summary/validation-summary.json`: the exact checkpoint commit, all nine checks PASS
and `full_gate: PASS`. Its `mcp/commit.txt` agrees. Python/TypeScript CodeQL, the aggregate CodeQL
result and dependency review also passed. The PR was OPEN, non-draft and MERGEABLE, with no merge.

This tracked document records executed checkpoint evidence; a commit cannot contain its own
content-derived SHA. Any subsequent documentation or implementation commit must repeat local
committed-head validation and receive green remote checks before the delivery verdict.
The [latest PR checks](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/20/checks)
and canonical artifact `phase-0-full-validation-<PR-HEAD-SHA>` bind the delivered revision.
Local logs are retained under `.cache/verify-*.log`; fresh MCP evidence and its current commit
are under `.validation/mcp/`. The final 34-item delivery report records the final SHA, matching
local/remote evidence, clean tree and unmerged PR; this checkpoint does not replace that audit.

## Limitations and deferred scope

The provisioned `mcp:read` token grants one operator reader access; tenant authorization and
OAuth issuance are not implemented. Public deployment requires externally terminated TLS.
Lists have no opaque cursor; Phase 5 historical selection bounds remain. Snapshots may change
when canonical source data changes. Observations and comparisons establish neither diagnosis
nor causation. Real proprietary BMW/Vgate/BimmerLink hardware compatibility remains outside
this synthetic protocol acceptance. Phase 7 LLM/agent orchestration and Phase 8 retrieval/RAG/
diagnosis remain deferred. No LLM, agent, RAG or vehicle-control functionality was added.
