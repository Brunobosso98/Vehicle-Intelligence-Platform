"""Local-only entry point for bounded MLOps planning and retrospective monitoring."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.infrastructure.trusted_files import write_exclusive_bytes
from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind
from vehicle_platform.mlops.monitoring import MonitoringProtocol, monitor_receipts
from vehicle_platform.mlops.operator_auth import authenticated_reviewer
from vehicle_platform.mlops.planner import plan_anomaly, plan_supervised
from vehicle_platform.mlops.policy import require_controlled_environment
from vehicle_platform.mlops.repository import ControlPlaneRepository
from vehicle_platform.mlops.reproduction import reproduce_supervised_run
from vehicle_platform.mlops.rollback import inspect_rollback_plan, plan_rollback
from vehicle_platform.mlops.runner import resume_pipeline, run_pipeline
from vehicle_platform.observability.telemetry import Telemetry

MAX_MANIFEST_BYTES = 65536


def _read_manifest(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_MANIFEST_BYTES:
            raise ValueError("manifest must be a bounded regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            body = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(body) > MAX_MANIFEST_BYTES:
            raise ValueError("manifest exceeds the size limit")
        return body
    finally:
        os.close(descriptor)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="vehicle-mlops", description="Controlled offline planning and receipt monitoring."
    )
    result.add_argument(
        "--metrics-file",
        type=Path,
        help="write this command's bounded Prometheus metrics to a new private local file",
    )
    commands = result.add_subparsers(dest="command", required=True)
    for name, description in (
        ("plan", "Validate a pipeline definition without database writes."),
        ("monitor", "Read a bounded window of existing prediction receipts."),
    ):
        command = commands.add_parser(name, help=description)
        command.add_argument("--manifest", required=True, type=Path)
    inspect = commands.add_parser("inspect", help="Read a bounded history of one pipeline run.")
    inspect.add_argument("--run-id", required=True, type=UUID)
    proposal = commands.add_parser("proposal", help="Read one immutable review proposal.")
    proposal.add_argument("--proposal-id", required=True, type=UUID)
    review = commands.add_parser("review", help="Append an explicit, authenticated human review.")
    review.add_argument("--proposal-id", required=True, type=UUID)
    review.add_argument("--proposal-checksum", required=True)
    review.add_argument("--decision", required=True, choices=("accept", "reject"))
    review.add_argument("--reason", required=True)
    review.add_argument("--execute", action="store_true")
    review.add_argument("--confirm-environment", choices=("development", "test"))
    review.add_argument("--confirm-proposal-checksum")
    rollback = commands.add_parser(
        "rollback-plan", help="Verify and optionally persist Phase 9D rollback readiness."
    )
    rollback.add_argument("--proposal-id", required=True, type=UUID)
    rollback.add_argument("--target-binding-id", required=True, type=UUID)
    rollback.add_argument("--execute", action="store_true")
    rollback.add_argument("--confirm-environment", choices=("development", "test"))
    rollback.add_argument("--confirm-proposal-checksum")
    rollback_inspect = commands.add_parser(
        "rollback-inspect", help="Re-verify one stored plan against current 9D state."
    )
    rollback_inspect.add_argument("--plan-id", required=True, type=UUID)
    run = commands.add_parser(
        "run",
        help=(
            "Dry-run by default; execute only with exact environment and fingerprint confirmation."
        ),
    )
    run.add_argument("--manifest", required=True, type=Path)
    run.add_argument("--execute", action="store_true")
    run.add_argument("--confirm-environment", choices=("development", "test"))
    run.add_argument("--fingerprint")
    run.add_argument("--champion-binding-id", type=UUID)
    resume = commands.add_parser(
        "resume", help="Inspect or safely recover one exact immutable pipeline definition."
    )
    resume.add_argument("--run-id", required=True, type=UUID)
    resume.add_argument("--manifest", required=True, type=Path)
    resume.add_argument("--execute", action="store_true")
    resume.add_argument("--confirm-environment", choices=("development", "test"))
    resume.add_argument("--fingerprint")
    resume.add_argument("--champion-binding-id", type=UUID)
    reproduce = commands.add_parser(
        "reproduce",
        help="Read-only deterministic rebuild of one completed supervised candidate.",
    )
    reproduce.add_argument("--run-id", required=True, type=UUID)
    return result


async def _run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    require_controlled_environment()
    manifest_commands = {"plan", "monitor", "run", "resume"}
    raw = _read_manifest(args.manifest) if args.command in manifest_commands else None
    definition = (
        PipelineDefinition.model_validate_json(raw)
        if raw and args.command in {"plan", "resume"}
        else None
    )
    protocol = (
        MonitoringProtocol.model_validate_json(raw) if raw and args.command == "monitor" else None
    )
    settings = Settings()
    database = Database(settings, command_timeout=60)
    telemetry = Telemetry(settings, database, service_name="vehicle-platform-mlops")
    try:
        try:
            if definition is not None and args.command == "plan":
                result = await (
                    plan_anomaly(database, definition)
                    if definition.kind is PipelineKind.ANOMALY
                    else plan_supervised(database, definition)
                )
                return result, 0 if result["status"] == "READY_TO_REVIEW" else 2
            if args.command == "run":
                if raw is None:
                    raise ValueError("manifest is required")
                result = await run_pipeline(
                    database,
                    PipelineDefinition.model_validate_json(raw),
                    execute=args.execute,
                    confirmed_environment=args.confirm_environment,
                    confirmed_fingerprint=args.fingerprint,
                    champion_binding_id=args.champion_binding_id,
                    telemetry=telemetry,
                )
                return result, 0 if result.get("execution") == "NOT_STARTED" or result.get(
                    "status"
                ) in {"DRY_RUN", "COMPLETED"} else 2
            if args.command == "resume" and definition is not None:
                result = await resume_pipeline(
                    database,
                    definition,
                    args.run_id,
                    execute=args.execute,
                    confirmed_environment=args.confirm_environment,
                    confirmed_fingerprint=args.fingerprint,
                    champion_binding_id=args.champion_binding_id,
                    telemetry=telemetry,
                )
                return result, 0 if result.get("execution") == "NOT_STARTED" or result.get(
                    "status"
                ) in {"COMPLETED", "IDEMPOTENT_REPLAY", "RUN_STILL_OWNED"} else 2
            if args.command == "reproduce":
                result = await reproduce_supervised_run(database, args.run_id, telemetry=telemetry)
                return result, 0 if result["receipt"]["status"] == "REPRODUCED" else 2
            if protocol is not None:
                return await monitor_receipts(database, protocol, telemetry=telemetry), 0
            if args.command == "inspect":
                return await ControlPlaneRepository(database).inspect_run(args.run_id), 0
            if args.command == "proposal":
                return await ControlPlaneRepository(database).inspect_proposal(args.proposal_id), 0
            if args.command == "review":
                environment = require_controlled_environment()
                if not args.execute:
                    return {
                        "schema_version": "phase10-review-v1",
                        "execution": "NOT_STARTED",
                        "proposal_id": str(args.proposal_id),
                        "decision": args.decision,
                        "serving_action": "NONE",
                        "real_world_predictive_validity": "NOT_ESTABLISHED",
                    }, 0
                if (
                    args.confirm_environment != environment
                    or args.confirm_proposal_checksum != args.proposal_checksum
                ):
                    raise ValueError("REVIEW_CONFIRMATION_MISMATCH")
                reviewer_id, reviewer_role = authenticated_reviewer()
                state = await ControlPlaneRepository(database).review_proposal(
                    args.proposal_id,
                    proposal_checksum=args.proposal_checksum,
                    decision=args.decision,
                    reviewer_id=reviewer_id,
                    reviewer_role=reviewer_role,
                    reason=args.reason,
                )
                telemetry.mlops_review_events.add(1, {"decision": args.decision})
                return {
                    "schema_version": "phase10-review-v1",
                    "status": state,
                    "proposal_id": str(args.proposal_id),
                    "reviewer_id": reviewer_id,
                    "serving_action": "NONE",
                    "real_world_predictive_validity": "NOT_ESTABLISHED",
                }, 0
            if args.command == "rollback-plan":
                result = await plan_rollback(
                    database,
                    args.proposal_id,
                    args.target_binding_id,
                    execute=args.execute,
                    confirmed_environment=args.confirm_environment,
                    confirmed_proposal_checksum=args.confirm_proposal_checksum,
                )
                if result.get("status") in {
                    "READY_FOR_SEPARATE_9D_REVIEW",
                    "BLOCKED",
                }:
                    telemetry.mlops_rollback_plans.add(1, {"state": result["status"]})
                return result, 0
            if args.command == "rollback-inspect":
                result = await inspect_rollback_plan(database, args.plan_id)
                return result, 0 if result["status"] == "READY_FOR_SEPARATE_9D_REVIEW" else 2
            raise ValueError("unsupported command")
        finally:
            if args.metrics_file is not None:
                write_exclusive_bytes(
                    args.metrics_file.parent,
                    Path(args.metrics_file.name),
                    telemetry.render_metrics(),
                )
    finally:
        telemetry.shutdown()
        await database.close()


def main() -> None:
    args = parser().parse_args()
    try:
        report, code = asyncio.run(_run(args))
    except (ValueError, RuntimeError, OSError, ValidationError, SQLAlchemyError):
        print(json.dumps({"status": "BLOCKED", "reason": "INVALID_OR_UNAVAILABLE_INPUT"}))
        sys.exit(2)
    print(json.dumps(report, sort_keys=True, allow_nan=False, default=str))
    sys.exit(code)


if __name__ == "__main__":
    main()
