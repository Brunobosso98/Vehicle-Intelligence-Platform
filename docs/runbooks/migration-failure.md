# Migration failure

Inspect migrate logs and `docker compose run --rm migrate alembic current`.
Confirm the installed PostgreSQL build actually contains TimescaleDB and extension-create privileges.
Migration 0001 uses CREATE EXTENSION IF NOT EXISTS under Alembic transactions, creates no telemetry.
Do not edit or stamp an applied revision to hide an error. Reproduce in `make test-integration` first.
Foundation downgrade rolls back revision metadata but preserves the extension to avoid future data loss.
Re-upgrade is tested. Future destructive changes require backup/restore and explicit rollout review.
