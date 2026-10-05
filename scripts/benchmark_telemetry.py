"""Phase 1 measured ingestion baseline; only an explicitly disposable database."""

import asyncio
import importlib.metadata
import json
import math
import os
import platform
import resource
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4

from prometheus_client.parser import text_string_to_metric_families
from pydantic import SecretStr
from sqlalchemy import text
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.telemetry.domain import SyntheticTelemetrySource
from vehicle_platform.telemetry.service import IngestionService, QueryService


def batch_count(telemetry: Telemetry) -> float:
    samples = [
        sample.value
        for family in text_string_to_metric_families(
            telemetry.render_metrics().decode()
        )
        for sample in family.samples
        if sample.name == "telemetry_db_batch_duration_seconds_count"
        and sample.labels.get("source") == "import"
    ]
    if not samples:
        raise RuntimeError("actual ingestion batch histogram was not measured")
    return sum(samples)


async def main() -> None:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not urlparse(url).path.removeprefix("/").startswith("vehicle_test"):
        raise SystemExit(
            "TEST_DATABASE_URL must explicitly select a disposable vehicle_test* DB"
        )
    settings = Settings(database_url=SecretStr(url), environment="test")
    database = Database(settings)
    telemetry = Telemetry(settings, database)
    vehicle, session = uuid4(), uuid4()
    origin = datetime.now(UTC) - timedelta(hours=4)
    frames, expected, batch_size = 14286, 100002, 1000
    try:
        async with database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO vehicles(id,manufacturer,model) VALUES(:id,'Synthetic','Benchmark')"
                ),
                {"id": vehicle},
            )
            await db.execute(
                text(
                    "INSERT INTO driving_sessions(id,vehicle_id,source_type,source_reference,started_at) "
                    "VALUES(:id,:vehicle,'synthetic','phase1-disposable-benchmark',:started)"
                ),
                {"id": session, "vehicle": vehicle, "started": origin},
            )
            await db.commit()
        importer = IngestionService(
            database, batch_size=batch_size, telemetry=telemetry
        )
        cpu_before = resource.getrusage(resource.RUSAGE_SELF)
        before = time.perf_counter()
        first = await importer.ingest(
            session, "synthetic", SyntheticTelemetrySource(origin, frames)
        )
        elapsed = time.perf_counter() - before
        resources = resource.getrusage(resource.RUSAGE_SELF)
        measured_batches = batch_count(telemetry)
        if (
            first.accepted != expected
            or first.rejected
            or measured_batches != math.ceil(expected / batch_size)
        ):
            raise RuntimeError(
                "Phase 1 ingest count or measured batch size disagrees with input"
            )
        async with database.session() as db:
            counts = (
                (
                    await db.execute(
                        text(
                            "SELECT count(*) AS persisted,count(DISTINCT sample_id) AS unique_samples "
                            "FROM telemetry_samples WHERE session_id=:id"
                        ),
                        {"id": session},
                    )
                )
                .mappings()
                .one()
            )
            stored_count = await db.scalar(
                text("SELECT sample_count FROM driving_sessions WHERE id=:id"),
                {"id": session},
            )
            versions = (
                (
                    await db.execute(
                        text(
                            "SELECT version() AS postgres,"
                            "(SELECT extversion FROM pg_extension WHERE extname='timescaledb') AS timescaledb"
                        )
                    )
                )
                .mappings()
                .one()
            )
            plan = await db.scalar(
                text(
                    "EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) "
                    "SELECT observed_at,numeric_value,normalized_unit,quality FROM telemetry_samples "
                    "WHERE session_id=:id AND signal_key=:signal AND observed_at>=:start "
                    "AND observed_at<:end ORDER BY observed_at,sequence_number,sample_id LIMIT 2000"
                ),
                {
                    "id": session,
                    "signal": "engine.rpm",
                    "start": origin,
                    "end": origin + timedelta(seconds=4000),
                },
            )
        plan = json.loads(plan) if isinstance(plan, str) else plan
        query_started = time.perf_counter()
        window = await QueryService(database, telemetry).query(
            session, ["engine.rpm"], origin, origin + timedelta(seconds=4000), 2000
        )
        query_seconds = time.perf_counter() - query_started
        if not window.truncated or len(window.points) != 2000:
            raise RuntimeError(
                "Phase 1 bounded query did not expose measured truncation"
            )
        replay_started = time.perf_counter()
        replay = await importer.ingest(
            session, "synthetic", SyntheticTelemetrySource(origin, frames)
        )
        replay_seconds = time.perf_counter() - replay_started
        async with database.session() as db:
            after = await db.scalar(
                text("SELECT count(*) FROM telemetry_samples WHERE session_id=:id"),
                {"id": session},
            )
        if (
            counts["persisted"] != expected
            or counts["unique_samples"] != expected
            or stored_count != expected
            or after != expected
        ):
            raise RuntimeError("Phase 1 persisted identities/counts changed")
        if (
            replay.accepted != 0
            or replay.duplicates != expected
            or replay.conflicts
            or replay.rejected
        ):
            raise RuntimeError(
                "Phase 1 deterministic replay failed canonical idempotency"
            )
        report = {
            "phase": 1,
            "database_scope": "explicit disposable vehicle_test*",
            "observations": expected,
            "frames": frames,
            "batch_size": batch_size,
            "actual_measured_batches": measured_batches,
            "ingest_elapsed_seconds": elapsed,
            "observations_per_second": expected / elapsed,
            "process_cpu_seconds": (
                resources.ru_utime
                + resources.ru_stime
                - cpu_before.ru_utime
                - cpu_before.ru_stime
            ),
            "peak_process_rss_mb": resources.ru_maxrss / 1024,
            "memory_scope": "Linux ingestion Python process peak RSS including driver/runtime, not DB container",
            "logical_cpus": os.cpu_count(),
            "host_ram_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "dependencies": {
                name: importlib.metadata.version(name)
                for name in ("sqlalchemy", "asyncpg", "fastapi")
            },
            "database_versions": dict(versions),
            "persisted": counts["persisted"],
            "unique_samples": counts["unique_samples"],
            "stored_session_count": stored_count,
            "bounded_query_seconds": query_seconds,
            "bounded_query_points": len(window.points),
            "query_truncated": window.truncated,
            "query_plan_analyze_buffers": plan,
            "replay_seconds": replay_seconds,
            "replay_duplicates": replay.duplicates,
            "replay_new_rows": replay.accepted,
            "pass": True,
        }
        print(json.dumps(report, indent=2))
    finally:
        await database.close()
        telemetry.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
