# ADR 0051: Independent deterministic agent evaluation

- Status: accepted
- Date: 2026-11-22

## Context

The existing agent has separate authorization, LangGraph orchestration, run-local
grounding and persistence boundaries. Reusing its grounding validator to generate
expected results would let the implementation under test grade itself. Historical
Phase 7D provider runs also span multiple source revisions and cannot be treated as
one final-SHA cohort.

## Decision

Phase 11 uses a frozen, versioned scenario corpus and derives expected source facts
from canonical rows in a disposable database. A separate deterministic grader checks
the persisted run's source ownership, exact fact path/value/unit, citation, expected
behavior and forbidden tools. It emits an append-only SHA-bound receipt and a checker
recomputes statuses from the frozen corpus. Normal CI uses the deterministic provider
and no paid calls. Phase 7D historical observations remain distinct from Phase 11
engineering outcomes.

The evaluator uses existing MCP server authorization and LangGraph paths. Test
fixtures cannot grant capabilities and do not create any production-facing route.
No migration is justified for versioned local receipts; Phase 0–10 source tables are
not modified by the runner.

## Consequences

This makes deterministic engineering checks repeatable and prevents the production
validator from serving as the sole oracle. It does not establish stochastic provider
reliability, resistance to unseen attacks, or mechanical diagnostic validity. Full
verification requires real disposable database execution and exact-SHA CI evidence.
