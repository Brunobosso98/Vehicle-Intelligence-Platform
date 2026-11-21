# Phase 10 pipeline and candidate evaluation

## Protocol

The controlled acceptance enumerates three supervised 9B tasks
(thermal degradation, performance degradation and fuel deviation) and four 9C
families (thermal, boost/air, performance and fuel). It runs the registered
9B trainer and 9C fitting path, verifies registered immutable artifacts, and
evaluates newly predeclared held-out synthetic cohorts through existing 9G
protocols.

For the bounded Phase 10 training input, the evaluator seeds a separate
deterministic six-vehicle Phase 9B fixture (150 pulls) and places its exact
sorted pull IDs in each immutable definition. The wider Phase 9G regression
corpus is not implicitly swept into these training datasets.

Supervised evaluation uses three deterministic, temporally ordered 4-vehicle
fixture blocks beginning April 1, June 1 and September 1, 2026. Their 20-session
blocks have disjoint vehicle and configuration identities, matching the fixed
9G calibration/validation/test protocol's holdout rules. Every evaluation pull
is after the March 1 training cutoff and before the October 2 evaluation
cutoff; this preserves chronological and entity-level separation without
relaxing the existing protocol.

Each run binds the committed repository SHA, definition version/fingerprint,
source role, exact 9A feature and dataset fingerprints, label/oracle checksum,
training/evaluation cutoffs, seed, candidate artifact checksum and evaluation
report checksum. Champion/challenger reports use the active compatible 9D
binding and identical eligible held-out rows. A family, task, horizon, role,
schema, source or cohort mismatch produces NOT_COMPARABLE.

## Executed candidate results

No Phase 10 database-backed candidate run has executed in the current
worktree. Consequently, there are no exact Phase 10 candidate metrics or
support counts to publish yet. The final CI artifact acceptance.json and
candidate-dossiers directory are the evidence sources. This report will be
updated from those exact-SHA artifacts before a VERIFIED declaration.

| Candidate                  | Training support | Held-out support | Metrics/uncertainty | Artifact checksum                       | Scientific status |
| -------------------------- | ---------------- | ---------------- | ------------------- | --------------------------------------- | ----------------- |
| 9B thermal degradation     | Not measured     | Not measured     | Not measured        | Not registered in this local acceptance | NOT_ESTABLISHED   |
| 9B performance degradation | Not measured     | Not measured     | Not measured        | Not registered in this local acceptance | NOT_ESTABLISHED   |
| 9B fuel deviation          | Not measured     | Not measured     | Not measured        | Not registered in this local acceptance | NOT_ESTABLISHED   |
| 9C thermal                 | Not measured     | Not measured     | Not measured        | Not registered in this local acceptance | NOT_ESTABLISHED   |
| 9C boost/air               | Not measured     | Not measured     | Not measured        | Not registered in this local acceptance | NOT_ESTABLISHED   |
| 9C performance             | Not measured     | Not measured     | Not measured        | Not registered in this local acceptance | NOT_ESTABLISHED   |
| 9C fuel                    | Not measured     | Not measured     | Not measured        | Not registered in this local acceptance | NOT_ESTABLISHED   |

The evaluator also re-runs one full 9B task using the same seed and asserts
byte-identical registered model artifact, dataset checksum and candidate
metrics. The independently verified reproduction receipt will be recorded
after exact-head CI execution.

## Dossier content

Every persisted proposal carries a separately checksummed candidate dossier:
task and horizon or anomaly family/method, source role, exact source/dataset/
feature/label/oracle lineage, training and evaluation time cutoffs, row and
session support, training family, held-out performance and uncertainty,
cross-family detector specificity, artifact checksum, applicability limits,
intended controlled environment and review state. The dossier preserves the
Phase 9G scientific-readiness status and explicitly states that real-world
mechanical failure predictive reliability is NOT_ESTABLISHED.
