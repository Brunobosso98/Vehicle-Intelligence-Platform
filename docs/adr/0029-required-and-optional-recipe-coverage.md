# ADR 0029: Required recipe coverage and explicit optional omissions

- Status: accepted
- Phase: 7D

## Reproduced failure

The complete sanitized round-21 G03 trace contains a valid investigation proposal
and capability-resolved plan. Required operating/performance signals are supported.
Coolant is optional and supported, while low fuel pressure is optional and unknown.
The recipe selector nevertheless required every supported optional signal to fit
one canonical recipe. No recipe covers that union, although performance-pull
covers all mandatory needs. The exact immutable plan deterministically reproduces
`recipe=None`, independently of any additional model call.

## Decision

A candidate recipe must cover every mapped required signal. Among those candidates,
maximize requested optional coverage, then preserve deterministic recipe-size,
duration and key tie breaks. Do not downgrade required needs. A genuinely required
unsupported combination still produces no recipe. Required unavailable signals
retain the existing missing/feasibility guards and cannot become approval-ready.

Every optional requested channel outside the selected recipe is explicit in
`dropped_signals`, remains a retained SignalNeed, and makes feasibility degraded.
Source support remains distinct from actual inclusion in this recipe: a source
may support an omitted channel. Optional unknown/unavailable channels remain
explicit too. Approval and capture execution rules are unchanged.

No Phase 4 recipe ingredients, rates, signal availability, catalog version or
configuration hash change. The mapping algorithm changes, recorded by the
supervisor hash marker `recipe_required_optional_selection: 1.0`. This is recipe
selection, not a new recipe or a PID/channel mapping. Existing sampling preflight
remains authoritative. No ECU/control operation is introduced.

## Evidence

Replay of the exact immutable plan now selects performance-pull version 1 with
FEASIBLE_WITH_DEGRADATION, no required_missing, and low-pressure/coolant explicitly
dropped. Original artifact and SEMANTIC_FAILURE score are unchanged; the replay is
not acceptance regrading. Positive and negative synthetic tests require the same
recipe when coolant is optional and no recipe when it becomes mandatory. Existing
unknown-channel/source and rate-degradation tests remain in scope. Focused run:
56 PASS. Full API, disposable-database integration, G03 real confirmation and
exact-head remote gates remain required. Accumulated spending before confirmation:
USD 4.320196060 / operator-authorized USD 5.00. Graph updates remain deferred.
