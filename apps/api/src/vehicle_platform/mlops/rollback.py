"""Readiness planning for an explicitly reviewed Phase 9D rollback."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from vehicle_platform.core.config import Settings
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.mlops.policy import require_controlled_environment
from vehicle_platform.mlops.repository import ControlPlaneRepository
from vehicle_platform.predictions.domain import PredictionError, ServingEventType
from vehicle_platform.predictions.service import PredictionService


async def plan_rollback(
    database: Database,
    proposal_id: UUID,
    target_binding_id: UUID,
    *,
    execute: bool = False,
    confirmed_environment: str | None = None,
    confirmed_proposal_checksum: str | None = None,
) -> dict[str, Any]:
    """Verify a historic compatible target and optionally persist a non-serving plan."""
    environment = require_controlled_environment()
    proposal_repository = ControlPlaneRepository(database)
    proposal_inspection = await proposal_repository.inspect_proposal(proposal_id)
    proposal = proposal_inspection["proposal"]
    if proposal_inspection["state"] != "APPROVED_FOR_CONTROLLED_REVIEW":
        raise ValueError("ROLLBACK_PROPOSAL_REQUIRES_HUMAN_REVIEW")
    if proposal["run_state"] != "COMPLETED" or proposal["source_role"] != "synthetic":
        raise ValueError("ROLLBACK_PROPOSAL_IS_NOT_ELIGIBLE")

    service = PredictionService(Settings(), database)
    try:
        target = await service.repository.binding(target_binding_id)
        if target is None:
            raise ValueError("ROLLBACK_TARGET_NOT_FOUND")
        if (
            target.environment != environment
            or target.latest_event_type is not ServingEventType.SUPERSEDED
        ):
            raise ValueError("ROLLBACK_TARGET_IS_STALE_OR_REVOKED")
        target_version_id = target.model_version_id or target.detector_version_id
        expected_kind = "supervised" if target.result_kind == "next_pull" else "anomaly"
        if (
            expected_kind != proposal["candidate_kind"]
            or target.source_role.value != proposal["source_role"]
        ):
            raise ValueError("ROLLBACK_TARGET_IS_INCOMPATIBLE_WITH_PROPOSAL")
        if target_version_id is None:
            raise ValueError("ROLLBACK_TARGET_HAS_NO_VERSION")
        candidate = await service.inspect_candidate(target.result_kind, target_version_id)
        if (
            candidate.artifact_checksum != target.artifact_checksum
            or candidate.feature_set_version != target.feature_set_version
            or candidate.feature_set_checksum != target.feature_set_checksum
            or candidate.schema_checksum != target.schema_checksum
            or candidate.source_role is not target.source_role
            or candidate.validation_status != "PASS"
        ):
            raise ValueError("ROLLBACK_TARGET_ARTIFACT_IS_STALE")
        bindings = await service.repository.bindings_for_slot(
            target.result_kind,
            target.subject_key,
            target.source_role,
            target.environment,
            target.scope,
        )
        active = [binding for binding in bindings if binding.is_active]
        if len(active) != 1 or active[0].id == target.id:
            raise ValueError("ROLLBACK_ACTIVE_BINDING_IS_NOT_UNIQUE")
        current = active[0]
        plan_body: dict[str, object] = {
            "schema_version": "phase10-rollback-plan-v1",
            "proposal_id": str(proposal_id),
            "proposal_checksum": str(proposal["content_checksum"]),
            "candidate_kind": expected_kind,
            "target_binding_id": str(target.id),
            "target_event_id": str(target.latest_event_id),
            "target_version_id": str(target_version_id),
            "target_artifact_checksum": target.artifact_checksum,
            "target_feature_set_version": target.feature_set_version,
            "target_feature_set_checksum": target.feature_set_checksum,
            "target_schema_checksum": target.schema_checksum,
            "target_latest_event_type": target.latest_event_type.value,
            "expected_active_binding_id": str(current.id),
            "expected_active_event_id": str(current.latest_event_id),
            "expected_active_version_id": str(
                current.model_version_id or current.detector_version_id
            ),
            "result_kind": target.result_kind,
            "subject_key": target.subject_key,
            "source_role": target.source_role.value,
            "environment": target.environment,
            "scope": target.scope,
            "candidate_validation": candidate.validation_status,
            "execution_command": "vehicle-prediction rollback",
            "serving_action": "NONE",
            "scientific_limitations": [
                "A rollback readiness plan does not change the active serving binding.",
                "Any rollback requires a separate authorized Phase 9D operator action.",
                "Synthetic evaluation does not establish real-world predictive validity.",
                "Real-world mechanical failure predictive reliability remains NOT_ESTABLISHED.",
            ],
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
        response: dict[str, Any] = {
            "schema_version": "phase10-rollback-plan-v1",
            "status": "READY_FOR_SEPARATE_9D_REVIEW",
            "plan": plan_body,
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
        if not execute:
            response["execution"] = "NOT_STARTED"
            return response
        if (
            confirmed_environment != environment
            or confirmed_proposal_checksum != proposal["content_checksum"]
        ):
            raise ValueError("ROLLBACK_PLAN_CONFIRMATION_MISMATCH")
        plan_id, checksum = await proposal_repository.create_rollback_plan(
            proposal_id,
            target_binding_id=target.id,
            target_event_id=target.latest_event_id,
            expected_active_binding_id=current.id,
            expected_active_event_id=current.latest_event_id,
            body=plan_body,
        )
        response.update({"execution": "PERSISTED", "plan_id": str(plan_id), "checksum": checksum})
        return response
    finally:
        await service.close()


async def inspect_rollback_plan(database: Database, plan_id: UUID) -> dict[str, Any]:
    """Re-check immutable plan lineage against the current 9D binding and artifact state."""
    repository = ControlPlaneRepository(database)
    stored = await repository.inspect_rollback_plan(plan_id)
    row = stored["plan"]
    body = row["body"]
    try:
        current = await plan_rollback(
            database,
            UUID(str(body["proposal_id"])),
            UUID(str(row["target_binding_id"])),
        )
    except (PredictionError, ValueError):
        return {
            "schema_version": "phase10-rollback-inspection-v1",
            "status": "STALE",
            "plan": stored["plan"],
            "readiness": "CURRENT_ARTIFACT_OR_BINDING_REQUIRES_REVIEW",
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
    is_current = stable_hash(current["plan"]) == row["content_checksum"] and current["plan"] == body
    return {
        "schema_version": "phase10-rollback-inspection-v1",
        "status": "READY_FOR_SEPARATE_9D_REVIEW" if is_current else "STALE",
        "plan": stored["plan"],
        "readiness": "CURRENT" if is_current else "CURRENT_ARTIFACT_OR_BINDING_REQUIRES_REVIEW",
        "serving_action": "NONE",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
    }
