# Phase 3 event and anomaly engine

Phase 3 transforms persisted canonical telemetry and Phase 2 pulls into versioned, factual events.
**Anomaly detection is not diagnosis.** An observation is a measured value; a detected event is a
deterministic classification; an anomaly is a deviation from a declared reference. A physical-cause
hypothesis is deliberately absent from the contract.

## Pipeline and limits

HTTP routes validate bounded requests and call the event application service. It loads at most
500,000 event-time-ordered observations and 200 pulls, reuses Phase 2 alignment/gap semantics,
constructs baselines, runs composable detectors, consolidates adjacent like events, then persists one
analysis run and structured events. Lists return at most 500 events. Repeated analysis with identical
profile hash is reused; `replace=true` replaces only that configuration's event rows. Other detector
versions/configurations remain auditable.

Every detector has a stable name, semantic version, and SHA-256 of sorted typed configuration.
Evidence, baseline reference, quality flags, signal, time range, severity, and heuristic confidence
are stored as typed JSON fields rather than prose. Confidence measures evidence quality and is not a
calibrated probability. Severity (`info`, `low`, `moderate`, `high`) combines magnitude and duration;
it is neither urgency advice nor diagnosis certainty.

## Baselines and comparability

The preference order is: (1) same-session comparable pulls, (2) sufficiently populated same-vehicle
and configuration history, (3) documented profile threshold, and (4) no/insufficient baseline.
Phase 3 implements levels 1, 3, and 4; history is represented in the contract but is not invented.
Pull comparability combines duration ratio (40%) and overlapping RPM span (60%); a score of at least
0.70 qualifies. Robust centers use median. MAD is `median(abs(x - median(x)))`; it does not assume a
Gaussian distribution.

## Taxonomy and detectors

Stable categories are performance, thermal, fuel, ignition, combustion, mixture, sensor,
telemetry_quality, and control_behavior. Implemented factual events are `boost_drop`,
`boost_overshoot`, `iat_rise`, three high-temperature events, `fuel_pressure_drop`,
`unexpected_throttle_closure`, `sensor_dropout`, `signal_stuck`, and `telemetry_gap`. Timing
correction, misfire and lambda types are reserved by the taxonomy but not detected because no reliable
canonical source signals exist. No PID mappings are fabricated.

Thresholds are heuristic development defaults, not authoritative BMW/N55 calibration or factory
safety limits. Drop/overshoot detectors require pull/high-load context and sustained evidence;
quality detectors report reduced analysis confidence, not a vehicle fault. Accelerator position is
not available, so throttle closure carries a quality flag and reduced confidence.

## Evaluation, troubleshooting, and boundaries

Synthetic scenarios must define injections and independent ground truth with type, time boundaries,
pull, signal, and magnitude band. Matching is one-to-one by type, pull when supplied, and temporal
overlap within one alignment interval; reports include per-class and micro/macro precision, recall,
F1, and boundary error. Detector changes require positive, noise/negative, missing-signal, and
false-positive tests plus version/hash review.

If no event is returned, inspect detector-run states (`no_event`, `insufficient_data`, or
`detector_not_applicable`), signal availability, quality flags and baseline references. Never infer
that a vehicle is healthy from absence of configured events. Phase 4 streaming, OBD acquisition,
Kafka and live events are deferred. ML, root-cause claims, repair advice, and labels such as boost
leak, HPFP failure, heat soak, bad coil/fuel/tune, or turbo failure are explicitly out of scope.

## Retrospective detector review

Detector version 1.1.0 is included in the profile configuration hash, preserving historical
results and preventing stale reuse. Temperature and overshoot thresholds require contiguous
above-threshold samples; disconnected spikes and explicit gaps cannot establish sustained
evidence. Same-session boost references include only comparable preceding pulls. The golden
evaluator checks all emitted types, with per-scenario precision/recall/F1 and boundary gates;
unexpected collateral events cannot be filtered away or matched across different scenarios.
