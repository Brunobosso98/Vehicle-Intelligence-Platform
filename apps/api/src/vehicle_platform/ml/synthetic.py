from __future__ import annotations

import asyncio
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text

from vehicle_platform.features.service import FeatureGenerationService
from vehicle_platform.infrastructure.database import Database


@dataclass(frozen=True)
class SyntheticFixture:
    session_ids: tuple[UUID, ...]
    pull_ids: tuple[UUID, ...]
    scenario_family_by_session: dict[str, str]
    held_out_vehicle_id: str
    configuration_ids_by_vehicle: dict[str, tuple[str, str]]


async def seed_predictive_fixture(database: Database) -> SyntheticFixture:
    """Seed canonical telemetry with deterministic observable progression and confounders."""
    start = datetime(2026, 1, 1, tzinfo=UTC)
    model = "N55-9B"
    configuration_ids: dict[str, tuple[UUID, UUID]] = {}
    vehicle_ids: list[UUID] = []
    session_ids: list[UUID] = []
    pull_ids: list[UUID] = []
    scenario_map: dict[str, str] = {}
    telemetry_rows: list[dict[str, Any]] = []
    pull_params: list[dict[str, Any]] = []
    schedule = [
        (round_index, vehicle_index) for round_index in range(5) for vehicle_index in range(7)
    ]
    schedule.extend((round_index, 7) for round_index in range(5))
    session_order = {item: index for index, item in enumerate(schedule)}

    async with database.session() as db:
        for vehicle_index in range(8):
            vehicle_id = (
                await db.execute(
                    text(
                        "INSERT INTO vehicles(manufacturer,model,engine_code,created_at) "
                        "VALUES('BMW',:model,'N55',:created) RETURNING id"
                    ),
                    {
                        "model": f"{model}-{vehicle_index}",
                        "created": start - timedelta(days=60),
                    },
                )
            ).scalar_one()
            vehicle_ids.append(vehicle_id)
            config_a_end = start + timedelta(minutes=2 * session_order[(3, vehicle_index)])
            config_a = (
                await db.execute(
                    text(
                        "INSERT INTO vehicle_configurations(vehicle_id,effective_at,ended_at,description,"  # noqa: E501
                        "metadata,provenance,created_at) VALUES(:vehicle,:effective,:ended,'stock',"
                        "CAST(:metadata AS jsonb),'phase9b-synthetic',:created) RETURNING id"
                    ),
                    {
                        "vehicle": vehicle_id,
                        "effective": start - timedelta(days=30),
                        "ended": config_a_end,
                        "metadata": '{"stage":"stock","fuel_type":"93 AKI"}',
                        "created": start - timedelta(days=30),
                    },
                )
            ).scalar_one()
            config_b = (
                await db.execute(
                    text(
                        "INSERT INTO vehicle_configurations(vehicle_id,effective_at,description,metadata,"  # noqa: E501
                        "provenance,created_at) VALUES(:vehicle,:effective,'stage2',CAST(:metadata AS jsonb),"  # noqa: E501
                        "'phase9b-synthetic',:created) RETURNING id"
                    ),
                    {
                        "vehicle": vehicle_id,
                        "effective": config_a_end,
                        "metadata": '{"stage":"stage2","fuel_type":"93 AKI"}',
                        "created": config_a_end,
                    },
                )
            ).scalar_one()
            configuration_ids[str(vehicle_id)] = (config_a, config_b)

        for session_index, (round_index, vehicle_index) in enumerate(schedule):
            vehicle_id = vehicle_ids[vehicle_index]
            configuration_id = configuration_ids[str(vehicle_id)][round_index // 3]
            at = start + timedelta(minutes=session_index * 2)
            session_id = (
                await db.execute(
                    text(
                        "INSERT INTO driving_sessions(vehicle_id,configuration_id,source_type,started_at,"  # noqa: E501
                        "ended_at,status,metadata,created_at) VALUES(:vehicle,:configuration,'synthetic',"  # noqa: E501
                        ":started,:ended,'completed',CAST(:metadata AS jsonb),:created) RETURNING id"  # noqa: E501
                    ),
                    {
                        "vehicle": vehicle_id,
                        "configuration": configuration_id,
                        "started": at,
                        "ended": at + timedelta(seconds=60),
                        "metadata": '{"data_role":"synthetic","generator":"phase9b-v1"}',
                        "created": start - timedelta(days=29),
                    },
                )
            ).scalar_one()
            session_ids.append(session_id)
            scenario_map[str(session_id)] = (
                "unseen_compound" if session_index >= 24 else "controlled_baseline"
            )
            current_iat = 292.0 + vehicle_index * 0.8 + round_index * 0.15
            fuel_baseline = 15_000_000.0 + vehicle_index * 30_000.0
            current_fuel = fuel_baseline
            previous_fuel_event = False
            # Keep every adjacent RPM sample within Phase 5's 1.0 s continuity
            # limit while preserving a measurable next-pull interval increase.
            base_interval = 0.72 + (vehicle_index % 3) * 0.02
            current_interval = base_interval
            for pull_index in range(5):
                pull_at = at + timedelta(seconds=3 + pull_index * 11)
                thermal_event = _event_flag(vehicle_index, round_index, pull_index, 1)
                performance_event = _event_flag(vehicle_index, round_index, pull_index, 2)
                fuel_event = _event_flag(vehicle_index, round_index, pull_index, 3)
                # Controlled label noise prevents any one sensor from being a perfect proxy.
                if _noise_flag(vehicle_index, round_index, pull_index, 1):
                    thermal_event = not thermal_event
                if _noise_flag(vehicle_index, round_index, pull_index, 2):
                    performance_event = not performance_event
                if _noise_flag(vehicle_index, round_index, pull_index, 3):
                    fuel_event = not fuel_event
                thermal_proxy = thermal_event
                performance_proxy = performance_event
                fuel_proxy = fuel_event
                if _noise_flag(vehicle_index, round_index, pull_index, 9):
                    thermal_proxy = not thermal_proxy
                if _noise_flag(vehicle_index, round_index, pull_index, 10):
                    performance_proxy = not performance_proxy
                if _noise_flag(vehicle_index, round_index, pull_index, 11):
                    fuel_proxy = not fuel_proxy
                # Preserve a controlled high-IAT negative case so the thermal
                # label cannot be learned as a raw temperature threshold.
                if current_iat >= 298.0 and _noise_flag(vehicle_index, round_index, pull_index, 12):
                    thermal_event = False
                    thermal_proxy = False
                current_fuel = fuel_baseline - (4_000_000.0 if previous_fuel_event else 0.0)
                thermal_step = 0.8 + (1.8 if thermal_proxy else 0.0)
                interval_for_pull = current_interval
                if pull_index:
                    interval_for_pull = current_interval
                next_interval = base_interval * (1.14 if performance_event else 1.0)
                next_iat = current_iat + (4.2 if thermal_event else 0.6)
                next_fuel = fuel_baseline - (4_000_000.0 if fuel_event else 0.0)
                boost_base = 112_000.0 + (10_000.0 if performance_proxy else 0.0)
                if _noise_flag(vehicle_index, round_index, pull_index, 4):
                    boost_base += -7_000.0 if performance_proxy else 7_000.0
                boost_pattern = [
                    boost_base - 1_200.0,
                    boost_base + 600.0,
                    boost_base + 1_100.0,
                    boost_base - 300.0,
                    boost_base + 400.0,
                    boost_base - 100.0,
                ]
                # The current pull contains a real pressure decline before some next-pull drops.
                fuel_drop = 1_000_000.0 if fuel_proxy else 120_000.0
                fuel_pattern = [
                    current_fuel,
                    current_fuel - fuel_drop * 0.2,
                    current_fuel - fuel_drop * 0.45,
                    current_fuel - fuel_drop * 0.7,
                    current_fuel - fuel_drop,
                    current_fuel - fuel_drop * 0.8,
                ]
                rpm_times = [
                    0.0,
                    0.4,
                    1.4,
                    1.4 + interval_for_pull,
                    2.4 + interval_for_pull,
                    2.8 + interval_for_pull,
                ]
                pull_duration = max(4.0, rpm_times[-1] + 0.1)
                poor_quality = session_index == 1 and pull_index == 2
                fuel_available = not (session_index == 0 and pull_index == 4)
                rpm_values = [2000.0, 2500.0, 3500.0, 4500.0, 5500.0, 6000.0]
                speed_values = [10.0, 13.0, 17.0, 23.0, 30.0, 35.0]
                sample_values: list[tuple[str, str, float]] = []
                for index in range(6):
                    sample_values.extend(
                        (
                            ("engine.rpm", "rpm", rpm_values[index]),
                            ("vehicle.speed", "m/s", speed_values[index]),
                            ("engine.throttle_position", "%", 92.0 - index * 0.5),
                            ("engine.boost_pressure", "Pa", boost_pattern[index]),
                            (
                                "engine.intake_air_temperature",
                                "K",
                                current_iat + thermal_step * index / 5,
                            ),
                            (
                                "engine.oil_temperature",
                                "K",
                                330.0 + round_index * 0.05 + index * 0.1,
                            ),
                            (
                                "engine.coolant_temperature",
                                "K",
                                335.0 + round_index * 0.03 + index * 0.05,
                            ),
                            ("fuel.high_pressure", "Pa", fuel_pattern[index]),
                        )
                    )
                pull_id = UUID(
                    str(
                        (
                            await db.execute(
                                text(
                                    "INSERT INTO pulls(session_id,started_at,ended_at,duration_ms,confidence,"  # noqa: E501
                                    "detector_name,algorithm_version,configuration_hash,vehicle_id,configuration_id,"
                                    "start_rpm,end_rpm,min_rpm,max_rpm,start_speed,end_speed,max_speed,max_boost,"
                                    "average_boost,start_iat,end_iat,iat_delta,max_oil_temperature,max_coolant_temperature,"
                                    "average_throttle,max_throttle,data_completeness,sample_count,quality_flags,metadata,"
                                    "created_at) VALUES(:session,:started,:ended,:duration,.95,'phase9b-synthetic','1',"  # noqa: E501
                                    ":config_hash,:vehicle,:configuration,2000,6000,2000,6000,10,35,35,:max_boost,"
                                    ":avg_boost,:start_iat,:end_iat,:iat_delta,331,336,90,92,:completeness,6,'{}',"
                                    "CAST(:metadata AS jsonb),:created) RETURNING id"
                                ),
                                {
                                    "session": session_id,
                                    "started": pull_at,
                                    "ended": pull_at + timedelta(seconds=pull_duration),
                                    "duration": int(pull_duration * 1000),
                                    "config_hash": hashlib.sha256(
                                        f"{configuration_id}".encode()
                                    ).hexdigest(),
                                    "vehicle": vehicle_id,
                                    "configuration": configuration_id,
                                    "max_boost": max(boost_pattern),
                                    "avg_boost": math.fsum(boost_pattern) / len(boost_pattern),
                                    "start_iat": current_iat,
                                    "end_iat": current_iat + thermal_step,
                                    "iat_delta": thermal_step,
                                    "completeness": 0.4 if poor_quality else 1.0,
                                    "metadata": json.dumps(
                                        {
                                            "available_signals": [
                                                "engine.rpm",
                                                "vehicle.speed",
                                                "engine.throttle_position",
                                                "engine.boost_pressure",
                                                "engine.intake_air_temperature",
                                                "engine.oil_temperature",
                                                "engine.coolant_temperature",
                                                *(["fuel.high_pressure"] if fuel_available else []),
                                            ]
                                        }
                                    ),
                                    "created": pull_at - timedelta(milliseconds=1),
                                },
                            )
                        ).scalar_one()
                    )
                )
                pull_ids.append(pull_id)
                pull_params.append(
                    {
                        "session_id": session_id,
                        "pull_id": pull_id,
                        "started_at": pull_at,
                        "ended_at": pull_at + timedelta(seconds=pull_duration),
                        "values": sample_values,
                        "times": rpm_times,
                        "boost": boost_pattern,
                        "fuel": fuel_pattern,
                        "iat": current_iat,
                        "thermal_step": thermal_step,
                        "vehicle_id": vehicle_id,
                        "fuel_available": fuel_available,
                    }
                )
                current_iat = next_iat
                current_fuel = next_fuel
                previous_fuel_event = fuel_event
                current_interval = next_interval

        for params in pull_params:
            for index, (signal, unit, value) in enumerate(params["values"]):
                sample_index = index // 8
                if signal == "fuel.high_pressure" and not params["fuel_available"]:
                    continue
                observed_at = params["started_at"] + timedelta(
                    seconds=params["times"][sample_index]
                )
                sample_id = hashlib.sha256(
                    f"{params['pull_id']}:{signal}:{sample_index}".encode()
                ).hexdigest()
                telemetry_rows.append(
                    {
                        "sample_id": sample_id,
                        "vehicle_id": params["vehicle_id"],
                        "session_id": params["session_id"],
                        "observed_at": observed_at,
                        "ingested_at": observed_at,
                        "signal": signal,
                        "value": value,
                        "unit": unit,
                        "raw": str(value),
                        "record": f"{params['pull_id']}:{signal}:{sample_index}",
                        "sequence": sample_index,
                        "quality": "valid",
                        "hash": sample_id,
                    }
                )
        await db.execute(
            text(
                "INSERT INTO telemetry_samples(sample_id,vehicle_id,session_id,observed_at,ingested_at,"  # noqa: E501
                "signal_key,numeric_value,normalized_unit,raw_signal,raw_value,source,source_record_id,"
                "sequence_number,quality,schema_version,content_hash) VALUES(:sample_id,:vehicle_id,:session_id,"  # noqa: E501
                ":observed_at,:ingested_at,:signal,:value,:unit,:signal,:raw,'synthetic',:record,:sequence,"
                ":quality,1,:hash)"
            ),
            telemetry_rows,
        )
        await db.commit()

    return SyntheticFixture(
        tuple(session_ids),
        tuple(pull_ids),
        scenario_map,
        str(vehicle_ids[-1]),
        {
            str(vehicle): (str(configs[0]), str(configs[1]))
            for vehicle, configs in configuration_ids.items()
        },
    )


async def generate_fixture_features(
    database: Database,
    fixture: SyntheticFixture,
    *,
    concurrency: int = 8,
    telemetry: Any | None = None,
) -> None:
    if not 1 <= concurrency <= 16:
        raise ValueError("synthetic feature generation concurrency must be 1..16")
    service = FeatureGenerationService(database, telemetry)
    await service.ensure_version()
    semaphore = asyncio.Semaphore(concurrency)

    async def generate(session_id: UUID) -> None:
        async with semaphore:
            result = await service.generate_session(session_id, max_pulls=5)
        if result["failed"]:
            raise RuntimeError("canonical Phase 9A feature generation failed for synthetic session")

    await asyncio.gather(*(generate(item) for item in fixture.session_ids))


def _event_flag(vehicle: int, round_index: int, pull: int, task: int) -> bool:
    value = (vehicle * 17 + round_index * 11 + pull * 7 + task * 13) % 20
    return value < 10


def _noise_flag(vehicle: int, round_index: int, pull: int, task: int) -> bool:
    value = (vehicle * 19 + round_index * 13 + pull * 11 + task * 17) % 13
    return value in {0, 1, 2}
