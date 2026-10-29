# Phase 9G operator runbook

Phase 9G runs only in a disposable `vehicle_test` PostgreSQL database. It may create synthetic
9A/9B/9C source fixtures in that database before taking the source-integrity baseline; every
research evaluation and 9G registry write after that baseline must leave those earlier-phase
tables unchanged. The Compose project is unique per run and is removed, with its database volume,
on success or failure.

## Run the gates

Use the locked project environment and Docker daemon:

```bash
make test-evaluation-calibration
make phase9g-acceptance
make benchmark-predictive-reliability
make predictive-reliability-observability
```

`phase9g-acceptance` validates Alembic upgrade through 0018, applies 0019, downgrades safely to
0018, reapplies the head, creates Phase 9B and 9C canonical synthetic artifacts, evaluates all
three 9B tasks and eight 9C detector combinations, persists immutable 9G reports, and runs the
independent checker. The benchmark and observability commands render measurements from that exact
passing receipt. Each report is tied to the current Git SHA; rerun the acceptance after any source
change.

Artifacts are written under ignored `.validation/phase9g/`: `acceptance.json`,
`independent-check.json`, logs, bounded JSON calibration artifacts, benchmark and observability
evidence. The runner rejects a non-`vehicle_test*` database, a dirty Git tree, a checkout SHA
mismatch, over-limit artifacts or rows, changed prior-phase source digests, and a changed replay.
The independent checker rejects a mismatched SHA, unsupported receipt schema, invalid checksum,
missing denominator, altered metric arithmetic, leakage, false claims, or serving-boundary change.

## Interpret the output

`engineering_status=PASS` means the declared offline engineering checks passed for this exact
receipt. It does not mean real-world model validity, real-world calibration, fault diagnosis,
production readiness, or deployment approval. Read the `scientific_readiness`, `applicability`,
`source_role`, `label_availability`, `drift`, `ood`, `coverage`, and `abstentions` records before
using any aggregate metric. If verified real failure labels and adjudicated outcomes are absent,
keep real-world calibration `NOT_ESTABLISHED`.

Candidate JSON under `.validation` is experimental and never loaded by the Phase 9D service. Do not
copy it into serving stores, change a frozen 9B/9C threshold, update an approval, or treat a high
score as a mechanical failure probability. Phase 9G creates no public API or agent-facing claim.

## Failure handling

The evaluator fails closed. Preserve `.validation/phase9g` from a failed disposable CI run for
investigation; do not edit the held-out scenario or acceptance threshold to make a failed result
pass. Fix implementation defects or document a scientifically valid negative result, then rerun
the same protocol on the exact new commit. When Docker is unavailable locally, run `make
verify-cloud` and mark all Docker/database/full-stack Phase 9G checks `CI REQUIRED` until the
canonical GitHub workflow executes successfully.
