# Component model

## CURRENT

Next.js serves telemetry, session/pull/event inspection, live acquisition and analytics workspaces.
Same-origin proxies forward typed requests to FastAPI. The API owns vehicle/configuration/session
records, CSV ingestion, deterministic analysis and immutable analytics results. A hardware-near
read-only collector publishes authenticated batches; Kafka transports them to a separate canonical
consumer. PostgreSQL/TimescaleDB persists all canonical telemetry and analytical provenance.

Pydantic exports OpenAPI; openapi-typescript generates shared frontend types. The optional OTel
Collector/Tempo/Prometheus/Grafana stack receives traces and scrapes metrics. Sanitized JSON logs
remain on stdout. Database trace export preserves operations and error categories without query
text or driver exception messages.

## FUTURE

MCP, agents, RAG, ML, causal diagnosis, production authentication and managed infrastructure are
outside Phases 0–5. No Redis, vector database, data lake or learned analytical model is installed.
