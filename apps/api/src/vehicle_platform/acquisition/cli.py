import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

import typer

from vehicle_platform.acquisition.adapters import ReplayAdapter, SyntheticLiveAdapter
from vehicle_platform.acquisition.collector import AcquisitionCollector, GatewayPublisher
from vehicle_platform.acquisition.domain import preflight
from vehicle_platform.acquisition.recipes import BY_KEY, RECIPES
from vehicle_platform.acquisition.stream import BoundedSpool
from vehicle_platform.telemetry.domain import RawTelemetryRecord

app = typer.Typer(help="Read-only vehicle telemetry collector.", no_args_is_help=True)


@app.command("preflight")
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


async def _preflight(recipe_key: str) -> dict[str, object]:
    recipe = BY_KEY.get(recipe_key)
    if recipe is None:
        raise typer.BadParameter("unknown recipe")
    adapter = SyntheticLiveAdapter()
    await adapter.connect()
    return asdict(preflight(recipe, await adapter.capabilities()))


@app.command()
def preflight_command(
    recipe: str = typer.Option(..., "--recipe"), json_output: bool = typer.Option(False, "--json")
) -> None:
    result = asyncio.run(_preflight(recipe))
    typer.echo(
        json.dumps(result, default=str) if json_output else f"readiness: {result['readiness']}"
    )


@app.command()
def probe(json_output: bool = typer.Option(False, "--json")) -> None:
    result = asyncio.run(_preflight("general-health"))
    typer.echo(
        json.dumps(result, default=str) if json_output else "Synthetic read-only adapter available"
    )


@app.command()
def start(
    recipe: str = typer.Option(..., "--recipe"),
    samples: int = typer.Option(120, min=1, max=100000),
    acquisition_id: UUID | None = typer.Option(None, "--acquisition-id"),
    gateway: str = typer.Option("http://127.0.0.1:8000", "--gateway"),
    spool: Path = typer.Option(Path("~/.vehicle-collector/spool").expanduser(), "--spool"),
) -> None:
    async def collect() -> int:
        selected = BY_KEY.get(recipe)
        if selected is None:
            raise typer.BadParameter("unknown recipe")
        adapter = SyntheticLiveAdapter(samples=samples)
        result = preflight(selected, await adapter.capabilities())

        async def local(batch: tuple[RawTelemetryRecord, ...]) -> None:
            return None

        publisher = GatewayPublisher(gateway, acquisition_id) if acquisition_id else local
        stats = await AcquisitionCollector(BoundedSpool(spool)).run(
            adapter, result.sampling_plan, publisher
        )
        return stats.published

    try:
        typer.echo(f"collected {asyncio.run(collect())} observations")
    except KeyboardInterrupt:
        typer.echo("collection stopped safely", err=True)
        raise typer.Exit(130) from None


@app.command()
def replay(path: Path, speed: float = typer.Option(10, min=0.01, max=1000)) -> None:
    content = path.read_bytes()

    async def run() -> int:
        adapter = ReplayAdapter(content, speed)
        await adapter.connect()
        capabilities = await adapter.capabilities()
        plan = preflight(BY_KEY["general-health"], capabilities).sampling_plan
        count = 0
        async for _record in adapter.read(plan):
            count += 1
        return count

    typer.echo(f"replayed {asyncio.run(run())} observations")
