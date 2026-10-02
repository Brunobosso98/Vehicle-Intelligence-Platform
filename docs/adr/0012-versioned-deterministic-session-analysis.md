# ADR 0012: Versioned deterministic session analysis

Status: Accepted

## Context

Phase 1 stores asynchronous signal observations as canonical event-time rows. Phase 2 must derive
segments and acceleration pulls without assuming synchronous PIDs, hiding missing data, or making
diagnostic claims. Results must remain reproducible after heuristics evolve.

## Decision

Use a bounded synchronous application service with independent alignment, conditioning,
segmentation, pull detection, metric, and persistence modules. Align observations to a profile's
200 ms grid using last-value carry-forward for at most two seconds; never interpolate across a
larger gap. Resolve duplicate signal/timestamps deterministically and median-filter RPM and speed
over three frames.

Persist half-open `[started_at, ended_at)` segment and pull records with detector name, algorithm
version, SHA-256 of canonical sorted configuration JSON, heuristic confidence, quality flags, and
explainable evidence. An identical run is reused; `replace=true` replaces only the identical
session/detector/version/hash identity, never another version. Analysis is limited to 500,000 raw
observations per request.

The generic and BMW F30/N55 reference values are labeled heuristic defaults, not factory
calibration. Pull qualification combines sustained throttle, positive RPM and speed slopes,
minimum duration, RPM delta, and speed delta. Missing optional boost lowers evidence quality but
does not fabricate a value or automatically reject a pull.

Deterministic scripted scenarios keep expected events separate from detector output. Matching uses
boundary tolerance with precision, recall, F1, and boundary-error reporting.

## Alternatives

- A throttle-only rule was rejected because it creates obvious stationary false positives.
- Linear interpolation was rejected because it can invent behavior between sparse observations.
- An asynchronous queue and ML classifier were rejected as premature Phase 3+ infrastructure.
- Overwriting all prior output was rejected because it destroys provenance.

## Consequences and risks

The approach is explainable, inexpensive, portable to other profiles, and testable without a real
vehicle. Fixed-grid alignment can shift a boundary by one interval; acceptance allows 1.5 seconds.
Heuristic confidence is explicitly not a calibrated probability. Long sessions require bounded
partitioning or a future job mechanism rather than bypassing the limit. Detection reports factual
context only; anomaly diagnosis remains deferred.
