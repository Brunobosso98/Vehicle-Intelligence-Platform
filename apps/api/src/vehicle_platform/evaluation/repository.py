from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import literal_column, select, text
from sqlalchemy import table as sql_table
from sqlalchemy.exc import DBAPIError

from vehicle_platform.evaluation.contracts import (
    EvaluationProtocol,
    EvaluationRun,
)
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database

EVALUATION_NAMESPACE = UUID("0ebd720b-4eb0-47eb-8c03-9a1510a1aa76")
SOURCE_TABLES = (
    "vehicles",
    "vehicle_configurations",
    "modifications",
    "driving_sessions",
    "pulls",
    "telemetry_samples",
    "feature_generation_runs",
    "dataset_definitions",
    "dataset_build_runs",
    "feature_set_versions",
    "feature_sets",
    "label_definitions",
    "ml_models",
    "training_runs",
    "supervised_datasets",
    "supervised_dataset_rows",
    "ml_model_versions",
    "anomaly_detector_definitions",
    "anomaly_reference_datasets",
    "anomaly_reference_rows",
    "anomaly_detector_versions",
    "anomaly_detection_runs",
    "anomaly_findings",
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
    "investigation_plans",
    "investigation_session_links",
    "investigation_events",
)


class EvaluationRegistryConflict(ValueError):
    pass


async def persist_evaluation(
    database: Database,
    *,
    protocol: EvaluationProtocol,
    run: EvaluationRun,
    reports: dict[str, dict[str, Any]],
    calibration_refs: dict[str, UUID | None],
) -> dict[str, Any]:
    if protocol.checksum != run.protocol_checksum:
        raise EvaluationRegistryConflict("evaluation run references a different protocol checksum")
    run_id = uuid5(EVALUATION_NAMESPACE, run.logical_key)
    protocol_body = _json(protocol.model_dump(mode="json"))
    source_manifest = _json(
        {
            "dataset": run.dataset_manifest.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in run.evidence],
            "folds": [item.model_dump(mode="json") for item in run.folds],
            "source_role": run.source_role.value,
            "not_for_serving": True,
        }
    )
    summary_body = _json(
        {
            "schema_version": run.schema_version,
            "engineering_status": run.engineering_status,
            "scientific_readiness": run.scientific_readiness.model_dump(mode="json"),
            "report_checksum": run.report_checksum,
            "no_source_mutations": run.no_source_mutations,
            "serving_artifacts_unchanged": run.serving_artifacts_unchanged,
            "not_for_serving": run.not_for_serving,
        }
    )
    async with database.session() as db:
        async with db.begin():
            await db.execute(
                text(
                    "INSERT INTO evaluation_protocols("
                    "protocol_version,schema_version,protocol_checksum,protocol_body) "
                    "VALUES(:version,:schema,:checksum,CAST(:body AS jsonb)) "
                    "ON CONFLICT(protocol_version) DO NOTHING"
                ),
                {
                    "version": protocol.protocol_version,
                    "schema": protocol.schema_version,
                    "checksum": protocol.checksum,
                    "body": protocol_body,
                },
            )
            stored_protocol = (
                await db.execute(
                    text(
                        "SELECT protocol_checksum FROM evaluation_protocols "
                        "WHERE protocol_version=:version"
                    ),
                    {"version": protocol.protocol_version},
                )
            ).scalar_one()
            if stored_protocol != protocol.checksum:
                raise EvaluationRegistryConflict(
                    "protocol version is already bound to a different checksum"
                )

            await db.execute(
                text(
                    "INSERT INTO evaluation_runs("
                    "id,protocol_version,logical_fingerprint,source_role,engineering_status,"
                    "git_sha,dataset_fingerprint,report_checksum,source_manifest,summary_body) "
                    "VALUES(:id,:protocol,:logical,:role,:status,:sha,:dataset,:checksum,"
                    "CAST(:manifest AS jsonb),CAST(:summary AS jsonb)) "
                    "ON CONFLICT(logical_fingerprint) DO NOTHING"
                ),
                {
                    "id": run_id,
                    "protocol": protocol.protocol_version,
                    "logical": run.logical_key,
                    "role": run.source_role.value,
                    "status": run.engineering_status,
                    "sha": run.git_sha,
                    "dataset": run.dataset_manifest.row_fingerprint,
                    "checksum": run.report_checksum,
                    "manifest": source_manifest,
                    "summary": summary_body,
                },
            )
            existing = (
                await db.execute(
                    text(
                        "SELECT id,report_checksum FROM evaluation_runs "
                        "WHERE logical_fingerprint=:logical"
                    ),
                    {"logical": run.logical_key},
                )
            ).one()
            if existing.report_checksum != run.report_checksum:
                raise EvaluationRegistryConflict(
                    "logical evaluation key maps to different report contents"
                )
            if existing.id != run_id:
                raise EvaluationRegistryConflict("logical evaluation identity is not deterministic")
            existing_reports = (
                await db.execute(
                    text(
                        "SELECT report_key,report_checksum FROM evaluation_metric_reports "
                        "WHERE evaluation_run_id=:id ORDER BY report_key"
                    ),
                    {"id": run_id},
                )
            ).all()
            if existing_reports:
                expected_reports = {key: stable_hash(body) for key, body in sorted(reports.items())}
                actual_reports = {row.report_key: row.report_checksum for row in existing_reports}
                if actual_reports != expected_reports:
                    raise EvaluationRegistryConflict(
                        "immutable report replay differs from previously persisted report rows"
                    )
                candidate_count = (
                    await db.execute(
                        text(
                            "SELECT count(*) FROM evaluation_calibration_candidates "
                            "WHERE evaluation_run_id=:id"
                        ),
                        {"id": run_id},
                    )
                ).scalar_one()
                applicability_count = (
                    await db.execute(
                        text(
                            "SELECT count(*) FROM evaluation_applicability_assessments "
                            "WHERE evaluation_run_id=:id"
                        ),
                        {"id": run_id},
                    )
                ).scalar_one()
                if candidate_count != len(run.calibration_candidates) or applicability_count != len(
                    run.applicability
                ):
                    raise EvaluationRegistryConflict(
                        "immutable evaluation child rows differ from replay support"
                    )
                return {
                    "run_id": str(run_id),
                    "idempotent_replay": True,
                    "report_checksum": run.report_checksum,
                }

            for key, body in sorted(reports.items()):
                body_json = _json(body)
                checksum = stable_hash(body)
                await db.execute(
                    text(
                        "INSERT INTO evaluation_metric_reports("
                        "id,evaluation_run_id,report_key,report_checksum,report_body) "
                        "VALUES(:id,:run,:key,:checksum,CAST(:body AS jsonb))"
                    ),
                    {
                        "id": uuid5(EVALUATION_NAMESPACE, f"{run_id}:metric:{key}"),
                        "run": run_id,
                        "key": key,
                        "checksum": checksum,
                        "body": body_json,
                    },
                )
            for candidate in run.calibration_candidates:
                body = candidate.model_dump(mode="json")
                await db.execute(
                    text(
                        "INSERT INTO evaluation_calibration_candidates("
                        "id,evaluation_run_id,task,method,candidate_state,"
                        "model_version_id,label_definition_checksum,calibration_dataset_checksum,"
                        "artifact_checksum,artifact_bytes,candidate_body) "
                        "VALUES(:id,:run,:task,:method,:state,:model,:label,:dataset,:artifact,"
                        ":size,CAST(:body AS jsonb))"
                    ),
                    {
                        "id": uuid5(
                            EVALUATION_NAMESPACE,
                            f"{run_id}:candidate:{candidate.task}:{candidate.method.value}",
                        ),
                        "run": run_id,
                        "task": candidate.task,
                        "method": candidate.method.value,
                        "state": candidate.state,
                        "model": calibration_refs.get(f"{candidate.task}:{candidate.method.value}"),
                        "label": candidate.validity_scope.label_definition_checksum,
                        "dataset": candidate.calibration_dataset_checksum,
                        "artifact": candidate.artifact_checksum,
                        "size": candidate.artifact_bytes,
                        "body": _json(body),
                    },
                )
            for assessment in run.applicability:
                body = assessment.model_dump(mode="json")
                checksum = stable_hash(body)
                await db.execute(
                    text(
                        "INSERT INTO evaluation_applicability_assessments("
                        "id,evaluation_run_id,subject_kind,subject_key,"
                        "subject_version,source_role,applicability_status,"
                        "assessment_checksum,assessment_body) "
                        "VALUES(:id,:run,:kind,:key,:version,:role,:status,:checksum,"
                        "CAST(:body AS jsonb))"
                    ),
                    {
                        "id": uuid5(
                            EVALUATION_NAMESPACE,
                            f"{run_id}:applicability:{assessment.subject_kind}:{assessment.subject_key}:{assessment.subject_version}:{assessment.source_role.value}",
                        ),
                        "run": run_id,
                        "kind": assessment.subject_kind,
                        "key": assessment.subject_key,
                        "version": assessment.subject_version,
                        "role": assessment.source_role.value,
                        "status": assessment.status.value,
                        "checksum": checksum,
                        "body": _json(body),
                    },
                )
    return {
        "run_id": str(run_id),
        "idempotent_replay": False,
        "report_checksum": run.report_checksum,
    }


async def source_table_digests(database: Database) -> dict[str, str]:
    """Read complete row digests without returning source identities or values."""
    result: dict[str, str] = {}
    async with database.session() as db:
        async with db.begin():
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            for table_name in SOURCE_TABLES:
                source = sql_table(table_name).alias("source_row")
                query: Any = (
                    select(literal_column("to_jsonb(source_row)::text"))
                    .select_from(source)
                    .order_by(literal_column("to_jsonb(source_row)::text"))
                )
                rows = (await db.execute(query)).scalars().all()
                if len(rows) > 250_000:
                    raise EvaluationRegistryConflict(
                        f"source digest row limit exceeded for allowlisted table {table_name}"
                    )
                digest = hashlib.sha256("".join(str(item) for item in rows).encode()).hexdigest()
                result[table_name] = stable_hash({"count": len(rows), "digest": digest})
    return result


async def assert_evaluation_immutability(database: Database, run_id: UUID) -> dict[str, bool]:
    immutable: dict[str, bool] = {}
    operations = {
        "evaluation_protocols": (
            "UPDATE evaluation_protocols SET schema_version=schema_version "
            "WHERE protocol_version='phase9g-protocol-v1'",
            "DELETE FROM evaluation_protocols WHERE protocol_version='phase9g-protocol-v1'",
        ),
        "evaluation_runs": (
            "UPDATE evaluation_runs SET engineering_status=engineering_status WHERE id=:id",
            "DELETE FROM evaluation_runs WHERE id=:id",
        ),
        "evaluation_metric_reports": (
            "UPDATE evaluation_metric_reports SET created_at=created_at "
            "WHERE evaluation_run_id=:id",
            "DELETE FROM evaluation_metric_reports WHERE evaluation_run_id=:id",
        ),
        "evaluation_calibration_candidates": (
            "UPDATE evaluation_calibration_candidates SET created_at=created_at "
            "WHERE evaluation_run_id=:id",
            "DELETE FROM evaluation_calibration_candidates WHERE evaluation_run_id=:id",
        ),
        "evaluation_applicability_assessments": (
            "UPDATE evaluation_applicability_assessments SET created_at=created_at "
            "WHERE evaluation_run_id=:id",
            "DELETE FROM evaluation_applicability_assessments WHERE evaluation_run_id=:id",
        ),
    }
    async with database.session() as db:
        for table, statements in operations.items():
            params = {} if table == "evaluation_protocols" else {"id": run_id}
            immutable[f"{table}:update"] = await _mutation_is_blocked(db, statements[0], params)
            immutable[f"{table}:delete"] = await _mutation_is_blocked(db, statements[1], params)
            immutable[f"{table}:truncate"] = await _mutation_is_blocked(db, f"TRUNCATE {table}", {})
    return immutable


async def _mutation_is_blocked(db: Any, statement: str, params: dict[str, UUID]) -> bool:
    try:
        await db.execute(text(statement), params)
    except DBAPIError:
        await db.rollback()
        return True
    await db.rollback()
    return False


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)
