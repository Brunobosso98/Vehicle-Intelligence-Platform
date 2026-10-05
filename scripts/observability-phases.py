"""Exercise measured Phase 1–5 paths and verify delivered, privacy-safe spans."""

import asyncio
import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from opentelemetry import context, propagate
from prometheus_client import generate_latest
from vehicle_platform.acquisition.adapters import ReplayAdapter
from vehicle_platform.acquisition.collector import (
    AcquisitionCollector,
    GatewayPublisher,
)
from vehicle_platform.acquisition.domain import preflight
from vehicle_platform.acquisition.recipes import BY_KEY
from vehicle_platform.acquisition.stream import BoundedSpool
from vehicle_platform.telemetry.domain import RawTelemetryRecord


def dataset(started: datetime) -> tuple[RawTelemetryRecord, ...]:
    records = []
    for tick in range(156):
        second = tick / 5
        active = next((s for s in (5, 15, 25) if s <= second < s + 6), None)
        offset = second - active if active is not None else 0
        values = (
            ("engine.rpm", 2200 + offset * 500, "rpm"),
            ("vehicle.speed", 18 + offset * 2, "m/s"),
            ("engine.throttle_position", 90 if active is not None else 20, "%"),
            (
                "engine.boost_pressure",
                115000 + offset * 1000 if active is not None else 5000,
                "Pa",
            ),
            ("engine.intake_air_temperature", 300 + offset * 0.5, "K"),
            ("fuel.high_pressure", 19000000 if active is not None else 8000000, "Pa"),
        )
        for signal, value, unit in values:
            sequence = len(records)
            records.append(
                RawTelemetryRecord(
                    started + timedelta(seconds=second),
                    signal,
                    value,
                    unit,
                    f"obs:{sequence}",
                    sequence,
                )
            )
    return tuple(records)


async def main() -> None:
    evidence = Path(".validation/observability")
    evidence.mkdir(parents=True, exist_ok=True)
    trace_id = uuid4().hex
    headers = {"traceparent": f"00-{trace_id}-0000000000000001-01"}
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://127.0.0.1:4318"
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8000", headers=headers, timeout=30
    ) as client:

        async def post(path: str, payload: dict[str, object]) -> dict[str, object]:
            response = await client.post(path, json=payload)
            response.raise_for_status()
            return response.json()

        vehicle = await post(
            "/api/v1/vehicles", {"manufacturer": "fixture", "model": "observability"}
        )
        vid = vehicle["id"]
        configuration = await post(
            f"/api/v1/vehicles/{vid}/configurations",
            {
                "effective_at": "2020-01-01T00:00:00Z",
                "description": "observability",
                "provenance": "runtime-fixture",
            },
        )
        cid = configuration["id"]
        session_ids = []
        pull_ids = []
        for day in (3, 2, 1):
            start = datetime.now(UTC) - timedelta(days=day)
            session = await post(
                "/api/v1/sessions",
                {
                    "vehicle_id": vid,
                    "configuration_id": cid,
                    "source_type": "csv",
                    "started_at": start.isoformat(),
                },
            )
            sid = session["id"]
            session_ids.append(sid)
            csv = "timestamp,signal,value,unit,record_id,sequence\n" + "\n".join(
                f"{r.observed_at.isoformat()},{r.signal},{r.value},{r.unit},{r.source_record_id},{r.sequence}"
                for r in dataset(start)
            )
            response = await client.post(
                f"/api/v1/sessions/{sid}/imports/csv",
                files={"file": ("observability.csv", csv, "text/csv")},
            )
            response.raise_for_status()
            queried = await client.get(
                f"/api/v1/sessions/{sid}/telemetry", params={"signal": "engine.rpm"}
            )
            queried.raise_for_status()
            assert queried.json()["points"]
            analysis = await post(
                f"/api/v1/sessions/{sid}/analysis", {"profile": "generic-v1"}
            )
            assert analysis["pull_count"] == 3
            await post(f"/api/v1/sessions/{sid}/events/analyze", {})
            response = await client.get(f"/api/v1/sessions/{sid}/pulls")
            response.raise_for_status()
            pull_ids.extend(p["id"] for p in response.json())
        for path, payload in (
            ("/api/v1/analytics/pulls/compare", {"pull_ids": pull_ids[:2]}),
            ("/api/v1/analytics/pulls/repeated", {"pull_ids": pull_ids}),
            (f"/api/v1/sessions/{session_ids[0]}/analytics", {}),
            (f"/api/v1/vehicles/{vid}/configurations/{cid}/baseline", {}),
            (f"/api/v1/vehicles/{vid}/trends/boost", {}),
        ):
            await post(path, payload)
        acquisition = await post(
            "/api/v1/acquisitions",
            {
                "vehicle_id": vid,
                "recipe_key": "performance-pull",
                "adapter": "replay",
                "source_id": "observability",
            },
        )
        aid = str(acquisition["id"])
        publisher = GatewayPublisher(
            "http://127.0.0.1:8000", UUID(aid), str(acquisition["ingestion_token"])
        )
        collector = AcquisitionCollector(
            BoundedSpool(evidence / "collector-spool"), batch_size=500
        )
        token = context.attach(propagate.extract(headers))
        try:
            records = dataset(datetime.now(UTC) - timedelta(seconds=60))
            content = "observed_at,signal,value,unit,record_id,sequence\n" + "\n".join(
                f"{r.observed_at.isoformat()},{r.signal},{r.value},{r.unit},{r.source_record_id},{r.sequence}"
                for r in records
            )
            adapter = ReplayAdapter(content.encode(), speed=0)
            plan = preflight(
                BY_KEY["performance-pull"], await adapter.capabilities()
            ).sampling_plan
            await collector.run(adapter, plan, publisher, heartbeat=publisher.heartbeat)
        finally:
            context.detach(token)
            await asyncio.to_thread(collector.traces.shutdown)
        (evidence / "collector-metrics.txt").write_bytes(
            generate_latest(collector.registry)
        )
        response = await client.post(
            f"/api/v1/acquisitions/{aid}/stop",
            headers={"Authorization": f"Bearer {acquisition['ingestion_token']}"},
        )
        response.raise_for_status()
        # Publication acknowledges Kafka, not canonical DB completion. A worker
        # recovering from an outage can still be draining when collection stops.
        # Wait on this fixture's actual persisted rows before canonical analysis.
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            persisted = await client.get(
                f"/api/v1/sessions/{acquisition['driving_session_id']}/telemetry",
                params={
                    "signal": sorted({record.signal for record in records}),
                    "limit": len(records) + 1,
                },
            )
            persisted.raise_for_status()
            if persisted.json()["returned"] == len(records):
                break
            await asyncio.sleep(0.2)
        else:
            raise RuntimeError(
                "observability acquisition did not persist all fixture rows"
            )
        finalized = await post(f"/api/v1/acquisitions/{aid}/finalize", {})
        assert finalized["phase2"]["pull_count"] == 3

        required = {
            "telemetry.import",
            "telemetry.persistence",
            "telemetry.query",
            "analysis.run",
            "analysis.alignment",
            "analysis.detectors",
            "analysis.persistence",
            "analytics.source_selection",
            "analytics.telemetry_load",
            "analytics.metric_extraction",
            "analytics.normalization",
            "analytics.comparability",
            "analytics.aggregation",
            "analytics.baseline_build",
            "analytics.trend_aggregation",
            "analytics.persistence",
            "acquisition.collector.batch",
            "acquisition.consumer.persistence",
            "acquisition.live_analysis",
        }
        names: set[str] = set()
        deadline = time.monotonic() + 60
        async with httpx.AsyncClient(timeout=5) as backend:
            while time.monotonic() < deadline:
                response = await backend.get(
                    f"http://127.0.0.1:3200/api/traces/{trace_id}"
                )
                if response.status_code == 200:
                    trace = response.json()
                    batches = trace.get("batches", [])
                    spans = [
                        s
                        for b in batches
                        for scope in b.get(
                            "scopeSpans", b.get("instrumentationLibrarySpans", [])
                        )
                        for s in scope["spans"]
                    ]
                    names = {s["name"] for s in spans}
                    services = {
                        a["value"].get("stringValue")
                        for b in batches
                        for a in b["resource"]["attributes"]
                        if a["key"] == "service.name"
                    }
                    if (
                        required <= names
                        and {
                            "vehicle-platform-api",
                            "vehicle-platform-stream-consumer",
                            "vehicle-platform-collector",
                        }
                        <= services
                    ):
                        encoded = json.dumps(trace)
                        assert (
                            "db.statement" not in encoded
                            and "db.query.text" not in encoded
                        )
                        assert str(acquisition["ingestion_token"]) not in encoded
                        assert any(
                            any(
                                a["key"] in {"db.system", "db.system.name"}
                                for a in s.get("attributes", [])
                            )
                            for s in spans
                        )
                        (evidence / "phases-1-5-trace.json").write_text(encoded)
                        break
                await asyncio.sleep(1)
            else:
                raise RuntimeError(
                    f"missing delivered stage spans: {sorted(required - names)}"
                )
        response = await client.get("/metrics")
        response.raise_for_status()
        for metric in (
            "telemetry_import_rows",
            "analysis_detection_runs",
            "events_analysis_runs",
            "analytics_runs",
            "acquisition_observations_received",
            "acquisition_collector_heartbeats",
        ):
            assert metric in response.text, metric
        (evidence / "phases-1-5-api-metrics.txt").write_text(response.text)
        print(
            json.dumps(
                {
                    "trace_id": trace_id,
                    "required_spans": sorted(required),
                    "services": sorted(services),
                    "sql_and_token_redaction": "PASS",
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
