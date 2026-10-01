ARG PYTHON_IMAGE=ghcr.io/astral-sh/uv:python3.12-trixie-slim@sha256:5ae92e4d35b8d586d50ddf4aba6ecdd9f744237284d31c86bf45077e4e17e4bd
FROM ghcr.io/astral-sh/uv:0.12.19@sha256:04d046b13e60d6bcec73cbc5e1cad25d680dea90c8573340950a0ac2d1aef424 AS uv
FROM ${PYTHON_IMAGE} AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
COPY apps/api/src ./src
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca; fi; \
    uv sync --frozen --no-dev --no-editable
FROM ${PYTHON_IMAGE} AS runtime
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
ARG APP_VERSION=0.1.0
ARG GIT_SHA
ARG BUILD_TIMESTAMP
ENV APP_VERSION=${APP_VERSION} GIT_SHA=${GIT_SHA} BUILD_TIMESTAMP=${BUILD_TIMESTAMP} \
    PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY --from=builder /app/.venv /app/.venv
COPY --chown=10001:10001 apps/api/alembic.ini ./
COPY --chown=10001:10001 apps/api/migrations ./migrations
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]
CMD ["uvicorn", "vehicle_platform.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
