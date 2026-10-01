ARG NODE_IMAGE=node:24.19.0-trixie-slim
FROM ${NODE_IMAGE} AS builder
USER root
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 NODE_USE_ENV_PROXY=1
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    npm install --global pnpm@11.19.0 && pnpm install --frozen-lockfile
COPY apps/web ./apps/web
COPY packages/contracts ./packages/contracts
ENV API_BASE_URL=http://api:8000
RUN pnpm --filter @vehicle-platform/web build
FROM ${NODE_IMAGE} AS runtime
USER root
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx
ARG APP_VERSION=0.1.0
ARG GIT_SHA
ARG BUILD_TIMESTAMP
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000 \
    APP_VERSION=${APP_VERSION} GIT_SHA=${GIT_SHA} BUILD_TIMESTAMP=${BUILD_TIMESTAMP}
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY --from=builder --chown=10001:10001 /app/apps/web/.next/standalone ./
COPY --from=builder --chown=10001:10001 /app/apps/web/.next/static ./apps/web/.next/static
USER 10001:10001
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s CMD ["node", "-e", "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]
CMD ["node", "apps/web/server.js"]
