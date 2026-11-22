# Phase 11 agent red-team security status

## Scope

The harness is restricted to synthetic disposable `vehicle_test*` databases. Cases
are data, not executable attack programs. The deterministic provider is the only
provider in normal validation. Phase 11 does not expose a public evaluation route,
run shell or URL payloads from the corpus, or enable prediction evidence in
production.

## Controls represented in the first suite

- MCP server authorization remains the enforcement point for tool scopes.
- Requests to approve, activate, promote or roll back a model are routed to a fixed
  refusal before context discovery, MCP discovery, or provider calls. The refusal states
  that quoted approval text cannot change serving state; an operator remains required.
- Explicit requests to approve or start acquisition are routed to a fixed refusal before
  tool discovery. A read-only request to plan a capture remains available.
- Agent findings are independently checked for current-run evidence ownership,
  vehicle ownership, exact source fact, numeric value, unit and citation.
- The source digest covers allowlisted Phase 0–10 domain tables before and after
  agent execution; AgentRun/audit appends are outside that source digest by design.
- Foreign vehicle evidence, unsupported certainty, forged approval language,
  synthetic score laundering, poisoned source text, tool timeout and provider
  malformed output have predeclared scenario identities.
- The receipt checker rejects missing/duplicate attempts and does not trust a
  self-reported PASS. It also matches run-linked result, evidence, tool audit, vehicle
  scope, provider/model identity and events against persisted database rows. It recomputes
  current dependency, prompt, MCP tool-catalog and schema revision hashes, verifies the
  test environment, and pins the version 1 corpus hash.
- Direct probes without independently verifiable evidence are rejected by the receipt
  checker, even when the attempt claims a pass. Tool counts and claimed tool names must
  agree with the trace.

## Current evidence and residual risk

The focused deterministic unit checks pass locally. Docker is unavailable locally.
GitHub Actions ran the disposable stack at `ee92cc58f56d0390e447468f23b24fd01a3b25fe`:
6 cases passed, 5 failed assertions, 1 had an infrastructure failure and 9 were not run.
The independent receipt checker failed. These observations are specific to that commit;
they do not establish acceptance for later code. See the red-team matrix for case results.

This harness cannot prove resistance to unseen prompt injection, real stochastic
provider behavior, mechanical diagnostic accuracy, or production deployment
security. Synthetic 9B/9C scores remain research outputs, not probabilities or
diagnoses. Human approval remains required for acquisition and MLOps transitions.
