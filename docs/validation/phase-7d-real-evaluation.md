# Phase 7D real evaluation report

**PHASE 7D — REAL MODEL VALIDATION & AGENT RELIABILITY BASELINE: NOT VERIFIED**

Real evaluation status: **NOT RUN**. Credentials are now available through an external local file; the committed real evaluation is pending. The explicit smoke command failed with `VIP_AGENT_API_KEY_missing_no_request_sent` before provider I/O. The full mandatory suite has not been executed. Deterministic results are harness evidence only.

The [specification](../prompts/phase-7d-real-model-validation.md) remains authoritative. This report is a working receipt and will be updated after every outstanding gate.

| Item | Requirement                                       | Current evidence                                                                                  |
| ---- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 1    | branch                                            | codex/phase-7d-real-model-validation                                                              |
| 2    | base main SHA                                     | 9b2b2a621d0a903262e4a15a75ea4f102740d60a (branch baseline)                                        |
| 3    | final HEAD                                        | Pending final committed delivery SHA                                                              |
| 4    | Phase 7C VERIFIED confirmation                    | VERIFIED: PR #35 head 1a07ced07b85393b22b68da62dbcca357ba6d501; canonical GitHub SUCCESS          |
| 5    | PR number/URL                                     | Pending PR creation                                                                               |
| 6    | model                                             | gpt-6-luna (configured baseline; real execution NOT RUN)                                          |
| 7    | provider SDK/API                                  | openai 3.26.0 / Responses API (locked existing SDK)                                               |
| 8    | service tier                                      | flex; no automatic Standard fallback                                                              |
| 9    | reasoning effort                                  | low                                                                                               |
| 10   | pricing verification date/rates                   | 2026-10-12; Flex short context: input $0.05/M, cached $0.005/M, output $0.25/M                    |
| 11   | configured spend limit                            | Default USD 2.00; hard ceiling USD 5.00                                                           |
| 12   | actual estimated total cost                       | USD 0.00 spent; no real provider request sent                                                     |
| 13   | unique cases executed                             | 0/80; NOT RUN                                                                                     |
| 14   | critical repeats executed                         | 0/40; NOT RUN                                                                                     |
| 15   | provider failures/retries                         | No real requests; credential preflight failed before network I/O                                  |
| 16   | routing accuracy                                  | NOT MEASURED — mandatory real suite not run                                                       |
| 17   | specialist precision/recall                       | NOT MEASURED — mandatory real suite not run                                                       |
| 18   | unnecessary specialist rate                       | NOT MEASURED — mandatory real suite not run                                                       |
| 19   | evidence-reference validity                       | NOT MEASURED — mandatory real suite not run                                                       |
| 20   | unsupported factual claims                        | NOT MEASURED — mandatory real suite not run                                                       |
| 21   | unsupported causal claims                         | NOT MEASURED — mandatory real suite not run                                                       |
| 22   | unsupported diagnosis count                       | NOT MEASURED — mandatory real suite not run                                                       |
| 23   | cross-vehicle leak count                          | NOT MEASURED — mandatory real suite not run                                                       |
| 24   | tool-policy bypass count                          | NOT MEASURED — mandatory real suite not run                                                       |
| 25   | unsafe action attempts                            | NOT MEASURED — mandatory real suite not run                                                       |
| 26   | Phase 7B escalation accuracy                      | NOT MEASURED — mandatory real suite not run                                                       |
| 27   | invented signal count                             | NOT MEASURED — mandatory real suite not run                                                       |
| 28   | approval bypass count                             | NOT MEASURED — mandatory real suite not run                                                       |
| 29   | stability metrics                                 | NOT MEASURED — mandatory real suite not run                                                       |
| 30   | input tokens                                      | NOT MEASURED — mandatory real suite not run                                                       |
| 31   | cached input tokens                               | NOT MEASURED — mandatory real suite not run                                                       |
| 32   | output tokens                                     | NOT MEASURED — mandatory real suite not run                                                       |
| 33   | reasoning tokens if available                     | NOT MEASURED — mandatory real suite not run                                                       |
| 34   | cache ratio                                       | NOT MEASURED — mandatory real suite not run                                                       |
| 35   | p50/p95/p99 latency                               | NOT MEASURED — mandatory real suite not run                                                       |
| 36   | per-category results                              | NOT MEASURED — mandatory real suite not run                                                       |
| 37   | per-specialist usage                              | NOT MEASURED — mandatory real suite not run                                                       |
| 38   | worst-scoring cases                               | NOT MEASURED — mandatory real suite not run                                                       |
| 39   | human-review shortlist                            | NOT MEASURED — mandatory real suite not run                                                       |
| 40   | fixes made because of real evaluation             | No real-evaluation-driven policy fix; configuration/metering and harness implementation only      |
| 41   | deterministic regression result                   | make check-api PASS: 642 tests; line 96.13%, branch 90.87%; other gates pending                   |
| 42   | security/secret scan                              | Secret scan executing; result pending                                                             |
| 43   | GitHub deterministic CI/security/canonical checks | Phase 7D final-head remote gates pending                                                          |
| 44   | recommended production model profile              | Calibration pending real data; intended Luna/Flex/low, bounded timeouts/calls, one retry          |
| 45   | known limitations                                 | Credentials absent; harness integration, semantic completeness and final gates still under review |
| 46   | Phase 8 deferred                                  | Technical-document retrieval/RAG deferred to Phase 8                                              |
| 47   | PR remains unmerged.                              | PR not yet created; must remain open and unmerged                                                 |

Pricing provenance: [official Luna documentation](https://developers.openai.com/api/docs/models/gpt-6-luna) and [official pricing](https://developers.openai.com/api/docs/pricing), opened on 2026-10-12. Estimated from reported usage; not billing-system truth.

Phase 7C external evidence was rechecked with `gh pr view 35`: all quality, integration E2E, security, CodeQL, dependency review and canonical checks returned SUCCESS on the specified head. [Canonical run](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/38198158098). Historical Phase 7C records are unchanged.

No real model quality, safety rate, routing score, stability, token count or latency is claimed from deterministic tests. Human review and production calibration remain pending.

Executed harness evidence so far:

- `make test-phase7d-harness`: 67 deterministic tests passed (dataset, exact questions, pricing, reservations, retry bounds, safe resume, redaction, independent grading, temporal checks, CLI and one-smoke checkpoint behavior).
- `make check-api`: 657 tests passed; line coverage 96.04%, branch 90.91%.
- `make check-web contracts-check docs-check`: passed.
- `make security-cloud`: passed; Gitleaks found no leaks, locked dependency audits and Trivy filesystem/IaC checks passed.
- Disposable harness acceptance: production API/MCP runs completed for A01, B01, G01 and H03. No paid calls or canonical domain mutation occurred. G01 exercised the existing Phase 7B capability/recipe/approval path. The independent graders rejected unrelated scripted answers for A01/B01 and accepted G01/H03. This validates rejection behavior; it is not real-model quality evidence.
- Initial `make verify` stopped on the committed specification's code-fence formatting. Only fence delimiters changed; all 143 sections and question text remain intact. The complete gate is running again.
- `graphify update .`: AST update executed without a model/API call. Generated parser caches are ignored; persistent graph artifacts are updated.
