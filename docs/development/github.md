# GitHub configuration

Trunk-based main, short-lived branches, required PRs. Enable a main ruleset requiring CI quality,
integration/E2E and security jobs; forbid direct/force pushes and deletion. Require current branches
where appropriate and reviewer approval once collaborators join. Give workflow tokens read-only scope.
Enable Dependabot alerts/updates, native secret scanning/push protection and private vulnerability reporting
when repository visibility/plan supports them. CodeQL supports Python and JS/TS; enable code scanning.
These remote settings are recommendations; Phase 0 does not mutate repository rules or push changes.
GitHub-hosted workflow execution and remote branch protection require repository-side review/configuration.

`full-validation.yml` is the canonical Phase 0 executor. It runs the repository's cloud-compatible
gate, builds the final Dockerfiles with commit metadata, validates disposable migrations and the real
stack/E2E/observability path, scans every declared image, and uploads commit-tied validation artifacts.
Require its `Canonical Docker and full-stack gate` job before Phase 0 completion.
