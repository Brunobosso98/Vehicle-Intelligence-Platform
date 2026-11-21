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
expiry extensions are prohibited. The local Docker daemon is unavailable, so
fresh image findings are CI REQUIRED.

## Reproduction and trust checks

The acceptance binds a run to the exact clean Git SHA, locked dependencies,
definition fingerprint, seed, protocol, time cutoffs, source role, 9A feature
schema, dataset/label/oracle checksums, registered artifact checksum and 9G
report checksum. Same-seed reproduction compares actual model artifact bytes,
evaluation cohort and matched candidate metrics.

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

Local worktree checks completed on 2026-11-21: 42 focused Phase 10 unit tests
and all 1,500 API unit tests passed; API line/branch coverage was 95.98% /
90.16%. The full `make verify-cloud` target passed, including API and web
typing/lint/tests, the production web build, contracts/docs, Gitleaks,
`pip-audit`, and the Trivy filesystem scan. These checks do not replace fresh
database, artifact, container, CodeQL or exact-head CI evidence.

The dedicated Phase 10 and canonical full-validation workflows upload
checksum-bound receipts. The implementation has not yet been published and no
fresh Security/Dependency Review/CodeQL receipt exists for its final SHA. Security
status is therefore unresolved until the exact final SHA is scanned and the
expired-policy records are correctly reviewed or remediated.
