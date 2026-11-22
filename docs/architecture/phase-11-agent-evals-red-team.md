# Phase 11 — Agent Evals / Red Team architecture

Phase 11 evaluates the existing read-only agent system. It adds no agent endpoint,
production capability, data acquisition path, model-serving path, or vehicle control.

## Data flow

```text
versioned static case manifest
  -> disposable vehicle_test database and synthetic source records
  -> real API AgentService -> existing LangGraph Supervisor/specialists
  -> official MCP Streamable HTTP server -> current server-side authorization
  -> persisted AgentRun, tool audit, run-local EvidenceRegistry and SSE events
  -> independent source snapshot + exact fact/unit/citation grader
  -> append-only, SHA-bound JSON receipt -> independent receipt checker
```

The actual HTTP acceptance starts the API and MCP processes using the existing
`scripts/agent_runtime.py`. The API uses the existing deterministic provider. The
source oracle reads canonical Phase 0–10 rows directly from the disposable database;
it does not call agent grounding validation to construct expected facts. All SQL
identifiers used by source snapshots are a fixed allowlist. The database name must
start with `vehicle_test` before the source oracle will connect.

## Trust boundaries

Case JSON is immutable, typed, size bounded and contains inert adversarial text only.
The evaluation fixture does not grant a tool or production privilege. Tool calls go
through existing MCP authorization. The grader checks each claim binding against the
run's own evidence rows, checking evidence UUID, run, selected vehicle, fact path,
value and unit. Expected source values are sourced independently from canonical DB
rows. No hidden reasoning is requested or stored.

Receipts include the repository SHA, canonical suite checksum, source fixture digest,
provider identity, paid-call count, and every case attempt. The verifier checks
coverage, unique IDs, suite/SHA match, receipt checksum, paid-call count, and
recomputes the structured grade. A receipt with omitted cases, altered findings,
falsified status, or wrong source ownership is rejected. The checksum is an
integrity check, not a signature or proof against an attacker able to rewrite every
artifact and trusted input.

## Provider modes and limits

Normal validation is deterministic and makes zero paid calls. No paid-provider
execution command is exposed by this iteration. The harness never requests hidden
reasoning. Phase 7D's 120 historical slots remain a separate mixed-round record;
they do not establish uniform final-SHA provider reliability. Real-world mechanical
predictive validity remains `NOT_ESTABLISHED`.

## Current implementation boundary

The current frozen suite is `phase11-agent-evals-v18` (`evals/phase11/suite-v14.json`),
with 24 authored cases across benign, critical, red-team, metamorphic, fault-injection
and provider-compatibility families. The disposable runner executes this bounded suite
through the API/LangGraph/MCP stack and direct authorization/provider probes; prior
exact-SHA runs passed the earlier 21-case suites. V8 adds independently checked isolation
between distinct BMW N55 and Toyota B58 vehicles with separate configurations. V9 adds
an explicitly graded unsafe-operation refusal case. V10 adds an actual Phase 7C ambiguous
multi-cause run and grades its persisted specialist conflict and uncertainty handling. V11
adds an actual two-session temporal lookup with independent newest-two ordering. V12 adds
run-foreign evidence citation injection. V13 corrects the approval-spoof cases' source
surface to the actual user prompt and states that poisoned approval documents are not yet covered.
V14 exercises a real `get_vehicle` MCP result whose typed nickname contains inert instruction-like
text. V15 injects a provider unit conflict against a numeric source fact and requires the grounding
correction path to abstain. V16 changes a canonical nickname between two API runs and verifies that
the second answer follows the changed value before restoring the disposable fixture. These changes
have not run on an exact SHA. V17 makes the future-pull and synthetic-score cases explicit user-prompt
attacks; it does not claim that this runner seeds 9B/9E evidence for them. V18 ensures the unit-fault
case performs a real latest-session MCP read before injecting its invalid binding.
This still does not cover every mandatory pathway in the
155-requirement specification. Phase 11 remains incomplete until the broader source,
specialist, lifecycle, adversarial, multi-vehicle and reliability matrices have real
execution and independent evidence. See the acceptance and traceability ledgers for
current status.
