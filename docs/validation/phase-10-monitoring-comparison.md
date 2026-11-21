# Phase 10 monitoring and comparison

## Monitoring protocol

The monitor uses only already persisted Phase 9D prediction receipts. Its
immutable protocol identifies the controlled serving binding, vehicle and
configuration scope, source role, model/detector version, feature schema,
baseline and comparison windows, observed and effective times, required
features, support floors and versioned PSI/location-shift thresholds.

The report keeps receipt, session, scored, abstained, error, quality-excluded,
missing-feature and source-role counts explicit. Baseline and comparison
windows are disjoint and each receipt is conserved once. No rows are reported
as NO_OBSERVATIONS; insufficient independent sessions remain
INSUFFICIENT_SUPPORT.

Source-feature drift and score-distribution shift are reported independently.
Without verified labels, performance and calibration are UNKNOWN. Synthetic
fixture labels are not joined to real-world receipts. There is no inference,
9E evidence materialization or agent execution in monitoring.

## Champion/challenger

The comparator reloads the actual active Phase 9D binding and its 9B/9C
artifact, checks lifecycle state, artifact checksum, schema, role, target and
cohort, then evaluates both versions on the exact same held-out rows. It
reports support, abstention and uncertainty with the candidate metrics. Raw
robust-MAD and isolation-forest scores are not compared across scales.

Any incompatibility, stale champion, missing bytes, changed cohort or leakage
returns NOT_COMPARABLE and a reason without ranking. Comparison is read-only
over prior Phase 9D/9E/9F/9G records.

## Current evidence

The database-backed monitoring and comparison evaluator is not yet executed in
this local environment because Docker is unavailable. Exact windows, counts,
PSI, abstention rates, offline comparison deltas and immutable source digest
results must come from the Phase 10 acceptance receipt for the exact final
SHA. They are not claimed here.

Regardless of fixture results, unlabeled real telemetry does not establish
predictive accuracy, recall or calibration. Real-world mechanical failure
predictive reliability remains NOT_ESTABLISHED.
