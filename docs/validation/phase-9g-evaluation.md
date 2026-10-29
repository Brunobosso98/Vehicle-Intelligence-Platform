# Phase 9G evaluation report

This report records the Phase 9G protocol and the scientific claim boundary. Numeric results must be
copied only from the checksummed, exact-SHA acceptance receipt and its independent checker; the
receipt remains the authoritative detailed source for counts, intervals, subgroup results, alarm
denominators, and benchmark measurements.

## Protocol

- Protocol: `phase9g-protocol-v1`; report schema: `phase9g-evaluation-v1`.
- Population: synthetic canonical Phase 9A FeatureSets generated through the existing Phase 9B and
  Phase 9C pipelines. Source role is retained per record.
- Held-out generator: `phase9g-heldout-v4`; three later windows use four distinct synthetic
  vehicles, five sessions per vehicle, and five pulls per session. The 9B training fixture retains
  its original default size and ordering. The bounded future cohorts keep the combined canonical
  9A source payload under its 32 MiB materialization limit and provide separate vehicle/configuration
  groups for the chronological calibration, validation, and test thirds.
- Supervised tasks: the three registered 9B `NEXT_PULL` tasks. Model artifacts and operating
  thresholds are loaded as registered and held fixed.
- Partitioning: strict chronological whole-session training, calibration, validation, and test;
  physical pulls, sessions, vehicles, and configurations are disjoint across evaluation folds.
  Model training vehicles and configurations are held out from every evaluation fold.
- Calibration: identity baseline and support-gated monotone sigmoid/isotonic candidates fit only on
  calibration data; validation-only Brier selection; test labels remain untouched until scoring.
- Uncertainty: session-cluster bootstrap with intervals unavailable below the minimum independent
  session support; raw counts and denominators remain visible.
- Anomalies: four existing Phase 9C families by two existing detector methods, reporting clean
  false alarms, target-family detections, cross-family alarms, quality abstentions, detector
  stability, and reference-size sensitivity.
- Drift: training-only feature/OOD reference; synthetic labeled prevalence/performance comparisons;
  real/imported unlabeled evidence can report only observed availability/distribution.

## Scientific status

No mechanical failure outcomes or labels are available in the acceptance dataset. Therefore real
predictive validity and real calibration are `NOT_ESTABLISHED`; production use is `PROHIBITED`.
Synthetic next-pull observable-label results describe only the versioned fixture population. They
do not become mechanical-failure probabilities. Phase 9C anomaly values remain statistical scores,
not health percentages. Any unsupported or insufficient candidate stays uncalibrated or abstains.

The final exact-SHA numerical tables and actual denominators are transcribed here after the
canonical acceptance run; the detailed checksummed measurements remain in the linked workflow
artifact in the [acceptance record](phase-9g-acceptance.md). Engineering verification is reported
separately from scientific applicability.
