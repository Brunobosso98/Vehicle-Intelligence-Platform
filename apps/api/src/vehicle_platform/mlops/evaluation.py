"""Persist canonical 9G supervised evidence for an internally registered candidate."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from vehicle_platform.evaluation.contracts import (
    CalibrationCandidate,
    DatasetManifest,
    EvaluationEvidenceRef,
    EvaluationRun,
    FoldManifest,
    ScientificReadinessReport,
    SourceRole,
)
from vehicle_platform.evaluation.protocol import default_protocol
from vehicle_platform.evaluation.repository import persist_evaluation, source_table_digests
from vehicle_platform.evaluation.splitting import (
    assert_disjoint_training_source,
    chronological_calibration_split,
)
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.domain import SupervisedDataset, SupervisedRow
from vehicle_platform.ml.pipeline import TaskRunResult
from vehicle_platform.mlops.policy import require_controlled_environment


def _fold(name: str, rows: tuple[SupervisedRow, ...]) -> FoldManifest:
    return FoldManifest(
        fold_id=name.lower(),
        partition=name,
        row_count=len(rows),
        positive_count=sum(bool(row.target) for row in rows),
        negative_count=sum(not row.target for row in rows),
        session_count=len({row.session_id for row in rows}),
        vehicle_count=len({row.vehicle_id for row in rows}),
        start_at=min((row.input_started_at for row in rows), default=None),
        end_at=max((row.target_started_at for row in rows), default=None),
        row_fingerprint=stable_hash(sorted(row.row_id for row in rows)),
        session_fingerprint=stable_hash(sorted({row.session_id for row in rows})),
        source_fingerprint=stable_hash(
            sorted((row.input_source_hash, row.target_source_hash) for row in rows)
        ),
        eligible=bool(rows),
    )


async def persist_supervised_evaluation(
    database: Database,
    *,
    task_run: TaskRunResult,
    evaluation_dataset: SupervisedDataset,
    report: dict[str, Any],
    cutoff: datetime,
    model_created_at: datetime,
    sources_before: dict[str, str],
) -> dict[str, Any]:
    """Store a single-task 9G report after checking lineage and prior-source immutability."""
    require_controlled_environment()
    if evaluation_dataset.task is not task_run.dataset.task:
        raise ValueError("evaluation and training task mismatch")
    if (
        report.get("task") != task_run.dataset.task.value
        or report.get("feature_set_version") != task_run.dataset.model_spec.feature_set_version
        or report.get("label_definition_checksum")
        != task_run.dataset.model_spec.label_definition.checksum
    ):
        raise ValueError("evaluation task, feature or label identity mismatch")
    if report.get("model_version_id") != str(task_run.model_version_id):
        raise ValueError("evaluation refers to a different registered model")
    if report.get("model_artifact_checksum") != task_run.artifact.checksum:
        raise ValueError("evaluation artifact checksum mismatch")
    if (
        report.get("source_role") != "synthetic"
        or report.get("real_failure_probability") is not False
    ):
        raise ValueError("evaluation violates source or scientific scope")
    partitions = chronological_calibration_split(evaluation_dataset.rows)
    assert_disjoint_training_source(task_run.dataset.rows, partitions)
    expected_partitions = {
        "TRAIN": task_run.training.split.train,
        "CALIBRATION": partitions.calibration,
        "VALIDATION": partitions.validation,
        "TEST": partitions.test,
    }
    reported_partitions = report.get("partitions")
    if not isinstance(reported_partitions, dict):
        raise ValueError("evaluation partition manifest is missing")
    for name, rows in expected_partitions.items():
        observed = reported_partitions.get(name)
        if (
            not isinstance(observed, dict)
            or observed.get("rows") != len(rows)
            or observed.get("row_fingerprint") != stable_hash(sorted(row.row_id for row in rows))
        ):
            raise ValueError("evaluation partition does not match its source rows")
    sources_after = await source_table_digests(database)
    if sources_before != sources_after:
        raise ValueError("prior source records changed during evaluation")
    rows = evaluation_dataset.rows
    exclusions = evaluation_dataset.exclusions
    manifest = DatasetManifest(
        source_role=SourceRole.SYNTHETIC,
        source_kind="canonical_9a_9b_supervised_holdout",
        row_count=len(rows) + len(exclusions),
        labeled_count=len(rows),
        unlabeled_count=len(exclusions),
        vehicle_count=len({row.vehicle_id for row in rows}),
        configuration_count=len({row.configuration_id for row in rows}),
        session_count=len({row.session_id for row in rows}),
        feature_set_version=task_run.dataset.model_spec.feature_set_version,
        source_fingerprint=evaluation_dataset.source_fingerprint,
        row_fingerprint=stable_hash(
            {"rows": sorted(row.row_id for row in rows), "exclusions": exclusions}
        ),
        cutoff=cutoff,
        known_at_policy="input_available_before_next_pull_target_v1",
        generator_version=None,
    )
    folds = (
        _fold("TRAIN", task_run.training.split.train),
        _fold("CALIBRATION", partitions.calibration),
        _fold("VALIDATION", partitions.validation),
        _fold("TEST", partitions.test),
    )
    candidates = tuple(
        CalibrationCandidate.model_validate_json(json.dumps(item, sort_keys=True, allow_nan=False))
        for item in report["calibration_candidates"]
    )
    clean_report = {
        key: value for key, value in report.items() if key != "_benchmark_calibration_fit_seconds"
    }
    reports = {f"supervised-{task_run.dataset.task.value}": clean_report}
    checksum = stable_hash(reports)
    protocol = default_protocol()
    logical_key = stable_hash(
        {
            "protocol": protocol.checksum,
            "dataset": evaluation_dataset.checksum,
            "model": task_run.artifact.checksum,
            "report": checksum,
        }
    )
    run = EvaluationRun(
        protocol_checksum=protocol.checksum,
        git_sha=task_run.dataset.manifest["repository_sha"],
        logical_key=logical_key,
        source_role=SourceRole.SYNTHETIC,
        dataset_manifest=manifest,
        folds=folds,
        evidence=(
            EvaluationEvidenceRef(
                kind="9b_model",
                version=report["model_version"],
                entity_fingerprint=stable_hash(str(task_run.model_version_id)),
                content_checksum=task_run.artifact.checksum,
                source_role=SourceRole.SYNTHETIC,
                known_at=model_created_at,
            ),
        ),
        metrics=(),
        calibration_candidates=candidates,
        applicability=(),
        drift=(),
        stress_scenarios=(),
        engineering_status="PASS",
        scientific_readiness=ScientificReadinessReport(
            engineering_pipeline="PASS",
            synthetic_calibration=(
                "SYNTHETIC_ONLY"
                if report.get("validation_selection_support", {}).get("selection_eligible") is True
                else "INSUFFICIENT_SUPPORT"
            ),
            real_world_predictive_validity="NOT_ESTABLISHED",
            real_world_calibration="NOT_ESTABLISHED",
            production_use="PROHIBITED",
            failure_labels_available=False,
            unsupported_claims=(
                "real-world calibration",
                "mechanical failure probability",
                "engine-health percentage",
                "production or maintenance decision",
            ),
        ),
        report_checksum=checksum,
        no_source_mutations=True,
        serving_artifacts_unchanged=True,
    )
    result = await persist_evaluation(
        database,
        protocol=protocol,
        run=run,
        reports=reports,
        calibration_refs={
            f"{item.task}:{item.method.value}": UUID(item.model_version_id) for item in candidates
        },
    )
    if await source_table_digests(database) != sources_before:
        raise ValueError("prior source records changed during evaluation persistence")
    return {
        "evaluation_run_id": result["run_id"],
        "report_checksum": checksum,
        "logical_key": logical_key,
        "scientific_readiness": run.scientific_readiness.model_dump(mode="json"),
    }
