# Local stack not starting

Run make bootstrap, docker info, docker compose config --quiet and docker compose ps.
Inspect failed service logs and health status. Check 3000/5432/8000 port conflicts and disk space.
Docker Hub anonymous rate limits require an authenticated local registry setup or environment recovery;
never embed registry credentials or disable TLS. Cloud builds may need scripts/cloud-build.sh for CA trust.
Cache directories are .cache; no writable HOME assumption. `docker compose down` preserves application
DB volumes. Only test integration scripts delete their own disposable project volumes.
