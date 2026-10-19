# Phase 9C — Anomaly Detection

You are implementing **Phase 9C — Anomaly Detection** for the Vehicle Intelligence Platform.

## 1. Mission and authoritative scope

Repository: `Brunobosso98/Vehicle-Intelligence-Platform`.
Required branch: `codex/phase-9c-anomaly-detection`.
Immutable baseline at branch creation: merged `main` SHA `105ef5a12f055558c55d87204f3ea5a91af73a13` (Phase 9B PR #42); Phase 9A PR #41 is also merged.

Phase 9 plan:

- 9A Feature Engineering Foundation — complete
- 9B Predictive Models — complete
- **9C Anomaly Detection — THIS TASK**
- 9D Prediction Service — later
- 9E PredictionEvidence — later
- 9F Agent Integration — later
- 9G Evaluation / Calibration — later
- 9H Predictive Intelligence UI — later

Build a scientifically cautious, deterministic and reproducible **offline anomaly detection layer** over the versioned Phase 9A FeatureSets and compatible Phase 9B offline ML infrastructure. Detect statistically unusual observed vehicle/pull behavior relative to eligible peer/history baselines; do not infer mechanical faults, causal diagnoses or component failure probabilities.

A Phase 3 rule-triggered event is different from a Phase 9C model anomaly. Retain both independently, avoiding duplicate or conflicting ownership.

## 2. Start-up procedure (MANDATORY)

1. Inspect `git status`, remotes, current branch, `git log`, and latest remote refs.
2. Fetch `origin`. Switch to `codex/phase-9c-anomaly-detection`, fast-forward only, and verify a clean working tree. Do not create a second 9C branch.
3. Verify baseline `105ef5a12f055558c55d87204f3ea5a91af73a13` is an ancestor and that both Phase 9A and 9B are present. If remote main advances, do not blindly rebase or force-push.
4. Read this COMPLETE specification, `docs/roadmap/README.md`, Phase 9A and 9B prompt/architecture/acceptance/ADRs/model cards, Phase 3 anomaly/event semantics, Phase 5 analytics, current database migrations, `Makefile`, full-validation workflows, security and observability conventions.
5. Inspect actual existing code/types/fixtures and migration head rather than assuming filenames or schema from this document.
6. Record baseline SHA, migration head, dependencies, existing checks and gaps. Implement, validate, document, push and open an unmerged PR. Work autonomously until mandatory criteria pass; do not stop after scaffolding.

## 3. Existing contracts to preserve

- Phase 9A: 79 deterministic, immutable versioned features, `phase9a-pull-v2`, `phase9a-feature-generator-v2`, `canonical-telemetry-v2`, exact temporal availability and provenance, missing-signal reasons, configuration/modification isolation, cutoff-aware datasets. Use existing approved APIs; do not copy feature formulas.
- Phase 9B: `vehicle_platform.ml` owns supervised next-pull labels, chronological splits, ModelSpec/model registry/training runs and trusted offline artifacts; migration `0014` introduced ML tables. Models are engineering-validation candidates, not production. Preserve all existing 9B task semantics and tests.
- Phase 3: event/anomaly deterministic rules already exist. Do not replace them with ML or silently change historical event meaning.
- Phase 6–8: MCP, read-only agent orchestration and documentary RAG exist. NO 9C agent/MCP integration.
- Signals must remain recorded, canonical and source-capability-aware. No synthetic measurements masquerading as real data.
- Real machine behavior, fault diagnosis, OEM safety limits, calibration validity and fleet generalization are NOT established by synthetic fixtures.

## 4. Hard scope boundaries

Implement in 9C:

- governed anomaly detector definitions;
- versioned offline reference datasets and detector fits;
- baseline statistical detector plus a bounded nonlinear unsupervised candidate;
- contextual anomaly evaluation using appropriate vehicle/configuration/history cohorts;
- offline batch scoring with quality and abstention states;
- immutable anomaly finding records, explanation-oriented feature contribution metadata _as descriptive associations only_, references and checksums;
- independent fixture acceptance, benchmarks, tests, observability, runbooks, model/detector cards, traceability ledger.

Do NOT implement:

- public online prediction/scoring API or automatic streaming service (9D);
- PredictionEvidence unified/public contract (9E);
- MCP, agent/supervisor integration (9F);
- fleet deployment, drift operations or probabilistic calibration program (9G/10);
- predictive user UI or alert badges (9H);
- automatic production promotion, retraining, intervention, notifications, ECU write/control, tuning advice, component diagnostics or RUL estimates.
  An **internal offline AnomalyFinding** is allowed in 9C; it is not the future 9E `PredictionEvidence` contract.

## 5. Detection goals and scenarios

At minimum cover 4 signal families whenever the source supports them:

1. thermal behavior: IAT start/delta, recovery and comparable historic pull trends;
2. boost/air behavior: peak/mean/rise and deviations in context;
3. performance: comparable 3,500–4,500 RPM interval behavior and robust comparable baseline;
4. fuel pressure: supply/rail minima or variability ONLY when actual fuel telemetry is available.

Also evaluate sensor quality and impossible/missing values as **quality/abstention** separately, not as proof of a mechanical anomaly. Provide an aggregate multivariate score where justified; report family-level detection and coverage. A single global one-size-fits-all model may not be assumed safe for different vehicles, modifications or acquisition sources.

Examples must include: atypical thermal rise with otherwise normal boost; boost deviation during otherwise normal performance; valid low-pressure fuel signal; missing fuel signal; atypical RPM performance not attributable to incompatible configuration mixing; corrupt/late/duplicated samples; sparse historical vehicle baseline; new vehicle/configuration without support; and repeated correlated anomalies.

## 6. Versioned domain contracts

Define stable, strict schemas, names adapted to repository conventions, for:

- `AnomalyDetectorDefinition`: key, method/family, intent, feature keys, units, expected temporal availability, source capability policy, cohort policy, quality policy, seed, fit parameters, normalization policy, scoring version, thresholds/decision policy, checksums and lifecycle status.
- `AnomalyReferenceDataset`: immutable Phase 9A dataset definition/checksum, cutoff, feature/version/schema, cohort identity and compatibility predicates, selected row lineage, quality and exclusions, source roles, temporal bounds, fingerprints.
- `AnomalyDetectorVersion`: detector definition/version/checksum, algorithm/library versions, reference checksum, fitted preprocessing and artifact checksum, training/source role, acceptance state, performance/validation metadata.
- `AnomalyDetectionRun`: run ID, immutable inputs, cutoff, outputs, counters, timing, algorithm checksum and failure state.
- `AnomalyFinding`: source FeatureSet/pull/session/vehicle/configuration identity, detector version, observation cutoff, score and direction, decision/status, family, reference cohort summary, features observed/absent, coverage, top associated deviations, reason codes and complete provenance. Include status such as `ANOMALOUS`, `INLIER`, `INSUFFICIENT_REFERENCE`, `INSUFFICIENT_SIGNAL`, `LOW_QUALITY`, `INCOMPATIBLE_CONTEXT`, `UNSUPPORTED_SOURCE`, `NOT_EVALUABLE`.
  Use existing storage abstractions when possible; avoid duplicated Phase 9B tables or ML registries. Add migrations additively after current head; do not edit old migrations. All persisted immutable contracts must have DB/test enforcement and versioned changes rather than silent mutation.

## 7. Temporal safety and data boundaries

- A scored observation uses only features recorded/available at its scoring observation cutoff; honor Phase 9A temporal eligibility. **No future samples, target-pull labels or post-cutoff features.**
- Distinguish retrospective **after-pull offline** scoring (can use observed end-of-pull features known by cutoff) from prospective scoring (deferred; not implemented in 9C). All outputs must declare `AFTER_PULL_OFFLINE` horizon.
- Reference cohort must contain records available before the scored observation's observation cutoff; exclude current scored row and its derived duplicates from reference. Evaluate same-session correlation and temporal overlap to prevent leakage.
- Separate fit/reference history from held-out evaluation periods; never learn normalization/threshold from untouched test.
- Replays, late ingestion, later-created modifications and events cannot retroactively alter an immutable already-scored decision. New cutoff/version may produce a new finding.
- Enforce compatible effective configuration, modifications, source capability and units; cross-vehicle pooling is opt-in only with documented stratification and evidence. No identity memorization.
- Historical repeated pull records from the same session should not be treated as independent vehicles. Splits should group by session and chronology.

## 8. Algorithms and score semantics

Implement TWO complementary approaches at minimum:
A. **Robust transparent baseline:** e.g., median/MAD with documented zero-MAD handling and/or robust IQR-based per-family deviations, bounded multivariate aggregation, explicit thresholds established from training/validation references.
B. **Nonlinear unsupervised candidate:** e.g., `IsolationForest` using project-pinned sklearn if compatible; fixed seed, bounded estimators/features/rows, single-thread or controlled concurrency, deterministic normalization. Use an allowlist of safe constructors/hyperparameters.

Anomaly scores are **relative engineering outlier scores**, NOT calibrated probabilities or risk percentages. Document orientation (larger = more anomalous) and model-specific score transforms. Output decision threshold and how it was established. Score baselines/candidates honestly; no requirement to choose the more complex algorithm if simple is equally good. The baseline must remain usable when insufficient data prevents nonlinear fitting.

Preprocessing is fit on eligible reference TRAIN data only; median/imputation/missingness logic must never silently equate missing sensor with healthy. Missing mandatory source-specific signals -> abstention/unsupported, not manufactured fuel anomalies. Reject invalid physical telemetry and invalid schema rather than treating them as valid normal measurements. Preserve source role in artifacts/reports.

Use explainability metadata: strongest normalized deviation features and direction, units and measured-vs-reference distribution, with careful wording `associated statistical deviation, not root cause`. For IsolationForest use descriptive baseline deviations, not false per-feature causal attribution. Do not require SHAP.

## 9. Sparse history, cold start and false-alert controls

Define and document explicit per-cohort minimum historical support, independent session support, chronological span and quality floor. Default to abstaining rather than inventing a robust baseline from 1–2 pulls. For eligible but sparse cohorts: use transparent `INSUFFICIENT_REFERENCE`; optional cohort fallback must be explicitly approved/tested and cannot mix configurations arbitrarily.

Prevent trivial duplicated/repeated alerts from similar highly correlated deviations by designing offline grouping or deduplication identifiers; this is not user notification/alerting. Do not turn one low-quality observation into multiple spurious anomaly families. Define sane bounds for classifying isolated one-point outliers vs persistent patterns; persistence metrics stay observational, not a diagnosis.

## 10. Evaluation design: labels are NOT ground truth

Unsupervised detectors do not require defect labels to train. To test engineering behavior use controlled synthetic injection/scenario fixtures with **hidden anomaly injection metadata for evaluation only**. Never allow injection identifiers, scenario labels, future labels or synthetic condition flags into fitting or scoring features.

Compare robust baseline and IsolationForest to:

- clean nominal normal data across multiple valid configurations;
- thermal-only, boost-only, fuel-only, performance-only perturbations;
- multivariate subtle departures;
- seasonal/thermal context changes that should not automatically be flagged as defects;
- quality corruption/noisy and missing data that should abstain;
- unknown source-capability and incompatible modifications;
- held-out unseen vehicle, configuration and synthetic scenario;
- low sample and constant-feature/zero-MAD cases.

Evaluation should report injection-detection recall, precision/F1 where defined, false-positive rate on clean data, family-level results, acceptance/abstention coverage, confusion matrix/support, candidate/baseline comparisons, stability over temporal folds, threshold sensitivity (validation only), and known failure modes. Predeclare engineering targets appropriate to controlled fixture before final held-out test; never tune the held-out test thresholds after inspection. Avoid misleading claims of real-world sensitivity/specificity.

## 11. Reproducibility and artifact security

- Fixed versioned detector specifications, dataset checksums, feature ordering/types/units, dependency versions, seeds and deterministic stable sorting.
- Repeated fit/score on the same frozen input must yield identical reference row IDs, selected algorithm, anomaly decisions and scores within documented strict tolerance. Serialized bytes need not be identical if underlying library serialization is nondeterministic; disclose this.
- Trusted artifacts ONLY under an internal ignored fixed root; bounded size, atomic writes, integrity/checksum, schema compatibility check and trusted-code loading. Never load arbitrary user artifact, untrusted pickle/joblib file, estimator class import path, SQL or Python expression.
- No unsafe path traversal, dynamic imports from user input, unrestricted admin HTTP, unrestricted training resources or secrets in logs.
- Verify pristine artifact reload and offline score match; corrupted/changed artifact must be rejected with a precise safe error.
- Deterministic idempotent scoring and concurrency behavior; no duplicate findings for equivalent immutable run/model/cutoff/input identity.

## 12. CLI and persistence

Implement bounded operator-only commands using project conventions, such as:

- `make test-anomalies`;
- `make phase9c-acceptance`;
- `make phase9c-detect` or a safe explicit fit/score CLI;
- `make benchmark-anomalies`;
- `make anomaly-observability`.

Require explicit aware cutoff, source role and detector scope; bounded vehicle/session/pull selection, row count, artifact sizes, CPU/memory/wall-time controls. Production execution should be disabled unless the existing project model deliberately permits a safe offline admin mode; never create internet-exposed endpoints. Provide a readable runbook with end-to-end examples and failure/abstention cases.

Add additive migration and validate fresh upgrade, current Phase 9B head -> new head, safe downgrade to previous migration and re-upgrade. Old models, FeatureSets, analytics/events, agents and RAG must remain unchanged.

## 13. Tests and independent acceptance

Tests must include, at minimum:

- family-specific normal/anomaly decisions and deterministic fixtures;
- missing/unsupported fuel and other sensors, zero/negative/invalid values, null reasons, units;
- corrupted/late/future input and observation cutoff enforcement;
- after-pull feature horizon eligibility and future target-source rejection;
- cross-vehicle/config/modification/source segregation;
- sparse history, zero-MAD constant feature, time gaps, entirely missing family;
- version/checksum/schema mismatch and immutable DB record protection;
- repeated deterministic fitting, replay idempotency, same-session grouping, concurrent writes;
- label/injection/scenario identity leak sentinels rejected before fit;
- artifact tampering and malicious path rejected;
- independent held-out scenario, vehicle, configuration and time folds;
- negative controls (random irrelevant feature must not dominate) and confounders;
- strong 9A + 9B regression.

Create an **independent** `scripts/evaluate_anomaly_detection.py` or equivalent that exercises real project feature-generation -> reference dataset -> fitting -> artifact persistence/reload -> held-out offline scoring -> findings DB checks -> metrics, not just wrapping unit tests. Use a disposable migrated TimescaleDB and realistic bounded synthetic telemetry variation; record all outputs in ignored `.validation/phase9c/`.

Accept only genuine executed results; no fabricated log summaries, placeholder pass counters or altered test thresholds to force green.

## 14. Performance and observability

Benchmark at least a reasonably sized reference cohort and 1,000+ offline scored observations where fixture budget permits; report model fit time, scoring throughput, database read and persistence times, peak memory, artifact size and degradation by detector. These are local engineering metrics, not production SLAs.

Metrics should include fit/score run state and duration, rows eligible/excluded, findings by family/status, unsupported-source, insufficient-reference and invalid-input counts, artifact bytes, score and threshold summary WITHOUT high-cardinality entity identifiers. Traces should include reference materialization, eligibility/temporal validation, fit, threshold selection, offline score, finding persistence, artifact validation. Do not log VIN, raw samples, complete feature matrices or credentials.

## 15. Documentation and traceability

Produce and maintain:

- `docs/architecture/phase-9c-anomaly-detection.md`;
- `docs/validation/phase-9c-acceptance.md`;
- `docs/validation/phase-9c-model-evaluation.md`;
- `docs/validation/phase-9c-traceability-ledger.md`;
- `docs/runbooks/anomaly-detection.md`;
- detector/model cards under `docs/ml/` following existing conventions;
- relevant new ADR(s) for cohort/cutoff policy, detector/threshold selection and trusted offline artifacts;
- README, roadmap, security, observability and dependency docs;
- test and evaluation commands with their receipts.

Update stale roadmap Phase 9A/9B "pending" statements to their actually merged state. Keep 9D–9H marked planned. Explain clearly: outlier detection is **not fault detection**, engine diagnosis, calibrated fault probability, a maintenance order or universal cross-car reference. Compare to Phase 3 rule events and 9B next-pull classifiers.

## 16. Mandatory validation and delivery

1. Implement full functional scope, additive migrations, tests, documented operator interfaces.
2. Run focused unit, integration and independent acceptance evaluator on disposable infrastructure.
3. Run reproducibility, scenarios, benchmark, observability, security/artifact tamper and leak sentinels.
4. Run Phase 9A + Phase 9B acceptances and all canonical deterministic Phase 0–8 regressions; use repository's `make verify` and integration/browser/security/CodeQL workflows where applicable. Do not trigger paid Phase 7D model or Phase 8 embedding calls; preserve documented accepted historical caveats.
5. Fix actual regressions without falsifying acceptance. If blocked externally, record exact unmet checks, not success.
6. Commit on required branch, working tree clean, push to origin, ensure remote HEAD == final local SHA.
7. Open a PR targeting `main` with summary, design decisions, migration(s), example fixture evidence, detector comparison, false-positive/abstention data, limits, benchmark, all test metrics, security and remote exact-SHA CI receipts. Do not merge: USER merges manually.
8. After any subsequent fix, rerun relevant gates for the _new_ exact final SHA. Check CI quality, integration/E2E, canonical Docker/full-stack, security, CodeQL Python/JS/TS, dependency review and any 9C-specific jobs, resolving failures under your control.

## 17. Definition of done — checklist

- [ ] Own domain boundaries and versioned detector/reference/finding schemas
- [ ] Additive migration with immutability and fresh/downgrade/re-upgrade tested
- [ ] Correct Phase 9A temporal/cutoff and source-capability compliance
- [ ] Compatible effective vehicle/configuration/modification history
- [ ] Thermal, boost, performance and source-eligible fuel coverage
- [ ] Robust baseline and nonlinear unsupervised candidate with reproducible selection
- [ ] Frozen leakage-safe reference datasets and chronological grouping
- [ ] Offline AFTER_PULL_OFFLINE score, documented score orientation and thresholds
- [ ] Explicit valid/inlier/anomaly and abstention states
- [ ] Internal traceable immutable anomaly findings with no diagnostic claim
- [ ] Sparse-cohort guard and cold-start handling
- [ ] Fixture evaluation including controlled injections, confounders, negative controls and clean false-positive rate
- [ ] Deterministic repeat, artifact tamper and identity/future leakage guards
- [ ] Independent DB acceptance and complete per-family evaluation reports
- [ ] CLI/runbooks/ADRs/detector cards/documentation
- [ ] Benchmark, telemetry, metrics and privacy checks
- [ ] Phase 9A + 9B and all deterministic prior phase regression passes
- [ ] Canonical local verify and final exact-head GitHub checks pass
- [ ] PR open/unmerged, remote branch pinned to final checked SHA
- [ ] 9D through 9H not implemented

## 18. Final report contract

Return in concise but evidence-rich form:

1. required branch, baseline and final SHA;
2. PR URL/state, migration ID(s);
3. implemented detector families and approaches, source/horizon/quality policies;
4. reference cohort constraints, version/checksum schema and immutable finding behavior;
5. eligible/excluded/abstained counts with explicit reasons;
6. comparison metrics per candidate + normal false-positive rates and injection recall/precision;
7. held-out scenario, vehicle, configuration and temporal evidence, reproducibility;
8. artifact/security/leakage/idempotency proof;
9. DB acceptance/benchmark/observability;
10. full regression command/results and exact-head CI links;
11. limitations, all remaining caveats, confirmation 9D–9H untouched.

Only when every mandatory gate truly passes, end the report with:
`PHASE 9C — ANOMALY DETECTION: VERIFIED`

Otherwise honestly end with:
`PHASE 9C — ANOMALY DETECTION: NOT VERIFIED`
and enumerate exact unresolved blockers. Keep working on fixable failures instead of ending early.

---

# Detailed engineering contract — mandatory implementation addendum

Sections 19–80 refine, rather than supersede, Sections 1–18. They are **normative acceptance requirements**. When a repository convention differs from an illustrative class or command name, retain the established convention and document the mapping. Prefer functioning, tested domain behavior to superficial class-count or file-count compliance.

## 19. Phase boundaries and expected delivery graph

```text
Recorded vehicle telemetry + sessions + pulls
  -> Phase 9A immutable feature snapshots and eligible cutoff
  -> source/capability/quality/compatibility validator
  -> chronological reference cohort materialization
  -> versioned transparent statistical baseline
     + versioned nonlinear unsupervised candidate
  -> validation-only decision threshold policy
  -> trusted bounded offline detector artifacts
  -> AFTER_PULL_OFFLINE batch evaluation
  -> internal immutable AnomalyFinding + provenance + abstention
  -> independent engineering evaluation and reports

Deferred: HTTP/streaming inference, MCP/agents, PredictionEvidence UI,
calibrated risk probability, user alerts, continuous retraining, production fleet operations.
```

Make the actual repository architecture authoritative for module placement, but maintain the ownership boundary. Do not expose a public detector through existing MCP tools accidentally.

## 20. Primary user scenarios and non-goals

The engine must answer: "Was this observed pull unusual relative to a defensible historical/reference cohort?" and "What measurable feature deviations explain the flag descriptively?" It must also clearly answer "Insufficient evidence" when appropriate. It cannot answer "Which part will fail?" or "What should the driver change?" Model output should be suitable for later investigation, not presented as a mechanical instruction.

## 21. Statistical meaning of an anomaly

Differentiate **point anomaly** (single unusual observation), **contextual anomaly** (unusual under comparable context), **collective pattern** (sequence of unusual observations), and **data-quality failure** (not a valid observation). Define which of the first three are actually implemented. Do not call all anomalous readings persistent failures. If temporal pattern detection is deferred, mark it as deferred instead of quietly treating one point as a sequence.

## 22. Coarse vs specific features

Each detector must declare a bounded, semantically motivated set of existing canonical feature keys. Do not throw all 79 features, identifiers and quality counters into a model by default. Include explicit measurement units and missingness policies. Prevent a feature from simultaneously serving as a quality-exclusion flag and the main evidence of a physical malfunction without documenting the distinction.

## 23. Minimum approved detector families

Implement thermal, boost/air, performance, and fuel only when data supports them. Optionally provide multivariate composite scoring as a separate detector definition. The reference for each detector must list exact feature keys and expected availability. Fuel pressure is never inferred from boost, throttle or RPM. Do not infer engine health from generic ECU labels.

## 24. Vehicle/configuration partition key

The cohort resolver must derive effective configuration from Phase 9A provenance and modification history at observation cutoff. Validate compatible vehicle, recorded setup, installed modifications, input units and source capabilities. Version the compatibility predicate and prove it forbids pairing a pre-modification pull with post-modification baseline without explicit compatible rationale.

## 25. Generic OBD-II capability contract

Existing Phase 9A capability matrix must be consulted. Generic OBD-II may expose RPM/speed/throttle and selected temperatures but not necessarily boost, IAT, fuel rail pressure, commanded pressure or accurate torque. Missing hardware signals yield explicit unsupported/unavailable states. An advertised signal is not assumed actually sampled; verify observed coverage in the selected window.

## 26. Multi-vehicle applicability

The architecture must handle arbitrary vehicles and future workshop use. Same-vehicle comparable configuration baseline should be the default. A cross-vehicle cohort, if added, must be explicitly versioned, segmented by compatible measurable context and thoroughly evaluated on held-out vehicle(s). Never infer that a reference learned from an N55 BMW applies universally to a different engine.

## 27. Quality gating precedence

Run source eligibility, temporal/cutoff, compatibility, row/schema validity, feature coverage, reference support and artifact compatibility checks in a documented order. When multiple failures apply, return a deterministic primary abstention reason and optional bounded secondary reasons. Low-quality data is **not** automatically anomalous vehicle behavior.

## 28. Temporal observation semantics

Declare a single timezone-aware `observation_cutoff` per scoring request and per persisted finding. Verify recorded-at/ingested-at and source-event availability consistently with Phase 9A policy; event creation time cannot retroactively enter a prior snapshot. An after-pull observed value is allowed only after its own availability time and before cutoff, never from future pulls or 9B targets.

## 29. Reference cohort leakage controls

Exclude current row, future rows, duplicate replay lineages, same physical observation under different IDs, and target-source derived rows. Document how session grouping reduces correlated train/test contamination. Filtering only by a timestamp on the feature row is insufficient when a source row was ingested late or a modification was created after cutoff.

## 30. Reference freshness and support

A cohort policy shall define min eligible pulls, min independent sessions, adequate chronological span, maximum allowed staleness when meaningful, and max supported rows. Do not set ungrounded hard minimums under a pretense of universally valid automotive science. Document engineering defaults, test low-support abstention, and permit policy version changes without mutating old detector identities.

## 31. Distribution shifts and operating context

Thermal/environment/vehicle-configuration variations can be legitimate. Document which contextual features are available to restrict or stratify comparisons and which are deliberately not observable. If ambient temperature, elevation, fuel type, gear, driving mode or slope is absent, do not invent it. Limit conclusions rather than smuggling missing context into a universal baseline.

## 32. Robust baseline mathematics

Use a documented transparent robust statistic, for example `median` with scaled `MAD = median(|x - median(x)|)`. If using robust z-score, define `z = (x - median)/(1.4826 * MAD)` for nonzero MAD. Define explicitly what happens for MAD=0 or near-zero: safe IQR/scale floor, constant-feature exclusion, or deterministic abstention. Do not divide by zero or amplify floating-point noise into spurious anomalies. For each feature state whether high, low or bidirectional deviation is relevant, or choose bidirectional unless justified.

## 33. Baseline score aggregation

Aggregate per-feature deviations with a named finite bounded function such as weighted max or robust quantile, not an unexplained sum of arbitrary different units. Normalize with training-only statistics, track contributing feature count and avoid score inflation solely because one detector family has more available features. Preserve exact score orientation: greater means more statistically unusual.

## 34. Nonlinear candidate bounds

Isolation Forest or a comparably established allowlisted algorithm is acceptable. Lock seed, number of estimators, max samples, feature count, scoring conversion, bounded fit runtime and thread count. Record library version, contamination/threshold semantics and reference cohort checksums. Never let user-supplied class import strings, arbitrary Python pipeline definitions or model blobs instantiate the estimator.

## 35. Nonlinear score transformation

Isolation Forest's raw `score_samples` / `decision_function` direction must be converted to explicit **higher = more anomalous** semantics, with exact reproducible transform. Do not treat the numeric output as probability, severity of a mechanical issue or calibrated likelihood. Save the transform version with the detector.

## 36. Missing-value policy

Per feature distinguish unavailable sensor, insufficient window, invalid sample, not applicable, low coverage and ordinary observed valid zero where physically meaningful. Imputation, if employed for the nonlinear candidate, must be fitted on TRAIN only, accompanied by missingness indicators and allowed only for optional features with adequate coverage. Missing mandatory physical features cause abstention, not a fabricated normal or abnormal reading.

## 37. Value and unit validation

Reject nonfinite values, incompatible units/dtypes, invalid physical sentinels and impossible timestamps. Do not hardcode universal tuning/engine limits or clamp genuine but unusual valid measurements to make models perform better. Respect Phase 9A canonical units, including Kelvin and Pascal where used. Distinguish negative physical pressure delta (potentially valid representation) from invalid absolute pressure according to existing signal contract.

## 38. Pure fit/transform/score separation

Extract pure or narrowly scoped domain routines with deterministic inputs, plus infrastructure adapters for DB/artifacts. A fitted detector must never modify its training distribution while scoring. Expose internal tested functions for fitting, scoring and constructing immutable finding data without making them externally callable API endpoints.

## 39. Train, validation and test partitioning

Split chronologically at whole-session level, with no overlapping observation windows. Fit preprocessing and detectors using TRAIN reference only. Select hyperparameters and threshold using VALIDATION only. Hold TEST untouched until all choices are frozen. Add a walk-forward or expanding-window mode and explicitly handle folds with insufficient independent sessions.

## 40. Legitimate data without anomaly labels

An unsupervised historical reference contains data whose true health state is unknown; the absence of an event is not proof of a healthy engine. Control contaminated reference assumptions, mark the engineering scope, and do not train directly on an oracle of "normal failure-free vehicle" unless the fixture is explicitly synthetic and thus limited.

## 41. Threshold policy

Define separately:

- score threshold construction (e.g. training-reference robust cutoffs or validated clean-reference quantile);
- threshold selection process (no test optimization);
- family-specific optional thresholds and exclusions;
- change/versioning rules;
- what "ANOMALOUS" means.

If engineering synthetic clean validation labels are used to enforce a false-positive budget, preserve those labels outside the model matrix and disclose that synthetic acceptance is privileged. Do not tune using final test injections and then pretend it was blind.

## 42. Detector candidate selection

Always report transparent baseline and nonlinear model results. Define a deterministic predeclared selection policy: acceptable false-positive/abstention coverage floors first, injected-scenario detection performance second, simplicity and runtime on ties. If data support is insufficient for nonlinear model but baseline is valid, report that outcome honestly. Do not silently force Isolation Forest as winner.

## 43. Comparative synthetic stress suite

Generate nominal profiles and independent hidden interventions for thermal, boost, performance, fuel and mixed cases. Interventions must change observable source telemetry/feature behavior, not directly write a score or label. Maintain semantic plausibility and both easy and subtle examples. Injected oracle classes are evaluation metadata only and must not become model features.

## 44. Confounders and hard negatives

Include: elevated IAT with otherwise compatible performance, fuel deviation without boost change, boost fluctuation without performance degradation, naturally different post-modification behavior that requires segregation, cold-start or environmental context shift, and occasional sparse sensor readings. Evaluate these separately rather than count them as easy positive injections.

## 45. Independent held-out scenarios

Keep an unseen perturbation pattern, severity mix, or generator mode out of model fitting and validation. Do not select model family or threshold by test scores. Show scenario-level metrics with exact support, including cases where recall is poor. A perfect synthetic score caused by a trivial signature must be flagged as suspicious rather than celebrated as real-world proof.

## 46. Held-out vehicles and configurations

Evaluate at least one entirely unseen vehicle/profile and one unseen effective configuration where reference support permits. If same-vehicle-only baseline cannot score a held-out new vehicle, **correctly abstain** and report coverage rather than cheating by cross-vehicle data leakage. Separate detection accuracy among scored cases from abstention and applicability rates.

## 47. Evaluation denominators

For each family report eligible reference rows, held-out candidate rows, scored rows, not-evaluable rows, abstained rows by reason, true/false positives/negatives where oracle exists, precision, recall, F1, normal false-positive rate, anomaly coverage, and support. Undefined metrics should be explicit `UNDEFINED` or `INSUFFICIENT_SUPPORT`, never silently converted to zero.

## 48. Metric philosophy

Anomalies are not mechanical failures. Oracle precision/recall on synthetic perturbations measures recovery of synthetic patterns only. In unlabeled real data, report anomaly rates and quality/coverage, not ground-truth sensitivity/specificity. Avoid statements about real-world "accuracy" without verified labels and sampling methodology.

## 49. Predeclared acceptance floors

Before inspecting held-out results, write a small machine-readable acceptance policy with bounded fixture-specific limits for clean false-positive rate, injected-family recall, minimum family support, abstention fidelity, deterministic replay and artifact validity. Document why floors are reasonable. Failed thresholds cannot be loosened after test inspection just to turn red green; improving fixture diversity is not grounds for discarding difficult cases.

## 50. Persistent finding identity

Use an idempotency identity based on detector version, frozen observation FeatureSet/reference identity, cutoff, scope and algorithm/threshold version. Upserting a logically new result over an immutable old finding is forbidden. Concurrent retry of identical input should reuse the same committed evidence or report a deterministic conflict. Ensure DB constraints prevent duplicate logical findings.

## 51. Finding contract and reason codes

Persist both score and decision threshold plus units of interpretation. Bounded evidence must include detector family, cohort support/reference interval, source role, exact input feature snapshot, missing/invalid reasons and top measured-vs-reference differences. Reasons must be programmatic enumerations with stable definitions and be tested for correct precedence.

## 52. Statistical contribution explanation

For the transparent baseline, record strongest normalized signed deviations and units. For Isolation Forest, if listing such deviations as explanations, explicitly say they are **descriptive comparisons** and do not mathematically decompose forest score or prove causes. Never claim "turbo is failing because boost differs" from an unsupervised score.

## 53. Persistence transaction boundaries

Detector artifact staging, registry row creation and finding writes must not leave a healthy registered version pointing at a missing/corrupt file. Use established staged/verified artifact pattern from 9B, mark failure states, recover safe retries, and test interrupted execution. Avoid accidental distributed transaction claims when storage spans filesystem and DB.

## 54. Immutability vs supersession

A revised threshold, cohort selection, algorithm, library version, schema, source capability or normalization needs a new version/checksum where it affects semantics. A later retrospective cutoff must create a new derivation, not rewrite earlier knowledge. Preserve old findings for forensic comparison.

## 55. Artifact serialization

Only internally generated allowlisted trusted-code artifacts, stored at a fixed internal root and checksum validated, may be read. Bounded size and atomic rename required. Record schema order/dtypes/units, model family, preprocessing version, pinned dependencies, source role and reference checksum. Reject arbitrary uploaded joblib/pickle and document their code-execution risk.

## 56. Operator CLI ergonomics

Provide clear `--help`, dry-run/validation path if project conventions support it, explicit UTC/offset aware cutoffs, detector family selection, source-role and bounded batch scope. Avoid unbounded synchronous database scans. Nonzero exit status on invalid run or failed acceptance. Structured safe summaries must not print raw VIN, customer data, secrets or giant feature matrices.

## 57. Data lifecycle and export

Keep reproducibility manifests and detailed evaluator results under ignored validation paths while checked-in reports summarize material facts. Avoid tracking generated artifacts, large customer datasets or credential-bearing telemetry. File exports, if any, are bound in size, safely escaped and rooted under a controlled directory.

## 58. Resource budgeting

Set finite defaults/maxima for reference rows, batch score rows, features per detector, candidate count, hyperparameters, wall time, memory-sensitive processing and artifact size. Streaming or batched DB access should be used rather than loading arbitrary unlimited fleets into RAM. Report the values chosen and why they are viable for CI.

## 59. Observability dimensions

Permitted metric labels: detector family, algorithm family, decision/state, bounded reason code, source role, success/failure; no raw vehicle/session/pull IDs, VIN, model checksums, feature values or arbitrary high-cardinality labels. Traces may carry bounded internal correlation IDs if current observability policy permits; keep metrics safe. Verify scrape and spans against actual operations.

## 60. Benchmark separation

Measure fit/reference materialization, preprocessing, offline scoring, persistence and reload separately, with peak RSS, artifact bytes and per-detector counts. Benchmark both nominal and mixed anomaly batches, including abstentions. Clearly distinguish synthetic workstation throughput from measured production performance, without invented SLA.

## 61. Source ownership and database migrations

Inspect migration head before writing. Add a new revision with a correct down_revision chain; never hardcode revision `0015` if another migration has landed. Add foreign keys, unique constraints, bounded enums and indexes justified by actual run/lookup patterns; document downgrade loss for new 9C records. Historical Phase 9B rows must survive migrations untouched.

## 62. Real imported telemetry smoke

If an actual project-local imported fixture exists, run a non-destructive compatibility smoke on a disposable copy where possible. Real data may have little or no eligible fuel/performance coverage. Report exact counts and abstention, but do not manufacture labels or infer validation accuracy. If no imported dataset is available, state so explicitly.

## 63. Failure taxonomy

Use controlled errors for `INSUFFICIENT_REFERENCE`, `UNSUPPORTED_SOURCE`, `SCHEMA_MISMATCH`, `VERSION_MISMATCH`, `ARTIFACT_CORRUPTED`, `LOW_QUALITY`, `DATA_LEAKAGE_BLOCKED`, `RESOURCE_LIMIT` and infrastructure issues. Do not swallow exceptions and return a misleading healthy result. Log aggregate reason/state, not telemetry content.

## 64. Unit test matrix

Cover every deterministic transform, context resolver, missing-signal route, MAD-zero case, signed deviation orientation, cutoff, family-specific rule, immutable checksum, artifact rejection, incomplete reference, schema mismatch and idempotency. Use property-based tests only if already supported and cost-effective; otherwise deterministic explicit edge fixtures.

## 65. Integration test matrix

On disposable migrated TimescaleDB test 9A FeatureSet consumption, cutoff-aware cohort selection, configuration/modification lineage, multi-session history, late ingestion, pool transaction boundaries, concurrent runs, immutable references, duplicate scoring, migration round trip and no mutation of Phase 3/9B data. Test rollback of failed writes.

## 66. Independent evaluator independence

The acceptance evaluator must execute the real training/scoring/persistence code path, but assertions should independently calculate expected fixture counts and hidden injection oracle judgments. It must not simply compare a function's returned status to that same function's chosen expected status. Produce per-case receipts with no private data.

## 67. Leakage adversaries

Introduce deliberate source manipulations: a future after-pull feature before cutoff, label-derived field, session/vehicle ID surrogate, target pull label, post-cutoff modification, late-ingested supposedly older sample, and synthetic oracle scenario identifier. Each must fail or be excluded before influencing fit or score, with independent assertion.

## 68. Non-fabrication adversaries

Provide data where fuel signal never existed, an optional signal was declared but not observed, timestamps are duplicated, one observation is NaN, and a pre-pull feature is unavailable. Verify null/abstention and honest report. No default zero or older "last good" substitution to make a missing measurement look normal.

## 69. Determinism adversaries

Repeat fitting twice under same spec/dataset/seed/dependency versions. Compare reference row order/checksum, fitted decision structure or scores within strict tolerance, chosen threshold, finding identities and statuses. Reorder insertion and rows to ensure deterministic sorted handling. Byte-equal joblib is not required unless demonstrated.

## 70. Regression and compatibility matrix

Run and record `make phase9a-acceptance`, `make phase9b-acceptance`, Phase 3 event tests, Phase 5 analytics, Phase 6 MCP, Phase 7 deterministic agent evaluations and Phase 8 RAG acceptance along with `make verify` or its current canonical successor. Do not claim a pass merely because a prior PR did. Existing real-model paid-suite caveats are historical, not permission to fabricate new evidence.

## 71. CI gate expectations

Final pushed SHA should have current GitHub workflow equivalents for API/Web quality, integration & browser E2E, canonical Docker/full-stack acceptance, image/security/dependency scan and Python + JS/TS CodeQL. For a 9C-specific job, report its actual workflow run. Evidence must refer to the exact final candidate SHA; if checks are rerun on a previous SHA, they are non-authoritative.

## 72. Documentation example scenarios

Include operator-oriented example tables: eligible compatible pull with normal score, thermal anomaly, absent fuel signal, sparse reference abstention, post-modification baseline reset, corrupted artifact rejection and same-input retry. Each explanation must say "engineering statistical deviation, not a confirmed fault".

## 73. Documentation of alternatives

Record why the transparent baseline and selected unsupervised method were chosen compared with plausible alternatives; trade off interpretability, robustness, small cohorts, contamination, scaling, source coverage, compute and licensing/maintenance burden. Avoid importing a second heavyweight ML stack just for Phase 9C.

## 74. ADR for score lifecycle

Document choice of relative score transform, cohort strategy and threshold/freeze/version semantics. Explain that Phase 9G future calibration and drift operations do not retroactively endow Phase 9C scores with validated probabilities or real-world risk confidence.

## 75. ADR for Phase 3/9B coexistence

Document distinct evidence sources: Phase 3 deterministic rules/events; Phase 9B supervised NEXT_PULL label classifiers; Phase 9C retrospective unsupervised observed deviations. Any correlation between an event, predictive score and anomaly score should be an offline comparison rather than counting three independent proofs of a single mechanical issue.

## 76. Scope freeze at PR completion

The PR must modify only necessary Phase 9C functionality, shared genuine bug fixes and documentation updates. Never build Phase 9D serving or Phase 9F tool wiring "while here." If a shared 9A/9B bug fix is required, preserve versioned semantics, add regression proof and clearly disclose its impact.

## 77. Review checklist before PR

Review all changed files for accidental credential leak, developer-local paths, test artifacts, unsupported real-world claims, insecure joblib deserialization, large uncontrolled SQL/CPU work, future data leaks, brittle CI test fixtures, mismatched docs, hidden feature schema assumptions and silently changed Phase 9A/9B versions. Include findings and fixes in the PR body.

## 78. Git hygiene and handoff

Use the existing remote branch. Commit coherent changes; prefer readable commits over one huge unreviewable blob. Before final sign-off check clean `git status`, `git log -1`, upstream SHA equality, PR diff relative to main, and branch checks. Do not auto-merge or enable auto-merge. Return links and exact SHA.

## 79. Honest completion statuses

Complete means working code + verified executed acceptance + exact-head required CI. If local validation passes but CI is pending/blocked, say `NOT VERIFIED` with precise pending checks. If Docker, API funds or platform infrastructure are unavailable, investigate safer equivalent validation without falsely equating it to required full-stack proof. No fabricated 100% results or cherry-picked success.

## 80. End-to-end acceptance narrative

The final report must tell an auditable story of: canonical telemetry -> Phase 9A source FeatureSet -> eligibility and cohort selection -> immutable reference + temporal split -> fit/validate two approaches -> freeze detector version/threshold -> held-out offline scoring -> persist immutable finding/abstention -> reproduce and tamper-check -> benchmark/trace -> full legacy regression -> exact-head GitHub checks. Supply hard numbers **observed from executed runs**, exact commands and links, and retain all caveats. Keep this delivery limited to Phase 9C.
