"""Read-only deterministic reconstruction of a completed supervised experiment."""

from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import text
from threadpoolctl import threadpool_limits

from vehicle_platform.evaluation.contracts import SourceRole
from vehicle_platform.evaluation.splitting import (
    EvaluationSplitError,
    chronological_calibration_split,
)
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.service import default_feature_version
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import ArtifactStore
from vehicle_platform.ml.domain import ModelState
from vehicle_platform.ml.labels import get_model_spec
from vehicle_platform.ml.pipeline import build_task_dataset
from vehicle_platform.ml.splitting import chronological_group_split
from vehicle_platform.ml.training import matrix_for_feature_mapping, train_and_evaluate
from vehicle_platform.mlops.comparison import matched_binary_metrics
from vehicle_platform.mlops.contracts import (
    PipelineDefinition,
    PipelineKind,
    ReproductionReceipt,
)
from vehicle_platform.mlops.planner import (
    checkout_is_dirty,
    materialize_supervised_readonly,
)
from vehicle_platform.mlops.policy import require_controlled_environment

_SCIENTIFIC_LIMITATIONS = (
    "Synthetic calibration is not proof of real-world predictive validity.",
    "Phase 9B scores are engineering-validation scores, not mechanical failure probabilities.",
    "Unlabeled real-world telemetry cannot establish accuracy, recall, or calibration.",
    "This experiment does not diagnose a confirmed vehicle component fault.",
    "Real-world mechanical failure predictive reliability remains NOT_ESTABLISHED.",
)


class ReproductionError(ValueError):
    """A completed run cannot be safely reconstructed from its immutable lineage."""


async def _within_budget(operation: Callable[[], Awaitable[Any]], deadline: float) -> Any:
    remaining = deadline - perf_counter()
    if remaining <= 0:
        raise ReproductionError("REPRODUCTION_TIMEOUT")
    try:
        return await asyncio.wait_for(operation(), timeout=remaining)
    except TimeoutError as error:
        raise ReproductionError("REPRODUCTION_TIMEOUT") from error


async def reproduce_supervised_run(
    database: Database,
    run_id: UUID,
    *,
    telemetry: Any | None = None,
) -> dict[str, Any]:
    """Rebuild an existing candidate without creating a pipeline, run or registry row.

    The original frozen 9G test fold is scored only as a read-only reproduction audit;
    it is never used for fitting, selection, calibration, tuning or threshold changes.
    """
    require_controlled_environment()
    async with database.session() as db, db.begin():
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        row = (
            (
                await db.execute(
                    text(
                        "SELECT r.state,r.definition_fingerprint,d.body,p.model_version_id,"
                        "e.output_body AS comparison FROM mlops_runs r "
                        "JOIN mlops_definitions d ON d.fingerprint=r.definition_fingerprint "
                        "JOIN mlops_proposals p ON p.run_id=r.id "
                        "JOIN LATERAL (SELECT output_body FROM mlops_step_events "
                        "WHERE run_id=r.id AND step_name='compare' AND state='SUCCEEDED' "
                        "ORDER BY event_number DESC LIMIT 1) e ON TRUE WHERE r.id=:id"
                    ),
                    {"id": run_id},
                )
            )
            .mappings()
            .one_or_none()
        )
    if row is None or row["state"] != "COMPLETED":
        raise ReproductionError("REPRODUCTION_REQUIRES_COMPLETED_SUPERVISED_RUN")
    if not isinstance(row["body"], dict) or not isinstance(row["comparison"], dict):
        raise ReproductionError("REPRODUCTION_LINEAGE_MISSING")
    definition = PipelineDefinition.model_validate_json(json.dumps(row["body"]))
    if (
        definition.kind is not PipelineKind.SUPERVISED
        or definition.task is None
        or definition.source_role is not SourceRole.SYNTHETIC
        or stable_hash(definition.model_dump(mode="json")) != row["definition_fingerprint"]
        or definition.fingerprint != row["definition_fingerprint"]
    ):
        raise ReproductionError("REPRODUCTION_DEFINITION_INELIGIBLE")
    task = definition.task
    model_spec = get_model_spec(task)
    if (
        len(model_spec.feature_keys) > definition.budget.max_features
        or len(model_spec.candidates) > definition.budget.max_candidates
        or default_feature_version().checksum != definition.expected_feature_checksum
    ):
        raise ReproductionError("REPRODUCTION_RESOURCE_LIMIT")
    comparison = row["comparison"]
    if (
        comparison.get("status") != "COMPARABLE_OFFLINE"
        or comparison.get("serving_action") != "NONE"
        or comparison.get("task") != task.value
        or comparison.get("source_role") != definition.source_role.value
        or comparison.get("evaluation_dataset_checksum") != definition.expected_evaluation_checksum
        or comparison.get("challenger_version_id") != str(row["model_version_id"])
        or not isinstance(comparison.get("challenger"), dict)
    ):
        raise ReproductionError("REPRODUCTION_COMPARISON_INELIGIBLE")
    if await checkout_is_dirty(definition.git_sha):
        raise ReproductionError("REPRODUCTION_SOURCE_COMMIT_MISMATCH")

    started = perf_counter()
    deadline = started + definition.budget.wall_seconds
    span_context = (
        telemetry.tracer.start_as_current_span(
            "mlops.experiment.reproduction",
            attributes={"mlops.pipeline_type": "supervised", "ml.task": task.value},
        )
        if telemetry is not None
        else nullcontext()
    )
    with span_context:
        dataset, _, _ = await _within_budget(
            lambda: build_task_dataset(
                database,
                task,
                definition.cutoff,
                source=definition.source_role.value,
                git_sha=definition.git_sha,
                telemetry=telemetry,
                candidate_pull_ids=definition.training_pull_ids,
                max_rows=definition.budget.max_rows,
                persist=False,
            ),
            deadline,
        )
        if (
            dataset.checksum != definition.expected_dataset_checksum
            or dataset.source_fingerprint != definition.expected_source_fingerprint
            or len({item.session_id for item in dataset.rows}) > definition.budget.max_sessions
        ):
            raise ReproductionError("REPRODUCTION_TRAINING_LINEAGE_MISMATCH")
        split = chronological_group_split(dataset)
        with threadpool_limits(limits=1):
            training = await _within_budget(
                lambda: asyncio.to_thread(train_and_evaluate, dataset, split, telemetry=telemetry),
                deadline,
            )
        candidate_id = UUID(str(row["model_version_id"]))
        model_store = ArtifactStore()
        registered_candidate = await _within_budget(
            lambda: model_store.load_registered(database, str(candidate_id)), deadline
        )

        async def _read_registered_dataset() -> Any:
            async with database.session() as db, db.begin():
                await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
                return (
                    (
                        await db.execute(
                            text(
                                "SELECT sd.checksum,sd.source_fingerprint,"
                                "manifest->>'source_role' AS source_role,"
                                "ld.checksum AS label_checksum,fsv.checksum AS feature_checksum "
                                "FROM supervised_datasets sd "
                                "JOIN label_definitions ld ON ld.id=:label_id "
                                "JOIN feature_set_versions fsv ON fsv.id=:feature_id "
                                "WHERE sd.id=:id AND sd.label_definition_id=:label_id "
                                "AND sd.feature_set_version_id=:feature_id"
                            ),
                            {
                                "id": registered_candidate.model_version.supervised_dataset_id,
                                "label_id": registered_candidate.model_version.label_definition_id,
                                "feature_id": (
                                    registered_candidate.model_version.feature_set_version_id
                                ),
                            },
                        )
                    )
                    .mappings()
                    .one_or_none()
                )

        registered_dataset = await _within_budget(_read_registered_dataset, deadline)
        if (
            registered_dataset is None
            or registered_dataset["source_role"] != definition.source_role.value
            or registered_dataset["source_fingerprint"] != dataset.source_fingerprint
            or registered_dataset["checksum"] != dataset.checksum
            or registered_dataset["label_checksum"] != model_spec.label_definition.checksum
            or registered_dataset["feature_checksum"] != definition.expected_feature_checksum
            or registered_candidate.model_version.task is not task
            or registered_candidate.model_version.state is not ModelState.CANDIDATE
            or registered_candidate.model_version.dataset_checksum != dataset.checksum
            or registered_candidate.model_version.repository_sha != definition.git_sha
            or registered_candidate.input_schema != training.input_schema
            or registered_candidate.model_spec_checksum != model_spec.checksum
            or registered_candidate.model_version.artifact_checksum
            != comparison.get("challenger_artifact_checksum")
        ):
            raise ReproductionError("REPRODUCTION_REGISTERED_CANDIDATE_MISMATCH")

        with tempfile.TemporaryDirectory(prefix="vehicle-mlops-reproduction-") as directory:
            staged_store = ArtifactStore(Path(directory))
            staged = staged_store.write(
                task,
                "v99999999",
                estimator=training.selected_model,
                input_schema=training.input_schema,
                threshold=training.selected_threshold,
                model_spec_checksum=registered_candidate.model_spec_checksum,
                family=training.selected_family.value,
            )
            if staged.size_bytes > definition.budget.max_artifact_bytes:
                raise ReproductionError("REPRODUCTION_ARTIFACT_EXCEEDS_BUDGET")
            smoke_row = split.test[0]
            smoke_matrix = matrix_for_feature_mapping(
                smoke_row.features, smoke_row.missing, model_spec
            )
            staged_store.verify_staged(
                staged,
                task=task,
                family=training.selected_family.value,
                input_schema=training.input_schema,
                threshold=training.selected_threshold,
                model_spec_checksum=registered_candidate.model_spec_checksum,
                smoke_matrix=smoke_matrix,
            )
            reproduced_artifact_checksum = staged.checksum
            reproduced_artifact_size = staged.size_bytes

        evaluation = await _within_budget(
            lambda: materialize_supervised_readonly(database, definition, evaluation=True),
            deadline,
        )
        if (
            evaluation.checksum != definition.expected_evaluation_checksum
            or evaluation.source_fingerprint != definition.expected_evaluation_source_fingerprint
            or comparison.get("evaluation_dataset_checksum") != evaluation.checksum
        ):
            raise ReproductionError("REPRODUCTION_EVALUATION_LINEAGE_MISMATCH")
        try:
            rows = chronological_calibration_split(evaluation.rows).test
        except EvaluationSplitError as error:
            raise ReproductionError("REPRODUCTION_EVALUATION_SPLIT_INELIGIBLE") from error
        if not rows or len(rows) > definition.budget.max_rows:
            raise ReproductionError("REPRODUCTION_EVALUATION_SUPPORT_INELIGIBLE")
        champion_id = UUID(str(comparison.get("champion_version_id")))
        champion = await _within_budget(
            lambda: model_store.load_registered(database, str(champion_id)), deadline
        )
        rebuilt_candidate = replace(
            registered_candidate,
            estimator=training.selected_model,
            input_schema=training.input_schema,
        )
        with threadpool_limits(limits=1):
            _, reproduced_metrics = await _within_budget(
                lambda: asyncio.to_thread(
                    matched_binary_metrics, champion, rebuilt_candidate, rows, definition
                ),
                deadline,
            )
        # Confirm the recorded incumbent identity remains a real registered artifact.
        if champion.model_version.id != champion_id:
            raise ReproductionError("REPRODUCTION_CHAMPION_ARTIFACT_MISMATCH")
        evaluation_rows_fingerprint = stable_hash(sorted(item.row_id for item in rows))
        if evaluation_rows_fingerprint != comparison.get("matched_row_fingerprint"):
            raise ReproductionError("REPRODUCTION_MATCHED_COHORT_MISMATCH")
        expected_metrics = comparison["challenger"]
        receipt = ReproductionReceipt(
            original_run_id=run_id,
            candidate_version_id=candidate_id,
            definition_fingerprint=definition.fingerprint,
            expected_source_fingerprint=definition.expected_source_fingerprint,
            reproduced_source_fingerprint=dataset.source_fingerprint,
            expected_training_dataset_checksum=definition.expected_dataset_checksum,
            reproduced_training_dataset_checksum=dataset.checksum,
            expected_artifact_checksum=registered_candidate.model_version.artifact_checksum,
            reproduced_artifact_checksum=reproduced_artifact_checksum,
            expected_evaluation_checksum=str(comparison["evaluation_dataset_checksum"]),
            reproduced_evaluation_checksum=evaluation.checksum,
            evaluation_rows_fingerprint=evaluation_rows_fingerprint,
            expected_metrics_checksum=stable_hash(expected_metrics),
            reproduced_metrics_checksum=stable_hash(reproduced_metrics),
            holdout_usage="READ_ONLY_REPRODUCTION_AUDIT_NO_SELECTION_OR_TUNING",
            scientific_limitations=_SCIENTIFIC_LIMITATIONS,
            status=(
                "REPRODUCED"
                if reproduced_artifact_checksum
                == registered_candidate.model_version.artifact_checksum
                and stable_hash(reproduced_metrics) == stable_hash(expected_metrics)
                else "MISMATCH"
            ),
        )
    elapsed = perf_counter() - started
    return {
        "receipt": receipt.model_dump(mode="json"),
        "reproduced_metrics": reproduced_metrics,
        "artifact_size_bytes": reproduced_artifact_size,
        "execution_seconds": elapsed,
        "pipeline_run_created": False,
        "registry_rows_written": False,
        "serving_action": "NONE",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "real_world_mechanical_failure_predictive_reliability": "NOT_ESTABLISHED",
        "scientific_limitations": list(_SCIENTIFIC_LIMITATIONS),
    }
