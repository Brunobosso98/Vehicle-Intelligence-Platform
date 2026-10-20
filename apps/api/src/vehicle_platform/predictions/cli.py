from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from typing import Any
from uuid import UUID

from vehicle_platform.anomalies.domain import SourceRole
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.predictions.domain import PredictionError
from vehicle_platform.predictions.service import PredictionService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vehicle-prediction",
        description="Review and explicitly control Phase 9D controlled serving approvals.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="list active serving approvals")
    listing.add_argument("--kind", choices=("next_pull", "anomaly"))
    listing.add_argument("--source-role", choices=_roles())
    candidate = commands.add_parser("inspect", help="verify a registered candidate and artifact")
    candidate.add_argument("--kind", required=True, choices=("next_pull", "anomaly"))
    candidate.add_argument("--version-id", required=True, type=UUID)
    approval = commands.add_parser("approve", help="create an immutable serving approval")
    approval.add_argument("--kind", required=True, choices=("next_pull", "anomaly"))
    approval.add_argument("--version-id", required=True, type=UUID)
    approval.add_argument("--source-role", required=True, choices=_roles())
    approval.add_argument("--reason", required=True)
    approval.add_argument("--operator-id", required=True)
    approval.add_argument("--review-reference", required=True)
    _confirmation(approval)
    for action in ("activate", "revoke", "rollback"):
        command = commands.add_parser(action, help=f"{action} a reviewed serving approval")
        command.add_argument("--binding-id", required=True, type=UUID)
        command.add_argument("--reason", required=True)
        command.add_argument("--operator-id", required=True)
        _confirmation(command)
    return parser


def _confirmation(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--yes", action="store_true", help="confirm this state-changing action")
    parser.add_argument(
        "--confirm-environment",
        required=True,
        choices=("development", "test"),
        help="repeat the controlled environment name",
    )


def _roles() -> tuple[str, ...]:
    return tuple(role.value for role in SourceRole if role is not SourceRole.MIXED)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    settings = Settings()
    if settings.environment == "production":
        raise PredictionError(
            403,
            "PREDICTION_PRODUCTION_CONTROL_DISABLED",
            "Prediction Service controls are disabled in production",
        )
    database = Database(settings, command_timeout=10, pool_pre_ping=False)
    service = PredictionService(settings, database)
    try:
        if args.command == "list":
            rows = await service.versions(limit=100)
            if args.kind:
                rows = [item for item in rows if item["result_kind"] == args.kind]
            if args.source_role:
                rows = [item for item in rows if item["source_role"].value == args.source_role]
            return {"status": "OK", "active_bindings": rows}
        if args.command == "inspect":
            candidate = await service.inspect_candidate(args.kind, args.version_id)
            return {"status": "VERIFIED_CANDIDATE", "candidate": asdict(candidate)}
        if not args.yes:
            raise PredictionError(
                422, "PREDICTION_EXPLICIT_CONFIRMATION_REQUIRED", "State changes require --yes"
            )
        if args.confirm_environment != settings.environment:
            raise PredictionError(
                403,
                "PREDICTION_ENVIRONMENT_CONFIRMATION_REQUIRED",
                "Confirmation does not match the configured environment",
            )
        if args.command == "approve":
            binding_id, event_id = await service.approve_candidate(
                args.kind,
                args.version_id,
                source_role=SourceRole(args.source_role),
                reason=args.reason,
                operator_id=args.operator_id,
                review_reference=args.review_reference,
                environment_confirmation=args.confirm_environment,
            )
            return {"status": "APPROVED", "binding_id": str(binding_id), "event_id": str(event_id)}
        binding, event_id = await service.transition(
            args.binding_id,
            args.command,
            reason=args.reason,
            operator_id=args.operator_id,
            environment_confirmation=args.confirm_environment,
        )
        return {
            "status": binding.latest_event_type.value,
            "binding_id": str(binding.id),
            "event_id": str(event_id),
            "model_version_id": str(binding.model_version_id) if binding.model_version_id else None,
            "detector_version_id": str(binding.detector_version_id)
            if binding.detector_version_id
            else None,
        }
    finally:
        await service.close()
        await database.close()


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = asyncio.run(_run(args))
    except Exception as error:
        print(
            json.dumps({"status": "FAILED", "error_category": type(error).__name__}),
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
