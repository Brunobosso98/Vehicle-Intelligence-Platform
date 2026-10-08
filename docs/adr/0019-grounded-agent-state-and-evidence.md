# ADR 0019: Grounded agent state and evidence

## Status

Accepted for Phase 7A implementation. Extends [ADR 0018](0018-read-only-mcp-adapter.md).

## Context

The Phase 7A specification requires natural-language orchestration through MCP, durable run
audit, explicit vehicle configuration timing, and enforceable claim support. Model prose alone
cannot establish numeric correctness, ownership or causation. Existing configuration and
modification records already represent effective/end and installation/removal intervals.

## Decision

Use LangGraph 1.2.14 with a typed application execution state. One graph resolves context,
requests a provider turn, executes permitted MCP tools, and validates structured findings.
No checkpoint service or provider thread is the canonical record. PostgreSQL agent-owned
tables persist public results, concise tool audits and bounded replayable SSE events.
Agent persistence uses per-session connections without reuse and a driver termination watchdog. A plain coroutine timeout
did not bound cancellation cleanup while the disposable PostgreSQL process was paused. Only the
owned connection is aborted after the session deadline; vehicle transactions use the existing pool.

Use the official OpenAI Python SDK 3.26.0 Responses API behind a provider protocol. Model and
credential are operator configuration. A deterministic provider exercises the same graph,
MCP boundary and validator without paid calls. LangGraph and OpenAI metadata declare
`Python >=3.10`; the project installs them in its Python 3.12 locked environment. References:
[LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview),
[OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling),
[Responses streaming](https://developers.openai.com/api/docs/guides/streaming-responses).

Vehicle reads use the official MCP client exclusively. Add a backward-compatible bounded
configuration-list tool to resolve active and historical intervals; keep envelope version 1.0
and advertise server version 1.1.0. No vehicle-domain schema migration is needed.

The model selects fixed public finding templates and exact evidence bindings. The validator
checks run and vehicle ownership, paths, values, units and classification requirements. The
application renders prose after validation. No arbitrary model narrative, private reasoning,
diagnosis or causal conclusion enters the published answer. API streaming publishes useful
execution progress followed by validated answer chunks, with durable replay and retrieval.

## Alternatives

A handwritten state machine has fewer dependencies but needs its own graph transition and
termination implementation. Direct application calls bypass the required MCP boundary.
Prompt-only citations cannot enforce evidence ownership or numeric correspondence. Publishing
unvalidated model tokens risks exposing unsupported assertions before validation completes.

## Consequences and risks

Template-based answers trade narrative flexibility for enforceable factual support. More public
templates can be added with independent tests. LangGraph adds transitive packages that must
pass existing dependency scanning. Provider latency and model reliability require optional
credentialed smoke checks; deterministic CI does not prove either. API concurrency is bounded
per process; the initial deployment supports one API worker and no distributed execution.
Database rollback removes only agent-owned audit tables and is destructive to those records;
operators preserve audit data before any production rollback. Phase 7B/7C/8 remain deferred.
