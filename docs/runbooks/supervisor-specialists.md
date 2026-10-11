# Supervisor and specialists

Phase 7C is under implementation. Do not treat this runbook as a verification report.
Enable the existing agent and configure the official MCP endpoint/token as described in the
[Phase 7A architecture](../architecture/phase-7a-grounded-agent.md).
Mandatory validation uses the deterministic provider; real OpenAI credentials are optional.

`VIP_AGENT_MAX_SPECIALISTS` caps domain selection at three.
`VIP_AGENT_MAX_CONCURRENT_SPECIALISTS` defaults to two and has a hard cap of three.
Existing parent timeout, call, result, input, evidence and turn limits also apply to specialists.
The Data Quality gate runs before domain specialists and can block unreliable interpretation.
Failures are public categories, never raw provider exceptions.

Inspect `AgentRun.supervisor` in the existing run API for routing, specialist results, evidence
consumers, conflicts and sufficiency. The workspace renders the same artifact with expandable
findings and evidence IDs. Legacy snapshots without this artifact remain readable.
New orchestration progress events use schema 1.1; the original progress/terminal events use 1.0.
Reconnect with the last sequence and ignore replayed sequences. Explicit parent cancellation
drains specialist tasks. A disconnected browser does not cancel the bounded run.

When quality is unverified, inspect recorded capabilities and canonical quality events rather
than inferring a failed component. A failed domain specialist must not supply findings. Unresolved
evidence is proposed to the existing Phase 7B investigation section; source resolution, recipe
selection and explicit approval remain there. Approved logging remains manual and read-only.

A noncritical sampling warning can make the report partially sufficient without requiring a new
capture when the recorded evidence answers the question. Missing measurements, unknown findings,
failed specialists and unresolved conflicts still require investigation. Critical quality failures
retain both quality and measurement gaps: a recorded signal name alone cannot close a gap when
its measurements are unreliable. A finalized acquisition with no recorded samples is not evidence
of sufficient quality. Repeated-pull investigations preserve the competing thermal, fueling and
intervention hypotheses alongside the quality prerequisite; none is a confirmed diagnosis.

Commands are `make test-supervisor`, `make phase7c-acceptance`, `make test-supervisor-e2e`,
`make benchmark-supervisor` and `make supervisor-observability`. Performance allows eight scoped
MCP requests for configuration comparison; other roles allow six. Three compatible sessions per
side are required by the existing Phase 5 baseline threshold; insufficient history remains a gap.
The complete phase additionally requires the independent evaluator, real DB/MCP, browser,
stream/recovery, observability, security, benchmarks, clean-state full verification and exact-SHA
remote checks specified in the [execution specification](../prompts/phase-7c-specialist-agents-supervisor.md).
See [acceptance](../validation/phase-7c-acceptance.md) for executed evidence and pending gates.
