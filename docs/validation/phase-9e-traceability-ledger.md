# Phase 9E traceability ledger

| ID     | Requirement                                                 | Implementation                                                     | Verification evidence                                                   |
| ------ | ----------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| P9E-01 | Versioned strict root, nodes, edges, facts, gaps and claims | `prediction_evidence/domain.py`, `builder.py`                      | Focused unit suite; acceptance graph oracle                             |
| P9E-02 | Deterministic identity and content checksums                | `canonical.py`, `builder.py`, repository replay                    | Canonical unit cases; sequential/concurrent replay receipts             |
| P9E-03 | Exact 9D receipt and historical approval event              | `repository.py`, `verifier.py`                                     | Independent receipt/binding/event row comparisons                       |
| P9E-04 | 9A source hash, feature schema, quality and cutoff          | `repository.py`, `builder.py`, `verifier.py`                       | Feature value/unit/hash/cutoff checks; late/naive timestamp cases       |
| P9E-05 | 9B task, model, label and NEXT_PULL boundary                | `repository.py`, `builder.py`                                      | Three-task receipts and no-target leak assertion                        |
| P9E-06 | 9C finding/run/reference, AFTER_PULL boundary               | `repository.py`, `builder.py`                                      | Four-family reference and finding comparisons                           |
| P9E-07 | No diagnosis, false probability or inferred corroboration   | Claim templates and fixed interpretations in `builder.py`          | Domain validation; interpretation and source relationship assertions    |
| P9E-08 | Immutable persistence, bounded graph and audits             | Migration `0017_prediction_evidence.py`; `repository.py`           | Migration round trip, trigger, FK, size, duplicate and rollback checks  |
| P9E-09 | Controlled HTTP and privacy-safe projection                 | `predictions/routes.py`, existing 9D budget middleware             | HTTP auth, peer, disabled, production, body, scope and disclosure cases |
| P9E-10 | Operator build/verify/inspect CLI                           | `prediction_evidence/cli.py`                                       | CLI help and guarded-operation unit/acceptance evidence                 |
| P9E-11 | Bounded operational telemetry                               | `observability/telemetry.py`, evidence service spans/metrics       | Evaluator checks exported series, spans and ID redaction                |
| P9E-12 | Independent disposable acceptance and benchmarks            | `scripts/evaluate_prediction_evidence.py`, `phase9e-validation.sh` | `.validation/phase9e/acceptance.json` uploaded by canonical workflow    |
| P9E-13 | Operator, architecture, threat and decision documentation   | Phase 9E architecture, ADR 0043, runbook and security docs         | `make docs-check`; review this ledger against final SHA                 |
| P9E-14 | No future phase or vehicle-control surface                  | No agent/MCP/UI/calibration/ECU integration added                  | OpenAPI route-set review and final diff review                          |

Final status is determined by the exact pushed commit and required GitHub checks. A local unit
pass or an older receipt cannot close a row requiring the disposable database or canonical CI.
