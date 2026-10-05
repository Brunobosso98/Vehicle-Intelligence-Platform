# Phase 6 acceptance evidence

Base main: `480e89acdecb6deecd2678389eab3f98fb7f3837` (Phase 0–5 hardening).
Branch: `codex/phase-6-mcp-tool-platform`.

## Executed development evidence

- SDK 2.0.0 official client negotiated `2026-07-28` automatically.
- Independent acceptance exercised all 22 tools, 35 positive/negative scenarios and three resources
  against disposable TimescaleDB. Fixture: two vehicles, three configurations, six sessions,
  eighteen detected pulls and factual boost-drop events, built through application routes.
- Table-count fingerprints before/after MCP calls were identical, including analytics and capability
  report tables. Read-only transactions additionally reject database writes.
- Sanitized delivered trace evidence: 35 MCP spans, nine analytics source-selection spans and 84
  database spans; SQL text and exception events absent.
- API unit gate: 243 tests passed; 96.58% line and 91.97% branch coverage, thresholds unchanged.

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

## Gates still requiring final committed-head evidence

Stdio/HTTP complete E2E, backend recovery, restart/reconnect, benchmark/result-size validation,
full existing Phase 0–5 regression, all local project checks, clean-state rerun, final SHA validation,
push, open PR and required checks for that SHA must all pass before Phase 6 is declared verified.
Development results above do not claim final delivery completion. The traceability ledger records
implementation/test ownership and remaining evidence.
