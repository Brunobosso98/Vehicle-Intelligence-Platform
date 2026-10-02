# Component model

## CURRENT

Next.js serves the shell and same-origin status proxy. FastAPI contains HTTP contracts,
configuration, database probe and observability modules. PostgreSQL stores Phase 1 vehicle/session data and canonical samples in a Timescale hypertable. Pydantic exports OpenAPI and
openapi-typescript generates shared frontend types. Optional Collector/Tempo/Prometheus/Grafana
receive traces and scrape metrics. JSON application logs remain on stdout.

## FUTURE

Event detection, analytics, MCP, agent orchestration, RAG and ML are future capabilities with no fake endpoints.
No streaming broker, Redis, data lake or vector database is installed.
