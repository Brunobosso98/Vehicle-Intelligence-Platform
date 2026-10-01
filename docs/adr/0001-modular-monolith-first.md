# ADR 0001: Modular monolith first

## Status

Accepted — 2026-10-01.

## Context

Future capabilities need boundaries but have no independent workloads yet.

## Decision

Build a modular FastAPI core with separate web runtime; extract only on demonstrated need.

## Alternatives considered

Empty microservices; a single unstructured application.

## Consequences

Less operational overhead; module discipline is essential. Extraction and streaming choices require future evidence.
