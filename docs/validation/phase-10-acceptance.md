# Phase 10 acceptance status

Status: NOT VERIFIED. The latest Phase 10 correction passes its focused local
checks; disposable-database and canonical Docker gates must pass on the final
branch SHA before verification.

## Current checkout evidence

The implementation worktree currently contains the additive 0020 migration,
fixed MLOps lifecycle, independent evaluator/checker, benchmark and
observability scripts, Phase 9H standalone regression changes, and dedicated
and canonical workflows.

Executed against the implementation worktree on 2026-11-22. The Phase 10
acceptance run on `2a9a91b5174a95f8114662d12aed5197b3f96c04` completed the
pipeline scenarios but failed while serializing a timezone-aware database
`datetime` in the final JSON receipt. The evaluator now converts aware
datetimes to ISO 8601 before calculating the receipt checksum and writing the
report; naive datetimes and unsupported values are rejected. This regression
passes its focused test. The correction and this report update are not yet
published:

| Check                                   | Result                                                                               | Evidence                                          |
| --------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------- |
| Check                                   | Result                                                                                  | Evidence                                           |
| --------------------------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Phase 10 focused unit suite             | PASS: 50 tests                                                                          | `apps/api/tests/unit/test_mlops.py`                |
| Datetime receipt regression             | PASS: aware ISO 8601, nested values, naive and unsupported-value rejection              | `test_phase10_acceptance_report_normalizes_aware_database_datetimes` |
| Ruff, formatting and evaluator strict mypy | PASS on the modified evaluator and unit test                                           | Local focused checks                               |
| Full API unit suite                     | PASS on SHA `59d40e5`: 1,507 tests, 95.83% line and 90.02% branch coverage               | `make check-api`                                   |
| Web, contracts, docs and production build | PASS on SHA `59d40e5`; Next.js 16.4.6                                                  | `make verify-cloud`                                |
| Analytics benchmark                     | PASS: 600,600 observations in 46.47 seconds; 5,398,831 peak traced Python bytes          | `make verify-cloud`                                |
| 158-requirement traceability ledger     | PASS: exactly 158 mapped rows                                                           | `docs/validation/phase-10-traceability-ledger.md`  |

These local checks are not exact-final-SHA proof. Docker CLI is unavailable in
this WSL distro. On `1f667cd03aeff9a92c19b7d2eee8b2563a7cc310`, Phase 9G, Phase
9H, Integration E2E, Security, Dependency Review and both CodeQL jobs passed.
Quality failed at 89.61% API branch coverage, and Phase 10 acceptance failed
while reading the active rollback binding (`PredictionKind` is a `Literal`, not
an enum). Both causes were corrected and focused checks passed.

On correction SHA `59d40e58823bab24114f508204a6732dc6c9f06a`, Quality, Phase
9G, Phase 9H, Integration E2E, Security, Dependency Review, CodeQL Python and
CodeQL JavaScript/TypeScript passed. Phase 10 acceptance failed at the 9D CLI
approval rehearsal because its synthetic-serving rationale omitted the
required `synthetic` scope; that cause was corrected. On SHA `2a9a91b`, Quality,
Integration E2E, Phase 9G, Phase 9H and Security (including Dependency Review
and both CodeQL jobs) passed. Phase 9H artifact `14732941722` verifies the
standalone `NODE_ENV=production` / `ENVIRONMENT=test` controlled flow, production
denial, persisted 9D/9E receipt reads and unchanged hashes across 43 source
tables. Security artifact `14732242668` reports 107 accepted High package
occurrences, zero Critical and zero blocked findings. Phase 10 failed only at
the final report JSON serialization described above. The old SHA's in-progress
full-validation run was canceled after this failure; it is not counted as a
pass. All required checks must run on the correction SHA.

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

The disposable Phase 10 evaluator failed at the rollback-binding snapshot on
`1f667cd`, at the synthetic approval rationale on `59d40e5`, and at final
datetime serialization on `2a9a91b`. Each cause has a targeted correction and
regression check. The Phase 10 and canonical full-stack receipts must rerun on
the correction SHA. Exact task/family metrics, row counts, drift windows and
performance will be recorded from the resulting checksum-bound artifacts,
never inferred from fixture definitions.

## Scientific and serving status

Synthetic calibration is not proof of real-world predictive validity. Phase
9B scores are not mechanical failure probabilities. Phase 9C anomaly scores
are not engine-health percentages or confirmed diagnoses. Unlabeled telemetry
cannot establish accuracy, recall or calibration. Real-world mechanical
failure predictive reliability remains NOT_ESTABLISHED.

Phase 10 proposals are review artifacts only. Existing Phase 9D authorization,
approval, activation, revocation and rollback remain authoritative.

## Current blockers

- Commit and push the serialization fix and report refresh to the existing
  Phase 10 branch; PR #64 is already open and must remain unmerged.
- Run all required GitHub checks against the exact final SHA, including
  Quality, Integration E2E, Security, Dependency Review, CodeQL Python,
  CodeQL JavaScript/TypeScript, Phase 9G/9H regression, Phase 10 independent
  acceptance, and canonical Docker/full-stack Phase 0–10.
- Rerun Security and verify the dated image-exception policy against the final
  SHA. SHA `2a9a91b` passed its scan; the correction SHA needs its own receipt.

Until these gates pass on the exact PR head, Phase 10 remains NOT VERIFIED.
