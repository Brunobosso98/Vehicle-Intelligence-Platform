# Phase 9G independent acceptance

## Gate and exact-SHA evidence

Run the complete Phase 9G gate with `make phase9g-acceptance`. The runner
[`scripts/phase9g-validation.sh`](../../scripts/phase9g-validation.sh) provisions a uniquely named
disposable Compose database, round-trips migration 0019 from revision 0018, exercises the
registered Phase 9B models and Phase 9C detector artifacts, and then runs the separate
[`scripts/check_predictive_reliability.py`](../../scripts/check_predictive_reliability.py)
arithmetic, lineage, integrity, and leakage gate.

The initial full independent acceptance passed on implementation SHA
`a625be75627a8bd4d8ee5056eb9a287bb58e7898`, based on merged Phase 9F SHA
`327c63f35b4e7bc0eba31bbec81d20206be8afa2`. It reports `engineering_status: PASS` and
`independent_status: PASS`. The report checksum is
`94afae0799f2df77ad17209d51930d24b4162e644a32b63ab7db409c935ae2dc`; the acceptance envelope
checksum is `aa10a4309f36f8198b75f56313e24c259eb2cc20bbc5a49b98b077cebec6a3d2`. The exact final
branch SHA and its required CI checks are recorded after the PR workflow completes; the local
acceptance SHA is not represented as the final delivery SHA.

The exact local receipt is retained, ignored, at `.validation/phase9g/acceptance.json`; the
independent result is in `.validation/phase9g/independent-check.log`. It is generated from real
registered Phase 9B/9C artifacts and canonical Phase 9A feature data using disposable database
infrastructure. Run-scoped research artifact copies stay under ignored
`.validation/phase9g/model-artifacts/` for provenance; they cannot be loaded by serving code.

## Independent checks exercised

The separate checker reconstructs the three tasks' Brier score, log loss, ECE, reliability bins,
AUROC, average precision, threshold confusion counts, session-cluster bootstrap intervals,
risk/coverage arithmetic, candidate selection, and calibration source checksums. It independently
recomputes all four anomaly families' clean false-positive, target-family, cross-family, and
abstention denominators. It verifies source and row fingerprints, partition identities, evidence
lineage, fold manifests, OOD and fixed shift adversaries, synthetic-to-real calibration fences,
and the registered 9B/9C artifact checksums.

The gate also verifies:

- Strict train/calibration/validation/test ordering and disjoint pull, session, vehicle, and
  configuration populations, including an adversarial training-session overlap rejection.
- Independent test metric arithmetic and validation-only candidate selection; test labels are not
  used to fit/select candidate maps.
- Byte-tamper rejection for copied 9B and 9C artifacts, plus a modified 9C receipt. Registered
  artifacts are never mutated.
- Report-hash falsification and fold-removal falsification rejection.
- Synthetic stress oracle metadata excluded from detector fit/features and no synthetic-to-real
  calibration transfer.
- Missing outcomes and unavailable required signals preserved as exclusions or abstentions.
- Source-table digests unchanged across research and persistence; only Phase 9G append-only tables
  added; immutable reports and idempotent replay.
- No serving models, thresholds, approvals, 9E evidence, or 9F claims promoted; no retraining,
  production calibration, or public endpoint.

The disposable database round-tripped migration 0019 down to 0018 and back to head. The 66 focused
evaluation tests passed. The repository's full API unit/quality gate also passed locally: 1,403
tests, 94.44% overall coverage (95.85% line and 90.02% branch coverage checker result). The
canonical all-phase Docker validation is separately tracked in the active exact-head run and the
PR CI evidence; a local phase result is never substituted for an exact final-SHA GitHub check.

The evaluator remains offline: it makes no paid AI, embedding, or remote telemetry calls. Source
materialization stays under the existing 32 MiB input cap; evaluation is limited to 20,000 rows.
Vehicle identity is not exposed in the report, metric labels omit entity identifiers, and only
hashed fingerprints bind row/session/vehicle/configuration lineage. The independent checker also
verifies no HTTP route or production-facing calibration surface was added.

## Engineering and scientific result

The evaluation dataset has 1,162 rows: 946 labeled and 216 held-out exclusions, across 84 sessions,
19 synthetic vehicles, and 34 configurations. The three 9B tasks and four 9C families were
exercised. Detailed calibration metrics and uncertainty are in
[the model report](phase-9g-model-calibration.md); alarm denominators and detector limitations
are in [the anomaly report](phase-9g-anomaly-reliability.md); drift and applicability evidence is
in [the source report](phase-9g-drift-applicability.md).

Engineering pipeline readiness is `PASS`. No real mechanical-failure labels or post-outcome
vehicle observations were present. Therefore real-world predictive validity and calibration are
`NOT_ESTABLISHED`; synthetic calibration is `SYNTHETIC_ONLY`; production use is `PROHIBITED`.
Phase 9B outputs are not failure probabilities, and Phase 9C scores are not engine-health
percentages.

## Benchmark and observability

The run processed 1,162 manifest rows and 12 folds under a 20,000-row limit. Offline evaluation
wall time was 728.081 seconds, CPU time 409.254 seconds, peak RSS 575,291,392 bytes (about 549
MiB), and 1,316 database sessions started. Per-task evaluation took 112.988 seconds for fuel,
113.641 for performance, and 110.732 for thermal. Metric-arithmetic-only elapsed time was 0.152
seconds; the receipt reports 131,256 arithmetic rows/second and 1.596 end-to-end evaluation
rows/second. These are local workload measurements, not a serving or vehicle SLA. Research
calibration artifacts totaled 4,166 bytes; same-key immutable report replay took 0.079 seconds.
The capped run stayed under 20,000 rows and the existing 32 MiB source budget; those are research
run bounds, not production sizing guidance.

Evaluation-run metrics were present, entity identifiers were not used as metric labels, and
required spans `evaluation.registry.persist` and `evaluation.supervised.task` were observed. The
acceptance process emitted telemetry shutdown/uninstrumentation warnings at exit while returning
success; this is recorded as a runtime warning, not described as a clean stderr run.
