"""Independent Phase 9C acceptance over generated Phase 9A FeatureSets and persisted findings."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import resource
import time
import tracemalloc
from collections import Counter
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from vehicle_platform.anomalies.artifacts import AnomalyArtifactError, ArtifactStore
from vehicle_platform.anomalies.definitions import detector_definition
from vehicle_platform.anomalies.detectors import (
    _forest_matrix,
    score_observation,
    transform_features,
)
from vehicle_platform.anomalies.domain import (
    AnomalyStatus,
    DetectorLifecycle,
    DetectorMethod,
    SourceRole,
    finding_idempotency_key,
)
from vehicle_platform.anomalies.evaluation import (
    MethodCandidate,
    classification_metrics,
    select_detector_method,
    select_validation_threshold,
)
from vehicle_platform.anomalies.service import AnomalyService
from vehicle_platform.core.config import Settings
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.service import FeatureGenerationService
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.observability.telemetry import Telemetry

BASE = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
EVIDENCE = Path(".validation/phase9c")
FAMILIES = ("thermal", "boost_air", "performance", "fuel")
METHODS = (DetectorMethod.ROBUST_MAD, DetectorMethod.ISOLATION_FOREST)
HARD_NEGATIVE_SCENARIOS = ("boost_fluctuation", "subtle_multivariate")
MAX_VALIDATION_FPR = 0.25
MIN_VALIDATION_COVERAGE = 0.8
MIN_VALIDATION_RECALL = 0.5
VALIDATION_TARGET_POLICY = {
    "version": "phase9c-controlled-fixture-floors-v1",
    "maximum_clean_false_positive_rate": MAX_VALIDATION_FPR,
    "minimum_eligible_coverage": MIN_VALIDATION_COVERAGE,
    "minimum_injection_recall": MIN_VALIDATION_RECALL,
    "selection_fold": "session 9, target-family injections versus clean controls",
    "initial_frozen_test_fold": "session 12, scored after the session 9 choice is frozen",
    "walk_forward_validation_fold": "session 12, reused only after its first model score is recorded",
    "walk_forward_untouched_test_fold": "session 13, opened after the expanding-window choice is frozen",
    "recovery_sessions": "sessions 10 and 11 contain only clean pulls after validation injections",
    "cross_family_injections": "reported separately from clean false-positive rate",
}
_ACTIVE_DATABASE: Database | None = None
_ACTIVE_TELEMETRY: Telemetry | None = None


@dataclass(frozen=True)
class PullSpec:
    pull_id: UUID
    session_id: UUID
    vehicle_id: UUID
    configuration_id: UUID
    started_at: datetime
    ended_at: datetime
    scenario: str
    duplicate_sample: bool
    fuel_available: bool
    environmental_context_shift: bool = False


@dataclass(frozen=True)
class SeededCohort:
    vehicle_id: UUID
    configuration_a: UUID
    configuration_b: UUID | None
    sessions: tuple[UUID, ...]
    pulls_by_session: tuple[tuple[PullSpec, ...], ...]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _scenario_metrics(
    pulls: tuple[PullSpec, ...],
    scores: tuple[float | None, ...],
    threshold: float,
    *,
    included_scenarios: set[str],
    positive_scenario: str,
) -> dict[str, Any]:
    selected = tuple(
        (score, pull.scenario == positive_scenario)
        for pull, score in zip(pulls, scores, strict=True)
        if pull.scenario in included_scenarios
    )
    return classification_metrics(
        tuple(score for score, _ in selected),
        tuple(label for _, label in selected),
        threshold,
    )


def _clean_control_metrics(
    pulls: tuple[PullSpec, ...],
    scores: tuple[float | None, ...],
    threshold: float,
) -> dict[str, Any]:
    return _scenario_metrics(
        pulls,
        scores,
        threshold,
        included_scenarios={"clean"},
        positive_scenario="__no_positive_scenario__",
    )


def _threshold_sensitivity(
    scores: tuple[float | None, ...],
    labels: tuple[bool, ...],
    initial_threshold: float,
) -> list[dict[str, Any]]:
    thresholds = sorted(
        {initial_threshold} | {float(score) for score in scores if score is not None}
    )
    return [
        {
            "threshold": threshold,
            "metrics": classification_metrics(scores, labels, threshold),
        }
        for threshold in thresholds
    ]


def _injection_alarm_rate(
    pulls: tuple[PullSpec, ...],
    scores: tuple[float | None, ...],
    threshold: float,
    *,
    excluded_scenario: str,
) -> dict[str, Any]:
    selected = tuple(
        (pull, score)
        for pull, score in zip(pulls, scores, strict=True)
        if pull.scenario in FAMILIES and pull.scenario != excluded_scenario
    )
    alarms = sum(score is not None and score > threshold for _, score in selected)
    return {
        "support": len(selected),
        "scored": sum(score is not None for _, score in selected),
        "abstained": sum(score is None for _, score in selected),
        "alarm_count": alarms,
        "alarm_rate": alarms / len(selected) if selected else None,
    }


def _scenarios_for_session(index: int, *, no_fuel: bool) -> tuple[str, ...]:
    if no_fuel:
        return ("clean",) * 5
    if index in {9, 12, 13}:
        scenarios = (
            "clean",
            "clean",
            "clean",
            "clean",
            "thermal",
            "thermal",
            "boost_air",
            "boost_air",
            "performance",
            "performance",
            "fuel",
            "fuel",
            *(("missing_fuel", "quality_duplicate") if index in {12, 13} else ()),
        )
        if index == 13:
            return (*scenarios, *HARD_NEGATIVE_SCENARIOS)
        return scenarios
    if index in {10, 11}:
        return ("clean",) * 5
    if index == 14:
        return ("config_holdout",)
    return ("clean",) * 5


async def _seed_vehicle(
    database: Database,
    *,
    name: str,
    first_day: int,
    session_count: int,
    no_fuel: bool = False,
    vehicle_id: UUID | None = None,
    configuration_id: UUID | None = None,
    configuration_b_id: UUID | None = None,
) -> SeededCohort:
    async with database.session() as db:
        if vehicle_id is None:
            vehicle_id = (
                await db.execute(
                    text(
                        "INSERT INTO vehicles(manufacturer,model,engine_code,created_at) "
                        "VALUES('Fixture','N55-9C-' || :name,'N55',:created) RETURNING id"
                    ),
                    {"name": name, "created": BASE - timedelta(days=100)},
                )
            ).scalar_one()
        if configuration_id is None:
            configuration_id = (
                await db.execute(
                    text(
                        "INSERT INTO vehicle_configurations(vehicle_id,effective_at,ended_at,"
                        "description,metadata,provenance,created_at) VALUES(:vehicle,:effective,"
                        ":ended,'fixture stock',CAST(:metadata AS jsonb),'phase9c-evaluator',:created) "
                        "RETURNING id"
                    ),
                    {
                        "vehicle": vehicle_id,
                        "effective": BASE - timedelta(days=60),
                        "ended": BASE + timedelta(days=first_day + session_count + 2),
                        "metadata": '{"stage":"stock","fuel":"93 AKI"}',
                        "created": BASE - timedelta(days=90),
                    },
                )
            ).scalar_one()
        if configuration_b_id is None and session_count >= 15 and not no_fuel:
            configuration_change_day = first_day + session_count - 1
            configuration_b_id = (
                await db.execute(
                    text(
                        "INSERT INTO vehicle_configurations(vehicle_id,effective_at,description,"
                        "metadata,provenance,created_at) VALUES(:vehicle,:effective,"
                        "'fixture stage change',CAST(:metadata AS jsonb),'phase9c-evaluator',:created) "
                        "RETURNING id"
                    ),
                    {
                        "vehicle": vehicle_id,
                        "effective": BASE + timedelta(days=configuration_change_day),
                        "metadata": '{"stage":"changed","fuel":"93 AKI"}',
                        "created": BASE - timedelta(days=89),
                    },
                )
            ).scalar_one()
            await db.execute(
                text("UPDATE vehicle_configurations SET ended_at=:ended WHERE id=:id"),
                {
                    "ended": BASE + timedelta(days=configuration_change_day),
                    "id": configuration_id,
                },
            )

        sessions: list[UUID] = []
        pulls_by_session: list[tuple[PullSpec, ...]] = []
        pull_rows: list[dict[str, Any]] = []
        sample_rows: list[dict[str, Any]] = []
        for session_index in range(session_count):
            day = first_day + session_index
            session_start = BASE + timedelta(days=day)
            active_vehicle = vehicle_id
            active_configuration = configuration_id
            if session_index == session_count - 1 and configuration_b_id is not None:
                active_configuration = configuration_b_id
            session_id = (
                await db.execute(
                    text(
                        "INSERT INTO driving_sessions(vehicle_id,configuration_id,source_type,"
                        "started_at,ended_at,status,metadata,created_at) VALUES(:vehicle,:config,"
                        "'synthetic',:started,:ended,'completed',CAST(:metadata AS jsonb),:created) "
                        "RETURNING id"
                    ),
                    {
                        "vehicle": active_vehicle,
                        "config": active_configuration,
                        "started": session_start,
                        "ended": session_start + timedelta(minutes=20),
                        "metadata": '{"data_role":"synthetic","generator":"phase9c-evaluator-v1"}',
                        "created": session_start - timedelta(days=40),
                    },
                )
            ).scalar_one()
            sessions.append(session_id)
            pull_specs: list[PullSpec] = []
            for pull_index, scenario in enumerate(
                _scenarios_for_session(session_index, no_fuel=no_fuel)
            ):
                pull_id = UUID(
                    bytes=hashlib.sha256(
                        f"phase9c:{name}:{session_index}:{pull_index}".encode()
                    ).digest()[:16]
                )
                started_at = session_start + timedelta(
                    minutes=1, seconds=pull_index * 10
                )
                severity = "test" if session_index in {12, 13} else "validation"
                values = _pull_values(
                    scenario,
                    session_index=session_index,
                    pull_index=pull_index,
                    severity=severity,
                    no_fuel=no_fuel,
                )
                ended_at = started_at + timedelta(seconds=values["times"][-1] + 0.1)
                duplicate = scenario == "quality_duplicate"
                fuel_available = bool(values["fuel_available"])
                signals = [
                    "engine.rpm",
                    "vehicle.speed",
                    "engine.throttle_position",
                    "engine.boost_pressure",
                    "engine.intake_air_temperature",
                    "engine.oil_temperature",
                    "engine.coolant_temperature",
                    "electrical.battery_voltage",
                    "environment.ambient_air_temperature",
                    "fuel.equivalence_ratio",
                    "fuel.low_pressure",
                    "engine.accelerator_position",
                    "engine.ignition_timing",
                ]
                if fuel_available:
                    signals.append("fuel.high_pressure")
                pull_specs.append(
                    PullSpec(
                        pull_id=pull_id,
                        session_id=session_id,
                        vehicle_id=active_vehicle,
                        configuration_id=active_configuration,
                        started_at=started_at,
                        ended_at=ended_at,
                        scenario=scenario,
                        duplicate_sample=duplicate,
                        fuel_available=fuel_available,
                        environmental_context_shift=session_index == 13,
                    )
                )
                config_hash = hashlib.sha256(
                    str(active_configuration).encode()
                ).hexdigest()
                pull_rows.append(
                    {
                        "id": pull_id,
                        "session": session_id,
                        "started": started_at,
                        "ended": ended_at,
                        "duration": round(
                            (ended_at - started_at).total_seconds() * 1000
                        ),
                        "config_hash": config_hash,
                        "vehicle": active_vehicle,
                        "config": active_configuration,
                        "start_rpm": 2500.0,
                        "end_rpm": 5500.0,
                        "max_rpm": 5500.0,
                        "start_speed": 10.0,
                        "end_speed": 35.0,
                        "max_speed": 35.0,
                        "max_boost": max(values["boost"]),
                        "average_boost": sum(values["boost"]) / len(values["boost"]),
                        "start_iat": values["iat_start"],
                        "end_iat": values["iat_start"] + values["iat_delta"],
                        "iat_delta": values["iat_delta"],
                        "completeness": 1.0,
                        "sample_count": len(values["times"]) * len(values["signals"]),
                        "metadata": json.dumps({"available_signals": signals}),
                        "created": started_at - timedelta(milliseconds=1),
                    }
                )
                for signal, unit, signal_values in values["signals"]:
                    for sample_index, sample_value in enumerate(signal_values):
                        observed_at = started_at + timedelta(
                            seconds=values["times"][sample_index]
                        )
                        sample_id = hashlib.sha256(
                            f"{pull_id}:{signal}:{sample_index}".encode()
                        ).hexdigest()
                        sample_rows.append(
                            {
                                "sample": sample_id,
                                "vehicle": active_vehicle,
                                "session": session_id,
                                "observed": observed_at,
                                "ingested": observed_at,
                                "signal": signal,
                                "value": sample_value,
                                "unit": unit,
                                "raw": str(sample_value),
                                "record": f"{pull_id}:{signal}:{sample_index}",
                                "sequence": sample_index,
                                "hash": sample_id,
                            }
                        )
                        if (
                            duplicate
                            and signal == "vehicle.speed"
                            and sample_index == 4
                        ):
                            duplicate_id = hashlib.sha256(
                                f"{sample_id}:duplicate".encode()
                            ).hexdigest()
                            sample_rows.append(
                                {
                                    **sample_rows[-1],
                                    "sample": duplicate_id,
                                    "record": f"{pull_id}:duplicate-speed",
                                    "sequence": sample_index + 100,
                                    "hash": duplicate_id,
                                }
                            )
            pulls_by_session.append(tuple(pull_specs))

        await db.execute(
            text(
                "INSERT INTO pulls(id,session_id,started_at,ended_at,duration_ms,confidence,"
                "detector_name,algorithm_version,configuration_hash,vehicle_id,configuration_id,"
                "start_rpm,end_rpm,max_rpm,start_speed,end_speed,max_speed,max_boost,average_boost,"
                "start_iat,end_iat,iat_delta,data_completeness,sample_count,metadata,created_at) "
                "VALUES(:id,:session,:started,:ended,:duration,.95,'phase9c-evaluator','1',"
                ":config_hash,:vehicle,:config,:start_rpm,:end_rpm,:max_rpm,:start_speed,:end_speed,"
                ":max_speed,:max_boost,:average_boost,:start_iat,:end_iat,:iat_delta,:completeness,"
                ":sample_count,CAST(:metadata AS jsonb),:created)"
            ),
            pull_rows,
        )
        await db.execute(
            text(
                "INSERT INTO telemetry_samples(sample_id,vehicle_id,session_id,observed_at,ingested_at,"
                "signal_key,numeric_value,normalized_unit,raw_signal,raw_value,source,source_record_id,"
                "sequence_number,quality,schema_version,content_hash) VALUES(:sample,:vehicle,:session,"
                ":observed,:ingested,:signal,:value,:unit,:signal,:raw,'synthetic',:record,:sequence,"
                "'valid',1,:hash)"
            ),
            sample_rows,
        )
        await db.commit()
    return SeededCohort(
        vehicle_id=vehicle_id,
        configuration_a=configuration_id,
        configuration_b=configuration_b_id,
        sessions=tuple(sessions),
        pulls_by_session=tuple(pulls_by_session),
    )


def _pull_values(
    scenario: str,
    *,
    session_index: int,
    pull_index: int,
    severity: str,
    no_fuel: bool,
) -> dict[str, Any]:
    temperature_offset = session_index * 0.22 + pull_index * 0.025
    if session_index == 13:
        # An unseen session-wide ambient/IAT level shift with ordinary within-pull behavior.
        # It is deliberately not an anomaly label or a model input.
        temperature_offset += 12.0
    iat_start = 290.0 + temperature_offset
    iat_delta = 2.0 + ((session_index + pull_index) % 4) * 0.08
    boost_base = 115_000.0 + ((session_index * 7 + pull_index * 3) % 9 - 4) * 180.0
    fuel_base = (
        15_000_000.0 + ((session_index * 11 + pull_index * 5) % 9 - 4) * 20_000.0
    )
    interval = 0.90 + ((session_index + pull_index) % 5 - 2) * 0.015
    fuel_available = not (no_fuel or scenario == "missing_fuel")
    if scenario == "thermal":
        iat_delta += 11.0 if severity == "validation" else 8.8
    elif scenario == "boost_air":
        boost_base += 32_000.0 if severity == "validation" else 22_000.0
    elif scenario == "performance":
        interval = 2.1 if severity == "validation" else 1.9
    elif scenario == "fuel":
        fuel_base -= 4_500_000.0 if severity == "validation" else 4_000_000.0
    elif scenario == "boost_fluctuation":
        pass
    elif scenario == "subtle_multivariate":
        iat_delta += 0.65
        boost_base += 900.0
        interval += 0.12

    times = [
        0.0,
        0.4,
        0.8,
        0.8 + interval * 0.25,
        0.8 + interval * 0.5,
        0.8 + interval * 0.75,
        0.8 + interval,
        1.2 + interval,
        1.6 + interval,
    ]
    rpm = [2500.0, 3000.0, 3500.0, 3750.0, 4000.0, 4250.0, 4500.0, 5000.0, 5500.0]
    speed = [10.0 + (item - 2500.0) / 120.0 for item in rpm]
    if scenario == "boost_fluctuation":
        boost = [
            boost_base + (-1.0 if index % 2 else 1.0) * 3_000.0
            for index in range(len(times))
        ]
    else:
        boost = [
            boost_base + ((index * 7) % 5 - 2) * 250.0 for index in range(len(times))
        ]
    iat = [
        iat_start + iat_delta * index / (len(times) - 1) for index in range(len(times))
    ]
    oil = [330.0 + session_index * 0.05 + index * 0.08 for index in range(len(times))]
    coolant = [
        335.0 + session_index * 0.03 + index * 0.04 for index in range(len(times))
    ]
    fuel = [
        fuel_base - index * (30_000.0 + pull_index * 800.0)
        for index in range(len(times))
    ]
    ambient = [288.0 + temperature_offset + index * 0.01 for index in range(len(times))]
    low_pressure = [520_000.0 - index * 350.0 for index in range(len(times))]
    signals: list[tuple[str, str, list[float]]] = [
        ("engine.rpm", "rpm", rpm),
        ("vehicle.speed", "m/s", speed),
        (
            "engine.throttle_position",
            "%",
            [92.0 - index * 0.25 for index in range(len(times))],
        ),
        ("engine.boost_pressure", "Pa", boost),
        ("engine.intake_air_temperature", "K", iat),
        ("engine.oil_temperature", "K", oil),
        ("engine.coolant_temperature", "K", coolant),
        ("electrical.battery_voltage", "V", [13.8] * len(times)),
        ("environment.ambient_air_temperature", "K", ambient),
        ("fuel.equivalence_ratio", "ratio", [1.0] * len(times)),
        ("fuel.low_pressure", "Pa", low_pressure),
        (
            "engine.accelerator_position",
            "%",
            [92.0 - index * 0.25 for index in range(len(times))],
        ),
        (
            "engine.ignition_timing",
            "deg",
            [10.0 - index * 0.1 for index in range(len(times))],
        ),
    ]
    if fuel_available:
        signals.append(("fuel.high_pressure", "Pa", fuel))
    return {
        "times": times,
        "boost": boost,
        "iat_start": iat_start,
        "iat_delta": iat_delta,
        "fuel_available": fuel_available,
        "signals": signals,
    }


async def _generate_feature_sets(
    database: Database, cohorts: tuple[SeededCohort, ...]
) -> dict[str, float]:
    service = FeatureGenerationService(database)
    await service.ensure_version()
    timings: dict[str, float] = {}
    sessions = sorted(
        {session_id for cohort in cohorts for session_id in cohort.sessions},
        key=str,
    )
    async with database.session() as db:
        session_order = {
            row.id: row.started_at
            for row in (
                await db.execute(
                    text(
                        "SELECT id,started_at FROM driving_sessions WHERE id=ANY(:ids)"
                    ),
                    {"ids": sessions},
                )
            ).all()
        }
    for session_id in sorted(sessions, key=lambda item: session_order[item]):
        started = time.perf_counter()
        result = await service.generate_session(session_id, max_pulls=100)
        elapsed = time.perf_counter() - started
        if result["failed"]:
            raise AssertionError(
                f"Phase 9A generation failed: {result['error_categories']}"
            )
        timings[str(session_id)] = elapsed
    return timings


async def _inject_temporal_leakage_adversaries(
    database: Database, cohort: SeededCohort
) -> dict[str, Any]:
    """Insert deliberately late telemetry and metadata before canonical feature generation."""
    target = cohort.pulls_by_session[13][0]
    late_sample_id = hashlib.sha256(
        f"phase9c-late-sample:{target.pull_id}".encode()
    ).hexdigest()
    late_ingested_at = target.ended_at + timedelta(days=1)
    future_modification_id = uuid4()
    future_modification_created_at = target.ended_at + timedelta(days=30)
    async with database.session() as db:
        await db.execute(
            text(
                "INSERT INTO telemetry_samples(sample_id,vehicle_id,session_id,observed_at,"
                "ingested_at,signal_key,numeric_value,normalized_unit,raw_signal,raw_value,"
                "source,source_record_id,sequence_number,quality,schema_version,content_hash) "
                "VALUES(:sample,:vehicle,:session,:observed,:ingested,'engine.boost_pressure',"
                "400000.0,'Pa','engine.boost_pressure','400000','synthetic',:record,999,'valid',1,:hash)"
            ),
            {
                "sample": late_sample_id,
                "vehicle": target.vehicle_id,
                "session": target.session_id,
                "observed": target.started_at + timedelta(seconds=0.4),
                "ingested": late_ingested_at,
                "record": f"phase9c-late:{target.pull_id}",
                "hash": late_sample_id,
            },
        )
        await db.execute(
            text(
                "INSERT INTO modifications(id,vehicle_id,configuration_id,category,manufacturer,"
                "product,installed_at,removed_at,notes,created_at) VALUES(:id,:vehicle,:configuration,"
                "'intake','Synthetic','post-cutoff intake',:installed,NULL,'leakage sentinel',:created)"
            ),
            {
                "id": future_modification_id,
                "vehicle": target.vehicle_id,
                "configuration": target.configuration_id,
                "installed": target.started_at - timedelta(days=1),
                "created": future_modification_created_at,
            },
        )
        await db.commit()
    return {
        "pull_id": target.pull_id,
        "late_sample_id": late_sample_id,
        "late_sample_observed_at": target.started_at + timedelta(seconds=0.4),
        "late_sample_ingested_at": late_ingested_at,
        "future_modification_id": future_modification_id,
        "future_modification_created_at": future_modification_created_at,
    }


async def _verify_temporal_leakage_adversaries(
    database: Database, adversaries: dict[str, Any]
) -> dict[str, Any]:
    async with database.session() as db:
        row = (
            (
                await db.execute(
                    text(
                        "SELECT fs.observation_cutoff,"
                        "fs.feature_values #>> '{boost_air.pressure_max,value}' AS boost_max,"
                        "fs.provenance #> '{source_context,active_modification_ids}' AS modification_ids "
                        "FROM feature_sets fs WHERE fs.pull_id=:pull ORDER BY fs.generated_at DESC LIMIT 1"
                    ),
                    {"pull": adversaries["pull_id"]},
                )
            )
            .mappings()
            .one()
        )
    observation_cutoff = row["observation_cutoff"]
    boost_max = float(row["boost_max"])
    modification_ids = tuple(str(item) for item in row["modification_ids"])
    late_sample_excluded = (
        adversaries["late_sample_observed_at"] <= observation_cutoff
        and adversaries["late_sample_ingested_at"] > observation_cutoff
        and boost_max < 200_000.0
    )
    future_modification_excluded = (
        adversaries["future_modification_created_at"] > observation_cutoff
        and str(adversaries["future_modification_id"]) not in modification_ids
    )
    _assert(
        late_sample_excluded, "late-ingested extreme telemetry influenced a FeatureSet"
    )
    _assert(
        future_modification_excluded,
        "post-cutoff modification influenced a FeatureSet cohort",
    )
    return {
        "late_sample_observed_before_cutoff": True,
        "late_sample_ingested_after_cutoff": True,
        "late_sample_excluded_from_canonical_feature_set": late_sample_excluded,
        "materialized_boost_pressure_max_pa": boost_max,
        "post_cutoff_modification_excluded_from_feature_context": future_modification_excluded,
    }


async def _verify_failed_persistence_rolls_back(
    database: Database,
    service: AnomalyService,
    *,
    detector_version_id: UUID,
    pull: PullSpec,
    observation_cutoff: datetime,
) -> dict[str, Any]:
    metadata = await service._load_version_metadata(detector_version_id)
    artifact = await service.artifacts.load_registered(
        database, str(detector_version_id)
    )
    rows = await service.repository.load_targets(
        (pull.pull_id,), observation_cutoff, artifact.definition
    )
    _assert(len(rows) == 1, "rollback probe FeatureSet is unavailable")
    observation = rows[0]
    finding = score_observation(
        artifact.definition,
        artifact.fitted,
        observation,
        observation_cutoff=observation_cutoff,
    )
    identity = finding_idempotency_key(
        detector_version_id=detector_version_id,
        observation=observation,
        observation_cutoff=observation_cutoff,
        scoring_version=artifact.definition.scoring_version,
        threshold=finding.threshold,
    )
    invalid_finding = replace(
        finding,
        contributions=({"oversized_rollback_probe": "x" * 20_000},),
    )
    run_identity = stable_hash(
        ["phase9c-rollback-probe", detector_version_id, pull.pull_id]
    )
    write_failed = False
    try:
        await service.registry.persist_run(
            run_identity=run_identity,
            detector_version_id=detector_version_id,
            reference_dataset_id=UUID(str(metadata["reference_dataset_id"])),
            observation_cutoff=observation_cutoff,
            source_role=SourceRole.SYNTHETIC,
            input_checksum=stable_hash(["rollback-input", identity]),
            artifact_checksum=str(metadata["artifact_checksum"]),
            requested_count=1,
            findings=((observation, invalid_finding, identity),),
            summary={
                "schema_version": "phase9c-rollback-probe-v1",
                "family": artifact.definition.family.value,
                "method": artifact.definition.method.value,
                "reference_dataset_id": str(metadata["reference_dataset_id"]),
                "reference_checksum": artifact.reference_checksum,
                "cohort_checksum": artifact.cohort.checksum,
            },
            duration_seconds=0.0,
        )
    except SQLAlchemyError:
        write_failed = True
    _assert(write_failed, "invalid oversized finding unexpectedly persisted")
    async with database.session() as db:
        persisted_runs = await db.scalar(
            text(
                "SELECT count(*) FROM anomaly_detection_runs WHERE run_identity=:identity"
            ),
            {"identity": run_identity},
        )
    _assert(persisted_runs == 0, "failed finding write left a partially committed run")
    return {
        "oversized_finding_write_rejected": write_failed,
        "detection_run_rolled_back": persisted_runs == 0,
        "run_identity": run_identity,
    }


async def _finding_details(
    database: Database, finding_ids: tuple[UUID, ...]
) -> dict[UUID, dict[str, Any]]:
    async with database.session() as db:
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT id,pull_id,status,score,threshold,coverage,reason_codes,"
                        "contributions,observation_cutoff FROM anomaly_findings WHERE id=ANY(:ids)"
                    ),
                    {"ids": list(finding_ids)},
                )
            )
            .mappings()
            .all()
        )
    return {UUID(str(row["id"])): dict(row) for row in rows}


async def _candidate_validation(
    database: Database,
    service: AnomalyService,
    cohort: SeededCohort,
    family: str,
    method: DetectorMethod,
    anchor: PullSpec,
    validation: tuple[PullSpec, ...],
    telemetry: Telemetry,
) -> dict[str, Any]:
    started = time.perf_counter()
    fit = await service.fit_detector_version(
        anchor_pull_id=anchor.pull_id,
        observation_cutoff=anchor.ended_at + timedelta(seconds=1),
        source_role=SourceRole.SYNTHETIC,
        family=family,
        method=method.value,
        git_sha="phase9c-evaluator",
    )
    fit_seconds = time.perf_counter() - started
    _assert(
        fit.state is DetectorLifecycle.CANDIDATE,
        f"{family}/{method.value} fit rejected",
    )
    validation_cutoff = max(item.ended_at for item in validation) + timedelta(seconds=1)
    score_started = time.perf_counter()
    run = await service.score_detector_version(
        detector_version_id=fit.detector_version_id,
        pull_ids=tuple(item.pull_id for item in validation),
        observation_cutoff=validation_cutoff,
        source_role=SourceRole.SYNTHETIC,
    )
    score_seconds = time.perf_counter() - score_started
    details = await _finding_details(database, run.finding_ids)
    score_by_pull = {
        UUID(str(details[finding_id]["pull_id"])): details[finding_id]["score"]
        for finding_id in run.finding_ids
    }
    scores = tuple(
        float(score_by_pull[item.pull_id])
        if score_by_pull.get(item.pull_id) is not None
        else None
        for item in validation
    )
    selection_indexes = tuple(
        index
        for index, item in enumerate(validation)
        if item.scenario in {"clean", family}
    )
    selection_scores = tuple(scores[index] for index in selection_indexes)
    selection_labels = tuple(
        validation[index].scenario == family for index in selection_indexes
    )
    with telemetry.tracer.start_as_current_span("anomaly.threshold.selection") as span:
        span.set_attribute("detector.family", family)
        span.set_attribute("detector.method", method.value)
        span.set_attribute("validation.observation_count", len(selection_indexes))
        threshold_result = select_validation_threshold(
            scores=selection_scores,
            labels=selection_labels,
            initial_threshold=float(fit.threshold or 0.0),
            maximum_clean_false_positive_rate=MAX_VALIDATION_FPR,
            minimum_coverage=MIN_VALIDATION_COVERAGE,
            minimum_injection_recall=MIN_VALIDATION_RECALL,
        )
    validation_scenario_metrics = _scenario_metrics(
        validation,
        scores,
        float(threshold_result.threshold),
        included_scenarios={"clean", *FAMILIES},
        positive_scenario=family,
    )
    return {
        "fit": fit,
        "fit_seconds": fit_seconds,
        "score_seconds": score_seconds,
        "validation_run": run,
        "validation_scores": scores,
        "validation_labels": tuple(item.scenario == family for item in validation),
        "validation_scenario_metrics": validation_scenario_metrics,
        "validation_selection_support": len(selection_indexes),
        "threshold_sensitivity_validation_only": _threshold_sensitivity(
            selection_scores, selection_labels, float(fit.threshold or 0.0)
        ),
        "threshold": threshold_result,
        "validation_metrics": threshold_result.metrics,
    }


async def evaluate() -> dict[str, Any]:
    global _ACTIVE_DATABASE, _ACTIVE_TELEMETRY
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError("acceptance requires the disposable vehicle_test database")
    settings = Settings(database_url=SecretStr(url), environment="test")
    database = Database(settings)
    _ACTIVE_DATABASE = database
    span_exporter = InMemorySpanExporter()
    telemetry = Telemetry(settings, database)
    _ACTIVE_TELEMETRY = telemetry
    telemetry.traces.add_span_processor(SimpleSpanProcessor(span_exporter))
    primary = await _seed_vehicle(
        database, name="primary", first_day=0, session_count=15
    )
    second_vehicle = None
    second_config = None
    async with database.session() as db:
        second_vehicle = (
            await db.execute(
                text(
                    "INSERT INTO vehicles(manufacturer,model,engine_code,created_at) "
                    "VALUES('Fixture','N55-9C-holdout','N55',:created) RETURNING id"
                ),
                {"created": BASE - timedelta(days=100)},
            )
        ).scalar_one()
        second_config = (
            await db.execute(
                text(
                    "INSERT INTO vehicle_configurations(vehicle_id,effective_at,description,metadata,"
                    "provenance,created_at) VALUES(:vehicle,:effective,'fixture holdout',"
                    "CAST(:metadata AS jsonb),'phase9c-evaluator',:created) RETURNING id"
                ),
                {
                    "vehicle": second_vehicle,
                    "effective": BASE - timedelta(days=60),
                    "metadata": '{"stage":"stock","fuel":"93 AKI"}',
                    "created": BASE - timedelta(days=90),
                },
            )
        ).scalar_one()
        await db.commit()
    holdout = await _seed_vehicle(
        database,
        name="held-vehicle",
        first_day=13,
        session_count=1,
        vehicle_id=second_vehicle,
        configuration_id=second_config,
    )
    no_fuel = await _seed_vehicle(
        database, name="without-fuel", first_day=30, session_count=10, no_fuel=True
    )
    cohorts = (primary, holdout, no_fuel)
    temporal_adversaries = await _inject_temporal_leakage_adversaries(database, primary)
    generation_timings = await _generate_feature_sets(database, cohorts)
    temporal_adversary_results = await _verify_temporal_leakage_adversaries(
        database, temporal_adversaries
    )

    artifact_root = EVIDENCE / f"artifacts-{uuid4().hex}"
    service = AnomalyService(
        database,
        artifacts=ArtifactStore(artifact_root),
        telemetry=telemetry,
    )
    anchor = primary.pulls_by_session[8][0]
    validation = primary.pulls_by_session[9]
    test_folds = {
        "session_12": primary.pulls_by_session[12],
        "session_13": primary.pulls_by_session[13],
    }
    test_targets = tuple(item for fold in test_folds.values() for item in fold)
    target_cutoff = max(item.ended_at for item in test_targets) + timedelta(seconds=1)
    fits: dict[str, dict[DetectorMethod, dict[str, Any]]] = {}
    fit_seconds: dict[str, float] = {}
    for family in FAMILIES:
        fits[family] = {}
        for method in METHODS:
            result = await _candidate_validation(
                database,
                service,
                primary,
                family,
                method,
                anchor,
                validation,
                telemetry,
            )
            fits[family][method] = result
            fit_seconds[f"{family}/{method.value}"] = result["fit_seconds"]

    selection: dict[str, Any] = {}
    frozen_versions: dict[str, dict[DetectorMethod, UUID]] = {}
    for family, methods in fits.items():
        candidates = tuple(
            MethodCandidate(
                method=method,
                threshold=float(result["threshold"].threshold),
                validation_metrics=result["validation_metrics"],
            )
            for method, result in methods.items()
        )
        passing_candidates = tuple(
            item for item in candidates if methods[item.method]["threshold"].accepted
        )
        _assert(
            bool(passing_candidates),
            f"{family} has no validation threshold meeting the predeclared floors",
        )
        selected = select_detector_method(
            passing_candidates,
            maximum_clean_false_positive_rate=MAX_VALIDATION_FPR,
            minimum_coverage=MIN_VALIDATION_COVERAGE,
        )
        selection[family] = {
            "selected_method": selected.method.value,
            "method_selection_reason": (
                "validation injection recall/precision with clean false-positive and coverage floors; "
                "robust baseline wins exact ties"
            ),
            "candidates": {
                method.value: {
                    "threshold": float(result["threshold"].threshold),
                    "threshold_floors_met": result["threshold"].accepted,
                    "validation_metrics": result["validation_metrics"],
                    "validation_all_injection_scenario_metrics": result[
                        "validation_scenario_metrics"
                    ],
                    "validation_selection_support": result[
                        "validation_selection_support"
                    ],
                    "threshold_sensitivity_validation_only": result[
                        "threshold_sensitivity_validation_only"
                    ],
                    "fit_seconds": result["fit_seconds"],
                    "validation_score_seconds": result["score_seconds"],
                }
                for method, result in methods.items()
            },
        }
        frozen_versions[family] = {}
        for method, result in methods.items():
            manifest = {
                "policy": VALIDATION_TARGET_POLICY,
                "family": family,
                "method": method.value,
                "threshold": float(result["threshold"].threshold),
                "validation_metrics": result["validation_metrics"],
                "validation_all_injection_scenario_metrics": result[
                    "validation_scenario_metrics"
                ],
                "threshold_sensitivity_validation_only": result[
                    "threshold_sensitivity_validation_only"
                ],
                "selected_method": selected.method.value,
            }
            evidence_checksum = stable_hash(
                {
                    "family": family,
                    "method": method.value,
                    "scores": result["validation_scores"],
                    "labels": result["validation_labels"],
                    "manifest": manifest,
                }
            )
            frozen = await service.freeze_validation_threshold(
                detector_version_id=result["fit"].detector_version_id,
                threshold=float(result["threshold"].threshold),
                validation_checksum=evidence_checksum,
                selection_manifest=manifest,
                accepted=method is selected.method,
                git_sha="phase9c-evaluator",
            )
            frozen_versions[family][method] = frozen.detector_version_id
            if method is selected.method:
                _assert(
                    frozen.state is DetectorLifecycle.ACCEPTED,
                    "selected detector was not accepted",
                )

    test_results: dict[str, Any] = {}
    accepted_replay: dict[str, Any] = {}
    for family, frozen_by_method in frozen_versions.items():
        test_results[family] = {}
        for method, version_id in frozen_by_method.items():
            run = await service.score_detector_version(
                detector_version_id=version_id,
                pull_ids=tuple(item.pull_id for item in test_targets),
                observation_cutoff=target_cutoff,
                source_role=SourceRole.SYNTHETIC,
            )
            details = await _finding_details(database, run.finding_ids)
            scores_by_pull = {
                UUID(str(details[finding_id]["pull_id"])): details[finding_id]["score"]
                for finding_id in run.finding_ids
            }
            statuses_by_pull = {
                UUID(str(details[finding_id]["pull_id"])): details[finding_id]["status"]
                for finding_id in run.finding_ids
            }
            thresholds_by_pull = {
                UUID(str(details[finding_id]["pull_id"])): details[finding_id][
                    "threshold"
                ]
                for finding_id in run.finding_ids
            }
            reasons_by_pull = {
                UUID(str(details[finding_id]["pull_id"])): details[finding_id][
                    "reason_codes"
                ]
                for finding_id in run.finding_ids
            }
            contributions_by_pull = {
                UUID(str(details[finding_id]["pull_id"])): details[finding_id][
                    "contributions"
                ]
                for finding_id in run.finding_ids
            }
            scores = tuple(
                float(scores_by_pull[item.pull_id])
                if scores_by_pull.get(item.pull_id) is not None
                else None
                for item in test_targets
            )
            threshold = float(fits[family][method]["threshold"].threshold)
            metrics = _scenario_metrics(
                test_targets,
                scores,
                threshold,
                included_scenarios={"clean", family},
                positive_scenario=family,
            )
            all_family_metrics = _scenario_metrics(
                test_targets,
                scores,
                threshold,
                included_scenarios={"clean", *FAMILIES},
                positive_scenario=family,
            )
            clean_metrics = _clean_control_metrics(test_targets, scores, threshold)
            cross_family_metrics = _injection_alarm_rate(
                test_targets,
                scores,
                threshold,
                excluded_scenario=family,
            )
            _assert(
                metrics["positive_support"] == 4 and metrics["negative_support"] == 8,
                f"{family}/{method.value} target-versus-clean denominator changed",
            )
            _assert(
                all_family_metrics["support"] == 24
                and cross_family_metrics["support"] == 12,
                f"{family}/{method.value} all-family denominators changed",
            )
            fold_metrics: dict[str, Any] = {}
            start_index = 0
            for fold_name, fold_pulls in test_folds.items():
                end_index = start_index + len(fold_pulls)
                fold_scores = scores[start_index:end_index]
                fold_metrics[fold_name] = {
                    "target_family_vs_clean": _scenario_metrics(
                        fold_pulls,
                        fold_scores,
                        threshold,
                        included_scenarios={"clean", family},
                        positive_scenario=family,
                    ),
                    "clean_controls": _clean_control_metrics(
                        fold_pulls, fold_scores, threshold
                    ),
                    "all_family_injections": _scenario_metrics(
                        fold_pulls,
                        fold_scores,
                        threshold,
                        included_scenarios={"clean", *FAMILIES},
                        positive_scenario=family,
                    ),
                    "cross_family_injection_alarms": _injection_alarm_rate(
                        fold_pulls,
                        fold_scores,
                        threshold,
                        excluded_scenario=family,
                    ),
                }
                start_index = end_index
            quality_controls = [
                {
                    "scenario": item.scenario,
                    "status": statuses_by_pull.get(item.pull_id, "NO_FINDING"),
                }
                for item in test_targets
                if item.scenario in {"missing_fuel", "quality_duplicate"}
            ]
            case_evaluation = []
            for index, item in enumerate(test_targets):
                score_value = scores[index]
                case_evaluation.append(
                    {
                        "fold": (
                            "session_12"
                            if index < len(test_folds["session_12"])
                            else "session_13"
                        ),
                        "scenario": item.scenario,
                        "environmental_context_shift": item.environmental_context_shift,
                        "status": statuses_by_pull.get(item.pull_id, "NO_FINDING"),
                        "score": score_value,
                        "threshold": thresholds_by_pull.get(item.pull_id),
                        "reason_codes": reasons_by_pull.get(item.pull_id, []),
                        "top_associated_features": contributions_by_pull.get(
                            item.pull_id, []
                        )[:3],
                        "predicted_anomaly": (
                            score_value > threshold if score_value is not None else None
                        ),
                        "evaluation_role": (
                            "target_vs_clean"
                            if item.scenario in {"clean", family}
                            else "held_out_hard_negative"
                            if item.scenario in HARD_NEGATIVE_SCENARIOS
                            else "cross_family_or_quality_control"
                        ),
                    }
                )
            test_results[family][method.value] = {
                "threshold_frozen_on_validation": threshold,
                "target_family_vs_clean_metrics": metrics,
                "clean_control_metrics": clean_metrics,
                "all_family_injection_metrics": all_family_metrics,
                "cross_family_injection_alarm_rate": cross_family_metrics,
                "quality_control_statuses": quality_controls,
                "case_evaluation": case_evaluation,
                "temporal_test_fold_metrics": fold_metrics,
                "run_id": str(run.run_id),
                "input_checksum": run.input_checksum,
                "artifact_checksum": run.artifact_checksum,
                "requested": run.requested_count,
                "finding_status_counts": run.status_counts,
                "idempotent_initial_run": run.idempotent_replay,
                "service_score_seconds": run.duration_seconds,
                "target_database_read_seconds": run.target_read_seconds,
                "finding_database_persistence_seconds": run.finding_persistence_seconds,
            }
            if method.value == selection[family]["selected_method"]:
                replay = await service.score_detector_version(
                    detector_version_id=version_id,
                    pull_ids=tuple(item.pull_id for item in test_targets),
                    observation_cutoff=target_cutoff,
                    source_role=SourceRole.SYNTHETIC,
                )
                _assert(
                    replay.idempotent_replay,
                    "re-scoring did not return an idempotent replay",
                )
                _assert(
                    replay.run_id == run.run_id,
                    "replay created a different detection run",
                )
                _assert(
                    replay.finding_ids == run.finding_ids,
                    "replay changed immutable finding IDs",
                )
                accepted_replay[family] = {
                    "same_run_id": replay.run_id == run.run_id,
                    "same_finding_ids": replay.finding_ids == run.finding_ids,
                    "idempotent": replay.idempotent_replay,
                }

    missing_fuel_statuses = [
        item["status"]
        for method_result in test_results["fuel"].values()
        for item in method_result["quality_control_statuses"]
        if item["scenario"] == "missing_fuel"
    ]
    duplicate_quality_statuses = [
        item["status"]
        for family_result in test_results.values()
        for method_result in family_result.values()
        for item in method_result["quality_control_statuses"]
        if item["scenario"] == "quality_duplicate"
    ]
    _assert(
        bool(missing_fuel_statuses)
        and all(
            status == AnomalyStatus.INSUFFICIENT_SIGNAL.value
            for status in missing_fuel_statuses
        ),
        "a missing fuel signal did not abstain as insufficient signal",
    )
    _assert(
        bool(duplicate_quality_statuses)
        and all(
            status == AnomalyStatus.LOW_QUALITY.value
            for status in duplicate_quality_statuses
        ),
        "duplicated telemetry did not abstain as low quality",
    )

    selected_validation = {
        family: selection[family]["selected_method"] for family in FAMILIES
    }
    selected_test = {
        family: test_results[family][DetectorMethod(selected_validation[family]).value][
            "target_family_vs_clean_metrics"
        ]
        for family in FAMILIES
    }
    heldout_stress_suite: dict[str, dict[str, Any]] = {}
    for family in FAMILIES:
        heldout_stress_suite[family] = {}
        for method in METHODS:
            cases = test_results[family][method.value]["case_evaluation"]
            environmental_controls = [
                item
                for item in cases
                if item["scenario"] == "clean" and item["environmental_context_shift"]
            ]
            environment_scored = [
                item for item in environmental_controls if item["score"] is not None
            ]
            heldout_stress_suite[family][method.value] = {
                "environmental_context_shift_clean_controls": {
                    "support": len(environmental_controls),
                    "scored": len(environment_scored),
                    "abstained": len(environmental_controls) - len(environment_scored),
                    "false_positives": sum(
                        item["predicted_anomaly"] is True for item in environment_scored
                    ),
                    "false_positive_rate": (
                        sum(
                            item["predicted_anomaly"] is True
                            for item in environment_scored
                        )
                        / len(environment_scored)
                        if environment_scored
                        else None
                    ),
                    "cases": environmental_controls,
                },
                "unseen_interventions": {
                    scenario: [item for item in cases if item["scenario"] == scenario]
                    for scenario in HARD_NEGATIVE_SCENARIOS
                },
            }

    # Expanding-window check: the second model uses only history before session 11,
    # selects on session 12, then scores the untouched session 13.
    walkforward_anchor = primary.pulls_by_session[11][0]
    walkforward_validation = primary.pulls_by_session[12]
    walkforward_test = primary.pulls_by_session[13]
    walkforward_candidates: dict[str, dict[DetectorMethod, dict[str, Any]]] = {}
    walkforward_selection: dict[str, Any] = {}
    walkforward_versions: dict[str, dict[DetectorMethod, UUID]] = {}
    for family in FAMILIES:
        walkforward_candidates[family] = {}
        for method in METHODS:
            result = await _candidate_validation(
                database,
                service,
                primary,
                family,
                method,
                walkforward_anchor,
                walkforward_validation,
                telemetry,
            )
            walkforward_candidates[family][method] = result
        passing = tuple(
            MethodCandidate(
                method=method,
                threshold=float(result["threshold"].threshold),
                validation_metrics=result["validation_metrics"],
            )
            for method, result in walkforward_candidates[family].items()
            if walkforward_candidates[family][method]["threshold"].accepted
        )
        _assert(
            bool(passing),
            f"walk-forward {family} has no validation candidate meeting the predeclared floors",
        )
        selected = select_detector_method(
            passing,
            maximum_clean_false_positive_rate=MAX_VALIDATION_FPR,
            minimum_coverage=MIN_VALIDATION_COVERAGE,
        )
        walkforward_selection[family] = {
            "selected_method": selected.method.value,
            "validation_session": "session_12",
            "test_session": "session_13",
            "reference_cutoff_anchor_session": "session_11",
            "candidates": {
                method.value: {
                    "threshold": float(result["threshold"].threshold),
                    "threshold_floors_met": result["threshold"].accepted,
                    "validation_metrics": result["validation_metrics"],
                    "threshold_sensitivity_validation_only": result[
                        "threshold_sensitivity_validation_only"
                    ],
                    "validation_all_injection_scenario_metrics": result[
                        "validation_scenario_metrics"
                    ],
                    "fit_seconds": result["fit_seconds"],
                    "validation_score_seconds": result["score_seconds"],
                }
                for method, result in walkforward_candidates[family].items()
            },
        }
        walkforward_versions[family] = {}
        for method, result in walkforward_candidates[family].items():
            threshold = float(result["threshold"].threshold)
            manifest = {
                "policy": VALIDATION_TARGET_POLICY,
                "evaluation_mode": "expanding_window",
                "reference_cutoff_anchor_session": "session_11",
                "validation_session": "session_12",
                "test_session": "session_13",
                "family": family,
                "method": method.value,
                "threshold": threshold,
                "validation_metrics": result["validation_metrics"],
                "selected_method": selected.method.value,
            }
            evidence_checksum = stable_hash(
                {
                    "family": family,
                    "method": method.value,
                    "scores": result["validation_scores"],
                    "labels": result["validation_labels"],
                    "manifest": manifest,
                }
            )
            frozen = await service.freeze_validation_threshold(
                detector_version_id=result["fit"].detector_version_id,
                threshold=threshold,
                validation_checksum=evidence_checksum,
                selection_manifest=manifest,
                accepted=method is selected.method,
                git_sha="phase9c-evaluator",
            )
            walkforward_versions[family][method] = frozen.detector_version_id

    walkforward_test_results: dict[str, dict[str, Any]] = {}
    walkforward_replays: dict[str, Any] = {}
    walkforward_test_cutoff = max(
        item.ended_at for item in walkforward_test
    ) + timedelta(seconds=1)
    for family in FAMILIES:
        walkforward_test_results[family] = {}
        for method, version_id in walkforward_versions[family].items():
            run = await service.score_detector_version(
                detector_version_id=version_id,
                pull_ids=tuple(item.pull_id for item in walkforward_test),
                observation_cutoff=walkforward_test_cutoff,
                source_role=SourceRole.SYNTHETIC,
            )
            details = await _finding_details(database, run.finding_ids)
            by_pull = {
                UUID(str(details[finding_id]["pull_id"])): details[finding_id]
                for finding_id in run.finding_ids
            }
            scores = tuple(
                float(by_pull[item.pull_id]["score"])
                if by_pull.get(item.pull_id, {}).get("score") is not None
                else None
                for item in walkforward_test
            )
            threshold = float(
                walkforward_candidates[family][method]["threshold"].threshold
            )
            metrics = _scenario_metrics(
                walkforward_test,
                scores,
                threshold,
                included_scenarios={"clean", family},
                positive_scenario=family,
            )
            clean_metrics = _clean_control_metrics(walkforward_test, scores, threshold)
            quality_statuses = [
                {
                    "scenario": item.scenario,
                    "status": by_pull[item.pull_id]["status"]
                    if item.pull_id in by_pull
                    else "NO_FINDING",
                }
                for item in walkforward_test
                if item.scenario in {"missing_fuel", "quality_duplicate"}
            ]
            walkforward_test_results[family][method.value] = {
                "detector_version_id": str(version_id),
                "threshold_frozen_on_session_12": threshold,
                "target_family_vs_clean_metrics": metrics,
                "clean_control_metrics": clean_metrics,
                "all_family_injection_metrics": _scenario_metrics(
                    walkforward_test,
                    scores,
                    threshold,
                    included_scenarios={"clean", *FAMILIES},
                    positive_scenario=family,
                ),
                "cross_family_injection_alarm_rate": _injection_alarm_rate(
                    walkforward_test,
                    scores,
                    threshold,
                    excluded_scenario=family,
                ),
                "quality_control_statuses": quality_statuses,
                "finding_status_counts": run.status_counts,
                "run_id": str(run.run_id),
                "input_checksum": run.input_checksum,
                "artifact_checksum": run.artifact_checksum,
                "requested": run.requested_count,
            }
            if method.value == walkforward_selection[family]["selected_method"]:
                replay = await service.score_detector_version(
                    detector_version_id=version_id,
                    pull_ids=tuple(item.pull_id for item in walkforward_test),
                    observation_cutoff=walkforward_test_cutoff,
                    source_role=SourceRole.SYNTHETIC,
                )
                _assert(
                    replay.idempotent_replay, "walk-forward replay was not idempotent"
                )
                _assert(
                    replay.run_id == run.run_id,
                    "walk-forward replay changed run identity",
                )
                _assert(
                    replay.finding_ids == run.finding_ids,
                    "walk-forward replay changed finding identity",
                )
                walkforward_replays[family] = {
                    "idempotent": replay.idempotent_replay,
                    "same_run_id": replay.run_id == run.run_id,
                    "same_finding_ids": replay.finding_ids == run.finding_ids,
                }

    walkforward_selected_test = {
        family: walkforward_test_results[family][
            walkforward_selection[family]["selected_method"]
        ]["target_family_vs_clean_metrics"]
        for family in FAMILIES
    }
    walkforward_missing_fuel_statuses = [
        item["status"]
        for method_result in walkforward_test_results["fuel"].values()
        for item in method_result["quality_control_statuses"]
        if item["scenario"] == "missing_fuel"
    ]
    walkforward_duplicate_quality_statuses = [
        item["status"]
        for family_result in walkforward_test_results.values()
        for method_result in family_result.values()
        for item in method_result["quality_control_statuses"]
        if item["scenario"] == "quality_duplicate"
    ]
    _assert(
        bool(walkforward_missing_fuel_statuses)
        and all(
            status == AnomalyStatus.INSUFFICIENT_SIGNAL.value
            for status in walkforward_missing_fuel_statuses
        ),
        "walk-forward missing-fuel target did not abstain as insufficient signal",
    )
    _assert(
        bool(walkforward_duplicate_quality_statuses)
        and all(
            status == AnomalyStatus.LOW_QUALITY.value
            for status in walkforward_duplicate_quality_statuses
        ),
        "walk-forward duplicated telemetry did not abstain as low quality",
    )

    # Exercise simultaneous run-identity collision handling. A distinct cutoff avoids the
    # already-persisted held-out run; the two requests race to create the same run identity.
    concurrent_probe = next(item for item in test_targets if item.scenario == "clean")
    concurrent_cutoff = target_cutoff + timedelta(seconds=1)
    concurrent_runs = await asyncio.gather(
        *(
            service.score_detector_version(
                detector_version_id=frozen_versions["thermal"][
                    DetectorMethod(selected_validation["thermal"])
                ],
                pull_ids=(concurrent_probe.pull_id,),
                observation_cutoff=concurrent_cutoff,
                source_role=SourceRole.SYNTHETIC,
            )
            for _ in range(2)
        )
    )
    _assert(
        len({item.run_id for item in concurrent_runs}) == 1,
        "concurrent identical scores created multiple detection runs",
    )
    _assert(
        len({item.finding_ids for item in concurrent_runs}) == 1
        and all(len(item.finding_ids) == 1 for item in concurrent_runs),
        "concurrent identical scores returned inconsistent finding IDs",
    )
    _assert(
        sorted(item.idempotent_replay for item in concurrent_runs) == [False, True],
        "concurrent score collision did not resolve to one creation and one replay",
    )
    concurrent_replay = {
        "one_run_id": True,
        "one_finding_id": True,
        "one_created_one_replayed": True,
        "run_id": str(concurrent_runs[0].run_id),
        "finding_id": str(concurrent_runs[0].finding_ids[0]),
    }
    rollback_probe = await _verify_failed_persistence_rolls_back(
        database,
        service,
        detector_version_id=frozen_versions["thermal"][
            DetectorMethod(selected_validation["thermal"])
        ],
        pull=concurrent_probe,
        observation_cutoff=concurrent_cutoff,
    )

    # Same-session, different-configuration, different-vehicle, and unsupported-signal guards.
    robust_selected_version = frozen_versions["thermal"][
        DetectorMethod(selected_validation["thermal"])
    ]
    anchor_run = await service.score_detector_version(
        detector_version_id=robust_selected_version,
        pull_ids=(anchor.pull_id,),
        observation_cutoff=anchor.ended_at + timedelta(seconds=1),
        source_role=SourceRole.SYNTHETIC,
    )
    anchor_details = await _finding_details(database, anchor_run.finding_ids)
    anchor_status = next(iter(anchor_details.values()))["status"]
    config_pull = primary.pulls_by_session[14][0]
    config_run = await service.score_detector_version(
        detector_version_id=robust_selected_version,
        pull_ids=(config_pull.pull_id,),
        observation_cutoff=config_pull.ended_at + timedelta(seconds=1),
        source_role=SourceRole.SYNTHETIC,
    )
    config_details = await _finding_details(database, config_run.finding_ids)
    config_status = next(iter(config_details.values()))["status"]
    vehicle_pull = holdout.pulls_by_session[0][0]
    vehicle_run = await service.score_detector_version(
        detector_version_id=robust_selected_version,
        pull_ids=(vehicle_pull.pull_id,),
        observation_cutoff=vehicle_pull.ended_at + timedelta(seconds=1),
        source_role=SourceRole.SYNTHETIC,
    )
    vehicle_details = await _finding_details(database, vehicle_run.finding_ids)
    vehicle_status = next(iter(vehicle_details.values()))["status"]

    no_fuel_anchor = no_fuel.pulls_by_session[8][0]
    no_fuel_fit = await service.fit_detector_version(
        anchor_pull_id=no_fuel_anchor.pull_id,
        observation_cutoff=no_fuel_anchor.ended_at + timedelta(seconds=1),
        source_role=SourceRole.SYNTHETIC,
        family="fuel",
        method=DetectorMethod.ROBUST_MAD.value,
        git_sha="phase9c-evaluator",
    )
    _assert(
        no_fuel_fit.state is DetectorLifecycle.REJECTED,
        "fuel model fit without fuel signals",
    )
    _assert(
        no_fuel_fit.rejection_reason == "REQUIRED_SIGNAL_UNAVAILABLE",
        "missing fuel source was not classified as unavailable",
    )
    no_fuel_target = no_fuel.pulls_by_session[9][0]
    no_fuel_run = await service.score_detector_version(
        detector_version_id=no_fuel_fit.detector_version_id,
        pull_ids=(no_fuel_target.pull_id,),
        observation_cutoff=no_fuel_target.ended_at + timedelta(seconds=1),
        source_role=SourceRole.SYNTHETIC,
    )
    no_fuel_details = await _finding_details(database, no_fuel_run.finding_ids)
    no_fuel_status = next(iter(no_fuel_details.values()))["status"]

    # The artifact loader is exercised by each service score. Verify a modified file is rejected.
    accepted_for_tamper = robust_selected_version
    registered = await service.artifacts.load_registered(
        database, str(accepted_for_tamper)
    )
    artifact_path = service.artifacts._checked_path(
        service.artifacts._expected_relative(registered.definition, registered.version)
    )
    artifact_bytes = artifact_path.read_bytes()
    artifact_tamper_rejected = False
    try:
        artifact_path.write_bytes(artifact_bytes + b"tampered")
        try:
            await service.artifacts.load_registered(database, str(accepted_for_tamper))
        except AnomalyArtifactError:
            artifact_tamper_rejected = True
    finally:
        artifact_path.write_bytes(artifact_bytes)
    _assert(artifact_tamper_rejected, "tampered trusted artifact was accepted")

    immutable_finding_id = next(iter(anchor_details))
    immutable_rejected = False
    async with database.session() as db:
        try:
            await db.execute(
                text("UPDATE anomaly_findings SET status='INLIER' WHERE id=:id"),
                {"id": immutable_finding_id},
            )
            await db.commit()
        except SQLAlchemyError:
            immutable_rejected = True
    _assert(immutable_rejected, "database allowed mutation of an immutable finding")
    _assert(
        anchor_status == AnomalyStatus.INCOMPATIBLE_CONTEXT.value,
        "anchor session was scored",
    )
    _assert(
        config_status == AnomalyStatus.INCOMPATIBLE_CONTEXT.value,
        "configuration holdout was scored",
    )
    _assert(
        vehicle_status == AnomalyStatus.INCOMPATIBLE_CONTEXT.value,
        "held-out vehicle was scored",
    )
    _assert(
        no_fuel_status == AnomalyStatus.UNSUPPORTED_SOURCE.value,
        "missing-fuel target did not abstain",
    )

    # Keep direct scoring separate from database work. Both 1,000-row batches include warmup,
    # a clean nominal case, and a mixed case with injected deviations and explicit abstentions.
    benchmark_family = FAMILIES[0]
    direct_benchmarks: dict[str, Any] = {}
    direct_score_count = 0
    direct_requested_count = 0
    benchmark_stage_seconds: dict[str, float] = {}
    for benchmark_method in METHODS:
        benchmark_version = frozen_versions[benchmark_family][benchmark_method]
        benchmark_definition = detector_definition(
            benchmark_family, benchmark_method.value
        )
        artifact_load_started = time.perf_counter()
        benchmark_artifact = await service.artifacts.load_registered(
            database, str(benchmark_version)
        )
        artifact_reload_seconds = time.perf_counter() - artifact_load_started
        materialization_started = time.perf_counter()
        clean_targets = tuple(item for item in test_targets if item.scenario == "clean")
        one_benchmark_row = await service.repository.load_targets(
            tuple(item.pull_id for item in clean_targets),
            target_cutoff,
            benchmark_definition,
        )
        _assert(
            len(one_benchmark_row) == len(clean_targets),
            "benchmark clean FeatureSets are unavailable",
        )
        benchmark_stage_seconds[
            f"{benchmark_method.value}/reference_materialization"
        ] = time.perf_counter() - materialization_started
        benchmark_stage_seconds[f"{benchmark_method.value}/artifact_reload"] = (
            artifact_reload_seconds
        )
        base_row = None
        for row in one_benchmark_row:
            candidate_result = score_observation(
                benchmark_definition,
                benchmark_artifact.fitted,
                row,
                observation_cutoff=target_cutoff,
            )
            if candidate_result.status is AnomalyStatus.INLIER:
                base_row = row
                break
        if base_row is None:
            raise AssertionError("benchmark has no scoreable clean held-out row")
        first_observation = replace(
            base_row, pull_id="benchmark-memory-sample", session_id="benchmark-session"
        )
        tracemalloc.start()
        first_result = score_observation(
            benchmark_definition,
            benchmark_artifact.fitted,
            first_observation,
            observation_cutoff=target_cutoff,
        )
        _, one_score_peak_traced_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        _assert(
            first_result.score is not None, "benchmark warmup observation abstained"
        )

        required_spec = next(
            spec for spec in benchmark_definition.features if spec.required
        )
        required_feature = base_row.features[required_spec.key]
        _assert(
            required_feature.value is not None,
            "benchmark clean row lacks the required detector feature",
        )

        def benchmark_row(
            index: int,
            kind: str,
            *,
            source_row: Any = base_row,
            feature_spec: Any = required_spec,
            source_feature: Any = required_feature,
            method: DetectorMethod = benchmark_method,
        ) -> Any:
            features = dict(source_row.features)
            if kind == "injected":
                features[feature_spec.key] = replace(
                    source_feature, value=float(source_feature.value) + 20.0
                )
            elif kind == "abstain":
                features[feature_spec.key] = replace(
                    source_feature,
                    value=None,
                    quality="missing",
                    missing_reason="insufficient_window",
                )
            return replace(
                source_row,
                pull_id=f"benchmark-{method.value}-{kind}-{index}",
                session_id=f"benchmark-session-{kind}-{index}",
                features=features,
            )

        nominal_rows = tuple(benchmark_row(index, "clean") for index in range(1_000))
        mixed_rows = tuple(
            benchmark_row(index, kind)
            for kind, count in (("clean", 600), ("injected", 300), ("abstain", 100))
            for index in range(count)
        )
        mixed_kinds = tuple(
            kind
            for kind, count in (("clean", 600), ("injected", 300), ("abstain", 100))
            for _ in range(count)
        )
        _assert(
            len(nominal_rows) == len(mixed_rows) == 1_000,
            "benchmark batches must each contain 1,000 observations",
        )

        transformed_rows: list[dict[str, float | None]] = []
        preprocessing_started = time.perf_counter()
        for observation in mixed_rows:
            transformed, _ = transform_features(benchmark_definition, observation)
            transformed_rows.append(transformed)
        feature_preprocessing_seconds = time.perf_counter() - preprocessing_started
        benchmark_stage_seconds[f"{benchmark_method.value}/feature_preprocessing"] = (
            feature_preprocessing_seconds
        )

        forest_matrix_seconds = 0.0
        scoreable_rows = [
            transformed
            for transformed in transformed_rows
            if all(
                transformed.get(key) is not None
                for key in benchmark_definition.required_feature_keys
            )
        ]
        _assert(
            len(scoreable_rows) == 900, "mixed benchmark must contain 100 abstentions"
        )
        if benchmark_method is DetectorMethod.ISOLATION_FOREST:
            forest_matrix_started = time.perf_counter()
            _forest_matrix(
                scoreable_rows,
                benchmark_artifact.fitted.feature_order,
                benchmark_artifact.fitted.optional_feature_order,
                benchmark_artifact.fitted.missing_indicator_order,
                benchmark_artifact.fitted.imputation_medians,
                benchmark_artifact.fitted.robust_centers,
                benchmark_artifact.fitted.robust_scales,
            )
            forest_matrix_seconds = time.perf_counter() - forest_matrix_started
        benchmark_stage_seconds[
            f"{benchmark_method.value}/forest_matrix_preprocessing"
        ] = forest_matrix_seconds

        def score_batch(
            rows: tuple[Any, ...],
            kinds: tuple[str, ...] | None = None,
            *,
            definition: Any = benchmark_definition,
            fitted: Any = benchmark_artifact.fitted,
            cutoff: datetime = target_cutoff,
        ) -> tuple[dict[str, int], float, dict[str, dict[str, int]]]:
            score_counts: Counter[str] = Counter()
            kind_status_counts: dict[str, Counter[str]] = {}
            started_at = time.perf_counter()
            for index, observation in enumerate(rows):
                result = score_observation(
                    definition,
                    fitted,
                    observation,
                    observation_cutoff=cutoff,
                )
                score_counts[result.status.value] += 1
                if kinds is not None:
                    kind_status_counts.setdefault(kinds[index], Counter())[
                        result.status.value
                    ] += 1
            return (
                dict(sorted(score_counts.items())),
                time.perf_counter() - started_at,
                {
                    kind: dict(sorted(counts.items()))
                    for kind, counts in sorted(kind_status_counts.items())
                },
            )

        nominal_status_counts, nominal_seconds, _ = score_batch(nominal_rows)
        mixed_status_counts, mixed_seconds, mixed_status_by_kind = score_batch(
            mixed_rows, mixed_kinds
        )
        nominal_scored = sum(
            count
            for status, count in nominal_status_counts.items()
            if status in {AnomalyStatus.INLIER.value, AnomalyStatus.ANOMALOUS.value}
        )
        mixed_scored = sum(
            count
            for status, count in mixed_status_counts.items()
            if status in {AnomalyStatus.INLIER.value, AnomalyStatus.ANOMALOUS.value}
        )
        _assert(
            nominal_scored == 1_000 and mixed_scored == 900,
            "nominal or mixed benchmark has unexpected scoring/abstention counts",
        )
        _assert(
            nominal_status_counts == {AnomalyStatus.INLIER.value: 1_000},
            "nominal benchmark control is not a clean inlier",
        )
        _assert(
            mixed_status_by_kind.get("abstain", {}).get(
                AnomalyStatus.INSUFFICIENT_SIGNAL.value
            )
            == 100,
            "mixed benchmark abstention category changed status",
        )
        direct_score_count += nominal_scored + mixed_scored
        direct_requested_count += len(nominal_rows) + len(mixed_rows)
        direct_benchmarks[benchmark_method.value] = {
            "materialized_clean_reference_rows": len(one_benchmark_row),
            "reference_materialization_seconds": round(
                benchmark_stage_seconds[
                    f"{benchmark_method.value}/reference_materialization"
                ],
                6,
            ),
            "artifact_reload_seconds": round(artifact_reload_seconds, 6),
            "feature_preprocessing_seconds_mixed_batch": round(
                feature_preprocessing_seconds, 6
            ),
            "forest_matrix_preprocessing_seconds_mixed_batch": round(
                forest_matrix_seconds, 6
            ),
            "nominal_batch": {
                "requested": len(nominal_rows),
                "scored": nominal_scored,
                "abstained": len(nominal_rows) - nominal_scored,
                "status_counts": nominal_status_counts,
                "score_seconds": round(nominal_seconds, 6),
                "scored_per_second": round(nominal_scored / nominal_seconds, 3),
            },
            "mixed_batch": {
                "requested": len(mixed_rows),
                "injected_deviation_cases": 300,
                "clean_cases": 600,
                "abstention_cases": 100,
                "scored": mixed_scored,
                "abstained": len(mixed_rows) - mixed_scored,
                "status_counts": mixed_status_counts,
                "status_counts_by_case": mixed_status_by_kind,
                "score_seconds": round(mixed_seconds, 6),
                "scored_per_second": round(mixed_scored / mixed_seconds, 3),
            },
            "requested_observations": 2_000,
            "scored_observations": nominal_scored + mixed_scored,
            "one_score_peak_traced_python_bytes": one_score_peak_traced_bytes,
            "artifact_size_bytes": service.artifacts._checked_path(
                service.artifacts._expected_relative(
                    benchmark_artifact.definition, benchmark_artifact.version
                )
            )
            .stat()
            .st_size,
        }
    _assert(
        direct_score_count >= 1_000, "benchmark scored fewer than 1000 observations"
    )
    process_peak_rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024

    async with database.session() as db:
        artifact_sizes = (
            (
                await db.execute(
                    text(
                        "SELECT d.family,d.method,dv.state,dv.artifact_size_bytes "
                        "FROM anomaly_detector_versions dv JOIN anomaly_detector_definitions d "
                        "ON d.id=dv.detector_definition_id WHERE dv.id=ANY(:ids)"
                    ),
                    {
                        "ids": [
                            version_id
                            for version_sets in (frozen_versions, walkforward_versions)
                            for methods in version_sets.values()
                            for version_id in methods.values()
                        ]
                    },
                )
            )
            .mappings()
            .all()
        )
        feature_set_count = await db.scalar(text("SELECT count(*) FROM feature_sets"))
        run_count = await db.scalar(text("SELECT count(*) FROM anomaly_detection_runs"))
        finding_count = await db.scalar(text("SELECT count(*) FROM anomaly_findings"))

    predeclared_gates = {
        "per_family_target_injection_recall_at_least_0_5": {
            family: (
                metric["recall"] is not None
                and metric["recall"]
                >= VALIDATION_TARGET_POLICY["minimum_injection_recall"]
            )
            for family, metric in selected_test.items()
        },
        "per_family_clean_control_false_positive_rate_at_most_0_25": {
            family: (
                test_results[family][selected_validation[family]][
                    "clean_control_metrics"
                ]["false_positive_rate"]
                is not None
                and test_results[family][selected_validation[family]][
                    "clean_control_metrics"
                ]["false_positive_rate"]
                <= VALIDATION_TARGET_POLICY["maximum_clean_false_positive_rate"]
            )
            for family in FAMILIES
        },
        "per_family_target_and_clean_coverage_at_least_0_8": {
            family: metric["anomaly_coverage"]
            >= VALIDATION_TARGET_POLICY["minimum_eligible_coverage"]
            for family, metric in selected_test.items()
        },
        "per_family_temporal_fold_recall_at_least_0_5": {
            family: {
                fold: metric["target_family_vs_clean"]["recall"] is not None
                and metric["target_family_vs_clean"]["recall"] >= MIN_VALIDATION_RECALL
                for fold, metric in test_results[family][selected_validation[family]][
                    "temporal_test_fold_metrics"
                ].items()
            }
            for family in FAMILIES
        },
        "per_family_temporal_fold_clean_control_false_positive_rate_at_most_0_25": {
            family: {
                fold: metric["clean_controls"]["false_positive_rate"] is not None
                and metric["clean_controls"]["false_positive_rate"]
                <= MAX_VALIDATION_FPR
                for fold, metric in test_results[family][selected_validation[family]][
                    "temporal_test_fold_metrics"
                ].items()
            }
            for family in FAMILIES
        },
        "per_family_temporal_fold_coverage_at_least_0_8": {
            family: {
                fold: metric["target_family_vs_clean"]["anomaly_coverage"]
                >= MIN_VALIDATION_COVERAGE
                for fold, metric in test_results[family][selected_validation[family]][
                    "temporal_test_fold_metrics"
                ].items()
            }
            for family in FAMILIES
        },
        "walk_forward_per_family_recall_at_least_0_5": {
            family: metric["recall"] is not None
            and metric["recall"] >= MIN_VALIDATION_RECALL
            for family, metric in walkforward_selected_test.items()
        },
        "walk_forward_per_family_clean_false_positive_rate_at_most_0_25": {
            family: (
                walkforward_test_results[family][
                    walkforward_selection[family]["selected_method"]
                ]["clean_control_metrics"]["false_positive_rate"]
                is not None
                and walkforward_test_results[family][
                    walkforward_selection[family]["selected_method"]
                ]["clean_control_metrics"]["false_positive_rate"]
                <= MAX_VALIDATION_FPR
            )
            for family in FAMILIES
        },
        "walk_forward_per_family_coverage_at_least_0_8": {
            family: metric["anomaly_coverage"] >= MIN_VALIDATION_COVERAGE
            for family, metric in walkforward_selected_test.items()
        },
    }
    all_fixture_floors_met = all(
        value
        for group in predeclared_gates.values()
        for result in group.values()
        for value in (result.values() if isinstance(result, dict) else (result,))
    )
    telemetry_spans = span_exporter.get_finished_spans()
    span_names = sorted({span.name for span in telemetry_spans})
    metric_text = telemetry.render_metrics().decode("utf-8")
    anomaly_metric_lines = [
        line for line in metric_text.splitlines() if line.startswith("anomaly_")
    ]
    required_spans = {
        "anomaly.reference.materialization",
        "anomaly.reference.eligibility",
        "anomaly.detector.fit",
        "anomaly.artifact.stage",
        "anomaly.threshold.selection",
        "anomaly.target.materialization",
        "anomaly.artifact.validation",
        "anomaly.observation.score",
        "anomaly.finding.persistence",
    }
    _assert(
        required_spans.issubset(set(span_names)), "anomaly trace spans are incomplete"
    )
    _assert(bool(anomaly_metric_lines), "anomaly metrics were not rendered")
    forbidden_metric_values = (str(primary.vehicle_id), str(test_targets[0].pull_id))
    _assert(
        not any(value in metric_text for value in forbidden_metric_values),
        "anomaly metric output contains an entity identifier",
    )

    report: dict[str, Any] = {
        "schema_version": "phase9c-acceptance-v1",
        "execution_state": "PASS" if all_fixture_floors_met else "FAIL",
        "database_pool_checked_out_before_close": int(
            getattr(database.engine.pool, "checkedout", lambda: -1)()
        ),
        "fixture_claim": "controlled deterministic synthetic engineering fixture only",
        "source_data": {
            "primary_vehicle_reference_sessions": 8,
            "primary_reference_rows_expected": 40,
            "anchor_session_excluded": True,
            "validation_session_pull_count": len(validation),
            "clean_recovery_sessions": {
                "session_10": len(primary.pulls_by_session[10]),
                "session_11": len(primary.pulls_by_session[11]),
            },
            "untouched_test_session_pull_count": len(test_targets),
            "untouched_test_temporal_folds": {
                name: len(pulls) for name, pulls in test_folds.items()
            },
            "feature_sets_generated": feature_set_count,
            "canonical_feature_generator": "phase9a-feature-generator-v2",
            "scenario_labels_persisted_as_features": False,
            "injection_metadata_used_for_fit_or_score": False,
            "session_12_role_in_walk_forward": (
                "first model test, then validation for the later model only"
            ),
            "session_13_opened_after_walk_forward_freeze": True,
            "feature_generation_seconds_total": round(
                sum(generation_timings.values()), 6
            ),
        },
        "threshold_policy": VALIDATION_TARGET_POLICY,
        "validation_selection": selection,
        "test_comparison_after_freeze": test_results,
        "walk_forward_evaluation": {
            "mode": "expanding_window",
            "first_model": {
                "reference_sessions": "0-7",
                "validation_session": "9",
                "first_test_session": "12",
            },
            "second_model": {
                "reference_cutoff_anchor_session": "11",
                "validation_session": "12",
                "untouched_test_session": "13",
                "session_12_becomes_validation_only_after_first_model_is_frozen_and_scored": True,
            },
            "selection": walkforward_selection,
            "test_comparison_after_freeze": walkforward_test_results,
            "selected_method_test_metrics": walkforward_selected_test,
            "replays": walkforward_replays,
        },
        "temporal_fold_stability": {
            family: {
                method: result["temporal_test_fold_metrics"]
                for method, result in methods.items()
            }
            for family, methods in test_results.items()
        },
        "selected_method_test_metrics": selected_test,
        "predeclared_test_floors": predeclared_gates,
        "observability": {
            "expected_spans_present": sorted(required_spans),
            "observed_anomaly_spans": [
                name for name in span_names if name.startswith("anomaly.")
            ],
            "anomaly_metric_series": anomaly_metric_lines,
            "entity_id_labels_absent": True,
        },
        "boundary_checks": {
            "same_anchor_session_abstained": anchor_status,
            "different_configuration_abstained": config_status,
            "unseen_vehicle_abstained": vehicle_status,
            "missing_fuel_reference_rejected": no_fuel_fit.rejection_reason,
            "missing_fuel_target_abstained": no_fuel_status,
            "tampered_artifact_rejected": artifact_tamper_rejected,
            "immutable_finding_update_rejected": immutable_rejected,
            "accepted_model_score_replay": accepted_replay,
            "walk_forward_accepted_model_score_replay": walkforward_replays,
            "concurrent_identical_model_score": concurrent_replay,
            "failed_finding_persistence_rollback": rollback_probe,
            "temporal_leakage_adversaries": temporal_adversary_results,
        },
        "held_out_stress_suite": {
            "method_and_threshold_frozen_before_session_12_and_13": True,
            "environmental_profile": (
                "session 13 has an unseen +12 K ambient/IAT level shift across all pulls; "
                "the within-pull IAT rise and performance telemetry remain unchanged"
            ),
            "unseen_interventions": {
                "boost_fluctuation": (
                    "alternating boost-pressure variation with unchanged RPM-duration behavior"
                ),
                "subtle_multivariate": (
                    "small simultaneous IAT-rise, boost-pressure and RPM-duration departures"
                ),
            },
            "oracle_metadata_excluded_from_features": True,
            "outcomes_by_family_and_method": heldout_stress_suite,
        },
        "benchmark": {
            "reference_rows": 40,
            "detector_fit_seconds": fit_seconds,
            "stage_span_seconds": {
                span_name: round(
                    sum(
                        (span.end_time - span.start_time) / 1_000_000_000
                        for span in telemetry_spans
                        if span.name == span_name
                        and span.start_time is not None
                        and span.end_time is not None
                    ),
                    6,
                )
                for span_name in (
                    "anomaly.reference.materialization",
                    "anomaly.reference.eligibility",
                    "anomaly.detector.fit",
                    "anomaly.artifact.stage",
                    "anomaly.target.materialization",
                    "anomaly.artifact.validation",
                    "anomaly.observation.score",
                    "anomaly.finding.persistence",
                )
            },
            "feature_generation_seconds": round(sum(generation_timings.values()), 6),
            "service_database_read_and_persistence_seconds": {
                family: {
                    method: {
                        "target_read": result[method]["target_database_read_seconds"],
                        "finding_persistence": result[method][
                            "finding_database_persistence_seconds"
                        ],
                        "service_end_to_end": result[method]["service_score_seconds"],
                    }
                    for method in result
                }
                for family, result in test_results.items()
            },
            "direct_offline_scored_observations": direct_score_count,
            "direct_offline_requested_observations": direct_requested_count,
            "direct_offline_by_method": direct_benchmarks,
            "evaluator_process_peak_rss_bytes": process_peak_rss_bytes,
            "artifact_sizes": [dict(row) for row in artifact_sizes],
            "persisted_detection_runs": run_count,
            "persisted_findings": finding_count,
            "note": (
                "direct offline timing separates canonical FeatureSet materialization, artifact "
                "reload, feature preprocessing, nominal scoring and mixed scoring from service "
                "database reads and persistence. Each method receives a 1,000-row nominal batch "
                "and a 1,000-row mixed batch with 100 explicit abstentions. One-row traced Python "
                "allocations are reported separately because tracing every scorer allocation "
                "materially distorts throughput. Process peak RSS covers the complete evaluator."
            ),
        },
        "limitations": [
            "Synthetic injections demonstrate controlled behavior only, not real-car detection performance.",
            "A score is a relative engineering deviation, not fault diagnosis or failure probability.",
            "Isolation Forest bytes may vary across compatible library builds despite deterministic fitted scores.",
        ],
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "acceptance.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    if not all_fixture_floors_met:
        raise AssertionError(
            "one or more predeclared held-out fixture floors were not met"
        )
    return report


async def _run_and_cleanup() -> dict[str, Any]:
    try:
        return await evaluate()
    finally:
        if _ACTIVE_TELEMETRY is not None:
            _ACTIVE_TELEMETRY.shutdown()
        if _ACTIVE_DATABASE is not None:
            await _ACTIVE_DATABASE.close()


def main() -> None:
    report = asyncio.run(_run_and_cleanup())
    concise = {
        "execution_state": report["execution_state"],
        "fixture_claim": report["fixture_claim"],
        "source_data": report["source_data"],
        "validation_selection": {
            family: {
                "selected_method": result["selected_method"],
                "candidates": {
                    method: candidate["validation_metrics"]
                    for method, candidate in result["candidates"].items()
                },
            }
            for family, result in report["validation_selection"].items()
        },
        "selected_method_test_metrics": report["selected_method_test_metrics"],
        "walk_forward_selected_test_metrics": report["walk_forward_evaluation"][
            "selected_method_test_metrics"
        ],
        "held_out_stress_summary": {
            family: {
                method: {
                    "environment_context_shift_clean_controls": {
                        key: stress["environmental_context_shift_clean_controls"][key]
                        for key in (
                            "support",
                            "scored",
                            "abstained",
                            "false_positives",
                            "false_positive_rate",
                        )
                    },
                    "unseen_interventions": {
                        scenario: [
                            {
                                "status": item["status"],
                                "predicted_anomaly": item["predicted_anomaly"],
                                "score": item["score"],
                                "threshold": item["threshold"],
                            }
                            for item in cases
                        ]
                        for scenario, cases in stress["unseen_interventions"].items()
                    },
                }
                for method, stress in methods.items()
            }
            for family, methods in report["held_out_stress_suite"][
                "outcomes_by_family_and_method"
            ].items()
        },
        "boundary_checks": {
            "concurrent_identical_model_score": report["boundary_checks"][
                "concurrent_identical_model_score"
            ]["one_created_one_replayed"],
            "failed_finding_persistence_rollback": report["boundary_checks"][
                "failed_finding_persistence_rollback"
            ]["detection_run_rolled_back"],
            "temporal_leakage_adversaries": report["boundary_checks"][
                "temporal_leakage_adversaries"
            ],
            "tampered_artifact_rejected": report["boundary_checks"][
                "tampered_artifact_rejected"
            ],
            "immutable_finding_update_rejected": report["boundary_checks"][
                "immutable_finding_update_rejected"
            ],
        },
        "benchmark": {
            "direct_offline_requested_observations": report["benchmark"][
                "direct_offline_requested_observations"
            ],
            "direct_offline_scored_observations": report["benchmark"][
                "direct_offline_scored_observations"
            ],
            "direct_offline_by_method": report["benchmark"]["direct_offline_by_method"],
            "persisted_detection_runs": report["benchmark"]["persisted_detection_runs"],
            "persisted_findings": report["benchmark"]["persisted_findings"],
            "evaluator_process_peak_rss_bytes": report["benchmark"][
                "evaluator_process_peak_rss_bytes"
            ],
            "database_pool_checked_out_before_close": report[
                "database_pool_checked_out_before_close"
            ],
        },
        "details_path": str(EVIDENCE / "acceptance.json"),
    }
    print(json.dumps(concise, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
