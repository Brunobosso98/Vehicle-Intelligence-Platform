# Phase 7C specialist agents and supervisor

Phase 7C is VERIFIED on the exact PR #35 head; the [current roadmap](../roadmap/README.md)
links canonical GitHub evidence. The authoritative execution specification is
[Phase 7C](../prompts/phase-7c-specialist-agents-supervisor.md); the
[ledger](../validation/phase-7c-traceability-ledger.md) tracks its complete scope.
The architectural decision is [ADR 0021](../adr/0021-bounded-supervisor-specialists.md).

The existing LangGraph 1.2.14 graph resolves context, enters one Supervisor stage and retains
the Phase 7A model/tool/grounding loop for final synthesis. Typed provider routing is constrained
by application intent and evidence hints. Recognized factual questions avoid a routing model call
and specialist fan-out. Data Quality gates domain specialists. Measured historical comparisons resolve recorded
capabilities through the same MCP boundary before interpreting those sessions; new quality failures
downgrade the parent report and preserve the warnings. These prerequisite reads count against
the global MCP budget. Findings with source limitations cannot yield an unqualified sufficient report. Performance, Thermal and
Fuel/Air/Boost run as bounded sibling tasks, coordinated only by the Supervisor.

Application code assigns specialist identity, filters the official Phase 6 catalog, enforces
immutable per-specialist allowlists, and validates results using the unchanged Phase 7A grounding
validator. Results retain classification, rendered statement, exact evidence bindings and temporal
configuration references. Model narrative and private reasoning are not public artifacts.

The evidence registry and normalized MCP cache belong to the parent run. A run-local lock serializes
MCP budget reservation, deterministic reads and evidence insertion; independent model waits can
overlap. Result ordering follows the specialist registry order. Evidence aggregation sorts by tool and
normalized selection while preserving canonical row order within each MCP result. Each sibling
receives a frozen shared snapshot plus its own reads; completion order cannot expose sibling input. Parent cancellation
cancels and drains pending siblings and retains completed/cancelled public audit results.
Concurrent runs have independent registries, locks and cache dictionaries.

Specialist defaults are four model turns, six MCP requests, 32 cited evidence items, 16 KiB public
result and 25 seconds. Performance permits eight MCP requests to read three sessions on each
side of a configuration boundary and compare them without weakening Phase 5 history thresholds. Thermal/Fuel allow one telemetry window; other specialists allow none.
The existing parent limits remain authoritative: 16 total turns, 32 MCP calls, one telemetry
window and 90 seconds by default. Domain selection is capped at three and concurrent specialist
tasks at two; Data Quality is a separate gating stage. These are initial configured limits;
benchmark evidence is still required to validate their practical behavior.

Specialist and Supervisor artifacts are bounded additive fields in the existing AgentRun JSON
snapshot. The optional `supervisor` field defaults to absent for historical records. No relational
schema change or new migration is currently needed. Existing API retrieval exposes the artifacts.
New orchestration SSE events use version 1.1; retained legacy events remain version 1.0. Replay
uses the existing sequence cursor and never re-executes specialists. Clients accept both versions.
An event lock serializes sequence allocation and persistence during parallel execution.

Validated competing thermal and fuel/boost events produce a structured conflict, preserving both
interpretations. Insufficiency proposes the existing operator-authorized Phase 7B workflow; it does
not start acquisition. Final synthesis must retain material missing-evidence categories so the
existing `investigable` policy can consume it. Historical runs remain immutable and follow-up uses
a new run over re-materialized MCP evidence. The independent acceptance suite exercises approval, canonical session import/processing, linkage
and a new run with only the relevant specialists. Its acquisition provenance is an explicit
controlled fixture; the existing Phase 7B browser gate separately exercises the real collector path.

Phase 7D owns comprehensive real-model routing, cost, latency and quality evaluation. Phase 8 owns
technical-document retrieval and RAG. This phase introduces neither external knowledge nor vehicle
control. Deterministic validation must use the production graph, real MCP and disposable databases.
