# Phase 11 reliability evaluation

No final reliability measurements are available yet. The deterministic provider is
for repeatable engineering checks and is not evidence of stochastic provider
reliability.

The current local suite `phase11-agent-evals-v30` defines 36 cases
(`suite-v26.json`, SHA-256
`72ac358fea2c4807b93bf95005e4fd4028edbf6462a72b3aa5d3d45ffb8a15bd`). No v30 disposable
execution or final-SHA reliability measurements are available yet. The HTTP runner is bounded to the
existing agent run timeout and 7C MCP/tool budgets. The environment used for this
implementation has no Docker binary, so latency, peak RSS, DB pool, tool timeout,
concurrency and cancellation benchmark results are `CI REQUIRED` or `NOT RUN`.

The current open-corpus dimensions are 3 benign, 2 critical, 20 red-team, 2 metamorphic, 8 fault
injection, and 1 provider-compatibility case. Severity counts are 15 critical, 16 major, 4 safety,
and 1 minor; languages are 24 English, 10 pt-BR, and 2 mixed. These are predeclared coverage
counts, not executed rates. Exact-SHA integration evidence is currently 0/36.

The receipt format and runner now record per-case end-to-end latency, time to the first
SSE event, routing duration, aggregate specialist work, tool-call duration and the RAG
tool subset. When provider responses expose it, the receipt also records token usage,
estimated cost and pricing version by run/routing/synthesis/specialist stage. CLI reports
calculate stage p50/p95/max with measured-case denominators. Specialist stage work can
overlap across concurrent specialists and is not an additive wall-clock decomposition.
Receipts also capture child-process peak RSS, user/system CPU time and process count.
The API stream reader enforces a 1 MiB cap while measuring SSE delivery.
The receipt checker requires a non-empty child resource measurement for integration
acceptance. These measurements have unit coverage only; disposable-stack values,
provider request latency, DB-pool pressure, and hardware context remain unmeasured. No
electrical energy measurement is available, and no energy claim is made.

Future reports must keep separate denominators for predeclared, attempted, executed,
fully graded, infrastructure-failed, skipped-budget, and not-run cases. Correct
abstentions/refusals count according to each case oracle. Critical failures must be
reported individually and cannot be hidden in an aggregate score.
