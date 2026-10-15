# ADR 0028: Enforce gap categories in wire schemas and trace public evaluation I/O

- Status: accepted
- Phase: 7D

## Confirmed failure

G03 real round twenty failed with the fixed safe rule code `gap_signal_category`.
The model attached signal roles to a gap category that disallows them. The
application correctly rejected the proposal. Previous artifacts did not retain
the rejected proposal, so their precise failed invariant cannot be reconstructed.
Accumulated estimated spending after round twenty is USD 4.313705110 / 5.00.

The static provider schema allowed combinations that the existing Pydantic
semantic validator rejected. The two constraints must agree at generation time.

## Decision

The structured proposal schema now uses two nested `anyOf` object branches:
measurement/data-quality gaps may carry semantic signal roles; every other gap
category requires an empty role array. All categories, required fields, existing
limits and the independent host validator remain intact. The supervisor hash
records `investigation_gap_role_schema: 1.0`. No score threshold, output finding,
source capability, recipe or approval is fabricated or relaxed.

At the operator's explicit request, `--diagnostics` enables paid-evaluation traces
under the ignored output directory's `diagnostics/` folder. Each actual model call
records sanitized request data/schema, its public structured output and function
arguments, linked to its charged receipt. Full SDK responses, reasoning items,
reasoning summaries, transport headers and credentials are never serialized.
Unparseable output is identified by hash rather than copied as free text.

MCP traces retain sanitized arguments/results, fixed error categories, timing and
case/sequence correlation. Requests are persisted before execution, and results
update their own file. Concurrent calls cannot overwrite one another. Original
run/audit/plan/evaluation artifacts retain final planning states. The opt-in flag
is part of checkpoint identity; generic CI never triggers a paid call. Historical
charges/results remain immutable, and all existing call/spend limits apply.

## Verification

Schema tests cover every gap category with valid empty roles and positive/negative
measurement-role cases. Diagnostic tests cover secret redaction, exclusion of
private reasoning, invalid output, provider/MCP failures and concurrent calls.
Focused tests and full API/remote acceptance must pass before final completion.
Only the unresolved G03 is selected for real confirmation; no full suite is
scheduled. Graph updates remain deferred under the operator's instruction.
