"""Runtime query embeddings: immutable cached vectors, explicit billing and deterministic CI."""

import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from test_knowledge import price

from vehicle_platform.core.config import Settings
from vehicle_platform.knowledge.domain import KnowledgeIndexVersion, digest
from vehicle_platform.knowledge.embeddings import EmbeddingLedger, EmbeddingSettings, query_key
from vehicle_platform.knowledge.queries import QueryEmbeddingEncoder, cached_query
from vehicle_platform.observability.telemetry import Telemetry


@pytest.fixture
def setup_query(tmp_path, settings):
    index = KnowledgeIndexVersion(
        id="synthetic-query-v1", corpus_checksum=digest("synthetic"), created_at=datetime.now(UTC)
    )
    repository = SimpleNamespace(active_index=AsyncMock(return_value=index))
    telemetry = Telemetry(settings)
    config = EmbeddingSettings(knowledge_ledger_path=tmp_path / "ledger.sqlite", _env_file=None)
    yield SimpleNamespace(index=index, repository=repository, telemetry=telemetry, config=config)
    telemetry.shutdown()


async def test_runtime_cache_lookup_never_creates_missing_ledger_or_provider(
    setup_query, monkeypatch
):
    value = setup_query
    constructor = Mock(side_effect=AssertionError("A cache-only request cannot buy embeddings"))
    monkeypatch.setattr("vehicle_platform.knowledge.queries.PaidEmbedder", constructor)
    encoder = QueryEmbeddingEncoder(value.repository, value.config, value.telemetry)
    assert await encoder("synthetic N55 query", value.index.id) is None
    assert not value.config.knowledge_ledger_path.exists()
    ledger = EmbeddingLedger(value.config.knowledge_ledger_path, Decimal(2), price())
    vector = [1.0] + [0.0] * 1535
    request = ledger.reserve(100)
    ledger.complete(request, 2, [(query_key("synthetic N55 query", value.index), vector)])
    assert await encoder("synthetic N55 query", value.index.id) == vector
    assert ledger.report()["requests"] == 1
    constructor.assert_not_called()
    assert await encoder("synthetic N55 query", "wrong-index") is None
    value.repository.active_index.return_value = None
    assert await encoder("synthetic N55 query", value.index.id) is None
    await encoder.close()


async def test_query_mode_and_model_mismatch_cannot_silently_switch_vectors(setup_query):
    value = setup_query
    encoder = QueryEmbeddingEncoder(
        value.repository,
        value.config.model_copy(update={"knowledge_query_mode": "disabled"}),
        value.telemetry,
    )
    assert await encoder("synthetic query", value.index.id) is None
    value.repository.active_index.assert_not_awaited()
    encoder = QueryEmbeddingEncoder(
        value.repository,
        value.config.model_copy(update={"embedding_model": "other"}),
        value.telemetry,
    )
    assert await encoder("synthetic query", value.index.id) is None
    encoder = QueryEmbeddingEncoder(
        value.repository,
        value.config.model_copy(update={"knowledge_query_mode": "paid"}),
        value.telemetry,
        confirmed=True,
        allow_paid=False,
    )
    assert await encoder("synthetic query", value.index.id) is None
    assert encoder._paid is None and not value.config.knowledge_ledger_path.exists()
    encoder = QueryEmbeddingEncoder(
        value.repository,
        value.config.model_copy(update={"knowledge_query_mode": "paid"}),
        value.telemetry,
        allow_paid=True,
    )
    assert await encoder("synthetic query", value.index.id) is None
    assert encoder._paid is None


@pytest.mark.parametrize("payload", ["invalid-json", "[]", "[0,0]"])
async def test_corrupt_query_cache_degrades_without_repurchasing(setup_query, payload):
    value = setup_query
    ledger = EmbeddingLedger(value.config.knowledge_ledger_path, Decimal(2), price())
    request = ledger.reserve(100)
    vector = [1.0] + [0.0] * 1535
    identity = query_key("synthetic query", value.index)
    ledger.complete(request, 2, [(identity, vector)])
    with ledger.connect() as db:
        db.execute("UPDATE cache SET vector=? WHERE identity=?", (payload, identity))
    encoder = QueryEmbeddingEncoder(value.repository, value.config, value.telemetry)
    assert await encoder("synthetic query", value.index.id) is None
    assert ledger.report()["requests"] == 1


@pytest.mark.parametrize(
    "mode", ["success", "cutoff", "missing_key", "timeout", "provider_failure"]
)
async def test_paid_query_requires_optin_and_uses_shared_durable_spend_guard(
    setup_query, monkeypatch, mode
):
    from pydantic import SecretStr

    value = setup_query
    price_file = value.config.knowledge_ledger_path.parent / "price.json"
    price_file.write_text(price().model_dump_json())
    config = value.config.model_copy(
        update={
            "knowledge_query_mode": "paid",
            "agent_api_key": None
            if mode == "missing_key"
            else SecretStr("synthetic-unit-query-key"),
            "knowledge_price_file": price_file,
            "phase8_max_spend": Decimal("0.00000001") if mode == "cutoff" else Decimal(2),
        }
    )
    vector = [1.0] + [0.0] * 1535
    client = SimpleNamespace(
        embeddings=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    model="text-embedding-3-small",
                    data=[SimpleNamespace(index=0, embedding=vector)],
                    usage=SimpleNamespace(total_tokens=2),
                )
            )
        ),
        close=AsyncMock(),
    )
    constructor = Mock(return_value=client)
    monkeypatch.setattr("vehicle_platform.knowledge.embeddings.AsyncOpenAI", constructor)
    if mode == "provider_failure":
        client.embeddings.create.side_effect = ValueError("must not expose credential or input")
    if mode == "timeout":
        monkeypatch.setattr(
            "vehicle_platform.knowledge.queries.cached_query", Mock(side_effect=TimeoutError)
        )
    encoder = QueryEmbeddingEncoder(
        value.repository, config, value.telemetry, confirmed=True, allow_paid=True
    )
    try:
        if mode == "success":
            values = await asyncio.gather(
                encoder("synthetic N55 query", value.index.id),
                encoder("synthetic N55 query", value.index.id),
            )
            assert values == [vector, vector]
            assert client.embeddings.create.await_count == 1
            assert (
                cached_query(config.knowledge_ledger_path, "synthetic N55 query", value.index)
                == vector
            )
        else:
            assert await encoder("synthetic N55 query", value.index.id) is None
            assert client.embeddings.create.await_count == int(mode == "provider_failure")
    finally:
        await encoder.close()
    if mode == "success":
        client.close.assert_awaited_once()
    if mode in {"missing_key", "timeout"}:
        constructor.assert_not_called()
        assert not config.knowledge_ledger_path.exists()
    if mode == "provider_failure":
        ledger = EmbeddingLedger(config.knowledge_ledger_path, Decimal(2), price())
        assert ledger.report()["pending_reservations"] == 1


def test_test_application_never_allows_paid_queries_from_environment(monkeypatch):
    from vehicle_platform.main import create_app

    monkeypatch.setenv("VIP_KNOWLEDGE_QUERY_MODE", "paid")
    monkeypatch.setenv("VIP_8_CONFIRM_EMBEDDING_SPEND", "yes")
    app = create_app(
        Settings(database_url="postgresql+asyncpg://test:test@127.0.0.1:1/test", environment="test")
    )
    assert app.state.knowledge_service.encoder.allow_paid is False


@pytest.mark.parametrize("sentinel", ["test-only-key", ""])
async def test_dotenv_only_embedding_key_is_redacted_without_corrupting_empty_settings(
    tmp_path, monkeypatch, sentinel
):
    from vehicle_platform.main import create_app

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VIP_AGENT_API_KEY", raising=False)
    (tmp_path / ".env").write_text("VIP_AGENT_API_KEY=" + sentinel + "\n")
    app = create_app(
        Settings(database_url="postgresql+asyncpg://test:test@127.0.0.1:1/test", environment="test")
    )
    async with app.router.lifespan_context(app):
        payload = '{"query":"' + (sentinel or "N55") + '"}'
        result = json.loads(app.state.knowledge_service.redact(payload))
        assert result["query"] == ("[redacted]" if sentinel else "N55")


async def test_encoder_rejects_secret_in_query_before_cache_or_provider(setup_query):
    from pydantic import SecretStr

    value = setup_query
    config = value.config.model_copy(
        update={"agent_api_key": SecretStr("test-only-key"), "knowledge_query_mode": "paid"}
    )
    encoder = QueryEmbeddingEncoder(
        value.repository, config, value.telemetry, confirmed=True, allow_paid=True
    )
    assert await encoder("do not upload test-only-key", value.index.id) is None
    assert not value.config.knowledge_ledger_path.exists()
    value.repository.active_index.assert_not_awaited()
