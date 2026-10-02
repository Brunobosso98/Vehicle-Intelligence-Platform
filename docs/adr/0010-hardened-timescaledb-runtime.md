# ADR 0010: Harden the pinned TimescaleDB runtime

## Status

Accepted — 2026-10-02.

## Context

Phase 0 requires PostgreSQL 17 and TimescaleDB 2.30.2. The exact official
`timescale/timescaledb:2.30.2-pg17` image passed database and migration behavior but its bundled
helper binaries failed the zero-Critical container policy. `timescaledb-parallel-copy` embeds a
vulnerable pgx release and is not referenced by application code, startup, migrations, health
checks, tests, or other Phase 0 behavior. The PostgreSQL entrypoint does require `gosu`, whose
official image binary was built with a vulnerable Go standard library. `timescaledb-tune` is retained
but was also built with an older Go toolchain.

## Decision

Build `vehicle-platform-timescaledb:local` from the exact official TimescaleDB 2.30.2 PostgreSQL 17
digest. Remove only the unused `timescaledb-parallel-copy` executable. Rebuild gosu 1.19 from its
checksum-verified source archive and rebuild timescaledb-tune 0.19.0 with a pinned patched Go 1.26.6
builder. Replace those two helper binaries, apply the available targeted libexpat update, and keep
all compilers and source outside the final stage. Run the final database container as the inherited
`postgres` user; the official image prepares the data directory for that UID, while gosu remains
available for compatibility with the inherited entrypoint.

The security gate preserves a machine-readable scan of the unmodified upstream image as
supply-chain evidence and separately enforces High/Critical policy on the hardened image that the
project actually executes. Database behavior remains subject to clean migration, downgrade,
re-upgrade, integration, stack, and E2E validation.

## Alternatives considered

- Suppress or ignore the scanner findings. Rejected because the Critical findings have concrete
  remediations and Phase 0 does not permit blanket suppression.
- Remove gosu. Rejected because the inherited PostgreSQL entrypoint uses it for privilege dropping.
- Change database architecture, PostgreSQL major version, or TimescaleDB version. Rejected as an
  unnecessary compatibility change outside this remediation.
- Rebuild TimescaleDB itself. Rejected because its extension binaries are not the source of the
  three Critical findings.

## Consequences and risks

The project owns a small security overlay and must rebuild it when its pinned Go image, gosu source,
timescaledb-tune source, or TimescaleDB base changes. Source hashes, versions, and base digests must
remain pinned. A build-time functional check verifies gosu privilege dropping and the retained
database executables; canonical CI verifies full behavior and scans the result.

The customization should be removed when an official compatible TimescaleDB 2.30.2 PostgreSQL 17
image no longer ships the vulnerable helpers, but only after equivalent database regression tests
and image security scans pass. Until then, the upstream scan remains visible and is not treated as
the policy result for the remediated runtime.
