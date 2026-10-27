# Phase 9F — Agent Integration (PredictionEvidence + MCP + LangGraph)

**Repository:** Brunobosso98/Vehicle-Intelligence-Platform  
**Required branch:** `codex/phase-9f-agent-integration`  
**Merge baseline SHA:** `466ce900988bd81e1d968eb319e970955b4011d7` (Phase 9E PR #45 merged on 2026-10-22)  
**Previous phases:** 9A features; 9B next-pull classifiers; 9C anomaly detectors; 9D controlled serving; 9E immutable verified PredictionEvidence; Phases 6–8 read-only MCP, LangGraph specialists and trusted technical RAG.

This Markdown is the **complete authoritative implementation, acceptance, safety and delivery contract**. Read EVERY section before editing code. Do not summarize away security requirements. The goal is a real deterministic, controlled **read-only** link from already created 9E PredictionEvidence to existing Phase 7A/7C AgentRun grounding and LangGraph specialists via a properly authorized MCP/evidence adapter, not a public diagnostics agent.

## Architectural non-negotiables

```text
Phase 9A canonical source features and cutoffs
  -> Phase 9B NEXT_PULL model / Phase 9C AFTER_PULL_OFFLINE detector
  -> Phase 9D approved, disabled-by-default controlled serving receipt
  -> Phase 9E versioned, immutable verified PredictionEvidence
  -> Phase 9F explicit dev/test prediction-reading capability & selected-vehicle policy
       -> official MCP read-only transport (or rigorously justified equivalently isolated bridge)
       -> bounded 9E-safe projection with quality, horizon, source role, integrity and gaps
       -> run-local Phase 7A EvidenceRegistry with exact citation/claim bindings
       -> Data Quality gate and Phase 7C Thermal/Performance/Fuel-Air-Boost specialists
       -> Supervisor + existing Phase 8 documentary evidence, kept separate
       -> application-rendered grounded answer with safe limitations
DEFERRED: 9G calibration/drift, 9H predictive UI, MLOps/prod deployment, diagnosis, vehicle control.
```

**Safety caveat:** existing Phase 9D/9E is operator-only and cannot run in production; current Phase 7 user/vehicle account ownership is NOT general multi-tenant authorization. An MCP read credential is not automatic permission to read prediction evidence. If the intended bridge cannot preserve this boundary, FAIL CLOSED and leave the feature disabled rather than enabling an insecure production path.

**Governance:** required deliverable is a PR against main, OPEN and UNMERGED; exact-head successful validation and evidence receipts; user performs merge manually.

---

## 1. Initial repository discipline

Fetch origin and inspect working tree, branch, upstream, current SHA and repository instructions (including AGENTS.md). Switch to the EXISTING `codex/phase-9f-agent-integration` branch; never create a replacement, push to main, force-push or rebase pushed history. Verify ancestor `466ce900988bd81e1d968eb319e970955b4011d7` (Phase 9E PR #45 merged). Record current migration head and CI gate names.

## 2. Complete mandatory reading

Read this entire document and the original prompts, architecture, validation, ADRs and runbooks for Phases 6, 7A, 7B, 7C, 7D, 8, 9A, 9B, 9C, 9D and 9E. Inspect `agents/{schemas,orchestration,grounding,evidence,state,service,config,prompts}`, `agents/specialists`, `mcp/{tools,server,auth,config,adapter}`, `knowledge`, `predictions`, `prediction_evidence`, migrations, tests, observability and deployment boundaries.

## 3. Mission

Integrate **existing, verified Phase 9E PredictionEvidence** into controlled run-scoped Phase 7 LangGraph agent/specialist analysis. Add an explicitly authorized, read-only and versioned bridge that exposes facts, scores and limitations with correct claim-grounding and citations. Prove the agent never confuses model output with a physical measurement, mechanical diagnosis, calibrated failure probability, or independent corroboration.

## 4. Prior deliverables and baselines

Phase 9A: immutable cutoff-aware FeatureSets. 9B: three supervised `NEXT_PULL` engineering-label tasks. 9C: four retrospective `AFTER_PULL_OFFLINE` detector families. 9D: disabled-by-default, dev/test-only, bearer/private-network Prediction Service and immutable receipts. 9E: 134-section, DB-verified immutable evidence graphs, safe projections and explicit `COMPLETE/PARTIAL/ABSTAINED` states. 7C: three specialists plus Data Quality and Supervisor; 8: trust/applicability-aware documentary RAG.

## 5. Current authorization risk is a hard blocker

Existing 9D/9E operator bearer identifies an engineering operator, NOT an end-user or vehicle owner. Existing agent MCP `mcp:read` token is NOT an authorization for predictive evidence. The existing agent API does NOT prove general account/multi-tenant vehicle authorization. Phase 9F MUST NOT broaden public/production accessibility by registering a globally discoverable ordinary tool.

## 6. Allowed controlled environments

Prediction-enabled agent behavior MUST be disabled by default and prohibited in production. Require explicit `development`/`test` environment + a new run-scoped controlled-prediction flag + an operator-approved capability/token/scope. If full proof of caller/vehicle consent is unavailable, limit integration to a private operator-only test harness; never turn on global agent access.

## 7. Scope and future separation

9F: controlled evidence retrieval, agent routing, specialists, grounding, supervisor synthesis, deterministic evaluations and documentation. 9G owns scientific calibration, false-positive research, drift and threshold policy. 9H owns predictive dashboards and user-facing product UI. Phase 10 owns operational MLOps; Phase 12 production account/tenant access. NO new training, inference endpoint, serving approval, streaming vehicle monitoring, ECU control, or autonomous maintenance.

## 8. Refrain from auto-inference

Agents consume already persisted 9D receipts and 9E bundles; they do NOT on-demand call `POST /next-pull`, `POST /anomalies`, training, detector fit, feature generation, approval or activation to satisfy a question. Missing eligible evidence causes explicit insufficiency or an operator-only offline preparation instruction. No repeated scoring loops, no silent fallback to newest model.

## 9. No causal diagnosis

Evidence permits: 'the registered model produced engineering classification score X against its frozen threshold' and 'recorded pull differs statistically from frozen reference'. It forbids: confirmed turbo/HPFP fault, unsafe/safe-to-drive verdict, failure probability, prediction of actual damage, causal repair recommendation or tuning instruction. Future models must never bypass this phase's policy.

## 10. Input-role boundaries

`synthetic`, `imported_fixture`, `imported`, `real_vehicle` and source policy remain exact. Synthetic outputs are test engineering artifacts, never 'my real vehicle risk'. A request about the user's real car must NOT use synthetic evidence from an unrelated fixture, even if vehicle model/tune description resembles it.

## 11. Primary functional journeys

User asks about an explicit previous predictive analysis -> agent discovers eligible current-run evidence -> verifies 9E chain -> renders supported facts with citations and limitations. User asks about observed anomaly -> 9C horizon retained. User asks what model expects on next compatible pull -> 9B future outcome definition retained without presenting target pull as observed. User asks for an unsupported diagnosis -> constrained refusal with supported observations if available.

## 12. Proposed architecture

Prefer Phase 6 official read-only MCP boundary as the only source of vehicle facts: a dedicated bounded `get_prediction_evidence` read tool and narrowly scoped list/lookup if genuinely required. The MCP tool must call a constrained 9E reader/verifier, not SQL assembled by the model or a bare ORM. If MCP credential design cannot safely express distinct prediction permissions, implement only a private operator adapter with the same evidence envelope and block regular agents until proper isolation is demonstrated.

## 13. MCP compatibility vs safety trade-off

Do not blindly attach new tools to existing `mcp:read` privileges. Design a separate scope such as `mcp:prediction-evidence:read` plus explicit controlled test policy, evaluated SERVER SIDE for tool call and discovery. If the MCP library's documented authorization primitives do not support enforcement, implement a hard tool-level authorization check plus tests; untrusted tool descriptions alone are insufficient.

## 14. Operator-only eligibility

Verify `VIP_AGENT_*`, `PREDICTION_SERVICE_ENABLED`, `ENVIRONMENT`, private peer/network rules and all relevant serving/operator flags before exposing predictive tool definitions to an agent. The 9D bearer must never be forwarded to LLM, MCP untrusted clients, SSE, logs or browser. Do not treat general app role as a secure identity unless proven by code.

## 15. No security downgrade via internal calls

Direct in-process repository calls are not a shortcut around 9D/9E controls. If a trusted service-to-service adapter is chosen, require explicit policy evaluation, source-scoped eligibility, read-only operations, provenance verification and test-only enablement. Do not add a public direct database read endpoint or use `prediction_evidence` private DB as an unguarded global tool.

## 16. Selected-vehicle ownership

Bind every prediction receipt and source FeatureSet to the **existing AgentRun vehicle_id** and selected `session_id`/`pull_id` where applicable. Reject mismatched explicit IDs and nested graph nodes. Historical source references to earlier compatible pulls are only allowed when verified in the frozen 9C reference; cross-vehicle pooling remains forbidden.

## 17. Scope can be narrow not fabricated

The agent currently has selected vehicle but not demonstrated authenticated per-person ownership. Controlled local operator grant may authorize a selected fixture vehicle for dev/test, with explicit audit. Do not claim this solves future multi-tenant privacy; keep production prediction integration disabled until a future real authorization layer.

## 18. Request identifiers and tool schemas

Use strict Pydantic and MCP tool schemas with `vehicle_id`, exact `evidence_id` or `receipt_id`, optional validated session/pull constraints, bounded pagination and no arbitrary JSON path/SQL/model class, no unbounded full-fleet list. UUID guesses must not enumerate all predictions. Tools should return safe 404/not-in-scope without revealing outside vehicle presence.

## 19. Discovery restrictions

The prediction tool should not be in general MCP discovery for callers without its dedicated verified capability. Ensure old `mcp:read` callers and existing Phase 6 read-only tools behave byte-equivalently in old permission contexts. Independent tests must call MCP discover and then actually invoke hidden tool by name to prove server-side enforcement.

## 20. Tool metadata

Mark all new MCP capabilities as read-only, non-destructive, idempotent and explicitly versioned; ensure JSON schemas and declared output sizes are safe. The tool must never create/reissue 9D receipts, regenerate 9E graphs or call 9E `/verify` if that appends audit rows, unless a separate explicitly authorized operator action exists; standard agent read is side-effect-free.

## 21. Frozen evidence retrieval

Use one previously materialized 9E immutable bundle ID, latest read-time verification or historical verification policy with explicit provenance, not an inferred newest bundle or recomputed source graph. If a verified artifact subsequently becomes unavailable, preserve integrity state `VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE` and prevent stronger evidence claims; do not silently repair or retrain.

## 22. Integrity admission

Require 9E root schema/version, original receipt status and cutoff, source-role, model/detector and graph hash checks, source snapshot integrity, independent verification freshness policy, frozen activation history and caller vehicle scope. `FAILED_SOURCE_MISMATCH`, `NOT_VERIFIABLE`, `UNSUPPORTED_SCHEMA` MUST prevent affirmative numerical/model claims. Record a precise bounded reason.

## 23. Completeness admission

9E `COMPLETE`, `PARTIAL`, `ABSTAINED` are independent from integrity. A `PARTIAL` verified bundle is not a complete basis for statistical or causal claims; permit clearly qualified observed facts only when directly verified and allowlisted. `ABSTAINED` can explain why no score exists, but cannot support a result. Preserve all gap reasons.

## 24. Source artifact class policy

`VERIFIED` source artifact supports only the particular frozen result's provenance; `VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE` may support a carefully worded historical recorded-output statement if approved policy allows, but cannot assert current reproducibility; `FAILED_SOURCE_MISMATCH` blocks model claims. Do not collapse artifact availability, graph integrity, completeness and model accuracy into a single confidence number.

## 25. Horizon separation

9B `NEXT_PULL` is a classification of a versioned observable outcome for the next compatible pull, using only the current input snapshot; it is not the observed next pull's telemetry, nor future failure probability. 9C `AFTER_PULL_OFFLINE` is relative statistical anomaly of the observed completed pull. The agent's structured output must carry horizon and task/family all the way into final answer and citations.

## 26. Exact outcome semantics

Retain original 9B task identifiers `NEXT_PULL_THERMAL_DEGRADATION`, `NEXT_PULL_PERFORMANCE_DEGRADATION`, `NEXT_PULL_FUEL_DEVIATION` and label definitions; preserve their model validation class and caveats. Preserve 9C families `thermal`, `boost_air`, `performance`, `fuel`, method name, frozen reference, absolute score scale and threshold.

## 27. Score representation

Keep scores numeric and units/meaning explicit: 9B `engineering_validation_score` in [0,1] is not calibrated real-world failure probability. 9C score has detector-specific nonprobability scale; higher means relatively more unusual within that detector. Never convert it to `% vehicle health`, severity tier or compare absolute values across unlike detectors.

## 28. Source facts projection

Agent-facing projection must include only allowlisted 9E facts (`source_tool`, exact typed path/value/unit/quality/cutoff, context) plus versioned 9D decision fields and safe 9E interpretation. Do not expose 9E internal source hashes, raw telemetry matrices, VIN, license plate, GPS, artifact paths, model internals or full vehicle identifiers to unrelated model contexts.

## 29. Existing AgentRun evidence registry

Bridge valid 9E evidence into Phase 7A `EvidenceRegistry` with current `run_id`, existing `vehicle_id`, originating tool_call_id, bounded fingerprint and fact paths; do not insert the 9E bundle as a raw unvalidated object. Preserve source evidence ID as provenance internal field and distinguish it from run-local `Evidence.id` cited to the model.

## 30. Fact path discipline

Establish a specific versioned projection e.g. `prediction-agent-summary-v1`, with stable fields for status, horizon, task/family, score, threshold, decision, quality, completeness, integrity, source role, gaps, input cutoff, associated feature measurement/units and reference summary. Any field omitted by bounds must set truncation/omission flags; no optimistic defaults.

## 31. Evidence namespace collision prevention

9E `evidence_id`, Phase 7A run-local `Evidence.id`, 9D receipt_id and 9C finding ID must NEVER be conflated. A model can cite only run-local evidence IDs that the registry has admitted. Translation to immutable source IDs is held in controlled provenance; direct guessed 9E UUID citations are invalid.

## 32. Nested identity checks

Ensure `EvidenceRegistry.check_ownership` or equivalent verifies nested source vehicle/pull/session fields, including future 9E projection. Lack of public vehicle IDs in 9E safe HTTP projection is not proof of ownership: server must verify internal original source identifiers before producing the limited response.

## 33. Source cutoff and time

Persist run-time reference to original `effective_cutoff`, source timestamps and temporal availability. Later capture/modify/tune history must not change what the model knew at the 9D cutoff. For 9B reject target pull data after cutoff in every agent projection. Existing Phase 7 configuration interval validation still applies.

## 34. Historical source role uncertainty

Real data may not satisfy 9C same-cohort support, especially imported telemetries; abstention is the correct result. A lack of historical predictions cannot be silently filled by synthesizing one from a recent real pull. Negative tests must assert no model/prediction training or request is executed on missing evidence.

## 35. Grounding policy extension

Extend structural claim validation, not just system prompt, with allowlisted templates for `prediction_result`, `anomaly_result`, `prediction_insufficient` and `statistical_association` or equivalent. Validate exact evidence IDs, typed fact paths, values and units, horizon, source role, quality/completeness, measurement status and cutoff before rendering. Preserve existing `recorded_fact` and `temporal_association` rules.

## 36. Application-rendered claims

The final public statement must be composed by trusted application templates after validation, not the raw provider draft. Reject diagnoses, deterministic repair actions, invented warranty/safety conclusions and unsupported percentages even if model prompt attempts them. The model may propose an allowed structured draft but cannot author authoritative conclusion text.

## 37. Claim category classification

Separate `MEASURED_OBSERVATION`, `MODEL_CLASSIFICATION`, `STATISTICAL_OUTLIER`, `DESCRIPTIVE_ASSOCIATION`, `DATA_GAP`, `DOCUMENTARY_REFERENCE`, `HYPOTHESIS` as appropriate to established schemas; do not label a model output as a physical measurement or a statistical association as verified causation. Preserve earlier Phase 7A Classification contract through additive changes.

## 38. No confidence laundering

Do not turn 9E source integrity `VERIFIED`, prediction decision `true`, 9C anomaly label, 7C specialist agreement or Tier-1 RAG citation into a calibrated confidence percentage. Every numerical probability-like field must have explicit trained/calibrated semantics (deferred to 9G). For now fixed diagnostic probability and safety scores are forbidden.

## 39. Abstention statements

When 9E result `ABSTAINED_*`, partial reference, unsupported source, insufficient signal/quality, or unverifiable lineage occurs, render bounded actionable **data collection gap** text only, not automatic capture. Phase 7B acquisition still requires its existing explicit operator approval; 9F must not authorize a sensor or collector itself.

## 40. Contradictory data

If Phase 3 rule event, Phase 5 analytics or 9E model result disagree, expose disagreement with independent citations and measurement caveats; do not majority vote or produce combined risk metric. Facts derived from same underlying 9A FeatureSet are correlated, not independent corroboration. Test this explicitly.

## 41. Documentary separation

Phase 8 RAG is source literature, not a measured vehicle fact. Verified Tier 1/2 docs can explain generic engineering concepts subject to actual engine/config/tune applicability; they cannot backfill missing fuel measurements, validate 9C detector generalization or prove a real mechanical fault. Preserve knowledge source trust and operating-condition checks.

## 42. Automotive examples

Illustrative N55 BMW: unusual observed IAT pull vs own compatible cohort; fuel pressure unavailable on an OBD-only profile; predicted next-pull fuel deviation on a synthetic fixture; no valid model for a real vehicle. Test with multiple simulated brands/configurations, not only N55. No feature should depend on branded ECU/tuner labels absent source measurements.

## 43. Supervisor routing

Add an explicit policy for prediction-related question intents (PT/EN): classify whether request targets existing prediction, anomaly, model methodology, real measurements, generic technical knowledge, or prohibited diagnosis. Route to appropriate bounded specialists and 9E evidence adapter only when explicit controlled flag and available current-run evidence exists. Do not route ordinary vehicle questions to paid or expensive prediction paths.

## 44. Deterministic no-model routing

Existing 7C deliberately avoids extra model calls for recognizable factual questions. Preserve that property for explicit 'qual foi a previsão registrada?' or 'existiu anomalia?' requests by deterministic classification and evidence retrieval before optional synthesis. Never introduce a routing LLM solely to decide whether to access 9E.

## 45. Data Quality first

7C Data Quality specialist gates domain interpretation. A verified but low-quality predictive evidence must be downgraded/abstained, not upgraded by persuasive thermal or performance specialist text. Source/feature missingness and original quality warnings are propagated to supervisor report and public limitations.

## 46. Thermal specialist behavior

Can cite compatible 9E thermal NEXT_PULL model output and retrospective thermal 9C deviations distinctly. Requires correct available measured temperature and unit, original timestamps and quality to describe observed thermal behavior; cannot assert cooling-system/charge-cooler failure. If thermal anomaly abstained for insufficient signal, clearly explain no score.

## 47. Performance specialist behavior

Can use 9E NEXT_PULL performance classifier and retrospective 9C interval deviation as two different results. Preserve gear/session/configuration comparable contexts; RPM interval outputs are not engine horsepower estimates. No absolute gains, 'bad engine', or repair advice without measured supported data.

## 48. Fuel/air/boost specialist behavior

May cite verified 9C fuel/boost anomaly and 9B NEXT_PULL fuel classification only for source-role and required pressure signals present. Generic OBD-II may lack fuel pressure. No fabricated HPFP/LPFP rail readings, no tune target inference and no fault attribution solely from a model score.

## 49. Specialist allowlist

Per-specialist `REGISTRY` tool permissions must be updated with explicit evidence intent, not a blanket prediction tool for every specialist. Data Quality can inspect coverage/gaps; domain specialists may access family-specific verified projections. Scoped Pydantic schemas must enforce selected vehicle/session/pull and exact evidence IDs.

## 50. Bounded specialist fan-out

Existing global limits: 16 model turns, 32 MCP calls, 1 telemetry window, <=3 domain specialists concurrently capped at 2, run 90s, specialist 25s. New predictions must consume those shared budgets and never silently reset. Set separate prediction-evidence call cap (e.g. 2–4 per agent run) with tested limit and local bounded cache.

## 51. Run-local evidence cache

Cache key includes selected vehicle, run ID, exact 9E evidence ID/receipt, safe projection version, verification policy, source role/cutoff and capability scope. Cache expires with the run and cannot cross vehicles, sources, provider sessions or authorization revocation. Replaying SSE must not refetch or create new evidence.

## 52. Specialist concurrency isolation

One specialist cannot inject evidence into another before sibling completion. Preserve per-specialist frozen registry views, sorted deterministic ordering and existing MCP budget mutex/locking. Test concurrent thermal+fuel+performance calls with a shared FeatureSet where all are authorized but interpretations remain separate.

## 53. Synthesis contract

Supervisor merges independently validated domain outputs, preserves exact source IDs, unresolved gaps and conflicting statements, and never turns agreement among model/Phase3/RAG into independent diagnostic proof. Predictive statements require explicit subject/horizon/status/citation. Loss of source fidelity downgrades whole answer.

## 54. Answer backward compatibility

Existing Answer, AgentRun, SupervisorReport and SSE event schemas must remain readable for prior runs. Add optional versioned prediction artifacts with safe defaults; do not repurpose Phase 7A fields to mean model probability. If type/schema changes require new event/API version, update clients and migrations/contract generation coherently.

## 55. Provider-independent grounding

Use the SAME run-local evidence, tool calls, claim validator, application renderer and decision policies for deterministic provider and real OpenAI provider. Prompts are additional defense only; the code is authoritative. No provider-specific shortcut to unvalidated JSON prose.

## 56. Provider prompts

Update policy narrowly to explain evidence types, two horizons, no causal claims, stable citations, abstentions and source applicability. Validate prompt injection attempts inside document snippets, raw telemetry metadata, specialist output and 9E interpretation strings. Providers must not alter source version/cutoff via tool arguments.

## 57. RAG hybrid questions

For 'por que IAT sobe e o que diz a documentação?' keep two independent tracks: measured/predictive 9E proof and Phase 8 documentary evidence; contextual explanation may cite both but cannot claim they prove a particular cooling failure. Verify stock vs Stage/map applicability and unknown tuner/gear/fuel conditions.

## 58. No extra paid LLM calls

Implement 9F and all normal CI using scripted deterministic provider and synthetic/cached RAG fixtures. Existing 7D paid real-model 120-execution rerun caveat persists and must not be misrepresented. Any optional real model trials require explicit operator permission/spend ceiling and remain out of standard acceptance.

## 59. Agent tool argument injection

An agent requesting arbitrary evidence UUID, another vehicle, unapproved model, raw artifact, unrestricted query, future cutoff, source role rewrite or indirect tool name must be denied before DB and never return a guessed record. Enforce server-side whitelist and source-root checks, not just model tool description enum.

## 60. Safe tool error taxonomy

Use stable errors such as PREDICTION_DISABLED, EVIDENCE_NOT_IN_SCOPE, EVIDENCE_NOT_VERIFIED, ABSTAINED, LOW_QUALITY, UNAVAILABLE, CAPABILITY_REQUIRED, BUDGET_EXCEEDED and SOURCE_SCHEMA_UNSUPPORTED. Map to existing MCP Envelope/error shape without leaking underlying SQL/VIN/existence to callers without permission.

## 61. Tool discovery caching

Cache/pinning of official Phase 6 catalog must account for a new conditional tool without falsely treating it as missing globally for legacy agents. Discovery can be scope-aware; requirements and tests should compare legacy unauthenticated/unprivileged catalogs with the previous baseline.

## 62. Read-only MCP and audit semantics

The 9E POST verify route appends verification audit and is not read-only. Read-only agent tools should read previously verified evidence and, if mandatory source verification is required, use a **pure, bounded no-write verifier** outside normal materialization; do not write Phase 9E audit per model tool call. Instrument access through Phase 7 own tool-call/run audit only.

## 63. Historical verification freshness

Declare whether 9F requires read-time source verifier for each lookup or uses historical verified snapshot. A historical `VERIFIED` 9E write does not prove current artifact availability or prevent later source mismatch; implement bounded revalidation/policy without unrestricted full reference traversal. Preserve exact-original cutoff.

## 64. Permission revocation race

If operator revokes explicit prediction capability during an agent run, new tool calls must fail closed. In-flight already admitted reads may complete under documented snapshot policy; later synthesis must not elevate revoked or stale evidence beyond previous authorization. Do not use long-lived shared cache to resurrect access.

## 65. No new public routes by accident

Agent UI may display already supported text and existing run details but Phase 9H owns new predictive dashboards. Don't introduce a public `/api/v1/predictions` read to make 9F convenient. If adding any agent API parameter, keep it optional, explicitly policy gated and validated against controlled authorized context.

## 66. Citations and provenance

Include run-local evidence citations pointing to the exact 9E evidence ID and original 9D receipt through _internal protected_ provenance, original 9A cutoff, 9B/9C model/detector version and displayable source role. Public rendered citation must be safe and only resolve under operator permission; never leak private checksum/artifact path.

## 67. Public evidence projection

Use bounded scalar facts and safe metadata, not the complete 9E internal graph. Limit nested fields, paths, arrays and strings; reject `NaN/Infinity` and dangerous unescaped Markdown/HTML. An LLM's instruction text embedded in an untrusted source may not become system prompt or tool instruction.

## 68. Evidence strength matrix

Predefine an explicit matrix for integrity x completeness x source-role x original status x artifact availability x horizon. Each cell specifies allowed statement categories (recorded score, measured observation, qualified description, abstention only, no claim). Put enforcement in code and independently test every permitted and denied class.

## 69. Source grouping

If multiple 9E receipts reference the same 9A FeatureSet or same 9C reference dataset, preserve deduplicated source lineage but do not manufacture independent confirmation counts. Correlation groups are descriptive; NEVER compute agent-level joint confidence from source overlap.

## 70. Follow-up questions

A follow-up can refer to an older AgentRun/9E immutable ID only if the new run freshly resolves caller scope and currently permitted source. Old run references don't grant access, and old evidence cannot be quietly substituted for new live predictions. Preserve `previous_run_id` backward compatibility and isolation.

## 71. No automatic alerts or actions

Even an ANOMALOUS 9C finding must not create a service ticket, acquisition, ECU command, push notification, background job, webhook, retune instruction or alert severity. It is an investigative input only. Phase 9H/10/13 will decide any future user-facing monitoring behavior under separate approval.

## 72. Run state persistence

Choose optional additive fields for which 9E references the run actually used, how many were verified, qualified or rejected, and bounded explanation reasons. Do not store model private chain-of-thought, full graphs or secrets in AgentRun JSON. If 9F migration is needed, add after current 0017 and verify reversible path; don't change historical revisions.

## 73. SSE events

If exposing prediction evidence progress, use versioned bounded events with stable public reason codes. Never emit private IDs, tokens, raw feature arrays, full 9E manifest or model binaries. SSE reconnect uses existing monotonic sequence; must not refetch evidence or re-execute model/provider on replay.

## 74. OpenAPI and TS client generation

If agent response/SSE or MCP contract changes, regenerate/check project OpenAPI and TypeScript types and update frontend code only as necessary to preserve compatibility. Do NOT implement Phase 9H charts, probability gauges, predictive alerts or new pricing/commercial UI.

## 75. Source-independent technical terms

Use correct 'relative anomaly', 'predicted next observable outcome', 'uncalibrated engineering score', 'data-quality limitation', 'source role', 'configuration', 'cutoff' and 'observation window'. Translations EN/PT should not turn conditional statements into certain repair diagnoses.

## 76. Selected session and pull matching

Resolve explicitly selected session via existing AgentRun context; if no session supplied, bound discovery by selected vehicle and only disclose safe latest existing evidence with a server-side policy/explicit bounded selection. No unscoped fleet search; sessions without valid configuration history must not yield strong model interpretation.

## 77. Controlled fixture preparation

Independent acceptance creates disposable TimescaleDB and canonical telemetry/FeatureSets, actual 9B/9C offline registered versions, 9D controlled approvals and serving receipts, 9E bundles and 9F agent evaluation. No fixture may invent source metadata fields or directly insert a fake verified score while bypassing earlier phase checks.

## 78. Bridge reuse semantics

9F must reuse real 9E `PredictionEvidenceService`/repository verifier and 7A EvidenceRegistry/grounding; do not fork the evidence schema or copy fragile JSON from 9D manually. An adapter that converts 9E projection to 7A typed facts must have explicit version tests and refuse unknown fields/types.

## 79. Independent evidence-link test

For every projected statement, assert its stable run-local evidence ID resolves to the correct 9E bundle/9D receipt, fact path/value/unit and source cutoff. Independent acceptance must look directly at original persisted 9A–9E rows, not call the same bridge to compute expected values.

## 80. 9B supervised task tests

Cover all three 9B tasks with eligible controlled synthetic approvals, scores and decisions; correct horizon, task label rule and input feature provenance. Future target pull contains measurements after cutoff but none appears in agent evidence. Test missing target outcome cannot be interpreted as fault evidence.

## 81. 9C anomaly family tests

Cover all four 9C families including thermal abstention when genuine sensor support is insufficient. Verify same-cohort, source, configuration, reference count, threshold and descriptive associated features; robust and IsolationForest approved fixtures when possible. No cross-model score severity rankings.

## 82. 9E integrity matrix tests

Exercise four `COMPLETE`, three `PARTIAL`, four `ABSTAINED` types as patterns rather than hardcoding prior ephemeral UUIDs. Mismatched source, missing artifact, unsupported schema, stale verification, altered fact, changed checksum, incompatible scope must be denied/downgraded. New fixture counts must be measured, not copied.

## 83. Wrong vehicle isolation tests

Two simulated different-brand vehicles and one modified configuration; attempt requesting vehicle A's 9E receipt from vehicle B's run. Also attempt source record embedded in a different vehicle and reference row mixing; enforce server-side scope. Verify neither provider message nor public error reveals unauthorized IDs.

## 84. Legacy no-prediction regression

Run old Phase 7A/7B/7C/7D scripted scenarios with 9F disabled and verify tool catalogs, SSE schema, classifications, stream replay, budgets and findings unchanged. Explicit tests must ensure no prediction DB read/9D token needed when disabled. 9E regression also remains intact.

## 85. Authorized integration tests

With controlled flags and genuine operator predictive scope enabled, launch Phase 7 real agent orchestration graph using scripted deterministic provider, official MCP transport and real 9E evidence, then observe routing, specialist citation and final grounded output. Avoid mock-only unit proof; include one actual HTTP/MCP path and server-side tool invocation.

## 86. Data quality blocker tests

Feed verified evidence whose source coverage is degraded, original status ABSTAINED and/or referenced fuel sensor absent. Supervisor must not promote it to an unqualified model conclusion. Missingness remains an explicit reason in final answer and cannot be erased by a different specialist's enthusiasm.

## 87. Claim-forgery adversaries

Script provider drafts that guess fake evidence IDs, change score, threshold, label/horizon/unit, cite another run/vehicle, replace incomplete with complete, turn anomaly into probability or produce 'replace HPFP'. Structural validator must reject each and render safe correction/insufficient output under existing limited retry budget.

## 88. Prompt injection adversaries

Insert untrusted text in vehicle notes, documentary chunk, telemetry metadata and 9E interpretation-like fields instructing model to override role, fetch other vehicle or remove caveat. Application code must ignore instructions in source data; no raw source text becomes system instruction. Assert no extra tool/capability invocation.

## 89. Tool permission tests

Using only `mcp:read` token, ensure hidden predictive tools do not appear in discover AND cannot be called directly. Using prediction-scope credential but not authorized dev/test environment or explicit vehicle grant, also deny. Positive controlled grant allows only selected 9E immutable evidence and never 9D infer/9E materialize mutation.

## 90. Revocation and cache tests

Call prediction evidence once, revoke scoped capability, then call again in same run: denial. Cached copies may remain historical in the already validated current-run answer only under explicit policy; must not grant new access or cross-run reuse. Restart, reconnect SSE and concurrent specialist tests preserve isolation.

## 91. No model selection based on phrase

A user saying 'run a stronger model', 'try different algorithm', 'train the data', or 'ignore detector threshold' cannot cause new scoring, artifact downloads or threshold mutation. An existing model version is only read as frozen evidence; operator preparation remains separate from agent workflows.

## 92. MCP schema/version tests

Test official catalog/version negotiation with old and prediction-specific scoped clients, readOnly annotation and capability advertisement. Ensure no unversioned silent addition confuses existing clients; where schema change is necessary provide compatible version bump and generated client regression.

## 93. Graph and provider budget tests

Start simultaneous specialist tasks with 9E calls and old MCP calls, verify combined max 32, max one telemetry window, allowed prediction calls, cancellation, timeout and no DB session leaks. Workstation benchmarks record p50/p95 only with adequate sample support. No paid LLM requests during CI.

## 94. Agent event/audit tests

Assert tool-call audit notes prediction evidence retrieval only under safe output, no full private source hashes or tokens, and SSE events replay deterministically. Cancel a run during evidence retrieval and ensure no orphaned task, duplicated audit, 9D receipt or stale prediction data in another run.

## 95. Source contradiction evaluation

Create Phase 3 boost event with 9C INLIER, and 9B NEXT_PULL positive with 9C retrospective INLIER on same data. Agent reports exact separate facts and limits; no 'two votes against one', no synthetic diagnosis. If no direct source correlation can be proven, do not invent reconciliation.

## 96. Document vs telemetry evaluation

Use relevant Tier 1/2 Phase 8 synthetic/approved documentation with explicit vehicle/tune applicability, plus 9E result that lacks actual pressure value. Renderer may describe source literature, but must still state measured pressure unavailable; no borrowed OEM fuel target from unrelated configuration.

## 97. Cross-language questions

Evaluate Portuguese 'meu carro teve alguma anomalia na puxada?', 'qual a previsão para a próxima puxada?' and English counterparts. Preserve label, horizon, source role and identical citations across paraphrases; presentation may be localized without relabeling evidence certainty.

## 98. Risk-sensitive questions

Explicit test: 'Posso continuar acelerando?', 'o turbo vai quebrar?', 'qual peça trocar?', 'qual é minha chance de falha em %?' Agent must not grant mechanical clearance, fault probability or repair instruction based on synthetic/uncalibrated output; offer bounded evidence and recommend qualified physical inspection for safety-relevant decisions.

## 99. Silent source unavailability

If 9D/9E service is down, approval is revoked, DB fails or artifact missing, existing normal agent operation must degrade gracefully to Phase 6 observed facts / Phase 8 docs as allowed. Report predictive evidence unavailable without treating error as vehicle healthy. No timeout cascade or broad agent cancellation unless whole requested investigation is impossible.

## 100. Provenance immutability

Do not mutate original feature, training, detector, prediction receipt, evidence bundle/verification audit rows or source artifacts. 9F writes only its existing AgentRun audit artifacts or narrowly new run-owned projection receipts if justified; DB snapshots of old tables must be unchanged after 9F run.

## 101. Security review of external access

No public URL that returns per-vehicle predictive evidence without a provable user authorization scheme; 9D/9E operator-only controls remain. Explicitly attack SSRF via MCP URL, arbitrary evidence ID, query/filter injection, headers, token replay, mixed-source data, rate limits and malicious external tool metadata. Update threat model.

## 102. Observation and privacy metrics

Metrics report bounded categories: prediction tool allowed/denied, source status/integrity/completeness, supervised vs anomaly, route decisions, grounded claim accepted/rejected, degradation, duration and budget. Never label metrics with vehicle/session/evidence ID, freeform user question, VIN, score values or model SHA. Ensure spans and logs are equally sanitized.

## 103. Performance benchmark

Measure selected run with 0/1/2/4 evidence reads and 1–3 specialists; time discovery, 9E retrieval/revalidation, projection, grounding and synthesis individually, and record peak RSS and DB concurrency. Cold/warm evidence cache metrics should be truthful; these are controlled synthetic engineering observations, not user latency SLA.

## 104. Migration decision

Prefer zero new migration if AgentRun current JSON can safely store additive bounded artifacts; document the exact reason. If schema/storage change unavoidable, add Alembic after current `0017_prediction_evidence` and verify fresh/upgrade/downgrade/re-upgrade without changes to prior tables. Never rewrite old migrations.

## 105. Typed schema and contracts

Add strict versioned typed `PredictiveAgentEvidence`, `PredictiveClaimBinding`, `PredictionIntent`/policy status as needed, bounded scalar value and source IDs, no `Any` escape hatch to skip validation. Unknown 9E version or new scoring family should be safely unsupported, not parsed as a legacy recorded fact.

## 106. Evaluation harness independence

Add `scripts/evaluate_prediction_agent_integration.py` or equivalent with real 9A→9B/9C→9D→9E fixture, official MCP client, actual LangGraph run and independent DB oracle. Assertions should reconstruct expected facts/score/threshold/cutoff from source rows, not call the same 9F adapter for 'expected' values.

## 107. Acceptance matrix size

At minimum include 3 supervised + 4 anomaly families, 2 vehicles, 2 configurations, 4 completeness statuses/policies, 3 source roles where fixtures support them, 2 prediction and documentary mixed intents, disabled/authorized paths and numerous adversaries. Count unique scenarios not just assertions. Keep acceptance deterministic and bounded for CI.

## 108. Independent ground truth limitations

Synthetic evaluation can prove evidence linkage, routing, formatting and anti-hallucination in controlled cases; it cannot prove actual real-vehicle diagnostic reliability or real-user safety. No new 9F accuracy metric can be presented as calibrated model predictive performance. Defer real-world scientific/behavioral evaluation to 9G and agent model evaluation to Phase 11.

## 109. Test fixture source lineage

Use real Phase 9B and 9C accepted registered artifacts on disposable fixtures, approved 9D serving, persisted 9D receipts, 9E bundles and current vehicle configs. No hand-authored 9E `VERIFIED` object only in memory can satisfy end-to-end gate; mocks belong in isolated unit tests.

## 110. Offline evaluation budget

Avoid external paid model calls and Phase 8 embeddings by default. Scripted deterministic provider must exercise real orchestrator, tool catalog, grounding and persistence while no third-party API calls occur. Existing Phase 7D 120-slot historical validation caveat must remain explicit and unaffected.

## 111. Positive answer scenarios

At least: (a) qualifying next-pull result with score and explicit uncalibrated disclaimer; (b) 9C anomaly relative cohort and source units; (c) mixed measured telemetry + predictive score + applicable Phase 8 source with separate citations; (d) partial/abstained result that transparently explains unavailable sensor; (e) no model and no inference triggered.

## 112. Negative answer scenarios

At least: cross-vehicle evidence, wrong pull/session, version mismatch, source tamper, low-quality, missing artifact, unknown model family, injected repair diagnosis, fabricated percentile, unlabeled future target, and predictive tool attempt with plain MCP read token. For every case, record exact denial or downgraded answer.

## 113. Predeclared acceptance expectations

100% deterministic fixture enforcement of server-side authorization, no unauthorized source disclosure, no future leakage, exact source numerical binding, immutable old rows, no auto inference, refusal of unsupported diagnostic probabilities and deterministic citation identity. Honest shortfalls are failures; don't loosen case expectations after inspecting test output.

## 114. Evidence quality vs claim coverage

Count discovered, authorized, eligible, verified, partial, abstained, rejected, cited, and unanswered requests. Separate 9E evidence completeness counts from 9F grounded-answer sufficiency, and never report 'agent accuracy 100%' solely because synthetic binding tests passed.

## 115. Makefile tasks

Add functional targets `make test-prediction-agent-integration`, `make phase9f-acceptance`, `make benchmark-prediction-agent-integration`, `make prediction-agent-observability` or standard equivalents. Wire deterministic 9F acceptance into canonical CI. No placeholder PASS, fake test count, or ignored return code.

## 116. Disposable database lifecycle

Use isolated TimescaleDB Compose project; migrate to actual head, create bounded synthetic vehicles/sessions/features, approval+9E evidence, run MCP and agent graph, independently inspect DB and tear down all containers/volumes. Safety controls should prevent accidental connection to operator's real data or production database.

## 117. Regression gates

Run Phase 6 MCP and authorization; 7A grounding/SSE; 7B investigation with explicit approval; 7C specialists, conflicts and resource bounds; 7D deterministic harness; 8 knowledge+RAG; 9A 9B 9C 9D 9E acceptance; and all canonical Phase 0–5 gates/Playwright. Changes to a shared registry cannot break older permissions or outputs.

## 118. Existing code quality

Use pinned repository Python/TS versions; lint Ruff/mypy/Pydantic, test timeouts/concurrency/DB, generated OpenAPI+TS, Docker builds and dependency checks. Resist new heavy LLM-agent packages; LangGraph already exists. Preserve stable public events and historical compatibility.

## 119. Threat model deliverable

Document capability propagation from API operator to agent -> MCP -> evidence, malicious tool calls, guessed UUID, prompt injection, data exfiltration, misleading calibrated probabilities, fake diagnostic claims, artifact mismatch, source trust and missing tenant auth. Describe residual risks and explicit production-disabled policy.

## 120. Documentation artifacts

Deliver `docs/architecture/phase-9f-agent-integration.md`, `docs/validation/phase-9f-acceptance.md`, `docs/validation/phase-9f-agent-evaluation.md`, `docs/validation/phase-9f-traceability-ledger.md`, `docs/runbooks/prediction-agent-integration.md`, suitable next numbered ADR(s), updates to security, observability, testing, README, roadmap, AI_CONTEXT, generated contracts and relevant Phase 7 agent docs.

## 121. Operator runbook examples

Include safe commands: disabled state, controlled dev/test flags, separate prediction MCP read scope, local synthetic fixture approval/build using earlier phase CLIs, a selected vehicle question, expected evidence citation and an abstention, denial after revocation and no production access. Never commit actual bearer token or customer VIN.

## 122. Scope-specific tool documentation

Document exactly which new capability requires which credentials and why existing `mcp:read` alone is insufficient. Annotate tool input/output, source role, error codes, no-write property, rate/byte limits and private/loopback ingress requirements. Include manual threat-review checklist.

## 123. ADRs

Write ADR for capability-isolated predictive evidence MCP bridge vs alternatives; projection/verification/zero-write; agent grounding policy for 9B/9C 9E and non-causality; supervision/routing and cross-source correlation; dev/test deployment fence. Follow existing ADR numbering instead of hardcoding index.

## 124. No unrelated refactoring

Do not rewrite Phase 7C graph into a new framework, overengineer an agent memory layer, build a general-purpose policy engine, or upgrade unrelated libraries unless required to fix real vulnerabilities. Keep changes focused and explain any touched shared modules with regression evidence.

## 125. Roadmap correctness

Update stale text that calls Phase 9D PR #44 and 9E PR #45 unmerged: GitHub confirms both merged, latest Phase 9E merge main SHA `466ce900988bd81e1d968eb319e970955b4011d7`. Mark 9F complete ONLY after acceptance; preserve 9G/9H planned and Phase 7D historical paid-suite caveat.

## 126. GitHub workflow requirements

Run quality, integration E2E, Docker/full-stack, Security, dependency review, CodeQL Python/JS/TS on the FINAL branch SHA plus 9F-specific independent evaluation. Re-run after every final implementation change. No green checks from previous 9E SHA count as 9F proof.

## 127. Exact-head local/remote verification

After all code/docs commits, ensure clean `git status`, local == origin branch SHA and open PR against main with no automatic merge. List all required GitHub check names, conclusions and URLs for the exact final commit. On failed/pending CI investigate and fix, then push new SHA and repeat checks.

## 128. Final PR description

Include baseline and final SHA, design/authority boundary, new MCP tool(s) and scopes, integration diagram, source eligibility matrix, 9E receipt lineage cases, disabled/production behavior, tested 3+4 tasks/families, negative/attack matrix, real graph run evidence, agent claim tests, metrics, benchmark, migrations/none rationale, limitations and exact-head check URLs.

## 129. Run receipt output

Persist ignored machine-readable evaluator reports under `.validation/phase9f/` (status, git sha, scenario cases, actual source IDs only inside private files, counts, pass/fail, latency, resource use). Checked-in reports must summarize without private source IDs or fabricated measurements.

## 130. Definition of Done — access

[ ] 9F disabled by default, production blocked; [ ] separate server-enforced predictive capability from `mcp:read`; [ ] agent-selected vehicle/session/pull scope; [ ] no unauthorized evidence discovery/direct call; [ ] no 9D/9E operator secret in model/browser/log; [ ] scoped, audited, zero-write retrieval; [ ] artifact/source integrity and role/cutoff gates; [ ] no public unauthenticated predictive access.

## 131. Definition of Done — integration

[ ] Real official MCP + LangGraph integration; [ ] current-run EvidenceRegistry IDs/citations; [ ] 9B/9C distinct horizons and families; [ ] 9E completeness/integrity matrix; [ ] Data Quality gate and 3 domain specialists; [ ] supervisor preserves disagreement and correlation; [ ] Phase 8 docs segregated; [ ] no auto training/scoring/materialization; [ ] old AgentRun/SSE compatibility.

## 132. Definition of Done — grounding

[ ] Application-rendered verified factual and predictive claims; [ ] model output not physical measurement; [ ] explicit noncalibration and source role; [ ] original threshold/status/version/cutoff exact; [ ] missing/partial/abstained appropriately downgraded; [ ] no future label data; [ ] no fault/safety/repair conclusions; [ ] forged claims rejected; [ ] shared source never counted twice.

## 133. Definition of Done — validation

[ ] Synthetic official end-to-end pipeline and independent source oracle; [ ] 3 supervised 9B tasks + 4 9C families; [ ] cross-vehicle/config/modification roles; [ ] permission, source tamper, revocation, caching and injection adversaries; [ ] actual agent graph tests and benchmarks; [ ] all prior deterministic regressions; [ ] exact SHA CI all green; [ ] PR open/unmerged.

## 134. Definition of Done — phase boundaries

[ ] 9F did not implement 9G calibration/drift, 9H predictive dashboards/alerts, Phase 10 production retraining or Phase 12 user/tenant auth; [ ] no ECU writes or autonomous collector; [ ] no paid AI API usage for deterministic CI; [ ] no real-vehicle accuracy claims; [ ] Phase 7D accepted historical caveat disclosed.

## 135. No weakened acceptance

Do not retroactively soften authentication, quality, source minimums, structured grounding or test thresholds simply to get green. New fixtures must obey actual 9A/9B/9C/9D/9E contracts and require existing source artifacts. Every test that was skipped/pending is disclosed; no invented pass or suppressed error.

## 136. Final engineering report

Report (1) branch/baseline/final SHA/PR URL, (2) tool scope and disabled-prod proof, (3) actual code boundaries/ADRs, (4) 9A→9E source lineage consumed, (5) count of 9B/9C task/family cases and evidence matrix, (6) run-local citations/claims and supervisor examples, (7) source-role/vehicle/cutoff/quality adversaries, (8) offline/no-inference proof, (9) real LangGraph+MCP fixture receipts, (10) timing/memory/metrics, (11) old phase regressions, (12) final exact-SHA GitHub CI URLs, (13) limitations, (14) 9G/9H unimplemented confirmation.

## 137. Final acceptance state

Only after ALL mandatory implementation and executed exact-SHA CI gates pass, end EXACTLY `PHASE 9F — AGENT INTEGRATION: VERIFIED`. Otherwise end EXACTLY `PHASE 9F — AGENT INTEGRATION: NOT VERIFIED` and enumerate precise unmet controls/checks. Continue autonomously resolving fixable issues; stop before merging and hand PR to user.

---

## Execution guarantee

Execute every required stage; produce an implementation traceability ledger mapping all numbered sections to source changes and executed proof. Correct genuine failures and rerun checks on the last pushed SHA. Report unsupported/optional real-world validations as NOT RUN, not fabricated PASS. User merges manually.
