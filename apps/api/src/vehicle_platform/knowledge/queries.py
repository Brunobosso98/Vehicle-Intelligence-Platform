"""Read cached query embeddings; paid misses require explicit operator opt-in and shared budget."""

import asyncio
import json
import sqlite3
from pathlib import Path

from vehicle_platform.knowledge.domain import KnowledgeIndexVersion, validate_vector
from vehicle_platform.knowledge.embeddings import (
    BudgetExceeded,
    EmbeddingLedger,
    EmbeddingSettings,
    PaidEmbedder,
    PriceVerification,
    embedding_namespace,
    query_key,
)
from vehicle_platform.knowledge.repository import KnowledgeRepository
from vehicle_platform.observability.telemetry import Telemetry


def cached_query(path: Path, query: str, index: KnowledgeIndexVersion) -> list[float] | None:
    if not path.is_file():
        return None
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=1) as db:
        row = db.execute(
            "SELECT vector FROM cache WHERE identity=?", (query_key(query, index),)
        ).fetchone()
        return validate_vector([float(v) for v in json.loads(row[0])]) if row else None


class QueryEmbeddingEncoder:
    def __init__(
        self,
        repository: KnowledgeRepository,
        settings: EmbeddingSettings,
        telemetry: Telemetry,
        *,
        confirmed: bool = False,
        allow_paid: bool = False,
    ) -> None:
        self.repository, self.settings = repository, settings
        self.telemetry = telemetry
        self.confirmed, self.allow_paid = confirmed, allow_paid
        self._paid: PaidEmbedder | None = None
        self._lock = asyncio.Lock()
        meter = telemetry.metrics.get_meter("vehicle_platform.knowledge")
        self.cache_hits = telemetry.embedding_cache_hits
        self.unavailable = meter.create_counter("embedding_query_unavailable_total")

    async def __call__(self, query: str, index_id: str) -> list[float] | None:
        if self.settings.knowledge_query_mode == "disabled":
            return None
        key = self.settings.agent_api_key
        if key and key.get_secret_value() and key.get_secret_value() in query:
            self.unavailable.add(1, {"category": "secret_contaminated_query"})
            return None
        index = await self.repository.active_index()
        if index is None or index.id != index_id:
            return None
        if (index.model, index.dimensions) != (
            self.settings.embedding_model,
            self.settings.embedding_dimensions,
        ):
            self.unavailable.add(1, {"category": "model_or_dimensions_mismatch"})
            return None
        try:
            async with asyncio.timeout(6):
                cached = await asyncio.to_thread(
                    cached_query, self.settings.knowledge_ledger_path, query, index
                )
                if cached is not None:
                    self.cache_hits.add(1)
                    return cached
                if self.settings.knowledge_query_mode != "paid":
                    self.unavailable.add(1, {"category": "query_not_cached"})
                    return None
                # Test applications never purchase embeddings, regardless of inherited env flags.
                if not self.confirmed or not self.allow_paid:
                    self.unavailable.add(1, {"category": "paid_query_not_authorized"})
                    return None
                async with self._lock:
                    # A concurrent request may have populated this exact query while we waited.
                    cached = await asyncio.to_thread(
                        cached_query, self.settings.knowledge_ledger_path, query, index
                    )
                    if cached is not None:
                        self.cache_hits.add(1)
                        return cached
                    if self._paid and self._paid.reuse_namespace != embedding_namespace(index):
                        await self._paid.close()
                        self._paid = None
                    if self._paid is None:
                        self.settings.validate_execution()
                        price_data = await asyncio.to_thread(
                            self.settings.knowledge_price_file.read_text
                        )
                        price = PriceVerification.model_validate_json(price_data)
                        ledger = await asyncio.to_thread(
                            EmbeddingLedger,
                            self.settings.knowledge_ledger_path,
                            self.settings.phase8_max_spend,
                            price,
                        )
                        self._paid = PaidEmbedder(
                            self.settings,
                            ledger,
                            confirmed=True,
                            reuse_namespace=embedding_namespace(index),
                            telemetry=self.telemetry,
                        )
                    identity = query_key(query, index)
                    vectors = await self._paid.embed([(identity, query)])
                    return vectors[identity]
        except BudgetExceeded:
            self.unavailable.add(1, {"category": "embedding_budget_exhausted"})
        except TimeoutError:
            self.unavailable.add(1, {"category": "query_embedding_timeout"})
        except (OSError, ValueError, sqlite3.Error):
            # Neither provider exception strings nor query/key/path values enter diagnostics.
            self.unavailable.add(1, {"category": "query_embedding_unavailable"})
        return None

    async def close(self) -> None:
        if self._paid is not None:
            await self._paid.close()
