"""Measure feature generation and dataset materialization over 100 synthetic pulls."""

import asyncio
import json
import os
import resource
import tracemalloc
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import text
from vehicle_platform.core.config import Settings
from vehicle_platform.features.datasets import DatasetBuilder
from vehicle_platform.features.domain import (
    CutoffPolicy,
    DatasetDefinition,
    EntityScope,
)
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.features.service import FeatureGenerationService
from vehicle_platform.infrastructure.database import Database


async def _seed(database: Database, count: int) -> tuple[UUID, datetime]:
    now = datetime.now(UTC)
    start = now - timedelta(days=3)
    async with database.session() as db:
        vehicle = (
            await db.execute(
                text(
                    "INSERT INTO vehicles(manufacturer,model,engine_code,created_at) VALUES('BMW','Benchmark','N55',:created) RETURNING id"
                ),
                {"created": start - timedelta(days=1)},
            )
        ).scalar_one()
        configuration = (
            await db.execute(
                text(
                    "INSERT INTO vehicle_configurations(vehicle_id,effective_at,description,metadata,provenance,created_at) VALUES(:vehicle,:effective,'Synthetic benchmark',CAST(:metadata AS jsonb),'feature-benchmark',:created) RETURNING id"
                ),
                {
                    "vehicle": vehicle,
                    "effective": start - timedelta(days=1),
                    "created": start - timedelta(days=1),
                    "metadata": '{"stage":"stock","fuel_type":"93 AKI"}',
                },
            )
        ).scalar_one()
        session = (
            await db.execute(
                text(
                    "INSERT INTO driving_sessions(vehicle_id,configuration_id,source_type,started_at,ended_at,status,metadata,created_at) VALUES(:vehicle,:configuration,'synthetic',:started,:ended,'completed',CAST(:metadata AS jsonb),:created) RETURNING id"
                ),
                {
                    "vehicle": vehicle,
                    "configuration": configuration,
                    "started": start,
                    "ended": now,
                    "created": start - timedelta(days=1),
                    "metadata": '{"data_role":"synthetic"}',
                },
            )
        ).scalar_one()
        pull_ids = (
            (
                await db.execute(
                    text(
                        "INSERT INTO pulls(session_id,started_at,ended_at,duration_ms,confidence,detector_name,algorithm_version,configuration_hash,vehicle_id,configuration_id,start_rpm,end_rpm,start_speed,end_speed,max_speed,max_boost,average_boost,start_iat,end_iat,iat_delta,max_oil_temperature,max_coolant_temperature,average_throttle,max_throttle,data_completeness,sample_count,created_at) "
                        "SELECT :session,CAST(:start AS timestamptz)+series.n*interval '1 minute',CAST(:start AS timestamptz)+series.n*interval '1 minute'+interval '4 seconds',4000,.95,'feature-benchmark','1',repeat(md5(series.n::text),2),:vehicle,:configuration,3000,5000,14,22,22,110000,100000,300,304,4,332,337,90,92,1.0,40,CAST(:start AS timestamptz)+series.n*interval '1 minute'-interval '1 second' FROM generate_series(0,:count-1) AS series(n) RETURNING id"
                    ),
                    {
                        "session": session,
                        "start": start,
                        "vehicle": vehicle,
                        "configuration": configuration,
                        "count": count,
                    },
                )
            )
            .scalars()
            .all()
        )
        await db.commit()
    if len(pull_ids) != count:
        raise AssertionError(
            f"expected {count} synthetic pull rows; inserted {len(pull_ids)}"
        )
    return session, start


async def main() -> None:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError("benchmark requires a disposable vehicle_test database")
    count = int(os.environ.get("FEATURE_BENCHMARK_PULLS", "100"))
    if not 100 <= count <= 1000:
        raise ValueError("FEATURE_BENCHMARK_PULLS must be between 100 and 1000")
    database = Database(Settings(database_url=SecretStr(url), environment="test"))
    try:
        session_id, start = await _seed(database, count)
        service = FeatureGenerationService(database)
        tracemalloc.start()
        started = perf_counter()
        generated = await service.generate_session(session_id, max_pulls=100)
        generation_seconds = perf_counter() - started
        if generated["failed"] or generated["generated"] != count:
            raise AssertionError(f"feature generation failed: {generated}")
        builder = DatasetBuilder(database, DEFAULT_REGISTRY)
        definition = DatasetDefinition(
            name=f"phase9a-benchmark-{count}",
            version="v1",
            row_scope=EntityScope.PULL,
            feature_set_version=service.version.version,
            selected_features=(
                "raw_context.engine_code",
                "performance.pull_duration_s",
                "quality.observation_count",
                "temporal_context.prior_pull_count",
            ),
            observation_cutoff=datetime.now(UTC),
            cutoff_policy=CutoffPolicy.ROW_END,
            minimum_quality=0.0,
            allow_configuration_mixing=True,
            source="synthetic",
        )
        materialize_started = perf_counter()
        result = await builder.build(definition)
        materialize_seconds = perf_counter() - materialize_started
        _, peak_bytes = tracemalloc.get_traced_memory()
        report = {
            "status": "MEASURED_SYNTHETIC_ONLY",
            "database": "disposable TimescaleDB",
            "pulls": count,
            "feature_definitions": len(DEFAULT_REGISTRY.list()),
            "generated_feature_sets": generated["generated"],
            "feature_generation_seconds": generation_seconds,
            "feature_generation_pulls_per_second": count / generation_seconds,
            "dataset_rows": len(result.rows),
            "dataset_exclusions": len(result.exclusions),
            "dataset_materialization_seconds": materialize_seconds,
            "dataset_rows_per_second": len(result.rows)
            / max(materialize_seconds, 1e-9),
            "dataset_checksum": result.checksum,
            "peak_python_bytes": peak_bytes,
            "max_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            * 1024,
            "fixture_start": start.isoformat(),
            "paid_calls": 0,
        }
        target = Path(".validation/phase9a/benchmark.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
