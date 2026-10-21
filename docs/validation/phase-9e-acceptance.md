# Phase 9E acceptance

This report defines the acceptance gate for the implementation branch. It is not a claim that
Phase 9E has passed final-head validation. The disposable database evaluator writes its actual
results to ignored `.validation/phase9e/acceptance.json`; the canonical GitHub workflow uploads that
directory and ties the result to the tested commit SHA.

## Executed local checks

The current WSL session has no usable Docker daemon: `docker info` reports that Docker cannot be
found in this WSL 2 distribution. `make bootstrap` passed after activating Node 24 and pnpm 11.19.0
through nvm/corepack. Disposable-database, container, full-stack, browser, image-security and
canonical observability results are **CI REQUIRED** until executed on the Docker-enabled runner.

The focused `test_prediction_evidence.py` suite and targeted Ruff/Python compilation results are
listed in the final task report with their exact commands. The full `make verify-cloud`, strict
typecheck and generated-contract checks must be recorded only after execution. This paragraph must
be updated from actual receipts before calling the final PR head verified.

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

Do not mark this phase VERIFIED until the pushed branch SHA equals the PR head SHA and the exact
commit has successful required quality, integration/E2E, Security, CodeQL, dependency-review and
canonical Docker/full-validation checks. After any fix, use the new SHA and its new receipts. Keep
this section updated with the PR number, commit SHA, workflow URLs, artifact name and any caveat.
