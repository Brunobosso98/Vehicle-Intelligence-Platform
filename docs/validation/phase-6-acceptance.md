# Phase 6 acceptance evidence

Base main: `480e89acdecb6deecd2678389eab3f98fb7f3837` (Phase 0–5 hardening).
Branch: `codex/phase-6-mcp-tool-platform`.

## Executed development evidence

- SDK 2.0.0 official client negotiated `2026-07-28` automatically.
- Independent acceptance exercised all 22 tools, 36 positive/negative scenarios and three resources
  against disposable TimescaleDB. Fixture: two vehicles, three configurations, six sessions,
  eighteen detected pulls and factual boost-drop events, built through application routes.
- Table-count fingerprints before/after MCP calls were identical, including analytics and capability
  report tables. Read-only transactions additionally reject database writes.
- Sanitized delivered trace evidence: 36 MCP spans, nine analytics source-selection spans and 292
  database spans; SQL text and exception events absent.
- API unit gate: 247 tests passed; 96.58% line and 92.10% branch coverage, thresholds unchanged.

- Actual stdio and HTTP subprocess clients passed the complete inventory, resources,
  safe validation errors, concurrent reads, authentication/scope/expiry negatives,
  restart/reconnect and bounded backend loss/recovery.
- Large fixture: 100,002 canonical samples and 102 sessions; 1,000 ordered points
  returned with explicit truncation, 439,310 wire bytes, 2,806,060 peak traced Python
  bytes; database UPDATE rejected by actual read-only transactions.
- Benchmark: 34 successful requests, zero errors; p50 0.962s, p95 1.345s,
  p99 1.458s, 1.324 requests/s, 2,104,956 peak traced Python bytes.
  Quantiles are descriptive for this small sample on local WSL, not an SLA.
- Actual Compose MCP request delivered MCP/database spans to Tempo and tool metrics
  to Prometheus; SQL and bearer token redaction verified in delivered evidence.
- Six existing disposable database/migration/stream integration tests passed.
- `make verify-cloud` passed the Phase 0–5 non-Docker regressions and security gates.

- Docker MCP HTTP E2E passed all 22 tools/resources, four concurrent pull reads,
  a real container stop/start and a new client lookup with the same fixture identity.
- Existing canonical stack, dependency recovery and full Phase 1–5 observability passed.
- Live stream benchmark persisted 100,000/100,000 observations with zero loss or duplicate canonical rows.
- Existing browser suite: eight Playwright tests passed. Frontend line coverage
  97.19%, branches 86.34%; thresholds and selectors unchanged.

## Executed complete local checkpoint

`make verify` passed at committed HEAD `4f15120966c2528aebf67739b84983f1b7f880a2`
on 2026-10-05, with a clean tree. It executed cloud/typing/coverage/format/contracts,
all Phase 0–5 acceptance and benchmarks, rebuilt images with this SHA, disposable
integration/migration validation, fresh MCP acceptance and all actual transports,
MCP runtime observability, canonical stack/recovery, eight browser E2E tests,
100k live observations, all eight image security policies and full observability.
No Docker-dependent check was skipped. Existing security risk exceptions were
retained; no new exception was introduced.

Checkpoint benchmark: 34/34 success, zero errors; p50 0.588s, p95 0.917s,
p99 1.028s, 2.045 requests/s, 1,983,341 peak traced Python bytes, maximum
173,166 wire bytes. Large results: 439,310 bytes and 2,781,888 peak traced bytes.

The completion audit then corrected two warning semantics: signals omitted by a
truncated sample set use `partial_window`, and quality/configuration limitations
do not imply insufficient history. Focused positive/negative unit cases and a
real client multi-signal truncation case cover these corrections. The final
committed revision must repeat the gate after this audit.

## Gates still requiring final committed-head evidence

Stdio/HTTP complete E2E, backend recovery, restart/reconnect, benchmark/result-size validation,
full existing Phase 0–5 regression, all local project checks, clean-state rerun, final SHA validation,
push, open PR and required checks for that SHA must all pass before Phase 6 is declared verified.
Development results above do not claim final delivery completion. The traceability ledger records
implementation/test ownership and remaining evidence.
