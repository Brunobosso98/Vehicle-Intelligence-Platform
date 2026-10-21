# Controlled prediction service runbook

This runbook is for a local development/test database only. Phase 9D is disabled by default and
cannot be enabled in production. Do not expose it through a public ingress. Results are engineering
signals, not diagnoses or failure probabilities.

## Enable a local controlled instance

1. Start the local disposable development stack and migrate it with the normal project workflow.
2. Generate a high-entropy local token without printing or committing it. For example, use
   `openssl rand -base64 48` in a private terminal and store the value in a local ignored `.env`.
3. Set `ENVIRONMENT=development`, `PREDICTION_SERVICE_ENABLED=true`, and
   `PREDICTION_OPERATOR_TOKEN` to that value. Keep the server bound to `127.0.0.1`.
4. Start the API and confirm normal health checks. Prediction routes return a sanitized 503 until
   the complete configuration is valid. Never enable this in production.

## Inspect, approve, and activate a candidate

From the repository root, use the local CLI with the same database environment. Candidate inspection
verifies registry state and trusted artifact integrity; it does not activate anything.

```bash
apps/api/.venv/bin/vehicle-prediction inspect --kind next_pull --version-id VERSION_UUID
apps/api/.venv/bin/vehicle-prediction approve --kind next_pull --version-id VERSION_UUID \
  --source-role synthetic --reason "Reviewed controlled engineering evaluation" \
  --operator-id local-operator --review-reference phase9d-review-001 \
  --yes --confirm-environment development
apps/api/.venv/bin/vehicle-prediction activate --binding-id BINDING_UUID \
  --reason "Activate reviewed controlled test binding" --operator-id local-operator \
  --yes --confirm-environment development
```

Use `--kind anomaly` for an accepted Phase 9C detector and select its supported source role.
Review the 9B/9C evaluation evidence, feature schema, source capability, checksum, runtime
compatibility and limitations before approval. Never label synthetic evidence as real-car
validation. The CLI refuses production and requires both the explicit `--yes` and an exact
environment confirmation for every state change.

## Request and retrieve a receipt

Requests require the configured operator bearer token. `observation_cutoff` must be timezone aware
and refer to the current completed pull. Supply an idempotency key when a caller needs safe retries.
Use only approved task/family and source-role values. The exact request/response schemas are
generated in `packages/contracts` from OpenAPI.

```bash
curl --fail-with-body http://127.0.0.1:8000/api/v1/prediction-service/versions \
  -H "Authorization: Bearer $PREDICTION_OPERATOR_TOKEN"
curl --fail-with-body http://127.0.0.1:8000/api/v1/prediction-service/next-pull \
  -H "Authorization: Bearer $PREDICTION_OPERATOR_TOKEN" \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: local-run-0001' \
  --data '{"pull_id":"PULL_UUID","vehicle_id":"VEHICLE_UUID","observation_cutoff":"2026-01-01T12:00:00Z","source_role":"synthetic","task":"NEXT_PULL_THERMAL_DEGRADATION"}'
curl --fail-with-body http://127.0.0.1:8000/api/v1/prediction-service/anomalies \
  -H "Authorization: Bearer $PREDICTION_OPERATOR_TOKEN" \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: local-run-0002' \
  --data '{"pull_id":"PULL_UUID","vehicle_id":"VEHICLE_UUID","observation_cutoff":"2026-01-01T12:00:00Z","source_role":"synthetic","family":"boost_air"}'
curl --fail-with-body http://127.0.0.1:8000/api/v1/prediction-service/runs/RECEIPT_UUID \
  -H "Authorization: Bearer $PREDICTION_OPERATOR_TOKEN"
```

The sample UUIDs and timestamp are placeholders. A missing or incompatible FeatureSet produces an
explicit abstention; Phase 9D does not create features on demand. Treat `NEXT_PULL` and
`AFTER_PULL_OFFLINE` as different result meanings. Do not infer probability, diagnosis, causation,
maintenance urgency, or vehicle safety from a score.

## Revoke, roll back, and troubleshoot

`revoke` prevents new inference and receipt replay against the binding. A request for a slot with no
other active version returns a sanitized `409 PREDICTION_NO_UNIQUE_ACTIVE_VERSION`. `rollback`
targets a previously approved binding whose latest event is `SUPERSEDED`; it appends a
`ROLLED_BACK` event and supersedes the currently active binding. It does not delete or edit history.
Use `vehicle-prediction list` to inspect active bindings. Save the `binding_id` emitted by `approve`
and `event_id` from each state change in the operator's review record.

```bash
apps/api/.venv/bin/vehicle-prediction list --kind next_pull --source-role synthetic
apps/api/.venv/bin/vehicle-prediction revoke --binding-id ACTIVE_BINDING_UUID \
  --reason "Revoke the reviewed synthetic test binding" --operator-id local-operator \
  --yes --confirm-environment development
# Repeat the same authorized next-pull request above: expect HTTP 409 with
# PREDICTION_NO_UNIQUE_ACTIVE_VERSION when no other version is active.
apps/api/.venv/bin/vehicle-prediction rollback --binding-id SUPERSEDED_BINDING_UUID \
  --reason "Restore the previously reviewed synthetic test version" --operator-id local-operator \
  --yes --confirm-environment development
apps/api/.venv/bin/vehicle-prediction list --kind next_pull --source-role synthetic
```

Use a `SUPERSEDED_BINDING_UUID` captured from its earlier approval/activation output and operator
audit record; `list` shows active bindings only. A revoked binding cannot be used as a rollback
target; review the candidate and its immutable history before restoring a prior version. The test
evaluator confirms that revocation blocks new inference and replay, and that rollback restores an
earlier reviewed binding in the same slot.

Common responses:

- `401`: missing or invalid bearer token. Tokens in query, cookie, or body are never accepted.
- `403`: request peer is outside the configured private/loopback trusted CIDRs.
- `409`: version/binding/artifact conflict or deterministic approval restriction.
- `413`, `429`, `408`, `504`: configured body, rate, body-wait, or handler budget.
- `422`: request shape, cutoff, source, or idempotency key is invalid.
- `503`: serving is disabled or unavailable.
- `404`: requested pull/receipt is unavailable without disclosing unauthorized vehicle history.

Check API logs and metrics using bounded reason labels only. Never add token, VIN, raw telemetry,
artifact path, feature values or checksums to a diagnostic. If an artifact fails verification,
restore it from its trusted registered source and re-inspect the version; do not bypass the loader.

## Validation commands

`make test-prediction-service` runs focused unit checks. `make phase9d-acceptance` builds an isolated
disposable database, prepares controlled 9A/9B/9C fixtures, performs the migration round trip and
real HTTP acceptance, and writes evidence under ignored `.validation/phase9d/`. The evaluator uses
synthetic engineering fixtures only. Docker-backed integration and the canonical full-stack gate
must pass on the exact PR head before Phase 9D can be called verified.
