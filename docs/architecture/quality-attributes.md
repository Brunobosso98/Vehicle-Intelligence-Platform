# Quality attributes

| Attribute       | Foundation mechanism                                     | Evidence / future work                  |
| --------------- | -------------------------------------------------------- | --------------------------------------- |
| Correctness     | typed contracts, failure tests                           | generated drift gate, integration/E2E   |
| Reliability     | separate live/ready, bounded DB and HTTP probes          | outage tests; no collector dependency   |
| Observability   | request/trace IDs, OTel metrics/traces, JSON logs        | exporter capture and profile runbook    |
| Performance     | async I/O, connection pooling, bounded label cardinality | ingestion baseline deferred to Phase 1  |
| Maintainability | explicit modules, ADRs, nested context                   | lint/types/CI and small local skills    |
| Security        | sanitized errors, loopback admin ports, non-root apps    | secret/dependency/container scans       |
| Explainability  | future output evidence classification                    | no diagnostic conclusions yet           |
| Reproducibility | locked packages, canonical Make commands                 | clean bootstrap and disposable fixtures |

No telemetry throughput or availability SLA is claimed without measurements.
