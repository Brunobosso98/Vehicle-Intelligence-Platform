---
name: quality-gate
description: Validate a completed implementation before concluding or submitting it for review.
---

# quality-gate

Choose checks based on actual scope; run focused tests during development. Before the Phase 0 gate,
detect both the Docker CLI and daemon as described in the gate matrix. Run `make verify` when Docker
is available; otherwise run `make verify-cloud` and label every Docker-dependent check `CI REQUIRED`.
Missing Docker is never successful container validation. Mandatory checks must fail visibly.
Report command, result, coverage, blocked checks with evidence, and unresolved risks.
See [Gate matrix](references/gates.md).
