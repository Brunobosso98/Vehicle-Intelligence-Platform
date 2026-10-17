"""Measure actual disposable SQL retrieval with explicitly synthetic, free fixture vectors."""

import asyncio
import json
import os
import resource
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from evaluate_knowledge import fixture_vector, seed_knowledge
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.knowledge.domain import RetrievalIntent, VehicleScope
from vehicle_platform.knowledge.repository import KnowledgeRepository
from vehicle_platform.knowledge.retrieval import KnowledgeService
from vehicle_platform.observability.telemetry import Telemetry


def percentiles(values):
    ordered = sorted(values)
    return {
        f"p{p}": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p / 100))]
        for p in (50, 95, 99)
    }


async def main():
    url = os.environ["TEST_DATABASE_URL"]
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError("Benchmark requires disposable database")
    settings = Settings(database_url=url, environment="test")
    database, telemetry = Database(settings), Telemetry(settings)
    repo = KnowledgeRepository(database)
    try:
        started = perf_counter()
        index, _ = await seed_knowledge(repo)
        ingestion = perf_counter() - started
        catalog = await repo.catalog()
        scope = VehicleScope(
            vehicle_id=uuid4(),
            engine="N55",
            calibration="tuned",
            stage="Stage 2",
            as_of=datetime.now(UTC),
            temporal_valid=True,
        )

        async def encode(query, index_id):
            assert index_id == index.id
            return fixture_vector(query)

        service = KnowledgeService(repo, telemetry, encode)
        times = {"lexical": [], "vector": [], "hybrid": [], "fusion_rerank": []}
        sizes = []
        for n in range(100):
            # Distinct intents exclude candidate-cache reuse from cold-query measurements.
            query = f"N55 fuel HPFP rail pressure operating context sample {n}"
            started = perf_counter()
            await repo.candidates(scope, query, index.id, None, "fuel")
            times["lexical"].append(perf_counter() - started)
            vector = fixture_vector(query)
            started = perf_counter()
            await repo.candidates(
                scope, "unmatched_identifier", index.id, vector, "fuel"
            )
            times["vector"].append(perf_counter() - started)
            started = perf_counter()
            result = await service.search(
                RetrievalIntent(query=query, topic="fuel"), scope
            )
            times["hybrid"].append(perf_counter() - started)
            times["fusion_rerank"].append(result.timings["fusion_rerank"])
            sizes.append(len(result.model_dump_json().encode()))
        receipt = {
            "status": "MEASURED_SYNTHETIC_ONLY",
            "database": "disposable-postgresql-pgvector",
            "embedding_provider": "synthetic-free",
            "paid_calls": 0,
            "samples": 100,
            "sources": len(catalog["sources"]),
            "documents": len(catalog["documents"]),
            "chunks": catalog["chunks"],
            "ingestion_seconds_excluding_download": ingestion,
            "chunk_throughput_per_second": catalog["chunks"] / ingestion,
            "embedding_api_latency_seconds": None,
            "embedding_latency_gap": "real endpoint latency belongs to explicitly paid corpus execution",
            "latency_seconds": {
                name: percentiles(values) for name, values in times.items()
            },
            "result_bytes": {"min": min(sizes), "max": max(sizes)},
            "max_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            * 1024,
            "index": index.model_dump(mode="json"),
        }
        target = Path(".validation/knowledge/benchmark.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))
    finally:
        await database.close()
        telemetry.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
