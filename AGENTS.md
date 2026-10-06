# Vehicle Intelligence Platform / N55 Intelligence Lab

Phases 0–4 passed canonical full-stack validation. Phase 5 deterministic automotive analytics is current; diagnosis and Phase 6+ infrastructure are not implemented.

- Canonical commands: `make bootstrap`, `make check-api`, `make check-web`, `make contracts-check`, `make verify`.
- Docker is not guaranteed in Codex Cloud. Detect it first; without it run `make verify-cloud` and
  report every Docker-dependent check as `CI REQUIRED`, never PASS or silently skipped. GitHub
  Actions `full-validation` is the canonical Docker/full-stack executor. See `docs/testing/strategy.md`.
- Observe and analyze only. Never control brakes, steering, throttle, flash or write the ECU.
- Preserve explicit module boundaries. Add dependencies only for a concrete need; pin and lock them.
- Version every schema change through Alembic; never edit an applied revision. Review data/lock risks.
- Significant lasting decisions need a numbered ADR; trivial implementation choices do not.
- Completion requires relevant typing, tests, error handling, security and documentation. Never claim checks passed without execution; report blocked checks and evidence.
  Read relevant context only: docs/architecture for boundaries, docs/testing for tests,
  docs/security for sensitive changes, docs/observability for instrumentation, docs/adr for decisions.
  Use local skills when their specific triggers apply. Do not implement future infrastructure speculatively.

Event-detector changes require a positive synthetic case, a negative/false-positive case, ground-truth evaluation where applicable, version/configuration-hash review, documentation, and disposable-database integration validation. Anomaly detection is not diagnosis.

Stream-contract changes require explicit schema versioning, backward-compatibility review, replay/idempotency tests, and documentation. Logging-recipe changes require rationale and availability for every signal, defined degraded behavior, a deterministic synthetic test, version/configuration-hash review, and documentation.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
