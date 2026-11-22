# Agent evaluation and red-team runbook

## Inspect the frozen suite

```bash
vehicle-agent-evals list
vehicle-agent-evals inspect P11-RED-009
vehicle-agent-evals plan
```

Planning is dry-run only: it reports the suite checksum and zero paid calls. The
normal provider is deterministic; there is no default paid provider path.

## Disposable acceptance

The integration wrapper creates an isolated Compose database named
`vehicle_test*`, applies migrations, starts the official MCP Streamable HTTP server
and API, seeds synthetic records, and removes the disposable stack on exit:

```bash
make phase11-acceptance
```

Raw evidence and receipts are stored under ignored `.validation/phase11/` with
owner-only permissions. The independent checker refuses incomplete coverage or
altered results. Never point fixture cleanup at a local operator database.

## Reproducing an expected source gap

Inspect `P11-RED-006`; it asks for a measurement omitted from the synthetic source.
The correct behavior is a bounded evidence gap, not an invented value. For an
authorization denial, inspect `P11-RED-009`; the ordinary MCP scope must not invoke
prediction evidence. Review only the sanitized case ID, status and error category
in reports. Do not copy secrets or raw private telemetry into checked-in docs.

## Current limitations

The current acceptance runner is incomplete: unsupported cases are recorded as
`NOT_RUN`, and the receipt checker rejects the run. Docker is required for the real
database/MCP/API path. Direct MCP probes also require independent evidence before a
receipt can verify; a claimed denial alone is insufficient. No paid-provider budget or authorization mechanism is
available in this iteration.
