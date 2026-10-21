# Phase 9E PredictionEvidence

Phase 9E materializes a bounded, versioned evidence manifest for one immutable Phase 9D
prediction receipt. It preserves the original result and links it to the exact approval event,
9A FeatureSet, 9B model or 9C finding/run/reference snapshot. The manifest is an engineering
provenance record. It does not diagnose a vehicle, estimate failure probability, establish
causation, or control the ECU.

## Ownership and flow

`vehicle_platform.prediction_evidence` owns typed evidence contracts, deterministic graph/fact
construction, safe projection, source verification and immutable persistence. It reads existing
9D/9A/9B/9C repositories; it does not retrain, rescore or select replacement versions.

```text
controlled 9D operator boundary
  -> immutable receipt and historical activation event
  -> repeatable-read, read-only source snapshot
  -> bounded 9A inputs + exact 9B model OR 9C finding/run/frozen reference
  -> cutoff, schema, quality and artifact-hash checks
  -> deterministic graph, facts, gaps and claim bindings
  -> canonical identity/content hashes
  -> immutable 9E bundle + normalized source/node/edge/fact/gap rows
  -> redacted operator projection; later verification appends an audit
```

`NEXT_PULL` is reserved for supervised 9B evidence about the next compatible pull from the
original current-pull snapshot. `AFTER_PULL_OFFLINE` is reserved for a retrospective 9C deviation
result on the already observed pull. The 9D effective cutoff is frozen; the evidence request has
no caller-selected cutoff.

## Graph and integrity

The root `PredictionEvidence` contract contains source nodes, directed edges, facts, explicit gaps,
bounded claim bindings, the original prediction, quality summary, completeness, integrity,
cutoffs, versions and checksums. Node IDs identify the receipt, binding, approval event, FeatureSet,
feature version, model/detector, anomaly run/finding and frozen reference dataset where available.
Edges describe recorded selection, derivation, scoring and comparison relationships; they do not
assert independent corroboration or physical causation.

Facts preserve source authority, units, quality, missing reason, observation/availability time and
source window. Only facts eligible at the frozen cutoff can be emitted. NEXT_PULL evidence never
reads or exposes the future target outcome. 9C reference facts come from the frozen reference
summary and recorded finding, not from a newly fitted detector or a download of the reference
matrix.

Completeness and integrity are separate. An abstention remains an abstention. Source mismatch,
unsupported schema, unavailable sources and artifact unavailability cannot become affirmative
claims. Artifact verification hashes registered bytes only; it never deserializes joblib data.
Hashes provide consistency evidence within the trusted application/database boundary, not digital
signatures against a privileged database writer.

Canonical JSON sorts object keys, normalizes aware timestamps to UTC and rejects non-finite values.
The logical fingerprint covers the frozen evidence identity and excludes `generated_at`; the
content checksum includes it. The evidence UUID is deterministic from the logical fingerprint.
Replay revalidates the stored manifest and converges on one immutable bundle. Oversized manifests
drop optional facts/claims only at record boundaries, increment `omitted_count`, add an
`INCOMPLETE_PROJECTION` gap and downgrade completeness to `PARTIAL` (abstentions stay
`ABSTAINED`).

Hard bounds are 32 nodes, 64 edges, 48 facts, 16 gaps, 8 claims, 4 KiB per fact JSON value, 64 KiB
per stored/HTTP manifest, a 50 MiB artifact hash, two evidence build/artifact-check slots, a six
second evidence budget and 32 verification audits per bundle. PostgreSQL also enforces bundle
size, graph references, allowed enums, row immutability and append-only audit rows.

## Persistence and API

Migration `0017_prediction_evidence` adds:

- `prediction_evidence_bundles`, keyed to the original 9D receipt and unique by receipt/schema;
- `prediction_evidence_sources`, `prediction_evidence_nodes`, `prediction_evidence_edges`,
  `prediction_evidence_facts` and `prediction_evidence_gaps`;
- `prediction_evidence_verification_audits`, append-only and capped at 32 rows per bundle by the
  application.

Update/delete triggers protect every 9E-owned table. Source rows from earlier phases are read-only
and their existing migrations are unchanged. Downgrading 0017 removes 9E records and tables while
preserving the original receipt and all Phase 0–9D data.

All routes remain under the existing controlled `/api/v1/prediction-service` boundary:

| Method and path                       | Behavior                                               |
| ------------------------------------- | ------------------------------------------------------ |
| `POST /runs/{receipt_id}/evidence`    | Materialize or replay one evidence bundle              |
| `GET /evidence/{evidence_id}`         | Read a safe projection without side effects            |
| `GET /runs/{receipt_id}/evidence`     | Read the bundle associated with a receipt              |
| `POST /evidence/{evidence_id}/verify` | Recheck frozen sources and append a verification audit |

The same bearer-header, trusted-peer, disabled-by-default, production denial, body/rate/in-flight
and request-timeout controls used by 9D apply. No fleet listing, public endpoint, user tenancy,
MCP tool, agent node, RAG ingestion or predictive UI is added. The safe projection omits internal
source IDs, source checksums, paths, matrices, tokens and private metadata.

The local operator CLI supports `build`, `verify` and `inspect`. Persistent build/verify requires a
matching development/test environment confirmation and `--yes`; production is rejected.

## Observability and failure behavior

Metrics use finite operation/outcome/gap/dimension labels and measure build/verify count, replay,
duration, graph size and gaps. Traces cover source resolution, claim construction, canonical hash,
immutable persistence, projection reads, independent verification and audit append. No entity ID,
VIN, artifact checksum, raw feature value or operator token is a metric label or span attribute.

Unknown receipts/evidence are 404, scope mismatch follows 9D's 409 behavior, oversized requests
are 413, request/admission limits are 429, disabled service is 503, operation-budget exhaustion is
503/504 according to the 9D middleware boundary, unsupported schemas are typed 422/409 errors,
and immutable identity conflicts are 409. Public errors contain no SQL, driver detail or source
payload.

See the [operator runbook](../runbooks/prediction-evidence.md), [acceptance report](../validation/phase-9e-acceptance.md),
[evaluation narrative](../validation/phase-9e-evidence-evaluation.md), and
[traceability ledger](../validation/phase-9e-traceability-ledger.md).
