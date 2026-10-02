import asyncio
import csv
import io
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from vehicle_platform.acquisition.domain import DeviceCapabilities, SamplingPlanItem, Support
from vehicle_platform.telemetry.domain import RawTelemetryRecord


class VehicleDataAdapter(Protocol):
    """Read-only adapter contract. Deliberately has no command/write operation."""

    async def connect(self) -> None: ...
    async def capabilities(self) -> DeviceCapabilities: ...
    def read(self, plan: tuple[SamplingPlanItem, ...]) -> AsyncIterator[RawTelemetryRecord]: ...
    async def close(self) -> None: ...


class SyntheticLiveAdapter:
    def __init__(self, scenario: str = "normal", samples: int = 120, speed: float = 0) -> None:
        self.scenario, self.samples, self.speed, self.connected = scenario, samples, speed, False
        self.reconnects = 0

    async def connect(self) -> None:
        self.connected = True

    async def capabilities(self) -> DeviceCapabilities:
        signals = {
            key: Support.SUPPORTED
            for key in (
                "engine.rpm",
                "vehicle.speed",
                "engine.throttle_position",
                "engine.boost_pressure",
                "engine.intake_air_temperature",
                "engine.oil_temperature",
                "engine.coolant_temperature",
                "fuel.high_pressure",
            )
        }
        if self.scenario == "missing_recommended":
            signals["engine.boost_pressure"] = Support.UNSUPPORTED
        return DeviceCapabilities("synthetic-live-v1", signals, 70)

    async def read(self, plan: tuple[SamplingPlanItem, ...]) -> AsyncIterator[RawTelemetryRecord]:
        start = datetime.now(UTC)
        selected = {item.signal for item in plan}
        held: RawTelemetryRecord | None = None
        for index in range(self.samples):
            if self.scenario == "disconnect" and index == self.samples // 2:
                self.connected = False
                await asyncio.sleep(0)
                self.connected = True
                self.reconnects += 1
            throttle = 88.0 if 20 <= index < 80 else 12.0
            rpm = 900 + (index - 20) * 70 if 20 <= index < 80 else 850
            speed = max(0, (index - 20) * 0.45) if index >= 20 else 0
            boost = max(-40000, (throttle - 25) * 3000)
            if self.scenario == "boost_drop" and 50 <= index < 65:
                boost *= 0.35
            values = {
                "engine.rpm": (rpm, "rpm"),
                "vehicle.speed": (speed, "m/s"),
                "engine.throttle_position": (throttle, "%"),
                "engine.boost_pressure": (boost, "Pa"),
                "engine.intake_air_temperature": (296 + index * 0.08, "K"),
                "engine.oil_temperature": (350, "K"),
                "engine.coolant_temperature": (360, "K"),
                "fuel.high_pressure": (12_000_000, "Pa"),
            }
            for offset, (signal, (value, unit)) in enumerate(values.items()):
                if signal not in selected:
                    continue
                record = RawTelemetryRecord(
                    start + timedelta(milliseconds=index * 100),
                    signal,
                    value,
                    unit,
                    f"synthetic:{index}:{signal}",
                    index * len(values) + offset,
                )
                if self.scenario == "out_of_order" and index == 20 and held is None:
                    held = record
                    continue
                yield record
                if held is not None and index == 21:
                    yield held
                    held = None
                if self.scenario == "duplicate" and index == 30:
                    yield record
            if self.speed:
                await asyncio.sleep(0.1 / self.speed)

    async def close(self) -> None:
        self.connected = False


class ReplayAdapter:
    def __init__(self, content: bytes, speed: float = 1) -> None:
        self.rows = tuple(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
        self.speed = speed

    async def connect(self) -> None:
        pass

    async def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            "csv-replay-v1", {row["signal"]: Support.SUPPORTED for row in self.rows}, 1000, False
        )

    async def read(self, plan: tuple[SamplingPlanItem, ...]) -> AsyncIterator[RawTelemetryRecord]:
        selected = {item.signal for item in plan}
        previous: datetime | None = None
        for index, row in enumerate(self.rows):
            if row["signal"] not in selected:
                continue
            observed = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00")).astimezone(
                UTC
            )
            if previous and self.speed > 0:
                await asyncio.sleep(min((observed - previous).total_seconds() / self.speed, 1))
            previous = observed
            yield RawTelemetryRecord(
                observed,
                row["signal"],
                float(row["value"]),
                row["unit"],
                row.get("record_id", str(index)),
                index,
            )

    async def close(self) -> None:
        pass


class ElmTransport(Protocol):
    async def request(self, command: str, request_timeout: float) -> str: ...
    async def close(self) -> None: ...


@dataclass(frozen=True)
class StandardPid:
    command: str
    signal: str
    unit: str
    decode: Callable[[bytes], float]


PIDS = (
    StandardPid("010C", "engine.rpm", "rpm", lambda b: (b[0] * 256 + b[1]) / 4),
    StandardPid("010D", "vehicle.speed", "m/s", lambda b: b[0] / 3.6),
    StandardPid("0111", "engine.throttle_position", "%", lambda b: b[0] * 100 / 255),
    StandardPid("010F", "engine.intake_air_temperature", "K", lambda b: b[0] - 40 + 273.15),
    StandardPid("0105", "engine.coolant_temperature", "K", lambda b: b[0] - 40 + 273.15),
)


class Elm327Adapter:
    """Generic standard-mode OBD-II reader; no proprietary or write commands."""

    def __init__(self, transport: ElmTransport, timeout: float = 1.0) -> None:
        self.transport, self.timeout, self.supported = transport, timeout, set[str]()

    async def connect(self) -> None:
        for command in ("ATZ", "ATE0", "ATL0", "ATS0"):
            await self.transport.request(command, self.timeout)
        response = await self.transport.request("0100", self.timeout)
        data = self._bytes(response, "4100")
        mask = int.from_bytes(data[:4], "big") if len(data) >= 4 else 0
        self.supported = {
            pid.signal for pid in PIDS if mask & (1 << (32 - int(pid.command[2:], 16)))
        }

    @staticmethod
    def _bytes(response: str, prefix: str) -> bytes:
        clean = "".join(response.upper().replace(">", "").split())
        if not clean.startswith(prefix):
            return b""
        try:
            return bytes.fromhex(clean[len(prefix) :])
        except ValueError:
            return b""

    async def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            "elm327-standard-read-only-v1",
            {
                pid.signal: (
                    Support.SUPPORTED if pid.signal in self.supported else Support.UNSUPPORTED
                )
                for pid in PIDS
            },
            12,
        )

    async def read(self, plan: tuple[SamplingPlanItem, ...]) -> AsyncIterator[RawTelemetryRecord]:
        selected = [
            pid
            for pid in PIDS
            if pid.signal in self.supported and any(item.signal == pid.signal for item in plan)
        ]
        sequence = 0
        while selected:
            for pid in selected:
                response = await self.transport.request(pid.command, self.timeout)
                values = self._bytes(response, "41" + pid.command[2:])
                if values:
                    yield RawTelemetryRecord(
                        datetime.now(UTC),
                        pid.signal,
                        pid.decode(values),
                        pid.unit,
                        f"elm:{sequence}",
                        sequence,
                    )
                    sequence += 1

    async def close(self) -> None:
        await self.transport.close()
