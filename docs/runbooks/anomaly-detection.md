# Offline anomaly detection runbook

Phase 9C is a local operator workflow over recorded Phase 9A FeatureSets. It produces relative
engineering deviations or explicit abstentions. It does not diagnose faults, estimate component
failure probability, issue maintenance advice, control a vehicle, or create an alert.

## Validate the implementation

The acceptance wrapper creates a fresh disposable TimescaleDB, upgrades from Phase 9B head `0014`
to `0015`, downgrades to `0014`, re-upgrades to head, generates canonical FeatureSets, and runs the
independent evaluator:

```bash
make test-anomalies
make phase9c-acceptance
make benchmark-anomalies
make anomaly-observability
```

All disposable telemetry, artifacts, benchmark results and reports live under ignored
`.validation/phase9c/`. The evaluator labels its results as a controlled synthetic engineering
fixture. It never calls a paid model or external service.

## Fit a candidate

Fit requires an anchor pull after the reference period, an aware cutoff that includes that completed
pull, an explicit source role, one family and one allowlisted method:

```bash
vehicle-anomaly fit \
  --family thermal \
  --method robust_mad \
  --anchor-pull-id 00000000-0000-0000-0000-000000000000 \
  --cutoff 2026-10-01T12:00:00Z \
  --source-role real_vehicle
```

The service selects only strictly prior same-vehicle, same-configuration, same-modification,
same-source history. It records exclusions and rejects insufficient sessions, rows, temporal span,
quality or source signals. Start with `--dry-run` to inspect support and candidate fit without
persisting the detector version. Fit candidates are not accepted for evaluation until a
validation-selected threshold is frozen.

## Freeze the validation choice

Use the evaluation artifact produced from whole validation sessions. The accepted version is
immutable and includes the validation checksum, selection policy, metrics and threshold manifest:

```bash
vehicle-anomaly freeze-threshold \
  --detector-version-id 00000000-0000-0000-0000-000000000000 \
  --threshold 3.5 \
  --validation-checksum 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef \
  --selection-manifest .validation/phase9c/selection.json \
  --accept
```

Do not choose a threshold from test results. The default training quantile is an initial candidate
cutoff only. Threshold changes create a new detector version; an existing version is not edited.

## Retrospective batch score

Score one to 1,000 unique completed pulls at an explicit observation cutoff:

```bash
vehicle-anomaly score \
  --detector-version-id 00000000-0000-0000-0000-000000000000 \
  --pull-ids 00000000-0000-0000-0000-000000000001,00000000-0000-0000-0000-000000000002 \
  --cutoff 2026-10-01T12:05:00Z \
  --source-role real_vehicle
```

The returned findings are persisted immutably. Repeating the same detector/cutoff/input set returns
the same run and finding IDs. If the source lacks a required signal, the context differs, the
feature was not yet available, reference support is insufficient, or quality checks fail, inspect
the reason/status and collect compatible evidence. Missing sensor data is not a normal value and
is not an anomaly finding.

## Expected outcomes

| Situation                                           | Expected result                                  | Meaning                                                                |
| --------------------------------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------- |
| Compatible nominal pull with supported signals      | `INLIER`                                         | No score crossed this version's relative statistical threshold.        |
| Atypical thermal rise in an eligible pull           | `ANOMALOUS` when the frozen threshold is crossed | Engineering statistical deviation, not a confirmed fault.              |
| Fuel pressure absent or not observed                | `UNSUPPORTED_SOURCE` or `INSUFFICIENT_SIGNAL`    | No fuel-pressure score is manufactured.                                |
| Fewer than the required rows, sessions or date span | `INSUFFICIENT_REFERENCE`                         | Wait for compatible history; do not borrow another vehicle's baseline. |
| Effective configuration or modification set differs | `INCOMPATIBLE_CONTEXT`                           | Fit a new compatible cohort after enough history exists.               |
| Registered artifact checksum changed                | Safe artifact error                              | The scorer refuses the modified file.                                  |
| Same model, cutoff and target set submitted again   | Same run and finding IDs                         | The replay is idempotent; the original evidence remains immutable.     |

## Operating limits

- The artifact loader accepts only registered, checksummed local detector versions.
- Reference snapshots and findings are append-only; use a new cutoff or detector version for new
  evidence.
- Do not compare vehicles or configurations across the default cohort boundary.
- Keep synthetic, imported and real-vehicle source roles separate.
- Never interpret a statistical deviation as diagnosis, causation, a safety limit, or failure risk.
- This phase has no service endpoint, streaming scorer, promotion flow, agent tool or user alert.
