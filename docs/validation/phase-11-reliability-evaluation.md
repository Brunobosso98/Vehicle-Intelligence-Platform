# Phase 11 reliability evaluation

No final reliability measurements are available yet. The deterministic provider is
for repeatable engineering checks and is not evidence of stochastic provider
reliability.

The current versioned suite `phase11-agent-evals-v18` defines 24 cases
(`suite-v14.json`, SHA-256
`769a231f3994c0fba07e27081a68398beeb198cea78a13106e2202b0aea2390e`). No v18 disposable
execution or final-SHA reliability measurements are available yet. The HTTP runner is bounded to the
existing agent run timeout and 7C MCP/tool budgets. The environment used for this
implementation has no Docker binary, so latency, peak RSS, DB pool, tool timeout,
concurrency and cancellation benchmark results are `CI REQUIRED` or `NOT RUN`.

Future reports must keep separate denominators for predeclared, attempted, executed,
fully graded, infrastructure-failed, skipped-budget, and not-run cases. Correct
abstentions/refusals count according to each case oracle. Critical failures must be
reported individually and cannot be hidden in an aggregate score.
