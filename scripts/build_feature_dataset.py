"""Build and export a bounded Phase 9A pull dataset from registered feature sets."""

import argparse
import asyncio
import json
import re
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from vehicle_platform.core.config import Settings
from vehicle_platform.features.datasets import DatasetBuilder, export_model_ready
from vehicle_platform.features.domain import (
    CutoffPolicy,
    DatasetDefinition,
    EntityScope,
)
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.infrastructure.database import Database


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("cutoff must include a timezone")
    return parsed


async def _run(args: argparse.Namespace) -> None:
    settings = Settings()
    database = Database(settings, command_timeout=60)
    try:
        definition = DatasetDefinition(
            name=args.name,
            version=args.version,
            row_scope=EntityScope.PULL,
            feature_set_version=args.feature_version,
            selected_features=tuple(args.features.split(",")),
            observation_cutoff=args.cutoff,
            cutoff_policy=CutoffPolicy(args.cutoff_policy),
            minimum_quality=args.minimum_quality,
            allow_configuration_mixing=args.allow_configuration_mixing,
            source=args.source,
        )
        builder = DatasetBuilder(database, DEFAULT_REGISTRY)
        async with asyncio.timeout(300):
            result = await builder.build(definition)
        data_path, manifest_path = export_model_ready(result, args.export_name)
        print(
            json.dumps(
                {
                    "row_count": len(result.rows),
                    "excluded_row_count": len(result.exclusions),
                    "checksum": result.checksum,
                    "dataset_definition_checksum": definition.checksum,
                    "data_path": str(data_path),
                    "manifest_path": str(manifest_path),
                },
                sort_keys=True,
                indent=2,
            )
        )
    finally:
        await database.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--feature-version", default="phase9a-pull-v2")
    parser.add_argument(
        "--features", required=True, help="comma-separated canonical feature keys"
    )
    parser.add_argument("--cutoff", type=_aware_datetime, required=True)
    parser.add_argument(
        "--cutoff-policy",
        choices=[item.value for item in CutoffPolicy],
        default="row_end",
    )
    parser.add_argument("--minimum-quality", type=float, default=0.0)
    parser.add_argument("--allow-configuration-mixing", action="store_true")
    parser.add_argument(
        "--source",
        choices=["synthetic", "real_vehicle", "imported", "imported_fixture", "mixed"],
        default="synthetic",
    )
    parser.add_argument("--export-name", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.export_name):
        parser.error("--export-name must be a bounded filename token")
    try:
        asyncio.run(_run(args))
    except (ValueError, LookupError, OSError, TimeoutError, SQLAlchemyError) as exc:
        parser.exit(1, f"dataset build failed: {type(exc).__name__}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
