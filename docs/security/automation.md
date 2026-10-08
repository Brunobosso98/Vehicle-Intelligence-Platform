# Security automation

`make security` requires gitleaks and Trivy. Install pinned release binaries using
`bash scripts/install-security-tools.sh`; tools go to .cache/bin and are not committed.
It scans first-party working-tree content, locked Python/Node production dependencies, filesystem/IaC
and all images declared in Compose (including the optional observability profile). No generic vulnerability exclusions are configured. Known Critical is
blocking; High must be fixed or have a finding-specific mitigation/owner/expiry reviewed in an exception.
Exceptions are explicit records in `docs/security/container-risk-acceptance.yaml`: each is scoped to exact images, CVE/package, owner, rationale and expiry. Critical findings are never excepted. Any High finding not matched by a current record blocks the gate. Vendor database/admin image scan completion is an explicit prerequisite; registry failures block the gate.

GitHub workflows run dependency audits, gitleaks, Trivy filesystem/images and CodeQL for Python/JS.
The named `dependency-review` check runs the complete locked Python and Node production audits plus
the filesystem/IaC scan. This is deliberately blocking and checks the full resolved dependency set:
GitHub's differential Dependency Review API cannot run while the repository Dependency Graph is
unavailable. If an administrator enables that graph, the differential action can be restored in
addition to—not instead of—the complete locked-dependency audit.
GitHub native secret scanning/push protection should be enabled in repository settings when supported.
Tools download vulnerability databases; network failure is a blocked check, never a clean result.
`TRIVY_CACHE_DIR` optionally selects the scanner cache location; the default remains `.cache/trivy`.
On WSL, a Linux filesystem cache avoids repeated database reads across the Windows mount. This
changes storage only; scanner scope, severity thresholds and exception policy are unchanged.
Filesystem scanning excludes installed dependency directories and generated builds/reports at any
depth. All first-party source, IaC and committed lockfiles remain included; locked dependencies
and canonical images receive their existing vulnerability audits.

`make security-cloud` runs the Docker-independent portion with machine-readable reports: Gitleaks,
locked Python/Node production audits, and Trivy filesystem/IaC. `make security` first runs that target,
scans every exact Compose image into `.validation/security/images`, then evaluates each report with
`scripts/security-policy.py`. Policy decisions are emitted under `.validation/security/policy` so an
accepted High remains visible in evidence. The reduced target does not imply that image security
passed; image results remain `CI REQUIRED` outside Docker-capable CI.
