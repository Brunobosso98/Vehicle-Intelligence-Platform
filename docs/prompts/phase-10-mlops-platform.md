# Phase 10 — MLOps Platform (Controlled Engineering Lifecycle)

**Repository:** `Brunobosso98/Vehicle-Intelligence-Platform`
**Required EXISTING branch:** `codex/phase-10-mlops-platform`
**Branch baseline:** `3085c5227a46c3c327249d0f2e982631d919b5a4` — merged Phase 9H PR #57 (2026-11-10).
**This phase:** Offline/control-plane reproducibility, pipeline orchestration, existing model/detector registry lifecycle, retrospective monitoring, matched model comparison, explicit review and rollback planning.
**Next phases:** 11 Agent Evals/Red Team; 12 Production Cloud Infrastructure; 13 Advanced Vehicle Intelligence.

This is the **authoritative implementation and acceptance contract**. Read ALL numbered sections before any code changes. Names of proposed new files/commands are examples to reconcile with the current repository; existing 9A–9H contracts are authoritative over guessed representations. No acceptance gate may be replaced with a simulated pass.

## Current architecture and target relationship

```text
       Phase 9A canonical FeatureSets and source provenance
                              |
             +----------------+----------------+
             v                                 v
      Phase 9B supervised               Phase 9C anomaly
      NEXT_PULL training                reference + detector fit
             |                                 |
             +----------------+----------------+
                              v
               Phase 9G OFFLINE evaluation
              reliability | shifts | applicability
                              |
                              v
         PHASE 10 MLOPS CONTROL PLANE (dev/test only)
          - versioned pipeline plan/run/step receipts
          - immutable experiment, data and artifact lineage
          - champion/challenger matched offline comparison
          - offline historical coverage, abstention, drift
          - policy gates, human review and rollback PLAN
          - reproducible audit, CI and OTel
                              |
                              | proposal/review only, NO auto-promotion
                              v
         Existing Phase 9D manual approval CLI and protected
         historical serving/evidence, not changed by Phase 10
                              |
          Phase 9E verified evidence -> Phase 9F grounded agents
                              |
                  Phase 9H protected UI
```

**Scientific rule:** Synthetic test/calibration quality proves only the stated source/population and original observable-label definitions. REAL-WORLD MECHANICAL FAILURE PREDICTIVE VALIDITY remains **NOT_ESTABLISHED**. Neither Phase 10 nor any automation may convert Phase 9B scores or 9C detector outputs into mechanical-failure probabilities.

**Safety/authorization rule:** No automatic production retraining, promotion, rollout, rollback or ECU writes. Phase 10 proposes and records engineering work; 9D state changes require a separate explicit authorized operator action. No public/agent/browser MLOps write APIs or exposed training tokens.

**Known inherited blocker:** The merged 9H Next.js standalone Docker runtime uses `NODE_ENV=production` while `predictiveEnabled()` and `demoEnabled()` currently reject that value even if `ENVIRONMENT=test`/development. Fix and validate this controlled-runtime issue without enabling public/actual production access. It is a required Phase 10 initial compatibility gate.

**Operational constraints:** Keep a bounded local/operator + GitHub Actions design. Phase 12 is responsible for production accounts, tenancy, cloud orchestration and high-availability deployments.

---

## 1. Phase 10 mission

Implement a fully auditable, deterministic, SECURITY-FIRST OFFLINE/CONTROLLED MLOps Control Plane atop the existing 9A–9H Vehicle Intelligence Platform: reproducible pipeline definitions and runs, immutable experiment lineage, candidate lifecycle, source-aware evaluation, offline champion/challenger comparisons, monitoring of recorded data/coverage/drift, explicit operator review, and rollback readiness. Deliver executed integration, not hypothetical schemas or dashboard mockups.

## 2. Repository and existing branch

Repository Brunobosso98/Vehicle-Intelligence-Platform, EXISTING branch codex/phase-10-mlops-platform, created directly from main at 3085c5227a46c3c327249d0f2e982631d919b5a4 following merged Phase 9H PR #57 on 2026-11-10. Fetch origin, verify exact ancestry/current HEAD and clean worktree; do not create alternate branch, rewrite history, force-push or modify main.

## 3. Complete mandatory reading

Read this ENTIRE numbered specification, root/nested AGENTS.md, roadmap, AI_CONTEXT.md, current Makefile, GitHub workflows, Phases 9A–9H architecture/acceptance/ADRs/CLIs/code, existing 7D caveats, security policy and the actual Alembic revision head BEFORE implementation. Map every requirement to source, tests, acceptance and delivery artifacts.

## 4. Repo reality: 9A source

Phase 9A provides immutable canonical FeatureSets, deterministic generation, row-time cutoffs, acquisition/source provenance, quality and bounded dataset manifests. All Phase 10 dataset selection must use those APIs/contracts; never compute features independently or permit post-cutoff future information.

## 5. Repo reality: 9B models

Phase 9B already owns three supervised NEXT_PULL tasks, temporal group splits, labels, selected candidate models, immutable ml_model_versions/training_runs, versioned artifact storage and stage CANDIDATE. Reuse `vehicle_platform.ml.{pipeline,registry,artifacts}` and their hashes instead of inventing a second model training/registry implementation.

## 6. Repo reality: 9C detectors

Phase 9C already owns thermal, boost_air, performance and fuel detector families, Robust MAD and IsolationForest candidates, fixed reference/cutoff/source-cohort policy, immutable anomaly_detector_versions and registered artifacts. Reuse originals; do not treat statistical anomalies as mechanical failures.

## 7. Repo reality: 9D serving

Phase 9D owns opt-in dev/test-only Prediction Service, source-role-specific active serving bindings, explicit approve/activate/revoke/rollback CLI, trusted artifacts and immutable receipts. Phase 10 cannot change those life-cycle semantics, expose approval HTTP endpoints, or activate automatically.

## 8. Repo reality: 9E/9F

Phase 9E materializes verified provenance over existing receipts; 9F serves source-bounded prediction evidence to gated MCP/LangGraph agents. Neither is an MLOps evaluation oracle, training trigger, or an endpoint for auto-upgrading model claims; preserve run-local grounding and all agent permissions.

## 9. Repo reality: 9G

Phase 9G provides research-only offline calibration, reliability metrics, bootstrap support, anomaly cross-family/false-alarm matrices, drift/OOD experiments, applicability and immutable evaluation records in Alembic 0019. Reuse these sources and explicitly report when scientific support is insufficient; never copy synthetic calibration into production.

## 10. Repo reality: 9H

Phase 9H added a protected read-only Next.js operator BFF with historical 9D/9E receipts, 9F agent context and 9G static research summary, while production/user-ownership access remains absent. Phase 10 must not widen 9H API, expose secrets, add an unprotected MLOps dashboard or start training via browser.

## 11. Critical inherited Phase 9H runtime blocker

Pre-merge code audit found `apps/web/src/lib/predictive/server.ts` requires `NODE_ENV !== 'production'` to enable private operator and synthetic demo, yet packaged `apps/web/Dockerfile` runs Next standalone with `NODE_ENV=production`; Compose sets `ENVIRONMENT=development`. Baseline 9H PR #57 merged at its audited `7d628bb` head, so this conflict persists unless later main changed it. Verify it, FIX safely as a required Phase 10 prerequisite, and demonstrate packaged `next start` or Docker standalone controlled test access. Production environment must STILL strictly deny private predictive reads and demo regardless of flags.

## 12. Phase 9H remediation safety

Do not fix by setting Docker image NODE_ENV=development or weakening production security. Separate Next build-runtime mode from explicit controlled platform environment; require configured dev/test env, independent credentials, source/vehicle allowlists, trusted private API/network, bind/ingress controls, default-off flags. Test NODE_ENV=production+ENVIRONMENT=test authorized; NODE_ENV=production+ENVIRONMENT=production denied; wrong/missing secrets, untrusted public peer denied. Run packaged browser E2E with actual 9D/9E receipts.

## 13. Non-goals and scope fence

NO production customer-facing model orchestration, real fleet deployment, general tenancy, automatic training on customer vehicles, auto-deploy/rollouts, self-healing, model store S3, distributed Kubernetes, Argo/Kubeflow/MLflow server by default, agent self-approval, ECU commands, live fault diagnosis, real vehicle failure probabilities, public monitoring alerts, Phase 11 agent red team or Phase 12 cloud infrastructure.

## 14. What MLOps means here

A control plane records WHAT was requested, WHO and WHY approved it, WHICH canonical dataset/code/model/detector/evaluator versions it used, WHEN it ran, WHAT scientific and engineering verdict it reached, and how it can be reproduced/rolled back. Development/test operators may run controlled offline jobs locally or via explicit CI; online inference remains in 9D.

## 15. Explicit scientific status split

Declare ENGINEERING_PIPELINE_VERIFIED separately from SCIENTIFIC_REAL_WORLD_VALIDITY_NOT_ESTABLISHED. Synthetic benchmark gains, calibrator fit, model selection or 9G ECE improvements do not mean safe/diagnostic/per-vehicle calibrated predictions. Unknown remains unknown.

## 16. ML scoring ontology

9B engineering_validation_score may be a supervised score for an EXACT next-pull observable label, never a general fault probability. 9C anomaly score is an outlier statistic method/family-specific and retrospective. 9G identity/sigmoid/isotonic are offline synthetic research-only; no score fusion or cross-family health percentage.

## 17. Offline human-approved safety

Nothing in Phase 10 can autonomously approve/activate/rollback any 9D serving binding, modify 9B/9C registered model/detector versions, change a frozen decision threshold, issue new 9D inference or 9E evidence by default. All proposed operational transitions are review documents until the independent 9D operator CLI is explicitly used.

## 18. Operating environments

Development/test controlled engineering dataset only. Production MLOps operation and any HTTP/agent trigger must fail closed by default. It is acceptable for a read-only scheduler status or report viewer to operate internally under explicit controls, but no public endpoint to launch a train/fit/evaluate job or inspect private datasets.

## 19. Source roles and strict cohorts

Carry exact source role `synthetic`, `imported_fixture`, `imported`, `real_vehicle` and existing mixed-source exclusion, vehicle/configuration/modification scope, source capability, sampling, sensor availability, cutoff and independent-session grouping through every run. Never train/evaluate a candidate on an incompatible source role without explicit protocol and truthful scope.

## 20. Existing source rights and privacy

Prefer synthetic and controlled fixture data for CI. Imported real-like data can support unlabeled feature distribution and source coverage only. Real labelled outcome training/evaluation requires explicit legal provenance, consent/rights, adjudicated observable-label definitions, timestamp and adequate support; do not invent positive/negative outcomes from DTC, high IAT, RAG, anomaly or operator comment.

## 21. Baseline security carry-forward

The merged 9H security policy contains 101 High package findings with reviewed, time-bounded exceptions, zero Critical and zero blocked as of final 9H scan. The narrow zlib exception expires 2026-11-12 and others 2026-11-18/20. Review scanners/current advisories as of execution; fix when possible, never silently stretch expiration or mask findings.

## 22. Architectural placement

Prefer `apps/api/src/vehicle_platform/mlops/` as bounded module (domain, orchestrator, policies, registry, monitors, reports, operator CLI, observability) and `scripts/phase10_*` for executable acceptance. Do not make another platform process unless there is evidence of need; the API modular monolith + CLI + GitHub Actions is sufficient.

## 23. No new heavyweight external platforms

Reuse existing SQLAlchemy/TimescaleDB, sklearn, Pydantic, pinned Python, OpenTelemetry, Docker and GitHub Actions. Avoid unnecessary Airflow, MLflow Tracking server, Celery, Redis, Kubernetes, cloud LLM APIs or external MLOps SaaS. If a new dependency is unavoidable, document alternatives and add pinned security-reviewed lockfile updates.

## 24. Control-plane data model

Define immutable, versioned strict contracts for PipelineDefinition, PipelineRun, PipelineStepRun, DatasetBinding, ExperimentManifest, ArtifactRef, CandidateRef, EvaluationGate, CandidateComparison, MonitoringProtocol, MonitoringWindow, DriftFinding, ReviewProposal, ReviewDecision, RollbackPlan, ReproductionReceipt and RunSummary.

## 25. Contracts versioning

Every persisted payload has explicit `schema_version`, fixed enums, bounded fields and safe defaults. Reject unsupported future schema, unknown method/task/family or arbitrary user-defined scripts. Pydantic strict+frozen where appropriate, no NaN/Inf, stable canonical hashing and UTC timezone-aware timestamps.

## 26. Two-level identities

Use deterministic pipeline logical key for intent+version+source+inputs+cutoff+seed and separate unique execution attempt identity. Identical idempotency request may replay same result; a new software commit, artifact or dataset must generate a new fingerprint. Never let retry overwrite a finalized attempt or pretend a failed attempt succeeded.

## 27. Pipeline template DAG

Define a finite allowed typed DAG: select 9A dataset+provenance -> validate source/cutoff/support -> [train 9B OR fit 9C] -> verify artifact -> evaluate candidate with 9G protocol -> compare -> generate review/report. No arbitrary shell tasks from untrusted manifest; dependency cycles and missing prerequisites fail before work.

## 28. Task/family catalog

Implement existing three 9B supervised NEXT_PULL tasks and four 9C families, including both supported 9C detector methods when artifact/version eligibility exists. Task policy must not silently substitute fuel detector to cover missing fuel pressure or convert 9C into a 9B task.

## 29. Pipeline definitions immutable

Definition includes schema/protocol versions, exact allowed task or detector family, source roles, cohort policy, selected feature/checksum, label or oracle definition, cutoff, split/seed, resource budget and evaluation gates. Once registered, changes create a new revision, not in-place overwrite.

## 30. Pipeline planner dry-run

Before data mutation, `plan` validates configuration, available artifacts/labels, source capability, sampling, cohort size, expected reads/writes, policy eligibility, prerequisites and budget; returns deterministic human-readable+JSON plan. Dry-run must not create training runs, model artifacts, serving approvals or evaluation records.

## 31. Controlled execution commands

Provide operator CLI commands such as `plan`, `run`, `resume`, `inspect`, `list`, `compare`, `monitor`, `propose`, `review`, `rollback-plan`, `reproduce` and `verify`; adjust exact syntax to code architecture. Each command has `--help`, explicit environment/task/source/protocol options, bounded selectors and structured exit codes.

## 32. Dry-run is default for dangerous tasks

No accidental train/fit/approve when invoking a bare CLI. State-creating work requires explicit `--execute` plus `--confirm-environment development|test` and exact pipeline fingerprint or analogous safeguards. Production invocation must fail closed, even if a repo GitHub Action dispatch parameter claims test.

## 33. Run state machine

Define PLANNED, QUEUED, CLAIMED, RUNNING, COMPLETED, INSUFFICIENT_SUPPORT, FAILED, CANCELLED, TIMED_OUT and optional BLOCKED_BY_POLICY, with allowed transitions and append-only transition events. No completed state if required artifacts or stage gates missing; failure keeps executed receipts and step status.

## 34. Step state machine

Steps are PENDING, RUNNING, SUCCEEDED, SKIPPED_INELIGIBLE, FAILED or CANCELLED with unique execution attempts, hash-bound inputs, start/end timestamps, source role and output references. Never call skipped training a PASS; propagate downstream skipped due missing labels/support.

## 35. Leases and concurrent operators

Use DB advisory/lease constraints or other deterministic coordination to prevent competing runners acting on same logical run. Bounded lease timeout, heartbeat/checkpoint and safe crash recovery; expired lease may be retried with documented fencing token, never two simultaneously authorized writers.

## 36. Idempotent resume and replay

A partial run must resume at a safe boundary with prior finished step checksum verification; if original artifact missing/tampered, fail safe and require a new proposal. Retry must not duplicate model versions, read/overwrite old artifacts or infer success from cached JSON alone.

## 37. Cancellation boundaries

Support operator cancellation before or between bounded steps; cancel active process gracefully and clean temporary resources. Do not leave orphan task locks, incomplete DB commits, leaking worker or unowned artifacts. No silent background operation after CLI exit unless explicitly queued under controlled scheduler.

## 38. Bounded resource policy

Cap dataset rows, sessions, features, candidate models, detector fit references, per-run artifacts, concurrent jobs, CPU/threads, memory, bootstrap iterations, wall time and DB query timeout by declared versioned resource budget. Limits enforced server-side/runner, not only UI/CLI text.

## 39. Artifact lifecycle and safety

Reuse internal 9B/9C trusted artifact roots, checksums, feature schema and loader controls; model bundles may contain pickle/joblib and are never accepted from arbitrary input or loaded before trusted origin/size/checksum/signature validation. No remote artifact URL, untrusted path or symlink escape.

## 40. Immutable experiment manifest

Record actual Git SHA, dependency pins, Python/sklearn/numpy versions, time cutoff, seed, feature schema/checksum, label definition, dataset rows/source-role, split identity, method hyperparams, model/detector artifact receipt, evaluation protocol and execution environment. Preserve provenance even on failure.

## 41. Experiment comparison identity

Champion and challenger comparisons use normalized task/family, same target/horizon, source role, matched cohort, matching source eligibility, immutable reference and exact evaluation protocol. Explicit `NOT_COMPARABLE` reasons when any constraint fails.

## 42. No build/test data contamination

Do not reuse final reserved 9G test holdout for training, calibration selection, candidate tuning or alert threshold optimization. A new experiment gets separately predeclared split and a later untouched holdout. Time/session/vehicle and config leakage tests must pass.

## 43. Evaluation gates as policies

Gate list includes engineering integrity/CI/coverage, chronological leakage, source-role eligibility, label support, artifact/training reproducibility, 9G scientific applicability and documented deployment limitations. A pass means only stated domain; absence of verified real labels forces `REAL_WORLD_VALIDITY_NOT_ESTABLISHED`.

## 44. Gate statuses

Each gate must be PASS, FAIL, INSUFFICIENT_SUPPORT, BLOCKED, NOT_APPLICABLE or NOT_EXECUTED with numeric denominator/support, reason, version, source evidence. `INSUFFICIENT_SUPPORT` is not quietly converted to PASS; overall readiness must distinguish execution complete from promotion eligible.

## 45. 9B evaluation policy

Use 9G Brier/log loss/ECE/reliability where genuine labels and held-out calibration evidence permit; AP/AUROC/F1/confusion only when defined. Report cluster-aware uncertainty and abstention/coverage. Candidate with insufficient support cannot claim improved calibrated failure risk.

## 46. 9C evaluation policy

Use clean-control false positive and cross-family alert matrices, detection support on synthetic injected target families, reference sensitivity, false-alarm burden per session, abstentions and source role; preserve method-specific score scales, never compare raw MAD to IF as equivalent.

## 47. 9G report reuse

Do NOT recalculate the same metrics using hand-written 'simplified' formulas. Invoke and validate Phase 9G canonical metric/assessment pipeline for candidate evaluations, and independently recompute a sample in the acceptance oracle. Version all methodology changes.

## 48. Calibration not serving

Store 9G calibrator candidates only in separate not-for-serving namespace and docs. MLOps may track calibration research lineage and suitability; cannot expose calibrated percentages in 9D, 9H or 9F, alter fixed 9B threshold or deploy a calibrator automatically.

## 49. Experimental seed handling

Record all PRNG seeds and generated fixture versions; ensure independent seed across folds and reproducible sorted input selection. Repeated runs vary only intentionally controlled stress cohorts, not hidden random data. Never force a supposedly improved model by changing test seed after inspecting scores.

## 50. Feature/schema compatibility guard

Training and evaluation reject unknown 9A feature version, feature ordering, canonical unit, missing required sensor, post-cutoff input, stale configuration/modification context or feature checksum mismatch. New feature schema requires new model candidate and can invalidate comparison/replay.

## 51. Artifact checksum and catalog

Catalog existing registered immutable model/detector metadata by safe FK/id and hash; do not duplicate binaries in mlops DB. Each candidate proposal points at exact immutable version/checksum and trusted artifact store. Mismatch, missing artifact, untrusted serializer or changed source role blocks proposal.

## 52. Candidate lifecycle separate from serving

Define versioned MLOps proposal lifecycle `DRAFT`, `EVALUATING`, `EVALUATED`, `REVIEW_REQUIRED`, `REJECTED`, `APPROVED_FOR_CONTROLLED_REVIEW`, `ARCHIVED`. It does NOT replace 9B `CANDIDATE`, 9C `ACCEPTED` or 9D `ServingBinding` states.

## 53. Proposal generation conditions

A report generator may create an immutable review proposal referencing evaluated candidate and potential same-task incumbent, bounded evidence and anticipated policy impact. It must never call 9D approval API/CLI or turn research-only eligibility into deployment permission.

## 54. Operator decision records

Explicit review requires operator identity and role from controlled offline auth config, exact proposal ID/hash, reason, scientific limitations, environment, comparison checksum and approval evidence. Store append-only audit, refuse ambiguous or stale proposals. An accepted review is NOT a serving activation.

## 55. Two-step serving separation

Even when an operator marks a candidate `APPROVED_FOR_CONTROLLED_REVIEW`, a separate conscious 9D `approve` and `activate` process with its own authorization/confirmation/source checks is still required. No Phase 10 command may silently execute 9D activation as a sub-step.

## 56. No CI approval privilege

GitHub CI can evaluate and report proposals but may not have 9D operator bearer or submit approve/activate/rollback actions. Pull requests and untrusted workflow_dispatch inputs must not gain protected secrets or write rights to serving metadata.

## 57. Rollback plan vs rollback execution

Phase 10 creates signed/hash-bound operator-readable rollback PLAN referencing an existing historical eligible 9D binding and its original artifact/version/source role, with gap/cutoff checks. Actual rollback remains an explicit separate 9D operator CLI action; never an auto-trigger from drift or CI failure.

## 58. Pre-flight rollback validation

Before presenting rollback plan, verify artifact checksum, version, source role, environment, approval history and current binding state. A missing/expired/incompatible artifact must block rollback readiness. Do not claim rollback succeeded until actual 9D event exists.

## 59. Audit after independent 9D action

Provide read-only reconciliation of current 9D serving state and approval events with MLOps proposal/rollback plan. Record observations with source event IDs; do not write to 9D immutable tables, impersonate operator or backdate an activation.

## 60. Clear prior phase immutable fences

9A FeatureSets, 9B/9C artifacts and model versions, 9D serving receipts/bindings/events, 9E evidence, 9F agent lineage and 9G evaluations remain immutable. Phase 10 may use 9B/9C official training APIs to create NEW controlled candidates, not mutate existing accepted versions or reuse their ID.

## 61. Deployment scope and naming

Call this a controlled model-release management/evaluation plane, not 'continuous deployment to vehicle', 'production ML monitoring', 'global model registry' or 'automatic rollback'. A lifecycle status `RELEASE_CANDIDATE` is evidence of review only, not live rollout.

## 62. Monitoring from already recorded receipts

Introduce bounded read-only periodic/explicit snapshots of historical 9D receipts: per task/family counts, scored/abstained/error statuses, source role, version, recorded/source cutoffs, coverage and age. No new 9D predictions, no extra 9E materialization and no 9F agent runs.

## 63. Monitoring without labels

From unlabeled imported/real data calculate signal availability, feature-source drift indicators and score distribution/abstention rates with correct provenance. Do not compute recall, precision, accuracy, calibration drift or mechanical failure risk without adjudicated ground truth.

## 64. Label-verified performance option

If independently verified target outcomes are AVAILABLE and policy permits, perform offline delayed-label join with timestamp-aware provenance and disjoint evaluation; report Brier/error confidence bounds and number of labels. If absent, return `REAL_DATA_UNLABELED`/`PERFORMANCE_UNKNOWN`, not fabricated 0 or synthetic surrogate.

## 65. Monitoring protocol and window

Define immutable MonitoringProtocol with cohort/source/task/model version, baseline selection, comparison window, minimum rows/sessions, sensor capability, quality exclusions, feature bins, method, alert thresholds and expected interpretation. Windows sorted by original observed time and original source role.

## 66. Captured vs observation time

Distinguish created_at, ingested_at, effective prediction cutoff, actual pull observed_at and optional label adjudication time. Do not compare future features against an old baseline as if known then; delayed ingestion must be handled explicitly and tests block horizon leakage.

## 67. Drift type taxonomy

Treat feature/covariate shift separately from prediction-score shift, input missingness, source role drift, reference cohort drift, actual label prevalence/performance drift and calibration drift. Offline source drift alone cannot prove model degradation or hardware failure.

## 68. Reuse 9G drift functions

Leverage 9G `population_stability_index`, `robust_location_shift`, OOD distance under source-aware baseline and bounded dimension limits. Preserve exact baseline version and protocol; no arbitrary dashboard PSI alert propagated to real vehicle as a mechanical diagnosis.

## 69. Shift thresholds versioned

Predeclare source-specific shift thresholds and minimum support in protocol before evaluating monitoring window; show warnings even if model performance is unknown, never choose threshold post-hoc to force nice dashboard. Inspect sensor sampling shifts as confounders.

## 70. Data quality and missingness

Report required vs observed sensors, canonical unit match, feature coverage, low-quality exclusions, duplicate timestamps, late ingestion and source role changes as possible causes. When monitoring window lacks adequate capability, prefer `INSUFFICIENT_SUPPORT` with raw counts.

## 71. Aggregation independence

Aggregate by independent session/vehicle and config for confidence or rate claims, not count thousands of correlated pull rows as independent engines. Store raw denominator and excluded/abstained counts; report statistically insufficient clusters rather than false-precision 95% intervals.

## 72. Zero-count ambiguity

When no newly scored 9D receipts exist, monitoring state is NO_OBSERVATIONS, not 0 alarms/healthy/normal. When no verified real outcomes exist, model error is UNKNOWN, never zero.

## 73. Multi-vehicle scope

Each monitor is scoped by source role, canonical feature version, engine family when observable and specific vehicle/config/modification (or valid supported aggregate). A single BMW-derived baseline cannot be silently advertised as cross-brand; unknown sensor availability remains unknown.

## 74. Shadow/challenger mode restricted

Optional shadow comparison uses offline read-only replay over a frozen eligible synthetic/controlled dataset with trusted candidate model/detector and predeclared time partition. No live 9D POST, no browser-triggered scoring, no extra auto evidence, and no side effect on active serving binding.

## 75. Challenger baseline provenance

Do not trust cached 'champion' labels. Verify actual currently active 9D binding and preserved version, plus original 9B/9C artifact checksum and model target/reference, before considering it champion. A historical active binding that was revoked is not currently live.

## 76. Same-cohort comparison requirement

Compare challenger and incumbent on IDENTICAL eligible held-out rows, same outcome/oracle, source role, cutoff, exact task/horizon, quality and exclusion policies. Surface differences in supported sample count and abstention. If incompatible, report NOT_COMPARABLE without ranking.

## 77. Decision impact report

Record proposed score/threshold/decision changes as hypothetical OFFLINE counts and economic assumptions only if supplied. No automatic threshold retuning or alert generation. Compare changes in abstention, false-alarm burden, latency, model size and uncertainty.

## 78. Serving version drift

Detect when a bound model/detector source checksum/version changed, artifact missing, approval revoked, feature schema stale or unresolved source role. This is an integrity/eligibility incident with a review flag, not permission for automatic replacement.

## 79. Artifacts and retention

Define content-addressed manifest for generated reports and referenced existing artifacts, immutable published receipts, protected temporary workspaces, size retention and operator cleanup. Never delete a model artifact still referenced by a 9D active/historical binding, receipt, evidence or MLOps audit; produce a DRY-RUN safe retention proposal first.

## 80. No destructive garbage collection

If implementing `gc-plan`, never perform auto delete in Phase 10. List exact unreferenced temporary artifacts and safe retention windows with reasons; deletion requires a separate future reviewed operator feature outside this phase.

## 81. Provenance graph

Create complete lineage traversable from source role, vehicle/config/cutoff + original 9A FeatureSet -> dataset/split -> 9B/9C artifact -> 9G evaluation -> Phase 10 proposal -> optional observed 9D approval. Missing edge or hash mismatch must block higher readiness.

## 82. Provenance immutability

Use FK, unique constraints and DB immutability/audit triggers where necessary. Never allow operator to rewrite a previously completed evaluation/proposal with changed report details under same ID. Record amendments as superseding events referencing older receipt.

## 83. DB migration

Inspect actual Alembic HEAD `0019_predictive_reliability`. If phase needs durable run/step/proposal/monitoring metadata, add additive `0020_mlops_control_plane` or next collision-free name, no historical migration rewrites. Test migration from 0019 -> head, downgrade -> 0019, reupgrade and fresh DB; protect prior 9A–9H records.

## 84. Normalized DB storage

Store bounded pipeline metadata, FK references, short status/metric summaries, immutable checksums and canonical small manifests. Do not duplicate all telemetry, FeatureSet matrices, raw 9E evidence graphs or PII in JSONB; large internal-only reports go to ignored artifact directory with verified digests.

## 85. Database transaction discipline

Use consistent short transactions, optimistic/FK/unique concurrency guards, timeouts, read-only source queries and separate append-only event writes. A failed step should atomically record failure without partially finalized model dossier. Never keep DB tx open across long sklearn fitting.

## 86. Crash-safe model staging

Stage new candidate artifacts under trusted temporary root, verify checksum/schema and source identity before registration; on failure clean only OWN unregistered staging, never delete shared artifact. Record immutable failure if model write and registry commit diverge; recovery reconciles safely.

## 87. Process lifecycle and crash recovery

Simulate SIGTERM/kill -9 during dataset build, training, evaluation, final registration and comparison. On restart, stale lease expires, run resumes from hash-checked checkpoint or emits terminal failure, with zero duplicate candidate versions or false PASS.

## 88. Observability architecture

Bounded counters/timers: mlops_pipeline_runs_total by pipeline type/status/source role; step duration, queue wait, artifact failures, evaluation gate failures, monitor windows, drift warnings and proposal decisions. OTel spans for immutable stage IDs and safe type/version labels; never put vehicle ID/VIN/path/hash/private feature values or arbitrary operator text in metric labels.

## 89. Failure taxonomy

Use stable reasons like SOURCE_ROLE_UNSUPPORTED, UNLABELED_REAL_DATA, INSUFFICIENT_COHORT, CUTOFF_LEAKAGE, ARTIFACT_TAMPERED, DRIFT_WITHOUT_LABELS, PIPELINE_TIMEOUT, LEASE_CONFLICT, SCHEMA_INCOMPATIBLE, SERVING_FENCE, STALE_PROPOSAL and MISSING_EVALUATION. Unknown reason fails closed and is not grouped as PASS.

## 90. Bounded logs

Emit structured one-line summaries with run ID opaque, pipeline type, stage name, outcome/status, elapsed time and trace correlation. Do not include training matrix, customer data, full model path, auth token, VIN, raw text notes or user/vehicle names in logs; redact in thrown error.

## 91. Performance and cost profile

Measure CPU, peak RSS, wall time, IO/artifact bytes, DB connections/queries and effective run concurrency for 3 9B tasks plus 4 9C detector families over bounded synthetic fixtures. Set predeclared budgets from existing 9B/9C/9G benchmarks; report actual results, not production SLAs.

## 92. Recovery and failure budget

Monitor failure, retry, per-stage timing, cancellation and predictable resource backoff. A pipeline stuck in RUNNING beyond lease should be recovered deliberately and leave audit trail; no infinite retrain loop or periodic billable external calls.

## 93. Operator UI not required

Phase 10 primarily API/internal CLI+CI. A small human-readable Markdown/JSON monitoring report is mandatory; do not build new public control-room web pages or inject activation controls into Phase 9H. If a UI read-only link improves traceability, it must preserve the existing 9H strict session and source boundary.

## 94. No external cloud/service writes

No GitHub Actions job uploads raw private telemetry/model artifacts or operator secrets; published CI artifacts contain synthetic fixtures and sanitized aggregate receipts only. No external W&B, MLflow tracking service, S3/GCS, email alert or paid external LLM is required.

## 95. Repository policies and CODEOWNERS

If adding workflow-based experiment execution, keep least privilege `contents: read` for routine CI; immutable synthetic job artifact may be uploaded for review. Any write to protected branches/PR review requires user permission outside automated pipeline; untrusted PRs cannot request privileged approval.

## 96. CI workflow design

Add separate `phase10-acceptance.yml` on PR, push/dispatch appropriately and include `make phase10-acceptance` in canonical full-validation workflow. For manual experiment workflow_dispatch allow only pinned fixture, task/family and protocol whitelist, default dry-run; no real data and no serving secrets.

## 97. Workflow artifact integrity

Publish sanitized manifest, run status, hashes, numeric aggregate metrics, comparison and monitoring report with exact commit SHA, workflow run URL and checksum. Receipt checker must reject report from an older SHA, swapped artifact or missing expected task/stress case.

## 98. No automatic scheduling by default

Scheduled monitor check can be proposed for later, but default Phase 10 has explicit operator trigger or CI synthetic check. No cron auto-training/approval, no background polling of live cars, no claim that system monitors every car 24/7.

## 99. Controlled schedule if implemented

If allowing periodic OFFLINE read-only monitoring under an explicit opt-in, require source-role allowlist, fixed maximum historical time window, start/end cutoffs, atomic dedupe and dry-run policy. It may emit internal review WARN only; cannot trigger inference, fit or serving actions.

## 100. Source attestation and trust

Do not let a user rename synthetic imported data as real_vehicle. Derive source role from existing 9A/9D attested provenance, verify source hash and configuration as-of cutoff; guard against a malicious edited manifest, DB source role or copied FeatureSet ID.

## 101. Unlabeled monitoring proper claims

A rising PSI, worse sensor completeness, more scoring abstentions or new anomalous distribution can recommend source/data review, not tell user mechanical fault probability increased or a part needs replacement. Differentiation reflected in metrics schema, report templates and output tests.

## 102. Scientific readiness policy

MLOps pipeline engineering outcome PASS is not readiness to serve a model on a real car. Keep status `SYNTHETIC_ONLY`, `REAL_DATA_UNLABELED`, `SUPPORT_INSUFFICIENT`, `OOD_WARNING`, `NO_REFERENCE`, `REVIEW_REQUIRED` or `NOT_ESTABLISHED` from canonical 9G, as relevant. Human cannot falsely override scientific facts by marking approved.

## 103. Model drift versus dataset drift

Without independently verified real-world ground truth, concept drift/calibration drift cannot be inferred; source drift available from FeatureSets can be classified separately. Test synthetic scenario with unshifted feature distribution but shifted outcome to show the difference.

## 104. Alert proposals not automatic notices

Monitoring can generate typed internal `MonitoringFinding`/`ReviewProposal` with severity LIMITED_TO_ENGINEERING and exact observed source counts. It must never issue fleet/user push notifications, production alerts or potentially unsafe driving decisions.

## 105. Safe baseline selection

Baseline time window and reference cohort must be chosen before comparison and preserve original 9C reference eligibility. Never borrow other vehicle hardware/modification cohort or future sessions to manufacture drift improvement.

## 106. Quality-adjusted comparisons

Report eligible vs abstained count and selection bias; a model with a low error rate because it scores 30% of easy pulls cannot appear better than one scoring 90% without explicit coverage comparison.

## 107. Reproducibility command

One explicit operator command must reconstruct a candidate's dataset/split/evaluation from frozen commit, protocol and fixture inputs on a disposable DB. Compare canonical row IDs, hashes and metrics within documented numeric tolerance; byte-identical pickle not mandatory across library changes.

## 108. Offline scoring equivalence

For a fixed eligible fixture, compare champion/challenger predictions via existing verified `offline_predict` or detector service, maintaining original score orientation/threshold. Verify equivalence with 9D recorded receipt where a corresponding stored approved version and cutoff exists, without requesting new 9D inference.

## 109. Incident review scenarios

Produce internal runbook for artifact missing/tamper, unexpected serving binding version, severe monitoring source drift, repeated pipeline failure, bad calibration experiment, leaked read-only UI capability and security exceptions expiry. Include safe containment and operator-only 9D rollback, not automatic incident modifications.

## 110. Security threat model

Explicit threat matrix for pipeline run injection, arbitrary artifact pickle load, path traversal/symlink TOCTOU, cross-source/vehicle data reuse, poisoned labels, target leakage, unapproved promotion, CI privilege escalation, lease races, stale reports, PII exfiltration, misleading scientific claims and model/version downgrade.

## 111. Secret handling

Operator-specific environment variables remain server-local; never embed secrets in pipeline manifests, CI logs, artifacts, browser bundles, prompt strings, GitHub PR descriptions or public metrics. CI should use throwaway fixture secrets for tested boundaries, not real 9D tokens.

## 112. Integrity adversarial tests

Tamper model artifact bytes, source FeatureSet hash, split manifest, label definition, evaluation receipt, proposal approval digest, 9D binding event and monitoring baseline fingerprint; independent checker detects it and blocked state persists after restart.

## 113. Authorization adversarial tests

Try non-dev/test environment, standard MCP read token, public web browser, unallowlisted source/vehicle, fake operator string and direct HTTP to pipeline CLI; no state changes or sensitive output. If pipeline has NO HTTP endpoint, test route catalog contains none.

## 114. Leakage adversarial tests

Inject future-observed feature, next-pull label into training feature, post-cutoff configuration, same physical session duplicated across train/calibration/test, training on final 9G reserved holdout and label adjudicated after cutoff. All blocked/reported with exact reason.

## 115. Concurrency adversarial tests

Two workers compete for same logical run and candidate version; only one lease can execute; replay gets identical result/blocked retry and no duplicate model versions. Test crashed worker lease expiry, idempotency key collision, stale proposed champion and partial artifact write.

## 116. Scientific claim adversarial tests

A high 9B supervised score, high 9C outlier value, low synthetic Brier, PSI alert and human review approval must NEVER yield real mechanical fault probability, confirmed component diagnosis, 'safe to drive' or production deployment. Check emitted JSON/Markdown wording and any 9H links.

## 117. Remote code/serialization adversary

Attempt manifest with shell command, Python expression, untrusted estimator class, URL artifact, extra task, escaped path, symlink and oversized model; reject before execution and deserialization. Do not use eval/exec/shell=True on user or manifest inputs.

## 118. Source mutation adversary

After pipeline run/replay/comparison/monitor and operator proposal, compare digests on immutable 9A–9H tables. Authorized NEW 9B/9C training creates new versions via existing APIs, but never mutates historical entries. Explicitly exclude new, declared candidates when comparing read-only monitor diffs.

## 119. Monitoring confidentiality adversary

A batch of real-like imported rows with VIN/GPS/owner data cannot be emitted in public report, tracer labels, CI artifacts, PR text or Markdown. Use safe aggregate only and prove absence in final artifact scans.

## 120. Durable database acceptance

Build fresh disposable TimescaleDB/Postgres, apply original migrations+0020; run/downgrade/reupgrade and verify previous 9D/9E/9F/9G data unchanged, only Phase10-owned schema changes. Test append-only finalized rows and approval/event FK constraints via direct SQL UPDATE/DELETE attempts.

## 121. First acceptance: 3 supervised tasks

Exercise real 9B pipeline with frozen synthetic 9A FeatureSets and three outcomes: fuel deviation, performance degradation, thermal degradation. Record actual source datasets, labels, exclusions, model versions, selected artifacts and 9G evaluation support. Must include one ineligible or insufficient candidate scenario.

## 122. Second acceptance: 4 anomaly families

Exercise 9C thermal, boost_air, performance, fuel on eligible same-cohort synthetic fixtures, preserving accepted detector artifacts and thresholds. Include both robust MAD and IF research comparisons when supported, and a no-reference abstention. No unfounded claims of fleet reliability.

## 123. Third acceptance: champion/challenger

Reconstruct or provision a reviewed 9D serving binding only in controlled fixture prior to read-only compare; compare matching challenger and original frozen incumbent on an identical untouched eligible holdout. Verify NOT_COMPARABLE branch when schema/source/target mismatches.

## 124. Fourth acceptance: proposals and rollback

Produce typed model dossier and REVIEW_REQUIRED proposal with exact source SHA and candidate. Simulate operator review but assert 9D serving binding/events unchanged; create rollback plan referencing trusted eligible historical binding, and reject stale/revoked/unsafe artifact plan. Do not execute actual rollback in normal pipeline.

## 125. Fifth acceptance: drift and missing labels

Prepare later synthetic shift and unlabeled imported source. Measure feature PSI/missingness/abstentions and document denominators; no real performance metric or calibration where missing labels; independent oracle catches 'accuracy=0' and 'real fault risk' mistakes.

## 126. Sixth acceptance: failure/crash/retry

Inject failure into each pipeline stage, two-worker lease conflict, restart, resume and cancellation. Check receipt/state transitions, no zombie jobs/duplicate model rows, no incomplete source mutation and bounded resource cleanup.

## 127. Seventh acceptance: 9H packaged regression

Execute actual `next build` + `next start` or the Docker standalone image with `NODE_ENV=production` AND ENVIRONMENT=test, explicit dev/test flags/credentials/allowlist/private backend, browser authorized read of 9D receipt+9E evidence. Confirm NODE_ENV=production + ENVIRONMENT=production, missing secrets or public config denies; existing 9H source parity/no-write tests still pass.

## 128. Eighth acceptance: integrity and privacy

Run artifact/checksum tamper, lineage version mismatch, unauthorized source role, untrusted model payload, path traversal, injection, raw secret/PII leak and stale run receipt attacks. Independent verifier requires all negative cases block with reason and no changed source artifacts.

## 129. Independent oracle

Implement scripts/evaluate_mlops.py + scripts/check_mlops.py (names may vary) that independently read 9A–9H DB and artifact manifest, verify cohort membership, original 9B/9C version IDs, evaluation report hashes, run/event transitions, proposals, no-serving state, monitoring denominators and exact committed SHA. Do not reuse the implementation's same validation function to assert itself.

## 130. Independent arithmetic

Hand-calculate a bounded small fixture for drift PSI, scored/abstained coverage, per-window counts, comparison delta and source/cohort identity. Assert expected outcomes from immutable source rows and independently computed primary metrics; do not accept opaque green shell exit only.

## 131. Acceptance evidence format

Write ignored `.validation/phase10/acceptance.json` with schema, code SHA, stage receipts, expected test/family counts, controlled source role and dataset counts, missingness/drift, comparison outcomes, proposal audit status, source digest before/after, CI/security/observability, benchmark and engineering vs scientific readiness. Create checker with checksum and reproducible command.

## 132. Coverage and number conservation

Assert all candidate rows partition into included, excluded, abstained or error with exact counts; sum monitor windows with no double count of same receipt; group by session for independence; no hidden losses when capped at max rows. Reject mismatch, not approximate.

## 133. Performance acceptance

Run bounded deterministic synthetic 3+4 model/detector pipeline and monitor 9D receipt window, report per-stage times, RSS/CPU and DB footprint. Predeclare budgets; if existing 9G acceptance is long, avoid repeatedly retraining unrelated historical phases in Phase 10 focused job except canonical validation.

## 134. Timeout semantics

Runner wall-time budget and per-step timeouts must be explicit. If CI runner cannot supply resources, mark requirement NOT VERIFIED instead of claiming pass from mocked model; include actual failure logs and recommendation for more capable runner.

## 135. Observability acceptance

Exercise OTel metrics/traces for run lifecycle, study evaluation, monitor warning, failed artifact, cancellation, review event and retry. Check labels bounded, no vehicle/user/PII fields, and spans reflect real timings. Preserve existing OTel stack smoke.

## 136. Web/API prior regressions

Run existing complete 9H protected BFF browser acceptance and original 9A–9G deterministic APIs; no UI control actions to start MLOps; the existing selected vehicle/history/evidence and Agent Workspace retain their security and correctness.

## 137. Full canonical validation

Run Makefile 0–9H gates plus new `make test-mlops`, `make phase10-acceptance`, `make benchmark-mlops`, `make mlops-observability`, new exact-head `phase10-acceptance.yml` and canonical Docker full-stack. Keep all 9H/9G checks green; do not relax checks/security scanner or exclusion thresholds.

## 138. Quality and dependency gates

Strict mypy/ruff/pytest coverage, generated OpenAPI and pnpm/TS, test integration, full Docker build, Gitleaks, Trivy, dependency review, CodeQL Python and JavaScript/TypeScript. Add no major dependency without lock/candidate audit. Pin GitHub Actions to approved SHA.

## 139. Current security exception handling

Run scanner with fresh database. Fix zlib exceptions expiring Nov 12 before deadline when compatible; otherwise document a real maintainer-reviewed short-term exception with specific proof, CVE/image/package/mitigation and review date, never silently renew. Other Highs expiring Nov 18/20 also tracked; unexcepted High or Critical blocks canonical gate.

## 140. Retain legacy business logic

Phase 10 must not change 9B outcome definitions, 9C frozen anomaly thresholds, 9D default-off/prod denial, 9E evidence graph verification, 9F grounded claims or 9G candidate calibration. If a prior 9H runtime issue is fixed, preserve all prior intended permission scopes and tests.

## 141. Model cards and dossiers

Generate per-candidate concise immutable dossier with task/horizon/source role, exact dataset/label/cohort, feature schema, training family, holdout performance and uncertainty, cross-family specificity, applicability limits, artifact checksum, intended environment and review status. Include 'No real-world mechanical-fault validation' prominently.

## 142. Operator decision notebook

Document explicit review checklist: verify serving candidate, CI exact SHA, change log, new model dossier, label support, source cohort, 9G scientific validity, rollback plan, stakeholder impact and maintenance safety. Required reviewer identity and reason are audit metadata, not a self-granted privilege.

## 143. Release readiness matrix

Separate PIPELINE_READY, EVALUATED_FOR_SYNTHETIC_ENGINEERING, REVIEW_REQUIRED, SERVING_APPROVAL_PENDING, APPROVED_FOR_CONTROLLED_REVIEW and NOT_PRODUCTION_READY. A successful CI run should never label an artifact 'deployed' unless an actual independently verified serving event is observed.

## 144. Release rollback rehearsals

In disposable controlled DB, validate the 9D CLI's existing explicit rollback logic on test-only candidate/binding after simulated fault; isolate it from normal MLOps automated run. Capture expected active binding before/after and no-effects when rollback denied; never run it against real data.

## 145. ML-specific incident guide

Runbooks for version mismatch, missing artifact, drift warning, low coverage, test leakage, scientific label absence and expired exception; safe operator resolution steps, provenance rechecks and controls to stop risky evaluation jobs. No 'restart model deployment automatically'.

## 146. Technical docs

Create docs/architecture/phase-10-mlops-platform.md with bounded architecture, state machine and data flow; docs/runbooks/mlops-control-plane.md; docs/validation/phase-10-acceptance.md, phase-10-pipeline-evaluation.md, phase-10-monitoring-comparison.md, phase-10-security-reproducibility.md and phase-10-traceability-ledger.md. Include exact observed results, not templates.

## 147. ADRs

Create sequential ADRs starting after `0046-phase9h-protected-predictive-ui.md` for offline MLOps lifecycle, separate governance versus 9D serving, immutable candidate/experiment lineage and human-only activation, source-role/label-gated monitoring. Add concise explanation why no Kubeflow/MLflow tracking service is required for Phase 10.

## 148. Roadmap correctness

Update README and docs/roadmap/README.md to mark 9G and 9H merged, PR #57 -> main 3085c5227a46c3c327249d0f2e982631d919b5a4, Phase 9 engineering complete with scientific `NOT_ESTABLISHED`, Phase 10 under implementation until exact-head accepted, Phases 11–13 still future. Clean stale 9H open-PR wording and old Phase 7A/7C inaccurate overview where safe.

## 149. Context and architecture notes

Update AI_CONTEXT.md, test strategy, security threat model, observability, local development and API/private operator docs with Phase 10 module names, runbooks, explicit not-for-serving limits, no online endpoints and CLI usage. No internal credentials or vehicle identifiers in checked-in examples.

## 150. Traceability ledger

Map every numbered section 1..N to implementation file, tests/CI receipt, doc/ADR and executed gate. `NOT_IMPLEMENTED` is not a PASS. Provide precise alternatives only when a requirement explicitly permits them, with independent evidence.

## 151. PR delivery and no merge

Push to existing `codex/phase-10-mlops-platform`, open PR against main and leave OPEN/UNMERGED. Confirm remote/local SHA, clean worktree, branch ancestry, new migration/ADRs and artifacts. Never merge or auto close the PR; user performs merge after review.

## 152. Exact head CI receipts

All required checks need HEAD SHA equality: Quality, Integration E2E, Security, Dependency Review, CodeQL Python, CodeQL JS/TS, canonical Docker/full-stack Phase0–10, Phase9G/9H acceptance, and Phase10 independent acceptance. Previous green SHA does not prove latest implementation; rerun after last change.

## 153. Canonical GitHub workflow failures

If a workflow times out, is cancelled, only tests a past SHA, fails new security scanning or does not exercise actual DB/artifact code, report NOT VERIFIED. Fix causes under your control; do not relabel a partial local 'make verify' as full validation.

## 154. Final acceptance: core

[ ] existing Phase 9H packaged-runtime incompatibility addressed safely and E2E proven; [ ] strict versioned, immutable MLOps pipeline/step/experiment contracts and persisted audit; [ ] all 3 supervised tasks and 4 anomaly families; [ ] exact source/feature/label/artifact lineage; [ ] idempotent bounded stage orchestration; [ ] no arbitrary code or production API.

## 155. Final acceptance: governance

[ ] 9G-based source-aware evaluation and honest uncertainty; [ ] matched champion/challenger offline comparator; [ ] source/quality/shift monitoring; [ ] explicit reviewed proposals and safe rollback plan only; [ ] no CI/manual command side-effect on active 9D without separate 9D explicit operation; [ ] no real-world failure probabilities.

## 156. Final acceptance: hardening

[ ] durable immutable DB records and 0020 migration roundtrip; [ ] artifact checksum/serialized path policy; [ ] concurrency, crash/recovery, staleness and adversarial leakage; [ ] privacy-safe metrics, no secret in reports; [ ] scanner exceptions fresh/current; [ ] zero old-source mutations outside explicitly created controlled candidates.

## 157. Final acceptance: proof and reporting

[ ] independent disposable DB acceptance and independent oracle; [ ] exact 9B+9C source counts, drift and support; [ ] failed/abstained cases visible; [ ] packed 9H browser with controlled mode; [ ] all 0–9H regressions and 0–10 full CI; [ ] benchmarks/OTel, docs, ADRs, traceability and final open PR exact SHA.

## 158. Final answer contract

Return authoritative base/current/final SHA and PR URL, complete architecture, exact run DAGs, experiment/candidate state transitions, 3+4 task/family metrics/support, challenger comparison/NOT_COMPARABLE controls, drift windows and unknown-label semantics, operator review and rollback limits, artifact/DB lineage and checksum proofs, idempotent recovery/attack results, packaged 9H fix receipts, security CVE status and dates, benchmark/OTel, migrations, independent test results, regression and exact-head CI links, scientific NOT_ESTABLISHED. End EXACTLY `PHASE 10 — MLOPS PLATFORM: VERIFIED` ONLY if all mandatory gates genuinely pass, otherwise `PHASE 10 — MLOPS PLATFORM: NOT VERIFIED` with precise blockers. DO NOT MERGE.

---

## Mandatory execution sequence

1. Fetch and inspect main+Phase 10 branch, read all requirements and root/nested AGENTS.md. 2. Reproduce and fix inherited packaged 9H controlled-operator blocker, retaining default-off and ENVIRONMENT=production refusal. 3. Map existing 9A/9B/9C/9D/9G registries/claims and finalize 10 run/state schemas. 4. Implement bounded reproducible plan/run/resume, immutable records, candidate comparison and monitor. 5. Add separate review/rollback PLAN without 9D activation. 6. Independently evaluate in disposable DB with actual prior code paths and adversarial tests, including full 9H packaged browser. 7. Run canonical entire stack, scanner, exact-head GH checks, docs, ADRs and traceability. 8. Push existing Phase 10 branch, create PR against main, leave open/unmerged. 9. Report executed evidence and science limits.
