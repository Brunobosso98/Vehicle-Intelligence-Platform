"""Read-only Phase 10 planning over the canonical Phase 9A, 9B and 9C contracts."""

from __future__ import annotations

import asyncio
import shutil
from collections import Counter
from typing import Any

from sqlalchemy import text

from vehicle_platform.anomalies.definitions import detector_definition
from vehicle_platform.anomalies.domain import MAX_REFERENCE_ROWS, ReferenceRow
from vehicle_platform.anomalies.domain import SourceRole as AnomalySourceRole
from vehicle_platform.anomalies.repository import AnomalyDataRepository
from vehicle_platform.evaluation.splitting import (
    EvaluationSplitError,
    assert_disjoint_training_source,
    chronological_calibration_split,
)
from vehicle_platform.features.datasets import DatasetBuilder
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.features.service import default_feature_version
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.domain import SupervisedDataset
from vehicle_platform.ml.labels import build_supervised_dataset, get_model_spec
from vehicle_platform.ml.pipeline import dataset_definitions
from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind
from vehicle_platform.mlops.holdout import prior_holdout_conflict
from vehicle_platform.mlops.policy import require_controlled_environment


async def plan_anomaly(database: Database, definition: PipelineDefinition) -> dict[str, Any]:
    """Inspect the actual 9C reference without fitting, registering, or serving a detector."""
    environment = require_controlled_environment()
    if (
        definition.kind is not PipelineKind.ANOMALY
        or definition.family is None
        or definition.method is None
        or definition.anchor_pull_id is None
    ):
        raise ValueError("anomaly planning requires family, method and anchor")
    dirty = await checkout_is_dirty(definition.git_sha)
    if definition.source_role.value != "synthetic":
        return {
            "schema_version": "phase10-plan-v1",
            "fingerprint": definition.fingerprint,
            "status": "BLOCKED",
            "reason": "EVALUATOR_ROLE_UNSUPPORTED",
            "writes_on_plan": [],
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
    detector = detector_definition(definition.family, definition.method)
    if len(detector.feature_keys) > definition.budget.max_features:
        raise ValueError("detector features exceed the declared budget")
    role = AnomalySourceRole(definition.source_role.value)
    repository = AnomalyDataRepository(database)
    anchor, feature_version_id, feature_checksum = await repository.load_anchor(
        definition.anchor_pull_id, definition.cutoff, role, detector
    )
    if anchor.pull_ended_at > definition.cutoff:
        raise ValueError("CUTOFF_LEAKAGE")
    reference = await repository.materialize_reference(
        anchor,
        feature_version_id,
        feature_checksum,
        detector,
        role,
        max_rows=min(definition.budget.max_rows, MAX_REFERENCE_ROWS),
    )
    sessions = len({row.session_id for row in reference.rows})
    expected_version = default_feature_version()
    if (
        anchor.source_type != "synthetic"
        or any(row.source_type != "synthetic" for row in reference.rows)
        or anchor.source_role is not role
        or reference.source_role is not role
    ):
        status, reason = "BLOCKED", "SOURCE_ROLE_MISMATCH"
    elif dirty:
        status, reason = "BLOCKED", "DIRTY_WORKTREE"
    elif (
        feature_checksum != definition.expected_feature_checksum
        or feature_checksum != expected_version.checksum
        or reference.feature_set_version != expected_version.version
    ):
        status, reason = "BLOCKED", "SCHEMA_INCOMPATIBLE"
    elif reference.source_fingerprint != definition.expected_source_fingerprint:
        status, reason = "BLOCKED", "SOURCE_FINGERPRINT_MISMATCH"
    elif reference.checksum(detector) != definition.expected_dataset_checksum:
        status, reason = "BLOCKED", "DATASET_CHECKSUM_MISMATCH"
    elif (
        len(reference.rows) > definition.budget.max_rows
        or sessions > definition.budget.max_sessions
    ):
        status, reason = "BLOCKED", "RESOURCE_LIMIT"
    elif (
        len(reference.rows) < int(detector.cohort_policy["minimum_reference_rows"])
        or sessions < int(detector.cohort_policy["minimum_independent_sessions"])
        or reference.temporal_span.total_seconds()
        < float(detector.cohort_policy["minimum_chronological_span_seconds"])
    ):
        status, reason = "INSUFFICIENT_SUPPORT", "INSUFFICIENT_COHORT"
    else:
        status, reason = "READY_TO_REVIEW", "REFERENCE_PRECONDITIONS_MET"
    evaluation_rows: tuple[ReferenceRow, ...] = ()
    evaluation_source = None
    evaluation_checksum = None
    evaluation_status = "NOT_CONFIGURED"
    clean_sessions: set[str] = set()
    target_sessions: set[str] = set()
    if status == "READY_TO_REVIEW":
        if (
            definition.evaluation_cutoff is None
            or definition.expected_evaluation_checksum is None
            or definition.expected_evaluation_source_fingerprint is None
            or definition.expected_oracle_checksum is None
            or not definition.evaluation_pull_ids
            or not definition.evaluation_oracle
        ):
            status, reason = "INSUFFICIENT_SUPPORT", "EVALUATION_ORACLE_REQUIRED"
            evaluation_status = "NOT_EXECUTED"
        else:
            evaluation_rows = await repository.load_targets(
                definition.evaluation_pull_ids, definition.evaluation_cutoff, detector
            )
            evaluation_source = anomaly_evaluation_source_fingerprint(evaluation_rows)
            evaluation_checksum = anomaly_evaluation_checksum(
                definition, detector.checksum, feature_checksum, evaluation_rows
            )
            expected_ids = {str(item) for item in definition.evaluation_pull_ids}
            observed_ids = {row.pull_id for row in evaluation_rows}
            oracle = {str(item.pull_id): item.scenario for item in definition.evaluation_oracle}
            labels = [oracle[row.pull_id] for row in evaluation_rows if row.pull_id in oracle]
            clean_sessions = {
                row.session_id for row in evaluation_rows if oracle.get(row.pull_id) == "clean"
            }
            target_sessions = {
                row.session_id
                for row in evaluation_rows
                if oracle.get(row.pull_id) == definition.family
            }
            if expected_ids != observed_ids or len(evaluation_rows) != len(expected_ids):
                status, reason = "BLOCKED", "EVALUATION_COHORT_MISMATCH"
                evaluation_status = "FAIL"
            elif any(row.cohort != reference.cohort for row in evaluation_rows):
                status, reason = "BLOCKED", "EVALUATION_COHORT_INCOMPATIBLE"
                evaluation_status = "FAIL"
            elif any(
                row.pull_started_at <= definition.cutoff
                or row.pull_ended_at > definition.evaluation_cutoff
                or row.observation_cutoff > definition.evaluation_cutoff
                for row in evaluation_rows
            ):
                status, reason = "BLOCKED", "EVALUATION_TIME_LEAKAGE"
                evaluation_status = "FAIL"
            elif {row.session_id for row in evaluation_rows}.intersection(
                row.session_id for row in reference.rows
            ):
                status, reason = "BLOCKED", "EVALUATION_SESSION_LEAKAGE"
                evaluation_status = "FAIL"
            elif evaluation_source != definition.expected_evaluation_source_fingerprint:
                status, reason = "BLOCKED", "EVALUATION_SOURCE_FINGERPRINT_MISMATCH"
                evaluation_status = "FAIL"
            elif evaluation_checksum != definition.expected_evaluation_checksum:
                status, reason = "BLOCKED", "EVALUATION_DATASET_CHECKSUM_MISMATCH"
                evaluation_status = "FAIL"
            elif (
                sum(label == "clean" for label in labels) < 2
                or sum(label == definition.family for label in labels) < 2
                or len(clean_sessions) < 2
                or len(target_sessions) < 2
            ):
                status, reason = "INSUFFICIENT_SUPPORT", "EVALUATION_LABEL_SUPPORT_LOW"
                evaluation_status = "INSUFFICIENT_SUPPORT"
            else:
                evaluation_status = "READY"
    return {
        "schema_version": "phase10-plan-v1",
        "fingerprint": definition.fingerprint,
        "environment": environment,
        "status": status,
        "reason": reason,
        "family": definition.family,
        "method": definition.method,
        "source_role": role.value,
        "feature_set_version": reference.feature_set_version,
        "feature_checksum": feature_checksum,
        "label_checksum": definition.expected_oracle_checksum,
        "detector_definition_checksum": detector.checksum,
        "reference_checksum": reference.checksum(detector),
        "source_fingerprint": reference.source_fingerprint,
        "reference_rows": len(reference.rows),
        "reference_sessions": sessions,
        "excluded_count": len(reference.exclusions),
        "evaluation_status": evaluation_status,
        "evaluation_rows": len(evaluation_rows),
        "evaluation_source_fingerprint": evaluation_source,
        "evaluation_dataset_checksum": evaluation_checksum,
        "evaluation_oracle_checksum": definition.expected_oracle_checksum,
        "evaluation_clean_sessions": len(clean_sessions) if definition.evaluation_oracle else 0,
        "evaluation_target_sessions": len(target_sessions) if definition.evaluation_oracle else 0,
        "writes_on_plan": [],
        "serving_action": "NONE",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "limitation": (
            "Reference support does not establish detection accuracy, engine health, "
            "component diagnosis or real-world mechanical failure probability."
        ),
    }


def anomaly_evaluation_source_fingerprint(rows: tuple[Any, ...]) -> str:
    """Bind an offline evaluation cohort to exact 9A FeatureSet/source provenance."""
    cohort_checksum = rows[0].cohort.checksum if rows else None
    return stable_hash(
        {
            "schema_version": "phase10-anomaly-evaluation-source-v1",
            "cohort_checksum": cohort_checksum,
            "rows": sorted(
                (str(row.feature_set_id), row.source_hash, row.provenance_hash) for row in rows
            ),
        }
    )


def anomaly_evaluation_checksum(
    definition: PipelineDefinition,
    detector_definition_checksum: str,
    feature_checksum: str,
    rows: tuple[Any, ...],
) -> str:
    if definition.family is None or definition.method is None:
        raise ValueError("anomaly family and method are required")

    return stable_hash(
        {
            "schema_version": "phase10-anomaly-evaluation-dataset-v1",
            "family": definition.family,
            "method": definition.method,
            "detector_definition_checksum": detector_definition_checksum,
            "feature_set_version": default_feature_version().version,
            "feature_checksum": feature_checksum,
            "cutoff": definition.evaluation_cutoff.isoformat()
            if definition.evaluation_cutoff
            else None,
            "rows": sorted(
                (
                    row.manifest(
                        detector_definition(definition.family, definition.method).feature_keys
                    )
                    for row in rows
                ),
                key=lambda item: item["pull_id"],
            ),
        }
    )


async def materialize_supervised_readonly(
    database: Database, definition: PipelineDefinition, *, evaluation: bool
) -> SupervisedDataset:
    require_controlled_environment()
    if definition.task is None:
        raise ValueError("supervised task is required")
    cutoff = definition.evaluation_cutoff if evaluation else definition.cutoff
    if cutoff is None:
        raise ValueError("evaluation cutoff is required")
    spec = get_model_spec(definition.task)
    inputs, outcomes = dataset_definitions(definition.task, cutoff, definition.source_role.value)
    builder = DatasetBuilder(database, DEFAULT_REGISTRY)
    candidates = definition.evaluation_pull_ids if evaluation else None
    input_data = await builder.build(
        inputs, candidate_pull_ids=candidates, persist=False, max_rows=definition.budget.max_rows
    )
    outcome_data = await builder.build(
        outcomes, candidate_pull_ids=candidates, persist=False, max_rows=definition.budget.max_rows
    )
    if evaluation and {str(item.pull_id) for item in input_data.candidates} != {
        str(item) for item in definition.evaluation_pull_ids
    }:
        raise ValueError("EVALUATION_COHORT_MISMATCH")
    return build_supervised_dataset(
        input_data, outcome_data, spec, repository_sha=definition.git_sha
    )


async def checkout_is_dirty(expected_sha: str) -> bool:
    """Verify the exact commit and report uncommitted source changes."""
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("planning requires a verifiable repository checkout")
    try:
        process = await asyncio.create_subprocess_exec(  # noqa: S603 -- fixed executable and arguments
            git,
            "rev-parse",
            "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=2)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise
    except (OSError, TimeoutError):
        raise RuntimeError("unable to verify the current repository commit") from None
    if process.returncode != 0 or stdout.decode("ascii").strip() != expected_sha:
        raise ValueError("SOURCE_COMMIT_MISMATCH")
    try:
        status_process = await asyncio.create_subprocess_exec(  # noqa: S603 -- fixed git command
            git,
            "status",
            "--porcelain",
            "--untracked-files=normal",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            status_output, _ = await asyncio.wait_for(status_process.communicate(), timeout=5)
        except TimeoutError:
            status_process.kill()
            await status_process.wait()
            raise
    except (OSError, TimeoutError):
        raise RuntimeError("unable to verify the repository worktree") from None
    if status_process.returncode != 0:
        raise RuntimeError("unable to verify the repository worktree")
    return bool(status_output)


async def plan_supervised(database: Database, definition: PipelineDefinition) -> dict[str, Any]:
    """Build a bounded read-only dataset plan without creating any registry rows."""
    environment = require_controlled_environment()
    worktree_dirty = await checkout_is_dirty(definition.git_sha)
    if definition.kind is not PipelineKind.SUPERVISED or definition.task is None:
        raise ValueError("supervised planning requires a supervised definition")
    if definition.source_role.value not in {"synthetic", "imported_fixture"}:
        return {
            "schema_version": "phase10-plan-v1",
            "fingerprint": definition.fingerprint,
            "status": "INSUFFICIENT_SUPPORT",
            "reason": "VERIFIED_REAL_OUTCOME_RIGHTS_NOT_ESTABLISHED",
            "writes": [],
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
    spec = get_model_spec(definition.task)
    feature_version = default_feature_version()
    if len(spec.feature_keys) > definition.budget.max_features:
        raise ValueError("model features exceed the declared budget")
    if len(spec.candidates) > definition.budget.max_candidates:
        raise ValueError("candidate models exceed the declared budget")
    async with database.session() as db, db.begin():
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        stored_checksum = await db.scalar(
            text("SELECT checksum FROM feature_set_versions WHERE version=:version"),
            {"version": spec.feature_set_version},
        )
    if (
        feature_version.version != spec.feature_set_version
        or stored_checksum != feature_version.checksum
        or definition.expected_feature_checksum != feature_version.checksum
    ):
        raise ValueError("SCHEMA_INCOMPATIBLE")
    inputs, outcomes = dataset_definitions(
        definition.task, definition.cutoff, definition.source_role.value
    )
    builder = DatasetBuilder(database, DEFAULT_REGISTRY)
    input_data = await builder.build(inputs, persist=False, max_rows=definition.budget.max_rows)
    outcome_data = await builder.build(outcomes, persist=False, max_rows=definition.budget.max_rows)
    dataset = build_supervised_dataset(
        input_data, outcome_data, spec, repository_sha=definition.git_sha
    )
    if definition.evaluation_cutoff is None:
        raise ValueError("evaluation cutoff is required")
    eval_inputs, eval_outcomes = dataset_definitions(
        definition.task, definition.evaluation_cutoff, definition.source_role.value
    )
    eval_input_data = await builder.build(
        eval_inputs,
        candidate_pull_ids=definition.evaluation_pull_ids,
        persist=False,
        max_rows=definition.budget.max_rows,
    )
    eval_outcome_data = await builder.build(
        eval_outcomes,
        candidate_pull_ids=definition.evaluation_pull_ids,
        persist=False,
        max_rows=definition.budget.max_rows,
    )
    evaluation_data = build_supervised_dataset(
        eval_input_data, eval_outcome_data, spec, repository_sha=definition.git_sha
    )
    prior_holdout_reason = await prior_holdout_conflict(
        database, (*dataset.rows, *evaluation_data.rows)
    )
    requested_ids = {str(item) for item in definition.evaluation_pull_ids}
    selected_ids = {str(item.pull_id) for item in eval_input_data.candidates}
    cohort_complete = selected_ids == requested_ids
    if len({row.session_id for row in evaluation_data.rows}) > definition.budget.max_sessions:
        raise ValueError("evaluation sessions exceed the declared budget")
    split_error = None
    try:
        partitions = chronological_calibration_split(evaluation_data.rows)
        assert_disjoint_training_source(dataset.rows, partitions)
    except EvaluationSplitError:
        split_error = "EVALUATION_SPLIT_INELIGIBLE"
    if len({row.session_id for row in dataset.rows}) > definition.budget.max_sessions:
        raise ValueError("dataset sessions exceed the declared budget")
    counts = Counter(bool(row.target) for row in dataset.rows)
    eligible = (
        len(dataset.rows) >= spec.minimum_rows
        and counts[True] >= spec.minimum_positive
        and counts[False] >= spec.minimum_negative
    )
    if worktree_dirty:
        status, reason = "BLOCKED", "DIRTY_WORKTREE"
    elif prior_holdout_reason is not None:
        status, reason = "BLOCKED", prior_holdout_reason
    elif dataset.source_fingerprint != definition.expected_source_fingerprint:
        status, reason = "BLOCKED", "SOURCE_FINGERPRINT_MISMATCH"
    elif dataset.checksum != definition.expected_dataset_checksum:
        status, reason = "BLOCKED", "DATASET_CHECKSUM_MISMATCH"
    elif evaluation_data.source_fingerprint != definition.expected_evaluation_source_fingerprint:
        status, reason = "BLOCKED", "EVALUATION_SOURCE_FINGERPRINT_MISMATCH"
    elif evaluation_data.checksum != definition.expected_evaluation_checksum:
        status, reason = "BLOCKED", "EVALUATION_DATASET_CHECKSUM_MISMATCH"
    elif not cohort_complete:
        status, reason = "BLOCKED", "EVALUATION_COHORT_MISMATCH"
    elif definition.source_role.value != "synthetic":
        status, reason = "BLOCKED", "EVALUATOR_ROLE_UNSUPPORTED"
    elif split_error is not None:
        status, reason = "INSUFFICIENT_SUPPORT", split_error
    elif not eligible:
        status, reason = "INSUFFICIENT_SUPPORT", "INSUFFICIENT_COHORT"
    else:
        status, reason = "READY_TO_REVIEW", "PRECONDITIONS_MET"
    return {
        "schema_version": "phase10-plan-v1",
        "fingerprint": definition.fingerprint,
        "environment": environment,
        "status": status,
        "reason": reason,
        "source_role": definition.source_role.value,
        "feature_set_version": spec.feature_set_version,
        "feature_checksum": feature_version.checksum,
        "label_checksum": spec.label_definition.checksum,
        "dataset_checksum": dataset.checksum,
        "evaluation_dataset_checksum": evaluation_data.checksum,
        "evaluation_source_fingerprint": evaluation_data.source_fingerprint,
        "evaluation_rows": len(evaluation_data.rows),
        "source_fingerprint": dataset.source_fingerprint,
        "input_dataset_checksum": input_data.checksum,
        "outcome_dataset_checksum": outcome_data.checksum,
        "candidate_pulls": len(input_data.candidates),
        "labeled_rows": len(dataset.rows),
        "positive_count": counts[True],
        "negative_count": counts[False],
        "excluded_count": len(dataset.exclusions),
        "sessions": len({row.session_id for row in dataset.rows}),
        "writes_on_plan": [],
        "planned_writes_on_execute": [
            "9B training run and new candidate",
            "Phase 10 run and events",
            "9G offline evaluation",
        ],
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "limitation": (
            "Synthetic target labels and scores do not establish mechanical failure risk."
        ),
    }
