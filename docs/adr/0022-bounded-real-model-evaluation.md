# ADR 0022: Bounded real-model evaluation and durable spend accounting

## Status

Accepted for Phase 7D harness implementation. Real-model reliability remains unverified until
mandatory evaluation and deterministic gates pass. Extends ADRs 0019–0021.

## Context

The Phase 7D specification requires 80 versioned questions, 40 critical repeats, a USD 2 default
budget, a USD 5 ceiling, safe resume and no paid calls in ordinary CI. A provider timeout may
still be billable. Process-local counters alone cannot preserve the budget through a crash.

## Decision

Keep evaluation outside the production request workflow. Explicit operator commands exercise the
production API routes, grounded supervisor, HTTP MCP, canonical disposable recordings and existing
Phase 7B investigation service. Use controlled replay source capabilities and preserve approval.
No production acquisition, new agent framework, RAG, relational schema or stream schema is added.

Add an optional internal response observer to the existing OpenAI Responses adapter. It receives
roles, request byte counts, public tool names, usage counters and response model/tier only.
It never receives credentials, HTTP headers, prompts or internal reasoning content. Record usage
before validating public JSON, so malformed answers are still charged.

An exclusively locked operator checkpoint atomically reserves the conservative per-call cost
before network I/O. Reported usage replaces that reservation; missing usage keeps the bound.
Completed cases are immutable within a suite. Interrupted cases are marked explicitly and are
never automatically replayed. One initial suite and at most one confirmation suite share the
same spend ledger. Manual deletion of operator artifacts invalidates this accounting history.

## Alternatives

A process-only budget loses crash evidence. Re-running completed cases wastes money and biases
results. A paid judge for every answer increases spend and introduces another uncertain output.
A second investigation implementation would duplicate existing capability/planner/approval policy.
Default CI execution with a real key would spend money on every push.

## Consequences and risks

Conservative reservations can stop earlier than provider billing would. Estimates remain distinct
from billing truth. Unknown or interrupted usage and incomplete repeats prevent verification.
Model quality and realistic latency require real calls; deterministic tests cannot establish them.
The operator must retain checkpoints and use a dedicated provider project/key with a separate
provider-side USD 5 limit. Pricing must be reverified against official documentation before use.

## Evidence-driven hardening

Two partial real attempts exposed local stream/database failure and model quality-gap tags overriding verified quality metadata. The implementation now keeps quality blocking application-owned, preserves durable interrupted run handles, and permits one read-only reconnect to the same run. Role task instructions are versioned v2; factual measurements remain usable when causes are unresolved.

Specification sections 95–96 permit an explicit operator request beyond two automatic schedules. The default limit stays two; a separately confirmed exception admits each operator-authorized additional bounded schedule with shared spend. This exception requires operator approval and is never a default CI or automatic tuning action.

Operator authorization on 2026-10-12 permits the additional rounds needed to finish validation while retaining a strict accumulated USD 2 ceiling. The default two-round limit remains for callers without explicit operator confirmation. Each invocation is bounded; no automatic evaluate/tune loop or model/tier fallback is added. Resume omits round-start flags and preserves all prior observations and cost reservations.

Round three completed all 120 attempts but missed quality thresholds. Confirmed defects prompted strict normalized Draft/investigation output, general routing focus fixes and consistent v3 prompt metadata. Report version 1.1 preserves deserialization of 1.0/v1/v2 snapshots; durable SSE sequencing is unchanged. Full final-candidate acceptance is still required.

Affected-case schedules implement specification section 95 without changing dataset questions or expectations. Case IDs belong to the immutable suite, selected critical repeats remain scheduled, selection is part of resume identity, and all calls share the original spend ledger. Their partial scope can never satisfy the full-suite gate. Explicit resume of never-attempted external-blocker markers preserves their history and rejects any marker that already has paid receipts.

The affected-case round exposed comparison before registered pull discovery and dropped routing context for zero-domain results. Bounded metadata discovery uses existing module ownership and quotas; it supplies IDs, not answers. Synthesis receives typed routing/quality context for every supervisor result. Role failures remain isolated and unknown/foreign pull IDs remain denied. Performance v4 and discovery configuration participate in the report hash; cumulative spending and full final-candidate acceptance requirements are unchanged.

## Operator instruction to continue within the hard ceiling

The operator subsequently requested necessary attempts to continue until persistent errors and the accumulated USD 2 limit stop them. Explicit `--operator-budget-progress` can admit a bounded schedule despite a conservative projection exceeding the remaining balance. Default callers still stop at projected-cost admission. The forecast and opt-in remain recorded; immutable invocation identity requires the same choice on resume. Per-call worst-case reservations, existing unknown usage, USD 2 spending, fixed case/request caps and model/tier remain enforced. This can produce incomplete budget-skipped acceptance, never a VERIFIED result from partial coverage.

Round-ten affected validation passed eleven of twelve observations; rejected configuration-related tools and failed grounding remain failures. Discovery strategy 1.1 improves the bounded owned metadata selection for setup comparisons by representing both recorded configurations when possible. Its version enters the supervisor configuration hash; role/global quotas and temporal/vehicle permissions are retained. General routing distinguishes recorded data reliability from source availability and domain mechanical reliability, preserving recorded-count lookup and refusing forced unbounded consensus. No dataset expectation or real observation is changed.
