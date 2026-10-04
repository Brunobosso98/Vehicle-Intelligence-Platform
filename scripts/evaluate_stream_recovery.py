"""Real-stack Phase 4 recovery; owns fixtures, never deletes application volumes."""

import asyncio
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
from vehicle_platform.acquisition.collector import (
    AcquisitionCollector,
    GatewayPublisher,
)
from vehicle_platform.acquisition.stream import BoundedSpool
from vehicle_platform.telemetry.domain import RawTelemetryRecord

COMPOSE_RECOVERY_TIMEOUT_SECONDS = 300


async def compose(*arguments: str) -> None:
    process = await asyncio.create_subprocess_exec(
        "docker", "compose", *arguments, stdout=asyncio.subprocess.DEVNULL
    )
    # PostgreSQL's health policy allows 180 seconds for crash recovery plus
    # up to 60 seconds of health retries. Keep this outer bound above that
    # documented window so it cannot cancel a progressing fsync recovery.
    async with asyncio.timeout(COMPOSE_RECOVERY_TIMEOUT_SECONDS):
        if await process.wait():
            raise RuntimeError(f"Compose recovery operation failed: {arguments[0]}")


async def wait_for_browser_proxies() -> None:
    """Wait until the real Next.js status and domain proxies recover too."""
    deadline = time.monotonic() + 120
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:3000", timeout=15
    ) as browser:
        while time.monotonic() < deadline:
            try:
                status, vehicles = await asyncio.gather(
                    browser.get("/api/status"), browser.get("/api/domain/vehicles")
                )
                status.raise_for_status()
                vehicles.raise_for_status()
                if status.json().get("kind") == "healthy":
                    return
            except (httpx.HTTPError, ValueError):
                pass
            await asyncio.sleep(2)
    raise RuntimeError("Next.js status/domain proxies did not recover")


async def main() -> None:
    base = "http://127.0.0.1:8000"
    pending = Path(".validation/retrospective/recovery-spool")
    if pending.exists() and pending.stat().st_size:
        raise RuntimeError(
            "previous recovery spool remains; preserve it before rerunning"
        )
    async with httpx.AsyncClient(base_url=base, timeout=30) as client:
        response = await client.post(
            "/api/v1/vehicles",
            json={
                "manufacturer": "BMW",
                "model": "335i",
                "nickname": "retrospective recovery fixture",
            },
        )
        response.raise_for_status()
        created = await client.post(
            "/api/v1/acquisitions",
            json={
                "vehicle_id": response.json()["id"],
                "recipe_key": "data-quality-validation",
                "adapter": "synthetic",
                "source_id": "recovery-acceptance",
            },
        )
        created.raise_for_status()
        acquisition = created.json()
        publisher = GatewayPublisher(
            base, UUID(acquisition["id"]), acquisition["ingestion_token"]
        )
        collector = AcquisitionCollector(BoundedSpool(pending), batch_size=20)

        async def outage_send(batch, publish):
            # Fail fast only while intentionally withholding a dependency.
            # Recovery then exercises the real collector's bounded retry policy.
            configured = collector.retries
            collector.retries = 0
            try:
                await collector._send(batch, publish)
            finally:
                collector.retries = configured

        origin = datetime.now(UTC) - timedelta(seconds=40)
        records = tuple(
            RawTelemetryRecord(
                origin + timedelta(seconds=i / 5 + (5 if i >= 40 else 0)),
                "engine.rpm",
                1000 + i * 5,
                "rpm",
                f"recovery:{i}",
                i,
            )
            for i in range(100)
        )
        try:
            # Pending acknowledged records must survive actual container recreation,
            # not just a stop/start preserving a container writable layer.
            await compose("stop", "stream-consumer")
            await publisher(records[:20])
            # Broker interruption while the acquisition is active uses the actual
            # HTTP publisher and bounded durable collector path.
            await compose("stop", "broker")
            await outage_send(records[20:40], publisher)
            if collector.spool.occupancy_bytes == 0:
                raise RuntimeError("broker failure did not activate spool")
            await compose(
                "up", "-d", "--no-deps", "--force-recreate", "--wait", "broker"
            )
            await collector._replay(publisher)
            if collector.spool.occupancy_bytes:
                raise RuntimeError("broker recovery did not drain spool")
            # Offset recovery must drain messages published with no consumer.
            await compose("stop", "stream-consumer")
            await publisher(records[40:60])
            # Preserve the existing worker configuration, including an enabled
            # observability overlay, when recovering a stopped container.
            await compose("up", "-d", "--no-recreate", "--wait", "stream-consumer")
            await compose("stop", "db")
            await outage_send(records[60:80], publisher)
            if not collector.spool.occupancy_bytes:
                raise RuntimeError("database outage did not activate durable recovery")
            await compose("up", "-d", "--no-recreate", "--wait", "db")
            await collector._replay(publisher)
            unavailable = GatewayPublisher(
                "http://127.0.0.1:1",
                UUID(acquisition["id"]),
                acquisition["ingestion_token"],
            )
            await outage_send(records[80:], unavailable)
            if not collector.spool.occupancy_bytes:
                raise RuntimeError("API interruption did not retain observations")
            await collector._replay(publisher)
            # Ambiguous delivery is replayed with new envelopes but stable
            # canonical identities; canonical rows must remain unique.
            await publisher(records)
            deadline = time.monotonic() + 60
            points = []
            while time.monotonic() < deadline:
                response = await client.get(
                    f"/api/v1/sessions/{acquisition['driving_session_id']}/telemetry",
                    params={"signal": "engine.rpm", "limit": 1000},
                )
                response.raise_for_status()
                points = response.json()["points"]
                if len(points) == len(records):
                    break
                await asyncio.sleep(0.2)
            if len(points) != len(records) or len(
                {p["sample_id"] for p in points}
            ) != len(records):
                raise RuntimeError("recovery lost or duplicated canonical observations")
            headers = {"Authorization": f"Bearer {acquisition['ingestion_token']}"}
            (
                await client.post(
                    f"/api/v1/acquisitions/{acquisition['id']}/stop", headers=headers
                )
            ).raise_for_status()
            finalized = await client.post(
                f"/api/v1/acquisitions/{acquisition['id']}/finalize"
            )
            finalized.raise_for_status()
            events = await client.get(
                f"/api/v1/sessions/{acquisition['driving_session_id']}/events"
            )
            events.raise_for_status()
            if not any(e["event_type"] == "telemetry_gap" for e in events.json()):
                raise RuntimeError(
                    "streamed acquisition gap was not visible in canonical events"
                )
            # Playwright's first page opens both proxies at once. Wait for them
            # after dependency recovery rather than starting E2E during the
            # observed transient DNS/network warm-up window.
            await wait_for_browser_proxies()
            print(
                json.dumps(
                    {
                        "produced": len(records),
                        "persisted": len(points),
                        "lost": len(records) - len(points),
                        "duplicate_canonical_rows": len(points)
                        - len({p["sample_id"] for p in points}),
                        "broker_restart_and_recreation": "PASS",
                        "consumer_restart": "PASS",
                        "telemetry_gap": "PASS",
                        "database_interruption": "PASS",
                        "api_unavailable": "PASS",
                        "spool_replayed": collector.stats.replayed,
                        "spool_dropped": collector.spool.dropped,
                        "browser_status_and_domain_proxies": "PASS",
                    },
                    indent=2,
                )
            )
        finally:
            # Restore dependencies on failure; preserve pending spool evidence.
            await compose(
                "up", "-d", "--no-recreate", "--wait", "db", "broker", "stream-consumer"
            )


if __name__ == "__main__":
    asyncio.run(main())
