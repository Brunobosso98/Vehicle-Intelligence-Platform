# ADR 0035: Phase 9C cohort and cutoff policy

Status: accepted for Phase 9C.

## Context

Pulls from different vehicles, effective configurations, modifications and sources are not
exchangeable. Multiple pulls in one session are correlated, and a retrospective scorer must not use
later data merely because it is present in the database.

## Decision

Fit each detector against one vehicle, exact effective configuration, exact active modification
set, source type and explicit source role. Do not pool vehicles or add an implicit fallback cohort.
Choose a completed anchor pull; its start time is the reference cutoff. Exclude the anchor session
and require each reference pull and FeatureSet to be strictly earlier and available by that cutoff.
Score targets at a separate timezone-aware cutoff and retain the `AFTER_PULL_OFFLINE` horizon.
Train/validation/test partitions group whole sessions chronologically; threshold selection uses
validation only. Require at least three independent sessions, seven days of span and method-specific
row support. Abstain on cold start or incompatible context.

## Consequences

- The initial system favors supportable per-vehicle baselines over broad but potentially misleading
  cross-vehicle coverage.
- New configurations and modifications need their own history before scoring.
- Whole-session splits reduce correlation leakage but do not prove real-world generalization.
- A changed observation cutoff or compatible cohort creates a new immutable evidence snapshot.

## Alternatives considered

- **Cross-vehicle pooling:** rejected until a separately governed stratification and evidence program
  demonstrates comparability.
- **Same-session train/test rows:** rejected because repeated pulls within one session are correlated.
- **Latest-known history at score time:** rejected for fitting because it can include data later than
  the anchor reference cutoff.
