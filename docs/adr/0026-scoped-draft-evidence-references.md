# ADR 0026: Scope structured draft references to visible evidence

- Status: accepted
- Phase: 7D

## Context

Affected real round sixteen preserved 93 prior PASS observations and executed only
27 previously non-PASS slots. It completed with 24 PASS, two semantic failures
and one provider failure, at cumulative USD 4.260082125. G03 failed with
`unknown_evidence` in the performance specialist and both bounded parent drafts.
F01 repeat 1 failed `unsupported_claim` in both parent drafts; its precise invalid
binding is not retained, so the failing unit, path or value cannot be inferred.
D08 repeat 1 failed because the provider was unavailable. These results remain
immutable and do not establish full-suite acceptance.

## Decision

Build each Responses draft schema with a shared enum containing exactly the
Evidence IDs visible to that model call. Both claim references and binding
references use the shared definition. With no evidence, both arrays are empty;
honest insufficiency and refusal remain possible. Specialist requests already
contain only their owned visible evidence. No entity IDs are substituted.

The [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
supports enum constraints and shared definitions. At most 100 evidence items are
allowed by existing application configuration; one shared enum stays below the
provider's documented enum limits. The supervisor hash records
`scoped_draft_evidence_ids: 1.0`.

## Consequences and verification

Host validation still checks current run/vehicle ownership, cited bindings,
paths, scalar values, units, classification and temporal context. A permitted
reference alone does not prove a fact. This change does not repair unsupported
values, paths or units by replacing them, relax grading, create findings, add
calls or increase retries. Existing limits and accumulated spend reservations
remain enforced. No prompt, domain schema or suite question changes.

Positive and negative schema tests cover visible and foreign claim/binding IDs,
request isolation and empty-evidence insufficiency. Focused runtime tests pass
(115 tests). Full API, exact-head remote checks and affected real confirmation
remain required. The operator authorizes only non-PASS slots under cumulative
USD 5.00; no additional full suite is authorized. Graph updates remain deferred.
