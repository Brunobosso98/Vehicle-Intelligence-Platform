from datetime import UTC, datetime, timedelta
from pathlib import Path

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
    assert required["engine.rpm"].estimated_hz >= 5
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


@pytest.mark.parametrize("status,error", [(202, None), (503, OSError), (422, ValueError)])
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
