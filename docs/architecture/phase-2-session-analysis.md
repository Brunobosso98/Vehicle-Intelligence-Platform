# Phase 2 session and pull analysis

Phase 2 is a read-only derivation pipeline: canonical telemetry → deterministic alignment → light
median conditioning → state segmentation and pull detection → factual metrics → versioned rows.
Routes only validate bounded requests and call the application service. No component writes an ECU
or issues an actuator command.

## Semantics

Alignment skips empty positions only after all carried values have expired. It advances on the
original time grid toward the next measured observation, retaining source order, carry-forward
expiry and the discontinuity marker. A sparse year-long gap therefore does not require a year of
empty alignment ticks. This preserves detector/profile semantics and version identities; short
and year-long gap cases plus the independent pull/event evaluator verify the optimization.

- Windows are half-open `[started_at, ended_at)`.
- The generic profile uses a 200 ms grid. A value is carried forward for no more than two seconds;
  unavailable values remain null and gaps terminate candidates.
- RPM/speed use a centered three-frame median. Other channels are not smoothed.
- Pulls require sustained high throttle plus rising RPM and speed, at least 3 s, 900 rpm and 3 m/s.
- Confidence is a normalized heuristic evidence score, not a probability.
- Configuration fingerprints are SHA-256 over sorted, compact JSON for all typed profile fields.
- An identical analysis is idempotently reused. Explicit replacement affects only the identical
  detector/version/hash; other versions remain auditable.

The `bmw-f30-n55-heuristic-v1` profile is a reference fixture, not claimed BMW calibration data.
Metrics remain null when channels are missing. Quality flags describe missing boost, insufficient
coverage and gaps without interpreting causes.

## API and limits

`POST /api/v1/sessions/{id}/analysis` runs or reuses analysis. Segment and pull lists are limited to
500 and 200 records respectively; analysis rejects more than 500,000 observations. Session pulls
and vehicle-filtered pulls support inspection/comparison. Pull detail is factual only.

## Synthetic validation

Scenario definitions generate mixed driving with three known pulls at 5/10/20 Hz plus stationary
high-throttle, short-burst, missing-boost, irregular, noisy, gap and reversed-ingestion variants.
Ground truth is stored separately. Acceptance is precision/recall ≥0.95 with boundary errors ≤1.5s.
