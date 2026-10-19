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
- immutable anomaly finding records, explanation-oriented feature contribution metadata *as descriptive associations only*, references and checksums;
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
8. After any subsequent fix, rerun relevant gates for the *new* exact final SHA. Check CI quality, integration/E2E, canonical Docker/full-stack, security, CodeQL Python/JS/TS, dependency review and any 9C-specific jobs, resolving failures under your control.

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
