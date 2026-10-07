# Phase 7A acceptance

Status: NOT VERIFIED. Implementation and validation are in progress.

Initial synchronized branch: `codex/phase-7a-agent-core-grounded-orchestration`.
Baseline HEAD: `903caa213c5e2afd93bc41ea5fefce95a105d59a`.
Base main: `3d925a455fd2cf8df835fb21e4a1f845d8551463`.
Phase 6 merge ancestry was checked successfully. Docker CLI and daemon are available.

Pre-existing root/web package-lock changes were preserved in a named Git stash before
switching branches. The implementation began with a clean working tree.

Required evidence includes independent golden grounding evaluation, disposable migration
and persistence checks, actual MCP transport execution/recovery, browser/SSE E2E,
delivered traces and metrics, benchmarks, security gates, Phase 0–6 regressions,
clean-state revalidation and checks at the final pushed PR HEAD. Results will be recorded
after execution. No current implementation artifact alone proves acceptance.

## Development evidence (uncommitted tree; not final delivery proof)

- Focused agent suite: 147 passed after the connection recovery and temporal-source checks;
  provider/service runtime suite: 33 passed after adding completed-output and answer-publication
  deadline checks. The full gate is in progress.
- `make check-api` previously passed 389 tests with line coverage 96.32% and branch coverage
  91.15%; the current full gate collects 395 tests and is not final delivery proof.
- `make check-web`: passed; line coverage 97.22%, branches 86.21%. TypeScript and production
  `make build` passed after fixing optional stream data handling.
- Independent golden suite passed 11 scenarios, including unsafe operation refusal and controlled
  low-quality/gap input: factual support and valid-reference rates 1.0; zero unsupported claims,
  cross-vehicle leaks, unsafe calls or budget violations. Domain row fingerprints stayed unchanged.
- `make test-integration`: 8 passed including direct Phase 6 → 7A migration, persistence, provider
  failure/recovery and actual abandoned-run/tool-audit reconciliation in disposable TimescaleDB.
- Authenticated HTTP lifecycle, cancellation, disconnected-stream replay, MCP failure/recovery and
  actual paused-database outage/recovery passed after using owned connections without reuse.
  Recovery requires the first new execution to succeed. Benchmark revalidation remains pending.
- Container agent observability passed: successful and failed traces delivered to Tempo, continuous
  HTTP → agent → MCP → database trace, exported metrics, credential redaction in public data/logs.
- Browser E2E, full regressions, security, clean-state and exact final remote SHA checks remain pending.
- Real-provider smoke has not run: provider credential and model are not configured. Deterministic
  evidence does not establish real-model interpretation, availability, token billing or latency.

All evidence above concerns development revisions; no final pushed HEAD or PR acceptance is claimed.
