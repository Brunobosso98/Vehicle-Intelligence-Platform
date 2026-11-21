#!/usr/bin/env python3
"""Run the controlled Phase 10 lifecycle against a disposable vehicle_test database."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vehicle_platform.anomalies.artifacts import (
    ArtifactStore as DetectorArtifactStore,
)
from vehicle_platform.anomalies.definitions import detector_definition
from vehicle_platform.anomalies.domain import (
    MAX_REFERENCE_ROWS,
    DetectorMethod,
)
from vehicle_platform.anomalies.domain import (
    SourceRole as AnomalySourceRole,
)
from vehicle_platform.anomalies.repository import AnomalyDataRepository
from vehicle_platform.core.config import Settings
from vehicle_platform.evaluation.contracts import SourceRole
from vehicle_platform.features.datasets import DatasetBuilder
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.features.service import default_feature_version
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.infrastructure.trusted_files import (
    read_verified_bytes,
    write_exclusive_bytes,
)
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.ml.labels import (
    build_supervised_dataset,
    get_model_spec,
)
from vehicle_platform.ml.pipeline import dataset_definitions
from vehicle_platform.ml.synthetic import (
    generate_fixture_features,
    seed_predictive_fixture,
)
from vehicle_platform.mlops.anomaly_comparison import compare_anomaly
from vehicle_platform.mlops.comparison import compare_supervised
from vehicle_platform.mlops.contracts import (
    AnomalyOracleLabel,
    PipelineDefinition,
    PipelineKind,
)
from vehicle_platform.mlops.monitoring import (
    MonitoringProtocol,
    monitor_receipts,
)
from vehicle_platform.mlops.planner import (
    anomaly_evaluation_checksum,
    anomaly_evaluation_source_fingerprint,
    materialize_supervised_readonly,
    plan_supervised,
)
from vehicle_platform.mlops.repository import ControlPlaneRepository
from vehicle_platform.mlops.rollback import (
    inspect_rollback_plan,
    plan_rollback,
)
from vehicle_platform.mlops.runner import run_pipeline
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.predictions.domain import AnomalyRequest, PredictionKind
from vehicle_platform.predictions.service import PredictionService

import scripts.evaluate_predictive_reliability as phase9g

EVIDENCE = ROOT / ".validation" / "phase10"
PHASE9B_ARTIFACT_ROOT = ROOT / "apps/api/.artifacts/phase9b"
PHASE9C_ARTIFACT_ROOT = ROOT / "apps/api/.artifacts/phase9c"
MAX_ARTIFACT_BYTES = 50 * 1024 * 1024
SERVING_TABLES = (
    "prediction_serving_bindings",
    "prediction_serving_events",
    "prediction_receipts",
    "prediction_evidence_bundles",
    "prediction_evidence_sources",
    "prediction_evidence_nodes",
    "prediction_evidence_edges",
    "prediction_evidence_facts",
    "prediction_evidence_gaps",
    "prediction_evidence_verification_audits",
    "agent_prediction_evidence_links",
    "agent_runs",
    "agent_tool_calls",
    "agent_stream_events",
    "evaluation_protocols",
    "evaluation_runs",
    "evaluation_metric_reports",
    "evaluation_calibration_candidates",
    "evaluation_applicability_assessments",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _git_sha() -> str:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable is unavailable")
    actual = subprocess.run(
        [git, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout.strip()
    expected = os.environ.get("GIT_SHA", actual)
    if actual != expected:
        raise RuntimeError("Phase 10 evaluator checkout differs from the requested SHA")
    dirty = subprocess.run(
        [git, "status", "--porcelain", "--untracked-files=normal"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout
    if dirty:
        raise RuntimeError("Phase 10 acceptance requires a clean, exact-SHA checkout")
    return actual


async def _table_digest(database: Database, tables: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    allowed_tables = frozenset(SERVING_TABLES)
    async with database.session() as db, db.begin():
        await db.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        )
        for table in tables:
            if table not in allowed_tables:
                raise ValueError("source digest requested an unapproved table")
            rows = (
                (
                    await db.execute(
                        text(
                            f"SELECT row_to_json(item)::text FROM {table} item ORDER BY 1"
                        )
                    )
                )
                .scalars()
                .all()
            )
            result[table] = stable_hash([str(row) for row in rows])
    return result


def _copy_registered_artifact(
    *,
    roots: tuple[Path, ...],
    relative_path: str,
    expected_checksum: str,
    expected_size: int | None,
    target_root: Path,
) -> None:
    relative = Path(relative_path)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ValueError("registered artifact path is outside its fixed namespace")
    if expected_size is not None and not 1 <= expected_size <= MAX_ARTIFACT_BYTES:
        raise ValueError("registered artifact exceeds the Phase 10 byte budget")
    matches = [root for root in roots if (root / relative).is_file()]
    if len(matches) != 1:
        raise ValueError("registered artifact source is missing or ambiguous")
    source_root = matches[0]
    source_path = source_root / relative
    # The Phase 9B registry stores a content checksum but no artifact-size column.
    # Derive the bounded size from the bytes verified against that immutable checksum.
    payload = read_verified_bytes(
        source_root,
        source_path,
        maximum_bytes=MAX_ARTIFACT_BYTES,
        expected_checksum=expected_checksum,
        expected_size=expected_size,
        expected_owner=os.getuid(),
        require_private=True,
    )
    target = target_root / relative
    verified_size = len(payload)
    if target.exists():
        existing = read_verified_bytes(
            target_root,
            target,
            maximum_bytes=MAX_ARTIFACT_BYTES,
            expected_checksum=expected_checksum,
            expected_size=verified_size,
            expected_owner=os.getuid(),
            require_private=True,
        )
        if existing != payload:
            raise ValueError("trusted artifact root has conflicting immutable bytes")
        return
    write_exclusive_bytes(target_root, relative, payload)


async def _register_champions(
    database: Database, settings: Settings, cohort: Any
) -> tuple[dict[str, UUID], dict[str, UUID]]:
    model_roots = tuple(
        (ROOT / ".validation" / "phase9g" / "model-artifacts").glob("run-*")
    )
    detector_roots = tuple((ROOT / ".validation" / "phase9c").glob("artifacts-*"))
    _require(
        bool(model_roots) and bool(detector_roots),
        "Phase 9G source artifacts are missing",
    )
    # A fit may resolve idempotently to any previously registered 9C version,
    # including a non-champion. Make each available source artifact accessible
    # under the normal trusted root after verifying its immutable receipt.
    async with database.session() as db:
        registered_detectors = (
            (
                await db.execute(
                    text(
                        "SELECT artifact_path,artifact_checksum,artifact_size_bytes "
                        "FROM anomaly_detector_versions WHERE artifact_path IS NOT NULL"
                    )
                )
            )
            .mappings()
            .all()
        )
    for registered in registered_detectors:
        relative = str(registered["artifact_path"])
        if any((root / relative).is_file() for root in detector_roots):
            _copy_registered_artifact(
                roots=detector_roots,
                relative_path=relative,
                expected_checksum=str(registered["artifact_checksum"]),
                expected_size=int(registered["artifact_size_bytes"]),
                target_root=PHASE9C_ARTIFACT_ROOT,
            )
    model_bindings: dict[str, UUID] = {}
    detector_bindings: dict[str, UUID] = {}
    service = PredictionService(settings, database)
    try:
        for task in MLTask:
            async with database.session() as db:
                row = (
                    (
                        await db.execute(
                            text(
                                "SELECT mv.id,mv.artifact_path,mv.artifact_checksum "
                                "FROM ml_model_versions mv "
                                "JOIN ml_models m ON m.id=mv.ml_model_id WHERE m.task=:task "
                                "ORDER BY mv.created_at DESC,mv.id DESC LIMIT 1"
                            ),
                            {"task": task.value},
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
            _require(row is not None, f"Phase 9G has no registered {task.value} model")
            model_id = UUID(str(row["id"]))
            _copy_registered_artifact(
                roots=model_roots,
                relative_path=str(row["artifact_path"]),
                expected_checksum=str(row["artifact_checksum"]),
                expected_size=None,
                target_root=PHASE9B_ARTIFACT_ROOT,
            )
            binding_id, _ = await service.approve_candidate(
                "next_pull",
                model_id,
                source_role=AnomalySourceRole.SYNTHETIC,
                reason="Explicit Phase 9D test setup for synthetic MLOps comparison.",
                operator_id="phase10-acceptance-operator",
                review_reference=f"phase10-test-setup-{task.value.lower()}",
                environment_confirmation="test",
            )
            await service.transition(
                binding_id,
                "activate",
                reason="Explicit Phase 9D activation for controlled synthetic acceptance.",
                operator_id="phase10-acceptance-operator",
                environment_confirmation="test",
            )
            model_bindings[task.value] = binding_id

        for family in ("thermal", "boost_air", "performance", "fuel"):
            async with database.session() as db:
                row = (
                    (
                        await db.execute(
                            text(
                                "SELECT v.id,v.artifact_path,v.artifact_checksum,"
                                "v.artifact_size_bytes "
                                "FROM anomaly_detector_versions v "
                                "JOIN anomaly_detector_definitions d "
                                "ON d.id=v.detector_definition_id "
                                "JOIN anomaly_reference_datasets r ON r.id=v.reference_dataset_id "
                                "WHERE d.family=:family AND r.vehicle_id=:vehicle "
                                "AND r.observation_cutoff<=:cutoff "
                                "AND v.state='ACCEPTED' AND "
                                "v.training_metrics->>'selection_state'='ACCEPTED' "
                                "ORDER BY v.created_at DESC,v.id DESC LIMIT 1"
                            ),
                            {
                                "family": family,
                                "vehicle": cohort.vehicle_id,
                                "cutoff": cohort.pulls_by_session[8][0].ended_at
                                + timedelta(seconds=1),
                            },
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
            _require(row is not None, f"Phase 9G has no accepted {family} detector")
            detector_id = UUID(str(row["id"]))
            _copy_registered_artifact(
                roots=detector_roots,
                relative_path=str(row["artifact_path"]),
                expected_checksum=str(row["artifact_checksum"]),
                expected_size=int(row["artifact_size_bytes"]),
                target_root=PHASE9C_ARTIFACT_ROOT,
            )
            binding_id, _ = await service.approve_candidate(
                "anomaly",
                detector_id,
                source_role=AnomalySourceRole.SYNTHETIC,
                reason="Explicit Phase 9D test setup for synthetic MLOps comparison.",
                operator_id="phase10-acceptance-operator",
                review_reference=f"phase10-test-setup-{family}",
                environment_confirmation="test",
            )
            await service.transition(
                binding_id,
                "activate",
                reason="Explicit Phase 9D activation for controlled synthetic acceptance.",
                operator_id="phase10-acceptance-operator",
                environment_confirmation="test",
            )
            detector_bindings[family] = binding_id
    finally:
        await service.close()
    return model_bindings, detector_bindings


async def _supervised_definition(
    database: Database,
    task: MLTask,
    training_pull_ids: tuple[UUID, ...],
    future_pull_ids: tuple[UUID, ...],
    *,
    git_sha: str,
) -> PipelineDefinition:
    cutoff = datetime(2026, 3, 1, tzinfo=UTC)
    evaluation_cutoff = datetime(2026, 10, 2, tzinfo=UTC)
    spec = get_model_spec(task)
    input_def, outcome_def = dataset_definitions(task, cutoff, "synthetic")
    builder = DatasetBuilder(database, DEFAULT_REGISTRY)
    training_pull_ids = tuple(sorted(training_pull_ids, key=str))
    if not training_pull_ids or len(training_pull_ids) > 20_000:
        raise AssertionError(
            "bounded Phase 9B training cohort is missing or exceeds its limit"
        )
    input_data = await builder.build(
        input_def, candidate_pull_ids=training_pull_ids, persist=False, max_rows=20_000
    )
    outcome_data = await builder.build(
        outcome_def,
        candidate_pull_ids=training_pull_ids,
        persist=False,
        max_rows=20_000,
    )
    selected_inputs = {str(item.pull_id) for item in input_data.candidates}
    selected_outcomes = {str(item.pull_id) for item in outcome_data.candidates}
    expected_training = {str(item) for item in training_pull_ids}
    if selected_inputs != expected_training or selected_outcomes != expected_training:
        raise AssertionError("Phase 9B training cohort changed during materialization")
    training = build_supervised_dataset(
        input_data, outcome_data, spec, repository_sha=git_sha
    )
    probe = PipelineDefinition(
        definition_version=f"p10-{task.value.lower()}-v2",
        kind=PipelineKind.SUPERVISED,
        task=task,
        source_role=SourceRole.SYNTHETIC,
        cutoff=cutoff,
        git_sha=git_sha,
        expected_source_fingerprint=training.source_fingerprint,
        expected_dataset_checksum=training.checksum,
        expected_feature_checksum=default_feature_version().checksum,
        evaluation_cutoff=evaluation_cutoff,
        training_pull_ids=training_pull_ids,
        evaluation_pull_ids=future_pull_ids,
        expected_evaluation_checksum="0" * 64,
        expected_evaluation_source_fingerprint="0" * 64,
    )
    evaluation = await materialize_supervised_readonly(database, probe, evaluation=True)
    return probe.model_copy(
        update={
            "expected_evaluation_checksum": evaluation.checksum,
            "expected_evaluation_source_fingerprint": evaluation.source_fingerprint,
        }
    )


async def _phase9c_primary(database: Database) -> Any:
    """Rehydrate the already seeded Phase 9C primary fixture without adding source rows."""
    from scripts.evaluate_anomaly_detection import (
        PullSpec,
        SeededCohort,
        _scenarios_for_session,
    )

    all_pulls: list[tuple[Any, ...]] = []
    session_ids: list[UUID] = []
    vehicle_id: UUID | None = None
    configuration_a: UUID | None = None
    configuration_b: UUID | None = None
    async with database.session() as db:
        for session_index in range(15):
            pull_group = []
            scenarios = _scenarios_for_session(session_index, no_fuel=False)
            for pull_index, scenario in enumerate(scenarios):
                identifier = UUID(
                    bytes=hashlib.sha256(
                        f"phase9c:primary:{session_index}:{pull_index}".encode()
                    ).digest()[:16]
                )
                row = (
                    (
                        await db.execute(
                            text(
                                "SELECT p.id,p.session_id,p.vehicle_id,p.configuration_id,"
                                "p.started_at,p.ended_at FROM pulls p WHERE p.id=:id"
                            ),
                            {"id": identifier},
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                _require(row is not None, "Phase 9C primary fixture row is unavailable")
                vehicle_id = UUID(str(row["vehicle_id"]))
                configuration = UUID(str(row["configuration_id"]))
                configuration_a = configuration_a or configuration
                if session_index == 14:
                    configuration_b = configuration
                session_ids.append(UUID(str(row["session_id"])))
                pull_group.append(
                    PullSpec(
                        pull_id=identifier,
                        session_id=UUID(str(row["session_id"])),
                        vehicle_id=vehicle_id,
                        configuration_id=configuration,
                        started_at=row["started_at"],
                        ended_at=row["ended_at"],
                        scenario=scenario,
                        duplicate_sample=scenario == "quality_duplicate",
                        fuel_available=scenario != "missing_fuel",
                        environmental_context_shift=session_index == 13,
                    )
                )
            all_pulls.append(tuple(pull_group))
    _require(
        vehicle_id is not None and configuration_a is not None,
        "Phase 9C cohort is empty",
    )
    return SeededCohort(
        vehicle_id=vehicle_id,
        configuration_a=configuration_a,
        configuration_b=configuration_b,
        sessions=tuple(dict.fromkeys(session_ids)),
        pulls_by_session=tuple(all_pulls),
    )


async def _anomaly_definition(
    database: Database, family: str, cohort: Any, *, git_sha: str
) -> PipelineDefinition:
    evaluator = AnomalyDataRepository(database)
    detector = detector_definition(family, DetectorMethod.ROBUST_MAD)
    anchor = cohort.pulls_by_session[8][0]
    cutoff = anchor.ended_at + timedelta(seconds=1)
    anomaly_role = AnomalySourceRole.SYNTHETIC
    anchor_row, feature_version_id, feature_checksum = await evaluator.load_anchor(
        anchor.pull_id, cutoff, anomaly_role, detector
    )
    reference = await evaluator.materialize_reference(
        anchor_row,
        feature_version_id,
        feature_checksum,
        detector,
        anomaly_role,
        max_rows=MAX_REFERENCE_ROWS,
    )
    target_pulls = tuple(
        sorted(
            (pull for group in cohort.pulls_by_session[10:14] for pull in group),
            key=lambda pull: str(pull.pull_id),
        )
    )
    evaluation_ids = tuple(pull.pull_id for pull in target_pulls)
    oracle_rows = []
    for pull in target_pulls:
        scenario = pull.scenario
        if scenario in {"quality_duplicate", "missing_fuel"}:
            scenario = "quality_excluded"
        elif scenario in {"boost_fluctuation", "subtle_multivariate"}:
            scenario = "ambiguous"
        if scenario not in {"clean", "thermal", "boost_air", "performance", "fuel"}:
            scenario = "unlabeled"
        oracle_rows.append(AnomalyOracleLabel(pull_id=pull.pull_id, scenario=scenario))
    oracle = tuple(sorted(oracle_rows, key=lambda item: str(item.pull_id)))
    evaluation_cutoff = max(pull.ended_at for pull in target_pulls) + timedelta(days=1)
    evaluation_rows = await evaluator.load_targets(
        evaluation_ids, evaluation_cutoff, detector
    )
    source_fingerprint = anomaly_evaluation_source_fingerprint(evaluation_rows)
    oracle_checksum = stable_hash([item.model_dump(mode="json") for item in oracle])
    provisional = PipelineDefinition(
        definition_version=f"p10-anomaly-{family}-v1",
        kind=PipelineKind.ANOMALY,
        family=family,  # type: ignore[arg-type]
        method=DetectorMethod.ROBUST_MAD.value,
        anchor_pull_id=anchor.pull_id,
        source_role=SourceRole.SYNTHETIC,
        cutoff=cutoff,
        git_sha=git_sha,
        expected_source_fingerprint=reference.source_fingerprint,
        expected_dataset_checksum=reference.checksum(detector),
        expected_feature_checksum=feature_checksum,
        evaluation_cutoff=evaluation_cutoff,
        evaluation_pull_ids=evaluation_ids,
        expected_evaluation_checksum="0" * 64,
        expected_evaluation_source_fingerprint=source_fingerprint,
        evaluation_oracle=oracle,
        expected_oracle_checksum=oracle_checksum,
    )
    eval_checksum = anomaly_evaluation_checksum(
        provisional, detector.checksum, feature_checksum, evaluation_rows
    )
    return provisional.model_copy(
        update={"expected_evaluation_checksum": eval_checksum}
    )


async def _run_definition(
    database: Database,
    telemetry: Telemetry,
    definition: PipelineDefinition,
    champion_binding_id: UUID,
) -> dict[str, Any]:
    plan_started = time.perf_counter()
    from vehicle_platform.mlops.planner import plan_anomaly

    planner = (
        plan_supervised if definition.kind is PipelineKind.SUPERVISED else plan_anomaly
    )
    first_plan = await planner(database, definition)
    second_plan = await planner(database, definition)
    _require(
        first_plan == second_plan, "repeated read-only planning changed its receipt"
    )
    _require(
        first_plan.get("status") == "READY_TO_REVIEW",
        "pipeline plan was not eligible: "
        f"{definition.definition_version} "
        f"{first_plan.get('status')}/{first_plan.get('reason')}; "
        f"training_rows={first_plan.get('labeled_rows', first_plan.get('reference_rows'))}; "
        f"evaluation_rows={first_plan.get('evaluation_rows')}; "
        f"sessions={first_plan.get('sessions')}; "
        f"evaluation_sessions={first_plan.get('evaluation_sessions')}",
    )
    planning_seconds = time.perf_counter() - plan_started
    started = time.perf_counter()
    result = await run_pipeline(
        database,
        definition,
        execute=True,
        confirmed_environment="test",
        confirmed_fingerprint=definition.fingerprint,
        champion_binding_id=champion_binding_id,
        telemetry=telemetry,
    )
    elapsed = time.perf_counter() - started
    if result.get("status") != "COMPLETED" and result.get("run_id"):
        failed_run = await ControlPlaneRepository(database).inspect_run(
            UUID(str(result["run_id"]))
        )
        result = {
            **result,
            "definition_version": definition.definition_version,
            "step_states": [
                {
                    "step": event["step_name"],
                    "state": event["state"],
                    "reason": (event.get("output_body") or {}).get("reason"),
                    "failed_criteria": (event.get("output_body") or {}).get(
                        "failed_criteria"
                    ),
                }
                for event in failed_run["steps"]
            ],
        }
    _require(
        result.get("status") == "COMPLETED", f"pipeline execution failed: {result}"
    )
    _require(
        result.get("comparison", {}).get("status") == "COMPARABLE_OFFLINE",
        f"matched champion comparison did not run: {definition.definition_version} "
        f"{result.get('comparison')}",
    )
    run_id = UUID(str(result["run_id"]))
    inspection = await ControlPlaneRepository(database).inspect_run(run_id)
    _require(inspection["run"]["state"] == "COMPLETED", "durable run did not complete")
    latest: dict[str, dict[str, Any]] = {}
    for event in inspection["steps"]:
        latest[str(event["step_name"])] = event
    required = {
        "select",
        "validate",
        "fit",
        "verify_artifact",
        "evaluate",
        "compare",
        "report",
    }
    _require(set(latest) == required, "pipeline did not persist every required stage")
    _require(
        all(
            item["state"] in {"SUCCEEDED", "SKIPPED_INELIGIBLE"}
            for item in latest.values()
        ),
        "pipeline has an incomplete stage",
    )
    replay = await run_pipeline(
        database,
        definition,
        execute=True,
        confirmed_environment="test",
        confirmed_fingerprint=definition.fingerprint,
        champion_binding_id=champion_binding_id,
        telemetry=telemetry,
    )
    _require(
        replay.get("status") == "EXISTING_RUN"
        and replay.get("idempotent_replay") is True,
        "exact replay created or changed a run",
    )
    artifact_checksum = str(result["execution_result"]["artifact_checksum"])
    artifact_version = result["execution_result"].get("model_version_id") or result[
        "execution_result"
    ].get("detector_version_id")
    if definition.kind is PipelineKind.SUPERVISED:
        # Keep the Phase 9B schema unchanged; the checksum is the source authority.
        artifact_query = (
            "SELECT artifact_path,artifact_checksum FROM ml_model_versions WHERE id=:id"
        )
        artifact_root = PHASE9B_ARTIFACT_ROOT
    else:
        artifact_query = (
            "SELECT artifact_path,artifact_checksum,artifact_size_bytes "
            "FROM anomaly_detector_versions WHERE id=:id"
        )
        artifact_root = PHASE9C_ARTIFACT_ROOT
    async with database.session() as db:
        artifact_row = (
            (await db.execute(text(artifact_query), {"id": artifact_version}))
            .mappings()
            .one()
        )
    _require(
        str(artifact_row["artifact_checksum"]) == artifact_checksum,
        "registered artifact checksum differs from the pipeline receipt",
    )
    artifact_relative_path = Path(str(artifact_row["artifact_path"]))
    artifact_expected_size = (
        int(artifact_row["artifact_size_bytes"])
        if definition.kind is PipelineKind.ANOMALY
        else None
    )
    artifact_payload = read_verified_bytes(
        artifact_root,
        artifact_root / artifact_relative_path,
        artifact_checksum,
        maximum_bytes=MAX_ARTIFACT_BYTES,
        expected_size=artifact_expected_size,
        expected_owner=os.getuid(),
        require_private=True,
    )
    artifact_size = len(artifact_payload)
    proposal_inspection = await ControlPlaneRepository(database).inspect_proposal(
        UUID(str(result["proposal_id"]))
    )
    proposal_body = proposal_inspection["proposal"]["body"]
    candidate_dossier = proposal_body.get("candidate_dossier")
    dossier_checksum = proposal_body.get("candidate_dossier_checksum")
    _require(
        isinstance(candidate_dossier, dict), "immutable candidate dossier is missing"
    )
    _require(
        isinstance(dossier_checksum, str)
        and stable_hash(candidate_dossier) == dossier_checksum,
        "candidate dossier checksum differs",
    )
    dossier_dir = EVIDENCE / "candidate-dossiers"
    subject = definition.task.value if definition.task else definition.family
    dossier_path = dossier_dir / (
        f"{definition.kind.value}-{subject}-{artifact_version}.json"
    )
    write_exclusive_bytes(
        dossier_dir,
        Path(dossier_path.name),
        (
            json.dumps(candidate_dossier, indent=2, sort_keys=True, allow_nan=False)
            + "\n"
        ).encode("utf-8"),
    )
    return {
        "run_id": str(run_id),
        "definition_fingerprint": definition.fingerprint,
        "kind": definition.kind.value,
        "subject": definition.task.value if definition.task else str(definition.family),
        "candidate_version_id": str(artifact_version),
        "artifact_checksum": artifact_checksum,
        "artifact_size_bytes": artifact_size,
        "evaluation_checksum": str(
            result["execution_result"].get("evaluation_report_checksum")
            or result["execution_result"].get("report_content_checksum")
        ),
        "comparison": result["comparison"],
        "proposal_id": str(result["proposal_id"]),
        "proposal_checksum": str(result["proposal_checksum"]),
        "candidate_dossier": candidate_dossier,
        "candidate_dossier_checksum": dossier_checksum,
        "candidate_dossier_file": str(dossier_path.relative_to(ROOT)),
        "plan_status": first_plan["status"],
        "planning_seconds": planning_seconds,
        "execution_seconds": elapsed,
        "stages": {name: str(event["state"]) for name, event in latest.items()},
        "exact_replay": True,
        "serving_action": "NONE",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
    }


async def _create_and_monitor_receipts(
    database: Database,
    settings: Settings,
    binding_id: UUID,
    cohort: Any,
    telemetry: Telemetry,
) -> dict[str, Any]:
    service = PredictionService(settings, database)
    try:
        baseline_pulls = tuple(
            pull for group in cohort.pulls_by_session[:2] for pull in group
        )
        comparison_pulls = tuple(
            pull for group in cohort.pulls_by_session[12:14] for pull in group
        )
        observed: dict[str, list[UUID]] = {"baseline": [], "comparison": []}
        for label, pulls in (
            ("baseline", baseline_pulls),
            ("comparison", comparison_pulls),
        ):
            for pull in pulls:
                result = await service.anomaly(
                    AnomalyRequest(
                        pull_id=pull.pull_id,
                        vehicle_id=pull.vehicle_id,
                        observation_cutoff=pull.ended_at + timedelta(seconds=1),
                        source_role=SourceRole.SYNTHETIC,
                        family="thermal",
                    ),
                    idempotency_key=None,
                )
                observed[label].append(result.receipt_id)
        async with database.session() as db:
            times = (
                (
                    await db.execute(
                        text(
                            "SELECT id,created_at FROM prediction_receipts WHERE id=ANY(:ids)"
                        ),
                        {"ids": observed["baseline"] + observed["comparison"]},
                    )
                )
                .mappings()
                .all()
            )
        by_id = {UUID(str(row["id"])): row["created_at"] for row in times}
        baseline_start = min(by_id[item] for item in observed["baseline"]) - timedelta(
            microseconds=1
        )
        baseline_end = max(by_id[item] for item in observed["baseline"]) + timedelta(
            microseconds=1
        )
        comparison_start = min(by_id[item] for item in observed["comparison"])
        comparison_end = max(
            by_id[item] for item in observed["comparison"]
        ) + timedelta(microseconds=1)
        comparison_start = max(comparison_start, baseline_end)
        binding = await service.repository.binding(binding_id)
        _require(binding is not None, "thermal 9D binding disappeared")
        async with database.session() as db:
            method = await db.scalar(
                text(
                    "SELECT d.method FROM anomaly_detector_versions v "
                    "JOIN anomaly_detector_definitions d ON d.id=v.detector_definition_id "
                    "WHERE v.id=:id"
                ),
                {"id": binding.detector_version_id},
            )
        _require(isinstance(method, str), "thermal detector method is unavailable")
        definition = detector_definition("thermal", DetectorMethod(method))
        protocol = MonitoringProtocol(
            binding_id=binding_id,
            vehicle_id=cohort.vehicle_id,
            configuration_id=cohort.configuration_a,
            source_role=SourceRole.SYNTHETIC,
            baseline_start=baseline_start,
            baseline_end=baseline_end,
            comparison_start=comparison_start,
            comparison_end=comparison_end,
            minimum_rows=2,
            minimum_sessions=2,
            max_rows_per_window=100,
            feature_keys=tuple(sorted(definition.feature_keys)),
        )
        source_before_monitor = await _table_digest(database, SERVING_TABLES)
        report = await monitor_receipts(database, protocol, telemetry=telemetry)
        source_after_monitor = await _table_digest(database, SERVING_TABLES)
        _require(
            source_before_monitor == source_after_monitor,
            "read-only monitoring mutated Phase 9D/9E/9F/9G rows",
        )
        baseline = report["windows"]["baseline"]
        comparison = report["windows"]["comparison"]
        _require(
            baseline["receipts"] == len(observed["baseline"]),
            "monitor lost baseline receipts",
        )
        _require(
            comparison["receipts"] == len(observed["comparison"]),
            "monitor lost comparison receipts",
        )
        _require(
            baseline["abstained"] + comparison["abstained"] > 0,
            "acceptance fixture did not exercise abstention monitoring",
        )
        _require(
            report["performance_drift"]["status"] == "UNKNOWN",
            "unlabeled receipts were converted into performance evidence",
        )
        _require(
            report["real_world_predictive_validity"] == "NOT_ESTABLISHED",
            "monitor overclaimed scientific validity",
        )
        return {
            "status": "PASS",
            "protocol_checksum": protocol.checksum,
            "protocol": protocol.model_dump(mode="json"),
            "source_type_composition": report["source_type_composition"],
            "source_role_drift": report["source_role_drift"],
            "baseline": baseline,
            "comparison": comparison,
            "drift_findings": {
                "feature_source": report["feature_source_drift"],
                "feature_distribution": report["feature_distribution_shift"],
                "missingness": report["missingness_shift"],
                "score_distribution": report["score_distribution_shift"],
                "performance": report["performance_drift"],
                "calibration": report["calibration_drift"],
            },
            "real_world_predictive_validity": report["real_world_predictive_validity"],
            "scientific_limitations": report["scientific_limitations"],
            "source_immutable_during_monitor": source_before_monitor
            == source_after_monitor,
            "serving_action": report["serving_action"],
        }
    finally:
        await service.close()


async def _review_proposal(
    proposal: dict[str, Any], *, database_url: str
) -> dict[str, Any]:
    token = (
        "phase10-acceptance-review-token-" + hashlib.sha256(os.urandom(32)).hexdigest()
    )
    reviewer = {
        "schema_version": "phase10-review-auth-v1",
        "operators": [
            {
                "id": "phase10-acceptance-reviewer",
                "role": "mlops_reviewer",
                "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            }
        ],
    }
    await asyncio.to_thread(EVIDENCE.mkdir, parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix="reviewer-", suffix=".json", dir=EVIDENCE
    )
    config = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(reviewer, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        environment = {
            **os.environ,
            "ENVIRONMENT": "test",
            "DATABASE_URL": database_url,
            "TEST_DATABASE_URL": database_url,
            "MLOPS_REVIEWER_CONFIG": str(await asyncio.to_thread(config.resolve)),
            "MLOPS_OPERATOR_TOKEN": token,
        }
        executable = Path(sys.executable).with_name("vehicle-mlops")
        common = [
            str(executable),
            "review",
            "--proposal-id",
            str(proposal["proposal_id"]),
            "--proposal-checksum",
            str(proposal["proposal_checksum"]),
            "--decision",
            "accept",
            "--reason",
            "Controlled synthetic candidate reviewed for the Phase 10 acceptance receipt.",
            "--execute",
            "--confirm-environment",
            "test",
            "--confirm-proposal-checksum",
            str(proposal["proposal_checksum"]),
        ]

        async def run_cli(token_value: str) -> tuple[int, str]:
            process = await asyncio.create_subprocess_exec(
                str(executable),
                *common[1:],
                env={**environment, "MLOPS_OPERATOR_TOKEN": token_value},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=60)
            return process.returncode or 0, stdout.decode("utf-8")

        denied_status, _ = await run_cli("wrong-operator-token")
        _require(denied_status == 2, "invalid reviewer credentials were accepted")
        accepted_status, accepted_stdout = await run_cli(token)
        _require(accepted_status == 0, "explicit authenticated review failed")
        value = json.loads(accepted_stdout)
        _require(
            value.get("status") == "APPROVED_FOR_CONTROLLED_REVIEW",
            "review did not produce a bounded human decision",
        )
        _require(
            value.get("serving_action") == "NONE",
            "MLOps review crossed the serving boundary",
        )
        return {"invalid_token_denied": True, "decision": value, "cli": str(executable)}
    finally:
        await asyncio.to_thread(config.unlink, missing_ok=True)


async def _prediction_cli(database_url: str, *arguments: str) -> dict[str, Any]:
    """Invoke the existing 9D CLI with a fixed test-only environment and bounded wait."""
    executable = Path(sys.executable).with_name("vehicle-prediction")
    environment = {
        **os.environ,
        "ENVIRONMENT": "test",
        "DATABASE_URL": database_url,
        "TEST_DATABASE_URL": database_url,
    }
    process = await asyncio.create_subprocess_exec(
        str(executable),
        *arguments,
        cwd=ROOT,
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise RuntimeError(
            "Phase 9D CLI exceeded its 30 second acceptance bound"
        ) from None
    if len(stdout) > 1024 * 1024 or len(stderr) > 1024 * 1024:
        raise RuntimeError("Phase 9D CLI output exceeded its acceptance bound")
    if process.returncode == 0:
        value = json.loads(stdout)
        if not isinstance(value, dict):
            raise TypeError("Phase 9D CLI returned a non-object receipt")
        return value
    try:
        error = json.loads(stderr)
    except json.JSONDecodeError:
        error = {}
    return {
        "status": "DENIED",
        "exit_code": process.returncode,
        "error_category": error.get("error_category", "UNKNOWN"),
    }


async def _active_binding_id(
    database: Database, settings: Settings, task: MLTask
) -> UUID:
    service = PredictionService(settings, database)
    try:
        bindings = await service.repository.bindings_for_slot(
            PredictionKind.NEXT_PULL,
            task.value,
            SourceRole.SYNTHETIC,
            "test",
        )
        active = [binding for binding in bindings if binding.is_active]
        _require(
            len(active) == 1, "9D rollback rehearsal lost its unique active binding"
        )
        return active[0].id
    finally:
        await service.close()


async def _tamper_candidate(database: Database, run: dict[str, Any]) -> bool:
    if run["kind"] == "supervised":
        from vehicle_platform.ml.artifacts import ArtifactStore, ArtifactValidationError

        store_type: Any = ArtifactStore
        error_type: Any = ArtifactValidationError
        table = "ml_model_versions"
    else:
        from vehicle_platform.anomalies.artifacts import AnomalyArtifactError

        store_type = DetectorArtifactStore
        error_type = AnomalyArtifactError
        table = "anomaly_detector_versions"
    query = (
        "SELECT artifact_path,artifact_checksum FROM ml_model_versions WHERE id=:id"
        if table == "ml_model_versions"
        else "SELECT artifact_path,artifact_checksum FROM anomaly_detector_versions WHERE id=:id"
    )
    async with database.session() as db:
        row = (
            (await db.execute(text(query), {"id": run["candidate_version_id"]}))
            .mappings()
            .one()
        )
    relative = Path(str(row["artifact_path"]))
    with tempfile.TemporaryDirectory(prefix="phase10-tamper-") as directory:
        root = Path(directory)
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        source_root = (
            PHASE9B_ARTIFACT_ROOT
            if run["kind"] == "supervised"
            else PHASE9C_ARTIFACT_ROOT
        )
        payload = read_verified_bytes(
            source_root,
            source_root / relative,
            maximum_bytes=MAX_ARTIFACT_BYTES,
            expected_checksum=str(row["artifact_checksum"]),
        )
        target.write_bytes(payload[:-1] + bytes([payload[-1] ^ 1]))
        try:
            await store_type(root).load_registered(
                database, str(run["candidate_version_id"])
            )
        except error_type:
            return True
    return False


async def _main() -> dict[str, Any]:
    git_sha = _git_sha()
    database_url = os.environ.get("TEST_DATABASE_URL", "")
    if not database_url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise RuntimeError("Phase 10 requires a disposable vehicle_test database")
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = database_url
    settings = Settings(
        database_url=SecretStr(database_url),
        environment="test",
        prediction_service_enabled=True,
        prediction_operator_token=SecretStr(
            "phase10-acceptance-token-" + hashlib.sha256(os.urandom(32)).hexdigest()
        ),
        prediction_operator_vehicle_ids="",
    )
    database = Database(settings, command_timeout=120)
    telemetry = Telemetry(
        settings, database, service_name="vehicle-platform-mlops-acceptance"
    )
    exporter = InMemorySpanExporter()
    telemetry.traces.add_span_processor(SimpleSpanProcessor(exporter))
    started = time.perf_counter()
    cpu_started = time.process_time()
    try:
        phase9g_report = await phase9g.run(
            allow_dirty=False, output=EVIDENCE.parent / "phase9g" / "acceptance.json"
        )
        _require(
            phase9g_report["engineering_status"] == "PASS",
            "Phase 9G source oracle did not pass",
        )
        _require(
            phase9g_report["scientific_readiness"]["real_world_predictive_validity"]
            == "NOT_ESTABLISHED",
            "Phase 9G scientific status changed",
        )
        training = await seed_predictive_fixture(
            database,
            start_at=datetime(2026, 1, 1, tzinfo=UTC),
            vehicle_model_prefix="PHASE10-TRAINING",
            engine_codes=("N55",),
            scenario_seed=0,
            generator_version="phase10-controlled-training-v1",
            vehicle_count=8,
        )
        await generate_fixture_features(database, training)
        # `Settings` is immutable. Use a per-fixture service configuration with a narrow
        # allowlist after the 9A fixture has established its vehicle UUIDs.
        # Keep the held-out evaluation partitions disjoint by vehicle and
        # configuration while preserving strictly increasing time. The 9G
        # calibration protocol rejects the same vehicle or configuration in
        # calibration, validation, and test, so each temporal block receives a
        # separate deterministic fixture.
        evaluation_fixtures: dict[MLTask, list[Any]] = {}
        for task in MLTask:
            evaluation_fixtures[task] = []
            for phase, start_at in (
                ("CALIBRATION", datetime(2026, 4, 1, tzinfo=UTC)),
                ("VALIDATION", datetime(2026, 6, 1, tzinfo=UTC)),
                ("TEST", datetime(2026, 9, 1, tzinfo=UTC)),
            ):
                fixture = await seed_predictive_fixture(
                    database,
                    start_at=start_at,
                    vehicle_model_prefix=f"P10-{task.value[:12]}-{phase}",
                    engine_codes=("N55", "B58", "S55"),
                    scenario_seed=9142,
                    generator_version=f"phase10-{task.value.lower()}-{phase.lower()}-v1",
                    vehicle_count=4,
                )
                await generate_fixture_features(database, fixture)
                evaluation_fixtures[task].append(fixture)
        task_pull_ids = {
            task: tuple(
                sorted(
                    (pull for fixture in fixtures for pull in fixture.pull_ids), key=str
                )
            )
            for task, fixtures in evaluation_fixtures.items()
        }
        phase9c_cohort = await _phase9c_primary(database)
        scope = str(phase9c_cohort.vehicle_id)
        settings = Settings(
            database_url=SecretStr(database_url),
            environment="test",
            prediction_service_enabled=True,
            prediction_operator_token=SecretStr(
                "phase10-controlled-token-" + hashlib.sha256(os.urandom(32)).hexdigest()
            ),
            prediction_operator_vehicle_ids=scope,
        )
        # Recreate telemetry with the same database and the now established test scope.
        telemetry.shutdown()
        telemetry = Telemetry(
            settings, database, service_name="vehicle-platform-mlops-acceptance"
        )
        exporter = InMemorySpanExporter()
        telemetry.traces.add_span_processor(SimpleSpanProcessor(exporter))
        # Seed read-only 9D source receipts separately, then prove the monitor itself
        # preserves their immutable source rows before taking the MLOps baseline.
        model_bindings, detector_bindings = await _register_champions(
            database, settings, phase9c_cohort
        )
        thermal_monitor = await _create_and_monitor_receipts(
            database, settings, detector_bindings["thermal"], phase9c_cohort, telemetry
        )
        definitions: list[tuple[PipelineDefinition, UUID]] = []
        for task in MLTask:
            definitions.append(
                (
                    await _supervised_definition(
                        database,
                        task,
                        tuple(sorted(training.pull_ids, key=str)),
                        task_pull_ids[task],
                        git_sha=git_sha,
                    ),
                    model_bindings[task.value],
                )
            )
        for family in ("thermal", "boost_air", "performance", "fuel"):
            definitions.append(
                (
                    await _anomaly_definition(
                        database, family, phase9c_cohort, git_sha=git_sha
                    ),
                    detector_bindings[family],
                )
            )
        outcomes: list[dict[str, Any]] = []
        for definition, binding_id in definitions:
            outcomes.append(
                await _run_definition(database, telemetry, definition, binding_id)
            )

        # Re-execute one complete Phase 9B training/evaluation pipeline with the
        # same source snapshot and seed under a new immutable definition revision.
        original_definition, original_binding = definitions[0]
        reproduction_definition = original_definition.model_copy(
            update={"definition_version": "p10-thermal-reproduction-v2"}
        )
        reproduction = await _run_definition(
            database, telemetry, reproduction_definition, original_binding
        )
        _require(
            reproduction["artifact_checksum"] == outcomes[0]["artifact_checksum"],
            "same-seed Phase 9B reproduction changed artifact bytes",
        )
        _require(
            reproduction["comparison"]["evaluation_dataset_checksum"]
            == outcomes[0]["comparison"]["evaluation_dataset_checksum"],
            "same-seed Phase 9B reproduction changed the holdout dataset",
        )
        _require(
            reproduction["comparison"]["challenger"]
            == outcomes[0]["comparison"]["challenger"],
            "same-seed Phase 9B reproduction changed matched candidate metrics",
        )

        # Pipelines append candidate and 9G evaluation receipts by design. Take
        # the immutability baseline after those writes, then isolate the later
        # offline comparison, monitoring, review, and rollback-plan operations.
        serving_before = await _table_digest(database, SERVING_TABLES)
        for (definition, binding_id), outcome in zip(
            definitions, outcomes, strict=True
        ):
            repeated_comparison = (
                await compare_supervised(
                    database,
                    definition,
                    champion_binding_id=binding_id,
                    challenger_version_id=UUID(outcome["candidate_version_id"]),
                )
                if definition.kind is PipelineKind.SUPERVISED
                else await compare_anomaly(
                    database,
                    definition,
                    champion_binding_id=binding_id,
                    challenger_version_id=UUID(outcome["candidate_version_id"]),
                )
            )
            _require(
                repeated_comparison == outcome["comparison"],
                "repeated matched comparison changed its deterministic result",
            )

        # Explicitly verify a mismatched champion is rejected without source writes.
        thermal_definition = definitions[0][0]
        incompatible = await compare_anomaly(
            database,
            definitions[4][0],
            champion_binding_id=detector_bindings["thermal"],
            challenger_version_id=UUID(outcomes[4]["candidate_version_id"]),
        )
        _require(
            incompatible["status"] == "NOT_COMPARABLE",
            "incompatible family champion was accepted",
        )
        _require(
            incompatible.get("serving_action") == "NONE",
            "incompatible comparison changed serving",
        )
        spoof = thermal_definition.model_copy(
            update={"source_role": SourceRole.IMPORTED}
        )
        spoof_plan = await plan_supervised(database, spoof)
        _require(
            spoof_plan["status"] != "READY_TO_REVIEW",
            "source-role spoofing passed the planner",
        )

        proposal = outcomes[0]
        proposal_receipt = await ControlPlaneRepository(database).inspect_proposal(
            UUID(proposal["proposal_id"])
        )
        _require(
            proposal_receipt["proposal"]["body"]["serving_permission"] is False,
            "proposal granted serving permission",
        )
        review = await _review_proposal(proposal, database_url=database_url)
        serving_after_mlops = await _table_digest(database, SERVING_TABLES)
        _require(
            serving_before == serving_after_mlops,
            "offline comparison, monitoring or review mutated prior 9D/9E/9F/9G records",
        )
        # Isolated 9D CLI rehearsal on the disposable candidate after a simulated fault.
        # MLOps review has completed; every state transition below requires explicit 9D flags.
        previous_binding_id = model_bindings[MLTask.THERMAL_DEGRADATION.value]
        previous_active = await _active_binding_id(
            database, settings, MLTask.THERMAL_DEGRADATION
        )
        _require(
            previous_active == previous_binding_id,
            "rollback rehearsal did not start from its recorded incumbent",
        )
        approved_binding = await _prediction_cli(
            database_url,
            "approve",
            "--kind",
            "next_pull",
            "--version-id",
            str(proposal["candidate_version_id"]),
            "--source-role",
            "synthetic",
            "--reason",
            "Isolated disposable Phase 10 rollback rehearsal candidate approval.",
            "--operator-id",
            "phase10-acceptance-operator",
            "--review-reference",
            "phase10-cli-rollback-rehearsal",
            "--yes",
            "--confirm-environment",
            "test",
        )
        _require(approved_binding.get("status") == "APPROVED", "9D CLI approval failed")
        candidate_binding_id = UUID(approved_binding["binding_id"])
        activated_binding = await _prediction_cli(
            database_url,
            "activate",
            "--binding-id",
            str(candidate_binding_id),
            "--reason",
            "Activate disposable candidate before simulated-fault rollback rehearsal.",
            "--operator-id",
            "phase10-acceptance-operator",
            "--yes",
            "--confirm-environment",
            "test",
        )
        _require(
            activated_binding.get("status") == "ACTIVATED"
            and await _active_binding_id(database, settings, MLTask.THERMAL_DEGRADATION)
            == candidate_binding_id,
            "9D CLI did not activate the isolated rollback rehearsal candidate",
        )
        rollback = await plan_rollback(
            database,
            UUID(proposal["proposal_id"]),
            previous_binding_id,
            execute=True,
            confirmed_environment="test",
            confirmed_proposal_checksum=proposal["proposal_checksum"],
        )
        _require(
            rollback["execution"] == "PERSISTED",
            "rollback readiness plan was not persisted",
        )
        rollback_inspection = await inspect_rollback_plan(
            database, UUID(rollback["plan_id"])
        )
        _require(
            rollback_inspection["status"] == "READY_FOR_SEPARATE_9D_REVIEW",
            "fresh rollback plan did not verify",
        )
        rollback_action = await _prediction_cli(
            database_url,
            "rollback",
            "--binding-id",
            str(previous_binding_id),
            "--reason",
            "Simulated post-activation fault in isolated disposable acceptance.",
            "--operator-id",
            "phase10-acceptance-operator",
            "--yes",
            "--confirm-environment",
            "test",
        )
        _require(
            rollback_action.get("status") == "ROLLED_BACK"
            and await _active_binding_id(database, settings, MLTask.THERMAL_DEGRADATION)
            == previous_binding_id,
            "existing 9D rollback CLI failed to restore its explicit target",
        )
        digest_before_denied_rollback = await _table_digest(database, SERVING_TABLES)
        denied_rollback = await _prediction_cli(
            database_url,
            "rollback",
            "--binding-id",
            str(previous_binding_id),
            "--reason",
            "Verify rollback is denied after its target is already active.",
            "--operator-id",
            "phase10-acceptance-operator",
            "--yes",
            "--confirm-environment",
            "test",
        )
        digest_after_denied_rollback = await _table_digest(database, SERVING_TABLES)
        _require(
            denied_rollback.get("status") == "DENIED"
            and denied_rollback.get("exit_code") == 2
            and digest_before_denied_rollback == digest_after_denied_rollback,
            "denied 9D rollback changed serving/source records",
        )
        rollback_plan_after_action = await inspect_rollback_plan(
            database, UUID(rollback["plan_id"])
        )
        _require(
            rollback_plan_after_action["status"] == "STALE",
            "rollback readiness plan was not invalidated by the actual 9D event",
        )
        serving_after_separate_9d_action = await _table_digest(database, SERVING_TABLES)
        rollback_rehearsal = {
            "status": "PASS",
            "simulated_fault": "post_activation_candidate_fault",
            "previous_active_binding_id": str(previous_active),
            "candidate_binding_id": str(candidate_binding_id),
            "active_binding_after_activation": str(candidate_binding_id),
            "rollback_cli": rollback_action,
            "active_binding_after_rollback": str(previous_binding_id),
            "denied_repeat": denied_rollback,
            "denied_repeat_had_no_source_effect": (
                digest_before_denied_rollback == digest_after_denied_rollback
            ),
            "readiness_plan_after_rollback": rollback_plan_after_action["status"],
            "serving_action_recorded_by_mlops": "NONE",
        }

        tamper_results = []
        for run in (*outcomes, reproduction):
            tamper_results.append(await _tamper_candidate(database, run))
        _require(all(tamper_results), "registered artifact tampering was not rejected")
        serving_final = await _table_digest(database, SERVING_TABLES)
        _require(
            serving_after_separate_9d_action == serving_final,
            "rollback planning or artifact verification mutated prior source records",
        )
        finished_spans = exporter.get_finished_spans()
        spans = sorted(span.name for span in finished_spans)
        metrics = telemetry.render_metrics().decode("utf-8")
        metric_lines = [
            line for line in metrics.splitlines() if line and not line.startswith("#")
        ]
        metric_names = sorted(
            {re.split(r"[\s{]", line, maxsplit=1)[0] for line in metric_lines}
        )
        metric_label_names = sorted(
            {
                field.split("=", maxsplit=1)[0].strip()
                for line in metric_lines
                if (match := re.search(r"\{([^}]*)\}", line))
                for field in match.group(1).split(",")
                if "=" in field
            }
        )
        span_attribute_names = sorted(
            {str(key) for span in finished_spans for key in (span.attributes or {})}
        )
        forbidden_labels = {
            "run_id",
            "artifact_id",
            "candidate_id",
            "vehicle_id",
            "session_id",
            "pull_id",
            "feature_key",
            "checksum",
            "vin",
            "secret",
            "token",
            "path",
        }
        _require(
            not forbidden_labels.intersection(metric_label_names),
            "entity or sensitive identifier was emitted as a metric label",
        )
        _require(
            not any(
                str(vehicle_id).lower() in metrics.lower()
                for vehicle_id in scope.split(",")
            ),
            "vehicle scope identifier leaked into metrics",
        )
        _require(
            "mlops_pipeline_runs" in metrics and "mlops_pipeline" in metrics,
            "Phase 10 metrics were not emitted",
        )
        _require(
            not any(
                str(value) in metrics
                for value in [item["run_id"] for item in (*outcomes, reproduction)]
            ),
            "run UUID leaked into metrics",
        )
        _require("mlops.pipeline.run" in spans, "Phase 10 trace span was not emitted")
        elapsed = time.perf_counter() - started
        return {
            "schema_version": "phase10-acceptance-v1",
            "git_sha": git_sha,
            "status": "PASS",
            "phase9g_source_receipt_checksum": phase9g_report["acceptance_checksum"],
            "supervised": {
                item["subject"]: item
                for item in outcomes
                if item["kind"] == "supervised"
            },
            "anomaly": {
                item["subject"]: item for item in outcomes if item["kind"] == "anomaly"
            },
            "deterministic_reproduction": {
                "status": "REPRODUCED",
                "original_run_id": outcomes[0]["run_id"],
                "reproduction_run_id": reproduction["run_id"],
                "original_definition_fingerprint": outcomes[0][
                    "definition_fingerprint"
                ],
                "reproduction_definition_fingerprint": reproduction[
                    "definition_fingerprint"
                ],
                "artifact_checksum_equal": reproduction["artifact_checksum"]
                == outcomes[0]["artifact_checksum"],
                "evaluation_dataset_checksum_equal": reproduction["comparison"][
                    "evaluation_dataset_checksum"
                ]
                == outcomes[0]["comparison"]["evaluation_dataset_checksum"],
                "candidate_metrics_equal": reproduction["comparison"]["challenger"]
                == outcomes[0]["comparison"]["challenger"],
                "reproduction": reproduction,
            },
            "monitoring": thermal_monitor,
            "proposal_review": review,
            "rollback_readiness": rollback_inspection,
            "rollback_rehearsal": rollback_rehearsal,
            "adversaries": {
                "incompatible_candidate_rejected": incompatible["status"]
                == "NOT_COMPARABLE",
                "source_role_spoof_rejected": spoof_plan["status"] != "READY_TO_REVIEW",
                "registered_artifact_tamper_rejected_count": sum(tamper_results),
                "registered_artifact_tamper_attempts": len(tamper_results),
                "idempotent_replay_count": len(outcomes) + 1,
                "source_tables_immutable_during_mlops": serving_before
                == serving_after_mlops,
                "serving_changes_only_after_separate_9d_action": (
                    serving_after_mlops != serving_after_separate_9d_action
                ),
                "rollback_planning_preserved_sources": (
                    serving_after_separate_9d_action == serving_final
                ),
            },
            "source_immutability": {
                "before_offline_comparison_monitor_review": serving_before,
                "after_comparison_monitor_review": serving_after_mlops,
                "after_separate_9d_action": serving_after_separate_9d_action,
                "after_separate_9d_action_and_rollback_planning": serving_final,
            },
            "observability": {
                "spans": spans,
                "span_attribute_names": span_attribute_names,
                "metric_names": metric_names,
                "metric_label_names": metric_label_names,
                "metrics_contains_runs": any(
                    name.startswith("mlops_pipeline_runs") for name in metric_names
                ),
                "entity_ids_in_metric_labels": False,
            },
            "performance": {
                "elapsed_seconds": elapsed,
                "cpu_seconds": time.process_time() - cpu_started,
                "peak_rss_bytes": int(
                    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                )
                * 1024,
                "pipeline_count": len(outcomes) + 1,
                "planning_seconds": sum(
                    item["planning_seconds"] for item in (*outcomes, reproduction)
                ),
                "execution_seconds": sum(
                    item["execution_seconds"] for item in (*outcomes, reproduction)
                ),
                "scope": (
                    "bounded disposable synthetic database acceptance; not production capacity"
                ),
            },
            "scientific_readiness": {
                "synthetic_calibration": "SYNTHETIC_ONLY",
                "unlabeled_real_world_performance": "UNKNOWN",
                "real_world_predictive_validity": "NOT_ESTABLISHED",
                "real_world_mechanical_failure_predictive_reliability": "NOT_ESTABLISHED",
                "limitations": [
                    "Synthetic calibration is not proof of real-world predictive validity.",
                    "Phase 9B supervised scores are not mechanical failure probabilities.",
                    (
                        "Phase 9C anomaly scores are not engine-health percentages or confirmed "
                        "diagnoses."
                    ),
                    (
                        "Unlabeled real-world telemetry cannot establish accuracy, recall or "
                        "calibration."
                    ),
                    "Source drift is not evidence of model-performance drift.",
                ],
            },
            "serving_boundary": {
                "mlops_auto_activation": False,
                "mlops_auto_deployment": False,
                "mlops_auto_rollback": False,
                "mlops_auto_retraining": False,
                "proposal_serving_permission": False,
                "separate_phase9d_action_recorded": True,
                "serving_action_by_mlops": "NONE",
            },
        }
    finally:
        telemetry.shutdown()
        await database.close()


async def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    result = await _main()
    result["acceptance_checksum"] = stable_hash(
        {key: value for key, value in result.items() if key != "acceptance_checksum"}
    )
    target = EVIDENCE / "acceptance.json"
    target.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "git_sha": result["git_sha"],
                "acceptance_checksum": result["acceptance_checksum"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
