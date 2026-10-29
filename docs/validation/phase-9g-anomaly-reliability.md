# Phase 9G anomaly reliability

The report covers the four frozen Phase 9C families (thermal, boost/air, performance, and fuel)
under robust MAD and Isolation Forest, with detector references and thresholds unchanged. It
separates clean-control false-positive rates, alarms on other named family interventions,
multi-family ambiguity, quality/capability abstentions, detector stability, and reference-size
sensitivity. An anomaly score is a statistical outlier measure, not an engine-health percentage
or calibrated failure probability.

Missing fuel pressure is a required-signal abstention for the fuel detector. Thermal, boost/air,
and performance detectors remain scored when their own inputs are available, so responses to that
missingness remain visible as confounder behavior. Duplicate/low-quality telemetry must abstain for
all families. This distinction preserves the sensor applicability of each detector while making
cross-family behavior observable.

## Exact-SHA results

The exact-SHA acceptance JSON and independent checker provide per-family/method numerators and
denominators for clean eligible/scored observations, target interventions, cross-family alarms,
quality abstentions, and reference-size subsets. Numeric results are recorded here only after the
independent checker passes; the synthetic intervention oracle is not a mechanical diagnosis.
