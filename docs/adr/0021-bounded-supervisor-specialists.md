# ADR 0021: Bounded supervisor and specialist analysis

## Status

Accepted for Phase 7C implementation. Extends [ADR 0019](0019-grounded-agent-state-and-evidence.md)
and [ADR 0020](0020-investigation-recipe-and-approval-boundary.md).

## Context

Phase 7C requires selective engineering analysis, quality gating and explicit conflicts. The
existing LangGraph orchestrator, MCP client, run-scoped evidence registry, structural grounding
and operator-approved investigation workflow already own their respective boundaries.

## Decision

Keep one supervisor in the existing agent execution owner. Specialists are bounded analyzers
with application-assigned identities, versioned policies, typed requests and results, and
immutable MCP allowlists. Route using typed provider intent constrained by deterministic question
and evidence hints. Simple factual requests retain the Phase 7A path without specialist execution.

Run Data Quality as a gate for telemetry interpretation. Independent domain specialists may
execute as siblings under bounded concurrency after that gate. All coordination stays in the
supervisor. No specialist conversation, recursive debate or independent vehicle-data access is
introduced. Validate specialist claims with the Phase 7A validator before aggregation and validate
final synthesis again. Render public statements using application templates.

Use a current-run shared evidence registry and normalized MCP call identities. Code enforces
specialist and parent budgets before calls, including cached requests. Publish bounded public
routing, results, conflicts and sufficiency in the existing agent snapshots and replay stream.
Preserve historical JSON snapshots with optional additive orchestration fields; no relational
table change is proposed. If relational schema changes become necessary, use a new migration.

Represent competing supported mechanisms explicitly rather than choosing a cause. Insufficient
or unreliable evidence proposes the existing Phase 7B path; its approval, acquisition and new-run
reanalysis invariants remain authoritative. Technical documentation remains a Phase 8 gap.

## Alternatives

Independent chatbots would duplicate evidence and allow conversation amplification. A new graph
platform or investigation service would replace working boundaries without a concrete need.
Prompt-only permissions cannot prevent tool escalation. Running every specialist would increase
latency and calls even for factual lookups. Publishing model prose would weaken numeric grounding.

## Consequences and risks

Specialist scopes and fixed public templates limit interpretation to supported platform evidence.
Parallel calls require deterministic evidence merging, atomic budget reservations, and cancellation
tests. Cache state must belong to one run and vehicle. Snapshot growth needs explicit bounds.
Concurrency remains local to the existing single worker; distributed scheduling is outside scope.
Deterministic validation proves policy and fixture behavior, not real-model quality, latency or
cost. Comprehensive real-provider evaluation remains Phase 7D. No measured performance claim is
made by this decision; acceptance, integration and benchmark evidence must be gathered separately.
