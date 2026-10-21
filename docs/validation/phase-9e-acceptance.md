# Phase 9E acceptance

This report defines the acceptance gate for the implementation branch. It is not a claim that
Phase 9E has passed final-head validation. The disposable database evaluator writes its actual
results to ignored `.validation/phase9e/acceptance.json`; the canonical GitHub workflow uploads that
directory and ties the result to the tested commit SHA.

## Executed local checks

Docker is reachable in WSL (`docker info --format '{{.ServerVersion}}'` returned `29.8.2` on
2026-10-21). The following local checks completed successfully against the implementation working
tree:

- `make verify-cloud`: passed, including Ruff, format, mypy, 1,216 API unit tests (96.44% line and
  91.04% branch coverage), Web lint/typecheck and 52 tests (94.74% line coverage), generated
  contracts, documentation checks, Prettier, production build, Phase 0–5 evaluations/benchmarks,
  Gitleaks, dependency scanning and containerized Trivy filesystem scanning.
- `make test-integration`: 13 passed; telemetry persisted and replayed 100,002 samples, with zero
  new rows on replay.
- `make containers` and `make security`: passed after rebuilding the API and Web images. Trivy
  reported zero Critical findings; all High findings were covered by the checked-in risk
  acceptance.
- `make phase9e-acceptance`: passed on the working tree in a prior run: 10 receipt types, three
  supervised tasks, four anomaly families, three abstentions, integrity controls, and observability
  checks. The ignored receipt contains the SHA from before the final small type-safety corrections;
  rerun it after commit to bind acceptance to the final source SHA.

These local results do not replace required checks on the pushed PR head. The canonical Docker/full-
stack, browser, image-security and observability receipts must be tied to that exact SHA before
calling this phase VERIFIED. The acceptance fixtures are synthetic and make no real-world model
accuracy claim.

## Required disposable acceptance

`make phase9e-acceptance` starts an isolated TimescaleDB Compose project, upgrades through 0016,
creates real 9A/9B/9C records and approved 9D receipts, then exercises the actual FastAPI routes.
The independent oracle compares source-row hashes, version/checksum references, prediction fields,
feature values/units, cutoffs, frozen anomaly references, graph edges and source reachability.
It round-trips migration 0017 and compares every Phase 0–9D table digest.

The gate requires three supervised tasks, four anomaly families, abstention and missing-FeatureSet
cases; 10-way idempotent materialization; bounded 100-way replay/admission; active and revoked
historical evidence reads; unauthenticated/query/cookie/public/disabled/production controls; safe
projection and body bounds; feature/artifact tamper detection and restoration; normalized-row
immutability; orphan/duplicate/oversize/rollback database controls; independent verification
audits; and delivered bounded metrics and spans.

`make benchmark-prediction-evidence` prints the measured cold build, warm replay, concurrency,
response size, RSS and observed DB-session results from the acceptance receipt. These are fixture
measurements, not production latency or model-accuracy SLAs. `make prediction-evidence-observability`
checks the recorded actual metric and span receipts, including identifier redaction.

## Final-head verification record

PR #45 final-head validation is pending for the commit produced from these results. Do not mark this
phase VERIFIED until the pushed branch SHA equals the PR head SHA and the exact commit has
successful required quality, integration/E2E, Security, CodeQL, dependency-review and canonical
Docker/full-validation checks. After any fix, use the new SHA and its new receipts. Record the final
commit SHA, workflow URLs, artifact name and any validation caveat here once those checks finish.
