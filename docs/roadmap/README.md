# Roadmap

- Phase 0 — Engineering Foundation (complete; canonical full validation passed before Phase 1)
- Phase 1 — Vehicle & Telemetry Core (complete)
- Phase 2 — Sessions & Pull Detection (complete)
- Phase 3 — Event / Anomaly Engine (complete)
- Phase 4 — Streaming & Live Vehicle Acquisition (complete)
- Phase 5 — Automotive Analytics (complete)
- Phase 6 — MCP Tool Platform (complete; see Phase 6 acceptance evidence)
- Phase 7A — Agent Core & Grounded Orchestration (implemented; see acceptance and PR-head receipts)
- Phase 7B — Investigation & Adaptive Logging (complete; canonical regression verified in Phase 7C)
- Phase 7C — Specialist Agent Orchestration (VERIFIED; PR #35 canonical exact-head gates passed)
- Phase 7D — Real Model Validation & Agent Reliability Baseline (completed with operator-accepted validation caveat; see report)
- Phase 8 — Technical RAG & Knowledge Intelligence (complete; see acceptance report)
- Phase 9A — Feature Engineering Foundation (complete; see acceptance report)
- Phase 9B — Predictive Models (complete as an offline evaluation foundation; see acceptance report)
- Phase 9C — Anomaly Detection (VERIFIED; merged baseline `7fc4c59` after PR #43)
- Phase 9D — Prediction Service (merged and verified; see its acceptance record)
- Phase 9E — PredictionEvidence (merged at baseline `466ce900988bd81e1d968eb319e970955b4011d7`; see its acceptance record)
- Phase 9F — Agent Integration (implementation and independent acceptance on its dedicated branch; exact-head PR checks determine verified delivery)
- Phase 9G — Evaluation / Calibration (implementation on the dedicated branch; exact-head
  independent and canonical checks determine verified delivery)
- Phase 9H — Predictive Intelligence UI (planned)
- Phase 10 — MLOps Platform (planned)
- Phase 11 — Agent Evals / Red Team (planned)
- Phase 12 — Production Cloud Infrastructure (planned)
- Phase 13 — Advanced Vehicle Intelligence (planned)

Phases 7A–7C are implemented. Phase 7B provides the bounded, approved, read-only investigation
and logging-recipe workflow. Phase 7C adds bounded specialists and supervisor orchestration.
Phase 7D is closed by operator acceptance: all 120 slots have PASS across rounds, but a complete
120-execution rerun on the final code was omitted because API balance was insufficient.
This is not a claim of uniform final-source real verification. Final GitHub Actions results
remain separately recorded in the [evaluation report](../validation/phase-7d-real-evaluation.md)
and PR checks. Phase 8 acceptance is recorded. Phase 9A builds only the deterministic offline
feature and dataset foundation; Phase 9B consumes that foundation for offline supervised next-pull
evaluation. Phase 9C adds verified offline anomaly scoring. Phase 9D adds an explicitly approved,
disabled-by-default controlled serving boundary and is merged. Phase 9E is a provenance layer over
immutable 9D receipts and is merged at baseline
`466ce900988bd81e1d968eb319e970955b4011d7`. Phase 9F integrates those existing bundles with the
agent through a controlled MCP scope; it does not start inference. Its exact-head acceptance and
open PR checks determine delivery status. Phase 9G adds an offline, immutable evaluation and
research-only calibration foundation; its real-world scientific validity remains not established
without verified outcomes. Phase 9H remains planned.

# Current phase

Phases 0–6 passed canonical acceptance. The Phase 7A agent consumes MCP facts and validates
structured claims. The [Phase 7A gate](../validation/phase-7a-acceptance.md) records executed
checkpoint evidence and identifies the exact-head delivery receipts.
Diagnosis, proven root-cause interpretation, online prediction services and future infrastructure remain deferred.

## Phase 7C implementation

Bounded specialist orchestration is VERIFIED over the validated Phase 6/7A/7B
boundaries. [The execution specification](../prompts/phase-7c-specialist-agents-supervisor.md)
and [traceability ledger](../validation/phase-7c-traceability-ledger.md) define the full gate.
[PR #35](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/35) merged at
`9b2b2a621d0a903262e4a15a75ea4f102740d60a`. Its final head
`1a07ced07b85393b22b68da62dbcca357ba6d501` passed CI quality/integration E2E,
Security/CodeQL/dependency review and the canonical Docker/full-stack gate
[run 38198158098](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/38198158098).
The local workstation issue does not reopen Phase 7C; historical receipts remain intact.
Comprehensive real-model evaluation is Phase 7D; documentary retrieval is Phase 8.

## Phase 8 acceptance

[The specification](../prompts/phase-8-technical-rag-knowledge-intelligence.md) remains the full
definition of done. Storage/retrieval, trust/applicability, controlled source selections, embedding
spend protection, scoped agent tools and the citation UI passed the corrected implementation
acceptance described in [the report](../validation/phase-8-acceptance.md). Its Phase 7D paid-suite
caveat remains separately documented.

## Phase 9A implementation checkpoint

The 9A branch defines 79 deterministic features, immutable version identity and provenance,
cutoff-aware pull generation, temporal/leakage validation, bounded reproducible datasets, operator
CLIs, profiling and observability. It has no model, prediction, public feature API or predictive UI.
The local independent evaluator, disposable integration, 100-pull benchmark and observability gate
are recorded in the [Phase 9A acceptance report](../validation/phase-9a-acceptance.md); Phase 9A is
merged and complete. Phase 9B is also merged and complete as an offline supervised evaluation
foundation, with its scope and evidence in the [architecture](../architecture/phase-9b-predictive-models.md)
and [acceptance report](../validation/phase-9b-acceptance.md). Neither phase serves online predictions
or diagnoses vehicle conditions.

The Phase 9 sequence is deliberately separated: 9B offline predictive models; 9C offline anomaly detection; 9D
prediction service; 9E PredictionEvidence; 9F agent integration; 9G evaluation/calibration; 9H
predictive intelligence UI.

## Phase 9C implementation

Phase 9C builds offline statistical deviation detectors over canonical 9A FeatureSets. It keeps
vehicle/configuration/modification/source cohorts isolated, requires temporal and independent-session
support, and freezes method/threshold choices from validation sessions before the held-out test.
It does not replace Phase 3 factual event rules or reuse Phase 9B supervised model labels. Follow
the [architecture](../architecture/phase-9c-anomaly-detection.md), [runbook](../runbooks/anomaly-detection.md),
the [acceptance report](../validation/phase-9c-acceptance.md), [model evaluation](../validation/phase-9c-model-evaluation.md),
and [traceability ledger](../validation/phase-9c-traceability-ledger.md). Implementation SHA
`c4da7f5df85f6a91e7add628e41c03885bd5f049` passed the canonical full-validation workflow and all
CI/Security checks before PR #43 merged into baseline `7fc4c59`; run links and artifact evidence
are recorded in its acceptance report.

## Phase 9D controlled serving

The [Phase 9D architecture](../architecture/phase-9d-prediction-service.md),
[runbook](../runbooks/prediction-service.md),
[acceptance record](../validation/phase-9d-acceptance.md),
[serving evaluation](../validation/phase-9d-model-serving-evaluation.md), and
[traceability ledger](../validation/phase-9d-traceability-ledger.md) define the controlled API,
approval state and evidence limits. Phase 9D is merged; its earlier exact-head receipts remain in
its acceptance report. No public production service is implied.
No public production service is implied.
