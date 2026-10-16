"""Evaluate a reviewed local corpus against 60 authored relevance/applicability oracles.

Default execution reads an existing real index and cached query vectors. It never calls
OpenAI. --synthetic-fixture-vectors installs clearly labelled free projections in a
DISPOSABLE database for CI only; those metrics do not prove real embedding quality.
"""

import argparse
import asyncio
import json
import os
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from evaluate_knowledge import fixture_vector
from sqlalchemy import text
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.knowledge.domain import (
    DocumentChunk,
    DocumentVersion,
    KnowledgeIndexVersion,
    KnowledgeSource,
    RetrievalIntent,
    SourceConflict,
    Trust,
    VehicleScope,
    digest,
    match,
)
from vehicle_platform.knowledge.embeddings import EmbeddingSettings, query_key
from vehicle_platform.knowledge.grounding import report, validate_reference
from vehicle_platform.knowledge.queries import QueryEmbeddingEncoder
from vehicle_platform.knowledge.repository import KnowledgeRepository
from vehicle_platform.knowledge.retrieval import KnowledgeService
from vehicle_platform.knowledge.tools import source_tuner_for
from vehicle_platform.observability.telemetry import Telemetry


async def evaluate(args: argparse.Namespace) -> None:
    corpus_file, golden_file = Path(args.corpus), Path(args.golden)
    corpus = json.loads(corpus_file.read_text())
    cases = json.loads(golden_file.read_text())["cases"]
    if len(cases) < 60 or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("At least 60 unique golden cases required")
    if len({c["query"] for c in cases}) != len(cases):
        raise ValueError("Golden questions must be distinct")
    url = (
        os.environ.get("TEST_DATABASE_URL")
        or Settings().database_url.get_secret_value()
    )
    if args.synthetic_fixture_vectors and not url.rsplit("/", 1)[-1].startswith(
        "vehicle_test"
    ):
        raise ValueError(
            "Synthetic vector installation requires a disposable test database"
        )
    settings = Settings(database_url=url, environment="test")
    db, telemetry = Database(settings), Telemetry(settings)
    repository = KnowledgeRepository(db)
    index = KnowledgeIndexVersion.model_validate(corpus["index"])
    if args.synthetic_fixture_vectors:
        index = index.model_copy(update={"id": "synthetic-free-" + index.id})
    documents = {
        d["key"]: DocumentVersion.model_validate(d["document"])
        for d in corpus["documents"]
    }
    sources = {
        d["key"]: KnowledgeSource.model_validate(d["source"])
        for d in corpus["documents"]
    }
    reviewed_chunks = {
        UUID(c["id"]): DocumentChunk.model_validate(c)
        for d in corpus["documents"]
        for c in d["chunks"]
    }
    known_versions = {d.id: key for key, d in documents.items()}
    query_cache: dict[str, list[float]] = {}
    query_encoder: QueryEmbeddingEncoder | None = None
    try:
        if args.synthetic_fixture_vectors:
            await repository.index(index)
            for entry in corpus["documents"]:
                document = DocumentVersion.model_validate(entry["document"])
                source = KnowledgeSource.model_validate(entry["source"])
                pieces = [DocumentChunk.model_validate(c) for c in entry["chunks"]]
                await repository.ingest(source, document, pieces, activate=True)
                for chunk in pieces:
                    await repository.store_vector(
                        chunk.id,
                        index.id,
                        fixture_vector(chunk.text),
                        index.cache_key(document.checksum, chunk.checksum),
                    )
            for item in corpus.get("conflicts", []):
                await repository.record_conflict(SourceConflict.model_validate(item))
            await repository.index(index, activate=True)
        else:
            embedding_receipt = json.loads(Path(args.embedding_receipt).read_text())
            if (
                embedding_receipt["index"] != index.model_dump(mode="json")
                or embedding_receipt["corpus_checksum"]
                != digest(corpus_file.read_bytes())
                or embedding_receipt["usage"]["tokens"] <= 0
                or Decimal(embedding_receipt["usage"]["estimated_spend_usd"])
                > Decimal("2.00")
            ):
                raise ValueError(
                    "Real embedding receipt does not prove this corpus/index"
                )
            # Read-only cache: evaluation cannot create a ledger or buy missing queries.
            with sqlite3.connect(
                Path(args.ledger).resolve().as_uri() + "?mode=ro", uri=True
            ) as cache:
                for case in cases:
                    row = cache.execute(
                        "SELECT vector FROM cache WHERE identity=?",
                        (query_key(case["query"], index),),
                    ).fetchone()
                    if row is None:
                        raise ValueError(
                            "Missing cached query embedding; use explicit paid preflight"
                        )
                    query_cache[case["query"]] = json.loads(row[0])
            query_encoder = QueryEmbeddingEncoder(
                repository,
                EmbeddingSettings(
                    agent_api_key=None,
                    knowledge_query_mode="cache_only",
                    knowledge_ledger_path=Path(args.ledger),
                ),
                telemetry,
            )
        active = await repository.active_index()
        if active != index:
            raise ValueError("Active index does not match the reviewed corpus")

        async def encode(query: str, index_id: str) -> list[float]:
            if index_id != index.id:
                raise ValueError("Unexpected index version")
            if args.synthetic_fixture_vectors:
                return fixture_vector(query)
            assert query_encoder is not None
            vector = await query_encoder(query, index_id)
            if vector is None or vector != query_cache[query]:
                raise ValueError(
                    "Runtime query encoder did not return the reviewed cached vector"
                )
            return vector

        service = KnowledgeService(repository, telemetry, encode)
        base_scope = {
            "vehicle_id": UUID("00000000-0000-4000-8000-000000000008"),
            "as_of": datetime.now(UTC),
            "make": "BMW",
            "model": "335i",
            "platform": "F30",
            "engine": "N55",
            "model_year": 2015,
            "calibration": "tuned",
            "stage": "Stage 2",
            "temporal_valid": True,
        }
        rows = []
        violations = {
            "fabricated_source": 0,
            "fabricated_citation": 0,
            "wrong_engine_normative_claim": 0,
            "unverified_normative_claim": 0,
            "forbidden_normative_claim": 0,
        }
        for case in cases:
            scope = VehicleScope.model_validate(base_scope | case["scope"])
            result = await service.search(
                RetrievalIntent(
                    query=case["query"],
                    topic=case["topic"],
                    need=case["need"],
                    source_tuner=source_tuner_for(case["query"]),
                ),
                scope,
            )
            expected = set(case["expected_documents"])
            if expected - documents.keys():
                raise ValueError("Golden references an unknown source selection")
            retrieved = [
                known_versions.get(e.document.id, "UNKNOWN") for e in result.evidence
            ]
            ranks = [i + 1 for i, key in enumerate(retrieved) if key in expected]
            rr = 1 / ranks[0] if ranks else 0.0
            recalls = (
                {
                    str(k): len(set(retrieved[:k]) & expected) / len(expected)
                    for k in (1, 3, 5)
                }
                if expected
                else {}
            )
            # Precision@5 retains its fixed denominator when fewer than five chunks return.
            precision = sum(key in expected for key in retrieved) / 5
            source_checks, citation_checks, applicable = [], [], []
            for evidence in result.evidence:
                selection = known_versions.get(evidence.document.id)
                known = (
                    selection is not None
                    and evidence.document == documents[selection]
                    and evidence.source == sources[selection]
                )
                violations["fabricated_source"] += int(not known)
                source_checks.append(
                    evidence.source.trust
                    in {Trust.TIER_1_AUTHORITATIVE, Trust.TIER_2_STRONG_TECHNICAL}
                    and evidence.source.source_type
                    not in case["forbidden_source_types"]
                )
                applicability = match(evidence.document.applicability, scope)
                applicable.append(
                    applicability.status != "INCOMPATIBLE"
                    and (evidence.document.applicability.engine or "").casefold()
                    not in {engine.casefold() for engine in case["forbidden_engines"]}
                )
                violations["wrong_engine_normative_claim"] += int(
                    evidence.eligible and applicability.status == "INCOMPATIBLE"
                )
                violations["unverified_normative_claim"] += int(
                    evidence.eligible and not source_checks[-1]
                )
                async with db.session() as session:
                    persisted = await session.scalar(
                        text("SELECT snapshot FROM knowledge_chunks WHERE id=:id"),
                        {"id": evidence.chunk_id},
                    )
                reviewed = reviewed_chunks.get(evidence.chunk_id)
                valid = (
                    persisted is not None
                    and reviewed is not None
                    and DocumentChunk.model_validate(persisted) == reviewed
                    and persisted["version_id"] == str(evidence.document.id)
                    and persisted["checksum"] == evidence.chunk_checksum
                    and evidence.snippet in persisted["text"]
                    and evidence.page == reviewed.page
                    and evidence.section == reviewed.section
                    and evidence.heading_path == reviewed.heading_path
                    and evidence.numeric_facts == reviewed.numeric_facts
                    and evidence.quality == reviewed.quality
                )
                citation_checks.append(valid)
                violations["fabricated_citation"] += int(not valid)
            grounded = report(result, hybrid=False)
            for claim in grounded.claims:
                validate_reference(claim, result)
                violations["forbidden_normative_claim"] += int(
                    case.get("require_no_normative_claim", False) and claim.normative
                )
            required_gaps = set(case["expected_gaps"])
            gaps_correct = required_gaps <= set(result.knowledge_gaps)
            if not required_gaps:
                gaps_correct = not result.knowledge_gaps
            rows.append(
                {
                    "id": case["id"],
                    "query": case["query"],
                    "expected": sorted(expected),
                    "retrieved": retrieved,
                    "recall": recalls,
                    "reciprocal_rank": rr,
                    "precision_at_5": precision,
                    "applicable": all(applicable),
                    "trust_correct": all(source_checks),
                    "citation_correct": all(citation_checks),
                    "gap_correct": gaps_correct,
                    "gaps": result.knowledge_gaps,
                    "evidence_count": len(result.evidence),
                }
            )
        positive = [r for r in rows if r["expected"]]
        average = lambda values: sum(values) / max(1, len(values))
        metrics = {
            **{
                f"recall_at_{k}": average([r["recall"][str(k)] for r in positive])
                for k in (1, 3, 5)
            },
            "mrr": average([r["reciprocal_rank"] for r in positive]),
            "precision_at_5": average([r["precision_at_5"] for r in positive]),
            "applicable_source_rate": average([r["applicable"] for r in rows]),
            "wrong_platform_rate": average([not r["applicable"] for r in rows]),
            "trust_tier_correctness": average([r["trust_correct"] for r in rows]),
            "citation_correctness": average([r["citation_correct"] for r in rows]),
            "knowledge_gap_accuracy": average([r["gap_correct"] for r in rows]),
        }
        passed = (
            metrics["recall_at_5"] >= 0.95
            and metrics["mrr"] >= 0.85
            and metrics["knowledge_gap_accuracy"] >= 0.95
            and all(v == 0 for v in violations.values())
            and all(
                metrics[k] == 1
                for k in [
                    "applicable_source_rate",
                    "trust_tier_correctness",
                    "citation_correctness",
                ]
            )
        )
        receipt = {
            "suite": "phase8-retrieval-golden",
            "status": "PASS" if passed else "FAIL",
            "embedding_provider": "synthetic-free"
            if args.synthetic_fixture_vectors
            else "cached-real-openai",
            "paid_calls": 0,
            "runtime_query_encoder": "synthetic-fixture"
            if args.synthetic_fixture_vectors
            else "QueryEmbeddingEncoder/cache_only",
            "cases": len(cases),
            "positive_cases": len(positive),
            "index": index.model_dump(mode="json"),
            "corpus_checksum": digest(corpus_file.read_bytes()),
            "golden_checksum": digest(golden_file.read_bytes()),
            "metrics": metrics,
            "violations": violations,
            "results": rows,
        }
        target = Path(args.receipt)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2) + "\n")
        print(
            json.dumps({k: v for k, v in receipt.items() if k != "results"}, indent=2)
        )
        if not passed:
            raise SystemExit("Retrieval quality gates failed; inspect per-case receipt")
    finally:
        if query_encoder is not None:
            await query_encoder.close()
        await db.close()
        telemetry.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=".knowledge/approved-corpus.json")
    parser.add_argument("--golden", default="docs/knowledge/n55-retrieval-golden.json")
    parser.add_argument("--ledger", default=".knowledge/embedding-ledger.sqlite")
    parser.add_argument(
        "--embedding-receipt", default=".validation/knowledge/real-embedding.json"
    )
    parser.add_argument(
        "--receipt", default=".validation/knowledge/retrieval-golden.json"
    )
    parser.add_argument("--synthetic-fixture-vectors", action="store_true")
    parser.add_argument("--export-queries", type=Path)
    args = parser.parse_args()
    if args.export_queries:
        cases = json.loads(Path(args.golden).read_text())["cases"]
        args.export_queries.write_text(
            json.dumps([c["query"] for c in cases], indent=2) + "\n"
        )
    else:
        asyncio.run(evaluate(args))


if __name__ == "__main__":
    main()
