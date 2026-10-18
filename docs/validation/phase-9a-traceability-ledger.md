# Phase 9A traceability ledger

The governing specification is
[Phase 9A Feature Engineering Foundation](../prompts/phase-9a-feature-engineering-foundation.md).
This ledger links requirements to the implementation and executable evidence. The final exact-head
CI receipts remain tied to the open Phase 9A PR.

| Requirement group                                              | Implementation                                                                                    | Evidence                                                                   |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Repository baseline and module boundaries                      | `vehicle_platform.features`; migration `0013`; no source-domain writes                            | `make check-api`, migration integration, full regression                   |
| Feature taxonomy, definitions, units and trusted calculators   | `features/domain.py`, `features/registry.py`                                                      | `tests/unit/test_features.py`; registry manifest count in acceptance       |
| Version identity and deterministic persistence                 | `FeatureSetVersion`, source/provenance hashes, unique feature-set identity and advisory lock      | `evaluate_features.py`; `test_zzz_features.py`                             |
| Provenance, quality, context and configuration history         | `features/context.py`, `features/service.py`                                                      | acceptance and disposable DB fixture                                       |
| Cutoff, temporal availability, leakage and horizon foundations | `features/service.py`, `features/datasets.py`                                                     | future-ingestion/event/pull, cross-vehicle/configuration and horizon tests |
| Dataset identity, validation, profiling and stable manifest    | `features/domain.py`, `features/datasets.py`                                                      | unit dataset checks; evaluator checksum/profile; 100-pull benchmark        |
| Safe export and resource bounds                                | fixed `.artifacts/phase9a` root, JSONL, atomic writes, 64 MiB cap, row/payload/lineage/batch caps | path traversal unit test; dataset acceptance                               |
| Operator workflow and recovery                                 | `scripts/generate_features.py`, `scripts/build_feature_dataset.py`                                | CLI help/type/lint checks; runbooks; acceptance commands                   |
| Migration and historical-data safety                           | revision `0013`, immutable prior revisions                                                        | disposable migration integration and canonical full validation             |
| Metrics, spans and bounded labels                              | `observability/telemetry.py`, feature service and builder                                         | `make feature-observability`; local metric and span receipt                |
| Security and API/UI boundary                                   | trusted formulas, parameterized SQL, no public API/MCP/UI, bounded operator export                | security review, code audit, `make security`                               |
| Phase 0–8 regression                                           | existing canonical suite plus Phase 9A gates in `make verify`                                     | exact-head workflow on PR; no paid Phase 7D or Phase 8 operations          |
| 9B candidate selection                                         | ranked semantic/availability/leakage/source/stability shortlist                                   | architecture and acceptance documents                                      |

The controlled acceptance dataset has two vehicles, three configurations, four sessions, five
pulls, thermal/boost/fuel variation, invalid and future-ingested observations, two chronological
events including a late-created event, an unavailable fuel signal, one incompatible configuration
transition and one low-quality pull. Benchmark fixtures are separate synthetic rows and are never
represented as real vehicle observations.
