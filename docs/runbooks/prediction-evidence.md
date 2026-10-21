# Prediction evidence operator runbook

Phase 9E is a development/test engineering capability. Keep `PREDICTION_SERVICE_ENABLED=false`
outside a controlled local environment. Production enablement is rejected. Do not publish this API
or treat its operator token as vehicle-owner consent.

## Prepare a controlled receipt

1. Use a migrated development/test database and synthetic or explicitly reviewed source data.
2. Register and review an existing 9B model or 9C detector using its existing offline workflow.
3. Approve and activate the exact candidate through the 9D operator controls. The evidence service
   cannot approve, activate, train or select a replacement.
4. Call the existing 9D `next-pull` or `anomalies` route with a timezone-aware cutoff. Retain the
   resulting receipt ID and its response. A score is an engineering output, not a failure
   probability or diagnosis.

## Materialize and inspect

The CLI reads `DATABASE_URL` and `ENVIRONMENT` from the local environment. It never accepts a raw
feature vector, artifact path or new cutoff.

```sh
ENVIRONMENT=test vehicle-prediction-evidence build \
  --receipt-id "$RECEIPT_ID" --confirm-environment test --yes --json

ENVIRONMENT=test vehicle-prediction-evidence inspect \
  --receipt-id "$RECEIPT_ID" --json

ENVIRONMENT=test vehicle-prediction-evidence verify \
  --evidence-id "$EVIDENCE_ID" --confirm-environment test --yes

ENVIRONMENT=test vehicle-prediction-evidence inspect \
  --evidence-id "$EVIDENCE_ID" --json
```

Repeat `build` for the same receipt to confirm the same evidence identity is reused. `inspect` is
read-only. `verify` rechecks the frozen source snapshot and appends a bounded audit; it does not
rerun 9D inference. An unavailable artifact can limit verification without deleting a historical
bundle.

The HTTP equivalents are `POST /api/v1/prediction-service/runs/{receipt_id}/evidence`,
`GET /api/v1/prediction-service/runs/{receipt_id}/evidence`,
`GET /api/v1/prediction-service/evidence/{evidence_id}` and
`POST /api/v1/prediction-service/evidence/{evidence_id}/verify`. They require the same local trusted
peer and bearer-header authorization as 9D. Tokens in query strings, cookies or request bodies are
rejected. There is no unscoped evidence listing.

## Historical revocation and gaps

Revoking or superseding a 9D binding blocks new inference according to the 9D lifecycle. An
authenticated controlled operator can still read evidence for an already-created receipt as a
historical record. The evidence must display abstentions, missing signals, quality limits and
verification gaps without upgrading the original result.

## Validation and tamper simulation

Run `make test-prediction-evidence` for pure contracts. Run `make phase9e-acceptance` only on the
isolated disposable Compose database; its evaluator temporarily corrupts a fixture FeatureSet and
artifact, restores each in a `finally` block, inserts a cutoff-late telemetry sample and modification,
and appends a cutoff-late 9C reference row to prove the verifier rejects changed source counts. The
late rows stay inside the disposable database, which the wrapper removes. It also materializes 9B
and 9C evidence for the same pull and checks that the bundles and claim horizons remain separate.
Never run its tamper procedure against a development, imported or production database. Save reports
only under ignored `.validation/phase9e/`.
