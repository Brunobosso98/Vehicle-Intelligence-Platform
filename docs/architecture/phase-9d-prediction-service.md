# Phase 9D controlled prediction service

Phase 9D adds a bounded FastAPI boundary around already registered Phase 9B supervised models
and Phase 9C anomaly detectors. It serves controlled engineering results from persisted Phase 9A
FeatureSets. A score is not a failure probability, diagnosis, maintenance instruction, or vehicle
control signal. The service is disabled by default, refuses production enablement, and does not
provide account or tenant authorization.

## Ownership and request flow

`vehicle_platform.predictions` owns serving authorization, binding lifecycle, request admission,
request identity, immutable result receipts, and the adapter between 9A/9B/9C. It delegates
feature generation and feature formulas to 9A, supervised inference and artifact verification to
9B, and detector inference and artifact verification to 9C. HTTP requests cannot train, calibrate,
activate versions, upload artifacts, or submit arbitrary feature vectors.

```text
private/loopback peer + bearer authorization
  -> disabled/environment fence, rate/body/concurrency/time budgets
  -> one active approval for exact task/family + role + environment + scope
  -> completed pull and persisted 9A FeatureSet at requested cutoff
  -> registered artifact checksum and schema verification
  -> bounded worker: 9B offline_predict OR 9C score_detector_version
  -> immutable receipt bound to request fingerprint and activation event
```

The supervised horizon is `NEXT_PULL`: classify the next compatible pull using only the current
pull's cutoff snapshot. Anomaly results use `AFTER_PULL_OFFLINE` for the already observed pull.
The route and typed response keep these horizons separate. Missing or incompatible evidence
produces an explicit reason-coded abstention; it never creates a fabricated score.

## Controlled access

`PREDICTION_SERVICE_ENABLED` defaults to `false`. Enabling it requires `ENVIRONMENT=development`
or `test` and a `PREDICTION_OPERATOR_TOKEN` of at least 43 non-space characters. Production
enablement is rejected during settings validation. The API checks the bearer header in ASGI
middleware before reading a request body or touching the database. Query, cookie, and body tokens
are not accepted. The peer address must be in `PREDICTION_TRUSTED_NETWORKS` (loopback by default;
only private, loopback, or link-local CIDRs are accepted). Forwarded headers do not establish
identity. Bind a controlled local instance to loopback; do not expose it through public ingress.

This operator token grants access to a controlled local dataset, not ownership of a vehicle. The
service must remain disabled until a future platform-wide account and vehicle authorization layer
exists for any shared or public deployment.

## Approval and immutable state

Migration `0016_prediction_service` adds:

- `prediction_serving_bindings`: immutable exact model/detector checksum, interface/schema,
  source-role, development/test environment, scope, operator reason, and review reference.
- `prediction_serving_events`: append-only approval, activation, supersession, revocation and
  rollback events. Current state is derived from ordered events; an advisory lock serializes
  competing transitions within one serving slot.
- `prediction_receipts`: bounded serialized response, idempotency fingerprint, cutoff, binding
  and activation-event snapshot, feature/model/detector checksums, score or abstention and minimal
  lineage. Database triggers reject updates and deletes on all three tables.

Approval is a second, explicit step after inspecting an existing registered candidate and trusted
artifact. One active binding is allowed per result kind, task/family, source role, environment and
scope. Each inference captures the activation event before loading inputs; a later revocation
blocks new requests and replays, while an already admitted request can finish against its captured
binding. Rollback is another event and restores a prior approved binding without editing history.

## Temporal and input compatibility

The caller supplies an aware observation cutoff. It must not precede the pull end or exceed the
configured bounded future allowance. The repository selects only a genuine persisted
`phase9a-pull-v2` FeatureSet available at that cutoff. Serving never invokes feature generation.
Snapshot checks bind the canonical version/checksum, source role, vehicle, configuration,
modification context, source window, quality, feature schema, and provenance. Post-cutoff ingestion
and metadata are excluded. Cross-vehicle, unsupported source, incomplete pull, invalid value,
missing required signal, incompatible schema and low-quality cases abstain or fail with a
sanitized typed error according to the request state.

Feature coverage counts applicable model inputs. A feature marked `not_applicable` remains in the
bounded missing-reason counts but is excluded from the coverage denominator; unavailable and
invalid expected features still reduce coverage.

Phase 9B versions remain task-specific and keep their frozen decision thresholds. The adapter
builds ordered values, units, missingness and quality from the persisted snapshot and calls the
registered `offline_predict` helper. Phase 9C uses the registered detector version and canonical
`AnomalyService.score_detector_version`; the service does not fit or tune detectors on request.
Caller-selected versions are accepted only when they match the active approved binding.

## Routes and resource limits

All routes live under `/api/v1/prediction-service` and require the same bearer/network/enablement
checks:

| Route                    | Purpose                                                   |
| ------------------------ | --------------------------------------------------------- |
| `GET /versions`          | Paginated safe metadata for active approved bindings only |
| `POST /next-pull`        | One approved Phase 9B supervised task                     |
| `POST /anomalies`        | One approved Phase 9C family                              |
| `GET /runs/{receipt_id}` | Retrieve the exact immutable response receipt             |

No approval or model-management route is exposed over HTTP. State-changing controls are local CLI
operations requiring `--yes` and a matching `--confirm-environment`.

Dedicated settings cap request body at 4 KiB by default (maximum 16 KiB), in-flight requests at 8
(maximum 32), CPU workers at 2 (maximum 4), request rate at 30 per minute (maximum 300), body wait
at 2 seconds, handler duration at 8 seconds, and future cutoff at 5 seconds. Numerical libraries
are constrained to one thread. A fixed worker pool and semaphore isolate artifact loading and
inference from the async event loop. Timeouts, disconnects, and cancellation release admission
resources; a CPU permit remains owned until a non-cancellable worker actually completes.

## Idempotency, errors, and minimal lineage

An optional bounded `Idempotency-Key` is stored only as a hash. A canonical request fingerprint
includes endpoint, request semantics, active binding event, and cutoff. Same-key/same-request and
concurrent replays converge on one receipt; changed request reuse conflicts. Authorization and
current revocation are checked before receipt replay. Failed persistence leaves no partial receipt
and can be retried.

Responses expose typed status, result kind, horizon, cutoff, safe task/family result, quality,
reason-coded abstention and bounded lineage identifiers. Raw telemetry, feature matrices,
VINs, artifact paths, private input/provenance hashes and secrets are not in the HTTP response or
observability labels. Errors distinguish authorization, peer denial, invalid input, unavailable
record/version, request budget, timeout, and sanitized internal failure.

## Observability and limits

Metrics use bounded endpoint/status/reason/result vocabularies for requests, receipts, approval
changes, denials, in-flight work, duration, worker activity and artifact loads. Traces separate
admission, binding resolution, feature lookup, artifact verification, model/detector scoring and
receipt persistence. No entity IDs, hashes, raw values, tokens or artifact paths are metric labels.
Latency and RSS are reported as observations; correctness and configured resource bounds are gates.

This service is an initial controlled boundary, not production readiness. Phase 9E shared evidence,
9F agent integration, 9G calibration/drift, 9H predictive UI, public tenancy/cloud identity,
retraining, and all ECU control are outside this phase.
