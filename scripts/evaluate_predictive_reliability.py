"""Phase 9G offline evaluation over registered Phase 9B/9C artifacts."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import resource
import shutil
import subprocess
import tempfile
import time
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import evaluate_anomaly_detection
import numpy as np
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from vehicle_platform.anomalies.artifacts import ArtifactStore as AnomalyArtifactStore
from vehicle_platform.core.config import Settings
from vehicle_platform.evaluation.anomaly import evaluate_phase9c_receipt
from vehicle_platform.evaluation.anomaly_sensitivity import (
    evaluate_reference_size_sensitivity,
)
from vehicle_platform.evaluation.applicability import assess_source_applicability
from vehicle_platform.evaluation.calibration import (
    CalibrationError,
    apply_calibrator,
    fit_calibrator,
)
from vehicle_platform.evaluation.contracts import (
    ApplicabilityAssessment,
    CalibrationCandidate,
    CalibrationMethod,
    DatasetManifest,
    DriftComparison,
    EvaluationEvidenceRef,
    EvaluationProtocol,
    EvaluationRun,
    FoldManifest,
    MetricResult,
    MetricStatus,
    ScientificReadinessReport,
    SourceRole,
    StressScenario,
)
from vehicle_platform.evaluation.drift import (
    drift_experiment,
    ood_distances,
    population_stability_index,
    robust_location_shift,
)
from vehicle_platform.evaluation.metrics import binary_metrics
from vehicle_platform.evaluation.observability import record_run_metrics
from vehicle_platform.evaluation.protocol import default_protocol
from vehicle_platform.evaluation.repository import (
    SOURCE_TABLES,
    assert_evaluation_immutability,
    persist_evaluation,
    source_table_digests,
)
from vehicle_platform.evaluation.splitting import (
    EvaluationSplitError,
    assert_disjoint_training_source,
    chronological_calibration_split,
)
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import (
    ArtifactStore as ModelArtifactStore,
)
from vehicle_platform.ml.artifacts import (
    ArtifactValidationError as ModelArtifactValidationError,
)
from vehicle_platform.ml.domain import MLTask, SupervisedRow
from vehicle_platform.ml.pipeline import TaskRunResult, build_task_dataset, train_task
from vehicle_platform.ml.synthetic import (
    generate_fixture_features,
    seed_predictive_fixture,
)
from vehicle_platform.observability.telemetry import Telemetry

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPOSITORY_ROOT / ".validation" / "phase9g"
TRAINING_CUTOFF = datetime(2026, 3, 1, tzinfo=UTC)
EVALUATION_CUTOFF = datetime(2026, 9, 1, tzinfo=UTC)
FUTURE_STARTS = (
    datetime(2026, 6, 1, tzinfo=UTC),
    datetime(2026, 7, 1, tzinfo=UTC),
    datetime(2026, 8, 1, tzinfo=UTC),
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _git_state(allow_dirty: bool) -> tuple[str, bool]:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git is required to bind the evaluation to a source SHA")
    sha = subprocess.run(
        [git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    expected = os.environ.get("GIT_COMMIT_SHA") or os.environ.get("GIT_SHA") or sha
    if sha != expected:
        raise RuntimeError(
            "evaluation commit SHA does not match the expected workflow SHA"
        )
    dirty = bool(
        subprocess.run(
            [git, "status", "--porcelain"], check=True, capture_output=True, text=True
        ).stdout.strip()
    )
    if dirty and not allow_dirty:
        raise RuntimeError("Phase 9G acceptance requires a clean worktree")
    return sha, dirty


async def _record_modifications(
    database: Database,
    fixture: Any,
) -> int:
    inserted = 0
    async with database.session() as db:
        for vehicle_id, (
            _stock_configuration,
            stage_configuration,
        ) in fixture.configuration_ids_by_vehicle.items():
            effective_at = await db.scalar(
                text("SELECT effective_at FROM vehicle_configurations WHERE id=:id"),
                {"id": UUID(stage_configuration)},
            )
            if not isinstance(effective_at, datetime):
                raise TypeError(
                    "synthetic stage configuration has no effective timestamp"
                )
            await db.execute(
                text(
                    "INSERT INTO modifications(vehicle_id,configuration_id,category,manufacturer,"
                    "product,installed_at,removed_at,notes,created_at) "
                    "VALUES(:vehicle,:configuration,'engine_calibration','Synthetic','stage2',"
                    ":installed,NULL,'controlled future modification fixture',:created)"
                ),
                {
                    "vehicle": UUID(vehicle_id),
                    "configuration": UUID(stage_configuration),
                    "installed": effective_at,
                    "created": effective_at,
                },
            )
            inserted += 1
        await db.commit()
    return inserted


async def _vehicle_context(database: Database) -> dict[str, Any]:
    async with database.session() as db:
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT v.engine_code,vc.metadata->>'stage' AS stage,"
                        "count(DISTINCT v.id) AS vehicles,count(DISTINCT vc.id) AS configurations,"
                        "count(DISTINCT m.id) AS modifications "
                        "FROM vehicles v JOIN driving_sessions s ON s.vehicle_id=v.id "
                        "JOIN vehicle_configurations vc ON vc.id=s.configuration_id "
                        "LEFT JOIN modifications m ON m.configuration_id=vc.id "
                        "WHERE v.model LIKE 'PHASE9G-HELDOUT-%' "
                        "GROUP BY v.engine_code,vc.metadata->>'stage' "
                        "ORDER BY v.engine_code,stage"
                    )
                )
            )
            .mappings()
            .all()
        )
    return {
        "source_role": SourceRole.SYNTHETIC.value,
        "engine_stage_groups": [dict(row) for row in rows],
        "telemetry_source_type": "synthetic",
        "modifications_linked_to_versioned_configuration": True,
        "identities_exposed": False,
    }


def _future_exclusions(dataset: Any, future_pull_ids: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for exclusion in dataset.exclusions:
        if str(exclusion.get("input_pull_id")) not in future_pull_ids:
            continue
        reason = str(exclusion.get("reason", "UNKNOWN"))
        counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _future_exclusion_fingerprints(
    dataset: Any, future_pull_ids: set[str]
) -> list[str]:
    return sorted(
        stable_hash(
            {
                "input_pull_id": str(item.get("input_pull_id")),
                "reason": str(item.get("reason", "UNKNOWN")),
            }
        )
        for item in dataset.exclusions
        if str(item.get("input_pull_id")) in future_pull_ids
    )


def _feature_signal_availability(rows: tuple[SupervisedRow, ...]) -> dict[str, int]:
    missing: dict[str, int] = {}
    for row in rows:
        for signal, reason in row.missing.items():
            missing[f"{signal}:{reason}"] = missing.get(f"{signal}:{reason}", 0) + 1
    return dict(sorted(missing.items()))


def _bounded_abstention_reasons(
    task_reports: dict[str, dict[str, Any]],
) -> dict[str, int]:
    output = {
        "MISSING_SIGNAL": 0,
        "LOW_QUALITY": 0,
        "NO_COMPATIBLE_TARGET": 0,
        "OTHER": 0,
    }
    for report in task_reports.values():
        for reason, count in report["label_availability"][
            "excluded_pair_counts"
        ].items():
            if reason == "MISSING_OUTCOME_SIGNAL":
                category = "MISSING_SIGNAL"
            elif reason == "INSUFFICIENT_OUTCOME_QUALITY":
                category = "LOW_QUALITY"
            elif reason in {
                "NO_COMPATIBLE_PRIOR",
                "NO_COMPATIBLE_NEXT_PULL",
                "CONFIGURATION_BOUNDARY",
                "INCOMPATIBLE_SESSION",
            }:
                category = "NO_COMPATIBLE_TARGET"
            else:
                category = "OTHER"
            output[category] += int(count)
    return output


def _session_overlap_adversary(
    training_rows: tuple[SupervisedRow, ...],
    future_rows: tuple[SupervisedRow, ...],
) -> bool:
    split = chronological_calibration_split(future_rows)
    poison = replace(
        split.calibration[0],
        group_id=training_rows[0].group_id,
        session_id=training_rows[0].group_id,
        row_id=stable_hash({"adversarial": "training-session-overlap"}),
    )
    try:
        poisoned = chronological_calibration_split((poison, *future_rows[1:]))
        assert_disjoint_training_source(training_rows, poisoned)
    except EvaluationSplitError:
        return True
    return False


async def _train_and_evaluate_supervised(
    database: Database,
    telemetry: Telemetry,
    *,
    model_store: ModelArtifactStore,
    protocol: EvaluationProtocol,
) -> tuple[dict[str, dict[str, Any]], dict[str, TaskRunResult], dict[str, Any]]:
    base = await seed_predictive_fixture(database)
    await generate_fixture_features(database, base, telemetry=telemetry)
    future_fixtures: list[Any] = []
    for index, start in enumerate(FUTURE_STARTS):
        fixture = await seed_predictive_fixture(
            database,
            start_at=start,
            vehicle_model_prefix=f"PHASE9G-HELDOUT-{index + 1}",
            engine_codes=("N55", "B58", "S55"),
            scenario_seed=(137, 641, 911)[index],
            generator_version="phase9g-heldout-v4",
            vehicle_count=4,
        )
        await _record_modifications(database, fixture)
        await generate_fixture_features(database, fixture, telemetry=telemetry)
        future_fixtures.append(fixture)

    scenario_map = dict(base.scenario_family_by_session)
    model_runs: dict[str, TaskRunResult] = {}
    task_reports: dict[str, dict[str, Any]] = {}
    durations: dict[str, float] = {}
    calibration_fit_durations: dict[str, dict[str, float]] = {}
    future_sessions = {
        str(item) for fixture in future_fixtures for item in fixture.session_ids
    }
    future_pulls = {
        str(item) for fixture in future_fixtures for item in fixture.pull_ids
    }
    future_pull_ids = tuple(
        item for fixture in future_fixtures for item in fixture.pull_ids
    )
    base_pulls = {str(item) for item in base.pull_ids}
    for task in MLTask:
        started = time.perf_counter()
        with telemetry.tracer.start_as_current_span(
            "evaluation.supervised.task", attributes={"evaluation.task": task.value}
        ):
            model_run = await train_task(
                database,
                task,
                TRAINING_CUTOFF,
                source="synthetic",
                git_sha=_git_state(allow_dirty=True)[0],
                telemetry=telemetry,
                artifact_store=model_store,
                scenario_family_by_session=scenario_map,
            )
            future_dataset, _input_dataset, _outcome_dataset = await build_task_dataset(
                database,
                task,
                EVALUATION_CUTOFF,
                source="synthetic",
                telemetry=telemetry,
                scenario_family_by_session={
                    str(session): "controlled_unseen_context"
                    for session in future_sessions
                },
                candidate_pull_ids=future_pull_ids,
            )
            requested_candidate_ids = {str(item) for item in future_pull_ids}
            materialized_candidate_ids = {
                item.pull_id for item in _input_dataset.candidates
            }
            cohort_materialization = {
                "requested_pull_count": len(requested_candidate_ids),
                "requested_pull_fingerprint": stable_hash(
                    sorted(requested_candidate_ids)
                ),
                "materialized_pull_count": len(materialized_candidate_ids),
                "materialized_pull_fingerprint": stable_hash(
                    sorted(materialized_candidate_ids)
                ),
                "unrequested_pull_count": len(
                    materialized_candidate_ids - requested_candidate_ids
                ),
                "training_pull_count": len(materialized_candidate_ids & base_pulls),
            }
            _assert(
                materialized_candidate_ids == requested_candidate_ids,
                f"{task.value} canonical dataset escaped the predeclared held-out cohort",
            )
            future_rows = tuple(
                row for row in future_dataset.rows if row.session_id in future_sessions
            )
            _assert(
                bool(future_rows),
                f"{task.value} has no later synthetic evaluation rows",
            )
            future_run = replace(model_run, dataset=future_dataset)
            loaded = await model_store.load_registered(
                database, str(model_run.model_version_id)
            )
            result = evaluate_predictive_task(
                future_run,
                loaded,
                future_rows,
                output_root=str(EVIDENCE_ROOT / "calibrators"),
                protocol=protocol,
            )
            fit_durations = result.pop("_benchmark_calibration_fit_seconds")
            replay = evaluate_predictive_task(
                future_run,
                loaded,
                future_rows,
                output_root=str(EVIDENCE_ROOT / "calibrators"),
                protocol=protocol,
            )
            replay.pop("_benchmark_calibration_fit_seconds")
            _assert(
                result == replay,
                f"{task.value} repeated evaluation changed deterministic scientific output",
            )
        task_reports[task.value] = {
            **result,
            "label_availability": {
                "source_pull_count": sum(
                    len(fixture.pull_ids) for fixture in future_fixtures
                ),
                "cohort_materialization": cohort_materialization,
                "labeled_next_pull_rows": len(future_rows),
                "excluded_pair_counts": _future_exclusions(
                    future_dataset, future_pulls
                ),
                "excluded_pair_fingerprints": _future_exclusion_fingerprints(
                    future_dataset, future_pulls
                ),
                "source_dataset_fingerprint": future_dataset.source_fingerprint,
                "training_unlabeled_pair_counts": _future_exclusions(
                    model_run.dataset, base_pulls
                ),
                "training_unlabeled_pair_fingerprints": _future_exclusion_fingerprints(
                    model_run.dataset, base_pulls
                ),
                "unlabeled_outcomes_fabricated": False,
                "signal_missingness_counts": _feature_signal_availability(future_rows),
            },
            "generator_versions": ["phase9g-heldout-v4"],
            "training_session_overlap_adversary_blocked": _session_overlap_adversary(
                model_run.training.split.train, future_rows
            ),
        }
        model_runs[task.value] = model_run
        durations[task.value] = time.perf_counter() - started
        calibration_fit_durations[task.value] = fit_durations
    context = await _vehicle_context(database)
    return (
        task_reports,
        model_runs,
        {
            "task_seconds": durations,
            "calibration_fit_seconds": calibration_fit_durations,
            "future_session_count": len(future_sessions),
            "future_pull_count": len(future_pulls),
            "vehicle_configuration_modification_context": context,
        },
    )


def evaluate_predictive_task(
    task_run: TaskRunResult,
    artifact: Any,
    future_rows: tuple[SupervisedRow, ...],
    *,
    output_root: str,
    protocol: EvaluationProtocol,
) -> dict[str, Any]:
    from vehicle_platform.evaluation.supervised import evaluate_supervised_task

    return evaluate_supervised_task(
        task_run=task_run,
        artifact=artifact,
        future_rows=future_rows,
        cutoff=EVALUATION_CUTOFF,
        output_root=output_root,
        bootstrap_resamples=200,
        calibration_fraction=protocol.calibration_fraction,
        validation_fraction=protocol.validation_fraction,
    )


async def _source_detector_ids(
    database: Database, receipt: dict[str, Any]
) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    async with database.session() as db:
        for family, methods in receipt["test_comparison_after_freeze"].items():
            output[family] = {}
            for method, result in methods.items():
                value = await db.scalar(
                    text(
                        "SELECT detector_version_id FROM anomaly_detection_runs "
                        "WHERE id=:run AND artifact_checksum=:checksum"
                    ),
                    {"run": result["run_id"], "checksum": result["artifact_checksum"]},
                )
                if value is None:
                    raise AssertionError(
                        f"{family}/{method} receipt has no registered detector"
                    )
                output[family][method] = str(value)
    return output


def _minimal_phase9c_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    cases: dict[str, dict[str, Any]] = {}
    for family, methods in receipt["test_comparison_after_freeze"].items():
        cases[family] = {}
        for method, result in methods.items():
            cases[family][method] = {
                "run_id": result["run_id"],
                "artifact_checksum": result["artifact_checksum"],
                "threshold_frozen_on_validation": result[
                    "threshold_frozen_on_validation"
                ],
                "case_evaluation": [
                    {
                        key: row.get(key)
                        for key in (
                            "fold",
                            "scenario",
                            "status",
                            "score",
                            "threshold",
                            "predicted_anomaly",
                            "environmental_context_shift",
                            "evaluation_role",
                        )
                    }
                    for row in result["case_evaluation"]
                ],
            }
    return {
        "schema_version": receipt["schema_version"],
        "execution_state": receipt["execution_state"],
        "source_data": receipt["source_data"],
        "benchmark": {"reference_rows": receipt["benchmark"]["reference_rows"]},
        "test_comparison_after_freeze": cases,
    }


async def _anomaly_evaluation() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any]
]:
    receipt = await evaluate_anomaly_detection.evaluate()
    database = evaluate_anomaly_detection._ACTIVE_DATABASE
    telemetry = evaluate_anomaly_detection._ACTIVE_TELEMETRY
    if database is None or telemetry is None:
        raise AssertionError(
            "Phase 9C source evaluator did not retain its disposable DB handle"
        )
    try:
        artifact_roots = await asyncio.to_thread(
            lambda: tuple((EVIDENCE_ROOT.parent / "phase9c").glob("artifacts-*"))
        )
        sensitivity = await evaluate_reference_size_sensitivity(
            database, receipt, artifact_roots=artifact_roots
        )
        repeated = await evaluate_reference_size_sensitivity(
            database, receipt, artifact_roots=artifact_roots
        )
        _assert(
            sensitivity == repeated, "9C reference-size experiment is not reproducible"
        )
        anomaly_report = evaluate_phase9c_receipt(receipt)
        detector_ids = await _source_detector_ids(database, receipt)
        for family, methods in detector_ids.items():
            for method, detector_id in methods.items():
                anomaly_report["families"][family][method]["detector_version_id"] = (
                    detector_id
                )
        return anomaly_report, sensitivity, _minimal_phase9c_receipt(receipt)
    finally:
        telemetry.shutdown()
        await database.close()
        evaluate_anomaly_detection._ACTIVE_DATABASE = None
        evaluate_anomaly_detection._ACTIVE_TELEMETRY = None


async def _integrity_adversaries(
    database: Database,
    model_store: ModelArtifactStore,
    model_runs: dict[str, TaskRunResult],
    phase9c_receipt: dict[str, Any],
    phase9c_report: dict[str, Any],
) -> dict[str, Any]:
    model_tamper_rejected: dict[str, bool] = {}
    model_artifact_manifest: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="phase9g-model-tamper-") as directory:
        temporary_root = Path(directory)
        for task, model_run in model_runs.items():
            source = model_store.root / model_run.artifact.relative_path
            source_bytes = await asyncio.to_thread(source.read_bytes)
            source_checksum = hashlib.sha256(source_bytes).hexdigest()
            _assert(
                source_checksum == model_run.artifact.checksum,
                f"{task} registered model bytes differ before tamper test",
            )
            model_artifact_manifest[task] = {
                "path": source.relative_to(REPOSITORY_ROOT).as_posix(),
                "checksum": source_checksum,
                "bytes": len(source_bytes),
            }
            target = temporary_root / model_run.artifact.relative_path
            await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copyfile, source, target)
            await asyncio.to_thread(_flip_one_byte, target)
            try:
                await ModelArtifactStore(temporary_root).load_registered(
                    database, str(model_run.model_version_id)
                )
            except ModelArtifactValidationError:
                model_tamper_rejected[task] = True
            else:
                model_tamper_rejected[task] = False

    first_family = next(iter(phase9c_receipt["test_comparison_after_freeze"]))
    first_method = next(
        iter(phase9c_receipt["test_comparison_after_freeze"][first_family])
    )
    detector_id = phase9c_report["families"][first_family][first_method][
        "detector_version_id"
    ]
    async with database.session() as db:
        registered = (
            (
                await db.execute(
                    text(
                        "SELECT artifact_path,artifact_checksum,artifact_size_bytes "
                        "FROM anomaly_detector_versions WHERE id=:id"
                    ),
                    {"id": detector_id},
                )
            )
            .mappings()
            .first()
        )
    if registered is None:
        raise AssertionError("9C artifact registry row is missing during tamper test")
    artifact_path = registered["artifact_path"]
    if not isinstance(artifact_path, str):
        raise TypeError("9C artifact path missing during tamper test")
    expected_artifact_checksum = str(registered["artifact_checksum"])
    expected_artifact_size = int(registered["artifact_size_bytes"])
    source_roots = await asyncio.to_thread(
        lambda: tuple((EVIDENCE_ROOT.parent / "phase9c").glob("artifacts-*"))
    )
    matching_paths = []
    for root in source_roots:
        candidate = root / artifact_path
        if not candidate.is_file():
            continue
        content = await asyncio.to_thread(candidate.read_bytes)
        if (
            len(content) == expected_artifact_size
            and hashlib.sha256(content).hexdigest() == expected_artifact_checksum
        ):
            matching_paths.append(candidate)
    if len(matching_paths) != 1:
        raise AssertionError("registered 9C artifact bytes are missing or ambiguous")
    source_file = matching_paths[0]
    anomaly_tamper_rejected = False
    with tempfile.TemporaryDirectory(prefix="phase9g-detector-tamper-") as directory:
        temporary_root = Path(directory)
        target = temporary_root / artifact_path
        await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copyfile, source_file, target)
        await asyncio.to_thread(_flip_one_byte, target)
        try:
            await AnomalyArtifactStore(temporary_root).load_registered(
                database, detector_id
            )
        except Exception as error:
            if type(error).__module__.startswith("vehicle_platform.anomalies"):
                anomaly_tamper_rejected = True
            else:
                raise

    detector_artifact_manifest: dict[str, dict[str, Any]] = {}
    artifact_roots = await asyncio.to_thread(
        lambda: tuple((EVIDENCE_ROOT.parent / "phase9c").glob("artifacts-*"))
    )
    async with database.session() as db:
        for family, methods in sorted(phase9c_report["families"].items()):
            for method, detector in sorted(methods.items()):
                row = (
                    (
                        await db.execute(
                            text(
                                "SELECT artifact_path,artifact_checksum,artifact_size_bytes "
                                "FROM anomaly_detector_versions WHERE id=:id"
                            ),
                            {"id": detector["detector_version_id"]},
                        )
                    )
                    .mappings()
                    .first()
                )
                if row is None or not isinstance(row["artifact_path"], str):
                    raise AssertionError(
                        "registered detector artifact metadata is missing"
                    )
                candidates = [
                    root / row["artifact_path"]
                    for root in artifact_roots
                    if (root / row["artifact_path"]).is_file()
                ]
                matching = []
                for candidate in candidates:
                    candidate_bytes = await asyncio.to_thread(candidate.read_bytes)
                    if (
                        len(candidate_bytes) == int(row["artifact_size_bytes"])
                        and hashlib.sha256(candidate_bytes).hexdigest()
                        == row["artifact_checksum"]
                    ):
                        matching.append(candidate)
                if len(matching) != 1:
                    raise AssertionError(
                        "registered detector artifact path is ambiguous"
                    )
                artifact_file = matching[0]
                artifact_bytes = await asyncio.to_thread(artifact_file.read_bytes)
                digest = hashlib.sha256(artifact_bytes).hexdigest()
                if digest != row["artifact_checksum"] or len(artifact_bytes) != int(
                    row["artifact_size_bytes"]
                ):
                    raise AssertionError(
                        "registered detector artifact bytes fail integrity"
                    )
                detector_artifact_manifest[f"{family}:{method}"] = {
                    "path": artifact_file.relative_to(REPOSITORY_ROOT).as_posix(),
                    "checksum": digest,
                    "bytes": len(artifact_bytes),
                }

    modified_receipt = json.loads(json.dumps(phase9c_receipt))
    modified_receipt["test_comparison_after_freeze"][first_family][first_method][
        "artifact_checksum"
    ] = "0" * 64
    source_receipt_tamper_rejected = False
    try:
        evaluate_phase9c_receipt(modified_receipt)
    except ValueError:
        source_receipt_tamper_rejected = True
    return {
        "9b_registered_artifact_tamper_rejected": model_tamper_rejected,
        "9c_registered_artifact_tamper_rejected": anomaly_tamper_rejected,
        "9c_source_receipt_checksum_tamper_rejected": source_receipt_tamper_rejected,
        "registered_artifact_manifest": {
            "9b_models": model_artifact_manifest,
            "9c_detectors": detector_artifact_manifest,
        },
        "source_artifacts_modified": False,
    }


def _flip_one_byte(path: Path) -> None:
    content = bytearray(path.read_bytes())
    if not content:
        raise AssertionError("cannot tamper with empty artifact")
    content[len(content) // 2] ^= 0x01
    path.write_bytes(content)


def _metric_results(
    task_reports: dict[str, dict[str, Any]],
) -> tuple[MetricResult, ...]:
    output: list[MetricResult] = []
    for _task, report in sorted(task_reports.items()):
        by_method = report["calibration_metrics"]["test"]
        method_metrics = {"identity_uncalibrated": by_method["identity_uncalibrated"]}
        selected = report["selected_research_candidate"]
        candidate = by_method.get(selected, {})
        if isinstance(candidate.get("metrics"), dict):
            method_metrics[f"selected_{selected}"] = candidate["metrics"]
        for metrics in method_metrics.values():
            for key in ("brier_score", "log_loss", "ece", "auroc", "average_precision"):
                metric = metrics.get(key)
                if isinstance(metric, dict):
                    output.append(
                        MetricResult.model_validate_json(
                            json.dumps(metric, sort_keys=True, separators=(",", ":"))
                        )
                    )
    return tuple(output)


def _drift_records(
    task_reports: dict[str, dict[str, Any]],
) -> tuple[DriftComparison, ...]:
    output: list[DriftComparison] = []
    for task, report in sorted(task_reports.items()):
        end = datetime.fromisoformat(report["partitions"]["TEST"]["end"])
        feature_report = report["drift"]["feature_drift"]
        for feature, values in sorted(feature_report["features"].items()):
            for metric_name, metric in (
                ("PSI", "psi"),
                ("MEDIAN_SHIFT", "robust_median_shift"),
            ):
                value = values[metric]
                threshold = 0.20 if metric_name == "PSI" else None
                output.append(
                    DriftComparison(
                        feature_family=f"{task}:{feature}",
                        metric=metric_name,
                        baseline_window="9B_TRAIN_ONLY",
                        comparison_window="9G_HELDOUT_TEST_ONLY",
                        value=value,
                        unit="population_stability_index"
                        if metric_name == "PSI"
                        else "robust_scale",
                        status=MetricStatus.DEFINED
                        if value is not None
                        else MetricStatus.INSUFFICIENT_SUPPORT,
                        cutoff=end,
                        labeled_support=report["partitions"]["TEST"]["rows"],
                        warning_threshold=threshold,
                        warning=bool(
                            threshold is not None
                            and value is not None
                            and value >= threshold
                        ),
                        interpretation=(
                            "feature distribution warning only; not fault or diagnosis evidence"
                        ),
                    )
                )
        prevalence = report["drift"]["label_prevalence_drift"]
        value = prevalence.get("value")
        output.append(
            DriftComparison(
                feature_family=task,
                metric="LABEL_PREVALENCE",
                baseline_window="9B_TRAIN_ONLY",
                comparison_window="9G_HELDOUT_TEST_ONLY",
                value=value,
                unit="synthetic_label_rate_delta",
                status=MetricStatus.DEFINED
                if value is not None
                else MetricStatus.UNDEFINED,
                cutoff=end,
                labeled_support=report["partitions"]["TEST"]["rows"],
                warning_threshold=0.10,
                warning=bool(value is not None and abs(value) >= 0.10),
                interpretation="synthetic target prevalence only; no real outcome claim",
            )
        )
        concept = report["drift"]["concept_performance_drift"]
        concept_value = concept.get("value")
        output.append(
            DriftComparison(
                feature_family=task,
                metric="CONCEPT_CHANGE",
                baseline_window="9B_TRAIN_ONLY",
                comparison_window="9G_HELDOUT_TEST_ONLY",
                value=concept_value,
                unit="synthetic_brier_delta",
                status=MetricStatus.DEFINED
                if concept_value is not None
                else MetricStatus.UNDEFINED,
                cutoff=end,
                labeled_support=report["partitions"]["TEST"]["rows"],
                warning_threshold=0.10,
                warning=bool(concept_value is not None and abs(concept_value) >= 0.10),
                interpretation="synthetic performance change; not production monitoring evidence",
            )
        )
        validation_ece = (
            report["calibration_metrics"]["validation"][
                report["selected_research_candidate"]
            ]
            .get("ece", {})
            .get("value")
        )
        test_ece = (
            report["calibration_metrics"]["test"]
            .get(report["selected_research_candidate"], {})
            .get("metrics", {})
            .get("ece", {})
            .get("value")
        )
        calibration_delta = (
            float(test_ece) - float(validation_ece)
            if validation_ece is not None and test_ece is not None
            else None
        )
        output.append(
            DriftComparison(
                feature_family=task,
                metric="CALIBRATION",
                baseline_window="9G_VALIDATION",
                comparison_window="9G_HELDOUT_TEST",
                value=calibration_delta,
                unit="synthetic_ece_delta",
                status=(
                    MetricStatus.DEFINED
                    if calibration_delta is not None
                    else MetricStatus.INSUFFICIENT_SUPPORT
                ),
                cutoff=end,
                labeled_support=report["partitions"]["TEST"]["rows"],
                warning_threshold=0.10,
                warning=bool(
                    calibration_delta is not None and abs(calibration_delta) >= 0.10
                ),
                interpretation=(
                    "synthetic validation-to-test reliability change; no transfer claim"
                ),
            )
        )
    return tuple(output)


def _applicability(
    task_reports: dict[str, dict[str, Any]],
    anomaly_report: dict[str, Any],
) -> tuple[ApplicabilityAssessment, ...]:
    output: list[ApplicabilityAssessment] = []
    for task, report in sorted(task_reports.items()):
        output.append(
            assess_source_applicability(
                subject_kind="9B_TASK",
                subject_key=task,
                subject_version=report["model_version"],
                source_role=SourceRole.SYNTHETIC,
                source_fingerprint=report["source_fingerprint"],
                evaluation_rows=report["partitions"]["TEST"]["rows"],
                labeled_outcomes=report["partitions"]["TEST"]["rows"],
                required_signals=tuple(
                    sorted(report["target_definition"].get("required_signals", ()))
                ),
                observed_signals=tuple(
                    report["target_definition"].get("required_signals", ())
                ),
                same_configuration_history=False,
                calibration_available=any(
                    item["method"] != CalibrationMethod.IDENTITY.value
                    and item["state"] in {"ELIGIBLE", "SELECTED"}
                    for item in report["calibration_candidates"]
                ),
            )
        )
        for role in (
            SourceRole.IMPORTED_FIXTURE,
            SourceRole.IMPORTED,
            SourceRole.REAL_VEHICLE,
        ):
            output.append(
                assess_source_applicability(
                    subject_kind="9B_TASK",
                    subject_key=task,
                    subject_version=report["model_version"],
                    source_role=role,
                    source_fingerprint=stable_hash(
                        {"role": role.value, "task": task, "rows": 0}
                    ),
                    evaluation_rows=0,
                    labeled_outcomes=0,
                    required_signals=tuple(
                        sorted(report["target_definition"].get("required_signals", ()))
                    ),
                    observed_signals=(),
                    same_configuration_history=False,
                    calibration_available=False,
                )
            )
    for family, methods in sorted(anomaly_report["families"].items()):
        first = next(iter(methods.values()))
        output.append(
            assess_source_applicability(
                subject_kind="9C_FAMILY",
                subject_key=family,
                subject_version=str(first["detector_version_id"]),
                source_role=SourceRole.SYNTHETIC,
                source_fingerprint=stable_hash(
                    sorted(item["artifact_checksum"] for item in methods.values())
                ),
                evaluation_rows=first["clean_false_alarm"]["eligible"],
                labeled_outcomes=0,
                required_signals=(),
                observed_signals=(),
                same_configuration_history=True,
                calibration_available=False,
            )
        )
    for kind, key, version in (
        ("9D_RECEIPT", "prediction-service", "phase9g-compatibility-review-v1"),
        ("9E_EVIDENCE", "prediction-evidence", "phase9g-compatibility-review-v1"),
        ("9F_AGENT", "agent-prediction", "phase9g-compatibility-review-v1"),
    ):
        output.append(
            assess_source_applicability(
                subject_kind=kind,
                subject_key=key,
                subject_version=version,
                source_role=SourceRole.SYNTHETIC,
                source_fingerprint=stable_hash({"kind": kind, "version": version}),
                evaluation_rows=0,
                labeled_outcomes=0,
                required_signals=(),
                observed_signals=(),
                same_configuration_history=False,
                calibration_available=False,
            )
        )
    return tuple(output)


async def _evidence_refs(
    database: Database,
    task_runs: dict[str, TaskRunResult],
    anomaly_report: dict[str, Any],
) -> tuple[EvaluationEvidenceRef, ...]:
    output: list[EvaluationEvidenceRef] = []
    feature_versions: set[str] = set()
    label_checksums: set[str] = set()
    for _task, model_run in sorted(task_runs.items()):
        model_spec = model_run.dataset.model_spec
        feature_versions.add(model_spec.feature_set_version)
        label_checksums.add(model_spec.label_definition.checksum)
        loaded_at = model_run.training.split.cutoffs.get("test_end")
        known_at = datetime.fromisoformat(loaded_at) if loaded_at else TRAINING_CUTOFF
        output.append(
            EvaluationEvidenceRef(
                kind="9B_REGISTERED_MODEL_ARTIFACT",
                version=model_run.training.selected_family.value,
                entity_fingerprint=stable_hash(str(model_run.model_version_id)),
                content_checksum=model_run.artifact.checksum,
                source_role=SourceRole.SYNTHETIC,
                known_at=known_at,
            )
        )
    async with database.session() as db:
        for feature_version in sorted(feature_versions):
            feature = (
                (
                    await db.execute(
                        text(
                            "SELECT checksum,created_at FROM feature_set_versions "
                            "WHERE version=:version"
                        ),
                        {"version": feature_version},
                    )
                )
                .mappings()
                .first()
            )
            if feature is None:
                raise AssertionError("registered feature-set version is unavailable")
            output.append(
                EvaluationEvidenceRef(
                    kind="9A_FEATURE_SET_SCHEMA",
                    version=feature_version,
                    entity_fingerprint=stable_hash(feature_version),
                    content_checksum=str(feature["checksum"]),
                    source_role=SourceRole.SYNTHETIC,
                    known_at=feature["created_at"],
                )
            )
        for label_checksum in sorted(label_checksums):
            label = (
                (
                    await db.execute(
                        text(
                            "SELECT key,version,checksum,created_at FROM label_definitions "
                            "WHERE checksum=:checksum"
                        ),
                        {"checksum": label_checksum},
                    )
                )
                .mappings()
                .first()
            )
            if label is None:
                raise AssertionError("registered label definition is unavailable")
            output.append(
                EvaluationEvidenceRef(
                    kind="9B_LABEL_DEFINITION",
                    version=f"{label['key']}:{label['version']}",
                    entity_fingerprint=stable_hash(label_checksum),
                    content_checksum=str(label["checksum"]),
                    source_role=SourceRole.SYNTHETIC,
                    known_at=label["created_at"],
                )
            )
        for family, methods in sorted(anomaly_report["families"].items()):
            for method, result in sorted(methods.items()):
                source = (
                    (
                        await db.execute(
                            text(
                                "SELECT v.created_at AS version_created_at,"
                                "r.created_at AS reference_created_at,r.checksum AS reference_checksum,"
                                "d.created_at AS definition_created_at,d.checksum AS definition_checksum,"
                                "d.version AS definition_version "
                                "FROM anomaly_detector_versions v "
                                "JOIN anomaly_reference_datasets r ON r.id=v.reference_dataset_id "
                                "JOIN anomaly_detector_definitions d ON d.id=v.detector_definition_id "
                                "WHERE v.id=:id"
                            ),
                            {"id": result["detector_version_id"]},
                        )
                    )
                    .mappings()
                    .first()
                )
                if source is None:
                    raise AssertionError(
                        "registered detector source lineage is unavailable"
                    )
                known_at = source["version_created_at"]
                if known_at is None:
                    raise AssertionError("detector artifact timestamp is unavailable")
                entity = stable_hash(result["detector_version_id"])
                output.append(
                    EvaluationEvidenceRef(
                        kind="9C_REFERENCE_DATASET",
                        version=f"{family}:{method}:{source['definition_version']}",
                        entity_fingerprint=stable_hash(
                            str(result["detector_version_id"]) + ":reference"
                        ),
                        content_checksum=str(source["reference_checksum"]),
                        source_role=SourceRole.SYNTHETIC,
                        known_at=source["reference_created_at"],
                    )
                )
                output.append(
                    EvaluationEvidenceRef(
                        kind="9C_DETECTOR_DEFINITION",
                        version=f"{family}:{method}:{source['definition_version']}",
                        entity_fingerprint=stable_hash(
                            str(result["detector_version_id"]) + ":definition"
                        ),
                        content_checksum=str(source["definition_checksum"]),
                        source_role=SourceRole.SYNTHETIC,
                        known_at=source["definition_created_at"],
                    )
                )
                output.append(
                    EvaluationEvidenceRef(
                        kind="9C_REGISTERED_DETECTOR_ARTIFACT",
                        version=f"{family}:{method}",
                        entity_fingerprint=entity,
                        content_checksum=result["artifact_checksum"],
                        source_role=SourceRole.SYNTHETIC,
                        known_at=known_at,
                    )
                )
    return tuple(output)


def _fold_manifests(
    task_reports: dict[str, dict[str, Any]],
) -> tuple[FoldManifest, ...]:
    output: list[FoldManifest] = []
    for task, report in sorted(task_reports.items()):
        for name, partition in report["partitions"].items():
            output.append(
                FoldManifest(
                    fold_id=f"{task}:{name}",
                    partition=name,
                    row_count=partition["rows"],
                    positive_count=partition["positives"],
                    negative_count=partition["negatives"],
                    session_count=partition["sessions"],
                    vehicle_count=partition["vehicles"],
                    start_at=datetime.fromisoformat(partition["start"]),
                    end_at=datetime.fromisoformat(partition["end"]),
                    row_fingerprint=partition["row_fingerprint"],
                    session_fingerprint=partition["session_fingerprint"],
                    source_fingerprint=report["source_fingerprint"],
                    eligible=(name in {"TRAIN", "TEST"} and partition["rows"] > 0),
                    exclusions=(
                        report["label_availability"]["excluded_pair_counts"]
                        if name == "TEST"
                        else {}
                    ),
                )
            )
    return tuple(output)


def _dataset_manifest(task_reports: dict[str, dict[str, Any]]) -> DatasetManifest:
    labeled_count = sum(
        sum(partition["rows"] for partition in report["partitions"].values())
        for report in task_reports.values()
    )
    unlabeled = sum(
        sum(report["label_availability"]["excluded_pair_counts"].values())
        for report in task_reports.values()
    )
    row_ids = sorted(
        row
        for report in task_reports.values()
        for partition in report["partitions"].values()
        for row in partition["row_ids"]
    )
    excluded_fingerprints = sorted(
        fingerprint
        for report in task_reports.values()
        for fingerprint in (
            *report["label_availability"]["excluded_pair_fingerprints"],
            *report["label_availability"]["training_unlabeled_pair_fingerprints"],
        )
    )
    row_ids.extend(excluded_fingerprints)
    row_ids.sort()
    source_dataset_fingerprints = sorted(
        report["label_availability"]["source_dataset_fingerprint"]
        for report in task_reports.values()
    )
    source = stable_hash(
        {
            "task_source_fingerprints": source_dataset_fingerprints,
            "excluded_pair_fingerprints": excluded_fingerprints,
        }
    )
    session_fingerprints = {
        item
        for report in task_reports.values()
        for partition in report["partitions"].values()
        for item in partition["session_fingerprints"]
    }
    vehicle_fingerprints = {
        item
        for report in task_reports.values()
        for partition in report["partitions"].values()
        for item in partition["vehicle_fingerprints"]
    }
    configuration_fingerprints = {
        item
        for report in task_reports.values()
        for partition in report["partitions"].values()
        for item in partition["configuration_fingerprints"]
    }
    feature_version = next(iter(task_reports.values()))["feature_set_version"]
    return DatasetManifest(
        source_role=SourceRole.SYNTHETIC,
        source_kind="canonical_phase9a_features_with_phase9g_heldout_synthetic_generator",
        row_count=labeled_count + unlabeled,
        labeled_count=labeled_count,
        unlabeled_count=unlabeled,
        vehicle_count=len(vehicle_fingerprints),
        configuration_count=len(configuration_fingerprints),
        session_count=len(session_fingerprints),
        feature_set_version=feature_version,
        source_fingerprint=source,
        row_fingerprint=stable_hash(row_ids),
        cutoff=EVALUATION_CUTOFF,
        known_at_policy="input_available_before_next_pull_target_v1",
        generator_version="phase9g-heldout-v4",
    )


def _stress_scenarios(phase9c_receipt: dict[str, Any]) -> tuple[StressScenario, ...]:
    names = sorted(
        {
            str(row["scenario"])
            for family in phase9c_receipt["test_comparison_after_freeze"].values()
            for method in family.values()
            for row in method["case_evaluation"]
        }
    )
    output: list[StressScenario] = []
    families = {"thermal", "boost_air", "performance", "fuel"}
    for name in names:
        positives = (name,) if name in families else ()
        output.append(
            StressScenario(
                scenario_id=f"9c-{name}",
                family=name if name in families else "confounder_or_quality_control",
                oracle_kind="controlled_synthetic_intervention_or_named_negative_control",
                oracle_positive_families=positives,
                expected_changes=("relative_deviation_may_change",),
                source_role=SourceRole.SYNTHETIC,
                generator_version="phase9c-evaluator-v1",
                metadata_excluded_from_features=True,
            )
        )
    return tuple(output)


def _positive_calibration_fixture(seed: int = 4917) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    size = 4_000
    raw = np.linspace(0.02, 0.98, size)
    logits = np.log(raw / (1 - raw))
    true_probability = 1 / (1 + np.exp(-(-0.45 + 0.62 * logits)))
    labels = rng.binomial(1, true_probability).astype(int)
    raw_values = tuple(float(value) for value in raw)
    label_values = tuple(int(value) for value in labels)
    clusters = tuple(f"session-{index // 40}" for index in range(size))
    ids = tuple(f"synthetic-row-{index}" for index in range(size))
    fit_end, validation_end = 2_400, 3_200
    fitted = fit_calibrator(
        CalibrationMethod.SIGMOID,
        raw_values[:fit_end],
        label_values[:fit_end],
        row_ids=ids[:fit_end],
        clusters=clusters[:fit_end],
        dataset_checksum=stable_hash(ids[:fit_end]),
    )
    if fitted is None:
        raise AssertionError(
            "known-bias sigmoid fixture did not meet preregistered support"
        )
    mapped = apply_calibrator(fitted, raw_values)

    def brier(values: Sequence[float], targets: Sequence[int]) -> float:
        predictions = np.asarray(values, dtype=np.float64)
        outcomes = np.asarray(targets, dtype=np.float64)
        return float(np.mean((predictions - outcomes) ** 2))

    validation_raw = brier(
        raw_values[fit_end:validation_end], label_values[fit_end:validation_end]
    )
    validation_mapped = brier(
        mapped[fit_end:validation_end], label_values[fit_end:validation_end]
    )
    test_raw = brier(raw_values[validation_end:], label_values[validation_end:])
    test_mapped = brier(mapped[validation_end:], label_values[validation_end:])
    if not validation_mapped < validation_raw:
        raise AssertionError(
            "synthetic known-bias fixture did not improve on validation"
        )
    return {
        "source_role": SourceRole.SYNTHETIC.value,
        "data_generating_mapping": "sigmoid(-0.45 + 0.62 * logit(raw_score))",
        "fit_rows": fit_end,
        "fit_sessions": len(set(clusters[:fit_end])),
        "validation_rows": validation_end - fit_end,
        "test_rows": size - validation_end,
        "validation_brier_identity": validation_raw,
        "validation_brier_sigmoid": validation_mapped,
        "test_brier_identity": test_raw,
        "test_brier_sigmoid": test_mapped,
        "improved_validation_only": True,
        "test_used_for_fit_or_selection": False,
        "real_world_calibration_claim": False,
    }


def _calibration_adversaries() -> dict[str, Any]:
    rejected_all_one = fit_calibrator(
        CalibrationMethod.SIGMOID,
        (0.1, 0.2, 0.3, 0.4),
        (1, 1, 1, 1),
        row_ids=("a", "b", "c", "d"),
        clusters=("s1", "s2", "s3", "s4"),
        dataset_checksum=stable_hash(("a", "b", "c", "d")),
        minimum_rows=4,
        minimum_each_class=2,
        minimum_clusters=4,
    )
    duplicate_rejected = False
    try:
        fit_calibrator(
            CalibrationMethod.SIGMOID,
            (0.1, 0.2),
            (0, 1),
            row_ids=("same", "same"),
            clusters=("s1", "s2"),
            dataset_checksum=stable_hash(("same",)),
            minimum_rows=2,
            minimum_each_class=1,
            minimum_clusters=2,
        )
    except CalibrationError:
        duplicate_rejected = True
    missing = binary_metrics(
        (0.1, None, 0.8, 0.7),
        (0, None, 1, 1),
        threshold=0.5,
        source_role=SourceRole.SYNTHETIC,
        fold_id="MISSING_LABEL_ADVERSARY",
        row_ids=("r1", "r2", "r3", "r4"),
        clusters=("s1", "s2", "s3", "s4"),
        bootstrap_resamples=0,
    )
    return {
        "single_class_calibrator_rejected": rejected_all_one is None,
        "duplicate_calibration_identity_rejected": duplicate_rejected,
        "missing_labels_excluded_from_denominator": (
            missing["support"]["scored_labeled"] == 3
            and missing["support"]["abstained_or_unlabeled"] == 1
            and missing["brier_score"]["denominator"] == 3
        ),
        "missing_label_metrics": missing,
    }


def _drift_adversaries() -> dict[str, Any]:
    baseline = (290.0, 291.0, 292.0, 293.0, 294.0)
    shifted = (310.0, 311.0, 312.0, 313.0, 314.0)
    unlabelled = drift_experiment(
        {"thermal.iat_start": baseline},
        {"thermal.iat_start": shifted},
    )
    shifted_ambient_stable_relationship = drift_experiment(
        {"ambient": (10, 11, 12, 13, 14, 15)},
        {"ambient": (30, 31, 32, 33, 34, 35)},
        baseline_labels=(0, 1, 0, 1, 0, 1),
        comparison_labels=(0, 1, 0, 1, 0, 1),
        baseline_predictions=(0.2, 0.8, 0.2, 0.8, 0.2, 0.8),
        comparison_predictions=(0.2, 0.8, 0.2, 0.8, 0.2, 0.8),
    )
    label_change_stable_features = drift_experiment(
        {"ambient": (10, 11, 12, 13, 14, 15)},
        {"ambient": (10, 11, 12, 13, 14, 15)},
        baseline_labels=(0, 0, 0, 0, 0, 0),
        comparison_labels=(1, 1, 1, 1, 1, 1),
        baseline_predictions=(0.2,) * 6,
        comparison_predictions=(0.2,) * 6,
    )
    ood = ood_distances(
        {"thermal.iat_start": tuple(float(item) for item in range(10, 20))},
        {"thermal.iat_start": (500.0, 501.0)},
    )
    return {
        "checks": {
            "unlabeled_concept_change_unknown": (
                unlabelled["concept_performance_drift"]["status"] == "UNKNOWN"
            ),
            "unlabeled_prevalence_shift_unknown": (
                unlabelled["label_prevalence_drift"]["status"] == "UNKNOWN"
            ),
            "feature_distribution_shift_warning": (
                unlabelled["feature_drift"]["status"] == "WARNING"
            ),
            "extreme_feature_outlier_warns_without_diagnosis": (
                ood["warning_feature_count"] == 1
                and "not a fault" in ood["interpretation"]
            ),
            "ambient_shift_does_not_prove_performance_loss": (
                shifted_ambient_stable_relationship["feature_drift"]["status"]
                == "WARNING"
                and shifted_ambient_stable_relationship["concept_performance_drift"][
                    "value"
                ]
                == 0.0
            ),
            "label_change_without_feature_shift_is_separately_evaluable": (
                label_change_stable_features["feature_drift"]["status"]
                == "NO_PREDECLARED_WARNING"
                and label_change_stable_features["concept_performance_drift"]["value"]
                > 0.0
            ),
        },
        "known_metrics": {
            "baseline_support": len(baseline),
            "comparison_support": len(shifted),
            "psi": population_stability_index(baseline, shifted),
            "robust_median_shift": robust_location_shift(baseline, shifted),
            "interpretation": "distribution warning only; not a diagnosis",
        },
    }


def _check_partition_safety(task_reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for task, report in task_reports.items():
        partitions = report["partitions"]
        names = ("TRAIN", "CALIBRATION", "VALIDATION", "TEST")
        for left_index, left in enumerate(names):
            for right in names[left_index + 1 :]:
                left_rows = set(partitions[left]["row_ids"])
                right_rows = set(partitions[right]["row_ids"])
                _assert(
                    not left_rows.intersection(right_rows),
                    f"{task} row leakage: {left}/{right}",
                )
                left_pulls = set(partitions[left]["pull_fingerprints"])
                right_pulls = set(partitions[right]["pull_fingerprints"])
                _assert(
                    not left_pulls.intersection(right_pulls),
                    f"{task} pull leakage: {left}/{right}",
                )
                left_sessions = set(partitions[left]["session_fingerprints"])
                right_sessions = set(partitions[right]["session_fingerprints"])
                _assert(
                    not left_sessions.intersection(right_sessions),
                    f"{task} session leakage: {left}/{right}",
                )
        _assert(
            partitions["TRAIN"]["end"]
            < partitions["CALIBRATION"]["start"]
            < partitions["VALIDATION"]["start"]
            < partitions["TEST"]["start"],
            f"{task} temporal windows are not strict chronological blocks",
        )
        _assert(
            report["holdout_axes"]["model_training_vehicle_holdout"],
            f"{task} vehicle holdout overlaps training",
        )
        _assert(
            report["holdout_axes"]["model_training_configuration_holdout"],
            f"{task} configuration holdout overlaps training",
        )
        output[task] = {
            "four_partition_rows_and_physical_pulls_disjoint": True,
            "strict_chronology": True,
            "training_vehicle_holdout": True,
            "training_configuration_holdout": True,
            "training_session_overlap_adversary_blocked": report[
                "training_session_overlap_adversary_blocked"
            ],
        }
        _assert(
            report["training_session_overlap_adversary_blocked"],
            f"{task} accepted an adversarial training-session overlap",
        )
    output["training_session_overlap_adversary_blocked"] = True
    return output


async def _tamper_checks(
    database: Database,
    model_store: ModelArtifactStore,
    model_runs: dict[str, TaskRunResult],
    anomaly_report: dict[str, Any],
    phase9c_receipt: dict[str, Any],
) -> dict[str, Any]:
    return await _integrity_adversaries(
        database,
        model_store,
        model_runs,
        phase9c_receipt,
        anomaly_report,
    )


def _curve_support(task_reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for task, report in sorted(task_reports.items()):
        result[task] = {}
        for split in ("validation", "test"):
            examples = report[f"{split}_examples"]
            source = report["calibration_metrics"][split]
            method_curves: dict[str, Any] = {}
            for method, item in source.items():
                if not isinstance(item, dict):
                    continue
                metrics = item.get("metrics", item)
                if isinstance(metrics, dict) and metrics.get("reliability_bins"):
                    method_curves[method] = metrics["reliability_bins"]
            result[task][split] = {
                "example_count": len(examples),
                "methods": method_curves,
                "curve_note": (
                    "raw synthetic outcome scores; uncertainty clusters by session"
                ),
            }
    return result


def _resource_benchmark() -> dict[str, Any]:
    row_count = 20_000
    raw = np.linspace(0.001, 0.999, row_count)
    labels = tuple(int(index % 7 in {0, 1, 2}) for index in range(row_count))
    rows = tuple(f"benchmark-row-{index}" for index in range(row_count))
    sessions = tuple(f"benchmark-session-{index // 100}" for index in range(row_count))
    started = time.perf_counter()
    cpu_started = time.process_time()
    result = binary_metrics(
        tuple(float(item) for item in raw),
        labels,
        threshold=0.5,
        source_role=SourceRole.SYNTHETIC,
        fold_id="BENCHMARK_ONLY",
        row_ids=rows,
        clusters=sessions,
        bootstrap_resamples=0,
    )
    elapsed = time.perf_counter() - started
    return {
        "row_limit": row_count,
        "elapsed_seconds": elapsed,
        "cpu_seconds": time.process_time() - cpu_started,
        "rows_per_second": row_count / elapsed if elapsed else None,
        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        * 1024,
        "metric_result_finite": math.isfinite(result["brier_score"]["value"]),
        "scope": "metric arithmetic only; not model serving or a production capacity claim",
    }


async def run(*, allow_dirty: bool, output: Path) -> dict[str, Any]:
    observed_sessions: set[Session] = set()

    def observe_session(session: Session, _transaction: Any, _connection: Any) -> None:
        observed_sessions.add(session)

    event.listen(Session, "after_begin", observe_session)
    try:
        return await _run_phase9g(
            allow_dirty=allow_dirty,
            output=output,
            observed_sessions=observed_sessions,
        )
    finally:
        event.remove(Session, "after_begin", observe_session)


async def _run_phase9g(
    *, allow_dirty: bool, output: Path, observed_sessions: set[Session]
) -> dict[str, Any]:
    git_sha, dirty = _git_state(allow_dirty)
    database_url = os.environ.get("TEST_DATABASE_URL", "")
    if not database_url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise RuntimeError("Phase 9G requires a disposable vehicle_test database")
    settings = Settings(database_url=SecretStr(database_url), environment="test")
    database = Database(settings, command_timeout=120)
    telemetry = Telemetry(settings, database)
    span_exporter = InMemorySpanExporter()
    telemetry.traces.add_span_processor(SimpleSpanProcessor(span_exporter))
    protocol = default_protocol()
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    model_artifact_workspace = tempfile.TemporaryDirectory(
        prefix="model-artifacts-", dir=EVIDENCE_ROOT
    )
    model_store = ModelArtifactStore(Path(model_artifact_workspace.name))
    started = time.perf_counter()
    cpu_started = time.process_time()
    training_span_names: set[str] = set()
    try:
        task_reports, task_runs, fixture_report = await _train_and_evaluate_supervised(
            database, telemetry, model_store=model_store, protocol=protocol
        )
        training_span_names = {span.name for span in span_exporter.get_finished_spans()}
    finally:
        telemetry.shutdown()
        await database.close()

    anomaly_report, sensitivity, phase9c_receipt = await _anomaly_evaluation()
    # Reopen after Phase 9B/9C source-generation jobs have completed. From this point
    # every Phase 9G action must leave all prior-phase source tables unchanged.
    database = Database(settings, command_timeout=120)
    telemetry = Telemetry(settings, database)
    span_exporter = InMemorySpanExporter()
    telemetry.traces.add_span_processor(SimpleSpanProcessor(span_exporter))
    try:
        before = await source_table_digests(database)
        model_tamper_report = await _tamper_checks(
            database, model_store, task_runs, anomaly_report, phase9c_receipt
        )
        partitions = _check_partition_safety(task_reports)
        positive = _positive_calibration_fixture()
        calibration_attacks = _calibration_adversaries()
        drift_attacks = _drift_adversaries()
        _assert(
            all(model_tamper_report["9b_registered_artifact_tamper_rejected"].values())
            and model_tamper_report["9c_registered_artifact_tamper_rejected"]
            and model_tamper_report["9c_source_receipt_checksum_tamper_rejected"],
            "artifact or source receipt tamper attack was accepted",
        )
        _assert(
            all(
                calibration_attacks[key]
                for key in calibration_attacks
                if key.endswith(("rejected", "denominator"))
            ),
            "calibration adversary failed",
        )
        _assert(
            all(drift_attacks["checks"].values()),
            "unlabeled drift/OOD adversary produced a false certainty",
        )

        assessments = _applicability(task_reports, anomaly_report)
        evidence = await _evidence_refs(database, task_runs, anomaly_report)
        folds = _fold_manifests(task_reports)
        dataset_manifest = _dataset_manifest(task_reports)
        candidates = tuple(
            CalibrationCandidate.model_validate_json(
                json.dumps(candidate, sort_keys=True, separators=(",", ":"))
            )
            for task_report in task_reports.values()
            for candidate in task_report["calibration_candidates"]
        )
        metrics = _metric_results(task_reports)
        drift = _drift_records(task_reports)
        stress = _stress_scenarios(phase9c_receipt)
        fold_manifest_payloads = tuple(item.model_dump(mode="json") for item in folds)
        dataset_manifest_payload = dataset_manifest.model_dump(mode="json")
        after_evaluation = await source_table_digests(database)
        _assert(
            before == after_evaluation,
            "research evaluation mutated a prior-phase source table",
        )

        scientific_reports: dict[str, dict[str, Any]] = {
            **{
                f"supervised-{task}": report
                for task, report in sorted(task_reports.items())
            },
            "anomaly-reliability": anomaly_report,
            "reference-size-sensitivity": sensitivity,
            "source-receipt": phase9c_receipt,
            "applicability": {
                f"{item.subject_kind}:{item.subject_key}:{item.source_role.value}": item.model_dump(
                    mode="json"
                )
                for item in assessments
            },
            "drift": {
                f"{item.feature_family}:{item.metric}:{item.comparison_window}": item.model_dump(
                    mode="json"
                )
                for item in drift
            },
        }
        report_checksum = stable_hash(scientific_reports)
        logical_key = stable_hash(
            {
                "protocol": protocol.checksum,
                "git_sha": git_sha,
                "dataset": dataset_manifest.row_fingerprint,
                "report": report_checksum,
            }
        )
        run = EvaluationRun(
            protocol_checksum=protocol.checksum,
            git_sha=git_sha,
            logical_key=logical_key,
            source_role=SourceRole.SYNTHETIC,
            dataset_manifest=dataset_manifest,
            folds=folds,
            evidence=evidence,
            metrics=metrics,
            calibration_candidates=candidates,
            applicability=assessments,
            drift=drift,
            stress_scenarios=stress,
            engineering_status="PASS",
            scientific_readiness=ScientificReadinessReport(
                engineering_pipeline="PASS",
                synthetic_calibration="SYNTHETIC_ONLY",
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
            report_checksum=report_checksum,
            no_source_mutations=True,
            serving_artifacts_unchanged=True,
        )
        with telemetry.tracer.start_as_current_span("evaluation.registry.persist"):
            persistence = await persist_evaluation(
                database,
                protocol=protocol,
                run=run,
                reports=scientific_reports,
                calibration_refs={
                    f"{candidate.task}:{candidate.method.value}": UUID(
                        candidate.model_version_id
                    )
                    for candidate in candidates
                },
            )
            replay_started = time.perf_counter()
            replay = await persist_evaluation(
                database,
                protocol=protocol,
                run=run,
                reports=scientific_reports,
                calibration_refs={
                    f"{candidate.task}:{candidate.method.value}": UUID(
                        candidate.model_version_id
                    )
                    for candidate in candidates
                },
            )
            replay_seconds = time.perf_counter() - replay_started
            immutable = await assert_evaluation_immutability(
                database, UUID(persistence["run_id"])
            )
        _assert(
            replay["idempotent_replay"], "same evaluation replay was not idempotent"
        )
        _assert(
            all(immutable.values()),
            "database accepted mutation of immutable evaluation rows",
        )
        after_persist = await source_table_digests(database)
        _assert(
            before == after_persist,
            "Phase 9G persistence mutated prior-phase source tables",
        )

        metric_duration = time.perf_counter() - started
        abstentions = sum(
            sum(report["label_availability"]["excluded_pair_counts"].values())
            for report in task_reports.values()
        )
        record_run_metrics(
            telemetry,
            source_role=SourceRole.SYNTHETIC,
            status="PASS",
            duration_seconds=metric_duration,
            row_count=dataset_manifest.row_count,
            abstentions=abstentions,
            artifact_bytes=sum(item.artifact_bytes for item in candidates),
            integrity_violations=0,
            drift_features=len(drift),
            session_count=dataset_manifest.session_count,
            calibration_candidates=tuple(
                (item.method.value, item.state) for item in candidates
            ),
            abstention_reasons=_bounded_abstention_reasons(task_reports),
        )
        metrics_text = telemetry.render_metrics().decode("utf-8")
        observed_spans = sorted(
            training_span_names
            | {span.name for span in span_exporter.get_finished_spans()}
        )
        required_spans = {"evaluation.supervised.task", "evaluation.registry.persist"}
        _assert(
            required_spans.issubset(observed_spans), "Phase 9G trace spans are missing"
        )
        _assert(
            "evaluation_runs" in metrics_text, "Phase 9G OTel metrics were not rendered"
        )
        telemetry.shutdown()

        benchmark = _resource_benchmark()
        benchmark["offline_evaluation_wall_seconds"] = time.perf_counter() - started
        benchmark["offline_evaluation_cpu_seconds"] = time.process_time() - cpu_started
        benchmark["task_seconds"] = fixture_report["task_seconds"]
        benchmark["calibration_fit_seconds"] = fixture_report["calibration_fit_seconds"]
        benchmark["row_count"] = dataset_manifest.row_count
        benchmark["fold_count"] = len(folds)
        benchmark["calibration_artifact_bytes"] = sum(
            candidate.artifact_bytes for candidate in candidates
        )
        benchmark["registry_replay_seconds"] = replay_seconds
        benchmark["database_sessions_started"] = len(observed_sessions)
        benchmark["registry_replay_cost"] = (
            "same logical key and immutable report checksums"
        )
        benchmark["evaluation_rows_per_second"] = (
            dataset_manifest.row_count / benchmark["offline_evaluation_wall_seconds"]
            if benchmark["offline_evaluation_wall_seconds"]
            else None
        )
        readiness = run.scientific_readiness.model_dump(mode="json")
        summary = {
            "schema_version": "phase9g-evaluation-v1",
            "base_sha": os.environ.get(
                "PHASE9G_BASE_SHA", "327c63f35b4e7bc0eba31bbec81d20206be8afa2"
            ),
            "final_sha": git_sha,
            "worktree_dirty_at_start": dirty,
            "protocol": {
                "version": protocol.protocol_version,
                "checksum": protocol.checksum,
                "definition": protocol.model_dump(mode="json"),
            },
            "report_checksum": report_checksum,
            "logical_key": logical_key,
            "engineering_status": "PASS",
            "scientific_readiness": readiness,
            "dataset_manifest": dataset_manifest_payload,
            "fold_manifests": fold_manifest_payloads,
            "evaluation_evidence": [item.model_dump(mode="json") for item in evidence],
            "tasks": task_reports,
            "calibration_curve_support": _curve_support(task_reports),
            "anomaly": anomaly_report,
            "reference_size_sensitivity": sensitivity,
            "source_receipt": phase9c_receipt,
            "source_integrity": {
                "tables": list(SOURCE_TABLES),
                "before_research": before,
                "after_research": after_evaluation,
                "after_persistence": after_persist,
                "unchanged_during_research": before == after_evaluation,
                "unchanged_by_9g_persistence": before == after_persist,
                "new_phase9g_tables_only": True,
            },
            "partitions_and_holdouts": partitions,
            "adversaries": {
                "artifact_integrity": model_tamper_report,
                "calibration": calibration_attacks,
                "drift_and_ood": drift_attacks["checks"],
                "known_drift_arithmetic": drift_attacks["known_metrics"],
                "positive_known_bias_calibration": positive,
                "anomaly_oracle_metadata_excluded_from_fit": True,
            },
            "applicability": [item.model_dump(mode="json") for item in assessments],
            "vehicle_context": fixture_report[
                "vehicle_configuration_modification_context"
            ],
            "stress_scenarios": [item.model_dump(mode="json") for item in stress],
            "drift": [item.model_dump(mode="json") for item in drift],
            "ood_and_coverage": {
                task: {
                    "ood": report["ood"],
                    "risk_coverage": report["calibration_metrics"]["test"]
                    .get(report["selected_research_candidate"], {})
                    .get("risk_coverage"),
                    "label_availability": report["label_availability"],
                }
                for task, report in sorted(task_reports.items())
            },
            "persistence": {
                "run_id": persistence["run_id"],
                "idempotent_replay": replay["idempotent_replay"],
                "immutable_rows": immutable,
                "prior_phase_source_tables_unchanged": True,
            },
            "observability": {
                "spans": observed_spans,
                "required_spans": sorted(required_spans),
                "metrics_contains_evaluation_runs": "evaluation_runs" in metrics_text,
                "entity_ids_used_as_metric_labels": False,
            },
            "benchmark": benchmark,
            "serving_fence": {
                "9b_artifacts_promoted": False,
                "9b_thresholds_changed": False,
                "9c_thresholds_changed": False,
                "9d_serving_approvals_changed": False,
                "9e_prediction_evidence_rewritten": False,
                "9f_agent_claims_promoted": False,
                "public_api_added": False,
                "automatic_retraining_or_promotion": False,
                "production_calibration": False,
            },
        }
        summary["acceptance_checksum"] = stable_hash(
            {
                key: value
                for key, value in summary.items()
                if key != "acceptance_checksum"
            }
        )
        await asyncio.to_thread(output.parent.mkdir, parents=True, exist_ok=True)
        payload = json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n"
        await asyncio.to_thread(output.write_text, payload, encoding="utf-8")
        return summary
    finally:
        telemetry.shutdown()
        await database.close()
        model_artifact_workspace.cleanup()


async def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        default=os.environ.get("PHASE9G_ALLOW_DIRTY") == "1",
        help="developer-only iteration mode; the receipt records the dirty state",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EVIDENCE_ROOT / "acceptance.json",
    )
    args = parser.parse_args()
    summary = await run(allow_dirty=args.allow_dirty, output=args.output)
    print(
        json.dumps(
            {
                "engineering_status": summary["engineering_status"],
                "scientific_readiness": summary["scientific_readiness"],
                "final_sha": summary["final_sha"],
                "report_checksum": summary["report_checksum"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(_main())
