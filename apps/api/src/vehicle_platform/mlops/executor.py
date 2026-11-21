"""Internal preclaimed workers using existing model and evaluation paths."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict
from uuid import UUID

from vehicle_platform.anomalies.artifacts import ArtifactStore as DetectorArtifactStore
from vehicle_platform.anomalies.definitions import detector_definition
from vehicle_platform.anomalies.domain import MAX_REFERENCE_ROWS, DetectorLifecycle
from vehicle_platform.anomalies.domain import SourceRole as AnomalySourceRole
from vehicle_platform.anomalies.repository import AnomalyDataRepository
from vehicle_platform.anomalies.service import AnomalyService
from vehicle_platform.evaluation.protocol import default_protocol
from vehicle_platform.evaluation.repository import source_table_digests
from vehicle_platform.evaluation.supervised import evaluate_supervised_task
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import ArtifactStore
from vehicle_platform.ml.domain import ModelState
from vehicle_platform.ml.pipeline import train_task
from vehicle_platform.mlops.anomaly_evaluation import evaluate_anomaly_candidate
from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind
from vehicle_platform.mlops.evaluation import persist_supervised_evaluation
from vehicle_platform.mlops.planner import (
    anomaly_evaluation_checksum,
    anomaly_evaluation_source_fingerprint,
    checkout_is_dirty,
    materialize_supervised_readonly,
)
from vehicle_platform.mlops.policy import require_controlled_environment
from vehicle_platform.mlops.report_store import read_report, write_report
from vehicle_platform.mlops.repository import ControlPlaneConflict, ControlPlaneRepository


class StepOwnership(TypedDict):
    run_id: UUID
    token: UUID
    fence: int
    attempt: int


async def execute_anomaly_fit_job(
    database: Database,
    definition: PipelineDefinition,
    *,
    run_id: UUID,
    token: UUID,
    fence: int,
) -> dict[str, Any]:
    """Fit and verify one synthetic 9C candidate under an already claimed run."""
    require_controlled_environment()
    if (
        definition.kind is not PipelineKind.ANOMALY
        or definition.family is None
        or definition.method is None
        or definition.anchor_pull_id is None
        or definition.source_role.value != "synthetic"
    ):
        raise ValueError("synthetic anomaly definition required")
    if await checkout_is_dirty(definition.git_sha):
        raise ValueError("DIRTY_WORKTREE")
    detector = detector_definition(definition.family, definition.method)
    if len(detector.feature_keys) > definition.budget.max_features:
        raise ValueError("RESOURCE_LIMIT")
    repo = ControlPlaneRepository(database)
    step: StepOwnership = {"run_id": run_id, "token": token, "fence": fence, "attempt": 1}
    checksum = definition.expected_dataset_checksum
    await repo.record_step(**step, name="fit", state="RUNNING", input_checksum=checksum)
    try:
        result = await AnomalyService(database).fit_detector_version(
            anchor_pull_id=definition.anchor_pull_id,
            observation_cutoff=definition.cutoff,
            source_role=AnomalySourceRole.SYNTHETIC,
            family=definition.family,
            method=definition.method,
            git_sha=definition.git_sha,
            expected_reference_checksum=checksum,
            expected_source_fingerprint=definition.expected_source_fingerprint,
            expected_feature_checksum=definition.expected_feature_checksum,
            expected_source_type="synthetic",
            max_reference_rows=min(definition.budget.max_rows, MAX_REFERENCE_ROWS),
            max_reference_sessions=min(definition.budget.max_sessions, MAX_REFERENCE_ROWS),
            max_artifact_bytes=definition.budget.max_artifact_bytes,
        )
    except Exception:
        try:
            await repo.record_step(
                **step,
                name="fit",
                state="FAILED",
                input_checksum=checksum,
                output={"reason": "FIT_FAILED"},
            )
        except ControlPlaneConflict:
            pass  # An expired owner cannot append events.
        raise
    if result.state is not DetectorLifecycle.CANDIDATE or result.artifact_checksum is None:
        await repo.record_step(
            **step,
            name="fit",
            state="FAILED",
            input_checksum=checksum,
            output={"reason": "CANDIDATE_REJECTED", "state": result.state.value},
        )
        raise ValueError("CANDIDATE_REJECTED")
    await repo.record_step(
        **step,
        name="fit",
        state="SUCCEEDED",
        input_checksum=checksum,
        output={
            "detector_version_id": str(result.detector_version_id),
            "reference_dataset_id": str(result.reference_dataset_id),
            "reference_checksum": result.reference_checksum,
            "artifact_checksum": result.artifact_checksum,
        },
    )
    await repo.record_step(
        **step,
        name="verify_artifact",
        state="RUNNING",
        input_checksum=result.artifact_checksum,
    )
    try:
        artifact = await DetectorArtifactStore().load_registered(
            database, str(result.detector_version_id)
        )
        if (
            artifact.artifact_checksum != result.artifact_checksum
            or artifact.reference_checksum != checksum
            or artifact.definition.checksum != detector.checksum
        ):
            raise ValueError("ARTIFACT_TAMPERED")
    except Exception:
        try:
            await repo.record_step(
                **step,
                name="verify_artifact",
                state="FAILED",
                input_checksum=result.artifact_checksum,
                output={"reason": "ARTIFACT_INVALID"},
            )
        except ControlPlaneConflict:
            pass
        raise
    await repo.record_step(
        **step,
        name="verify_artifact",
        state="SUCCEEDED",
        input_checksum=result.artifact_checksum,
        output={
            "detector_version_id": str(result.detector_version_id),
            "artifact_checksum": result.artifact_checksum,
            "reference_checksum": result.reference_checksum,
        },
    )
    return {
        "detector_version_id": str(result.detector_version_id),
        "reference_dataset_id": str(result.reference_dataset_id),
        "reference_checksum": result.reference_checksum,
        "artifact_checksum": result.artifact_checksum,
        "evaluation_status": "NOT_EXECUTED",
        "serving_action": "NONE",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "limitation": "Anomaly score is not an engine-health percentage or a diagnosis.",
    }


async def evaluate_anomaly_job(
    database: Database,
    definition: PipelineDefinition,
    *,
    run_id: UUID,
    detector_version_id: UUID,
) -> dict[str, Any]:
    """Evaluate a registered 9C candidate on an independently labeled frozen cohort."""
    require_controlled_environment()
    if (
        definition.kind is not PipelineKind.ANOMALY
        or definition.family is None
        or definition.method is None
        or definition.evaluation_cutoff is None
        or definition.expected_evaluation_checksum is None
        or definition.expected_evaluation_source_fingerprint is None
        or definition.expected_oracle_checksum is None
        or not definition.evaluation_pull_ids
        or not definition.evaluation_oracle
    ):
        raise ValueError("ANOMALY_EVALUATION_MANIFEST_REQUIRED")
    if await checkout_is_dirty(definition.git_sha):
        raise ValueError("SOURCE_COMMIT_MISMATCH")
    detector = detector_definition(definition.family, definition.method)
    oracle = {str(item.pull_id): item.scenario for item in definition.evaluation_oracle}
    if stable_hash([item.model_dump(mode="json") for item in definition.evaluation_oracle]) != (
        definition.expected_oracle_checksum
    ):
        raise ValueError("ORACLE_CHECKSUM_MISMATCH")
    rows = await AnomalyDataRepository(database).load_targets(
        definition.evaluation_pull_ids, definition.evaluation_cutoff, detector
    )
    if {row.pull_id for row in rows} != set(oracle) or len(rows) != len(oracle):
        raise ValueError("EVALUATION_COHORT_MISMATCH")
    source_fingerprint = anomaly_evaluation_source_fingerprint(rows)
    dataset_checksum = anomaly_evaluation_checksum(
        definition,
        detector.checksum,
        definition.expected_feature_checksum,
        rows,
    )
    if source_fingerprint != definition.expected_evaluation_source_fingerprint:
        raise ValueError("EVALUATION_SOURCE_CHANGED")
    if dataset_checksum != definition.expected_evaluation_checksum:
        raise ValueError("EVALUATION_DATASET_CHANGED")
    before = await source_table_digests(database)
    artifact = await DetectorArtifactStore().load_registered(database, str(detector_version_id))
    if (
        artifact.detector_version_id != str(detector_version_id)
        or artifact.definition.checksum != detector.checksum
        or artifact.reference_checksum != definition.expected_dataset_checksum
    ):
        raise ValueError("ARTIFACT_LINEAGE_MISMATCH")
    report = evaluate_anomaly_candidate(
        artifact,
        rows,
        oracle,
        training_cutoff=definition.cutoff,
        cutoff=definition.evaluation_cutoff,
    )
    if await source_table_digests(database) != before:
        raise ValueError("SOURCE_MUTATION_DURING_EVALUATION")
    report.update(
        {
            "definition_fingerprint": definition.fingerprint,
            "evaluation_dataset_checksum": dataset_checksum,
            "evaluation_source_fingerprint": source_fingerprint,
            "oracle_checksum": definition.expected_oracle_checksum,
            "phase9g_protocol_version": "phase9g-protocol-v2",
            "phase9g_protocol_checksum": default_protocol(seed=definition.seed).checksum,
            "source_mutations": False,
            "scientific_readiness": (
                "SYNTHETIC_ONLY"
                if report["status"] == "SYNTHETIC_EVALUATED"
                else "INSUFFICIENT_SUPPORT"
            ),
        }
    )
    report_checksum, report_bytes = write_report(run_id, report)
    if read_report(run_id, expected_checksum=report_checksum) != report:
        raise ValueError("REPORT_INTEGRITY_FAILURE")
    return {
        "evaluation_status": report["status"],
        "scientific_readiness": report["scientific_readiness"],
        "detector_version_id": str(detector_version_id),
        "artifact_checksum": artifact.artifact_checksum,
        "evaluation_dataset_checksum": dataset_checksum,
        "evaluation_source_fingerprint": source_fingerprint,
        "report_content_checksum": stable_hash(report),
        "report_file_checksum": report_checksum,
        "report_bytes": report_bytes,
        "evaluation_summary": {
            "target_metrics": report["target_metrics"],
            "support": report["support"],
            "cross_family_alerts": report["cross_family_alerts"],
        },
        "report": report,
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "serving_action": "NONE",
    }


async def execute_supervised_job(
    database: Database,
    definition: PipelineDefinition,
    *,
    run_id: UUID,
    token: UUID,
    fence: int,
) -> dict[str, Any]:
    """Run in a supervised worker after the parent has validated and claimed the plan."""
    require_controlled_environment()
    if definition.kind is not PipelineKind.SUPERVISED or definition.task is None:
        raise ValueError("supervised definition required")
    if definition.source_role.value != "synthetic" or definition.evaluation_cutoff is None:
        raise ValueError("canonical 9G supervised evaluation currently requires synthetic labels")
    if await checkout_is_dirty(definition.git_sha):
        raise ValueError("DIRTY_WORKTREE")
    repo = ControlPlaneRepository(database)
    step: StepOwnership = {"run_id": run_id, "token": token, "fence": fence, "attempt": 1}
    dataset_checksum = definition.expected_dataset_checksum
    await repo.record_step(**step, name="fit", state="RUNNING", input_checksum=dataset_checksum)
    try:
        task_run = await train_task(
            database,
            definition.task,
            definition.cutoff,
            source=definition.source_role.value,
            git_sha=definition.git_sha,
            expected_dataset_checksum=dataset_checksum,
            expected_source_fingerprint=definition.expected_source_fingerprint,
            candidate_pull_ids=definition.training_pull_ids,
            max_rows=definition.budget.max_rows,
            max_sessions=definition.budget.max_sessions,
            max_features=definition.budget.max_features,
            max_candidates=definition.budget.max_candidates,
            max_artifact_bytes=definition.budget.max_artifact_bytes,
        )
    except Exception:
        try:
            await repo.record_step(
                **step,
                name="fit",
                state="FAILED",
                input_checksum=dataset_checksum,
                output={"reason": "FIT_FAILED"},
            )
        except ControlPlaneConflict:
            pass
        raise
    if task_run.training.state is not ModelState.CANDIDATE:
        await repo.record_step(
            **step,
            name="fit",
            state="FAILED",
            input_checksum=dataset_checksum,
            output={"reason": "CANDIDATE_REJECTED", "state": task_run.training.state.value},
        )
        raise ValueError("CANDIDATE_REJECTED")
    await repo.record_step(
        **step,
        name="fit",
        state="SUCCEEDED",
        input_checksum=dataset_checksum,
        output={
            "training_run_id": str(task_run.run_id),
            "model_version_id": str(task_run.model_version_id),
            "artifact_checksum": task_run.artifact.checksum,
            "state": task_run.training.state.value,
        },
    )
    artifact_checksum = task_run.artifact.checksum
    await repo.record_step(
        **step, name="verify_artifact", state="RUNNING", input_checksum=artifact_checksum
    )
    try:
        artifact = await ArtifactStore().load_registered(database, str(task_run.model_version_id))
        if artifact.model_version.artifact_checksum != artifact_checksum:
            raise ValueError("ARTIFACT_TAMPERED")
    except Exception:
        try:
            await repo.record_step(
                **step,
                name="verify_artifact",
                state="FAILED",
                input_checksum=artifact_checksum,
                output={"reason": "ARTIFACT_INVALID"},
            )
        except ControlPlaneConflict:
            pass
        raise
    await repo.record_step(
        **step,
        name="verify_artifact",
        state="SUCCEEDED",
        input_checksum=artifact_checksum,
        output={
            "model_version_id": str(task_run.model_version_id),
            "artifact_checksum": artifact_checksum,
        },
    )
    expected_eval = definition.expected_evaluation_checksum
    if expected_eval is None:
        raise ValueError("MISSING_EVALUATION")
    await repo.record_step(**step, name="evaluate", state="RUNNING", input_checksum=expected_eval)
    evaluation_data = await materialize_supervised_readonly(database, definition, evaluation=True)
    if (
        evaluation_data.checksum != expected_eval
        or evaluation_data.source_fingerprint != definition.expected_evaluation_source_fingerprint
    ):
        raise ValueError("EVALUATION_SOURCE_CHANGED")
    before = await source_table_digests(database)
    research_root = Path("apps/api/.artifacts/phase10/research") / str(run_id)
    report = evaluate_supervised_task(
        task_run=task_run,
        artifact=artifact,
        future_rows=evaluation_data.rows,
        cutoff=definition.evaluation_cutoff,
        output_root=str(research_root),
        seed=definition.seed,
        bootstrap_resamples=definition.budget.max_bootstrap_resamples,
    )
    canonical_report = {
        key: value for key, value in report.items() if key != "_benchmark_calibration_fit_seconds"
    }
    phase10_report = {
        "schema_version": "phase10-9g-evaluation-receipt-v1",
        "evaluation_report_checksum": stable_hash(canonical_report),
        "phase9g_report": canonical_report,
        "scientific_limitations": [
            "Synthetic calibration does not prove real-world predictive validity.",
            "Supervised scores are not mechanical failure probabilities.",
            "Unlabeled telemetry cannot establish accuracy, recall or calibration.",
            "Real-world mechanical failure predictive reliability remains NOT_ESTABLISHED.",
        ],
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "serving_action": "NONE",
    }
    report_file_checksum, report_bytes = write_report(run_id, phase10_report)
    if stable_hash(read_report(run_id, expected_checksum=report_file_checksum)) != stable_hash(
        phase10_report
    ):
        raise ValueError("REPORT_INTEGRITY_FAILURE")
    evidence = await persist_supervised_evaluation(
        database,
        task_run=task_run,
        evaluation_dataset=evaluation_data,
        report=report,
        cutoff=definition.evaluation_cutoff,
        model_created_at=artifact.model_version.created_at,
        sources_before=before,
    )
    await repo.record_step(
        **step,
        name="evaluate",
        state="SUCCEEDED",
        input_checksum=expected_eval,
        output={
            "evaluation_run_id": evidence["evaluation_run_id"],
            "report_checksum": evidence["report_checksum"],
            "evaluation_report_checksum": stable_hash(canonical_report),
            "report_file_checksum": report_file_checksum,
            "report_bytes": report_bytes,
            "scientific_readiness": evidence["scientific_readiness"],
        },
    )
    return {
        "model_version_id": str(task_run.model_version_id),
        "artifact_checksum": artifact_checksum,
        "training_family": task_run.training.selected_family.value,
        "evaluation_summary": {
            "target_definition": canonical_report["target_definition"],
            "partitions": canonical_report["partitions"],
            "calibration_metrics": canonical_report["calibration_metrics"],
            "validation_selection_support": canonical_report["validation_selection_support"],
            "selected_research_candidate": canonical_report["selected_research_candidate"],
            "source_role": canonical_report["source_role"],
        },
        "training_run_id": str(task_run.run_id),
        **evidence,
        "report_content_checksum": stable_hash(canonical_report),
        "evaluation_report_checksum": stable_hash(canonical_report),
        "report_file_checksum": report_file_checksum,
        "report_bytes": report_bytes,
        "serving_action": "NONE",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
    }
