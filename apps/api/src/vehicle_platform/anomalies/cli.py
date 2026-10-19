from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from vehicle_platform.anomalies.definitions import detector_definition
from vehicle_platform.anomalies.detectors import DetectorFitError, fit_detector
from vehicle_platform.anomalies.domain import SourceRole
from vehicle_platform.anomalies.repository import AnomalyDataRepository
from vehicle_platform.anomalies.service import AnomalyService
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database

MAX_MANIFEST_BYTES = 64 * 1024


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vehicle-anomaly",
        description="Fit or score bounded Phase 9C offline anomaly detectors.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    fit = commands.add_parser("fit", help="fit one detector from a prior same-vehicle cohort")
    _detector_arguments(fit)
    fit.add_argument("--anchor-pull-id", required=True, type=UUID)
    fit.add_argument("--cutoff", required=True, type=parse_cutoff)
    fit.add_argument("--source-role", required=True, choices=_source_roles())
    fit.add_argument("--dry-run", action="store_true", help="validate and fit without persistence")

    freeze = commands.add_parser(
        "freeze-threshold", help="create an immutable version with a validation-selected threshold"
    )
    freeze.add_argument("--detector-version-id", required=True, type=UUID)
    freeze.add_argument("--threshold", required=True, type=float)
    freeze.add_argument("--validation-checksum", required=True)
    freeze.add_argument("--selection-manifest", required=True, type=Path)
    freeze.add_argument(
        "--accept", action="store_true", help="record the selected accepted detector"
    )

    score = commands.add_parser("score", help="score 1 to 1000 completed pulls offline")
    score.add_argument("--detector-version-id", required=True, type=UUID)
    score.add_argument("--pull-ids", required=True, type=parse_pull_ids)
    score.add_argument("--cutoff", required=True, type=parse_cutoff)
    score.add_argument("--source-role", required=True, choices=_source_roles())
    return parser


def parse_cutoff(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "cutoff must be ISO 8601 with an explicit offset"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("cutoff must include a timezone offset")
    return parsed


def parse_pull_ids(value: str) -> tuple[UUID, ...]:
    try:
        ids = tuple(UUID(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as error:
        raise argparse.ArgumentTypeError("pull IDs must be comma-separated UUIDs") from error
    if not 1 <= len(ids) <= 1000 or len(set(ids)) != len(ids):
        raise argparse.ArgumentTypeError("provide 1 to 1000 unique pull IDs")
    return ids


def _source_roles() -> tuple[str, ...]:
    return tuple(role.value for role in SourceRole if role is not SourceRole.MIXED)


def _require_source_role(role: SourceRole | None) -> SourceRole:
    if role is None:
        raise ValueError("this command requires an explicit source role")
    return role


def _detector_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--family", required=True, choices=("thermal", "boost_air", "performance", "fuel")
    )
    parser.add_argument("--method", required=True, choices=("robust_mad", "isolation_forest"))


def _read_selection_manifest(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("selection manifest must be a regular file no larger than 64 KiB")
    try:
        decoded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("selection manifest must contain valid JSON") from error
    if not isinstance(decoded, dict):
        raise ValueError("selection manifest root must be an object")
    return decoded


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    settings = Settings()
    if settings.environment == "production":
        raise RuntimeError("offline anomaly commands are disabled in production")
    database = Database(settings, command_timeout=60)
    source_role = SourceRole(args.source_role) if hasattr(args, "source_role") else None
    try:
        if args.command == "fit" and args.dry_run:
            source_role = _require_source_role(source_role)
            definition = detector_definition(args.family, args.method)
            repository = AnomalyDataRepository(database)
            anchor, version_id, version_checksum = await repository.load_anchor(
                args.anchor_pull_id, args.cutoff, source_role, definition
            )
            if args.cutoff < anchor.pull_ended_at:
                raise ValueError("cutoff must include the completed anchor pull")
            dataset = await repository.materialize_reference(
                anchor, version_id, version_checksum, definition, source_role
            )
            try:
                fitted = fit_detector(definition, dataset)
            except DetectorFitError as error:
                return {
                    "status": "REJECTED",
                    "reason": error.reason.value,
                    "family": definition.family.value,
                    "method": definition.method.value,
                    "reference_rows": len(dataset.rows),
                    "reference_sessions": len({row.session_id for row in dataset.rows}),
                    "reference_checksum": dataset.checksum(definition),
                    "dry_run": True,
                }
            return {
                "status": "VALID",
                "family": definition.family.value,
                "method": definition.method.value,
                "reference_rows": len(dataset.rows),
                "reference_sessions": len({row.session_id for row in dataset.rows}),
                "reference_checksum": dataset.checksum(definition),
                "threshold": fitted.threshold,
                "included_features": list(fitted.feature_order),
                "dry_run": True,
            }
        service = AnomalyService(database)
        if args.command == "fit":
            source_role = _require_source_role(source_role)
            fit_result = await service.fit_detector_version(
                anchor_pull_id=args.anchor_pull_id,
                observation_cutoff=args.cutoff,
                source_role=source_role,
                family=args.family,
                method=args.method,
            )
            return _version_result(fit_result)
        if args.command == "freeze-threshold":
            manifest = _read_selection_manifest(args.selection_manifest)
            freeze_result = await service.freeze_validation_threshold(
                detector_version_id=args.detector_version_id,
                threshold=args.threshold,
                validation_checksum=args.validation_checksum,
                selection_manifest=manifest,
                accepted=args.accept,
            )
            return _version_result(freeze_result)
        source_role = _require_source_role(source_role)
        score_result = await service.score_detector_version(
            detector_version_id=args.detector_version_id,
            pull_ids=args.pull_ids,
            observation_cutoff=args.cutoff,
            source_role=source_role,
        )
        return {
            "status": "COMPLETED",
            "run_id": str(score_result.run_id),
            "run_identity": score_result.run_identity,
            "detector_version_id": str(score_result.detector_version_id),
            "requested_count": score_result.requested_count,
            "scored_count": score_result.scored_count,
            "missing_feature_set_count": score_result.missing_feature_set_count,
            "status_counts": score_result.status_counts,
            "input_checksum": score_result.input_checksum,
            "artifact_checksum": score_result.artifact_checksum,
            "idempotent_replay": score_result.idempotent_replay,
            "summary": score_result.summary,
        }
    finally:
        await database.close()


def _version_result(result: Any) -> dict[str, Any]:
    return {
        "status": result.state.value,
        "detector_version_id": str(result.detector_version_id),
        "version": result.version,
        "reference_dataset_id": str(result.reference_dataset_id),
        "reference_checksum": result.reference_checksum,
        "fit_checksum": result.fit_checksum,
        "threshold": result.threshold,
        "artifact_checksum": result.artifact_checksum,
        "rejection_reason": result.rejection_reason,
        "created": result.created,
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = asyncio.run(_run(args))
    except Exception as error:
        print(
            json.dumps({"status": "FAILED", "error_category": type(error).__name__}),
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("status") == "REJECTED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
