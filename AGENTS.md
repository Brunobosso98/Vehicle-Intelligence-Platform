# Vehicle Intelligence Platform / N55 Intelligence Lab

Phase 0 is an engineering foundation; Phase 1 telemetry is not implemented.

- Canonical commands: `make bootstrap`, `make check-api`, `make check-web`, `make contracts-check`, `make verify`.
- Observe and analyze only. Never control brakes, steering, throttle, flash or write the ECU.
- Preserve explicit module boundaries. Add dependencies only for a concrete need; pin and lock them.
- Version every schema change through Alembic; never edit an applied revision. Review data/lock risks.
- Significant lasting decisions need a numbered ADR; trivial implementation choices do not.
- Completion requires relevant typing, tests, error handling, security and documentation. Never claim checks passed without execution; report blocked checks and evidence.
  Read relevant context only: docs/architecture for boundaries, docs/testing for tests,
  docs/security for sensitive changes, docs/observability for instrumentation, docs/adr for decisions.
  Use local skills when their specific triggers apply. Do not implement future infrastructure speculatively.
