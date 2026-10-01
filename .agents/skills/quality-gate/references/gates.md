# Gate matrix

- API: make check-api; contract regeneration/check when API changes.
- Web: make check-web and make build; E2E for user-visible flows.
- Database: make test-integration, with clean/prior/rollback migrations.
- Infrastructure: Compose render, container builds, startup/health and security scans.
- Full Phase 0: make verify plus observability profile export/view verification.
  A blocked environment is a limitation, never a passed gate. Preserve failure artifacts without secrets.
