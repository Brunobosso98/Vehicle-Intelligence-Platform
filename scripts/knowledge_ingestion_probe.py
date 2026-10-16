"""Disposable ingestion instrumentation probe; its embedding transport cannot access a network.

Run only inside the knowledge observability test container. The synthetic ledger is isolated
from the operator's cumulative paid ledger. No OpenAI call or real-model validation is claimed.
"""

import asyncio
import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from uuid import uuid4

import httpx
from openai import AsyncOpenAI
from opentelemetry import trace
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.knowledge.domain import (
    Applicability,
    DocumentVersion,
    KnowledgeSource,
    Trust,
    digest,
)
from vehicle_platform.knowledge.embeddings import (
    EmbeddingLedger,
    EmbeddingSettings,
    PaidEmbedder,
    PriceVerification,
)
from vehicle_platform.knowledge.extraction import Section, chunks
from vehicle_platform.knowledge.repository import KnowledgeRepository
from vehicle_platform.observability.telemetry import Telemetry


async def exercise(telemetry: Telemetry, settings: Settings) -> str:
    database = Database(settings)
    now = datetime.now(UTC)
    source = KnowledgeSource(
        id=uuid4(),
        publisher="Synthetic observability fixture",
        canonical_url="https://example.com/knowledge-instrumentation",
        source_type="supplier",
        trust=Trust.TIER_2_STRONG_TECHNICAL,
        status="VERIFIED",
        verified_at=now,
    )
    content = "Project-authored synthetic documentary observability reference."
    document = DocumentVersion(
        id=uuid4(),
        document_id=uuid4(),
        source_id=source.id,
        source_version=1,
        title="Synthetic instrumentation probe",
        checksum=digest(content),
        retrieved_at=now,
        mime="text/plain",
        license_note="Project-authored synthetic fixture",
        applicability=Applicability(
            subsystems=["diagnostics"], calibration="principle"
        ),
        redistribution="synthetic",
        status="EXTRACTED",
    )
    pieces = chunks(document.id, [Section(("Synthetic instrumentation",), content)])
    price = PriceVerification(
        model="text-embedding-3-small",
        usd_per_million=Decimal("0.02"),
        verified_on=datetime.now(UTC).date(),
        official_url="https://developers.openai.com/api/docs/models/text-embedding-3-small",
    )
    ledger = EmbeddingLedger(
        Path("/tmp/knowledge-probe-ledger.sqlite"), Decimal(2), price
    )
    embedding = PaidEmbedder(
        EmbeddingSettings(agent_api_key="synthetic-no-network-probe"),
        ledger,
        confirmed=True,
        telemetry=telemetry,
    )
    await embedding.close()

    def response(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST" and request.url.path == "/v1/embeddings"
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": "text-embedding-3-small",
                "data": [
                    {
                        "object": "embedding",
                        "index": 0,
                        "embedding": [1.0] + [0.0] * 1535,
                    }
                ],
                "usage": {"prompt_tokens": 2, "total_tokens": 2},
            },
        )

    embedding.client = AsyncOpenAI(
        api_key="synthetic-no-network-probe",
        max_retries=0,
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(response), trust_env=False
        ),
    )
    repository = KnowledgeRepository(database, telemetry)
    try:
        with telemetry.tracer.start_as_current_span(
            "knowledge.operator_probe",
            record_exception=False,
            set_status_on_exception=False,
        ):
            identifier = format(
                trace.get_current_span().get_span_context().trace_id, "032x"
            )
            await repository.ingest(source, document, pieces)
            try:
                await repository.ingest(
                    source.model_copy(update={"version": 99}), document, pieces
                )
            except ValueError:
                pass
            else:
                raise AssertionError("Inconsistent provenance was accepted")
            await embedding.embed([("synthetic-observability", content)])
            await embedding.embed([("synthetic-observability", content)])
        telemetry.traces.force_flush(timeout_millis=10000)
        return identifier
    finally:
        await embedding.close()
        await database.close()


def main() -> None:
    settings = Settings()
    if (
        settings.environment != "test"
        or not settings.database_url.get_secret_value()
        .rsplit("/", 1)[-1]
        .startswith("vehicle_test")
        or os.environ.get("KNOWLEDGE_FREE_PROBE") != "yes"
    ):
        raise SystemExit("Disposable explicitly enabled knowledge probe required")
    telemetry = Telemetry(settings, service_name="vehicle-platform-knowledge-probe")
    try:
        identifier = asyncio.run(exercise(telemetry, settings))
        Path("/tmp/knowledge-probe-receipt.json").write_text(
            json.dumps(
                {
                    "trace_id": identifier,
                    "paid_calls": 0,
                    "embedding_transport": "synthetic-mock",
                }
            )
        )

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                payload = telemetry.render_metrics()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: object) -> None:
                pass

        with HTTPServer(("0.0.0.0", 8002), Handler) as server:
            server.serve_forever()
    finally:
        telemetry.shutdown()


if __name__ == "__main__":
    main()
