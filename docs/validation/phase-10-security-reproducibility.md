# Phase 10 security and reproducibility review

## Current finding status

The latest exact-head Security run is
[44975653467](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44975653467),
artifact
[14735462917](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44975653467/artifacts/14735462917),
for SHA `c2ffa6a49009e87814a0e071cdbf6af10e4ecb78`. It reports the same 107
accepted High package occurrences, zero Critical and zero blocked findings
across selected images. The 20 exact risk reviews remain dated 2026-11-21 and
expire 2026-12-05. The expired zlib exception remains removed, and selected
application images have no zlib CVE. A new scan is required for the pending
matched-feature fingerprint correction SHA.

The policy on implementation SHA `74797be570e301444671cc9b307306647c15efcf`
contains 20 exact High-risk records, all reviewed on 2026-11-21 and expiring
2026-12-05. Fifteen older records had expired on November 18 or 20; commit
`f8dfe32` explicitly re-reviewed them and added five exact reviews for new
findings. No records are expired on the current scan date, and none was
silently extended. The old zlib exception for `CVE-2026-76844` expired
2026-11-12 and remains removed; the selected final API/Web images use patched
zlib, and the fresh scan reports no zlib CVE in them.

Security run [44966623657](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44966623657)
and [artifact 14731604483](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44966623657/artifacts/14731604483)
report 107 accepted High package occurrences and zero Critical or blocked
findings across the selected images: API 50, Web 48, Collector 1, Prometheus 2,
Tempo 2, Grafana 4, Kafka 0 and custom TimescaleDB 0. The upstream
`timescale/timescaledb:2.30.2-pg17` report separately contains 271 High and 3
Critical findings; that image is not selected for runtime, and the rebuilt
custom TimescaleDB image has zero High and Critical findings. No scanner is
disabled, no severity is changed, and the report retains upstream results.

Security run [44970219136](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44970219136)
and [artifact 14733790199](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44970219136/artifacts/14733790199)
are the successful exact-head scan for SHA `74797be`. A fresh scan is required
for the pending UUID serializer correction SHA. Docker CLI is unavailable in
this WSL distribution, so image scans run in GitHub Actions.

## Reproduction and trust checks

The acceptance binds a run to the exact clean Git SHA, locked dependencies,
definition fingerprint, seed, protocol, time cutoffs, source role, 9A feature
schema, dataset/label/oracle checksums, registered artifact checksum and 9G
report checksum. `vehicle-mlops reproduce --run-id` rebuilds the same 9B model
from its original training cohort in a private temporary directory and checks
the frozen 9G evaluation cohort using read-only scoring. This audit creates no
new experiment, run, registry row or evaluation record, and held-out scores
cannot select or tune a candidate. The independent checker repeats the
reconstruction and compares source, artifact, cohort and metric hashes while
verifying source and serving tables remain unchanged.

Registered artifacts are loaded through existing allowlisted 9B/9C serializers
and private trusted paths. The independent checker verifies path containment,
no symlink traversal, regular-file type, owner, private mode, size and content
checksum. Negative cases cover tampered bytes, unsafe serialized payload,
source-role spoof, source leakage, stale candidate, unauthorized reviewer,
invalid proposal checksum, expired lease and concurrent ownership.

Telemetry uses bounded OTel attributes and no vehicle/receipt/user identifiers
as metric labels. Reports use fixture IDs only where required by the disposable
database oracle; public or production APIs do not expose training or MLOps.

## Current execution status

The latest exact-head Phase 10 run on `c2ffa6a` generated its evaluator receipt,
then the independent checker compared pull IDs to a fingerprint of 9C matched
feature rows. The 9C row ID binds the 9A feature-set ID, source hash and
observation cutoff. The checker now independently reconstructs those rows from
the persisted feature set and version checksum before recomputing the
fingerprint.

The prior exact-head Phase 10 run on `5b0c92f` generated its evaluator receipt,
then failed in the independent checker because it queried `pulls.source_type`,
which actually belongs to the owning `driving_sessions` row. The checker now
joins the table by the persisted pull session ID and verifies the session's
source type without changing source data.

The preceding exact-head Phase 10 run on `da31da9` generated its evaluator receipt,
then failed in the independent checker because it queried the nonexistent
`ml_model_versions.artifact_size_bytes` column. The checker now measures 9B
artifact size from the safely opened file, enforces the byte bound and matches
the receipt checksum and size; a focused test covers the actual 9B/9C query
schemas. The current correction passes 52 Phase 10 unit tests, Ruff,
formatting and strict Mypy locally. `make check-api` on SHA `59d40e5` passed 1,507 API tests,
95.83% line coverage and 90.02% branch coverage. The preceding exact-head SHA
`1f667cd03aeff9a92c19b7d2eee8b2563a7cc310`
passed Phase 9G, Phase 9H, Integration E2E, Security, Dependency Review and
both CodeQL jobs. Its Quality check failed at 89.61% branch coverage, and its
Phase 10 evaluator failed at the active-binding snapshot due to treating the
`PredictionKind` typing alias as an enum. On correction SHA
`59d40e58823bab24114f508204a6732dc6c9f06a`, Quality, Phase 9G, Phase 9H,
Integration E2E, Security, Dependency Review and both CodeQL jobs pass. Its
Phase 10 independent acceptance failed because the 9D approval rehearsal
reason omitted the required explicit `synthetic` scope; the evaluator now
states that scope. On SHA `2a9a91b`, Quality, Integration E2E, Phase 9G, Phase
9H, Security, Dependency Review and both CodeQL jobs passed. Its Phase 10
acceptance completed lifecycle scenarios but failed to serialize a database
`datetime` in the final JSON receipt. On SHA `74797be`, it then exposed a UUID
in the same receipt. On `da31da9`, the evaluator completed and wrote a receipt,
but the independent checker queried the absent 9B artifact size column. The
focused regression and 51-test Phase 10 unit suite pass locally. Phase 9H's
exact-head artifact proves the standalone runtime gate and no source-table
mutation; the current checker correction SHA still needs disposable database
and full exact-head CI receipts. None of these local checks replace those gates.

The dedicated Phase 10 and canonical full-validation workflows upload
checksum-bound receipts. The implementation is published on the existing
Phase 10 branch and PR #64. The final report update will create a new SHA, so
the mandatory checks and container scan must complete against that exact final
SHA before declaring verified.
