# Predictive Intelligence UI operator runbook

This workspace is for one controlled local or test operator. It is not a customer or vehicle-owner
authorization system. Do not expose the API or web service to public ingress.

## Configure a local operator session

Keep all values in an ignored local environment file or secret manager. Generate independent,
high-entropy values for `PREDICTION_OPERATOR_TOKEN`, `PREDICTIVE_UI_OPERATOR_SECRET`, and
`PREDICTIVE_UI_SESSION_SECRET` (at least 43 non-whitespace characters each). Set:

```dotenv
ENVIRONMENT=development
PREDICTION_SERVICE_ENABLED=true
PREDICTION_OPERATOR_TOKEN=<unique server-only 9D bearer>
PREDICTION_OPERATOR_VEHICLE_IDS=<comma-separated fixture vehicle UUIDs>
PREDICTIVE_UI_ENABLED=true
PREDICTIVE_UI_OPERATOR_SECRET=<independent browser operator credential>
PREDICTIVE_UI_SESSION_SECRET=<independent session MAC secret>
PREDICTIVE_UI_ALLOWED_VEHICLE_IDS=<same bounded vehicle UUIDs>
PREDICTIVE_UI_ORIGIN=http://localhost:3000
PREDICTIVE_UI_API_ALLOWED_HOSTS=api,localhost,127.0.0.1,::1
PREDICTIVE_UI_DEMO_ENABLED=false
```

For HTTPS set `PREDICTIVE_UI_COOKIE_SECURE=true`. Compose defaults to a private API/web network and
the web service allowlists `api` as its upstream hostname. If the fixed subnet conflicts with a
local network, update `compose.yaml` subnet and the API's trusted web `/32` together. The vehicle
allowlist must be a small controlled fixture scope; an ID from the public vehicle selector is not
proof of ownership.

Start the API and web app using the repository's documented development command. Open
`http://localhost:3000/predictive`, authenticate with the independent UI operator credential, then
choose only a server-returned allowed vehicle. Real persisted history comes only from 9D receipts;
the 9G summary is a static offline research snapshot.

## Modes and interpretation

- **Controlled operator:** requires all independent flags, secrets, API peer/bearer checks, and
  the vehicle allowlist. History/detail/evidence/AgentRun reads are bounded and read-only.
- **Synthetic demonstration:** set `PREDICTIVE_UI_DEMO_ENABLED=true` only in development/test.
  The button is explicit; the static fixture makes no API request and cannot replace missing real
  history.
- **Unavailable/empty:** inspect API and browser route status, configured origin, and allowlist.
  No recorded receipt does not mean no anomaly or healthy condition.

9B values are engineering-validation scores, not mechanical-failure probabilities. 9C values are
offline statistical scores, not engine-health percentages, fault proof, or diagnosis. Phase 9G is
synthetic-only research; real-world predictive validity and calibration remain `NOT_ESTABLISHED`.
The workspace never runs inference, training, evidence materialization/verification, agent
execution, calibration promotion, background monitoring, or ECU control.

## Disable and invalidate access

Set `PREDICTIVE_UI_ENABLED=false` or remove the UI operator secret/session secret to make all real
workspace routes fail closed. Also disable `PREDICTION_SERVICE_ENABLED` or rotate its bearer to
close the upstream service. `ENVIRONMENT=production` always disables this UI even when flags are
set. Restart the local web process after credential rotation; sessions are process-local and the
restart revokes them. Use the UI logout control for normal session termination.

## Troubleshooting

| Symptom                 | Check                                                                                                                                                                 |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Workspace unavailable   | Environment is `development`/`test`; all independent flags/secrets exist; configured origin matches the browser URL.                                                  |
| Login rejected          | UI operator credential is separate from the 9D bearer; credentials are at least 43 non-whitespace characters.                                                         |
| No vehicles             | Both UI and API allowlists contain the same valid vehicle UUID and the 9D service is enabled.                                                                         |
| Upstream unavailable    | API base URL uses an explicitly allowlisted host and the BFF peer is in `PREDICTION_TRUSTED_NETWORKS`.                                                                |
| Receipt/evidence hidden | Vehicle, receipt and evidence source must match; schema and original score/horizon/source role must be supported and consistent.                                      |
| Evidence absent         | No evidence is materialized by opening the UI. Follow the Phase 9E operator runbook outside this workspace if a controlled evidence operation is separately required. |

See [Phase 9D](prediction-service.md), [Phase 9E](prediction-evidence.md), and
[Phase 9F](prediction-agent-integration.md) runbooks for their independent service boundaries.
