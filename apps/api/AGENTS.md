# API

Keep HTTP contracts/routes, configuration, infrastructure and observability separate.
Use async I/O and typed signatures; do not block the event loop. Mypy strict and Ruff are mandatory.
SQLAlchemy sessions/connections must have bounded lifetimes. Migration scripts live in migrations/.
Liveness never touches dependencies. Readiness is bounded and validates required extension availability.
Never log connection URLs, input bodies, SQL parameters or exception strings containing secrets.
Return the ErrorResponse contract with request ID; keep internal failure classifications meaningful.
Run `make check-api`; add real integration tests for database changes (`make test-integration`).
Export and check contracts when HTTP models change. Avoid empty domain scaffolding.
