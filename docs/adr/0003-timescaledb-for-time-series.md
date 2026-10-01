# ADR 0003: TimescaleDB foundation

## Status

Accepted — 2026-10-01.

## Context

Future telemetry is relational time-series; Phase 0 has no samples.

## Decision

PostgreSQL 17 + TimescaleDB, activated by Alembic; no telemetry tables. Preserve extension on foundation downgrade.

## Alternatives considered

Plain PostgreSQL only; specialized non-relational time-series database.

## Consequences

Extension deployment is an operational dependency. Hypertables and throughput claims wait for Phase 1 data.
