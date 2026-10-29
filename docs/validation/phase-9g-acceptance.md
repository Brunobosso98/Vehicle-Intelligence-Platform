# Phase 9G independent acceptance

The executable acceptance is `make phase9g-acceptance`, implemented by
[`scripts/phase9g-validation.sh`](../../scripts/phase9g-validation.sh). It runs against a uniquely
named disposable Compose database, round-trips migration 0019 from revision 0018, invokes the
canonical 9B trainer and 9C acceptance source, then runs
[`scripts/check_predictive_reliability.py`](../../scripts/check_predictive_reliability.py) as a
separate arithmetic/provenance/leakage gate.

The checker independently reconstructs Brier score, log loss, ECE bins, AUROC, average precision,
threshold confusion counts, cluster bootstrap intervals, risk/coverage denominators, candidate
selection, calibration source checksums, clean false-positive rates, target and cross-family alarm
counts, source manifests, fold identities, evidence lineage, and fixed PSI/robust-shift adversary
arithmetic. It also checks known calibration and drift adversaries, calibration/test separation,
unlabeled source behavior, serving fences, idempotent persistence, immutable database records, and
before/after source-table digests.

The runner exercises the three registered 9B task artifacts and the four 9C detector families
using both registered detector methods. It checks local byte-tamper copies of the registered 9B and
9C artifacts and a modified 9C receipt. Tamper copies are temporary; registered source artifacts
are not changed. A repeated identical evaluation must produce the same scientific report before
the idempotent database replay is checked.

## Current exact-head result

This document is updated from the exact final-SHA canonical acceptance run before delivery. The
authoritative per-run report is the workflow artifact `phase-0-full-validation-<SHA>`, containing
`phase9g/acceptance.json`, `phase9g/independent-check.json`, and run logs. No result is considered
verified until the canonical Docker/full-stack job and independent checker pass on the same SHA.

Real-world predictive validity and calibration remain `NOT_ESTABLISHED` unless independently
verified real-world outcomes meet the protocol. A synthetic fixture pass is not mechanical-failure
calibration evidence.
