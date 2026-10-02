# PHASE 0 COMPLETION REPORT

Date: 2026-10-01.

## PHASE 0 STATUS: NOT COMPLETE

The engineering foundation is implemented and substantially validated, but this closure environment
does not have the Docker CLI. Consequently the mandatory canonical image, Compose, database,
observability and complete security reruns were not executable, and `make verify` returned 2.
The mandatory complete gate failed on proven environment and security blockers. Do not start
Phase 1 as if all foundation acceptance criteria had passed.

The validation model is now explicit: Codex Cloud runs `make verify-cloud` for every legitimate
non-container check, while GitHub Actions `full-validation` is the canonical Docker/full-stack
executor. The cloud gate passed locally, but creating the workflow is not execution evidence.
Container builds, stack/database/integration/E2E, image security and full observability remain
**CI REQUIRED** until that commit-tied workflow runs successfully.

## Closure rerun result

A detached checkout at commit `99b5356` bootstrapped successfully with initially empty isolated uv
and pnpm caches. After deleting application build outputs, `make verify-local` passed from that clean
tree: frozen installs, Python and TypeScript lint/types/unit coverage, contracts, documentation,
formatting and the production Web build all passed. Current locked Python and Node production audits
also returned no known vulnerabilities.

The canonical `make verify` rerun passed its complete local/static section and production build, then
failed at `docker compose build` because `docker` is not installed (shell exit 127; Make exit 2).
This is neither a Docker Hub rate limit nor evidence of an upstream outage. API/Web builds, metadata,
runtime UID/content, local stack, migrations, E2E, full observability and image scans are therefore
**NOT RUN** for the final source state. Historical evidence below is retained but is not substituted
for final acceptance.

## Architecture

Modular FastAPI monolith with explicit HTTP/config/database/observability boundaries, separate
Next.js UI, generated contracts and optional local observability. No future domain/services are faked.
Permanent observation-only vehicle safety boundary. Nine ADRs record decisions and actual trade-offs.

## Repository

Strict Python/TypeScript tooling, exact direct pins, uv.lock and pnpm-lock.yaml; root/nested context,
four progressive-disclosure skills, developer commands, security policies, contribution instructions,
architecture/data/versioning docs, current runbooks and Phase 1 outline.

## Applications

API /health/live, /health/ready, /version, OpenAPI and /metrics work. Errors are sanitized and
correlated. Config validates mandatory DB URL, production TLS, optional metadata and UTC timestamps.
Web status shell uses generated contracts through a server-only proxy with loading/failure/retry,
error boundary, keyboard focus and accessibility. No telemetry dashboard or agent feature is claimed.

## Database

PostgreSQL 17.11 and TimescaleDB 2.30.2 were compiled from official pinned source archives with
recorded SHA256 hashes because Docker Hub pulls were blocked. Migration 0001 activated TimescaleDB
on a clean disposable database; downgrade preserves extension deliberately; re-upgrade and repeated
head passed. Only Alembic metadata is in the public schema. Upstream Timescale container equivalence
was not verified. Local foundation uses one development principal; production roles are a future rollout concern.

## Observability

A real network request /health/ready with request ID `phase0-real-trace` generated trace
`dbc674760edd910fc1416a590e1d8fba`. The real OTel Collector received this ID, matching JSON app logs.
Request counters/duration were visible through /metrics; readiness failure counter was observed while
DB was stopped. Real OTLP HTTP delivery and W3C correlation also have automated tests.
Full provisioned Tempo/Grafana profile failed on registry HTTP 503; visualization in those components
was not verified. JSON stdout is the Phase 0 structured-log solution; Loki was deliberately omitted.

## Testing and coverage

Unit, contract, Python/TS type, lint/format and Next production build passed in the original workspace.
Real disposable DB integration and two Playwright smoke tests passed. Axe reported no violations;
keyboard access and API failure/retry were exercised. Chromium 151 installed in the environment was
used; downloading the pinned Playwright browser was denied by network policy.
34 backend units passed (99.63% lines, 96.88% branches); 9 web units passed (100% each).
Static context results and detailed evidence are in [validation evidence](../testing/validation-evidence.md).
Backend executable first-party code enforces separate 90% line and branch thresholds; frontend
logic/components enforce 85% in each dimension. Migrations are tested by integration, generated code
and declarative framework configuration are excluded from unit coverage for documented reasons.

## Security

Gitleaks found no secrets. Initial locked production Python/Node audits found no known vulnerabilities;
a subsequent mandatory rerun failed on public-registry HTTP 503, so the security gate remains non-zero.
Trivy filesystem/IaC reported zero High/Critical findings after fixes. Final inspected app images had
0 Critical, 44 High each, without available FixedVersion in the scanner. No blanket suppression or
exception was added. Completed container scans cover the two app images; upstream database and
observability image scan completion remains blocked/unverified and is required by the security command. See [finding inventory](../security/container-findings.md).
The initial fallback Critical findings were corrected by Trixie/updates and removing build-only npm
from the Node runtime. Non-root/read-only/capability restrictions remain in place.

## CI/CD

PR/push workflows configure frozen installs, lint/format/types/unit/contracts/build, real DB tests,
container startup, E2E, coverage/debug artifacts, security audits/scans, CodeQL and dependency review
when supported. Dependabot and concurrency cancellation configured; action refs pinned to verified
commit hashes. No remote workflow run, branch protection, deployment or cloud provisioning performed.

## Codex context

AGENTS created: root, apps/api, apps/web, packages/contracts and infra. Skills created manually in
supported YAML/frontmatter format: feature-delivery, architecture-decision, database-migration and
quality-gate. Each has narrowly scoped trigger text and separate reference material.

## Validation

Executed commands and precise results: [validation evidence](../testing/validation-evidence.md).
Canonical `make verify` returned non-zero on canonical Node image metadata HTTP 429; an earlier build also failed registry HTTP 503.
No check was converted into a skip or hidden success. The fallback web runtime received a permissions
repair layer and npm removal matching the corrected source recipes; a full clean rebuild of the final
Dockerfiles was blocked by registry failures. Do not represent that runtime test as a canonical rebuild.

Follow-up on 2026-10-01: PyPI, npm and GitHub HTTP probes returned 200, and
`docker manifest inspect node:24.19.0-trixie-slim` succeeded. Locked production Python and Node
dependency audits were rerun and reported no known vulnerabilities. The earlier 429/503 failures
are historical evidence, not proof of a continuing outage. Their origin was not isolated between
the external services and the environment proxy. Full canonical image downloads/builds, empty-cache
bootstrap and the observability profile still require successful reruns. At that point, the 44 High
package findings per image were known to represent eight distinct CVEs, but advisory/exposure triage
was incomplete; absence of a scanner FixedVersion did not establish that remediation was impossible.

Closure update: empty-cache locked installation and a clean-artifact production build now pass.
The eight prior unique CVEs have been individually mapped to Debian packages, upstream fixes,
runtime reachability and review conditions in the finding inventory. Because final images could not
be built or scanned here, those records are not accepted exceptions and the image gate remains open.
The current security rerun passed secret scanning, locked dependency audits and filesystem/IaC
scanning, then failed on the pinned third-party Timescale image. Its bundled Go binaries contain
fixed Critical findings, so the zero-Critical requirement is independently unmet; fail-fast behavior
left the remaining image scans not run.

## Known limitations

- The current closure environment has no Docker CLI. Canonical images, the Compose stack, database
  validation, E2E, observability backends/failure behavior and all image scans could not run.
- Earlier HTTP 429/503 registry events are historical only; they are not treated as current permanent
  unavailability. Fresh Python and Node dependency downloads succeeded in this closure rerun.
- Chromium download was denied (`Domain forbidden`); local installed browser validated E2E.
- Final-image confirmation of the eight historically observed High CVEs remains unavailable; no
  accepted exception exists without a fresh canonical scan.
- The pinned Timescale image currently reports Critical bundled-binary vulnerabilities with upstream
  fixes; selecting and validating a safe supported upstream release remains required.
- Full observability visualization, failure recovery and remote CI/rulesets remain unverified.
- Docker vfs exhausted the 32GB workspace during repeated builds; generated build cache/dangling
  images were reclaimed, and builds serialized. Application data was not deleted.

## Deferred deliberately to Phase 1+

Vehicle/telemetry/session/modification models, immutable raw datasets, import/idempotency,
hypertables, event detection, streaming, analytics, MCP, agents, RAG, ML/MLOps/evals and cloud.

## Files worth reviewing

[README](../../README.md), [Makefile](../../Makefile), [API factory](../../apps/api/src/vehicle_platform/main.py),
[configuration](../../apps/api/src/vehicle_platform/core/config.py), [migration](../../apps/api/migrations/versions/0001_timescaledb.py),
[web shell](../../apps/web/src/app/page.tsx), [Compose](../../compose.yaml), [CI](../../.github/workflows/ci.yml),
[threat model](../security/threat-model.md), [finding inventory](../security/container-findings.md), [task map](phase-0.md).

## ADRs created

0001 modular monolith; 0002 polyglot toolchain/Mypy; 0003 TimescaleDB;
0004 OpenTelemetry and released contrib numbering exception; 0005 contracts;
0006 Codex context; 0007 trunk-based development; 0008 ESLint official compatibility bridge;
0009 runtime security and validation-only fallback.

## Recommended first task for Phase 1

First close the listed Phase 0 blockers and rerun canonical make verify plus full observability profile.
Then implement Vehicle/VehicleConfiguration with identifiers, migrations, typed contracts and real
integration tests, following [the Phase 1 outline](phase-1-outline.md).
