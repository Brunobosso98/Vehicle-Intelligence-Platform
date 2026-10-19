# Phase 9C offline anomaly detection

Phase 9C adds retrospective, after-pull statistical deviation scoring over immutable Phase 9A
FeatureSets. It is a separate owner from Phase 3's deterministic event rules and Phase 9B's
supervised next-pull models. A 9C score is not fault detection, a diagnosis, a calibrated failure
probability, a maintenance order, or a universal cross-vehicle comparison.

## Ownership and data flow

`vehicle_platform.anomalies` owns governed detector definitions, eligible reference snapshots,
detector versions, trusted artifact validation, offline scoring, persisted findings, and run
summaries. It reads Phase 9A feature sets and canonical vehicle/session/configuration context. It
does not copy or recompute Phase 9A feature formulas, mutate Phase 3 events, or reuse Phase 9B's
supervised registry. Migration `0015` adds only anomaly-owned tables and triggers.

```text
canonical Phase 9A FeatureSets at an aware cutoff
        ↓ exact vehicle/configuration/modification/source and quality checks
immutable, checksummed reference rows from strictly prior sessions
        ↓ deterministic robust baseline + bounded Isolation Forest candidate
candidate detector versions and internal trusted artifacts
        ↓ validation-only method and threshold selection (whole held-out sessions)
immutable version with frozen validation threshold
        ↓ retrospective bounded batch score (1 to 1000 pulls)
immutable run and per-pull findings with feature associations and abstentions
```

The reference cutoff is the anchor pull's start. The anchor session is excluded, and each selected
reference FeatureSet, pull end, and owning entity must be available before that cutoff. A scoring
request has a separate explicit observation cutoff. Each finding records that scoring cutoff; its
feature values and source windows must be available by it. No target outcome or future samples enter
the model input. The horizon is always `AFTER_PULL_OFFLINE`.

## Cohort and support policy

The default cohort is one vehicle, one effective configuration, one exact active modification set,
one source type and one declared source role. There is no cross-vehicle fallback or pooling. A
reference requires at least 12 rows for robust MAD or 24 for Isolation Forest, three independent
sessions, seven calendar days of pull history, 80% feature coverage during fitting and scoring,
and valid required features.
The reference input is bounded to 10,000 rows and 32 MiB before materialization. Pull completeness
must be at least 0.75; invalid or duplicated timestamps cause quality exclusion. A missing required
signal creates an unsupported/insufficient-signal abstention, never an inferred healthy value.

For cold starts, incompatible context, absent required sensors and low-quality pulls, the service
abstains. Optional missing values remain explicit; only Isolation Forest's optional-feature
imputation is fitted from eligible training rows and is accompanied by a missingness indicator.
No default behavior equates missing sensor data with normal behavior.

## Detectors and score interpretation

The registry has four independent families: thermal, boost/air, comparable RPM performance, and
fuel pressure when the source provides the required pressure signal. The robust baseline uses a
median center, `1.4826 * MAD`, an IQR fallback for zero MAD, and deterministic exclusion for
constant features. Its bounded score is the maximum eligible absolute robust deviation, so adding
features does not inflate the result. The nonlinear candidate is a fixed-seed, single-threaded
Isolation Forest with bounded rows, estimators and feature count. Its score is `-score_samples`.
Both use the same convention: larger scores indicate more unusual observations. Neither score is a
probability.

Phase 9C implements point and contextual deviations at the pull level. Thermal scoring can compare
the pull's starting intake temperature with available pre-pull context; the remaining families use
their declared within-pull features. The derived multi-family summary reports agreement among
eligible family scores without fitting a fifth model. Sequence and persistence detectors are
deferred; repeated findings receive stable correlation-group IDs for later offline analysis.

Boost/air detector definition `2.0.0` excludes Phase 9A's `boost_air.history_deviation_pa`. That
feature already compares a pull to a rolling set of prior pulls; fitting another cohort deviation
on top of it can mark a return to the usual pressure range as unusual after a previous outlier.
Version 2 scores within-pull pressure behavior instead. The canonical 9A feature remains unchanged.

The training-reference 95th percentile is only an initial candidate cutoff. Method comparison and
threshold selection use predeclared validation floors on whole validation sessions. Clean-control
false-positive rates are separate from cross-family injection alarms. The evaluator first freezes
on session 9 and scores session 12. It then expands history through session 11, uses session 12 as
the later model's validation fold, freezes a second version, and opens session 13 as its untouched
test. Each fold's threshold is fixed before its test. Validation-only threshold sensitivity is
reported; test metrics never select a method or threshold.
An Isolation Forest feature contribution is a descriptive robust comparison against the reference,
not a decomposition of the forest score or a causal explanation. Wording is explicitly
“associated statistical deviation, not root cause.”

The internal multi-family summary reports agreement among independently scored families only when
at least two valid family scores exist. It trains no fifth model, does not turn one poor-quality
observation into several anomalies, and makes no diagnostic claim. Repeated findings retain stable
correlation-group IDs for offline analysis; this is not a notification or alert system.

## Persistence and artifact boundary

Migration `0015` adds immutable detector definitions, reference datasets and rows, detector
versions, detection runs, and findings. Database triggers reject updates and deletes. Checksums
bind definitions, selected Phase 9A rows, fit inputs, validation evidence, frozen thresholds,
artifacts and run inputs. A finding contains the source FeatureSet/pull/session/vehicle/configuration,
score and threshold, status, coverage, observed/absent features, bounded reason codes, top
associated deviations, cohort summary, cutoff and provenance hashes.

Joblib artifacts are written atomically beneath the fixed ignored
`apps/api/.artifacts/phase9c/` root, capped at 50 MiB and loaded only through a registered version
ID. The loader checks the exact path, file size and SHA-256 before trusted-code deserialization, then
validates detector schema, definition checksum, cohort manifest, fitted preprocessing, training
metrics, threshold and allowlisted estimator class. Arbitrary artifact paths and estimator import
names are not accepted. Artifact serialization bytes are not claimed to be deterministic; fitted
scores and decisions are checked for deterministic replay.

The CLI is local operator-only and bounded. It has no HTTP, MCP, agent, UI, streaming, promotion or
production scoring endpoint. It refuses a production environment. Phase 9D owns any future scoring
service, 9E owns a future shared evidence contract, 9F agent integration, 9G broader calibration and
drift work, and 9H predictive UI.

## Observability and limits

Metrics cover fit/run state, duration, eligible/excluded reference rows, finding status, score and
threshold distributions, and artifact bytes. Labels are bounded family/method/state/status/reason
values only. Traces separate reference materialization and eligibility, fit, artifact staging and
validation, validation threshold selection, target materialization, scoring and finding persistence.
Entity IDs, VINs, raw samples, feature matrices, checksums and secrets are not metric labels or
logged values.

The independent evaluator uses controlled synthetic telemetry through the real Phase 9A feature
generator, persisted 9C registry, artifact reload and finding database. Its final test folds follow
two clean recovery sessions after validation injections. The last session also uses an unseen
ambient intake-temperature level shift, alternating boost fluctuation and a subtle combined
thermal/boost/performance perturbation; their scenario metadata is evaluation-only. The evaluator
separately records clean-control behavior under the environmental shift and the family decisions
for the hidden interventions. It injects an extreme older-observed but late-ingested sample and a
post-cutoff modification before Phase 9A generation, then independently verifies that both are
excluded. An earlier development run showed false
alarms on immediate post-injection clean pulls when the boost detector used a rolling historical
feature; that report is retained under ignored `.validation/phase9c/` and is not final acceptance.
The evaluator measures local engineering performance only. Passing synthetic injection tests says nothing about real-car sensitivity,
specificity, mechanical condition, fleet generalization or calibration. See the
[operator runbook](../runbooks/anomaly-detection.md), [acceptance report](../validation/phase-9c-acceptance.md),
[evaluation report](../validation/phase-9c-model-evaluation.md), and ADRs 0035–0038.
