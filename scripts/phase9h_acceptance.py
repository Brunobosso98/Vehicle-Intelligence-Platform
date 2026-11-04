"""Independent Phase 9H database oracle and no-write acceptance checker."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".validation" / "phase9h"
REPORT_9E = ROOT / ".validation" / "phase9e" / "acceptance.json"
ORACLE = EVIDENCE / "source-oracle.json"
TABLES = (
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
    "prediction_evidence_bundles",
    "prediction_evidence_sources",
    "prediction_evidence_nodes",
    "prediction_evidence_edges",
    "prediction_evidence_facts",
    "prediction_evidence_gaps",
    "prediction_evidence_verification_audits",
    "agent_runs",
    "agent_tool_calls",
    "agent_stream_events",
    "agent_prediction_evidence_links",
    "evaluation_protocols",
    "evaluation_runs",
    "evaluation_metric_reports",
    "evaluation_calibration_candidates",
    "evaluation_applicability_assessments",
)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


async def _digests(database: Database) -> dict[str, str]:
    result: dict[str, str] = {}
    async with database.session() as db, db.begin():
        await db.execute(text("SET TRANSACTION READ ONLY"))
        for table in TABLES:
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
            result[table] = _canonical_hash([str(row) for row in rows])
    return result


def _report_receipts(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    for task, item in report.get("supervised", {}).items():
        expected[str(item["receipt_id"])] = {"kind": "supervised", "task": task, **item}
    for family, item in report.get("anomaly_families", {}).items():
        expected[str(item["receipt_id"])] = {
            "kind": "anomaly",
            "family": family,
            **item,
        }
    for key, item in report.get("abstentions", {}).items():
        expected[str(item["receipt_id"])] = {"kind": "abstention", "label": key, **item}
    correlated = report.get("correlated_sources", {})
    for key, item_key in (
        ("next_pull", "next_pull_receipt_id"),
        ("anomaly", "anomaly_receipt_id"),
    ):
        receipt_id = correlated.get(item_key)
        if receipt_id and receipt_id not in expected:
            expected[str(receipt_id)] = {
                "kind": "correlated_source",
                "label": key,
                "receipt_id": str(receipt_id),
            }
    return expected


def _vehicle_scope_ids(rows: Iterable[RowMapping]) -> list[str]:
    vehicle_ids = sorted({str(row["vehicle_id"]) for row in rows})
    if not vehicle_ids:
        raise RuntimeError("The source oracle contains no vehicle scopes.")
    if len(vehicle_ids) > 20:
        raise RuntimeError(
            "The source oracle exceeds the 20-vehicle controlled operator allowlist."
        )
    return vehicle_ids


def _same_number(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    try:
        return abs(float(left) - float(right)) <= 1e-12
    except (TypeError, ValueError):
        return False


def _stored_decision_matches(stored: str | None, response_value: Any) -> bool:
    if response_value is None:
        return stored is None
    if type(response_value) is not bool:
        return False
    return stored == str(response_value)


async def prepare(database: Database, git_sha: str) -> dict[str, Any]:
    if not REPORT_9E.exists():
        raise RuntimeError("Run Phase 9E acceptance before Phase 9H.")
    report = json.loads(REPORT_9E.read_text(encoding="utf-8"))
    if report.get("status") != "PASS" or report.get("git_sha") != git_sha:
        raise RuntimeError("Phase 9E acceptance is not PASS for this exact source SHA.")
    expected = _report_receipts(report)
    if not expected:
        raise RuntimeError("Phase 9E acceptance returned no source receipts.")
    records: list[dict[str, Any]] = []
    ids = sorted(expected)
    params = {f"receipt_{index}": value for index, value in enumerate(ids)}
    placeholders = ",".join(f":receipt_{index}" for index in range(len(ids)))
    async with database.session() as db, db.begin():
        await db.execute(text("SET TRANSACTION READ ONLY"))
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT r.id,r.response_body,r.result_kind,r.horizon,r.status,r.source_role,"
                        "r.requested_cutoff,r.effective_cutoff,r.engineering_validation_score,"
                        "r.anomaly_score,r.threshold,r.decision,r.quality_summary,r.created_at,"
                        "p.vehicle_id,p.session_id,p.id AS pull_id,"
                        "COALESCE(p.configuration_id,s.configuration_id) AS configuration_id,"
                        "s.source_type,b.id AS evidence_id,b.completeness,b.integrity "
                        "FROM prediction_receipts r JOIN pulls p ON p.id=r.pull_id "
                        "JOIN driving_sessions s ON s.id=p.session_id AND s.vehicle_id=p.vehicle_id "
                        "LEFT JOIN prediction_evidence_bundles b ON b.receipt_id=r.id "
                        f"WHERE r.id IN ({placeholders}) ORDER BY r.created_at,r.id"
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
    if len(rows) != len(expected):
        raise RuntimeError(
            f"Expected {len(expected)} original receipts; found {len(rows)}."
        )
    vehicle_ids = _vehicle_scope_ids(rows)
    for row in rows:
        original = dict(row["response_body"])
        key = str(row["id"])
        context = expected[key]
        score = (
            row["engineering_validation_score"]
            if row["engineering_validation_score"] is not None
            else row["anomaly_score"]
        )
        response_score = (
            original.get("engineering_validation_score")
            if original.get("result_type") == "next_pull"
            else original.get("anomaly_score")
        )
        mismatches: list[str] = []
        if original.get("receipt_id") != key:
            mismatches.append("receipt_id")
        if original.get("result_type") != row["result_kind"]:
            mismatches.append("result_type")
        if original.get("horizon") != row["horizon"]:
            mismatches.append("horizon")
        if original.get("status") != row["status"]:
            mismatches.append("status")
        if original.get("source_role") != row["source_role"]:
            mismatches.append("source_role")
        if original.get("requested_cutoff") != row[
            "requested_cutoff"
        ].isoformat().replace("+00:00", "Z"):
            mismatches.append("requested_cutoff")
        expected_effective_cutoff = (
            row["effective_cutoff"].isoformat().replace("+00:00", "Z")
            if row["effective_cutoff"]
            else None
        )
        if original.get("effective_cutoff") != expected_effective_cutoff:
            mismatches.append("effective_cutoff")
        if not _same_number(score, response_score):
            mismatches.append("score")
        if not _same_number(original.get("threshold"), row["threshold"]):
            mismatches.append("threshold")
        if not _stored_decision_matches(row["decision"], original.get("decision")):
            mismatches.append("decision")
        if original.get("quality") != row["quality_summary"]:
            mismatches.append("quality")
        if mismatches:
            raise RuntimeError(
                f"Persisted columns and original response differ for {key}: "
                f"{', '.join(mismatches)}."
            )
        records.append(
            {
                "receipt_id": key,
                "kind": context["kind"],
                "label": context.get(
                    "task", context.get("family", context.get("label"))
                ),
                "result_type": row["result_kind"],
                "task": original.get("task"),
                "family": original.get("family"),
                "horizon": row["horizon"],
                "status": row["status"],
                "source_role": row["source_role"],
                "requested_cutoff": original.get("requested_cutoff"),
                "effective_cutoff": original.get("effective_cutoff"),
                "score": score,
                "threshold": row["threshold"],
                "decision": row["decision"],
                "model_version_id": original.get("model_version_id"),
                "detector_version_id": original.get("detector_version_id"),
                "vehicle_id": str(row["vehicle_id"]),
                "session_id": str(row["session_id"]),
                "pull_id": str(row["pull_id"]),
                "configuration_id": str(row["configuration_id"])
                if row["configuration_id"]
                else None,
                "recorded_at": row["created_at"].isoformat().replace("+00:00", "Z"),
                "source_type": row["source_type"],
                "evidence_id": str(row["evidence_id"]) if row["evidence_id"] else None,
                "evidence_completeness": row["completeness"],
                "evidence_integrity": row["integrity"],
                "quality": original.get("quality"),
                "original_response_fingerprint": _canonical_hash(original),
                "evidence_receipt_fingerprint": _canonical_hash(
                    {
                        "receipt_id": key,
                        "evidence_id": str(row["evidence_id"])
                        if row["evidence_id"]
                        else None,
                        "completeness": row["completeness"],
                        "integrity": row["integrity"],
                    }
                ),
            }
        )
    counts: dict[str, set[str]] = {
        "supervised_tasks": set(),
        "anomaly_families": set(),
    }
    for record in records:
        if record["result_type"] == "next_pull" and record["task"]:
            counts["supervised_tasks"].add(record["task"])
        if record["result_type"] == "anomaly" and record["family"]:
            counts["anomaly_families"].add(record["family"])
    if len(counts["supervised_tasks"]) != 3 or len(counts["anomaly_families"]) != 4:
        raise RuntimeError(
            "The source oracle must contain all three 9B tasks and four 9C families."
        )
    records_per_vehicle = {
        vehicle_id: sum(record["vehicle_id"] == vehicle_id for record in records)
        for vehicle_id in vehicle_ids
    }
    default_vehicle_id = min(
        vehicle_ids,
        key=lambda vehicle_id: (-records_per_vehicle[vehicle_id], vehicle_id),
    )
    baseline = await _digests(database)
    payload = {
        "schema_version": "phase9h-source-oracle-v2",
        "git_sha": git_sha,
        "vehicle_id": default_vehicle_id,
        "vehicle_ids": vehicle_ids,
        "source_role": "synthetic",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "records": records,
        "supervised_tasks": sorted(counts["supervised_tasks"]),
        "anomaly_families": sorted(counts["anomaly_families"]),
        "database_before_ui": baseline,
    }
    payload["oracle_checksum"] = _canonical_hash(payload)
    ORACLE.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


async def verify(database: Database, git_sha: str) -> dict[str, Any]:
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    checksum = oracle.pop("oracle_checksum", None)
    if (
        oracle.get("schema_version") != "phase9h-source-oracle-v2"
        or oracle.get("git_sha") != git_sha
    ):
        raise RuntimeError(
            "Phase 9H source oracle belongs to a different commit or schema."
        )
    if checksum != _canonical_hash(oracle):
        raise RuntimeError("Phase 9H source oracle checksum mismatch.")
    after = await _digests(database)
    changed = [
        table for table in TABLES if oracle["database_before_ui"][table] != after[table]
    ]
    if changed:
        raise RuntimeError(f"UI browsing mutated protected phase records: {changed}")
    metrics_root = EVIDENCE / "playwright"
    metrics = {
        name: json.loads((metrics_root / name).read_text(encoding="utf-8"))
        for name in ("synthetic-ui-metrics.json", "persisted-ui-metrics.json")
    }
    if metrics["synthetic-ui-metrics.json"].get("mode") != "synthetic-demo":
        raise RuntimeError("Synthetic UI metrics are missing the isolated demo mode.")
    if (
        metrics["persisted-ui-metrics.json"].get("mode")
        != "protected-persisted-read-only"
    ):
        raise RuntimeError("Persisted UI metrics are missing the protected mode.")
    for name, result in metrics.items():
        browser = result.get("browser", {})
        if result.get("axeViolationCount") != 0 or result.get("browserConsoleErrors"):
            raise RuntimeError(f"Accessibility or browser console findings in {name}.")
        if any(
            item.get("overflowPx") != 0 for item in result.get("responsiveOverflow", [])
        ):
            raise RuntimeError(f"Responsive horizontal overflow in {name}.")
        if browser.get("horizontalOverflowPx") != 0:
            raise RuntimeError(f"Final viewport horizontal overflow in {name}.")
    persisted_metrics = metrics["persisted-ui-metrics.json"]
    if persisted_metrics.get("bearerDisclosureCount") != 0:
        raise RuntimeError("The browser network trace includes the 9D operator bearer.")
    if persisted_metrics.get("serverSecretDisclosureCount") != 0:
        raise RuntimeError(
            "A server-only predictive secret appeared in a browser surface."
        )
    if persisted_metrics.get("internalApiHostRequests") != 0:
        raise RuntimeError("The browser contacted the private API host directly.")
    report = {
        "schema_version": "phase9h-independent-acceptance-v1",
        "git_sha": git_sha,
        "status": "PASS",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "authorized_vehicle_id": oracle["vehicle_id"],
        "authorized_vehicle_ids": oracle.get("vehicle_ids", [oracle["vehicle_id"]]),
        "source_records": len(oracle["records"]),
        "supervised_tasks": oracle["supervised_tasks"],
        "anomaly_families": oracle["anomaly_families"],
        "original_response_fingerprints": {
            item["receipt_id"]: item["original_response_fingerprint"]
            for item in oracle["records"]
        },
        "evidence_receipt_fingerprints": {
            item["receipt_id"]: item["evidence_receipt_fingerprint"]
            for item in oracle["records"]
        },
        "database_before_ui": oracle["database_before_ui"],
        "database_after_ui": after,
        "mutated_tables": changed,
        "ui_metrics": metrics,
        "browser_evidence": str(EVIDENCE / "playwright"),
        "status_checks": [
            "3_phase_9b_tasks",
            "4_phase_9c_families",
            "persisted_response_matches_columns",
            "phase_9e_evidence_scope_and_state",
            "ui_browse_no_database_mutations",
            "synthetic_demo_separate_from_persisted_reads",
            "wcag_2_2_aa_and_zero_browser_console_errors",
            "responsive_overflow_and_chart_resource_measurements",
            "no_bearer_or_private_api_host_in_browser_network",
            "no_server_secret_in_browser_html_storage_url_bundle_or_network",
        ],
    }
    report["report_checksum"] = _canonical_hash(report)
    (EVIDENCE / "acceptance.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


async def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "verify"))
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    process = await asyncio.create_subprocess_exec(
        "git", "rev-parse", "HEAD", stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError("Unable to resolve the current Git SHA.")
    actual = stdout.decode("utf-8").strip()
    if actual != args.expected_sha:
        raise RuntimeError(f"Expected source SHA {args.expected_sha}, found {actual}.")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    database = Database(Settings())
    try:
        result = await (
            prepare(database, args.expected_sha)
            if args.mode == "prepare"
            else verify(database, args.expected_sha)
        )
    finally:
        await database.close()
    print(
        json.dumps(
            {
                "status": result.get("status", "PREPARED"),
                "git_sha": args.expected_sha,
                "records": len(result.get("records", [])),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(run())
