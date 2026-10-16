# Controlled knowledge ingestion

Phase 8 is under implementation; see the acceptance checkpoint for unexecuted gates.
Source acquisition is an operator workflow. Agents and public APIs cannot download URLs or ingest
files. MCP remains authoritative for observed vehicle facts.

## Reconstruct the reviewed corpus

Run commands from the repository root, using the existing API virtual environment.

```bash
apps/api/.venv/bin/python scripts/prepare_knowledge_corpus.py
```

The manifest is `docs/knowledge/n55-source-manifest.json`. The reconstruction script downloads
only its configured reviewed sources when a local raw file is absent, verifies MIME and the exact
recorded checksum, then selects reviewed section/paragraph locators. A changed page stops ingestion
and requires the refresh review. HTML may change dynamically; never update a checksum merely to
make the command pass. Review the extracted paragraphs, applicability, quality and conflicts first.

Raw documents and selected text stay in ignored `.knowledge/`, outside public Git. Preserve publisher
copyright. No full-source export API exists. Missing official manuals and exact tune targets remain
knowledge gaps. Do not substitute a third-party manual mirror without reviewing its rights.

## Explicit embedding preflight and execution

Set `DATABASE_URL` through the existing local secret/environment mechanism. Migrate the intended
knowledge database to 0011 using the pgvector-capable Timescale image. Keep production data intact.
Use the existing `VIP_AGENT_API_KEY` secret; never paste it into shell history, command arguments,
logs, reports or screenshots. The dedicated CLI accepts a local secret-file path via `--env-file`.

Export the golden questions without buying embeddings:

```bash
apps/api/.venv/bin/python scripts/evaluate_knowledge_retrieval.py \
  --export-queries .knowledge/golden-queries.json
```

After checking the current official price and its verification date in
`docs/knowledge/embedding-price.json`, execute the explicitly authorized paid command:

```bash
VIP_8_CONFIRM_EMBEDDING_SPEND=yes make phase8-embed-corpus \
  PHASE8_EMBED_ARGS='--queries .knowledge/golden-queries.json'
```

The CLI validates the key, model, dimensions and fresh official price before calls. It prints model,
dimensions, document/chunk counts, conservative token estimate, projected incremental spend,
absolute ceiling and repository SHA. The one tiny smoke and all corpus/query requests share the same
SQLite ledger and USD 2 ceiling. No Luna generation suite is invoked. SDK retries are disabled.

Do not delete, replace or move the ledger to evade accumulated spend. Back up its completed vectors
and pending reservations. An uncertain failed request remains conservatively reserved; restarting
does not erase it. Completed chunks are reused across restarts and corpus publications; unchanged
text may reuse an embedding across document versions within the same embedding pipeline.
Changing model/dimensions/chunker/normalization requires an explicit new index. A new corpus or
ranking version alone does not justify repurchasing unchanged vectors.

New document versions are staged without changing live pointers. Activation checks every staged
chunk has its index vector, then publishes all document pointers and the active index atomically.
A missing embedding or interrupted batch leaves the previous published corpus usable.

## Evaluate without further API spending

```bash
make phase8-retrieval-eval
```

This requires the already embedded reviewed index and all golden query vectors in the local cache.
It reads cache data without invoking OpenAI. A missing vector fails visibly. The receipt records
index, corpus/dataset checksums, per-case results, Recall@1/3/5, MRR, precision, applicability, trust,
citations and knowledge gaps. Synthetic projection metrics cannot substitute for this real gate.
Generic `make verify` and ordinary CI must never invoke the paid embedding command.
