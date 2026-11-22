# Phase 10 acceptance status

Status: NOT VERIFIED. The latest Phase 10 correction passes its focused local
checks; disposable-database and canonical Docker gates must pass on the final
branch SHA before verification.

## Current checkout evidence

On SHA `5b0c92f9f44945af0680b97474721b7ea48145e9`, the Phase 10 evaluator
completed and emitted a PASS receipt, then the independent checker failed on
its final lineage query because it selected `pulls.source_type`. The Phase 9A
schema stores that field on `driving_sessions`; the checker now joins each
immutable pull to its owning session and checks the session's source role.
The 52-test focused suite, Ruff, formatting and strict mypy pass locally. The
same SHA passed Quality, Integration E2E, Security, Dependency Review, both
CodeQL analyses, and Phase 9G/9H. The canonical full-validation workflow was
canceled after the Phase 10 failure and is not a pass. This focused acceptance
must pass before the full workflow is rerun.

The latest exact-head run, on SHA `da31da985ebf2f13cf62cf3ae7762606742238e1`,
completed the Phase 10 evaluator and wrote a PASS receipt, but the independent
receipt checker correctly failed closed: its query requested
`ml_model_versions.artifact_size_bytes`, a column absent from the existing 9B
registry schema. The checker now reads the registered artifact through a
private no-follow file descriptor, enforces the 50 MiB bound, measures the
actual bytes and verifies the registry checksum and Phase 10 receipt size. It
uses the stored size only for the 9C registry, which has that field. A focused
regression checks both query shapes, bounded reads and mismatch rejection.
The 51-test Phase 10 unit suite, Ruff, format check and strict checker mypy pass
locally after this correction. These results do not replace the required
disposable-database rerun.

On `da31da9`, Quality/Integration E2E, Security (including Dependency Review
and both CodeQL jobs), Phase 9G and Phase 9H passed. Phase 10 independent
acceptance failed only at the checker schema query above; the canonical Phase
0 full-validation run was canceled afterward and is not a pass. Every required
workflow must run again on the correction's exact final SHA.

After the Phase 9A lineage correction, local `make verify-cloud` passed: API
1,510 tests (95.83% line and 90.02% branch coverage), web 140 tests (91.96% line
coverage), production build, contracts, docs, Phase 0–5 deterministic checks,
analytics benchmark and cloud security checks. The analytics benchmark processed
600,600 observations in 46.71 seconds with 5,401,131 peak traced Python bytes.
Docker is unavailable locally, so database/container integration and the
canonical Phase 0–10 run remain `CI REQUIRED`; the local command is not exact-SHA
evidence.

The implementation worktree currently contains the additive 0020 migration,
fixed MLOps lifecycle, independent evaluator/checker, benchmark and
observability scripts, Phase 9H standalone regression changes, and dedicated
and canonical workflows.

Executed against the implementation worktree on 2026-11-22. The Phase 10
acceptance run on `2a9a91b5174a95f8114662d12aed5197b3f96c04` completed the
pipeline scenarios but failed while serializing a timezone-aware database
`datetime` in the final JSON receipt. The evaluator now converts aware
datetimes to ISO 8601 and UUID values to canonical strings before calculating
the receipt checksum and writing the report; naive datetimes and unsupported
values are rejected. These cases pass the focused test. The datetime fix was
published on SHA `246889c`.
That SHA's Quality job passed the API suite, web lint/typecheck/tests and
coverage, then stopped only because this report needed Prettier formatting.
The formatting correction passed the one-file Prettier check locally; this
final report update still needs exact-SHA CI:

| Check                                      | Result                                                                          | Evidence                                                             |
| ------------------------------------------ | ------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Phase 10 focused unit suite                | PASS: 51 tests                                                                  | `apps/api/tests/unit/test_mlops.py`                                  |
| Receipt serialization regression           | PASS: aware ISO 8601, UUID, scalar/nested values and invalid-value rejection    | `test_phase10_acceptance_report_normalizes_aware_database_datetimes` |
| Ruff, formatting and evaluator strict mypy | PASS on the modified evaluator and unit test                                    | Local focused checks                                                 |
| Full API unit suite                        | PASS on SHA `59d40e5`: 1,507 tests, 95.83% line and 90.02% branch coverage      | `make check-api`                                                     |
| Web, contracts, docs and production build  | PASS on SHA `59d40e5`; Next.js 16.4.6                                           | `make verify-cloud`                                                  |
| Analytics benchmark                        | PASS: 600,600 observations in 46.47 seconds; 5,398,831 peak traced Python bytes | `make verify-cloud`                                                  |
| 158-requirement traceability ledger        | PASS: exactly 158 mapped rows                                                   | `docs/validation/phase-10-traceability-ledger.md`                    |

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
occurrences, zero Critical and zero blocked findings. Phase 10 failed at final
report serialization on `2a9a91b` for `datetime`, then on `74797be` for a UUID
value also returned by a database-backed report. The serializer now handles
both supported types, and the focused Phase 10 unit suite passes. On SHA
`246889c`, Quality failed only at Prettier for this report; the API suite passed
1,508 tests with 95.83% line and 90.02% branch coverage. That formatting issue
was corrected and Quality passed on `74797be`. The full-stack run on `74797be`
was canceled after the Phase 10 failure and is not counted as a pass. The
current serializer fix must complete every required check on its exact SHA.

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
`1f667cd`, at the synthetic approval rationale on `59d40e5`, and during final
receipt serialization on `2a9a91b` (`datetime`) and `74797be` (`UUID`). On
`da31da9`, the evaluator scenarios and receipt completed, then the independent
checker queried an unavailable 9B registry size column. On `5b0c92f`, the
checker then queried `source_type` from `pulls` instead of its owning
`driving_sessions` row. Each cause has a targeted correction and regression
check. The Phase 10 and canonical full-stack receipts must rerun on the latest
correction SHA. Exact task/family metrics, row counts, drift windows and
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

- Commit and push the Phase 9A source-lineage checker fix and updated reports to the
  existing Phase 10 branch; PR #64 is already open and must remain unmerged.
- Run all required GitHub checks against the exact final SHA, including
  Quality, Integration E2E, Security, Dependency Review, CodeQL Python,
  CodeQL JavaScript/TypeScript, Phase 9G/9H regression, Phase 10 independent
  acceptance, and canonical Docker/full-stack Phase 0–10.
- Rerun Security and verify the dated image-exception policy against the final
  SHA. SHA `5b0c92f` passed its scan; the current checker correction SHA needs
  its own receipt.

Until these gates pass on the exact PR head, Phase 10 remains NOT VERIFIED.
