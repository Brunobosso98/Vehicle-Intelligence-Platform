FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58 AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake bison flex libssl-dev zlib1g-dev pkg-config && rm -rf /var/lib/apt/lists/*
WORKDIR /source
COPY postgres.tar.gz timescaledb.tar.gz ./
RUN tar xzf postgres.tar.gz && mv postgres-* postgres && cd postgres && ./configure --without-readline --without-icu --with-openssl && make -j4 && make install
RUN tar xzf timescaledb.tar.gz && cd timescaledb-* && ./bootstrap -DREGRESS_CHECKS=OFF -DUSE_TELEMETRY=OFF -DPG_CONFIG=/usr/local/pgsql/bin/pg_config && cmake --build build -j4 && cmake --install build
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58
COPY --from=builder /usr/local/pgsql /usr/local/pgsql
ENV PATH=/usr/local/pgsql/bin:$PATH PGDATA=/var/lib/postgresql/data/pgdata
RUN groupadd --gid 10001 postgres && useradd --uid 10001 --gid postgres --no-create-home postgres && mkdir -p /var/lib/postgresql/data && chown -R postgres:postgres /var/lib/postgresql
COPY --chmod=755 database-entrypoint.sh /entrypoint.sh
USER 10001:10001
EXPOSE 5432
ENTRYPOINT ["bash", "/entrypoint.sh"]
