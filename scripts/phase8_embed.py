"""Explicit paid corpus/query embedding command; never invoked by generic verification."""

import argparse
import asyncio
import json
import os
from decimal import Decimal
from pathlib import Path

from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.knowledge.domain import (
    DocumentChunk,
    DocumentVersion,
    KnowledgeIndexVersion,
    KnowledgeSource,
    SourceConflict,
    digest,
)
from vehicle_platform.knowledge.embeddings import (
    BudgetExceeded,
    EmbeddingLedger,
    EmbeddingSettings,
    PaidEmbedder,
    PriceVerification,
    embedding_namespace,
)
from vehicle_platform.knowledge.repository import KnowledgeRepository
from vehicle_platform.observability.telemetry import Telemetry


async def execute(args: argparse.Namespace) -> None:
    from check_knowledge_security import verify

    settings = EmbeddingSettings(_env_file=args.env_file)
    settings.validate_execution()
    if os.environ.get("VIP_8_CONFIRM_EMBEDDING_SPEND") != "yes":
        raise ValueError(
            "Set VIP_8_CONFIRM_EMBEDDING_SPEND=yes for this dedicated paid command"
        )
    price = PriceVerification.model_validate_json(Path(args.price).read_text())
    price.verify()
    corpus_path = Path(args.corpus)
    corpus = json.loads(corpus_path.read_text())
    key = settings.agent_api_key.get_secret_value() if settings.agent_api_key else ""
    if key and key in json.dumps(corpus):
        raise ValueError("Private key detected in corpus; embedding aborted")
    manifest = json.loads(Path("docs/knowledge/n55-source-manifest.json").read_text())
    verify(Path.cwd(), manifest, key)
    index = KnowledgeIndexVersion.model_validate(corpus["index"])
    if index.corpus_checksum != digest(
        json.dumps(
            {
                "documents": corpus["documents"],
                "conflicts": corpus.get("conflicts", []),
            },
            sort_keys=True,
        )
    ):
        raise ValueError("Corpus content does not match its approved index checksum")
    documents = [
        DocumentVersion.model_validate(d["document"]) for d in corpus["documents"]
    ]
    chunk_sets = [
        [DocumentChunk.model_validate(c) for c in d["chunks"]]
        for d in corpus["documents"]
    ]
    sources = [KnowledgeSource.model_validate(d["source"]) for d in corpus["documents"]]
    if (
        not documents
        or len({doc.id for doc in documents}) != len(documents)
        or any(not pieces for pieces in chunk_sets)
    ):
        raise ValueError("Paid preflight requires unique nonempty document selections")
    chunk_ids = []
    for source, doc, pieces in zip(sources, documents, chunk_sets, strict=True):
        if (
            doc.source_id != source.id
            or doc.source_version != source.version
            or source.status != "VERIFIED"
            or doc.status not in {"EXTRACTED", "INDEXED"}
            or any(chunk.version_id != doc.id for chunk in pieces)
        ):
            raise ValueError(
                "Paid preflight requires approved consistent source provenance"
            )
        chunk_ids.extend(chunk.id for chunk in pieces)
    if len(set(chunk_ids)) != len(chunk_ids):
        raise ValueError("Paid preflight requires unique chunks")
    ledger = EmbeddingLedger(Path(args.ledger), settings.phase8_max_spend, price)
    entries = [
        (index.cache_key(doc.checksum, chunk.checksum), chunk.text)
        for doc, pieces in zip(documents, chunk_sets, strict=True)
        for chunk in pieces
    ]
    if args.queries:
        from vehicle_platform.knowledge.embeddings import query_key

        queries = json.loads(Path(args.queries).read_text())
        if (
            not isinstance(queries, list)
            or len(queries) > 10000
            or any(
                not isinstance(query, str)
                or not 3 <= len(query.strip()) <= 1000
                or (key and key in query)
                for query in queries
            )
        ):
            raise ValueError("Invalid or secret-contaminated query embedding input")
        entries += [(query_key(query, index), query) for query in queries]
    entries = list(dict(entries).items())
    missing = [(key, content) for key, content in entries if ledger.cached(key) is None]
    tokens = sum(len(content.encode()) for _, content in missing)
    projected = (
        Decimal(tokens + len(b"N55 embedding preflight"))
        * price.usd_per_million
        / 1_000_000
    )
    process = await asyncio.create_subprocess_exec(
        "git",
        "rev-parse",
        "HEAD",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    output, _ = await process.communicate()
    if process.returncode != 0:
        raise ValueError("Repository SHA unavailable")
    sha = output.decode().strip()
    print(
        json.dumps(
            {
                "model": index.model,
                "dimensions": index.dimensions,
                "documents": len(documents),
                "chunks": sum(map(len, chunk_sets)),
                "estimated_tokens_upper_bound": tokens,
                "projected_incremental_cost_usd": str(projected),
                "configured_ceiling_usd": str(settings.phase8_max_spend),
                "repository_sha": sha,
                "prior_ledger": ledger.report(),
                "price_verification": price.model_dump(mode="json"),
            },
            indent=2,
        ),
        flush=True,
    )
    if (
        Decimal(str(ledger.report()["estimated_spend_usd"])) + projected
        > settings.phase8_max_spend
    ):
        raise BudgetExceeded("projected_corpus_embedding_spend_exceeds_ceiling")
    config = Settings()
    database = Database(config)
    telemetry = Telemetry(
        config, database, service_name="vehicle-platform-knowledge-ingestion"
    )
    paid = PaidEmbedder(
        settings,
        ledger,
        confirmed=True,
        reuse_namespace=embedding_namespace(index),
        telemetry=telemetry,
    )
    repo = KnowledgeRepository(database, telemetry)
    try:
        # One tiny smoke, cached across crashes/resumes; all token charges share the same ledger.
        smoke = "N55 embedding preflight"
        smoke_key = index.cache_key(digest("smoke"), digest(smoke))
        await paid.embed([(smoke_key, smoke)])
        print(json.dumps({"smoke": "PASS", "usage": ledger.report()}), flush=True)
        await repo.index(index)
        for source, doc, pieces in zip(sources, documents, chunk_sets, strict=True):
            await repo.ingest(source, doc, pieces)
        for item in corpus.get("conflicts", []):
            await repo.record_conflict(SourceConflict.model_validate(item))
        for offset in range(0, len(entries), 32):
            await paid.embed(entries[offset : offset + 32])
        for doc, pieces in zip(documents, chunk_sets, strict=True):
            for chunk in pieces:
                identity = index.cache_key(doc.checksum, chunk.checksum)
                vector = ledger.cached(identity)
                if vector is None:
                    raise ValueError("Incomplete corpus; index will not activate")
                await repo.store_vector(chunk.id, index.id, vector, identity)
        await repo.activate_corpus(index, [document.id for document in documents])
        receipt = {
            "index": index.model_dump(mode="json"),
            "corpus_checksum": digest(corpus_path.read_bytes()),
            "repository_sha": sha,
            "documents": len(documents),
            "chunks": sum(map(len, chunk_sets)),
            "usage": ledger.report(),
            "successful_endpoint_latency_seconds": paid.successful_endpoint_latencies,
            "successful_endpoint_calls_this_run": len(
                paid.successful_endpoint_latencies
            ),
        }
        Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
        Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2), flush=True)
    finally:
        metrics_path = Path(args.receipt).with_suffix(".prom")
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_bytes(telemetry.render_metrics())
        await paid.close()
        await database.close()
        telemetry.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--price", default="docs/knowledge/embedding-price.json")
    parser.add_argument("--corpus", default=".knowledge/approved-corpus.json")
    parser.add_argument("--queries")
    parser.add_argument("--ledger", default=".knowledge/embedding-ledger.sqlite")
    parser.add_argument(
        "--receipt", default=".validation/knowledge/real-embedding.json"
    )
    args = parser.parse_args()
    try:
        asyncio.run(execute(args))
    except Exception:  # noqa: BLE001 - sanitized CLI boundary; never print provider/config errors
        # Provider/parser/config exceptions must not expose key values, input text or connection URLs.
        raise SystemExit(
            "Embedding stopped; inspect sanitized preflight/ledger. No secret was emitted."
        ) from None


if __name__ == "__main__":
    main()
