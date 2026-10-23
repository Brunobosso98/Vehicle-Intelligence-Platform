# Phase 9F agent evaluation

This evaluation measures integration behavior over deterministic, synthetic records created by the
Phase 9E disposable pipeline. It checks whether a specific persisted 9E source can be authorized,
revalidated, projected, cited and rendered by the actual LangGraph agent through the official MCP
client. It does not measure predictive accuracy, real-vehicle diagnostic reliability or user safety.

## Independent source oracle

The evaluator runs inside `scripts/phase9e-validation.sh` after the earlier phases have created
canonical 9A FeatureSets, registered 9B/9C artifacts, approved 9D bindings, persisted receipts and
materialized immutable 9E bundles. Expected scores, thresholds, labels, horizons, source role,
cutoffs, artifact state and source IDs come from those persisted bundle and source rows. The
acceptance inspects the private 9F mapping separately from the run-local evidence and public answer.

The evaluated matrix includes all three 9B tasks, all four 9C families, complete/partial/abstained
source outcomes, two vehicle/configuration scopes, read cases with 0/1/2/4 selected IDs, ordinary
MCP denial and direct-call denial, production/disabled/missing-capability/vehicle/budget checks,
same-pull lineage, family-specific specialist routing and capability revocation before a later read.
Any source whose original quality or completeness is insufficient must produce a cited `DATA_GAP`
without its score. An eligible source must produce exact run-local fact bindings and application
rendered prose. A shared 9A FeatureSet is correlated lineage, not independent corroboration.

The focused 9F integration suite also routes a hybrid question through the Orchestrator's knowledge
intent and scope handling with a deterministic synthetic Tier 1 retrieval result. It combines the
retrieval with a selected 9E prediction and asserts that the prediction finding cites only its
run-local MCP evidence while the separate knowledge claim cites only documentary evidence. This
unit scenario checks citation separation and applicability; it is not included in the disposable
database report's scenario counts.

## Measurements and privacy

The ignored `.validation/phase9f/acceptance.json` receipt records its Git SHA, scenario and citation
counts, source completeness/integrity/artifact counts, actual run IDs, end-to-end run durations,
per-stage trace durations, read-count cases, combined evaluator process peak RSS and database-session
peak. Memory and database-session measurements are explicitly scoped to the combined 9E+9F
evaluator process; they are not an isolated Phase 9F production estimate.

Metrics use bounded outcome, result type, horizon, source role, integrity, completeness and status
labels. Authorization and grounding outcomes are bounded categories. The evaluator checks that
vehicle/session/pull/configuration/source identifiers do not appear in metrics or span attributes,
and that source evidence, receipt and feature-set IDs do not enter provider input or public
AgentRun snapshots. Source IDs remain in the ignored operator receipt and the private mapping table.

## Run and delivery status

`make test-prediction-agent-integration` runs the focused contracts. `make phase9f-acceptance` runs
the full disposable 9A→9E→9F pipeline and checks that the 9F report belongs to the current Git SHA.
`make benchmark-prediction-agent-integration` and `make prediction-agent-observability` consume the
same actual receipt. Their output is fixture measurement only. The canonical `full-validation`
workflow uploads the report; only checks on the final PR head establish delivery status.

No paid model API or 7D real-model evaluation is part of this gate. Phase 7D's operator-accepted
120-slot caveat remains unchanged. Real-world evaluation, calibration and drift belong to Phase 9G;
broader agent evaluation belongs to Phase 11.
