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

Phase 3 uses fourteen independently configured golden scenarios: normal repeated pulls, noisy healthy,
boost drop, boost overshoot, repeated-pull IAT rise, fuel-pressure drop, sensor dropout, signal stuck,
telemetry gap, throttle closure, high intake/oil/coolant thresholds, and a multi-anomaly session. `make phase3-acceptance` prints per-class
and micro/macro TP/FP/FN, precision, recall, F1, boundary errors, and healthy false positives, then
runs informational normal, multi-anomaly, and 100k+ observation benchmarks. The gate requires at
least 0.95 precision/recall/F1 and zero false positives in both healthy scenarios; latency is recorded
but deliberately not gated. Disposable Timescale integration validates revision 0004 downgrade to
the intact Phase 2 schema, re-upgrade, real persistence, filters, details, replacement and idempotency.

Disposable database regression coverage also runs the canonical stream consumer persistence path:
bounded poll transactions, receipt replay, duplicate canonical identities, whole-poll rollback,
provisional finding SQL typing, nullable-boundary finalization, findings/SSE responses and
repeated-evaluation idempotency. Phase 5 browser selection and error assertions are scoped to the
analytics region so Phase 3 controls and Next.js route announcements cannot satisfy its locators.
Timeline segments use list items containing native buttons; accessibility checks cover populated
sessions as well as the initial workspace.
Phase 3 fixtures use timestamps later than retained sessions so repeated runs validate their own
anomalous and healthy evidence without resetting application volumes.
Web unit tests use one worker to bound simultaneous jsdom startup on WSL; assertions, worker
startup timeout and coverage thresholds remain unchanged.

# Retrospective phase gates

`make phases-0-5-acceptance` runs the static/build engineering gate plus independent Phase 1
CSV/identity checks, Phase 2 pull ground-truth evaluation and benchmark, Phase 3 all-event
ground truth, Phase 4 recipe availability/rate checks and bounded collector checks, and Phase 5
numeric/history golden evaluation and benchmark. Pure gates do not substitute for Docker.

`make test-integration` creates disposable TimescaleDB and Kafka with a loopback-only ephemeral
broker port. It validates full migration cycles and the discovered Phase 5 parent while retaining
earlier-phase fixture rows. Poll persistence tests use real database transactions; finalization
observes the real broker's empty topic boundary rather than mocking its drain check.
`make phase4-stack-acceptance` interrupts broker, consumer, database and gateway connectivity
while records are in flight, then checks unique canonical identities and persisted gap events.
Its bounded Compose-operation deadline is 300 seconds, above PostgreSQL's 180-second startup
grace and up to 60 seconds of health retries. This permits measured crash-recovery fsync to finish;
it does not change application or stream-finalization deadlines.
After replay it also waits, for at most 120 seconds, for the real Next.js status and vehicle
proxies to return healthy responses before Playwright begins. The prior recovery run showed both
first-page proxy requests pending during container-network warm-up while later browser flows passed.

The canonical workflow and `make verify` include this recovery gate and the 100k live benchmark.
Playwright additionally starts deterministic live acquisition through the browser, observes SSE
provisional findings, stops/finalizes and checks confirmed canonical reconciliation. Artifact
paths remain ignored; they must not enter commits. Original timeouts and quality thresholds
remain gates. The 15-second stream-drain deadline rejects pending finalization with 409; it does
not convert an undrained stream into success.

The disposable integration gate also runs the original Phase 1 ingestion performance protocol:
100,002 actual synthetic observations, measured 1,000-row batch execution, canonical identities,
full replay, real bounded query/truncation, analyzed buffer/query plan, versions and process CPU/RSS.
It requires the explicitly supplied `vehicle_test*` database and never resets retained application
volumes. Kafka's external test listener is selected only after an actual Docker host-port publication
probe. This avoids treating a free Linux ephemeral port as proof of Docker Desktop/WSL host forwarding.
A known publishable `TEST_KAFKA_PORT` can be supplied; bounded setup failure remains a failed gate.
