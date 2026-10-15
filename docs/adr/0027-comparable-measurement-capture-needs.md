# ADR 0027: Preserve capture needs when comparable measurements are absent

- Status: accepted
- Phase: 7D

## Evidence

Affected round seventeen completed only three unresolved slots after ADR 0026:
D08 repeat 1 and F01 repeat 1 passed. G03 produced grounded observations and a
capability-resolved plan but failed recipe selection. The immutable artifact
contains an unresolved required comparable-history gap, an available-data quality
gap, and required unknown/unavailable supplementary lambda/timing needs. No
recipe was fabricated and no acquisition was approved. Cumulative estimated
spending is USD 4.291108365 of the operator-authorized USD 5.00 ceiling.

## Decision

Existing-evidence search must not resolve measurement/quality gaps solely from
available channels when a required comparable-history gap lacks sufficient
registered deterministic comparison evidence. Preserve those measurement needs
for capture. Optional history does not impose this rule, and a sufficient
comparison retains normal existing-data resolution. No measurements or analysis
results are invented.

Investigation policy v4 distinguishes the minimum primary measurement objective
from optional mechanism-specific discriminators. Essential unavailable evidence
must remain essential. Optional unknown roles and limitations remain explicit.
New comparable measurements need semantic operating-context needs as well as the
history gap; available channels alone do not establish comparable measurements.
The existing source resolver, Sampling Planner, recipe catalog and approval flow
remain authoritative. New supervisor hash markers identify both changes.

## Verification

Positive and negative tests cover required missing history, optional history,
sufficient registered comparisons, measurement/quality categories and existing
unreliable-data handling. The focused investigation/runtime run passed 97 tests.
Full API, affected G03 and exact-head remote acceptance remain required. Historical
results and spending remain unchanged. The operator requests only unresolved
slots, so no full suite is scheduled and no full-cohort acceptance is claimed.
