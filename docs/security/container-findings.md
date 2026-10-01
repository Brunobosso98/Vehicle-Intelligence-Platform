# Container scan findings — 2026-10-01

**Blocking, no exception accepted.** Final inspected API/web images: 0 Critical and 44 High
package findings each, representing eight distinct CVEs repeated across binary packages.
These correspond to the CVEs listed below, with no FixedVersion returned
by the inspected Trivy database. An absent FixedVersion is not evidence that remediation is
impossible, or that the vulnerability is exploitable in this runtime; finding-specific advisory
and exposure analysis remains incomplete. Application Python/Node production dependency audits
passed earlier, a later rerun failed on HTTP 503, and a follow-up rerun on 2026-10-01 passed both.
The complete container/security gate has not passed.

The initial Bookworm fallback had Critical findings and was replaced. Runtime Trixie updates
fixed available OpenSSL/PCRE findings. Bundled npm's Critical tar finding was removed by excluding
npm/npx from the final Node runtime; npm remains in the builder only. No vulnerability IDs have
been suppressed. Non-root/read-only/capability restrictions reduce exposure but are not an accepted
substitute for this gate. Before closing Phase 0: use an upstream-fixed base or review each finding
with evidence, package/scope, mitigation, owner and expiry. This report is not such an exception.

| CVE            | Severity | Packages                                                                                         | Upstream status | Fix evidence             |
| -------------- | -------- | ------------------------------------------------------------------------------------------------ | --------------- | ------------------------ |
| CVE-2025-69720 | HIGH     | libncursesw6, libtinfo6, ncurses-base, ncurses-bin                                               | affected        | No fixed version in scan |
| CVE-2026-16742 | HIGH     | libsystemd0, libudev1                                                                            | affected        | No fixed version in scan |
| CVE-2026-54369 | HIGH     | libacl1                                                                                          | affected        | No fixed version in scan |
| CVE-2026-76642 | HIGH     | bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux | affected        | No fixed version in scan |
| CVE-2026-78408 | HIGH     | bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux | affected        | No fixed version in scan |
| CVE-2026-78409 | HIGH     | bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux | affected        | No fixed version in scan |
| CVE-2026-78410 | HIGH     | bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux | affected        | No fixed version in scan |
| CVE-2026-9538  | HIGH     | perl-base                                                                                        | fix_deferred    | No fixed version in scan |
