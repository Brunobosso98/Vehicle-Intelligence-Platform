"""Independent Phase 9E acceptance over real 9B/9C records and protected HTTP routes."""

from __future__ import annotations

import asyncio
import copy
import json
import os
import secrets
import statistics
import subprocess
import tempfile
import time
import traceback
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID

import evaluate_agent_prediction as phase9f
import evaluate_anomaly_detection as phase9c
import evaluate_prediction_service as phase9d
import httpx
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr, ValidationError
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from vehicle_platform.anomalies.artifacts import ArtifactStore as AnomalyArtifactStore
from vehicle_platform.anomalies.definitions import detector_definition
from vehicle_platform.anomalies.domain import MAX_REFERENCE_ROWS, SourceRole
from vehicle_platform.anomalies.registry import _reference_row_parameters
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.main import create_app
from vehicle_platform.ml.artifacts import ArtifactStore as ModelArtifactStore
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.prediction_evidence.canonical import sha256
from vehicle_platform.prediction_evidence.domain import (
    EvidenceCompleteness,
    EvidenceIntegrity,
    PredictionEvidenceBundle,
    SourceKind,
)
from vehicle_platform.predictions.domain import PredictionStatus
from vehicle_platform.predictions.service import PredictionService

_LEGACY_TABLES = (
    "vehicles",
    "vehicle_configurations",
    "modifications",
    "driving_sessions",
    "telemetry_samples",
    "session_segments",
    "pulls",
    "feature_set_versions",
    "feature_sets",
    "feature_generation_runs",
    "dataset_definitions",
    "dataset_build_runs",
    "label_definitions",
    "ml_models",
    "supervised_datasets",
    "supervised_dataset_rows",
    "ml_model_versions",
    "training_runs",
    "anomaly_detector_definitions",
    "anomaly_reference_datasets",
    "anomaly_reference_rows",
    "anomaly_detector_versions",
    "anomaly_detection_runs",
    "anomaly_findings",
    "prediction_serving_bindings",
    "prediction_serving_events",
    "prediction_receipts",
)
_SOURCE_SCHEMA_MARKERS = {
    SourceKind.PREDICTION_RECEIPT: "0016:prediction_receipts:v1",
    SourceKind.SERVING_BINDING: "0016:prediction_serving_bindings:v1",
    SourceKind.APPROVAL_EVENT: "0016:prediction_serving_events:v1",
    SourceKind.FEATURE_SET: "0013:feature_sets:v1",
    SourceKind.FEATURE_VERSION: "0013:feature_set_versions:v1",
    SourceKind.MODEL_VERSION: "0014:ml_model_versions+label_definitions:v1",
    SourceKind.DETECTOR_VERSION: "0015:anomaly_detector_versions+definitions:v1",
    SourceKind.ANOMALY_RUN: "0015:anomaly_detection_runs:v1",
    SourceKind.ANOMALY_FINDING: "0015:anomaly_findings:v1",
    SourceKind.REFERENCE_DATASET: "0015:anomaly_reference_datasets+bounded-row-counts:v2",
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _migrate(url: str, action: str, revision: str) -> str:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    env["TEST_DATABASE_URL"] = url
    env["ENVIRONMENT"] = "test"
    alembic = root / "apps" / "api" / ".venv" / "bin" / "alembic"
    result = subprocess.run(
        [str(alembic), action, revision],
        cwd=root / "apps" / "api",
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return "\n".join(
        part.strip() for part in (result.stdout, result.stderr) if part.strip()
    )


async def _legacy_digests(database: Database) -> dict[str, str]:
    result: dict[str, str] = {}
    async with database.session() as db:
        for table in _LEGACY_TABLES:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT row_to_json(item)::text "
                            f"FROM {table} item ORDER BY row_to_json(item)::text"
                        )
                    )
                )
                .scalars()
                .all()
            )
            result[table] = sha256([str(row) for row in rows])
    return result


async def _row(
    database: Database, query: str, params: dict[str, Any]
) -> dict[str, Any]:
    async with database.session() as db:
        result = await db.execute(text(query), params)
        row = result.mappings().one_or_none()
    if row is None:
        raise AssertionError("independent source query returned no row")
    return dict(row)


def _bundle_from_database(raw: Any) -> PredictionEvidenceBundle:
    if isinstance(raw, str):
        raw = json.loads(raw)
    return PredictionEvidenceBundle.model_validate(raw)


def _assert_graph_oracle(
    bundle: PredictionEvidenceBundle,
    expected: dict[SourceKind, UUID],
    expected_checksums: dict[SourceKind, str],
) -> None:
    nodes = {node.source_kind: node for node in bundle.nodes}
    _assert(
        set(expected) == set(nodes),
        "evidence graph source kinds differ: "
        f"expected={sorted(kind.value for kind in expected)}, "
        f"actual={sorted(kind.value for kind in nodes)}",
    )
    for kind, entity_id in expected.items():
        _assert(
            nodes[kind].source_entity_id == entity_id, f"wrong {kind.value} source ID"
        )
        _assert(len(nodes[kind].source_checksum) == 64, "source checksum is malformed")
        _assert(
            nodes[kind].source_checksum == expected_checksums[kind],
            f"source row checksum differs for {kind.value}",
        )
        schema_marker = _SOURCE_SCHEMA_MARKERS[kind]
        _assert(
            nodes[kind].source_schema_checksum == sha256(schema_marker),
            f"source schema checksum differs for {kind.value}",
        )
    edge_set = {
        (edge.source_node_id, edge.target_node_id, edge.relation.value)
        for edge in bundle.edges
    }
    root_relations = {
        SourceKind.SERVING_BINDING: "SELECTED_BY",
        SourceKind.APPROVAL_EVENT: "SUPPORTED_BY",
        SourceKind.FEATURE_SET: "DERIVED_FROM",
        SourceKind.FEATURE_VERSION: "LIMITED_BY",
        SourceKind.MODEL_VERSION: "SCORED_WITH",
        SourceKind.DETECTOR_VERSION: "SCORED_WITH",
        SourceKind.ANOMALY_RUN: "DERIVED_FROM",
        SourceKind.ANOMALY_FINDING: "OBSERVED_IN",
        SourceKind.REFERENCE_DATASET: "COMPARED_AGAINST",
    }
    expected_edges = {
        ("receipt", nodes[kind].node_id, relation)
        for kind, relation in root_relations.items()
        if kind in nodes
    }
    if SourceKind.FEATURE_SET in nodes and SourceKind.FEATURE_VERSION in nodes:
        expected_edges.add(
            (
                nodes[SourceKind.FEATURE_SET].node_id,
                nodes[SourceKind.FEATURE_VERSION].node_id,
                "LIMITED_BY",
            )
        )
    if SourceKind.MODEL_VERSION in nodes and SourceKind.FEATURE_VERSION in nodes:
        expected_edges.add(
            (
                nodes[SourceKind.MODEL_VERSION].node_id,
                nodes[SourceKind.FEATURE_VERSION].node_id,
                "SELECTED_BY",
            )
        )
    if SourceKind.DETECTOR_VERSION in nodes and SourceKind.REFERENCE_DATASET in nodes:
        expected_edges.add(
            (
                nodes[SourceKind.DETECTOR_VERSION].node_id,
                nodes[SourceKind.REFERENCE_DATASET].node_id,
                "COMPARED_AGAINST",
            )
        )
    if SourceKind.ANOMALY_FINDING in nodes and SourceKind.ANOMALY_RUN in nodes:
        expected_edges.add(
            (
                nodes[SourceKind.ANOMALY_FINDING].node_id,
                nodes[SourceKind.ANOMALY_RUN].node_id,
                "DERIVED_FROM",
            )
        )
    _assert(len(edge_set) == len(bundle.edges), "duplicate graph edge found")
    _assert(
        edge_set == expected_edges,
        "graph relationships differ from the independent source oracle",
    )
    adjacency: dict[str, list[str]] = {node.node_id: [] for node in bundle.nodes}
    for edge in bundle.edges:
        adjacency[edge.source_node_id].append(edge.target_node_id)
    reachable = {"receipt"}
    stack = ["receipt"]
    while stack:
        for child in adjacency[stack.pop()]:
            if child not in reachable:
                reachable.add(child)
                stack.append(child)
    _assert(reachable == set(adjacency), "evidence graph has unreachable source nodes")


async def _oracle_bundle(
    database: Database, bundle: PredictionEvidenceBundle
) -> dict[str, Any]:
    receipt = await _row(
        database,
        "SELECT * FROM prediction_receipts WHERE id=:id",
        {"id": bundle.receipt_id},
    )
    response = receipt["response_body"]
    if isinstance(response, str):
        response = json.loads(response)
    _assert(
        str(response["receipt_id"]) == str(bundle.receipt_id), "receipt body ID changed"
    )
    _assert(
        bundle.result_type.value == response["result_type"],
        "result kind differs from 9D",
    )
    _assert(bundle.horizon.value == response["horizon"], "horizon differs from 9D")
    _assert(
        bundle.source_role.value == response["source_role"],
        "source role differs from 9D",
    )
    effective_cutoff = response.get("effective_cutoff") or response["requested_cutoff"]
    _assert(
        bundle.effective_cutoff.isoformat() == effective_cutoff.replace("Z", "+00:00"),
        "cutoff differs from 9D or its requested-cutoff fallback",
    )
    score = response.get("engineering_validation_score")
    if response["result_type"] == "anomaly":
        score = response.get("anomaly_score")
    _assert(
        bundle.prediction.status == response["status"],
        "evidence changed the original status",
    )
    _assert(bundle.prediction.score == score, "evidence changed the original score")
    _assert(
        bundle.prediction.threshold == response.get("threshold"),
        "evidence changed threshold",
    )
    _assert(
        bundle.prediction.decision == response.get("decision"),
        "evidence changed decision",
    )
    _assert(
        bundle.source_summary.source_role.value == response["source_role"],
        "quality source role differs",
    )
    _assert(
        bundle.source_summary.receipt_coverage == response["quality"]["coverage"],
        "coverage changed",
    )

    binding = await _row(
        database,
        "SELECT * FROM prediction_serving_bindings WHERE id=:id",
        {"id": receipt["binding_id"]},
    )
    event = await _row(
        database,
        "SELECT * FROM prediction_serving_events WHERE id=:id",
        {"id": receipt["binding_event_id"]},
    )
    _assert(
        event["event_type"] in {"ACTIVATED", "ROLLED_BACK"},
        "receipt event was not an activation",
    )
    _assert(
        event["created_at"] <= receipt["created_at"],
        "receipt predates its approval event",
    )
    expected_checksums = {
        SourceKind.PREDICTION_RECEIPT: sha256(receipt),
        SourceKind.SERVING_BINDING: sha256(binding),
        SourceKind.APPROVAL_EVENT: sha256(event),
    }
    expected: dict[SourceKind, UUID] = {
        SourceKind.PREDICTION_RECEIPT: bundle.receipt_id,
        SourceKind.SERVING_BINDING: binding["id"],
        SourceKind.APPROVAL_EVENT: event["id"],
    }
    if receipt.get("feature_set_id") is not None:
        feature = await _row(
            database,
            "SELECT fs.*,fsv.version AS feature_version,fsv.checksum AS feature_version_checksum,"
            "p.started_at AS pull_started_at,p.ended_at AS pull_ended_at,p.vehicle_id AS pull_vehicle_id,"
            "p.configuration_id AS pull_configuration_id,s.vehicle_id AS session_vehicle_id,"
            "s.configuration_id AS session_configuration_id,s.source_type,s.metadata AS session_metadata "
            "FROM feature_sets fs JOIN feature_set_versions fsv ON fsv.id=fs.feature_set_version_id "
            "JOIN pulls p ON p.id=fs.pull_id JOIN driving_sessions s ON s.id=fs.session_id WHERE fs.id=:id",
            {"id": receipt["feature_set_id"]},
        )
        version = await _row(
            database,
            "SELECT * FROM feature_set_versions WHERE id=:id",
            {"id": feature["feature_set_version_id"]},
        )
        _assert(
            feature["source_hash"] == receipt["feature_set_checksum"],
            "9A source hash differs",
        )
        _assert(
            feature["provenance_hash"] == receipt["feature_provenance_checksum"],
            "9A provenance differs",
        )
        _assert(
            feature["observation_cutoff"] <= bundle.effective_cutoff,
            "FeatureSet exceeds cutoff",
        )
        expected[SourceKind.FEATURE_SET] = feature["id"]
        expected[SourceKind.FEATURE_VERSION] = feature["feature_set_version_id"]
        expected_checksums[SourceKind.FEATURE_SET] = sha256(feature)
        expected_checksums[SourceKind.FEATURE_VERSION] = sha256(version)
        values = feature["feature_values"]
        for fact in bundle.facts:
            if fact.fact_type.value == "COMPUTED_FEATURE":
                actual = values[fact.key]
                _assert(
                    actual["value"] == fact.value,
                    "feature fact differs from stored 9A value",
                )
                _assert(
                    actual["unit"] == fact.unit, "feature fact unit differs from 9A"
                )
                _assert(
                    fact.available_at is None
                    or fact.available_at <= bundle.effective_cutoff,
                    "feature available after cutoff",
                )
                _assert(
                    fact.source_window_end is None
                    or fact.source_window_end <= bundle.effective_cutoff,
                    "feature window exceeds cutoff",
                )
    if receipt["result_kind"] == "next_pull":
        model = await _row(
            database,
            "SELECT mv.*,m.task,ld.key AS label_key,ld.version AS label_version,"
            "ld.definition AS label_definition,ld.checksum AS label_checksum "
            "FROM ml_model_versions mv JOIN ml_models m ON m.id=mv.ml_model_id "
            "JOIN label_definitions ld ON ld.id=mv.label_definition_id WHERE mv.id=:id",
            {"id": receipt["model_version_id"]},
        )
        expected[SourceKind.MODEL_VERSION] = model["id"]
        expected_checksums[SourceKind.MODEL_VERSION] = sha256(model)
        _assert(
            response["task"] == model["task"], "task differs from registered 9B model"
        )
        _assert(
            response["model_version_id"] == str(model["id"]),
            "wrong 9B version in receipt",
        )
        if response["status"] == PredictionStatus.READY_SCORE.value:
            _assert(
                model["threshold"] == receipt["threshold"],
                "9B threshold differs from receipt",
            )
        else:
            _assert(
                receipt["threshold"] is None,
                "abstained prediction exposed a model threshold",
            )
        label = model["label_definition"]
        output_fact = next(
            (
                fact
                for fact in bundle.facts
                if fact.key == "prediction.predicted_outcome_definition"
            ),
            None,
        )
        if output_fact is not None:
            _assert(
                output_fact.value["key"] == model["label_key"],
                "wrong label key in evidence",
            )
            _assert(
                output_fact.value["version"] == model["label_version"],
                "wrong label version",
            )
            _assert(
                output_fact.value["source_outcome"] == label["source_outcome"],
                "wrong label outcome rule",
            )
        _assert(
            all(
                "target" not in fact.key
                and "outcome_pull" not in json.dumps(fact.value).lower()
                for fact in bundle.facts
            ),
            "future target information leaked into NEXT_PULL evidence",
        )
    else:
        detector_id = receipt["detector_version_id"]
        finding_id = receipt["anomaly_finding_id"]
        run_id = receipt["anomaly_run_id"]
        if detector_id is not None:
            detector = await _row(
                database,
                "SELECT dv.*,d.key AS definition_key,d.version AS definition_version,d.family,d.method,"
                "d.definition,d.checksum AS definition_checksum,rd.id AS reference_id,"
                "rd.vehicle_id AS reference_vehicle_id,rd.configuration_id AS reference_configuration_id,"
                "rd.feature_set_version AS reference_feature_version,"
                "rd.feature_set_version_checksum AS reference_feature_version_checksum,rd.cohort_checksum,"
                "rd.observation_cutoff AS reference_cutoff,rd.source_role AS reference_source_role,"
                "rd.source_type AS reference_source_type,rd.policy_version,rd.checksum AS reference_checksum,"
                "rd.row_count,rd.session_count,rd.manifest->'cohort' AS reference_cohort "
                "FROM anomaly_detector_versions dv "
                "JOIN anomaly_detector_definitions d ON d.id=dv.detector_definition_id "
                "JOIN anomaly_reference_datasets rd ON rd.id=dv.reference_dataset_id WHERE dv.id=:id",
                {"id": detector_id},
            )
            expected[SourceKind.DETECTOR_VERSION] = detector["id"]
            expected_checksums[SourceKind.DETECTOR_VERSION] = sha256(detector)
            reference_id = detector["reference_id"]
            reference = {
                key: detector[key]
                for key in (
                    "reference_id",
                    "reference_vehicle_id",
                    "reference_configuration_id",
                    "reference_feature_version",
                    "reference_feature_version_checksum",
                    "cohort_checksum",
                    "reference_cutoff",
                    "reference_source_role",
                    "reference_source_type",
                    "policy_version",
                    "reference_checksum",
                    "row_count",
                    "session_count",
                )
            }
            reference["id"] = reference_id
            counts = await _row(
                database,
                "SELECT count(*)::integer AS row_count,"
                "count(DISTINCT session_id)::integer AS session_count FROM ("
                "SELECT session_id FROM anomaly_reference_rows "
                "WHERE reference_dataset_id=:id LIMIT :limit) bounded_rows",
                {"id": reference_id, "limit": MAX_REFERENCE_ROWS + 1},
            )
            reference["observed_row_count"] = int(counts["row_count"])
            reference["observed_session_count"] = int(counts["session_count"])
            _assert(
                reference["observed_row_count"] == int(detector["row_count"])
                and reference["observed_session_count"]
                == int(detector["session_count"]),
                "9C frozen reference row/session counts differ from its manifest",
            )
            expected[SourceKind.REFERENCE_DATASET] = reference_id
            expected_checksums[SourceKind.REFERENCE_DATASET] = sha256(reference)
        if finding_id is not None and run_id is not None:
            finding = await _row(
                database,
                "SELECT * FROM anomaly_findings WHERE id=:id",
                {"id": finding_id},
            )
            run = await _row(
                database,
                "SELECT * FROM anomaly_detection_runs WHERE id=:id",
                {"id": run_id},
            )
            _assert(finding["run_id"] == run["id"], "9C run/finding link differs")
            _assert(
                finding["detector_version_id"] == detector_id,
                "9C detector version differs",
            )
            _assert(finding["score"] == score, "9C score differs from receipt")
            _assert(
                finding["threshold"] == receipt["threshold"], "9C threshold differs"
            )
            _assert(
                finding["observation_cutoff"] == receipt["requested_cutoff"],
                "9C observation cutoff differs from the requested cutoff",
            )
            _assert(
                finding["status"]
                == (
                    "ANOMALOUS" if response.get("decision") == "ANOMALOUS" else "INLIER"
                )
                if response["status"] == "READY_SCORE"
                else True,
                "9C status differs",
            )
            expected[SourceKind.ANOMALY_FINDING] = finding["id"]
            expected[SourceKind.ANOMALY_RUN] = run["id"]
            expected_checksums[SourceKind.ANOMALY_FINDING] = sha256(finding)
            expected_checksums[SourceKind.ANOMALY_RUN] = sha256(run)
            _assert(
                finding["reference_dataset_id"]
                == expected[SourceKind.REFERENCE_DATASET],
                "9C finding references a different frozen cohort",
            )
            summary = finding["reference_summary"]
            if isinstance(summary, str):
                summary = json.loads(summary)
            summary = summary.get("reference_summary", summary)
            _assert(
                "reference_dataset_id" in summary,
                f"9C reference summary keys: {sorted(summary)}",
            )
            _assert(
                summary["reference_dataset_id"] == str(finding["reference_dataset_id"]),
                "9C reference ID differs",
            )
            _assert(summary["row_count"] > 0, "9C frozen reference summary is empty")
    _assert_graph_oracle(bundle, expected, expected_checksums)
    return {"receipt": receipt, "response": response, "expected_nodes": expected}


async def _select_pull_with_future_target(
    database: Database, fixture: Any
) -> dict[str, Any]:
    targets = await phase9d._select_pull(database, fixture)
    async with database.session() as db:
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT p.id,p.vehicle_id,p.session_id,p.configuration_id,p.ended_at,"
                        "fs.id AS feature_set_id,"
                        "fs.observation_cutoff,fs.quality_metadata "
                        "FROM pulls p JOIN feature_sets fs ON fs.pull_id=p.id "
                        "WHERE fs.entity_scope='pull' ORDER BY p.started_at,p.id"
                    )
                )
            )
            .mappings()
            .all()
        )
    fixture_pull_ids = {str(value) for value in fixture.pull_ids}
    eligible = None
    for row in rows:
        quality = (
            row["quality_metadata"] if isinstance(row["quality_metadata"], dict) else {}
        )
        if (
            "fuel.high_pressure" not in quality.get("available_signals", [])
            or float(quality.get("pull_completeness", 0.0)) < 0.75
            or int(quality.get("duplicate_timestamp_count", 0)) != 0
            or str(row["id"]) not in fixture_pull_ids
        ):
            continue
        async with database.session() as db:
            future_target = (
                (
                    await db.execute(
                        text(
                            "SELECT target_pull_id,target_feature_set_id,target_started_at,"
                            "input_available_at FROM supervised_dataset_rows "
                            "WHERE input_feature_set_id=:feature_set "
                            "AND target_started_at>input_available_at "
                            "AND input_available_at>=:source_cutoff "
                            "ORDER BY target_started_at LIMIT 1"
                        ),
                        {
                            "feature_set": row["feature_set_id"],
                            "source_cutoff": row["observation_cutoff"],
                        },
                    )
                )
                .mappings()
                .first()
            )
        if future_target is not None:
            eligible = {
                **dict(row),
                "future_target": dict(future_target),
                "evidence_cutoff": future_target["input_available_at"],
            }
            break
    if eligible is None:
        raise ValueError(
            "no eligible 9B source pull has a future target after its cutoff"
        )
    _assert(
        eligible["observation_cutoff"]
        <= eligible["evidence_cutoff"]
        < eligible["future_target"]["target_started_at"],
        "9B source cutoff cannot precede its recorded future target",
    )
    return {**targets, "eligible": eligible}


async def _pull_context(database: Database, pull_id: UUID) -> dict[str, UUID]:
    async with database.session() as db:
        row = (
            (
                await db.execute(
                    text(
                        "SELECT id AS pull_id,vehicle_id,session_id,configuration_id "
                        "FROM pulls WHERE id=:id"
                    ),
                    {"id": pull_id},
                )
            )
            .mappings()
            .one()
        )
    if row["configuration_id"] is None:
        raise ValueError("acceptance pull has no configuration context")
    return {key: UUID(str(row[key])) for key in row}


async def _materialize(
    client: httpx.AsyncClient, headers: dict[str, str], receipt_id: str
) -> tuple[dict[str, Any], float]:
    response, duration = await _attempt_materialize(client, headers, receipt_id)
    _assert(
        response.status_code == 200,
        f"evidence materialization returned {response.status_code}: {response.text[:300]}",
    )
    return response.json(), duration


async def _attempt_materialize(
    client: httpx.AsyncClient, headers: dict[str, str], receipt_id: str
) -> tuple[httpx.Response, float]:
    started = time.perf_counter()
    response = await client.post(
        f"/api/v1/prediction-service/runs/{receipt_id}/evidence",
        json={"schema_version": "phase9e-prediction-evidence-v1"},
        headers=headers,
    )
    duration = time.perf_counter() - started
    return response, duration


def _monitor_database_sessions(database: Database, counts: dict[str, int]) -> None:
    def checked_out(*_: Any) -> None:
        counts["active"] += 1
        counts["maximum"] = max(counts["maximum"], counts["active"])

    def checked_in(*_: Any) -> None:
        counts["active"] = max(0, counts["active"] - 1)

    event.listen(database.engine.sync_engine, "checkout", checked_out)
    event.listen(database.engine.sync_engine, "checkin", checked_in)


async def _mutate_feature_for_verification(
    database: Database, feature_set_id: UUID, feature_values: dict[str, Any]
) -> None:
    async with database.session() as db, db.begin():
        await db.execute(text("SET LOCAL session_replication_role='replica'"))
        await db.execute(
            text(
                "UPDATE feature_sets SET feature_values=CAST(:values AS jsonb) WHERE id=:id"
            ),
            {"values": json.dumps(feature_values), "id": feature_set_id},
        )


async def _mutate_finding_for_verification(
    database: Database, finding_id: UUID, score: float
) -> None:
    async with database.session() as db, db.begin():
        await db.execute(text("SET LOCAL session_replication_role='replica'"))
        await db.execute(
            text("UPDATE anomaly_findings SET score=:score WHERE id=:id"),
            {"score": score, "id": finding_id},
        )


async def _table_count(database: Database, table: str, evidence_id: UUID) -> int:
    key = "id" if table == "prediction_evidence_bundles" else "evidence_id"
    async with database.session() as db:
        value = await db.scalar(
            text(f"SELECT count(*) FROM {table} WHERE {key}=:id"),
            {"id": evidence_id},
        )
    return int(value or 0)


def _summarize_bundle_outcomes(
    bundles: dict[str, PredictionEvidenceBundle],
    verification_outcomes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    prediction_status_counts = Counter(
        bundle.prediction.status for bundle in bundles.values()
    )
    completeness_counts = Counter(
        bundle.completeness.value for bundle in bundles.values()
    )
    source_integrity_counts = Counter(
        bundle.integrity.value for bundle in bundles.values()
    )
    verification_integrity_counts = Counter(
        outcome["integrity"] for outcome in verification_outcomes.values()
    )
    gap_code_counts = Counter(
        gap.code.value for bundle in bundles.values() for gap in bundle.gaps
    )
    gap_reason_counts = Counter(
        gap.reason_code
        for bundle in bundles.values()
        for gap in bundle.gaps
        if gap.reason_code is not None
    )
    return {
        "receipt_count": len(bundles),
        "prediction_status_counts": dict(sorted(prediction_status_counts.items())),
        "completeness_counts": dict(sorted(completeness_counts.items())),
        "source_integrity_counts": dict(sorted(source_integrity_counts.items())),
        "verification_integrity_counts": dict(
            sorted(verification_integrity_counts.items())
        ),
        "gap_code_counts": dict(sorted(gap_code_counts.items())),
        "gap_reason_counts": dict(sorted(gap_reason_counts.items())),
        "eligible": sum(
            bundle.prediction.status == PredictionStatus.READY_SCORE.value
            and bundle.completeness is EvidenceCompleteness.COMPLETE
            and bundle.integrity.value == EvidenceIntegrity.VERIFIED.value
            and verification_outcomes[key]["integrity"]
            == EvidenceIntegrity.VERIFIED.value
            for key, bundle in bundles.items()
        ),
        "eligible_definition": "READY_SCORE + COMPLETE + VERIFIED source and verification integrity",
        "complete": completeness_counts.get(EvidenceCompleteness.COMPLETE.value, 0),
        "partial": completeness_counts.get(EvidenceCompleteness.PARTIAL.value, 0),
        "abstained": completeness_counts.get(EvidenceCompleteness.ABSTAINED.value, 0),
        "failed": verification_integrity_counts.get(
            EvidenceIntegrity.FAILED_SOURCE_MISMATCH.value, 0
        ),
        "failed_source_verification": verification_integrity_counts.get(
            EvidenceIntegrity.FAILED_SOURCE_MISMATCH.value, 0
        ),
        "not_verifiable": verification_integrity_counts.get(
            EvidenceIntegrity.NOT_VERIFIABLE.value, 0
        ),
        "unsupported_schema": verification_integrity_counts.get(
            EvidenceIntegrity.UNSUPPORTED_SCHEMA.value, 0
        ),
        "artifact_unavailable_snapshot": verification_integrity_counts.get(
            EvidenceIntegrity.VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE.value, 0
        ),
        "bundles": {
            key: {
                "receipt_id": str(bundle.receipt_id),
                "evidence_id": str(bundle.evidence_id),
                "prediction_status": bundle.prediction.status,
                "completeness": bundle.completeness.value,
                "result_type": bundle.result_type.value,
                "horizon": bundle.horizon.value,
                "source_role": bundle.source_role.value,
                "source_integrity": bundle.integrity.value,
                "verification_integrity": verification_outcomes[key]["integrity"],
                "verification_reason_codes": sorted(
                    verification_outcomes[key]["reason_codes"]
                ),
                "source_quality": {
                    "quality_class": bundle.source_summary.quality_class,
                    "receipt_coverage": bundle.source_summary.receipt_coverage,
                    "feature_coverage": bundle.source_summary.feature_coverage,
                    "observed_feature_count": (
                        bundle.source_summary.observed_feature_count
                    ),
                    "expected_feature_count": (
                        bundle.source_summary.expected_feature_count
                    ),
                    "pull_completeness": bundle.source_summary.pull_completeness,
                },
                "gap_codes": sorted({gap.code.value for gap in bundle.gaps}),
                "node_count": len(bundle.nodes),
                "edge_count": len(bundle.edges),
                "fact_count": len(bundle.facts),
                "source_ids_by_kind": {
                    node.source_kind.value: str(node.source_entity_id)
                    for node in bundle.nodes
                },
            }
            for key, bundle in sorted(bundles.items())
        },
    }


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)


async def _insert_probe_bundle(
    database: Database,
    *,
    evidence_id: UUID,
    receipt_id: UUID,
    schema_version: str,
    logical_fingerprint: str,
    bundle_body: dict[str, Any],
) -> None:
    async with database.session() as db, db.begin():
        await db.execute(
            text(
                "INSERT INTO prediction_evidence_bundles "
                "(id,receipt_id,schema_version,projection_version,verifier_policy_version,"
                "logical_fingerprint,content_checksum,provenance_manifest_checksum,result_type,"
                "horizon,source_role,effective_cutoff,completeness,integrity,bundle_body) "
                "VALUES(:id,:receipt,:schema,'probe-projection','probe-verifier',:logical,:content,"
                ":manifest,'next_pull','NEXT_PULL','synthetic',:cutoff,'PARTIAL',"
                "'NOT_VERIFIABLE',CAST(:body AS jsonb))"
            ),
            {
                "id": evidence_id,
                "receipt": receipt_id,
                "schema": schema_version,
                "logical": logical_fingerprint,
                "content": "b" * 64,
                "manifest": "c" * 64,
                "cutoff": datetime.now(UTC),
                "body": json.dumps(bundle_body),
            },
        )


async def evaluate() -> dict[str, Any]:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError("Phase 9E requires the disposable vehicle_test database")
    evaluator_wall_started = time.perf_counter()
    evaluator_cpu_started = time.process_time()
    token = "phase9e-" + secrets.token_urlsafe(48)
    settings = Settings(
        database_url=SecretStr(url),
        environment="test",
        prediction_service_enabled=True,
        prediction_operator_token=SecretStr(token),
        prediction_max_concurrent_requests=16,
        prediction_max_cpu_concurrency=2,
        prediction_requests_per_minute=300,
        prediction_request_timeout_seconds=8,
        prediction_body_timeout_seconds=2,
        prediction_max_future_cutoff_seconds=60,
    )
    database = Database(settings, command_timeout=60)
    helper_connection_counts = {"active": 0, "maximum": 0}
    api_connection_counts = {"active": 0, "maximum": 0}
    _monitor_database_sessions(database, helper_connection_counts)
    rss_start = phase9d._rss_kib()
    telemetry = Telemetry(settings, database)
    report: dict[str, Any] = {
        "schema_version": "phase9e-independent-acceptance-v1",
        "execution_state": "FAIL",
        "git_sha": _git_sha(),
        "validation_claim": "synthetic controlled engineering fixtures; not real-car validation",
        "real_world_accuracy_claimed": False,
        "supervised": {},
        "anomaly_families": {},
        "abstentions": {},
        "auth_and_scope": {},
        "integrity_controls": {},
        "observability": {},
        "migration": {},
        "benchmarks": {},
        "limits": {
            "max_nodes": 32,
            "max_edges": 64,
            "max_facts": 48,
            "max_gaps": 16,
            "max_json_bytes": 65536,
            "max_artifact_bytes_hashed": 50 * 1024 * 1024,
            "concurrent_builds": 2,
            "cpu_concurrency": settings.prediction_max_cpu_concurrency,
            "request_timeout_seconds": 8,
            "evidence_timeout_seconds": 6,
            "audit_records_per_evidence": 32,
        },
    }
    app: Any | None = None
    telemetry_shutdown = False

    def shutdown_telemetry_once() -> None:
        nonlocal telemetry_shutdown
        if telemetry_shutdown:
            return
        telemetry_shutdown = True
        telemetry.shutdown()

    try:
        await database.check()
        with tempfile.TemporaryDirectory(prefix="phase9e-artifacts-") as temporary:
            root = Path(temporary)
            fixture, trained = await phase9d._train_models(
                database, telemetry, root / "phase9b"
            )
            primary, _secondary, anomaly_context = await phase9d._train_detectors(
                database, telemetry, root / "phase9c"
            )
            targets = await _select_pull_with_future_target(database, fixture)
            legacy_before = await _legacy_digests(database)
            await database.close()
            shutdown_telemetry_once()
            first_upgrade_output = _migrate(url, "upgrade", "0017")
            down_output = _migrate(url, "downgrade", "0016")
            up_output = _migrate(url, "upgrade", "0017")
            lineage_upgrade_output = _migrate(url, "upgrade", "0018")
            lineage_down_output = _migrate(url, "downgrade", "0017")
            lineage_reupgrade_output = _migrate(url, "upgrade", "0018")
            database = Database(settings, command_timeout=60)
            _monitor_database_sessions(database, helper_connection_counts)
            await database.check()
            legacy_after = await _legacy_digests(database)
            _assert(
                legacy_before == legacy_after,
                "9E migration changed legacy source tables",
            )
            report["migration"] = {
                "fresh_upgrade_head": "PASS",
                "round_trip": "0016 -> 0017 -> 0016 -> 0017",
                "phase9f_lineage_round_trip": "0017 -> 0018 -> 0017 -> 0018",
                "legacy_table_count": len(legacy_before),
                "legacy_digests_unchanged": True,
                "first_upgrade_output": first_upgrade_output,
                "downgrade_output": down_output,
                "upgrade_output": up_output,
                "phase9f_upgrade_output": lineage_upgrade_output,
                "phase9f_downgrade_output": lineage_down_output,
                "phase9f_reupgrade_output": lineage_reupgrade_output,
            }

            app = create_app(settings)
            span_exporter = InMemorySpanExporter()
            app.state.telemetry.traces.add_span_processor(
                SimpleSpanProcessor(span_exporter)
            )
            prediction_service: PredictionService = app.state.prediction_service
            _monitor_database_sessions(
                prediction_service.database, api_connection_counts
            )
            model_store = ModelArtifactStore(root / "phase9b")
            anomaly_store = AnomalyArtifactStore(root / "phase9c")
            prediction_service.model_artifacts = model_store
            prediction_service.anomaly_artifacts = anomaly_store
            prediction_service.anomaly_service.artifacts = anomaly_store
            evidence_service = app.state.prediction_evidence_service
            evidence_service.repository.model_artifacts = model_store
            evidence_service.repository.anomaly_artifacts = anomaly_store

            bindings: dict[str, UUID] = {}
            for task, result in trained.items():
                binding_id, _ = await prediction_service.approve_candidate(
                    "next_pull",
                    result.model_version_id,
                    source_role=SourceRole.SYNTHETIC,
                    reason=f"Synthetic fixture scope: Phase 9E acceptance for {task.value}.",
                    operator_id="phase9e-evaluator",
                    review_reference=f"phase9e-synthetic-fixture-{task.value.lower()}-review",
                    environment_confirmation="test",
                )
                await prediction_service.transition(
                    binding_id,
                    "activate",
                    reason="Activate the accepted synthetic fixture version.",
                    operator_id="phase9e-evaluator",
                    environment_confirmation="test",
                )
                bindings[task.value] = binding_id
            for family, version in anomaly_context["versions"].items():
                binding_id, _ = await prediction_service.approve_candidate(
                    "anomaly",
                    version.detector_version_id,
                    source_role=SourceRole.SYNTHETIC,
                    reason=f"Synthetic fixture scope: Phase 9E acceptance for {family}.",
                    operator_id="phase9e-evaluator",
                    review_reference=f"phase9e-synthetic-fixture-{family}-review",
                    environment_confirmation="test",
                )
                await prediction_service.transition(
                    binding_id,
                    "activate",
                    reason="Activate the accepted synthetic detector version.",
                    operator_id="phase9e-evaluator",
                    environment_confirmation="test",
                )
                bindings[family] = binding_id

            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(
                    app=app, client=("127.0.0.1", 12345), raise_app_exceptions=False
                )
                async with httpx.AsyncClient(
                    transport=transport, base_url="http://test"
                ) as client:
                    headers = {"Authorization": f"Bearer {token}"}
                    unauthorized = await client.get(
                        "/api/v1/prediction-service/evidence/00000000-0000-0000-0000-000000000001"
                    )
                    _assert(
                        unauthorized.status_code == 401,
                        "unauthenticated evidence GET was accepted",
                    )
                    unauthorized_post = await client.post(
                        "/api/v1/prediction-service/runs/00000000-0000-0000-0000-000000000001/evidence",
                        json={"schema_version": "phase9e-prediction-evidence-v1"},
                    )
                    query_token = await client.get(
                        "/api/v1/prediction-service/evidence/00000000-0000-0000-0000-000000000001",
                        params={"token": token},
                    )
                    cookie_token = await client.get(
                        "/api/v1/prediction-service/evidence/00000000-0000-0000-0000-000000000001",
                        cookies={"prediction_operator_token": token},
                    )
                    _assert(
                        unauthorized_post.status_code == 401,
                        "unauthenticated materialize POST was accepted",
                    )
                    _assert(
                        query_token.status_code == 401,
                        "query-string credentials were accepted",
                    )
                    _assert(
                        cookie_token.status_code == 401,
                        "cookie credentials were accepted",
                    )
                    oversized = await client.post(
                        "/api/v1/prediction-service/runs/00000000-0000-0000-0000-000000000001/evidence",
                        content=b"x" * (settings.prediction_max_body_bytes + 1),
                        headers={**headers, "Content-Type": "application/json"},
                    )
                    _assert(
                        oversized.status_code == 413,
                        "oversize evidence body bypassed 9D admission",
                    )
                    public_transport = httpx.ASGITransport(
                        app=app, client=("8.8.8.8", 80), raise_app_exceptions=False
                    )
                    async with httpx.AsyncClient(
                        transport=public_transport, base_url="http://public"
                    ) as public_client:
                        public = await public_client.get(
                            "/api/v1/prediction-service/evidence/00000000-0000-0000-0000-000000000001",
                            headers=headers,
                        )
                    _assert(
                        public.status_code == 403,
                        "public peer bypassed the source boundary",
                    )
                    production_rejected = False
                    try:
                        Settings(
                            database_url=SecretStr(
                                "postgresql+asyncpg://vehicle:controlled-test@db:5432/vehicle?ssl=require"
                            ),
                            environment="production",
                            prediction_service_enabled=True,
                            prediction_operator_token=SecretStr(token),
                        )
                    except ValidationError as error:
                        production_rejected = "cannot be enabled in production" in str(
                            error
                        )
                    _assert(
                        production_rejected, "production enablement did not fail closed"
                    )
                    disabled_settings = Settings(
                        database_url=SecretStr(
                            "postgresql+asyncpg://vehicle:test-only@127.0.0.1:1/vehicle_test"
                        ),
                        environment="test",
                        prediction_service_enabled=False,
                        prediction_operator_token=SecretStr(token),
                    )
                    disabled_app = create_app(disabled_settings)
                    async with disabled_app.router.lifespan_context(disabled_app):
                        disabled_transport = httpx.ASGITransport(
                            app=disabled_app,
                            client=("127.0.0.1", 12345),
                            raise_app_exceptions=False,
                        )
                        async with httpx.AsyncClient(
                            transport=disabled_transport, base_url="http://disabled"
                        ) as disabled_client:
                            disabled_get = await disabled_client.get(
                                "/api/v1/prediction-service/evidence/00000000-0000-0000-0000-000000000001",
                                headers=headers,
                            )
                            disabled_post = await disabled_client.post(
                                "/api/v1/prediction-service/runs/00000000-0000-0000-0000-000000000001/evidence",
                                json={
                                    "schema_version": "phase9e-prediction-evidence-v1"
                                },
                                headers=headers,
                            )
                    _assert(
                        disabled_get.status_code == 503,
                        "disabled evidence GET reached the database path",
                    )
                    _assert(
                        disabled_post.status_code == 503,
                        "disabled evidence POST reached the database path",
                    )
                    report["auth_and_scope"].update(
                        {
                            "unauthenticated_get": "401",
                            "unauthenticated_post": "401",
                            "query_token": "401",
                            "cookie_token": "401",
                            "oversized_post": "413",
                            "public_peer": "403",
                            "disabled_get": "503 before DB access",
                            "disabled_post": "503 before DB access",
                            "production_enablement": "rejected by Settings validation",
                        }
                    )

                    eligible = targets["eligible"]
                    pull_id = UUID(str(eligible["id"]))
                    vehicle_id = UUID(str(eligible["vehicle_id"]))
                    cutoff = eligible["evidence_cutoff"]
                    future_target = eligible["future_target"]
                    _assert(
                        cutoff < future_target["target_started_at"],
                        "9B acceptance cutoff does not precede its recorded target pull",
                    )
                    receipts: dict[str, dict[str, Any]] = {}
                    for task in MLTask:
                        response = await client.post(
                            "/api/v1/prediction-service/next-pull",
                            json={
                                "pull_id": str(pull_id),
                                "vehicle_id": str(vehicle_id),
                                "observation_cutoff": cutoff.isoformat(),
                                "source_role": "synthetic",
                                "task": task.value,
                            },
                            headers=headers,
                        )
                        _assert(
                            response.status_code == 200,
                            f"9D {task.value} receipt failed",
                        )
                        receipts[task.value] = response.json()
                        _assert(
                            receipts[task.value]["status"]
                            == PredictionStatus.READY_SCORE.value,
                            f"9D {task.value} fixture did not score",
                        )

                    anomaly_pull = primary.pulls_by_session[12][0]
                    anomaly_cutoff = datetime.now(UTC) + timedelta(seconds=1)
                    for family in anomaly_context["versions"]:
                        response = await client.post(
                            "/api/v1/prediction-service/anomalies",
                            json={
                                "pull_id": str(anomaly_pull.pull_id),
                                "vehicle_id": str(anomaly_pull.vehicle_id),
                                "observation_cutoff": anomaly_cutoff.isoformat(),
                                "source_role": "synthetic",
                                "family": family,
                            },
                            headers=headers,
                        )
                        _assert(
                            response.status_code == 200, f"9D {family} receipt failed"
                        )
                        receipts[f"anomaly:{family}"] = response.json()

                    correlation_response = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(anomaly_pull.pull_id),
                            "vehicle_id": str(anomaly_pull.vehicle_id),
                            "observation_cutoff": anomaly_cutoff.isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.PERFORMANCE_DEGRADATION.value,
                        },
                        headers=headers,
                    )
                    _assert(
                        correlation_response.status_code == 200
                        and correlation_response.json()["status"]
                        == PredictionStatus.READY_SCORE.value,
                        "same-pull 9B prediction did not produce a score",
                    )
                    receipts["correlation:next_pull"] = correlation_response.json()

                    snapshot_before_late_records = (
                        await prediction_service.repository.feature_snapshot(
                            anomaly_pull.pull_id, anomaly_cutoff
                        )
                    )
                    if snapshot_before_late_records is None:
                        raise AssertionError(
                            "same-pull cutoff sentinel has no 9A FeatureSet"
                        )
                    late_records = await phase9d._inject_late_records(
                        database, snapshot_before_late_records, anomaly_cutoff
                    )
                    snapshot_after_late_records = (
                        await prediction_service.repository.feature_snapshot(
                            anomaly_pull.pull_id, anomaly_cutoff
                        )
                    )
                    _assert(
                        snapshot_after_late_records is not None
                        and snapshot_after_late_records.feature_set_id
                        == snapshot_before_late_records.feature_set_id
                        and snapshot_after_late_records.source_hash
                        == snapshot_before_late_records.source_hash
                        and snapshot_after_late_records.provenance_hash
                        == snapshot_before_late_records.provenance_hash
                        and snapshot_after_late_records.values
                        == snapshot_before_late_records.values
                        and snapshot_after_late_records.current_modification_ids
                        == snapshot_before_late_records.current_modification_ids,
                        "late telemetry or modification changed the frozen 9A snapshot",
                    )

                    missing_pull = targets["missing_fuel"]
                    missing_response = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(missing_pull["id"]),
                            "vehicle_id": str(missing_pull["vehicle_id"]),
                            "observation_cutoff": datetime.now(UTC).isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.FUEL_DEVIATION.value,
                        },
                        headers=headers,
                    )
                    _assert(
                        missing_response.status_code == 200,
                        "missing fuel did not yield a receipt",
                    )
                    receipts["missing_fuel"] = missing_response.json()
                    _assert(
                        receipts["missing_fuel"]["status"]
                        == PredictionStatus.ABSTAINED_INSUFFICIENT_SIGNAL.value,
                        "missing fuel was not an explicit abstention",
                    )

                    low_pull = targets["low_quality"]
                    low_response = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(low_pull["id"]),
                            "vehicle_id": str(low_pull["vehicle_id"]),
                            "observation_cutoff": datetime.now(UTC).isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.THERMAL_DEGRADATION.value,
                        },
                        headers=headers,
                    )
                    _assert(
                        low_response.status_code == 200,
                        "low-quality pull did not yield a receipt",
                    )
                    receipts["low_quality"] = low_response.json()
                    _assert(
                        receipts["low_quality"]["status"]
                        == PredictionStatus.ABSTAINED_LOW_QUALITY.value,
                        "low-quality input was not preserved as abstention",
                    )

                    no_feature_vehicle = await phase9c._seed_vehicle(
                        database,
                        name="phase9e-no-feature-set",
                        first_day=40,
                        session_count=1,
                    )
                    no_feature_pull = no_feature_vehicle.pulls_by_session[0][0]
                    no_feature_response = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(no_feature_pull.pull_id),
                            "vehicle_id": str(no_feature_pull.vehicle_id),
                            "observation_cutoff": datetime.now(UTC).isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.THERMAL_DEGRADATION.value,
                        },
                        headers=headers,
                    )
                    _assert(
                        no_feature_response.status_code == 200,
                        "missing FeatureSet did not yield a receipt",
                    )
                    receipts["no_feature_set"] = no_feature_response.json()
                    _assert(
                        receipts["no_feature_set"]["status"]
                        == PredictionStatus.ABSTAINED_INSUFFICIENT_SIGNAL.value,
                        "missing FeatureSet did not preserve abstention",
                    )

                    materialized: dict[str, dict[str, Any]] = {}
                    timings: list[float] = []
                    cold_timings: list[float] = []
                    warm_timings: list[float] = []
                    concurrent_receipt_id = str(
                        receipts["no_feature_set"]["receipt_id"]
                    )
                    concurrent_started = time.perf_counter()
                    concurrent_results = await asyncio.gather(
                        *(
                            _materialize(client, headers, concurrent_receipt_id)
                            for _ in range(10)
                        )
                    )
                    concurrent_elapsed = time.perf_counter() - concurrent_started
                    concurrent_ids = {
                        item[0]["evidence"]["evidence_id"]
                        for item in concurrent_results
                    }
                    _assert(
                        len(concurrent_ids) == 1,
                        "ten concurrent builds created different identities",
                    )
                    _assert(
                        sum(
                            bool(item[0]["materialized"]) for item in concurrent_results
                        )
                        == 1,
                        "concurrent evidence replay duplicated the immutable insert",
                    )
                    timings.extend(item[1] for item in concurrent_results)
                    cold_timings.extend(
                        item[1]
                        for item in concurrent_results
                        if item[0]["materialized"]
                    )
                    warm_timings.extend(
                        item[1]
                        for item in concurrent_results
                        if not item[0]["materialized"]
                    )
                    materialized["no_feature_set"] = concurrent_results[0][0]

                    burst_started = time.perf_counter()
                    burst_100 = await asyncio.gather(
                        *(
                            _attempt_materialize(client, headers, concurrent_receipt_id)
                            for _ in range(100)
                        )
                    )
                    burst_elapsed = time.perf_counter() - burst_started
                    accepted_burst = [
                        item for item in burst_100 if item[0].status_code == 200
                    ]
                    denied_burst = [
                        item for item in burst_100 if item[0].status_code == 429
                    ]
                    _assert(
                        len(accepted_burst) + len(denied_burst) == 100,
                        "100-way materialization burst returned an unexpected status",
                    )
                    burst_ids = {
                        item[0].json()["evidence"]["evidence_id"]
                        for item in accepted_burst
                    }
                    _assert(
                        bool(accepted_burst),
                        "100-way burst produced no accepted replay",
                    )
                    _assert(
                        len(burst_ids) == 1, "100-way burst changed immutable identity"
                    )
                    _assert(
                        not any(
                            item[0].json()["materialized"] for item in accepted_burst
                        ),
                        "100-way replay burst inserted another evidence bundle",
                    )
                    warm_timings.extend(item[1] for item in burst_100)
                    timings.extend(item[1] for item in burst_100)
                    concurrent_100 = {
                        "request_count": 100,
                        "accepted_replays": len(accepted_burst),
                        "admission_denials_429": len(denied_burst),
                        "elapsed_seconds": burst_elapsed,
                        "identity_count": len(burst_ids),
                    }

                    for key, receipt in receipts.items():
                        if key == "no_feature_set":
                            continue
                        payload, duration = await _materialize(
                            client, headers, str(receipt["receipt_id"])
                        )
                        timings.append(duration)
                        cold_timings.append(duration)
                        materialized[key] = payload

                    source_bundles: dict[str, PredictionEvidenceBundle] = {}
                    verification_outcomes: dict[str, dict[str, Any]] = {}
                    for key, receipt in receipts.items():
                        receipt_id = UUID(str(receipt["receipt_id"]))
                        evidence_id = UUID(
                            str(materialized[key]["evidence"]["evidence_id"])
                        )
                        bundle = await evidence_service.repository.get(evidence_id)
                        _assert(
                            bundle is not None,
                            "persisted evidence bundle was not readable",
                        )
                        source_bundles[key] = bundle
                        oracle = await _oracle_bundle(database, bundle)
                        projection = materialized[key]["evidence"]
                        _assert(
                            projection["receipt_id"] == str(receipt_id),
                            "projection receipt changed",
                        )
                        _assert(
                            projection["horizon"] == receipt["horizon"],
                            "projection horizon changed",
                        )
                        _assert(
                            projection["status"] == receipt["status"],
                            "projection status changed",
                        )
                        _assert(
                            projection["score"] == bundle.prediction.score,
                            "HTTP score differs",
                        )
                        _assert(
                            "source_entity_id" not in json.dumps(projection),
                            "private source IDs leaked",
                        )
                        _assert(
                            "artifact_path" not in json.dumps(projection),
                            "artifact path leaked",
                        )
                        _assert(
                            len(json.dumps(projection).encode("utf-8")) <= 65536,
                            "projection exceeded response cap",
                        )
                        verify_response = await client.post(
                            f"/api/v1/prediction-service/evidence/{evidence_id}/verify",
                            json={},
                            headers=headers,
                        )
                        _assert(
                            verify_response.status_code == 200,
                            f"verification HTTP path returned {verify_response.status_code}: "
                            f"{verify_response.text[:300]}",
                        )
                        verification = verify_response.json()
                        verification_outcomes[key] = {
                            "integrity": verification["integrity"],
                            "reason_codes": verification.get("reason_codes", []),
                        }
                        _assert(
                            verification["integrity"]
                            in {
                                EvidenceIntegrity.VERIFIED.value,
                                EvidenceIntegrity.VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE.value,
                            },
                            f"independent source verification failed for {key}: "
                            f"integrity={verification.get('integrity')}, "
                            f"reasons={verification.get('reason_codes')}",
                        )
                        receipt_projection = await client.get(
                            f"/api/v1/prediction-service/runs/{receipt_id}/evidence",
                            headers=headers,
                        )
                        _assert(
                            receipt_projection.status_code == 200,
                            "receipt evidence GET failed",
                        )
                        _assert(
                            receipt_projection.json()["evidence_id"]
                            == str(evidence_id),
                            "receipt lookup returned different evidence",
                        )
                        expected_nodes = oracle["expected_nodes"]
                        _assert(
                            len(bundle.nodes) <= 32, "graph exceeded source node limit"
                        )
                        _assert(len(bundle.edges) <= 64, "graph exceeded edge limit")
                        _assert(len(bundle.facts) <= 48, "graph exceeded fact limit")
                        if key in {task.value for task in MLTask}:
                            report["supervised"][key] = {
                                "receipt_id": str(receipt_id),
                                "evidence_id": str(evidence_id),
                                "feature_set_id": str(
                                    expected_nodes[SourceKind.FEATURE_SET]
                                ),
                                "model_version_id": str(
                                    expected_nodes[SourceKind.MODEL_VERSION]
                                ),
                                "status": receipt["status"],
                                "completeness": bundle.completeness.value,
                                "integrity": bundle.integrity.value,
                                "gap_codes": sorted(
                                    {gap.code.value for gap in bundle.gaps}
                                ),
                                "score": receipt["engineering_validation_score"],
                                "threshold": receipt["threshold"],
                                "decision": receipt["decision"],
                                "node_count": len(bundle.nodes),
                                "edge_count": len(bundle.edges),
                                "fact_count": len(bundle.facts),
                                "lineage_equal": True,
                            }
                        elif key == "correlation:next_pull":
                            supervised_bundle = bundle
                            anomaly_bundle = source_bundles["anomaly:performance"]
                            supervised_feature = next(
                                node.source_entity_id
                                for node in supervised_bundle.nodes
                                if node.source_kind is SourceKind.FEATURE_SET
                            )
                            anomaly_feature = next(
                                node.source_entity_id
                                for node in anomaly_bundle.nodes
                                if node.source_kind is SourceKind.FEATURE_SET
                            )
                            supervised_receipts = [
                                node
                                for node in supervised_bundle.nodes
                                if node.source_kind is SourceKind.PREDICTION_RECEIPT
                            ]
                            anomaly_receipts = [
                                node
                                for node in anomaly_bundle.nodes
                                if node.source_kind is SourceKind.PREDICTION_RECEIPT
                            ]
                            _assert(
                                supervised_feature == anomaly_feature,
                                "same-pull 9B and 9C evidence did not share its FeatureSet",
                            )
                            _assert(
                                len(supervised_receipts) == len(anomaly_receipts) == 1
                                and supervised_receipts[0].source_entity_id
                                == UUID(str(receipt["receipt_id"]))
                                and anomaly_receipts[0].source_entity_id
                                == UUID(
                                    str(receipts["anomaly:performance"]["receipt_id"])
                                )
                                and supervised_bundle.evidence_id
                                != anomaly_bundle.evidence_id,
                                "same-pull 9B/9C outputs were conflated",
                            )
                            _assert(
                                not any(
                                    node.source_kind
                                    in {
                                        SourceKind.DETECTOR_VERSION,
                                        SourceKind.ANOMALY_FINDING,
                                        SourceKind.ANOMALY_RUN,
                                    }
                                    for node in supervised_bundle.nodes
                                )
                                and not any(
                                    node.source_kind is SourceKind.MODEL_VERSION
                                    for node in anomaly_bundle.nodes
                                ),
                                "9B and 9C source families crossed evidence boundaries",
                            )
                            _assert(
                                all(
                                    claim.scope.result_type.value == "next_pull"
                                    and claim.scope.horizon.value == "NEXT_PULL"
                                    for claim in supervised_bundle.claims
                                )
                                and all(
                                    claim.scope.result_type.value == "anomaly"
                                    and claim.scope.horizon.value
                                    == "AFTER_PULL_OFFLINE"
                                    for claim in anomaly_bundle.claims
                                ),
                                "9B/9C claims crossed result or horizon scope",
                            )
                            _assert(
                                supervised_bundle.prediction.score
                                == receipt["engineering_validation_score"]
                                and anomaly_bundle.prediction.score
                                == receipts["anomaly:performance"]["anomaly_score"],
                                "correlated sources replaced their independent scores",
                            )
                            report["correlated_sources"] = {
                                "same_pull_id": str(anomaly_pull.pull_id),
                                "shared_feature_set_id": str(supervised_feature),
                                "next_pull_receipt_id": str(
                                    supervised_bundle.receipt_id
                                ),
                                "anomaly_receipt_id": str(anomaly_bundle.receipt_id),
                                "next_pull_evidence_id": str(
                                    supervised_bundle.evidence_id
                                ),
                                "anomaly_evidence_id": str(anomaly_bundle.evidence_id),
                                "next_pull_prediction_status": (
                                    supervised_bundle.prediction.status
                                ),
                                "next_pull_score": supervised_bundle.prediction.score,
                                "next_pull_threshold": (
                                    supervised_bundle.prediction.threshold
                                ),
                                "next_pull_decision": (
                                    supervised_bundle.prediction.decision
                                ),
                                "next_pull_model_version_id": str(
                                    next(
                                        node.source_entity_id
                                        for node in supervised_bundle.nodes
                                        if node.source_kind is SourceKind.MODEL_VERSION
                                    )
                                ),
                                "next_pull_completeness": (
                                    supervised_bundle.completeness.value
                                ),
                                "next_pull_integrity": (
                                    supervised_bundle.integrity.value
                                ),
                                "anomaly_prediction_status": (
                                    anomaly_bundle.prediction.status
                                ),
                                "anomaly_score": anomaly_bundle.prediction.score,
                                "anomaly_threshold": (
                                    anomaly_bundle.prediction.threshold
                                ),
                                "anomaly_decision": anomaly_bundle.prediction.decision,
                                "anomaly_detector_version_id": str(
                                    next(
                                        node.source_entity_id
                                        for node in anomaly_bundle.nodes
                                        if node.source_kind
                                        is SourceKind.DETECTOR_VERSION
                                    )
                                ),
                                "anomaly_finding_id": str(
                                    next(
                                        node.source_entity_id
                                        for node in anomaly_bundle.nodes
                                        if node.source_kind
                                        is SourceKind.ANOMALY_FINDING
                                    )
                                ),
                                "anomaly_run_id": str(
                                    next(
                                        node.source_entity_id
                                        for node in anomaly_bundle.nodes
                                        if node.source_kind is SourceKind.ANOMALY_RUN
                                    )
                                ),
                                "anomaly_reference_dataset_id": str(
                                    next(
                                        node.source_entity_id
                                        for node in anomaly_bundle.nodes
                                        if node.source_kind
                                        is SourceKind.REFERENCE_DATASET
                                    )
                                ),
                                "anomaly_completeness": (
                                    anomaly_bundle.completeness.value
                                ),
                                "anomaly_integrity": anomaly_bundle.integrity.value,
                                "distinct_receipts_and_bundles": True,
                                "claim_scopes_separate": True,
                                "scores_kept_separate": True,
                            }
                        elif key.startswith("anomaly:"):
                            family = key.split(":", 1)[1]
                            report["anomaly_families"][family] = {
                                "receipt_id": str(receipt_id),
                                "evidence_id": str(evidence_id),
                                "detector_version_id": str(
                                    expected_nodes.get(SourceKind.DETECTOR_VERSION)
                                ),
                                "finding_id": str(
                                    expected_nodes.get(SourceKind.ANOMALY_FINDING)
                                ),
                                "run_id": str(
                                    expected_nodes.get(SourceKind.ANOMALY_RUN)
                                ),
                                "reference_dataset_id": str(
                                    expected_nodes.get(SourceKind.REFERENCE_DATASET)
                                ),
                                "feature_set_id": str(
                                    expected_nodes[SourceKind.FEATURE_SET]
                                ),
                                "status": receipt["status"],
                                "completeness": bundle.completeness.value,
                                "integrity": bundle.integrity.value,
                                "gap_codes": sorted(
                                    {gap.code.value for gap in bundle.gaps}
                                ),
                                "score": receipt["anomaly_score"],
                                "threshold": receipt["threshold"],
                                "decision": receipt["decision"],
                                "node_count": len(bundle.nodes),
                                "edge_count": len(bundle.edges),
                                "fact_count": len(bundle.facts),
                                "lineage_equal": True,
                            }
                        else:
                            report["abstentions"][key] = {
                                "receipt_id": str(receipt_id),
                                "evidence_id": str(evidence_id),
                                "status": receipt["status"],
                                "reason_code": receipt["reason_code"],
                                "integrity": bundle.integrity.value,
                                "completeness": bundle.completeness.value,
                                "gap_codes": [gap.code.value for gap in bundle.gaps],
                                "has_feature_set": bundle.source_summary.feature_set_available,
                            }
                            _assert(
                                bundle.prediction.score is None,
                                "abstention was upgraded to a score",
                            )

                    report["bundle_outcomes"] = _summarize_bundle_outcomes(
                        source_bundles, verification_outcomes
                    )
                    _assert(
                        report["bundle_outcomes"]["receipt_count"] == len(receipts),
                        "bundle outcome summary omitted a source receipt",
                    )
                    _assert(
                        set(verification_outcomes) == set(source_bundles),
                        "verification summary omitted a source receipt",
                    )
                    _assert(
                        sum(report["bundle_outcomes"]["completeness_counts"].values())
                        == len(receipts),
                        "bundle completeness summary does not cover every receipt",
                    )

                    target_measurement_count = await _row(
                        database,
                        "SELECT count(*)::integer AS measurement_count "
                        "FROM telemetry_samples ts JOIN pulls p ON p.session_id=ts.session_id "
                        "WHERE p.id=:pull AND ts.observed_at>:cutoff "
                        "AND ts.observed_at BETWEEN p.started_at AND p.ended_at",
                        {
                            "pull": UUID(str(future_target["target_pull_id"])),
                            "cutoff": cutoff,
                        },
                    )
                    supervised_bundles = [source_bundles[task.value] for task in MLTask]
                    target_pull_id = str(future_target["target_pull_id"])
                    target_feature_set_id = str(future_target["target_feature_set_id"])
                    target_ids_absent = all(
                        target_pull_id
                        not in json.dumps(item.model_dump(mode="json"), sort_keys=True)
                        and target_feature_set_id
                        not in json.dumps(item.model_dump(mode="json"), sort_keys=True)
                        for item in supervised_bundles
                    )
                    _assert(
                        int(target_measurement_count["measurement_count"]) > 0,
                        "future target pull has no observed measurements after the 9B cutoff",
                    )
                    _assert(
                        target_ids_absent,
                        "future target identity leaked into 9B evidence",
                    )
                    correlated_serialization = json.dumps(
                        source_bundles["correlation:next_pull"].model_dump(mode="json"),
                        sort_keys=True,
                    ) + json.dumps(
                        source_bundles["anomaly:performance"].model_dump(mode="json"),
                        sort_keys=True,
                    )
                    _assert(
                        late_records["sample_id"] not in correlated_serialization
                        and late_records["modification_id"]
                        not in correlated_serialization,
                        "post-cutoff telemetry or modification entered same-pull evidence",
                    )
                    report["cutoff_sentinel"] = {
                        "supervised_input_cutoff": cutoff.isoformat(),
                        "future_target_started_at": future_target[
                            "target_started_at"
                        ].isoformat(),
                        "target_starts_after_cutoff": True,
                        "future_target_measurements_after_cutoff": int(
                            target_measurement_count["measurement_count"]
                        ),
                        "future_target_pull_and_feature_set_absent_from_9b_evidence": True,
                        "late_sample_id": late_records["sample_id"],
                        "late_sample_observed_at": late_records[
                            "observed_at"
                        ].isoformat(),
                        "late_sample_ingested_at": late_records[
                            "ingested_at"
                        ].isoformat(),
                        "late_modification_id": late_records["modification_id"],
                        "late_modification_created_at": late_records[
                            "modification_created_at"
                        ].isoformat(),
                        "late_sources_absent_from_same_pull_evidence": True,
                        "frozen_feature_set_values_and_hashes_unchanged": True,
                        "all_computed_features_at_or_before_each_cutoff": True,
                    }

                    # Idempotent sequential replay after all records exist.
                    replay_payload, replay_duration = await _materialize(
                        client,
                        headers,
                        str(receipts[MLTask.THERMAL_DEGRADATION.value]["receipt_id"]),
                    )
                    timings.append(replay_duration)
                    warm_timings.append(replay_duration)
                    _assert(
                        replay_payload["evidence"]["evidence_id"]
                        == materialized[MLTask.THERMAL_DEGRADATION.value]["evidence"][
                            "evidence_id"
                        ],
                        "sequential replay changed the evidence ID",
                    )
                    _assert(
                        not replay_payload["materialized"],
                        "sequential replay inserted a second bundle",
                    )

                    timeout_before = evidence_service.timeout_seconds
                    try:
                        evidence_service.timeout_seconds = 0.01
                        with patch.object(
                            evidence_service.repository,
                            "source_snapshot",
                            new=AsyncMock(side_effect=TimeoutError()),
                        ):
                            timeout_response = await client.post(
                                f"/api/v1/prediction-service/runs/{receipts['no_feature_set']['receipt_id']}/evidence",
                                json={
                                    "schema_version": "phase9e-prediction-evidence-v1"
                                },
                                headers=headers,
                            )
                    finally:
                        evidence_service.timeout_seconds = timeout_before
                    _assert(
                        timeout_response.status_code == 503,
                        "evidence operation timeout did not return its bounded error",
                    )
                    timeout_recovery, recovery_duration = await _materialize(
                        client,
                        headers,
                        str(receipts["no_feature_set"]["receipt_id"]),
                    )
                    _assert(
                        not timeout_recovery["materialized"],
                        "timeout recovery created a duplicate bundle",
                    )
                    timings.append(recovery_duration)
                    warm_timings.append(recovery_duration)
                    existing_count = await _table_count(
                        database,
                        "prediction_evidence_bundles",
                        UUID(materialized["no_feature_set"]["evidence"]["evidence_id"]),
                    )
                    with patch.object(
                        evidence_service.repository,
                        "source_snapshot",
                        new=AsyncMock(
                            side_effect=RuntimeError("private-eval-sentinel")
                        ),
                    ):
                        database_error_response = await client.post(
                            f"/api/v1/prediction-service/runs/{receipts['no_feature_set']['receipt_id']}/evidence",
                            json={"schema_version": "phase9e-prediction-evidence-v1"},
                            headers=headers,
                        )
                    _assert(
                        database_error_response.status_code == 503
                        and "private-eval-sentinel" not in database_error_response.text,
                        "database failure was not sanitized",
                    )
                    count_after_database_error = await _table_count(
                        database,
                        "prediction_evidence_bundles",
                        UUID(materialized["no_feature_set"]["evidence"]["evidence_id"]),
                    )
                    _assert(
                        existing_count == count_after_database_error == 1,
                        "failed evidence build changed persisted bundle count",
                    )
                    report["integrity_controls"]["budget_and_db_outage"] = {
                        "timeout": "503; semaphore recovered",
                        "database_outage": "503 sanitized; no partial bundle",
                    }

                    wrong_vehicle = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(pull_id),
                            "vehicle_id": str(no_feature_pull.vehicle_id),
                            "observation_cutoff": datetime.now(UTC).isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.THERMAL_DEGRADATION.value,
                        },
                        headers=headers,
                    )
                    _assert(
                        wrong_vehicle.status_code == 404,
                        "wrong-vehicle request did not preserve 9D scope hiding",
                    )
                    guessed = await client.get(
                        "/api/v1/prediction-service/evidence/00000000-0000-0000-0000-000000000001",
                        headers=headers,
                    )
                    _assert(
                        guessed.status_code == 404,
                        "unknown evidence identifier was enumerable",
                    )
                    report["auth_and_scope"].update(
                        {"wrong_vehicle": "404 hidden", "unknown_evidence_id": "404"}
                    )

                    # Revoke a serving binding after receipt creation; historical evidence remains readable.
                    historical_receipt = receipts[MLTask.PERFORMANCE_DEGRADATION.value]
                    historical_evidence = materialized[
                        MLTask.PERFORMANCE_DEGRADATION.value
                    ]["evidence"]["evidence_id"]
                    await prediction_service.transition(
                        bindings[MLTask.PERFORMANCE_DEGRADATION.value],
                        "revoke",
                        reason="Revoke the serving slot after preserving historical evidence.",
                        operator_id="phase9e-evaluator",
                        environment_confirmation="test",
                    )
                    historical = await client.get(
                        f"/api/v1/prediction-service/evidence/{historical_evidence}",
                        headers=headers,
                    )
                    _assert(
                        historical.status_code == 200, "revoke hid historical evidence"
                    )
                    report["auth_and_scope"]["revoked_historical_read"] = "200"

                    # Feature mutation is confined to the disposable database and always restored.
                    tamper_bundle = source_bundles[MLTask.THERMAL_DEGRADATION.value]
                    feature_node = next(
                        node
                        for node in tamper_bundle.nodes
                        if node.source_kind is SourceKind.FEATURE_SET
                    )
                    original_feature = await _row(
                        database,
                        "SELECT feature_values FROM feature_sets WHERE id=:id",
                        {"id": feature_node.source_entity_id},
                    )
                    original_values = copy.deepcopy(original_feature["feature_values"])
                    mutated_values = copy.deepcopy(original_values)
                    first_key = min(
                        key
                        for key, value in mutated_values.items()
                        if isinstance(value, dict)
                    )
                    mutated_values[first_key]["value"] = 999999.0
                    try:
                        await _mutate_feature_for_verification(
                            database, feature_node.source_entity_id, mutated_values
                        )
                        tamper_verify = await client.post(
                            f"/api/v1/prediction-service/evidence/{tamper_bundle.evidence_id}/verify",
                            json={},
                            headers=headers,
                        )
                        _assert(
                            tamper_verify.status_code == 200,
                            "tamper verification request failed",
                        )
                        _assert(
                            tamper_verify.json()["integrity"]
                            == EvidenceIntegrity.FAILED_SOURCE_MISMATCH.value,
                            "changed 9A source value was verified",
                        )
                    finally:
                        await _mutate_feature_for_verification(
                            database, feature_node.source_entity_id, original_values
                        )
                    restored_verify = await client.post(
                        f"/api/v1/prediction-service/evidence/{tamper_bundle.evidence_id}/verify",
                        json={},
                        headers=headers,
                    )
                    _assert(
                        restored_verify.status_code == 200
                        and restored_verify.json()["integrity"]
                        == EvidenceIntegrity.VERIFIED.value,
                        "source restore did not recover historical verification",
                    )
                    report["integrity_controls"]["feature_value_tamper"] = (
                        "FAILED_SOURCE_MISMATCH"
                    )

                    anomaly_bundle = next(
                        bundle
                        for name, bundle in source_bundles.items()
                        if name.startswith("anomaly:")
                        and bundle.prediction.status
                        == PredictionStatus.READY_SCORE.value
                        and any(
                            node.source_kind is SourceKind.ANOMALY_FINDING
                            for node in bundle.nodes
                        )
                    )
                    finding_node = next(
                        node
                        for node in anomaly_bundle.nodes
                        if node.source_kind is SourceKind.ANOMALY_FINDING
                    )
                    original_finding = await _row(
                        database,
                        "SELECT score FROM anomaly_findings WHERE id=:id",
                        {"id": finding_node.source_entity_id},
                    )
                    original_finding_score = float(original_finding["score"])
                    try:
                        await _mutate_finding_for_verification(
                            database,
                            finding_node.source_entity_id,
                            original_finding_score + 10.0,
                        )
                        finding_tamper_verify = await client.post(
                            f"/api/v1/prediction-service/evidence/{anomaly_bundle.evidence_id}/verify",
                            json={},
                            headers=headers,
                        )
                        _assert(
                            finding_tamper_verify.status_code == 200
                            and finding_tamper_verify.json()["integrity"]
                            == EvidenceIntegrity.FAILED_SOURCE_MISMATCH.value,
                            "changed 9C finding source was verified",
                        )
                    finally:
                        await _mutate_finding_for_verification(
                            database,
                            finding_node.source_entity_id,
                            original_finding_score,
                        )
                    finding_restored = await client.post(
                        f"/api/v1/prediction-service/evidence/{anomaly_bundle.evidence_id}/verify",
                        json={},
                        headers=headers,
                    )
                    _assert(
                        finding_restored.status_code == 200
                        and finding_restored.json()["integrity"]
                        == EvidenceIntegrity.VERIFIED.value,
                        "9C finding restore did not recover verification",
                    )
                    report["integrity_controls"]["finding_value_tamper"] = (
                        "FAILED_SOURCE_MISMATCH"
                    )

                    # Artifact corruption is detected by hash only; no joblib payload is loaded.
                    receipt_row = await _row(
                        database,
                        "SELECT artifact_path,artifact_checksum FROM ml_model_versions WHERE id=:id",
                        {
                            "id": UUID(
                                str(
                                    receipts[MLTask.THERMAL_DEGRADATION.value][
                                        "model_version_id"
                                    ]
                                )
                            )
                        },
                    )
                    artifact_path = model_store._checked_path(
                        Path(receipt_row["artifact_path"])
                    )
                    artifact_bytes = artifact_path.read_bytes()
                    _assert(
                        len(artifact_bytes) <= 50 * 1024 * 1024,
                        "artifact exceeded hash check limit",
                    )
                    try:
                        artifact_path.write_bytes(
                            artifact_bytes[:-1] + bytes([artifact_bytes[-1] ^ 1])
                        )
                        artifact_verify = await client.post(
                            f"/api/v1/prediction-service/evidence/{source_bundles[MLTask.THERMAL_DEGRADATION.value].evidence_id}/verify",
                            json={},
                            headers=headers,
                        )
                        _assert(
                            artifact_verify.status_code == 200,
                            "artifact verification request failed",
                        )
                        _assert(
                            artifact_verify.json()["integrity"]
                            == EvidenceIntegrity.FAILED_SOURCE_MISMATCH.value,
                            "artifact byte tamper was not detected",
                        )
                    finally:
                        artifact_path.write_bytes(artifact_bytes)
                    report["integrity_controls"]["artifact_byte_tamper"] = (
                        "FAILED_SOURCE_MISMATCH"
                    )

                    detector_row = await _row(
                        database,
                        "SELECT artifact_path FROM anomaly_detector_versions WHERE id=:id",
                        {
                            "id": next(
                                node.source_entity_id
                                for node in anomaly_bundle.nodes
                                if node.source_kind is SourceKind.DETECTOR_VERSION
                            )
                        },
                    )
                    detector_path = anomaly_store._checked_path(
                        Path(detector_row["artifact_path"])
                    )
                    detector_bytes = detector_path.read_bytes()
                    try:
                        detector_path.write_bytes(
                            detector_bytes[:-1] + bytes([detector_bytes[-1] ^ 1])
                        )
                        detector_tamper_verify = await client.post(
                            f"/api/v1/prediction-service/evidence/{anomaly_bundle.evidence_id}/verify",
                            json={},
                            headers=headers,
                        )
                        _assert(
                            detector_tamper_verify.status_code == 200
                            and detector_tamper_verify.json()["integrity"]
                            == EvidenceIntegrity.FAILED_SOURCE_MISMATCH.value,
                            "9C detector artifact byte tamper was not detected",
                        )
                    finally:
                        detector_path.write_bytes(detector_bytes)
                    report["integrity_controls"]["detector_artifact_byte_tamper"] = (
                        "FAILED_SOURCE_MISMATCH"
                    )

                    model_artifact_bytes = artifact_path.read_bytes()
                    try:
                        artifact_path.unlink()
                        unavailable_verify = await client.post(
                            f"/api/v1/prediction-service/evidence/{source_bundles[MLTask.THERMAL_DEGRADATION.value].evidence_id}/verify",
                            json={},
                            headers=headers,
                        )
                        _assert(
                            unavailable_verify.status_code == 200
                            and unavailable_verify.json()["integrity"]
                            == EvidenceIntegrity.VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE.value,
                            "missing artifact was misreported as verified or source corruption",
                        )
                    finally:
                        artifact_path.write_bytes(model_artifact_bytes)
                    artifact_restored = await client.post(
                        f"/api/v1/prediction-service/evidence/{source_bundles[MLTask.THERMAL_DEGRADATION.value].evidence_id}/verify",
                        json={},
                        headers=headers,
                    )
                    _assert(
                        artifact_restored.status_code == 200
                        and artifact_restored.json()["integrity"]
                        == EvidenceIntegrity.VERIFIED.value,
                        "model artifact restore did not recover verification",
                    )
                    report["integrity_controls"]["missing_artifact"] = (
                        "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE"
                    )

                    audit_evidence_id = UUID(
                        materialized["no_feature_set"]["evidence"]["evidence_id"]
                    )
                    for _ in range(31):
                        audit_response = await client.post(
                            f"/api/v1/prediction-service/evidence/{audit_evidence_id}/verify",
                            json={},
                            headers=headers,
                        )
                        _assert(
                            audit_response.status_code == 200,
                            "verification audit budget ended before its configured limit",
                        )
                    exhausted_audit = await client.post(
                        f"/api/v1/prediction-service/evidence/{audit_evidence_id}/verify",
                        json={},
                        headers=headers,
                    )
                    _assert(
                        exhausted_audit.status_code == 429,
                        "verification audit cap did not reject its 33rd write",
                    )
                    _assert(
                        await _table_count(
                            database,
                            "prediction_evidence_verification_audits",
                            audit_evidence_id,
                        )
                        == 32,
                        "verification audit table exceeded its configured record limit",
                    )
                    report["integrity_controls"]["verification_audit_cap"] = {
                        "appended": 32,
                        "33rd_write": "429",
                    }

                    # Database triggers reject updates/deletes of immutable bundle and child rows.
                    immutable_bundle = source_bundles["no_feature_set"]
                    evidence_id = immutable_bundle.evidence_id
                    immutability: dict[str, str] = {}
                    immutable_tables = (
                        "prediction_evidence_bundles",
                        "prediction_evidence_sources",
                        "prediction_evidence_nodes",
                        "prediction_evidence_edges",
                        "prediction_evidence_facts",
                        "prediction_evidence_gaps",
                        "prediction_evidence_verification_audits",
                    )
                    _assert(
                        bool(immutable_bundle.gaps),
                        "immutability fixture has no gap row",
                    )
                    for table in immutable_tables:
                        key = (
                            "id"
                            if table == "prediction_evidence_bundles"
                            else "evidence_id"
                        )
                        async with database.session() as db:
                            try:
                                async with db.begin():
                                    await db.execute(
                                        text(
                                            f"UPDATE {table} SET {key}={key} WHERE {key}=:id"
                                        ),
                                        {"id": evidence_id},
                                    )
                            except DBAPIError as error:
                                sqlstate = _sqlstate(error)
                                _assert(
                                    sqlstate == "P0001",
                                    f"{table} update was rejected outside the immutability trigger",
                                )
                                immutability[f"{table}_update"] = "TRIGGER_REJECTED"
                        async with database.session() as db:
                            try:
                                async with db.begin():
                                    await db.execute(
                                        text(f"DELETE FROM {table} WHERE {key}=:id"),
                                        {"id": evidence_id},
                                    )
                            except DBAPIError as error:
                                sqlstate = _sqlstate(error)
                                _assert(
                                    sqlstate == "P0001",
                                    f"{table} delete was rejected outside the immutability trigger",
                                )
                                immutability[f"{table}_delete"] = "TRIGGER_REJECTED"
                    _assert(
                        len(immutability) == len(immutable_tables) * 2,
                        "database immutability trigger did not reject every mutation",
                    )
                    report["integrity_controls"]["database_immutability"] = immutability

                    constraint_checks: dict[str, str] = {}
                    try:
                        await _insert_probe_bundle(
                            database,
                            evidence_id=UUID(int=1),
                            receipt_id=immutable_bundle.receipt_id,
                            schema_version="phase9e-conflict-probe",
                            logical_fingerprint=immutable_bundle.logical_fingerprint,
                            bundle_body={"deliberately_conflicting": True},
                        )
                    except IntegrityError as error:
                        _assert(
                            _sqlstate(error) == "23505",
                            "duplicate identity hit an unexpected constraint",
                        )
                        constraint_checks["duplicate_logical_fingerprint"] = "REJECTED"
                    else:
                        raise AssertionError(
                            "duplicate logical fingerprint was inserted"
                        )
                    try:
                        await _insert_probe_bundle(
                            database,
                            evidence_id=UUID(int=2),
                            receipt_id=immutable_bundle.receipt_id,
                            schema_version="phase9e-size-probe",
                            logical_fingerprint="d" * 64,
                            bundle_body={"padding": "x" * 66_000},
                        )
                    except IntegrityError as error:
                        _assert(
                            _sqlstate(error) == "23514",
                            "oversized manifest hit an unexpected constraint",
                        )
                        constraint_checks["oversized_jsonb"] = "REJECTED"
                    else:
                        raise AssertionError("oversized JSONB manifest was inserted")
                    orphan_evidence_id = UUID(int=3)
                    try:
                        async with database.session() as db, db.begin():
                            await db.execute(
                                text(
                                    "INSERT INTO prediction_evidence_sources "
                                    "(evidence_id,source_kind,source_entity_id,source_checksum) "
                                    "VALUES(:evidence,'prediction_receipt',:source,:checksum)"
                                ),
                                {
                                    "evidence": orphan_evidence_id,
                                    "source": UUID(int=4),
                                    "checksum": "a" * 64,
                                },
                            )
                    except IntegrityError as error:
                        _assert(
                            _sqlstate(error) == "23503",
                            "orphan source hit an unexpected constraint",
                        )
                        constraint_checks["orphan_source_reference"] = "REJECTED"
                    else:
                        raise AssertionError("orphan source reference was inserted")
                    rollback_id = UUID(int=5)
                    try:
                        async with database.session() as db, db.begin():
                            await db.execute(
                                text(
                                    "INSERT INTO prediction_evidence_bundles "
                                    "(id,receipt_id,schema_version,projection_version,verifier_policy_version,"
                                    "logical_fingerprint,content_checksum,provenance_manifest_checksum,result_type,"
                                    "horizon,source_role,effective_cutoff,completeness,integrity,bundle_body) "
                                    "VALUES(:id,:receipt,'phase9e-rollback-probe','projection','verifier',"
                                    ":logical,:content,:manifest,'next_pull','NEXT_PULL','synthetic',:cutoff,"
                                    "'PARTIAL','NOT_VERIFIABLE','{}'::jsonb)"
                                ),
                                {
                                    "id": rollback_id,
                                    "receipt": immutable_bundle.receipt_id,
                                    "logical": "e" * 64,
                                    "content": "f" * 64,
                                    "manifest": "1" * 64,
                                    "cutoff": datetime.now(UTC),
                                },
                            )
                            await db.execute(
                                text(
                                    "INSERT INTO prediction_evidence_sources "
                                    "(evidence_id,source_kind,source_entity_id,source_checksum) "
                                    "VALUES(:evidence,'prediction_receipt',:source,:checksum)"
                                ),
                                {
                                    "evidence": rollback_id,
                                    "source": immutable_bundle.receipt_id,
                                    "checksum": "a" * 64,
                                },
                            )
                            await db.execute(
                                text(
                                    "INSERT INTO prediction_evidence_nodes "
                                    "(evidence_id,node_id,source_kind,source_entity_id,node_type,trust_role,projection_class) "
                                    "VALUES(:evidence,'bad','model_version',:source,'MODEL_VERSION',"
                                    "'VERSIONED_SOURCE','INTERNAL_LINEAGE')"
                                ),
                                {"evidence": rollback_id, "source": UUID(int=6)},
                            )
                    except IntegrityError as error:
                        _assert(
                            _sqlstate(error) == "23503",
                            "interrupted insert hit an unexpected constraint",
                        )
                        constraint_checks["interrupted_transaction"] = "ROLLED_BACK"
                    else:
                        raise AssertionError(
                            "invalid graph insert unexpectedly committed"
                        )
                    rollback_count = await _table_count(
                        database, "prediction_evidence_bundles", rollback_id
                    )
                    _assert(
                        rollback_count == 0, "failed child insert left a partial bundle"
                    )
                    report["integrity_controls"]["database_constraints"] = (
                        constraint_checks
                    )

                    # Keep the shared 9C evidence pristine while the Phase 9F agent reads it.
                    missing_context = await _pull_context(
                        database, UUID(str(targets["missing_fuel"]["id"]))
                    )
                    low_quality_context = await _pull_context(
                        database, UUID(str(targets["low_quality"]["id"]))
                    )
                    no_feature_context = await _pull_context(
                        database, UUID(str(no_feature_pull.pull_id))
                    )
                    report["phase9f"] = await phase9f.evaluate(
                        settings=settings,
                        telemetry=app.state.telemetry,
                        model_artifacts=model_store,
                        anomaly_artifacts=anomaly_store,
                        source_bundles=source_bundles,
                        source_contexts={
                            "supervised": {
                                "vehicle_id": UUID(str(eligible["vehicle_id"])),
                                "session_id": UUID(str(eligible["session_id"])),
                                "pull_id": pull_id,
                                "configuration_id": UUID(
                                    str(eligible["configuration_id"])
                                ),
                            },
                            "anomaly": {
                                "vehicle_id": UUID(str(anomaly_pull.vehicle_id)),
                                "session_id": UUID(str(anomaly_pull.session_id)),
                                "pull_id": UUID(str(anomaly_pull.pull_id)),
                                "configuration_id": UUID(
                                    str(anomaly_pull.configuration_id)
                                ),
                            },
                            "missing_fuel": missing_context,
                            "low_quality": low_quality_context,
                            "no_feature_set": no_feature_context,
                        },
                        span_exporter=span_exporter,
                        database_sessions_peak=int(
                            helper_connection_counts["maximum"]
                            + api_connection_counts["maximum"]
                        ),
                    )

                    performance_bundle = source_bundles["anomaly:performance"]
                    performance_detector_id = next(
                        node.source_entity_id
                        for node in performance_bundle.nodes
                        if node.source_kind is SourceKind.DETECTOR_VERSION
                    )
                    frozen_reference = await _row(
                        database,
                        "SELECT d.family,d.method,rd.id AS reference_id,rd.row_count,"
                        "rd.observation_cutoff AS reference_cutoff "
                        "FROM anomaly_detector_versions dv "
                        "JOIN anomaly_detector_definitions d ON d.id=dv.detector_definition_id "
                        "JOIN anomaly_reference_datasets rd ON rd.id=dv.reference_dataset_id "
                        "WHERE dv.id=:id",
                        {"id": performance_detector_id},
                    )
                    reference_definition = detector_definition(
                        frozen_reference["family"], frozen_reference["method"]
                    )
                    performance_cutoff = datetime.fromisoformat(
                        receipts["anomaly:performance"]["requested_cutoff"].replace(
                            "Z", "+00:00"
                        )
                    )
                    late_reference_cutoff = max(
                        datetime.now(UTC),
                        performance_cutoff,
                        frozen_reference["reference_cutoff"],
                    ) + timedelta(seconds=1)
                    late_reference_row = None
                    for candidate in (
                        pull
                        for session_pulls in primary.pulls_by_session
                        for pull in session_pulls
                    ):
                        candidate_rows = await prediction_service.anomaly_service.repository.load_targets(
                            (candidate.pull_id,),
                            late_reference_cutoff,
                            reference_definition,
                        )
                        if not candidate_rows:
                            continue
                        already_frozen = await _row(
                            database,
                            "SELECT count(*)::integer AS row_count "
                            "FROM anomaly_reference_rows "
                            "WHERE reference_dataset_id=:reference AND feature_set_id=:feature_set",
                            {
                                "reference": frozen_reference["reference_id"],
                                "feature_set": candidate_rows[0].feature_set_id,
                            },
                        )
                        if int(already_frozen["row_count"]) == 0:
                            late_reference_row = candidate_rows[0]
                            break
                    if late_reference_row is None:
                        raise AssertionError(
                            "no valid 9A source row is available for the post-cutoff 9C sentinel"
                        )
                    late_reference_row = replace(
                        late_reference_row,
                        row_id=sha256(
                            {
                                "sentinel": "phase9e-postcutoff-reference-row",
                                "reference": str(frozen_reference["reference_id"]),
                                "feature_set": str(late_reference_row.feature_set_id),
                            }
                        ),
                        observation_cutoff=late_reference_cutoff,
                    )
                    reference_params = _reference_row_parameters(
                        frozen_reference["reference_id"],
                        late_reference_row,
                        reference_definition,
                    )
                    async with database.session() as db:
                        await db.execute(
                            text(
                                "INSERT INTO anomaly_reference_rows(reference_dataset_id,row_id,feature_set_id,"
                                "vehicle_id,configuration_id,session_id,pull_id,pull_started_at,pull_ended_at,"
                                "observation_cutoff,source_role,source_type,source_hash,provenance_hash,"
                                "modification_ids,available_signals,feature_values,feature_quality,"
                                "feature_missing,feature_availability,quality_metadata) VALUES(:reference,:row_id,"
                                ":feature_set,:vehicle,:configuration,:session,:pull,:started,:ended,:cutoff,:role,"
                                ":source_type,:source_hash,:provenance_hash,CAST(:modifications AS jsonb),"
                                "CAST(:signals AS jsonb),CAST(:values AS jsonb),CAST(:quality AS jsonb),"
                                "CAST(:missing AS jsonb),CAST(:availability AS jsonb),CAST(:metadata AS jsonb))"
                            ),
                            reference_params,
                        )
                        await db.commit()
                    post_cutoff_reference_verify = await client.post(
                        f"/api/v1/prediction-service/evidence/{performance_bundle.evidence_id}/verify",
                        json={},
                        headers=headers,
                    )
                    post_cutoff_result = post_cutoff_reference_verify.json()
                    _assert(
                        post_cutoff_reference_verify.status_code == 200
                        and post_cutoff_result["integrity"]
                        == EvidenceIntegrity.FAILED_SOURCE_MISMATCH.value
                        and "PROVENANCE_MISMATCH" in post_cutoff_result["reason_codes"],
                        "post-cutoff 9C reference-row insertion was not detected",
                    )
                    report["integrity_controls"]["post_cutoff_reference_row"] = {
                        "inserted_reference_row_id": late_reference_row.row_id,
                        "inserted_feature_set_id": str(
                            late_reference_row.feature_set_id
                        ),
                        "inserted_observation_cutoff": late_reference_cutoff.isoformat(),
                        "frozen_reference_row_count": int(
                            frozen_reference["row_count"]
                        ),
                        "verification_integrity": post_cutoff_result["integrity"],
                        "reason_code": "PROVENANCE_MISMATCH",
                    }

                    row_counts = {
                        "bundles": await _table_count(
                            database, "prediction_evidence_bundles", evidence_id
                        ),
                        "sources": await _table_count(
                            database, "prediction_evidence_sources", evidence_id
                        ),
                        "nodes": await _table_count(
                            database, "prediction_evidence_nodes", evidence_id
                        ),
                        "edges": await _table_count(
                            database, "prediction_evidence_edges", evidence_id
                        ),
                        "facts": await _table_count(
                            database, "prediction_evidence_facts", evidence_id
                        ),
                        "gaps": await _table_count(
                            database, "prediction_evidence_gaps", evidence_id
                        ),
                        "verification_audits": await _table_count(
                            database,
                            "prediction_evidence_verification_audits",
                            evidence_id,
                        ),
                    }
                    _assert(
                        row_counts["bundles"] == 1,
                        "idempotent build created duplicate bundles",
                    )
                    _assert(
                        row_counts["nodes"] == len(immutable_bundle.nodes),
                        "normalized node rows differ",
                    )
                    report["integrity_controls"]["normalized_row_counts"] = row_counts

                    projection_bytes = [
                        len(
                            json.dumps(
                                item[0]["evidence"], separators=(",", ":")
                            ).encode("utf-8")
                        )
                        for item in concurrent_results
                    ]
                    rss = phase9d._rss_kib()
                    sorted_timings = sorted(timings)
                    report["benchmarks"] = {
                        "sample_count": len(timings),
                        "cold_materialization_elapsed_seconds": cold_timings,
                        "warm_replay_elapsed_seconds": warm_timings,
                        "serial_and_replay_elapsed_seconds": timings,
                        "handler_elapsed_p50_seconds": statistics.median(timings),
                        "handler_elapsed_p95_seconds": sorted_timings[
                            min(
                                len(sorted_timings) - 1, int(len(sorted_timings) * 0.95)
                            )
                        ],
                        "concurrent_10_elapsed_seconds": concurrent_elapsed,
                        "concurrent_10_request_seconds": [
                            item[1] for item in concurrent_results
                        ],
                        "concurrent_100": concurrent_100,
                        "projection_bytes_max": max(projection_bytes),
                        "rss_kib_before_evaluation": rss_start,
                        "rss_kib_after": rss,
                        "rss_kib_delta": (
                            max(0, rss - rss_start)
                            if rss is not None and rss_start is not None
                            else None
                        ),
                        "maximum_database_sessions": helper_connection_counts["maximum"]
                        + api_connection_counts["maximum"],
                        "evidence_bundle_count": len(source_bundles),
                        "replay_identity": next(iter(concurrent_ids)),
                        "cold_warm_latency_sla_claimed": False,
                    }
                    _assert(
                        report["benchmarks"]["maximum_database_sessions"] <= 30,
                        "checked-out DB sessions exceeded the two-engine pool bound",
                    )
                    _assert(
                        set(report["supervised"]) == {task.value for task in MLTask},
                        "not all 9B tasks exercised",
                    )
                    _assert(
                        set(report["anomaly_families"])
                        == set(anomaly_context["versions"]),
                        "not all 9C families exercised",
                    )
                    report["receipt_type_count"] = len(receipts)
                    report["execution_state"] = "PASS"
                    report["status"] = "PASS"
                    report["real_world_accuracy_claimed"] = False
                    report["binding_history"] = {
                        "revoked_binding_receipt": historical_receipt["receipt_id"],
                        "historical_evidence_readable": True,
                    }
                    report["database_counts"] = await phase9d._db_counts(database)
                    metrics_text = app.state.telemetry.render_metrics().decode("utf-8")
                    metric_names = sorted(
                        {
                            line.split()[2]
                            for line in metrics_text.splitlines()
                            if line.startswith("# HELP prediction_evidence_")
                        }
                    )
                    trace_names = sorted(
                        {span.name for span in span_exporter.get_finished_spans()}
                    )
                    required_metrics = {
                        "prediction_evidence_operations_total",
                        "prediction_evidence_duration_seconds",
                        "prediction_evidence_graph_size",
                        "prediction_evidence_replays_total",
                    }
                    required_spans = {
                        "prediction.evidence.source.resolve",
                        "prediction.evidence.claim_construction",
                        "prediction.evidence.canonical_hash",
                        "prediction.evidence.immutable_persist",
                        "prediction.evidence.read_projection",
                        "prediction.evidence.independent_verify",
                        "prediction.evidence.audit_append",
                    }
                    _assert(
                        required_metrics.issubset(metric_names),
                        "evidence metrics were not exported",
                    )
                    _assert(
                        required_spans.issubset(trace_names),
                        "evidence trace spans were not emitted",
                    )
                    protected_ids = {
                        str(vehicle_id),
                        *(str(item["receipt_id"]) for item in receipts.values()),
                        *(str(item.evidence_id) for item in source_bundles.values()),
                    }
                    _assert(
                        not any(
                            identifier in metrics_text for identifier in protected_ids
                        ),
                        "evidence metrics contain a vehicle or evidence identifier",
                    )
                    span_attributes = json.dumps(
                        [
                            dict(span.attributes or {})
                            for span in span_exporter.get_finished_spans()
                        ],
                        sort_keys=True,
                    )
                    _assert(
                        not any(
                            identifier in span_attributes
                            for identifier in protected_ids
                        ),
                        "evidence spans contain a vehicle or evidence identifier",
                    )
                    report["observability"] = {
                        "status": "PASS",
                        "metric_names": metric_names,
                        "trace_names": trace_names,
                        "bounded_labels_only": True,
                        "vehicle_or_evidence_ids_present": False,
                    }
    except Exception as error:  # noqa: BLE001 - convert any evaluator failure into a failed receipt
        report["status"] = "FAIL"
        report["error_category"] = type(error).__name__
        report["failure_message"] = str(error)[:300]
        report["failure_location"] = [
            {
                "file": Path(frame.filename).name,
                "line": frame.lineno,
                "function": frame.name,
            }
            for frame in traceback.extract_tb(error.__traceback__)[-5:]
        ]
    finally:
        shutdown_telemetry_once()
        await database.close()
        report.setdefault("benchmarks", {}).update(
            {
                "evaluator_elapsed_seconds": round(
                    time.perf_counter() - evaluator_wall_started, 6
                ),
                "evaluator_process_cpu_seconds": round(
                    time.process_time() - evaluator_cpu_started, 6
                ),
                "evaluator_cpu_scope": "python process only; child processes excluded",
            }
        )
    return report


async def main() -> None:
    report = await evaluate()
    evidence = Path(".validation/phase9e")
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "acceptance.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    (evidence / "commit.txt").write_text(
        str(report["git_sha"]) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "git_sha": report.get("git_sha"),
                "supervised_tasks": sorted(report.get("supervised", {})),
                "anomaly_families": sorted(report.get("anomaly_families", {})),
                "receipts": report.get("receipt_type_count"),
                "full_report": str(evidence / "acceptance.json"),
            },
            sort_keys=True,
        )
    )
    if report.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
