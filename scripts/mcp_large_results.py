"""Large legitimate canonical dataset: response, memory and SQL read-only safety."""

import asyncio
import os
import tracemalloc
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from mcp import Client
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.main import create_app
from vehicle_platform.mcp.adapter import Adapter
from vehicle_platform.mcp.config import MCPSettings
from vehicle_platform.mcp.database import ReadOnlyDatabase
from vehicle_platform.mcp.server import create_server
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.telemetry.domain import RawTelemetryRecord
from vehicle_platform.telemetry.service import IngestionService

START = datetime(2026, 4, 1, tzinfo=UTC)


class DenseSource:
    async def read(self) -> AsyncIterator[RawTelemetryRecord]:
        for index in range(100002):
            yield RawTelemetryRecord(
                START + timedelta(microseconds=index * 500),
                "engine.rpm",
                900,
                "rpm",
                str(index),
                index,
            )


async def main() -> None:
    import json

    url = os.environ["TEST_DATABASE_URL"]
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError("disposable database required")
    settings = Settings(database_url=SecretStr(url), environment="test")
    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://fixture"
        ) as api,
    ):
        vehicle = (
            await api.post(
                "/api/v1/vehicles", json={"manufacturer": "fixture", "model": "large"}
            )
        ).json()["id"]
        sessions = []
        for index in range(102):
            response = await api.post(
                "/api/v1/sessions",
                json={
                    "vehicle_id": vehicle,
                    "source_type": "synthetic",
                    "started_at": (START + timedelta(days=index)).isoformat(),
                },
            )
            assert response.status_code == 201
            sessions.append(response.json()["id"])
        writable = Database(settings)
        try:
            result = await IngestionService(writable).ingest(
                UUID(sessions[0]), "synthetic", DenseSource()
            )
            assert result.accepted == 100002 and result.rejected == 0
        finally:
            await writable.close()
    readonly = ReadOnlyDatabase(settings)
    telemetry = Telemetry(settings, readonly, service_name="vehicle-platform-mcp")
    try:
        async with readonly.session() as db:
            assert await db.scalar(text("SHOW transaction_read_only")) == "on"
            assert await db.scalar(text("SHOW statement_timeout")) == "5s"
        rejected = False
        try:
            async with readonly.session() as db:
                await db.execute(
                    text("UPDATE vehicles SET model='forbidden' WHERE id=:id"),
                    {"id": UUID(vehicle)},
                )
        except SQLAlchemyError:
            rejected = True
        assert rejected, "MCP database must reject writes"
        async with Client(
            create_server(
                Adapter(readonly, settings, telemetry), telemetry, MCPSettings()
            )
        ) as client:
            listed = await client.call_tool(
                "list_sessions", {"vehicle_id": vehicle, "limit": 100}
            )
            assert not listed.is_error
            assert (
                listed.structured_content["returned"] == 100
                and listed.structured_content["truncated"]
            )
            arguments = {
                "vehicle_id": vehicle,
                "session_id": sessions[0],
                "signals": ["engine.rpm"],
                "window": {
                    "start": START.isoformat(),
                    "end": (START + timedelta(seconds=60)).isoformat(),
                },
                "max_samples": 1000,
            }
            tracemalloc.start()
            result = await client.call_tool("get_telemetry_window", arguments)
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            assert not result.is_error, result
            data = result.structured_content
            assert data["returned"] == 1000 and data["truncated"]
            assert data["data"]["points"][0]["value"] == 900
            assert data["data"]["points"][0]["sequence"] == 0
            assert data["data"]["points"][-1]["sequence"] == 999
            size = len(result.model_dump_json().encode())
            assert size <= 524288
            assert peak < 32 * 1024 * 1024, (
                "bounded result should not materialize the 100k source"
            )
            print(
                json.dumps(
                    {
                        "large_results": "PASS",
                        "canonical_samples": 100002,
                        "sessions": 102,
                        "returned_samples": 1000,
                        "truncated": True,
                        "result_bytes": size,
                        "python_traced_memory_bytes": {
                            "current": current,
                            "peak": peak,
                        },
                        "database_write_rejected": True,
                    }
                )
            )
    finally:
        await readonly.close()
        telemetry.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
