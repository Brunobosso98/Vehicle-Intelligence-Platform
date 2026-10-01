# ADR 0009: Runtime base security and cloud validation

## Status

Accepted — 2026-10-01.

## Context

Docker Hub anonymous pulls were rate-limited in the execution environment. A verified official
GHCR Python/uv mirror is available. The older Bookworm mirror reported Critical OS findings.

## Decision

Use the verified official Python 3.12.14 Trixie GHCR digest for API and apply available runtime
OS updates. Use official Node 24.19.0 Trixie for the canonical web image. An optional validation
workflow compiles pinned official PostgreSQL/Timescale sources and uses the checksum-verified
Node distribution on that same Trixie base when Docker Hub is unavailable.

## Alternatives considered

Leaving known Critical findings in the Bookworm base; silently ignoring scanner output;
embedding registry credentials; weakening TLS; stopping database validation at the first pull failure.

## Consequences

The source-built database verifies behavior but does not establish equivalence to the upstream
Timescale image. Canonical Node/Timescale image pulls remain a separate acceptance check.
Runtime apt security updates make the OS layer date-dependent; rebuild and scan regularly.
No finding is silently excluded. High findings without distro fixes remain blocking unless a
finding-specific reviewed exception is explicitly documented. No such exception is accepted here.
