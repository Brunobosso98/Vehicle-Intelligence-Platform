# Phase 9G drift and applicability

The drift study compares later synthetic windows against training-only feature and OOD references.
It separates covariate/source-availability changes from label-prevalence, concept/performance,
calibration, and detector/reference changes. Only the labeled synthetic windows support the latter
comparisons in this acceptance run. Unlabeled real/imported telemetry can support feature
availability and distribution descriptions only; it cannot establish changing predictive error,
calibration, or mechanical failure rates.

Applicability decisions are versioned by task or detector, source role, feature and label
definitions, required signals, vehicle/configuration context, data support, calibration status,
artifact integrity, and shift status. Synthetic results remain `SYNTHETIC_ONLY`; real-world
predictive validity and calibration remain `NOT_ESTABLISHED`, and production use remains
`PROHIBITED`. Missing channels stay missing and are excluded or abstained; they are not imputed as
healthy outcomes.

## Exact-SHA results

The exact-SHA acceptance JSON supplies the actual drift metrics, OOD distances, missing-signal
counts, scored/abstained coverage, and applicability decisions. Numeric summaries are copied here
only after the independent checker passes. A feature-distribution shift is a review warning, not
evidence of performance degradation or diagnosis.
