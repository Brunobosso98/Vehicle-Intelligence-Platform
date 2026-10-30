# Phase 9G — Evaluation & Calibration (Scientific Reliability Foundation)

**Repository:** Brunobosso98/Vehicle-Intelligence-Platform
**Required EXISTING branch:** `codex/phase-9g-evaluation-calibration`
**Branch baseline:** `327c63f35b4e7bc0eba31bbec81d20206be8afa2` — merged Phase 9F PR #50 (2026-10-27)
**Current phase:** Phase 9G — offline evaluation, research-only calibration, anomaly false-alarm and drift/applicability studies.
**Future:** Phase 9H Predictive Intelligence UI; Phase 10 MLOps; Phase 11 Agent Evals/Red Team; Phase 12 Cloud Production Infrastructure.

This document is the **authoritative, complete execution, scientific-integrity and acceptance contract**. Read ALL numbered sections before writing code. Code paths and dataset identities mentioned are grounded in the existing 9B/9C/9D/9E/9F source and must be inspected/reconciled with real repository conventions. Deliver real code and executed evidence, not a scaffold.

## Non-negotiable separation

```text
9A canonical time-aware FeatureSets
  -> 9B supervised NEXT_PULL model artifacts + EXACT original label rules
  -> 9C retrospective AFTER_PULL_OFFLINE detectors + frozen same-cohort baselines
  -> 9D controlled serving receipts / 9E verified evidence / 9F grounded agents
  -> 9G OFFLINE controlled evaluation only
       chronological grouped fit / calibration / independent held-out test
       proper scoring rules + reliability uncertainty for synthetic 9B labels
       9C clean false alarms, cross-family alerts, outlier stability
       shift / OOD / coverage / abstention and applicability analysis
       immutable reproducible engineering evaluation reports
DEFERRED: real-world claims without labeled evidence, production model promotion,
deployment, live drift monitors, public probability fields, 9H UI, vehicle control.
```

**Critical:** Phase 9G is allowed to conclude ENGINEERING VERIFIED while explicitly reporting **REAL-WORLD PREDICTIVE VALIDITY / CALIBRATION NOT ESTABLISHED**. This is not a contradiction: correct scientific reporting is a mandatory part of completion. Synthetic-label calibration is NOT a mechanical-failure probability.

**Git:** Work only on existing branch; create PR but DO NOT MERGE. User merges after independent review.

---

## 1. Mission and scientific boundary

Build a versioned, reproducible and independently auditable OFFLINE evaluation/calibration laboratory for immutable Phase 9B supervised NEXT_PULL models, Phase 9C retrospective anomaly detectors and the reliability/applicability of downstream Phase 9D–9F claims. Measure the true limits of each source role. Calibration on engineering synthetic labels is strictly synthetic-domain calibration; NEVER relabel it as real-vehicle fault probability, production safety, diagnosis or permission for broader serving.

## 2. Git and exact baseline

Repository Brunobosso98/Vehicle-Intelligence-Platform. Required EXISTING branch codex/phase-9g-evaluation-calibration, created from merged main SHA 327c63f35b4e7bc0eba31bbec81d20206be8afa2 (PR #50 Phase 9F). Fetch origin, check clean tree and AGENTS.md, switch to this branch, verify baseline ancestry and current Alembic HEAD. No second branch, force push, main writes or auto merge.

## 3. Authoritative documents

Read this full specification, README, roadmap, AGENTS.md and source/docs/ADRs/tests of Phases 9A–9F plus Phase 3 anomaly rules, Phase 7 agent claim validation and Phase 8 RAG. Read apps/api/src/vehicle_platform/{features,ml,anomalies,predictions,prediction_evidence,agents,mcp}; scripts/evaluate_predictive_models.py, evaluate_anomaly_detection.py, evaluate_prediction_service.py, evaluate_prediction_evidence.py, evaluate_agent_prediction.py and full validation workflow. Map all 9G requirements to real implementations.

## 4. Why Phase 9G exists

Previous engineering evaluations prove execution, isolation and specific fixture discrimination, not scientific reliability on deployed cars. 9B reported task-dependent synthetic AP/F1 with small held-out test cohorts and limited fold support; 9C Robust MAD dominated fixture tests while alternative IsolationForest missed or over-flagged patterns. The 9C held-out test recorded cross-family alarms, e.g. thermal 6/12 and boost/fuel 4/12, distinct from clean-control FPR. Treat these observed limitations as mandatory evaluation subjects rather than marketing footnotes.

## 5. Non-goals

Do NOT create production calibration, continuous fleet drift monitoring, auto retraining, online ML serving, predictive UI/alerts (9H), new MCP/agent answer tools, real-vehicle diagnosis, ECU commands, driving safety permission, failure probability, remaining useful life, tune selection, maintenance instructions or causal root-cause analysis. Phase 10 owns MLOps, Phase 11 broad agent Evals, Phase 12 production infrastructure.

## 6. Evaluation artifacts not promotion

This phase should produce frozen EvaluationProtocols, EvaluationRuns, MetricReports, ConditionalCalibrationCandidates and ApplicabilityAssessments with immutable source lineage and explicit gate status. These are offline engineering records. A good synthetic calibration report does NOT activate, approve, deploy, change Phase 9D serving thresholds, alter existing 9E bundles or make Phase 9F agent outputs more certain.

## 7. Distinct score ontology

9B engineering_validation_score in [0,1] is a supervised score for one next-compatible-pull outcome rule; it is NOT calibrated mechanical fault risk. 9C robust MAD/IsolationForest scores are detector-relative outlier values, not probabilities. 9F confidence field, 9E integrity and source quality are different dimensions. Never mix them into one 0–100% health/failure rating.

## 8. Source role partitions

Retain exact synthetic, imported_fixture, imported and real_vehicle roles and source capability eligibility. Synthetic and imported observations lacking verified outcome labels cannot produce real-world calibration accuracy. Holdout subsets and real-source smoke must remain distinguishable in artifact names, database records, metrics and reports.

## 9. Original model contracts

Preserve three MLTask identifiers NEXT_PULL_THERMAL_DEGRADATION, NEXT_PULL_PERFORMANCE_DEGRADATION and NEXT_PULL_FUEL_DEVIATION, frozen label definitions, preprocessing, model registry, threshold, artifact SHA and temporal horizon. Evaluate the original recorded result without rewriting original trained ModelSpec, LabelDefinition or TrainingRun.

## 10. Anomaly family contracts

Evaluate thermal, boost_air, performance and fuel at minimum. Respect versioned detector definition, frozen reference selection, method (robust_mad or isolation_forest), thresholds, source capability, quality abstention and AFTER_PULL_OFFLINE horizon. Do not conflate a Phase 3 deterministic event with a 9C model-detected deviation.

## 11. Engineering evidence limitations

No mechanical failure labels are available in the accepted synthetic fixtures; 9B target labels describe constructed observable next-pull conditions, not broken parts. 9C injected anomalies are oracle-labeled synthetic perturbations, not true diagnosed engine defects. Define accuracy and calibration only relative to their EXACT outcome/oracle definitions and experimental population.

## 12. Applicability model

Define an explicit versioned ApplicabilityDecision for each task/family, model/detector version, source role, vehicle/config context, required signals, data sufficiency, evaluation coverage, calibration evidence, and acceptable operational scope. Typical states: SYNTHETIC_ONLY, EVALUATION_INSUFFICIENT, REAL_DATA_UNLABELED, INCOMPATIBLE, OOD_WARNING, NO_REFERENCE, NOT_CALIBRATED, REVIEW_REQUIRED. A report may not silently promote real-world eligibility.

## 13. Offline evaluation pipeline

Source immutable 9A FeatureSets and frozen 9B/9C artifacts; reconstruct identical eligible time/source cohorts, group chronological partitions, derive no future-inference features, read their existing outputs, produce evaluation-only reports and candidate mappings, independently verify metrics and persist immutable evaluation evidence. No automatic HTTP scoring or agent access is needed for this pipeline.

## 14. Evaluation schema versioning

Create versioned strict Pydantic/domain contracts for EvaluationProtocol, DatasetManifest, FoldManifest, MetricDefinition, MetricResult, CalibrationMethod, CalibrationCandidate, ReliabilityBin, CalibrationValidityScope, DriftComparison, StressScenario, ApplicabilityAssessment, EvaluationRun and EvaluationEvidenceRef. Follow repo conventions; ensure finite values, bounded arrays, units and explicit denominator definitions.

## 15. Source SHA and immutable references

Store exact model/detector version IDs and checksums, Phase 9A FeatureSet/version/provenance hashes, label-definition version for 9B, reference dataset for 9C, source role, effective configuration/modifications, cutoff and generator fixture version. All report points must be reproducible against trusted frozen source snapshots.

## 16. Evaluation identity and idempotency

A deterministic logical evaluation key binds protocol version, source role, dataset row fingerprints, fold/split policy, model/detector versions, calibration method and hyperparameters, seed and evaluation target. Identical offline rerun should reuse or produce semantically identical immutable reports; changed calibration or input cannot overwrite old results.

## 17. Temporal leakage safety

Use real Phase 9A known-at-cutoff policy, both observed_at and ingested_at, modification recorded_at and 9B next-pull temporal target boundaries. Training/preprocessing/calibrator tuning MUST NOT see final held-out future observations. Include explicit adversarial sentinels for post-cutoff feature, target label, late ingestion and retroactive modification.

## 18. Chronological group splits

Use independent sessions as grouping units and time-ordered training, calibration/validation, final test and walk-forward windows. No same-session pull splitting across fit/calibration/test; no duplicated/replayed physical observation across boundaries. Distinguish vehicle-level and configuration-level holdouts from within-vehicle time holdouts.

## 19. Separate calibration fit data

For 9B, fit existing classifier on designated TRAIN only; fit calibration mapping on genuinely disjoint CALIBRATION portion, optionally use separate VALIDATION for method choice, keep FINAL TEST untouched. If existing 9B versions cannot support proper disjoint calibration without retraining, create an OFFLINE evaluation-only experiment version, not a replacement of registered serving artifact, and document protocol difference.

## 20. Prevent split over-optimism

Do not fit sigmoid or isotonic mapping on the same final test labels used for evaluating the curve. If prior 9B test observations were already inspected during 9B and now used to design 9G methods, call them historical analysis and reserve NEW untouched synthetic scenarios/time windows for 9G unbiased testing. Test protocol must predeclare selections before unsealing final holdout.

## 21. Calibration method baseline

At minimum compare identity/uncalibrated scores with a bounded calibration candidate such as Platt/sigmoid and a conservative isotonic candidate only when data support is adequate. Use fixed seeds and monotonicity constraints. Simple calibrated candidates preferred for sparse support; no isotonic fit on five independent observations masquerading as robust calibration.

## 22. Calibration fit artifact

Record calibrator family, input model version and training/calibration sample identity/checksums, fitted parameters and dependency versions. Trusted internal artifact root, fixed allowlisted serializer, checksum and bounded size. No user model uploads or arbitrary pickle loading. Deserialization should not permit untrusted Python execution.

## 23. Calibration is target-specific

Calibrate 9B probability of its originally defined synthetic NEXT_PULL observable label only, conditional on fixture/source role and population. No mapping of any 9C anomaly score to calibrated 'fault probability'. If a synthetic injected-anomaly likelihood experiment is attempted, call it fixture-injection likelihood and ensure separate nonserving research type.

## 24. Calibration metric suite

For 9B compute Brier Score, log loss with clipping justified and reported, reliability/calibration bins and Expected Calibration Error (ECE) with declared bin choice. Add slope/intercept where data support; compute AUROC and average precision (AP) separately because discrimination and calibration are not identical. Do not call F1 a calibration metric.

## 25. Small sample reliability

Specify minimum independent positives, negatives, sessions, vehicles and bins before allowing an asserted calibration assessment. When too sparse, return INSUFFICIENT_SUPPORT, undefined CI or descriptive only, not a perfect reliability score. Use coarse few-bin diagrams with counts, calibration intervals and explicit support; never visually smooth away missing bins.

## 26. Calibration confidence bounds

Compute proper finite-sample uncertainty around Brier/log loss and reliability frequency where possible using session- or vehicle-cluster resampling, not row-iid bootstrap on correlated pulls. If support is insufficient for valid clustered CI, report missing CI and limited support. Never invent precise 95% reliability from small synthetic folds.

## 27. Identity versus calibrated benchmark

For each 9B task show original frozen score, identity baseline, sigmoid and isotonic (when eligible), with Brier, log loss, AP, reliability bins, threshold decision parity/changes and source coverage. Explain that calibration may improve proper score metrics while altering threshold decisions; do NOT silently apply mapping to original 9D/9F thresholds.

## 28. Calibration selection criteria

Predeclare selection based on validation-only proper scoring rule(s), sample support, monotonicity and complexity. Use a deterministic tie break favoring identity/simple method. Calibration curve goodness on held-out TEST cannot be used to choose model/hyperparameters then reported as unbiased success.

## 29. Threshold decision trade-offs

Evaluate existing 9B threshold sensitivity on validation and untouched test, precision-recall curves, positive/negative predictive value for the SYNTHETIC scenario prevalence, false-positive/false-negative costs under explicitly stated hypothetical costs, and abstention/coverage. Do not pretend synthetic class prevalence equals real fleet prevalence.

## 30. Decision threshold freeze

Do not overwrite ModelSpec or existing 9D model binding threshold. Any experiment-threshold must be a versioned OFFLINE research decision policy and only applies to its defined evaluation cohort. A new production threshold would require explicit future approval plus source-domain validation, outside 9G.

## 31. Prevalence shift

Report calibration sensitivity when synthetic positive outcome prevalence changes. Predictive values depend on base rate. Use explicit simulation scenarios with base rates named as hypothetical; avoid extrapolating 9B class labels to real-world mechanical-failure rates or warranty incidents.

## 32. Multi-horizon discipline

Preserve original NEXT_PULL target semantics and AFTER_PULL_OFFLINE detection in all evaluation data. Any temporal extension to next N pulls or live streaming is a new target/version and out of Phase 9G.

## 33. Anomaly false-positive controls

For 9C evaluate clean-control FPR separately from cross-family alarms, correlated-session repeated alarm counts, false alarm burden per independent session and after applying explicit quality/capability abstention. Report counts and denominators including non-scored cases. A true synthetic perturbation affecting more than one family is not automatically a false positive in another; define oracle semantics per scenario.

## 34. Cross-family confusion matrix

Design a matrix whose columns are exact synthetic intervention families and clean contexts, rows are 9C detector families, values counts/score coverage/alarms. Explicitly expose false cross-family flags, e.g. prior thermal 6/12 and fuel/boost 4/12 from the Phase 9C tested fixture, without confusing this with clean-control FPR or diagnosis.

## 35. Alarm deduplication research

Research offline correlated-event grouping at same pull/session and repeated features, so summaries can distinguish many detector findings from independent episodes. Do not alter persisted 9C findings, combine probabilities or launch notifications; record candidate grouping policies with source lineage and compare burden transparently.

## 36. Anomaly score normalization

Study score distributions per 9C method and family without mixing MAD score scales with IsolationForest. Characterize sensitivity to reference size, robust-scale zero-MAD cases, source noise and environmental context. Do not map detector scores to percentages of component health.

## 37. Method selection reevaluation

Evaluate original robust MAD and IsolationForest artifacts under new reserved stress scenarios. Keep original frozen 9C method/threshold choices intact; create a separate research recommendation. Report when nonlinear candidate misses anomalies caught by baseline, or when baseline overfires, without cherry-picking only favorable examples.

## 38. Anomaly calibration warning

No verified mechanical normal/failure ground truth exists. Therefore 9G must NOT produce a deployed 9C probability estimator for engine damage. ROC/PR or injection detection metrics are permitted only relative to controlled injected perturbations and explicitly named scenario oracles.

## 39. Conformal and selective inference feasibility

If exploring conformal p-values, prediction sets or selective classification, only do so under documented exchangeability and temporal-dependence conditions. Nonstationary sequential vehicle pulls break naive IID assumptions; default to feasibility report or guarded research-only candidates with honest failures, not sweeping 90/95% coverage claims.

## 40. Abstention evaluation

Audit 9B/9C/9D/9E actual abstention categories: insufficient signal, low quality, missing reference, incompatible context, unsupported source, cutoff, missing artifact and unverified evidence. Compute selective risk/error among scored samples and coverage among all eligible requests; never count abstentions as correct predictions or healthy outcomes.

## 41. Coverage-risk curves

For supported 9B research thresholds, plot risk/error versus retained sample fraction, including missing sensors and low-quality filters. Use ordered risk-coverage points with raw support; do not choose an apparently perfect operating point by discarding hard cohorts after seeing their held-out labels.

## 42. Subgroup and cohort evaluation

Group by vehicle, effective configuration, modification state, source type/role, available signal families, time windows, ambient/context where measured, session and synthetic generator scenario. Show subgroup support, error rates/coverage and inequality of support; small subgroups must be marked insufficient, not ranked by arbitrary single successes.

## 43. Cold start and sparse reference

Test new vehicle/configuration and low-history 9C reference policy. Measure proportion safely abstained vs incorrectly scored. Do not relax Phase 9C minimum same-config sessions or use cross-vehicle surrogate to make dashboard percentages look comprehensive.

## 44. Drift definitions

Separate covariate/feature drift, label/prevalence drift, concept/performance drift, calibration drift and detector/reference drift. With unlabeled real data, only feature/source availability/distribution changes may be measurable; concept/performance/calibration drift require trustworthy post-outcome labels and appropriate temporal evaluation.

## 45. Offline drift protocols

Evaluate frozen baseline vs later synthetic windows and, if sanitized imported real-like source exists, feature-only comparisons. Compute reasonable bounded PSI/KS/Wasserstein or robust median/IQR shifts with validity caveats and corrections for multiple comparisons where appropriate. Do not claim fleet real-drift detection from a single synthetic dataset.

## 46. Drift stress generator

Generate unseen environmental temperature shifts, session-specific sensor noise, changed acquisition sampling, missing fuel pressure, configuration/modification changes, distribution tails and shifted class prevalence. Ensure injection metadata remains evaluation-only and each stress maps to source telemetry/FeatureSets, not direct score edits.

## 47. Seasonal and environmental confounds

An IAT ambient shift may be legitimate; don't call it intercooler failure. Assess contextual grouping by available ambient/temperature/gear if measured; unseen environmental variables remain unknown. Evaluate false-alarm burden under environment changes and distinguish sensor capability from actually observed measurements.

## 48. Modification and tune context

Separate pre/post hardware modifications or calibration changes using existing 9A provenance as-of cutoff. A data distribution shift caused by Stage/tune change may require a new baseline/cohort, not a fault alarm. Do not infer ECU map from marketing tag or missing metadata.

## 49. Sustained versus transient changes

Characterize one-off unusual pull versus repeated deviations across sessions. Temporal clustering can be reported as observational behavior only. Never infer imminent component failure or causation from persistence without documented validated mechanical outcomes.

## 50. Data quality sensitivity

Corrupt timestamps, duplicated samples, missing pressure/temperature, unit mismatch and low signal coverage; measure robustness and correctly abstained cases. Evaluate apparent predictive gains from dropping hard/invalid cases without pretending selectively filtered performance reflects all driving data.

## 51. Source-role real/imported smoke

If a sanitized imported CSV example is available, run READ-ONLY feature distribution and capability evaluation using disposable database. Previous 9C imported smoke had 264 pulls across 30 vehicle/config cohorts and no eligible exact-cohort detector fit. Record the actual new count rather than assuming availability. No diagnosis, no invented target labels, no calibrated metrics on unlabeled data.

## 52. Real-labeled dataset policy

If verified real-world outcome labels happen to exist, require explicit provenance, source rights, outcome/label definition, timestamp, independent adjudication, privacy handling and sufficient support before computation. Without these, output REAL_LABELS_NOT_AVAILABLE; do not infer mechanical fault status from high IAT, DTC or original model score.

## 53. Outcome adjudication

Establish a future-ready controlled label spec for human-verified observable pull outcomes and separately adjudicated mechanical failures, with explicit identity redaction and case definitions. Design only protocol/schemas as needed, not a production annotation or customer PII collection system.

## 54. Error taxonomy

Use stable statuses: VERIFIED_FIXTURE_EVALUATION, SUPPORT_INSUFFICIENT, UNLABELED_REAL_DATA, OUT_OF_DOMAIN, SCHEMA_MISMATCH, SOURCE_ROLE_MISMATCH, TEMPORAL_LEAKAGE_BLOCKED, ARTIFACT_INVALID, REFERENCE_INELIGIBLE, RESOURCE_LIMIT, NOT_CALIBRATED, NOT_APPLICABLE, EVALUATOR_FAILED and REQUIRES_HUMAN_REVIEW. Do not swallow errors into a passing number.

## 55. Report claims guard

Add machine-readable AllowedClaimCategory such as SYNTHETIC_FIXTURE_METRIC, UNLABELED_DISTRIBUTION_METRIC, MEASURED_SOURCE_COVERAGE, UNCALIBRATED_SCORE, SCIENTIFIC_LIMITATION. Guard against representing synthetic Brier as real-car calibration, detector anomaly as failure probability or 9F 'moderate confidence' as statistical certainty.

## 56. Evaluation provenance graph

Define bounded source references to real model/detector registry, immutable feature snapshots, exact original 9D/9E evidence when applicable, fold manifests, outcome oracle, calibration input rows and report protocol. All report nodes must be linked to source role and known-at time; source hashes are private metadata not public URLs.

## 57. Immutable evaluation audit

If DB persistence is appropriate, add additive Alembic revision after actual 0018_agent_prediction_lineage HEAD; do not edit historical migrations. Store protocol/definition, immutable dataset/split/fold/metrics/calibration candidates and evaluation receipts with source checksums/unique constraints and DB-enforced immutability. A simpler stable files+manifest research output is acceptable ONLY if clearly justified and independently verifiable, but expected 9G versioned evaluation lifecycle should be durable and auditable.

## 58. Persistence volume bounds

Bound retained rows/metrics/protocols and avoid duplicating all telemetry or sensitive FeatureSet numeric matrices in JSONB. Store capped aggregates and trusted source foreign keys/hashes; large evaluation-generated outputs live under ignored .validation/phase9g with machine-readable summaries. No customer VIN, GPS, IDs in public reports.

## 59. Artifact storage security

Use internal rooted ignored storage, size limits, atomic creation, checksum verification, schema/version/method allowlist and fixed serializers for calibrators. Never download random user models, load arbitrary pickle from HTTP, evaluate SQL expressions or accept arbitrary Python estimator classes from user-input flags.

## 60. CLI research operations

Operator-only bounded commands: list protocol/versions, build evaluation cohort, run supervised calibration study, run anomaly stress evaluation, inspect reports/applicability, verify hashes, export sanitized summary. No state-changing public HTTP routes and no operator action that promotes candidate to live scoring. Provide --help, explicit source role/cutoff/seed, caps and meaningful nonzero exit codes.

## 61. Zero new runtime public API

Phase 9G is OFFLINE. Do not expand 9D service API, Phase 9F MCP tool, AgentRun response or Phase 9H UI to expose calibrated percentages. If future-facing type is needed, keep it internal and opt-in; public 9B/9C score semantics remain exactly as before.

## 62. No automatic serving approval

Never change ServingBinding APPROVED/ACTIVE events, current model/detector artifact or Phase 9D thresholds. Evaluation result cannot auto-activate a new model, even when synthetic metrics pass. Agent predictions in 9F must stay uncalibrated engineering outputs with same caveats.

## 63. Post-evaluation scientific gate

Define a versioned ScientificReadinessReport separate from CI's engineering PASS: e.g. PIPELINE_VERIFIED, SYNTHETIC_CALIBRATION_ONLY, INSUFFICIENT_REAL_LABELS, PRODUCTION_USE_PROHIBITED. Engineering implementation can be Phase 9G VERIFIED while real-world readiness remains NOT_ESTABLISHED. Ensure no code/README mixes these statuses.

## 64. Fixture protocol preregistration

Before final held-out generation, define in-repo versioned scenario plan and floors for metric computations, oracle support, latency/bounds and guard correctness. Freeze method choice, binning and comparison expectations. Do not inspect final stress scenario results then alter its design solely to pass metrics.

## 65. Fixture diversity

Generate independent synthetic vehicle profiles across at least 2 or more engine/config analogues, sessions/time, data capability and modification transitions, with deterministic unseen pattern families. Retain the actual 9B labels, not arbitrary fault tags. Avoid single generator shortcut that a model can identify by meaningless ID.

## 66. Do not force favorable model scores

No hard requirement for calibration to beat uncalibrated score on all synthetic folds. A scientifically honest negative finding (isotonic overfits, cross-family alarms, ECE worsens) is valid if evaluator reports it and protocol works. Acceptance is about correctness, rigorous measurement, provenance, safe claims and full coverage, NOT fabricated perfect calibration.

## 67. Predeclared engineering targets

Gates may require 100% deterministic split integrity, source security, metric arithmetic, report completeness and safe status distinctions. Synthetic performance thresholds may be a monitoring reference only; document when below target without relaxing gate after seeing test. For small cohorts, a valid INSUFFICIENT_SUPPORT report is scientifically acceptable and must be independently verified.

## 68. Holdout methods

Use final chronologically later stress windows and vehicle/config holdouts. Group both training/calibration/test and cluster CI by meaningful independent sessions/vehicles. When a holdout new vehicle cannot be scored because no 9C baseline, abstention is correct and coverage must reflect it.

## 69. Calibration bins robustness

Test fixed-width and quantile bins only when support permits. ECE with bin counts must report sample size, bin method and mathematical formula; empty bins carry no invented positive rates. Validate exact 0/1 score handling, clipping for log loss and no bin-index off-by-one.

## 70. Brier scoring correctness

For binary outcomes compute mean squared (p-y)^2 with documented weights and sample support. Positive labels must derive from the exact 9B outcome definition; compare independent hand calculations on tiny adversarial fixtures including all-negative, all-positive, score 0/1 and missing labels.

## 71. Log loss correctness

Clip p using documented epsilon ONLY for numerical stability, not to hide miscalibration. Labels and predicted probabilities must be finite, valid and aligned by immutable example ID, not array row order; reject NaN/Inf, duplicate/missing IDs, ambiguous label provenance.

## 72. ECE caveats

ECE is binning-sensitive and may appear good with low support even for a poor model. Include per-bin counts, observed positive fraction, mean score and weighted absolute error. Interpret calibration slopes/intercepts only when fitted support is reasonable; do not overstate confidence from one seed.

## 73. Discrimination metrics

Calculate AUROC and AP, including correct undefined behavior for single-class test. Report balanced accuracy, precision, recall, F1, confusion matrix and base rate when thresholded decisions are defined, with explicit denominator and abstention handling. Do not claim an area under ROC for absent class.

## 74. Class imbalance

Vary simulated next-pull outcome prevalence, preserve correct positive/negative support and avoid oversampling final TEST before evaluation. Any class weights or resampling must occur in TRAIN only, with transformed score semantics documented. Do not report optimistic overall accuracy dominated by negatives as calibration proof.

## 75. Model comparisons across tasks

Compare each 9B task with its own task-specific label and source support, not directly rank thermal probability against performance or fuel label for 'car condition'. Aggregate dashboard-like summaries only as macro-level report tables with clear supports; not end-user UI.

## 76. False-positive burden denominator

Compute false alerts per clean eligible pull, per independent session and per observation window; distinguish alarms per detector and deduplicated observation groups. A model that abstains on 50% of hard cases cannot be called low-FPR without reporting scored coverage.

## 77. Cross-family stress matrix detail

For each 9C family x synthetic intervention, report eligible, scored, abstained, anomalous/inlier, true target-family injection support, cross-family alarm rate and clean controls. Include confounding combined interventions as MULTI_FAMILY_OR_AMBIGUOUS, not arbitrary false positives.

## 78. Reference contamination

Inject some anomalous-looking or synthetic perturbed patterns into reference TRAIN only under a declared controlled scenario and compare detector sensitivity/FPR. No automatic unsupervised labels from model outputs treated as true normal. Document contamination assumptions and how reference selection changes results.

## 79. Out-of-distribution cases

Generate unseen vehicle/config, temperature ranges, source sampling rates and missing channels. Estimate feature/reference distance only from TRAIN-fitted statistics; never fit OOD threshold on final holdout. OOD_WARNING is a restriction/abstention, not a different mechanical diagnosis.

## 80. Sensor availability coverage

Quantify actual observed required signals for 9B/9C source roles; generic OBD-II may not contain fuel pressure or exact torque. Explicit unavailable/unsupported signals remain null and excluded, not imputed or guessed from boost/RPM. Variation in acquisition must not create false mechanical risk.

## 81. Parameter robustness

On VAL-only stress test variation of seed, training cohort length, contamination of reference, calibration bin count, IF tree count and robust MAD zero-scale handling. Fixed benchmark resource caps. Record which changes materially alter results; DO NOT use TEST to pick tuning and then hide sensitivity.

## 82. Reproducibility scope

Identical frozen dataset/protocol/seed/runtime must reproduce row selection, fold identities, numeric metrics within strict tolerance, selected calibration candidate and report checksums where canonical format permits. Artifact byte identity isn't assumed across joblib versions. Record library pins and feature ordering.

## 83. Cross-run independence

A later recalculation must have new version/fingerprint when source selection, thresholds, calibration algorithm or protocol changes. Never rewrite old evaluations or original 9D/9E receipts. Preserve traceability of older 9B/9C artifacts used for all comparisons.

## 84. Data independence tests

Deliberately duplicate same pull into training and test under changed IDs, reuse same physical session, feed post-cutoff label, move a calibration label into test, and add feature derived from target. All must be detected or excluded and independent evaluator must assert reason. No source identity feature in ML matrix.

## 85. Physical plausibility guards

Synthetic perturbations must correspond to plausible telemetry dimensions, canonical units and valid timestamp/quality; they must not directly edit classifier scores, 9C findings or labels to produce an easy pass. If a stress is outside physical plausibility, label it adversarial input validation rather than real vehicle behavior.

## 86. Unseen-context specificity

Separate noise caused by ambient IAT, actual within-pull IAT rise, boost pressure baseline and performance interval changes. Confounds can generate cross-family alarms; preserve them as genuine limitations. Do not label unchanged performance as thermal/performance fault from artificial IAT alone.

## 87. Quality confound cases

Evaluate source duplicate timestamps, truncated intervals, NaN, late ingestion, impossible canonical pressure, missing optional signal and missing mandatory fuel. Confirm the correct 9A/9B/9C/9D pipeline abstains or rejects rather than yields a fabricated healthy score.

## 88. Original threshold comparison

Compute original frozen decision behavior vs offline research candidate decision mapping for 9B/9C, but never mutate or silently relabel registered threshold decision. Report disagreement counts by source/family/context; downstream 9F answer still cites original 9D receipt and 9E evidence.

## 89. Coverage vs validity hierarchy

Create a clear matrix where data-quality validity, temporal validity, source-role eligibility, calibration support, evaluation sample support, shift compatibility and artifact verification are separate dimensions. A model with high AP but source role synthetic can still be NOT_ELIGIBLE_FOR_REAL_VEHICLE.

## 90. Selective policy recommendations

Produce machine-readable proposed engineering policies such as ABSTAIN_ON_LOW_QUALITY, REQUIRE_SAME_CONFIG_HISTORY, FLAG_UNCALIBRATED, REVIEW_ON_SHIFT, with evidence. Recommendations are proposals only, not changes to active application behavior or automatic agent policy.

## 91. Real-world validation readiness plan

Document exact evidence needed to responsibly evaluate models on real cars: sufficiently many independent vehicle/session examples, qualified labels for observable outcomes, prospective cutoff collection, source consent, robust sensors, mileage/modifications/config metadata, representative environments, error costs and external evaluation. Do not invent numeric population requirements absent design justification.

## 92. Multi-vehicle commercial applicability

Evaluate which capabilities generalize across multiple car brands through canonical signals, which depend on enhanced OEM sensors, and which are presently N55-like synthetic assumptions. Produce a per-source capability/applicability report; never claim workshop/commercial readiness based only on synthetic successes.

## 93. Vehicle owner privacy

Synthetic fixtures preferred. For imported/real data smoke, scrub VIN, license plate, GPS, owner, location, file path and raw metadata. Never upload real private telemetry to external providers; do not commit identifiable row-level data or store sensitive IDs in metric labels.

## 94. Threat model for scientific reports

Consider metric laundering, cherry-picked partitions, population shift, label contamination, source spoofing, model artifact substitution, test leakage, targeted injection, overfitting isotonic, fabricated calibration curves and misleading error-rate claims. Add executable checks and residual limitations.

## 95. Statistical significance

Do not claim methods superior from a few samples. Provide confidence intervals where possible, paired per-session comparison and appropriate support. If not powered, report difference as descriptive and NOT_STATISTICALLY_RESOLVED, rather than treating two decimal places as proof.

## 96. Multiple comparisons

Many families, stress cases, thresholds and cohort slices increase chance findings. Document family-wise false discovery concerns; preregister primary endpoints and mark exploratory comparisons. Avoid claiming all subgroups validated because one aggregate test passed.

## 97. Confidence intervals under clustering

Use bootstrap units based on independent vehicles or sessions with documented deterministic seeds and resamples. If fewer independent clusters than floor, avoid false precision and return insufficient support. Record CI construction and assumptions and exclude leak of grouped IDs in public report.

## 98. Data drift vs performance drift

Input-feature drift is measurable without labels; performance drift is not. A PSI threshold hit is a distribution warning, not evidence that prediction error or hardware failure increased. Never infer degraded recall from unlabeled imported telemetry.

## 99. Temporal re-evaluation

Score frozen models on later eligible synthetic windows without refit (under exact artifact/data policies) and compare error/coverage/bins over time. A separate optional evaluation-only retrain comparison may be allowed for research, but cannot modify current registry or serve predictions; if done, keep strict training split and exact experimental artifact identities.

## 100. Safeguards for evaluation-time fitting

Fitting a calibration candidate is permitted OFFLINE on designated calibration partitions, but never invoked from Phase 9D HTTP, Phase 9F agent, MCP, or public UI. Reject accidental import/wiring that makes newly fitted maps available for on-demand inference without explicit future production approval.

## 101. Code architecture

Prefer a new `vehicle_platform.evaluation` or `vehicle_platform.calibration` bounded package with pure metrics/calibration/drift modules, immutable typed contracts, protocol runner and repository adapters. Reuse 9B splitting, labels and model artifact loaders and 9C detector scoring/frozen reference. Avoid a new heavyweight ML framework or copying existing feature formulas.

## 102. Dependencies

Reuse pinned numpy/scipy/sklearn/pydantic/sqlalchemy and existing pytest. Add dependencies only when justified, pinned, audited and reflected in uv.lock. CI must work offline using deterministic fixtures; no paid AI, external analytics, unrestricted web/network access.

## 103. Execution resources

Bound row counts, folds, calibrator candidates, bootstrap repetitions, batch sizes, CPU threads, memory, wall clock, artifact bytes and output report size. Fit/score in worker threads/process isolation as appropriate, never unbounded database scan. Staged artifacts must be atomic and cleaned on failure.

## 104. Operator authentication

9G CLIs are internal operator/offline tasks, not general users. If any internal API route is necessary for reading reports, require same or stricter 9D dev/test authorization and do not expose source IDs or private metrics. Prefer NO HTTP surface. No secret in environment output, logs or stored evaluation receipt.

## 105. Migrations, if introduced

Inspect latest Alembic head (Phase 9F introduced 0018_agent_prediction_lineage). Add 0019 or next available revision additively. Test upgrade from 0018, downgrade to 0018, re-upgrade, fresh database migration and zero mutations to previous FeatureSets, models, anomaly findings, prediction receipts, evidence bundles or agent evidence links.

## 106. DB immutability tests

Assert new finalized evaluation protocol/calibration receipt/report rows immutable via DB checks/triggers or content-addressed versioning. Unauthorized UPDATE/DELETE, conflicting fingerprint and wrong FK must reject and rollback. Concurrency/idempotent replay must not duplicate versions or incomplete reports.

## 107. Validation artifact layout

Use ignored `.validation/phase9g/` for manifests, raw aggregate observations, fold receipts, per-model/per-family metric JSON, calibration/reliability chart data, stress/outlier matrices, benchmark and final summary. No raw telemetry or customer data. Checked-in docs summarize meaningful results and point to evaluator commands for reproduction.

## 108. Machine-readable reports

Output a stable `phase9g-evaluation-v1` JSON with base SHA, final SHA, source roles, cohort supports, label/oracle availability, methods, bins, actual metrics and undefined states, calibration candidate decisions, cross-family alarms, drift metrics, OOD/abstention counts, gate results and scientific readiness label.

## 109. Text reports and charts

Provide human-readable Markdown summary plus deterministic noninteractive charts if existing repo supports generated plots. Calibration diagrams, histogram, scatter or heatmap must be labeled synthetic and generated into ignored report artifacts, not added as Phase 9H UI. Display support and confidence limits; no deceptive color-filled 'vehicle health' badge.

## 110. Original baseline reconstruction

Re-run original accepted 9B and 9C metrics from existing canonical evaluators, compare with versioned historical values, and document legitimate fixture changes. Do not force bit-exact equality if fixture generation evolved; tie all comparisons to immutable source SHA and protocol. Keep historical 9C cross-family findings visible.

## 111. Independent evaluator

Implement `scripts/evaluate_predictive_reliability.py` or equivalent, with independent oracle arithmetic and genuine project code paths. Set up disposable TimescaleDB for 9A/9B/9C/9D/9E as required, generate new controlled held-out scenarios, load actual registered model/detector artifacts, execute offline calibration/stress, persist and verify receipts. Do not simply assert the same function's output equals itself.

## 112. Independent numerical oracle

For selected tiny deterministic fixtures hand-calculate Brier, ECE bins, confusion/FPR, source coverage, log loss, AP simple cases and PSI/moment shift where defined. Independent evaluator must compute expected outcomes without calling the production metric implementation. Machine-assert rounding and undefined classification.

## 113. End-to-end holdout

Generate a separate unseen engineering synthetic split with at least all three 9B tasks and all four 9C families, normal plus confounded and shifted cases. Score with frozen prior artifact and valid serving semantics, but calibrate only on disjoint designated set. Held-out fit/scoring is NOT the same as invoking 9D model serving from the agent.

## 114. Positive calibration fixture

A model with known simulated calibration bias should demonstrate appropriate method fit and improvement on VALIDATION when supported, with scored TEST comparison reported honestly. A perfectly calibrated synthetic null fixture should not be degraded by forced isotonic mapping without documentation.

## 115. Negative calibration fixture

A badly misspecified or too-small cohort, all-negative labels or extreme shift should produce insufficient support or worse held-out calibration without a falsely favorable score. Method selection should abstain or retain identity according to predeclared policy. Tests confirm no 'calibration success' without evidence.

## 116. Label availability adversaries

Remove target outcome from 9B final window or supply late-labeled pull and verify no future-derived label enters calibrator fitting. A missing real mechanical label is not negative; ignore it in calibration numerator/denominator with explicit count and reason.

## 117. Chronological adversaries

Duplicate sessions, overlap history, same physical pull rekeyed, post-cutoff configuration, future target, late ingestion, reserved final test label in calibration train. Verify no leakage and that grouped fold counts/row hashes remain deterministic.

## 118. Calibration contamination adversaries

Fit isotonic with test labels, target-derived score, prevalence chosen after test, or scaled features learned on test; guard rejects or independent acceptance detects leakage. Verify no trained calibrator updates the 9B original ModelVersion, checksum or 9D ServingBinding.

## 119. Anomaly injection adversaries

Fuel missing vs low fuel pressure, clean ambient shift, high/low thermal, boost-only with no performance change, subtle multi-family, sampling noise, normal but unusual configuration and reference contamination. Each scenario's oracle remains evaluation metadata and does not become detector input.

## 120. Cross-family alarms adversaries

Deliberately create a boost-only injection that triggers a fuel detector and verify the cross-family matrix exposes it as cross-family alarm, not a confirmed fuel fault. Include both independent family and multi-family actual perturbations to prevent simplistic misleading false-positive accounting.

## 121. Drift adversaries

Generate feature distribution changes with unchanged label relationship and label relationship changes without obvious mean shift. Assert the evaluator distinguishes observable feature drift from evaluable performance drift and declares concept drift UNKNOWN when labels are missing.

## 122. Subgroup leakage adversaries

Create two vehicles with same make/engine label but different configuration/telemetry source and ensure they are not silently treated as one healthy baseline. Hold out one vehicle entirely; document correct abstention when no eligible reference, not forced cross-vehicle generalization.

## 123. Artifact tampering

Change calibrated map/model artifact bytes, version, library tag, feature order, fold manifest or source checksum. Reject with safe machine codes before untrusted load or verified evaluation output. Test path traversal/symlink attacks and artifact byte upper bound.

## 124. Source integrity adversaries

Mutate saved 9D receipt threshold, 9E evidence graph, 9A source hashes, 9C frozen reference or 9F run-local citation mapping; evaluator must refuse to treat inconsistent result as valid calibration support. Never silently pick newest replacement version.

## 125. Numerical pathologies

Test NaN/Inf, negative/over-one probabilities, scores exactly 0 and 1, empty bins, zero-variance MAD, constant targets, ties, unbalanced folds, undefined ROC/AP, out-of-range timestamps, unit mismatches and extremely small support. Produce explicit error/undefined state, not fabricated 0.0.

## 126. Report antifabrication checks

No acceptance report may claim metrics absent from executed source score rows. Compare expected total with actual sample/support denominators and original row IDs; ensure missing/abstained not counted as TN. Require commit-tied source manifests and no stale run receipts.

## 127. 9F compatibility tests

9F's agent must still render original uncalibrated 9B score and 9C statistical output, keep `score_is_probability=false`, respect 9E verified evidence, source role, diagnostic refusal and production block. Run deterministic agent-MCP acceptance on previously verified fixture; no new calibrated percentages, diagnoses or mandatory 9G dependency.

## 128. 9D compatibility tests

Previous authorized 9D API scores/thresholds/responses should remain byte/semantic equivalent for exact same fixture, source and version; 9G neither approves new models nor exposes calibrator via service. Test disabled/prod behavior still fail closed.

## 129. 9E compatibility tests

9E immutable PredictionEvidence source graph remains unmodified. 9G may reference it for lineage but not rewrite verified states or claim scientific calibration from source integrity. Test snapshots of pre-existing DB table digests.

## 130. 9C regression tests

Run anomaly acceptance including original reference support, quality/cutoff, robust MAD/IsolationForest, source roles, matched configuration, artifact checksum and original benchmark. No 9G research threshold changes existing 9C decisions.

## 131. 9B regression tests

Run original predictive models acceptance, valid time-ordered train/val/test, model registry and frozen artifact checks, held-out and walk-forward. Add independent 9G research-only calibrator and preserve all original output IDs and scores.

## 132. 9A and earlier regression

Run Phase 9A feature/dataset full acceptance, Phases 0–8 canonical deterministic gate, Phase 6 MCP, Phase 7 specialist and 7D deterministic harness, Phase 8 cached RAG. No paid provider calls. Keep Phase 7D final-source 120-execution rerun caveat documented.

## 133. Quality and typing

Python Ruff, mypy, pytest coverage, strict dataclasses/Pydantic, SQLAlchemy/migration validation, dependency review, container security, CodeQL, generated contracts if touched. Do not weaken test, lint, security rules or thresholds to force green.

## 134. Benchmark protocol

Report per-study wall time, CPU, peak RSS, DB sessions, dataset row/fold count, calibration fit time, offline evaluation throughput, artifact bytes and replay cost across normal and maximum supported fixture sizes. This is workstation/CI engineering performance, not real-time on-car response SLA.

## 135. Observability contract

Add bounded OTel counters/timers/histograms for evaluation runs, methods, status, calibration source role, abstention reasons, dataset support, drift feature family and integrity violations. Never include vehicle IDs, VINs, feature numeric values, artifact path/hash, arbitrary user query or label source string as metric labels.

## 136. Tracing and privacy

Trace cohort materialization, group/time eligibility, source artifact check, offline score extraction, calibrator fit, held-out evaluation, drift/stress computation, report canonicalization and immutable persistence with bounded categorical attributes. No raw metric score arrays, customer data or secrets in spans/logs.

## 137. Operator runbook

Document prerequisite Docker/TimescaleDB, safe disposable DB config, sequence of 9B/9C artifact evaluation, 9G protocol generation, calibration candidate, held-out tests, anomaly false-alarm matrix, drift comparison, report inspection and cleanup. Include no real token, VIN or customer dataset. Use reliable make commands.

## 138. Make targets

Implement actual functional targets (adapt names to repo): `make test-predictive-reliability`, `make phase9g-acceptance`, `make benchmark-predictive-reliability`, `make predictive-reliability-observability`, optional `make calibration-report`. Wire bounded deterministic checks into canonical Docker/full stack. No no-op PASS.

## 139. Document architecture

Create `docs/architecture/phase-9g-evaluation-calibration.md`, protocol diagrams, source/version mapping, 9B vs 9C scientific distinctions, result/label eligibility, calibration policy and serving fence. Explain how 9G reports might support future 9H display with caveats without actually adding dashboard functionality.

## 140. Document evaluation

Create `docs/validation/phase-9g-acceptance.md`, `docs/validation/phase-9g-model-calibration.md`, `docs/validation/phase-9g-anomaly-reliability.md`, `docs/validation/phase-9g-drift-applicability.md` and a 9G traceability ledger mapped to ALL numbered sections. Reports cite actual generated receipts and numerical supports.

## 141. ADRs

Add next sequential ADR(s): calibration candidates limited to synthetic/offline research; disjoint chronological calibration+held-out splits and uncertainty; anomaly false-alarm vs injected-pattern semantics; immutable evaluation artifacts, source-role scientific gating and no auto-promotion. Inspect ADR numbering before choosing filenames.

## 142. Update roadmap and context

Update README, docs/roadmap/README.md, AI_CONTEXT.md, testing/observability/security docs and applicable model cards. Phase 9F PR #50 is merged at baseline 327c63f35b4e7bc0eba31bbec81d20206be8afa2. Mark 9G implemented only after verified gate; 9H remains planned, no production readiness claim.

## 143. Phase 9H interface caution

9H may eventually visualize properly labeled source/quality/applicability and uncalibrated risk notices; 9G exposes only internal versioned research read contracts or sanitized static aggregates for future consideration. Do not build UI gauges, live trends, push alerts or probability badges now.

## 144. Scientific communication

Write plain-language examples explaining Brier, ECE, false-positive burden, OOD shift and different sensor/cutoff meanings. Distinguish measured vehicle observation, synthetic classifier target, outlier score and verified mechanical fault. No percentages labeled 'engine will fail' based solely on synthetic training.

## 145. Caveat documentation

Clearly display no adjudicated mechanical failures, no real-vehicle outcome labels, no verified cross-brand generalization, small historical test cohorts, model-per-task variability and 9C family specificity issues. Real-world calibration, maintenance safety and prediction/repair decisions remain unestablished.

## 146. Calibrator version incompatibility

New 9A feature-generator, 9B model version or 9B label definition, 9C detector method/cohort or package version invalidates direct comparison without explicit documented compatible mapping. Reject unknown future schemas instead of silently coercing or claiming historical performance.

## 147. Model reporting ethics

Never cherry-pick favorable F1/precision from synthetic scenario without describing lower holdout values. The original performance 9B held-out test F1 around 0.643 vs validation 0.786 is a known limitation; 9G must preserve honest failure modes and not 'correct' them through retrospective split changes.

## 148. Predeclared standard acceptance

All mandatory correctness/integrity/gating/security/leakage/determinism tests must pass. Statistical success means valid metrics and honest insufficient results, NOT necessarily improved calibration, low alarm rates, absence of drift or generalizable automotive accuracy. Fail CI only when protocol/implementation or predeclared engineering scenario expectation is violated; report scientifically poor model performance truthfully.

## 149. Repeated calibration research

Repeat calibration experiments across deterministic multiple synthetic fixture seeds only with correct nested splits, reporting between-seed variance. Never report the aggregate as multiple independent real vehicles when generator design is shared. Deduplicate correlated physical observations.

## 150. Reproducibility manifest

Record Git SHA, protocol/fold/model/detector/schema checksums, sklearn/numpy/scipy versions, calendar cutoffs, random seeds, bounded worker counts, synthetic generator version, expected label/oracle and all selected hyperparameters. Include exact rerun commands and checksum verification.

## 151. HTTP isolation

Do not expose a general report API or 9G calibration endpoint that could be accessed with standard agent/MCP credentials. Test 9D/9E production-disabled and 9F gated behavior remain, and no extra tool appears in ordinary `mcp:read` catalog.

## 152. No write to existing source records

Perform pre/post database checksums/digests on 9A FeatureSets, 9B training/model tables, 9C reference/finding, 9D bindings/receipts, 9E bundles and 9F links. Only 9G-owned evaluation records may be inserted. If research requires fresh synthetic source fixtures they are on disposable DB and tagged accordingly.

## 153. Metric uncertainty serialization

Every metric must declare measure name/version, value or undefined reason, denominator, positive/negative support where relevant, excluded/abstained count, source role, cohort/fold ID, independence assumptions and uncertainty interval status. For continuous drift metric include unit/domain/cutoff.

## 154. Evaluation report completeness

No hiding under 'overall passed': per 9B task and 9C detector family provide baseline, method result, calibration/applicability, covered vs abstained source, holdout performance, stress/confounds and notable error cases. A final report must enumerate unsupported real-world conclusions.

## 155. Check positive real-data absence

An entirely unlabeled imported set must yield coverage/drift/quality info and NO Brier/calibration/failure prediction quality. Tests should assert unsupported statuses for 9B real calibration rather than silently using injected source perturbations as surrogate truth.

## 156. Clustered reliability negative

A confidence interval computed treating 40 correlated pulls from one session as 40 independent vehicles should be rejected by protocol/lint oracle or explicitly marked NONINDEPENDENT_DESCRIPTIVE. Independent sessions/vehicles are the resampling unit.

## 157. Drift false certainty negative

Under a constant input distribution but shifted label outcome, feature-only drift cannot prove concept shift. Under changed ambient input with stable outcomes, feature shift need not imply predictive performance loss. Both negative examples should be machine asserted.

## 158. Threshold sensitivity and utility

Report changes in precision, recall, alert burden and coverage over a bounded predefined grid for existing 9B scores and 9C research thresholds. If costs are unknown, provide scenario cost curves labeled hypothetical, not optimal recommended user alerts.

## 159. Calibration scoring under OOD

A mapping calibrated on synthetic source role or familiar vehicle/config must not be applied to unknown real role or OOD cohort. Return calibration applicability NOT_ESTABLISHED or OOD_WARNING; do not interpolate unmeasured conditions as healthy risk.

## 160. Sensitivity to reference sizes

9C reference min independent sessions and temporal span is already enforced; vary valid cohort sizes within controlled research and show threshold/alarm stability. Never rescore with future reference data for a historical cutoff.

## 161. Experimental artifacts serving fence

Ensure neither 9D approval CLI nor registered `ml_model_versions` can accidentally treat a calibration research file as a serving artifact. Use distinct registry/namespace/artifact root and explicit not-for-serving type checks.

## 162. Agent confidence research limit

9F agent deterministic grounding may be reevaluated for claim coverage, abstention and calibration-language errors, but not auto-calibrated into confidence about hardware fault. Any broad real-model evaluation of agent answers is Phase 11 or operator-approved separate scope, not a paid call hidden inside 9G.

## 163. Event alignment without pseudo-labels

Phase 3 `boost_drop` or `fuel_pressure_drop` events are observed rule events and may be correlated with 9C deviations for exploratory analysis, but cannot automatically serve as true component-failure label or proof of independent support. Report overlaps/descriptive rates only.

## 164. Report artifact falsification adversary

Manually change cached acceptance JSON to PASS, remove a fold, alter report SHA or hide failed stress cases: checker must reject due source/manifest/expected case set mismatch. Old 9F green SHA never counts as 9G exact-head success.

## 165. Independent run checker

Provide `scripts/report_predictive_reliability.py` or checker module that verifies receipt schema, exact current SHA, source-role/source dataset identity, every expected task/family/fold, numeric finiteness, denominator conservation, calibration eligibility, no source mutation and all mandatory independent tests PASS.

## 166. Canonical CI requirements

After final implementation SHA push, run quality, integration E2E, canonical Docker/full-stack, Security, Dependency Review, CodeQL Python/JS/TS and 9G evaluation/acceptance on that EXACT SHA. Recover from failures under your control. Stale branch checks and locally generated receipts from another commit are not authoritative.

## 167. External validation blocker honesty

If no real labels, report scientific readiness NOT_ESTABLISHED while still allowing Phase 9G engineering VERIFIED when implementation and synthetic/offline criteria pass. If Docker or CI is unavailable, report NOT VERIFIED with exact missing gates; don't replace all required integration gates with mocked tests.

## 168. PR ownership

Commit cohesive code/docs changes on existing `codex/phase-9g-evaluation-calibration`, push and open PR to main, leave OPEN and UNMERGED. Confirm local/remote HEAD equality, clean status, versioned migration/ADRs, tests, evaluator receipts and check links. Never auto-merge.

## 169. PR audit content

Include baseline 327c63f, final SHA, scope, protocol/algorithm decisions, calibration experiments per 9B task, 9C cross-family alarm matrix and threshold tradeoffs, drift and OOD, source role/support/abstention, real-label absence, no serving promotion, migration/immutable reports, benchmark, security, prior regressions and exact-head CI links.

## 170. Definition of Done — core contracts

[ ] Versioned, strict, deterministic offline evaluation protocols and reports; [ ] source-role/cutoff/canonical feature lineage; [ ] 9B three task reliability and disjoint calibration fit; [ ] 9C four detector families, clean FPR and cross-family alarms; [ ] separate scored/abstained coverage; [ ] applicable/OOD/unknown status; [ ] no diagnosed mechanical fault or false calibration percentage.

## 171. Definition of Done — research integrity

[ ] New unseen chronological, vehicle and scenario holds without leakage; [ ] proper metrics Brier/logloss/ECE/bins/support, F1/AP/BA where defined; [ ] uncertainty with grouped independence; [ ] honest negative outcomes/undefined support; [ ] offline PSI/shift and drift caveats; [ ] calibrator artifact only research; [ ] no active-model modification.

## 172. Definition of Done — security and persistence

[ ] Additive 9G-only registry/migration if needed; [ ] checksum/immutability/replay integrity; [ ] artifact tamper/source spoof protections; [ ] no customer PII/log labels; [ ] no public API, new MCP tool or Phase 9F score upgrade; [ ] no auto retrain/promote; [ ] controlled bounded operator CLI; [ ] zero writes to earlier phase immutable records.

## 173. Definition of Done — validation

[ ] Independent disposable DB evaluator and numerical oracle; [ ] 3x9B +4x9C frozen source coverage; [ ] leakage/holdout/real-label absence/false alarm/drift/quality adversaries; [ ] 9A–9F deterministic regression; [ ] full canonical Docker CI on last SHA; [ ] benchmark/observability and docs/ADR/runbook/ledger; [ ] PR OPEN, unmerged.

## 174. Definition of Done — science statuses

[ ] Engineering pipeline PASS can coexist with NOT_ESTABLISHED real-world validity; [ ] calibration maps are fixture-only; [ ] no reported real failure probability; [ ] unknown/unlabeled real sources remain unknown; [ ] no claimed per-vehicle guarantee or safe-to-drive decision; [ ] Phase 9H user UI, Phase 10 MLOps and prod Cloud explicitly deferred.

## 175. Final response contract

Return actual branch/base/final SHA/PR URL, implemented schemas/migrations, 9B task metrics before/after research calibration by split/support, 9C per-family clean FPR/cross-family alarms, uncertainty and undefined cases, OOD/drift/abstentions, applicable vs inapplicable source roles, independent evaluator and malicious test results, baseline regressions, benchmark/OTel, exact-head CI URLs, caveats and confirmation no serving changes. End EXACTLY `PHASE 9G — EVALUATION & CALIBRATION: VERIFIED` ONLY if all engineering gates pass; otherwise `PHASE 9G — EVALUATION & CALIBRATION: NOT VERIFIED` with precise blockers. Scientific real-world readiness remains separately NOT_ESTABLISHED without real labels; user performs merge.

## Required execution sequence

1. Inspect repository, branch and full spec. 2. Design versioned protocol/splits and pre-register synthetic holdout evaluation. 3. Implement offline evaluation and calibration/false-alarm/drift modules. 4. Run independent disposable DB acceptance and adversaries. 5. Document all observed results, including failures and unlabelled applicability limits. 6. Run full prior-phase regressions and canonical CI on final SHA. 7. Commit/push/open PR, do NOT merge. 8. Report exact executed evidence.
