# Phase 10 security and reproducibility review

## Current finding status

The current checked-in container policy has 15 exception records that expired:
13 on 2026-11-18 and two on 2026-11-20. They have not been silently extended.
The old zlib exception expiring 2026-11-12 was removed after patched zlib was
verified in the November 14 API/Web image builds; that historical Trivy scan
found neither CVE-2026-76844 nor CVE-2026-85091. It does not prove the final
Phase 10 image is clean or that the November 21 image has been rescanned.

The final API, Web, database, broker and observability images require a fresh
Trivy database and exact-image scan. Any remaining High findings must match
specific unexpired reviewed policy records; expired, unmatched High or any
Critical blocks acceptance. Scanner exclusions, severity downgrades and policy
expiry extensions are prohibited. Docker CLI is unavailable in this WSL
distribution, so fresh image findings are CI REQUIRED.

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

The current reproduction correction passed 45 focused Phase 10 unit tests,
changed-module Ruff and formatting checks, API typing for the MLOps modules,
strict typing for the independent checker and benchmark, and Python compilation
on 2026-11-21. Earlier `make verify-cloud` evidence on the implementation
before this correction reported 1,500 API tests, 95.98% line and 90.16% branch
coverage, web checks and filesystem scans; it must be rerun for final-source
acceptance. None of these local checks replace disposable database, artifact,
container, CodeQL or exact-head CI evidence.

The dedicated Phase 10 and canonical full-validation workflows upload
checksum-bound receipts. The implementation has not yet been published and no
fresh Security/Dependency Review/CodeQL receipt exists for its final SHA. Security
status is therefore unresolved until the exact final SHA is scanned and the
expired-policy records are correctly reviewed or remediated.
