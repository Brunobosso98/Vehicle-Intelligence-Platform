import asyncio
import json
from collections.abc import Awaitable
from dataclasses import asdict
from enum import StrEnum
from pathlib import Path
from uuid import UUID

import typer
from prometheus_client import start_http_server

from vehicle_platform.acquisition.adapters import (
    Elm327Adapter,
    ElmTcpTransport,
    ReplayAdapter,
    SyntheticLiveAdapter,
    VehicleDataAdapter,
)
from vehicle_platform.acquisition.collector import AcquisitionCollector, GatewayPublisher
from vehicle_platform.acquisition.domain import preflight
from vehicle_platform.acquisition.recipes import BY_KEY, RECIPES
from vehicle_platform.acquisition.stream import BoundedSpool
from vehicle_platform.telemetry.domain import RawTelemetryRecord


def execute[T](operation: Awaitable[T]) -> T:
    async def invoke() -> T:
        return await operation

    try:
        return asyncio.run(invoke())
    except (OSError, TimeoutError, ValueError):
        typer.echo(
            "Collector input or dependency unavailable; inspect readiness and spool.", err=True
        )
        raise typer.Exit(1) from None


class AdapterKind(StrEnum):
    SYNTHETIC = "synthetic"
    OBD = "obd"


def adapter_for(
    kind: AdapterKind, host: str | None, port: int, samples: int = 120
) -> VehicleDataAdapter:
    if kind is AdapterKind.OBD:
        if not host:
            raise typer.BadParameter("--obd-host is required for read-only OBD")
        return Elm327Adapter(ElmTcpTransport(host, port))
    return SyntheticLiveAdapter(samples=samples)


app = typer.Typer(help="Read-only vehicle telemetry collector.", no_args_is_help=True)


@app.command("devices")
def devices(json_output: bool = typer.Option(False, "--json")) -> None:
    devices_found = [{"id": "synthetic", "adapter": "synthetic-live-v1", "read_only": True}]
    typer.echo(
        json.dumps(devices_found) if json_output else "synthetic  synthetic-live-v1  read-only"
    )


@app.command()
def recipes() -> None:
    for recipe in RECIPES:
        typer.echo(
            f"{recipe.key}\t{recipe.name}\tv{recipe.version}\t{recipe.configuration_hash[:12]}"
        )


async def _preflight(
    recipe_key: str,
    kind: AdapterKind = AdapterKind.SYNTHETIC,
    host: str | None = None,
    port: int = 35000,
) -> dict[str, object]:
    recipe = BY_KEY.get(recipe_key)
    if recipe is None:
        raise typer.BadParameter("unknown recipe")
    adapter = adapter_for(kind, host, port)
    try:
        await adapter.connect()
        return asdict(preflight(recipe, await adapter.capabilities()))
    finally:
        await adapter.close()


@app.command("preflight")
def preflight_command(
    recipe: str = typer.Option(..., "--recipe"),
    json_output: bool = typer.Option(False, "--json"),
    adapter: AdapterKind = typer.Option(AdapterKind.SYNTHETIC, "--adapter"),
    obd_host: str | None = typer.Option(None, "--obd-host"),
    obd_port: int = typer.Option(35000, "--obd-port", min=1, max=65535),
) -> None:
    result = execute(_preflight(recipe, adapter, obd_host, obd_port))
    typer.echo(
        json.dumps(result, default=str) if json_output else f"readiness: {result['readiness']}"
    )


@app.command()
def probe(
    json_output: bool = typer.Option(False, "--json"),
    adapter: AdapterKind = typer.Option(AdapterKind.SYNTHETIC, "--adapter"),
    obd_host: str | None = typer.Option(None, "--obd-host"),
    obd_port: int = typer.Option(35000, "--obd-port", min=1, max=65535),
) -> None:
    result = execute(_preflight("general-health", adapter, obd_host, obd_port))
    typer.echo(
        json.dumps(result, default=str)
        if json_output
        else f"Read-only {adapter.value} probe: {result['readiness']}"
    )


@app.command()
def start(
    recipe: str = typer.Option(..., "--recipe"),
    adapter: AdapterKind = typer.Option(AdapterKind.SYNTHETIC, "--adapter"),
    obd_host: str | None = typer.Option(None, "--obd-host"),
    obd_port: int = typer.Option(35000, "--obd-port", min=1, max=65535),
    dry_run: bool = typer.Option(False, "--dry-run"),
    metrics_port: int = typer.Option(0, "--metrics-port", min=0, max=65535),
    samples: int = typer.Option(120, min=1, max=100000),
    acquisition_id: UUID | None = typer.Option(None, "--acquisition-id"),
    gateway: str = typer.Option("http://127.0.0.1:8000", "--gateway"),
    spool: Path = typer.Option(Path("~/.vehicle-collector/spool").expanduser(), "--spool"),
) -> None:
    if acquisition_id is None and not dry_run:
        raise typer.BadParameter(
            "--acquisition-id is required; use --dry-run for explicit simulation"
        )

    async def collect() -> int:
        selected = BY_KEY.get(recipe)
        if selected is None:
            raise typer.BadParameter("unknown recipe")
        source = adapter_for(adapter, obd_host, obd_port, samples)
        await source.connect()
        result = preflight(selected, await source.capabilities())
        await source.close()
        if result.readiness == "blocked":
            raise typer.BadParameter("required signals or rates are unavailable")

        async def local(batch: tuple[RawTelemetryRecord, ...]) -> None:
            return None

        publisher = GatewayPublisher(gateway, acquisition_id) if acquisition_id else local
        collector = AcquisitionCollector(BoundedSpool(spool))
        if metrics_port:
            start_http_server(metrics_port, addr="127.0.0.1", registry=collector.registry)
        stats = await collector.run(
            source,
            result.sampling_plan,
            publisher,
            heartbeat=publisher.heartbeat if isinstance(publisher, GatewayPublisher) else None,
        )
        return stats.published

    try:
        count = execute(collect())
        outcome = "dry-run observed" if dry_run else "gateway accepted"
        typer.echo(f"{outcome} {count} observations")
    except KeyboardInterrupt:
        typer.echo("collection stopped safely", err=True)
        raise typer.Exit(130) from None


@app.command()
def replay(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    speed: float = typer.Option(10, min=0.01, max=1000),
    recipe: str = typer.Option("general-health", "--recipe"),
    acquisition_id: UUID | None = typer.Option(None, "--acquisition-id"),
    gateway: str = typer.Option("http://127.0.0.1:8000", "--gateway"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    metrics_port: int = typer.Option(0, "--metrics-port", min=0, max=65535),
    spool: Path = typer.Option(Path("~/.vehicle-collector/spool").expanduser(), "--spool"),
) -> None:
    if acquisition_id is None and not dry_run:
        raise typer.BadParameter("--acquisition-id is required; use --dry-run for validation")
    if path.stat().st_size > 10_000_000:
        raise typer.BadParameter("replay file exceeds 10 MB")
    content = path.read_bytes()

    async def run() -> int:
        selected = BY_KEY.get(recipe)
        if selected is None:
            raise typer.BadParameter("unknown recipe")
        adapter = ReplayAdapter(content, speed)
        capabilities = await adapter.capabilities()
        result = preflight(selected, capabilities)
        if result.readiness == "blocked":
            raise typer.BadParameter("replay lacks required signals or rates")

        async def inspect(batch: tuple[RawTelemetryRecord, ...]) -> None:
            return None

        publisher = GatewayPublisher(gateway, acquisition_id) if acquisition_id else inspect
        collector = AcquisitionCollector(BoundedSpool(spool))
        if metrics_port:
            start_http_server(metrics_port, addr="127.0.0.1", registry=collector.registry)
        stats = await collector.run(adapter, result.sampling_plan, publisher)
        return stats.published

    outcome = "dry-run observed" if dry_run else "gateway accepted replay"
    typer.echo(f"{outcome} {execute(run())} observations")
