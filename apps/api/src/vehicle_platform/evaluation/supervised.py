from __future__ import annotations

import importlib.metadata
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from vehicle_platform.evaluation.applicability import source_fingerprint
from vehicle_platform.evaluation.artifacts import read_calibrator, write_calibrator
from vehicle_platform.evaluation.calibration import (
    CalibrationError,
    FittedCalibrator,
    apply_calibrator,
    fit_calibrator,
    select_calibration_method,
)
from vehicle_platform.evaluation.contracts import (
    CalibrationCandidate,
    CalibrationMethod,
    CalibrationValidityScope,
    SourceRole,
)
from vehicle_platform.evaluation.metrics import binary_metrics
from vehicle_platform.evaluation.protocol import PROTOCOL_THRESHOLDS
from vehicle_platform.evaluation.splitting import (
    EvaluationPartitions,
    assert_disjoint_training_source,
    chronological_calibration_split,
)
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.ml.artifacts import TrustedModelArtifact, offline_predict
from vehicle_platform.ml.domain import SupervisedRow
from vehicle_platform.ml.pipeline import TaskRunResult


def evaluate_supervised_task(
    *,
    task_run: TaskRunResult,
    artifact: TrustedModelArtifact,
    future_rows: tuple[SupervisedRow, ...],
    cutoff: datetime,
    output_root: str = "apps/api/.artifacts/phase9g/research",
    seed: int = 9142,
    bootstrap_resamples: int = 200,
    calibration_fraction: float = 1 / 3,
    validation_fraction: float = 1 / 3,
) -> dict[str, Any]:
    if len(future_rows) > 20_000:
        raise ValueError("supervised evaluation rows exceed the fixed protocol limit")
    if artifact.model_version.id != task_run.model_version_id:
        raise ValueError("loaded 9B artifact does not match the registered model version")
    if artifact.model_version.artifact_checksum != task_run.artifact.checksum:
        raise ValueError("loaded 9B artifact checksum differs from the task source receipt")
    if artifact.model_version.threshold != task_run.training.selected_threshold:
        raise ValueError("loaded 9B serving threshold differs from the frozen training receipt")
    if artifact.model_version.task.value != task_run.dataset.task.value:
        raise ValueError("loaded 9B artifact task does not match its canonical label dataset")
    if not future_rows:
        raise ValueError("supervised evaluation cohort is empty")
    partitions = chronological_calibration_split(
        future_rows,
        calibration_fraction=calibration_fraction,
        validation_fraction=validation_fraction,
    )
    assert_disjoint_training_source(task_run.training.split.train, partitions)
    scores = _score_rows(artifact, future_rows)
    by_row_id = {row.row_id: score for row, score in zip(future_rows, scores, strict=True)}
    partition_rows = {
        "calibration": partitions.calibration,
        "validation": partitions.validation,
        "test": partitions.test,
    }
    partition_scores = {
        name: tuple(by_row_id[row.row_id] for row in rows) for name, rows in partition_rows.items()
    }
    fitted: dict[CalibrationMethod, FittedCalibrator | None] = {}
    fit_errors: dict[CalibrationMethod, str] = {}
    artifact_refs: dict[CalibrationMethod, tuple[str | None, int]] = {}
    calibration_fit_seconds: dict[str, float] = {}
    source_role = SourceRole.SYNTHETIC
    original_threshold = float(task_run.training.selected_threshold)
    calibration_rows = partitions.calibration
    calibration_scores = partition_scores["calibration"]
    calibration_labels = tuple(int(row.target) for row in calibration_rows)
    calibration_ids = tuple(row.row_id for row in calibration_rows)
    calibration_clusters = tuple(row.session_id for row in calibration_rows)
    calibration_checksum = calibration_dataset_checksum(calibration_rows)
    training_rows = task_run.training.split.train
    training_vehicles = {row.vehicle_id for row in training_rows}
    evaluation_vehicles = {row.vehicle_id for row in future_rows}
    training_configurations = {row.configuration_id for row in training_rows}
    evaluation_configurations = {row.configuration_id for row in future_rows}
    validity_scope = CalibrationValidityScope(
        source_role=source_role,
        task=task_run.dataset.task.value,
        label_definition_checksum=task_run.dataset.model_spec.label_definition.checksum,
        model_version_id=str(task_run.model_version_id),
        model_artifact_checksum=task_run.artifact.checksum,
        feature_set_version=task_run.dataset.model_spec.feature_set_version,
        vehicle_context_fingerprint=stable_hash(sorted({row.vehicle_id for row in future_rows})),
        configuration_context_fingerprint=stable_hash(
            sorted({row.configuration_id for row in future_rows})
        ),
        cutoff=max(row.target_started_at for row in calibration_rows),
        not_for_serving=True,
    )

    for method in CalibrationMethod:
        fit_started = time.perf_counter()
        try:
            candidate = fit_calibrator(
                method,
                calibration_scores,
                calibration_labels,
                row_ids=calibration_ids,
                clusters=calibration_clusters,
                dataset_checksum=calibration_checksum,
                minimum_rows=40,
                minimum_each_class=10,
                minimum_clusters=10,
                isotonic_minimum_rows=100,
                isotonic_minimum_each_class=30,
                isotonic_minimum_clusters=30,
            )
        except CalibrationError as error:
            candidate = None
            fit_errors[method] = type(error).__name__
        fitted[method] = candidate
        if candidate is None:
            artifact_refs[method] = (None, 0)
        elif method is CalibrationMethod.IDENTITY:
            artifact_refs[method] = (None, 0)
        else:
            _, digest, size = write_calibrator(
                candidate,
                root=Path(output_root),
                scope={
                    "task": task_run.dataset.task.value,
                    "source_role": source_role.value,
                    "feature_set_version": task_run.dataset.model_spec.feature_set_version,
                    "label_definition_checksum": (
                        task_run.dataset.model_spec.label_definition.checksum
                    ),
                    "vehicle_context_fingerprint": validity_scope.vehicle_context_fingerprint,
                    "configuration_context_fingerprint": (
                        validity_scope.configuration_context_fingerprint
                    ),
                    "cutoff": validity_scope.model_dump(mode="json")["cutoff"],
                },
                model_version_id=str(task_run.model_version_id),
                model_artifact_checksum=task_run.artifact.checksum,
                label_definition_checksum=task_run.dataset.model_spec.label_definition.checksum,
                dependency_versions={
                    name: importlib.metadata.version(name)
                    for name in ("numpy", "scipy", "scikit-learn")
                },
            )
            stored = read_calibrator(
                Path(output_root) / task_run.dataset.task.value / f"{digest}.json",
                root=Path(output_root),
                expected_checksum=digest,
            )
            if (
                stored["parameters"] != candidate.parameters
                or stored["calibration_row_checksum"] != candidate.calibration_row_checksum
                or stored["model_artifact_checksum"] != task_run.artifact.checksum
            ):
                raise CalibrationError("serialized calibrator differs from its fitted source")
            artifact_refs[method] = (digest, size)
        calibration_fit_seconds[method.value] = time.perf_counter() - fit_started

    validation_metrics: dict[CalibrationMethod, dict[str, Any]] = {}
    validation_support = _selection_support(partitions.validation)
    validation_selection_eligible = (
        validation_support["rows"] >= 20
        and validation_support["positives"] >= 5
        and validation_support["negatives"] >= 5
        and validation_support["sessions"] >= 5
        and validation_support["vehicles"] >= 2
    )
    validation_support["selection_eligible"] = validation_selection_eligible
    for method, candidate in fitted.items():
        if candidate is None:
            validation_metrics[method] = {
                "eligible": False,
                "status": "REJECTED" if method in fit_errors else "INSUFFICIENT_SUPPORT",
                "brier_score": {
                    "value": None,
                    "undefined_reason": (
                        "CALIBRATOR_FIT_REJECTED"
                        if method in fit_errors
                        else "CALIBRATION_SUPPORT_BELOW_PROTOCOL_FLOOR"
                    ),
                },
                "rejection_code": fit_errors.get(method),
            }
            continue
        mapped = apply_calibrator(candidate, partition_scores["validation"])
        rows = partitions.validation
        report = binary_metrics(
            mapped,
            tuple(int(row.target) for row in rows),
            threshold=original_threshold,
            source_role=source_role,
            fold_id="VALIDATION",
            row_ids=tuple(row.row_id for row in rows),
            clusters=_session_cluster_fingerprints(rows),
            bin_count=5,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        )
        validation_metrics[method] = {
            "eligible": validation_selection_eligible,
            "status": "ELIGIBLE" if validation_selection_eligible else "INSUFFICIENT_SUPPORT",
            "support": validation_support,
            **report,
        }
    selected_method = select_calibration_method(validation_metrics)

    candidates: list[CalibrationCandidate] = []
    test_metrics: dict[str, Any] = {}
    mapped_test_scores: dict[str, tuple[float, ...]] = {}
    mapped_validation_scores: dict[str, tuple[float, ...]] = {}
    test_rows = partitions.test
    test_raw = partition_scores["test"]
    test_labels = tuple(int(row.target) for row in test_rows)
    test_ids = tuple(row.row_id for row in test_rows)
    test_clusters = _session_cluster_fingerprints(test_rows)
    raw_test_metrics = binary_metrics(
        test_raw,
        test_labels,
        threshold=original_threshold,
        source_role=source_role,
        fold_id="TEST",
        row_ids=test_ids,
        clusters=test_clusters,
        bin_count=5,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed + 1,
    )
    for method in CalibrationMethod:
        fitted_candidate = fitted[method]
        artifact_digest: str | None = artifact_refs[method][0]
        artifact_size = artifact_refs[method][1]
        if fitted_candidate is None:
            candidates.append(
                CalibrationCandidate(
                    method=method,
                    state="REJECTED" if method in fit_errors else "INSUFFICIENT_SUPPORT",
                    task=task_run.dataset.task.value,
                    model_version_id=str(task_run.model_version_id),
                    input_score_semantics=(
                        "9B engineering_validation_score for the original synthetic "
                        "NEXT_PULL observable label"
                    ),
                    calibration_row_count=len(calibration_rows),
                    calibration_positive_count=sum(calibration_labels),
                    calibration_negative_count=len(calibration_labels) - sum(calibration_labels),
                    calibration_cluster_count=len(set(calibration_clusters)),
                    calibration_dataset_checksum=calibration_checksum,
                    validation_metrics=validation_metrics[method],
                    test_metrics={
                        "status": (
                            "CALIBRATOR_FIT_REJECTED"
                            if method in fit_errors
                            else "NOT_EVALUATED_INELIGIBLE_CALIBRATOR"
                        ),
                        "rejection_code": fit_errors.get(method),
                    },
                    artifact_checksum=None,
                    artifact_bytes=0,
                    validity_scope=validity_scope,
                    not_for_serving=True,
                )
            )
            test_metrics[method.value] = {
                "status": "REJECTED" if method in fit_errors else "INSUFFICIENT_SUPPORT",
                "reason": (
                    "CALIBRATOR_FIT_REJECTED"
                    if method in fit_errors
                    else "CALIBRATION_SUPPORT_BELOW_PROTOCOL_FLOOR"
                ),
                "rejection_code": fit_errors.get(method),
                "test_metrics": None,
            }
            continue
        mapped_test = apply_calibrator(fitted_candidate, test_raw)
        mapped_validation = apply_calibrator(fitted_candidate, partition_scores["validation"])
        mapped_test_scores[method.value] = mapped_test
        mapped_validation_scores[method.value] = mapped_validation
        report = binary_metrics(
            mapped_test,
            test_labels,
            threshold=original_threshold,
            source_role=source_role,
            fold_id="TEST",
            row_ids=test_ids,
            clusters=test_clusters,
            bin_count=5,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed + 2,
        )
        selected = method is selected_method and validation_selection_eligible
        candidates.append(
            CalibrationCandidate(
                method=method,
                state=(
                    "SELECTED"
                    if selected
                    else "ELIGIBLE"
                    if validation_selection_eligible
                    else "REJECTED"
                ),
                task=task_run.dataset.task.value,
                model_version_id=str(task_run.model_version_id),
                input_score_semantics=(
                    "9B engineering_validation_score for the original synthetic "
                    "NEXT_PULL observable label"
                ),
                calibration_row_count=len(calibration_rows),
                calibration_positive_count=sum(calibration_labels),
                calibration_negative_count=len(calibration_labels) - sum(calibration_labels),
                calibration_cluster_count=len(set(calibration_clusters)),
                calibration_dataset_checksum=calibration_checksum,
                validation_metrics=validation_metrics[method],
                test_metrics=report,
                artifact_checksum=artifact_digest,
                artifact_bytes=artifact_size,
                validity_scope=validity_scope,
                not_for_serving=True,
            )
        )
        test_metrics[method.value] = {
            "status": (
                "SELECTED"
                if selected
                else "ELIGIBLE_NOT_SELECTED"
                if validation_selection_eligible
                else "INSUFFICIENT_VALIDATION_SUPPORT"
            ),
            "metrics": report,
            "threshold_decision_changes": _decision_changes(
                test_raw, mapped_test, original_threshold
            ),
            "threshold_grid_sensitivity": _threshold_sensitivity(
                mapped_test,
                test_labels,
                test_ids,
                test_clusters,
                validation_rows=partitions.validation,
                validation_scores=mapped_validation,
                threshold_grid=PROTOCOL_THRESHOLDS,
                original_threshold=original_threshold,
            ),
            "hypothetical_prevalence": _hypothetical_prevalence(report),
            "risk_coverage": _risk_coverage(mapped_test, test_labels),
        }

    source_fp = source_fingerprint(
        source_role,
        [row.session_id for row in future_rows],
        {
            "rows": sorted(row.row_id for row in future_rows),
            "input_source_hashes": sorted(row.input_source_hash for row in future_rows),
            "target_source_hashes": sorted(row.target_source_hash for row in future_rows),
        },
    )
    training_features = {
        feature: _feature_values(training_rows, feature)
        for feature in task_run.dataset.model_spec.feature_keys
    }
    test_features = {
        feature: _feature_values(test_rows, feature)
        for feature in task_run.dataset.model_spec.feature_keys
    }
    from vehicle_platform.evaluation.drift import drift_experiment, ood_distances

    drift = drift_experiment(
        {key: [float(value) for value in values] for key, values in training_features.items()},
        {key: [float(value) for value in values] for key, values in test_features.items()},
        baseline_labels=tuple(row.target for row in training_rows),
        comparison_labels=test_labels,
        baseline_predictions=tuple(_score_rows(artifact, (row,))[0] for row in training_rows),
        comparison_predictions=test_raw,
    )
    ood = ood_distances(
        {key: [float(value) for value in values] for key, values in training_features.items()},
        {key: [float(value) for value in values] for key, values in test_features.items()},
    )
    return {
        "task": task_run.dataset.task.value,
        "feature_set_version": task_run.dataset.model_spec.feature_set_version,
        "target_definition": task_run.dataset.model_spec.label_definition.manifest(),
        "label_definition_checksum": task_run.dataset.model_spec.label_definition.checksum,
        "model_version_id": str(task_run.model_version_id),
        "model_version": artifact.model_version.version,
        "model_repository_sha": artifact.model_version.repository_sha,
        "model_artifact_checksum": task_run.artifact.checksum,
        "source_dataset_fingerprint": task_run.dataset.source_fingerprint,
        "model_threshold_frozen": original_threshold,
        "model_threshold_changed": False,
        "source_role": source_role.value,
        "source_fingerprint": source_fp,
        "partitions": _partition_reports(partitions, task_run.training.split.train),
        "calibration_candidates": [item.model_dump(mode="json") for item in candidates],
        "selected_research_candidate": selected_method.value,
        "selection_policy": (
            "validation-only Brier; ties within 1e-4 prefer identity, then sigmoid, then isotonic"
        ),
        "validation_selection_support": validation_support,
        "calibration_metrics": {
            "calibration": _calibration_support(calibration_rows),
            "validation": {method.value: value for method, value in validation_metrics.items()},
            "test": {"identity_uncalibrated": raw_test_metrics, **test_metrics},
        },
        "calibration_examples": _example_evidence(calibration_rows, calibration_scores),
        "validation_examples": _example_evidence(
            partitions.validation,
            partition_scores["validation"],
            mapped_validation_scores,
        ),
        "test_examples": _example_evidence(test_rows, test_raw, mapped_test_scores),
        "holdout_axes": {
            "model_training_vehicle_holdout": training_vehicles.isdisjoint(evaluation_vehicles),
            "model_training_configuration_holdout": training_configurations.isdisjoint(
                evaluation_configurations
            ),
            "training_vehicle_fingerprint_count": len(training_vehicles),
            "evaluation_vehicle_fingerprint_count": len(evaluation_vehicles),
            "training_configuration_fingerprint_count": len(training_configurations),
            "evaluation_configuration_fingerprint_count": len(evaluation_configurations),
            "training_session_count": len({row.session_id for row in training_rows}),
            "evaluation_session_count": len({row.session_id for row in future_rows}),
            "evaluation_partition_policy": (
                "whole-session strict chronology; model training/evaluation vehicle and "
                "configuration holdout measured independently"
            ),
            "test_vehicles": len({row.vehicle_id for row in test_rows}),
            "test_configurations": len({row.configuration_id for row in test_rows}),
        },
        "subgroups": _subgroup_metrics(test_rows, test_raw),
        "_benchmark_calibration_fit_seconds": calibration_fit_seconds,
        "drift": drift,
        "ood": ood,
        "threshold_is_research_only": True,
        "synthetic_to_real_calibration_transfer": False,
        "real_failure_probability": False,
        "score_ontology": (
            "synthetic observable next-pull label score; not a mechanical failure probability"
        ),
    }


def _score_rows(
    artifact: TrustedModelArtifact, rows: tuple[SupervisedRow, ...]
) -> tuple[float, ...]:
    spec = artifact.model_version.input_schema
    version = str(spec["feature_set_version"])
    expected = tuple(str(item) for item in spec["raw_feature_order"])
    units = {key: DEFAULT_REGISTRY.resolve(key).unit for key in expected}
    output: list[float] = []
    for row in rows:
        if tuple(row.features) != expected:
            raise ValueError("canonical 9A model feature order changed during evaluation")
        result = offline_predict(
            artifact,
            feature_set_version=version,
            features=row.features,
            units=units,
            missing=row.missing,
            feature_quality=row.feature_quality,
        )
        value = float(result["engineering_validation_score"])
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("registered 9B artifact returned an invalid engineering score")
        if result["probability_is_real_world_failure_probability"] is not False:
            raise ValueError("9B score ontology changed during evaluation")
        output.append(value)
    return tuple(output)


def _partition_reports(
    partitions: EvaluationPartitions, training_rows: tuple[SupervisedRow, ...]
) -> dict[str, Any]:
    values: dict[str, tuple[SupervisedRow, ...]] = {
        "TRAIN": training_rows,
        "CALIBRATION": partitions.calibration,
        "VALIDATION": partitions.validation,
        "TEST": partitions.test,
    }
    return {
        name: {
            "rows": len(rows),
            "positives": sum(row.target for row in rows),
            "negatives": sum(not row.target for row in rows),
            "sessions": len({row.group_id for row in rows}),
            "vehicles": len({row.vehicle_id for row in rows}),
            "row_fingerprint": stable_hash(sorted(row.row_id for row in rows)),
            "session_fingerprint": stable_hash(sorted({row.session_id for row in rows})),
            "session_fingerprints": sorted({stable_hash(row.session_id) for row in rows}),
            "vehicle_fingerprints": sorted({stable_hash(row.vehicle_id) for row in rows}),
            "configuration_fingerprints": sorted(
                {stable_hash(row.configuration_id) for row in rows}
            ),
            "pull_fingerprints": sorted(
                {
                    stable_hash(pull_id)
                    for row in rows
                    for pull_id in (row.input_pull_id, row.target_pull_id)
                }
            ),
            "start": min(row.input_started_at for row in rows).isoformat(),
            "end": max(row.target_started_at for row in rows).isoformat(),
            "row_ids": [row.row_id for row in sorted(rows, key=lambda item: item.row_id)],
        }
        for name, rows in values.items()
    }


def _calibration_support(rows: tuple[SupervisedRow, ...]) -> dict[str, int]:
    return {
        "rows": len(rows),
        "positives": sum(row.target for row in rows),
        "negatives": sum(not row.target for row in rows),
        "sessions": len({row.session_id for row in rows}),
        "vehicles": len({row.vehicle_id for row in rows}),
        "configuration_count": len({row.configuration_id for row in rows}),
    }


def _selection_support(rows: tuple[SupervisedRow, ...]) -> dict[str, int]:
    return {
        "rows": len(rows),
        "positives": sum(row.target for row in rows),
        "negatives": sum(not row.target for row in rows),
        "sessions": len({row.session_id for row in rows}),
        "vehicles": len({row.vehicle_id for row in rows}),
        "configurations": len({row.configuration_id for row in rows}),
    }


def _feature_values(rows: tuple[SupervisedRow, ...], feature: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.features.get(feature)
        if value is not None:
            values.append(float(value))
    return values


def calibration_dataset_checksum(rows: tuple[SupervisedRow, ...]) -> str:
    """Hash calibration lineage using the binary-label encoding in the report contract."""
    return stable_hash(
        sorted(
            (row.row_id, row.input_source_hash, row.target_source_hash, int(row.target))
            for row in rows
        )
    )


def _session_cluster_fingerprints(rows: tuple[SupervisedRow, ...]) -> tuple[str, ...]:
    return tuple(stable_hash(row.session_id) for row in rows)


def _example_evidence(
    rows: tuple[SupervisedRow, ...],
    scores: tuple[float, ...],
    mapped_scores: dict[str, tuple[float, ...]] | None = None,
) -> list[dict[str, Any]]:
    return [
        {
            "example_fingerprint": row.row_id,
            "session_fingerprint": stable_hash(row.session_id),
            "input_source_checksum": row.input_source_hash,
            "target_source_checksum": row.target_source_hash,
            "score": score,
            "label": int(row.target),
            "quality_class": row.quality_class,
            "calibrated_scores": {
                method: method_scores[index]
                for method, method_scores in sorted((mapped_scores or {}).items())
            },
        }
        for index, (row, score) in enumerate(zip(rows, scores, strict=True))
    ]


def _subgroup_metrics(rows: tuple[SupervisedRow, ...], scores: tuple[float, ...]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for axis in ("vehicle", "configuration"):
        groups: dict[str, list[int]] = {}
        for index, row in enumerate(rows):
            identity = row.vehicle_id if axis == "vehicle" else row.configuration_id
            groups.setdefault(stable_hash(identity), []).append(index)
        output[axis] = {}
        for fingerprint, indices in sorted(groups.items()):
            labels = [int(rows[index].target) for index in indices]
            values = [scores[index] for index in indices]
            support_ok = (
                len(indices) >= 20 and len({rows[index].session_id for index in indices}) >= 5
            )
            output[axis][fingerprint] = {
                "status": "DESCRIPTIVE" if support_ok else "INSUFFICIENT_SUPPORT",
                "rows": len(indices),
                "sessions": len({rows[index].session_id for index in indices}),
                "positive_support": sum(labels),
                "negative_support": len(labels) - sum(labels),
                "brier_score": sum(
                    (score - label) ** 2 for score, label in zip(values, labels, strict=True)
                )
                / len(indices),
                "identities_exposed": False,
            }
    return output


def _decision_changes(
    raw: tuple[float, ...], calibrated: tuple[float, ...], threshold: float
) -> dict[str, Any]:
    before = tuple(score >= threshold for score in raw)
    after = tuple(score >= threshold for score in calibrated)
    return {
        "original_threshold_frozen": threshold,
        "changed_decisions": sum(left != right for left, right in zip(before, after, strict=True)),
        "evaluated_rows": len(before),
        "agreement_rate": sum(left == right for left, right in zip(before, after, strict=True))
        / len(before)
        if before
        else 0.0,
        "threshold_mutated": False,
    }


def _threshold_sensitivity(
    test_scores: tuple[float, ...],
    test_labels: tuple[int, ...],
    test_ids: tuple[str, ...],
    test_clusters: tuple[str, ...],
    *,
    validation_rows: tuple[SupervisedRow, ...],
    validation_scores: tuple[float, ...],
    threshold_grid: tuple[float, ...],
    original_threshold: float,
) -> dict[str, Any]:
    validation_threshold_rows = [
        {
            "threshold": threshold,
            "metrics": binary_metrics(
                validation_scores,
                tuple(int(item.target) for item in validation_rows),
                threshold=threshold,
                source_role=SourceRole.SYNTHETIC,
                fold_id="VALIDATION",
                row_ids=tuple(item.row_id for item in validation_rows),
                clusters=_session_cluster_fingerprints(validation_rows),
                bootstrap_resamples=0,
            )["decision"],
        }
        for threshold in threshold_grid
    ]
    test_rows = [
        {
            "threshold": threshold,
            "metrics": binary_metrics(
                test_scores,
                test_labels,
                threshold=threshold,
                source_role=SourceRole.SYNTHETIC,
                fold_id="TEST",
                row_ids=test_ids,
                clusters=test_clusters,
                bootstrap_resamples=0,
            )["decision"],
        }
        for threshold in threshold_grid
    ]
    return {
        "validation_only_for_policy_review": validation_threshold_rows,
        "test_descriptive_only": test_rows,
        "frozen_original_threshold": original_threshold,
        "hypothetical_cost_curves": [
            {
                "false_positive_cost_units": fp,
                "false_negative_cost_units": fn,
                "values": [
                    {
                        "threshold": row["threshold"],
                        "cost": row["metrics"]["false_positive"] * fp
                        + row["metrics"]["false_negative"] * fn,
                    }
                    for row in validation_threshold_rows
                ],
            }
            for fp, fn in ((1, 1), (1, 5), (5, 1))
        ],
        "costs_are_hypothetical_relative_units": True,
    }


def _hypothetical_prevalence(report: dict[str, Any]) -> list[dict[str, Any]]:
    decision = report["decision"]
    tpr = decision["recall"]
    fpr = decision["false_positive_rate"]
    if tpr is None or fpr is None:
        return [
            {"prevalence": rate, "ppv": None, "npv": None, "status": "UNDEFINED_SUPPORT"}
            for rate in (0.05, 0.10, 0.20, 0.40)
        ]
    output = []
    for prevalence in (0.05, 0.10, 0.20, 0.40):
        ppv_denominator = tpr * prevalence + fpr * (1 - prevalence)
        specificity = 1 - fpr
        npv_denominator = specificity * (1 - prevalence) + (1 - tpr) * prevalence
        output.append(
            {
                "prevalence": prevalence,
                "ppv": tpr * prevalence / ppv_denominator if ppv_denominator else None,
                "npv": specificity * (1 - prevalence) / npv_denominator
                if npv_denominator
                else None,
                "label": "hypothetical synthetic observable-label base rate; not fleet prevalence",
            }
        )
    return output


def _risk_coverage(scores: tuple[float, ...], labels: tuple[int, ...]) -> list[dict[str, Any]]:
    confidence = sorted(range(len(scores)), key=lambda index: (-abs(scores[index] - 0.5), index))
    output = []
    for fraction in (1.0, 0.9, 0.8, 0.6, 0.4):
        retained = max(1, math.ceil(len(scores) * fraction)) if scores else 0
        indices = confidence[:retained]
        errors = sum((scores[index] >= 0.5) != bool(labels[index]) for index in indices)
        output.append(
            {
                "retained_fraction": retained / len(scores) if scores else 0.0,
                "retained_count": retained,
                "abstained_count": len(scores) - retained,
                "selective_error": errors / retained if retained else None,
                "risk_policy": (
                    "ordered by absolute distance from uncalibrated decision score 0.5; "
                    "descriptive only"
                ),
            }
        )
    return output
