# Gate matrix

- API: make check-api; contract regeneration/check when API changes.
- Web: make check-web and make build; E2E for user-visible flows.
- Database: make test-integration, with clean/prior/rollback migrations.
- Infrastructure: Compose render, container builds, startup/health and security scans.
- Executor selection: run `command -v docker >/dev/null && docker info >/dev/null 2>&1`.
  If true, use `make verify`. If false, use `make verify-cloud` and report container builds,
  Compose/database/integration/E2E, image scans and full observability as `CI REQUIRED`.
- Codex Cloud gate: `make verify-cloud` covers all non-container static, unit, build, dependency,
  secret and filesystem/IaC validation.
- Full Phase 0: `make verify` locally with Docker, or the canonical GitHub Actions
  `full-validation` workflow. Phase completion requires the latter to execute successfully.
  A blocked environment is never a passed gate. Preserve failure artifacts without secrets.
