"""Independent Phase 9B synthetic acceptance using canonical Phase 9A features."""

import asyncio
import json
import os
import tempfile
import time
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr
from sqlalchemy import text
from threadpoolctl import threadpool_limits
from vehicle_platform.core.config import Settings
from vehicle_platform.features.datasets import DatasetCandidate
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import ArtifactStore, offline_predict
from vehicle_platform.ml.domain import (
    CandidateFamily,
    MLTask,
    SupervisedDataset,
    SupervisedRow,
)
from vehicle_platform.ml.labels import (
    SupervisedDatasetError,
    pair_compatibility_reason,
    validate_model_features,
)
from vehicle_platform.ml.pipeline import train_task
from vehicle_platform.ml.splitting import scenario_holdout_split, temporal_blocks
from vehicle_platform.ml.synthetic import (
    generate_fixture_features,
    seed_predictive_fixture,
)
from vehicle_platform.ml.training import (
    _build_pipeline,
    _probabilities,
    _select_threshold,
    classification_metrics,
    matrix_for_rows,
    reset_random_seeds,
    train_and_evaluate,
)
from vehicle_platform.observability.telemetry import Telemetry


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _stable_training_evidence(result: Any) -> dict[str, Any]:
    return {
        "split": result.split.row_ids,
        "candidate_validation": {
            item.family.value: item.validation_metrics for item in result.candidates
        },
        "selected_family": result.selected_family.value,
        "selected_parameters": result.selected_parameters,
        "selected_threshold": result.selected_threshold,
        "test_metrics": result.test_metrics,
        "feature_importance": result.feature_importance,
        "walk_forward": result.walk_forward,
    }


def _score_rows(
    model: Any,
    rows: tuple[SupervisedRow, ...],
    dataset: SupervisedDataset,
    threshold: float,
) -> dict[str, Any]:
    matrix, labels, _, _ = matrix_for_rows(rows, dataset.model_spec)
    scores = _probabilities(model, matrix)
    return classification_metrics(labels, scores, threshold)


def _scenario_holdout(dataset: SupervisedDataset) -> dict[str, Any]:
    split = scenario_holdout_split(dataset, held_out_family="unseen_compound")
    result = train_and_evaluate(dataset, split)
    return {
        "held_out_family": "unseen_compound",
        "train_rows": len(split.train),
        "validation_rows": len(split.validation),
        "test_rows": len(split.test),
        "train_groups": split.group_counts["train"],
        "validation_groups": split.group_counts["validation"],
        "test_groups": split.group_counts["test"],
        "selected_family": result.selected_family.value,
        "test_metrics": result.test_metrics["selected"],
        "state": result.state.value,
        "test_influenced_selection": False,
    }


def _configuration_holdout(
    dataset: SupervisedDataset,
    configuration_ids_by_vehicle: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    held_configuration_ids = {item[1] for item in configuration_ids_by_vehicle.values()}
    known = tuple(
        row
        for row in dataset.rows
        if row.configuration_id not in held_configuration_ids
    )
    held = tuple(
        row for row in dataset.rows if row.configuration_id in held_configuration_ids
    )
    blocks = temporal_blocks(known)
    _assert(
        len(blocks) >= 3, "configuration holdout lacks chronological reference groups"
    )
    split_at = max(2, int(len(blocks) * 0.7))
    train = tuple(row for block in blocks[:split_at] for row in block.rows)
    validation = tuple(row for block in blocks[split_at:] for row in block.rows)
    _assert(
        bool(train and validation and held),
        "configuration holdout has an empty partition",
    )
    _assert(
        max(row.target_started_at for row in train)
        < min(row.input_started_at for row in validation),
        "configuration holdout validation is not later than training",
    )
    _assert(
        {row.configuration_id for row in train + validation}.isdisjoint(
            held_configuration_ids
        ),
        "held-out configuration leaked into training or threshold validation",
    )
    spec = dataset.model_spec
    candidate = next(
        item
        for item in spec.candidates
        if item.key is CandidateFamily.LOGISTIC_REGRESSION
    )
    train_matrix, train_labels, _, _ = matrix_for_rows(train, spec)
    validation_matrix, validation_labels, _, _ = matrix_for_rows(validation, spec)
    held_matrix, held_labels, _, _ = matrix_for_rows(held, spec)
    model = _build_pipeline(candidate, spec.seed)
    reset_random_seeds(spec.seed)
    with threadpool_limits(limits=1):
        model.fit(train_matrix, train_labels)
    threshold = _select_threshold(
        validation_labels,
        _probabilities(model, validation_matrix),
        spec.threshold_grid,
    )
    metrics = classification_metrics(
        held_labels, _probabilities(model, held_matrix), threshold
    )
    return {
        "training_configuration_count": len({row.configuration_id for row in train}),
        "held_out_configuration_count": len(held_configuration_ids),
        "train_rows": len(train),
        "validation_rows": len(validation),
        "test_rows": len(held),
        "selected_family": candidate.key.value,
        "threshold_source": "validation only",
        "test_metrics": metrics,
        "test_used_for_selection": False,
    }


def _confounder_evidence(
    performance: SupervisedDataset, fuel: SupervisedDataset
) -> dict[str, int]:
    performance_rows = performance.rows
    fuel_rows = fuel.rows
    high_iat_without_performance = sum(
        row.target is False
        and float(row.features.get("thermal.iat_start") or 0.0) >= 298.0
        for row in performance_rows
    )
    performance_with_stable_iat = sum(
        row.target and float(row.features.get("thermal.iat_delta_k") or 0.0) < 1.5
        for row in performance_rows
    )
    fuel_with_normal_boost = sum(
        row.target
        and float(row.features.get("boost_air.pressure_max") or 0.0) < 120_000.0
        for row in fuel_rows
    )
    boost_variation_without_performance = sum(
        not row.target
        and float(row.features.get("boost_air.pressure_stddev_pa") or 0.0) >= 500.0
        for row in performance_rows
    )
    return {
        "high_iat_without_performance_degradation_rows": high_iat_without_performance,
        "performance_degradation_with_stable_iat_rows": performance_with_stable_iat,
        "fuel_deviation_with_normal_boost_rows": fuel_with_normal_boost,
        "boost_variation_without_performance_degradation_rows": boost_variation_without_performance,
    }


def _leakage_sentinel_checks(dataset: SupervisedDataset) -> dict[str, bool]:
    spec = dataset.model_spec
    label_source = spec.label_definition.source_feature_keys[0]
    invalid_cases = {
        "target_outcome": label_source,
        "future_only": "future.target_sensor_mean",
        "entity_identity": "vehicle.id",
    }
    results: dict[str, bool] = {}
    for name, feature in invalid_cases.items():
        malformed = type(
            "LeakageSpec",
            (),
            {
                "feature_keys": (feature,),
                "label_definition": spec.label_definition,
            },
        )()
        try:
            validate_model_features(malformed)
        except (SupervisedDatasetError, ValueError):
            results[name] = True
        else:
            results[name] = False
    return results


def _pair_boundary_checks(dataset: SupervisedDataset) -> dict[str, bool]:
    row = dataset.rows[0]
    current = DatasetCandidate(
        pull_id=row.input_pull_id,
        vehicle_id=row.vehicle_id,
        configuration_id=row.configuration_id,
        session_id=row.session_id,
        started_at=row.input_started_at.isoformat(),
        ended_at=row.input_available_at.isoformat(),
    )
    target = DatasetCandidate(
        pull_id=row.target_pull_id,
        vehicle_id=row.vehicle_id,
        configuration_id=row.configuration_id,
        session_id=row.session_id,
        started_at=row.target_started_at.isoformat(),
        ended_at=row.target_started_at.isoformat(),
    )
    return {
        "same_vehicle_configuration_is_compatible": pair_compatibility_reason(
            current, target
        )
        is None,
        "cross_vehicle_history_rejected": pair_compatibility_reason(
            current, replace(target, vehicle_id="another-vehicle")
        )
        is not None,
        "cross_configuration_pair_rejected": pair_compatibility_reason(
            current, replace(target, configuration_id="another-configuration")
        )
        is not None,
        "input_after_target_rejected": pair_compatibility_reason(
            replace(current, ended_at=target.started_at), target
        )
        is not None,
    }


async def evaluate() -> dict[str, Any]:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError(
            "predictive acceptance requires a disposable vehicle_test database"
        )
    database = Database(
        Settings(database_url=SecretStr(url), environment="test"), command_timeout=60
    )
    settings = Settings(database_url=SecretStr(url), environment="test")
    telemetry = Telemetry(settings, database)
    span_exporter = InMemorySpanExporter()
    telemetry.traces.add_span_processor(SimpleSpanProcessor(span_exporter))
    overall_started = time.perf_counter()
    try:
        fixture = await seed_predictive_fixture(database)
        await generate_fixture_features(database, fixture, telemetry=telemetry)
    except Exception:
        telemetry.shutdown()
        await database.close()
        raise
    report: dict[str, Any] = {
        "status": "PASS",
        "validation_type": "ENGINEERING_VALIDATION",
        "real_world_accuracy_claimed": False,
        "statement": (
            "These models are engineering-validation models trained/evaluated on "
            "controlled/synthetic project data unless explicitly stated otherwise."
        ),
        "fixture": {
            "vehicle_count": 8,
            "configuration_count": 16,
            "session_count": len(fixture.session_ids),
            "pull_count": len(fixture.pull_ids),
            "held_out_vehicle": fixture.held_out_vehicle_id,
            "scenario_families": dict(
                sorted(Counter(fixture.scenario_family_by_session.values()).items())
            ),
            "seed": "deterministic-formula-v1",
            "feature_generation_path": "FeatureGenerationService.generate_session",
            "poor_quality_pull_injected": True,
            "missing_fuel_signal_pull_injected": True,
        },
        "tasks": {},
    }
    datasets_by_task: dict[MLTask, SupervisedDataset] = {}
    try:
        with tempfile.TemporaryDirectory(prefix="phase9b-artifacts-") as artifact_root:
            artifact_store = ArtifactStore(Path(artifact_root))
            for task in MLTask:
                started = time.perf_counter()
                result = await train_task(
                    database,
                    task,
                    datetime.now(UTC),
                    source="synthetic",
                    artifact_store=artifact_store,
                    scenario_family_by_session=fixture.scenario_family_by_session,
                    telemetry=telemetry,
                )
                dataset = result.dataset
                datasets_by_task[task] = dataset
                training = result.training
                _assert(
                    dataset.manifest["validation_type"] == "ENGINEERING_VALIDATION",
                    f"{task.value} lacks synthetic validation labeling",
                )
                _assert(
                    len(dataset.rows) >= dataset.model_spec.minimum_rows,
                    f"{task.value} lacks minimum rows",
                )
                _assert(
                    sum(row.target for row in dataset.rows)
                    >= dataset.model_spec.minimum_positive
                    and sum(not row.target for row in dataset.rows)
                    >= dataset.model_spec.minimum_negative,
                    f"{task.value} lacks class support",
                )
                _assert(
                    len(training.candidates) == 3
                    and {item.family for item in training.candidates}
                    == set(CandidateFamily),
                    f"{task.value} did not evaluate dummy, linear and nonlinear baselines",
                )
                _assert(
                    training.test_evaluated_after_selection,
                    "test evaluation order missing",
                )
                _assert(
                    training.manifest()["test_influenced_selection"] is False,
                    "test set was used during model selection",
                )
                _assert(
                    training.acceptance["all_criteria_pass"]
                    and training.state.value == "CANDIDATE",
                    f"{task.value} did not satisfy predeclared engineering acceptance: "
                    f"{training.acceptance}",
                )
                _assert(
                    not any(item.warnings for item in training.candidates),
                    f"{task.value} has a failed candidate family",
                )
                exclusions = Counter(item["reason"] for item in dataset.exclusions)
                if task is MLTask.FUEL_DEVIATION:
                    _assert(
                        any(
                            "MISSING_OUTCOME_SIGNAL" in row["reason"]
                            for row in dataset.exclusions
                        ),
                        "missing fuel outcome signal was not explicitly excluded",
                    )
                _assert(
                    any(
                        "INSUFFICIENT_OUTCOME_QUALITY" in row["reason"]
                        for row in dataset.exclusions
                    ),
                    f"{task.value} did not record an inadequate target quality exclusion",
                )
                leakage = _leakage_sentinel_checks(dataset)
                _assert(
                    all(leakage.values()),
                    f"{task.value} leakage sentinels failed: {leakage}",
                )
                boundaries = _pair_boundary_checks(dataset)
                _assert(
                    all(boundaries.values()),
                    f"{task.value} compatibility boundary checks failed: {boundaries}",
                )
                _assert(
                    all(
                        not key.endswith((".id", "_id"))
                        for key in dataset.rows[0].features
                    ),
                    f"{task.value} identity-like model input was admitted",
                )

                first = dataset.rows[0]
                repeat = train_and_evaluate(dataset, training.split)
                _assert(
                    _stable_training_evidence(training)
                    == _stable_training_evidence(repeat),
                    f"{task.value} repeated training evidence differs",
                )
                feature_matrix, _, _, _ = matrix_for_rows((first,), dataset.model_spec)
                first_probability = _probabilities(
                    training.selected_model, feature_matrix
                )[0]
                loaded = await artifact_store.load_registered(
                    database, str(result.model_version_id)
                )
                units = {
                    key: DEFAULT_REGISTRY.resolve(key).unit
                    for key in dataset.model_spec.feature_keys
                }
                offline = offline_predict(
                    loaded,
                    feature_set_version=dataset.model_spec.feature_set_version,
                    features=first.features,
                    units=units,
                    missing=first.missing,
                    feature_quality=first.feature_quality,
                )
                _assert(
                    abs(
                        float(offline["engineering_validation_score"])
                        - float(first_probability)
                    )
                    <= 1e-12,
                    f"{task.value} offline prediction differs from in-process inference",
                )
                _assert(
                    offline["probability_is_real_world_failure_probability"] is False,
                    "offline score was mislabeled as a failure probability",
                )

                scenario = _scenario_holdout(dataset)
                vehicle_rows = tuple(
                    row
                    for row in training.split.test
                    if row.vehicle_id == fixture.held_out_vehicle_id
                )
                _assert(
                    bool(vehicle_rows),
                    f"{task.value} held-out vehicle missing from final test window",
                )
                vehicle_metrics = _score_rows(
                    training.selected_model,
                    vehicle_rows,
                    dataset,
                    training.selected_threshold,
                )
                config_holdout = _configuration_holdout(
                    dataset, fixture.configuration_ids_by_vehicle
                )

                offline_started = time.perf_counter()
                inference_count = 1000
                for _ in range(inference_count):
                    offline_predict(
                        loaded,
                        feature_set_version=dataset.model_spec.feature_set_version,
                        features=first.features,
                        units=units,
                        missing=first.missing,
                        feature_quality=first.feature_quality,
                    )
                inference_seconds = time.perf_counter() - offline_started

                class_counts = Counter(
                    "positive" if row.target else "negative" for row in dataset.rows
                )
                async with database.session() as db:
                    registered_dataset = (
                        await db.execute(
                            text(
                                "SELECT id,row_count FROM supervised_datasets "
                                "WHERE task=:task AND checksum=:checksum"
                            ),
                            {"task": task.value, "checksum": dataset.checksum},
                        )
                    ).one()
                    registry_rows = (
                        await db.execute(
                            text(
                                "SELECT count(*) FROM supervised_dataset_rows "
                                "WHERE supervised_dataset_id=:id"
                            ),
                            {"id": registered_dataset.id},
                        )
                    ).scalar_one()
                report["tasks"][task.value] = {
                    "label_definition": dataset.model_spec.label_definition.manifest(),
                    "state": training.state.value,
                    "label_checksum": dataset.model_spec.label_definition.checksum,
                    "model_spec": dataset.model_spec.manifest(),
                    "dataset_manifest": dataset.manifest,
                    "dataset_checksum": dataset.checksum,
                    "input_dataset_checksum": dataset.input_dataset_checksum,
                    "outcome_dataset_checksum": dataset.outcome_dataset_checksum,
                    "row_count": len(dataset.rows),
                    "class_counts": dict(class_counts),
                    "exclusions_by_reason": dict(sorted(exclusions.items())),
                    "split": training.manifest()["split"],
                    "candidate_models": [
                        item.manifest() for item in training.candidates
                    ],
                    "selected_model": training.manifest()["selected_model"],
                    "test_metrics": training.test_metrics,
                    "feature_importance": training.feature_importance,
                    "walk_forward": training.walk_forward,
                    "overfit_warnings": list(training.overfit_warnings),
                    "acceptance": training.acceptance,
                    "scenario_holdout": scenario,
                    "vehicle_holdout_test": {
                        "vehicle_count": 1,
                        "row_count": len(vehicle_rows),
                        "metrics": vehicle_metrics,
                    },
                    "configuration_holdout": config_holdout,
                    "leakage_sentinels": leakage,
                    "compatibility_boundaries": boundaries,
                    "reproducibility": {
                        "repeat_training_matches": True,
                        "split_row_ids_identical": True,
                        "selected_family_identical": True,
                        "predictions_identical_within_1e-12": True,
                        "metrics_identical": True,
                        "artifact_bytes_determinism_claimed": False,
                    },
                    "training_run_id": str(result.run_id),
                    "model_version_id": str(result.model_version_id),
                    "artifact": {
                        "path": result.artifact.relative_path,
                        "checksum": result.artifact.checksum,
                        "size_bytes": result.artifact.size_bytes,
                        "format": "joblib, fixed allowlist, internal-only trusted load",
                    },
                    "registered_row_count": registry_rows,
                    "offline_inference": {
                        "score": offline["engineering_validation_score"],
                        "matches_in_process": True,
                        "real_world_failure_probability": False,
                        "throughput_predictions": inference_count,
                        "throughput_predictions_per_second": inference_count
                        / inference_seconds,
                    },
                    "elapsed_seconds": time.perf_counter() - started,
                }
            confounders = _confounder_evidence(
                datasets_by_task[MLTask.PERFORMANCE_DEGRADATION],
                datasets_by_task[MLTask.FUEL_DEVIATION],
            )
            _assert(
                all(value > 0 for value in confounders.values()),
                f"synthetic confounders are not represented: {confounders}",
            )
            report["confounders"] = confounders
            async with database.session() as db:
                counts = (
                    (
                        await db.execute(
                            text(
                                "SELECT (SELECT count(*) FROM label_definitions) labels, "
                                "(SELECT count(*) FROM ml_models) models, "
                                "(SELECT count(*) FROM supervised_datasets) datasets, "
                                "(SELECT count(*) FROM ml_model_versions) versions, "
                                "(SELECT count(*) FROM training_runs) runs"
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
            report["registry_counts"] = dict(counts)
            report["benchmark"] = {
                "fixture_rows": len(fixture.pull_ids),
                "feature_generation_seconds_included": True,
                "total_acceptance_seconds": time.perf_counter() - overall_started,
                "peak_process_rss_bytes": _peak_rss_bytes(),
            }
            telemetry.traces.force_flush()
            span_names = {span.name for span in span_exporter.get_finished_spans()}
            expected_spans = {
                "ml.dataset_materialization",
                "ml.label_generation",
                "ml.temporal_split",
                "ml.leakage_validation",
                "ml.candidate_training",
                "ml.validation_selection",
                "ml.test_evaluation",
                "ml.artifact_staging",
                "ml.model_registration",
            }
            _assert(
                expected_spans <= span_names,
                f"ML training trace spans missing: {expected_spans - span_names}",
            )
            traced_entity_ids = {
                str(identifier)
                for identifier in (
                    fixture.held_out_vehicle_id,
                    *fixture.pull_ids[:3],
                    *fixture.session_ids[:3],
                )
            }
            _assert(
                all(
                    not any(
                        identifier in repr(span.attributes)
                        for identifier in traced_entity_ids
                    )
                    for span in span_exporter.get_finished_spans()
                ),
                "vehicle, pull, or session identifier leaked into ML span attributes",
            )
            metrics_text = telemetry.render_metrics().decode("utf-8")
            expected_metric_prefixes = (
                "ml_training_runs",
                "ml_candidate_models",
                "ml_model_evaluations",
                "ml_dataset_rows",
                "ml_candidate_training_duration",
                "ml_artifact_size",
                "ml_labels_exclusions",
            )
            exported_metric_names = sorted(
                {
                    line.split(" ", maxsplit=1)[0]
                    for line in metrics_text.splitlines()
                    if line and not line.startswith("#")
                }
            )
            _assert(
                all(
                    any(name.startswith(prefix) for name in exported_metric_names)
                    for prefix in expected_metric_prefixes
                ),
                "Phase 9B metrics are missing from Prometheus exposition",
            )
            _assert(
                "vehicle_id" not in metrics_text
                and "session_id" not in metrics_text
                and "pull_id" not in metrics_text,
                "entity identifiers leaked into Phase 9B metric attributes",
            )
            report["observability"] = {
                "metrics_exported": exported_metric_names,
                "training_trace_spans": sorted(expected_spans),
                "observed_trace_spans": sorted(span_names),
                "entity_ids_in_metric_attributes": False,
                "sample_content_logged": False,
            }
            _assert(
                all(item["state"] == "CANDIDATE" for item in report["tasks"].values()),
                "one or more trained tasks did not reach CANDIDATE state",
            )
    finally:
        telemetry.shutdown()
        await database.close()
    return report


def _peak_rss_bytes() -> int:
    import resource

    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value * 1024


async def main() -> None:
    report = await evaluate()
    path = Path(".validation/phase9b/acceptance.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    summary = {
        "status": report["status"],
        "validation_type": report["validation_type"],
        "fixture": {
            key: report["fixture"][key]
            for key in (
                "vehicle_count",
                "configuration_count",
                "session_count",
                "pull_count",
            )
        },
        "tasks": {
            task: {
                "state": result["state"],
                "rows": result["row_count"],
                "selected_family": result["selected_model"]["family"],
                "test_average_precision": result["test_metrics"]["selected"][
                    "average_precision"
                ],
                "test_f1": result["test_metrics"]["selected"]["f1"],
            }
            for task, result in sorted(report["tasks"].items())
        },
        "registry_counts": report["registry_counts"],
        "acceptance_seconds": report["benchmark"]["total_acceptance_seconds"],
        "real_world_accuracy_claimed": report["real_world_accuracy_claimed"],
        "full_report": str(path),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
