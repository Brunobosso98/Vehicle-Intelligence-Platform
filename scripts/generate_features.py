"""Bounded operator CLI for deterministic Phase 9A feature generation."""

import argparse
import asyncio
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from vehicle_platform.core.config import Settings
from vehicle_platform.features.service import FeatureGenerationService
from vehicle_platform.infrastructure.database import Database


def _cutoff(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("observation cutoff must include a timezone")
    return parsed


async def _run(args: argparse.Namespace) -> int:
    settings = Settings()
    database = Database(settings, command_timeout=60)
    service = FeatureGenerationService(database)
    try:
        if args.dry_run:
            async with asyncio.timeout(30):
                result = await service.estimate_session(
                    args.session, max_pulls=args.max_pulls
                )
            result["observation_cutoff"] = (
                args.observation_cutoff.isoformat() if args.observation_cutoff else None
            )
            print(json.dumps(result, sort_keys=True, indent=2))
            return 2 if result["exceeds_batch_limit"] else 0
        async with asyncio.timeout(300):
            result = await service.generate_session(
                args.session,
                observation_cutoff=args.observation_cutoff,
                max_pulls=args.max_pulls,
            )
        print(json.dumps(result, sort_keys=True, indent=2))
        return 1 if result["failed"] else 0
    finally:
        await database.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=UUID, required=True)
    parser.add_argument("--observation-cutoff", type=_cutoff)
    parser.add_argument("--max-pulls", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_pulls <= 100:
        parser.error("--max-pulls must be between 1 and 100")
    try:
        return asyncio.run(_run(args))
    except (ValueError, LookupError, OSError, TimeoutError, SQLAlchemyError) as exc:
        parser.exit(1, f"feature generation failed: {type(exc).__name__}\n")


if __name__ == "__main__":
    raise SystemExit(main())
