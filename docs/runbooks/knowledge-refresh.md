# Knowledge source refresh

Refresh is an explicit operator review, independent from runtime agent questions. Never expose URL
fetching, source verification, file paths or source-status changes as model tools.

1. Start from the configured source URL in `docs/knowledge/n55-source-manifest.json`. Acquire a
   candidate through `knowledge.security.download`, which checks public HTTP(S), pinned DNS/TLS,
   redirects, MIME and size/time limits. Store it separately under ignored `.knowledge/`.
2. Compare its raw SHA-256 with the approved manifest. Unchanged content needs no new extraction or
   embedding. A changed checksum is a candidate, not approval. Preserve the old raw file and corpus.
3. Review publisher identity, publication/version information, copyright, engine/platform/fuel/tune
   applicability and exact selected section/paragraph locators. Check document instructions, tables,
   diagrams and source conflicts. A newer date alone does not resolve an applicability conflict.
4. Increment the immutable source verification version when its metadata/status changes. Create a
   new document version for changed text or applicability. Never overwrite an existing source,
   document or chunk snapshot; the repository rejects mutations of an existing identity.
5. Update the manifest/reconstruction selection and research report together. Record why the new
   text is accepted, rejected or quarantined. Preserve absent/unknown metadata rather than guessing.
6. Prepare a new explicit index with its corpus checksum and pipeline versions. Use the ingestion
   runbook's dedicated paid command, the SAME ledger, and fresh official price verification. Reuse
   unchanged vectors; reserve spend before missing batches. Do not reset the ceiling at refresh.
7. Publish only after all index vectors exist, using atomic corpus activation. Run golden retrieval,
   historical-session applicability, conflicts, citations and hybrid acceptance against that index.
   Keep old retrieval snapshots and document versions for audit. Cached retrieval candidates are
   invalidated by document publication, source-version revocation or conflict status changes.

## Controlled refresh commands

The operator CLI supports the existing reviewed source keys. It uses the bounded downloader;
ordinary runtime agents and generic verification do not invoke acquisition.

```bash
apps/api/.venv/bin/python scripts/refresh_knowledge_source.py stage bosch-hdp
```

For an applicability-only correction, add `--existing-local` to stage the checksum-verified
approved raw file without downloading it again. The original retrieval date is preserved.

This writes an immutable checksum-addressed `candidate.json` under `.knowledge/refresh/`.
Changed bytes are stored beside it as `source.bin`; unchanged content creates no duplicate raw file.
Replaying the command reuses the matching artifact. A changed base manifest requires a fresh review.
Parser failures and document instructions produce a quarantined candidate that cannot be accepted.
The configured private key is checked before any candidate or review bytes are written.

Write a separate local review file identifying the exact old/new checksums and the reviewed
paragraph locators for **every** document selection belonging to that source. For example:

```json
{
  "base_source_checksum": "<approved raw SHA-256>",
  "candidate_checksum": "<candidate raw SHA-256>",
  "reviewer": "<reviewer identity>",
  "reason": "<publisher, applicability, rights and selected-text review rationale>",
  "decision": "ACCEPTED",
  "reviewed_extraction_limitations": [],
  "selection_overrides": {
    "hdp-operating-principle": [[1, null], [8, null]]
  },
  "source_conflicts": []
}
```

These locator numbers are illustrative: inspect the exact candidate's extracted sections before
using them. `null` selects the complete section; a paragraph index or `before:MARKER` selects a
reviewed part. Supply the exact extraction limitations from the candidate, including an explicit
empty list when none were reported. `source_conflicts` is an explicit review result: use an empty
list when none remain, or records with `selection`, `topic` and `explanation` for unresolved conflicts.
The known conflicting MHD raw checksum retains its conflict even after metadata-only review.
A changed MHD page requires explicit conflict review before reconstruction.

Optional `metadata` can correct title/date/version/applicability/rights notes. It cannot silently
change publisher, canonical identity, source type or trust. An unchanged raw file can receive a
new source/document version for an explicit metadata correction; an otherwise unchanged refresh
does not generate another version. Metadata corrections retain unknown vehicle hardware/tune facts.
Use `REJECTED` or `QUARANTINED` to record a decision without generating a reconstruction manifest.

```bash
apps/api/.venv/bin/python scripts/refresh_knowledge_source.py review \
  .knowledge/refresh/bosch-hdp/<candidate-checksum>/candidate.json \
  .knowledge/refresh/bosch-hdp/review-input.json
apps/api/.venv/bin/python scripts/prepare_knowledge_corpus.py \
  --manifest .knowledge/refresh/bosch-hdp/<candidate-checksum>/reviewed-manifest.json \
  --output .knowledge/refreshed-corpus.json
```

Review decisions and complete manifests use atomic exclusive installation. Retrying an interrupted
manifest write keeps the first decision; conflicting retries are rejected. The original source
manifest/raw files and the active database corpus remain untouched. Local source paths must resolve
inside `.knowledge/` and do not participate in document identity, so relocating an artifact cannot
change its documentary version. Secret scans still apply; the CLI does not change scan exceptions.

After reviewing the reconstructed corpus, use the ingestion runbook's explicitly confirmed paid
command with `PHASE8_EMBED_ARGS='--corpus .knowledge/refreshed-corpus.json --queries .knowledge/golden-queries.json'`.
Keep the same ledger. Unchanged text reuses its vectors. Only complete-vector atomic publication
moves database pointers; failures preserve the previous active corpus. Repeat real retrieval,
historical applicability, conflict and hybrid gates against the newly published version before
updating the repository's canonical research metadata. Preserve previous evidence and raw versions.

Migration `0012` permits distinct immutable document snapshots with the same content checksum.
It takes a bounded table lock (five-second lock timeout) and replaces the old content uniqueness
constraint with a lookup index. It changes no documentary bytes or vehicle records. Downgrade
to `0011` is safe only before such metadata revisions exist: PostgreSQL refuses duplicate-checksum
history rather than deleting versions. Keep `0012` and use a forward fix when that history exists.

On October 16, the reviewed bootmod3 EWG applicability correction published a complete new index
with zero provider calls and passed all sixty real-vector retrieval cases. This is checkpoint
evidence; the final committed-head repeat and broader acceptance remain separate gates.
