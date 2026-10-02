SHELL := /bin/bash
.DEFAULT_GOAL := help
API := apps/api/.venv/bin
export UV_CACHE_DIR ?= $(CURDIR)/.cache/uv
export UV_LINK_MODE := copy
export XDG_DATA_HOME ?= $(CURDIR)/.cache/data
export XDG_CACHE_HOME ?= $(CURDIR)/.cache
export NEXT_TELEMETRY_DISABLED := 1
export COMPOSE_PARALLEL_LIMIT ?= 1
export PLAYWRIGHT_BROWSERS_PATH ?= $(CURDIR)/.cache/ms-playwright
export BUILDX_CONFIG ?= $(CURDIR)/.cache/buildx
export PATH := $(CURDIR)/.cache/bin:$(PATH)
export API_BASE_URL ?= http://127.0.0.1:8000
.PHONY: help bootstrap dev dev-api dev-web up down db-up db-migrate db-downgrade lint format typecheck check-api check-web test test-unit test-integration test-e2e contracts contracts-check build containers security security-cloud verify verify-cloud verify-local phase3-acceptance phase4-acceptance stream-test live-stream-benchmark observability-up observability-check observability-full stack-check docs-check
help:
	@echo 'bootstrap up down dev-api dev-web check-api check-web test-unit test-integration test-e2e contracts security-cloud security verify-cloud verify'
bootstrap:
	bash scripts/bootstrap.sh
dev: up
dev-api:
	cd apps/api && DATABASE_URL="$${DATABASE_URL:-postgresql+asyncpg://vehicle:local-development-only@127.0.0.1:5432/vehicle}" .venv/bin/uvicorn vehicle_platform.main:create_app --factory --reload --no-access-log
dev-web:
	pnpm --filter @vehicle-platform/web dev
up:
	docker compose up -d --build --wait
down:
	docker compose down
db-up:
	docker compose up -d db --wait
db-migrate:
	docker compose run --rm migrate
db-downgrade:
	docker compose run --rm migrate alembic downgrade -1
lint:
	$(API)/ruff check apps/api/src apps/api/tests apps/api/migrations scripts/*.py
	pnpm --filter @vehicle-platform/web lint
format:
	$(API)/ruff format apps/api/src apps/api/tests apps/api/migrations scripts/*.py
	pnpm format
typecheck:
	$(API)/mypy apps/api/src
	pnpm --filter @vehicle-platform/web typecheck
check-api:
	$(API)/ruff check apps/api/src apps/api/tests apps/api/migrations scripts/*.py
	$(API)/ruff format --check apps/api/src apps/api/tests apps/api/migrations scripts/*.py
	$(API)/mypy apps/api/src
	$(API)/pytest apps/api/tests/unit --cov=vehicle_platform --cov-config=apps/api/pyproject.toml --cov-branch --cov-report=term-missing --cov-report=xml:apps/api/coverage.xml
	$(API)/python scripts/check_coverage.py
check-web:
	pnpm --filter @vehicle-platform/web lint
	pnpm --filter @vehicle-platform/web typecheck
	pnpm --filter @vehicle-platform/web test
test-unit:
	$(API)/pytest apps/api/tests/unit --cov=vehicle_platform --cov-config=apps/api/pyproject.toml --cov-branch
	pnpm --filter @vehicle-platform/web test
test: test-unit test-integration test-e2e
test-integration:
	bash scripts/integration.sh
test-e2e:
	pnpm --filter @vehicle-platform/web test:e2e
contracts:
	pnpm contracts
contracts-check:
	pnpm contracts:check
build:
	pnpm --filter @vehicle-platform/web build
containers:
	docker compose build
security-cloud:
	bash scripts/security-cloud.sh
security:
	bash scripts/security.sh
observability-up:
	docker compose -f compose.yaml -f infra/docker/observability/compose.yaml --profile observability up -d --build --wait
observability-check:
	$(API)/python scripts/observability-smoke.py
observability-full:
	bash scripts/observability-validation.sh
stack-check:
	bash scripts/stack-smoke.sh
docs-check:
	$(API)/python scripts/check_context.py
	@set -e; for script in scripts/*.sh; do bash -n "$$script"; done
verify-local: check-api check-web contracts-check docs-check
	pnpm format:check
	$(MAKE) build
phase3-acceptance:
	$(API)/python scripts/evaluate_events.py
	$(API)/python scripts/benchmark_events.py
stream-test:
	$(API)/pytest apps/api/tests/unit/test_acquisition.py
	$(API)/python scripts/benchmark_stream.py
live-stream-benchmark:
	$(API)/python scripts/benchmark_stream_live.py
phase4-acceptance: stream-test contracts-check
verify-cloud: verify-local phase3-acceptance phase4-acceptance security-cloud
verify: verify-cloud containers test-integration
	$(MAKE) up
	$(MAKE) stack-check
	$(MAKE) test-e2e
	$(MAKE) security
	$(MAKE) observability-up
	$(MAKE) observability-full
