# Phase 9H — Predictive Intelligence UI

**Repository:** Brunobosso98/Vehicle-Intelligence-Platform
**Existing branch:** `codex/phase-9h-predictive-intelligence-ui`
**Verified starting baseline:** `2249930642d8f854649913c9c3145e6e5ffea498` (main after Phase 9G PR #55 merged on 2026-10-30)
**Purpose:** Build the final Phase 9 frontend with real, source-exact 9B–9G history/evidence/science, dev/test-only operator authorization and polished, accessible responsive UX.
**Boundary:** This is engineering visualization over protected historical receipts. It is NOT production diagnosis, real-world calibration, autonomous prediction, public customer access, MLOps or ECU control.

This file is the COMPLETE authoritative implementation, security, visual quality, acceptance and delivery contract. Read ALL numbered requirements BEFORE implementing. Resolve filename examples against actual repository and AGENTS.md; do not assume an endpoint exists just because a suggested name appears.

## Current repo reality (must confirm)

- apps/web uses Next.js 16 App Router, React 19, strict TypeScript, generated OpenAPI types from packages/contracts, existing dark styling and SVG charts.
- Existing selected-vehicle UI is VehicleWorkspace, with TelemetryDashboard, AnalyticsWorkspace, AgentWorkspace, KnowledgeWorkspace and LiveAcquisition.
- Existing generic `/api/domain/[...path]` proxy is NOT an authentication/authorization boundary for PredictionService.
- 9D is disabled by default, dev/test only, with trusted-peer and operator bearer; 9E adds safe verifiable evidence projections, 9F has separately gated agent evidence.
- 9G `phase9g-protocol-v2` is offline scientific evaluation: synthetic-label calibration only; real-world predictive validity `NOT_ESTABLISHED`.
- The Phase 9G security report contains time-bounded High-severity exceptions expiring 2026-11-01 and 2026-11-02. Revisit these before final 9H verification.

## Non-negotiable information flow

```text
Persisted canonical 9A observations + historical pull/session/config
   |
9B NEXT_PULL classifiers   +   9C AFTER_PULL_OFFLINE anomaly detectors
   |
9D dev/test operator-approved immutable prediction receipts
   |
9E provenance-verified safe evidence projections
   |                                9G sanitized OFFLINE research summaries
   v                                             |
9H SERVER-ONLY controlled operator BFF  <--------+
   |  explicit browser session, private backend, exact vehicle/source scope
   v
Protected Next.js responsive Predictive Intelligence workspace
   overview | pull history | model result | anomaly | evidence | science
   |
Optional LINK to already recorded 9F grounded AgentRun, not auto execution
NO public access, no on-demand model training/scoring, no source mutation.
```

**Scientific status:** Engineering UI may be VERIFIED even though real-vehicle diagnostic/calibration readiness is NOT_ESTABLISHED. That limitation must remain prominent in all relevant panels.
**Git discipline:** Work on EXISTING branch, commit/push, open PR targeting main, DO NOT MERGE.

---

## 1. Mission and user value

Build a complete, polished, responsive Predictive Intelligence UI integrated into the EXISTING Next.js Vehicle Intelligence Platform, allowing a permitted controlled operator to explore previously recorded Phase 9D prediction receipts, Phase 9E verifiable evidence, Phase 9F contextual agent findings, and appropriately scoped Phase 9G OFFLINE scientific evaluation summaries. Make correct interpretation, source authenticity, data quality and limitations evident. Deliver functioning routes, components, typed data adapters and tested interactions, not a design mockup.

## 2. Exact Git baseline

Repository: Brunobosso98/Vehicle-Intelligence-Platform. REQUIRED EXISTING branch: codex/phase-9h-predictive-intelligence-ui. Branch-created main baseline SHA: 2249930642d8f854649913c9c3145e6e5ffea498, which MERGED Phase 9G PR #55. Fetch origin, inspect clean status/remotes/upstream, verify baseline ancestor and branch; never recreate branch, force-push, rewrite history, commit to main, or merge the PR.

## 3. Read the full contract

Read every numbered section of this document before editing implementation. Check root AGENTS.md and all nested ones, particularly apps/web/AGENTS.md: App Router, strict TS, Server Components by default, generated contracts, no client secrets, accessible loading/errors/retry and make check-web. Inspect project Makefile, existing web/browser tests, API security, complete 9A–9G documentation, architecture, ADRs, test conventions and CI receipts.

## 4. Actual frontend foundation

Existing apps/web/src/app/page.tsx currently shows an older PHASE 5 landing page, VehicleWorkspace, TelemetryDashboard, AnalyticsWorkspace, AgentWorkspace and KnowledgeWorkspace; styles are in globals.css and existing UI uses hand-authored responsive SVG for telemetry. Preserve these functional workflows and enhance navigation/cohesion rather than replacing the app with an unconnected dashboard, arbitrary new framework or static screenshot.

## 5. Actual browser proxy boundary

The current apps/web/src/app/api/domain/[...path]/route.ts forwards arbitrary domain paths to /api/v1 and may forward an inbound Authorization header; it is NOT a prediction-specific login or tenant authorization boundary. Do not add the 9H UI by exposing 9D/9E operator bearer through this generic proxy. Explicitly verify that protected 9H data cannot be obtained via a generic domain proxy path, including direct-call attempts.

## 6. Backend existing prediction boundary

9D uses /api/v1/prediction-service with PredictionRequestBudgetMiddleware: disabled by default, development/test only, trusted source peer IP, server-side high-entropy operator bearer, request budgets and timeouts. It offers /versions, POST /next-pull, POST /anomalies, GET /runs/{receipt_id}. 9E adds protected materialization/verification and GET evidence safe-projection routes. All new access MUST preserve or strengthen those controls.

## 7. No user/tenant auth has been proved

The platform has not implemented production-grade account identity or per-owner vehicle authorization. Merely choosing a vehicle_id in VehicleWorkspace, running the Next.js process on localhost, providing a client-side flag or checking an Origin header DOES NOT grant data access. No 9H route may make 9D/9E results available to arbitrary browser visitors or production accounts. Fail closed, and implement controlled internal operator access only.

## 8. Two permitted experience modes

A) Controlled operator mode: only development/test, explicit browser/operator authorization, strict server-side scope and real persisted 9D/9E evidence. B) Clearly labeled synthetic demonstration mode using non-sensitive, versioned fixtures that never invoke private prediction endpoints and cannot be confused with current live vehicle diagnostics. Mode boundaries must be obvious; no silent fallback from real missing results to demo synthetic data.

## 9. No feature creep

9H is a READ-ONLY visualization/exploration layer, not model training, on-demand scoring, 9E materialization, evidence re-verification writes, 9F agent execution, 9G calibration promotion, Phase 10 MLOps, Phase 11 agent eval, Phase 12 production identity/cloud or ECU/tuner controls. Existing agent workspace can be linked for context but 9H must not trigger a new agent call without separate explicit user action via preexisting authorized flow.

## 10. Scientific non-negotiables

9B supervised NEXT_PULL engineering scores are NOT real mechanical-failure probabilities. 9C AFTER_PULL_OFFLINE anomaly outputs are NOT probabilities, severity, proof of a damaged part or future predictions. 9G calibration is synthetic research only; real-world predictive validity and calibration remain NOT_ESTABLISHED, and production use is prohibited. UI MUST explicitly display these meanings on cards, charts, tooltips, accessible descriptions and exports.

## 11. Overall information architecture

Define a cohesive dashboard route/section for the existing selected vehicle: Overview, Pull History, Predictions, Anomalies, Evidence Detail, Scientific Reliability and Agent Context. Prefer meaningful subroutes with share-safe URL state and server-driven protected data; a compact tabbed workspace is acceptable if it provides deep links, keyboard navigation and stable browser history. No new public vehicle/fleet directory.

## 12. Visual design principles

Build a thoughtful automotive engineering product aesthetic that extends existing charcoal/dark theme (#101416, #192024, teal highlight) with restrained contrast, clear typography, sparing iconography, precise data labels, generous spacing and coherent responsive grid. Avoid a 'spacecraft HUD' caricature, neon overload, glossy gauges that falsely imply certainty, fake machine-learning pictures or stock imagery. Trust and clarity beat decorative dashboards.

## 13. Multicar not N55-only

Maintain the original N55 brand/history if desired but the platform must display and analyze supported vehicles from any make based on canonical telemetry. Labels never presume all cars have BMW-specific sensors or Stage 2 configuration. Use source-controlled vehicle name and effective configuration; if missing, show unknown, not BMW/N55 inferred defaults.

## 14. Primary personas and journeys

Persona 1: operator reviewing existing imported telemetry and correctly seeing prediction unavailable. Persona 2: engineer investigating a synthetic fixture's 9C anomaly with exact source/threshold/quality. Persona 3: operator comparing 9B next-pull outcomes and 9G research applicability. Persona 4: reviewer inspecting a verified 9E evidence chain and a related 9F agent run. Persona 5: narrow/mobile user needing keyboard and screen-reader supported workflows.

## 15. Mandatory complete UX states

Every panel needs loading, authorized-empty, no registered model, no prediction recorded, abstained, partial evidence, source mismatch, unsupported schema, science-unavailable, forbidden, disabled, timed-out, network failure, retry and explicitly synthetic demo. Distinguish no evidence from normal/healthy vehicle and from access denied. Avoid generic error states that look like 0 anomalies.

## 16. Success is falsifiable

A full-stack controlled test proves a real authorized browser can choose a fixture vehicle, see real persisted 9D receipts and 9E safe projections with exact source fields, inspect statuses/limits/cutoffs, use interactive but bounded charts, switch vehicle without leaks and leave the environment with unchanged prediction/evidence/evaluation source tables. The public/unauthorized browser sees no private predictive data or metadata.

## 17. Backend ownership and contract inspection

Inspect exact Pydantic 9D PredictionResponse, 9E PredictionEvidenceProjection, 9F AgentRun/grounding refs, 9G EvaluationRun/ApplicabilityAssessment, 9A FeatureSet/Telemetry and original pull/session data; map fields and version identifiers into generated TS types. Do not invent a GET endpoint, evidence field, probability or model explanation because a UI mock needs it.

## 18. Server-only BFF proposal

Prefer a narrow Next.js server-only Backend-for-Frontend over uncontrolled direct browser-to-9D calls. Server must resolve verified controlled-operator session and vehicle grant, then invoke the existing 9D/9E protected service with a server-only bearer and fixed allowed paths/verbs. Never expose bearer to client JavaScript, serialized props, logs, HTML, preload, hydration, source maps or browser network responses.

## 19. Operator login strategy

Implement a minimal dedicated DEVELOPMENT/TEST-ONLY operator login/session if the repo lacks one. Require a high-entropy separately configured browser/operator credential or equivalent trustworthy operator identity; rate-limit credential attempts, use constant-time verification and secure secret storage. Do NOT reuse frontend status/API_BASE_URL, unrestricted existing app access, acquisition token or MCP read credential as browser prediction authorization.

## 20. Session cookie hardening

After verified local operator grant, use HttpOnly, SameSite=Strict, Path-scoped, short-lived, cryptographically MACed opaque cookie (or a safer comparable server-side session); set Secure when HTTPS, do not depend on unsecured cross-site cookies. Login/logout, expiration, rotation, replay, tampering and dev-test-only fence must be tested. Production must not accept the operator login even with demo environment variables.

## 21. CSRF and same-origin policy

Protect all stateful auth entry/logout and any optional POST BFF calls with Origin/Referer checks and an explicit CSRF strategy. All operational prediction/evidence reads should be GET with no side effects; do not allow public cross-site resource requests. Configure Cache-Control: no-store for auth and private responses; never embed secrets in URLs or localStorage.

## 22. Server peer/network enforcement

A Next.js backend fetch to the prediction API must originate within the backend trusted network, not by blindly trusting X-Forwarded-For or user-supplied IP. Prevent attacker-selected backend URL, SSRF, host/port/path injection and external redirect following. Any reverse proxy/trusted network change must be reflected in threat model and actual Docker/browser test.

## 23. Fail-closed enablement

Introduce independently validated 9H_PREDICTIVE_UI_ENABLED=false default and controlled operator mode settings, with ENVIRONMENT=development/test and existing 9D enablement and operator credential required. In production, neither BFF nor its private routes may return predicted outputs even if a cookie and feature flags are forged. Existing public landing and non-predictive pages must remain stable.

## 24. Allowlisted BFF routes

Expose only specific safe read operations, e.g. /api/predictive/availability, /api/predictive/vehicles/{id}/receipts (bounded), /api/predictive/receipts/{id}, /api/predictive/evidence/{id}, /api/predictive/evaluation/summaries (sanitized), as repo conventions allow. DO NOT forward arbitrary subpaths/methods or raw user Authorization headers to /api/v1/prediction-service. Read-only scoped route handlers enforce auth before DB/backends.

## 25. Vehicle IDOR prevention

Server-side verify the selected vehicle is within the controlled operator grant/scope; do not treat an ID returned from unprotected /api/domain/vehicles as proof of ownership. Every receipt and nested 9E evidence source must bind to the same authorized vehicle/config/pull before projection. Guessed UUIDs, direct deep links and stale cross-vehicle cache access return a nondisclosing forbidden/not-found result.

## 26. Limited operator scope semantics

Since no general user ownership system exists, a permitted controlled engineering operator may be allowed an explicitly configured fixture dataset, vehicle whitelist or private test environment; document that this does not constitute per-owner tenancy. Never claim SaaS production authorization. If a proper server-side scope cannot be established, restrict 9H to synthetic public demo mode and leave protected real-source views disabled.

## 27. No browser bearer forwarding

Do not place a 9D high-entropy bearer in a React state, prompt field, query string, DOM attribute, public environment variable, fetch request to /api/domain, generated frontend API type default, API examples sent to browser or encoded URL. The 9H BFF injects it only on server-to-server calls after independent browser identity and source-scoping checks.

## 28. Refuse generic proxy bypass

Audit direct calls via /api/domain/prediction-service/*, encoded/slash-normalized variants, repeated segment, query encoding and mixed-case paths; reject those from browser regardless of client-provided Authorization. Preserve legacy domain routes and legitimate MCP/agent infrastructure; secure the proxy with route allowlist/negative guard rather than breaking all existing features.

## 29. No arbitrary server fetch

Hard-code operator server endpoints to trusted API_BASE_URL and fixed read-only path builder, validate UUIDs/schema/limit/offset and permitted enum strings; disable redirects or verify exact target origin. Never accept an arbitrary target URL, open redirect, remote artifact URL or backend query language from 9H browser input.

## 30. Authentication before revealing availability

Even GET /api/predictive/availability must avoid listing private model counts, vehicle IDs and whether a guessed receipt exists to unauthenticated visitors. It may report generic 'not available' with no sensitive metadata. All restricted routes check identity and environment before contacting backend or selecting a data source.

## 31. Query budgets and response caps

Enforce max 4 KiB request bodies or tighter as applicable, strict query schema, max page size (e.g. 20), max history/receipts per vehicle, max chart sample count (e.g. <=500), concurrency per operator, rate limit and 8-10 second cancellation timeout in the BFF. Coordinate with 9D existing rate budgets; don't create an unbounded polling DDoS.

## 32. Abort and cancellation

On user navigation, vehicle change, retry or BFF abort, cancel underlying fetches, release concurrency permits and discard stale response. Use Request.signal, AbortController and sequence-generation guards as appropriate. No background open-ended prediction polling, silent retry storms or incomplete stream left after unmount.

## 33. Private cache policy

Server-side private prediction/evidence responses are no-store and not stored in shared Next.js cache, CDN, service worker or static build. Client in-memory cache must be keyed by controlled session, selected vehicle, role, exact receipt, evidence ID and source version; purge on logout, vehicle switch, token revocation and failed scope check.

## 34. Security headers

Keep next.config.ts security headers and strengthen 9H routes with cache no-store, appropriate Content-Security-Policy compatible with Next.js and chart rendering, nosniff, strict referrer and frame blocking. Avoid remote fonts and third-party scripts that could leak traces. Security headers are defense-in-depth, not authentication.

## 35. No session leakage through SSR

Server Components may fetch authorized data only after operator session checks; generated HTML and hydration cache must be private/no-store. Do not render hidden private JSON while showing a disabled overlay. Next.js metadata/static SEO previews must never contain source IDs, scores or vehicle history.

## 36. Client-facing types

Use generated `packages/contracts/generated/api` for FastAPI-compatible schemas, and a small explicit TS schema for only sanitized BFF UI projections when necessary. No broad `any`, unsafe unchecked casts or manual duplicate Pydantic definitions; inspect OpenAPI and regenerate contract versioning. Strict runtime validation at untrusted BFF/browser boundary required.

## 37. BFF projection privacy

Return bounded safe DTOs with result kind, horizon, task/family, decision/status, frozen score/threshold, original cutoff, source role, quality/coverage, evidence integrity/completeness, stable opaque ID and minimal safe model/detector version. Exclude raw VIN, license plate, GPS, user PII, internal path, source row fingerprints, raw feature arrays, full evidence graph, auth headers and secret-derived hashes.

## 38. Read-only receipt discovery gap

Existing 9D has GET receipt by known UUID but no global public vehicle receipt list. Implement a narrowly scoped, sorted, paginated, READ-ONLY server-side discovery/index if required. It must live behind existing 9D authenticated, dev/test-only middleware and server-side vehicle/source policy. Never add an unguarded /api/v1/receipts global route. If unable to build safe discovery, require exact pre-provisioned fixture receipt IDs and document reduced UX rather than bypass authorization.

## 39. No timeline from made-up data

Historical list entries must originate in real persisted 9D receipts or independently versioned synthetic demo fixtures with explicit provenance. No interpolation of gaps as healthy pulls, no generated future target outcomes and no inferred time if missing. A missing timestamp/status is explicitly unavailable.

## 40. Filter semantics

Filters vehicle/configuration/session/pull, task, anomaly family, horizon, source role, decision, completeness, integrity and date range must operate on permitted bounded data. Server paginates/sorts by immutable recorded timestamps and stable tie-breaker; client filters should not incorrectly imply all history loaded. Changing filters resets page and cancels old requests.

## 41. Receipts after revocation

A historical immutable 9D/9E receipt may remain available to a permitted operator after its serving binding was revoked if existing audit policy allows historical reading. UI must show historical binding state and not suggest the model can still be served, and must never reactivate it or trigger a new inference.

## 42. 9E evidence verification semantics

Separate historical verified integrity, current source re-check, completeness, artifact availability and original prediction status. If the read path does not provide a fresh independent verification status, label it 'verified when materialized' rather than 'verified now'. Never invoke 9E POST verify (which appends audit) from a normal dashboard GET.

## 43. No evidence materialization

9H UI must not call 9E POST /runs/{id}/evidence to create a bundle just because user opens a card. If prior materialization absent, show 'evidence not yet available' and operator-only instructions outside UI. There must be no button falsely advertised as a read-only verify when it writes audit rows.

## 44. 9G offline evaluation access

9G evaluation registry/metrics are offline research artifacts, with no general HTTP API. Safely expose only a bounded, separately versioned, SANITIZED snapshot/aggregate generated by a trusted operator export or checked-in fixture, marked with protocol version, source role, model version, git SHA and observed test support. Do not expose raw calibration artifacts, full fold rows, source hashes or private registries to arbitrary browsers.

## 45. 9G research freshness

A snapshot with a historical code SHA or fixture version is a historical experiment, not current production monitoring. State exact protocol/date/source and separate it from current vehicle results. Warn if no compatible evaluation or evaluation artifact available. Never silently substitute a synthetic evaluation for the selected real vehicle.

## 46. No calibration serving promotion

9G identity/sigmoid/isotonic research candidates remain NOT_FOR_SERVING. UI may compare synthetic fixture-only experiment metrics with support, but may NOT apply research calibration map to a 9D score, change decision thresholds or show 'calibrated risk %' for real cars.

## 47. Source role visual hierarchy

Every predictive result prominently displays SYNTHETIC / IMPORTED_FIXTURE / IMPORTED / REAL_VEHICLE with human-readable explanation. Synthetic fixture banners must remain visible even after scroll, detail expansion and export. Never hide them in a tooltip while showing large scary numbers.

## 48. Horizon badges and wording

Use plain text descriptors 'Próxima puxada — classificação de resultado observável' for NEXT_PULL and 'Puxada observada — desvio estatístico retrospectivo' for AFTER_PULL_OFFLINE. Labels must not say engine failure prediction. Include task/family identifier and exact original cutoff in detail.

## 49. Supervised 9B card

Display original engineering_validation_score, frozen decision threshold, labeled target outcome definition, source role, sample/coverage quality, model version, feature evidence status, timestamp/cutoff and conspicuous noncalibration caveat. A boolean threshold decision means crossed study threshold for a synthetic observable outcome, not a diagnosed defect.

## 50. 9B visualization

A scalar score and frozen threshold can use a small calibrated-in-pixels linear scale or bullet chart labeled 'engineering score, uncalibrated' with numeric tick values 0.0–1.0, not a circular engine-health gauge. Mark measured score/threshold accurately, show accessible data table and differentiate missing/abstained from zero. Any visual fill is not health/probability.

## 51. 9C anomaly card

Display family, detector algorithm, observed pull, relative outlier score, frozen detector threshold, INLIER/ANOMALOUS or explicit abstention, reference comparability, coverage and context. For method-specific scales do not force 0–100%, do not rank severity across Robust MAD and IsolationForest, and don't color all anomalies as safety-critical.

## 52. 9C comparison chart

When 9C has recorded compatible reference median/IQR/MAD or factor summary, render observed versus frozen reference with exact canonical unit and supported window. Otherwise render only score-versus-threshold, honest 'reference statistics unavailable', and link to evidence limitations; never compute an imagined vehicle normal baseline from different car.

## 53. Method axis fidelity

Robust MAD and Isolation Forest score scales differ. Display separate axes/panels with method labels, fixed threshold and orientation. Never plot them on the same unqualified y-axis or derive a unified failure probability. Inliers can have unusual measurements and anomalies can arise from distribution shifts unrelated to faults.

## 54. Telemetry visualization integration

Use existing TelemetryDashboard/AnalyticsWorkspace signal plots where the original pull/session/feature match. Plot raw observed telemetry only if permitted, within canonical unit/time semantics; 9D/9E evidence typically offers bounded aggregates, not a full signal matrix. Do not silently fetch new unrelated raw telemetry to strengthen a claim.

## 55. Cross-panel linked selection

Selected vehicle, configuration, session and pull should stay synchronized across predictive overview, existing telemetry/analytics/agent panel when paths support exact identities. Selecting a different vehicle must clear incompatible previous selections and protected evidence data immediately. Prevent a stale card from vehicle A appearing while vehicle B header is selected.

## 56. View overview information hierarchy

Overview should show permitted count of already recorded predictions, eligible scored/abstained counts, evidence verification breakdown and latest reviewed pull (if permission and bounded query permit). These are record availability metrics, NOT number of mechanical problems or vehicle health. Default empty state must not display zeros as healthy fleet.

## 57. History table

Provide accessible paginated pull history with time, session, configuration, source, 9B/9C kind, status, result, quality, evidence completeness and detail action. Sort stable by persisted timestamp and ID. Show recorded-time vs observation-cutoff distinctions and bounded page sizes; no infinite-scrolling flood.

## 58. Prediction versus event distinction

Existing Phase 3 deterministic events are distinct from Phase 9C statistical anomalies. Use separate icon/label/legend and provenance in same timeline if shown. Do not combine event severity with model score into an arbitrary single ranking, nor count two derived observations as independent proof.

## 59. Multi-receipt grouping

A single pull may have several 9B tasks and 9C families. Group by same input pull to avoid visual clutter but preserve EACH receipt, horizon, method, threshold and evidence lineage. Never sum their scores or count overlapping source features as independent confirmations of a mechanical problem.

## 60. Evidence detail viewer

Build a structured read-only evidence panel for a specific 9E safe projection: original receipt/model, horizon, cutoff, source role, integrity, completeness, original prediction, typed facts/units, allowed claim templates, explicit gaps, artifact status and source summary. Provide stable deep link and an accessible list of connected source types if safe. Do not expose internal full graph or source hash.

## 61. Claim-to-source linking

Each displayed model statement or factual measurement must indicate the corresponding safe 9E fact/evidence class and a clickable or navigable in-app citation within the authorized context. A citation should never be a raw internal DB URL or guessed opaque UUID accessible outside the session. If a fact path is absent, hide/mark the claim as unsupported, not invent one.

## 62. Verification state UX

Show status categories VERIFIED, VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE, FAILED_SOURCE_MISMATCH, NOT_VERIFIABLE and UNSUPPORTED_SCHEMA with plain-language consequences. Verified means source consistency, not truth of hardware diagnosis. Failed/mismatched blocks affirmative claims; stale/unverifiable warrants a prominent limit and no confident score highlight.

## 63. Completeness UX

COMPLETE, PARTIAL and ABSTAINED have independent meanings from integrity. An abstained receipt may have fully verifiable explanation despite no score; a partial source graph cannot be visually promoted as complete. Display reasons and omitted_count where present. No amber/green visual alone carries crucial information.

## 64. Quality and missing signals

Display exact 9D quality_class, expected/observed feature count, coverage and missing-reason counts with an accessible table or plain text. Missing pressure, thermal signal or quality-limited FeatureSets must not be treated as zero measurement or normal reading. Provide useful information about missing data, not automatic acquisition.

## 65. Source/time context

Display recorded original effective cutoff in explicit timezone and readable locale format, distinguish observation versus issuance time. All date/time visualizations have UTC storage and deterministic pt-BR rendering; avoid DST or client-server hydration mismatch. Future target label values must never be shown as known observations at earlier cutoffs.

## 66. Scientific readiness panel

Expose 9G engineering readiness and scientific applicability independently: 'Avaliação de engenharia: aprovada' and 'Validação preditiva em veículos reais: não estabelecida'. Show source role, label/oracle provenance and why this limits interpretation. Do not use a big 'accuracy 91%' without specifying synthetic task, metric, N and interval.

## 67. 9G calibration research charts

Where a trusted sanitized source snapshot exists, show 9B task-level Brier, log loss, ECE, AUROC/AP and support/caveats, and validation-selected identity/sigmoid comparison. Reliability diagrams must display bin row/session counts and note per-bin low support. Hide scientific chart if eligibility/report checksum not verified or metadata absent; never fabricate reliable curves.

## 68. 9G anomaly false-alarm matrix

Render a method-by-family comparison of clean-control alarms, other-family alarms, target detections and abstentions with exact numerators/denominators. Clearly distinguish cross-family alarms from clean-control FPR and synthetic interventions from real mechanical failures. A table with tooltips/legend is preferred to flashy heatmap unsupported by small counts.

## 69. 9G drift and OOD context

Display 9G offline PSI/shift and OOD research as experiment data only, source role and reference/protocol shown. Six PSI alerts on synthetic comparisons do not automatically mean the selected car is deteriorating. No live drift badges, automatic alarms or unqualified 'normal vs abnormal' tags for real telemetry.

## 70. Confidence interval disclosure

Confidence intervals must include sample and independent session support; missing intervals stay missing. ECE fixed-width bins with insufficient independent sessions are descriptive, not exact confidence guarantees. Avoid chart lines suggesting high precision when test support is sparse.

## 71. No misleading probability UI

Ban oil-can/engine-warning red alarm imagery tied directly to uncalibrated score, 'risk of engine failure 83%', 'vehicle health 17%', 'safe to drive' indicator, prescriptive part-replacement badge and automatically generated urgent maintenance. Display engineering score numbers only with method/task/cutoff/source limits alongside.

## 72. No automatic 'repair recommendation'

The 9H interface can suggest 'verificar qualidade/coleta de dados' or 'procurar profissional habilitado para uma questão de segurança' as bounded neutral text, but cannot diagnose an intercooler, HPFP or turbo or order a repair because 9C threshold was crossed. No ECU-write or tuner integration.

## 73. Agent context widget

For an authorized selected vehicle/pull show links to existing Phase 9F AgentRun(s) only when a verified server-side relation from a run-local evidence reference to original 9E evidence exists. Display specialist findings with their original citations and limitations; do not infer that unrelated agent text explains the model score.

## 74. 9F agent no auto-run

Opening or filtering prediction cards must not create an AgentRun, invoke MCP, call a paid LLM, trigger telemetry capture or extend a prediction scope. A contextual 'Abrir investigação existente' link is read-only. If an explicit new question action is provided, it must use existing 9F authorization and separate deliberate confirmation, not background effect.

## 75. Agent-generated text trust

Do not render model-originated output with dangerouslySetInnerHTML or unsanitized Markdown/HTML. Agent explanations require application-verified claim output and existing grounding contract; untrusted raw answer remains escaped or restricted. Protect against prompt injection content inside model evidence/vehicle notes.

## 76. Design system tokens

Define coherent CSS custom properties or existing design tokens for neutral backgrounds, surfaces, foreground, subtle outlines, warning/blocked/verified states and focus. Distinguish semantic meanings with text/icons not just hue. Maintain WCAG AA contrast in dark mode; if supporting light mode, validate both, but do not introduce unnecessary theme complexity.

## 77. Typography and density

Use legible system font stack or approved bundled fonts without external fetch dependency, tabular figures for scores, clear 12–16 px supporting text, consistent spacing and precision. Labels should be readable at 320px; avoid horizontal scrolling for primary cards and truncate only noncritical IDs with accessible full label.

## 78. Responsive desktop layout

At >=1200px provide selected vehicle context, overview metrics, two-column predictive panels, history table and detail side panel when appropriate. At tablet collapse to one main content region plus cards. At phone >=320px stack panels, make filter controls scroll/wrap with labels and preserve drill-down readability, no offscreen button/graph.

## 79. Mobile chart behavior

SVG/charts must scale or switch to accessible data table under narrow widths, with pinned legend and numeric values available in text. Tooltips must work through keyboard/tap; no hover-only evidence; avoid tiny targets, clipping, janky animation or forced sideways page scrolling.

## 80. Accessibility baseline

Meet WCAG 2.2 AA for core tasks: semantic headings/regions, skip link, properly associated labels, logical heading level, keyboard-only navigation, clearly visible focus, tab state aria-selected, accessible names, status live regions, meaningful error text, no focus trap and 200%/400% zoom. Use axe and human keyboard auditing in CI.

## 81. Reduced motion and color

Respect prefers-reduced-motion; any transition is nonessential and fast. Do not encode anomaly in red vs green alone; show method, text status, value and threshold. Colorblind-friendly contrast matters in historical charts and clean/cross-family matrix.

## 82. Screen-reader charts

Provide chart title, axis meaning, method/units/score interpretation, data table alternative and summary of missing/uncertainty. An SVG with only decorative lines is insufficient. Mark hidden decorative paths aria-hidden and announce no-score/abstention meaning textually.

## 83. Keyboard chart navigation

Ensure users can navigate timepoints/rows through accessible table/list instead of needing precise mouse position. Selected source/evidence links work with Enter/Space; on change announce selected pull and model. No global keystrokes that conflict with browser or assistive tech.

## 84. Localization

Existing layout uses lang=pt-BR while some components are English. New 9H should be pt-BR first and provide consistent canonical technical terms and short English source labels where necessary. No fabricated technical translation that changes confidence/horizon; datetime/number formatting locale safe and testable.

## 85. Empty-state writing

Write helpful states: 'Nenhuma previsão registrada para esta puxada', 'O detector não tinha histórico suficiente', 'Este sensor não estava disponível', 'A evidência não pôde ser verificada', 'Os modelos estão disponíveis apenas em testes controlados'. Never phrase empty as 'O carro está perfeito' or imply active monitoring.

## 86. Error handling and retry

Show distinct 401 session expired (login again), 403 source unavailable/out of scope, 404 receipt not found, 409 integrity/approval conflict, 429 rate limited (honor Retry-After), 503 disabled/unavailable, timeout/aborted and malformed version. Retrying never triggers a training or inference request and should not leak original sensitive error bodies.

## 87. No phantom progress metrics

UI skeletons can indicate loading, but do not show a synthetic or percentage progress score unless actual server progress exists. A pending evidence request should not display PASS from an older fixture. Overly long BFF requests should time out with safe retry, no uncontrolled polling.

## 88. Performance budgets

Set evidence-based load targets for initial render, interactive selection and chart rendering under disposable fixture sizes. Do not make production SLA claims from CI. Avoid importing a heavyweight chart library when existing SVG is sufficient; lazy-load detailed charts and reuse React memoization and server-side pagination.

## 89. Render performance measurement

Measure response payload, DOM nodes, chart points, client JS size, core web vitals or reproducible web-vitals approximation in Chromium across desktop/mobile. Predeclare practical fixture-dependent budgets and report observed values; don't hide failing samples by reducing fixture cardinality after measurement.

## 90. Network budgets

Initial overview should make bounded server requests, only fetch detail after selection, avoid N+1 requests for each historical receipt and use server aggregation where justified. Do not fetch all raw telemetry, all evidence graphs or all 9G fold scores into the browser. No SSE stream for static historical card.

## 91. Viewport validation

Playwright screenshots/visual regression at desktop 1440x900, tablet ~768x1024 and mobile ~390x844 or standard project viewports; compare full page and representative card/detail states, including long labels/empty/partial/abstained. Manually review images for clipping, collisions, density and contrast before marking VERIFIED.

## 92. Avoid fake screenshot/illustration

User expects working React/Next.js components. Render real HTML/SVG from verified data; do not substitute generated raster mockup for code or screenshot tests. A design reference is not a functional requirement pass unless actual page navigation/interaction and data integrity are proven.

## 93. UI state machine

Model data state with finite discriminated union: feature disabled, not authenticated, vehicle scope denied, loading, ready scored, ready no scores, abstained, partial/integrity-limited, empty, error. Keep snapshot identity/vehicle ID with response to reject stale asynchronous updates; do not merge incompatible stale states.

## 94. URL state

Choose only non-sensitive route params such as controlled vehicle alias, selected tab, and safe opaque receipt ID; avoid tokens, VIN, full source hashes or internal stack traces in URLs. Deep links are not authorization; reload must recheck session+vehicle+receipt and fail closed.

## 95. Refresh behavior

Manual refresh of historical data may re-fetch read-only data with no-store; it does not create a new scoring run. Clearly show 'atualizado em' only for the time data was fetched, not imply the vehicle is monitored live. No unbounded periodic refresh.

## 96. No real-time implication

Phase 4 live acquisition dashboard exists separately; 9D is controlled offline/on-demand serving, 9C AFTER_PULL_OFFLINE, 9G offline research. New 9H predictive panels must not masquerade as continuously monitoring the engine, use 'live risk' wording or trigger notifications based on past model scores.

## 97. Version and data lineage

Show model/detector/evidence/prediction schema version in expandable technical detail. Persist original cutoff, run/receipt selected and source role. A new 9G research report does not retroactively alter old score. Unknown future schema must fail to explicit 'versão não suportada', not be guessed.

## 98. Canonical units

Respect 9A units: Kelvin vs Celsius, Pascal vs bar, m/s vs km/h, etc. Display conversions only through named, deterministic, unit-tested helper and show both unit/precision where useful. Distinguish gauge vs absolute boost; do not apply OEM-specific thresholds to generic source.

## 99. Numeric precision rules

Scores and thresholds are rounded FOR DISPLAY ONLY; comparison uses original machine values. An input score 0.4996 and threshold 0.5000 may both render 0.50, so show enough decimals or a threshold decision warning that avoids contradicting source. Null/NaN/Inf are unavailable, not zero or blank healthy values.

## 100. Metric support formatting

9G Brier/ECE/AUROC/AP values require metric name, held-out test support and 95% CI when present. Do not render 0.91 AUROC as 91% vehicle prediction accuracy. For single-class/undefined metrics show 'não definido' with reason; source role synthetic remains adjacent.

## 101. Multiple comparisons caveat

When showing three tasks or eight detector candidates, user may think largest number is always best. Provide explainer that methods/tasks have different targets, population and thresholds; no universal 'best algorithm for BMW' badge. Distinguish validation-selected candidates from final test descriptive metrics.

## 102. App-wide navigation integration

Update existing home/header to reflect Phase 9 progress without falsely claiming product or real-world calibration ready. Add navigation from VehicleWorkspace to Predictive Intelligence preserving selected vehicle, and return links to telemetry, analytics, agent and knowledge. Existing Phase 5 copy can be modernized to accurate roadmap, but avoid redesigning unrelated domain flows unnecessarily.

## 103. Selected vehicle source-of-truth

One controlled UI selection is applied to all predictive page state. Derive backend query from server-approved scope; if the user changes vehicle while detail open, clear data before new request and invalidate authorized session-scoped cache. Cross-brand test cases verify no BMW-only assumptions.

## 104. Typed chart component API

Create reusable PredictionScorePlot, AnomalyDeviationPlot, ReliabilityCurve, AlarmMatrix, QualityCoverage, EvidenceStatus and HistoryTable with narrow prop types and pure rendering. Keep data fetching/authorization out of chart components. Each chart receives safe DTO from BFF and can be tested with deterministic fixtures.

## 105. Component architecture

Prefer apps/web/src/components/predictive/ directory, server-only lib/predictive/* for typed BFF and private API, and dedicated App Router route or integrated section. Server components for initial protected data; small client components for filter and chart interaction. No global provider with raw private state, and no unnecessary dependency on CSS-in-JS framework.

## 106. Existing UI compatibility

Do not break TelemetryDashboard SVG, AnalyticsWorkspace pull comparison, LiveAcquisition recording state, KnowledgeWorkspace citations, AgentWorkspace SSE/specialists or SystemStatusPanel. Vehicle switch still disables selection during active acquisition. Dedicated 9H route must not change existing API proxy semantics except justified security guards.

## 107. Design tokens and layout verification

Build component tokens with documented spacing/typography, background, borders, focus/error/skeleton and responsive breakpoints. Add screenshots to ignored validation artifacts; do not commit huge generated graphify-out changes unless necessary to actual code graph and explain changed output. Prior phases had excessive generated graph churn.

## 108. No external analytics trackers

No third-party telemetry/cookies/heatmap scripts, analytics CDNs or web font fetch. Existing OTel first-party only, with no vehicle/evidence IDs in labels. Dev/test operator UI must not send private feature values to external SaaS logs.

## 109. Observability UI events

Instrument bounded metrics: page-view category (not URL IDs), auth denied, receipt list requested, evidence opened, abstention viewed, chart render failure, data unavailable and load duration. Exclude exact receipt/vehicle IDs, VIN, source hashes, token, values, user question and detailed filter strings from metric labels.

## 110. Structured server logs

Log request correlation, endpoint class, sanitized denial and latency; redact secrets and private IDs where policy dictates. Never include raw 9E facts, model input matrix, personal vehicle nicknames or per-user secret. User-facing troubleshooting may show an opaque support reference within authorized session only.

## 111. Security audit of Next/server bundling

Add unit/CI assertions that no value of PREDICTION_OPERATOR_TOKEN, internal API URL, dashboard session signing key or source hash appears in rendered HTML, browser JavaScript chunks, error JSON, source maps or generated static assets. Access to environment variables must be in server-only modules.

## 112. Static assets and hydration

No static serialization of private predictions during next build or public preview. Ensure dynamic/no-store on protected route handlers and Server Components; a server build can run without any prediction credentials when feature is disabled. Hydration must not change decisions due to locale rounding.

## 113. No source mutation

Viewing predicted scores/evidence and 9G evaluations must not modify feature sets, model versions, 9C findings, 9D serving bindings/receipts, 9E bundles/verifier audit, 9F agent links or 9G research reports. Independent tests snapshot database digests before/after browsing the UI.

## 114. Controlled BFF read-only backend design

If adding an internal read/list service or API endpoint for 9H, keep it read-only behind existing prediction middleware and server-side source authorization; ensure approval and model lifecycles unchanged. Prefer DB query via trusted API service to direct Next.js DB credentials. No new model artifact loading in web runtime.

## 115. Approval and binding display

Show historical model serving binding and activation-event identity only as safe metadata and with correct active/revoked history. A model's 9G research score does not imply active 9D serving approval. Don't provide Activate/Approve/Revoke buttons through UI; these remain protected operator CLI policies outside 9H.

## 116. Evidence proof wording

'Fonte íntegra e verificada' means checksum/source consistency inside trusted DB/application boundary, not cryptographic proof against fully privileged adversary. Avoid 'auditoria infalível' and 'certificado de diagnóstico'; show source lineage/limits with deterministic citation.

## 117. Same-source correlation display

When two predictions/anomaly flags share the same 9A FeatureSet, group/link as related results rather than independent corroborating alerts. No stacked diagnostic '3 of 3 agree = 99% fault' logic. Show source overlap and separateness of task targets.

## 118. No raw LLM model output as fact

9F agent content must be accompanied by grounded run-local citations and verified source fact paths. If supporting evidence is inaccessible/not verified after permission check, show 'análise anterior sem evidência disponível' rather than rendering a high-confidence summary.

## 119. Privacy under copying and export

Optional copy/CSV export must include only authorized redacted safe-projection fields, source role, cutoff, caveats and exact status; no raw VIN, customer data, auth or source hashes. The default export should not leak into clipboard silently; user explicitly activates and the content warns experimental validity.

## 120. Printing and screenshots

Print styles may support review reports, but labels/limitations/synthetic identity must remain on the printed page. No hidden sensitive JSON in print DOM, no claim the printout is an inspection certificate. Tests inspect print CSS and screenshot output where appropriate.

## 121. No hidden operational settings

Do not expose operator keys, API host, feature-flag bypass switches, alternate model version path or synthetic/real source toggles that bypass authorization as 'advanced settings'. An operator choosing a view mode is not authorized to alter back-end source role or approval.

## 122. Accessible filtering and search

Use labeled form controls with bounded enumerations, date ranges and stable state. Search is over safe labels/opaque IDs only, not raw SQL or arbitrary feature path. Avoid search-as-you-type requests on every keystroke; debounce/cancel, apply caps and announce result counts.

## 123. Keyboard-focused detail navigation

When opening evidence detail, move focus to a meaningful heading or accessible dialog following standard focus management; when closing, return focus to originating item. Browser Back restores selected receipt/filter after authorization recheck. No inaccessible native summary inside a focus trap.

## 124. Loading and skeleton quality

Use consistent skeleton shape without placeholder numeric risk values; present aria-busy and a polite status. On lazy detail failure, keep overview stable and show explicit retry. Empty states differentiate no allowed receipt and no indexed history.

## 125. Synchronous status semantics

Health of general API must not imply prediction service enabled. A green SystemStatusPanel cannot authorize 9H. 9H availability is an independent guarded status; if unavailable all charts must show disabled/empty without revealing model metadata.

## 126. Graceful degradation

When 9D is disabled or 9E proof unavailable, existing Telemetry, Analytics and Agent/RAG workspaces continue to load. 9H shows controlled non-predictive explanation or synthetic demo ONLY if user explicitly selects demonstration; no breaking shared app error boundary.

## 127. Tests using actual Next server

Use Next App Router server route integration and live browser testing, not only mocked React components. Verify protected BFF routes, generated client/runtime DTO, credential session lifecycle and actual 9D/9E API path with disposable Postgres+API. Include one real browser end-to-end playback across vehicle/pull/evidence.

## 128. Synthetic demo provenance

Use a fixed versioned demo fixture file separate from real data, with deterministic declared timestamps, source role synthetic, label 'Dados simulados para demonstração' and zero resemblance to personalized vehicle metrics. It is acceptable to use illustrative values if prominently labeled; never use fabricated PR/real serving receipt IDs as if authentic.

## 129. Controlled fixture real path

Provision disposable DB and run actual 9A FeatureSet generation, 9B/9C accepted models, 9D controlled approval+receipt, 9E materialization and optionally linked 9F run/9G sanitized summary. Browser must display values that match server DB source via an independent oracle; do not create a front-end fixture pretending to be a persisted result.

## 130. Three supervised task cases

Test NEXT_PULL_THERMAL_DEGRADATION, NEXT_PULL_PERFORMANCE_DEGRADATION, NEXT_PULL_FUEL_DEVIATION. Verify score/threshold/decision/cutoff/model version/source role exactly, no future outcome shown as observation, correctly missing/unsupported fuel and explicit synthetic-only caveat. At least one scored and one abstained fixture.

## 131. Four anomaly family cases

Test 9C thermal, boost_air, performance, fuel. Verify method-specific score orientation, cutoff, same-config frozen reference, 9E link, correct inlier/outlier and abstained states, not a combined health score. Robust MAD and IsolationForest where valid, but don't invent one when no accepted version.

## 132. 9E proof state matrix

Test COMPLETE/PARTIAL/ABSTAINED crossed with VERIFIED/NOT_VERIFIABLE/FAILED_SOURCE_MISMATCH/UNSUPPORTED_SCHEMA and artifact-unavailable historical state where feasible. Independent oracle confirms UI status and claim restrictions. A failed graph must not show affirmative 'caused by turbo' or green vehicle health.

## 133. 9G scientific visual proof

Use real sanitized 9G summary generated from protocol phase9g-protocol-v2, with source SHA and SYNTHETIC_ONLY labels; show per-task Brier/log loss/ECE/AUROC/AP support and correct undefined bins. Show 9C family/method cross-family vs clean denominators, synthetic OOD and no real validity. Validate figures against original report in independent test.

## 134. 9G no-cohort edge case

If an evaluation snapshot references a mismatched model/task/version/source-role, no calibration claim is shown for selected vehicle; display 'estudo não aplicável'. Test a fake imported real data row with no outcomes yields REAL_DATA_UNLABELED, not interpolated Brier.

## 135. Cross-vehicle adversary

Create two different makes/vehicles and configurations; select one vehicle and request other's receipt/evidence through UI, BFF and generic proxy. Must reject before private data is returned, show nondisclosing error and clear cached previous vehicle data. Verify direct guessed IDs, URL tampering and session replay.

## 136. Disabled environment adversary

With 9H flag off, 9D flag off, ENVIRONMENT=production or missing secrets, all 9H private BFF routes and protected pages fail closed. The ordinary public app remains operational and no private metadata appears. A forged cookie or synthetic flag must not override production denial.

## 137. Authentication adversary

Test wrong/missing/oversized operator secret, brute force rate cap, malformed/expired/rotated/signature-tampered session cookie, query/body token, stolen old session after logout, cross-origin request, direct BFF call and stale browser tab. No readable private source before auth.

## 138. CSRF and server-only token adversary

Test cross-site GET/POST, Origin spoof/referer missing policy, POST login/logout CSRF, client-supplied Authorization to generic domain proxy, BFF path traversal, encoded slash/percent, SSRF target URLs and redirect to public host. No operator bearer leak or unsafe backend route accepted.

## 139. Read vs write adversary

Confirm normal 9H browsing never issues POST /next-pull, POST /anomalies, /evidence materialize or /verify, agent ask, serving approve or calibration fit. Monitor backend method/event counters and pre/post table digests. Only an explicit independent operator workflow outside 9H can produce those records.

## 140. Temporal and stale selection adversary

Rapidly change vehicle and pull while previous requests are in flight; verify no stale data rendered under wrong header. Insert newer telemetry after original cutoff and confirm old receipt/evidence display unchanged. Sorting and date zones must remain stable around midnight/DST.

## 141. Numeric/UI manipulation adversary

A receipt has score 0.4996 with threshold 0.5000, null score, infinite invalid score, extremely large anomaly scale, negative valid feature value and a method not known to renderer. Expected: precise original decision/units, explicit unavailable for invalid, method-specific safe fallback, no misleading percentage or fake confidence.

## 142. Accessibility adversary

Automated axe on desktop/mobile for overview, login, empty, error, history, chart, evidence details and 9G panel; manual scripted keyboard-only navigation and focus recovery; zoom 200/400%, high contrast, reduced motion, screen-reader label inspection. Fail gate for severe/critical violations and no keyboard route to detail.

## 143. Responsive visual regression

Use Playwright screenshot review at desktop/tablet/mobile with long task names, many badges and nested warnings; check overflow and accessibility labels. Compare to captured baseline when deterministic, or inspect actual PNG artifacts and iterate. Avoid brittle pixel-exact CI checks across font environments without tolerance.

## 144. Performance benchmarks

Benchmark initial protected route TTFB/render, list 20 receipts, detail 1 evidence graph safe projection, chart 500 points and switching vehicles. Capture total client bundle KB, request count, p50/p95 where enough samples, memory and render time with controlled fixture. No production SLA claims.

## 145. Budget saturation tests

Saturate allowed concurrent BFF requests and 9D budgets; verify 429 or explicit busy, no leaked worker/DB sessions, unaffected unrelated health routes, bounded retries, no temporary unprotected fallback and proper cleanup after abort/disconnect.

## 146. Unit and component suite

Vitest/Testing Library test all helper formatting, source role/horizon/status mapping, derived display state, limits, chart axis labels/score orientation, date/time/unit conversions, keyboard events, errors, no score to 0, source switch cache clear and demo mode. Use generated TS contract types and strict no-any checks.

## 147. Backend API integration suite

FastAPI route/SQL tests for any new read-only vehicle receipt index/list, auth/private network, server-side vehicle scope, stable pagination, rate/size limits, immutable persisted source, stale revocation, no path traversal and no cross-vehicle query. Regression verifies 9D/9E existing endpoints unchanged.

## 148. End-to-end multi-workspace suite

Browser journeys: existing landing -> vehicle selection -> predictive overview -> filtered history -> 9B/9C detail -> 9E provenance -> 9G science -> linked 9F existing run -> back to telemetry/analytics without state loss. Run with controlled fixture and external disabled/public mode; no new agent generation.

## 149. Existing web regression

Run existing `make check-web`, web Vitest coverage, Playwright smoke, agent, investigation, knowledge and supervisor tests; ensure old screenshots/functionality not degraded. If changing navigation/global CSS, verify live-acquisition and graphs remain usable on mobile and keyboard.

## 150. Canonical all-phase regression

Execute Phases 0–9G deterministic acceptance, migrations, canonical full-stack Docker, stream/telemetry, events, analytics, MCP, agents/RAG and 9A–9G research checks. No paid agent or embedding calls. Phase 7D historical 120-run paid rerun caveat stays disclosed, not claimed complete.

## 151. Database migration policy

Prefer zero new migration because 9H is visualization. If a small server-side index or operator session ledger cannot be implemented without persistence, create additive next Alembic revision after actual 0019 and test upgrade/downgrade/re-upgrade/fresh DB; never edit old 9D/9E/9G migrations or mutate their immutable source rows. Session storage must not become a general user account system.

## 152. No production login architecture claim

A dev/test operator cookie is NOT a future customer account, subscription entitlement or tenant isolation. Document that Phase 12 must add robust real-user auth, ownership, encryption/consent, retention, audit, backups and deployment hardening before real customer data can be publicly served.

## 153. Security exception expiry remediation

Current baseline 9G security docs record residual High findings with API/Web exceptions expiring 2026-11-01 and observability exceptions expiring 2026-11-02. At execution (2026-11-03 or later), these dates have passed. Re-scan with current Trivy DB; FIX vulnerable images/packages where possible; review new vendor patches and exact image digests. Do NOT simply ignore expired exceptions or extend dates to force green. Any genuinely renewed narrow exception needs explicit maintainer risk evidence and time-bounded justification, with unlisted High/Critical still blocking under project security policy.

## 154. Supply chain control

Keep Next.js/React/pnpm/npm lock pinned; package review CodeQL JS/TS, Python, dependency review, secret scan and Docker image scan all run on final SHA. Avoid introducing new charting/security npm packages unless necessary and audited; no external CDN and no unpinned latest dependencies.

## 155. Secrets and CORS policy

API operator bearer, 9H operator login secret and cookie-signing secret are independent server-only values; never commit them. Browser never directly targets backend internal host. Avoid enabling wildcard CORS, credentialed cross-origin proxying or unscoped authentication cookies. Tests prove no accidental secret in Next build output.

## 156. Threat model deliverable

Document public Next generic domain proxy, identity/session leakage, 9D bearer, IDOR, CSRF, SSRF, cross-vehicle stale caching, source role confusion, misleading science, analytics exfiltration, prompt injection, dashboard-induced expensive operations, image/QR leak and model/artifact tampering. Mark residual lack of real tenancy and explicit dev/test-only policy.

## 157. Observability and validation docs

Create `docs/architecture/phase-9h-predictive-intelligence-ui.md`, `docs/validation/phase-9h-acceptance.md`, `docs/validation/phase-9h-ui-evaluation.md`, `docs/validation/phase-9h-security-accessibility.md`, `docs/validation/phase-9h-traceability-ledger.md`, `docs/runbooks/predictive-intelligence-ui.md`, design-system tokens/UX guidance, relevant ADR(s) and updates to README/roadmap/AI_CONTEXT/observability/testing/security.

## 158. Runbook operator sequence

Document controlled launch: disable-by-default proof, generate separate dev/test operator/browser secrets, configure private backend network, prepare authentic synthetic model/9D receipts/9E evidence and 9G sanitized report, login, select authorized fixture vehicle, browse history/detail, inspect verification, logout, invalidate session and cleanup. Do not include real bearer, VIN or production environment workaround.

## 159. ADRs required

Record BFF and browser operator authorization versus insecure direct proxy; 9D receipt listing read-only with vehicle scope; 9G research snapshots and source identity; deterministic score visual semantics/horizon and 9E evidence integrity; no-write UI and deferred public accounts. Use next sequential ADR number, inspect existing list and preserve prior decisions.

## 160. Independent acceptance evaluator

Implement `scripts/evaluate_predictive_ui.py` or repo-standard equivalent that provisions real disposable DB/API/Next app and deterministic fixtures, then performs independent HTTP/browser assertions and direct source/oracle checks. Do not accept merely checking mock screenshots or React component props as Phase 9H completion.

## 161. Machine-readable acceptance receipt

Emit `.validation/phase9h/acceptance.json` with code SHA, fixture source roles, counts, original receipt/evidence source fingerprints in ignored private artifact only, UI status mapping, auth denials, BFF methods, chart bounds, accessibility/viewport, no-write DB digest, performance, security scan and final gate status. Include checksum and independent checker to reject stale or forged report.

## 162. Independent oracle for UI claims

Checker reads original 9D receipts, 9E bundle safe projections and 9G sanitized research report independent of UI formatting, compares task/family/horizon/scores/thresholds/cutoffs/source role, denominators and view labels. It must detect a deliberate tampered UI DTO or screenshot claiming wrong value and fail.

## 163. Evidence of exact 9D/9E reads

At least one E2E controlled browser request must reach the real FastAPI protected 9D/9E read handlers with correct BFF server token, private peer, browser session and selected vehicle; verify response values match DB/source. Screenshots generated from hardcoded React fixtures are secondary, not a replacement.

## 164. Operator session lifecycle E2E

Test first load disabled -> authorized login -> permitted fixture view -> evidence detail -> logout -> browser Back -> private data no longer returned; repeat with expired session and rotated secret. Network trace confirms no raw bearer or internal API host in browser traffic.

## 165. Synthetic demo vs operator E2E

Run standalone demo-only mode with no DB/prediction tokens and ensure accessible labeled fixture content; run real controlled mode with actual DB and ensure no demo fallback when data missing; test production mode rejects private operations and demo is never misrepresented as live.

## 166. Hard negative privacy matrix

Probe 401/403/404/429, guessed UUID, foreign vehicle, unauthorized nested evidence reference, source-role spoofing, malformed evaluation scope, too-large response, recursive redirects, cross-site request and direct /api/domain proxy with Authorization. Every forbidden case must leave no private score or vehicle metadata in response body, logs, client bundle or rendered HTML.

## 167. Source and no-write digest matrix

The E2E checks read-only database digests for allowlisted Phase 9A–9G tables, including evaluation 0019 records and 9E verification audits, before and after browsing. Identical digests (excluding unrelated telemetry live feeds explicitly not invoked) and no new 9D/9E/9F writes are mandatory.

## 168. Scientific-language acceptance

Machine-assert Portuguese/English output doesn't say real failure probability, engine-health percentage, vehicle safe-to-drive, confirmed failed component, production-ready calibration or alert from a single synthetic score. Test explicit questions and demo values that might tempt those claims.

## 169. Legacy route hardening regression

If the generic Next.js domain proxy is restricted for predictive URLs, verify all existing permitted domain endpoints still work, especially vehicles, sessions, pull lists, telemetry signals, analytics, MCP/agent run audit and live acquisition routes. Denial should target only unauthorized prediction namespace and path aliases.

## 170. Security exceptions as delivery gate

Final 9H full-stack security gate must be genuinely PASS under current date and latest scanner and documented current exception policy. Baseline exceptions expired on 2026-11-01/02; any stale accepted High must be fixed or explicitly reviewed by authorized maintainer under project policy, never hidden by disabling scanning.

## 171. Canonical documentation claims

Update roadmap to record 9G PR #55 MERGED SHA `2249930642d8f854649913c9c3145e6e5ffea498`, all phases 9A–9G integrated; 9H becomes complete only after exact-head validation. Preserve scientific caveat NOT_ESTABLISHED real-car validity; declare Phase 9 sequence complete as engineering UI only, not product commercial readiness.

## 172. Screenshot artifact delivery

Save real Playwright screenshots and accessible data snapshots under ignored `.validation/phase9h/screenshots/` for responsive overview, scored prediction, anomaly, abstained, proof mismatch, login/denied, science and mobile states. Checked-in doc links to commands and capture IDs, not oversized generated screenshots or sensitive data.

## 173. Validation performance receipts

Report rendering times, request byte counts, fixture size, axes and chart data count, layout overflow metrics, browser console errors, accessibility findings and CI environment characteristics. If visual quality is poor or layout clips, iterate before final HEAD; do not declare done just because tests technically pass.

## 174. End-to-end security priority

When choosing scope tradeoffs, prefer fewer real authorized flows fully protected over a broad dashboard leaking sensitive data. A feature-disabled but polished synthetic demonstration is valid fallback ONLY when separately labeled; uncontrolled private browsing, hardcoded token and fake real evidence are absolute blockers.

## 175. Traceability ledger

Map EVERY numbered 9H section to source code changes, tests, docs and exact executed proof. Requirements are not complete by repeating the heading in ledger; provide actual implementation pointers/test IDs or explain deliberate supported alternatives. Independent checker must verify no missing/duplicate numbered entries.

## 176. CI workflow integration

Add specific 9H acceptance job and wire to canonical Docker full-stack, web checks and browser Playwright; require Quality, Integration E2E, full-stack, Security, Dependency Review, CodeQL Python and JS/TS, Phase 9H independent acceptance on the EXACT final commit SHA. A prior Phase 9G green build does not prove this branch.

## 177. No stale successful checks

After every final fix to login/BFF/data UI/docs, push the new SHA and rerun affected plus full mandatory checks; record remote branch SHA and check job conclusions matching that exact commit. Do not report VERIFIED while pending or after a canceled/timeout full-stack run.

## 178. PR review preparation

Open PR from existing branch to main, leave OPEN and UNMERGED. Body includes baseline/final SHA, architecture and operator boundary, BFF routes, live vs synthetic sources, UI screenshots, 9B/9C/9D/9E/9F/9G cross-checks, negative auth cases, no-write proof, responsive accessibility results, performance, scanner findings, regressions and final-head CI URLs.

## 179. Scope audit final

Before final acceptance verify no public customer auth invented, no model promotion/retraining, no on-demand inference or 9E materialization from dashboard, no new vehicle control, no real-world diagnostic claims, no 9G calibrator served, no background push/monitoring and no externally reachable prediction data. Record any deferred multi-tenant work.

## 180. Definition of Done — UI

[ ] Professional integrated Next.js responsive Predictive Intelligence route with existing selected vehicle; [ ] overview/history/9B predictions/9C anomalies/9E evidence/9G science/9F existing investigation context; [ ] real persisted authorized source not just demo; [ ] robust loading/empty/abstained/partial/error cases; [ ] keyboard and mobile chart/table parity; [ ] source/time/version/quality readable.

## 181. Definition of Done — security

[ ] Disabled by default, production blocked, true server-side operator session and vehicle scope; [ ] 9D operator bearer server-only, no arbitrary /api/domain proxy bypass; [ ] bounded read-only BFF, no CORS/CSRF/SSRF/IDOR/token leakage; [ ] no private cache/static serialization; [ ] login/expiry/logout/revocation; [ ] explicit synthetic demo separation; [ ] refreshed security scan and expired-exception remediation.

## 182. Definition of Done — scientific integrity

[ ] Score/horizon/method/threshold match original 9D receipt; [ ] 9E integrity and completeness distinct, failures fail closed; [ ] source role always visible; [ ] 9G synthetic calibration and applicability clearly separate; [ ] no mechanical failure % or real-world calibration; [ ] no automatically triggered inference/agent training; [ ] linked but non-fused Phase 3/9C/9F evidence and honest gaps.

## 183. Definition of Done — validation

[ ] Strict TS/generated OpenAPI/Next production build; [ ] React unit and Playwright responsive browser; [ ] axe+keyboard, no console/overflow/secrets; [ ] actual disposable DB/API/9D/9E source oracle; [ ] 3 supervised tasks + 4 anomaly families + 9G research snapshot; [ ] IDOR/CSRF/disabled/science adversaries; [ ] zero source writes; [ ] all 0–9G regressions and full-stack security/CodeQL PASS on final SHA.

## 184. Definition of Done — delivery

[ ] Traceability mapped all numbered requirements; [ ] architecture, ADR, runbook, evaluation, accessibility/security and screenshot receipts; [ ] implementation committed/pushed to EXISTING 9H branch; [ ] PR OPEN and UNMERGED; [ ] remote HEAD == validated SHA; [ ] mandatory workflow checks PASS at last SHA; [ ] real-vehicle scientific readiness remains NOT_ESTABLISHED.

## 185. Final engineering handoff

Report baseline/current/final SHA and PR URL; route/component inventory and design system; BFF/session policy proof; demonstration vs controlled real DB path; per 9B/9C UI mapping, 9E evidence/integrity, 9F linked run, 9G scientific limitations; screenshot and responsive/a11y evidence; API/auth/IDOR/CSRF/SSRF matrix; no-write DB digests; performance/observability; security CVE outcomes; local/all-phase regressions; exact-final-SHA CI URLs; remaining commercial/real-data limitations. End EXACTLY `PHASE 9H — PREDICTIVE INTELLIGENCE UI: VERIFIED` ONLY when all mandatory implemented and executed gates pass. Else end `PHASE 9H — PREDICTIVE INTELLIGENCE UI: NOT VERIFIED` with actual blockers. Never merge.

---

## Execution sequence and final verification

1. Verify baseline and fully read requirements. 2. Inspect exact source contracts and security. 3. Implement smallest SAFE controlled browser authorization and bounded BFF/read index. 4. Implement responsive integrated UI with exact source semantics and synthetic demo only when labeled. 5. Run independent live-API/browser tests, visuals, accessibility, security, no-write proof. 6. Remediate/review expired security exceptions honestly. 7. Run canonical regressions/full stack and exact-SHA CI. 8. Commit/push/open PR, no merge, report evidence and scientific limitations.
