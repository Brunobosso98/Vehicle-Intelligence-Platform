# Phase 9H security review — 2026-11-04

**Disposition: NOT VERIFIED.** The 9H code adds a disabled-by-default development/test historical
operator surface. Fresh scans show High findings and recorded exception dates have expired on
November 1 or 2, 2026. No expiry was extended to force a passing result.

## Boundary implemented

The BFF uses a fixed configured origin and host allowlist, GET-only route grammar, server-only 9D
bearer injection, a 30-minute HMAC-protected session plus server-side revocation state, a separate
operator credential, exact Origin/Referer and CSRF checks, shared explicit vehicle UUID allowlists,
fixed path/query validation, login/request throttles, a four-request concurrency cap, eight-second
timeout, one-megabyte response cap, redirect rejection, abort support and private `no-store`
responses. The same predictive namespace is blocked through the generic domain proxy. API reads are
vehicle-scoped, bounded, read-only and nondisclosing for foreign IDs.

This is not customer identity, tenant isolation or vehicle-owner authorization. The boundary is
unsuitable for public ingress or shared users; deployment and network controls must keep it local
or in a controlled test environment.

## Fresh image scans

Trivy 0.76.1 was installed from the pinned release checksum in `scripts/install-security-tools.sh`;
its database was refreshed on 2026-11-04. Exact registry images were scanned by digest into ignored
`.validation/phase9h/security/` reports.

The first 2026-11-04 locked Python dependency audit identified seven High advisories in `pypdf`
6.21.2, used only by the isolated PDF extraction worker. The exact pin and lockfile were updated to
6.21.4. The subsequent locked `pip-audit` reported no known vulnerabilities, and the focused PDF
parser/security regression passed 83 tests.

The first exact-head Docker workflows exposed stale `libexpat` pins in the hardened TimescaleDB and
Kafka images: Alpine had advanced from `2.9.0-r0` to `2.10.0-r0`, but the Dockerfiles still requested
the older version after `apk upgrade`. Both recipes now pin `2.10.0-r0`. Final-head image build,
scan, and database acceptance are required to validate this fix.

The latest local `make security-cloud` run passed the knowledge-security check, gitleaks (no
secrets), locked `pip-audit` (no known vulnerabilities) and the production Node audit. Its Trivy
filesystem/IaC scan did **not** produce a result: Trivy 0.76.1 exited with
`helm scan config error: context deadline exceeded` under its default five-minute scan timeout.
This is an incomplete scan, not a clean report. A retry with the documented longer timeout and the
exact-head Security job remain required.

| Image                                                                                            | Finding                                                                                              | Action/status                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| OpenTelemetry Collector contrib 0.164.0                                                          | 1 High, `CVE-2026-116587`, go-jose 4.1.5 (fixed 4.1.6)                                               | Replaced with official core 0.164.0 digest `sha256:28b6d41ac51bff6b41ba5e8fe503569ffb9d6a1ea90f7a78419e86f34e44f750`; Trivy core scan reported 0 High/Critical. Runtime component compatibility still requires CI. |
| Tempo 3.0.5 digest `sha256:54bfbf8713813b5eb56e0ddf580553f48f9d55d7d8b15159159c91ecfdb5b949`     | 1 High, `CVE-2026-116587`, go-jose 4.1.4 (fixed 4.1.6)                                               | Existing exception expired 2026-11-02; retained visibly, not extended. Tempo 3.1.1 was also scanned and retains the finding.                                                                                       |
| Grafana 12.4.14 digest `sha256:ae509d9ae8c1021ca32ec370a9ca975d40165eda9fccd1e1102d317ff8787cd7` | 3 High: `CVE-2026-116587` go-jose 4.1.4; `CVE-2026-21728` and `CVE-2026-28377` embedded Tempo module | Existing exceptions expired 2026-11-02; not extended. Grafana 13.3.0 candidate reported 39 High occurrences and was not adopted.                                                                                   |
| API and Web built images                                                                         | Recorded package-specific Debian High findings                                                       | Docker is unavailable locally, so current exact built-image scan and policy result are **CI REQUIRED**. Eight existing finding exceptions expire 2026-11-01 and remain expired.                                    |

The collector change is limited to the configured core receiver/exporter/processors and health
check. Canonical Docker validation must prove the image starts with the checked-in config and
passes OTLP/health smoke before the replacement is operationally accepted.

The policy in [security automation](automation.md) blocks unlisted High and all Critical findings;
expired exceptions do not authorize a pass. `make security-cloud` covers locked dependencies,
secrets and filesystem/IaC only. Full image and exception evaluation requires `make security` in
Docker-capable CI.

## Required follow-up

1. Scan final source/API/Web images through the canonical policy on the exact PR SHA.
2. Fix introduced High/Critical findings; do not extend existing expiries outside the documented
   policy review and approval process.
3. Confirm the core Collector configuration starts and passes health/OTLP smoke.
4. Require Security, Dependency Review and both CodeQL workflows to pass on the same final SHA.
