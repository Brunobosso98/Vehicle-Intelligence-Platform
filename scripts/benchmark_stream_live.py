#!/usr/bin/env python3
import asyncio
import json
import os
import statistics
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx


async def canonical_counts(acquisition_id: str, session_id: str) -> dict[str, int]:
    # UUID validation makes this test-only psql command independent of application
    # query implementations while keeping every selection bound to its own fixture.
    acquisition, session = UUID(acquisition_id), UUID(session_id)
    query = f"""SELECT json_build_object(
      'received_messages',(SELECT count(*) FROM stream_receipts WHERE acquisition_session_id='{acquisition}'),
      'persisted',(SELECT count(*) FROM telemetry_samples WHERE session_id='{session}'),
      'unique_samples',(SELECT count(DISTINCT sample_id) FROM telemetry_samples WHERE session_id='{session}')
    );"""
    process = await asyncio.create_subprocess_exec(
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "sh",
        "-c",
        'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "$1"',
        "benchmark-query",
        query,
        stdout=asyncio.subprocess.PIPE,
    )
    output, _ = await process.communicate()
    if process.returncode:
        raise RuntimeError("benchmark identity query failed")
    decoded = json.loads(output)
    return {
        key: int(decoded[key])
        for key in ("received_messages", "persisted", "unique_samples")
    }


async def worker_metrics() -> dict[str, float]:
    from prometheus_client.parser import text_string_to_metric_families

    process = await asyncio.create_subprocess_exec(
        "docker",
        "compose",
        "exec",
        "-T",
        "stream-consumer",
        "python",
        "-c",
        "import urllib.request; print(urllib.request.urlopen('http://stream-consumer:8001/metrics',timeout=3).read().decode())",
        stdout=asyncio.subprocess.PIPE,
    )
    output, _ = await process.communicate()
    if process.returncode:
        raise RuntimeError("benchmark worker metric query failed")
    result: dict[str, float] = {}
    for family in text_string_to_metric_families(output.decode()):
        for sample in family.samples:
            result[sample.name] = result.get(sample.name, 0) + sample.value
    return result


async def memory_snapshot() -> list[dict[str, str]]:
    ids = await asyncio.create_subprocess_exec(
        "docker",
        "compose",
        "ps",
        "-q",
        "api",
        "stream-consumer",
        "broker",
        stdout=asyncio.subprocess.PIPE,
    )
    output, _ = await ids.communicate()
    if ids.returncode:
        raise RuntimeError("benchmark container lookup failed")
    containers = output.decode().split()
    if len(containers) != 3:
        raise RuntimeError("benchmark requires all three actual pipeline containers")
    stats = await asyncio.create_subprocess_exec(
        "docker",
        "stats",
        "--no-stream",
        "--format",
        "{{json .}}",
        *containers,
        stdout=asyncio.subprocess.PIPE,
    )
    output, _ = await stats.communicate()
    if stats.returncode:
        raise RuntimeError("benchmark memory measurement failed")
    samples = [
        {"container": row["Name"], "memory_usage": row["MemUsage"]}
        for line in output.decode().splitlines()
        if (row := json.loads(line))
    ]
    if len(samples) != 3:
        raise RuntimeError("benchmark requires three measured container memory samples")
    return samples


def buffered_points(metrics: dict[str, float]) -> float:
    if "acquisition_consumer_buffered_points" not in metrics:
        raise RuntimeError("actual consumer buffer gauge was not measured")
    return metrics["acquisition_consumer_buffered_points"]


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
        metrics_before = await worker_metrics()
        memory_samples = [{"produced": 0, "containers": await memory_snapshot()}]
        buffered_samples = [buffered_points(metrics_before)]
        broker_before = await client.get("/metrics")
        broker_before.raise_for_status()
        from prometheus_client.parser import text_string_to_metric_families

        def broker_seconds(body: str) -> float:
            return sum(
                sample.value
                for family in text_string_to_metric_families(body)
                for sample in family.samples
                if sample.name == "acquisition_broker_publish_duration_seconds_sum"
                and sample.labels.get("outcome") == "acknowledged"
            )

        # Keep all 100 Hz fixture observations in the past at publication start.
        started_at = datetime.now(UTC) - timedelta(milliseconds=total * 10)
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
            if (offset + batch_size) % 25000 == 0:
                memory_samples.append(
                    {
                        "produced": offset + batch_size,
                        "containers": await memory_snapshot(),
                    }
                )
                buffered_samples.append(buffered_points(await worker_metrics()))
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
        counts = await canonical_counts(
            acquisition["id"], acquisition["driving_session_id"]
        )
        metrics_after = await worker_metrics()
        buffered_samples.append(buffered_points(metrics_after))
        broker_after = await client.get("/metrics")
        broker_after.raise_for_status()
        broker_publish_seconds = broker_seconds(broker_after.text) - broker_seconds(
            broker_before.text
        )
        elapsed = time.perf_counter() - started
        stop = await client.post(
            f"/api/v1/acquisitions/{acquisition['id']}/stop", headers=headers
        )
        stop.raise_for_status()
    db_seconds = metrics_after.get(
        "telemetry_db_batch_duration_seconds_sum", 0
    ) - metrics_before.get("telemetry_db_batch_duration_seconds_sum", 0)
    if db_seconds <= 0:
        raise RuntimeError("actual DB persistence duration was not measured")
    report = {
        "observations_produced": total,
        "observations_accepted": total,
        "observations_persisted": persisted,
        "lost_observations": total - persisted,
        "duplicate_messages_received": counts["received_messages"]
        - counts["persisted"],
        "duplicate_canonical_rows": counts["persisted"] - counts["unique_samples"],
        "consumer_throughput_observations_per_second": persisted / elapsed,
        "db_persistence_throughput_observations_per_second": persisted / db_seconds,
        "producer_throughput": total / producer_seconds,
        "gateway_batch_latency_p50_ms": statistics.median(latencies) * 1000,
        "gateway_batch_latency_p95_ms": sorted(latencies)[
            int(len(latencies) * 0.95) - 1
        ]
        * 1000,
        "end_to_end_seconds": time.perf_counter() - started,
        "broker_acknowledgement_mean_batch_ms": broker_publish_seconds
        / len(latencies)
        * 1000,
        "container_memory_samples": memory_samples,
        "consumer_buffered_points_samples": buffered_samples,
        "consumer_buffer_bound": 20000,
        "buffer_growth": "actual bounded window gauge sampled at 0/25k/50k/75k/100k and drain",
        "reconnect_behavior": "covered by deterministic collector and E2E scenarios",
    }
    print(json.dumps(report, indent=2))
    if (
        max(buffered_samples) > 20000
        or broker_publish_seconds <= 0
        or persisted != total
        or counts["unique_samples"] != total
        or counts["received_messages"] != total
    ):
        raise SystemExit("live benchmark lost observations")


if __name__ == "__main__":
    asyncio.run(main())
