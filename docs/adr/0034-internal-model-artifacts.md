# ADR 0034: Internal trusted model artifacts

Status: accepted for Phase 9B.

## Context

The offline training pipeline must preserve an estimator for reproducible local evaluation and
later serving work. Artifact loading can execute code when pickle-based formats are used, and 9B
does not define a public model-serving or artifact-ingest boundary.

## Decision

Store bounded joblib artifacts under a fixed ignored application directory. Write atomically and
record SHA-256, task, model version, dataset, schema, family, threshold and pinned runtime library
versions in the registry. Load only by registered model-version ID after verifying the resolved
path, checksum, allowlisted family, task/spec checksum and exact feature schema. Perform staged
smoke inference before registration. The offline helper accepts only this registry-backed path.

## Consequences

- Joblib/pickle files are trusted internal artifacts and must never be loaded from user input.
- Model artifacts remain local and ignored; they are not shipped to a public API or committed.
- A future service must add its own authorization, resource, schema and lifecycle contract.
- Artifact byte-for-byte determinism is not claimed; estimator predictions and report metrics are
  checked for deterministic repeatability.

## Alternatives considered

- **Load caller-supplied model files:** rejected because deserialization can execute code.
- **Add a registry/object-storage service:** rejected because offline 9B does not need deployment
  or distributed artifact delivery.
- **Persist estimator bytes in the relational database:** rejected because relational rows should
  retain identity and metadata, not opaque model binaries.
