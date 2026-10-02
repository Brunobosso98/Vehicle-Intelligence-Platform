# ADR 0013: Deterministic evidence-first event architecture

Status: Accepted

## Context

Phase 3 must identify noteworthy measured behavior without turning correlation into component
diagnosis. Results must remain reproducible as thresholds evolve and must operate on irregular,
partially missing Phase 1 telemetry aligned by Phase 2.

## Decision

Use composable synchronous detectors over the existing bounded alignment. Persist analysis runs and
first-class events containing structured evidence, baseline provenance, heuristic severity and
confidence, detector name/version, and deterministic configuration hash. Prefer comparable prior
pulls, then sufficiently populated configuration history, profile thresholds, and finally explicit
insufficient baseline. Use medians/MAD and deterministic consolidation rather than learned models.
Identical analysis is reused; explicit replacement is scoped to the identical configuration.

## Alternatives

A single anomaly function was rejected because it couples loading, reference construction and
detection. Universal hard limits were rejected because configurations differ. ML was rejected before
reliable ground truth exists. Diagnostic prose and root-cause rules were rejected because evidence
does not establish component failure.

## Consequences and risks

Events are explainable, regression-testable and future-agent-ready, but heuristic thresholds require
versioning and may not generalize. Same-session baselines need multiple comparable pulls; the engine
must say insufficient data rather than invent history. Synchronous analysis is bounded to prevent
amplification. Phase 4 queues/streaming and diagnosis remain deferred.
