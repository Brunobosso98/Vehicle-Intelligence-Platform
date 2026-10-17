# ADR 0030: Technical knowledge storage, retrieval and provenance

Status: accepted for Phase 8 implementation; validation pending.

## Context

MCP owns observed vehicle facts. Phase 8 introduces versioned documentary knowledge without
changing the Phase 5 analytics or allowing source text to become agent policy. The current
TimescaleDB 2.30.2/PostgreSQL 17 image can compile pgvector alongside its existing extension.
A small initial corpus does not justify a hosted vector database or approximate search index.

## Decision

Use PostgreSQL FTS (`simple`) and pgvector exact cosine distance, 1536 dimensions, with
`text-embedding-3-small`. Pin the extension source and verify its checksum during image build.
Use an additive Alembic revision; keep the extension on downgrade. Do not alter revisions 1–10.
Sources have immutable numbered verification snapshots; documents have checksum-addressed
versions and an explicit current-version pointer. Evidence retains the exact source version,
document version, chunk checksum, index identity, retrieval run and vehicle applicability scope.
Conflicts remain separately auditable and prohibit unqualified normative use while open.

Retrieve bounded lexical and vector candidates after source/trust/engine filtering. Fuse ranked
lists with reciprocal rank (k=60), then deterministic trust, applicability, exact identifiers,
version and extraction-quality factors. No paid reranker. Document the implemented formula
in the architecture document and evaluate independently against at least 60 questions.

A typed internal knowledge-tool layer is separate from the read-only vehicle MCP server. It
owns retrieval audit writes, avoiding a write inside MCP's read-only transactions. Agents
receive only bounded evidence; each specialist has an application-owned topic allowlist.
They cannot supply URLs, SQL, engine overrides or arbitrary configuration metadata.

Applicability distinguishes principles, stock targets and exact tune-specific references.
Unknown tuner/map/hardware remains partial, never an invented Stage 2 specification. Historical
scope derives from MCP's session-effective configuration and installed modification intervals.
High trust alone cannot override a mismatch. Community/unverified/quarantined sources cannot
support normative claims. Numeric claims require reviewed value/unit/conditions and applicability.

Copyrighted sources remain in ignored local corpus storage. Commit metadata, reconstruction
procedures and synthetic fixtures, not full manuals. Public APIs expose bounded metadata/citations,
not source files, vectors or a chunk-export endpoint. Source refresh creates a reviewed new version.

Paid embedding is opt-in and independent of generic verification and Phase 7D generation. A durable
ledger reserves conservative token cost before calls, preserves ambiguous failures and atomically
caches completed vectors. Model/dimensions/chunker/normalization changes require a new index identity.
USD 2 is an absolute cumulative ceiling, including smoke, query vectors, retries and failures.

## Alternatives

A hosted vector database adds credentials, billing and isolation without a demonstrated need.
Embeddings alone lose exact identifiers and applicability. Fixed-window chunks lose section/table
provenance. A knowledge tool in MCP would require separating audit writes from its read-only engine.
Model-memory claims have no documentary provenance and cannot satisfy the requirements.

## Consequences and risks

Operators must build the extension and acquire legally usable source material. Old evidence remains
readable after a refresh. Exact search scales linearly; benchmark before adding HNSW/IVFFlat. Source
metadata needs human review; extraction never establishes correctness of ambiguous tables or diagrams.
No speed, retrieval quality or corpus completeness is claimed until measured gates execute.
