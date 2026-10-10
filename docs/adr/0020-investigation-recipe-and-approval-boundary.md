# ADR 0020: Investigation recipe and approval boundary

## Status

Accepted for Phase 7B implementation. Extends [ADR 0019](0019-grounded-agent-state-and-evidence.md)
and [ADR 0015](0015-acquisition-lifecycle-and-recipes.md).

## Context

The Phase 7A agent returns grounded facts and typed missing-evidence categories. Phase 4 owns a
fixed, versioned LoggingRecipe catalog, read-only source capabilities, deterministic sampling and
preflight. Phase 7B needs to turn unresolved questions into collectable evidence needs without
letting model output become an acquisition command. Historical session signal absence cannot prove
that a source is incapable of collecting that signal.

## Decision

Persist an investigation as a bounded, public typed snapshot with explicit state transitions,
optimistic versioning and replayable events. Keep session links in a separate referential table.
The originating completed AgentRun is immutable and linked by ID; later analysis creates a new run.

Represent model-facing needs as a closed semantic taxonomy. Deterministic code maps each role to
canonical telemetry, then checks whether Phase 4 has a collectable recipe requirement. The
canonical ignition-timing field can exist in imported data while remaining unavailable through the
current Phase 4 recipe catalog. Source support and recorded-in-session status are separate fields.

Select a versioned Phase 4 LoggingRecipe by coverage of known collectable signals and pass it to
the existing Phase 4 preflight/Sampling Planner. Do not execute model-authored signals, frequencies,
PIDs or instructions. An unverified source cannot produce an approval-ready recipe. Approval binds
the exact recipe hash and investigation version; changing the recipe invalidates it. Approval marks
readiness only. The existing local read-only collector remains the acquisition mechanism.

## Alternatives

A second model-authored recipe format would duplicate Phase 4 feasibility rules and make collector
execution difficult to audit. Automatically selecting a future session by timestamp would risk
cross-vehicle or cross-configuration linkage. Treating missing session data as unsupported source
capability would produce false unavailable claims.

## Consequences and risks

The fixed Phase 4 catalog limits the combinations Phase 7B can offer. A useful need outside that
catalog remains explicit and uncollectable. New acquisition support requires a verified Phase 4
catalog change with its own version/hash and tests. Investigation records are additive; the 0010
downgrade removes their audit history, so it is suitable only for disposable validation or after
an explicit archival decision. Database rows require a follow-up service check for vehicle and
configuration ownership before linking a session.
