# Database not ready

1. Call /health/live and /health/ready separately; 200/503 means application alive, dependency unavailable.
2. Inspect `docker compose ps db migrate` and `docker compose logs db migrate` without publishing secrets.
3. Check .env's local host URL versus container db hostname and ensure ports are free.
4. `make db-migrate` activates TimescaleDB. Inspect alembic current; do not fake extension availability.
5. Retry readiness; bounded failures must stay sanitized. Never delete volumes to fix production data.
