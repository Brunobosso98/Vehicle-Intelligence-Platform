# Phase 11 reliability evaluation

No final reliability measurements are available yet. The deterministic provider is
for repeatable engineering checks and is not evidence of stochastic provider
reliability.

The current local suite `phase11-agent-evals-v41` defines 47 cases
(`suite-v37.json`, SHA-256
`d6ea1fe84fab05705a7577c1db2c375d11bf3a6bdc1f463c1fc5b7e4fb7eff0d`). No v41 disposable
execution or final-SHA reliability measurements are available yet. The HTTP runner is bounded to the
existing agent run timeout and 7C MCP/tool budgets. The environment used for this
implementation has no Docker binary, so latency, peak RSS, DB pool, tool timeout,
concurrency and cancellation benchmark results are `CI REQUIRED` or `NOT RUN`.

The current open-corpus dimensions are 3 benign, 2 critical, 20 red-team, 6 metamorphic, 15 fault
injection, and 1 provider-compatibility case. Suite v31 adds orphaned-run recovery, v32 adds API
database outage, v33 adds missing knowledge-index handling, v34 adds 9E checksum mismatch, v35
adds 9B/9C artifact unavailability, v36 adds direct 9D model-artifact rejection, and v37 adds a
transient MCP disconnect recovery. Suite v38 adds English and Portuguese nickname paraphrases; v39 adds a same-question 9F
authorization metamorph with no per-run evidence ID; v40 adds temporal source-order mutation; v41
adds concurrent oversize-request admission checks. Severity counts are 19 critical, 23 major,
4 safety, and 1 minor; languages are 32 English, 13 pt-BR, and 2 mixed. These are predeclared
coverage counts, not executed rates.
Exact-SHA integration evidence is currently 0/47.

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

The CLI `report` and `benchmark` outputs also compute a deterministic 95% percentile
cluster-bootstrap interval for the observed PASS rate. A cluster is
`attack_family × vehicle_fixture`, or `family × intent × vehicle_fixture` when no
attack family is registered. Each unique, fully graded case contributes to its
cluster mean; duplicate, unrun, incomplete, infrastructure-failed and budget-skipped
attempts do not enter the rate. The seeded bootstrap resamples clusters, not prompt
variants. With no graded cases or fewer than two independent clusters, the interval
is `UNDEFINED` with a reason and denominator. These intervals describe the tested
open corpus and deterministic provider only; they are not confidence bounds for
stochastic provider or real-world vehicle reliability.

## Historical worktree checkpoint — v38

Suite v38 adds two frozen nickname paraphrases in English and Portuguese. Both ask for the same
recorded vehicle fact, require the official `get_vehicle` tool, and use the same exact `/nickname`
oracle, including the inert instruction-like fixture value. The earlier v37 source mutation case
continues to verify that changing the canonical value changes the next answer and restoring the
source restores its digest. The suite then had 45 scheduled cases and SHA-256
`16b05ed861a5b44e05888e97b70db8b477587605f29a4838f65b59bb558b5664`.

`make test-agent-evals` passed 203 tests at this checkpoint. Disposable execution was 0/45 because
Docker was not available. Exact-SHA CI, hidden independent holdout selection, resource exhaustion
breadth, time/authorization metamorphs and remaining Phase 7B/9F/10 side-effect cases were still
outstanding. Phase 11 remained **NOT VERIFIED**.

## Historical worktree checkpoint — v39

Suite v39 contains 46 cases, including a paired 9F authorization metamorph: the same prediction
question is asked with the selected synthetic evidence ID and without it. The missing-ID run is
required to abstain and have no prediction evidence or successful prediction tool call. The frozen
suite SHA-256 is `09b323e66bb005f9e5b8497622f8f0c43e6cce4cdcfa6ae730f9baa58c33d15a`.

The focused evaluator suite passes 204 tests. `make verify-cloud` passed 1,731 API tests, 140 web
tests, API line/branch coverage 95.38%/90.10%, typing, Ruff, contracts, docs, formatting, production
build, deterministic Phase 0–5 checks and cloud security scans. Disposable execution remains 0/46;
Docker-backed acceptance is `CI REQUIRED`. Independent holdout selection, broader resource/time
metamorphs, and remaining authorization and Phase 7B/9F/10 action probes still block VERIFIED status.

## Current worktree checkpoint — v41

The 47-case v41 suite adds a paired temporal source-order metamorph and expands the API input-boundary
case to eight concurrent over-limit requests. The focused evaluator suite passes 205 tests.
Current-source `make verify-cloud` passes with 1,732 API tests, 140 web tests, 95.35%/90.07% API
line/branch coverage and all cloud-compatible checks. Exact-SHA CI run 45273030474 failed before
case execution because the egress firewall blocked the loopback-published Docker database after
DNAT; the report records zero attempts and zero provider calls. A second exact-SHA attempt
(`84f55a08e587fffef6d0a3b4e45de10738848362`) failed identically: the host's Docker path did not
match conntrack's original-destination rule. The source now inspects the disposable database
container IP and permits only TCP/5432 to that address; shell syntax and the cloud gate pass, but
Docker confirmation awaits a new final-SHA run. A third run on
`b6dff4c1e4b70c2ab7da8dff09e0050cecc0d6af` confirmed DB access and journaled 16 attempts, then
failed with HTTP 422 on `P11-RED-016`: the harness omitted the required prediction capability header.
The runner now supplies that ephemeral header only for explicitly authorized evidence reads, with
focused regression coverage. Exact-SHA run `f8a8b1465d867199f0baf662880082b0bc816ccc` passed CI,
Security, Phase 9G, Phase 9H, and Phase 10, then reached the same authorized 9E read and failed
because the independent source oracle expected projected `path` entries inside the immutable bundle;
the persisted 9E schema stores those outputs in typed bundle fields and model-version lineage. The
oracle now derives its eight expected facts from the accepted immutable bundle and its receipt-bound
model version. Exact-SHA run `5e049849f5778a872247631be5a2e0aed8347d34` passed that case and journaled
27 attempts, then failed while serializing `P11-PROVIDER-001`: the operator plan's nested scoring
threshold object did not fit the scalar-only direct-probe schema. The runner now deterministically
flattens nested scalar fields before recording and hashing the probe summary. `make test-agent-evals`
passes 208 tests; the runner passes strict mypy, and Ruff/format checks pass. The disposable
integration and final-SHA gates remain pending; the current branch is **NOT VERIFIED**. On `54076e7`, CI, Security,
Phase 9G, Phase 9H and Phase 10 passed; full validation was cancelled after the known Phase 11
failure. Independent holdout selection and broader cutoff/resource plus authorization/Phase 7B/9F/10
action coverage remain unresolved.
