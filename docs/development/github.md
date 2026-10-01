# GitHub configuration

Trunk-based main, short-lived branches, required PRs. Enable a main ruleset requiring CI quality,
integration/E2E and security jobs; forbid direct/force pushes and deletion. Require current branches
where appropriate and reviewer approval once collaborators join. Give workflow tokens read-only scope.
Enable Dependabot alerts/updates, native secret scanning/push protection and private vulnerability reporting
when repository visibility/plan supports them. CodeQL supports Python and JS/TS; enable code scanning.
These remote settings are recommendations; Phase 0 does not mutate repository rules or push changes.
GitHub-hosted workflow execution and remote branch protection require repository-side review/configuration.
