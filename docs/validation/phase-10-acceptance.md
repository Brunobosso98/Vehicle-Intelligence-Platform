# Phase 10 acceptance status

Status: NOT VERIFIED. This report separates executed local checks from the
disposable database, Docker and exact-head GitHub Actions gates still required.

## Current checkout evidence

The implementation worktree currently contains the additive 0020 migration,
fixed MLOps lifecycle, independent evaluator/checker, benchmark and
observability scripts, Phase 9H standalone regression changes, and dedicated
and canonical workflows.

Executed against the implementation worktree on 2026-11-22. The code fixes are
published on the existing branch at `59d40e58823bab24114f508204a6732dc6c9f06a`;
the report corrections in this update are not yet pushed, so the local checks
below are not final-SHA receipts:

| Check                                   | Result                                                                               | Evidence                                          |
| --------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------- |
| Phase 10 focused unit suite             | PASS: 49 tests                                                                       | `apps/api/tests/unit/test_mlops.py`               |
| API unit suite                          | PASS: 1,507 tests; 95.83% line and 90.02% branch coverage                            | `make check-api`                                  |
| Web checks                              | PASS: lint, typecheck, 140 tests; 91.96% line coverage                               | `make verify-cloud`                               |
| API typing and MLOps script strict mypy | PASS: 206 API source files and 5 strict script files                                 | `make verify-cloud`                               |
| Ruff and formatting                     | PASS: 356 Python files; Prettier clean                                               | `make verify-cloud`                               |
| Contracts, docs and production build    | PASS; Next.js 16.4.6                                                                 | `make verify-cloud`                               |
| Secret and dependency scans             | PASS: Gitleaks no leaks; pip-audit no known vulnerabilities; cloud Trivy scan passed | `make verify-cloud`                               |
| Analytics benchmark                     | PASS: 600,600 observations in 46.47 seconds; 5,398,831 peak traced Python bytes      | `make verify-cloud`                               |
| 158-requirement traceability ledger     | PASS: exactly 158 mapped rows                                                        | `docs/validation/phase-10-traceability-ledger.md` |

These are local source checks, not final exact-head CI proof. Docker CLI is
unavailable in this WSL distro. On the preceding candidate SHA
`1f667cd03aeff9a92c19b7d2eee8b2563a7cc310`, Phase 9G, Phase 9H, Integration
E2E, Security, Dependency Review and both CodeQL jobs passed. Quality failed at
89.61% API branch coverage, and Phase 10 acceptance failed while reading the
active rollback binding (`PredictionKind` is a `Literal`, not an enum). Both
causes were corrected and focused checks passed.

On correction SHA `59d40e58823bab24114f508204a6732dc6c9f06a`, Quality, Phase
9G, Phase 9H, Integration E2E, Security, Dependency Review, CodeQL Python and
CodeQL JavaScript/TypeScript passed. The fresh Security artifact reports 107
accepted High package occurrences, zero Critical and zero blocked findings.
Phase 10 independent acceptance failed at the 9D CLI approval rehearsal:
the synthetic-serving approval reason omitted the required explicit
`synthetic` scope. The evaluator now includes that scope; its focused Ruff,
formatting, strict Mypy and compile checks pass. Canonical Docker/full-stack
validation was still running when this report was refreshed. The report/code
update creates a new SHA, so all required checks must finish on that final SHA
before delivery.

## Required independent acceptance

The exact-head job runs scripts/phase10-validation.sh in a disposable
vehicle_test database. It round-trips migration 0020, runs database-backed
state/immutability tests, uses the existing 9A/9B/9C/9G paths for all three
supervised tasks and four anomaly families, performs matched comparisons and
adversarial checks, then reconstructs one completed supervised candidate in a
temporary artifact root and independently verifies artifact bytes, matched
metrics, frozen evaluation lineage, unchanged database tables, dossiers,
source digests, run/stage transitions and receipt checksum. Reproduction does
not create a second pipeline or evaluation record. The workflow also writes
benchmark and OTel receipts.

The canonical full-validation job runs the real packaged Phase 9H standalone
image and browser regression, security scanning, all prior phase checks, and
the Phase 10 evaluator on its final commit SHA.

The disposable Phase 10 evaluator on `1f667cd` failed at its final rollback
binding snapshot; the corrected evaluator on `59d40e5` reached 9D approval but
failed because the test rationale omitted the explicit synthetic scope. That
scope is corrected locally and the exact-head acceptance must rerun. Exact
task/family metrics, row counts, drift windows and performance will be recorded
from the resulting checksum-bound CI artifacts, never inferred from fixture
definitions.

## Scientific and serving status

Synthetic calibration is not proof of real-world predictive validity. Phase
9B scores are not mechanical failure probabilities. Phase 9C anomaly scores
are not engine-health percentages or confirmed diagnoses. Unlabeled telemetry
cannot establish accuracy, recall or calibration. Real-world mechanical
failure predictive reliability remains NOT_ESTABLISHED.

Phase 10 proposals are review artifacts only. Existing Phase 9D authorization,
approval, activation, revocation and rollback remain authoritative.

## Current blockers

- Commit and push this report refresh to the existing Phase 10 branch; PR #64
  is already open and must remain unmerged.
- Run all required GitHub checks against the exact final SHA, including
  Quality, Integration E2E, Security, Dependency Review, CodeQL Python,
  CodeQL JavaScript/TypeScript, Phase 9G/9H regression, Phase 10 independent
  acceptance, and canonical Docker/full-stack Phase 0–10.
- Rerun Security and verify the dated image-exception policy against the final
  SHA. The correction-SHA scan passed; the report-only SHA needs its own receipt.

Until these gates pass on the exact PR head, Phase 10 remains NOT VERIFIED.
