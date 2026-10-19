# Phase 9C model evaluation

## Evidence boundary and temporal split

The independent acceptance uses controlled synthetic telemetry generated through the canonical
Phase 9A feature generator and persisted through the Phase 9C registry, trusted artifacts and
finding tables. Scenario metadata is evaluation-only: it is not written to source features or used
to fit or score. These measurements describe recovery of synthetic patterns, not mechanical
ground truth, real-car sensitivity, fault probability or diagnostic quality.

The first comparison fits eight chronological reference sessions (40 pull FeatureSets), selects
the method and threshold on validation session 9, and then opens sessions 12 and 13. The test
folds contain 14 and 16 pulls respectively. Two clean recovery sessions separate validation
injections from test. The target-versus-clean denominator is four target-family injections and
eight clean controls per detector. Session 13 is the untouched hidden-stress fold and has an
unseen ambient/IAT level shift plus two additional intervention patterns. A second expanding
window records session 12 as the first model's test before using it as the next model's validation;
the later model trains through session 11 and leaves session 13 untouched.

## Validation-only method selection

Acceptance floors were fixed before test scoring: clean-control false-positive rate at most 0.25,
eligible scoring coverage at least 0.80, and injection recall at least 0.50. Robust MAD wins exact
ties on validation performance and coverage. Metrics below use 2 injected and 4 clean validation
observations per family. `IF` is the bounded, fixed-seed Isolation Forest candidate.

| Family      | Candidate  | Threshold | Precision | Recall |   F1 | Clean FPR | Coverage | Selected |
| ----------- | ---------- | --------: | --------: | -----: | ---: | --------: | -------: | -------- |
| Boost/air   | Robust MAD |     3.500 |      1.00 |   1.00 | 1.00 |      0.00 |     1.00 | Yes      |
| Boost/air   | IF         |     0.586 |      0.67 |   1.00 | 0.80 |      0.25 |     1.00 |          |
| Fuel        | Robust MAD |     3.500 |      1.00 |   1.00 | 1.00 |      0.00 |     1.00 | Yes      |
| Fuel        | IF         |     0.582 |      1.00 |   1.00 | 1.00 |      0.00 |     1.00 |          |
| Performance | Robust MAD |     3.500 |      1.00 |   1.00 | 1.00 |      0.00 |     1.00 | Yes      |
| Performance | IF         |     0.558 |      0.67 |   1.00 | 0.80 |      0.25 |     1.00 |          |
| Thermal     | Robust MAD |     3.500 |      1.00 |   1.00 | 1.00 |      0.00 |     0.83 | Yes      |
| Thermal     | IF         |     0.553 |      0.67 |   1.00 | 0.80 |      0.25 |     0.83 |          |

Robust MAD was selected for all four families. Selection used validation only. The fuel candidates
tied, so the transparent baseline won the predeclared simplicity/runtime tie-break. The thermal
coverage shortfall is a correct `FEATURE_COVERAGE_TOO_LOW` abstention when pre-pull context is not
available; missing context is not replaced with a healthy value.

## Untouched target-versus-clean results

The following metrics combine sessions 12 and 13. Each comparison has four target-family
injections and eight clean controls; the confusion counts include scored cases only, and coverage
reports abstentions against all 12 cases.

| Family      | Candidate  | TP / FP / TN / FN | Precision | Recall |   F1 | Clean FPR | Coverage |
| ----------- | ---------- | ----------------: | --------: | -----: | ---: | --------: | -------: |
| Boost/air   | Robust MAD |     4 / 0 / 8 / 0 |      1.00 |   1.00 | 1.00 |      0.00 |     1.00 |
| Boost/air   | IF         |     3 / 1 / 7 / 1 |      0.75 |   0.75 | 0.75 |     0.125 |     1.00 |
| Fuel        | Robust MAD |     4 / 0 / 8 / 0 |      1.00 |   1.00 | 1.00 |      0.00 |     1.00 |
| Fuel        | IF         |     4 / 1 / 7 / 0 |      0.80 |   1.00 | 0.89 |     0.125 |     1.00 |
| Performance | Robust MAD |     4 / 0 / 8 / 0 |      1.00 |   1.00 | 1.00 |      0.00 |     1.00 |
| Performance | IF         |     4 / 2 / 6 / 0 |      0.67 |   1.00 | 0.80 |      0.25 |     1.00 |
| Thermal     | Robust MAD |     4 / 0 / 6 / 0 |      1.00 |   1.00 | 1.00 |      0.00 |     0.83 |
| Thermal     | IF         |     4 / 4 / 2 / 0 |      0.50 |   1.00 | 0.67 |      0.50 |     0.83 |

The thermal models each abstained on two of 12 target-versus-clean cases because pre-pull context
was missing; all four thermal positive injections were still scored. Robust MAD had no false
positive among its six scored clean thermal cases. The selected candidates' cross-family alarms
are reported separately from clean-control FPR:

| Detector family | Cross-family alarms / 12 | Alarm rate |
| --------------- | -----------------------: | ---------: |
| Boost/air       |                   4 / 12 |      0.333 |
| Fuel            |                   4 / 12 |      0.333 |
| Performance     |                   0 / 12 |      0.000 |
| Thermal         |                   6 / 12 |      0.500 |

The cross-family rates remain a material limitation. A low clean-control FPR does not establish
family specificity.

## Hidden environmental and intervention cases

Session 13 applies an unseen +12 K intake-temperature level shift to all pulls while retaining
ordinary within-pull IAT rise and RPM-duration behavior. Its four clean controls per family were
not used to select thresholds. The table reports scored clean controls and false alarms. Thermal
coverage is 3/4 because one target lacks adequate pre-pull coverage.

| Family      | Robust MAD: false alarms / scored | IF: false alarms / scored |
| ----------- | --------------------------------: | ------------------------: |
| Boost/air   |                             0 / 4 |                     0 / 4 |
| Fuel        |                             0 / 4 |                     1 / 4 |
| Performance |                             0 / 4 |                     1 / 4 |
| Thermal     |                             0 / 3 |                     2 / 3 |

The remaining two hidden intervention patterns also changed source telemetry, not model outputs:

| Held-out intervention                                        | Boost/air                      | Fuel                           | Performance          | Thermal              |
| ------------------------------------------------------------ | ------------------------------ | ------------------------------ | -------------------- | -------------------- |
| Alternating boost fluctuation, with unchanged RPM duration   | Both methods flagged           | Robust MAD flagged; IF did not | Neither flagged      | Neither flagged      |
| Subtle simultaneous IAT-rise, boost and RPM-duration changes | Robust MAD flagged; IF did not | Both methods flagged           | Both methods flagged | Both methods flagged |

These are controlled perturbation outcomes, not fault labels. The extra sensitivity outside the
target family is a cross-family alarm, not evidence that the other subsystems are faulty. The test
cases demonstrate that the nonlinear candidate can miss perturbations that the selected robust
baseline detects; no threshold was adjusted after seeing them.

## Expanding-window and quality controls

The later model was selected on session 12 and tested once on untouched session 13. Robust MAD
was again selected for every family. Each target-versus-clean comparison has two injected cases
and four clean cases. Boost/air, fuel and performance each scored 6/6 with precision, recall and
F1 of 1.00 and clean FPR 0/4. Thermal scored 5/6: both target injections and all three eligible
clean cases were correct, with one `FEATURE_COVERAGE_TOO_LOW` abstention. Across the first frozen
model and the expanding-window model, selected robust thresholds remained 3.5.

| Control                                             | Observed outcome                                                                    |
| --------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Missing required fuel pressure on a fuel target     | `INSUFFICIENT_SIGNAL`                                                               |
| Vehicle/source with no fuel pressure history        | Fit rejected as `REQUIRED_SIGNAL_UNAVAILABLE`; scoring returns `UNSUPPORTED_SOURCE` |
| Duplicate/low-quality telemetry                     | `LOW_QUALITY`                                                                       |
| Same anchor session                                 | `INCOMPATIBLE_CONTEXT`                                                              |
| Different effective configuration or unseen vehicle | `INCOMPATIBLE_CONTEXT`                                                              |
| Required thermal pre-pull coverage missing          | `INSUFFICIENT_SIGNAL` / `FEATURE_COVERAGE_TOO_LOW`                                  |
| Replay of identical model, cutoff and target batch  | Same run and finding IDs in both temporal folds                                     |

The evaluator created 153 Phase 9A FeatureSets, persisted 37 runs and 581 findings, and observed
zero checked-out database connections before close. It separately verified two concurrent
identical requests resolve to one created run and one idempotent replay, and that an oversized
finding rejected by a database check rolls back its enclosing run insert.

## Leakage, artifact and immutability checks

Before canonical feature generation, the evaluator inserted an extreme boost sample whose event
time precedes the pull cutoff but whose ingestion time follows it, plus a modification with an
effective time in the past and a creation time after the cutoff. The Phase 9A FeatureSet excluded
both: its boost maximum remained 114,960 Pa and its active modification list did not contain the
sentinel. A unit adversary added an oracle scenario feature and label metadata, then changed
vehicle/session/pull identifiers; the detector score and decision were unchanged, and the
undeclared feature was absent from the definition. A separate cohort test rejects a changed
modification set before session-overlap checks.

Artifact reload rejected a modified file by checksum. Database triggers rejected an update to an
immutable finding. Unit coverage verifies failed staged-artifact validation removes staged files.
Repeated fits produced matching fitted checksums and deterministic scores; sequential and
concurrent idempotency checks returned stable finding identity. Serialized joblib bytes are not
claimed to be stable across compatible library builds.

## Local imported-data compatibility smoke

A read-only export of local CSV telemetry was scrubbed and loaded into a fresh disposable
TimescaleDB. VINs, source references, raw source metadata and original record keys were removed or
replaced. The source database was not modified.

| Input                                               |                           Count |
| --------------------------------------------------- | ------------------------------: |
| Imported CSV sessions                               |                              96 |
| Vehicle/configuration cohorts                       |                              30 |
| Pulls                                               |                             264 |
| Telemetry samples                                   |                          63,680 |
| Canonical Phase 9A pull FeatureSets generated       |          264 across 88 sessions |
| Feature-generation failures                         |                               0 |
| Phase 9C family/method fit attempts                 |                               8 |
| Fits rejected for insufficient exact-cohort support | 8 (`REFERENCE_SUPPORT_TOO_LOW`) |
| Scored imported pulls                               |                               0 |

The largest observed exact vehicle/configuration cohort had at most 12 pulls before excluding
the anchor, below the nonlinear 24-row requirement and insufficient for the tested robust
reference policy. No imported labels or accuracy metrics were available.

## Performance, artifacts and observability

The direct thermal scorer benchmark uses a held-out clean inlier: 1,000 nominal rows and a mixed
1,000-row batch of 600 clean rows, 300 telemetry perturbations and 100 required-feature
abstentions. Results are offline workstation measurements, not a production SLO. The IF candidate
scored the 300 mild benchmark perturbations as inliers; Robust MAD flagged all 300. This agrees
with the separate held-out comparison and is retained as a limitation.

| Direct scorer    | Nominal: 1,000 inliers |                   Mixed: 900 scored / 100 abstained | Nominal throughput | Mixed throughput |     Artifact | One-score traced allocation |
| ---------------- | ---------------------: | --------------------------------------------------: | -----------------: | ---------------: | -----------: | --------------------------: |
| Robust MAD       |                  1,000 | 600 inliers, 300 anomalous, 100 insufficient signal |         10,918.9/s |       10,628.2/s |  1,038 bytes |                 9,951 bytes |
| Isolation Forest |                  1,000 |                900 inliers, 100 insufficient signal |             28.7/s |           32.4/s | 79,028 bytes |               494,263 bytes |

For eight clean FeatureSets, canonical target materialization took 0.019 s for either method;
artifact reload took 0.011 s for Robust MAD and 0.038 s for IF. Mixed-batch feature preprocessing
took 0.0073 s and 0.0067 s respectively; IF matrix assembly took 0.0012 s. Service timings
separately record target reads and finding persistence. Across the acceptance, Phase 9A feature
generation took 16.450 s, evaluator peak RSS was 233,263,104 bytes, and key anomaly span durations
were: reference materialization 3.404 s, eligibility 3.402 s, detector fit 1.699 s, target
materialization 2.063 s, artifact validation 1.140 s, observation scoring 4.869 s, and finding
persistence 2.078 s. These are local measurements and do not establish production capacity.

The evaluator verified reference, fit, threshold-selection, artifact, target-score and finding
spans. Metric labels contain only bounded family, method, state and status values; entity IDs were
absent from rendered metrics. Detailed per-case receipts are in the ignored
`.validation/phase9c/acceptance.json`; this checked-in report summarizes the observed run.

## Limits

- Synthetic perturbations establish controlled behavior only. Real-vehicle performance is unknown.
- Cross-family alarms remain material for boost/air, fuel and thermal detectors.
- IF missed mild thermal injections in the direct mixed benchmark and produced extra alarms under
  the unseen environmental shift; validation-only selection chose Robust MAD for all families.
- Imported local cohorts did not have enough support to fit or score; no imported-data accuracy
  claim is available.
- A statistical deviation is not a fault, diagnosis, root cause, safety limit or failure
  probability.
- Isolation Forest artifact bytes may vary across compatible library builds despite deterministic
  fitted scores.
- This evidence covers Phase 9C only; Phases 9D–9H remain planned and unimplemented.
