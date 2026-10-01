---
name: quality-gate
description: Validate a completed implementation before concluding or submitting it for review.
---

# quality-gate

Choose checks based on actual scope; run focused tests during development.
For Phase 0 completion, run `make verify`. Mandatory checks must fail visibly; never silently skip them.
Include lint, format, types, units, contracts, integration/E2E/build/migrations/security when applicable.
Report command, result, coverage, blocked checks with evidence, and unresolved risks.
See [Gate matrix](references/gates.md).
