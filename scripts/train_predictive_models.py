"""Run a bounded offline Phase 9B model training job against configured data."""

import argparse
import asyncio
import json
from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.ml.pipeline import train_task
from vehicle_platform.observability.telemetry import Telemetry


def _cutoff(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("cutoff must be ISO-8601") from error
    if parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("cutoff must include a timezone")
    return parsed


async def _run(args: argparse.Namespace) -> int:
    settings = Settings()
    if settings.environment == "production":
        raise ValueError(
            "offline Phase 9B training is disabled in production environment"
        )
    database = Database(settings, command_timeout=60)
    telemetry = Telemetry(settings, database)
    try:
        results: list[dict[str, Any]] = []
        async with asyncio.timeout(args.timeout_seconds):
            for task in args.tasks:
                result = await train_task(
                    database,
                    task,
                    args.observation_cutoff,
                    source=args.source_role,
                    git_sha=settings.git_sha,
                    telemetry=telemetry,
                )
                results.append(
                    {
                        "task": task.value,
                        "model_spec": result.dataset.model_spec.manifest(),
                        "dataset": result.dataset.manifest,
                        "split": result.training.manifest()["split"],
                        "candidates": [
                            item.manifest() for item in result.training.candidates
                        ],
                        "selected": result.training.manifest()["selected_model"],
                        "acceptance": result.training.acceptance,
                        "training_run_id": str(result.run_id),
                        "model_version_id": str(result.model_version_id),
                        "artifact": {
                            "path": result.artifact.relative_path,
                            "checksum": result.artifact.checksum,
                            "size_bytes": result.artifact.size_bytes,
                        },
                    }
                )
        print(
            json.dumps(
                {"status": "completed", "tasks": results}, indent=2, sort_keys=True
            )
        )
        return (
            0 if all(item["acceptance"]["all_criteria_pass"] for item in results) else 2
        )
    finally:
        telemetry.shutdown()
        await database.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        action="append",
        dest="tasks",
        type=MLTask,
        choices=list(MLTask),
        required=True,
        help="repeat to train multiple allowlisted tasks",
    )
    parser.add_argument("--observation-cutoff", type=_cutoff, required=True)
    parser.add_argument(
        "--source-role",
        choices=("synthetic", "real_vehicle", "imported", "imported_fixture", "mixed"),
        required=True,
    )
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    if not 30 <= args.timeout_seconds <= 3600:
        parser.error("--timeout-seconds must be between 30 and 3600")
    try:
        return asyncio.run(_run(args))
    except (ValueError, LookupError, OSError, TimeoutError, SQLAlchemyError) as error:
        parser.exit(1, f"predictive model training failed: {type(error).__name__}\n")


if __name__ == "__main__":
    raise SystemExit(main())
