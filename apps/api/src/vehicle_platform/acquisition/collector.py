import asyncio
import json
import logging
import os
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID, uuid4

import httpx
from opentelemetry import propagate
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from vehicle_platform.acquisition.adapters import VehicleDataAdapter
from vehicle_platform.acquisition.domain import SamplingPlanItem
from vehicle_platform.acquisition.stream import BoundedSpool
from vehicle_platform.telemetry.domain import RawTelemetryRecord


@dataclass
class CollectorStats:
    produced: int = 0
    published: int = 0
    replayed: int = 0
    reconnects: int = 0
    dropped: int = 0


class AcquisitionCollector:
    """Hardware-near bounded collector with retry, backpressure, and disk replay."""

    def __init__(
        self, spool: BoundedSpool, batch_size: int = 100, queue_size: int = 1000, retries: int = 3
    ) -> None:
        if (
            not 1 <= batch_size <= 500
            or not batch_size <= queue_size <= 100000
            or not 0 <= retries <= 10
        ):
            raise ValueError("invalid collector bounds")
        self.spool, self.batch_size, self.retries = spool, batch_size, retries
        self.queue: asyncio.Queue[RawTelemetryRecord] = asyncio.Queue(maxsize=queue_size)
        self.stats = CollectorStats()
        self.registry = CollectorRegistry()
        self.produced_metric = Counter(
            "collector_observations_produced", "Adapter observations", registry=self.registry
        )
        self.published_metric = Counter(
            "collector_observations_published",
            "Gateway acknowledgements including replay",
            registry=self.registry,
        )
        self.replayed_metric = Counter(
            "collector_observations_replayed", "Acknowledged durable replay", registry=self.registry
        )
        self.dropped_metric = Counter(
            "collector_observations_dropped",
            "Capacity-rejected future observations",
            registry=self.registry,
        )
        self.reconnect_metric = Counter(
            "collector_recoveries", "Successful spool recovery cycles", registry=self.registry
        )
        self.spool_metric = Gauge(
            "collector_spool_bytes", "Durable pending bytes", registry=self.registry
        )
        self.spool_metric.set_function(lambda: self.spool.occupancy_bytes)
        self.queue_metric = Gauge(
            "collector_queue_observations", "Bounded in-memory queue", registry=self.registry
        )
        self.queue_metric.set_function(self.queue.qsize)
        self.batch_duration = Histogram(
            "collector_batch_duration_seconds",
            "Bounded publication/retry/spool execution",
            registry=self.registry,
        )
        self.traces = TracerProvider(
            resource=Resource.create({"service.name": "vehicle-platform-collector"})
        )
        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if endpoint:
            self.traces.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=endpoint.rstrip("/") + "/v1/traces", timeout=2)
                )
            )
        self.tracer = self.traces.get_tracer("vehicle_platform.collector")

    async def run(
        self,
        adapter: VehicleDataAdapter,
        plan: tuple[SamplingPlanItem, ...],
        publish: Callable[[tuple[RawTelemetryRecord, ...]], Awaitable[None]],
        *,
        heartbeat: Callable[[dict[str, object]], Awaitable[None]] | None = None,
    ) -> CollectorStats:
        await adapter.connect()
        batch: list[RawTelemetryRecord] = []
        started = datetime.now(UTC)
        last_sample: datetime | None = None
        closed = asyncio.Event()
        try:
            await adapter.capabilities()
        except BaseException:
            await adapter.close()
            await asyncio.to_thread(self.traces.shutdown)
            raise
        sampling = [asdict(item) for item in plan]

        async def report(connected: bool) -> None:
            if heartbeat is None:
                return
            try:
                await heartbeat(
                    {
                        "adapter_state": "connected" if connected else "disconnected",
                        "collection_started_at": started.isoformat(),
                        "last_sample_received_at": last_sample.isoformat() if last_sample else None,
                        "queue_observations": self.queue.qsize(),
                        "spool_bytes": self.spool.occupancy_bytes,
                        "spool_capacity_bytes": self.spool.maximum_bytes,
                        "spool_capacity_state": self.spool.capacity_state,
                        "dropped_observations": self.stats.dropped,
                        "capability_snapshot": asdict(await adapter.capabilities()),
                        "sampling_plan": sampling,
                    }
                )
            except (OSError, ValueError):
                logging.getLogger(__name__).warning('{"event":"collector.heartbeat_unavailable"}')

        async def report_periodically() -> None:
            while not closed.is_set():
                try:
                    await asyncio.wait_for(closed.wait(), timeout=5)
                except TimeoutError:
                    await report(True)

        task: asyncio.Task[None] | None = None
        try:
            await report(True)
            if heartbeat:
                task = asyncio.create_task(report_periodically())
            await self._replay(publish)
            async for record in adapter.read(plan):
                last_sample = datetime.now(UTC)
                self.stats.produced += 1
                self.produced_metric.inc()
                await self.queue.put(record)  # bounded backpressure
                batch.append(await self.queue.get())
                self.queue.task_done()
                if len(batch) >= self.batch_size:
                    await self._send(tuple(batch), publish)
                    batch.clear()
            if batch:
                await self._send(tuple(batch), publish)
                batch.clear()
        except BaseException:
            if batch:
                await self._spool(tuple(batch))
            raise
        finally:
            closed.set()
            if task:
                await task
            await report(False)
            await adapter.close()
            await asyncio.to_thread(self.traces.shutdown)
        self.stats.dropped = self.spool.dropped
        return self.stats

    async def _send(
        self,
        batch: tuple[RawTelemetryRecord, ...],
        publish: Callable[[tuple[RawTelemetryRecord, ...]], Awaitable[None]],
    ) -> None:
        started = perf_counter()
        try:
            with self.tracer.start_as_current_span("acquisition.collector.batch"):
                await self._send_observed(batch, publish)
        finally:
            self.batch_duration.observe(perf_counter() - started)

    async def _send_observed(
        self,
        batch: tuple[RawTelemetryRecord, ...],
        publish: Callable[[tuple[RawTelemetryRecord, ...]], Awaitable[None]],
    ) -> None:
        if self.spool.occupancy_bytes:
            await self._replay(publish)
            if self.spool.occupancy_bytes:
                await self._spool(batch)
                return
        if await self._publish_with_retry(batch, publish):
            self.stats.published += len(batch)
            self.published_metric.inc(len(batch))
            return
        await self._spool(batch)

    async def _publish_with_retry(
        self,
        batch: tuple[RawTelemetryRecord, ...],
        publish: Callable[[tuple[RawTelemetryRecord, ...]], Awaitable[None]],
    ) -> bool:
        for attempt in range(self.retries + 1):
            try:
                await publish(batch)
                return True
            except (OSError, TimeoutError) as exc:
                logging.getLogger(__name__).warning(
                    json.dumps(
                        {
                            "event": "collector.publish_retry",
                            "attempt": attempt + 1,
                            "maximum_attempts": self.retries + 1,
                            "exception_type": type(exc).__name__,
                        }
                    )
                )
                if attempt < self.retries:
                    await asyncio.sleep(
                        min(0.1 * 2**attempt, 1) * (1 + secrets.randbelow(201) / 1000)
                    )
        return False

    async def _spool(self, batch: tuple[RawTelemetryRecord, ...]) -> None:
        for record in batch:
            payload = f"{record.observed_at.isoformat()}\t{record.signal}\t{record.value}\t{record.unit}\t{record.source_record_id}\t{record.sequence if record.sequence is not None else ''}".encode()
            accepted = await asyncio.to_thread(self.spool.append, payload)
            self.stats.dropped = self.spool.dropped
            if not accepted:
                self.dropped_metric.inc()
                logging.getLogger(__name__).warning(
                    json.dumps(
                        {
                            "event": "collector.spool_capacity_reached",
                            "dropped": self.stats.dropped,
                            "pending_bytes": self.spool.occupancy_bytes,
                        }
                    )
                )

    async def _replay(
        self, publish: Callable[[tuple[RawTelemetryRecord, ...]], Awaitable[None]]
    ) -> None:
        from datetime import datetime

        recovered = False
        while payloads := await asyncio.to_thread(self.spool.peek, self.batch_size):
            records = []
            for payload in payloads:
                observed, signal, value, unit, record_id, sequence = payload.decode().split("\t")
                records.append(
                    RawTelemetryRecord(
                        datetime.fromisoformat(observed),
                        signal,
                        float(value),
                        unit,
                        record_id,
                        int(sequence) if sequence else None,
                    )
                )
            if not await self._publish_with_retry(tuple(records), publish):
                return
            # Cancellation, process failure, or failed publication leaves pending
            # records durable. A replay after an ambiguous success is idempotent.
            await asyncio.to_thread(self.spool.acknowledge, len(records))
            self.stats.replayed += len(records)
            self.replayed_metric.inc(len(records))
            self.published_metric.inc(len(records))
            self.stats.published += len(records)
            if not recovered:
                self.stats.reconnects += 1
                self.reconnect_metric.inc()
                recovered = True


class GatewayPublisher:
    def __init__(
        self, base_url: str, acquisition_id: UUID, token: str | None = None, timeout: float = 10
    ) -> None:
        self.base_url, self.acquisition_id = base_url.rstrip("/"), acquisition_id
        self.token = token or os.environ.get("VEHICLE_ACQUISITION_TOKEN", "")
        if len(self.token) < 32:
            raise ValueError(
                "VEHICLE_ACQUISITION_TOKEN is required and must not be passed on the command line"
            )
        self.timeout = timeout

    async def heartbeat(self, payload: dict[str, object]) -> None:
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 3)) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/acquisitions/{self.acquisition_id}/heartbeat",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json=payload,
                )
        except httpx.TransportError as exc:
            raise OSError("acquisition heartbeat transport unavailable") from exc
        if response.status_code >= 500 or response.status_code == 429:
            raise OSError("acquisition heartbeat dependency unavailable")
        if response.status_code != 200:
            raise ValueError(f"gateway rejected heartbeat ({response.status_code})")

    async def __call__(self, records: tuple[RawTelemetryRecord, ...]) -> None:
        body = {
            "schema_version": "1.0",
            "batch_id": str(uuid4()),
            "observations": [
                {
                    "message_id": str(uuid4()),
                    "observed_at": item.observed_at.isoformat(),
                    "sequence": item.sequence,
                    "signal": item.signal,
                    "value": item.value,
                    "unit": item.unit,
                    "source_record_id": item.source_record_id,
                }
                for item in records
            ],
        }
        carrier: dict[str, str] = {}
        propagate.inject(carrier)
        headers = {
            "Authorization": f"Bearer {self.token}",
            **{
                key: value for key, value in carrier.items() if key in {"traceparent", "tracestate"}
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/acquisitions/{self.acquisition_id}/batches",
                    headers=headers,
                    json=body,
                )
        except httpx.TransportError as exc:
            raise OSError("acquisition gateway transport unavailable") from exc
        if response.status_code >= 500 or response.status_code == 429:
            raise OSError("acquisition gateway unavailable")
        if response.status_code != 202:
            raise ValueError(f"gateway rejected acquisition batch ({response.status_code})")
