# Phase 2 validation baseline

The golden suite evaluates three mixed-drive sample rates (5/10/20 Hz), stationary aggressive
throttle, short burst, missing boost, irregular/noisy sampling, telemetry gap and out-of-order
input. On the development runner, all 12 expected pulls were detected with 0 false positives and 0
false negatives: precision 1.0, recall 1.0, F1 1.0. Mean/median start error was 0.289/0.4 s and
mean/median end error was 0.4/0.4 s. These boundaries reflect the 200 ms analysis grid. State
classification is regression-tested by required state presence; a time-weighted accuracy claim is
not made because overlapping warm-up/driving labels require a future labeling policy.

Run `apps/api/.venv/bin/python scripts/benchmark_analysis.py` for a deterministic 119,000-observation,
850-second workload (20 Hz per signal, repeated scripted mixed drive). Record query and persistence
timings separately in canonical disposable-Timescale CI; this pure benchmark reports alignment,
segmentation, pull detection, total CPU wall time and Python peak allocation. Timings are evidence,
not an SLO and not a pass/fail threshold.

On the Codex Linux/Python 3.12 runner, the 119,000-observation run produced 4,250 aligned frames,
160 segments and 15 pulls. Alignment took 2.3022 s, segmentation 0.0420 s, pull detection 0.0117 s,
total pure-analysis time 2.3559 s, and Python peak allocation was 10.41 MiB. Database query and
persistence measurements remain **CI REQUIRED** because this runner has no disposable TimescaleDB.
