# ADR 0004: OpenTelemetry observability

## Status

Accepted — 2026-10-01.

## Context

Requests need portable traces, metrics and correlated logs.

## Decision

OTel SDK with bounded async OTLP export, OTel Prometheus reader, structured stdout JSON. Optional Collector/Tempo/Prometheus/Grafana profile.

## Alternatives considered

Vendor-specific SDK; always-on large observability stack; Loki immediately.

## Consequences

Local profile adds memory use. JSON stdout avoids unused log infrastructure. OTel contrib distributions retain 0.x beta numbering; this is an explicit ecosystem exception: use released canonical instrumentation/exporter pinned alongside stable core, isolate APIs, and validate with tests. No application beta/RC framework is selected.
