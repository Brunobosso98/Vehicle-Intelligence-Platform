# Phase 9A feature engineering foundation

Phase 9A introduces deterministic, versioned pull features and a leakage-aware dataset builder.
The feature package consumes canonical Phase 1 telemetry, Phase 2 sessions and pulls, Phase 3
events, and vehicle configuration/modification history. It does not change those source records.
The pipeline produces persisted feature snapshots and reproducible model-ready datasets; it does
not train a model or issue a health score.

## Ownership and data flow

`vehicle_platform.features` owns typed feature definitions, the trusted calculator registry,
feature generation, provenance, temporal validation, dataset materialization, profiling, splits,
and export. It may read canonical telemetry/session/pull/event/configuration tables. Migration
0013 owns only `feature_*` and `dataset_*` persistence. Telemetry, analysis, event, analytics,
MCP, agent, investigation, supervisor, and knowledge modules retain their existing ownership.

```text
canonical vehicle evidence
        ↓ bounded reads at an observation cutoff
typed FeatureContext + immutable FeatureSetVersion
        ↓ trusted Python calculators (no eval or user formulas)
FeatureSet JSONB values + source/provenance hashes
        ↓ cutoff, quality, ownership, configuration and lineage checks
DatasetDefinition → ordered rows + profile + exclusions + manifest/checksum
        ↓ operator CLI only
bounded JSONL and manifest under apps/api/.artifacts/phase9a/
```

There is no public feature API, MCP feature tool, or feature inspector UI in 9A. Generation and
dataset export run as local operator commands with the application's configured database access.
The CLI applies strict batch, row, payload and output bounds. Authentication for a future remote
admin API must reuse the platform's operator authorization before any network exposure. The
user-facing predictive interface belongs to Phase 9H.

## Definitions and version identity

`FeatureDefinition` fixes a canonical dotted key, meaning, category, unit, scalar type, entity
scope, source-signal requirements, minimum quality, algorithm/version, temporal availability,
nullability, logical bounds and tags. The registry maps each active definition to trusted code.
Formulas are not loaded from database rows or caller input. Numeric inputs and outputs use
canonical SI units: temperature K, pressure Pa, speed m/s, acceleration m/s², time s, angular
speed RPM and percent as percentage points. The feature's definition records units; conversion for
presentation is not part of the persisted feature vector.

The current registry has 79 definitions: thermal 22, boost/air 14, quality 14, fuel 9,
raw context 7, history 5, performance 6 and temporal context 2. `SESSION` and `PULL` remain
taxonomy categories; current definitions are assigned to their semantic family and are scoped to
pull/vehicle/configuration. There are no session-category-only definitions yet. The feature keys
with `boost_air` use the same canonical boost/air family.

Performance features reuse the analytics domain's bounded monotonic crossing logic for three
fixed 1,000-RPM bands: 2,500–3,500, 3,500–4,500 and 4,500–5,500 RPM. Values are seconds per
1,000 RPM. A feature stays unavailable when the input lacks a boundary crossing, has a gap above
the configured maximum, or reverses RPM before completing the interval.

Each definition also carries an acquisition class in its versioned manifest. `CORE` has no
specific telemetry signal dependency, `OPTIONAL` depends only on standard generic OBD-II PIDs,
and `SOURCE_SPECIFIC` needs at least one signal outside that generic set. The acceptance profile
emits a machine-readable feature-by-source matrix for the synthetic generator, CSV replay,
generic OBD-II, and a richer future source. CSV entries are conditional on mapped input columns;
generic OBD-II entries still require per-vehicle preflight. The matrix describes signal-set
compatibility and does not guarantee a live source can provide a measurement.

`FeatureSetVersion` hashes ordered definitions plus generator/source-schema versions and
selection, quality and temporal policies. Reusing a version with a different checksum raises a
conflict; formula or policy changes require a new version. Feature vectors are immutable rows
keyed by vehicle, pull, version and source snapshot hash. A recompute over identical source
content reuses the same row; changed source content creates a separate snapshot and leaves the
older row intact.

The current generator, source-snapshot shape and registry are recorded under
`phase9a-pull-v2` (`phase9a-feature-generator-v2`, `canonical-telemetry-v2`). The previously
persisted `phase9a-pull-v1` definitions and snapshots remain immutable.

Each feature value stores its value or explicit missing reason, unit, quality, availability time,
source window, source signal/entity IDs and calculation details. FeatureSet provenance adds the
vehicle/session/pull/configuration/modification context, source records, observation cutoff,
generator identity and stable source/provenance hashes. IDs stay in persisted lineage, never in
metric labels.

## Quality, context and time

No interpolation is used. Invalid-quality samples do not enter physical aggregates; the quality
family still counts raw and invalid observations. Signal coverage and pull completeness gate
features that require sufficient coverage. A sensor absent from the source remains null with
`unavailable_signal`; missing does not mean zero. Stage/calibration/fuel/hardware context is
populated only from recorded configuration metadata. “Stage 2” is not a target or universal
operating range, and RAG/documentary values are never persisted as measured features.

All source timestamps must be timezone-aware. Telemetry requires both `observed_at` and
`ingested_at` at or before the feature observation cutoff. Entity creation, configuration and
modification records must also be known by that cutoff. Historical pulls and events must end
strictly before the target pull starts, belong to the same vehicle and effective configuration,
and have compatible active modifications. Future pulls, late-created events, future-ingested
samples, and mismatched ownership are rejected or excluded with a bounded reason code. No history
crosses vehicle/configuration boundaries.

Pre-pull IAT, oil and coolant evidence uses the latest vehicle sample observed strictly before the
pull start within a five-minute lookback, with sample observation, ingestion and owning session
creation constrained by the cutoff. It is stored separately from current-pull observations, so it
does not affect pull coverage or quality aggregates. A latest invalid-quality pre-pull sample stays
invalid rather than falling back to an older good value. These rows are part of the source hash and
feature provenance. If no bounded pre-pull observation exists, the thermal feature is unavailable.

Definitions classify values as pre-event, during-window, post-window or historical-only. Dataset
cutoff policies are row start, row end or a global cutoff; the builder selects the latest feature
snapshot that is valid for that row and cutoff. Horizon metadata supports next pull, next session,
end of current pull and bounded minutes-ahead foundations. It filters availability; Phase 9A does
not create a target label or predict an outcome.

## Dataset contract

`DatasetDefinition` fixes a pull-row scope, unique name/version, feature-set version, selected and
required feature keys, cutoff/horizon, minimum history and quality, configuration-mixing policy,
split policy and optional target-label lineage. Label sources cannot overlap selected model input
features. `DatasetBuilder` returns rows with deterministic identity derived from vehicle,
configuration, session, pull, cutoff and feature version. Rows are stably ordered by time and
entity. Excluded rows retain a bounded reason code; an unavailable optional feature is represented
in the row's missing map.

The manifest includes definition and feature-version checksums, selected feature keys, cutoff,
row/time/entity distributions, missingness, quality, exclusions, source role, JSONL format and the
dataset checksum. The checksum covers the dataset definition, row identities and feature values,
missingness, source hashes and sorted exclusions. Statistical profiling reports null rates,
numeric quantiles/min/max/mean/dispersion, categorical counts, quality, time/configuration/vehicle
distributions, quality-failure exclusions, and possible extremes without deleting outliers.
Numeric synthetic extremes are marked `synthetic_boundary`; real or imported extremes are marked
`possible_real_extreme` for review.

Chronological and walk-forward split helpers preserve ordering. Exports use canonical JSON Lines
plus a JSON manifest and are atomically written under the fixed approved artifact directory. Path
components are constrained; output is capped at 64 MiB. Database reads are bounded to 100,000
candidate pulls, 32 MiB of source feature payload and 200,000 lineage entities.

## 9B candidate shortlist

This is a domain and collection-readiness ranking for initial 9B experiments, not a model result or
supervised feature selection. All history inputs must be strictly prior to the prediction row and
compatible with its vehicle, effective configuration and modifications.

| Rank | Candidate family      | Candidate inputs                                                                                             | Availability and leakage basis                                                                | Stability basis                                                                    |
| ---: | --------------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
|    1 | Thermal progression   | Prior-pull IAT start/delta, pre-pull thermal state, IAT recovery, prior thermal-pull count                   | IAT is broadly collectable; recovery and history use completed prior pulls only               | Canonical temperature units, bounded windows, explicit missingness                 |
|    2 | Next-pull performance | Prior comparable pull duration, normalized RPM-interval times, rolling compatible performance                | Requires finalized prior pulls and their RPM/speed coverage; current-pull outcome is excluded | Reuses deterministic Phase 5 analytics and measured intervals                      |
|    3 | Boost deviation       | Prior peak/mean boost, rise behavior, compatible-baseline deviation, prior boost-drop count                  | Boost pressure is source-dependent; only events strictly before cutoff are eligible           | Uses recorded pressure and prior compatible baselines; no target boost is inferred |
|    4 | Fuel deviation        | Recorded rail-pressure minimum/delta/variability; actual-versus-commanded error only when both signals exist | Source-specific and often unavailable; missing signals remain unavailable                     | No universal pressure threshold or documentation-derived measured value            |
|    5 | Data-quality gating   | Coverage, invalid/missing counts, maximum gap, sample-interval variability, availability bitmap              | Available from observed telemetry and quality metadata; cutoff applies to every source        | Deterministic counts/ratios support eligibility and confidence analysis            |

9B should re-rank these inputs against actual source coverage, temporal safety, semantic relevance and
stability before model experiments. No target labels or target-performance measurements informed
this shortlist. It does not claim fleet representativeness or predictive validity.

## Operations and failure recovery

`scripts/generate_features.py` accepts one session, an optional aware cutoff, a 1–100 pull limit
and a no-write `--dry-run` estimator. Dry-run is capped at 30 seconds; generation and dataset
build jobs are capped at five minutes with 60-second database command timeouts. Successful pulls persist independently. Failures are
categorized; rerunning is idempotent for unchanged source, and a corrected source hash creates a
new immutable result. A version/checksum mismatch requires a feature version bump. Dataset
materialization is a separate operator command and persists a completed dataset build receipt
before writing its bounded export files.

The pipeline adds bounded OpenTelemetry counters/histograms for generation, nulls, leakage
rejections, dataset rows/exclusions and durations. Generation spans separate configuration
resolution, telemetry reads, calculation and persistence. The benchmark records database-read,
feature-compute and persistence time separately for each generated pull, along with total generation,
dataset materialization and memory. Feature and dataset spans carry counts and version, not vehicle
IDs, raw samples, credentials or SQL. See the
[feature generation runbook](../runbooks/feature-generation.md),
[dataset runbook](../runbooks/dataset-builder.md),
[Phase 9A acceptance](../validation/phase-9a-acceptance.md), and
[ADR 0031](../adr/0031-versioned-feature-engineering-and-temporal-datasets.md).
