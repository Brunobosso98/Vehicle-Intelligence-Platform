# Phase 9B — Predictive Models

You are implementing **Phase 9B — Predictive Models** for the Vehicle Intelligence Platform.

Phase 9 is intentionally split into:

- 9A — Feature Engineering Foundation
- **9B — Predictive Models**
- 9C — Anomaly Detection
- 9D — Prediction Service
- 9E — PredictionEvidence
- 9F — Agent Integration
- 9G — Evaluation / Calibration
- 9H — Predictive Intelligence UI

This specification covers **9B only**.

Phase 9A already established deterministic, versioned, leakage-safe feature engineering and dataset construction.

Phase 9B must build the first controlled predictive-model training and offline evaluation layer on top of that foundation.

Conceptually:

```text
Phase 9A FeatureSet / DatasetDefinition
        ↓
time-aware dataset
        ↓
label definition
        ↓
chronological / walk-forward split
        ↓
baseline models
        ↓
candidate models
        ↓
evaluation
        ↓
selected model artifact
        ↓
versioned MLModel / MLModelVersion

NO online prediction service yet.
NO agent integration yet.
NO anomaly engine yet.
```

The purpose of 9B is NOT to claim production-grade mechanical failure prediction.

The purpose is to establish a reproducible, leakage-safe predictive ML training system and demonstrate meaningful next-state prediction on controlled data.

---

## 1. Repository / branch / baseline

Repository:

\`Brunobosso98/Vehicle-Intelligence-Platform\`

Required branch:

\`codex/phase-9b-predictive-models\`

Phase 9B was created from the final Phase 9A candidate branch because Phase 9A had not yet been merged at branch-creation time.

Known Phase 9A final candidate HEAD:

\`af02e6ee8556fdf13e87e8f4aa0b408b2b2688e4\`

Required ancestry before implementation:

the Phase 9B branch must contain the complete Phase 9A implementation and specification.

Before implementation:

1. inspect git status;
2. inspect remotes;
3. fetch origin;
4. switch to \`codex/phase-9b-predictive-models\`;
5. pull fast-forward only;
6. verify clean working tree;
7. verify \`af02e6ee8556fdf13e87e8f4aa0b408b2b2688e4\` is an ancestor;
8. check whether Phase 9A PR #41 has since been merged;
9. if main now contains the Phase 9A merge, verify ancestry and do not unnecessarily rebase/rewrite pushed history;
10. read this entire specification;
11. inspect Phase 9A FeatureDefinition, FeatureSet, FeatureSetVersion, DatasetDefinition and DatasetBuilder;
12. inspect current migration head;
13. inspect synthetic/golden telemetry generators;
14. inspect Phase 5 analytics and Phase 3 event semantics;
15. inspect existing security, observability, benchmark and acceptance patterns.

Do not create another Phase 9B branch.

Do not work directly on main.

Do not force-push.

Do not rewrite pushed history.

---

## 2. Phase 9B purpose

Phase 9B must answer:

- what outcome are we predicting;
- at what horizon;
- which features were legally available at prediction time;
- which dataset/version trained the model;
- how train/validation/test were separated temporally;
- which model families were compared;
- which metrics determined selection;
- whether class imbalance was handled;
- whether model output is reproducible;
- whether synthetic and real evidence are distinguished;
- what limitations prevent stronger claims.

The result must be a trustworthy offline predictive-model foundation for later serving in 9D.

---

## 3. Hard boundaries

Do NOT implement in 9B:

- unsupervised/general anomaly detection (9C);
- online prediction API/service (9D);
- PredictionEvidence public contract (9E);
- agent tools or supervisor use of predictions (9F);
- production calibration/drift program (9G);
- Predictive Intelligence product UI (9H);
- automated retraining;
- model promotion automation;
- model rollback orchestration;
- fleet learning;
- failure-time / remaining-useful-life claims;
- direct maintenance decisions;
- component failure probabilities without real failure labels;
- autonomous vehicle control;
- ECU writes/flashing/coding.

A minimal engineering training/evaluation inspector is optional, but no predictive product UX.

---

## 4. Predictive philosophy

The first predictive models should predict **observable future vehicle behavior**, not mechanical diagnoses.

Allowed initial concepts include:

- next-pull thermal degradation;
- next-pull performance degradation;
- next-pull fuel-pressure deviation when sufficient signals exist.

Do not train:

- "HPFP failure";
- "turbo failure";
- "engine failure";
- "component will break in X km";

unless the repository contains sufficient validated real failure labels, which it currently should not assume.

---

## 5. Initial supervised tasks

Implement three bounded predictive tasks where supported by the Phase 9A acceptance data.

### TASK A — NEXT_PULL_THERMAL_DEGRADATION

Predict whether the next compatible pull will exhibit materially worse thermal state/degradation compared with the current/past state.

### TASK B — NEXT_PULL_PERFORMANCE_DEGRADATION

Predict whether the next compatible pull will exhibit measurable performance degradation relative to a valid prior baseline/current pull.

### TASK C — NEXT_PULL_FUEL_DEVIATION

Predict whether the next compatible pull will exhibit abnormal fuel-pressure behavior relative to the vehicle/configuration historical context.

Task C may be marked source-limited if required signals are unavailable in a dataset.

Do not fabricate a fuel model from absent signals.

---

## 6. Prediction horizon

All mandatory initial tasks use:

\`NEXT_PULL\`

The feature row must be materialized strictly before the outcome pull.

The outcome/label belongs to the next compatible pull.

The training pipeline must use Phase 9A horizon/availability validation.

Any POST_WINDOW feature belonging to the target pull is forbidden.

---

## 7. LabelDefinition

Introduce a formal LabelDefinition abstraction.

Suggested fields:

- key;
- name;
- description;
- dtype;
- task type;
- horizon;
- source outcome;
- algorithm/version;
- required outcome signals;
- quality policy;
- compatibility policy;
- threshold policy;
- provenance;
- active/deprecated.

Label formulas are versioned.

Do not silently alter label semantics.

---

## 8. Label provenance

Every label must be reconstructable to:

- target vehicle;
- target configuration;
- target pull/session;
- outcome time/window;
- source values;
- algorithm/version;
- quality status.

Labels may use the future outcome because they are targets.

Features may not.

This distinction must be explicit and tested.

---

## 9. Avoid circular labels

Do not create a misleading model that merely reproduces an existing deterministic rule and then claim predictive intelligence.

If an existing Phase 3 event is used as a label:

mark the task/model as:

\`DETECTOR_IMITATION_BASELINE\`

and treat it only as an engineering baseline.

Prefer labels based on measurable next-pull continuous/relative outcomes rather than direct copies of event flags.

---

## 10. Thermal label

Create a deterministic next-pull thermal-degradation definition.

It should consider measurable next-pull thermal behavior, for example:

- starting IAT relative to current/prior compatible pull;
- IAT delta;
- recovery state;
- repeated-pull progression.

The exact label formula must:

- be deterministic;
- use only target-pull outcome data;
- be configuration-compatible;
- be quality-gated;
- be documented;
- avoid arbitrary undocumented OEM thresholds.

Prefer relative vehicle/configuration behavior over generic "high IAT" cutoffs.

---

## 11. Performance label

Create a deterministic next-pull performance-degradation definition.

Use an existing validated Phase 5 performance measure such as:

- comparable RPM interval duration;
- repeated-pull normalized performance.

Do not invent horsepower.

Do not compare incompatible configurations.

Label should capture measurable next-pull degradation relative to a valid prior comparable state.

---

## 12. Fuel-deviation label

Where fuel signals permit:

define next-pull deviation using actual recorded fuel-pressure behavior and compatible historical context.

Possible inputs to label creation:

- min pressure;
- drop rate;
- variability;
- actual-vs-commanded error only if commanded exists.

Do not use a static "N55 HPFP healthy threshold".

Do not use Phase 8 documentary values as ground-truth telemetry labels.

---

## 13. Label quality

A target pull with insufficient outcome data must not receive a fabricated label.

Use explicit exclusion reasons such as:

- MISSING_OUTCOME_SIGNAL;
- INSUFFICIENT_OUTCOME_QUALITY;
- NO_COMPATIBLE_PRIOR;
- NO_COMPATIBLE_NEXT_PULL;
- CONFIGURATION_BOUNDARY;
- LABEL_NOT_APPLICABLE.

---

## 14. Dataset versioning

Training datasets must reference:

- DatasetDefinition;
- FeatureSetVersion;
- LabelDefinition version;
- repository SHA;
- source/corpus fingerprint;
- time bounds;
- row identifiers;
- dataset checksum.

A model must never reference an anonymous dataframe.

---

## 15. Model-ready row

Each supervised row must clearly separate:

```text
X = features available before NEXT_PULL
y = outcome measured in NEXT_PULL
```

Persist or export target identity separately from feature identity.

Do not permit the target pull's POST_WINDOW values in X.

---

## 16. Compatibility

Current/next pulls used in one supervised pair must satisfy compatibility rules.

At minimum:

- same vehicle;
- compatible effective configuration;
- no invalid modification boundary;
- source quality adequate;
- chronological ordering valid.

If configuration changes between current and next pull:

exclude unless a future task explicitly studies configuration transitions.

---

## 17. Train / validation / test split

Random row shuffling must NOT be the primary split.

Implement chronological separation.

Recommended:

- earliest block → train;
- later block → validation;
- latest block → test.

Also support walk-forward evaluation.

Rows from a future period must never enter training for an earlier evaluation window.

---

## 18. Group isolation

Prevent related rows from leaking across splits.

Consider grouping by:

- vehicle;
- session;
- temporal block.

At minimum:

pulls from the same outcome sequence/session must not create trivial leakage across train/test.

Document the grouping policy.

---

## 19. Vehicle isolation evaluation

Current data may contain few vehicles.

Provide at least one controlled evaluation mode where a vehicle is held out when fixture volume permits.

This tests portability but must not be presented as fleet validation.

If sample size is insufficient, report it rather than fabricate confidence.

---

## 20. Configuration isolation evaluation

Provide evaluation by configuration.

Report metrics separately where sample count permits.

A model that performs only on one configuration must not be described as generally configuration-aware.

---

## 21. Baseline models

Every task must include simple baselines.

At minimum compare:

### Dummy baseline

- majority / prior / simple deterministic baseline appropriate to task.

### Linear baseline

- LogisticRegression for classification;
- linear/regularized regression if a regression task is selected.

Do not skip simple models.

---

## 22. Candidate model families

Evaluate a bounded set of tabular models.

Prefer stable, explainable, reproducible libraries.

Candidate families may include:

- LogisticRegression;
- RandomForestClassifier/Regressor;
- HistGradientBoostingClassifier/Regressor;
- GradientBoosting;
- ExtraTrees where justified.

XGBoost/LightGBM may be evaluated only if dependency/security/portability costs are justified.

Do not add heavyweight ML frameworks unnecessarily.

No deep neural network is required.

---

## 23. Model selection philosophy

Select the simplest model that meets quality requirements.

Do not choose a more complex model solely because one metric is marginally higher.

Consider:

- validation performance;
- test performance;
- stability;
- inference cost;
- feature availability;
- interpretability;
- reproducibility;
- dependency risk.

Document the selection rubric.

---

## 24. Hyperparameter search

If tuning is used:

- bounded search space;
- deterministic random seed;
- validation-only selection;
- no test-set tuning;
- strict max trials;
- report trial count.

Do not run open-ended AutoML.

Recommended maximum:

20 candidate parameter combinations per task unless the repository evidence justifies fewer/more.

---

## 25. Randomness

Centralize deterministic seeds.

Record:

- Python seed;
- NumPy seed;
- model random_state;
- split version.

Repeated training on identical data/config should produce identical or documented deterministic outputs.

---

## 26. Preprocessing

Use a versioned sklearn-style pipeline or equivalent.

Preprocessing may include:

- numeric imputation only where semantically safe;
- missing indicators;
- scaling for linear models;
- categorical encoding for known bounded context fields.

Do not blindly mean-impute semantically unavailable sensor values.

Prefer:

- explicit missing flags;
- feature exclusion;
- model support for missing values;

depending on feature semantics.

---

## 27. Missing-value policy

The model pipeline must preserve Phase 9A missing semantics where useful.

Do not collapse:

UNAVAILABLE_SIGNAL

and:

INSUFFICIENT_QUALITY

into indistinguishable zero values.

If categorical missing reason is encoded, bound its cardinality.

---

## 28. Feature selection

Initial model feature sets must use the candidate shortlist from 9A.

Feature selection must be domain/leakage/availability aware.

Do not use the test set to select features.

Do not perform unrestricted recursive feature elimination on the full dataset.

---

## 29. Forbidden features

Explicitly reject:

- target pull outcome features;
- target-derived events;
- future-session aggregates;
- future configuration;
- future maintenance/modification state;
- document/RAG target values presented as telemetry;
- unique IDs that trivially memorize entities;
- timestamps used as arbitrary identity proxies unless semantically justified.

---

## 30. Dataset size reality

Current project datasets are small relative to production ML.

The training system must distinguish:

### ENGINEERING_VALIDATION

synthetic/golden controlled data.

### REAL_WORLD_VALIDATION

real vehicle/fleet data.

Phase 9B may be VERIFIED using engineering-validation criteria.

It must NOT claim real-world predictive accuracy unless sufficient real labeled data exists.

---

## 31. Synthetic training

Synthetic/golden datasets may be used to validate:

- pipeline correctness;
- split safety;
- signal learnability;
- model registry;
- evaluation;
- reproducibility.

Synthetic metrics must be labeled synthetic.

Do not market them as expected real-car performance.

---

## 32. Real-data smoke

If repository data contains real/imported sessions:

run a non-claiming compatibility smoke.

Verify:

- feature materialization;
- label eligibility;
- training row generation.

Do not train/evaluate statistically weak real data as though it proves performance.

---

## 33. MLModel

Introduce a model-family/domain abstraction.

Suggested fields:

- id/key;
- task;
- description;
- target/label key;
- prediction horizon;
- intended scope;
- status;
- created_at.

This is not yet a production deployment registry.

---

## 34. MLModelVersion

Introduce an immutable trained-version abstraction.

Suggested metadata:

- model ID;
- version;
- algorithm;
- hyperparameters;
- random seed;
- FeatureSetVersion;
- DatasetDefinition/version;
- LabelDefinition/version;
- dataset checksum;
- training time range;
- train/validation/test counts;
- metrics;
- artifact path/key;
- artifact checksum;
- training code version/repository SHA;
- library versions;
- created_at;
- status.

No silent artifact replacement.

---

## 35. Model artifact storage

Store trained artifacts in a bounded application-controlled location.

Do not commit large binary model artifacts to Git unless very small/test-only and repository policy explicitly allows it.

Recommended:

- local artifact directory ignored by Git;
- metadata/checksum persisted;
- deterministic reconstruction from dataset/spec.

Security:

never load arbitrary user-provided pickle/joblib artifacts.

Only load artifacts created/registered by trusted training workflow and verified by checksum.

Document serialization risk.

---

## 36. Artifact format

Choose a practical safe-enough format for current Python stack.

If using joblib/pickle:

- document code execution risk;
- load only trusted internal artifacts;
- enforce artifact path + checksum + registry identity;
- never expose artifact upload to users.

If a safer portable format such as ONNX/skops is justified, evaluate it.

Do not add format complexity with no benefit.

---

## 37. TrainingRun

Create a TrainingRun / ModelTrainingRun.

Suggested fields:

- run ID;
- task;
- dataset version/checksum;
- label version;
- candidate models;
- selected model;
- started/finished;
- seed;
- status;
- metrics;
- artifact checksum;
- error category;
- trace ID.

---

## 38. Training CLI

Provide an explicit controlled training command.

Example equivalent:

\`make phase9b-train\`

Training is not paid-provider work.

It must:

- print dataset/version;
- print split counts;
- print task;
- print candidates;
- print seed;
- write artifacts to controlled location;
- persist metadata.

Do not train automatically on API request.

---

## 39. No online serving

Phase 9B may perform offline prediction during evaluation.

Do NOT create a production HTTP prediction endpoint.

Do NOT add live prediction to session ingestion.

That belongs to 9D.

---

## 40. Metrics — classification

For classification tasks report:

- confusion matrix;
- precision;
- recall;
- F1;
- ROC-AUC where both classes exist;
- PR-AUC where both classes exist;
- balanced accuracy;
- class support.

Do not report undefined metrics as zero without noting undefined status.

---

## 41. Metrics — regression

If any task is formulated as regression, report:

- MAE;
- RMSE;
- R² where meaningful;
- prediction interval/coverage only if actually implemented.

Do not force classification if continuous prediction is more appropriate.

However, the mandatory task interface must remain interpretable.

---

## 42. Probability metrics

If models expose probabilities:

record:

- Brier score;
- basic reliability/calibration summary.

Do not perform full production probability calibration in 9B.

Formal calibration hardening belongs to 9G.

Do not claim "80% means 80% real-world probability" yet.

---

## 43. Threshold selection

Classification decision thresholds must be selected on validation data only.

Do not optimize threshold on test data.

Store threshold with the ModelVersion.

Default 0.5 may be retained if no valid reason to tune.

---

## 44. Imbalance

Measure class balance.

If handling imbalance:

- class weights;
- bounded resampling;

must happen on training data only.

Never oversample before splitting.

Avoid synthetic resampling methods unless sample size/benefit is justified.

---

## 45. Evaluation by time

Report metrics by chronological segment / walk-forward fold.

A single aggregate metric is insufficient.

Identify degradation across time.

---

## 46. Evaluation by configuration

Where sample volume permits:

report:

- per configuration;
- aggregate.

Do not hide poor minority-configuration performance.

---

## 47. Evaluation by quality

Report model performance on:

- high-quality feature rows;
- degraded-but-eligible rows;

if sample size permits.

Do not let quality failures silently poison evaluation.

---

## 48. Generalization caveat

If trained on synthetic data from a known generator:

explicitly state the possibility of learning generator-specific patterns.

Create at least one holdout scenario/profile not used in training fixture generation.

---

## 49. Scenario holdout

Reserve at least one synthetic scenario family for final testing.

Example:

train/validation:

- stable;
- moderate degradation profiles.

test:

- unseen combination or severity.

Do not reuse identical deterministic sequences across all splits.

---

## 50. Feature importance

Provide offline feature importance.

For linear model:

- coefficients.

For tree model:

- native importance/permutation importance.

Prefer permutation importance on held-out validation/test where practical.

Do not present feature importance as mechanical causality.

Wording/documentation must explicitly say:

"predictive contribution / association, not physical cause."

---

## 51. SHAP boundary

SHAP is not mandatory in 9B.

Full prediction explanation may be introduced later alongside PredictionEvidence/agents.

If SHAP is added:

- keep offline;
- bound computation;
- do not imply causality.

Avoid dependency bloat merely to add SHAP.

---

## 52. Reproducibility

Given identical:

- repository SHA;
- dataset checksum;
- FeatureSetVersion;
- LabelDefinition;
- model spec;
- seed;
- dependencies;

training output must be reproducible within the deterministic guarantees of the selected library.

Artifact checksum should be stable where library serialization permits.

If byte-level artifact serialization is non-deterministic, model predictions/metrics must still be deterministic and the limitation documented.

---

## 53. ModelSpec

Create a versioned model specification.

Fields may include:

- task;
- candidate feature keys;
- preprocessing;
- algorithm family;
- hyperparameter search bounds;
- selection metric;
- threshold policy;
- random seed.

Do not bury training configuration in CLI flags only.

---

## 54. Selection metric

Choose a primary validation metric per task.

For imbalanced degradation classification:

prefer a metric such as:

- PR-AUC;
- F1;
- balanced accuracy;

rather than raw accuracy.

Document why.

Use secondary metrics to avoid pathological selection.

---

## 55. Minimum model acceptance

A selected model must outperform the dummy baseline on the primary validation/test criteria.

Do not accept a complex model that does not materially outperform baseline.

For controlled synthetic engineering validation, define thresholds based on fixture difficulty rather than arbitrary claims.

---

## 56. Overfit detection

Compare:

- train;
- validation;
- test.

Flag large gaps.

Do not hide overfit because test set is small.

Produce explicit:

- OVERFIT_WARNING;
- INSUFFICIENT_TEST_SUPPORT;
- CLASS_MISSING_IN_FOLD;

states.

---

## 57. Data sufficiency policy

Before training each task verify:

- minimum row count;
- both classes for classification;
- minimum positive support;
- enough chronological coverage;
- enough compatible configurations where intended.

If insufficient:

return:

\`INSUFFICIENT_TRAINING_DATA\`

Do not fabricate a model.

---

## 58. Initial minimums

Set conservative engineering minimums.

Example starting floor for controlled classification:

- at least 100 rows total;
- at least 20 positive;
- at least 20 negative;
- meaningful validation/test support.

If current acceptance fixture is smaller, generate a larger deterministic synthetic training fixture rather than lowering standards silently.

Do not claim these minimums prove real-world adequacy.

---

## 59. Synthetic training fixture

Extend existing deterministic generators to create enough model-training sequences.

Include variation in:

- vehicle;
- configuration;
- initial thermal state;
- recovery interval;
- boost behavior;
- fuel behavior;
- performance;
- signal quality.

Avoid trivially encoding labels in one obvious feature.

---

## 60. Confounder tests

Create cases where simple correlations should not become false universal rules.

Examples:

- high IAT but no performance degradation;
- performance degradation with stable IAT;
- fuel deviation with normal boost;
- boost variation without degradation.

This prevents models from succeeding only through simplistic single-feature shortcuts.

---

## 61. Negative controls

Include irrelevant/noise features in controlled fixtures.

Selected model should not depend heavily on them.

Report if irrelevant features dominate importance.

---

## 62. Leakage sentinel feature

For tests only, create an intentionally illegal future/target feature.

Training pipeline must reject it before model fit.

This is a hard acceptance scenario.

---

## 63. ID memorization sentinel

Create a unique random/entity ID-like feature in test fixture.

Training feature validator should reject identity-only fields unless explicitly allowed.

Prevent trivial vehicle/session memorization.

---

## 64. Train pipeline architecture

Recommended structure:

```text
DatasetDefinition
→ labeled dataset builder
→ leakage validator
→ chronological splitter
→ preprocessing pipeline
→ candidate trainer
→ validation selector
→ final selected fit
→ test evaluator
→ artifact registry
→ report
```

Do not mix test evaluation into model selection.

---

## 65. Final fit policy

After selecting hyperparameters on train/validation:

define whether selected model is:

- fit on train only and test once; or
- refit on train+validation then evaluate on untouched test.

Document the exact policy.

Do not reuse test for tuning afterward.

---

## 66. Walk-forward evaluation

Implement at least one walk-forward evaluation mode.

For each fold:

train only on earlier data;
evaluate later period.

Aggregate metrics and variance.

---

## 67. Dataset immutability

Once a TrainingRun starts:

its dataset checksum must not change.

If source changes during training:

fail or pin the materialized dataset snapshot.

Do not mix rows from different dataset revisions.

---

## 68. Model registry state

Use bounded states such as:

- TRAINING;
- EVALUATED;
- REJECTED;
- CANDIDATE.

Do not introduce PRODUCTION promotion in 9B.

Production deployment lifecycle belongs to 9D/10.

---

## 69. No automatic promotion

A model passing evaluation must not automatically become the model served to users.

It remains a CANDIDATE.

---

## 70. Security

Training pipeline must reject:

- arbitrary Python expressions;
- arbitrary estimator class import strings from users;
- arbitrary pickle/model uploads;
- path traversal;
- arbitrary output paths;
- arbitrary SQL.

Candidate model families must come from a fixed registry/allowlist.

---

## 71. Resource bounds

Training must have bounded:

- dataset rows;
- feature count;
- candidate models;
- hyperparameter trials;
- CPU parallelism;
- wall time;
- artifact size.

Avoid \`n_jobs=-1\` by default in CI if it causes uncontrolled resource use.

---

## 72. Failure recovery

A failed candidate model must:

- record failure;
- not corrupt other candidates;
- preserve run report;
- allow controlled retry.

Do not mark TrainingRun success if selected model artifact is missing/corrupt.

---

## 73. Artifact verification

Before registering ModelVersion:

- artifact exists;
- checksum matches;
- deserialization smoke passes in trusted process;
- expected feature schema matches;
- offline prediction smoke passes.

---

## 74. Input schema

ModelVersion must record exact expected input features/order/dtypes/units.

Offline inference must reject:

- missing mandatory features;
- incompatible FeatureSetVersion;
- wrong unit/schema;
- wrong model task.

---

## 75. Offline inference helper

Provide a private/offline helper to run predictions for evaluation.

This is not the Phase 9D service.

It may be used by:

- acceptance;
- benchmark;
- model report.

Do not expose it as a production endpoint.

---

## 76. Benchmark

Benchmark:

- labeled dataset materialization;
- training time per candidate;
- total bounded search time;
- artifact size;
- offline inference throughput;
- peak memory.

Use controlled fixture sizes.

Do not claim an SLA.

---

## 77. Observability

Add safe metrics:

- training_runs_total;
- training_runs_failed_total;
- candidate_models_total;
- candidate_training_duration_seconds;
- model_evaluations_total;
- dataset_rows_training;
- model_artifact_bytes;
- label_exclusions_total.

Avoid vehicle/session IDs in metric labels.

---

## 78. Tracing

Trace:

```text
TrainingRun
→ dataset materialization
→ label build
→ leakage validation
→ split
→ candidate fit
→ validation
→ selection
→ test evaluation
→ artifact register
```

Do not trace complete feature matrices.

---

## 79. Logging

Log:

- run ID;
- task;
- dataset checksum;
- model family;
- seed;
- counts;
- metrics summary;
- failure category.

Do not log full datasets.

---

## 80. Database migration

Add additive migration(s) for:

- LabelDefinition / version if persisted;
- MLModel;
- MLModelVersion;
- TrainingRun;

as architecture requires.

Do not edit historical migrations.

Test:

- fresh upgrade;
- Phase 9A DB upgrade;
- downgrade where safe;
- re-upgrade.

---

## 81. API

No prediction API.

A bounded engineering/admin API may expose:

- model definitions;
- model versions;
- training run metadata;
- metrics;
- artifact metadata (not arbitrary download).

Training should remain explicit CLI/job-style, not unrestricted synchronous HTTP.

---

## 82. Frontend

Predictive product UI is deferred to 9H.

A small engineering Model Registry view is optional if consistent with the project.

Do not add:

- health gauges;
- risk warnings;
- live predictions;
- user-facing maintenance advice.

---

## 83. Acceptance evaluator

Create an independent evaluator such as:

\`scripts/evaluate_predictive_models.py\`

and target equivalent:

\`make phase9b-acceptance\`

It must exercise:

- actual Phase 9A dataset path;
- label generation;
- leakage guard;
- temporal split;
- training;
- model selection;
- artifact persistence;
- offline inference;
- reproducibility.

Do not merely wrap unit tests.

---

## 84. Mandatory acceptance tasks

Acceptance must train/evaluate:

1. thermal next-pull model;
2. performance next-pull model;
3. fuel-deviation next-pull model if eligible.

If fuel task is not eligible on one source:

the acceptance dataset must include a source where required fuel signals exist.

---

## 85. Mandatory baselines

For each task:

- dummy baseline;
- linear baseline;
- at least one nonlinear candidate.

Selected candidate must be justified.

---

## 86. Acceptance safety checks

Must prove:

- future feature rejected;
- target-derived feature rejected;
- cross-vehicle history rejected;
- cross-config invalid pair rejected;
- ID memorization feature rejected;
- insufficient target quality excluded;
- missing label signal not fabricated;
- test set never used in hyperparameter selection.

---

## 87. Acceptance reproducibility

Run identical training twice on controlled fixture.

Required:

- same split row IDs;
- same selected model family;
- same hyperparameters;
- same predictions;
- same metrics within strict deterministic tolerance.

If artifact bytes differ:
document serialization reason.

---

## 88. Acceptance quality

Do not require absurd near-100% model scores.

Synthetic tasks should be nontrivial.

The selected model must:

- outperform dummy baseline;
- show meaningful predictive signal;
- avoid obvious leakage;
- not catastrophically overfit.

Define task-specific thresholds based on the final fixture and document them before final evaluation.

---

## 89. Suggested engineering thresholds

Starting guidance only:

- F1 >= 0.75 where classification is balanced enough;
- PR-AUC meaningfully above positive prevalence;
- balanced accuracy >= 0.70;
- selected model better than dummy on untouched test.

If the designed task is intentionally harder:
document why thresholds differ.

Never lower thresholds after seeing test results merely to pass.

---

## 90. Real-world claim guard

Final reports/UI/docs must state:

"These models are engineering-validation models trained/evaluated on controlled/synthetic project data unless explicitly stated otherwise."

No claims such as:

- predicts N55 failures;
- clinically/mechanically validated;
- production maintenance predictor;
- fleet validated.

---

## 91. Model card

Create one model card per mandatory task.

Suggested path:

\`docs/ml/models/<task>.md\`

Include:

- purpose;
- prohibited use;
- horizon;
- label;
- features;
- dataset;
- split;
- algorithm;
- metrics;
- configuration coverage;
- synthetic/real status;
- limitations;
- failure modes;
- safety notes.

---

## 92. Training report

Create:

\`docs/validation/phase-9b-model-evaluation.md\`

Include all candidates, not only winner.

Avoid cherry-picking.

---

## 93. Architecture docs

Create/update:

- \`docs/architecture/phase-9b-predictive-models.md\`
- \`docs/runbooks/model-training.md\`
- \`docs/validation/phase-9b-acceptance.md\`
- \`docs/validation/phase-9b-traceability-ledger.md\`
- model cards;
- roadmap;
- README;
- observability/security docs.

---

## 94. ADRs

At minimum consider ADRs for:

- model artifact format/security;
- chronological split policy;
- model-family allowlist/selection;
- label-definition policy.

---

## 95. Phase 9A regression

Run full Phase 9A acceptance.

9B must not mutate FeatureDefinition semantics to improve model scores.

If a genuine 9A defect is found:
fix generically, version affected feature definitions properly, and rerun 9A acceptance.

Do not hack features for labels.

---

## 96. Phase 0–8 regression

Run all deterministic required regressions.

Do not automatically rerun:

- paid Phase 7D Luna suite;
- paid Phase 8 embedding calls.

Use existing deterministic/cached paths.

---

## 97. Security gates

Run existing security/CodeQL/dependency/image policies.

ML dependencies must be pinned/locked and audited.

Avoid adding dependency stacks with known blocked vulnerabilities.

---

## 98. Clean-state validation

From fresh disposable infrastructure:

- migrations;
- Phase 9A feature generation;
- labeled dataset build;
- split;
- training;
- evaluation;
- artifact register;
- offline inference;
- Phase 9B acceptance;
- security;
- observability;
- deterministic regressions.

---

## 99. Make targets

Add repository-conventional equivalents:

- \`make test-models\`
- \`make phase9b-acceptance\`
- \`make phase9b-train\`
- \`make benchmark-models\`
- \`make model-observability\`

Generic verify may run deterministic bounded training fixtures.

No external paid API required.

---

## 100. Final exact-head validation

After all changes are committed:

- clean working tree;
- capture exact HEAD;
- run complete relevant local validation;
- push;
- verify origin branch equals local HEAD;
- monitor exact-head GitHub checks.

A fix after validation creates a new final candidate and relevant gates must rerun.

---

## 101. Pull request

Open PR against main only after Phase 9A is present in main or Git ancestry makes the diff clean.

Suggested title:

\`feat: add Phase 9B predictive model foundation\`

Do not merge.

User will merge manually.

PR body must include:

- tasks/labels;
- dataset versions;
- split policy;
- model candidates;
- selection;
- train/validation/test metrics;
- baseline comparisons;
- reproducibility;
- artifacts;
- model cards;
- synthetic-vs-real limitations;
- benchmark;
- security;
- regression;
- exact final SHA.

---

## 102. Remote checks

Final SHA must pass current equivalents:

- CI/quality;
- integration E2E;
- Security;
- CodeQL Python;
- CodeQL JS/TS;
- dependency review;
- canonical Docker/full-stack;
- Phase 9B dedicated gate if added.

Do not use older-SHA evidence.

---

## 103. Definition of Done — labels/datasets

- [ ] LabelDefinition implemented/versioned;
- [ ] thermal next-pull label;
- [ ] performance next-pull label;
- [ ] fuel-deviation next-pull label;
- [ ] target quality/exclusion policy;
- [ ] Phase 9A horizon enforcement;
- [ ] chronological split;
- [ ] walk-forward;
- [ ] no test tuning;
- [ ] leakage sentinel blocked.

---

## 104. Definition of Done — models

- [ ] dummy baselines;
- [ ] linear baselines;
- [ ] nonlinear candidates;
- [ ] bounded hyperparameter selection;
- [ ] deterministic seeds;
- [ ] selected candidate per task;
- [ ] ModelSpec;
- [ ] MLModel;
- [ ] MLModelVersion;
- [ ] TrainingRun;
- [ ] artifact checksum/security;
- [ ] offline inference helper.

---

## 105. Definition of Done — evaluation

- [ ] untouched test evaluation;
- [ ] walk-forward evaluation;
- [ ] configuration breakdown;
- [ ] class support;
- [ ] overfit detection;
- [ ] feature importance as association;
- [ ] baseline comparison;
- [ ] reproducibility run;
- [ ] scenario holdout;
- [ ] real-world claim guard.

---

## 106. Definition of Done — engineering

- [ ] migrations;
- [ ] unit tests;
- [ ] DB integration;
- [ ] independent acceptance;
- [ ] benchmark;
- [ ] observability;
- [ ] security;
- [ ] Phase 9A regression;
- [ ] Phase 0–8 deterministic regression;
- [ ] clean-state validation;
- [ ] exact final-SHA GitHub checks.

---

## 107. Final report

Return at least:

1. branch;
2. Phase 9A ancestry/base;
3. final SHA;
4. PR URL/state;
5. migration revision;
6. LabelDefinition design;
7. thermal label;
8. performance label;
9. fuel label;
10. label exclusions;
11. DatasetDefinition/version/checksum;
12. total rows;
13. train rows;
14. validation rows;
15. test rows;
16. chronological split;
17. walk-forward folds;
18. vehicle/configuration coverage;
19. model families tested;
20. hyperparameter trial counts;
21. selected model per task;
22. dummy baseline metrics;
23. linear baseline metrics;
24. selected model metrics;
25. test confusion matrices;
26. precision/recall/F1;
27. ROC-AUC/PR-AUC where defined;
28. balanced accuracy;
29. Brier/basic probability metrics;
30. class distribution;
31. overfit warnings;
32. scenario holdout results;
33. cross-vehicle evaluation if possible;
34. configuration evaluation;
35. reproducibility results;
36. ModelSpec;
37. MLModel/Version;
38. TrainingRun;
39. artifact format/checksum/security;
40. offline inference;
41. feature importance;
42. leakage sentinel result;
43. ID memorization sentinel;
44. benchmark;
45. observability;
46. security;
47. Phase 9A regression;
48. Phase 0–8 regression;
49. clean-state;
50. exact-head GitHub checks;
51. model-card locations;
52. synthetic-vs-real statement;
53. known limitations;
54. confirmation 9C–9H not implemented;
55. confirmation PR unmerged.

End with exactly:

\`PHASE 9B — PREDICTIVE MODELS: VERIFIED\`

only if every mandatory requirement is genuinely satisfied.

Otherwise continue fixing anything within your control.

If a genuine external blocker remains, use:

\`PHASE 9B — PREDICTIVE MODELS: NOT VERIFIED\`

and document the blocker precisely.

Do not merge the PR.
