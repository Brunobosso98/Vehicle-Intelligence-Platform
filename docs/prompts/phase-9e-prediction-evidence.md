# Phase 9E — PredictionEvidence: Traceable Predictive Evidence Foundation

**Repository:** Brunobosso98/Vehicle-Intelligence-Platform  
**Existing branch:** codex/phase-9e-prediction-evidence  
**Exact branch-creation baseline:** 5998a378b0fee1fbe6d0156b7cb55ec7fcb40f6b (Phase 9D PR #44 merged, 2026-10-21)  
**Prior phases:** 9A canonical Feature Engineering; 9B supervised next-pull engineering models; 9C retrospective unsupervised anomaly detection; 9D authenticated controlled prediction serving.  
**This phase:** 9E PredictionEvidence, a distinct deterministic, auditable and bounded evidence contract.  
**Future phases:** 9F Agent Integration; 9G Evaluation/Calibration; 9H Predictive UI; 10 MLOps; 11 Agent Evals; 12 Production Cloud Infrastructure.

**Mission:** For every eligible immutable 9D prediction receipt, materialize and independently verify a versioned **PredictionEvidence** bundle that says exactly (a) what result was recorded, (b) what source facts and model/reference version it came from, (c) which measurement or statistical associations support the _description_ of the result, (d) what gaps/conflicts/limits apply, and (e) whether its chain of custody remains verifiable. This is an evidence integrity/projection layer, not new prediction, probabilistic calibration, diagnosis, repair advice, agent wiring, RAG search, or predictive UI.

The entire document is an authoritative execution contract. ALL numbered requirements are normative. Interpret illustrative filenames and endpoint spellings by existing repository conventions; never claim a function exists without inspecting the code. If a requirement is impossible because source data is absent, produce an explicit typed evidence gap and bounded failure/abstention, not invented evidence or changed earlier semantics.

## 1. Mandatory startup and git discipline

Fetch origin, inspect remotes/status/working tree/HEAD/main and scoped AGENTS.md instructions. Switch to the EXISTING branch \`codex/phase-9e-prediction-evidence\`; never create a second 9E branch. Verify merged main SHA \`5998a378b0fee1fbe6d0156b7cb55ec7fcb40f6b\` is an ancestor and Phase 9D PR #44 is merged. Work only on the 9E branch; no force push, main write, history rewrite or auto-merge.

## 2. Required deep repository reading

Read this entire specification. Inspect \`docs/roadmap/README.md\`; Phase 9A/9B/9C/9D prompts, architecture, ADRs, model cards, validation and runbooks; \`apps/api/src/vehicle_platform/{features,ml,anomalies,predictions,agents,knowledge}\`; migrations 0013–0016; API auth/budgets/error schemas; tests, Makefile, workflows, observability and security. Map exact source fields before building any evidence claims.

## 3. Actual prior-phase record owners

Phase 9A immutable \`feature_sets\` and their version/quality/provenance; Phase 9B \`ml_model_versions\`, label/model definitions, datasets, registered trusted artifacts; Phase 9C \`anomaly_detector_versions\`, reference datasets, \`anomaly_detection_runs\` and \`anomaly_findings\`; Phase 9D \`prediction_serving_bindings\`, append-only \`prediction_serving_events\`, \`prediction_receipts\`. 9E MUST reuse these immutable authoritative records, not create duplicate prediction algorithms.

## 4. Recognize real 9D schema and boundaries

The 9D \`PredictionResponse\` schema is \`phase9d-prediction-response-v1\`, with result types \`next_pull\` and \`anomaly\`, source roles, cutoff, status, score/threshold/decision, quality and minimal lineage. 9D HTTP namespace is \`/api/v1/prediction-service\`, disabled by default and restricted to authenticated dev/test operator, private/loopback source. It has no platform-wide account authorization. Preserve ALL these fences.

## 5. Distinct result horizons

\`NEXT_PULL\` from 9B refers to a future _observable outcome rule_ compared with the known input pull; future target telemetry, actual target outcomes, target labels and leakage are forbidden as "evidence" for the prediction at original cutoff. \`AFTER_PULL_OFFLINE\` from 9C is a retrospective observed statistical deviation for a completed pull; it is not a forecast. Evidence schemas and renderer must retain this distinction throughout.

## 6. Formal Definition of Done

An authenticated controlled operator can take a specific persisted 9D receipt, materialize a complete immutable evidence bundle with typed source references, feature/provenance/cutoff checks, decision and quality bindings, bounded associations and explicit limitations, independently verify it from frozen records, replay idempotently, and retrieve a safe redacted projection. Missing, mismatched, revoked, low-quality or insufficient input creates honest status/gaps, not fictitious facts.

## 7. Scope freeze

9E implements evidence contracts/projection/verifier, immutable persistence, bounded protected materialization/read/verification interfaces, tests/evaluation, observability, performance and documentation. It DOES NOT implement Phase 9F MCP/agent/specialist tool registration, LangGraph reasoning, 9G calibration/drift, 9H product UI, online external serving or 10 automated retraining. No new Phase 9B/9C model training or hidden prediction calls are allowed.

## 8. Non-diagnostic scientific contract

Do not translate model scores into mechanical failure probabilities, "confidence 92%", recommended repair, urgent safety alert, remaining useful life, turbo diagnosis or OEM safety thresholds. Treat 9B scores as uncalibrated engineering classification scores and 9C scores as relative statistical deviation. No inference about actual component damage from an unverified statistical signal.

## 9. Core component architecture

Implement a narrowly owned \`PredictionEvidenceService\`, immutable domain contracts, \`PredictionEvidenceRepository\`, deterministic projection builder and independent verifier. Prefer a sibling \`vehicle_platform.prediction_evidence\` package over cross-layer cycles. Reuse 9D response/provenance conventions; 9D continues to own serving, while 9E owns **derived evidence** and verification, never scores.

## 10. Canonical evidence graph

The bundle must contain a rooted finite graph with typed source nodes and explicit edges: receipt -> approved binding/event -> model or detector version -> frozen feature snapshot -> applicable source context -> emitted fact/association/decision. For 9C link to anomaly run/finding and historical reference dataset. Record typed edges; never fabricate an edge just to produce a complete graph.

## 11. Versioned root contract

Define \`PredictionEvidence\` / \`PredictionEvidenceBundle\` with schema version e.g. \`phase9e-prediction-evidence-v1\`, bundle ID, original receipt ID, result kind/horizon, source role, task/family, cutoff, evidence status, integrity state, original score/threshold/decision or explicit abstention, coverage, source summary, evidence nodes/edges/facts/gaps, interpretation, limitations, provenance manifest checksum, derived bundle checksum and generated timestamp.

## 12. Deterministic canonicalization

Use a named versioned canonical JSON/hash helper: exact stable key ordering, deterministic Decimal/float representation, UTC aware timestamps, IEEE finite-value validation, enum text and sorted source edges where ordering has no semantic meaning. State which fields are excluded from logical identity (e.g. nondeterministic creation timestamp). Distinguish source checksum, immutable content checksum and optional purely local signature.

## 13. Hashes are not signatures

SHA-256 digests detect mismatches with trusted reference state but DO NOT establish external authenticity, tamper resistance against fully privileged database attackers or trusted hardware provenance. Never market them as digital signatures. Optional keyed sealing would require a separate operational secret and key lifecycle; do not introduce it without real verification and scoped design.

## 14. Typed EvidenceNode contract

Use an allowlist of node types such as PREDICTION_RECEIPT, SERVING_BINDING, APPROVAL_EVENT, FEATURE_SET, FEATURE_VERSION, MODEL_VERSION, DETECTOR_VERSION, ANOMALY_FINDING, ANOMALY_RUN, REFERENCE_DATASET, FEATURE_OBSERVATION and QUALITY_CONTEXT. Each node declares source table/entity identity internally, source snapshot checksum, time-validity scope, quality/trust role and visible projection class. No arbitrary SQL table paths or user-defined node types.

## 15. Typed EvidenceEdge contract

Allowlist directional edge semantics such as DERIVED_FROM, SCORED_WITH, SELECTED_BY, OBSERVED_IN, SUPPORTED_BY, COMPARED_AGAINST, MEASURED_AT and LIMITED_BY. Ensure every edge references existing nodes in the same bundle, rooted graph is connected for usable evidence, and no cycles imply causal direction or independent corroboration.

## 16. Typed EvidenceFact contract

Fact includes bounded stable key/path, type, observed value (if permitted), unit, source node, cutoff eligibility, quality status, source window and descriptive meaning. Keep measured quantities separate from algorithm output values. Retain null with reason rather than replace with zero. Do not allow untyped freeform LLM-authored facts.

## 17. Fact classification and authority

Categorize SOURCE_MEASUREMENT, COMPUTED_FEATURE, MODEL_OUTPUT, STATISTICAL_REFERENCE, CONTEXT_DESCRIPTOR, QUALITY_INDICATOR and INTERPRETATION_LIMIT. The "model says X" claim can cite model output; "IAT was 54 C" needs actual eligible IAT/derived feature source; "turbo is broken" has no permitted fact class and must be rejected.

## 18. ClaimBinding structure

Define a small application-authored claim set with exact fact IDs, expected values and units, cutoff, scope, permitted claim category and validation outcome. Any textual summary must be rendered from validated structured facts and fixed templates. Never accept arbitrary model-generated diagnoses or provider narratives as canonical PredictionEvidence.

## 19. Evidence gap taxonomy

Typed bounded gaps: NO_FEATURE_SET, INPUT_ABSTAINED, SIGNAL_UNAVAILABLE, FEATURE_NOT_YET_OBSERVED, LOW_QUALITY, REFERENCE_INSUFFICIENT, CONTEXT_INCOMPATIBLE, UNKNOWN_CONFIG, MODEL_ARTIFACT_UNAVAILABLE, PROVENANCE_MISMATCH, EVIDENCE_SOURCE_MISSING, SOURCE_SCHEMA_MISMATCH, CUTOFF_MISMATCH, UNSUPPORTED_SOURCE, AMBIGUOUS_ASSOCIATION, INCOMPLETE_PROJECTION and UNVERIFIED_SOURCE. Stable precedence and permitted coexisting gaps required.

## 20. Integrity and completeness are orthogonal

Store separate integrity state (e.g. VERIFIED, FAILED_SOURCE_MISMATCH, NOT_VERIFIABLE, UNSUPPORTED_SCHEMA), evidence completeness (COMPLETE, PARTIAL, ABSTAINED), and original serving prediction status. A 9D ABSTAINED result can yield a fully verified **abstention explanation**; do not call that a valid predictive score. Missing sources can make an integrity check not verifiable without falsely declaring it tampered.

## 21. No quality upgrades

A PARTIAL, low-coverage or abstained source cannot become HIGH_QUALITY just because its evidence bundle is complete as a record. Preserve original Phase 9A/9D quality and attach per-evidence quality. A verified chain proves traceability under available trusted records; it does not prove physical sensor accuracy or calibrated model reliability.

## 22. Source facts vs model claims

Never store the predicted next-pull target as an observed fact if it has not occurred. Separate \`predicted_outcome_definition\` from \`observed_input_facts\`. If the actual target is recorded after prediction cutoff, keep it OUT of the original 9E evidence; future model evaluation (9G) may compare predictions and outcomes in a separately versioned evaluation record.

## 23. 9C statistical attribution limits

Use already recorded 9C finding's observed-vs-reference deviations, normalized distances, feature directions and coverage only if present and verifiable. A top associated feature is DESCRIPTIVE, not a causal decomposition of Isolation Forest or a confirmed defective part. Don't invent SHAP or external model feature contributions when not computed.

## 24. 9B classifier explanation limits

Phase 9B feature importance/coefficients are model-level associations, not validated per-prediction Shapley values or causal explanations. 9E can record exact versioned input features, model-wide association metadata, score/threshold and source context; must not claim an exact per-instance attribution unless a real bounded, validated algorithm is implemented with its own receipts.

## 25. Source provenance hierarchy

Prefer committed immutable IDs and hashes: 9D receipt fingerprint/binding_event_id; exact 9A FeatureSet/version/source/provenance; exact 9B model version/task/threshold/artifact; exact 9C detector/reference/checksum/anomaly finding. No "latest version", filename similarity, human note, nickname or source free-text string can substitute for authoritative lineage.

## 26. Reference graph source roles

Synthetic, imported, imported_fixture and real_vehicle must remain exact and visible as categorical provenance. Synthetic-only model evidence CANNOT substantiate generalization to real vehicles. Mixed source roles are rejected by 9D, and 9E must not reintroduce them through cross-source evidence joins.

## 27. Vehicle and context fence

Verify all source feature sets, pulls, sessions, configurations, active modifications and reference cohorts (where applicable) resolve to the same source vehicle/context as the original 9D receipt. Referenced records may be from prior compatible pulls only when 9C's frozen reference manifest explicitly lists them, and only if time-eligible. No cross-vehicle copy-and-paste facts.

## 28. Effective configuration as-of

Historical effective configuration/modification state is determined as-of the original FeatureSet cutoff, respecting Phase 9A/9D recorded-at rules. Later-dated modifications, retroactively entered history and edited names cannot rewrite the old evidence. If authoritative immutable snapshots cannot reconstruct an old context, return NOT_VERIFIABLE/PARTIAL instead of current-state facts.

## 29. Observation time vs ingestion time

Keep source observed_at, available_at, source_window_end and ingestion/creation times distinct. A sample physically measured earlier but recorded after the original cutoff cannot prove a historical model knew it. Test late-inserted samples and modification context that would otherwise make a result look more convincing.

## 30. Cutoff enforcement

Each fact node must be eligible at the corresponding historical 9D \`effective_cutoff\` (or earlier within 9C reference cutoff). Use timezone-aware UTC consistent normalization; reject naive timestamps. A derived evidence creation timestamp is later than cutoff and does NOT imply observation data became available earlier.

## 31. Request cutoff is frozen

9D stored \`requested_cutoff\` and \`effective_cutoff\`. Evidence generation accepts only receipt ID and projection version, not a fresh mutable caller-defined cutoff. Different cutoffs correspond to distinct 9D prediction receipts. No evidence endpoint can rescore "as of now" implicitly.

## 32. Immutable 9D decision preservation

Preserve original receipt response byte/semantic fingerprint, score, status, threshold, decision, task/family and horizon exactly; round-trip through typed 9D schema. Never flip ANOMALOUS to INLIER, change score to fit a narrative, or change an ABSTAINED record to READY_SCORE in the evidence projection.

## 33. Verification without prediction execution

The 9E verifier checks source references, stored values, version compatibility and decision/threshold consistency; it MUST NOT retrain or call the online 9D inference endpoint to manufacture a fresh receipt. Optional offline equivalence checks are an _independent validation tool_, not a required read path that re-executes a revoked detector.

## 34. Source snapshot consistency

For complete evidence, verify the 9D \`prediction_receipts\` record against its \`response_body\`, binding and activation event, stored FeatureSet identity/source hash/provenance checksum and immutable corresponding model/detector versions. Any contradiction yields FAILED_SOURCE_MISMATCH (or clearly named equivalent), never a silent substitute.

## 35. Event history semantics

A serving activation event at admission is historical proof of approval snapshot, not proof the binding is **currently** active. Current REVOKED/SUPERSEDED must not retroactively falsify historically valid outputs. Distinguish historical permission at scoring time from current ability to start a new inference. Do not reactivate a model during evidence retrieval.

## 36. Revoked binding access

Historical evidence can be retrievable only inside existing authenticated controlled operator boundary with explicit audited policy. Revocation stops **new serving/replay scoring**, not necessarily historical forensic reading. If repository's existing 9D receipt route allows retrieval after revoke, align and document that behavior rather than silently changing its security semantics.

## 37. Model artifact no longer available

An immutable receipt might exist after an artifact has been garbage-collected or corrupted. Distinguish VERIFIED_SNAPSHOT_WITH_ARTIFACT_UNAVAILABLE from full verification of model artifact, or return PARTIAL/NOT_VERIFIABLE as appropriate. Do not deserialize arbitrary bytes from a client or claim full end-to-end proof if the artifact cannot be checked.

## 38. Identity and reference manifest

A bundle's stable logical fingerprint includes original receipt ID/fingerprint, evidence schema/projection version, referenced immutable source checksums, source role, historical cutoff and canonical evidence content. Derived later requests with the SAME frozen evidence should be idempotent. Truly changed data/version must create a new explicitly versioned bundle or a failed verification receipt, not overwrite old.

## 39. Verification at creation vs later

At build time record what was verified, exact source checksums/versions and verification policy version. Later read-time verification SHOULD recompute and compare bounded source evidence, with separate ephemerally computed verification status or append-only verification audit. Never mutate historic immutable bundle claiming its previous "VERIFIED" status now means current source availability.

## 40. Bounded chain of custody

Keep durable source-ID mapping, source-schema checksum, content hash, created_at, deterministic ordered graph and validation receipts. Graph nodes/edges must not contain full raw telemetry matrices, VIN, GPS, secrets, third-party documents, arbitrary notes or vehicle identifiers as high-cardinality public details.

## 41. Evidence materialization lifecycle

Choose explicit \`POST /api/v1/prediction-service/runs/{receipt_id}/evidence\` to materialize one bundle, and separate read-only \`GET /api/v1/prediction-service/evidence/{id}\` plus \`GET /api/v1/prediction-service/runs/{receipt_id}/evidence\` if justified. Keep normal GET operations side-effect-free; do not transparently persist a new bundle on an HTTP GET.

## 42. Reuse 9D access controls exactly

Every evidence route MUST remain under \`/api/v1/prediction-service\` and inherit existing disable-by-default, production denial, bearer operator auth, peer allowlist, body/rate/inflight/timeout controls. Extend 9D route parser as needed without weakening earlier protections. Under no circumstances expose an unauthenticated \`/api/v1/evidence\` endpoint.

## 43. Dedicated evidence request resource limits

Bound source records, graph nodes/edges/facts, JSON bytes, per-claim depth, maximum source time span, concurrent builds, DB query time, record output bytes, and verification work. Existing prediction body max 4KiB and 8s handler timeout are real defaults; design feasible bounded work or separately stricter controls without bypassing the existing middleware.

## 44. Controlled internal API boundary

9E endpoint is operator-only engineering capability, not public account-linked fleet evidence. Do NOT treat valid operator token as vehicle owner consent. No API exposure to internet, no cross-tenant access, no cloud deployment in 9E, and no user-scoped auth claim. Production enablement remains blocked; test production-disabled behavior for new routes.

## 45. Output projection tiers

Have a rich **internal evidence manifest** with IDs/hashes and bounded eligible facts, and a privacy-safe **operator-facing response projection** with opaque evidence ID, allowable results/measurements, high-level references, status and limits. Only the internal manifest may contain source hashes or full internal lineage, if existing policy permits. No full model artifact, private filename or raw reference matrix in HTTP.

## 46. Safe schema contract and OpenAPI

Use strict Pydantic models with \`extra=forbid\`, versioned discriminated sections for supervised vs anomaly, bounded literals/reason codes, finite numerics and max lengths. Generate OpenAPI/TypeScript contracts through project tooling. Keep existing 9D response shape backward compatible and do not make legacy fields required retrospectively.

## 47. Evidence node count and bounds

Choose explicit defaults and hard caps e.g. 32 source nodes, 64 edges, 48 facts, 16 gaps and 8 claim bindings per receipt, or measured comparable bounds. Overflow must yield structured TRUNCATED/PARTIAL state with evidence of omitted elements; **never** continue to claim complete chain from a silently truncated graph.

## 48. Projection content sizing

Set database JSONB max bytes and HTTP response hard cap. Validate UTF-8, finite floats, controlled precision, arrays/dicts and recursion limits. Truncate safely at record boundaries with omitted_count; do not cut a claim mid-number or drop its quality flag. Avoid unwitting secrets in string-valued metadata.

## 49. Database migration after 0016

Inspect Alembic HEAD first, then add strictly additive 9E revision after \`0016_prediction_service\` (likely 0017, but verify actual head). Create owned tables for immutable bundles and source/fact materialization, plus optional append-only verification audit. Maintain foreign keys to original receipt and existing immutable source rows where possible. No old migration edits, destructive schema changes or legacy data rewrites.

## 50. Persistence option trade-offs

Select and document whether bounded JSONB manifest plus normalized source references or normalized nodes/edges/facts is appropriate. Insist on DB-enforced immutable receipts and checksums either way. Do not create a large graph database dependency solely for 9E. Traceability/queries must be feasible with PostgreSQL/TimescaleDB and existing SQLAlchemy stack.

## 51. No duplicate 9D receipts

9E bundle references original \`prediction_receipts.id\`; it does not modify 9D \`response_body\`, generate new predictions, reissue idempotency tokens or create a fake serving binding. 9E may append a distinct evidence derivation only. Test 9A, 9B, 9C and 9D pre/post database table digests where appropriate.

## 52. Immutability enforcement

Completed evidence manifest, original fact values, evidence root identity, node/edge links and source checksum pointers must be UPDATE/DELETE protected at database level. A repeated generation with identical source+version returns same bundle ID; a conflicting hash or manually modified source is rejected, not overwritten.

## 53. Append-only verification audit

If materialization or later operator verification records verification attempts, store a bounded append-only audit with timestamp, outcome, policy/schema version and aggregate reason codes, but no raw sensor values/secret. Make the audit policy explicit and avoid an unbounded row-per-view storm. Reading evidence should not silently create a verification audit unless contract says it does.

## 54. Idempotency and concurrent builds

Two identical authenticated POST materializations racing must return the SAME stored evidence ID/fingerprint and no duplicated graph rows. Use unique DB constraints, deterministic manifest and safe insert conflict handling. Avoid long-lived DB transactions during validation or JSON construction; staged source snapshots must be transactionally consistent or stale-read conflicts must be detectable.

## 55. Snapshot isolation race

Assemble from a consistent read view or individually verified immutable source checksums; recheck before commit if needed. Revocations/new versions and later FeatureSets cannot mutate the historical receipt lineage. If a source changes while generating, reject atomically with verifiable reason instead of persisting a mixed-time graph.

## 56. Missing original FeatureSet

A 9D receipt may be a valid \`ABSTAINED_INSUFFICIENT_SIGNAL\` with NULL \`feature_set_id\`. Generate **abstention evidence** rooted in the actual receipt, binding and missing-feature reason. Do not require a fabricated FeatureSet to make an evidence bundle complete as an explanation of abstention; mark measurement completeness accordingly.

## 57. Low-quality evidence

A low-quality 9D receipt must preserve recorded low-quality reason and coverage, not cherry-pick one clean measurement to declare a strong result. If data has quality warnings, link the warnings to relevant observations; missing coverage must be visible in the structured claim limitations.

## 58. Strongest permitted 9B explanation

For supervised receipt, include the outcome definition label and observable rule, original model family/version/threshold, ordered actual eligible input features (bounded selected subset), per-feature quality/unit/timestamps, validation class/source provenance and explicit no-calibration disclaimer. Any model-wide importance/association must be labeled MODEL_LEVEL_ASSOCIATION, not current pull cause.

## 59. Supervised label provenance

Link the source **definition/version/checksum** for NEXT_PULL outcome rules (3K IAT change, 8% interval change or 88% pressure ratio as existing 9B definitions specify). The label definition explains WHAT the model was trained to classify, not evidence that the future target has occurred. Do not include target labels, target pull ID or future label realization in current prediction evidence.

## 60. Feature selection and leakage safeguards

Allow only ordered versioned features in the original 9B ModelSpec/registry schema. Exclude identity surrogates, target-derived feature keys, post-cutoff values and optional fields not in the frozen model. No special "diagnosis context" from future pull added under a freeform note.

## 61. 9B score verification

Verify stored score within strict documented tolerance against stored 9D response and numeric bounds [0,1]; compare decision with recorded frozen threshold and task. This is **receipt internal consistency**, not real-world predictive validity or retraining. If artifact and verified snapshot are available, optional independent offline equality can be part of deterministic acceptance, not a mandatory runtime refit.

## 62. Complete 9C association chain

For anomaly receipt, link original 9C \`anomaly_finding_id\`, \`anomaly_run_id\`, detector version, accepted threshold, reference dataset checksum, source FeatureSet and bounded top observed deviations **actually persisted** by 9C. Verify finding's source hashes/status/score against 9D receipt. Do not rerun the reference cohort with current latest history.

## 63. Frozen 9C reference context

9C reference is exactly same vehicle/config/modifications/source, minimum historical support and strict cutoff as recorded. Evidence should show a bounded reference summary (eligible count, session count, time span, statistical center when actually present) and version/checksum. Do not fetch later cohort data to improve baseline or imply all same-engine vehicles share a "normal" reference.

## 64. Anomaly method semantics

Robust MAD and IsolationForest scores have different raw numeric scales and threshold origins. Do not rank anomaly severity across detectors simply by score. Higher-is-more-unusual within the detector contract; "different from frozen cohort" is permitted, "probability of turbo failure" is not. For IsolationForest descriptive deviations are not a decomposition of tree votes.

## 65. Outcome and source disagreement

Support explicit conflicts: a 9D receipt claims READY_SCORE but DB score absent; a 9C finding says INLIER while 9D decision says ANOMALOUS; horizon/task mismatch; version checksum mismatch; quality says unavailable while fact claims measured. Verifier returns a typed integrity failure; no silent majority vote or suppression of the conflicting node.

## 66. Multiple evidence sources are not independent votes

A Phase 3 event, Phase 9B prediction, 9C anomaly and 9A features may derive from the SAME telemetry. Even if later linked contextually, never count them as four independent confirmations of a mechanical issue. Cross-source corroboration requires independence proof, beyond scope. 9E should not automatically fuse them into a joint confidence percentage.

## 67. Phase 3 and Phase 5 boundaries

Phase 3 event rules and Phase 5 deterministic analytics are distinct systems. 9E may reference them ONLY if a real explicit source relation is present and verified as-of the cutoff; not automatically reconstruct, merge or mutate them. If out of scope for initial evidence projection, document that, and avoid inventing event/analytics support.

## 68. Phase 8 RAG and technical sources

Technical manuals and retrieval excerpts are documentary context, not measured telemetry. 9E MUST NOT consult RAG to fill missing evidence or claim manufacturer fault cause. Phase 8 KnowledgeEvidence is separate with source trust/applicability; future 9F integration may combine bundles and citations under guarded agent claims, but 9E does not fetch manuals or model generated opinions.

## 69. Agent compatibility without agent wiring

Design stable evidence node/claim IDs and typed fact paths usable by future Phase 9F grounded agents. However DO NOT register an MCP tool, alter LangGraph supervisor, expand agent public claims, add specialist prediction decisions, modify existing agent prompts or pass private evidence in model context during 9E. Tests must assert there is no new agent execution path.

## 70. Policy-governed allowed statements

Implement typed deterministic statements: "At cutoff [time], registered model [version] produced score [x] relative to threshold [t] for named next-pull outcome"; "The observed post-pull feature [name, unit] deviated relative to this versioned cohort"; "Insufficient signal/coverage prevented scoring." Disallow diagnostic/repair/certainty language in renderer templates.

## 71. Non-causal explanation vocabulary

Approved words: "observed", "associated", "statistically unusual", "compared with the selected reference", "recorded by the model", "not evaluable". Disallow "caused", "proved defect", "failing turbine", "fault probability", "safe to drive", "must replace", "urgent maintenance". Test deterministic serializer and renderers across languages if any localization exists.

## 72. No invented physical units

Use exact 9A canonical unit key, preserving Kelvin/Pascal if canonical measurements are K/Pa; optional display conversion may be deterministic, named, unit-tested and versioned. Never display a temperature 54C as a measured record unless verified underlying value was measured/derived and converted. Do not silently convert boost absolute versus relative pressure.

## 73. Observed vs reference measurements

For comparison present reference count, frozen distribution statistic and measured observation with units from compatible feature definition. Never invent reference mean if only median exists; never present a single anonymous "healthy" vehicle benchmark as OEM target. The user's BMW/N55 is an illustrative consumer, not fixture identity.

## 74. Source quality context

Preserve pull completeness, invalid/duplicate timestamp count, feature quality, missing reasons, source-role and capability matrix if actually recorded. Do not interpret source capability as physical sensor sampling. If an OBD source does not provide fuel pressure, the bundle explicitly says so rather than fabricating a pressure from RPM/boost.

## 75. Absence of reference support

If anomaly detector version was rejected or 9D correctly abstained, evidence must not synthesize reference statistics. Show the exact persisted status/reason and, where present, predeclared minimum reference requirements, source role and cohort policy; avoid leaking unrelated vehicles in cohort summaries.

## 76. Contradiction handling

Support deterministic three-way classification: CONSISTENT, CONTRADICTORY, NOT_CHECKABLE. Contradiction is not resolved through a narrative LLM. Source of truth is immutable versioned record; if 9D receipt and persisted 9C finding disagree, mark evidence FAILED_SOURCE_MISMATCH and stop rendering affirmative model claims while retaining a safe audit explanation.

## 77. Explicit "unknown" dimensions

Unknown gear, altitude, weather, fuel grade, ECU tune vendor/map, actual torque, mechanical condition or error code must remain unknown when not explicitly measured. These unknown contextual variables can limit interpretation; they may not be filled from the vehicle model or inferred from "Stage 2" notes.

## 78. Selection of top associations

Deterministically sort by recorded absolute normalized deviation (when defined), stable feature key and direction, with bounded top N. Recompute only what source data and versioned statistic actually permit, and mark derivation. Never choose associations simply because their names suggest an engine component problem.

## 79. Confidence terminology

Distinguish source provenance verification, data-quality coverage, model validation class, threshold applicability and real-world calibration. Do not collapse them into a fake single "confidence 97%". 9G owns scientific calibration/accuracy/drift research. If a field is named confidence, rename it to evidence_integrity/coverage unless strictly defined.

## 80. Evidence completeness grading

Complete graph requires actual receipt, binding/event, exact input FeatureSet when one existed, model/detector version and relevant finding/reference for anomaly, all checksum matches and no truncation in needed source facts. Partial graph may still be useful but must be labeled PARTIAL with gaps. Abstention explanation may be verifiable without a FeatureSet but cannot pretend measurement evidence exists.

## 81. Re-verification CLI

Provide operator-only local \`vehicle-prediction-evidence verify --evidence-id ...\` or equivalent, with strict time/row limits, optional JSON sanitized output, nonzero exit on actual mismatch, and dry-run inspect if project patterns permit. No destructive repair, data mutation or automatic recalibration.

## 82. Materialization CLI

Provide \`vehicle-prediction-evidence build --receipt-id ... --schema-version ...\` or equivalent with explicit controlled environment, bounded local identity, dry-run and summary of created/reused evidence. Never accept direct user model paths or feature vectors. Do not require API credentials for trusted server-local CLI if project operator policy already provides equivalent control.

## 83. Read-only inspection CLI

Provide bounded \`inspect\`/ \`list\` scoped to an explicit receipt/evidence identifier where appropriate. Do not create an unfiltered vehicle evidence dump. Print minimal safe IDs, statuses, counts, checksum prefix, coverage and gaps, never raw VIN, entire source graph or high-cardinality secrets.

## 84. HTTP materialize request validation

Validate receipt UUID, original source role, fixed v1 schema, optional idempotency key and scoped operator policy. Do not accept client-authored evidence nodes, custom fact paths, SQL, JavaScript expressions, freeform claims, proposed scores or "trust me" hashes. The authoritative source is existing immutable DB state.

## 85. HTTP GET evidence behavior

Authenticated GET returns safe projection with explicit integrity/completeness label, bounded node and claim summaries, source limitations and reproducibility fingerprint; no side effects. Unknown or inaccessible ID must not enumerate vehicles or artifacts. Old bundle retrieved after binding revoke is a historical read, not reactivation of scoring.

## 86. Disable-by-default and production fence tests

With \`PREDICTION_SERVICE_ENABLED=false\`, all new 9E HTTP paths must reject before database reads. With \`ENVIRONMENT=production\`, enablement must fail closed just like 9D. No 9E alternate router bypass. Header credentials are mandatory; query/cookie/body tokens rejected. Trusted peer validation also mandatory.

## 87. Budget/admission tests

Add adversaries for oversize request body, request rate overflow, concurrent materialization, slow client, early disconnect, 8s handler timeout, CPU-intensive optional verify, and DB outage. Check no leaked semaphores/threads/DB sessions and no partially inserted bundles. Scope graph serialization memory remains bounded.

## 88. IDOR and disclosure tests

Wrong-vehicle receipt ID, wrong source role, another fixture vehicle, guessed evidence UUID and attempts to retrieve evidence from another local controlled source must follow existing 9D operator access scope. Do not invent per-user tenancy; enforce all available controlled source-context checks. Never expose a fleet-wide unscoped evidence listing.

## 89. Artifact tamper adversaries

Mutate or remove registered model/detector artifact, substitute symlink/path, change SHA, task or expected sklearn/library version. No untrusted joblib deserialization. If source-verified evidence can be built from frozen record without artifact, mark artifact check NOT_VERIFIABLE; do not claim end-to-end VERIFIED. Distinguish verifying a receipt from executing model inference.

## 90. Source tamper adversaries

Introduce conflicting source_hash, changed feature value without corresponding checksum, malformed reference manifest, missing evidence foreign key, altered recorded threshold, wrong label version, wrong 9C finding status, arbitrary extra feature path and duplicated edge. All must be detected or explicitly listed as uncheckable, never yield verified affirmative evidence.

## 91. Model-result contradiction tests

For 9B: deliberately mismatch score vs threshold/decision, task horizon and feature schema. For 9C: mismatched finding status, detector threshold, reference checksum and original FeatureSet provenance. Expect failed/unsupported evidence with no "fault explanation". Test identical backend-stored score with different string formatting to ensure numeric equivalence rules are well defined.

## 92. Replay and concurrency test suite

Materialize same receipt twice, concurrently 10 times and after service restart; require stable evidence identity and digest, no duplicate records and same safe projection. Reorder DB rows, JSON keys and fact extraction order without changing semantic canonical hash. Changed projection version must produce a distinct versioned identity, not mutate old.

## 93. Temporal leakage test suite

Add target pull measurement after original NEXT_PULL cutoff, late-ingested old sample, newly created modification with earlier effective date, post-cutoff 9C reference rows, current-state metadata changes and ambiguous timezone. Verify evidence source graph remains as-of original frozen cutoff. No future observation fact may enter original bundle.

## 94. Correlated-source caution cases

Build two events/features from the same underlying telemetry and assert evidence composer doesn't count them as independent support. Add 9B score + 9C finding for same pull as distinct receipts; don't merge into independent diagnostic votes. Make this behavior machine-asserted rather than documentation-only.

## 95. Quality/missingness test suite

Missing fuel pressure, insufficient thermal coverage, invalid finite-value sentinel, declared-but-unobserved capability, duplicate samples, mixed roles and insufficient reference support must yield correct bounded gap/status, not a non-null fabricated physical measurement. No score from an original abstained receipt, and no positive claim from corrupted source.

## 96. Positive reference chain test suite

Prove 9C source finding/reference cohort is same vehicle/effective configuration/modification/source, predates anchor cutoff, has frozen counts/units and cannot be reinterpreted with later history. Exercise Robust MAD and Isolation Forest if accepted fixtures exist. For 9B prove exact model version/label definition/feature order without accessing next-pull actual outcome.

## 97. Three mandatory supervised fixture cases

Build evidence for each of the existing 9B tasks: thermal degradation, performance degradation, fuel deviation. Compare materialized outcome wording, original 9D score/threshold/decision, eligible input FeatureSet, task/version, quality and source role. Include at least one abstention and one missing fuel capability. No target label enters proof.

## 98. Four mandatory anomaly fixture cases

Build evidence for 9C thermal, boost_air, performance and fuel families. At least one 9C thermal evidence case may legitimately be ABSTAINED_INSUFFICIENT_SIGNAL (as in 9D accepted fixture); add a second positive thermal-compatible fixture if feasible, without faking sensor measurements or loosening original detector constraints. Respect original method/threshold.

## 99. Example engineering data flow

A 9D receipt "anomaly/inlier" -> 9E load immutable 9D receipt -> resolve original 9C run/finding -> verify exact feature snapshot/cutoff -> reference checksum/method/family -> emit descriptive evidence factors and gap codes -> canonicalize manifest -> persist immutable bundle -> serve safe projection. Every arrow must be backed by actual source rows, not a mock-only schema.

## 100. Independent acceptance evaluator

Create \`scripts/evaluate_prediction_evidence.py\` (or repo-conventional equivalent). It MUST exercise genuine Phase 9D serving receipts from actual 9B and 9C pipelines on migrated disposable TimescaleDB, then 9E materialization, immutable persistence, independent source/semantic verifier, HTTP auth/read, concurrency, negative controls, result lineage equality and regression checks. Unit mocks alone do not count.

## 101. Evaluator independent oracle

The evaluator may use project services to create source fixtures, but its assertions must independently compute expected node count/edge relationships, source-row hash/score match, cutoff eligibility and wrong-source rejection. Do not simply compare evidence builder outputs with that same builder's own "verification" function and call it independent. Predeclare expected fixture facts/edges and reason outcomes before scoring.

## 102. Disposable migration round-trip

Test \`0016 -> new 9E revision -> 0016 -> new 9E revision\`, plus fresh DB migration from base. Before/after digests for Phase 0–9D tables must remain equal. Test downgrade drops only 9E-owned tables and preserves original prediction receipts, models, anomaly findings and prior user/session data. Note 9E new records are lost on downgrade as documented.

## 103. Database immutability tests

Attempt UPDATE/DELETE on evidence bundle, node/fact manifests and audit entries; trigger/constraint must reject. Try duplicate logical fingerprint with conflicting projection content; fail safely. Orphan source references and oversized JSONB must be rejected. Simulate interrupted inserts and verify full rollback.

## 104. Field equivalence to 9D

For each evidence bundle match exact original 9D \`receipt_id\`, result_type, horizon, score/threshold/decision, source role and cutoff; compare with stored response_body and typed \`PredictionResponse\`. Differences or unsupported future 9D schema versions result in typed "unsupported schema", never implicit best-effort coercion with verified status.

## 105. 9C canonical source equality

For anomaly receipts, match 9D receipt's anomaly_run_id/anomaly_finding_id and version to actual 9C finding row and its reference dataset manifest. 9E may read the recorded top deviations; cannot train a new detector to derive more favorable factors. Demonstrate tampered finding projection rejection.

## 106. 9A source integrity equality

Verify selected FeatureSet ID, source hash, provenance hash, feature version checksum, source role, quality and time windows from 9D receipt against stored 9A row. Validate feature value's missing reason and unit using Phase 9A feature registry. If full source value is unavailable but 9D receipt exists, classify partial verification appropriately.

## 107. As-of quality proof

Evidence must record both receipt quality summary and fact-level observed coverage; no double count of optional fields, no coercion of invalid to missing-as-healthy, and no use of future-known metadata. Test coverage calculations with missing/invalid and legitimate numeric zero.

## 108. Trusted verifier threat model

The trusted boundary is the application process + database with read-only source integrity and owned immutable 9E writes. Hashes protect consistency, not against privileged DBA rewrite of all records. An attacker with the bearer token can request controlled historic evidence; future user-authorization is not solved. Discuss denial-of-service and artifact provenance explicitly.

## 109. Information minimization

Avoid complete VIN, license plate, GPS, raw telemetry sample arrays, operator token, embedding text, training row matrices, unrestricted notes, source file paths or model binary bytes in evidence responses and metrics. Internally store only necessary bounded feature values and IDs when claims require them. Sanitized projections are mandatory for HTTP.

## 110. Observation metrics

Define bounded OpenTelemetry counters/timers: evidence build attempts/success/failure, verification outcomes by finite enum, gap counts by reason, provenance source type, graph sizes histogram, build/verify duration, replay count, DB conflict and request denials. No vehicle IDs, receipt UUIDs, VINs, artifact checksums or feature floats as metric labels.

## 111. Tracing

Trace receipt lookup, access boundary, source-graph resolution, cutoff eligibility, data-quality verification, claim construction, canonical hash, immutable persistence, read projection and independent verification. Use bounded span attributes and preserve existing 9D correlation policy; don't trace raw feature matrices or human notes.

## 112. Performance benchmarks

Benchmark cold/warm evidence build and independent verification for 9B+9C receipts, 1/10/100 serial and near-max concurrent requests, complete, partial and abstained bundles. Report elapsed time, p50/p95 where sample count sufficient, peak RSS, maximum DB sessions, bytes, graph counts and replay cost. These are local engineering observations, NOT production latency SLAs.

## 113. Denial-of-service controls

Validate bounded graph traversal using explicit visited set, depth cap and source-query limit; no recursive self-referencing graph or unbounded anomaly reference row download. For 9C materialize only frozen reference summary and top associated feature deviations rather than all 10,000 reference rows. Query timeouts and clean pool close required.

## 114. Pure core and adapters

Prefer testable pure \`build_manifest\`, \`validate_source_claims\`, \`canonicalize\`, \`hash_evidence\`, \`render_safe_projection\` with separately bounded async repository. Pure builders cannot read the current clock except supplied generated_at, and cannot import GUI or LLM provider. Avoid circular imports with 9D and existing agents.

## 115. Error/status mapping

Establish machine-readable codes for RECEIPT_NOT_FOUND, RECEIPT_SCHEMA_UNSUPPORTED, EVIDENCE_NOT_AVAILABLE, EVIDENCE_SOURCE_MISMATCH, SOURCE_NOT_VERIFIABLE, FEATURE_OUT_OF_CUTOFF, VEHICLE_SCOPE_MISMATCH, EVIDENCE_INTEGRITY_FAILED, PROJECTION_TRUNCATED, BUDGET_EXCEEDED, IMMUTABLE_CONFLICT and INTERNAL_ERROR. Honor 9D HTTP 401/403/404/409/413/429/503/504 semantics.

## 116. No inferred corroboration

If two model outputs derive from same 9A feature set, mark them separately or related but not independent. No ensemble consensus or new "predictive reliability grade" generated from agreeing scores in 9E. Any future combined confidence requires 9G calibration and evaluation. This rule is a core review blocker.

## 117. Documentation deliverables

Create:

- \`docs/architecture/phase-9e-prediction-evidence.md\`
- \`docs/validation/phase-9e-acceptance.md\`
- \`docs/validation/phase-9e-evidence-evaluation.md\`
- \`docs/validation/phase-9e-traceability-ledger.md\`
- \`docs/runbooks/prediction-evidence.md\`
- supporting ADRs and security/threat model updates;
- \`README.md\`, \`AI_CONTEXT.md\`, roadmap, testing, observability and generated contracts as relevant.
  Machine receipts must be saved under ignored \`.validation/phase9e/\`.

## 118. ADR requirements

Record accepted architecture choices for evidence schema/graph ownership; receipt vs derivation fingerprint and immutable persistence; 9B/9C provenance semantics and cutoff; approved fact/claim templates, verification states and non-causal limitation; controlled HTTP authorization and privacy. Prefer repository's next sequential ADR number; inspect existing registry so no duplicate numbers.

## 119. Operator runbook

Show how to prepare controlled dev/test fixture, generate 9D approved serving receipt, materialize evidence, verify it, retrieve safe redacted JSON, repeat idempotently, revoke 9D model without erasing history, inspect abstention and simulated tamper scenarios. No real production token, VIN, private vehicle data or external model charges in example commands.

## 120. Evaluator evidence narrative

Produce source lineage tables for 3 supervised tasks + 4 anomaly families, complete/partial/abstained counts, node/fact/edge counts, verification outcomes, explicit gap reason counts, replay SHA/IDs, cutoff-leak sentinel, independent score+version equality and malicious mismatch outcomes. Record actual measured values only and state synthetic fixtures don't establish real-car reliability.

## 121. Makefile targets

Add actual functional targets e.g. \`make test-prediction-evidence\`, \`make phase9e-acceptance\`, \`make benchmark-prediction-evidence\`, \`make prediction-evidence-observability\`. Integrate with canonical full-validation and summary/artifact publishing. No no-op success targets or fake receipts. Bound clean environment setup to CI capacity.

## 122. Phase 9A–9D regression

Run full 9A feature generation, 9B supervised trainer/acceptance, 9C anomaly detector/acceptance, 9D controlled prediction service/real HTTP/approval gates, plus canonical Phases 0–8 deterministic suites. Ensure 9E does not change 9D scoring outputs, request auth, response compatibility, serving approval or idempotency.

## 123. Security/regression gates

Run \`make verify\` and repo's exact equivalent cloud/local commands, Python strict typing/Ruff, coverage, generated TypeScript/OpenAPI contract check, Playwright E2E, observability, build, dependency audit, secret checks, Docker security scan, CodeQL Python/JS/TS and dependency review. No external paid embeddings or real-model 7D suites by default; preserve historical paid-evaluation caveat.

## 124. Independent HTTP/DB security acceptance

On disposable migrated DB run actual FastAPI ASGI + real HTTP control path. Probe unauthenticated POST/GET, private-peer denial, disabled flag, attempted production enablement, malformed body/ID, oversize requests, role mismatch, cross-vehicle receipt, active/revoked historical read, forced DB rollback and 10-way repeated materialization. Verify no private data returned.

## 125. Resilience and missing sources

Test absent original receipt, absent source FeatureSet, unavailable 9B/9C artifact, missing old anomaly reference, destroyed older training artifact, unsupported new future version and canceled build. Preserve historical source references or explicit NOT_VERIFIABLE; don't delete an old verified bundle just because an artifact is now missing. Do not silently use newest replacement model.

## 126. Real/imported data smoke

If sanitized actual imported CSV fixture is available, optionally test compatibility on disposable copy; 9C previously observed 264 imported pulls but lacked enough exact-cohort history. Do not lower minimum reference support or forge labels just to produce real-case success. Record NOT_RUN/no eligible evidence and reasons when no valid source set exists.

## 127. Capacity/resource acceptance

Predeclare fixture-focused bounded thresholds for maximum graph size, JSON bytes, memory, DB connections, request rates, worker usage and concurrency correctness. Accuracy/performance across real cars is unknown and cannot be a fabricated acceptance floor. For 9E source-integrity, hash determinism, leak sentinels and auth invariants the expected test pass rate is 100%.

## 128. CI exact final SHA policy

After implementation commit and push, capture HEAD and origin/branch SHA equality. Open PR against \`main\` and DO NOT MERGE. Verify GitHub Actions quality, integration/E2E, Security, CodeQL Python/JS/TS, dependency review and Canonical Docker/full-stack gate ALL successful on that exact final SHA, including Phase 9E independent evaluator and older phase gates. After fix, rerun on new SHA; stale receipts cannot prove latest commit.

## 129. PR body and audit deliverables

PR description includes branch and baseline, final exact SHA, migration table map, root evidence schema and examples, known limitations, auth controls, 9A–9D lineage proof, 9B/9C differentiation, false diagnostic guard, positive/negative fixture counts, withheld/absent sources, benchmark, observability, security tests, prior phase regressions and exact-head CI URLs. No auto-merge, no premature 9F tools.

## 130. Phase boundary tests

Explicitly prove 9E adds no MCP tool, LangGraph node, agent provider invocation, agent question routes, RAG source ingestion, threshold calibration or predictive UI. Shared file modifications only to truly necessary wiring, migration, docs, contracts, tests and observability. No ECU command or mechanical action surface introduced.

## 131. Definition of Done — provenance and semantics

- [ ] Versioned PredictionEvidence root, facts, nodes, edges, gaps and claim bindings
- [ ] Exact 9D receipt/binding-event/FeatureSet/version source links
- [ ] 9B NEXT_PULL and 9C AFTER_PULL_OFFLINE distinguished
- [ ] 3 supervised task + 4 anomaly family fixture coverage
- [ ] Source/feature/quality/cutoff/version/checksum verification
- [ ] Verifiable evidence of abstentions, missing signals and insufficient references
- [ ] Deterministic non-causal human-readable interpretation
- [ ] Model scores NEVER presented as mechanical failure probabilities
- [ ] Source association vs causation, no fake confidence or corroboration
- [ ] Frozen historical scope (vehicle/config/mod/source/time) with late-data safety

## 132. Definition of Done — persistence and security

- [ ] Additive migration after 0016, clean rollback/upgrade; zero legacy data mutation
- [ ] Immutable content-addressed bundles and source references, deterministic replay
- [ ] DB triggers/constraints prohibit UPDATE/DELETE and invalid graph references
- [ ] Source mismatches and not-verifiable gaps distinguished from verified results
- [ ] Bounded authenticated controlled HTTP and operator CLI
- [ ] Production disabled and 9D approval/revoke semantics untouched
- [ ] Privacy-safe projection; no raw VIN, tokens, artifacts, telemetry matrices or secrets
- [ ] Adversarial integrity, spoofing, cross-vehicle, as-of and availability tests
- [ ] Concurrent identical materializations yield same evidence identity

## 133. Definition of Done — validation and delivery

- [ ] Real independent evaluator on disposable TimescaleDB and actual HTTP path
- [ ] Independent oracle checks source claims, graph links and cutoff
- [ ] Model/detector and receipt value parity with frozen 9D/9B/9C values
- [ ] Unit tests, DB integration, latency/resource benchmarks and OTel gates
- [ ] Phase 9A, 9B, 9C, 9D and canonical earlier regression PASS
- [ ] README, architecture, ADRs, runbook, evaluation, ledger and generated contracts updated
- [ ] Final-head GitHub quality, full-stack, integration, security and CodeQL PASS
- [ ] PR open/unmerged, clean branch, exact remote SHA verified
- [ ] NO Phase 9F agents, 9G calibration, 9H UI, Phase 10 MLOps or production exposure

## 134. Final report contract

Deliver a concise but evidence-rich engineering handoff:

1. repository branch, merged 9D baseline, final SHA, PR URL/state;
2. actual new migration revision, schema names and immutable constraints;
3. provenance graph / schemas and stable identity/hash algorithm;
4. number of original receipt types, eligible/partial/abstained/failing evidence bundles;
5. 9B three task parity (score/threshold/decision, feature source), no future outcome leakage;
6. 9C four family parity (run/finding/reference/score, context, abstentions);
7. typed claim and source verification, all mismatch/NOT_VERIFIABLE behaviors;
8. original source freeze/cutoff/source-role/vehicle-config-mod safeguards;
9. real DB source/receipt integrity and idempotent concurrent replay receipts;
10. protected HTTP CLI routes and all auth/production-disabled tests;
11. graph/time/CPU/memory/resource bounds, benchmark metrics and trace/metrics receipts;
12. security scan and independent adversarial tests;
13. local and exact-head remote Phase 9A–9D regression gates;
14. PR exact-head canonical Docker/full-stack, quality, integration, CodeQL and dependency URLs;
15. real-world data absence and all honest validation caveats;
16. explicit confirmation Phase 9F–9H absent and user must merge manually.

ONLY if all mandatory gates genuinely passed, end with EXACT line:
\`PHASE 9E — PREDICTIONEVIDENCE: VERIFIED\`

Otherwise end with EXACT line:
\`PHASE 9E — PREDICTIONEVIDENCE: NOT VERIFIED\`

Keep working through fixable failures rather than stopping at a partial scaffold. Never invent a pass, edit acceptance thresholds after observing failures merely to force green, spend paid provider credits by default, or merge the PR.
