# Phase 9A — Feature Engineering Foundation

You are implementing **Phase 9A — Feature Engineering Foundation** for the Vehicle Intelligence Platform.

Phase 9 is intentionally split into eight sub-phases:

- **9A — Feature Engineering Foundation**
- **9B — Predictive Models**
- **9C — Anomaly Detection**
- **9D — Prediction Service**
- **9E — PredictionEvidence**
- **9F — Agent Integration**
- **9G — Evaluation / Calibration**
- **9H — Predictive Intelligence UI**

This specification covers **9A only**.

Do NOT prematurely implement 9B–9H.

The purpose of 9A is to create the deterministic, versioned, leakage-safe feature foundation that every later predictive model will depend on.

Conceptually:

~~~text
canonical telemetry
+ sessions
+ pulls
+ events
+ analytics
+ vehicle/configuration/modification context
        ↓
Feature Definitions
        ↓
Feature Extraction
        ↓
Feature Sets
        ↓
Dataset Builder
        ↓
Leakage / temporal validation
        ↓
model-ready datasets

NO predictive model yet.
~~~

The Phase 9A implementation must be production-grade enough that later model training can trust feature identity, provenance, temporal boundaries and reproducibility.

---

## 1. Repository / branch / baseline

Repository:

\`Brunobosso98/Vehicle-Intelligence-Platform\`

Required branch:

\`codex/phase-9a-feature-engineering-foundation\`

Known Phase 8 merge commit / Phase 9A baseline:

\`d1e35baba8f11c89f413e54c228a86724605a8f1\`

Before implementation:

1. inspect git status;
2. inspect remotes;
3. fetch origin;
4. switch to \`codex/phase-9a-feature-engineering-foundation\`;
5. pull fast-forward only;
6. verify clean working tree;
7. verify \`d1e35baba8f11c89f413e54c228a86724605a8f1\` is an ancestor;
8. read this entire specification;
9. inspect Phase 1 telemetry schema;
10. inspect Phase 2 sessions/pulls;
11. inspect Phase 3 event engine;
12. inspect Phase 5 analytics and baselines;
13. inspect VehicleConfiguration / Modification temporal logic;
14. inspect Phase 6 MCP tool shapes;
15. inspect Phase 7 grounding/evidence structures;
16. inspect Phase 8 knowledge additions only to ensure no conflict;
17. inspect migration head and existing domain conventions;
18. inspect benchmark / acceptance infrastructure before adding new pipelines.

Do not create another Phase 9A branch.

Do not work directly on main.

Do not force-push.

Do not rewrite pushed history.

---

## 2. Phase 9A purpose

Phase 9A must define and persist deterministic features suitable for future predictive learning.

It must answer:

- what feature exists;
- what the feature means;
- what units it uses;
- from which source data it was derived;
- for which vehicle/session/pull/configuration it applies;
- which algorithm/version created it;
- when in time the feature was observable;
- whether it is safe to use for a requested prediction horizon;
- whether data quality was sufficient;
- whether future information leaked into the feature;
- whether it is reproducible.

The result should be a stable model-ready interface.

---

## 3. Out of scope

Do NOT implement in 9A:

- XGBoost training;
- LightGBM training;
- Random Forest prediction;
- neural networks;
- anomaly models;
- model registry promotion;
- prediction APIs;
- prediction scores;
- SHAP explanations;
- automated retraining;
- feature store SaaS;
- online feature serving;
- model drift;
- user-facing health scores;
- maintenance predictions;
- component failure probabilities;
- fleet-wide learning;
- new paid LLM work;
- new embedding work unless Phase 8 regression requires no-cost reuse.

Those belong to later phases.

---

## 4. Feature categories

Create a formal taxonomy.

At minimum:

### RAW_CONTEXT
Stable contextual attributes:
- vehicle/platform;
- engine;
- configuration identifier;
- relevant modifications;
- fuel/calibration when recorded.

### SESSION
Whole-session derived features.

### PULL
Pull-specific features.

### THERMAL
Temperature and heat behavior.

### PERFORMANCE
Performance/acceleration behavior.

### BOOST_AIR
Boost/throttle/air related behavior.

### FUEL
Fuel-pressure / fueling behavior from actually recorded signals.

### QUALITY
Data quality/readiness features.

### HISTORY
Past-only historical aggregates.

### TEMPORAL_CONTEXT
Features derived from time/order/history boundaries.

Do not create features for unavailable sensors.

---

## 5. Feature definition model

Introduce a stable FeatureDefinition abstraction.

Suggested fields:

- id/key;
- canonical name;
- category;
- description;
- unit;
- dtype;
- entity scope;
- required signals;
- optional signals;
- minimum quality;
- algorithm identifier;
- algorithm version;
- temporal availability rule;
- nullability;
- expected bounds where logically deterministic;
- tags;
- active/deprecated state.

Definitions must be immutable by version.

Do not silently change a feature formula under the same version.

---

## 6. Feature key naming

Use deterministic names.

Examples:

- \`thermal.iat_start_c\`
- \`thermal.iat_end_c\`
- \`thermal.iat_delta_c\`
- \`thermal.iat_slope_c_per_s\`
- \`thermal.recovery_time_s\`
- \`performance.pull_duration_s\`
- \`performance.relative_to_baseline_pct\`
- \`boost.peak_bar\`
- \`boost.mean_bar\`
- \`fuel.rail_pressure_min_bar\`
- \`fuel.rail_pressure_drop_rate_bar_per_s\`
- \`quality.coverage_ratio\`
- \`quality.max_gap_ms\`
- \`history.prior_pull_count\`

Actual naming must match repository domain vocabulary.

Never encode version in ad hoc string suffixes if a formal version field exists.

---

## 7. Scope

A feature must explicitly declare scope.

Examples:

- VEHICLE
- CONFIGURATION
- SESSION
- PULL
- WINDOW

Do not store a pull feature as though it were a session-wide fact.

---

## 8. FeatureSet

Introduce a FeatureSet / FeatureVector persistence abstraction.

Suggested fields:

- id;
- vehicle_id;
- configuration_id;
- session_id optional;
- pull_id optional;
- scope;
- feature_set_version;
- generated_at;
- source_window_start;
- source_window_end;
- observation_cutoff;
- feature values;
- quality metadata;
- provenance hash;
- source hash;
- generator version.

Prefer normalized storage only if it improves queries/versioning; JSONB may be acceptable for bounded vectors if indexing needs are limited.

Document the decision.

---

## 9. FeatureSetVersion

Create a version object or equivalent containing:

- version identifier;
- feature definition set;
- generator version;
- source schema version;
- selection policy;
- quality policy;
- temporal policy;
- created_at;
- checksum.

A model later must be able to say:

"I was trained with FeatureSetVersion X."

---

## 10. Determinism

Given identical canonical input and the same FeatureSetVersion:

the feature output must be identical.

Test exact or bounded numeric determinism.

Do not depend on wall-clock time, random order or external web/model calls.

---

## 11. Temporal availability

Every feature must know when it becomes available.

Example:

A complete pull-duration feature is only available after the pull ends.

A "current IAT" feature may be available at time T.

A feature using the end of a session cannot be used to predict an outcome at the start of that session.

Encode temporal availability in application logic, not only documentation.

---

## 12. Observation cutoff

Dataset generation must support an \`observation_cutoff\`.

A generated training row must use only information that existed at or before that cutoff.

No future sample may enter the row.

This is mandatory.

---

## 13. Leakage prevention

Implement explicit guards for:

- temporal leakage;
- label leakage;
- future-session leakage;
- future-pull leakage;
- future-event leakage;
- post-outcome analytics leakage;
- cross-configuration leakage;
- cross-vehicle leakage.

Leakage checks must be tested independently.

---

## 14. Temporal split foundation

Phase 9A must prepare for time-aware splits.

Create utilities for:

- chronological split;
- train/validation/test by timestamp;
- walk-forward windows;
- minimum history constraints.

Do not implement model training.

Do not make random 80/20 splitting the default.

---

## 15. Configuration-aware features

Features must preserve effective VehicleConfiguration.

A feature generated from a session must resolve configuration as-of session time.

Historical data must not inherit current modifications.

Store or reference:

- effective configuration;
- active modifications;
- calibration/tune metadata if present;
- fuel metadata if present.

---

## 16. Stage 2 handling

Do not create a generic numeric feature called "stage_2_target".

"Stage 2" may be encoded only as known configuration metadata.

If tuner/map/version is unknown:

preserve unknown values.

Do not invent tune parameters.

---

## 17. Data quality gating

A feature requiring signals must evaluate signal quality.

Examples:

- missing ratio;
- coverage;
- gaps;
- stuck signal;
- invalid samples;
- truncation.

Each feature should either:

- produce a value with quality metadata;
- produce null/UNAVAILABLE;
- fail validation if mandatory quality is not met.

Do not fabricate values by interpolation unless the feature definition explicitly allows a documented deterministic interpolation method.

---

## 18. Missing values

Use explicit missing semantics.

Differentiate:

- UNAVAILABLE_SIGNAL;
- INSUFFICIENT_COVERAGE;
- INVALID_QUALITY;
- NOT_APPLICABLE;
- NOT_OBSERVED_YET;
- COMPUTATION_ERROR.

Do not use numeric zero as a generic missing value.

---

## 19. Units

All numeric features require canonical units.

Use existing canonical unit infrastructure.

Any unit conversion must be deterministic and tested.

Do not mix PSI/bar, C/F, km/h/m/s silently.

---

## 20. Source provenance

For every feature value, the system must be able to reconstruct:

- source session;
- source pull/window;
- source signals;
- source time range;
- source algorithm/version;
- relevant analytics/events;
- configuration.

A feature is derived evidence, not magic state.

---

## 21. Feature provenance hash

Create a stable provenance/source hash from:

- vehicle/context identity;
- source entity IDs;
- source data fingerprint;
- feature definition version;
- generator version.

This supports immutable recomputation checks.

---

## 22. Idempotency

Regenerating the same feature set for unchanged canonical input should:

- reuse or replace idempotently according to architecture;
- not create uncontrolled duplicates;
- preserve identical hash/value.

Changing source data or version should create a distinct output/version.

---

## 23. Immutable historical outputs

Do not mutate a prior FeatureSet version in place.

If formula changes:

new FeatureSetVersion.

If canonical source data changes:

new computation identity / updated source hash.

Preserve audit history.

---

## 24. Feature registry

Build a central registry of feature definitions.

Avoid feature formulas scattered across API handlers.

Suggested interface:

- register definitions;
- resolve by key/version;
- list active definitions;
- validate dependencies;
- evaluate scope;
- compute.

Feature definitions should be discoverable for later ML pipelines.

---

## 25. Initial feature family — thermal

Implement meaningful deterministic features where signals exist:

- start IAT;
- end IAT;
- min/max/mean IAT;
- IAT delta;
- IAT slope;
- oil temperature start/end/min/max/mean;
- coolant start/end/min/max/mean;
- pull-to-pull thermal increase;
- thermal recovery between pulls;
- pre-pull thermal state;
- cumulative prior pull count.

Do not create oil/coolant features if the signal is not available.

---

## 26. Thermal recovery

Define recovery carefully.

Example:

end of prior pull → start of next pull.

Possible features:

- elapsed recovery seconds;
- IAT recovery delta;
- oil recovery delta;
- coolant recovery delta.

No future pull data may leak into a row predicting the current pull.

---

## 27. Initial feature family — performance

Where deterministic Phase 5 analytics support it:

- pull duration;
- normalized RPM interval times;
- relative performance vs prior comparable pull;
- relative performance vs compatible baseline;
- repeated-pull index;
- rolling past performance mean;
- rolling past performance variance.

Do not derive horsepower if horsepower is not measured.

---

## 28. Historical performance

Historical aggregate features must use only prior compatible observations.

Example:

for pull 5:

history may include pulls 1–4, not 5 future outcome or later pulls.

Test this explicitly.

---

## 29. Initial feature family — boost/air

Where signals exist:

- boost start/end/min/max/mean;
- boost rise rate;
- boost variability;
- throttle min/max/mean;
- throttle closure fraction;
- boost vs historical baseline;
- relevant event counts prior to cutoff.

Do not invent target boost if no target signal exists.

---

## 30. Initial feature family — fuel

Where recorded:

- rail pressure start/end/min/max/mean;
- pressure delta;
- pressure drop rate;
- pressure variability;
- actual-vs-commanded error only if commanded signal exists;
- historical deviation.

Do not use a static universal HPFP threshold.

Do not create target pressure from Phase 8 documentation as a measured feature.

Technical references remain KnowledgeEvidence, not raw features.

---

## 31. Initial feature family — data quality

At minimum:

- observation count;
- expected/actual coverage if known;
- coverage ratio;
- missing sample count;
- max gap duration;
- median sample interval;
- sample interval variability;
- stuck-signal count;
- dropout/event count;
- truncation flags;
- signal availability bitmap or bounded representation.

These features are useful later for prediction confidence and gating.

---

## 32. Event-derived features

Phase 3 events may be used as derived features only when temporally valid.

Examples:

- count of boost-drop events before cutoff;
- count of telemetry-gap events before cutoff;
- prior-session thermal event count.

Do not include an event that is defined by the outcome being predicted unless explicitly building a post-hoc dataset.

Document feature/label conflicts.

---

## 33. Analytics-derived features

Reuse Phase 5 deterministic analytics rather than recomputing duplicate formulas.

Feature generator should call domain services or reusable analytics logic.

Do not copy/paste algorithms into ML code.

---

## 34. Raw telemetry aggregation

When features require telemetry:

use bounded deterministic windows.

Avoid pulling millions of points into memory unnecessarily.

Prefer database-side aggregates or existing domain services when they preserve semantics.

---

## 35. Numerical stability

Handle:

- NaN;
- infinity;
- divide by zero;
- empty windows;
- one-sample windows;
- duplicate timestamps.

Invalid numerics must never persist silently.

---

## 36. Feature validation

Each generated FeatureSet must pass validation:

- definition exists;
- correct scope;
- dtype;
- finite numeric values;
- canonical units;
- valid temporal bounds;
- valid vehicle/configuration scope;
- valid provenance;
- quality state.

Reject invalid feature sets.

---

## 37. DatasetDefinition

Create a typed dataset specification abstraction.

Suggested fields:

- dataset name/version;
- row entity/scope;
- feature set version;
- selected feature keys;
- observation cutoff rule;
- eligibility filters;
- configuration compatibility;
- history requirements;
- quality requirements;
- optional label definition placeholder;
- split policy;
- created_at/checksum.

In 9A, label may remain optional/placeholder.

---

## 38. DatasetBuilder

Implement deterministic dataset assembly.

It must:

- select eligible entities;
- resolve feature sets;
- enforce observation cutoff;
- enforce configuration rules;
- enforce quality policy;
- produce stable row order;
- record excluded rows/reasons;
- compute dataset checksum.

---

## 39. Dataset row identity

Every row must have stable identifiers:

- vehicle;
- configuration;
- session;
- pull/window;
- observation cutoff;
- feature set version.

Do not rely on dataframe row index as identity.

---

## 40. Dataset export

Support a safe model-ready export format.

CSV/Parquet may be appropriate.

Prefer Parquet if dependencies and ecosystem fit.

Protect against spreadsheet formula injection if CSV is supported.

Do not include secrets or large raw telemetry blobs.

---

## 41. Dataset manifest

Every exported dataset gets a manifest:

- dataset version;
- SHA/checksum;
- row count;
- feature list;
- feature version;
- time bounds;
- vehicle count;
- configuration count;
- excluded rows;
- missing-value stats;
- quality stats.

Later model artifacts must reference this manifest.

---

## 42. Reproducibility

Given:

- same repository SHA;
- same database snapshot/source hashes;
- same DatasetDefinition;

dataset output must be reproducible.

Test checksums on controlled fixtures.

---

## 43. Baseline feature matrix

Build at least one controlled model-ready dataset from project synthetic/golden telemetry.

Suggested row scope:

PULL.

Use a bounded set of meaningful features from:

- thermal;
- performance history;
- boost;
- fuel if available;
- data quality;
- configuration context.

Do not include future outcome values.

---

## 44. Synthetic dataset role

Synthetic data is allowed for engineering validation.

Clearly label:

- synthetic;
- real vehicle;
- imported fixture.

Do not claim predictive real-world validity from synthetic data.

---

## 45. Real data compatibility

Feature pipeline must work with real imported/live sessions without formula changes.

If the repository includes real-like fixture data, exercise it.

Do not require the user's physical vehicle for CI.

---

## 46. Feature availability matrix

Create a report/matrix:

feature × source/capability.

Examples:

- synthetic generator;
- CSV import;
- generic OBD;
- richer future sources.

This prevents later models from depending on features impossible to collect in production.

---

## 47. Minimum viable prediction inputs

Document which features are broadly collectable vs source-specific.

Example categories:

- CORE;
- OPTIONAL;
- SOURCE_SPECIFIC.

9B should be able to choose models based on feature availability.

---

## 48. Feature selection is not model training

Do not use target labels to select features in Phase 9A.

No supervised correlation-based optimization yet.

Use domain/availability-based initial selection.

---

## 49. Statistical profiling

For generated datasets provide deterministic profiling:

- count;
- null rate;
- min/max;
- mean/std where meaningful;
- quantiles;
- unique count for categorical;
- distribution by configuration.

This is diagnostic, not model fitting.

---

## 50. Outlier reporting

Report suspicious values.

Do not automatically delete outliers.

Classify:

- quality failure;
- possible real extreme;
- synthetic boundary.

Later models may decide policies.

---

## 51. Configuration distribution

Dataset report must show row counts by configuration.

Avoid hidden imbalance.

Example:

stock = 95%
stage2 = 5%

This matters later for model validity.

---

## 52. Vehicle distribution

Dataset report must show row counts by vehicle.

In current single/few vehicle state, document limited generalization.

Do not claim fleet-general models.

---

## 53. Time distribution

Report earliest/latest observation and temporal density.

This supports later chronological splitting.

---

## 54. Future Phase 9B interface

9A should expose a clean interface for 9B such as:

- load DatasetDefinition;
- materialize dataset;
- return X + metadata;
- optional future y/label attachment;
- split utilities.

Do not couple to a specific ML library.

---

## 55. Feature computation API

Add internal/application services first.

A bounded read-only REST/API may expose:

- FeatureDefinition list;
- FeatureSet metadata;
- feature values;
- dataset definitions/status;
- dataset manifest.

Avoid exposing unrestricted compute queries.

---

## 56. MCP exposure

Do not expose ML training through MCP.

A small read-only feature metadata tool may be useful later, but 9A should only add MCP surface if required by architecture.

Prefer deferring PredictionEvidence-facing tools to 9D/9E.

---

## 57. Frontend

Keep UI minimal.

Add an engineering Feature/Dataset inspector if useful:

- feature definitions;
- versions;
- generation status;
- dataset manifest;
- quality/missing stats.

Do not build Predictive Intelligence UI yet; that belongs to 9H.

---

## 58. Persistence migration

Use additive migration(s).

Do not edit historical migrations.

Test:

- fresh upgrade;
- existing Phase 8 DB upgrade;
- downgrade where safe;
- re-upgrade.

Preserve Timescale/pgvector/knowledge tables.

---

## 59. Indexes

Add indexes based on actual query patterns:

- vehicle;
- configuration;
- session/pull;
- version;
- generated_at.

Do not over-index JSON blindly.

---

## 60. Batch computation

Feature generation should support bounded batches.

Control:

- max sessions/pulls;
- memory;
- transaction size;
- timeout.

Do not load complete telemetry history into RAM.

---

## 61. Incremental computation

Support:

- compute features for new finalized session;
- recompute specific FeatureSetVersion;
- detect unchanged input.

Do not force full-history recompute on every new session.

---

## 62. Recompute policy

A new FeatureSetVersion may require backfill.

Backfill must be explicit.

Do not silently rewrite all rows.

Provide dry-run/count estimate.

---

## 63. Concurrency

Concurrent feature generation must not produce duplicate inconsistent rows.

Use appropriate unique constraints/locking/idempotency.

Test two workers on same input.

---

## 64. Failure recovery

If one row/entity fails:

- record failure safely;
- continue bounded batch where appropriate;
- allow retry;
- do not commit half-valid FeatureSet.

Use transactional boundaries.

---

## 65. Feature generation run

Create a FeatureGenerationRun or equivalent if useful.

Fields:

- id;
- feature set version;
- requested scope;
- started/ended;
- counts;
- success/failure;
- error categories;
- source snapshot;
- trace ID.

Do not persist stack traces with secrets.

---

## 66. Observability metrics

Add metrics such as:

- feature_generation_runs_total;
- feature_sets_generated_total;
- feature_generation_failures_total;
- feature_generation_duration_seconds;
- feature_null_values_total;
- leakage_rejections_total;
- dataset_rows_total;
- dataset_excluded_rows_total;
- dataset_build_duration_seconds.

Avoid high-cardinality labels.

---

## 67. Tracing

Trace:

~~~text
feature generation
→ source resolve
→ configuration resolve
→ telemetry/analytics read
→ feature compute
→ validation
→ persistence
~~~

Dataset build:

~~~text
dataset build
→ candidate selection
→ feature resolve
→ temporal validation
→ eligibility
→ manifest
~~~

---

## 68. Logging

Log IDs/versions/counts, not full telemetry.

Include:

- run ID;
- feature version;
- row/entity;
- exclusion reason;
- duration;
- trace ID.

Do not log huge feature matrices.

---

## 69. Performance

Create a benchmark.

At minimum:

- 100 pulls;
- 1,000 pulls if fixture generation is cheap;
- bounded telemetry sample volume.

Measure:

- feature generation throughput;
- DB read time;
- compute time;
- persistence time;
- dataset materialization time;
- memory.

Do not claim production SLA.

---

## 70. Leakage test fixtures

Create explicit malicious/edge fixtures.

Examples:

### Future pull leakage
Feature row for pull 2 accidentally sees pull 3.

Expected:
rejected.

### Future event leakage
An event recorded after cutoff enters current row.

Expected:
rejected.

### Current outcome leakage
Dataset intended to predict pull duration includes final pull duration.

Expected:
dependency/label conflict detection when label is defined later or mark as post-outcome-only.

### Cross-vehicle
History from vehicle B enters vehicle A.

Expected:
rejected.

### Cross-config
Incompatible configuration history used without allowed policy.

Expected:
rejected.

---

## 71. Leakage metadata

Feature definitions should have an availability class like:

- PRE_EVENT;
- DURING_WINDOW;
- POST_WINDOW;
- HISTORICAL_ONLY.

This supports later label/horizon checks.

---

## 72. Prediction horizon foundation

Define a PredictionHorizon abstraction or helper.

Examples later:

- NEXT_PULL;
- NEXT_SESSION;
- 5_MINUTES_AHEAD;
- END_OF_CURRENT_PULL.

9A may implement typed horizon semantics without models.

Feature eligibility depends on horizon.

---

## 73. Horizon validation

Example:

For NEXT_PULL prediction:

current session prior pulls may be valid;
next pull outcome is not.

Test feature filtering by horizon.

---

## 74. Label definition foundation

Introduce a label specification interface without training models.

Examples future labels:

- next_pull_performance_degradation;
- thermal_degradation_next_pull;
- fuel_pressure_deviation_next_pull.

Do not finalize all labels yet.

The interface must allow later deterministic labels with temporal boundaries.

---

## 75. No circular labels

Document that using existing deterministic event output as a label can be useful but may merely teach the model to imitate a rule.

Later phases must distinguish:

- detector imitation baseline;
- genuinely predictive target.

9A should expose metadata to identify source of labels.

---

## 76. Feature lineage graph

Provide machine-readable lineage:

feature
→ source signals/services
→ source window
→ algorithm/version.

This can be JSON metadata.

No need for a graph database.

---

## 77. Documentation

Create:

- \`docs/architecture/phase-9a-feature-engineering.md\`
- \`docs/runbooks/feature-generation.md\`
- \`docs/runbooks/dataset-builder.md\`
- \`docs/validation/phase-9a-acceptance.md\`
- \`docs/validation/phase-9a-traceability-ledger.md\`

Update:

- roadmap;
- README;
- architecture overview;
- testing strategy;
- observability docs.

---

## 78. ADRs

At minimum document:

- FeatureSet storage representation;
- feature versioning strategy;
- dataset export format;
- temporal/leakage policy.

---

## 79. Independent acceptance

Create an independent evaluator such as:

\`scripts/evaluate_features.py\`

with a target equivalent to:

\`make phase9a-acceptance\`

It must use actual domain/database paths.

Do not merely wrap unit tests.

---

## 80. Acceptance dataset

Use controlled data containing:

- at least two vehicles;
- multiple configurations;
- multiple sessions;
- repeated pulls;
- thermal variation;
- boost/fuel variation;
- quality problems;
- chronological history.

Ensure enough diversity to test isolation and temporal behavior.

---

## 81. Acceptance scenarios

At minimum:

1. feature registry loads;
2. deterministic recompute identical;
3. version change creates distinct FeatureSet;
4. session configuration resolved historically;
5. pull thermal features correct;
6. pull performance features correct;
7. boost features correct;
8. fuel features correct when available;
9. unavailable fuel signal remains unavailable;
10. quality features correct;
11. prior-history feature excludes current/future;
12. future pull leakage rejected;
13. future event leakage rejected;
14. cross-vehicle history rejected;
15. cross-config incompatible history rejected;
16. horizon filters features correctly;
17. dataset rows stable;
18. dataset checksum reproducible;
19. missing/invalid rows explain exclusions;
20. concurrent compute idempotent.

---

## 82. Acceptance metrics

Report:

- feature definitions count;
- FeatureSets generated;
- deterministic equality rate;
- leakage violations detected;
- invalid persisted features;
- cross-vehicle leaks;
- cross-config leaks;
- unavailable-signal fabrication;
- dataset checksum stability;
- dataset excluded rows by reason;
- benchmark metrics.

Targets:

- deterministic equality = 100%;
- invalid persisted features = 0;
- undetected deliberate leakage = 0;
- cross-vehicle leaks = 0;
- incompatible cross-config leaks = 0;
- fabricated unavailable values = 0;
- reproducible dataset checksum = 100% on controlled fixtures.

---

## 83. Unit tests

Test:

- feature definition validation;
- units;
- temporal availability;
- scope;
- quality;
- missing reasons;
- registry;
- each feature family;
- history calculations;
- horizon filtering;
- leakage guards;
- dataset builder;
- manifest;
- checksum;
- export;
- idempotency.

---

## 84. Database integration

Use disposable real DB.

Test:

- migrations;
- persistence;
- version uniqueness;
- recompute;
- batch failure;
- concurrent generation;
- dataset build query behavior.

---

## 85. Phase 1–5 integration

Feature generation must reuse canonical domain behavior.

Run regressions proving no changes to:

- telemetry;
- pulls;
- events;
- analytics.

---

## 86. Phase 6–8 regression

Run deterministic regressions for:

- MCP;
- agents;
- investigation;
- supervisor;
- Phase 7D harness;
- RAG/knowledge.

Do not rerun paid Phase 7D Luna suite automatically.

Do not repurchase Phase 8 embeddings unless inputs/index changed and explicit Phase 8 command is invoked.

---

## 87. Security

Feature/dataset pipelines must not:

- expose secrets;
- execute arbitrary expressions;
- eval feature formulas from untrusted text;
- accept arbitrary SQL;
- write outside bounded export directory;
- permit path traversal.

If dataset export path is configurable:
validate it.

---

## 88. Resource bounds

Define:

- max rows per API request;
- max feature count;
- max batch size;
- export size behavior;
- timeout.

Large dataset generation should be CLI/job-style, not unrestricted synchronous HTTP.

---

## 89. API authorization

Feature computation/admin operations require appropriate operator/admin auth.

Read-only feature metadata may use existing auth model.

No public unauthenticated dataset export.

---

## 90. Synthetic benchmark generator

Reuse existing synthetic telemetry generator.

Add deterministic fixture profiles if needed:

- stable;
- thermal degradation;
- boost deviation;
- fuel deviation;
- poor quality.

Do not alter existing generator semantics in ways that break prior acceptance.

---

## 91. Baseline profiling report

Generate a feature profiling artifact for the acceptance dataset.

Include:

- feature name;
- unit;
- availability;
- null rate;
- min/max/mean;
- quality;
- configuration distribution.

This becomes the starting point for 9B model design.

---

## 92. Recommended 9B candidate features

At the end of 9A produce a documented shortlist of candidate features for 9B.

Categories:

- thermal risk;
- next-pull performance;
- fuel deviation.

Do not train models yet.

Rank candidates by:

- semantic relevance;
- availability;
- leakage safety;
- source coverage;
- stability.

Not by target performance.

---

## 93. Phase 9 roadmap status

Update roadmap to show:

- 9A current/completed when done;
- 9B Predictive Models next;
- 9C Anomaly Detection;
- 9D Prediction Service;
- 9E PredictionEvidence;
- 9F Agent Integration;
- 9G Evaluation/Calibration;
- 9H Predictive Intelligence UI.

Do not mark later phases implemented.

---

## 94. Make targets

Add repository-conventional equivalents:

- \`make test-features\`
- \`make phase9a-acceptance\`
- \`make test-feature-integration\`
- \`make benchmark-features\`
- \`make feature-observability\`

Integrate deterministic 9A into canonical full verification.

---

## 95. Browser E2E

If a Feature inspector UI is added, test:

- feature definitions;
- feature set details;
- dataset manifest;
- no prediction UI claims.

Keep it minimal.

If no UI is justified, document that 9H owns user-facing predictive UI; do not add pointless UI solely for test count.

---

## 96. Clean-state validation

From fresh disposable state:

- migrations;
- synthetic fixture generation;
- feature generation;
- dataset build;
- acceptance;
- integration;
- regressions;
- observability;
- security.

---

## 97. Final exact-head validation

After all changes committed:

- clean tree;
- capture exact HEAD;
- run full local relevant validation;
- push;
- ensure origin equals HEAD;
- monitor exact-head GitHub checks.

Any fix after validation creates a new HEAD and requires rerunning relevant gates.

---

## 98. PR

Open PR against main.

Suggested title:

\`feat: add Phase 9A feature engineering foundation\`

PR must remain unmerged.

User will merge manually.

PR body should include:

- feature architecture;
- registry/versioning;
- feature families;
- leakage controls;
- dataset builder;
- reproducibility;
- benchmark;
- acceptance metrics;
- migrations;
- observability;
- security;
- regressions;
- 9B candidate feature shortlist;
- final SHA.

---

## 99. Remote checks

Final SHA must pass current equivalents of:

- CI/quality;
- integration E2E;
- Security;
- CodeQL Python;
- CodeQL JavaScript/TypeScript;
- dependency review;
- canonical Docker/full-stack;
- Phase 9A gate if added.

Do not rely on older SHA checks.

---

## 100. Definition of Done — architecture

- [ ] FeatureDefinition;
- [ ] FeatureSet;
- [ ] FeatureSetVersion;
- [ ] deterministic registry;
- [ ] provenance;
- [ ] configuration context;
- [ ] temporal availability;
- [ ] observation cutoff;
- [ ] horizon foundation;
- [ ] leakage policy;
- [ ] dataset definition/builder;
- [ ] reproducible manifest.

---

## 101. Definition of Done — features

- [ ] thermal family;
- [ ] performance family;
- [ ] boost/air family;
- [ ] fuel family when signals exist;
- [ ] data-quality family;
- [ ] prior-history features;
- [ ] explicit unavailable handling;
- [ ] canonical units.

---

## 102. Definition of Done — safety/integrity

- [ ] future leakage blocked;
- [ ] cross-vehicle blocked;
- [ ] incompatible cross-config blocked;
- [ ] no fabricated sensor values;
- [ ] no target values from RAG treated as measured feature;
- [ ] no arbitrary code/eval;
- [ ] export path safe;
- [ ] auth enforced.

---

## 103. Definition of Done — dataset

- [ ] deterministic row identity;
- [ ] chronological split helpers;
- [ ] walk-forward helper;
- [ ] stable ordering;
- [ ] profiling;
- [ ] exclusions report;
- [ ] checksum;
- [ ] model-ready export;
- [ ] synthetic acceptance dataset.

---

## 104. Definition of Done — validation

- [ ] unit tests;
- [ ] DB integration;
- [ ] independent 9A acceptance;
- [ ] benchmark;
- [ ] observability;
- [ ] security;
- [ ] Phase 0–8 deterministic regressions;
- [ ] clean-state;
- [ ] exact final SHA GitHub green.

---

## 105. Final report

Return at least:

1. branch;
2. base SHA;
3. final SHA;
4. PR URL/state;
5. migration revision;
6. FeatureDefinition design;
7. FeatureSet storage;
8. FeatureSetVersion;
9. feature definition count;
10. thermal feature count;
11. performance feature count;
12. boost/air feature count;
13. fuel feature count;
14. quality feature count;
15. history feature count;
16. units strategy;
17. missing-value semantics;
18. quality gating;
19. provenance;
20. configuration awareness;
21. Stage 2 behavior;
22. temporal availability;
23. observation cutoff;
24. leakage guards;
25. horizon foundation;
26. DatasetDefinition;
27. DatasetBuilder;
28. export format;
29. manifest/checksum;
30. acceptance dataset;
31. acceptance metrics;
32. deterministic equality;
33. leakage test results;
34. cross-vehicle results;
35. cross-config results;
36. profiling;
37. benchmark;
38. concurrency/idempotency;
39. failure recovery;
40. API;
41. frontend if any;
42. observability;
43. security;
44. Phase 0–8 regression;
45. clean-state validation;
46. GitHub exact-SHA checks;
47. recommended 9B candidate features;
48. known limitations;
49. confirmation 9B–9H not implemented;
50. confirmation PR unmerged.

End with exactly:

\`PHASE 9A — FEATURE ENGINEERING FOUNDATION: VERIFIED\`

only if all mandatory requirements are satisfied.

Otherwise continue fixing anything within your control.

If a genuine external blocker remains, end with:

\`PHASE 9A — FEATURE ENGINEERING FOUNDATION: NOT VERIFIED\`

and document the blocker precisely.

Do not merge the PR.
