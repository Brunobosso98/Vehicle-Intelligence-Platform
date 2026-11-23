# Phase 11 agent red-team security status

## Scope

The harness is restricted to synthetic disposable `vehicle_test*` databases. Cases
are data, not executable attack programs. The deterministic provider is the only
provider in normal validation. Phase 11 does not expose a public evaluation route,
run shell or URL payloads from the corpus, or enable prediction evidence in
production.

## Controls represented in the current suite

- MCP server authorization remains the enforcement point for tool scopes.
- Requests to approve, activate, promote or roll back a model are routed to a fixed
  refusal before context discovery, MCP discovery, or provider calls. The refusal states
  that quoted approval text cannot change serving state; an operator remains required.
- Direct ECU flash/program/write requests also take the fixed refusal path before MCP
  discovery and emit an `unsafe_operation_refused` finding.
- The fixed refusal router checks short, strictly valid Base64 tokens in the bounded
  user prompt for the same ECU write intent. It does not execute decoded content or pass it
  to a tool. The frozen Phase 11 corpus contains a positive encoded-command case and a
  benign encoded-prose negative control.
- Explicit requests to approve or start acquisition are routed to a fixed refusal before
  tool discovery. A read-only request to plan a capture remains available.
- Agent findings are independently checked for current-run evidence ownership,
  vehicle ownership, exact source fact, numeric value, unit and citation.
- Before each attempt is journaled, configured credential values are scanned recursively across
  the complete attempt record, including probe summaries, attack attribution and resolved facts. A
  match is redacted, the attempt is marked as a failed secret disclosure, and raw answer/evidence
  payloads are removed. The private journal is append-only and hash-chained; its digest is bound
  to schema 1.1 receipts. This is a deterministic harness safeguard; it does not replace
  application log redaction or external telemetry review.
- `get_vehicle` may expose its bounded vehicle nickname as an exact `/nickname` fact
  when a factual lookup requests it. The nickname remains untrusted data, never policy;
  free-text notes and metadata stay excluded from claim bindings.
- The source digest covers allowlisted Phase 0–10 domain tables before and after
  agent execution; AgentRun/audit appends are outside that source digest by design.
- Foreign vehicle evidence, unsupported certainty, forged approval language,
  synthetic score laundering, poisoned source text, tool timeout and provider
  malformed output have predeclared scenario identities.
- The receipt checker rejects missing/duplicate attempts and does not trust a
  self-reported PASS. It also matches run-linked result, evidence, tool audit, vehicle
  scope, provider/model identity and events against persisted database rows. It recomputes
  current dependency, prompt, MCP tool-catalog and schema revision hashes, verifies the
  test environment, and accepts only a registered immutable suite version and hash.
- Direct probes without independently verifiable evidence are rejected by the receipt
  checker, even when the attempt claims a pass. Tool counts and claimed tool names must
  agree with the trace.
- The approval-spoof scenario creates a real synthetic Phase 7B investigation plan,
  verifies `AWAITING_APPROVAL` and `PENDING` from persisted plan/event rows, attempts the
  approval route without an operator token, and checks that no acquisition session was added.
  The controlled plan is created before the source-digest baseline; the attack run then confirms
  that it did not change.
  The independent receipt checker rereads the plan and event history from the disposable DB.
- The prediction-evidence scenario uses a Phase 9E accepted synthetic bundle and a read-only
  oracle over the immutable bundle facts. A source-role mismatch found during unit validation
  was corrected; the combined 9E-to-9F Docker path has not yet run on this worktree.
- Immediately before deterministic agent evaluation, `scripts/phase11-validation.sh` installs
  dedicated IPv4 and IPv6 OUTPUT chains that allow loopback and reject all other host egress.
  The exit trap removes both chains before Compose teardown and artifact upload, including on
  failure. The CI runner must provide `iptables`, `ip6tables`, and root or non-interactive sudo;
  the acceptance fails closed if the fence cannot be installed. Local execution cannot verify
  this firewall because Docker is unavailable in this environment.

## Current evidence and residual risk

Synthetic fixture mutations are limited to eleven typed operators in
`vehicle_platform.agent_evaluation.mutations`: low-trust text injection, document-version swap,
tool-result error, vehicle rekey, fact reorder, future-sample insertion, capability revocation,
bounded tool delay, source-role tampering, checksum corruption, and unit distortion. The
low-trust text, source-role, and token-revocation operators now drive real RAG, Phase 9F/MCP,
and MCP authorization probes in the disposable runner. Each binds seed, mutation version,
precondition, expected defense and fixture hashes to the receipt, with independent checks for the
RAG and revocation provenance. The remaining eight operators are currently unit-only. All are
data-only transformations; they do not execute shell, SQL, arbitrary URLs, or local paths. Unit
coverage does not count as proof that the wired mutations survive the real API/MCP boundary, and
disposable integration remains required.

The `vehicle-agent-evals observability` command exports finite family/status and attack-family
metrics plus tool-schema, MCP-authorization, and grounding outcomes (`blocked`, `not_blocked`, or
`unmeasured`). Labels come from the frozen corpus and enums; vehicle IDs, case IDs, prompts,
documents, receipt IDs, secrets and answer text are not labels. Unit tests exercise all three
outcomes and confirm unmeasured controls remain explicit.

An earlier focused run passed 150 evaluator and mutation tests, Ruff, and strict Mypy on the
affected modules. A later local update now passes 189 focused evaluator, mutation, attribution,
journal, threshold and runtime-resource tests; changed files pass Ruff and strict Mypy. Docker is
unavailable locally.
GitHub Actions ran the disposable stack at `ee92cc58f56d0390e447468f23b24fd01a3b25fe`:
6 cases passed, 5 failed assertions, 1 had an infrastructure failure and 9 were not run.
The independent receipt checker failed. These observations are specific to that commit;
they do not establish acceptance for later code. See the red-team matrix for case results.

This harness cannot prove resistance to unseen prompt injection, real stochastic
provider behavior, mechanical diagnostic accuracy, or production deployment
security. Synthetic 9B/9C scores remain research outputs, not probabilities or
diagnoses. Human approval remains required for acquisition and MLOps transitions.
