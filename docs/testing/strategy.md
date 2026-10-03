# Testing strategy

Fast unit tests cover config, middleware, errors, timeout/unavailable behavior and frontend states
without external APIs. Backend coverage uses branches and separate 90% line and branch thresholds; frontend first-party
logic and status component require 85% in each dimension. Generated artifacts, declarative framework
configuration and migration scripts are excluded from unit coverage; migrations have real integration tests.
Phase 1 SQL-backed HTTP routes and ingestion/query services are likewise excluded from the unit
coverage denominator and exercised through disposable TimescaleDB integration tests; pure parsing,
normalization, identity and synthetic generation remain in the strict unit coverage gate.

Integration uses a new isolated Compose project and disposable TimescaleDB database, fails if it is
not explicitly named vehicle_test\*, and validates clean upgrade, downgrade preserving extension,
re-upgrade/idempotent head and real API readiness. Contract tests inspect OpenAPI and regenerate TS.
Playwright uses the real stack to validate readiness display, keyboard navigation and axe accessibility;
a browser transport failure validates recovery. Do not replace the happy path API with mocks in E2E.

Run make check-api/check-web during development, make verify for Phase 1 delivery. CI preserves
coverage and browser reports/traces on failures. No private API or production fixture is needed.

Validation uses split executors without splitting acceptance criteria. Codex Cloud runs
`make verify-cloud`, the mandatory non-container subset. Docker-dependent results are `CI REQUIRED`.
GitHub Actions `full-validation` runs the canonical `make verify` responsibilities on Ubuntu with
Docker: final images, disposable database/migrations, stack behavior, integration, E2E, image scans
and backend-queryable observability. Phase 0 canonical validation passed before Phase 1 began. Only a successful commit-tied canonical workflow can complete Phase 1.
Future synthetic and golden datasets: normal-session, heat-soak, boost-drop, fuel-pressure-drop,
timing-correction and sensor-failure. Add real dataset files only when used by event/ML regression tests.
A meaningful ingestion performance baseline belongs to Phase 1, not an artificial health benchmark.

Phase 2 golden tests generate, rather than commit, deterministic mixed-drive, false-positive
throttle, short-burst, missing-boost, irregular-sampling, telemetry-gap and noisy-signal data.
Detection acceptance is precision and recall ≥0.95 and mean start/end boundary error ≤1.5 seconds
at 5, 10 and 20 Hz. Disposable Timescale integration validates migration, persistence,
idempotency and configuration isolation; real-stack E2E validates timeline, inspection and factual
comparison. The canonical workflow records the 100k-observation benchmark without a brittle SLO.

# Phase 3 acceptance

Phase 3 uses eleven independently configured golden scenarios: normal repeated pulls, noisy healthy,
boost drop, boost overshoot, repeated-pull IAT rise, fuel-pressure drop, sensor dropout, signal stuck,
telemetry gap, throttle closure, and a multi-anomaly session. `make phase3-acceptance` prints per-class
and micro/macro TP/FP/FN, precision, recall, F1, boundary errors, and healthy false positives, then
runs informational normal, multi-anomaly, and 100k+ observation benchmarks. The gate requires at
least 0.95 precision/recall/F1 and zero false positives in both healthy scenarios; latency is recorded
but deliberately not gated. Disposable Timescale integration validates revision 0004 downgrade to
the intact Phase 2 schema, re-upgrade, real persistence, filters, details, replacement and idempotency.
