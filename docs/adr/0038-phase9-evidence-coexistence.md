# ADR 0038: Phase 3, 9B and 9C evidence coexistence

Status: accepted for Phase 9C.

## Context

The platform already records deterministic Phase 3 events and Phase 9B supervised next-pull
evaluation outputs. Phase 9C adds a separate retrospective statistical deviation signal. These
outputs can refer to related observations, but they use different evidence, time horizons and
labels.

## Decision

Keep the three owners and records distinct:

- Phase 3 event rules describe deterministic measured event evidence under their existing rules.
- Phase 9B models evaluate supervised next-pull labels within their offline validation contracts.
- Phase 9C scores unusual after-pull Phase 9A features against an exact compatible historical
  cohort; the score is neither a diagnosis nor a defect probability.

Do not replace, rewrite, merge or silently deduplicate one source against another. If a future
analysis compares these signals, it must be an explicitly offline evaluation that preserves each
source's provenance and treats correlated outputs as related evidence rather than independent
proof of a mechanical condition. Agent, MCP, service and UI integration remain outside Phase 9C.

## Consequences

- Historical Phase 3 event meaning and Phase 9B labels stay unchanged.
- The internal anomaly finding remains owned by the Phase 9C registry and records its own feature,
  cohort, cutoff, detector version and abstention reasons.
- Any common evidence presentation needs a later versioned contract and explicit correlation rules.
- Statistical deviations cannot support component failure, causal or maintenance claims.

## Alternatives considered

- **Replace Phase 3 event rules with learned anomalies:** rejected because their evidence and
  semantics differ.
- **Count each signal as an independent confirmation:** rejected because the inputs may be
  correlated and none establishes mechanical causation.
- **Add agent or product wiring in 9C:** rejected; those boundaries belong to later phases.
