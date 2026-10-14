# Phase 7D real-model validation

Status: round fifteen remains NOT VERIFIED after resume. Its 120 slots contain 93 PASS, ten semantic, nine runtime and six provider failures, one interrupted marker and one budget-skipped observation. The unchanged USD 4 ceiling blocked further funding at USD 3.996470140. Strict routing and reported-role recall pass; designated escalation is 91.67%, below 95%. All thirteen canonical checks passed on evaluated source 52f8267423697a9e0894f06a0afdbafe65951326. The authoritative scope is
[the complete execution specification](../prompts/phase-7d-real-model-validation.md).
[ADR 0022](../adr/0022-bounded-real-model-evaluation.md) records evaluation ownership and accounting.

The current `evals/phase7d/suite-v2.json` and retained historical `suite-v1.json` each contain exactly 80 unique questions, ten per category A–H.
The specified 20 critical questions receive two additional observations. The loader rejects
identity, category, duplicate-question, specialist-partition and repeat-count inconsistencies.
Questions and expected behavior come from the specification and controlled canonical fixtures,
not model-generated answers. Dataset changes require a new version and renewed review.

`scripts/phase7d_eval.py` owns explicit paid execution. It exercises production API routes via
ASGI HTTP, a separate actual HTTP MCP server, disposable PostgreSQL persistence, the existing
LangGraph supervisor and the existing Phase 7B service. Controlled recordings use canonical
import, pull analytics and event analysis. Replay capabilities come from actual CSV content.
The evaluator never approves a recipe or starts acquisition. Domain fingerprints detect changes
to canonical vehicle data after evaluation. Provider output is graded independently of production
validators using numeric/unit bindings, evidence ownership, routes, gaps, capabilities and audits.

The existing `OpenAIProvider` sends explicit service tier/reasoning settings and `store=false`.
Its SDK retries remain disabled. Optional internal receipts measure routing, specialists,
synthesis and investigation calls, including usage from malformed structured output. Public API
and SSE event sequencing remains unchanged. Supervisor report metadata version 1.1 records the actual v3 prompt; report 1.0 and prompt v1/v2 remain readable. Reasoning token counts are usage metadata only; reasoning
content is neither requested nor stored.

The checkpoint reserves estimated cost before each network call. Completed response usage
replaces the reservation. Timeouts, transport failures, missing usage and interruptions retain a
conservative bound. An exclusive file lock serializes operator invocations. Completed paid cases
are not rerun on resume; interrupted cases remain explicitly incomplete. SHA, dataset hash, prompt
versions, SDK, model, tier, reasoning and limits must match. Confirmation is limited to a second
suite and shares accumulated spend. See the runbook for crash and provider-blocker handling.

The output report includes category/role usage, costs, routing/recall, tool efficiency, grounding,
causal/diagnostic restraint, missing evidence, Phase 7B escalation, stability, latency quantiles,
provider failures and a maximum twenty-slot human-review shortlist. Missing observations produce
null metrics and NOT VERIFIED. Real-evaluation success is separate from final repository/remote
acceptance. Production profile calibration remains pending real observations.

Phase 8 owns documentary gaps and retrieval. Phase 7D adds no RAG, vehicle control or ECU writes.

## Hardening from partial real observations

Role policies v2 separate the delegated objective from the parent question and keep factual measurements alongside unresolved causes. The recorded-quality gate remains application-owned: poor, absent or truncated quality and failed/timed-out quality roles block interpretation; an unsupported model data_quality category cannot contradict verified reliable metadata. Other uncertainty remains visible.

The evaluation uses a bounded 45-second specialist profile (application default 25), 60-second provider timeout, 180-second run timeout and 230-second case timeout. One local read-only public-stream reconnect targets the same persisted run; it never creates another paid run. Provider infrastructure retry remains capped at one.

Two automatic schedules remain the default maximum. A separately confirmed operator exception permits each additional bounded schedule and records every opt-in in the ledger, with all spending shared. The exception is not invoked automatically.

The report includes exact Decimal cost and token aggregation per case key across all paid rounds and smoke, retaining unknown-usage reservations. Aggregation scope fields distinguish current-round quality/category metrics from cumulative usage and spend. Historical raw results are not regraded or replaced by these reporting fields.

Operator authorization on 2026-10-12 permits the additional rounds needed to finish validation while retaining a strict accumulated USD 2 ceiling. The default two-round limit remains for callers without explicit operator confirmation. Each invocation is bounded; no automatic evaluate/tune loop or model/tier fallback is added. Resume omits round-start flags and preserves all prior observations and cost reservations.

## Strict outputs and affected-case verification

Completed round-three receipts exposed invalid specialist/investigation output and routing precedence errors. Draft and investigation outputs now use the pinned OpenAI SDK strict-schema normalizer. Nullable fields remain required and nullable; completed usage is recorded before application parsing. Exact units, values, identity, evidence ownership, temporal context and semantic proposal validation remain enforced. Known unsafe intent constrains the typed draft to an explicit fixed refusal with no fact bindings.

The compact specialist wire payload keeps the entire resolved context and every supplied evidence fact while omitting the duplicate context and question inside the scope object. Identity, budget, allowlist, evidence/session IDs and the untrusted-data boundary remain present. Free projection samples use that same payload and normalized draft schema; per-call reservations retain their stricter bound.

Repeated `--case-id` flags select an explicit affected-case schedule from the immutable suite. Selected critical cases retain both repeats. The selection is recorded in the committed evaluation identity and cost projection, and cannot change on resume. Partial validation never satisfies full-suite acceptance. A later full candidate suite remains required.

Explicit paid resume may retry only NOT_RUN_EXTERNAL_BLOCKER markers with no call receipts. Prior markers remain audited. Completed, failed, interrupted and budget-skipped paid observations remain preserved and are not automatically replayed. New prompt metadata and old snapshot deserialization are covered by contract tests; historical/new report variants render in the same web component. Durable event IDs, sequence and idempotent replay are covered by the existing regression gates.

Cost projection keeps the original two-turn-per-role assumption until a prior full 120-observation schedule has actually been attempted. It can then use the rounded-up median number of recorded turns per role from that complete schedule, with one extra agent turn per case as a contingency. Partial schedules do not recalibrate this estimate. Free samples measure the current prompt payload, no caching discount is assumed, and pre-network reservations still enforce the hard cumulative limit independently of the likely-cost forecast.

## Registered pull discovery and routing context

Round-four Performance called a comparison before any owned pull IDs had been discovered. The registered-ID check correctly rejected that request. Performance now discovers up to twenty pulls for each of at most two already resolved sessions before its first model turn, unless owned list evidence already exists. Discovery uses the existing allowlist, tool lock/cache, audit events, specialist MCP budget, global MCP/evidence/input budgets and specialist deadline. Failures remain isolated to that role; failed quality gates still prevent domain dispatch. Foreign or invented IDs remain rejected. Performance policy v4 and discovery strategy 1.0 are included in the configuration hash. No comparison result is synthesized by this discovery step.

Synthesis now receives the supervisor report even when no domain specialist is selected. This preserves typed unsafe/factual/quality intent and completed quality findings; the strict explicit-refusal schema can therefore apply to zero-specialist unsafe requests. It adds no model turn or tool permission.

Blocked-quality synthesis retains validated capability facts and quality-event metadata (event type, signal, severity and duration), while excluding vehicle measurements, associations and hypotheses. Its confidence remains low, missing-quality categories stay explicit, and domain interpretation stays blocked. This preserves an observed dropout/stuck signal without treating poor telemetry as reliable performance evidence.

Preflight separately measures parent payloads with no domain/quality dispatch instead of charging them for the largest multi-specialist synthesis payload. It also samples the actual public investigation input through the deterministic proposal provider, so missing investigation samples do not default to an unrelated larger prompt. Domain and unsampled-role fallbacks remain conservative, topology/contingency/output assumptions are retained, and the accumulated/per-call USD 2 guard is unchanged.

Free cost preflight now executes every selected unique suite question through the deterministic production graph. Samples are tagged by immutable case ID and use that question's largest observed payload for each role. The extra parent-turn contingency uses the same question's parent sample; unseen roles retain the largest role/global fallback. Full acceptance forecasts sample all 80 unique questions and account for the 40 repeated calls; sparse-history cases use their actual sparse fixture vehicle. Output, topology, caching and hard-budget assumptions are unchanged. Deterministic sampling is cost evidence only, never real-model quality evidence.

An explicitly operator-authorized `--operator-budget-progress` attempt may start with a conservative full-cost projection above remaining funds. It keeps the forecast visible and permits only calls admitted by the existing hard per-call ledger checks. Default projected-cost rejection remains. The opt-in is part of resume identity; budget-skipped observations cannot satisfy full acceptance. The current operator authorization is to continue within USD 2, with no increased ceiling or fallback tier/model.

## Related-domain routing and deterministic selection correction

Round-nine routing restricted linked performance/thermal/fuel observations to a single domain before the typed model could select other relevant specialists. Coordinated changes, contrasting measurements, mechanism comparisons and torque intervention now retain the relevant candidates. Narrow named-mechanism questions and factual metadata remain scoped. General positive/negative tests use new wording; no evaluation phrase or case identifier is matched. Existing fixed caps, safety precedence and evidence quality gate still apply. This routing change requires real affected-case evaluation and full final-candidate acceptance.

Application-owned pull discovery also exposed a deterministic-provider regression: overlapping list evidence contains distinct evidence IDs for the same pull entity. The provider now deduplicates selected entity IDs, limits repeated-pull analysis to the requested session, consumes already owned list metadata and deduplicates configuration-comparison groups. Foreign-session metadata does not satisfy current-session discovery. This changes deterministic test selection, not real-provider answers or dataset expectations.

## Quality, source capability and comparison metadata scope

Real related-domain validation exposed remaining routing requests for signal reliability and source availability. Reliability interpretation, missing samples and abrupt sensor-zero questions now retain Data Quality scope; source capability lookup and simple recorded counts remain factual. Forced unbounded specialist agreement is rejected by the existing application refusal boundary. Mechanical reliability without a data-quality request retains domain analysis. No specialist recursion, new model, public schema or future infrastructure is introduced.

Discovery strategy 1.1 keeps the existing maximum two owned session reads and twenty pulls per read. For questions about configuration/modification/replacement comparisons, it selects the newest session and an already resolved, temporally valid session from a different configuration when available. Otherwise it retains the newest two sessions. Selection filters the specialist session allowlist; an unowned or invalid temporal contrast never supplies registered IDs. The updated strategy version participates in the supervisor configuration hash. No result, diagnosis, missing measurement or answer is synthesized by metadata discovery.

## Scoped tools, terminal drafts and optional capture planning

ADR 0025 records per-turn entity-ID schemas, the reserved terminal draft, safe Data Quality summary reads, explicit zero-call quality-blocked role records and independent recognition of canonical numerical semantics. Suite v2 preserves the complete question/fixture/repeat set, aligns optional G09 planning with specification section 82, and strengthens public capture-approval notice checks. Historical receipts remain unchanged. No budget, retry or interpretation guard is expanded.
