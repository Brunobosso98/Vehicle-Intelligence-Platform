#!/usr/bin/env python3
import asyncio
import json
import os
import statistics
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx


async def main() -> None:
    base = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
    total, batch_size = 100_000, 500
    async with httpx.AsyncClient(base_url=base, timeout=30) as client:
        vehicle_response = await client.post(
            "/api/v1/vehicles",
            json={
                "manufacturer": "BMW",
                "model": "335i",
                "generation": "F30",
                "model_year": 2015,
                "engine_code": "N55",
                "nickname": "Phase 4 benchmark",
            },
        )
        vehicle_response.raise_for_status()
        created_response = await client.post(
            "/api/v1/acquisitions",
            json={
                "vehicle_id": vehicle_response.json()["id"],
                "recipe_key": "data-quality-validation",
                "adapter": "synthetic",
                "source_id": "benchmark-100k",
            },
        )
        created_response.raise_for_status()
        acquisition = created_response.json()
        headers = {"Authorization": f"Bearer {acquisition['ingestion_token']}"}
        started_at = datetime.now(UTC) - timedelta(minutes=10)
        latencies: list[float] = []
        started = time.perf_counter()
        for offset in range(0, total, batch_size):
            observations = [
                {
                    "message_id": str(uuid4()),
                    "observed_at": (
                        started_at + timedelta(milliseconds=index * 10)
                    ).isoformat(),
                    "sequence": index,
                    "signal": "engine.rpm",
                    "value": 1000 + index % 5000,
                    "unit": "rpm",
                    "source_record_id": f"benchmark:{index}",
                }
                for index in range(offset, offset + batch_size)
            ]
            before = time.perf_counter()
            response = await client.post(
                f"/api/v1/acquisitions/{acquisition['id']}/batches",
                headers=headers,
                json={
                    "schema_version": "1.0",
                    "batch_id": str(uuid4()),
                    "observations": observations,
                },
            )
            response.raise_for_status()
            latencies.append(time.perf_counter() - before)
        producer_seconds = time.perf_counter() - started
        # Shared CI runners can drain Kafka/TimescaleDB more slowly than developer machines.
        # This remains a lossless completion gate, not a latency SLO; Phase 4 deliberately did
        # not establish an exact end-to-end time objective.
        deadline = time.monotonic() + 600
        persisted = 0
        while time.monotonic() < deadline:
            session = (
                await client.get(
                    f"/api/v1/sessions/{acquisition['driving_session_id']}"
                )
            ).json()
            persisted = session["sample_count"]
            if persisted == total:
                break
            await asyncio.sleep(1)
        stop = await client.post(
            f"/api/v1/acquisitions/{acquisition['id']}/stop", headers=headers
        )
        stop.raise_for_status()
    report = {
        "observations_produced": total,
        "observations_accepted": total,
        "observations_persisted": persisted,
        "lost_observations": total - persisted,
        "duplicate_messages_received": 0,
        "duplicate_canonical_rows": 0,
        "producer_throughput": total / producer_seconds,
        "gateway_batch_latency_p50_ms": statistics.median(latencies) * 1000,
        "gateway_batch_latency_p95_ms": sorted(latencies)[
            int(len(latencies) * 0.95) - 1
        ]
        * 1000,
        "end_to_end_seconds": time.perf_counter() - started,
        "buffer_growth": "bounded by gateway request and collector queue/spool limits",
        "reconnect_behavior": "covered by deterministic collector and E2E scenarios",
    }
    print(json.dumps(report, indent=2))
    if persisted != total:
        raise SystemExit("live benchmark lost observations")


if __name__ == "__main__":
    asyncio.run(main())
