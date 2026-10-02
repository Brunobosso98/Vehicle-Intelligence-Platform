import asyncio
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID, uuid4

import httpx

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
        if not 1 <= batch_size <= 500 or queue_size < batch_size or not 0 <= retries <= 10:
            raise ValueError("invalid collector bounds")
        self.spool, self.batch_size, self.retries = spool, batch_size, retries
        self.queue: asyncio.Queue[RawTelemetryRecord] = asyncio.Queue(maxsize=queue_size)
        self.stats = CollectorStats()

    async def run(
        self,
        adapter: VehicleDataAdapter,
        plan: tuple[SamplingPlanItem, ...],
        publish: Callable[[tuple[RawTelemetryRecord, ...]], Awaitable[None]],
    ) -> CollectorStats:
        await adapter.connect()
        try:
            await self._replay(publish)
            batch: list[RawTelemetryRecord] = []
            async for record in adapter.read(plan):
                self.stats.produced += 1
                await self.queue.put(record)  # bounded backpressure
                batch.append(await self.queue.get())
                self.queue.task_done()
                if len(batch) >= self.batch_size:
                    await self._send(tuple(batch), publish)
                    batch.clear()
            if batch:
                await self._send(tuple(batch), publish)
        finally:
            await adapter.close()
        self.stats.dropped = self.spool.dropped
        return self.stats

    async def _send(
        self,
        batch: tuple[RawTelemetryRecord, ...],
        publish: Callable[[tuple[RawTelemetryRecord, ...]], Awaitable[None]],
    ) -> None:
        for attempt in range(self.retries + 1):
            try:
                await publish(batch)
                self.stats.published += len(batch)
                return
            except (OSError, TimeoutError):
                if attempt < self.retries:
                    await asyncio.sleep(min(0.1 * 2**attempt, 1))
        for record in batch:
            payload = f"{record.observed_at.isoformat()}\t{record.signal}\t{record.value}\t{record.unit}\t{record.source_record_id}\t{record.sequence if record.sequence is not None else ''}".encode()
            self.spool.append(payload)

    async def _replay(
        self, publish: Callable[[tuple[RawTelemetryRecord, ...]], Awaitable[None]]
    ) -> None:
        from datetime import datetime

        records = []
        for payload in self.spool.drain():
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
        for offset in range(0, len(records), self.batch_size):
            batch = tuple(records[offset : offset + self.batch_size])
            try:
                await publish(batch)
                self.stats.replayed += len(batch)
                self.stats.published += len(batch)
            except (OSError, TimeoutError):
                for record in records[offset:]:
                    self.spool.append(
                        f"{record.observed_at.isoformat()}\t{record.signal}\t{record.value}\t{record.unit}\t{record.source_record_id}\t{record.sequence if record.sequence is not None else ''}".encode()
                    )
                return


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
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/acquisitions/{self.acquisition_id}/batches",
                headers={"Authorization": f"Bearer {self.token}"},
                json=body,
            )
        if response.status_code >= 500:
            raise OSError("acquisition gateway unavailable")
        if response.status_code != 202:
            raise ValueError(f"gateway rejected acquisition batch ({response.status_code})")
