# Phase 9B predictive model foundation

Phase 9B adds bounded offline supervised training over Phase 9A feature snapshots. It predicts
observable behavior on the next compatible pull. It does not diagnose a component, estimate failure
probability, serve predictions, or change vehicle operation.

## Ownership and flow

`vehicle_platform.ml` owns the versioned task/label definitions, label reconstruction, compatibility
checks, temporal splits, fixed candidate allowlist, training/evaluation, artifact checks and model
registry writes. It reads canonical Phase 9A datasets and feature definitions. Migration `0014`
owns label definitions, model definitions and versions, supervised dataset receipts/rows, and
training runs. Existing telemetry, pulls, analytics and feature records retain their owners.

```text
Phase 9A input and outcome datasets at a declared cutoff
        ↓ next-compatible-pull pairing and versioned outcome rule
immutable supervised rows with lineage and checksums
        ↓ chronological session-group train / validation / test
dummy + logistic regression + random forest
        ↓ validation-only model and threshold selection
test report + walk-forward / scenario / vehicle / configuration checks
        ↓ internal-only bounded joblib artifact and smoke inference
registered MLModelVersion + TrainingRun
```

The input row is strictly before the target pull. Pairing requires the same vehicle, effective
configuration and compatible modification state. The immediately following candidate pull is used;
an incompatible, low-quality or unavailable outcome is excluded with a bounded reason rather than
skipped in favor of a later, easier target. Identity fields and target-source features are barred
from the model matrix.

## Initial tasks and limits

All labels are binary `NEXT_PULL` outcomes and have immutable checksums:

| Task                                | Observable outcome rule                                                                                                   | Key limitation                                          |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `NEXT_PULL_THERMAL_DEGRADATION`     | Target pull IAT begins at least 3 K above the input pull start                                                            | Relative engineering threshold, not an OEM limit        |
| `NEXT_PULL_PERFORMANCE_DEGRADATION` | Target 3,500–4,500 RPM interval per 1,000 RPM is at least 8% slower than input                                            | Requires comparable, continuous RPM coverage            |
| `NEXT_PULL_FUEL_DEVIATION`          | Target minimum high-pressure fuel is at most 88% of the compatible prior-pull mean; at least two prior pulls are required | Source-limited; no universal pressure limit is inferred |

Each task keeps input features separate from outcome features and persists outcome values, source
pull/session/configuration, timestamps, quality, algorithm version and source hash. Outcome values
from the target pull never enter the model vector. Label or threshold changes require a new label
version and checksum.

## Dataset and model identity

The Phase 9A input and outcome `DatasetDefinition` snapshots are persisted alongside the supervised
dataset. The supervised manifest includes both dataset checksums, label/model spec checksums,
ordered feature schema, row and exclusion counts, source role, cutoff, seed/split policies and
repository revision. Candidate rows retain exclusion reason and lineage. Database triggers reject
updates/deletes to immutable label, dataset, row and model-version records.

`ModelSpec` fixes features, task semantics, the dummy/logistic/random-forest candidate families,
small bounded parameter grids, seed, split version, threshold grid and minimum support/acceptance
criteria. Preprocessing is fit within each training partition: median imputation, missingness
indicators, and scaling for logistic regression. No test-derived model or threshold selection is
allowed. Selection uses validation average precision subject to predeclared F1, balanced-accuracy
and lift floors; a simpler eligible candidate wins close ties. The test set evaluates the selected
candidate and dummy baseline after selection.

Chronological session groups form train, validation and test partitions. Whole temporal blocks are
kept together so overlapping label windows do not cross a split. Walk-forward uses expanding
training windows. Separate scenario, held-out-vehicle and held-out-configuration reports expose
generalization limits. Feature importance is a model association summary, not causal evidence.

## Artifacts and execution boundary

The operator CLI is the only training entry point. It requires an explicit task, aware cutoff and
source role; batch and CPU/thread settings are bounded. It refuses a production environment. No
HTTP, MCP, agent, UI, retraining or promotion path is added.

Artifacts are internal trusted-code joblib files under the fixed ignored
`apps/api/.artifacts/phase9b/` root, capped at 50 MiB and written atomically. The registry records
the exact model/task/version, schema, estimator family, dataset, metrics, checksum and runtime
library versions. Loading requires a registered model and matching checksum/schema/version.
Joblib uses pickle semantics and therefore is only loaded from this application-owned, verified
artifact directory; never load user-supplied artifacts. Offline inference checks exact feature
order, units, missingness and quality and returns an explicitly named engineering-validation score,
not a real-world failure probability.

## Synthetic evidence and safety

The canonical fixture uses seeded, controlled telemetry and runs the actual Phase 9A feature
generation path. It includes explicit low-quality and missing-fuel exclusions, controlled
confounders, scenario/vehicle/configuration holds and deterministic repetitions. The acceptance
evaluator labels the results `ENGINEERING_VALIDATION`; it does not claim fleet accuracy or
mechanical diagnosis. Real data can be smoke-trained only when configured source coverage and row
support meet the task floor. Insufficient support is recorded as a rejected run, never repaired by
fabricating labels.

Training metrics and spans use bounded task, family, state and reason values. Entity IDs, VINs,
checksums, feature values, raw samples and credentials stay out of metric attributes and logs.
See the [model-training runbook](../runbooks/model-training.md), [acceptance report](../validation/phase-9b-acceptance.md),
and ADRs [0032](../adr/0032-versioned-next-pull-labels.md), [0033](../adr/0033-offline-model-selection-and-splits.md),
and [0034](../adr/0034-internal-model-artifacts.md).
