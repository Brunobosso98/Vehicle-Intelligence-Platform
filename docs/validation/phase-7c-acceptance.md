# Phase 7C acceptance

## Result

The Phase 7C implementation passed canonical full-stack validation on source commit
`a0b8987a7f1cc9f038d225112a36c3d6e6c6ca5d` in [GitHub Actions run 38153299504](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/38153299504).
The job completed with `FULL GATE: PASS` after the complete Phase 0–7C stack, browser, database,
security, observability, clean-state, and acceptance checks. The run took 44m28s. Its uploaded
`phase-0-full-validation-a0b8987a7f1cc9f038d225112a36c3d6e6c6ca5d` artifact contains the
commit-tied receipts, including the supervisor acceptance, benchmark, browser, and observability
logs. The later agent-observability readiness fix is included in the current branch, and its exact-
HEAD canonical rerun remains required before delivery. PR
[#35](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/35) remains open and
unmerged.

The readiness-fix commit `bd7f5dfda0ec03932f97b66fa66205b4b559c49e` also passed the complete
canonical workflow in [run 38179771780](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/38179771780)
(`FULL GATE: PASS`, 38m07s). Its CI jobs passed in
[run 38179771726](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/38179771726),
and security, both CodeQL languages, and dependency review passed in
[run 38179771817](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/38179771817).
That commit also passed local `make verify` with exit code 0. These are exact receipts for
`bd7f5df`. The linked workflow checks the documentation/report commit on the exact PR head, and
its generated summary binds gate results to that SHA.

The report and traceability ledger are part of this delivery. The workflow attached to the PR must
validate the resulting report commit as the final HEAD; its generated validation summary will record
the exact commit SHA and each gate result.

## Phase 7C receipts

- Independent evaluator: **PASS**, 23 scored executions and 196 actual HTTP MCP calls. It checked
  604 supported factual claims, 121/121 valid evidence references, 12/12 golden routes, one
  correctly handled conflict, and one correctly handled Phase 7B escalation. Unsupported factual
  claims, diagnoses, causal claims, unknown evidence references, cross-vehicle leaks, unnecessary
  specialists, missing required claims, tool-policy violations, budget violations, and unsafe
  action calls were all zero.
- Faults and recovery: provider/tool policy rejection, foreign vehicle, foreign evidence, timeout,
  provider failure, failed data-quality prerequisite, oversized response, evidence reuse, sibling
  parallelism, cancellation, and recovery after faults all passed through the real API/MCP path.
  Linked-session reanalysis created a new run over a newly materialized session.
- Browser: production Next.js and authenticated HTTP MCP E2E passed, including routing, structured
  specialist findings, conflict, grounded evidence, and the investigation recommendation. One
  Chromium test passed in 15.7 seconds.
- Benchmark: **PASS** with deterministic provider and four simultaneous independent runs. Zero,
  one, two-parallel, three-specialist, conflict/escalation, concurrency, and other-vehicle paths
  were measured for elapsed time, calls, cache hits, serialized result/SSE bytes, and process RSS.
  RSS is a Linux `/proc/PID/status` snapshot, not peak or per-request allocation. Real-model latency
  was not measured; real cost is unknown.
- Observability: **PASS**. Successful and failed supervisor traces, the MCP trace chain, exported
  metrics, and redaction were verified against the delivered collector, Tempo, and Prometheus.
  The trace set included the complete `data_quality`, `performance`, and `thermal` role spans.
- Persistence and compatibility: disposable database migration/integration and legacy AgentRun
  snapshots passed. No relational migration was needed; Supervisor state is an optional bounded
  artifact in the existing JSON record. SSE retains version 1.0 and supports additive version 1.1
  progress events.

## Local and canonical validation

- `make verify` on `bd7f5dfda0ec03932f97b66fa66205b4b559c49e`: **PASS**. This full local Docker
  validation included 580 API tests, 45 web tests, API coverage
  of 96.00% lines / 90.61% branches, web coverage of 93.57% statements / 85.43% branches /
  91.76% functions / 94.91% lines, mypy, Ruff, TypeScript, contracts, context, formatting,
  production build, deterministic Phase 0–5 checks, Phase 6–7C acceptance and regression paths,
  disposable database integration, stack recovery, 100,000-event persistence benchmark,
  observability, gitleaks, dependency security, and image scans. The default Docker builder was
  used after the environment's selected builder failed to start its Dockerfile frontend. The
  report commit still requires a fresh exact-HEAD local verification.
- The first canonical remote attempt on `772eadc` exposed a Tempo partial-snapshot race: its first
  trace query omitted one specialist span although the completed trace contained all roles. The
  observability validator now waits for the complete role-span set. It also waits for collector
  health, the OTLP listener, and Tempo readiness before emitting spans. The canonical run on
  `a0b8987` then passed the complete Phase 7C observability gate. A later readiness fix in
  `bd7f5df` makes `observability_agent.py` wait for collector health, its OTLP listener, and Tempo
  readiness. The exact `bd7f5df` local and canonical full-stack runs both passed; the final-head
  workflow repeats these checks for the delivered report.

The linked workflow and artifact are the source of exact commit-tied evidence. No paid real-provider
smoke was run. Deterministic provider usage is known zero; cost, real-model latency, and real-model
quality remain unknown. Phase 7D real-model evaluation and Phase 8 technical-document RAG remain
deferred. This implementation analyzes recorded evidence only; it does not diagnose a vehicle or
control vehicle hardware, brakes, steering, throttle, or ECU state.

See the [98-requirement traceability ledger](phase-7c-traceability-ledger.md) and the
[Phase 7C architecture](../architecture/phase-7c-specialist-agents-supervisor.md).
