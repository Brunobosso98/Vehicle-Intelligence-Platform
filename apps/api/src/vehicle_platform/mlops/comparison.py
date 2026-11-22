"""Matched, retrospective comparisons against an independently activated 9D binding."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import text
from threadpoolctl import threadpool_limits

from vehicle_platform.evaluation.contracts import SourceRole
from vehicle_platform.evaluation.metrics import binary_metrics
from vehicle_platform.evaluation.splitting import (
    EvaluationSplitError,
    chronological_calibration_split,
)
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.features.service import default_feature_version
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import (
    ArtifactStore,
    ArtifactValidationError,
    TrustedModelArtifact,
    offline_predict,
)
from vehicle_platform.ml.domain import SupervisedRow
from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind
from vehicle_platform.mlops.planner import checkout_is_dirty, materialize_supervised_readonly
from vehicle_platform.mlops.policy import require_controlled_environment
from vehicle_platform.mlops.source_integrity import prior_source_digest
from vehicle_platform.predictions.repository import CONTROLLED_SCOPE, PredictionRepository


def _not_comparable(reason: str) -> dict[str, Any]:
    return {
        "schema_version": "phase10-comparison-v1",
        "status": "NOT_COMPARABLE",
        "reason": reason,
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "serving_action": "NONE",
        "limitation": (
            "Offline results do not establish mechanical failure probability or diagnosis."
        ),
    }


def _scores(
    artifact: TrustedModelArtifact, rows: tuple[SupervisedRow, ...]
) -> tuple[float | None, ...]:
    schema = artifact.input_schema
    keys = tuple(str(key) for key in schema["raw_feature_order"])
    units = {key: DEFAULT_REGISTRY.resolve(key).unit for key in keys}
    output: list[float | None] = []
    for row in rows:
        prediction = offline_predict(
            artifact,
            feature_set_version=str(schema["feature_set_version"]),
            features=row.features,
            units=units,
            missing=row.missing,
            feature_quality=row.feature_quality,
        )
        if prediction.get("probability_is_real_world_failure_probability") is not False:
            raise ValueError("score ontology is incompatible")
        output.append(float(prediction["engineering_validation_score"]))
    return tuple(output)


def matched_binary_metrics(
    champion: TrustedModelArtifact,
    challenger: TrustedModelArtifact,
    rows: tuple[SupervisedRow, ...],
    definition: PipelineDefinition,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply the canonical 9G binary protocol to one matched offline cohort."""
    first = _scores(champion, rows)
    second = _scores(challenger, rows)
    paired_first = tuple(
        left if left is not None and right is not None else None
        for left, right in zip(first, second, strict=True)
    )
    paired_second = tuple(
        right if left is not None and right is not None else None
        for left, right in zip(first, second, strict=True)
    )
    labels = [row.target for row in rows]
    row_ids = [row.row_id for row in rows]
    clusters = [row.session_id for row in rows]
    return (
        binary_metrics(
            paired_first,
            labels,
            threshold=champion.model_version.threshold,
            source_role=SourceRole.SYNTHETIC,
            fold_id="matched_holdout",
            row_ids=row_ids,
            clusters=clusters,
            bootstrap_resamples=definition.budget.max_bootstrap_resamples,
            seed=definition.seed,
        ),
        binary_metrics(
            paired_second,
            labels,
            threshold=challenger.model_version.threshold,
            source_role=SourceRole.SYNTHETIC,
            fold_id="matched_holdout",
            row_ids=row_ids,
            clusters=clusters,
            bootstrap_resamples=definition.budget.max_bootstrap_resamples,
            seed=definition.seed,
        ),
    )


async def compare_supervised(
    database: Database,
    definition: PipelineDefinition,
    *,
    champion_binding_id: UUID,
    challenger_version_id: UUID,
) -> dict[str, Any]:
    """Score one frozen 9A/9B cohort with two registered artifacts, without serving writes."""
    environment = require_controlled_environment()
    if definition.kind is not PipelineKind.SUPERVISED or definition.task is None:
        raise ValueError("supervised definition required")
    if definition.source_role is not SourceRole.SYNTHETIC:
        return _not_comparable("SYNTHETIC_PROTOCOL_REQUIRED")
    if await checkout_is_dirty(definition.git_sha):
        return _not_comparable("DIRTY_WORKTREE")
    bindings = PredictionRepository(database)
    binding = await bindings.binding(champion_binding_id)
    if binding is None or not binding.is_active or binding.model_version_id is None:
        return _not_comparable("NO_ACTIVE_CHAMPION")
    if (
        binding.environment != environment
        or binding.scope != CONTROLLED_SCOPE
        or binding.result_kind != "next_pull"
        or binding.source_role.value != definition.source_role.value
        or binding.subject_key != definition.task.value
    ):
        return _not_comparable("CHAMPION_SCOPE_MISMATCH")
    dataset = await materialize_supervised_readonly(database, definition, evaluation=True)
    if (
        dataset.checksum != definition.expected_evaluation_checksum
        or dataset.source_fingerprint != definition.expected_evaluation_source_fingerprint
    ):
        return _not_comparable("EVALUATION_SOURCE_MISMATCH")
    try:
        rows = chronological_calibration_split(dataset.rows).test
    except EvaluationSplitError:
        return _not_comparable("EVALUATION_SPLIT_INELIGIBLE")
    if not rows:
        return _not_comparable("NO_LABELED_OBSERVATIONS")
    if len(rows) > definition.budget.max_rows:
        return _not_comparable("RESOURCE_LIMIT")
    store = ArtifactStore()
    try:
        champion = await store.load_registered(database, str(binding.model_version_id))
        challenger = await store.load_registered(database, str(challenger_version_id))
    except (ArtifactValidationError, ValueError, OSError):
        return _not_comparable("ARTIFACT_INVALID")
    if (
        champion.model_version.artifact_checksum != binding.artifact_checksum
        or binding.feature_set_checksum != default_feature_version().checksum
        or binding.feature_set_version != dataset.model_spec.feature_set_version
        or binding.schema_checksum != stable_hash(champion.input_schema)
        or champion.model_version.task != definition.task
        or challenger.model_version.task != definition.task
        or champion.model_version.label_definition_id
        != challenger.model_version.label_definition_id
        or champion.model_version.feature_set_version_id
        != challenger.model_version.feature_set_version_id
        or champion.input_schema != challenger.input_schema
        or champion.model_spec_checksum != challenger.model_spec_checksum
    ):
        return _not_comparable("MODEL_SCHEMA_OR_TARGET_MISMATCH")
    source_before = await prior_source_digest(database)
    sessions = [UUID(value) for value in {row.session_id for row in rows}]
    vehicles = [UUID(value) for value in {row.vehicle_id for row in rows}]
    configurations = [UUID(value) for value in {row.configuration_id for row in rows}]
    pulls = [UUID(value) for row in rows for value in (row.input_pull_id, row.target_pull_id)]
    async with database.session() as db, db.begin():
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        for version in (champion.model_version, challenger.model_version):
            source = (
                (
                    await db.execute(
                        text(
                            "SELECT sd.manifest->>'source_role' AS source_role, "
                            "max(r.target_started_at) AS last_target, "
                            "bool_or(r.session_id=ANY(CAST(:sessions AS uuid[])) "
                            "OR r.vehicle_id=ANY(CAST(:vehicles AS uuid[])) "
                            "OR r.configuration_id=ANY(CAST(:configs AS uuid[])) "
                            "OR r.input_pull_id=ANY(CAST(:pulls AS uuid[])) "
                            "OR r.target_pull_id=ANY(CAST(:pulls AS uuid[]))) AS overlaps "
                            "FROM supervised_datasets sd JOIN supervised_dataset_rows r "
                            "ON r.supervised_dataset_id=sd.id WHERE sd.id=:id GROUP BY sd.manifest"
                        ),
                        {
                            "id": version.supervised_dataset_id,
                            "sessions": sessions,
                            "vehicles": vehicles,
                            "configs": configurations,
                            "pulls": pulls,
                        },
                    )
                )
                .mappings()
                .one_or_none()
            )
            if source is None or source["source_role"] != definition.source_role.value:
                return _not_comparable("MODEL_SOURCE_ROLE_MISMATCH")
            if source["overlaps"] or source["last_target"] >= min(
                row.input_started_at for row in rows
            ):
                return _not_comparable("HOLDOUT_LEAKAGE")
    try:
        with threadpool_limits(limits=1):
            champion_metrics, challenger_metrics = await asyncio.to_thread(
                matched_binary_metrics, champion, challenger, rows, definition
            )
    except (ArtifactValidationError, ValueError):
        return _not_comparable("SCHEMA_INCOMPATIBLE")
    row_ids = [row.row_id for row in rows]
    latest = await bindings.binding(champion_binding_id)
    if latest is None or not latest.is_active or latest.latest_event_id != binding.latest_event_id:
        return _not_comparable("STALE_CHAMPION_BINDING")
    try:
        await store.load_registered(database, str(binding.model_version_id))
        await store.load_registered(database, str(challenger_version_id))
    except (ArtifactValidationError, ValueError, OSError):
        return _not_comparable("ARTIFACT_INVALID")
    if await prior_source_digest(database) != source_before:
        return _not_comparable("PRIOR_SOURCE_MUTATION_DURING_COMPARISON")
    metric_delta: dict[str, float | None] = {}
    for name in sorted(set(champion_metrics).intersection(challenger_metrics)):
        champion_result = champion_metrics[name]
        challenger_result = challenger_metrics[name]
        if (
            not isinstance(champion_result, dict)
            or not isinstance(challenger_result, dict)
            or "value" not in champion_result
            or "value" not in challenger_result
        ):
            continue
        champion_value = champion_result["value"]
        challenger_value = challenger_result["value"]
        metric_delta[name] = (
            float(challenger_value) - float(champion_value)
            if champion_value is not None and challenger_value is not None
            else None
        )
    return {
        "schema_version": "phase10-comparison-v1",
        "status": "COMPARABLE_OFFLINE",
        "source_role": definition.source_role.value,
        "task": definition.task.value,
        "evaluation_dataset_checksum": dataset.checksum,
        "matched_row_fingerprint": stable_hash(sorted(row_ids)),
        "champion_binding_id": str(binding.id),
        "champion_event_id": str(binding.latest_event_id),
        "champion_version_id": str(binding.model_version_id),
        "challenger_version_id": str(challenger_version_id),
        "champion_artifact_checksum": champion.model_version.artifact_checksum,
        "challenger_artifact_checksum": challenger.model_version.artifact_checksum,
        "champion": champion_metrics,
        "challenger": challenger_metrics,
        "metric_delta": metric_delta,
        "eligible_rows": len(rows),
        "abstention_status": "NOT_EVALUATED_BY_OFFLINE_PREDICTOR",
        "champion_abstentions": None,
        "challenger_abstentions": None,
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "serving_action": "NONE",
        "limitation": (
            "Synthetic observable-label comparisons do not establish mechanical failure "
            "probability, calibration, diagnosis or deployment permission. The offline "
            "predictor does not apply the 9D serving abstention policy."
        ),
    }
