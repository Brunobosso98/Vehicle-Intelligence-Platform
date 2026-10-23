# Phase 9F agent integration acceptance

The independent acceptance is executed inside the Phase 9E disposable database run so the agent
reads actual immutable 9E bundles built from 9B/9C serving receipts while their controlled model
and detector artifacts are available. `make phase9f-acceptance` runs that evaluator and verifies
`.validation/phase9f/acceptance.json`. The canonical full-validation workflow uploads the report
and records a separate Phase 9F result in its exact-commit summary.

The gate checks:

- ordinary MCP discovery hides `get_prediction_evidence`, and direct calls fail without its scope;
- the dedicated token sees the read-only tool and cannot cross the selected-vehicle allowlist;
- a plain recorded-result lookup skips provider routing/turns and opens only the selected evidence;
- read-time 9E verification adds no verification audit and does not rerun inference;
- the next-pull result and retrospective anomaly preserve their distinct horizons and safe wording;
- a same-pull pair has distinct receipt/evidence IDs, a shared FeatureSet and only descriptive
  association language;
- an interpretive prediction request selects only the matching domain specialist;
- the focused integration suite combines a selected 9E prediction with applicable synthetic Phase 8
  documentation and preserves separate prediction and documentary citations;
- exact source evidence, receipt and FeatureSet IDs stay out of provider input and public AgentRun
  snapshots while a private run-local mapping is stored;
- an ordinary vehicle question uses the regular MCP credential and never calls the prediction tool.

All fixtures are generated in an isolated disposable PostgreSQL database. PASS means this controlled
synthetic integration path met its contracts. It does not establish real-vehicle predictive
accuracy, fleet/generalization performance, diagnosis, or production readiness. The CI artifact
contains the commit SHA, selected fixtures, checks and run IDs; exact-head GitHub checks remain the
source of final delivery status.
