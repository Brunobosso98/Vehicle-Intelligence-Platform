# Phase 7D real evaluation

Use a dedicated OpenAI API project/key. Configure its provider-side ceiling at USD 5 separately;
the repository never changes billing settings. Supply the key through the local environment or
an already ignored `.env` file. Never paste it into prompts, reports or PR text. `.env` and
`.env.*` are ignored; `.env.example` contains names and safe defaults only.

Required configuration:

```text
VIP_AGENT_API_KEY=<local secret>
VIP_AGENT_MODEL=gpt-6-luna
VIP_AGENT_SERVICE_TIER=flex
VIP_AGENT_REASONING_EFFORT=low
VIP_7D_MAX_SPEND_USD=2.00
```

Verify current official [model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna)
and [pricing](https://developers.openai.com/api/docs/pricing) before running. The 2026-10-12
short-context Flex assumptions per million tokens are USD 0.05 input, USD 0.005 cached input
and USD 0.25 output. Long context is rejected by the harness. Reverify/update the rate provenance
if older than seven days. Estimates are not provider billing truth. Flex never falls back to
Standard or a different model automatically.

Run deterministic tests and security scanning first:

```sh
make test-phase7d-harness
make check-api
make verify
```

Paid execution requires a clean committed SHA and explicit operator confirmation:

```sh
make phase7d-smoke PHASE7D_ARGS=--confirm-paid-eval
make phase7d-real-eval PHASE7D_ARGS=--confirm-paid-eval
make phase7d-report
```

The suite command starts a disposable `vehicle_test*` database and runs canonical migrations.
The preflight displays model, tier, reasoning, case count, provider-call cap, spend limit and SHA.
The smoke is one controlled test with function calling and structured output; it is checkpointed
and reused by the suite. A failed/interrupted smoke stops execution. Before bulk spending,
free deterministic production-graph samples measure fixture prompt sizes and combine them with
observed smoke usage to forecast the suite cost. Projection above the limit stops bulk calls.
Normal `make verify` and GitHub push/PR CI do not invoke these paid targets.

Default limits: 120 end-to-end observations, 18 provider requests per case, 16 production model
steps, three domain specialists plus the Data Quality gate, 32 parent MCP calls plus eleven bounded Phase 7B reads (43 total), one telemetry window,
one infrastructure retry, one grounding correction and bounded model/run/case deadlines. The evaluation specialist deadline is 45 seconds; application defaults remain 25 seconds. One local read-only SSE reconnect targets the same durable run and never creates a new paid run.
The default spend threshold is USD 2; values above USD 5 or nonfinite values are rejected.
Per-call reservations prevent starting requests without remaining budget. Remaining cases are
budget-skipped when that threshold blocks execution. Skipped cases are never passes.

Raw artifacts and the ledger live in ignored `.validation/phase7d/`. Retain the entire directory
for resume. An operator lock prevents concurrent spenders. Invoke the same command to resume:
completed cases keep their results; interrupted cases keep their charged bound and are not
replayed automatically. Changed SHA/dataset/profile/rates are rejected. Interrupted observations
prevent verification; inspect their durable run handle and artifact before deciding on a bounded
operator rerun. Do not delete the checkpoint to force another full suite.

After a genuine general policy/architecture fix, one confirmation suite can be explicitly selected:

```sh
make phase7d-real-eval PHASE7D_ARGS='--confirm-paid-eval --confirmation-suite'
```

After general fixes, validate affected cases explicitly before full confirmation (specification section 95):

```sh
make phase7d-real-eval PHASE7D_ARGS='--confirm-paid-eval --confirmation-suite --operator-extra-suite --case-id A04 --case-id B01 --case-id G03'
```

Use the operator exception only when that additional schedule is already authorized. This example selects three immutable suite cases; selected critical cases also receive their two repeats. Preflight displays the actual selected count and projects only the selected schedule. Selection, SHA, limits, rates and cumulative spend are retained in the checkpoint. Resume must repeat the same case IDs and omit both round-start flags. Affected-case results cannot establish full 80-plus-40 acceptance.

Never-attempted cases marked NOT_RUN_EXTERNAL_BLOCKER may be resumed by another explicit paid invocation after the provider recovers. Old markers are audited; paid results, interrupted cases and retained usage reservations are preserved. A marker with any existing provider receipt is rejected rather than replayed.

Both suites share spend. The confirmation flag starts round two exactly once; omit `--confirmation-suite` when resuming an already started second round. A third full suite is rejected by default. Sections 95–96 require an explicit operator request for anything beyond two schedules. After concrete hardening and operator approval, an extra round can be started with `--confirm-paid-eval --confirmation-suite --operator-extra-suite`; spending remains shared and the USD 2 configuration is not raised. Further rounds require the same explicit round-start confirmation and operator authorization; every invocation remains limited to 120 observations and the accumulated spend ceiling. Omit both round-start flags when resuming an already started extra round. Do not tune repeatedly against exact
questions. Separate infrastructure failures from semantic failures. Individual bounded provider/runtime failures are recorded and the suite continues; three consecutive provider failures, authentication/configuration errors, harness failures or budget exhaustion stop spending. Internal specialist/tool deadlines are runtime failures, not OpenAI outages. Retain uncertainty, unsupported
signals and Phase 8 documentary gaps. Never approve/acquire data automatically for these fixtures.

Generate the JSON report, inspect failures and the human-review shortlist, and commit a sanitized
summary in `docs/validation/phase-7d-real-evaluation.md`. Include exact GitHub final-head gate links.
Only declare VERIFIED after the mandatory real suite, zero-tolerance metrics, quality thresholds
and all deterministic gates pass. Leave the PR open and unmerged.

Operator authorization on 2026-10-12 permits the additional rounds needed to finish validation while retaining a strict accumulated USD 2 ceiling. The default two-round limit remains for callers without explicit operator confirmation. Each invocation is bounded; no automatic evaluate/tune loop or model/tier fallback is added. Resume omits round-start flags and preserves all prior observations and cost reservations.

## Explicit attempt within the existing remaining budget

The default preflight stops when the projected full schedule exceeds the remaining ledger balance. If the operator explicitly requests continued attempts until the existing hard ceiling is reached, `--operator-budget-progress` records that choice in the immutable invocation identity and projection. It does not raise the configured limit, release reservations, bypass per-call checks, change model/tier, or claim the full schedule can finish. Results can terminate with SKIPPED_BUDGET_LIMIT and remain NOT VERIFIED.

```sh
make phase7d-real-eval PHASE7D_ARGS='--confirm-paid-eval --confirmation-suite --operator-extra-suite --operator-budget-progress'
```

The user explicitly authorized continued necessary calls within the accumulated USD 2 ceiling. This opt-in honors that instruction while retaining the default projected-cost admission rule for other callers. Resume keeps `--confirm-paid-eval --operator-budget-progress` and omits round-start flags. Never infer permission to increase spending from this option.
