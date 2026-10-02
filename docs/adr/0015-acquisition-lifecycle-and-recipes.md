# ADR 0015: Versioned recipes and acquisition lifecycle

Status: accepted for Phase 4

## Decision

A dedicated collector owns read-only device connection, discovery, scheduling, quality measurement, buffering, and reconnect. The API owns expiring session-scoped credentials and lifecycle state. `LoggingRecipe` is immutable and versioned; its deterministic configuration hash captures all semantics. Known objective keys map deterministically to recipes. Arbitrary language interpretation is deferred.

Preflight separates requested canonical information from adapter PID mappings and reports `ready`, `degraded`, or `blocked`. The priority-aware sampling planner protects required signals under an explicit request budget. Post-log capability assessment uses actual rates, gaps, duration, and completeness—not requested rates and never a health score.

Live segmentation/events reuse Phase 2/3 semantics and are explicitly provisional. Stop/finalize persists remaining observations, runs canonical Phase 2 then Phase 3, and reconciles by stable evidence. Provisional badges never appear as canonical conclusions.

The browser receives one-second Server-Sent Event snapshots with a hard ten-minute connection bound and a 200-point/60-second presentation window. SSE is one-way, automatically reconnectable, works through the existing same-origin proxy boundary, and avoids a bidirectional command surface. The worker performs bounded 2,000-observation micro-batches rather than re-running full-session analysis. This intentionally trades sub-second latency for bounded CPU and deterministic reuse of the Phase 2 detectors.

## Consequences

Recipe meaning cannot be silently changed: edits require a new version/hash, rationale, degraded behavior, deterministic tests, and docs. The adapter has no arbitrary command method. Generic standardized OBD-II is supported behind a transport boundary; BMW proprietary PIDs require evidence and physical Vgate compatibility remains pending.
