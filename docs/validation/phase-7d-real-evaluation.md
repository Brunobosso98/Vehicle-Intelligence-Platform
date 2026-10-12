# Phase 7D real evaluation report

**PHASE 7D — REAL MODEL VALIDATION & AGENT RELIABILITY BASELINE: NOT VERIFIED**

Real evaluation status: **PARTIAL**. The real smoke passed against commit `967c7d0d80a3fc4adbc3b73835324b87f8fe3a60` with two completed Responses calls, actual model `gpt-6-luna`, actual tier `flex`, low reasoning requested, function calling and structured output. Smoke cost: USD 0.00006245. Credentials were read from an external local file and never copied into the repository.

The first suite was interrupted at A04 by local PostgreSQL connection failure. Resume preserved A01–A03, marked A04 INTERRUPTED, and executed A05. A02/A03 passed; A01 failed supervisor output validation. A05 completed publicly but its optional performance specialist timed out. The harness incorrectly classified that internal timeout as a provider failure and stopped, leaving 115 observations unrun. Accumulated usage/reservations: USD 0.021768420. These partial observations do not establish baseline quality. A bounded confirmation suite is pending general reliability fixes.

The [specification](../prompts/phase-7d-real-model-validation.md) remains authoritative. This report is a working receipt and will be updated after every outstanding gate.

| Item | Requirement                                       | Current evidence                                                                                                |
| ---- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 1    | branch                                            | codex/phase-7d-real-model-validation                                                                            |
| 2    | base main SHA                                     | 9b2b2a621d0a903262e4a15a75ea4f102740d60a (branch baseline)                                                      |
| 3    | final HEAD                                        | Pending final committed delivery SHA                                                                            |
| 4    | Phase 7C VERIFIED confirmation                    | VERIFIED: PR #35 head 1a07ced07b85393b22b68da62dbcca357ba6d501; canonical GitHub SUCCESS                        |
| 5    | PR number/URL                                     | [PR #36](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/36), draft/open/unmerged            |
| 6    | model                                             | gpt-6-luna; actual smoke and partial-suite receipts                                                             |
| 7    | provider SDK/API                                  | openai 3.26.0 / Responses API (locked existing SDK)                                                             |
| 8    | service tier                                      | flex; no automatic Standard fallback                                                                            |
| 9    | reasoning effort                                  | low                                                                                                             |
| 10   | pricing verification date/rates                   | 2026-10-12; Flex short context: input $0.05/M, cached $0.005/M, output $0.25/M                                  |
| 11   | configured spend limit                            | Default USD 2.00; hard ceiling USD 5.00                                                                         |
| 12   | actual estimated total cost                       | USD 0.021768420 including retained unknown-usage reservations                                                   |
| 13   | unique cases executed                             | 4/80 executed; A04 interrupted; confirmation pending                                                            |
| 14   | critical repeats executed                         | 0/40; pending confirmation                                                                                      |
| 15   | provider failures/retries                         | One internal specialist timeout misclassified by initial harness; corrected classification pending confirmation |
| 16   | routing accuracy                                  | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 17   | specialist precision/recall                       | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 18   | unnecessary specialist rate                       | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 19   | evidence-reference validity                       | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 20   | unsupported factual claims                        | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 21   | unsupported causal claims                         | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 22   | unsupported diagnosis count                       | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 23   | cross-vehicle leak count                          | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 24   | tool-policy bypass count                          | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 25   | unsafe action attempts                            | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 26   | Phase 7B escalation accuracy                      | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 27   | invented signal count                             | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 28   | approval bypass count                             | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 29   | stability metrics                                 | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 30   | input tokens                                      | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 31   | cached input tokens                               | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 32   | output tokens                                     | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 33   | reasoning tokens if available                     | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 34   | cache ratio                                       | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 35   | p50/p95/p99 latency                               | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 36   | per-category results                              | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 37   | per-specialist usage                              | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 38   | worst-scoring cases                               | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 39   | human-review shortlist                            | NOT MEASURED — mandatory real suite incomplete                                                                  |
| 40   | fixes made because of real evaluation             | No real-evaluation-driven policy fix; configuration/metering and harness implementation only                    |
| 41   | deterministic regression result                   | make check-api PASS: 642 tests; line 96.13%, branch 90.87%; other gates pending                                 |
| 42   | security/secret scan                              | Secret scan executing; result pending                                                                           |
| 43   | GitHub deterministic CI/security/canonical checks | Phase 7D final-head remote gates pending                                                                        |
| 44   | recommended production model profile              | Calibration pending real data; intended Luna/Flex/low, bounded timeouts/calls, one retry                        |
| 45   | known limitations                                 | Credentials absent; harness integration, semantic completeness and final gates still under review               |
| 46   | Phase 8 deferred                                  | Technical-document retrieval/RAG deferred to Phase 8                                                            |
| 47   | PR remains unmerged.                              | PR not yet created; must remain open and unmerged                                                               |

Pricing provenance: [official Luna documentation](https://developers.openai.com/api/docs/models/gpt-6-luna) and [official pricing](https://developers.openai.com/api/docs/pricing), opened on 2026-10-12. Estimated from reported usage; not billing-system truth.

Phase 7C external evidence was rechecked with `gh pr view 35`: all quality, integration E2E, security, CodeQL, dependency review and canonical checks returned SUCCESS on the specified head. [Canonical run](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/38198158098). Historical Phase 7C records are unchanged.

No real model quality, safety rate, routing score, stability, token count or latency is claimed from deterministic tests. Human review and production calibration remain pending.

Executed harness evidence so far:

- `make test-phase7d-harness`: 85 deterministic tests passed, plus 23 targeted CLI tests after strengthening fatal receipt checks (dataset, exact questions, pricing, reservations, retry bounds, safe resume, redaction, independent grading, temporal checks, CLI and one-smoke checkpoint behavior).
- `make check-api`: 665 tests passed; line coverage 96.04%, branch 90.91%.
- `make check-web contracts-check docs-check`: passed.
- `make security-cloud`: passed; Gitleaks found no leaks, locked dependency audits and Trivy filesystem/IaC checks passed.
- Disposable harness acceptance: production API/MCP runs completed for A01, B01, G01 and H03. No paid calls or canonical domain mutation occurred. G01 exercised the existing Phase 7B capability/recipe/approval path. The independent graders rejected unrelated scripted answers for A01/B01 and accepted G01/H03. This validates rejection behavior; it is not real-model quality evidence.
- Initial `make verify` stopped on the committed specification's code-fence formatting. Only fence delimiters changed; all 143 sections and question text remain intact. The complete gate is running again.
- `graphify update .`: AST update executed without a model/API call. Generated parser caches are ignored; persistent graph artifacts are updated.

## General fixes prompted by real execution

- Strict supervisor routing schema includes only intent and specialists; usage comes from provider metadata. This follows the official [Structured Outputs requirements](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses). Application validation and dispatch policy remain authoritative.
- Distinguish internal run/specialist/tool deadlines from provider transport/authentication failures. Individual bounded failures remain observations; three consecutive provider failures, authentication/configuration errors, harness failures and budget exhaustion stop paid execution. Existing per-case retry and request caps remain enforced.
- Preserve the durable run ID and finish a failed checkpoint when Starlette wraps a database error after SSE has started.
- An absent public answer on a failed run is not an invented factual claim. The failed-run result remains a failure. Summary verification also requires meaningful missing evidence, signals, recipes, temporal context and refusal checks.
- The web acquisition test now waits for its EventSource before simulating offline. Targeted validation: seven tests passed. An intervening broad local test under concurrent Docker builds hit unrelated worker/test deadlines; final broad rerun remains required.
