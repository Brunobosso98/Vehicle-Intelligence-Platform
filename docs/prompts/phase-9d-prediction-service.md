# Phase 9D — Prediction Service

You are the autonomous lead engineer implementing **Phase 9D — Prediction Service** in Vehicle Intelligence Platform. This is a complete execution contract, not a brainstorming document. Read it IN FULL, including every requirement and final acceptance gate, before touching implementation.

Repository: Brunobosso98/Vehicle-Intelligence-Platform
Required existing branch: codex/phase-9d-prediction-service
Branch-created baseline: 7fc4c59f63a7be64e4ece5ab77bf61b09fc98bc0 (merged Phase 9C PR #43)
Previous completed foundations: Phase 9A Feature Engineering, Phase 9B Predictive Models, Phase 9C Anomaly Detection
Next phases: 9E PredictionEvidence, 9F Agent Integration, 9G Evaluation / Calibration, 9H Predictive Intelligence UI, 10 MLOps Platform, 12 Cloud Production Infrastructure

**Fundamental objective:** Make already trained, registered, compatible Phase 9B supervised models and accepted Phase 9C offline anomaly detectors available through a **bounded, authenticated, explicit-approval-only, read-only-with-respect-to-the-vehicle prediction service**. Provide real on-demand request/response inference, durable serving receipts and observational operational metrics. Never equate a model score with a real-world failure probability, diagnosis or maintenance instruction.

This is the FIRST controlled service boundary around offline intelligence. It is NOT a declaration of production readiness. The API currently has no platform-wide account authentication; Phase 9D therefore MUST be disabled by default and MUST NOT publicly serve predictions without new effective access controls and explicit source/version approval. Production and multi-tenant public exposure remain outside this phase.

---

## 1. Initial Git and repository inspection

1. Verify clean working tree, current branch, remotes, upstream, current SHA and Git configuration. Fetch origin.
2. Switch to the EXISTING branch codex/phase-9d-prediction-service and fast-forward only.
3. Verify exact baseline merge SHA 7fc4c59f63a7be64e4ece5ab77bf61b09fc98bc0 is in ancestry. Check current origin/main and preserve the merged 9A/9B/9C history.
4. Do not create a replacement branch, push to main, force-push, rewrite already pushed history or silently rebase.
5. Check repo-specific AGENTS.md guidance and all nested agent instructions. Fully read this file before code changes.
6. Record baseline SHA, current migration head, checks, runtimes, live state, and verified dependencies.

## 2. Read authoritative prior phase artifacts

Inspect, not merely summarize:
- docs/prompts/phase-9a-feature-engineering-foundation.md and 9A architecture/acceptance;
- docs/prompts/phase-9b-predictive-models.md and 9B architecture, model cards, evaluator, registry, artifacts and offline_predict;
- docs/prompts/phase-9c-anomaly-detection.md and 9C architecture, detector cards, service, registry, artifacts, evaluators and accepted threshold model;
- docs/roadmap/README.md, Makefile, .github/workflows, API routes/contracts/errors/budgets, core Settings, telemetry, migrations and tests;
- Phase 3 factual event logic, Phase 5 analytics and Phase 6 MCP access boundaries;
- security threat model and Phase 7/8 agent authorization and trust model, without reusing agent authorization indiscriminately.

## 3. 9D definition of success

A trusted operator can explicitly approve a previously evaluated immutable model/detector version for **controlled engineering serving**. An authenticated, bounded client can submit one observed completed pull and cutoff, obtain either a trustworthy version-pinned engineering score/result or an explicit abstention, and retrieve the exact durable serving receipt. Replays, failures, rollback, incompatible vehicle/context, missing signals, unsafe artifacts and unauthorized requests must behave deterministically.

The service must operate through real FastAPI HTTP routes and a directly testable service core; it cannot be merely a CLI wrapper or mock JSON. **No public fleet service or production deployment** is implied.

## 4. Existing Phase 9A data contract

9A created 79 versioned features, canonical Phase 9A pull FeatureSets, typed missing reasons, source capability classification, feature value timestamps, observed/ingested cutoffs, stable checksums and effective modification-aware history. Existing version identifiers include phase9a-pull-v2, phase9a-feature-generator-v2 and canonical-telemetry-v2. Do not rewrite 9A feature formulas to make a prediction easier.

Only genuine persisted FeatureSets produced through validated Phase 9A generation, with compatible checksum and source, may enter 9D. No client-submitted arbitrary float vectors for general vehicle inference.

## 5. Existing Phase 9B supervised contract

9B owns THREE next-compatible-pull engineering classification tasks:
- NEXT_PULL_THERMAL_DEGRADATION;
- NEXT_PULL_PERFORMANCE_DEGRADATION;
- NEXT_PULL_FUEL_DEVIATION (source limited).

Model versions are immutable CANDIDATE artifacts in the existing ml registry. The 9B ArtifactStore.load_registered checks internal joblib SHA, task, schema, threshold, dependency versions and allowlisted model family. The offline_predict helper accepts ordered features, expected units, missingness and quality and returns an engineering_validation_score plus a selected threshold decision. REUSE rather than bypass these checks.

A 9B candidate MUST NOT become service-eligible automatically merely because offline synthetic acceptance passed.

## 6. Existing Phase 9C anomaly contract

9C has four independent families (thermal, boost/air, performance, fuel), robust MAD + Isolation Forest candidates, exact same-vehicle/configuration/modification/source cohorts, immutable reference datasets and findings, accepted validation threshold choices, AFTER_PULL_OFFLINE horizon and explicit abstentions. Its AnomalyService.score_detector_version and trusted artifact loader must remain the authoritative behavior. The service must not train, refit, recalibrate or select a detector while responding to requests.

9C accepted candidate selection is **not** equal to 9D serving approval. Require an explicit second authorization to expose a version via service.

## 7. Distinct prediction horizons

Supervised 9B: NEXT_PULL — classify the next compatible pull's observable thermal/performance/fuel outcome from information available at the current input pull cutoff. Never read the actual future target pull to produce this score.

Anomaly 9C: AFTER_PULL_OFFLINE — characterize the already observed current completed pull relative to its frozen historical reference. Do not label it predictive failure estimation. Keep both categories explicit in route and result types.

## 8. Do not implement 9E–9H or Phase 10/12

Do not implement the public PredictionEvidence canonical contract, cross-tool evidence graph or causal explanation (9E); MCP tools, specialist agents and supervisor integration (9F); a fleet-wide calibration, drift/monitoring and retraining program (9G/10); predictive dashboard/gauges/notifications (9H); cloud identity, accounts, fleet authorization or general multi-tenant infrastructure (12).

9D may persist MINIMAL serving provenance for its own audit/idempotency. It must not claim to have completed the richer 9E proof contract.

## 9. Permanent safety boundaries

No ECU flash, coding, actuators, tuning, vehicle commands, unsafe modifications, automatic maintenance orders, failure-time predictions, root-cause declarations, OEM limits invented from generic data, or decision-making that overrides a qualified mechanic. Report an engineering model result with uncertainty and coverage limitations. Model scores are NOT probabilities that an engine, turbo or fuel pump will fail.

## 10. Architecture and ownership

Create a new narrowly scoped module following project conventions, tentatively vehicle_platform.predictions or vehicle_platform.prediction_service. It orchestrates the existing 9A/9B/9C domains, never copies their formulas or forks their registries.

Suggested flow:
  HTTP request + auth/rate/body admission
    -> explicit serving binding lookup and authorization
    -> vehicle/pull scope, cutoff, snapshot and compatibility checks
    -> registered immutable artifact load / verify
    -> bounded 9B offline_predict or 9C offline scoring
    -> append-only durable prediction receipt or explicit abstention
    -> sanitized typed response and metrics.

## 11. Existing API security limitation

Existing core API vehicle routes are not a universal authenticated account/tenant API. The 9D implementation MUST NOT assume authentication from their existence. In particular, Phase 4 acquisition bearer tokens identify a collection session, not a prediction-service operator or a vehicle owner. Phase 7 agent credentials are NOT a general solution to model-serving authorization.

Do not add unprotected /api/v1/predictions endpoints. If a safe authenticated dev/test serving surface cannot be demonstrated, fail closed and keep only a protected internal operator route; document the limitation honestly.

## 12. Explicit enablement / environment fence

The service must be disabled by default. Add bounded, validated Settings flags, e.g., PREDICTION_SERVICE_ENABLED=false plus protected operator credential secret and allowed environments. The first 9D implementation is allowed ONLY in controlled development/test or dedicated approved internal test mode, never in an arbitrary externally exposed production process.

A production boot MUST remain safe by disabling the serving routes or rejecting every request even when a caller sends a header. No demo/dev credentials in production. No silently permissive default when environment variables are missing.

## 13. Transport authorization

Use server-side bearer header validation with a securely generated high-entropy secret, constant-time comparison and no token logging; or reuse a demonstrably equal-or-stronger established operator identity mechanism if one truly exists. Header token must not be accepted as a query parameter, cookie, path or body field. Reject missing, malformed, oversized, wrong and revoked/rotated credentials before any artifact or vehicle database lookup.

Explicitly test authenticated vs unauthenticated behavior for both POST and GET surfaces and all versions, including introspection metadata.

## 14. Scope and privacy fence

This phase does not introduce user accounts or multi-tenancy. Its token grants bounded **operator-level** access to a controlled local dataset only; it is not a substitute for per-user ownership. Disallow production exposure until future real authorization exists. If scoped vehicle grants are added, validate them server-side before selecting any FeatureSet, not based on client-reported ownership.

Avoid leaking IDs, vehicle history, VIN, calibration context, artifact paths, full sensor matrices or model internals in unauthorized responses.

## 15. Network exposure

Limit documentation and runtime configuration to loopback/private trusted engineering environments. Never bind the prediction service to an Internet-accessible ingress by default. Do not trust X-Forwarded-For for identity enforcement absent a trusted proxy configuration. Bearer authentication remains mandatory even on loopback because loopback alone is not an authorization policy.

## 16. Dedicated request budgets

Add a dedicated Phase 9D admission/budget layer applied before large request parsing or DB/model work. Enforce max body bytes, content type, bounded fields, string lengths, batch size, rate, concurrency, timeouts and safe cancellation on disconnect. Do not reuse acquisition or agent budgets if their path semantics do not cover prediction routes.

## 17. Async execution and CPU isolation

The API uses async Python; sklearn/IsolationForest and joblib loading can block. Do not perform unbounded CPU-bound scoring on the event loop. Use bounded worker/thread execution, concurrency semaphores and fixed numerical thread counts; prove cancellation/timeout releases permits. Do not spawn unconstrained background tasks or process workers from an HTTP request.

## 18. API surface (typed and minimal)

Implement a stable, versioned engineering namespace consistent with existing FastAPI conventions. Suggested endpoints:
- GET /api/v1/prediction-service/versions — list ONLY explicitly serve-approved versions and bounded safe metadata;
- POST /api/v1/prediction-service/next-pull — authenticated 9B supervised inference;
- POST /api/v1/prediction-service/anomalies — authenticated 9C after-pull scoring;
- GET /api/v1/prediction-service/runs/{id} — fetch a bounded persisted serving receipt.

Names may be adapted if existing router/contract conventions demand it. All serving routes MUST use the same mandatory authorization/enablement/budgets. No training, activation, artifact upload/download or threshold-edit route exposed to HTTP.

## 19. HTTP request contract

Define strict Pydantic request types. For 9B require current completed pull, optional explicit vehicle for cross-check, task enum, timezone-aware observation_cutoff, source_role and optionally exact approved version. For 9C require completed pull(s), anomaly family/accepted detector or approved binding, cutoff, source role. Do not accept anonymous arbitrary feature vectors, formulas, class names, artifact filenames or SQL.

If version omitted, resolve only a single explicit active approved binding; no "latest candidate" fallback.

## 20. HTTP response contract

Versioned response schema must contain result type, task/family, horizon, status, stable receipt ID, requested and effective cutoff, selected model/detector version IDs, source role, quality/coverage summary, decision and score when valid, threshold where applicable, minimal lineage refs, and a clearly labeled interpretation/limitation field.

On abstention omit misleading numeric scores, keep explicit reason and quality/source state. Unknown/unsafe errors get a sanitized standard error shape. Do not return raw full artifacts or feature matrices.

## 21. Typed outcome states

Use status groups such as READY_SCORE, ABSTAINED_INSUFFICIENT_SIGNAL, ABSTAINED_LOW_QUALITY, ABSTAINED_INSUFFICIENT_REFERENCE, ABSTAINED_INCOMPATIBLE_CONTEXT, ABSTAINED_UNAPPROVED_VERSION, ABSTAINED_UNSUPPORTED_SOURCE, ABSTAINED_CUTOFF, and INTERNAL_FAILURE as repository conventions permit. Distinguish retriable infrastructure errors from legitimate no-evidence abstentions.

HTTP 401/403 is authorization, 413 is body size, 429 is budget, 404 is inaccessible/unavailable record, 409 is deterministic approval/version conflict, 422 is invalid shape/semantics and 503/504 is unavailable/timeout. Do not translate denied authorization into a "healthy vehicle" result.

## 22. Minimal provenance, not full PredictionEvidence

Store version, input FeatureSet ID/checksum, observed cutoff, model/algorithm version, source role, unit/schema signature, artifact checksum, threshold version, resulting score/decision/abstention reason, serving binding ID and created timestamp. More expansive cross-modal evidence contracts belong to 9E.

Avoid leaking raw telemetry or customer identity into logs or broad HTTP metadata endpoints.

## 23. Explicit serving approval model

Add a versioned **ServingApproval** / **ServingBinding** or equivalent dedicated registry, additive to 9B/9C. Model versions and detector versions retain immutable original lifecycle records. Approval must be explicit and auditable; it cannot be inferred from model CANDIDATE status, successful fixture tests or detector ACCEPTED status.

Approval applies to a specific exact version/checksum, task/family, source role, allowed environment, interface contract and serving scope. Require a reason, operator identity/attestation and immutable review/validation reference.

## 24. Readiness and approval safeguards

Before approval inspect:
- valid registered immutable 9B or 9C version with present trusted artifact;
- acceptable model/detector evaluation state and documented limitations;
- schema, source capability and cutoff support;
- synthetic-vs-real training provenance and out-of-domain restrictions;
- library/runtime compatibility and checksum verification;
- reference health/validation floor where applicable;
- environment and approved service version.

A synthetic-only engineering model can be approved ONLY for explicitly labeled synthetic engineering serving/fixture use. It MUST NOT automatically be approved to serve a real vehicle.

## 25. Promotion separation

A ServingApproval is **not production model promotion**. Use labels such as ENGINEERING_APPROVED or CONTROLLED_TEST only, not PRODUCTION_READY. Do not mutate 9B CANDIDATE -> PRODUCTION or 9C ACCEPTED -> production merely to satisfy this phase. Automatic promotion and fleet rollout belong later.

## 26. Operator approval interface

Provide a local operator CLI with explicit approve/activate, inspect, revoke/deactivate and optionally list commands. It must require environment confirmation, exact version, source role, documented justification and bounded intended scope. No HTTP endpoint should mint or modify approval. A dry-run must validate artifacts/source/eligibility without writing if supported by repo patterns.

## 27. Append-only activation and revocation

Maintain an immutable event ledger or versioned bindings with explicit supersession. Revoking approval must immediately prevent new scores from using that version; historical receipts remain intact. A changed binding must create a new event/version, not edit a past scoring receipt. Validate optimistic concurrency to prevent concurrent approvals creating ambiguous active choices.

## 28. Unique routing per task and scope

At most one currently active serving binding can resolve for a given approved task/family + source role + environment + intended scope, unless a fully explicit deterministic selector is supplied. Do not silently pick newest by timestamp or lexicographic version. Conflicting bindings must fail closed.

## 29. Rollback behavior

Operator can atomically switch back to a previously reviewed compatible version, with a recorded new binding event and reason. No auto-rollback triggered by scores. Old receipts stay bound to the original model and cutoff. Verify both happy path and conflicts for activation/supersession/revocation in disposable DB.

## 30. Safe artifact loading

Reuse Phase 9B and 9C trusted artifact loaders. They verify registry ownership, path, size, checksum, type, schema and pinned dependencies BEFORE deserializing joblib. Never load user-supplied pickle/joblib, arbitrary registry paths, dynamic Python expression/class name, signed URL download or uploaded files. All errors remain redacted.

## 31. Service startup and readiness

Disabled default means no model is eagerly loaded and no secrets need be supplied. Enabled controlled test mode validates its server-side secret and resource limits on startup. If approved models are missing, keep process otherwise healthy but serving readiness explicitly unavailable; never select an unapproved replacement.

## 32. On-demand model loading

Choose a bounded caching policy, or always load after checks if resource budget allows. Cache key must include version ID, artifact checksum, schema version and immutable binding identity. Cache cannot bypass fresh revocation/approval status; revocation invalidates or preempts use. No unbounded cache of models per vehicle or per user.

## 33. TOCTOU protections

Ensure approval and artifact validity are checked at the correct snapshot in relation to inference. Define semantics if revocation races with an in-flight request: admission snapshot and durable receipt must document which state was used. Never serve with an artifact whose bytes changed between verification and use.

## 34. Database migration

Add an additive migration after current 0015_anomaly_detection head (verify no intervening migrations first). Suggested tables for serving approval/binding history, inference requests/runs and minimal results with ownership/checksum constraints. Do not modify old migration files or rewrite 9B/9C persisted history. Explicitly test upgrade from existing 0015, downgrade and re-upgrade in disposable DB.

## 35. Persistence immutability

Use database constraints and/or triggers to keep completed prediction receipts immutable; activation ledger is append-only. Do not overwrite an old result when a model, cutoff, scope or input data changes. A new input fingerprint generates a new receipt. Use foreign keys/indexes where justified, and bound JSON payload bytes.

## 36. Deterministic request identity

Derive an idempotency identity from normalized request scope, authorized serving binding, exact model/detector version, cutoff, source role, input FeatureSet fingerprint and request contract version. Identical replay must return same result/receipt ID. A changed feature snapshot or model version cannot reuse an unrelated receipt.

## 37. Concurrency and transactions

Use unique constraints and database-safe retry/upsert or transactional locks as appropriate. Parallel identical requests must not duplicate durable receipts. A failure after artifact validation or before commit must leave no partially successful receipt. Define cancellation and retry semantics; do not hold long DB transactions over costly sklearn inference.

## 38. No implicit feature generation on request

By default consume already persisted verified Phase 9A FeatureSets. Do not transparently ingest telemetry, alter sessions, generate thousands of new FeatureSets, refit detectors or train models during a prediction request. If a FeatureSet is absent, return explicit unavailable/abstention and document how the operator can prepare it offline.

## 39. Phase 9B feature extraction adapter

Implement a narrow adapter mapping persisted canonical feature_values/quality/provenance to the exact ordered feature input schema expected by existing ml.artifacts.offline_predict. Preserve missing_reason, unit, numeric dtype, feature_quality and known-at-cutoff metadata. Never silently reorder, coerce incompatible units or replace missing fuel with zero.

## 40. Supervised feature availability

The input FeatureSet and every selected feature observation must be available at or before requested inference cutoff. Target NEXT_PULL outcome may not yet have happened and must NEVER be queried to score the current input. Enforce no target label, future event, late-ingested sample or post-cutoff modification leakage. Use 9A horizon validators, not a less strict duplicate.

## 41. Supervised context comparability

Follow 9B task's model/dataset/source applicability: current vehicle/effective configuration/modification state, telemetry source capability and adequate quality. Do not claim a model trained only on synthetic evidence works on N55 real data without explicit coverage and approval. Reject entity ID features and labels in score matrix.

## 42. Three mandatory supervised tasks

The controlled end-to-end fixture must serve NEXT_PULL_THERMAL_DEGRADATION, NEXT_PULL_PERFORMANCE_DEGRADATION and NEXT_PULL_FUEL_DEVIATION when signals exist. Each task may abstain for missing fuel, quality or model mismatch. Results must use 9B's frozen threshold and score logic without refit/retuning.

## 43. 9B result semantics

Return numerical engineering_validation_score in [0,1] only if valid. It is a model classification score for a defined future observable outcome, NOT the calibrated probability of a physical defect or any guaranteed risk percentage. The boolean decision is score-versus-frozen-threshold. Include label/task/horizon/version semantics and explicit non-calibration caveat.

## 44. 9C inference adapter

Use existing 9C detector version registry and existing AnomalyService scoring path, including strict cohort, quality and cutoff guards. Do not bypass immutable reference identity, required minimum row/session/span, source roles, detector threshold or artifact checks. Bind its internal anomaly finding to the 9D serving receipt instead of creating a conflicting second finding schema.

## 45. Four mandatory anomaly families

Exercise thermal, boost/air, performance and fuel in the controlled fixture. Support rejected/missing/low-quality feature scenarios, cold reference, mismatched vehicle/config/modification/source, replay and failed detector artifact. Keep 9C point/contextual semantics; no streaming persistence detector.

## 46. 9C result semantics

Report AFTER_PULL_OFFLINE horizon, INLIER/ANOMALOUS or explicit abstention, detector score orientation (higher = more statistically unusual), frozen threshold, coverage and model/reference version. Never convert a robust z-like score or IsolationForest value into a 0–100% fault-risk meter. Do not merge Phase 3 event assertions with statistical anomalies.

## 47. Historical Phase 9C findings

A 9C service request may reuse the existing idempotent finding when matching exact immutable inputs/cutoff/version. Do not modify the old finding. Preserve 9C run ID, finding ID and correlation-group reference as minimal internal lineage if permitted by access policy. Do not expose broad lists of other vehicles' findings.

## 48. Source roles

Handle synthetic, imported/imported_fixture and real_vehicle roles according to existing enums. A model trained on synthetic may only be served for an explicitly permitted test profile until separately evaluated/approved for other roles. Mixed role is denied unless a defensible documented policy exists; never silently treat "mixed" as proven real-world applicability.

## 49. Feature-version compatibility

Require exact Phase 9A FeatureSetVersion checksum and schema contract expected by registered 9B/9C version. Reject a future newer version that changes feature meaning without formal compatibility mapping. Future work can add explicit adapters; automatic shape coercion is forbidden.

## 50. Time and cutoff conventions

All submitted cutoffs must be timezone-aware ISO-8601. Define API timestamp normalization, upper future bound, observed-at and ingested-at availability, pull ended-at and created-at policy, source version recorded-at rules and timestamp-based state selection. Score after a completed input pull only; no inference on an in-progress pull under retrospective semantics.

## 51. Late-arriving telemetry

An observation with earlier physical timestamp but later ingestion time cannot influence an earlier cutoff. A recalculation at a later explicitly authorized cutoff creates a different immutable result identity, not a rewrite. Test this in end-to-end evaluator before and after ingestion.

## 52. Configuration history

No cross-vehicle mixing, and no blending pre/post hardware changes or incompatible calibration setups. Configuration and active modifications must be determined as known by the cutoff. Newly recorded historical modifications cannot change a prior receipt. Require explicit source capability, not guessed sensor readings.

## 53. Quality and abstention precedence

Apply: auth/enablement -> serving approval -> request shape/budget -> entity/cutoff -> version/source/capability -> feature schema and temporal eligibility -> data quality/reference -> artifact validation -> scoring. Document deterministic reason precedence when several causes apply. A low-quality/unsupported observation must not be interpreted as healthy or anomalous.

## 54. Missing signals

Missing sensor data remains missing with recorded reason. Require actual fuel-pressure measurements for fuel tasks. Optional missingness passes to 9B using trained imputation only under 9B's own schema; mandatory missingness causes abstention. Never synthesize a fuel-pressure value from boost, RPM or RAG documents.

## 55. Invalid samples and values

No NaN/Inf, booleans as numbers, unit mismatch, physically impossible sentinel values or unsupported quality state. Reject tampered FeatureSet provenance and inconsistent units before invoking sklearn. Preserve valid zeros and signs where physical semantics permit. Use canonical unit checks rather than arbitrary OEM limits.

## 56. Input limit enforcement

Limit number of pulls per request and total response records (prefer one pull for 9B and small bounded batch for 9C), model count, JSON body bytes, cutoff range, query rows, query duration, artifact bytes and max source record size. Document exact hard bounds and benchmark at/near limits. A global unbounded "all vehicles" query must not exist.

## 57. Latency budgeting

Bound end-to-end request time including DB acquisition, artifact verify/reload, inference and persistence. Set distinct timeout classifications: user canceled, 429 busy, 503 unavailable, 504 timeout. Do not claim an SLA from workstation/CI synthetic results. Ensure CPU budget prevents one heavy Isolation Forest request from starving normal health endpoints.

## 58. Idempotency header

An optional client idempotency key may be supported, but it must be bounded and scoped to authorization/request identity, never used alone to equate different FeatureSets or artifact versions. Server-side derived fingerprint is authoritative. Duplicate request with conflicting key/body returns a deterministic conflict.

## 59. Response privacy and tenant limitation

Never return full raw VIN, GPS, source token, artifact filesystem path, original full telemetry payload or third-party/user identifiers. For 9D controlled test a minimal existing vehicle ID may be returned only to the authorized operator for the explicit requested vehicle; no ambient fleet discovery. If multi-tenant ownership is not implemented, document that per-user access is unsupported and production remains disabled.

## 60. Model registry listing semantics

Only list explicitly approved versions in caller's allowed scope, with task/family, horizon, source applicability, evaluation class, validation status and approved version ID. Never enumerate unapproved experimental artifacts, filenames, disk paths or training datasets through the service. Pagination/limit and stable sorting mandatory.

## 61. Prediction history retrieval

GET receipt by opaque UUID or stable safe ID. Require auth before lookup; constrain to authorized controlled scope. Unknown, inaccessible and revoked-scope records return safe consistent HTTP behavior. Historical receipt retrieval is permitted after approval revoked only if audit policy expressly allows it; no new scoring on revoked versions.

## 62. Multi-call integrity

A service request touching 9C finding persistence and 9D receipt must not return "success" while either required committed receipt is missing. Provide a consistent transactional or compensating strategy, with idempotent retry and explicit partial-failure recovery. Never assume a distributed transaction across artifact filesystem, 9C finding table and 9D receipt.

## 63. Serving result state machines

Define request lifecycle (e.g. VALIDATING, READY, COMPLETED, ABSTAINED, FAILED) and binding states (APPROVED, ACTIVE, REVOKED, SUPERSEDED). Completed immutable receipts cannot move backward. Pending states cannot be mistaken for a successful score; rejected failures must retain safe reason and trace identifiers without raw samples.

## 64. Model and detector version pinning

Never infer an artifact version by filesystem scan, task filename or "highest version" sort. Resolve exact registered version from active binding or from an explicit version authorized by a matching active approval. Test both paths. A wrong family or task must be rejected rather than coerced.

## 65. Model tampering and dependency mismatch

Corrupt bytes, substitute symlink, modify checksum, change model schema, library version, estimator family or threshold. Every attack must fail before an unsafe load or successful score. Do not catch checksum error then fall back to another artifact. No arbitrary import of model algorithm classes.

## 66. Training and prediction separation

Serving must never instantiate TrainingRun, call train_task, modify LabelDefinition or reconstruct outcomes, fit a new IsolationForest, or tune any threshold on an HTTP path. Detect and assert no writes to training/reference/versioned feature tables in integration tests. Only serving receipts and reuse of 9C internal findings are permitted.

## 67. Operator commands

Provide a documented CLI to list approved/available candidates, inspect compatibility, approve, activate, revoke, rollback and optionally perform one smoke inference without public HTTP. Disallow production activation. Require explicit confirmation for state-changing operations; print safe bounded IDs, no secret values, and use nonzero exit status on failures.

## 68. Read-only service mode

Apart from its audit receipt tables (and idempotent existing 9C finding writes) the inference service is read-only. A failure must never mutate vehicle telemetry, configuration, pulls, events, FeatureSets, label training data or detector references. Add DB-level permission checks where practical without rearchitecting all project DB roles.

## 69. Endpoint availability contract

When the feature is disabled, the prediction routes must not provide scoring or private information. Choose 404 or 503 consistently and document the decision; never disclose artifact inventory unauthenticated. When enabled but not approved, deny with a clear safe approved-version absence status. Health readiness of unrelated API routes remains intact.

## 70. OpenAPI and generated clients

Add typed Pydantic schemas and generated contract checks following repo conventions. Do not accidentally publish secrets, internal artifact paths or raw model parameters in OpenAPI schema. A small generated API client contract is acceptable if required by CI; **no actual predictive product UI**.

## 71. Versioned API contract

Set an explicit v1 response/request schema version and describe forward compatibility. Future 9E can embed richer evidence under separately versioned types without breaking 9D receipts. Return clear deprecation/error responses for unknown versions and invalid enum combinations.

## 72. Status code and reason taxonomy

Use structured, bounded machine codes for unauthorized, feature disabled, approval missing/revoked, unsupported source, missing FeatureSet, insufficient quality, cutoff mismatch, cohort incompatible, model mismatch, artifact corrupt, busy and timeout. Stable reason codes MUST be tested. Avoid raw SQL/stack traces, sensitive enum values or credentials in HTTP error bodies.

## 73. Failure recovery

Test DB unavailable, artifact missing, corrupted file, sklearn exception, timeout, cancellation during scoring, aborted persistence, duplicate concurrent request and connection pool shutdown. Recovered systems must not resurrect revoked serving bindings or return stale cached success. Document retryable vs terminal failures.

## 74. Database connection discipline

Reuse project Database session patterns. Do not keep transactions and connections open during CPU-bound scoring. Use bounded pool/timeouts and close background resources during FastAPI lifespan. Assert no leaked DB connections at teardown in the independent evaluator.

## 75. Observability events

Instrument auth rejected, request accepted, binding selected/denied, feature lookup, artifact verified, prediction scored, abstention, persistence, replay, timeout and failure with bounded categorical reason labels. No raw vehicle identifiers, VIN, source hashes, version UUIDs, feature values, private prompts or tokens as metric labels.

## 76. Metrics design

Suggested metric classes: prediction_service_requests_total by endpoint/state; predictions_scored_total by task/family and source_role; prediction_abstentions_total by reason; prediction_duration_seconds; model_artifact_load_seconds; serving_approval_state_changes_total; current active approval count without high-cardinality labels; in-flight requests; rate-limit denials. Reuse existing OpenTelemetry patterns.

## 77. Traces and logs

Trace request budget/auth admission, serving binding resolve, canonical snapshot lookup, schema/quality validation, trusted load, inference, optional 9C finding reuse, receipt write and response. Correlation IDs only as permitted by repo security policy; metrics must not use them as labels. Redact credentials and raw feature matrices from traces/logging.

## 78. Benchmark design

Benchmark warmed and cold model loads, 9B logistic/rf paths, 9C robust MAD and IsolationForest paths, DB feature retrieval, approval lookup, scoring and result write. Include 1, 10 and near-max bounded requests, contention and after-disconnect cleanup. Record P50/P95/P99 only with adequate sample size, otherwise label insufficient samples. No production SLA.

## 79. Data coverage report

For each task/family report requested, authorized, admitted, approved, eligible, scored, abstained by reason and failed counts, plus role/version/quality coverage. Denied auth requests must not get counted as inference outcomes. Disclose whether fixtures are synthetic, imported or real-world unlabeled.

## 80. Independent acceptance evaluator

Implement scripts/evaluate_prediction_service.py (or repo-conventional equivalent) with a genuinely independent assertion layer. It MUST exercise actual canonical 9A data, 9B/9C registered trusted artifacts, serving approval CLI/service, real FastAPI ASGI/HTTP request/response, DB receipts, concurrent replay, authorization, revocation, latency budgets and observability. It must not simply assert mocks or predetermined JSON responses.

## 81. Disposable infrastructure

The canonical acceptance must create a fresh disposable TimescaleDB, migrate 0015 -> new head, downgrade to 0015 and re-upgrade, materialize controlled Phase 9A FeatureSets and register compatible 9B/9C model/detector versions using their real pipelines. Avoid expensive repeated generation when a verified deterministic fixture can safely reuse artifacts; no fixture may bypass version validation.

## 82. Real HTTP test proof

Use an in-process ASGI transport for fast deterministic tests plus actual launched HTTP/client integration in disposable stack where project conventions require. Verify POST and GET response models and header/URL behavior, client cancellation, 413/429/401/403/409/422/503, and that auth denial occurs before database/model access.

## 83. Auth adversaries

Prove empty header, basic auth, bearer typo, invalid token, oversized token, query-token attempt, token in POST body, expired/rotated token if supported, missing feature enablement, spoofed forwarded headers and production environment fail closed. Measure that no registered artifact load, feature query or sensitive status is disclosed.

## 84. Approval adversaries

Try unapproved CANDIDATE, 9C version accepted only for offline validation, rejected detector, incomplete/evaluation-failing model, altered checksum, wrong task, wrong source role, unvalidated real profile, conflicting active bindings and revoked binding. Every case must be blocked, independent of request permissions.

## 85. Cross-vehicle adversaries

Attempt wrong vehicle ID for pull, configuration change, late-created modification, wrong telemetry source, test synthetic model on real_vehicle, unsupported fuel on OBD-II and mismatched effective setup. No cross-vehicle data leak or "fallback to pooled fleet" should occur. Include oracle assertions and reason-coded abstentions.

## 86. Temporal adversaries

Create a future target-pull label available after cutoff, a late-ingested feature, an event created after cutoff, an observation before pull ended-at, a future-dated or naive cutoff, and a modification recorded retroactively. All must either be rejected or excluded deterministically. Scoring outcome must be invariant to future-only changes under the frozen cutoff.

## 87. Schema and quality adversaries

Inject missing pressure, wrong Kelvin/Pascal unit, NaN, Inf, boolean numeric, duplicate timestamp quality, invalid feature quality, missing_reason mismatch, unsupported 9A version and unknown feature key. Assert no fabricated score and no silent coercion. Required missing sensor returns an explicit abstention.

## 88. Reproducibility

Repeat identical approved requests after cold reload and warm cache. Compare numerical results within appropriate deterministic tolerance, version identity, input hash, cutoff, threshold, output class, receipts and abstention reasons. Repeat with reordered requests and parallel callers. Serialization bytes need not be stable if prior model cards already disclose that limitation.

## 89. Direct offline equivalence

For every mandatory 9B task compare real service response to ml.artifacts.offline_predict on the EXACT same verified ordered feature snapshot and model version. For every 9C family compare service score/decision to existing AnomalyService or deterministic internal 9C finding. Any difference beyond declared tolerance is a gate failure.

## 90. Synthetic fixture variety

Include multiple vehicles and distinct configurations, a modified setup, several chronological sessions and pulls, source-role boundaries, available/unavailable fuel, valid/low-quality observations, thermal/performance/boost perturbations and at least one cold-start cohort. Do not require all real-world tasks to score if the canonical setup lacks corresponding signals; synthetic acceptance fixture must deliberately include those signals to prove functionality.

## 91. Production-disabled demonstration

Test that ENVIRONMENT=production with all demonstration tokens/flags still cannot serve inference. Startup error or route-disabled behavior is acceptable but must be explicit and safe. Any acceptance path that secretly enables public unauthenticated serving is an absolute merge blocker.

## 92. 9D migration compatibility

Confirm Phase 9B labels/models, Phase 9C detector artifacts/findings, 9A feature records and earlier vehicle data are unchanged after migrations. Run fresh/upgrade/downgrade/re-upgrade, checksum old records, test immutable trigger behavior and serving receipt constraints. Never edit historical migrations.

## 93. Persistence adversaries

Verify duplicate concurrent request, failed result insertion, invalid JSON size, missing model foreign key, approval revoke during a request, rollback to earlier reviewed model and retrieval of historical receipt. Confirm no partial successful result appears after an induced DB exception.

## 94. Security scans and package policy

Run existing dependency review, CodeQL Python and JavaScript/TypeScript, secret scanning, image scanning and input-fuzz-like adversaries. Prefer reusing pinned existing sklearn/SQLAlchemy/FastAPI dependencies, adding no heavyweight serving framework unless strongly justified. Document any new dependencies, exact versions, lock changes and CVE dispositions.

## 95. No paid services

No paid real-model agent validation or Phase 8 embedding API calls are required for 9D. Use cached/deterministic paths and recorded prior paid-evaluation caveats. Do not run paid providers by default. The Prediction Service must not invoke generative AI; it's deterministic model/detector inference over recorded data.

## 96. Existing phase regression

Run canonical regressions for Phases 0–8, specifically Phase 6 MCP isolation, Phase 7 agents deterministic harness, Phase 8 RAG cached paths, Phase 9A feature/dataset validation, 9B supervised evaluation and 9C anomalies, including database migrations, browser E2E and security. 9D must not break current API clients.

## 97. Make targets

Add appropriate repository-conventional targets, tentatively:
- make test-prediction-service;
- make phase9d-acceptance;
- make benchmark-prediction-service;
- make prediction-service-observability;
- make prediction-service-smoke;
- make verify (canonical aggregate includes bounded deterministic 9D acceptance).

No passing target may be a no-op/placeholder. Avoid uncontrolled multi-hour repeated paid setup in local tests.

## 98. Benchmark and resource floors

Before final benchmark, predeclare specific engineering limits that can be measured reliably in CI, including request body, max batch, concurrency, artifact size and timeout cleanup. Latency numbers are observational; make gates about boundedness/correctness and measured utilization rather than an arbitrary "under 10 ms on all machines" claim.

## 99. Documentation artifacts

Create/update:
- docs/architecture/phase-9d-prediction-service.md;
- docs/validation/phase-9d-acceptance.md;
- docs/validation/phase-9d-model-serving-evaluation.md;
- docs/validation/phase-9d-traceability-ledger.md;
- docs/runbooks/prediction-service.md;
- relevant security threat model and runtime/operator auth docs;
- model/detector cards only if serving restrictions materially change their stated limitations;
- README, roadmap, AI_CONTEXT and testing/observability docs;
- generated API contracts and new ADRs.

## 100. Required ADRs

At minimum evaluate ADRs for (a) fail-closed controlled engineering API scope/auth; (b) immutable service approval/activation/revocation and snapshot semantics; (c) inference results/receipts without prematurely implementing PredictionEvidence; and (d) reuse of trusted 9B/9C joblib artifacts, CPU budgets and handler isolation. Follow repository ADR naming; do not overwrite prior ADRs.

## 101. Runbook examples

Include exact operator steps: enable controlled test mode with a locally generated secret; create/review version; explicit approve/activate for SYNTHETIC scope; POST supervised score; POST anomaly score; read receipt; repeat idempotently; revoke; demonstrate denial after revoke; troubleshoot low quality, absent fuel, mismatch, 429 and corrupt artifact. Never include a real token or customer VIN in committed examples.

## 102. Human-readable interpretations

Examples must identify scores as engineering values:
- a NEXT_PULL observable outcome classifier's score reflects a learned pattern under controlled training data, not real-world failure risk;
- a 9C anomaly score is relative statistical unusualness;
- abstention means the service lacks enough compatible evidence, not "vehicle healthy";
- predictive service readiness does not establish calibration or fleet validation.

## 103. Migration and serving state security review

Threat-model role spoofing, bearer leakage, public route accidentally enabled, model artifact deserialization, stale approval cache, version confusion, replay/idempotency, sensitive inference access and denial of service via CPU expensive jobs. Add executable tests and mitigations. Document remaining deployment controls that belong to future production infrastructure.

## 104. Real-data compatibility smoke

If a sanitized local CSV-import dataset is available, test read-only compatibility in a disposable copy without weakening minimum support. Record eligible/abstained counts; 9C previously had 264 imported pulls but insufficient exact-cohort support and eight rejected fits. Do not misrepresent this smoke as real-car accuracy or automatically approve real roles.

## 105. Evaluation-report integrity

Reports distinguish tested fixture, synthetic oracle metrics, uncontrolled real-world unknowns and genuine prior 9B/9C model-card limits. Keep both failed and passing candidate stories. Never copy older head's CI success and label it final-head proof. Include raw ignored machine-readable receipts, summarized checked-in reports and reproducibility instructions.

## 106. Consistent old docs

The 9C PR #43 was merged at 7fc4c59f63a7be64e4ece5ab77bf61b09fc98bc0. Update stale README, roadmap, AI_CONTEXT or acceptance text that still suggests PR #43 is open, while preserving historic reports as historical snapshots where accurate. Mark 9D implementation after proof; keep 9E–9H future.

## 107. Focused test cases

Create focused unit tests for flags/auth, enum validation, approval and binding lookup, schema mapping, cutoff, offline equivalence, results, metrics/cardinality, cache invalidation, artifact validation, idempotent keys, race/revoke, budgets, timeouts and clean shutdown. Existing 9A/9B/9C focused suites remain passing.

## 108. Independent DB + HTTP acceptance cases

The evaluator must independently assert:
- effective gate is disabled without explicit config;
- secret rejects unauthorized requests before data work;
- explicit approved version needed for serving;
- 3/3 9B tasks return correct frozen direct-offline-equivalent scores when eligible;
- 4/4 9C families return correct direct-9C-equivalent results when eligible;
- source/quality/time/compatibility abstentions and malicious cases;
- immutable receipts, idempotency, revoke/rollback, no cross-vehicle leakage;
- snapshot integrity, migrate round trip, no model retraining, no ECU write;
- bounded resources, metrics, tracing, security and cleanup.

## 109. Scope-specific acceptance floors

Predeclare engineering fixture floors for expected task/family support, idempotency correctness, response schema completeness, auth denial, resource-budget rejection, artifact-integrity rejection and complete absence of known temporal/cross-context leakage. Mandatory security guards, numeric equivalence and immutable receipts require 100% fixture pass. Real-car prediction accuracy must NOT be a gate because real failure labels don't exist.

## 110. Clean-state validation command

From clean disposable infrastructure run migrations, 9A generation, 9B artifact training/registration, 9C detector acceptance, 9D explicit test approval, real request paths, stored receipt retrieval, revocation denial and all regressions. Capture deterministic commands, versions and outcome counts. If the full suite cannot run locally, run the canonical CI and document what's missing.

## 111. Git and final exact-head verification

After the final implementation change:
1. Capture exact commit SHA, clean git status and branch ahead/behind.
2. Run all relevant deterministic local checks on the final code.
3. Push to codex/phase-9d-prediction-service, verify remote SHA exactly matches.
4. Open a PR targeting main only; no merge and no auto-merge.
5. Monitor every REQUIRED GitHub check on the exact final SHA: quality, integration E2E, Python & JS/TS CodeQL, Security, dependency-review, canonical Docker/full-stack and 9D-specific acceptance.
6. After any fix/reformat/change, repeat relevant validations and recheck the NEW final SHA.
7. Do not state VERIFIED while final-head gates are running/canceled/timed out.

## 112. PR review content

Include: overview and exact scope boundaries; target/base SHA; migrations; API surface; protection flags and why production stays blocked; approval/activation state machine; 9B/9C reuse; source-role gating; resource budgets; auth failure and replay tests; numerical equivalence; fixture response examples; additive schema; metrics/benchmark; full regression receipts; security status; limitations and exact-head CI run links.

## 113. Definition of Done — serving security

- [ ] All prediction routes disabled by default
- [ ] Production service exposure explicitly blocked
- [ ] Server-side operator authentication, no query/body credentials
- [ ] Auth checked before DB/artifact access
- [ ] Bounded body/rate/concurrency/timeouts and no event-loop CPU starvation
- [ ] No user-account/multi-tenant claim
- [ ] No unapproved or auto-selected model/detector serving
- [ ] Explicit version-scoped, source-scoped operator approval and revocation
- [ ] Artifact, schema, dependency checksum and path security preserved
- [ ] Safe error responses and sanitized metrics/traces/logging

## 114. Definition of Done — inference correctness

- [ ] All 3 Phase 9B supervised tasks supported with frozen thresholds
- [ ] All 4 Phase 9C anomaly families supported with frozen detector versions
- [ ] Different horizons NEXT_PULL and AFTER_PULL_OFFLINE clearly separated
- [ ] Source role and vehicle/configuration/modification isolation
- [ ] Real Phase 9A FeatureSets only; no arbitrary client-supplied values
- [ ] Temporal and input quality/availability proof
- [ ] No future label/late sample leakage
- [ ] Exact offline equivalence within declared tolerances
- [ ] No training/fit/threshold mutation on serving paths
- [ ] Explicit reason-coded abstention, no fabricated scores
- [ ] Idempotent replay and durable immutable minimal receipts

## 115. Definition of Done — engineering

- [ ] Current-head additive migration and downgrade/re-upgrade receipt
- [ ] Focused unit suite and real disposable DB integration
- [ ] Independent actual HTTP acceptance evaluator
- [ ] Concurrency/revocation/cancellation tests
- [ ] Auth/security adversaries, tamper rejection, cross-context sentinels
- [ ] API contracts and runbook/ADRs/traceability/architecture
- [ ] Benchmark and bounded metrics/traces
- [ ] Phase 9A/9B/9C full regression, plus previous deterministic gates
- [ ] Canonical Docker/full-stack + CodeQL/security/dependency checks on final SHA
- [ ] Branch pushed, PR OPEN and UNMERGED, exact-head receipts
- [ ] No 9E PredictionEvidence, 9F agents, 9G calibration or 9H UI

## 116. Final report contract

Return real executed evidence for:
1. branch, baseline, final SHA and PR URL/state;
2. migration ID and table/state machine design;
3. exact operator enablement/auth/access and production guard;
4. approval/activate/revoke/rollback scenarios and audit event counts;
5. 9B task results, scores, threshold decisions and direct offline equality;
6. 9C family results, anomaly/abstention counts and direct 9C equality;
7. source-role and configuration/cutoff/quality evidence;
8. 9A FeatureSet version/provenance and model/artifact checks;
9. idempotency, concurrent replay, receipt immutability and safe failure recovery;
10. actual HTTP endpoints and status/security matrix;
11. benchmark/CPU concurrency/memory/latency observations;
12. metrics/traces with sensitive data exclusion;
13. unit/integration/evaluator/9A/9B/9C/older regressions;
14. canonical final-HEAD GitHub checks with URLs;
15. real-data compatibility caveat and limits on synthetic model validity;
16. confirmation that 9E–9H, production cloud deployment and ECU control are absent.

END EXACTLY with one of these two lines, only as supported by actual evidence:

PHASE 9D — PREDICTION SERVICE: VERIFIED

or

PHASE 9D — PREDICTION SERVICE: NOT VERIFIED

If fixable failures remain, continue working before final reporting. If genuine external blockers remain, specify the blocked checks and no unsupported PASS claim. NEVER merge the pull request.
