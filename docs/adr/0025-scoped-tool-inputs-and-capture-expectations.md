# ADR 0025: Scoped tool inputs and capture expectations

- Date: 2026-10-14
- Status: Accepted for implementation; full real confirmation pending.

## Context

Affected round fourteen completed 23 observations on b3260fd: 14 passed, nine failed semantically and none failed provider availability. Remaining observations exposed rejected tool contexts, specialists spending their last turn on reads, numerical answers obscured by incidental metadata, and an evaluator that did not recognize canonical gap statistics or indexed telemetry measurements.

The authoritative specification, section 82, says a G09 plan may be prepared. Dataset v1 instead required both a plan and a recipe. The approval requirement itself must remain explicit even when existing evidence makes further capture unnecessary.

## Decision

Advertise the existing specialist permissions in per-turn tool schemas using owned, current-run entity IDs. Preserve nullable configuration filters, original cardinality and source schemas; omit a tool when its required known IDs cannot satisfy its prerequisites. The existing application ownership, role permissions and context checks remain authoritative. Function parameters retain the existing explicit non-strict mode; The model receives these ID choices; the host still validates all arguments. See the [official function-calling documentation](https://developers.openai.com/api/docs/guides/function-calling).

Reserve the existing last specialist turn for a typed draft by advertising no tools on that turn. Do not increase turns, retries, byte limits, tool limits or spending. Prioritize actual performance quantities and actual point values before incidental metadata.

Data Quality may read its already permitted session summaries to assess reliability even when that reliability blocks domain interpretation. Other specialists remain blocked. Record each selected but blocked role as the existing `skipped` status with `quality_gate_blocked`, zero calls, zero tokens and no findings. These records describe selection and blocked execution; they do not claim that a model ran. The existing streams and HTTP schema already support this status. Reported-role coverage is distinct from actual model/tool calls and receipts.

Recognize canonical recorded signal-gap counts/durations as quality evidence and numeric telemetry point values through their exact canonical source channel. Require a unique supported value and matching source unit; reject unknown channels, unsupported values, nulls, unrelated sources and unrelated sample counts. No acceptance threshold changes and no historical regrading.

Retain immutable suite v1 and add suite v2. Both contain the same 80 questions, fixtures, specialist constraints, 20 critical questions and 40 repeats. V2 makes the G09 plan/recipe optional in accordance with section 82 and requires a public, application-owned explicit capture-approval notice for both G09 and G10. G10 still requires its bounded investigation and recipe. The independent grader rejects a missing notice. No automatic capture or approval is added.

Prompt markers become grounded-v6, data-quality-v6, performance-v7, thermal-v6 and fuel-air-boost-v6. Supervisor hashes include routing-hints 1.5, scoped-tool-schemas 1.0, specialist-terminal-draft 1.0 and quality-blocked-role-records 1.0.

## Evidence and limits

The new Data Quality read regression failed on the prior guarded implementation and passed after correction; the metadata-refresh regression remained passing. Tests preserve the prohibition on domain execution when quality fails and assert zero calls/tokens for each skipped record. Other tests cover owned and guessed IDs, foreign vehicle/run/session evidence, unique comparison IDs, nullable filters, last-turn budget preservation, canonical numerical semantics, capture notices and unchanged v1/question/repeat definitions.

Original paid results, receipt reservations and costs remain immutable. Round fourteen ended at accumulated USD 3.081113650 of the authorized USD 4.00. The new cohort must execute all 120 observations with suite v2; it cannot combine results from different candidate sources. Final real confirmation, human review, canonical gates and the deferred graph update remain required.

Integrated `make check-api` passed 865 tests, typing/lint and coverage (96.07% line, 91.39% branch). A separate immutable D05 review recognizes its supported numeric throttle point and changes only question-evidence coverage; historical receipts remain unchanged.
