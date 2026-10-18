"""Real PostgreSQL coverage for Phase 9A persistence and temporal guards."""

import asyncio
import hashlib
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from vehicle_platform.core.config import Settings
from vehicle_platform.features.datasets import DatasetBuilder
from vehicle_platform.features.domain import CutoffPolicy, DatasetDefinition, EntityScope
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.features.service import FeatureGenerationService
from vehicle_platform.infrastructure.database import Database

pytestmark = pytest.mark.integration


def _test_database_url() -> str:
    value = os.environ.get("TEST_DATABASE_URL")
    if not value or not value.rsplit("/", 1)[-1].startswith("vehicle_test"):
        pytest.fail("TEST_DATABASE_URL must target a disposable vehicle_test* database")
    return value


async def _seed(database: Database) -> dict[str, object]:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    async with database.session() as db:
        vehicles: dict[str, UUID] = {}
        for key, engine in (("a", "N55"), ("b", "N55")):
            vehicles[key] = (
                await db.execute(
                    text(
                        "INSERT INTO vehicles(manufacturer,model,engine_code,created_at) "
                        "VALUES('BMW',:model,:engine,:created) RETURNING id"
                    ),
                    {
                        "model": f"Feature-{key}-{uuid4().hex[:8]}",
                        "engine": engine,
                        "created": start - timedelta(days=5),
                    },
                )
            ).scalar_one()
        config_a = (
            await db.execute(
                text(
                    "INSERT INTO vehicle_configurations(vehicle_id,effective_at,ended_at,description,"
                    "metadata,provenance,created_at) VALUES(:vehicle,:effective,:ended,'Stage A',"
                    "CAST(:metadata AS jsonb),'feature-test',:created) RETURNING id"
                ),
                {
                    "vehicle": vehicles["a"],
                    "effective": start - timedelta(days=4),
                    "ended": start + timedelta(seconds=30),
                    "metadata": '{"stage":"stock","fuel_type":"93 AKI"}',
                    "created": start - timedelta(days=4),
                },
            )
        ).scalar_one()
        config_b = (
            await db.execute(
                text(
                    "INSERT INTO vehicle_configurations(vehicle_id,effective_at,description,metadata,"
                    "provenance,created_at) VALUES(:vehicle,:effective,'Stage B',CAST(:metadata AS jsonb),"
                    "'feature-test',:created) RETURNING id"
                ),
                {
                    "vehicle": vehicles["a"],
                    "effective": start + timedelta(seconds=30),
                    "metadata": '{"stage":"stage2","fuel_type":"93 AKI"}',
                    "created": start - timedelta(days=1),
                },
            )
        ).scalar_one()
        config_c = (
            await db.execute(
                text(
                    "INSERT INTO vehicle_configurations(vehicle_id,effective_at,description,metadata,"
                    "provenance,created_at) VALUES(:vehicle,:effective,'Vehicle B',CAST(:metadata AS jsonb),"
                    "'feature-test',:created) RETURNING id"
                ),
                {
                    "vehicle": vehicles["b"],
                    "effective": start - timedelta(days=4),
                    "metadata": '{"stage":"stock","fuel_type":"91 AKI"}',
                    "created": start - timedelta(days=4),
                },
            )
        ).scalar_one()
        await db.execute(
            text(
                "INSERT INTO modifications(vehicle_id,configuration_id,category,manufacturer,product,"
                "installed_at,created_at) VALUES(:vehicle,:config,'intake','Fixture','Intake',:installed,:created)"
            ),
            {
                "vehicle": vehicles["a"],
                "config": config_a,
                "installed": start - timedelta(hours=2),
                "created": start - timedelta(hours=2),
            },
        )
        session_ids: dict[str, UUID] = {}
        for key, vehicle_id, configuration_id, at, ended in (
            (
                "first",
                vehicles["a"],
                config_a,
                start - timedelta(minutes=2),
                start + timedelta(seconds=15),
            ),
            (
                "second",
                vehicles["a"],
                config_a,
                start + timedelta(seconds=20),
                start + timedelta(seconds=30),
            ),
            (
                "third",
                vehicles["a"],
                config_b,
                start + timedelta(seconds=40),
                start + timedelta(seconds=50),
            ),
            (
                "fourth",
                vehicles["b"],
                config_c,
                start + timedelta(seconds=50),
                start + timedelta(seconds=60),
            ),
        ):
            session_ids[key] = (
                await db.execute(
                    text(
                        "INSERT INTO driving_sessions(vehicle_id,configuration_id,source_type,started_at,"
                        "ended_at,status,metadata,created_at) VALUES(:vehicle,:configuration,'synthetic',"
                        ":started,:ended,'completed',CAST(:metadata AS jsonb),:created) RETURNING id"
                    ),
                    {
                        "vehicle": vehicle_id,
                        "configuration": configuration_id,
                        "started": at,
                        "ended": ended,
                        "metadata": '{"data_role":"synthetic"}',
                        "created": start - timedelta(days=1),
                    },
                )
            ).scalar_one()
        pull_ids: dict[str, UUID] = {}
        pull_specs = (
            ("p1", "a", "first", config_a, start, 1.0, True),
            ("p2", "a", "first", config_a, start + timedelta(seconds=10), 1.0, True),
            ("p3", "a", "second", config_a, start + timedelta(seconds=20), 0.85, False),
            ("p4", "a", "third", config_b, start + timedelta(seconds=40), 1.0, True),
            ("p5", "b", "fourth", config_c, start + timedelta(seconds=50), 0.25, True),
        )
        signal_specs = (
            ("engine.rpm", "rpm", 3000.0, 500.0),
            ("vehicle.speed", "m/s", 14.0, 2.0),
            ("engine.throttle_position", "%", 90.0, 1.0),
            ("engine.boost_pressure", "Pa", 100_000.0, 2_000.0),
            ("engine.intake_air_temperature", "K", 300.0, 1.0),
            ("engine.oil_temperature", "K", 330.0, 0.5),
            ("engine.coolant_temperature", "K", 335.0, 0.5),
            ("fuel.high_pressure", "Pa", 15_000_000.0, -100_000.0),
        )
        for (
            name,
            vehicle_key,
            session_key,
            configuration_id,
            at,
            completeness,
            fuel_available,
        ) in pull_specs:
            vehicle_id = vehicles[vehicle_key]
            session_id = session_ids[session_key]
            pull_id = (
                await db.execute(
                    text(
                        "INSERT INTO pulls(session_id,started_at,ended_at,duration_ms,confidence,detector_name,"
                        "algorithm_version,configuration_hash,vehicle_id,configuration_id,start_rpm,end_rpm,"
                        "start_speed,end_speed,max_speed,max_boost,average_boost,start_iat,end_iat,iat_delta,"
                        "max_oil_temperature,max_coolant_temperature,average_throttle,max_throttle,data_completeness,"
                        "sample_count,quality_flags,metadata,created_at) VALUES(:session,:started,:ended,4000,"
                        ".95,'feature-test','1','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',"
                        ":vehicle,:configuration,3000,5000,14,22,22,110000,100000,300,304,4,332,337,90,92,"
                        ":completeness,40,'{}',CAST(:metadata AS jsonb),:created) RETURNING id"
                    ),
                    {
                        "session": session_id,
                        "started": at,
                        "ended": at + timedelta(seconds=4),
                        "vehicle": vehicle_id,
                        "configuration": configuration_id,
                        "completeness": completeness,
                        "metadata": '{"available_signals":["engine.rpm","vehicle.speed",'
                        '"engine.throttle_position","engine.boost_pressure",'
                        '"engine.intake_air_temperature","engine.oil_temperature",'
                        '"engine.coolant_temperature","fuel.high_pressure"]}'
                        if fuel_available
                        else '{"available_signals":["engine.rpm","vehicle.speed",'
                        '"engine.throttle_position","engine.boost_pressure",'
                        '"engine.intake_air_temperature","engine.oil_temperature",'
                        '"engine.coolant_temperature"]}',
                        "created": at - timedelta(milliseconds=1),
                    },
                )
            ).scalar_one()
            pull_ids[name] = pull_id
            for index in range(5):
                observed_at = at + timedelta(seconds=index)
                for signal, unit, initial, delta in signal_specs:
                    if signal == "fuel.high_pressure" and not fuel_available:
                        continue
                    value = initial + index * delta
                    sample_id = hashlib.sha256(f"{pull_id}:{signal}:{index}".encode()).hexdigest()
                    await db.execute(
                        text(
                            "INSERT INTO telemetry_samples(sample_id,vehicle_id,session_id,observed_at,"
                            "ingested_at,signal_key,numeric_value,normalized_unit,raw_signal,raw_value,source,"
                            "source_record_id,sequence_number,quality,schema_version,content_hash) "
                            "VALUES(:sample,:vehicle,:session,:observed,:ingested,:signal,:value,:unit,:signal,"
                            ":raw,'synthetic',:record,:sequence,:quality,1,:hash)"
                        ),
                        {
                            "sample": sample_id,
                            "vehicle": vehicle_id,
                            "session": session_id,
                            "observed": observed_at,
                            "ingested": observed_at,
                            "signal": signal,
                            "value": value,
                            "unit": unit,
                            "raw": str(value),
                            "record": f"{name}-{signal}-{index}",
                            "sequence": index,
                            "quality": "invalid"
                            if name == "p5" and signal == "engine.rpm" and index == 0
                            else "valid",
                            "hash": sample_id,
                        },
                    )
            if name == "p3":
                future_id = hashlib.sha256(f"{pull_id}:future-ingest".encode()).hexdigest()
                await db.execute(
                    text(
                        "INSERT INTO telemetry_samples(sample_id,vehicle_id,session_id,observed_at,ingested_at,"
                        "signal_key,numeric_value,normalized_unit,raw_signal,raw_value,source,source_record_id,"
                        "sequence_number,quality,schema_version,content_hash) VALUES(:sample,:vehicle,:session,"
                        ":observed,:ingested,'fuel.high_pressure',18000000,'Pa','fuel.high_pressure','18000000',"
                        "'synthetic','future-ingest',99,'valid',1,:hash)"
                    ),
                    {
                        "sample": future_id,
                        "vehicle": vehicle_id,
                        "session": session_id,
                        "observed": at + timedelta(seconds=3),
                        "ingested": at + timedelta(seconds=5),
                        "hash": future_id,
                    },
                )
        run_id = (
            await db.execute(
                text(
                    "INSERT INTO event_analysis_runs(session_id,profile,configuration_hash,status,"
                    "detector_states,event_count,started_at,finished_at) VALUES(:session,'feature-test',"
                    "'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb','completed',"
                    "'{}',2,:started,:finished) RETURNING id"
                ),
                {
                    "session": session_ids["first"],
                    "started": start,
                    "finished": start + timedelta(seconds=25),
                },
            )
        ).scalar_one()
        for event_start, event_end, created in (
            (
                start + timedelta(seconds=12),
                start + timedelta(seconds=13),
                start + timedelta(seconds=14),
            ),
            (
                start + timedelta(seconds=16),
                start + timedelta(seconds=17),
                start + timedelta(seconds=25),
            ),
        ):
            await db.execute(
                text(
                    "INSERT INTO detected_events(vehicle_id,session_id,analysis_run_id,event_type,category,"
                    "started_at,ended_at,duration_ms,severity,confidence,algorithm_name,algorithm_version,"
                    "configuration_hash,baseline_type,baseline_reference,evidence,created_at) VALUES(:vehicle,"
                    ":session,:run,'boost_drop','performance',:started,:ended,1000,'moderate',.9,"
                    "'feature-test','1','bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',"
                    "'none','{}','{}',:created)"
                ),
                {
                    "vehicle": vehicles["a"],
                    "session": session_ids["first"],
                    "run": run_id,
                    "started": event_start,
                    "ended": event_end,
                    "created": created,
                },
            )
        await db.commit()
    return {
        "start": start,
        "vehicles": vehicles,
        "configurations": {"a": config_a, "b": config_b, "c": config_c},
        "sessions": session_ids,
        "pulls": pull_ids,
    }


async def test_persistence_cutoffs_history_dataset_and_concurrency() -> None:
    url = _test_database_url()
    database = Database(Settings(database_url=url, environment="test"))
    try:
        fixture = await _seed(database)
        pulls = fixture["pulls"]
        assert isinstance(pulls, dict)
        service = FeatureGenerationService(database)
        preview = await service.estimate_session(fixture["sessions"]["first"], max_pulls=2)
        assert preview["candidate_pulls"] == 2
        assert preview["expected_new_feature_sets"] == 2
        assert preview["mutates_database"] is False
        async with database.session() as db:
            versions_before_preview = await db.scalar(
                text("SELECT count(*) FROM feature_set_versions")
            )
        assert versions_before_preview == 0
        version_id = await service.ensure_version()
        assert isinstance(version_id, UUID)

        first = await service.generate_pull(pulls["p1"])
        same_p2_a, same_p2_b = await asyncio.gather(
            service.generate_pull(pulls["p2"]), service.generate_pull(pulls["p2"])
        )
        assert same_p2_a.id == same_p2_b.id
        assert same_p2_a.source_hash == same_p2_b.source_hash
        target = await service.generate_pull(pulls["p3"])
        next_configuration = await service.generate_pull(pulls["p4"])
        poor_quality = await service.generate_pull(pulls["p5"])

        assert first.values["fuel.rail_pressure_mean"].value is not None
        assert target.values["thermal.iat_delta_k"].value == 4
        assert target.values["history.prior_boost_mean_pa"].value is not None
        assert target.values["temporal_context.prior_pull_count"].value == 2
        assert target.values["history.prior_event_count"].value == 1
        assert target.values["fuel.rail_pressure_mean"].missing_reason.value == "unavailable_signal"
        assert target.values["quality.observation_count"].value == 35
        assert next_configuration.configuration_id == fixture["configurations"]["b"]
        assert next_configuration.values["temporal_context.prior_pull_count"].value == 0
        assert poor_quality.quality_metadata["pull_completeness"] == 0.25

        isolated_version = replace(service.version, version="phase9a-pull-v1-integration")
        isolated_service = FeatureGenerationService(database)
        isolated_service.version = isolated_version
        isolated = await isolated_service.generate_pull(pulls["p3"])
        assert isolated.id != target.id
        assert isolated.feature_set_version == isolated_version.version

        bad_batch = await service.generate_session(
            fixture["sessions"]["first"], observation_cutoff=fixture["start"] - timedelta(days=2)
        )
        assert bad_batch["failed"] == 2

        dataset_definition = DatasetDefinition(
            name=f"phase9a-integration-{uuid4().hex[:10]}",
            version="v1",
            row_scope=EntityScope.PULL,
            feature_set_version=service.version.version,
            selected_features=(
                "raw_context.engine_code",
                "thermal.iat_delta_k",
                "history.prior_boost_mean_pa",
                "history.prior_event_count",
                "quality.observation_count",
            ),
            observation_cutoff=fixture["start"] + timedelta(seconds=60),
            cutoff_policy=CutoffPolicy.ROW_END,
            minimum_quality=0.5,
            allow_configuration_mixing=True,
        )
        builder = DatasetBuilder(database, DEFAULT_REGISTRY)
        built_a = await builder.build(dataset_definition)
        built_b = await builder.build(dataset_definition)
        assert built_a.checksum == built_b.checksum
        assert built_a.manifest["row_count"] == 4
        assert built_a.manifest["excluded_rows_by_reason"]["minimum_quality_not_met"] == 1
        assert built_a.checksum == built_b.checksum

        async with database.session() as db:
            count = await db.scalar(
                text(
                    "SELECT count(*) FROM feature_sets WHERE pull_id=:pull "
                    "AND feature_set_version_id=(SELECT id FROM feature_set_versions WHERE version=:version)"
                ),
                {"pull": pulls["p2"], "version": service.version.version},
            )
            assert count == 1
            version_count = await db.scalar(text("SELECT count(*) FROM feature_set_versions"))
            assert version_count >= 2
            inverted_run_times = await db.scalar(
                text(
                    "SELECT count(*) FROM feature_generation_runs r JOIN feature_sets fs "
                    "ON fs.pull_id=r.requested_entity_id "
                    "AND fs.feature_set_version_id=r.feature_set_version_id "
                    "AND fs.source_hash=r.source_snapshot_hash "
                    "WHERE r.generated_count>0 AND r.started_at>fs.generated_at"
                )
            )
            assert inverted_run_times == 0
    finally:
        await database.close()
