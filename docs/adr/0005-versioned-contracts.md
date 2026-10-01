# ADR 0005: Generated versioned contracts

## Status

Accepted — 2026-10-01.

## Context

Web must not copy API models manually.

## Decision

Pydantic is the source; checked OpenAPI snapshot and generated TypeScript with drift gate. SemVer app, future /api/v1 domain routes and event .v1 suffixes.

## Alternatives considered

Hand-written shared interfaces; full generated runtime client.

## Consequences

Compile-time types do not validate network inputs; boundary runtime checks remain required. Breaking changes need reviewed transitions.
