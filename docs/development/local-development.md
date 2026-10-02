# Local development

Prerequisites: Node 24.19.0 LTS, pnpm 11.19.0 (`npm install -g pnpm@11.19.0`), Python 3.12.14,
uv 0.12.19, Docker Engine and Compose v2, Make/Bash. No cloud credentials or private services.
`make bootstrap` creates a local .env once and installs frozen locks; safe to rerun.
`make up` builds apps, starts DB, runs the one-shot migration, then waits for app health.
Web: http://localhost:3000; API: http://localhost:8000; docs: /docs.
`make down` preserves application data. Local example credentials must not be reused elsewhere.

For hot reload: make db-up, make db-migrate (build the API image first), then make dev-api and
make dev-web in separate terminals. Host DATABASE_URL uses 127.0.0.1; Compose uses db.
API_BASE_URL is server-only. Missing mandatory config fails startup; production DB requires explicit
credentials and TLS. APP_VERSION defaults to 0.1.0; optional GIT_SHA and timezone-aware BUILD_TIMESTAMP
come from build arguments/runtime environment. Backend always uses UTC internally.

Checks: make check-api, make check-web, make contracts-check, make test-integration.
Install browser with `pnpm --filter @vehicle-platform/web exec playwright install --with-deps chromium`
when system package installation is available; PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright.
`make test-e2e` uses a running real stack. `make verify` builds and starts the stack and runs all gates;
it deliberately leaves application stack/data available for inspection. make observability-up enables
local traces/metrics views. See docs/security/automation.md for scanner prerequisites.

Executor split: `make verify-cloud` is the complete non-container gate for Codex Cloud. It includes
format/lint/types/unit coverage, contracts/generated synchronization, production Web build,
documentation, locked dependency audits, secret scanning and filesystem/IaC scanning. `make verify`
remains the complete Docker/full-stack gate. When Docker is unavailable, its container, Compose,
database, integration, E2E, image-security and full-observability checks are `CI REQUIRED`, not passed.
The GitHub Actions `full-validation` workflow is the canonical Phase 0 executor and must pass before
Phase 0 can be declared complete.

Codex Cloud: caches live in .cache; frozen installs need only public registries. A restricted network
can block browser/scanner/image downloads; record exact failures. Pass proxy CA as BuildKit secret via
scripts/cloud-build.sh; never commit a session certificate or proxy credentials. See completion report
for which container variants were actually validated in the current environment.

If Docker Hub is rate-limited, `bash scripts/cloud-validation.sh` prepares explicitly named
validation-only source images. It prints the Compose/test overrides for verification. This
alternative is recorded separately from a canonical upstream-image build; it does not bypass
network policy and does not waive scanner findings. Docker >=24 is required for the built-in
BuildKit secret/permission features. Runtime images apply available OS updates and must be rescanned.
