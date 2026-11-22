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
    return (await latest_session_ids(database_url, vehicle_id, limit=1))[0]


async def latest_session_ids(
    database_url: str, vehicle_id: str, *, limit: int = 2
) -> tuple[str, ...]:
    """Return the newest canonical session IDs in deterministic temporal order."""
    if not is_disposable_database_url(database_url):
        raise ValueError("Phase 11 source oracle requires a disposable vehicle_test database")
    if limit not in {1, 2}:
        raise ValueError("session oracle limit is outside the supported bound")
    engine = create_async_engine(database_url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as connection:
            values = (
                (
                    await connection.execute(
                        text(
                            "SELECT id::text FROM driving_sessions "
                            "WHERE vehicle_id=CAST(:vehicle AS uuid) "
                            "ORDER BY started_at DESC, id DESC LIMIT :limit"
                        ),
                        {"vehicle": vehicle_id, "limit": limit},
                    )
                )
                .scalars()
                .all()
            )
        if len(values) != limit:
            raise ValueError("fixture_has_no_sessions")
        return tuple(str(value) for value in values)
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
                    "WHERE vehicle_id=CAST(:vehicle AS uuid) AND event_type=:event_type "
                    "AND session_id=(SELECT id FROM driving_sessions "
                    "WHERE vehicle_id=CAST(:vehicle AS uuid) "
                    "ORDER BY started_at DESC, id DESC LIMIT 1))"
                ),
                {"vehicle": vehicle_id, "event_type": event_type},
            )
        return bool(value)
    finally:
        await engine.dispose()


async def source_signal_present(database_url: str, vehicle_id: str, signal: str) -> bool:
    """Check a telemetry signal directly in the latest canonical vehicle session."""
    if not is_disposable_database_url(database_url):
        raise ValueError("Phase 11 source oracle requires a disposable vehicle_test database")
    if signal not in {
        "engine.rpm",
        "vehicle.speed",
        "engine.throttle_position",
        "engine.boost_pressure",
        "engine.intake_air_temperature",
        "engine.oil_temperature",
        "engine.coolant_temperature",
        "fuel.high_pressure",
    }:
        raise ValueError("oracle_signal_not_allowlisted")
    engine = create_async_engine(database_url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as connection:
            present = await connection.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM telemetry_samples t "
                    "JOIN driving_sessions s ON s.id=t.session_id "
                    "WHERE s.vehicle_id=CAST(:vehicle AS uuid) "
                    "AND s.id=(SELECT id FROM driving_sessions "
                    "WHERE vehicle_id=CAST(:vehicle AS uuid) "
                    "ORDER BY started_at DESC,id DESC LIMIT 1) "
                    "AND t.signal_key=:signal)"
                ),
                {"vehicle": vehicle_id, "signal": signal},
            )
        return bool(present)
    finally:
        await engine.dispose()


async def verify_vehicle_scope_fixture(
    database_url: str,
    *,
    source_vehicle_id: str,
    request_vehicle_id: str,
    source_session_id: str,
) -> dict[str, str | int | float | bool | None]:
    """Independently verify distinct vehicle/config identities and session ownership."""
    if not is_disposable_database_url(database_url):
        raise ValueError("Phase 11 source oracle requires a disposable vehicle_test database")
    engine = create_async_engine(database_url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            """
                        SELECT
                            source_vehicle.id::text AS source_id,
                            request_vehicle.id::text AS request_id,
                            source_vehicle.manufacturer AS source_make,
                            request_vehicle.manufacturer AS request_make,
                            source_vehicle.engine_code AS source_engine,
                            request_vehicle.engine_code AS request_engine,
                            (SELECT count(*) FROM vehicle_configurations c
                             WHERE c.vehicle_id=source_vehicle.id) AS source_configs,
                            (SELECT count(*) FROM vehicle_configurations c
                             WHERE c.vehicle_id=request_vehicle.id) AS request_configs,
                            EXISTS(SELECT 1 FROM driving_sessions s
                                   WHERE s.id=CAST(:session AS uuid)
                                   AND s.vehicle_id=source_vehicle.id) AS session_owned_by_source,
                            EXISTS(SELECT 1 FROM driving_sessions s
                                   WHERE s.id=CAST(:session AS uuid)
                                   AND s.vehicle_id=request_vehicle.id) AS session_owned_by_request
                        FROM vehicles source_vehicle
                        CROSS JOIN vehicles request_vehicle
                        WHERE source_vehicle.id=CAST(:source AS uuid)
                          AND request_vehicle.id=CAST(:request AS uuid)
                        """
                        ),
                        {
                            "source": source_vehicle_id,
                            "request": request_vehicle_id,
                            "session": source_session_id,
                        },
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise ValueError("vehicle_scope_fixture_missing")
        return {
            "distinct_vehicle_ids": row["source_id"] != row["request_id"],
            "distinct_manufacturers": row["source_make"] != row["request_make"],
            "distinct_engines": row["source_engine"] != row["request_engine"],
            "source_vehicle_configuration_count": int(row["source_configs"]),
            "request_vehicle_configuration_count": int(row["request_configs"]),
            "session_owned_by_source_vehicle": bool(row["session_owned_by_source"]),
            "session_not_owned_by_request_vehicle": not bool(row["session_owned_by_request"]),
        }
    finally:
        await engine.dispose()


async def resolve_case_facts(
    database_url: str, case: AgentEvalCase, vehicle_id: str
) -> tuple[OracleFact, ...]:
    """Resolve each corpus fact directly from its allowlisted source table."""
    resolved: list[OracleFact] = []
    recent_session_ids: tuple[str, ...] | None = None
    for fact in case.expected_facts:
        value: str | int | float | bool | None
        is_recent_session = (
            fact.source_table == "driving_sessions"
            and fact.path == "/id"
            and fact.value in {"fixture-latest-session", "fixture-second-latest-session"}
        )
        if is_recent_session:
            if recent_session_ids is None:
                recent_session_ids = await latest_session_ids(database_url, vehicle_id)
            offset = 0 if fact.value == "fixture-latest-session" else 1
            value = recent_session_ids[offset]
        elif fact.source_table == "detected_events" and fact.path == "/event_type":
            if not await event_exists(database_url, vehicle_id, str(fact.value)):
                raise ValueError("fixture_expected_event_missing")
            value = fact.value
        elif fact.source_table == "vehicles" and fact.path == "/nickname":
            engine = create_async_engine(database_url, pool_size=1, max_overflow=0)
            try:
                async with engine.connect() as connection:
                    value = await connection.scalar(
                        text("SELECT nickname FROM vehicles WHERE id=CAST(:vehicle AS uuid)"),
                        {"vehicle": vehicle_id},
                    )
            finally:
                await engine.dispose()
            if not isinstance(value, str):
                raise ValueError("fixture_expected_vehicle_nickname_missing")
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
