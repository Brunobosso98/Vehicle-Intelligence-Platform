from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest

from vehicle_platform.acquisition.adapters import (
    Elm327Adapter,
    ElmTcpTransport,
    ReplayAdapter,
    SyntheticLiveAdapter,
)
from vehicle_platform.acquisition.collector import AcquisitionCollector, GatewayPublisher
from vehicle_platform.acquisition.domain import DeviceCapabilities, Readiness, Support, preflight
from vehicle_platform.acquisition.quality import assess_dataset, measure_signal_quality
from vehicle_platform.acquisition.recipes import BY_KEY, BY_OBJECTIVE, RECIPES
from vehicle_platform.acquisition.stream import BoundedSpool, RawTelemetryMessage


def test_provisional_window_is_event_time_bounded_without_discarding_canonical_input() -> None:
    from vehicle_platform.acquisition.worker import StreamConsumer
    from vehicle_platform.analysis.domain import Observation
    from vehicle_platform.core.config import Settings

    worker = StreamConsumer(Mock(), Settings())
    acquisition_id = uuid4()
    newest = datetime(2026, 1, 1, tzinfo=UTC)
    retained = [
        Observation(newest - timedelta(days=365), "engine.rpm", 900),
        Observation(newest, "engine.rpm", 3000),
        Observation(newest - timedelta(seconds=60), "engine.rpm", 2000),
        Observation(newest - timedelta(seconds=60, milliseconds=1), "engine.rpm", 1900),
    ]
    worker.windows[acquisition_id].extend(retained)
    assert worker._live_window(acquisition_id) == retained[1:3]
    assert list(worker.windows[acquisition_id]) == retained
    assert worker._live_window(uuid4()) == []


def capabilities(*missing: str, throughput: float = 70) -> DeviceCapabilities:
    names = {r.signal for recipe in RECIPES for r in recipe.requirements}
    return DeviceCapabilities(
        "test",
        {name: Support.UNSUPPORTED if name in missing else Support.SUPPORTED for name in names},
        throughput,
    )


def test_every_recipe_is_versioned_stable_and_has_rationale() -> None:
    assert len(BY_OBJECTIVE) == 6
    for recipe in RECIPES:
        assert recipe.version == 1 and len(recipe.configuration_hash) == 64
        assert all(
            item.reason and item.minimum_hz <= item.preferred_hz for item in recipe.requirements
        )


def test_preflight_ready_degraded_and_blocked() -> None:
    recipe = BY_KEY["performance-pull"]
    assert preflight(recipe, capabilities()).readiness is Readiness.READY
    degraded = preflight(recipe, capabilities("engine.boost_pressure"))
    assert degraded.readiness is Readiness.DEGRADED
    assert "boost_analysis" in degraded.unavailable_capabilities
    blocked = preflight(recipe, capabilities("engine.rpm"))
    assert blocked.readiness is Readiness.BLOCKED
    assert blocked.required_missing == ("engine.rpm",)


def test_sampling_budget_protects_required_signals() -> None:
    result = preflight(BY_KEY["performance-pull"], capabilities(throughput=18))
    required = {item.signal: item for item in result.sampling_plan}
    assert required["engine.rpm"].estimated_hz == 10
    assert required["vehicle.speed"].estimated_hz == 3
    assert required["engine.throttle_position"].estimated_hz == 5
    assert result.readiness is Readiness.DEGRADED
    assert "boost_analysis" in result.unavailable_capabilities
    assert "boost_analysis" not in result.expected_capabilities
    assert sum(item.estimated_hz for item in result.sampling_plan) <= 18


@pytest.mark.parametrize(
    "scenario",
    ["normal", "boost_drop", "disconnect", "out_of_order", "duplicate", "missing_recommended"],
)
async def test_golden_synthetic_scenarios(scenario: str) -> None:
    adapter = SyntheticLiveAdapter(scenario, samples=35)
    await adapter.connect()
    result = preflight(BY_KEY["performance-pull"], await adapter.capabilities())
    records = [record async for record in adapter.read(result.sampling_plan)]
    await adapter.close()
    assert records
    if scenario == "disconnect":
        assert adapter.reconnects == 1
    if scenario == "duplicate":
        identities = [item.source_record_id for item in records]
        assert len(identities) > len(set(identities))
    if scenario == "missing_recommended":
        assert result.readiness is Readiness.DEGRADED


async def test_replay_is_deterministic() -> None:
    content = (
        b"observed_at,signal,value,unit,record_id\n"
        b"2026-01-01T00:00:00Z,engine.rpm,1000,rpm,1\n"
        b"2026-01-01T00:00:01Z,engine.rpm,1100,rpm,2\n"
    )
    adapter = ReplayAdapter(content, speed=1000)
    await adapter.connect()
    plan = preflight(BY_KEY["general-health"], await adapter.capabilities()).sampling_plan
    assert [r.value async for r in adapter.read(plan)] == [1000, 1100]
    await adapter.close()


async def test_replay_skips_unplanned_signal_without_sleep() -> None:
    content = (
        b"observed_at,signal,value,unit,record_id\n"
        b"2026-01-01T00:00:00Z,unknown,1,count,1\n"
        b"2026-01-01T00:00:01Z,engine.rpm,1100,rpm,2\n"
    )
    adapter = ReplayAdapter(content, speed=0)
    await adapter.connect()
    plan = preflight(BY_KEY["general-health"], capabilities()).sampling_plan
    assert [r.signal async for r in adapter.read(plan)] == ["engine.rpm"]


class FakeElm:
    def __init__(self) -> None:
        self.commands: list[str] = []

    async def request(self, command: str, request_timeout: float) -> str:
        self.commands.append(command)
        return {"0100": "41 00 00 18 00 00", "010C": "41 0C 1F 40", "010D": "41 0D 64"}.get(
            command, "OK"
        )

    async def close(self) -> None:
        pass


async def test_elm327_only_uses_allowlisted_read_commands() -> None:
    transport = FakeElm()
    adapter = Elm327Adapter(transport)
    await adapter.connect()
    capability = await adapter.capabilities()
    assert all(command.startswith(("AT", "01")) for command in transport.commands)
    assert not hasattr(adapter, "write") and capability.discovery_supported
    plan = preflight(BY_KEY["general-health"], capability).sampling_plan
    source = adapter.read(plan)
    assert (await anext(source)).signal == "engine.rpm"
    await source.aclose()
    await adapter.close()
    with pytest.raises(ValueError, match="Mode 01"):
        await ElmTcpTransport("127.0.0.1").request("04", 0.1)


async def test_elm_tcp_transport_connects_reads_reuses_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Reader:
        async def readuntil(self, separator: bytes) -> bytes:
            assert separator == b">"
            return b"41 0C 1F 40>"

    class Writer:
        def __init__(self) -> None:
            self.writes: list[bytes] = []
            self.closed = False

        def write(self, value: bytes) -> None:
            self.writes.append(value)

        async def drain(self) -> None:
            return None

        def close(self) -> None:
            self.closed = True

        async def wait_closed(self) -> None:
            return None

    writer = Writer()

    async def connect(host: str, port: int):
        assert host == "adapter" and port == 35000
        return Reader(), writer

    monkeypatch.setattr("vehicle_platform.acquisition.adapters.asyncio.open_connection", connect)
    transport = ElmTcpTransport("adapter")
    assert await transport.request("010C", 1) == "41 0C 1F 40>"
    assert await transport.request("ATE0", 1) == "41 0C 1F 40>"
    assert writer.writes == [b"010C\r", b"ATE0\r"]
    await transport.close()
    assert writer.closed and transport.writer is None


def test_bounded_spool_replays_and_reports_overflow(tmp_path: Path) -> None:
    spool = BoundedSpool(tmp_path / "spool", 12)
    assert spool.occupancy_bytes == 0 and spool.drain() == ()
    assert spool.append(b"one") and spool.append(b"two")
    assert not spool.append(b"too-large") and spool.dropped == 1
    assert spool.drain() == (b"one", b"two") and spool.occupancy_bytes == 0


def test_stream_contract_and_dataset_capability() -> None:
    record = __import__(
        "vehicle_platform.telemetry.domain", fromlist=["RawTelemetryRecord"]
    ).RawTelemetryRecord(datetime.now(UTC), "engine.rpm", 1000, "rpm", "one", 1)
    message = RawTelemetryMessage.from_record(
        __import__("uuid").uuid4(), "safe-source", "vehicle-id", record
    )
    assert b'"schema_version":"1.0"' in message.encode() and b"token" not in message.encode()
    start = datetime.now(UTC)
    qualities = tuple(
        measure_signal_quality(
            signal, tuple(start + timedelta(milliseconds=100 * i) for i in range(20)), 10
        )
        for signal in ("engine.rpm", "vehicle.speed", "engine.throttle_position")
    )
    report = {item.key: item for item in assess_dataset(qualities, 2)}
    assert not report["ignition_correction_analysis"].supported
    assert "verified" in report["ignition_correction_analysis"].unavailable_reason
    assert report["pull_detection"].supported and not report["boost_analysis"].supported
    empty = measure_signal_quality("engine.rpm", (start,), 10)
    assert empty.stale_ratio == 1 and empty.missing_ratio == 1


async def test_collector_retries_spools_and_replays_without_loss(tmp_path: Path) -> None:
    spool = BoundedSpool(tmp_path / "collector-spool", 100_000)
    adapter = SyntheticLiveAdapter(samples=3)
    plan = preflight(BY_KEY["performance-pull"], await adapter.capabilities()).sampling_plan
    failures = 4

    async def unavailable(batch: tuple[object, ...]) -> None:
        nonlocal failures
        failures -= 1
        raise OSError("network unavailable")

    first = await AcquisitionCollector(spool, batch_size=10, retries=3).run(
        adapter, plan, unavailable
    )
    assert first.produced > 0 and first.published == 0 and spool.occupancy_bytes > 0
    accepted: list[object] = []

    async def available(batch: tuple[object, ...]) -> None:
        accepted.extend(batch)

    second = await AcquisitionCollector(spool, batch_size=10).run(
        SyntheticLiveAdapter(samples=1), plan, available
    )
    assert second.replayed == first.produced
    assert second.published == len(accepted)
    assert spool.occupancy_bytes == 0


def test_collector_rejects_unbounded_configuration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="bounds"):
        AcquisitionCollector(BoundedSpool(tmp_path / "spool"), batch_size=501)
    with pytest.raises(ValueError, match="TOKEN"):
        GatewayPublisher("http://gateway", __import__("uuid").uuid4(), token="short")


@pytest.mark.parametrize(
    "status,error", [(202, None), (503, OSError), (429, OSError), (422, ValueError)]
)
async def test_gateway_publisher_classifies_responses(
    monkeypatch: pytest.MonkeyPatch, status: int, error: type[Exception] | None
) -> None:
    class Response:
        status_code = status

    class Client:
        def __init__(self, timeout: float) -> None:
            assert timeout == 10

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> Response:
            assert "Authorization" in kwargs["headers"]  # type: ignore[operator]
            return Response()

    monkeypatch.setattr("vehicle_platform.acquisition.collector.httpx.AsyncClient", Client)
    publisher = GatewayPublisher("http://gateway/", __import__("uuid").uuid4(), "x" * 43)
    record = __import__(
        "vehicle_platform.telemetry.domain", fromlist=["RawTelemetryRecord"]
    ).RawTelemetryRecord(datetime.now(UTC), "engine.rpm", 1000, "rpm", "one", 1)
    if error:
        with pytest.raises(error):
            await publisher((record,))
    else:
        await publisher((record,))


@pytest.mark.parametrize("driver", ["sqlalchemy", "asyncpg"])
def test_consumer_database_failure_exits_without_sql_inputs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], driver: str
) -> None:
    import asyncio
    import json
    import runpy
    from collections.abc import Coroutine

    from asyncpg import CannotConnectNowError
    from sqlalchemy.exc import SQLAlchemyError

    from vehicle_platform.acquisition import worker

    def fail(coroutine: Coroutine[None, None, None]) -> None:
        coroutine.close()
        error = SQLAlchemyError if driver == "sqlalchemy" else CannotConnectNowError
        raise error("private database URL and telemetry inputs")

    monkeypatch.setattr(asyncio, "run", fail)
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(Path(worker.__file__)), run_name="__main__")
    assert result.value.code == 1
    output = capsys.readouterr()
    event = json.loads(output.err)
    assert event["event"] == "stream.persistence_failed"
    assert event["error_category"] == "database_error"
    assert "private" not in output.err and not output.out


async def test_spool_acknowledges_only_after_publish_and_recovers_in_same_run(
    tmp_path: Path,
) -> None:
    import asyncio

    spool = BoundedSpool(tmp_path / "pending", 100_000)
    collector = AcquisitionCollector(spool, batch_size=1, retries=0)
    from vehicle_platform.telemetry.domain import RawTelemetryRecord

    record = RawTelemetryRecord(datetime.now(UTC), "engine.rpm", 1000, "rpm", "one", 1)
    received = []

    async def offline(batch):
        raise OSError("offline")

    await collector._send((record,), offline)
    assert spool.occupancy_bytes > 0

    async def cancelled(batch):
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await collector._replay(cancelled)
    # A new collector sees the original durable record after interrupted replay.
    restored = BoundedSpool(tmp_path / "pending", 100_000)
    assert restored.peek(1)

    async def online(batch):
        received.extend(batch)

    await collector._send((record,), online)
    assert received == [record, record]  # ambiguous duplicate delivery keeps stable source identity
    assert spool.occupancy_bytes == 0
    assert collector.stats.replayed == 1


def test_spool_atomic_acknowledgement_preserves_remaining_records(tmp_path: Path) -> None:
    spool = BoundedSpool(tmp_path / "pending", 20)
    assert spool.peek(1) == ()
    spool.acknowledge(1)
    assert spool.append(b"one") and spool.append(b"two")
    spool.acknowledge(1)
    assert spool.peek(1) == (b"two",)
    assert spool.path.stat().st_mode & 0o777 == 0o600
    spool.path.write_bytes(b"x" * 21)
    with pytest.raises(ValueError, match="capacity"):
        spool.peek(1)
    with pytest.raises(ValueError, match="capacity"):
        spool.acknowledge(1)


@pytest.mark.parametrize("exhausted", [False, True])
async def test_spool_replay_retries_and_only_acknowledges_success(
    tmp_path: Path, exhausted
) -> None:
    spool = BoundedSpool(tmp_path / "retry-replay")
    collector = AcquisitionCollector(spool, batch_size=1, retries=1)
    from vehicle_platform.telemetry.domain import RawTelemetryRecord

    record = RawTelemetryRecord(datetime.now(UTC), "engine.rpm", 900, "rpm", "one", 1)
    await collector._spool((record,))
    attempts = []

    async def publish(batch):
        attempts.append(batch)
        if exhausted or len(attempts) == 1:
            raise OSError("dependency unavailable")

    await collector._replay(publish)
    assert attempts == [(record,), (record,)]
    assert bool(spool.occupancy_bytes) is exhausted
    assert collector.stats.replayed == (0 if exhausted else 1)
    assert collector.stats.dropped == 0


def test_spool_partial_os_writes_preserve_complete_records(tmp_path: Path, monkeypatch) -> None:
    import os

    original = os.write
    monkeypatch.setattr(os, "write", lambda fd, payload: original(fd, payload[:3]))
    spool = BoundedSpool(tmp_path / "partial-writes")
    assert spool.append(b"complete-record")
    assert spool.peek(1) == (b"complete-record",)


def test_spool_large_file_replay_keeps_memory_bounded_and_records_intact(tmp_path: Path) -> None:
    import tracemalloc

    path = tmp_path / "large-spool"
    record = b"x" * 4096
    with path.open("wb") as output:
        for _ in range(2000):
            output.write(record + b"\n")
    spool = BoundedSpool(path)
    tracemalloc.start()
    try:
        assert spool.peek(2) == (record, record)
        spool.acknowledge(1)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert peak < 1_000_000
    assert spool.occupancy_bytes == 1999 * (len(record) + 1)
    assert spool.peek(1) == (record,)
    assert path.stat().st_mode & 0o777 == 0o600
    for operation in (spool.peek, spool.acknowledge):
        with pytest.raises(ValueError, match="nonnegative"):
            operation(-1)
    oversized = BoundedSpool(tmp_path / "oversized-record")
    assert oversized.append(b"x" * 65537) is False
    assert oversized.dropped == 1 and oversized.occupancy_bytes == 0
    corrupted = b"x" * 65538 + b"\n"
    oversized.path.write_bytes(corrupted)
    for operation in (oversized.peek, oversized.acknowledge):
        with pytest.raises(ValueError, match="bounded message"):
            operation(1)
        assert oversized.path.read_bytes() == corrupted


async def test_gateway_transport_errors_enter_retry_spool_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import uuid4

    import httpx

    from vehicle_platform.telemetry.domain import RawTelemetryRecord

    class Client:
        def __init__(self, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr("vehicle_platform.acquisition.collector.httpx.AsyncClient", Client)
    with pytest.raises(OSError, match="transport unavailable"):
        await GatewayPublisher("http://gateway", uuid4(), "x" * 43)(
            (RawTelemetryRecord(datetime.now(UTC), "engine.rpm", 1000, "rpm", "one", 1),)
        )


def test_spool_failed_atomic_ack_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spool = BoundedSpool(tmp_path / "pending", 20)
    assert spool.append(b"one")

    def fail(*args: object) -> None:
        raise OSError("filesystem interruption")

    monkeypatch.setattr("vehicle_platform.acquisition.stream.os.replace", fail)
    with pytest.raises(OSError):
        spool.acknowledge(1)
    assert spool.peek(1) == (b"one",)
    assert list(tmp_path.iterdir()) == [spool.path]


def test_preflight_blocks_supported_signals_with_inadequate_poll_budget() -> None:
    from vehicle_platform.acquisition.domain import DeviceCapabilities, Support, preflight
    from vehicle_platform.acquisition.recipes import BY_KEY

    recipe = BY_KEY["performance-pull"]
    signals = {r.signal: Support.SUPPORTED for r in recipe.requirements}
    result = preflight(recipe, DeviceCapabilities("slow", signals, 0))
    assert result.readiness == "blocked"
    assert any("sampling rate" in warning for warning in result.warnings)
    assert all(item.estimated_hz == 0 for item in result.sampling_plan)
    for budget in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            DeviceCapabilities("invalid", signals, budget)


def test_stream_contract_requires_aware_finite_observations() -> None:
    from uuid import uuid4

    from pydantic import ValidationError

    from vehicle_platform.api.domain_contracts import StreamObservation

    fields = {
        "message_id": uuid4(),
        "sequence": 1,
        "signal": "engine.rpm",
        "unit": "rpm",
        "source_record_id": "one",
    }
    with pytest.raises(ValidationError, match="timezone"):
        StreamObservation(**fields, observed_at=datetime(2026, 1, 1), value=1000)
    with pytest.raises(ValidationError):
        StreamObservation(**fields, observed_at=datetime.now(UTC), value=float("nan"))
    assert StreamObservation(**fields, observed_at=datetime.now(UTC), value=1000).value == 1000


async def test_collector_interruption_preserves_unpublished_partial_batch(tmp_path: Path) -> None:
    import asyncio

    class InterruptedAdapter(SyntheticLiveAdapter):
        async def read(self, plan):
            yield RawTelemetryRecord(
                datetime(2026, 1, 1, tzinfo=UTC), "engine.rpm", 900, "rpm", "partial", 1
            )
            raise asyncio.CancelledError

    from vehicle_platform.telemetry.domain import RawTelemetryRecord

    spool = BoundedSpool(tmp_path / "partial")
    collector = AcquisitionCollector(spool, batch_size=10)

    async def publish(records):
        pytest.fail("partial batch should be preserved on interruption")

    with pytest.raises(asyncio.CancelledError):
        await collector.run(InterruptedAdapter(), (), publish)
    assert len(spool.peek(10)) == 1
    assert b"partial" in spool.peek(10)[0]


async def test_elm_recovers_timeout_without_reusing_sequence(monkeypatch) -> None:
    import asyncio

    class IntermittentElm(FakeElm):
        rpm_calls = 0

        async def request(self, command, request_timeout):
            if command == "010C":
                self.rpm_calls += 1
                if self.rpm_calls == 2:
                    raise TimeoutError
            return await super().request(command, request_timeout)

    async def immediate(_delay):
        return None

    monkeypatch.setattr(asyncio, "sleep", immediate)
    transport = IntermittentElm()
    adapter = Elm327Adapter(transport)
    await adapter.connect()
    plan = preflight(BY_KEY["performance-pull"], capabilities()).sampling_plan
    records = []
    async for record in adapter.read(plan):
        records.append(record)
        if len(records) == 4:
            break
    await adapter.close()
    assert adapter.reconnects == 1
    assert [r.sequence for r in records] == [0, 1, 2, 3]
    assert len({r.source_record_id for r in records}) == 4
    assert all(
        command.startswith("01") or command in {"ATZ", "ATE0", "ATL0", "ATS0"}
        for command in transport.commands
    )


def test_replay_normalizes_aliases_and_rejects_naive_nonfinite_or_bad_shape() -> None:
    from vehicle_platform.telemetry.domain import NormalizationError

    valid = (
        b"timestamp,signal,value,unit,record_id,sequence\n2026-01-01T00:00:00Z,speed,36,km/h,1,7\n"
    )
    adapter = ReplayAdapter(valid, speed=0)
    assert adapter.records[0].signal == "vehicle.speed"
    assert adapter.records[0].value == 10
    assert adapter.records[0].sequence == 7
    with pytest.raises(ValueError):
        ReplayAdapter(valid.replace(b"00:00:00Z", b"00:00:00"))
    with pytest.raises(NormalizationError):
        ReplayAdapter(valid.replace(b",36,", b",NaN,"))
    with pytest.raises(ValueError):
        ReplayAdapter(valid + b"2026-01-01T00:00:01Z,speed,36\n")
    with pytest.raises(ValueError):
        ReplayAdapter(valid, speed=float("nan"))


async def test_pending_spool_precedes_new_data_and_overflow_is_visible(tmp_path, caplog) -> None:
    from vehicle_platform.telemetry.domain import RawTelemetryRecord

    spool = BoundedSpool(tmp_path / "fifo", maximum_bytes=200)
    collector = AcquisitionCollector(spool, batch_size=1, retries=0)
    first = RawTelemetryRecord(datetime(2026, 1, 1, tzinfo=UTC), "engine.rpm", 900, "rpm", "old", 1)
    second = RawTelemetryRecord(
        datetime(2026, 1, 1, tzinfo=UTC), "engine.rpm", 1000, "rpm", "new", 2
    )
    calls = []

    async def unavailable(records):
        calls.append(records[0].source_record_id)
        raise OSError

    await collector._send((first,), unavailable)
    await collector._send((second,), unavailable)
    assert calls == ["old", "old"]  # New observations cannot overtake durable pending ones.
    assert b"old" in spool.peek(2)[0] and b"new" in spool.peek(2)[1]
    await collector._spool((first,) * 10)
    assert collector.stats.dropped > 0
    assert "collector.spool_capacity_reached" in caplog.text


@pytest.mark.parametrize(
    "scenario", ["cruise", "jitter", "dropout", "thermal", "fuel_pressure_drop"]
)
async def test_extended_synthetic_modes_have_measured_behavior(scenario: str) -> None:
    adapter = SyntheticLiveAdapter(scenario=scenario, samples=300)
    await adapter.connect()
    plan = preflight(BY_KEY["performance-pull"], await adapter.capabilities()).sampling_plan
    records = [record async for record in adapter.read(plan)]
    grouped = {
        signal: [r for r in records if r.signal == signal] for signal in {r.signal for r in records}
    }
    if scenario == "cruise":
        assert {r.value for r in grouped["vehicle.speed"]} == {18}
        assert {r.value for r in grouped["engine.rpm"]} == {1800}
    if scenario == "jitter":
        times = [r.observed_at for r in grouped["engine.rpm"]]
        assert len({(b - a).total_seconds() for a, b in zip(times, times[1:], strict=False)}) > 1
    if scenario == "dropout":
        assert len(grouped["engine.rpm"]) - len(grouped["engine.boost_pressure"]) == 25
    if scenario == "thermal":
        assert {r.value for r in grouped["engine.intake_air_temperature"]} == {370}
    if scenario == "fuel_pressure_drop":
        assert min(r.value for r in grouped["fuel.high_pressure"]) == 5_000_000
        assert max(r.value for r in grouped["fuel.high_pressure"]) == 12_000_000
    await adapter.close()


def test_synthetic_settings_reject_unsupported_or_nonfinite_inputs() -> None:
    for settings in (
        {"scenario": "invented"},
        {"samples": 0},
        {"speed": float("inf")},
        {"speed": -1},
    ):
        with pytest.raises(ValueError):
            SyntheticLiveAdapter(**settings)


async def test_collector_reports_actual_recovery_metrics_and_payload_free_spans(tmp_path) -> None:
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from prometheus_client import generate_latest

    from vehicle_platform.telemetry.domain import RawTelemetryRecord

    collector = AcquisitionCollector(
        BoundedSpool(tmp_path / "metrics-spool"), batch_size=1, retries=0
    )
    spans = InMemorySpanExporter()
    collector.traces.add_span_processor(SimpleSpanProcessor(spans))
    record = RawTelemetryRecord(
        datetime(2026, 1, 1, tzinfo=UTC), "engine.rpm", 900, "rpm", "private-record", 1
    )

    async def unavailable(records):
        raise OSError("gateway unavailable")

    delivered = []

    async def available(records):
        delivered.extend(records)

    await collector._send((record,), unavailable)
    assert collector.spool.occupancy_bytes > 0
    await collector._replay(available)
    measured = generate_latest(collector.registry).decode()
    assert "collector_observations_replayed_total 1.0" in measured
    assert "collector_observations_published_total 1.0" in measured
    assert "collector_recoveries_total 1.0" in measured
    assert "collector_spool_bytes 0.0" in measured
    assert delivered == [record]
    assert spans.get_finished_spans()[0].name == "acquisition.collector.batch"
    assert "private-record" not in str(spans.get_finished_spans()[0].attributes)
    collector.traces.shutdown()


@pytest.mark.parametrize(
    "heartbeat_age,sample_age,adapter_state,expected",
    [
        (0, 0, "connected", "connected"),
        (16, 0, "connected", "silent"),
        (0, 16, "connected", "stalled"),
        (0, 0, "disconnected", "disconnected"),
    ],
)
def test_collector_health_distinguishes_transport_and_sampling(
    heartbeat_age: int, sample_age: int, adapter_state: str, expected: str
) -> None:
    from vehicle_platform.acquisition.quality import collector_health

    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert collector_health({}, now)["state"] == "not_reported"
    quality = {
        "collector": {
            "received_at": (now - timedelta(seconds=heartbeat_age)).isoformat(),
            "last_sample_received_at": (now - timedelta(seconds=sample_age)).isoformat(),
            "collection_started_at": (now - timedelta(seconds=30)).isoformat(),
            "adapter_state": adapter_state,
        }
    }
    assert collector_health(quality, now)["state"] == expected
    quality["collector"]["last_sample_received_at"] = None
    assert collector_health(quality, now)["state"] in {"stalled", "silent", "disconnected"}


async def test_collector_reports_capabilities_bounds_and_graceful_disconnect(
    tmp_path: Path,
) -> None:
    reports: list[dict[str, object]] = []
    adapter = SyntheticLiveAdapter(samples=1)
    await adapter.connect()
    plan = preflight(BY_KEY["performance-pull"], await adapter.capabilities()).sampling_plan

    async def heartbeat(payload: dict[str, object]) -> None:
        reports.append(payload)

    async def publish(records: tuple[object, ...]) -> None:
        assert records

    collector = AcquisitionCollector(BoundedSpool(tmp_path / "spool"))
    stats = await collector.run(adapter, plan, publish, heartbeat=heartbeat)
    assert stats.published == stats.produced > 0
    assert [report["adapter_state"] for report in reports] == ["connected", "disconnected"]
    assert reports[0]["last_sample_received_at"] is None
    assert reports[1]["last_sample_received_at"] is not None
    assert reports[0]["capability_snapshot"] and reports[0]["sampling_plan"]
    assert reports[1]["queue_observations"] == reports[1]["spool_bytes"] == 0
    assert not adapter.connected


@pytest.mark.parametrize("invalid_stamp", ["2026-01-01T00:00:00", "2025-12-31T23:59:59Z"])
def test_heartbeat_rejects_naive_or_prestart_sample_receipt(invalid_stamp: str) -> None:
    from pydantic import ValidationError

    from vehicle_platform.api.domain_contracts import AcquisitionHeartbeat

    with pytest.raises(ValidationError):
        AcquisitionHeartbeat.model_validate(
            {
                "adapter_state": "connected",
                "collection_started_at": "2026-01-01T00:00:00Z",
                "last_sample_received_at": invalid_stamp,
                "queue_observations": 0,
                "spool_bytes": 0,
                "dropped_observations": 0,
            }
        )


@pytest.mark.parametrize("outcome", [200, 503, 429, 401, "network"])
async def test_gateway_heartbeat_is_scoped_and_failures_are_explicit(monkeypatch, outcome) -> None:
    from uuid import uuid4

    import httpx

    sent = []

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            sent.append((url, kwargs))
            if outcome == "network":
                raise httpx.ConnectError("dependency interrupted")
            return httpx.Response(outcome)

    monkeypatch.setattr("vehicle_platform.acquisition.collector.httpx.AsyncClient", Client)
    acquisition = uuid4()
    publisher = GatewayPublisher("http://gateway", acquisition, "x" * 43)
    if outcome == 200:
        await publisher.heartbeat({"adapter_state": "connected"})
    else:
        with pytest.raises(ValueError if outcome == 401 else OSError):
            await publisher.heartbeat({"adapter_state": "connected"})
    assert sent[0][0].endswith(f"/{acquisition}/heartbeat")
    assert sent[0][1]["headers"]["Authorization"] == "Bearer " + "x" * 43


async def test_collector_heartbeat_interruption_does_not_erase_samples(tmp_path: Path) -> None:
    adapter = SyntheticLiveAdapter(samples=1)
    collector = AcquisitionCollector(BoundedSpool(tmp_path / "offline"))

    async def heartbeat(payload: dict[str, object]) -> None:
        raise OSError("gateway unavailable")

    async def publish(records: tuple[object, ...]) -> None:
        raise OSError("gateway unavailable")

    await adapter.connect()
    plan = preflight(BY_KEY["performance-pull"], await adapter.capabilities()).sampling_plan
    stats = await collector.run(adapter, plan, publish, heartbeat=heartbeat)
    assert stats.produced > 0
    assert len(collector.spool.peek(100)) == stats.produced
    assert not adapter.connected


async def test_collector_capability_failure_closes_adapter(tmp_path: Path) -> None:
    class FailedCapabilities(SyntheticLiveAdapter):
        async def capabilities(self):
            raise OSError("adapter unavailable")

    adapter = FailedCapabilities(samples=1)
    collector = AcquisitionCollector(BoundedSpool(tmp_path / "failed"))

    async def publish(records):
        pytest.fail("discovery failure cannot publish")

    with pytest.raises(OSError):
        await collector.run(adapter, (), publish)
    assert not adapter.connected


async def test_periodic_heartbeat_continues_while_adapter_waits(tmp_path: Path) -> None:
    import asyncio

    from vehicle_platform.telemetry.domain import RawTelemetryRecord

    reported = asyncio.Event()
    reports: list[dict[str, object]] = []

    class WaitingAdapter(SyntheticLiveAdapter):
        async def read(self, plan):
            await reported.wait()
            yield RawTelemetryRecord(datetime.now(UTC), "engine.rpm", 900, "rpm", "waited", 1)

    async def heartbeat(payload: dict[str, object]) -> None:
        reports.append(payload)
        if len(reports) == 2:
            reported.set()

    async def publish(records: tuple[object, ...]) -> None:
        assert len(records) == 1

    adapter = WaitingAdapter(samples=1)
    collector = AcquisitionCollector(BoundedSpool(tmp_path / "waiting"))
    await asyncio.wait_for(collector.run(adapter, (), publish, heartbeat=heartbeat), timeout=7)
    assert len(reports) == 3
    assert reports[1]["adapter_state"] == "connected"
    assert reports[1]["last_sample_received_at"] is None
    assert reports[2]["adapter_state"] == "disconnected"


async def test_synthetic_sampler_achieves_distinct_planned_rates() -> None:
    adapter = SyntheticLiveAdapter(samples=300)
    await adapter.connect()
    plan = preflight(BY_KEY["performance-pull"], await adapter.capabilities()).sampling_plan
    records = [record async for record in adapter.read(plan)]
    for signal, expected_hz in (
        ("engine.rpm", 10),
        ("engine.intake_air_temperature", 5),
        ("engine.oil_temperature", 2),
    ):
        observed = tuple(record.observed_at for record in records if record.signal == signal)
        assert measure_signal_quality(signal, observed, expected_hz).actual_hz == pytest.approx(
            expected_hz, abs=0.01
        )
    await adapter.close()


@pytest.mark.parametrize(
    "bytes_used,state",
    [
        (0, "normal"),
        (69, "normal"),
        (70, "warning"),
        (89, "warning"),
        (90, "near_capacity"),
        (100, "capacity_reached"),
    ],
)
def test_spool_capacity_states_are_measured(tmp_path, bytes_used, state) -> None:
    spool = BoundedSpool(tmp_path / "capacity", maximum_bytes=100)
    spool.path.write_bytes(b"x" * bytes_used)
    assert spool.capacity_state == state


@pytest.mark.parametrize("maximum_bytes", [0, -1, 1073741825])
def test_invalid_spool_capacity_is_rejected(tmp_path, maximum_bytes) -> None:
    with pytest.raises(ValueError):
        BoundedSpool(tmp_path / "capacity", maximum_bytes)


async def test_unavailable_optional_pid_preserves_other_reads(monkeypatch) -> None:
    import asyncio

    class NoDataElm(FakeElm):
        async def request(self, command, request_timeout):
            if command == "010C":
                return "NO DATA"
            return await super().request(command, request_timeout)

    async def immediate(_delay):
        return None

    monkeypatch.setattr(asyncio, "sleep", immediate)
    adapter = Elm327Adapter(NoDataElm())
    await adapter.connect()
    plan = preflight(BY_KEY["general-health"], await adapter.capabilities()).sampling_plan
    source = adapter.read(plan)
    record = await anext(source)
    assert record.signal == "vehicle.speed"
    assert (await adapter.capabilities()).signals["engine.rpm"] is Support.UNAVAILABLE
    await source.aclose()
    await adapter.close()
