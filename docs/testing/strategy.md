# Testing strategy

Fast unit tests cover config, middleware, errors, timeout/unavailable behavior and frontend states
without external APIs. Backend coverage uses branches and separate 90% line and branch thresholds; frontend first-party
logic and status component require 85% in each dimension. Generated artifacts, declarative framework
configuration and migration scripts are excluded from unit coverage; migrations have real integration tests.

Integration uses a new isolated Compose project and disposable TimescaleDB database, fails if it is
not explicitly named vehicle_test*, and validates clean upgrade, downgrade preserving extension,
re-upgrade/idempotent head and real API readiness. Contract tests inspect OpenAPI and regenerate TS.
Playwright uses the real stack to validate readiness display, keyboard navigation and axe accessibility;
a browser transport failure validates recovery. Do not replace the happy path API with mocks in E2E.

Run make check-api/check-web during development, make verify for Phase 0 delivery. CI preserves
coverage and browser reports/traces on failures. No private API or production fixture is needed.
Future synthetic and golden datasets: normal-session, heat-soak, boost-drop, fuel-pressure-drop,
timing-correction and sensor-failure. Add real dataset files only when used by event/ML regression tests.
A meaningful ingestion performance baseline belongs to Phase 1, not an artificial health benchmark.
