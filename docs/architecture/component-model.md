# Component model

## CURRENT

Next.js serves the shell and same-origin status proxy. FastAPI contains HTTP contracts,
configuration, database probe and observability modules. PostgreSQL stores only Alembic revision
metadata; TimescaleDB is installed by the foundation migration. Pydantic exports OpenAPI and
openapi-typescript generates shared frontend types. Optional Collector/Tempo/Prometheus/Grafana
receive traces and scrape metrics. JSON application logs remain on stdout.

## FUTURE

Vehicle/session domain, ingestion, event engine, analytics, MCP, agent orchestration, RAG and
ML are planned capabilities. They have no packages, containers or fake endpoints yet.
No streaming broker, Redis, data lake or vector database is installed.
