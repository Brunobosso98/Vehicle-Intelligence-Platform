# ADR 0043: Phase 9E immutable prediction evidence

Status: accepted for Phase 9E implementation; final exact-head verification is recorded in the
acceptance report.

## Context

Phase 9D stores an immutable prediction receipt, but operators need a bounded explanation of the
receipt's exact source versions, temporal eligibility, quality and gaps. Re-running inference or
fitting a replacement model would change the historical question and can make revoked or unavailable
artifacts unsafe to load.

## Decisions

- A `PredictionEvidence` manifest is owned by a new `prediction_evidence` module and is rooted in one
  immutable 9D receipt. Supervised `NEXT_PULL` and anomaly `AFTER_PULL_OFFLINE` remain distinct.
- Source resolution uses a repeatable-read, read-only transaction. It retains IDs and hashes
  internally, uses the original cutoff, validates 9A feature provenance and 9B/9C registry links,
  and never trains or invokes online inference.
- A versioned canonical JSON graph is stored in PostgreSQL with normalized source/node/edge/fact/gap
  rows. Logical identity excludes generation time; the content checksum includes it. Identical
  source snapshots replay deterministically. Changed sources conflict rather than overwrite.
- Every evidence-owned table rejects UPDATE and DELETE. Verification outcomes are separate
  append-only audit rows. Downgrade drops only 9E data.
- Operator responses use a distinct privacy-safe projection. The routes reuse 9D's network, bearer,
  disablement and resource controls; production stays disabled.
- Facts describe recorded observations and statistical associations only. Scores are never
  probabilities, model agreement is not independent corroboration, and evidence does not imply
  causation or diagnosis.

## Consequences

Operators can inspect and later recheck exactly which immutable records supported an engineering
result, including explicit missingness and unverifiable sources. PostgreSQL remains the only graph
store. Content bounds can yield a structured partial bundle with an omission count. Hashes protect
consistency inside the trusted application/database boundary but do not authenticate a privileged
database rewrite.

No 9F agent, 9G calibration, 9H UI, production exposure or ECU control path is introduced.

## Alternatives considered

- **Recompute the prediction during evidence retrieval:** rejected because it could select current
  data or a replacement model and would not preserve the original decision.
- **Store only a JSON response:** rejected because normalized source and graph rows need database
  constraints and reviewable lineage.
- **Add a graph database:** rejected because the bounded graph fits the existing PostgreSQL stack.
- **Treat matching 9B/9C results as votes:** rejected because shared features and contexts are
  correlated and do not establish independent support.
