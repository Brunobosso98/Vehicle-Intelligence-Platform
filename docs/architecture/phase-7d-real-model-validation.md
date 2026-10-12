# Phase 7D real-model validation

Status: implementation in progress; real evaluation NOT RUN. The authoritative scope is
[the complete execution specification](../prompts/phase-7d-real-model-validation.md).
[ADR 0022](../adr/0022-bounded-real-model-evaluation.md) records evaluation ownership and accounting.

`evals/phase7d/suite-v1.json` contains exactly 80 unique questions, ten per category A–H.
The specified 20 critical questions receive two additional observations. The loader rejects
identity, category, duplicate-question, specialist-partition and repeat-count inconsistencies.
Questions and expected behavior come from the specification and controlled canonical fixtures,
not model-generated answers. Dataset changes require a new version and renewed review.

`scripts/phase7d_eval.py` owns explicit paid execution. It exercises production API routes via
ASGI HTTP, a separate actual HTTP MCP server, disposable PostgreSQL persistence, the existing
LangGraph supervisor and the existing Phase 7B service. Controlled recordings use canonical
import, pull analytics and event analysis. Replay capabilities come from actual CSV content.
The evaluator never approves a recipe or starts acquisition. Domain fingerprints detect changes
to canonical vehicle data after evaluation. Provider output is graded independently of production
validators using numeric/unit bindings, evidence ownership, routes, gaps, capabilities and audits.

The existing `OpenAIProvider` sends explicit service tier/reasoning settings and `store=false`.
Its SDK retries remain disabled. Optional internal receipts measure routing, specialists,
synthesis and investigation calls, including usage from malformed structured output. Public API
and SSE schemas remain unchanged. Reasoning token counts are usage metadata only; reasoning
content is neither requested nor stored.

The checkpoint reserves estimated cost before each network call. Completed response usage
replaces the reservation. Timeouts, transport failures, missing usage and interruptions retain a
conservative bound. An exclusive file lock serializes operator invocations. Completed paid cases
are not rerun on resume; interrupted cases remain explicitly incomplete. SHA, dataset hash, prompt
versions, SDK, model, tier, reasoning and limits must match. Confirmation is limited to a second
suite and shares accumulated spend. See the runbook for crash and provider-blocker handling.

The output report includes category/role usage, costs, routing/recall, tool efficiency, grounding,
causal/diagnostic restraint, missing evidence, Phase 7B escalation, stability, latency quantiles,
provider failures and a maximum twenty-slot human-review shortlist. Missing observations produce
null metrics and NOT VERIFIED. Real-evaluation success is separate from final repository/remote
acceptance. Production profile calibration remains pending real observations.

Phase 8 owns documentary gaps and retrieval. Phase 7D adds no RAG, vehicle control or ECU writes.
