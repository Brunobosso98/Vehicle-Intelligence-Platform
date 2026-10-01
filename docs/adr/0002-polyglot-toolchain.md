# ADR 0002: Polyglot toolchain

## Status

Accepted — 2026-10-01.

## Context

Web and scientific/automotive analysis have different ecosystems.

## Decision

Next.js/React/strict TS/pnpm for web; FastAPI/Pydantic/SQLAlchemy async/uv for API. Use Mypy strict: mature SQLAlchemy/Pydantic support and deterministic CI; Ruff for lint/format.

## Alternatives considered

All-Python web; all-TypeScript analytics; Pyright instead of Mypy.

## Consequences

Two toolchains are an intentional maintenance cost. Locks and generated contracts reduce interface drift.
