# Contributing

Read README and docs/development/local-development.md; run make bootstrap.
Use short-lived feat/, fix/, chore/, docs/ or refactor/ branches from main. Prefer Conventional Commits.
Run focused checks while developing and relevant quality gates before a PR. Regenerate changed
contracts; use new Alembic revisions and isolated migration tests. Record significant lasting choices
in numbered ADRs with alternatives and consequences. Never add dependencies or future services without use.

Definition of Done: acceptance behavior, typing, lint/format, meaningful tests, errors/logging/signals,
security, relevant documentation, contracts/migrations and CI pass, with limitations reported honestly.
PR template accepts N/A for irrelevant sections. No production data/secrets or unsafe vehicle control.
See docs/development/github.md for recommended main protection and repository security settings.
