# Phase 10 security and reproducibility review

## Exact-SHA security evidence

Security run [44988811008](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/44988811008) passed on implementation SHA `c5114e07972456a9922f7d06f8c1925129adc351`, including the container policy, Dependency Review and CodeQL Python and JavaScript/TypeScript checks. The exact artifact reports 107 accepted High package occurrences and zero Critical or blocked findings in selected runtime images: API 50, Web 48, OpenTelemetry Collector 1, Prometheus 2, Tempo 2, Grafana 4, Kafka 0 and custom TimescaleDB 0.

The 20 exact High-risk exception records were reviewed on 2026-11-21 and expire 2026-12-05. The former zlib exception for `CVE-2026-76844`, which expired 2026-11-12, remains removed; selected application images report no zlib CVE. The upstream Timescale image scan separately reports 271 High and 3 Critical findings; it is not the selected runtime image. The rebuilt custom TimescaleDB runtime image has zero High and Critical findings. Scanner configuration remains enabled and upstream findings are retained.

## Reproducibility and artifact trust

The evaluator binds each run to the exact repository SHA, locked pipeline definition and fingerprint, source role, immutable dataset and 9A feature fingerprints, label/oracle checksum, train/evaluation cutoffs, seed, candidate artifact checksum and Phase 9G evaluation report checksum. Reproduction rebuilt a selected 9B candidate in a private temporary root and verified byte-identical artifact, data and metrics checksums against frozen evaluation lineage. It wrote no additional pipeline, registry or evaluation record.

Artifacts are read through existing allowlisted 9B/9C serializers and private trusted roots. The independent checker verifies path containment, no symlink traversal, regular-file and ownership/mode conditions, configured size bound and content checksum. Acceptance rejected incompatible candidates, source-role spoofing, temporal/source leakage, stale artifacts, unauthorized reviewer credentials, invalid proposal checksums, tampered bytes and unsafe serialized payloads. Replay was idempotent; lease/fencing and concurrent ownership were exercised. Source records and serving bindings remained unchanged by monitoring, comparison and review.

Metrics use bounded OpenTelemetry attributes and omit vehicle, receipt and user identifiers from labels. The acceptance observed pipeline-run and stage-event counters, duration histogram bucket/count/sum series and pipeline/monitor spans, with no sensitive identifier in exported output.

## Failure recovery evidence

Earlier exact-head independent runs exposed receipt and checker defects: unsupported datetime/UUID normalization, a `PredictionKind` alias treated as an enum, omitted synthetic scope, an absent 9B artifact-size column, `source_type` queried from `pulls` instead of its owning session, and a 9C cohort fingerprint built from pull IDs instead of matched feature-row IDs. Each defect received a targeted regression and was replayed before the full acceptance. The canonical run on `439e099` then exposed ambiguous artifact-root lookup. Resolution verifies candidate bytes against immutable registry checksum and size; its targeted regression and isolated acceptance passed on `04c6c49`. The canonical Phase 0–10 workflow and all independent gates passed on `c5114e0`; see the acceptance report.

## Scientific applicability and serving boundary

The evidence uses deterministic synthetic fixtures in disposable infrastructure. Synthetic calibration does not prove real-world predictive validity. Phase 9B supervised scores are not mechanical failure probabilities; Phase 9C anomaly scores are not engine-health percentages or confirmed component diagnoses. Unlabeled real-world telemetry cannot establish accuracy, recall or calibration. Real-world mechanical failure predictive reliability remains **NOT_ESTABLISHED**.

Phase 10 proposals are review artifacts only. They do not authorize serving changes or automatic retraining. Any actual transition requires a separate explicit authorized operator action through the established Phase 9D lifecycle.
