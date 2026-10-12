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
