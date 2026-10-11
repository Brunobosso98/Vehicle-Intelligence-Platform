# Phase 7C acceptance progress

Phase 7C is **not verified**. The [traceability ledger](phase-7c-traceability-ledger.md)
maps all 98 specification requirements to implementation and validation evidence. Exact final
committed-head local and remote validation remains mandatory.

## Baseline and current checkpoint

Branch: `codex/phase-7c-specialist-agents-supervisor`. Synchronized specification baseline:
`93a6998dba47c67d86675d3d3d87b090ec0cb4d2`. Phase 7B merge
`c8bfd163a5f90bbc19d3ae224a4e8a2cfb711208` is an ancestor. The complete specification and
Phase 6/7A/7B boundaries were read before implementation. Docker CLI and daemon are available.
PR [#35](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/35) is open and unmerged.

Current source correction checkpoint: `eadb69d1e0f0963a024af0179b83b98a7bcb7fa6`; the Phase 7B
benchmark fixture correction is pending commit. The measurements below are development evidence,
not final committed-head verification.

- `make check-api`: **580 passed**, lint and typing passed; line coverage **96.00%**, branch
  coverage **90.61%**, both above the configured 90% floor.
- Focused Supervisor/provider/investigation regression: **126 passed**.
- `make phase7b-acceptance`: **61 scenarios passed** through real API/MCP and a disposable
  TimescaleDB. Approval, source/vehicle linkage, reanalysis, replay, cancellation and recovery passed.
  The sufficient-answer case now uses canonical imported and processed recordings. Finalized link
  fixtures without samples still fail the quality gate correctly.
- `make benchmark-investigation`: **PASS** after adding a canonical, processed 10 Hz repeated-pull
  recording with no captured fuel-pressure channel. It retains the three-hypothesis benchmark
  assertion, creates a real fuel measurement gap and keeps recorded RPM/speed/throttle/temperature
  reliable. Planning used one deterministic provider call and four existing-evidence MCP calls,
  producing two gaps and four signal needs. The linked follow-up reported actual MCP call and
  duration counters; RSS readings are current-process samples, not peak memory.
- Corrective behavior preserves quality and measurement gaps, prevents unreliable signal availability
  from closing a measurement gap, retains the domain hypothesis alongside a quality prerequisite,
  and allows answers with noncritical limitations without automatically requesting a capture.
- The first `make verify` invocation on this correction failed during web checks: Vitest timed out
  starting the analytics test worker while image reconstruction was active. Seven files and 35 tests
  ran, but the missing analytics file made that coverage incomplete. This is a failed gate, not a
  valid frontend coverage measurement. A full repeat after image reconstruction is mandatory;
  worker timeouts and coverage thresholds remain unchanged. The next invocation passed API, web,
  contracts, context, format, production build, cloud security and nine integration tests before
  Compose could not publish host port 5432. The Docker daemon returned a Windows forwarding error;
  WSL reported no listener on 5432. A temporary Compose port override published the database on
  15432, and the full stack reached healthy API, web, broker and database services. A complete
  `make verify` repetition with that host-port-only mapping remains mandatory.

## Earlier executed evidence and limits

These results apply to earlier checkpoints and require final repetition:

- `make bootstrap`: locked dependencies installed.
- `make check-web`: passed; statements 93.57%, branches 85.43%, functions 91.76%, lines 94.91%.
- Contracts, context checks, formatting and production Next build passed.
- `make test-integration`: nine passed, including legacy AgentRun JSON, persisted Supervisor
  results and versioned SSE replay in a disposable database.
- Phase 7A grounded evaluation and HTTP failure/recovery/replay passed.
- Independent Phase 7C acceptance at `6ce0c1b`: 23 evaluated executions and 196 actual MCP calls;
  604 independently checked supported numeric bindings, 121 valid evidence references,
  12/12 correct golden routes, one correct conflict and one correct escalation. Unsupported
  factual/diagnostic/causal claims, unknown references, unsafe calls, cross-vehicle leaks and
  budget/policy violations were all zero.
- An earlier local Phase 7C repetition failed during the cache-reuse scenario with public category
  `database_unavailable`; PostgreSQL recorded cancellation of an event INSERT during concurrent
  image reconstruction. A later isolated supervisor evaluator passed all cases; final complete
  acceptance, browser, benchmark and observability repetition remains required.
- Actual production browser Supervisor flow, evidence/conflict display, investigation recommendation
  and axe accessibility passed at an earlier checkpoint.
- Supervisor benchmark passed, including four concurrent independent runs, cross-vehicle isolation,
  bounded calls and serialized result/stream bytes. Memory readings are process VmRSS snapshots,
  not per-request or peak memory. Deterministic elapsed times are not real-model latency.
- Canonical GitHub validation at `6ce0c1b` passed its Supervisor gate (including repeated fresh-state
  acceptance/browser and delivered Supervisor observability), but its full workflow failed Phase 7B.
  At `eadb69d`, Phase 7B acceptance (61 scenarios), browser (two tests) and observability passed;
  its three-hypothesis benchmark failed because the legacy recording had critical quality warnings
  and correctly received a fourth data-quality hypothesis. The corrected benchmark above preserves
  three hypotheses on reliable measurements with a real measurement gap. A new full remote run is
  mandatory.
- GitHub quality, integration E2E, security, both CodeQL languages and dependency review passed
  at `6ce0c1b`. Final exact-SHA checks still must pass.

## Delivery gates still pending

Full local `make verify`, current independent Supervisor acceptance, complete Phase 0–7B regression,
actual collector/broker investigation browser flow, delivered local observability, security images,
benchmarks, repeated fresh disposable validation, final documentation/report, clean final committed
and pushed SHA, and every required GitHub check on that same SHA remain mandatory.

Paid real-provider smoke is **NOT RUN**. Deterministic usage is known zero; real-provider cost
remains unknown without validated usage/pricing. Comprehensive real-provider evaluation is deferred
to Phase 7D; RAG remains deferred to Phase 8. No diagnosis or ECU/vehicle-control capability is added.
