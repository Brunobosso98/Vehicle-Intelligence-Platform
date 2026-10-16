# Phase 8 technical RAG

Implementation and validation in progress. Real corpus/retrieval, browser and instrumentation
checkpoints have passed; complete frozen regressions and exact-final-head acceptance remain pending.
The authoritative requirements remain the
[Phase 8 specification](../prompts/phase-8-technical-rag-knowledge-intelligence.md).

## Ownership and storage

MCP is the sole source of observed vehicle facts. KnowledgeRepository owns only `knowledge_*`
tables. RetrievalRun audit writes use its own bounded transactions. The knowledge layer cannot
write telemetry, approve acquisition or issue ECU commands. [ADR 0030](../adr/0030-technical-knowledge-storage-and-provenance.md)
records the vector backend, trust/applicability, embedding identity and copyright decisions.

Migration 0011 adds immutable numbered source verification snapshots, document versions, current
version pointers, structured chunks/FTS, index metadata, pgvector embeddings, conflicts and retrieval
audit. It preserves old evidence and does not rewrite prior migrations. Downgrade removes only
knowledge tables and preserves the shared vector extension. Exact cosine search avoids unnecessary
HNSW/IVFFlat infrastructure for the small initial corpus. pgvector 0.8.2 is checksum-pinned and built
alongside TimescaleDB 2.30.2/PostgreSQL 17; LLVM bitcode is disabled for compatible portable builds.

## Extraction and acquisition

The operator-only downloader accepts HTTP(S), validates public DNS addresses, pins the connection
IP with hostname TLS verification, checks every redirect, bounds redirects/time/bytes and validates
MIME/signature. No agent receives URL fetching, filesystem paths, SQL or shell capabilities.
HTML ignores scripts/styles/navigation; headings and table rows retain context. Markdown follows
headings, paragraphs and tables. PDF parsing runs with a clean environment and CPU/address-space/
page/character limits in an isolated process with an execution deadline. Image-only pages explicitly
lack OCR; PDF tables require review. Oversize indivisible paragraphs/tables require operator review
instead of blind token slicing. Duplicate content is checksum-deduplicated within a document.

## Ranking

Current verified source status, non-community trust, engine/platform compatibility and current
approved document versions filter candidate generation. The index joins only stored vectors belonging
to its explicit identity, keeping pending unembedded chunks out of indexed retrieval.

The union of the top 30 lexical and top 30 vector candidates is reranked deterministically:

`score = (1/(60+lexical_rank) + 1/(60+vector_rank)) * trust * applicability * quality * (0.25 + 0.75*exactness)`

Absent list membership contributes zero. Trust factors are 1.0/0.9/0.6/0 for tiers 1–4.
Applicability is 0 for incompatible contexts, bounded at 0.7 for partial, otherwise 0.75 plus
0.05 per explicit matched identity dimension, capped at 1. Ambiguous extraction has factor 0.4;
other extraction quality has factor 1. Open conflicts multiply score by 0.8 and prohibit normative
eligibility. Exactness is the fraction of query alphanumeric tokens present in chunk text, heading,
publisher, document title and documentary tuner metadata.
Stable chunk-ID ordering resolves ties. Return at most five citations and audit the scope/index.
Ranking version `rrf-trust-applicability-identifiers-v3` includes these explicit identifiers after
the first 60-case synthetic-vector evaluation exposed excessive specificity preference. An explicitly
requested documentary vendor filters sources without changing the vehicle's actual tuner/map.
Lexical candidates use
a bounded OR of distinct alphanumeric query terms (`postgres-simple-or-v2`); vector list membership
requires cosine similarity greater than 0.2. Only current document versions participate, so an old
version cannot silently outrank its approved replacement. Publication and audit preserve old snapshots.

Stock references on a tuned/unknown calibration remain partial. Tune-specific references require
known vendor and map, with supplied fuel/hardware/part restrictions checked. A stage label alone
cannot supply that identity. `knowledge_scope` consumes MCP-resolved session-effective configuration
and active modification intervals; the later active configuration cannot overwrite a historical one.
Unknown part identity is preserved because the current Modification schema has no explicit part number.

## Evidence and claims

KnowledgeEvidence links retrieval → source verification version → document checksum/version →
chunk checksum/page/section/heading path. It retains the vehicle scope hash, trust/applicability,
rank scores, a bounded snippet and reviewed numeric facts. Eligible normative evidence requires
verified Tier 1/2, exact applicability, adequate extraction and no open conflict. Numeric validation
matches the reviewed value, unit and source conditions exactly under the same vehicle scope.

Reviewed numeric facts distinguish descriptive values from stock targets, tune targets and service
limits. A cylinder count cannot satisfy a pressure-target request. The host renderer preserves the
literal, unit and source operating conditions; a conditional documented target does not establish
that the recorded vehicle met those conditions. Stock targets require explicitly stock calibration
without a contradictory Stage label. Tune targets require matching vendor/map metadata. Validation
recomputes applicability against the current scope instead of trusting a stale eligibility flag.
Pending documents, community/unverified sources and open conflicts cannot produce these claims.

AgentRun and scoped specialist tools now consume these contracts. The independent disposable
PostgreSQL/MCP evaluator executed four deterministic knowledge/hybrid questions. Bounded metadata,
query and vehicle-isolated citation APIs and the minimal UI are implemented. Browser acceptance
passed; the strengthened hybrid operating-condition cohort and final-head repeats remain pending.
Phase 7A vehicle claim grounding remains
separate from application-rendered documentary excerpts.

Candidate caching is bounded to 64 entries/30 seconds and keyed by intent, complete vehicle scope,
index and a database revision. Source verification-version changes, document publication and conflict
status changes invalidate the revision before reuse. Every answer receives new evidence/retrieval IDs
and its own audit, including cache hits. This avoids cross-vehicle/configuration citation reuse.

## Embedding spend boundary

`EmbeddingLedger` uses SQLite transactions and integer pico-dollar charges for serialized admissions.
UTF-8 byte counts conservatively bound input tokens. Pending reservations survive failures/restarts;
completed usage and vectors commit atomically. Cache identity includes document/chunk checksums,
model/dimensions, chunker/normalization and the explicit embedding-cache version. Corpus/ranking publication IDs
do not force repurchasing unchanged embeddings. A pipeline-scoped content alias also reuses unchanged
text across document versions, retaining each document/checksum cache identity and original charge. The cumulative absolute ceiling
is USD 2, including smoke, document and query calls. Provider SDK retries are zero. A failed request
retains its reservation; no automatic repurchase loop exists.

Official documentation was fetched on 2026-10-15: [model and price](https://developers.openai.com/api/docs/models/text-embedding-3-small),
[dimensions and guide](https://developers.openai.com/api/docs/guides/embeddings),
[endpoint](https://developers.openai.com/api/reference/resources/embeddings/methods/create).
The verified standard rate is USD 0.02 per million input tokens, default dimensions 1536.
The dedicated paid CLI executed a real smoke/build on 2026-10-15: four calls, 2,473 tokens,
USD 0.00004946 calculated spend; the immediate resume made zero new calls. Sixty real-vector
retrieval cases passed. See the [acceptance checkpoint](../validation/phase-8-acceptance.md) for
metrics and the remaining final-head gates. Ordinary unit/database tests use synthetic free vectors.

Runtime query encoding defaults to `VIP_KNOWLEDGE_QUERY_MODE=cache_only`: absent/corrupt cached vectors
degrade to lexical retrieval. `disabled` avoids vector lookup. Explicit `paid` mode additionally
requires the dedicated spend confirmation and shares the persistent corpus ledger and fresh price
verification; test applications deny paid queries regardless of inherited flags. SQLite work runs
outside the event loop. Query encoding has a deadline and fixed sanitized failure categories.

Document versions stage without moving live pointers. `activate_corpus` checks every document has
nonempty fully embedded chunks and atomically publishes pointers plus the index. A real database
test verifies a partial new version leaves the previous document/index usable. See the
[ingestion runbook](../runbooks/knowledge-ingestion.md) and [refresh review](../runbooks/knowledge-refresh.md).

Migration 0012 allows immutable applicability corrections with unchanged text; the text checksum
still reuses embeddings. Reconstruction v3 derives a stable timestamp from reviewed provenance,
so output paths do not change an index snapshot. A real EWG metadata refresh and expanded supplier
corpus passed all sixty actual-vector queries; cumulative spend is USD 0.00005402, five calls and
2,701 tokens for twelve selections/twenty-three chunks. Raw text and vectors remain ignored.

Hybrid fuel/boost requests first read the MCP summary and, for fuel, the historical configuration
baseline. After progressive disclosure they read one detected pull boundary and at most sixteen
co-recorded observations in its first 200 ms: actual fuel pressure, RPM, throttle and boost retain
canonical units and timestamps. This is an illustrative operating sample alongside the broader
session summary, never a universal target or a complete pull. Unavailable commanded pressure/load
and exact calibration cannot be inferred from these observations. The deterministic provider keeps
these measurements in its final factual answer; the documentary renderer separately explains
source applicability and missing exact-map targets. A Stage 2 configuration question alone does
not request a before/after modification comparison.
