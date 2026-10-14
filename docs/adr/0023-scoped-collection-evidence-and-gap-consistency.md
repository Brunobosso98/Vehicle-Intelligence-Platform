# ADR 0023: Scoped collection evidence and consistent evidence gaps

- Date: 2026-10-14
- Status: Accepted for implementation; real-model reliability remains unverified.

## Context

The Phase 7D real evaluation exposed two representation gaps. Splitting list results into row evidence discarded empty collections and their counts. A factual response could also declare missing evidence without the insufficiency finding required by the existing Phase 7B eligibility check. These gaps prevented grounded answers and investigation proposals despite available source records or explicitly declared uncertainty.

## Decision

Project an additional collection snapshot after existing row evidence. Bind its returned count and completeness to the actual scoped MCP response. Expose a total count only for a complete response. Empty complete collections support a count of zero. Validate every nested record's vehicle ownership before publishing any evidence, and charge the snapshot against the existing evidence limit.

Collection snapshots use the existing Evidence fields, a distinct collection evidence type, nullable entity identifiers and the `agent-collection-v1` projection marker. The source fingerprint includes collection data, selection context and completeness. Consumers that require entity IDs select actual records with non-null identifiers. Row evidence remains available in its existing order.

Normalize declared missing evidence into a fixed insufficiency finding before application grounding. Preserve supported observations, lower confidence and retain the declared gap categories. Factual documentation gaps do not acquire synthesized telemetry needs. The existing Phase 7B service determines eligibility, searches existing evidence, resolves source capabilities and builds bounded recipes with explicit approval.

Preserve canonical quality-event identity and measured gap/time/confidence details in blocked-quality synthesis. Restrict this projection to registered quality events and exclude mechanical-cause fields. Share the actual claim-template constraints between parent and specialist instructions; hypothesis planning requires clean, complete supporting evidence or empty support lists.

Version affected prompts and include routing, quality projection, collection projection and grounded synthesis markers in the supervisor configuration hash.

## Consequences and verification

The existing public Evidence field structure supports the additional snapshots. Collection counts describe scoped responses, and partial lists expose a returned count rather than a total. Evidence, input, output, tool, specialist, retry and spending limits continue to apply.

Positive and negative tests cover empty/nonempty/partial collections, ownership rejection before publication, evidence budgets, quality-event filtering, comparative pull routing, template instructions and factual gap consistency. The integrated API checks passed 790 tests, typing/lint, 96.07% line coverage and 91.39% branch coverage. The final real-model confirmation and exact-final-head canonical gates remain required.

## Follow-up from affected real confirmation

The independent round-thirteen review recognizes canonical acceleration mean/delta and coolant/oil start/end measurements as their existing semantic domains. Recognition requires an allowed canonical source tool, an exact unique fact, finite numeric value and matching source unit. Counts, nulls, unrelated tools and unsupported values do not qualify. Historical paid scores remain immutable; no acceptance threshold changes.

Shared MCP instructions now expose the existing same-configuration, ownership and cardinality prerequisites to all roles. Routing distinguishes capture planning from control and rejects requests to use another vehicle. Signal availability cannot resolve a data-quality gap when the supervisor already established unreliable evidence. This preserves the existing quality gate and capture approval boundaries; it does not enable acquisition.

The graph update is deferred until all checks pass under the user's explicit instruction.

The quality-gap regression failed before the fix and passed afterward. Subsequent API validation passed 820 tests, typing/lint and coverage; 80 focused tests passed after the final measurement-identity instructions. The real confirmation remains pending.
