# Phase 11 reliability evaluation

No final reliability measurements are available yet. The deterministic provider is
for repeatable engineering checks and is not evidence of stochastic provider
reliability.

The versioned suite currently defines 21 cases. The HTTP runner is bounded to the
existing agent run timeout and 7C MCP/tool budgets. The environment used for this
implementation has no Docker binary, so latency, peak RSS, DB pool, tool timeout,
concurrency and cancellation benchmark results are `CI REQUIRED` or `NOT RUN`.

Future reports must keep separate denominators for predeclared, attempted, executed,
fully graded, infrastructure-failed, skipped-budget, and not-run cases. Correct
abstentions/refusals count according to each case oracle. Critical failures must be
reported individually and cannot be hidden in an aggregate score.
