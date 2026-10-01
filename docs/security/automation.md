# Security automation

`make security` requires gitleaks and Trivy. Install pinned release binaries using
`bash scripts/install-security-tools.sh`; tools go to .cache/bin and are not committed.
It scans first-party working-tree content, locked Python/Node production dependencies, filesystem/IaC
and all images declared in Compose (including the optional observability profile). No generic vulnerability exclusions are configured. Known Critical is
blocking; High must be fixed or have a finding-specific mitigation/owner/expiry reviewed in an exception.
No exception exists initially. Vendor database/admin image scan completion is an explicit prerequisite; registry failures block the gate.

GitHub workflows run dependency audits, gitleaks, Trivy filesystem/images and CodeQL for Python/JS.
Dependency review may require public repository or GitHub Advanced Security availability; see workflow.
GitHub native secret scanning/push protection should be enabled in repository settings when supported.
Tools download vulnerability databases; network failure is a blocked check, never a clean result.
