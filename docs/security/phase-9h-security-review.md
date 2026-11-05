# Phase 9H security review — 2026-11-05

**Reviewed Security gate status:** PASS on PR head
`e27dbc264558b6468846b5929ad197fa8b89cd94` in run
[`42112442920`](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/42112442920).
Trivy 0.76.1 found 95 High package occurrences across the selected runtime images; all matched
current image/CVE/package records, with 0 Critical and 0 blocked findings. Dependency Review and
both CodeQL jobs also passed on this exact SHA. The Security workflow did not retain downloadable
Trivy JSON; the final-image counts below come from the exact run log.

| Selected runtime image  | High / accepted | Critical | Policy result |
| ----------------------- | --------------: | -------: | ------------- |
| API                     |         46 / 46 |        0 | PASS          |
| Web                     |         45 / 45 |        0 | PASS          |
| Kafka                   |           0 / 0 |        0 | PASS          |
| TimescaleDB             |           0 / 0 |        0 | PASS          |
| OpenTelemetry Collector |           0 / 0 |        0 | PASS          |
| Prometheus              |           0 / 0 |        0 | PASS          |
| Tempo                   |           1 / 1 |        0 | PASS          |
| Grafana                 |           3 / 3 |        0 | PASS          |

The 95 accepted High occurrences remain visible residual risk and do not represent remediation.
API/Web `CVE-2026-76844` in zlib has a short expiry of 2026-11-12. The other package and vendor
image exceptions expire 2026-11-18 and require replacement/rescan as fixes become available.

The 2026-11-05 Trivy database introduced one new High occurrence in each application image. The
Security workflow did not publish its JSON reports. A local Trivy 0.76.1 scan of both exact pinned
base digests identified the new candidate as `CVE-2026-76844` in `zlib1g`
`1:1.3.dfsg+really1.3.1-1+b1`; the final-image count increased by exactly one in each image.
Debian bug #1153063 says Trixie remains vulnerable and contains an upstream backport patch, but no
fixed Trixie package is published. This identification is pending confirmation by the next exact
final-image scan. [Debian bug #1153063](https://go.mail-archive.com/debian-bugs-dist%40lists.debian.org/msg2131737.html)
and the [CVE description](https://www.suse.com/security/cve/CVE-2026-76844.html) describe a heap
buffer overflow after a failed write followed by a later `gz*` write.

The repository search found no direct zlib/gzip API calls in application code; the only match is a
test confirming that inbound `Content-Encoding: gzip` is unsupported. This does not prove that a
runtime dependency cannot reach the library behavior. The new exact API/Web exception is reviewed
through 2026-11-12 and requires a rebuild as soon as Debian publishes a stable fix. It is not a
remediation claim and does not renew any previous exception.

The canonical Docker/full-stack run on
`0ed6553243346e7bf37854d7722ea14570ea6eba` completed the Phase 0–9G regressions, but final
enforcement failed for generic E2E, container security and the preflight 9H research-summary
comparison. The refreshed records then passed the mandatory Security workflow on
`5ffe99d60d8e809450fd6177e8449c3780c1a442` (run `41906643193`): 93 accepted High package
occurrences, zero Criticals and zero blocked findings; Dependency Review and both CodeQL jobs also
passed. That is evidence for `5ffe99d`; the current release result is reported by the PR checks.

## Predictive operator boundary

The BFF is disabled by default and rejected in production. It uses a fixed configured API origin
and host allowlist, GET-only route grammar, server-only 9D bearer injection, a 30-minute
HMAC-protected session plus server-side revocation state, a separate operator credential, exact
Origin/Referer and CSRF checks, explicit vehicle UUID allowlists, fixed path/query validation,
login/request throttles, a four-request concurrency cap, eight-second timeout, one-megabyte
response cap, redirect rejection, abort support and private `no-store` responses. The same
predictive namespace is blocked through the generic domain proxy. API reads are vehicle-scoped,
bounded, read-only and nondisclosing for foreign IDs.

This is not customer identity, tenant isolation or vehicle-owner authorization. The boundary is
unsuitable for public ingress or shared users. Deployment and network controls must keep it local
or in a controlled test environment.

## Previous Security workflow image scan on `5ffe99d`

Security run `41906643193` scanned the images built from the PR code using Trivy 0.76.1 and
the refreshed 2026-11-04 database. Its job log records the policy totals; the Security workflow did
not publish downloadable machine-readable reports. The canonical run `41890926830` separately
retained detailed reports under
`security/images/`. Selected runtime totals were 93 High package occurrences and zero Criticals:

| Image                                 | Scan result         | Findings                                                                       |
| ------------------------------------- | ------------------- | ------------------------------------------------------------------------------ |
| `vehicle-platform-api:local`          | 45 High, 0 Critical | Eight previously reviewed Debian CVEs plus `CVE-2026-119373` in `libsqlite3-0` |
| `vehicle-platform-web:local`          | 44 High, 0 Critical | Eight previously reviewed Debian CVEs plus `CVE-2026-119373` in `libsqlite3-0` |
| `vehicle-platform-timescaledb:local`  | 0 High, 0 Critical  | Current hardened runtime image                                                 |
| `vehicle-platform-kafka:local`        | 0 High, 0 Critical  | Current patched Alpine runtime image                                           |
| Collector core 0.164.0, pinned digest | 0 High, 0 Critical  | Replaced the contrib image that contained affected go-jose                     |
| Prometheus 3.15.1, pinned digest      | 0 High, 0 Critical  | No current High or Critical findings                                           |
| Tempo 3.0.5, pinned digest            | 1 High, 0 Critical  | `CVE-2026-116587`, embedded go-jose 4.1.4                                      |
| Grafana 12.4.14, pinned digest        | 3 High, 0 Critical  | `CVE-2026-116587`, `CVE-2026-21728`, `CVE-2026-28377`                          |

The separate scan of the pinned upstream TimescaleDB base image reported 96 High and 3 Critical
occurrences. It is not the selected Compose runtime image and is not evaluated as a runtime image by
`scripts/security-policy.py`. The final TimescaleDB image scan reported zero High/Critical: the
Dockerfile rebuilds `gosu` and `timescaledb-tune` with the pinned Go 1.26.10 builder and removes the
vulnerable `timescaledb-parallel-copy` binary. No Critical finding is excepted for a selected
runtime image.

## API and Web package findings

At that earlier SHA, the images contained 89 High package occurrences across nine Debian CVEs. Debian's tracker
shows the listed Trixie packages remain vulnerable; fixes for several are available only in
unstable, and the remaining Trixie entries are no-DSA, postponed or awaiting a point release.
These are operating-system packages rather than locked Python or Node dependencies.

The newly reported `CVE-2026-119373` affects `libsqlite3-0` 3.46.1-7+deb13u2. Debian lists Trixie
as vulnerable and the fixed package in unstable. The upstream issue requires a detail=none FTS5
table with negative row IDs and then a prefix `MATCH` query. The application creates no FTS5 table
and issues no FTS5 `MATCH` query. Its SQLite embedding ledger uses ordinary tables and parameterized
queries; vehicle records use PostgreSQL. The finding is recorded separately for the exact API/Web
image aliases and package, with a short review expiry. [Debian's current SQLite tracker entry](https://security-tracker.debian.org/tracker/CVE-2026-119373)
documents the affected Trixie version and fixed unstable version.

The other Debian package groups and their application-level constraints are recorded in
[`container-risk-acceptance.yaml`](container-risk-acceptance.yaml): the ncurses issue is in the
unused `infocmp` CLI; the systemd issue requires a logged-in systemd-homed user; the ACL issue
requires a privileged pathname API call; the util-linux issues require privileged mount helpers,
`nsenter` or fstab-authorized mount flows; and the Perl issue requires processing a crafted archive.
These service containers run as UID 10001, read-only, with all capabilities dropped and
`no-new-privileges`; those constraints are mitigations, not claims that the packages are fixed.

## Vendor image review and residual findings

The current official Tempo release listing identifies 3.1.1 as latest; the repository's earlier
candidate scan found the same `go-jose` 4.1.4 finding in 3.1.1. The current official Grafana
listing identifies 13.3.0 as latest; the repository's candidate scan found 39 High occurrences, so
it was not selected as a security fix. No compatible candidate was established that removes the
remaining embedded-module findings. Tempo and Grafana bind to loopback; Tempo uses local storage
without OIDC/JWT/JWK authentication, and Grafana exposes anonymous Viewer access only. These
controls reduce reachability but do not remove binary findings.

The go-jose vendor fix is version 4.1.6 or later. Grafana's embedded Tempo module fixes the two
Tempo findings at 2.10.2 and 2.10.3 or later respectively. The time-bounded records identify these
specific remediation conditions and expire on 2026-11-18. See the [Tempo release history](https://github.com/grafana/tempo/releases),
[Grafana release history](https://github.com/grafana/grafana/releases), and
[go-jose advisory](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q).

## Reviewed exceptions and policy result

The 12 previously expired records were reviewed against the exact 2026-11-04 reports and current
vendor/Debian status. They now have `reviewed_on: 2026-11-04`, the `repository-maintainer` owner,
finding-specific mitigations and remediation conditions, and a short `2026-11-18` expiry. The
SQLite finding received an exact image/CVE/package record after source review. The new zlib record
has a separate 2026-11-12 expiry because Debian has not published a stable fix. No Critical finding
is excepted, no scanner scope was removed, and no severity was downgraded.

The old canonical run correctly failed because the policy rejected the expired records before it
could match findings. The refreshed exception file passed policy evaluation for the selected images
in Security run `41906643193`, with 0 Criticals and 0 blocked High findings; that result applied only
to `5ffe99d`. The new zlib record was then confirmed in the exact final-image scan on `e27dbc2` and
matched the reviewed API/Web exception. It does not convert the failed `5e402da` run into a pass.

## Dependency, filesystem and secrets scans

The exact canonical artifact reports zero High/Critical filesystem or IaC findings, zero locked
Python dependency findings, zero Node audit findings and an empty Gitleaks result. The earlier
dependency issue in `pypdf` 6.21.2 was fixed by pinning 6.21.4; the focused parser/security
regression passed 83 tests. The Alpine `libexpat` pins in TimescaleDB and Kafka were refreshed to
2.10.0-r0, and both selected images scanned with zero High/Critical findings.

## Exact-run failures and follow-up

The canonical report for `0ed6553` records:

- `E2E`: failed because a generic production-container browser test expected a test-only demo
  button, and it ran a live-oracle test without an oracle. Both cases are now gated against the
  actual server session response and the disposable-database harness.
- `Container security`: failed because records expired on November 1 and 2, 2026. Refreshed records
  passed the Security workflow on `5ffe99d` (run `41906643193`); fresh final-SHA scanning is still
  required.
- `Phase 9H`: stopped before disposable database/browser acceptance because the 9G bootstrap
  confidence-interval endpoint changed across fresh synthetic cohorts. A narrow 0.020 interval
  endpoint tolerance now validates finite, ordered, bounded intervals; all point metrics,
  thresholds, reliability bins and other aggregates remain exact.

The canonical report also shows Phases 0–9G, Docker builds, migrations, database, stack, stream,
observability, and historical E2E components passed. The 9H persisted-value parity, no-write digest,
and access-control browser checks remain unproved until the corrected exact-head acceptance job
completes.
