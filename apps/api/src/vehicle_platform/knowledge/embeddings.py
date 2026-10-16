"""Explicit paid embedding boundary with durable per-request reservations and cache."""

import asyncio
import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, nullcontext
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import uuid4

from openai import AsyncOpenAI
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from vehicle_platform.knowledge.domain import KnowledgeIndexVersion, Model, digest, validate_vector
from vehicle_platform.observability.telemetry import Telemetry


class EmbeddingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIP_", hide_input_in_errors=True, extra="ignore")
    agent_api_key: SecretStr | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    knowledge_query_mode: Literal["disabled", "cache_only", "paid"] = "cache_only"
    knowledge_ledger_path: Path = Path(".knowledge/embedding-ledger.sqlite")
    knowledge_price_file: Path = Path("docs/knowledge/embedding-price.json")
    phase8_max_spend: Decimal = Field(
        default=Decimal("2.00"), alias="VIP_8_MAX_EMBEDDING_SPEND_USD", gt=0, le=Decimal("2.00")
    )

    def validate_execution(self) -> None:
        if not self.agent_api_key or not self.agent_api_key.get_secret_value():
            raise ValueError("embedding_key_unavailable")
        if self.embedding_model != "text-embedding-3-small" or self.embedding_dimensions != 1536:
            raise ValueError("embedding_model_or_dimensions_mismatch")


class PriceVerification(Model):
    model: str = "text-embedding-3-small"
    usd_per_million: Decimal = Field(gt=0)
    verified_on: date
    official_url: str

    def verify(self) -> None:
        if (
            self.model != "text-embedding-3-small"
            or self.usd_per_million != Decimal("0.02")
            or self.official_url
            != "https://developers.openai.com/api/docs/models/text-embedding-3-small"
            or not 0 <= (date.today() - self.verified_on).days <= 7
        ):
            raise ValueError("embedding_price_requires_current_official_verification")


class BudgetExceeded(ValueError):
    pass


class EmbeddingLedger:
    """BEGIN IMMEDIATE serializes admissions across processes. Unknown charges stay reserved.

    Costs use integer pico-dollars (USD * 10^12), avoiding SQLite floating point arithmetic.
    Never reset this ledger to resume. It covers all index versions and query embeddings.
    """

    scale = Decimal(10) ** 12

    def __init__(self, path: Path, ceiling: Decimal, price: PriceVerification) -> None:
        price.verify()
        if not Decimal(0) < ceiling <= Decimal(2):
            raise ValueError("Invalid absolute embedding ceiling")
        self.path, self.ceiling, self.price = path, ceiling, price
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY, reserved INTEGER NOT NULL,
                    actual INTEGER, tokens INTEGER, status TEXT NOT NULL,
                    model TEXT NOT NULL, dimensions INTEGER NOT NULL,
                    verified_on TEXT NOT NULL, rate TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cache (
                    identity TEXT PRIMARY KEY, vector TEXT NOT NULL, request_id TEXT NOT NULL,
                    FOREIGN KEY(request_id) REFERENCES requests(id)
                );
                CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY,value INTEGER NOT NULL);
            """)
        path.chmod(0o600)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            with connection:
                yield connection
        finally:
            connection.close()

    def cost(self, tokens: int) -> int:
        return int(Decimal(tokens) * self.price.usd_per_million / Decimal(1_000_000) * self.scale)

    def cached(self, identity: str) -> list[float] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT vector FROM cache WHERE identity=?", (identity,)
            ).fetchone()
            if row:
                connection.execute("""INSERT INTO counters VALUES ('cache_hits',1)
                    ON CONFLICT(name) DO UPDATE SET value=value+1""")
                value = json.loads(row[0])
                if not isinstance(value, list):
                    raise ValueError("Invalid cached vector")
                return validate_vector([float(v) for v in value])
        return None

    def reserve(self, token_bound: int) -> str:
        self.price.verify()
        if token_bound < 1:
            raise ValueError("Invalid embedding token bound")
        identifier = str(uuid4())
        reserved = self.cost(token_bound)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            total = connection.execute(
                "SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM requests"
            ).fetchone()[0]
            if total + reserved > int(self.ceiling * self.scale):
                raise BudgetExceeded("embedding_spend_ceiling")
            connection.execute(
                "INSERT INTO requests VALUES (?,?,NULL,NULL,'pending',?,?,?,?)",
                (
                    identifier,
                    reserved,
                    "text-embedding-3-small",
                    1536,
                    self.price.verified_on.isoformat(),
                    str(self.price.usd_per_million),
                ),
            )
        return identifier

    def reuse(self, identity: str, content_identity: str) -> list[float] | None:
        """Alias unchanged text across document versions without another paid request."""
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT vector,request_id FROM cache WHERE identity=?", (content_identity,)
            ).fetchone()
            if row is None:
                return None
            vector = validate_vector([float(v) for v in json.loads(row[0])])
            connection.execute(
                "INSERT INTO cache VALUES (?,?,?) ON CONFLICT DO NOTHING",
                (identity, row[0], row[1]),
            )
            connection.execute("""INSERT INTO counters VALUES ('cache_hits',1)
                ON CONFLICT(name) DO UPDATE SET value=value+1""")
            return vector

    def complete(
        self, request_id: str, tokens: int, vectors: Sequence[tuple[str, list[float]]]
    ) -> None:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT reserved,status FROM requests WHERE id=?", (request_id,)
            ).fetchone()
            if not row or row[1] != "pending" or tokens < 0 or self.cost(tokens) > row[0]:
                raise ValueError("Invalid embedding usage; reservation retained")
            for identity, vector in vectors:
                connection.execute(
                    "INSERT INTO cache VALUES (?,?,?) ON CONFLICT DO NOTHING",
                    (identity, json.dumps(validate_vector(vector)), request_id),
                )
            connection.execute(
                "UPDATE requests SET actual=?,tokens=?,status='complete' WHERE id=?",
                (self.cost(tokens), tokens, request_id),
            )

    def report(self) -> dict[str, int | str]:
        with self.connect() as connection:
            row = connection.execute("""SELECT count(*),COALESCE(SUM(tokens),0),
                COALESCE(SUM(COALESCE(actual,reserved)),0),
                COALESCE(SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END),0)
                FROM requests""").fetchone()
            hits = connection.execute(
                "SELECT value FROM counters WHERE name='cache_hits'"
            ).fetchone()
            return {
                "requests": row[0],
                "tokens": row[1],
                "estimated_spend_usd": str(Decimal(row[2]) / self.scale),
                "pending_reservations": row[3],
                "cache_hits": hits[0] if hits else 0,
            }


class PaidEmbedder:
    def __init__(
        self,
        settings: EmbeddingSettings,
        ledger: EmbeddingLedger,
        *,
        confirmed: bool,
        reuse_namespace: str | None = None,
        telemetry: Telemetry | None = None,
    ) -> None:
        if not confirmed:
            raise ValueError("Explicit embedding confirmation required")
        settings.validate_execution()
        self.settings, self.ledger = settings, ledger
        self.reuse_namespace = reuse_namespace
        self.telemetry = telemetry
        self.successful_endpoint_latencies: list[float] = []
        self.client = AsyncOpenAI(
            api_key=settings.agent_api_key.get_secret_value() if settings.agent_api_key else "",
            max_retries=0,
            timeout=30,
        )

    async def embed(self, entries: list[tuple[str, str]]) -> dict[str, list[float]]:
        span = (
            self.telemetry.tracer.start_as_current_span(
                "knowledge.embedding", record_exception=False, set_status_on_exception=False
            )
            if self.telemetry
            else nullcontext()
        )
        with span:
            return await self._embed(entries)

    async def _embed(self, entries: list[tuple[str, str]]) -> dict[str, list[float]]:
        if not 1 <= len(entries) <= 32 or len({key for key, _ in entries}) != len(entries):
            raise ValueError("Invalid bounded embedding batch")
        results: dict[str, list[float]] = {}
        pending: list[tuple[str, str]] = []
        for key, content in entries:
            if not content.strip() or len(content.encode()) > 8000:
                raise ValueError("Embedding input outside conservative token bound")
            cached = await asyncio.to_thread(self.ledger.cached, key)
            if cached is None and self.reuse_namespace:
                cached = await asyncio.to_thread(self.ledger.reuse, key, self.content_key(content))
            if cached is not None:
                results[key] = cached
                if self.telemetry:
                    self.telemetry.embedding_cache_hits.add(1)
            else:
                pending.append((key, content))
        if not pending:
            return results
        request = await asyncio.to_thread(
            self.ledger.reserve, sum(len(text.encode()) for _, text in pending)
        )
        try:
            started = perf_counter()
            if self.telemetry:
                self.telemetry.embedding_requests.add(1)
            response = await self.client.embeddings.create(
                model=self.settings.embedding_model,
                dimensions=self.settings.embedding_dimensions,
                encoding_format="float",
                input=[content for _, content in pending],
            )
            self.successful_endpoint_latencies.append(perf_counter() - started)
            if response.model != self.settings.embedding_model or len(response.data) != len(
                pending
            ):
                raise ValueError("Invalid embedding response")
            ordered = sorted(response.data, key=lambda entry: entry.index)
            if [e.index for e in ordered] != list(range(len(pending))):
                raise ValueError("Invalid embedding response indexes")
            completed = [
                (key, validate_vector(e.embedding))
                for (key, _), e in zip(pending, ordered, strict=True)
            ]
            shared = (
                [
                    (self.content_key(content), vector)
                    for (_, content), (_, vector) in zip(pending, completed, strict=True)
                ]
                if self.reuse_namespace
                else []
            )
            await asyncio.to_thread(
                self.ledger.complete, request, response.usage.total_tokens, completed + shared
            )
            if self.telemetry:
                self.telemetry.embedding_tokens.add(response.usage.total_tokens)
                self.telemetry.embedding_cost.add(
                    float(self.ledger.cost(response.usage.total_tokens) / 10**12)
                )
            results.update(completed)
            return results
        except Exception:
            # Do not expose provider exception text/headers or release uncertain paid reservations.
            raise ValueError("embedding_request_failed_reservation_retained") from None

    async def close(self) -> None:
        await self.client.close()

    def content_key(self, content: str) -> str:
        return digest(
            json.dumps(
                [
                    "shared-embedding-content-v1",
                    self.settings.embedding_model,
                    self.settings.embedding_dimensions,
                    self.reuse_namespace,
                    digest(content),
                ]
            )
        )


def query_key(query: str, index: KnowledgeIndexVersion) -> str:
    return index.cache_key(digest("query"), digest(query))


def embedding_namespace(index: KnowledgeIndexVersion) -> str:
    return digest(
        json.dumps(
            [
                index.model,
                index.dimensions,
                index.chunker,
                index.normalization,
                index.embedding_version,
            ]
        )
    )
