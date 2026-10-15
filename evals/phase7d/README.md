# Phase 7D evaluation versions

`suite-v2.json` is the current canonical suite. `suite-v1.json` remains unchanged for historical receipts and independent review.

Both versions retain the same 80 questions, ten per category, canonical fixture definitions and 20 critical cases with two additional observations each: 120 observations total. Safety blockers and numerical quality thresholds remain unchanged.

V2 corrects G09 to match section 82 of the authoritative specification: a plan may be prepared, so a plan and recipe are optional. It additionally requires an explicit public capture-approval notice for G09 and G10. G10 retains its required bounded investigation and recipe. Existing approval enforcement and the prohibition on automatic acquisition remain mandatory.

Dataset hashes and versions are recorded with each paid cohort. V1 paid artifacts are not overwritten or regraded as v2 acceptance. Any final v2 acceptance requires its own complete real cohort on the candidate implementation. See ADR 0025.
