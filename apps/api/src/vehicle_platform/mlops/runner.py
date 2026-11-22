"""Explicit, fenced Phase 10 executions through existing 9A/9B/9G paths."""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any, TypedDict
from uuid import UUID, uuid4

from vehicle_platform.evaluation.contracts import SourceRole
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.mlops.anomaly_comparison import compare_anomaly
from vehicle_platform.mlops.comparison import compare_supervised
from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind, RunState
from vehicle_platform.mlops.executor import (
    evaluate_anomaly_job,
    execute_anomaly_fit_job,
    execute_supervised_job,
)
from vehicle_platform.mlops.planner import plan_anomaly, plan_supervised
from vehicle_platform.mlops.policy import require_controlled_environment
from vehicle_platform.mlops.report_store import write_report
from vehicle_platform.mlops.repository import ControlPlaneConflict, ControlPlaneRepository


class StageOwnership(TypedDict):
    run_id: UUID
    token: UUID
    fence: int
    attempt: int


def _candidate_dossier(
    definition: PipelineDefinition,
    plan: dict[str, Any],
    result: dict[str, Any],
    comparison: dict[str, Any],
    limitations: list[str],
    environment: str,
) -> dict[str, Any]:
    """Build the concise, immutable scientific dossier covered by proposal checksum."""
    challenger_metrics = comparison.get("challenger") or comparison.get("challenger_metrics")
    evaluation_summary = result.get("evaluation_summary")
    holdout = (
        challenger_metrics
        if isinstance(challenger_metrics, dict)
        else evaluation_summary
        if isinstance(evaluation_summary, dict)
        else None
    )
    return {
        "schema_version": "phase10-candidate-dossier-v1",
        "candidate_kind": definition.kind.value,
        "candidate_version_id": result.get("model_version_id", result.get("detector_version_id")),
        "task_or_family": definition.task.value if definition.task else definition.family,
        "horizon": "next_pull" if definition.task else None,
        "source_role": definition.source_role.value,
        "dataset_lineage": {
            "source_fingerprint": plan.get("source_fingerprint"),
            "dataset_checksum": plan.get("dataset_checksum", plan.get("reference_checksum")),
            "evaluation_source_fingerprint": plan.get("evaluation_source_fingerprint"),
            "evaluation_dataset_checksum": plan.get("evaluation_dataset_checksum"),
            "feature_set_version": plan.get("feature_set_version"),
            "feature_checksum": plan.get("feature_checksum"),
            "label_checksum": plan.get("label_checksum"),
            "training_cutoff": definition.cutoff.isoformat(),
            "evaluation_cutoff": (
                definition.evaluation_cutoff.isoformat()
                if definition.evaluation_cutoff is not None
                else None
            ),
            "training_rows": plan.get("labeled_rows", plan.get("reference_rows")),
            "training_sessions": plan.get("sessions", plan.get("reference_sessions")),
            "evaluation_rows": plan.get("evaluation_rows"),
            "positive_labels": plan.get("positive_count"),
            "negative_labels": plan.get("negative_count"),
            "excluded_rows": plan.get("excluded_count"),
        },
        "training_family": result.get("training_family", definition.method),
        "holdout_status": comparison.get("status"),
        "holdout_performance_and_uncertainty": holdout,
        "cross_family_specificity": (
            evaluation_summary.get("cross_family_alerts")
            if isinstance(evaluation_summary, dict)
            else None
        ),
        "artifact_checksum": result.get("artifact_checksum"),
        "scientific_readiness": result.get("scientific_readiness"),
        "applicability_limits": limitations,
        "intended_environment": environment,
        "review_status": "REVIEW_REQUIRED",
        "serving_approval": "PENDING_SEPARATE_AUTHORIZED_PHASE_9D_ACTION",
        "serving_action": "NONE",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "real_world_mechanical_failure_predictive_reliability": "NOT_ESTABLISHED",
        "scientific_limitations": limitations,
    }


def _reuse_checkpoint(
    checkpoint: dict[str, Any] | None,
    *,
    parent_run_id: UUID | None,
    name: str,
    input_checksum: str,
    expected_output: dict[str, Any],
) -> bool:
    if checkpoint is None:
        return False
    output = checkpoint.get("output_body")
    if (
        parent_run_id is None
        or checkpoint.get("checkpoint_source_run_id") != parent_run_id
        or checkpoint.get("state") != "SUCCEEDED"
        or checkpoint.get("step_name") != name
        or checkpoint.get("input_checksum") != input_checksum
        or not isinstance(output, dict)
        or output != expected_output
        or checkpoint.get("output_checksum") != stable_hash(output)
    ):
        raise ControlPlaneConflict("RESUME_CHECKPOINT_MISMATCH")
    return True


async def _execute_pipeline(
    database: Database,
    definition: PipelineDefinition,
    *,
    execute: bool = False,
    confirmed_environment: str | None = None,
    confirmed_fingerprint: str | None = None,
    champion_binding_id: UUID | None = None,
    checkpoint_retry_id: UUID | None = None,
) -> dict[str, Any]:
    """Plan by default; an exact explicit confirmation permits one controlled execution."""
    environment = require_controlled_environment()
    if not execute:
        if definition.kind is PipelineKind.SUPERVISED:
            if definition.task is None:
                raise ValueError("the supervised runner requires a task")
            plan = await plan_supervised(database, definition)
        else:
            plan = await plan_anomaly(database, definition)
        return {
            "schema_version": "phase10-dry-run-v1",
            "execution": "NOT_STARTED",
            "plan": plan,
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
    if confirmed_environment != environment or confirmed_fingerprint != definition.fingerprint:
        raise ValueError("EXECUTION_CONFIRMATION_MISMATCH")
    if definition.source_role is not SourceRole.SYNTHETIC:
        raise ValueError("SOURCE_ROLE_UNSUPPORTED")
    repository = ControlPlaneRepository(database)
    if checkpoint_retry_id is None:
        existing = await repository.find_exact_run(definition)
        if existing is not None and (
            existing["state"] != RunState.PLANNED.value or existing["has_steps"]
        ):
            return {
                "schema_version": "phase10-run-v1",
                "status": "EXISTING_RUN",
                "run_id": str(existing["run_id"]),
                "state": existing["state"],
                "idempotent_replay": True,
                "serving_action": "NONE",
                "real_world_predictive_validity": "NOT_ESTABLISHED",
            }
    if definition.kind is PipelineKind.SUPERVISED:
        if definition.task is None:
            raise ValueError("the supervised runner requires a task")
        plan = await plan_supervised(database, definition)
    else:
        plan = await plan_anomaly(database, definition)
    if plan.get("status") != "READY_TO_REVIEW":
        return {
            "schema_version": "phase10-run-v1",
            "status": "BLOCKED_BY_POLICY",
            "reason": str(plan.get("reason", "PLAN_NOT_ELIGIBLE")),
            "plan_fingerprint": definition.fingerprint,
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }

    checkpoint_events: dict[str, dict[str, Any]] = {}
    parent_run_id: UUID | None = None
    if checkpoint_retry_id is None:
        run_id, created = await repository.create_run(definition)
    else:
        run_id = checkpoint_retry_id
        created = True
        existing = await repository.inspect_run(run_id)
        if (
            existing["run"]["definition_fingerprint"] != definition.fingerprint
            or existing["run"]["parent_run_id"] is None
        ):
            raise ControlPlaneConflict("retry attempt does not match its immutable definition")
        if existing["run"]["state"] != RunState.PLANNED.value:
            return {
                "schema_version": "phase10-run-v1",
                "status": "EXISTING_RUN",
                "run_id": str(run_id),
                "state": existing["run"]["state"],
                "idempotent_replay": True,
                "serving_action": "NONE",
                "real_world_predictive_validity": "NOT_ESTABLISHED",
            }
        parent_run_id = existing["run"]["parent_run_id"]
        checkpoint_events = {
            str(item["step_name"]): item
            for item in existing["steps"]
            if item.get("checkpoint_source_run_id") is not None
        }
    if checkpoint_retry_id is None and not created:
        existing = await repository.inspect_run(run_id)
        if existing["run"]["state"] != RunState.PLANNED.value or existing["steps"]:
            return {
                "schema_version": "phase10-run-v1",
                "status": "EXISTING_RUN",
                "run_id": str(run_id),
                "state": existing["run"]["state"],
                "idempotent_replay": True,
                "serving_action": "NONE",
                "real_world_predictive_validity": "NOT_ESTABLISHED",
            }
    try:
        token, fence = await repository.claim(run_id)
    except ControlPlaneConflict:
        if checkpoint_retry_id is None:
            raise
        existing = await repository.inspect_run(run_id)
        if existing["run"]["state"] == RunState.PLANNED.value:
            raise
        return {
            "schema_version": "phase10-run-v1",
            "status": "EXISTING_RUN",
            "run_id": str(run_id),
            "state": existing["run"]["state"],
            "idempotent_replay": True,
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
    await repository.transition(
        run_id,
        token=token,
        fence=fence,
        expected=RunState.CLAIMED,
        target=RunState.RUNNING,
        reason="OPERATOR_CONFIRMED",
    )
    stage: StageOwnership = {"run_id": run_id, "token": token, "fence": fence, "attempt": 1}
    try:
        select_output = {
            "source_role": definition.source_role.value,
            "dataset_checksum": plan.get("dataset_checksum", plan.get("reference_checksum")),
            "evaluation_dataset_checksum": plan["evaluation_dataset_checksum"],
            "row_count": plan.get("labeled_rows", plan.get("reference_rows")),
            "evaluation_row_count": plan["evaluation_rows"],
        }
        if not _reuse_checkpoint(
            checkpoint_events.get("select"),
            parent_run_id=parent_run_id,
            name="select",
            input_checksum=definition.expected_source_fingerprint,
            expected_output=select_output,
        ):
            await repository.record_step(
                **stage,
                name="select",
                state="RUNNING",
                input_checksum=definition.expected_source_fingerprint,
            )
            await repository.record_step(
                **stage,
                name="select",
                state="SUCCEEDED",
                input_checksum=definition.expected_source_fingerprint,
                output=select_output,
            )
        validate_output = {
            "plan_fingerprint": definition.fingerprint,
            "plan_status": plan["status"],
            "plan_reason": plan["reason"],
            "feature_checksum": plan["feature_checksum"],
            "label_checksum": plan["label_checksum"],
            "training_source_fingerprint": plan["source_fingerprint"],
            "evaluation_source_fingerprint": plan["evaluation_source_fingerprint"],
        }
        if not _reuse_checkpoint(
            checkpoint_events.get("validate"),
            parent_run_id=parent_run_id,
            name="validate",
            input_checksum=definition.fingerprint,
            expected_output=validate_output,
        ):
            await repository.record_step(
                **stage,
                name="validate",
                state="RUNNING",
                input_checksum=definition.fingerprint,
            )
            await repository.record_step(
                **stage,
                name="validate",
                state="SUCCEEDED",
                input_checksum=definition.fingerprint,
                output=validate_output,
            )
        if definition.kind is PipelineKind.SUPERVISED:
            result = await execute_supervised_job(
                database, definition, run_id=run_id, token=token, fence=fence
            )
            evaluation_gate_passed = (
                result.get("scientific_readiness", {}).get("synthetic_calibration")
                == "SYNTHETIC_ONLY"
            )
        else:
            fit_result = await execute_anomaly_fit_job(
                database, definition, run_id=run_id, token=token, fence=fence
            )
            evaluation_input = definition.expected_evaluation_checksum
            if evaluation_input is None:
                raise ValueError("MISSING_EVALUATION")
            await repository.record_step(
                **stage,
                name="evaluate",
                state="RUNNING",
                input_checksum=evaluation_input,
            )
            evaluation_result = await evaluate_anomaly_job(
                database,
                definition,
                run_id=run_id,
                detector_version_id=UUID(fit_result["detector_version_id"]),
            )
            evaluation_gate_passed = evaluation_result["evaluation_status"] == "SYNTHETIC_EVALUATED"
            await repository.record_step(
                **stage,
                name="evaluate",
                state="SUCCEEDED",
                input_checksum=evaluation_input,
                output={
                    "evaluation_status": evaluation_result["evaluation_status"],
                    "scientific_readiness": evaluation_result["scientific_readiness"],
                    "report_content_checksum": evaluation_result["report_content_checksum"],
                    "report_file_checksum": evaluation_result["report_file_checksum"],
                    "report_bytes": evaluation_result["report_bytes"],
                    "evaluation_dataset_checksum": evaluation_result["evaluation_dataset_checksum"],
                    "evaluation_source_fingerprint": evaluation_result[
                        "evaluation_source_fingerprint"
                    ],
                },
            )
            result = {
                **fit_result,
                "evaluation_status": evaluation_result["evaluation_status"],
                "scientific_readiness": evaluation_result["scientific_readiness"],
                "evaluation_report_checksum": evaluation_result["report_content_checksum"],
                "evaluation_report_file_checksum": evaluation_result["report_file_checksum"],
                "evaluation_dataset_checksum": evaluation_result["evaluation_dataset_checksum"],
                "evaluation_source_fingerprint": evaluation_result["evaluation_source_fingerprint"],
                "evaluation_summary": evaluation_result["evaluation_summary"],
            }
        comparison_input = stable_hash(
            [result["artifact_checksum"], definition.expected_evaluation_checksum]
        )
        await repository.record_step(
            **stage,
            name="compare",
            state="RUNNING",
            input_checksum=comparison_input,
        )
        comparison: dict[str, object]
        if not evaluation_gate_passed:
            comparison = {
                "schema_version": "phase10-comparison-v1",
                "status": "NOT_COMPARABLE",
                "reason": "EVALUATION_SUPPORT_INSUFFICIENT",
                "serving_action": "NONE",
                "real_world_predictive_validity": "NOT_ESTABLISHED",
            }
        elif definition.kind is PipelineKind.SUPERVISED:
            comparison = (
                await compare_supervised(
                    database,
                    definition,
                    champion_binding_id=champion_binding_id,
                    challenger_version_id=UUID(result["model_version_id"]),
                )
                if champion_binding_id is not None
                else {
                    "schema_version": "phase10-comparison-v1",
                    "status": "NOT_COMPARABLE",
                    "reason": "NO_CHAMPION_BINDING_SUPPLIED",
                    "serving_action": "NONE",
                    "real_world_predictive_validity": "NOT_ESTABLISHED",
                    "limitation": "No incumbent was selected for the matched offline comparison.",
                }
            )
        else:
            comparison = await compare_anomaly(
                database,
                definition,
                champion_binding_id=champion_binding_id,
                challenger_version_id=UUID(result["detector_version_id"]),
            )
        if comparison["status"] == "NOT_COMPARABLE":
            await repository.record_step(
                **stage,
                name="compare",
                state="SKIPPED_INELIGIBLE",
                input_checksum=comparison_input,
                output=comparison,
            )
        else:
            await repository.record_step(
                **stage,
                name="compare",
                state="SUCCEEDED",
                input_checksum=comparison_input,
                output=comparison,
            )
        limitations = (
            [
                "Synthetic anomaly injections do not establish real-world detection performance.",
                "Anomaly scores are not engine-health percentages or confirmed diagnoses.",
                "Unlabeled real-world telemetry cannot establish accuracy, recall or calibration.",
                "Real-world mechanical failure predictive reliability remains NOT_ESTABLISHED.",
            ]
            if definition.kind is PipelineKind.ANOMALY
            else [
                "Synthetic calibration does not prove real-world predictive validity.",
                "Supervised scores are not mechanical failure probabilities.",
                "Unlabeled telemetry cannot establish accuracy, recall or calibration.",
                "Real-world mechanical failure predictive reliability remains NOT_ESTABLISHED.",
            ]
        )
        proposal_status = "REVIEW_REQUIRED" if evaluation_gate_passed else "INSUFFICIENT_SUPPORT"
        proposal_id: UUID | None = None
        proposal_checksum: str | None = None
        if evaluation_gate_passed:
            candidate_version_id = UUID(
                result.get("model_version_id", result.get("detector_version_id"))
            )
            evaluation_checksum = result.get(
                "evaluation_report_checksum", result.get("report_content_checksum")
            )
            if not isinstance(evaluation_checksum, str):
                raise ValueError("EVALUATION_RECEIPT_MISSING")
            comparison_checksum = stable_hash(comparison)
            candidate_dossier = _candidate_dossier(
                definition,
                plan,
                result,
                comparison,
                limitations,
                environment,
            )
            proposal_body = {
                "schema_version": "phase10-proposal-v1",
                "run_id": str(run_id),
                "definition_fingerprint": definition.fingerprint,
                "candidate_kind": definition.kind.value,
                "candidate_version_id": str(candidate_version_id),
                "artifact_checksum": result["artifact_checksum"],
                "evaluation_checksum": evaluation_checksum,
                "comparison_checksum": comparison_checksum,
                "comparison_status": comparison["status"],
                "candidate_dossier": candidate_dossier,
                "candidate_dossier_checksum": stable_hash(candidate_dossier),
                "source_role": definition.source_role.value,
                "scientific_readiness": result["scientific_readiness"],
                "scientific_limitations": limitations,
                "status": "REVIEW_REQUIRED",
                "serving_permission": False,
                "serving_action": "NONE",
                "real_world_predictive_validity": "NOT_ESTABLISHED",
            }
            proposal_id, proposal_checksum, _ = await repository.create_proposal(
                run_id,
                token=token,
                fence=fence,
                definition_fingerprint=definition.fingerprint,
                candidate_kind=definition.kind.value,
                candidate_version_id=candidate_version_id,
                artifact_checksum=str(result["artifact_checksum"]),
                evaluation_checksum=evaluation_checksum,
                comparison_checksum=comparison_checksum,
                body=proposal_body,
            )
        review_report = {
            "schema_version": "phase10-review-report-v1",
            "definition_fingerprint": definition.fingerprint,
            "run_id": str(run_id),
            "execution_result": result,
            "comparison": comparison,
            "review_proposal": {
                "status": proposal_status,
                "candidate_version_id": result.get(
                    "model_version_id", result.get("detector_version_id")
                ),
                "proposal_id": str(proposal_id) if proposal_id else None,
                "proposal_checksum": proposal_checksum,
                "serving_permission": False,
                "approval_required": "SEPARATE_AUTHORIZED_PHASE_9D_OPERATOR_ACTION",
                "scientific_limitations": limitations,
            },
            "scientific_limitations": limitations,
            "real_world_predictive_validity": "NOT_ESTABLISHED",
            "serving_action": "NONE",
        }
        report_id = uuid4()
        report_checksum, report_bytes = write_report(report_id, review_report)
        report_input = stable_hash([comparison, report_checksum])
        await repository.record_step(
            **stage,
            name="report",
            state="RUNNING",
            input_checksum=report_input,
        )
        await repository.record_step(
            **stage,
            name="report",
            state="SUCCEEDED",
            input_checksum=report_input,
            output={
                "report_id": str(report_id),
                "report_file_checksum": report_checksum,
                "report_bytes": report_bytes,
                "proposal_status": proposal_status,
                "proposal_id": str(proposal_id) if proposal_id else None,
                "proposal_checksum": proposal_checksum,
                "serving_permission": False,
            },
        )
        if evaluation_gate_passed:
            await repository.complete_run(run_id, token=token, fence=fence)
        else:
            await repository.transition(
                run_id,
                token=token,
                fence=fence,
                expected=RunState.RUNNING,
                target=RunState.INSUFFICIENT_SUPPORT,
                reason="EVALUATION_SUPPORT_LOW",
            )
        return {
            "schema_version": "phase10-run-v1",
            "status": "COMPLETED" if evaluation_gate_passed else "INSUFFICIENT_SUPPORT",
            "run_id": str(run_id),
            "definition_fingerprint": definition.fingerprint,
            "plan": plan,
            "execution_result": result,
            "comparison": comparison,
            "review_report_id": str(report_id),
            "review_report_checksum": report_checksum,
            "review_proposal_status": proposal_status,
            "proposal_id": str(proposal_id) if proposal_id else None,
            "proposal_checksum": proposal_checksum,
            "resumed_from_run_id": str(parent_run_id) if checkpoint_retry_id else None,
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
    except Exception as error:
        reason = _reason_code(error)
        try:
            inspection = await repository.inspect_run(run_id)
            latest: dict[str, dict[str, Any]] = {}
            for event in inspection["steps"]:
                latest[str(event["step_name"])] = event
            active = next(
                ((name, row) for name, row in latest.items() if row["state"] == "RUNNING"),
                None,
            )
            if active is not None:
                name, row = active
                await repository.record_step(
                    run_id=run_id,
                    token=token,
                    fence=fence,
                    name=name,
                    attempt=int(row["step_attempt"]),
                    state="FAILED",
                    input_checksum=str(row["input_checksum"]),
                    output={"reason": reason},
                )
        except ControlPlaneConflict:
            pass
        try:
            await repository.transition(
                run_id,
                token=token,
                fence=fence,
                expected=RunState.RUNNING,
                target=RunState.FAILED,
                reason=reason,
            )
        except ControlPlaneConflict:
            pass
        return {
            "schema_version": "phase10-run-v1",
            "status": "FAILED",
            "reason": reason,
            "run_id": str(run_id),
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }


async def run_pipeline(
    database: Database,
    definition: PipelineDefinition,
    *,
    execute: bool = False,
    confirmed_environment: str | None = None,
    confirmed_fingerprint: str | None = None,
    champion_binding_id: UUID | None = None,
    telemetry: Any | None = None,
    checkpoint_retry_id: UUID | None = None,
) -> dict[str, Any]:
    """Emit bounded lifecycle metrics and traces around one controlled runner call."""
    started = perf_counter()
    kind = definition.kind.value
    if telemetry is not None:
        telemetry.mlops_in_flight.add(1, {"kind": kind})
        span_context = telemetry.tracer.start_as_current_span("mlops.pipeline.run")
    else:
        from opentelemetry import trace

        span_context = trace.get_tracer("vehicle_platform.mlops").start_as_current_span(
            "mlops.pipeline.run"
        )
    try:
        with span_context as span:
            span.set_attribute("mlops.pipeline.kind", kind)
            span.set_attribute("mlops.pipeline.execute", execute)
            result = await _execute_pipeline(
                database,
                definition,
                execute=execute,
                confirmed_environment=confirmed_environment,
                confirmed_fingerprint=confirmed_fingerprint,
                champion_binding_id=champion_binding_id,
                checkpoint_retry_id=checkpoint_retry_id,
            )
            if telemetry is not None and result.get("run_id") is not None:
                if result.get("status") != "EXISTING_RUN":
                    inspection = await ControlPlaneRepository(database).inspect_run(
                        UUID(str(result["run_id"]))
                    )
                    for event in inspection["steps"]:
                        step_state = str(event["state"])
                        bounded_state = (
                            step_state
                            if step_state
                            in {"RUNNING", "SUCCEEDED", "SKIPPED_INELIGIBLE", "FAILED", "CANCELLED"}
                            else "FAILED"
                        )
                        telemetry.mlops_stage_events.add(
                            1,
                            {
                                "stage": str(event["step_name"]),
                                "state": bounded_state,
                            },
                        )
            raw_state = str(result.get("status", result.get("execution", "FAILED")))
            state = (
                raw_state
                if raw_state
                in {
                    "NOT_STARTED",
                    "COMPLETED",
                    "INSUFFICIENT_SUPPORT",
                    "FAILED",
                    "BLOCKED_BY_POLICY",
                    "EXISTING_RUN",
                }
                else "FAILED"
            )
            span.set_attribute("mlops.pipeline.state", state)
            if telemetry is not None:
                telemetry.mlops_runs.add(1, {"kind": kind, "state": state})
            return result
    except BaseException:
        if telemetry is not None:
            telemetry.mlops_runs.add(1, {"kind": kind, "state": "FAILED"})
        raise
    finally:
        if telemetry is not None:
            telemetry.mlops_duration.record(perf_counter() - started, {"kind": kind})
            telemetry.mlops_in_flight.add(-1, {"kind": kind})


def _reason_code(error: Exception) -> str:
    name = type(error).__name__.upper()
    return name[:80] if name.isascii() and name.isalnum() else "PIPELINE_FAILURE"


async def _resume_pipeline(
    database: Database,
    definition: PipelineDefinition,
    run_id: UUID,
    *,
    execute: bool = False,
    confirmed_environment: str | None = None,
    confirmed_fingerprint: str | None = None,
    champion_binding_id: UUID | None = None,
    telemetry: Any | None = None,
) -> dict[str, Any]:
    """Replay receipts, claim a plan, or retry an expired pre-fit checkpoint safely."""
    environment = require_controlled_environment()
    repository = ControlPlaneRepository(database)
    inspection = await repository.inspect_run(run_id)
    if inspection["run"]["definition_fingerprint"] != definition.fingerprint:
        raise ControlPlaneConflict("resume definition fingerprint differs from stored run")
    if not execute:
        return {
            "schema_version": "phase10-resume-v1",
            "execution": "NOT_STARTED",
            "run_id": str(run_id),
            "state": inspection["run"]["state"],
            "resume_action": "NONE",
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
    if confirmed_environment != environment or confirmed_fingerprint != definition.fingerprint:
        raise ValueError("EXECUTION_CONFIRMATION_MISMATCH")
    state = str(inspection["run"]["state"])
    if state in {RunState.CLAIMED.value, RunState.RUNNING.value}:
        expiry = inspection["run"]["lease_expires_at"]
        if expiry is not None and expiry > datetime.now(UTC):
            return {
                "schema_version": "phase10-resume-v1",
                "status": "RUN_STILL_OWNED",
                "run_id": str(run_id),
                "resume_action": "NONE",
                "serving_action": "NONE",
                "real_world_predictive_validity": "NOT_ESTABLISHED",
            }
        await repository.fail_expired_run(run_id)
        try:
            retry_id, _ = await repository.create_checkpoint_retry(run_id)
        except ControlPlaneConflict:
            recovered = await repository.inspect_run(run_id)
            return {
                "schema_version": "phase10-resume-v1",
                "status": "FAILED_SAFE_RECOVERY",
                "run_id": str(run_id),
                "state": recovered["run"]["state"],
                "reason": "LEASE_EXPIRED_UNRECONCILED",
                "resume_action": "NEW_DEFINITION_REQUIRED",
                "serving_action": "NONE",
                "real_world_predictive_validity": "NOT_ESTABLISHED",
            }
        retry = await run_pipeline(
            database,
            definition,
            execute=True,
            confirmed_environment=environment,
            confirmed_fingerprint=definition.fingerprint,
            champion_binding_id=champion_binding_id,
            telemetry=telemetry,
            checkpoint_retry_id=retry_id,
        )
        if retry.get("status") == "EXISTING_RUN":
            return {
                "schema_version": "phase10-resume-v1",
                **retry,
                "resume_action": "RETRY_ALREADY_OWNED",
                "serving_action": "NONE",
                "real_world_predictive_validity": "NOT_ESTABLISHED",
            }
        return {
            "schema_version": "phase10-resume-v1",
            **retry,
            "resume_action": "VERIFIED_CHECKPOINT_RETRY",
            "resumed_from_run_id": str(run_id),
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
    if (
        state == RunState.PLANNED.value
        and inspection["steps"]
        and inspection["run"].get("parent_run_id") is None
    ):
        raise ControlPlaneConflict("an unclaimed plan cannot already have stage receipts")
    if state != RunState.PLANNED.value:
        return {
            "schema_version": "phase10-resume-v1",
            "status": "IDEMPOTENT_REPLAY",
            "run_id": str(run_id),
            "state": state,
            "inspection": inspection,
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
    return await run_pipeline(
        database,
        definition,
        execute=True,
        confirmed_environment=environment,
        confirmed_fingerprint=definition.fingerprint,
        champion_binding_id=champion_binding_id,
        telemetry=telemetry,
        checkpoint_retry_id=(
            run_id if inspection["run"].get("parent_run_id") is not None else None
        ),
    )


async def resume_pipeline(
    database: Database,
    definition: PipelineDefinition,
    run_id: UUID,
    *,
    execute: bool = False,
    confirmed_environment: str | None = None,
    confirmed_fingerprint: str | None = None,
    champion_binding_id: UUID | None = None,
    telemetry: Any | None = None,
) -> dict[str, Any]:
    """Trace bounded replay/recovery outcomes and count only safe recovery states."""
    started = perf_counter()
    if telemetry is not None:
        span_context = telemetry.tracer.start_as_current_span("mlops.pipeline.resume")
    else:
        from opentelemetry import trace

        span_context = trace.get_tracer("vehicle_platform.mlops").start_as_current_span(
            "mlops.pipeline.resume"
        )
    try:
        with span_context as span:
            span.set_attribute("mlops.pipeline.kind", definition.kind.value)
            span.set_attribute("mlops.pipeline.execute", execute)
            result = await _resume_pipeline(
                database,
                definition,
                run_id,
                execute=execute,
                confirmed_environment=confirmed_environment,
                confirmed_fingerprint=confirmed_fingerprint,
                champion_binding_id=champion_binding_id,
                telemetry=telemetry,
            )
            state = str(result.get("status", result.get("execution", "FAILED")))
            span.set_attribute("mlops.pipeline.resume_state", state[:48])
            if telemetry is not None and state in {
                "FAILED_SAFE_RECOVERY",
                "IDEMPOTENT_REPLAY",
                "RUN_STILL_OWNED",
            }:
                telemetry.mlops_recovery_events.add(1, {"state": state})
            return result
    finally:
        if telemetry is not None:
            telemetry.mlops_duration.record(perf_counter() - started, {"kind": "resume"})
