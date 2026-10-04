# Local stack not starting

Run make bootstrap, docker info, docker compose config --quiet and docker compose ps.
Inspect failed service logs and health status. Check 3000/5432/8000 port conflicts and disk space.
Docker Hub anonymous rate limits require an authenticated local registry setup or environment recovery;
never embed registry credentials or disable TLS. Cloud builds may need scripts/cloud-build.sh for CA trust.
Cache directories are .cache; no writable HOME assumption. `docker compose down` preserves application
DB volumes. Only test integration scripts delete their own disposable project volumes.

On Windows/WSL, check the Windows listener as well as Linux listeners when 5432 is unavailable.
An installed Windows PostgreSQL service may own the port; stop it only with the owner's approval
and an administrator PowerShell. Restore it after the Docker database releases the port.
The database healthcheck uses TCP so the temporary Unix-socket-only initdb server cannot start
migrations prematurely. Allow cold initialization and disk recovery to finish before retrying.
Cold database initialization has a three-minute healthcheck grace period followed by bounded
retries; a successful TCP probe still marks it healthy immediately.

Canonical Make targets build each distinct application image sequentially (`db`, `broker`,
`migrate`, `web`) before startup. API and consumer share the migration image. This avoids concurrent
Dockerfile frontend failures observed on Docker Desktop while preserving pinned Dockerfiles and
all security gates. Compose 5 always uses Bake: `COMPOSE_BAKE=false` and
`COMPOSE_PARALLEL_LIMIT=1` do not serialize its builds. `make up` and `make observability-up`
first execute `make containers`, then start the freshly built images with `--no-build --wait`.
If a build fails, startup is not executed; no previously built image substitutes for a failed gate.
