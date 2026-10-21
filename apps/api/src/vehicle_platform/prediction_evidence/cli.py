from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any
from uuid import UUID

from vehicle_platform.anomalies.artifacts import ArtifactStore as AnomalyArtifactStore
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import ArtifactStore as ModelArtifactStore
from vehicle_platform.prediction_evidence.service import PredictionEvidenceService
from vehicle_platform.predictions.domain import PredictionError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vehicle-prediction-evidence")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="materialize immutable evidence from one 9D receipt")
    build.add_argument("--receipt-id", required=True, type=UUID)
    build.add_argument("--schema-version", default="phase9e-prediction-evidence-v1")
    build.add_argument("--dry-run", action="store_true")
    verify = commands.add_parser(
        "verify", help="recheck frozen evidence sources and append an audit"
    )
    verify.add_argument("--evidence-id", required=True, type=UUID)
    inspect = commands.add_parser("inspect", help="show a bounded safe projection")
    selector = inspect.add_mutually_exclusive_group(required=True)
    selector.add_argument("--evidence-id", type=UUID)
    selector.add_argument("--receipt-id", type=UUID)
    for command in (build, verify):
        command.add_argument("--confirm-environment", choices=("development", "test"))
        command.add_argument(
            "--yes", action="store_true", help="confirm persistent evidence or audit write"
        )
    for command in (build, inspect):
        command.add_argument("--json", action="store_true", help="emit sanitized JSON")
    return parser


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    settings = Settings()
    if settings.environment not in {"development", "test"}:
        raise PredictionError(
            403,
            "PREDICTION_EVIDENCE_CONTROL_DISABLED",
            "Prediction evidence controls are disabled outside development/test",
        )
    if args.command in {"build", "verify"}:
        if (
            args.confirm_environment is not None
            and args.confirm_environment != settings.environment
        ):
            raise PredictionError(
                403,
                "PREDICTION_EVIDENCE_ENVIRONMENT_MISMATCH",
                "Confirmation does not match the configured environment",
            )
        persistent = not (args.command == "build" and args.dry_run)
        if persistent and args.confirm_environment is None:
            raise PredictionError(
                422,
                "PREDICTION_EVIDENCE_ENVIRONMENT_CONFIRMATION_REQUIRED",
                "Persistent evidence operations require --confirm-environment",
            )
        if persistent and not args.yes:
            raise PredictionError(
                422,
                "PREDICTION_EVIDENCE_CONFIRMATION_REQUIRED",
                "Persistent evidence operations require --yes",
            )
    database = Database(settings, command_timeout=4, pool_pre_ping=False)
    service = PredictionEvidenceService(
        database,
        model_artifacts=ModelArtifactStore(),
        anomaly_artifacts=AnomalyArtifactStore(),
    )
    try:
        if args.command == "build":
            projection, created, bundle = await service.materialize(
                args.receipt_id,
                schema_version=args.schema_version,
                dry_run=args.dry_run,
            )
            return {
                "status": "DRY_RUN" if args.dry_run else ("MATERIALIZED" if created else "REUSED"),
                "evidence_id": str(bundle.evidence_id),
                "receipt_id": str(bundle.receipt_id),
                "logical_fingerprint": bundle.logical_fingerprint,
                "content_checksum": bundle.content_checksum,
                "integrity": bundle.integrity.value,
                "completeness": bundle.completeness.value,
                "node_count": len(bundle.nodes),
                "edge_count": len(bundle.edges),
                "fact_count": len(bundle.facts),
                "gap_codes": [item.code.value for item in bundle.gaps],
                "projection": projection.model_dump(mode="json") if args.json else None,
            }
        if args.command == "verify":
            result = await service.verify(args.evidence_id)
            return {
                "status": result.integrity.value,
                "verification": result.model_dump(mode="json"),
            }
        projection = (
            await service.read(args.evidence_id)
            if args.evidence_id is not None
            else await service.read_for_receipt(args.receipt_id)
        )
        return {"status": "OK", "evidence": projection.model_dump(mode="json")}
    finally:
        await database.close()


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = asyncio.run(_run(args))
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), default=str))
    except Exception as error:
        print(
            json.dumps({"status": "FAILED", "error_category": type(error).__name__}, sort_keys=True)
        )
        if isinstance(error, PredictionError):
            raise SystemExit(1) from None
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
