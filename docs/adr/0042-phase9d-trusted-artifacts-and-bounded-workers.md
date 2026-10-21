# ADR 0042: Phase 9D trusted artifacts and bounded inference workers

Status: accepted for Phase 9D.

## Context

The existing 9B/9C artifacts use joblib and CPU-bound scikit-learn inference. Deserialization is
trusted-code execution, and synchronous scoring on the FastAPI event loop can stall unrelated
requests. Serving must retain the existing artifact validation and use a fixed workload budget.

## Decision

Load models/detectors only by an approved registered version through the existing 9B/9C trusted
artifact stores, which verify registered paths, checksums, schemas and supported dependency/model
contracts. Never accept caller paths or uploaded joblib data. Run loading and scoring on a fixed
thread pool bounded by an asyncio semaphore, constrain numerical libraries to one thread, and
enforce request deadlines. On coroutine cancellation, keep the CPU permit until the underlying
thread actually exits.

## Consequences

- A timed-out request cannot create unbounded background CPU work.
- Artifact bytes and latency are measured; benchmark timings are observations rather than a
  cross-machine SLA.
- `threadpoolctl` is an explicit pinned runtime dependency for fixed numerical-thread limits.
- Model training, detector fitting and threshold selection remain offline operations.

## Alternatives considered

- **Call `joblib.load` on request-supplied data:** rejected as arbitrary pickle execution.
- **Run synchronous scoring in the event loop:** rejected because it stalls other async work.
- **Spawn one unconstrained process per request:** rejected due to unbounded process and memory
  growth.
