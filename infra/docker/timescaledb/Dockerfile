# syntax=docker/dockerfile:1.7
FROM --platform=$BUILDPLATFORM golang:1.26.9-alpine3.23@sha256:96123126ac58e910f4dd3619a8901e2fb6d1ad84b59b1232cac7c9ea65a8f888 AS helper-builder

ARG TARGETOS
ARG TARGETARCH
ARG TARGETVARIANT
ARG GOSU_VERSION=1.19
ARG GOSU_SOURCE_SHA256=cd9719b775dbfedae53923c9b0dc792b66d42c51e0b36652ed6f747fbadc0164
ARG TIMESCALEDB_TUNE_VERSION=v0.19.0

RUN set -eux; \
    apk add --no-cache ca-certificates curl tar; \
    curl -fsSL "https://github.com/tianon/gosu/archive/refs/tags/${GOSU_VERSION}.tar.gz" -o /tmp/gosu.tar.gz; \
    echo "${GOSU_SOURCE_SHA256}  /tmp/gosu.tar.gz" | sha256sum -c -; \
    mkdir -p /src/gosu /out; \
    tar -xzf /tmp/gosu.tar.gz -C /src/gosu --strip-components=1; \
    cd /src/gosu; \
    CGO_ENABLED=0 GOOS="${TARGETOS}" GOARCH="${TARGETARCH}" GOARM="${TARGETVARIANT#v}" \
      go build -trimpath -ldflags='-d -s -w' -o /out/gosu .; \
    CGO_ENABLED=0 GOOS="${TARGETOS}" GOARCH="${TARGETARCH}" GOARM="${TARGETVARIANT#v}" \
      GOBIN=/out go install "github.com/timescale/timescaledb-tune/cmd/timescaledb-tune@${TIMESCALEDB_TUNE_VERSION}"

FROM timescale/timescaledb:2.30.2-pg17@sha256:b346edcdb51a1fd6020e3965e0bd1c9f3406fa6d5fbce1e28f4852587ef934e2

LABEL org.opencontainers.image.title="Vehicle Platform hardened TimescaleDB" \
      org.opencontainers.image.version="2.30.2-pg17" \
      org.opencontainers.image.base.name="timescale/timescaledb:2.30.2-pg17" \
      org.opencontainers.image.base.digest="sha256:b346edcdb51a1fd6020e3965e0bd1c9f3406fa6d5fbce1e28f4852587ef934e2"

COPY --from=helper-builder /out/gosu /usr/local/bin/gosu
COPY --from=helper-builder /out/timescaledb-tune /usr/local/bin/timescaledb-tune

RUN set -eux; \
    apk upgrade --no-cache; \
    rm -f /usr/local/bin/timescaledb-parallel-copy; \
    test ! -e /usr/local/bin/timescaledb-parallel-copy; \
    gosu --version; \
    gosu postgres true; \
    timescaledb-tune --version; \
    postgres --version

USER postgres
