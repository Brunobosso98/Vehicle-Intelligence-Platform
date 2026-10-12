# Roadmap

- Phase 0 — Engineering Foundation (complete; canonical full validation passed before Phase 1)
- Phase 1 — Vehicle & Telemetry Core (complete)
- Phase 2 — Sessions & Pull Detection (complete)
- Phase 3 — Event / Anomaly Engine (complete)
- Phase 4 — Streaming & Live Vehicle Acquisition (complete)
- Phase 5 — Automotive Analytics (complete)
- Phase 6 — MCP Tool Platform (complete; see Phase 6 acceptance evidence)
- Phase 7A — Agent Core & Grounded Orchestration (implemented; see acceptance and PR-head receipts)
- Phase 7B — Investigation & Adaptive Logging (complete; canonical regression verified in Phase 7C)
- Phase 7C — Specialist Agent Orchestration (VERIFIED; PR #35 canonical exact-head gates passed)
- Phase 7D — Real Model Validation & Agent Reliability Baseline (in progress; real evaluation pending)
- Phase 8 — Technical RAG (planned)
- Phase 9 — ML / Predictive Models (planned)
- Phase 10 — MLOps Platform (planned)
- Phase 11 — Agent Evals / Red Team (planned)
- Phase 12 — Production Cloud Infrastructure (planned)
- Phase 13 — Advanced Vehicle Intelligence (planned)

Phases 7A–7C are implemented. Phase 7B provides the bounded, approved, read-only investigation
and logging-recipe workflow. Phase 7C adds bounded specialists and supervisor orchestration.
Phase 7D evaluates a real model; Phase 8+ capabilities remain deferred.

# Current phase

Phases 0–6 passed canonical acceptance. The Phase 7A agent consumes MCP facts and validates
structured claims. The [Phase 7A gate](../validation/phase-7a-acceptance.md) records executed
checkpoint evidence and identifies the exact-head delivery receipts.
Unsupported diagnosis, proven root-cause interpretation, RAG, ML and future infrastructure remain deferred.

## Phase 7C implementation

Bounded specialist orchestration is VERIFIED over the validated Phase 6/7A/7B
boundaries. [The execution specification](../prompts/phase-7c-specialist-agents-supervisor.md)
and [traceability ledger](../validation/phase-7c-traceability-ledger.md) define the full gate.
[PR #35](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/35) merged at
`9b2b2a621d0a903262e4a15a75ea4f102740d60a`. Its final head
`1a07ced07b85393b22b68da62dbcca357ba6d501` passed CI quality/integration E2E,
Security/CodeQL/dependency review and the canonical Docker/full-stack gate
[run 38198158098](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/38198158098).
The local workstation issue does not reopen Phase 7C; historical receipts remain intact.
Comprehensive real-model evaluation is Phase 7D; documentary retrieval and RAG remain Phase 8.
