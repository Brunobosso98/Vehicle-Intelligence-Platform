# Container scan findings — 2026-10-01

## Current disposition

**Blocking; no exception is accepted for an unbuilt image.** The prior inspected API and Web
runtime images each reported 44 High occurrences and no Critical occurrences. Grouping the
machine-readable Trivy output produced eight unique CVEs; the 44 count was package occurrences,
not 44 vulnerabilities. Docker is not installed in the current closure environment, so the final
Dockerfiles could not be rebuilt or rescanned and the prior result cannot be promoted to current
acceptance evidence.

Both application images use Debian 13 (Trixie) slim runtime bases. The prior package versions below
match the Debian Trixie versions reported by the Debian Security Tracker. All packages were present
in the final runtime layers rather than only in a builder. They are OS/base-image packages, not
Python or Node production dependencies. The locked production dependency audits were rerun and
reported no known vulnerabilities.

## Unique finding inventory

| CVE                                                                          | Source / binary package(s)                                                                                    | Installed        | Upstream fixed version                                                          | Images / occurrences | Runtime exposure and disposition                                                                                                                                                                                                              |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------- | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | ncurses / libncursesw6, libtinfo6, ncurses-base, ncurses-bin                                                  | 6.5+20250216-2   | Debian unstable 6.6+20260608-2; no Trixie DSA                                   | API, Web / 4 each    | Flaw is in the `infocmp` CLI. The services do not invoke it and run without shell-driven input. Keep base patched; replace with a fixed stable Trixie package when published.                                                                 |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | systemd / libsystemd0, libudev1                                                                               | 257.13-1~deb13u1 | upstream 258.10/261.2; Debian unstable 262-1; no Trixie DSA                     | API, Web / 2 each    | Exploitation requires a local logged-in `systemd-homed` user. Containers do not run systemd/homed, have one non-root service user, drop all capabilities and are read-only. Refresh when Trixie publishes a fix.                              |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | acl / libacl1                                                                                                 | 2.3.2-2          | upstream/Debian unstable 2.4.0; planned for a Trixie point release              | API, Web / 1 each    | Requires a privileged caller using pathname ACL APIs on attacker-controlled paths. The applications neither call ACL APIs nor run privileged; read-only filesystems further constrain writes. Refresh at the next fixed Trixie point release. |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | util-linux / bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux | 2.41.5-0+deb13u1 | Debian unstable 2.42.3-1; no Trixie DSA                                         | API, Web / 9 each    | Requires privileged mount helpers and post-mount hooks. Runtime is non-root, drops every capability, has no host mount authority and does not invoke `mount`. Refresh when fixed in stable.                                                   |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | util-linux / same nine binaries/libraries                                                                     | 2.41.5-0+deb13u1 | Debian unstable 2.42.4-1; no Trixie DSA                                         | API, Web / 9 each    | Requires a privileged operator invoking `nsenter --join-cgroup` against an attacker-controlled target. `nsenter` is not an application code path and the container has neither privilege nor capabilities. Refresh when fixed in stable.      |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | util-linux / same nine binaries/libraries                                                                     | 2.41.5-0+deb13u1 | Debian unstable 2.42.3-1; no Trixie DSA                                         | API, Web / 9 each    | Requires an fstab-authorized unprivileged mount and Linux 6.15+ detached-tree path. The runtime does not invoke mounts, supply attacker-controlled fstab entries or retain mount capabilities. Refresh when fixed in stable.                  |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | util-linux / same nine binaries/libraries                                                                     | 2.41.5-0+deb13u1 | Debian unstable 2.42.3-1; no Trixie DSA                                         | API, Web / 9 each    | Requires SUID mount, a configured fstab bind mount and attacker control of its source path. None is exposed by the application; all capabilities are dropped. Refresh when fixed in stable.                                                   |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538)   | perl / perl-base                                                                                              | 5.40.1-6+deb13u1 | upstream Archive::Tar 3.10; Debian unstable perl 5.42.3-1; Trixie fix postponed | API, Web / 1 each    | Requires processing an attacker-crafted tar through Perl `Archive::Tar`. Neither service executes Perl or accepts archives. Do not add archive processing; refresh after Debian resolves upstream regression concerns.                        |

The occurrence arithmetic is `4 + 2 + 1 + (4 × 9) + 1 = 44` per image. Debian classifies each
stable-suite issue as minor, no-DSA, postponed, or planned for a point release. That differs from
Trivy's High classification but does not erase the scanner result.

## Narrow residual-risk records

Each row above is a finding-specific exposure analysis and remediation tracker. The security owner
is the repository maintainer. Mandatory review is **2026-11-01**, on any Trixie base digest refresh,
or when Debian publishes a fixed stable package, whichever occurs first. Current mitigations for
all eight findings are non-root UID/GID 10001, read-only filesystem, `no-new-privileges`, all Linux
capabilities dropped, no interactive users, and no vehicle-control or archive-upload surface.

These records are **not accepted exceptions in this run**: acceptance requires rebuilding and
rescanning the final runtime images, confirming installed versions and zero Critical findings, and
then reviewer approval. No `.trivyignore`, `--ignore-unfixed`, severity downgrade, excluded runtime
package, or ignored scanner exit code is used.

## Image-content and coverage status

### Third-party infrastructure scan

The current `make security` run reached the remotely retrievable
`timescale/timescaledb:2.30.2-pg17` image even though no local Docker CLI is installed. It found
one High Alpine package issue with a published fix (`libexpat` CVE-2026-93990, 2.8.4-r0 to
2.8.5-r0), plus bundled Go-binary findings: `gosu` contained 21 High and one Critical,
`timescaledb-parallel-copy` contained 29 High and two Critical, and `timescaledb-tune` contained
16 High. Examples of fixed Critical findings are CVE-2025-68121 in Go stdlib within `gosu`
(installed Go 1.24.6; fixed 1.24.13/1.25.7) and CVE-2026-33815 in pgx within
`timescaledb-parallel-copy` (installed 5.7.2; fixed 5.9.0).

Canonical GitHub Actions run
[`36945217453`](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/36945217453)
failed its image-security stage and final enforcement on this policy violation. A fresh scan of the
exact `2.30.2-pg17` digest found 70 High/Critical occurrences across 39 unique CVEs, including three
Critical findings: CVE-2025-68121 in `gosu` and CVE-2026-33815/CVE-2026-33816 in
`timescaledb-parallel-copy`. Each has a published fixed dependency/runtime version. Docker Hub
currently maps `latest-pg17` to the same digest, so no newer compatible official tag is available.

This upstream image therefore fails the Phase 0 zero-Critical deliverable policy. The repository
does not own those binaries, but must update to a safe supported Timescale release/tag before
closure. The scan driver now continues across every declared image, writes each machine-readable
report, accumulates failures, and exits non-zero at the end. This preserves fail-closed policy while
preventing one vulnerable infrastructure image from hiding the scan status of later images.

The Dockerfiles use multi-stage builds. The API runtime copies only its virtual environment,
Alembic configuration and migrations; uv is builder-only. The Web runtime copies Next standalone
output and static assets and explicitly removes npm/npx; pnpm remains builder-only. Neither recipe
installs compilers or git in the runtime. Python's standard library supplies the API health check,
and Node's built-in `fetch` supplies the Web health check, so curl/wget are unnecessary.

Prior runtime execution confirmed UID 10001. Compose declares read-only roots, `/tmp` tmpfs,
all capabilities dropped and `no-new-privileges`. Those controls and runtime contents require a
fresh image inspection before current acceptance. The database scan **FAILED**. Third-party findings
remain advisory-tracking responsibilities rather than first-party code ownership, but complete scan
evidence is still a Phase 0 prerequisite. The next canonical run will exercise the non-fail-fast scan
driver and retain per-image evidence for API, Web, Collector, Prometheus, Tempo, and Grafana even
when the database image continues to violate policy.

## Canonical rerun 36952758342

The hardened database runtime now scans with **0 Critical and 0 High** findings. Prometheus 3.15.0
also scans with **0 Critical and 0 High**. API/Web retain only the eight previously analyzed Debian
Trixie High CVEs and are evaluated through exact image/CVE/package acceptance records that expire
2026-11-01; any unlisted High or any Critical remains blocking.

Tempo 2.10.8, the latest patch in the existing 2.10 line, scans with 0 Critical and 12 High findings.
Grafana 12.4.12, the latest 12.4 patch, scans with 0 Critical and 2 High findings. Those exact
third-party findings are recorded with a shorter 2026-10-15 expiry because remediation requires a
vendor refresh or an explicitly tested Tempo 3/Grafana 13 migration. The observability profile binds
its administrative endpoints to loopback and is not a production deployment.

The available major-version candidates were also scanned before accepting that residual risk.
Tempo 3.0.3 retained the same 12 High findings, while Grafana 13.2.2 increased the result to 104 High
occurrences across 33 unique advisories. Neither candidate is a security remediation, and adopting
either would add major-version compatibility risk without reducing the relevant findings. The
working 2.10.8 and 12.4.12 releases therefore remain selected, with every exception scoped to its
exact immutable image digest. Collector 0.161.0 and Prometheus 3.15.0 were likewise digest-pinned;
both produced zero Critical and zero High findings in the canonical scan.

At that earlier scan, OpenTelemetry Collector 0.162.0 had no published container manifest, so the
repository retained 0.161.0. The 0.162.0 manifest is now published. The 2026-10-09 refresh moves
to its exact multi-platform digest and checks it under the same fail-closed policy.

## 2026-10-09 Go advisory refresh

The same database refresh found four High occurrences in the first-party hardened TimescaleDB
image: the two Go advisories below appeared in each of `gosu` and `timescaledb-tune`, which had
been compiled with Go 1.26.6. The helper builder now uses the pinned official Go 1.26.9 image
digest. A fresh build confirmed both helpers and PostgreSQL start, and a scan of the rebuilt
runtime image reports **zero High and zero Critical** findings. No database-image exception was
added.

The refreshed Trivy database reported two newly published Go standard-library High findings in
the pinned observability images. The exact image scans found 2 Collector, 4 Prometheus, 2 new
Tempo and 6 new Grafana occurrences, with zero new Critical findings. The extra Prometheus and
Grafana occurrences are repeated embedded binaries, not additional CVEs. The full image scans
still enforce every pre-existing finding through `container-risk-acceptance.yaml`.

The [Go advisory for CVE-2026-78667](https://pkg.go.dev/vuln/GO-2026-6609) describes CPU
exhaustion in `net/http` file-serving functions when parsing a Range header with many small ranges.
The [Go advisory for CVE-2026-97031](https://pkg.go.dev/vuln/GO-2026-6607) describes memory
exhaustion from malformed TLS ECH outer-extension references. Both were published on 2026-10-08
and are fixed in Go 1.26.9 or 1.27.2. Collector 0.162.0 contains Go 1.26.8, Prometheus 3.15.0
contains 1.27.1, Tempo 2.10.8 contains 1.26.5, and Grafana 12.4.12 contains 1.26.6 in the
scanned binaries. These are the latest compatible published image releases currently selected;
the Go fixes had not yet reached them at this scan.

The four images are enabled only by the local observability Compose profile, which publishes
their HTTP ports to `127.0.0.1`. This limits the Range-header denial-of-service path to local
callers. The profile configures no TLS/ECH listener, so the ECH server path is not exposed. Exact
image/CVE/package exceptions expire on 2026-10-15. The repository maintainer must refresh each
digest when a vendor image built with a fixed Go version is available; no Critical finding is
accepted.
