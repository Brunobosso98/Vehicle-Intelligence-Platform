"""Read-only source snapshots and independent fact lookup for disposable fixtures."""

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from vehicle_platform.agent_evaluation.contracts import AgentEvalCase, OracleFact

TABLES = (
    "vehicles",
    "vehicle_configurations",
    "modifications",
    "driving_sessions",
    "telemetry_samples",
    "pulls",
    "session_segments",
    "detected_events",
    "event_analysis_runs",
    "analytics_runs",
    "acquisition_sessions",
    "stream_receipts",
    "provisional_findings",
    "stream_dead_letters",
    "acquisition_source_capabilities",
    "investigation_plans",
    "investigation_session_links",
    "investigation_events",
    "dataset_capability_reports",
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
    "evaluation_protocols",
    "evaluation_runs",
    "evaluation_metric_reports",
    "evaluation_calibration_candidates",
    "evaluation_applicability_assessments",
    "knowledge_sources",
    "knowledge_documents",
    "knowledge_document_versions",
    "knowledge_indexes",
    "knowledge_chunks",
    "knowledge_embeddings",
    "knowledge_conflicts",
    "mlops_definitions",
    "mlops_runs",
    "mlops_proposals",
    "mlops_proposal_events",
    "mlops_rollback_plans",
    "mlops_run_events",
    "mlops_step_events",
)


def is_disposable_database_url(database_url: str) -> bool:
    try:
        url = make_url(database_url)
    except Exception:
        return False
    return (
        url.drivername == "postgresql+asyncpg"
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and bool(url.database and url.database.startswith("vehicle_test"))
        and not url.query
    )


def _canonical(values: list[dict[str, Any]]) -> bytes:
    return json.dumps(values, sort_keys=True, separators=(",", ":"), default=str).encode()


async def source_digest(database_url: str) -> str:
    """Hash canonical Phase 1–10 rows directly, excluding append-only agent audit data."""
    if not is_disposable_database_url(database_url):
        raise ValueError("Phase 11 source oracle requires a disposable vehicle_test database")
    engine = create_async_engine(
        database_url, pool_size=1, max_overflow=0, isolation_level="REPEATABLE READ"
    )
    try:
        parts: list[tuple[str, list[dict[str, Any]]]] = []
        async with engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            for table in TABLES:
                exists = await connection.scalar(text("SELECT to_regclass(:name)"), {"name": table})
                if exists is None:
                    raise ValueError(f"fixture_source_table_missing:{table}")
                rows = (
                    (
                        await connection.execute(
                            text(  # noqa: S608 - table names come from fixed TABLES allowlist
                                f"SELECT to_jsonb(t) AS row FROM {table} t"  # noqa: S608
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                normalized = [row if isinstance(row, dict) else json.loads(row) for row in rows]
                normalized.sort(key=lambda row: json.dumps(row, sort_keys=True, default=str))
                parts.append((table, normalized))
        snapshot = [{"table": name, "rows": rows} for name, rows in parts]
        return hashlib.sha256(_canonical(snapshot)).hexdigest()
    finally:
        await engine.dispose()


async def persisted_agent_run(database_url: str, run_id: str) -> dict[str, Any] | None:
    """Load persisted run, tool audit and event evidence independently of the receipt."""
    if not is_disposable_database_url(database_url):
        raise ValueError("Phase 11 source oracle requires a disposable vehicle_test database")
    try:
        identifier = UUID(run_id)
    except (ValueError, TypeError):
        return None
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT vehicle_id::text AS vehicle_id,status,snapshot "
                            "FROM agent_runs WHERE id=:run"
                        ),
                        {"run": identifier},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            calls = (
                (
                    await db.execute(
                        text(
                            "SELECT snapshot FROM agent_tool_calls WHERE agent_run_id=:run "
                            "ORDER BY started_at,id LIMIT 32"
                        ),
                        {"run": identifier},
                    )
                )
                .scalars()
                .all()
            )
            events = (
                (
                    await db.execute(
                        text(
                            "SELECT snapshot FROM agent_stream_events WHERE agent_run_id=:run "
                            "ORDER BY sequence LIMIT 400"
                        ),
                        {"run": identifier},
                    )
                )
                .scalars()
                .all()
            )
        return {
            "vehicle_id": str(row["vehicle_id"]),
            "status": str(row["status"]),
            "snapshot": row["snapshot"],
            "tool_calls": list(calls),
            "events": list(events),
        }
    finally:
        await engine.dispose()


async def latest_session_id(database_url: str, vehicle_id: str) -> str:
    """Independent oracle: select the latest canonical session without agent code."""
    if not is_disposable_database_url(database_url):
        raise ValueError("Phase 11 source oracle requires a disposable vehicle_test database")
    engine = create_async_engine(database_url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as connection:
            value = await connection.scalar(
                text(
                    "SELECT id::text FROM driving_sessions "
                    "WHERE vehicle_id=CAST(:vehicle AS uuid) "
                    "ORDER BY started_at DESC, id DESC LIMIT 1"
                ),
                {"vehicle": vehicle_id},
            )
        if value is None:
            raise ValueError("fixture_has_no_sessions")
        return str(value)
    finally:
        await engine.dispose()


async def event_exists(database_url: str, vehicle_id: str, event_type: str) -> bool:
    """Check a golden event directly in the canonical source table."""
    if not is_disposable_database_url(database_url):
        raise ValueError("Phase 11 source oracle requires a disposable vehicle_test database")
    engine = create_async_engine(database_url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as connection:
            value = await connection.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM detected_events "
                    "WHERE vehicle_id=CAST(:vehicle AS uuid) AND event_type=:event_type)"
                ),
                {"vehicle": vehicle_id, "event_type": event_type},
            )
        return bool(value)
    finally:
        await engine.dispose()


async def resolve_case_facts(
    database_url: str, case: AgentEvalCase, vehicle_id: str
) -> tuple[OracleFact, ...]:
    """Resolve each corpus fact directly from its allowlisted source table."""
    resolved: list[OracleFact] = []
    for fact in case.expected_facts:
        value: str | int | float | bool | None
        is_latest_session = (
            fact.source_table == "driving_sessions"
            and fact.path == "/id"
            and fact.value == "fixture-latest-session"
        )
        if is_latest_session:
            value = await latest_session_id(database_url, vehicle_id)
        elif fact.source_table == "detected_events" and fact.path == "/event_type":
            if not await event_exists(database_url, vehicle_id, str(fact.value)):
                raise ValueError("fixture_expected_event_missing")
            value = fact.value
        else:
            raise ValueError("independent_fact_resolver_unavailable")
        resolved.append(fact.model_copy(update={"value": value}))
    return tuple(resolved)


async def schema_revision(database_url: str) -> str:
    """Read the applied Alembic revision from the disposable acceptance database."""
    if not is_disposable_database_url(database_url):
        raise ValueError("Phase 11 source oracle requires a disposable vehicle_test database")
    engine = create_async_engine(database_url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as connection:
            value = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        if value is None:
            raise ValueError("fixture_schema_revision_missing")
        return str(value)
    finally:
        await engine.dispose()
