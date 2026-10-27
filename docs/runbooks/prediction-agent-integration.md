# Phase 9F agent integration runbook

Phase 9F is a controlled development/test capability. Keep it disabled outside an isolated local
environment. Its records are engineering evidence only; they do not establish real-car accuracy,
vehicle condition, or operator consent.

## Controlled configuration

The API needs all of the following:

- `PREDICTION_SERVICE_ENABLED=true` with the existing 9D operator token and trusted peer policy.
- `VIP_AGENT_PREDICTION_EVIDENCE_ENABLED=true`.
- `VIP_AGENT_PREDICTION_CAPABILITY_TOKEN`: a high-entropy operator capability used only in the
  `X-VIP-Prediction-Agent-Capability` request header.
- `VIP_AGENT_PREDICTION_MCP_TOKEN`: a dedicated high-entropy token for predictive reads, distinct
  from both the operator capability and `VIP_AGENT_MCP_TOKEN`.
- `VIP_AGENT_PREDICTION_VEHICLE_IDS`: a JSON array of selected vehicle UUIDs, for example
  `["00000000-0000-0000-0000-000000000001"]`.
- Matching `VIP_MCP_PREDICTION_EVIDENCE_ENABLED=true`, a separate
  `VIP_MCP_PREDICTION_TOKEN`, `VIP_MCP_PREDICTION_VEHICLE_IDS` as a JSON array, and the ordinary
  `VIP_MCP_TOKEN`. Its transport must be authenticated Streamable HTTP.

Set the 9D `PREDICTION_SERVICE_ENABLED` and the 9F agent/MCP settings together. Startup validation
rejects production, stdio, missing allowlists, shared credentials, and absent 9D service state.
Ordinary MCP readers keep only `mcp:read`; the predictive token receives its own scope.

## Ask about an existing result

1. Materialize the intended 9D receipt through the existing controlled 9E process and retain its
   exact evidence UUID.
2. Include `include_prediction_evidence: true` and one to four selected UUIDs in the agent ask.
   Select no more records than the configured per-run read cap (default two).
3. Send the operator capability in the `X-VIP-Prediction-Agent-Capability` header. The selected
   vehicle must match both configured allowlists; optional `pull_id`/`session_id` further narrows
   context.
4. Read the run's generated evidence ID and answer citation. Exact 9E source/receipt/FeatureSet IDs
   live only in `agent_prediction_evidence_links` for controlled audit and are not returned by API.

The 9E summary is revalidated at read time without writing an audit row. An abstention, incomplete
source, unsupported schema, non-high quality, source mismatch or failed integrity check returns a
data-gap answer. Fix the original source issue through its owning 9A–9E workflow; do not ask the
agent to rescore or change the result.

For a local-only exercise, keep both predictive flags false until an operator has built a
disposable fixture. `make phase9f-acceptance` creates eligible 9B/9C artifacts, approvals, receipts,
9E bundles and agent runs in a disposable database, then removes it. It never needs a paid model
provider. Do not point this runbook flow at retained, customer or production data.

An explicit request uses the existing AgentRun route and exact materialized 9E evidence UUID:

```sh
curl --fail-with-body http://127.0.0.1:8000/api/v1/vehicles/$VEHICLE_ID/agent-runs \
  -H 'Content-Type: application/json' \
  -H "X-VIP-Prediction-Agent-Capability: $PREDICTION_CAPABILITY" \
  --data '{"question":"Qual foi a previsão registrada?","include_prediction_evidence":true,"prediction_evidence_ids":["'$EVIDENCE_ID'"]}'
```

The returned claim cites the AgentRun-local evidence ID. Its limitation identifies the recorded
source role, exact `NEXT_PULL` or `AFTER_PULL_OFFLINE` horizon and non-calibrated engineering score.
An `ABSTAINED`/`PARTIAL` or low-quality bundle instead returns a `DATA_GAP` answer without its
ineligible score. A risk-sensitive question such as “Posso continuar acelerando?” takes a fixed
application refusal path. It makes no safe-to-drive conclusion, failure-probability estimate or
part-replacement instruction, skips prediction reads, and recommends physical inspection by a
qualified professional before high-load operation. English equivalents follow the same policy.

To simulate operator revocation in a running process, rotate the prediction capability and remove
the selected vehicle from both allowlists. New evidence reads in an already running graph fail with
`prediction_capability_revoked`; reconnects and new runs must reauthorize from current settings.
The existing capability is not user/tenant authorization, and production remains rejected even if
all flags and credentials are present.

## Migration and acceptance

Apply migration 0018 together with the previous agent and prediction-service schema versions.
`agent_prediction_evidence_links` has a cascading run foreign key and is private; do not add it to
public API or MCP responses.

Run `make test-prediction-agent-integration` for focused contracts. `make phase9f-acceptance` runs
the 9E evaluator on a disposable `vehicle_test*` database, creates synthetic 9B/9C receipts, and
tests the API agent/MCP/9E path before the database is removed. It writes a current-commit report
under `.validation/phase9f/`. The report contains actual fixture IDs for engineering review and is
ignored by Git. It includes test-only source and artifact mutations from the 9E evaluator; never
run it against retained development or production data. Without Docker, report the acceptance as CI
REQUIRED and run `make verify-cloud` for the cloud-compatible gates.

The MCP operation accepts only a selected vehicle, exact `evidence_id`, and optional session/pull
constraints. It is discoverable only with `mcp:prediction-evidence:read`, served over authenticated
Streamable HTTP, bounded to four selected IDs and the configured per-run read limit (default two).
It is read-only and idempotent; it never creates a receipt or verification audit. Stable failure
categories are `prediction_disabled`, `prediction_capability_required`,
`prediction_capability_revoked`, `prediction_vehicle_not_authorized`,
`prediction_evidence_unavailable`, `prediction_evidence_not_verified`,
`prediction_horizon_mismatch`, and `prediction_evidence_budget_exhausted`. Outside-scope UUIDs are
hidden as unavailable. The 9D operator bearer never enters the MCP client, provider, browser or log.

Before enabling a local run, manually confirm the API and MCP bind only to loopback/private ingress,
all three credentials are distinct and absent from the shell history/report, both vehicle allowlists
match the synthetic fixture, and production/stdio are rejected. Ordinary `mcp:read` discovery and
direct invocation must continue to deny the prediction tool.
