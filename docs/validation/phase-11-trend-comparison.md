# Phase 11 historical comparison and trend eligibility

## Conclusion

No cross-phase numeric trend is currently eligible. The available evaluations use different
corpora, source versions, and outcome oracles. The repeated question in the Phase 7C and Phase 11
fixtures is a useful scenario relationship, but it does not establish an equivalent scored case.
Do not calculate an improvement or regression percentage from these records.

This is a comparison inventory, not a Phase 11 acceptance result. The current Phase 11 suite has
36 scheduled cases in `evals/phase11/suite-v26.json`; none has been executed against the current
uncommitted worktree's disposable API/MCP stack. The latest accepted historical Phase 11 receipt
and current-worktree evidence are described separately in
[`phase-11-acceptance.md`](phase-11-acceptance.md).

## Comparison inventory

| Historical evaluation                          | Available evidence                                                                                                                                                                                                                                                             | Similar Phase 11 scope                                                                                                                                                                                                                                                                                                                                                                  | Equivalence decision                                                                                                                                                                                 |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Phase 7D real-model evaluation                 | `suite-v2.json`, 80 question IDs and 120 scheduled slots; eventual PASS observations span multiple rounds and source SHAs. One native 120-slot round recorded 93 PASS, 10 semantic failures, 9 runtime failures, 6 provider failures, 1 interrupted and 1 budget-skipped slot. | `evals/phase11/phase7d-id-mapping-v1.json` maps only A01 to `P11-BENIGN-001` as `similar_intent_not_equivalent`; the remaining mappings do not define a shared per-case oracle.                                                                                                                                                                                                         | No numeric comparison. The historical report explicitly does not claim one complete same-final-source run.                                                                                           |
| Phase 7C specialist acceptance                 | Canonical run at `bd7f5dfda0ec03932f97b66fa66205b4b559c49e`: 23 scored executions, 196 HTTP MCP calls, 604 factual claims, 121/121 valid references and 12/12 golden routes.                                                                                                   | `P11-RED-013` repeats the question “Why did performance degrade after repeated pulls?” and uses an ambiguous multi-cause fixture. Phase 7C's `ambiguous` golden uses a `mixed` recording and requires three specialists; Phase 11 additionally grades persisted conflicting findings, an `INSUFFICIENT` synthesis, an investigation recommendation and zero supported diagnosis claims. | Related intent, different execution contract and oracle. These aggregate metrics are not comparable. A future per-case trend needs a shared versioned fixture and explicitly aligned outcome fields. |
| Phase 9F synthetic prediction-agent evaluation | Phase 9E/9F disposable pipeline evaluates 11 immutable bundles across 9B/9C tasks, abstentions, and one same-pull correlation case; report covers authorization, lineage, projection, citation and rendering behaviors.                                                        | `P11-RED-016` exercises an accepted synthetic 9F prediction read and requires calibration, diagnosis and driving-safety caveats. `P11-RED-017/018` cover capability scope and source-role tampering.                                                                                                                                                                                    | Related capability areas, but the reports do not define a shared Phase 11 case ID, shared case-level denominator, and identical grading oracle. No numeric comparison.                               |

## Rules for future trend reporting

- Compare a case only when its immutable case identity, fixture/source construction, and oracle
  fields are equivalent. A similar prompt or shared feature area is insufficient.
- Keep dataset version, code SHA, provider mode, attempt denominator, and missing/failed outcomes
  visible beside every metric.
- Keep the Phase 7D mixed-round/source-SHA limitation intact; it is not a final-source reliability
  baseline.
- Add an explicit crosswalk and re-evaluate the aligned cases before publishing any percentage
  change. Until then, report the inventories and gaps above without a trend chart.

## Sources

- [Phase 7D real-model evaluation](phase-7d-real-evaluation.md)
- [Phase 7C acceptance](phase-7c-acceptance.md)
- [Phase 9F agent evaluation](phase-9f-agent-evaluation.md)
- [Phase 11 suite](../../evals/phase11/suite-v26.json)
- [Phase 7D ID mapping](../../evals/phase11/phase7d-id-mapping-v1.json)
- [Phase 11 requirement 122](../prompts/phase-11-agent-evals-red-team.md#122-coverage-and-regression-trends)
