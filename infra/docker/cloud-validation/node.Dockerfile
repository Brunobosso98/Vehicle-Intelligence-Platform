FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim@sha256:5ae92e4d35b8d586d50ddf4aba6ecdd9f744237284d31c86bf45077e4e17e4bd
COPY node-dist /usr/local
RUN chmod -R a+rX /usr/local
USER 10001:10001
