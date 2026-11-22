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

The first suite version contains 21 authored cases across benign, critical, red-team,
metamorphic, fault-injection and provider-compatibility families. The disposable
HTTP runner currently executes the supported factual, event, injection and refusal/
scope probes; it reports all other manifest cases as `NOT_RUN`. The Phase 11 gate is
therefore incomplete until every mandatory path has real execution and independent
evidence. See the acceptance and traceability ledgers for current status.
