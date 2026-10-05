import asyncio
import csv
import io
import math
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import Protocol

from vehicle_platform.acquisition.domain import DeviceCapabilities, SamplingPlanItem, Support
from vehicle_platform.telemetry.domain import (
    SIGNAL_BY_ALIAS,
    RawTelemetryRecord,
    normalize_value,
    parse_timestamp,
)


class VehicleDataAdapter(Protocol):
    """Read-only adapter contract. Deliberately has no command/write operation."""

    async def connect(self) -> None: ...
    async def capabilities(self) -> DeviceCapabilities: ...
    def read(self, plan: tuple[SamplingPlanItem, ...]) -> AsyncIterator[RawTelemetryRecord]: ...
    async def close(self) -> None: ...


class SyntheticLiveAdapter:
    def __init__(self, scenario: str = "normal", samples: int = 120, speed: float = 0) -> None:
        allowed = {
            "normal",
            "cruise",
            "boost_drop",
            "thermal",
            "fuel_pressure_drop",
            "jitter",
            "dropout",
            "disconnect",
            "out_of_order",
            "duplicate",
            "missing_recommended",
        }
        if scenario not in allowed or samples < 1 or not math.isfinite(speed) or speed < 0:
            raise ValueError("invalid synthetic scenario, sample count or speed")
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
        rates = {item.signal: item.estimated_hz for item in plan if item.estimated_hz > 0}
        selected = set(rates)
        next_due = dict.fromkeys(selected, 0.0)
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
            if self.scenario in {"boost_drop", "fuel_pressure_drop"}:
                # Three independently scripted six-second high-load windows at
                # 10 Hz in the 300-frame acceptance fixture. The final window
                # has a lower observed boost level; no component cause is implied.
                window = next(
                    (begin for begin in (20, 100, 180) if begin <= index < begin + 60), None
                )
                throttle = 88.0 if window is not None else 12.0
                rpm = 2200 + (index - window) * 70 if window is not None else 850
                speed = 18 + (index - window) * 0.45 if window is not None else 0
                boost = (
                    66150
                    if window == 180 and self.scenario == "boost_drop"
                    else 189000
                    if window is not None
                    else -39000
                )
            if self.scenario == "cruise":
                rpm, speed, throttle, boost = 1800, 18, 20, -15000
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
            if self.scenario == "thermal":
                values["engine.intake_air_temperature"] = (370, "K")
                values["engine.oil_temperature"] = (430, "K")
                values["engine.coolant_temperature"] = (405, "K")
            if self.scenario == "fuel_pressure_drop" and 200 <= index < 240:
                values["fuel.high_pressure"] = (5_000_000, "Pa")
            for offset, (signal, (value, unit)) in enumerate(values.items()):
                if (
                    signal not in selected
                    or index / 10 + 1e-9 < next_due[signal]
                    or (
                        self.scenario == "dropout"
                        and signal == "engine.boost_pressure"
                        and 25 <= index < 50
                    )
                ):
                    continue
                next_due[signal] += 1 / rates[signal]
                record = RawTelemetryRecord(
                    start
                    + timedelta(
                        milliseconds=index * 100
                        + ((index % 3 - 1) * 10 if self.scenario == "jitter" else 0)
                    ),
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
        if len(content) > 10_000_000 or not math.isfinite(speed) or speed < 0:
            raise ValueError("invalid replay size or speed")
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not {"signal", "value", "unit", "record_id"} <= set(
            headers
        ):
            raise ValueError("invalid replay columns")
        time_key = "timestamp" if "timestamp" in headers else "observed_at"
        if time_key not in headers:
            raise ValueError("replay requires an aware observation timestamp")
        records = []
        for index, row in enumerate(reader):
            if None in row or any(value is None for value in row.values()):
                raise ValueError("replay row shape does not match headers")
            definition = SIGNAL_BY_ALIAS.get(row["signal"].lower())
            if definition is None:
                continue
            value, _quality = normalize_value(float(row["value"]), row["unit"], definition)
            observed = parse_timestamp(row[time_key])
            if row["record_id"].startswith(("=", "+", "-", "@")):
                raise ValueError("formula-prefixed replay identity")
            records.append(
                RawTelemetryRecord(
                    observed,
                    definition.key,
                    value,
                    definition.unit,
                    row["record_id"],
                    int(row["sequence"]) if row.get("sequence") else index,
                )
            )
        self.records = tuple(records)
        self.speed = speed

    async def connect(self) -> None:
        pass

    async def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            "csv-replay-v1", {row.signal: Support.SUPPORTED for row in self.records}, 1000, False
        )

    async def read(self, plan: tuple[SamplingPlanItem, ...]) -> AsyncIterator[RawTelemetryRecord]:
        selected = {item.signal for item in plan}
        previous: datetime | None = None
        for record in self.records:
            if record.signal not in selected:
                continue
            if previous and self.speed > 0:
                await asyncio.sleep(
                    max(0, min((record.observed_at - previous).total_seconds() / self.speed, 1))
                )
            previous = record.observed_at
            yield record

    async def close(self) -> None:
        pass


class ElmTransport(Protocol):
    async def request(self, command: str, request_timeout: float) -> str: ...
    async def close(self) -> None: ...


class ElmTcpTransport:
    """Concrete ELM327 TCP/RFCOMM bridge transport with a strict read-only command allowlist."""

    def __init__(self, host: str, port: int = 35000) -> None:
        self.host, self.port = host, port
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None

    async def request(self, command: str, request_timeout: float) -> str:
        normalized = command.strip().upper()
        allowed = {"ATZ", "ATE0", "ATL0", "ATS0", "0100", *(pid.command for pid in PIDS)}
        if normalized not in allowed:
            raise ValueError("only ELM setup and standard OBD-II Mode 01 reads are permitted")
        if self.writer is None or self.reader is None:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=request_timeout
            )
        reader, writer = self.reader, self.writer
        if reader is None or writer is None:
            raise ConnectionError("ELM transport connection unavailable")
        writer.write((normalized + "\r").encode("ascii"))
        await writer.drain()
        response = await asyncio.wait_for(reader.readuntil(b">"), timeout=request_timeout)
        return response.decode("ascii", errors="replace")

    async def close(self) -> None:
        if self.writer is not None:
            self.writer.close()
            await self.writer.wait_closed()
        self.reader = None
        self.writer = None


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
        self.sequence = 0
        self.reconnects = 0
        self.unavailable = set[str]()

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
                    Support.UNAVAILABLE
                    if pid.signal in self.unavailable
                    else Support.SUPPORTED
                    if pid.signal in self.supported
                    else Support.UNSUPPORTED
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
        rates = {item.signal: item.estimated_hz for item in plan}
        due = {pid.signal: monotonic() for pid in selected if rates[pid.signal] > 0}
        failures = 0
        while due:
            key = min(due, key=lambda signal: due[signal])
            pid = next(item for item in selected if item.signal == key)
            await asyncio.sleep(max(0, due[key] - monotonic()))
            try:
                response = await self.transport.request(pid.command, self.timeout)
                failures = 0
            except (OSError, TimeoutError):
                failures += 1
                if failures > 3:
                    raise ConnectionError("read-only adapter retries exhausted") from None
                await self.transport.close()
                await asyncio.sleep(min(0.1 * 2 ** (failures - 1), 1))
                await self.connect()
                self.reconnects += 1
                continue
            due[key] = monotonic() + 1 / rates[key]
            values = self._bytes(response, "41" + pid.command[2:])
            required_bytes = 2 if pid.command == "010C" else 1
            if len(values) >= required_bytes:
                self.unavailable.discard(key)
                yield RawTelemetryRecord(
                    datetime.now(UTC),
                    pid.signal,
                    pid.decode(values),
                    pid.unit,
                    f"elm:{self.sequence}",
                    self.sequence,
                )
                self.sequence += 1
            else:
                self.unavailable.add(key)

    async def close(self) -> None:
        await self.transport.close()
