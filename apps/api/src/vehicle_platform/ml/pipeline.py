from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from vehicle_platform.features.datasets import DatasetBuild, DatasetBuilder
from vehicle_platform.features.domain import CutoffPolicy, DatasetDefinition, EntityScope
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.features.service import FeatureGenerationService
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import ArtifactReceipt, ArtifactStore
from vehicle_platform.ml.domain import MLTask, ModelState, SupervisedDataset
from vehicle_platform.ml.labels import build_supervised_dataset, get_model_spec
from vehicle_platform.ml.registry import MLRegistry, repository_sha
from vehicle_platform.ml.splitting import chronological_group_split
from vehicle_platform.ml.training import (
    InsufficientTrainingData,
    TaskTrainingResult,
    matrix_for_feature_mapping,
    train_and_evaluate,
)


@dataclass(frozen=True)
class TaskRunResult:
    dataset: SupervisedDataset
    input_dataset: DatasetBuild
    outcome_dataset: DatasetBuild
    training: TaskTrainingResult
    run_id: UUID
    model_version_id: UUID
    artifact: ArtifactReceipt


def dataset_definitions(
    task: MLTask | str,
    cutoff: datetime,
    source: str,
) -> tuple[DatasetDefinition, DatasetDefinition]:
    spec = get_model_spec(task)
    if source not in {"synthetic", "real_vehicle", "imported", "imported_fixture", "mixed"}:
        raise ValueError("unsupported Phase 9B dataset source role")
    suffix = spec.checksum[:8]
    input_definition = DatasetDefinition(
        name=f"phase9b_{spec.task.value.lower()}_inputs",
        version=f"v-{suffix}-{cutoff.strftime('%Y%m%d%H%M%S')}",
        row_scope=EntityScope.PULL,
        feature_set_version=spec.feature_set_version,
        selected_features=spec.feature_keys,
        observation_cutoff=cutoff,
        cutoff_policy=CutoffPolicy.ROW_END,
        minimum_quality=0.75,
        allow_configuration_mixing=True,
        source=source,  # type: ignore[arg-type]
    )
    outcome_definition = DatasetDefinition(
        name=f"phase9b_{spec.task.value.lower()}_outcomes",
        version=f"v-{suffix}-{cutoff.strftime('%Y%m%d%H%M%S')}",
        row_scope=EntityScope.PULL,
        feature_set_version=spec.feature_set_version,
        selected_features=spec.outcome_feature_keys,
        observation_cutoff=cutoff,
        cutoff_policy=CutoffPolicy.ROW_END,
        minimum_quality=0.75,
        required_features=spec.outcome_feature_keys,
        allow_configuration_mixing=True,
        source=source,  # type: ignore[arg-type]
    )
    return input_definition, outcome_definition


async def build_task_dataset(
    database: Database,
    task: MLTask | str,
    cutoff: datetime,
    *,
    source: str,
    git_sha: str | None = None,
    telemetry: Any | None = None,
    scenario_family_by_session: Mapping[str, str] | None = None,
    candidate_pull_ids: Sequence[UUID] | None = None,
) -> tuple[SupervisedDataset, DatasetBuild, DatasetBuild]:
    spec = get_model_spec(task)
    generation = FeatureGenerationService(database, telemetry)
    await generation.ensure_version()
    input_definition, outcome_definition = dataset_definitions(task, cutoff, source)
    builder = DatasetBuilder(database, DEFAULT_REGISTRY, telemetry)
    context = (
        telemetry.tracer.start_as_current_span(
            "ml.dataset_materialization", attributes={"ml.task": spec.task.value}
        )
        if telemetry is not None
        else nullcontext()
    )
    with context:
        input_dataset = await builder.build(input_definition, candidate_pull_ids=candidate_pull_ids)
        outcome_dataset = await builder.build(
            outcome_definition, candidate_pull_ids=candidate_pull_ids
        )
    label_context = (
        telemetry.tracer.start_as_current_span(
            "ml.label_generation", attributes={"ml.task": spec.task.value}
        )
        if telemetry is not None
        else nullcontext()
    )
    with label_context:
        dataset = build_supervised_dataset(
            input_dataset,
            outcome_dataset,
            spec,
            repository_sha=git_sha or repository_sha(),
            scenario_family_by_session=scenario_family_by_session,
        )
    if telemetry is not None:
        for reason, count in Counter(str(item["reason"]) for item in dataset.exclusions).items():
            telemetry.label_exclusions.add(count, {"task": spec.task.value, "reason": reason})
    return dataset, input_dataset, outcome_dataset


async def train_task(
    database: Database,
    task: MLTask | str,
    cutoff: datetime,
    *,
    source: str,
    git_sha: str | None = None,
    telemetry: Any | None = None,
    artifact_store: ArtifactStore | None = None,
    scenario_family_by_session: Mapping[str, str] | None = None,
) -> TaskRunResult:
    spec = get_model_spec(task)
    commit = git_sha or repository_sha()
    store = artifact_store or ArtifactStore()
    registry = MLRegistry(database)
    dataset, input_dataset, outcome_dataset = await build_task_dataset(
        database,
        task,
        cutoff,
        source=source,
        git_sha=commit,
        telemetry=telemetry,
        scenario_family_by_session=scenario_family_by_session,
    )
    (
        label_id,
        model_id,
        feature_version_id,
        input_definition_id,
        outcome_definition_id,
    ) = await registry.ensure_definitions(spec, input_dataset, outcome_dataset)
    supervised_id = await registry.persist_dataset(
        dataset,
        label_definition_id=label_id,
        feature_set_version_id=feature_version_id,
        input_dataset_definition_id=input_definition_id,
        outcome_dataset_definition_id=outcome_definition_id,
        repository_sha=commit,
    )
    trace_id: str | None = None
    if telemetry is not None:
        from opentelemetry import trace

        context = trace.get_current_span().get_span_context()
        if context.is_valid:
            trace_id = format(context.trace_id, "032x")
    run_id = await registry.start_run(
        dataset,
        spec=spec,
        label_definition_id=label_id,
        input_dataset_definition_id=input_definition_id,
        outcome_dataset_definition_id=outcome_definition_id,
        supervised_dataset_id=supervised_id,
        repository_sha=commit,
        trace_id=trace_id,
    )
    artifact: ArtifactReceipt | None = None
    registered = False
    try:
        split_context = (
            telemetry.tracer.start_as_current_span(
                "ml.temporal_split", attributes={"ml.task": spec.task.value}
            )
            if telemetry is not None
            else nullcontext()
        )
        with split_context:
            split = chronological_group_split(dataset)
        try:
            result = train_and_evaluate(dataset, split, telemetry=telemetry)
        except Exception as error:
            if isinstance(error, InsufficientTrainingData):
                label_exclusions = Counter(item["reason"] for item in dataset.exclusions)
                outcome_exclusions = Counter(item["reason"] for item in outcome_dataset.exclusions)
                raise InsufficientTrainingData(
                    f"{error}; labeled_rows={len(dataset.rows)}; "
                    f"input_rows={len(input_dataset.rows)}; "
                    f"outcome_rows={len(outcome_dataset.rows)}; "
                    f"label_exclusions={dict(label_exclusions)}; "
                    f"outcome_exclusions={dict(outcome_exclusions)}"
                ) from error
            raise
        version_token = await registry.reserve_model_version()
        artifact_context = (
            telemetry.tracer.start_as_current_span(
                "ml.artifact_staging", attributes={"ml.task": spec.task.value}
            )
            if telemetry is not None
            else nullcontext()
        )
        with artifact_context:
            artifact = store.write(
                spec.task,
                version_token,
                estimator=result.selected_model,
                input_schema=result.input_schema,
                threshold=result.selected_threshold,
                model_spec_checksum=spec.checksum,
                family=result.selected_family.value,
            )
            smoke_row = split.test[0]
            smoke_matrix = matrix_for_feature_mapping(smoke_row.features, smoke_row.missing, spec)
            store.verify_staged(
                artifact,
                task=spec.task,
                family=result.selected_family.value,
                input_schema=result.input_schema,
                threshold=result.selected_threshold,
                model_spec_checksum=spec.checksum,
                smoke_matrix=smoke_matrix,
            )
        register_context = (
            telemetry.tracer.start_as_current_span(
                "ml.model_registration", attributes={"ml.task": spec.task.value}
            )
            if telemetry is not None
            else nullcontext()
        )
        with register_context:
            version_id = await registry.register_model_version(
                result,
                dataset,
                model_id=model_id,
                label_definition_id=label_id,
                feature_set_version_id=feature_version_id,
                input_dataset_definition_id=input_definition_id,
                outcome_dataset_definition_id=outcome_definition_id,
                supervised_dataset_id=supervised_id,
                repository_sha=commit,
                version_token=version_token,
                artifact_path=artifact.relative_path,
                artifact_checksum=artifact.checksum,
                state=result.state,
            )
        registered = True
        await registry.finish_run(
            run_id,
            result=result,
            state=result.state,
            artifact_checksum=artifact.checksum,
            model_version_id=version_id,
        )
        if telemetry is not None:
            telemetry.training_runs.add(1, {"task": spec.task.value, "state": result.state.value})
            telemetry.model_artifact_size.record(artifact.size_bytes, {"task": spec.task.value})
        return TaskRunResult(
            dataset,
            input_dataset,
            outcome_dataset,
            result,
            run_id,
            version_id,
            artifact,
        )
    except Exception as error:
        if artifact is not None and not registered:
            store.delete_staged(artifact)
        category = _safe_error_category(error)
        await registry.finish_run(
            run_id,
            result=None,
            state=ModelState.REJECTED,
            error_category=category,
            artifact_checksum=artifact.checksum if artifact else None,
        )
        if telemetry is not None:
            telemetry.training_failures.add(1, {"task": spec.task.value, "category": category})
        raise


def _safe_error_category(error: Exception) -> str:
    value = getattr(error, "reason", None)
    if isinstance(value, str) and value:
        return value.upper().replace(" ", "_")[:80]
    if type(error).__name__ == "InsufficientTrainingData":
        return "INSUFFICIENT_TRAINING_DATA"
    if type(error).__name__ == "SplitValidationError":
        return "INVALID_TEMPORAL_SPLIT"
    return type(error).__name__.upper()[:80]
