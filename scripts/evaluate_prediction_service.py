"""Independent Phase 9D acceptance over real Phase 9A/9B/9C records and HTTP routes."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import secrets
import statistics
import subprocess
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID

import evaluate_anomaly_detection as phase9c
import httpx
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from vehicle_platform.anomalies.artifacts import ArtifactStore as AnomalyArtifactStore
from vehicle_platform.anomalies.domain import (
    AnomalyStatus,
    DetectorLifecycle,
    DetectorMethod,
    SourceRole,
)
from vehicle_platform.anomalies.evaluation import (
    MethodCandidate,
    select_detector_method,
)
from vehicle_platform.anomalies.service import AnomalyService
from vehicle_platform.core.config import Settings
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.service import FeatureGenerationService
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.main import create_app
from vehicle_platform.ml.artifacts import (
    ArtifactStore as ModelArtifactStore,
)
from vehicle_platform.ml.artifacts import (
    offline_predict,
)
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.ml.pipeline import train_task
from vehicle_platform.ml.synthetic import (
    generate_fixture_features,
    seed_predictive_fixture,
)
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.predictions.domain import PredictionError, PredictionStatus
from vehicle_platform.predictions.service import PredictionService


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _percentile(samples: list[float], percentile: float) -> float:
    ordered = sorted(samples)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _rss_kib() -> int | None:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


async def _legacy_table_digests(database: Database) -> dict[str, str]:
    tables = (
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
    )
    digests: dict[str, str] = {}
    async with database.session() as db:
        for table in tables:
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
            digests[table] = stable_hash([str(row) for row in rows])
    return digests


def _migration_round_trip(database_url: str) -> str:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["TEST_DATABASE_URL"] = database_url
    env["ENVIRONMENT"] = "test"
    alembic = root / "apps" / "api" / ".venv" / "bin" / "alembic"
    output: list[str] = []
    for action, revision in (("downgrade", "0015"), ("upgrade", "head")):
        completed = subprocess.run(
            [str(alembic), action, revision],
            cwd=root / "apps" / "api",
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        output.append(completed.stdout.strip())
        output.append(completed.stderr.strip())
    return "\n".join(part for part in output if part)


async def _db_counts(database: Database) -> dict[str, int]:
    tables = (
        "vehicles",
        "driving_sessions",
        "pulls",
        "telemetry_samples",
        "modifications",
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
    )
    async with database.session() as db:
        return {
            table: int(await db.scalar(text(f"SELECT count(*) FROM {table}")) or 0)
            for table in tables
        }


async def _inject_late_records(
    database: Database,
    snapshot: Any,
    request_cutoff: datetime,
) -> dict[str, Any]:
    sample_id = hashlib.sha256(
        f"phase9d-late-sample:{snapshot.pull_id}".encode()
    ).hexdigest()
    modification_id = UUID(
        hashlib.sha256(
            f"phase9d-late-modification:{snapshot.pull_id}".encode()
        ).hexdigest()[:32]
    )
    observed_at = snapshot.pull_started_at + timedelta(seconds=0.4)
    ingested_at = request_cutoff + timedelta(days=1)
    modification_created_at = request_cutoff + timedelta(days=1)
    async with database.session() as db:
        await db.execute(
            text(
                "INSERT INTO telemetry_samples(sample_id,vehicle_id,session_id,observed_at,"
                "ingested_at,signal_key,numeric_value,normalized_unit,raw_signal,raw_value,"
                "source,source_record_id,sequence_number,quality,schema_version,content_hash) "
                "VALUES(:sample,:vehicle,:session,:observed,:ingested,'engine.boost_pressure',"
                "400000.0,'Pa','engine.boost_pressure','400000','synthetic',:record,999,"
                "'valid',1,:hash)"
            ),
            {
                "sample": sample_id,
                "vehicle": snapshot.vehicle_id,
                "session": snapshot.session_id,
                "observed": observed_at,
                "ingested": ingested_at,
                "record": f"phase9d-late:{snapshot.pull_id}",
                "hash": sample_id,
            },
        )
        await db.execute(
            text(
                "INSERT INTO modifications(id,vehicle_id,configuration_id,category,manufacturer,"
                "product,installed_at,removed_at,notes,created_at) VALUES(:id,:vehicle,:configuration,"
                "'intake','Synthetic','post-cutoff intake',:installed,NULL,'late metadata sentinel',:created)"
            ),
            {
                "id": modification_id,
                "vehicle": snapshot.vehicle_id,
                "configuration": snapshot.configuration_id,
                "installed": snapshot.pull_started_at - timedelta(days=1),
                "created": modification_created_at,
            },
        )
        await db.commit()
    return {
        "sample_id": sample_id,
        "observed_at": observed_at,
        "ingested_at": ingested_at,
        "modification_id": str(modification_id),
        "modification_created_at": modification_created_at,
        "request_cutoff": request_cutoff,
    }


async def _train_models(
    database: Database, telemetry: Telemetry, artifact_root: Path
) -> tuple[Any, dict[MLTask, Any]]:
    fixture = await seed_predictive_fixture(database)
    await generate_fixture_features(database, fixture, telemetry=telemetry)
    artifacts = ModelArtifactStore(artifact_root)
    trained: dict[MLTask, Any] = {}
    for task in MLTask:
        result = await train_task(
            database,
            task,
            datetime.now(UTC),
            source="synthetic",
            artifact_store=artifacts,
            scenario_family_by_session=fixture.scenario_family_by_session,
            telemetry=telemetry,
        )
        _assert(
            result.training.acceptance["all_criteria_pass"],
            f"{task.value} candidate failed acceptance",
        )
        _assert(
            result.training.state.value == "CANDIDATE",
            f"{task.value} did not register as a candidate",
        )
        trained[task] = result
    return fixture, trained


async def _train_detectors(
    database: Database, telemetry: Telemetry, artifact_root: Path
) -> tuple[Any, Any, dict[str, Any]]:
    primary = await phase9c._seed_vehicle(
        database, name="phase9d-primary", first_day=0, session_count=15
    )
    secondary = await phase9c._seed_vehicle(
        database, name="phase9d-secondary", first_day=13, session_count=1
    )
    await phase9c._generate_feature_sets(database, (primary, secondary))
    anomaly_store = AnomalyArtifactStore(artifact_root)
    service = AnomalyService(database, artifacts=anomaly_store, telemetry=telemetry)
    anchor = primary.pulls_by_session[8][0]
    validation = primary.pulls_by_session[9]
    selected: dict[str, Any] = {}
    evidence: dict[str, Any] = {}
    for family in phase9c.FAMILIES:
        candidates: dict[DetectorMethod, dict[str, Any]] = {}
        for method in phase9c.METHODS:
            candidates[method] = await phase9c._candidate_validation(
                database,
                service,
                primary,
                family,
                method,
                anchor,
                validation,
                telemetry,
            )
        eligible = tuple(
            MethodCandidate(
                method=method,
                threshold=float(result["threshold"].threshold),
                validation_metrics=result["validation_metrics"],
            )
            for method, result in candidates.items()
            if result["threshold"].accepted
        )
        _assert(bool(eligible), f"{family} has no accepted validation threshold")
        choice = select_detector_method(
            eligible,
            maximum_clean_false_positive_rate=phase9c.MAX_VALIDATION_FPR,
            minimum_coverage=phase9c.MIN_VALIDATION_COVERAGE,
        )
        selected_validation = candidates[choice.method]
        manifest = {
            "policy": phase9c.VALIDATION_TARGET_POLICY,
            "family": family,
            "method": choice.method.value,
            "threshold": float(selected_validation["threshold"].threshold),
            "validation_metrics": selected_validation["validation_metrics"],
            "selected_method": choice.method.value,
        }
        checksum = stable_hash(
            {
                "family": family,
                "method": choice.method.value,
                "scores": selected_validation["validation_scores"],
                "labels": selected_validation["validation_labels"],
                "manifest": manifest,
            }
        )
        frozen = await service.freeze_validation_threshold(
            detector_version_id=selected_validation["fit"].detector_version_id,
            threshold=float(selected_validation["threshold"].threshold),
            validation_checksum=checksum,
            selection_manifest=manifest,
            accepted=True,
            git_sha="phase9d-controlled-acceptance",
        )
        _assert(
            frozen.state is DetectorLifecycle.ACCEPTED,
            f"{family} detector was not accepted",
        )
        selected[family] = frozen
        evidence[family] = {
            "method": choice.method.value,
            "validation_threshold": frozen.threshold,
            "validation_checksum": checksum,
        }
    return (
        primary,
        secondary,
        {"service": service, "versions": selected, "evidence": evidence},
    )


async def _select_pull(database: Database, fixture: Any) -> dict[str, Any]:
    async with database.session() as db:
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT p.id,p.vehicle_id,p.ended_at,fs.observation_cutoff,fs.quality_metadata "
                        "FROM pulls p JOIN feature_sets fs ON fs.pull_id=p.id "
                        "WHERE fs.entity_scope='pull' ORDER BY p.started_at,p.id"
                    )
                )
            )
            .mappings()
            .all()
        )
    parsed = []
    for row in rows:
        quality = (
            row["quality_metadata"] if isinstance(row["quality_metadata"], dict) else {}
        )
        available = quality.get("available_signals", [])
        parsed.append({**dict(row), "quality": quality, "available": set(available)})
    eligible = next(
        item
        for item in parsed
        if item["available"].issuperset({"fuel.high_pressure"})
        and float(item["quality"].get("pull_completeness", 0.0)) >= 0.75
        and int(item["quality"].get("duplicate_timestamp_count", 0)) == 0
        and str(item["id"]) in {str(value) for value in fixture.pull_ids}
    )
    missing_fuel = next(
        item
        for item in parsed
        if "fuel.high_pressure" not in item["available"]
        and str(item["id"]) in {str(value) for value in fixture.pull_ids}
    )
    low_quality = next(
        item
        for item in parsed
        if (
            float(item["quality"].get("pull_completeness", 0.0)) < 0.75
            or int(item["quality"].get("duplicate_timestamp_count", 0)) > 0
        )
        and str(item["id"]) in {str(value) for value in fixture.pull_ids}
    )
    return {
        "eligible": eligible,
        "missing_fuel": missing_fuel,
        "low_quality": low_quality,
    }


async def evaluate() -> dict[str, Any]:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError(
            "Phase 9D acceptance requires the disposable vehicle_test database"
        )
    token = "phase9d-" + secrets.token_urlsafe(48)
    settings = Settings(
        database_url=SecretStr(url),
        environment="test",
        prediction_service_enabled=True,
        prediction_operator_token=SecretStr(token),
        prediction_max_concurrent_requests=8,
        prediction_max_cpu_concurrency=2,
        prediction_requests_per_minute=300,
        prediction_request_timeout_seconds=8,
        prediction_body_timeout_seconds=2,
        prediction_max_future_cutoff_seconds=60,
    )
    database = Database(settings, command_timeout=60)
    telemetry = Telemetry(settings, database)
    exporter = InMemorySpanExporter()
    telemetry.traces.add_span_processor(SimpleSpanProcessor(exporter))
    report: dict[str, Any] = {
        "schema_version": "phase9d-acceptance-v1",
        "execution_state": "FAIL",
        "validation_claim": "controlled synthetic engineering fixture only",
        "real_world_accuracy_claimed": False,
        "tasks": {},
        "anomaly_families": {},
        "coverage": {},
        "boundary_checks": {},
        "resource_limits": {
            "max_body_bytes": settings.prediction_max_body_bytes,
            "max_concurrent_requests": settings.prediction_max_concurrent_requests,
            "max_cpu_concurrency": settings.prediction_max_cpu_concurrency,
            "request_timeout_seconds": settings.prediction_request_timeout_seconds,
            "body_timeout_seconds": settings.prediction_body_timeout_seconds,
        },
    }
    migration_output = ""
    app_metrics = ""
    app_trace_names: list[str] = []
    peak_in_flight = 0
    rss_after_serving = _rss_kib()
    try:
        await database.check()
        with tempfile.TemporaryDirectory(prefix="phase9d-artifacts-") as temporary:
            artifact_root = Path(temporary)
            fixture, trained = await _train_models(
                database, telemetry, artifact_root / "phase9b"
            )
            primary, secondary, anomaly_context = await _train_detectors(
                database, telemetry, artifact_root / "phase9c"
            )
            late_feature_vehicle = await phase9c._seed_vehicle(
                database, name="phase9d-late-feature", first_day=30, session_count=1
            )
            late_feature_pull = late_feature_vehicle.pulls_by_session[0][0]
            target_pulls = await _select_pull(database, fixture)
            source_digests_before = await _legacy_table_digests(database)
            await database.close()
            telemetry.shutdown()
            migration_output = _migration_round_trip(url)
            database = Database(settings, command_timeout=60)
            telemetry = Telemetry(settings, database)
            await database.check()
            source_digests_after = await _legacy_table_digests(database)
            _assert(
                source_digests_before == source_digests_after,
                "9A/9B/9C persisted records changed during migration round-trip",
            )
            report["migration_round_trip"] = {
                "downgrade_to": "0015",
                "upgrade_to": "0016",
                "legacy_table_digests_unchanged": True,
                "legacy_table_count": len(source_digests_before),
                "command_output": migration_output,
            }
            initial_counts = await _db_counts(database)
            eligible = target_pulls["eligible"]
            pull_id = UUID(str(eligible["id"]))
            vehicle_id = UUID(str(eligible["vehicle_id"]))
            cutoff = datetime.now(UTC)

            app = create_app(settings)
            prediction_service: PredictionService = app.state.prediction_service
            prediction_service.model_artifacts = ModelArtifactStore(
                artifact_root / "phase9b"
            )
            prediction_service.anomaly_artifacts = AnomalyArtifactStore(
                artifact_root / "phase9c"
            )
            prediction_service.anomaly_service.artifacts = (
                prediction_service.anomaly_artifacts
            )
            span_exporter_http = InMemorySpanExporter()
            app.state.telemetry.traces.add_span_processor(
                SimpleSpanProcessor(span_exporter_http)
            )
            rss_before_serving = _rss_kib()
            latency_samples: list[float] = []
            coverage: dict[str, dict[str, int]] = {}

            bindings: dict[str, UUID] = {}
            for task, result in trained.items():
                binding_id, _ = await prediction_service.approve_candidate(
                    "next_pull",
                    result.model_version_id,
                    source_role=SourceRole.SYNTHETIC,
                    reason=f"Phase 9D synthetic acceptance for {task.value} controlled serving.",
                    operator_id="phase9d-evaluator",
                    review_reference=f"phase9d-acceptance-{task.value.lower()}",
                    environment_confirmation="test",
                )
                await prediction_service.transition(
                    binding_id,
                    "activate",
                    reason="Activate the reviewed synthetic acceptance version.",
                    operator_id="phase9d-evaluator",
                    environment_confirmation="test",
                )
                bindings[task.value] = binding_id
            for family, version in anomaly_context["versions"].items():
                binding_id, _ = await prediction_service.approve_candidate(
                    "anomaly",
                    version.detector_version_id,
                    source_role=SourceRole.SYNTHETIC,
                    reason=f"Phase 9D synthetic acceptance for the {family} detector.",
                    operator_id="phase9d-evaluator",
                    review_reference=f"phase9d-acceptance-{family}",
                    environment_confirmation="test",
                )
                await prediction_service.transition(
                    binding_id,
                    "activate",
                    reason="Activate the reviewed synthetic detector version.",
                    operator_id="phase9d-evaluator",
                    environment_confirmation="test",
                )
                bindings[family] = binding_id

            # Exercise replacement and rollback through append-only serving events.
            thermal_task = MLTask.THERMAL_DEGRADATION
            prior_binding = bindings[thermal_task.value]
            duplicate_binding, _ = await prediction_service.approve_candidate(
                "next_pull",
                trained[thermal_task].model_version_id,
                source_role=SourceRole.SYNTHETIC,
                reason="Second reviewed synthetic binding for rollback acceptance.",
                operator_id="phase9d-evaluator",
                review_reference="phase9d-rollback-review",
                environment_confirmation="test",
            )
            await prediction_service.transition(
                duplicate_binding,
                "activate",
                reason="Replace the prior active binding for rollback acceptance.",
                operator_id="phase9d-evaluator",
                environment_confirmation="test",
            )
            await prediction_service.transition(
                prior_binding,
                "rollback",
                reason="Restore the previously active reviewed synthetic binding.",
                operator_id="phase9d-evaluator",
                environment_confirmation="test",
            )

            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
                async with httpx.AsyncClient(
                    transport=transport, base_url="http://test"
                ) as client:
                    headers = {"Authorization": f"Bearer {token}"}
                    unauthorized = await client.get(
                        "/api/v1/prediction-service/versions?token=" + token
                    )
                    _assert(
                        unauthorized.status_code == 401,
                        "query-string credential was accepted",
                    )
                    unauthorized_receipt = await client.get(
                        "/api/v1/prediction-service/runs/00000000-0000-0000-0000-000000000001"
                    )
                    _assert(
                        unauthorized_receipt.status_code == 401,
                        "receipt lookup disclosed authorization state",
                    )
                    auth_adversaries: tuple[dict[str, str], ...] = (
                        {},
                        {"Authorization": "Basic " + token},
                        {"Authorization": "Beare " + token},
                        {"Authorization": "Bearer invalid"},
                        {"Authorization": "Bearer " + "x" * 2049},
                        {"Cookie": "prediction_token=" + token},
                        {"X-Forwarded-For": "127.0.0.1"},
                    )
                    for adversary in auth_adversaries:
                        denied = await client.get(
                            "/api/v1/prediction-service/versions",
                            headers=adversary,
                        )
                        _assert(
                            denied.status_code == 401,
                            "an invalid auth channel was accepted",
                        )
                    public_transport = httpx.ASGITransport(
                        app=app, client=("8.8.8.8", 80)
                    )
                    async with httpx.AsyncClient(
                        transport=public_transport, base_url="http://public-test"
                    ) as public_client:
                        public_peer = await public_client.get(
                            "/api/v1/prediction-service/versions",
                            headers={
                                **headers,
                                "X-Forwarded-For": "127.0.0.1",
                            },
                        )
                    _assert(
                        public_peer.status_code == 403,
                        "X-Forwarded-For spoofing bypassed the private network fence",
                    )
                    unauthenticated_invalid_json = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        content=b"{invalid-json",
                        headers={"Content-Type": "application/json"},
                    )
                    _assert(
                        unauthenticated_invalid_json.status_code == 401,
                        "unauthenticated body was parsed before authorization",
                    )
                    body_token = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={"operator_token": token},
                        headers={"Content-Type": "application/json"},
                    )
                    _assert(
                        body_token.status_code == 401, "body credential was accepted"
                    )
                    oversized = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        content=b"x" * (settings.prediction_max_body_bytes + 1),
                        headers={**headers, "Content-Type": "application/json"},
                    )
                    _assert(
                        oversized.status_code == 413,
                        "body budget was not enforced before parsing",
                    )
                    listed = await client.get(
                        "/api/v1/prediction-service/versions", headers=headers
                    )
                    _assert(
                        listed.status_code == 200 and len(listed.json()["items"]) == 7,
                        "active version listing differs",
                    )
                    openapi = (await client.get("/openapi.json")).json()
                    prediction_paths = {
                        path: spec
                        for path, spec in openapi["paths"].items()
                        if path.startswith("/api/v1/prediction-service")
                    }
                    _assert(
                        len(prediction_paths) == 4,
                        "prediction HTTP contract is incomplete",
                    )
                    _assert(
                        all(
                            "security" in operation
                            for path in prediction_paths.values()
                            for operation in path.values()
                        ),
                        "prediction OpenAPI endpoints do not declare bearer security",
                    )
                    _assert(
                        token not in json.dumps(openapi),
                        "operator token leaked into OpenAPI",
                    )

                    for task, trained_result in trained.items():
                        body = {
                            "pull_id": str(pull_id),
                            "vehicle_id": str(vehicle_id),
                            "observation_cutoff": cutoff.isoformat(),
                            "source_role": "synthetic",
                            "task": task.value,
                        }
                        start = time.perf_counter()
                        response = await client.post(
                            "/api/v1/prediction-service/next-pull",
                            json=body,
                            headers={
                                **headers,
                                "Idempotency-Key": f"phase9d-{task.value.lower()}",
                            },
                        )
                        duration = time.perf_counter() - start
                        _assert(
                            response.status_code == 200,
                            f"{task.value} HTTP prediction failed: {response.text}",
                        )
                        result = response.json()
                        _assert(
                            result["status"] == "READY_SCORE",
                            f"{task.value} did not score",
                        )
                        _assert(
                            result["horizon"] == "NEXT_PULL",
                            f"{task.value} horizon changed",
                        )
                        _assert(
                            result["score_is_probability"] is False,
                            "engineering score was mislabeled",
                        )
                        _assert(
                            duration < settings.prediction_request_timeout_seconds,
                            "request exceeded its declared time budget",
                        )
                        latency_samples.append(duration)
                        _assert(
                            not {
                                "source_hash",
                                "provenance_hash",
                                "feature_values",
                                "artifact_path",
                            }
                            & set(result),
                            "private snapshot or artifact metadata was exposed",
                        )
                        snapshot = await prediction_service.repository.feature_snapshot(
                            pull_id, cutoff
                        )
                        _assert(
                            snapshot is not None,
                            "accepted request did not use a persisted FeatureSet",
                        )
                        if snapshot is None:
                            raise AssertionError(
                                "accepted request did not use a persisted FeatureSet"
                            )
                        model_artifact = (
                            await prediction_service.model_artifacts.load_registered(
                                prediction_service.database,
                                str(trained_result.model_version_id),
                                worker=prediction_service.worker,
                            )
                        )
                        features, units, missing, qualities = (
                            prediction_service._model_inputs(model_artifact, snapshot)
                        )
                        direct = await prediction_service.worker(
                            offline_predict,
                            model_artifact,
                            feature_set_version=snapshot.feature_set_version,
                            features=features,
                            units=units,
                            missing=missing,
                            feature_quality=qualities,
                        )
                        _assert(
                            abs(
                                float(result["engineering_validation_score"])
                                - float(direct["engineering_validation_score"])
                            )
                            <= 1e-12,
                            f"{task.value} differs from offline_predict",
                        )
                        _assert(
                            result["decision"]
                            == direct["observable_behavior_prediction"],
                            f"{task.value} decision differs from offline_predict",
                        )
                        _assert(
                            abs(
                                float(result["threshold"])
                                - float(direct["decision_threshold"])
                            )
                            <= 1e-12,
                            f"{task.value} threshold differs from its frozen 9B threshold",
                        )
                        if task is MLTask.THERMAL_DEGRADATION:
                            feature_key = next(
                                key
                                for key in model_artifact.input_schema[
                                    "raw_feature_order"
                                ]
                                if snapshot.values[key].get("value") is not None
                            )
                            invalid_cases: list[tuple[str, Any]] = []
                            bad_unit = copy.deepcopy(snapshot)
                            bad_unit.values[feature_key]["unit"] = "wrong-unit"
                            invalid_cases.append(("unit", bad_unit))
                            bad_nan = copy.deepcopy(snapshot)
                            bad_nan.values[feature_key]["value"] = float("nan")
                            invalid_cases.append(("nan", bad_nan))
                            bad_boolean = copy.deepcopy(snapshot)
                            bad_boolean.values[feature_key]["value"] = True
                            invalid_cases.append(("boolean", bad_boolean))
                            bad_missing_reason = copy.deepcopy(snapshot)
                            bad_missing_reason.values[feature_key]["value"] = None
                            bad_missing_reason.values[feature_key]["missing_reason"] = (
                                None
                            )
                            invalid_cases.append(("missing_reason", bad_missing_reason))
                            for case_name, invalid_snapshot in invalid_cases:
                                try:
                                    prediction_service._model_inputs(
                                        model_artifact, invalid_snapshot
                                    )
                                except PredictionError:
                                    continue
                                raise AssertionError(
                                    f"malformed persisted feature {case_name} was accepted"
                                )
                            report["boundary_checks"]["feature_schema_adversaries"] = (
                                True
                            )
                        changed_body = {
                            **body,
                            "observation_cutoff": (
                                cutoff + timedelta(microseconds=1)
                            ).isoformat(),
                        }
                        conflicting_replay = await client.post(
                            "/api/v1/prediction-service/next-pull",
                            json=changed_body,
                            headers={
                                **headers,
                                "Idempotency-Key": f"phase9d-{task.value.lower()}",
                            },
                        )
                        _assert(
                            conflicting_replay.status_code == 409,
                            "a changed cutoff reused an existing client idempotency key",
                        )
                        second, third = await asyncio.gather(
                            client.post(
                                "/api/v1/prediction-service/next-pull",
                                json=body,
                                headers={
                                    **headers,
                                    "Idempotency-Key": f"phase9d-replay-{task.value.lower()}",
                                },
                            ),
                            client.post(
                                "/api/v1/prediction-service/next-pull",
                                json=body,
                                headers={
                                    **headers,
                                    "Idempotency-Key": f"phase9d-replay-{task.value.lower()}",
                                },
                            ),
                        )
                        _assert(
                            second.status_code == third.status_code == 200,
                            "concurrent replay failed",
                        )
                        _assert(
                            second.json()["receipt_id"] == third.json()["receipt_id"],
                            "concurrent replay produced different receipts",
                        )
                        report["tasks"][task.value] = {
                            "model_version_id": str(trained_result.model_version_id),
                            "binding_id": str(bindings[task.value]),
                            "receipt_id": result["receipt_id"],
                            "score": result["engineering_validation_score"],
                            "threshold": result["threshold"],
                            "decision": result["decision"],
                            "direct_offline_equal": True,
                            "concurrent_replay_same_receipt": True,
                            "duration_seconds": round(duration, 6),
                        }
                        coverage[task.value] = {
                            "requested": 1,
                            "authorized": 1,
                            "admitted": 1,
                            "approved": 1,
                            "eligible": 1,
                            "scored": int(result["status"] == "READY_SCORE"),
                            "abstained": int(result["status"] != "READY_SCORE"),
                            "failed": 0,
                        }

                    # A later ingestion and a late-created metadata row must not
                    # rewrite the already-persisted as-of snapshot or receipt.
                    thermal_body = {
                        "pull_id": str(pull_id),
                        "vehicle_id": str(vehicle_id),
                        "observation_cutoff": cutoff.isoformat(),
                        "source_role": "synthetic",
                        "task": thermal_task.value,
                    }
                    snapshot_before_late_ingestion = (
                        await prediction_service.repository.feature_snapshot(
                            pull_id, cutoff
                        )
                    )
                    _assert(
                        snapshot_before_late_ingestion is not None,
                        "eligible pull lost its persisted as-of FeatureSet",
                    )
                    if snapshot_before_late_ingestion is None:
                        raise AssertionError(
                            "eligible pull lost its persisted as-of FeatureSet"
                        )
                    late_records = await _inject_late_records(
                        database,
                        snapshot_before_late_ingestion,
                        cutoff,
                    )
                    snapshot_after_late_ingestion = (
                        await prediction_service.repository.feature_snapshot(
                            pull_id, cutoff
                        )
                    )
                    _assert(
                        snapshot_after_late_ingestion is not None
                        and snapshot_after_late_ingestion.feature_set_id
                        == snapshot_before_late_ingestion.feature_set_id
                        and snapshot_after_late_ingestion.source_hash
                        == snapshot_before_late_ingestion.source_hash
                        and snapshot_after_late_ingestion.provenance_hash
                        == snapshot_before_late_ingestion.provenance_hash,
                        "post-cutoff inputs changed the canonical as-of feature snapshot",
                    )
                    replay_after_late_ingestion = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json=thermal_body,
                        headers={
                            **headers,
                            "Idempotency-Key": "test-key-1",
                        },
                    )
                    _assert(
                        replay_after_late_ingestion.status_code == 200
                        and replay_after_late_ingestion.json()["receipt_id"]
                        == report["tasks"][thermal_task.value]["receipt_id"],
                        "late-ingested inputs changed the historical prediction receipt",
                    )
                    report["boundary_checks"]["late_ingestion_cutoff_invariant"] = True
                    report["late_input_sentinels"] = {
                        "sample_ingested_after_cutoff": late_records[
                            "ingested_at"
                        ].isoformat(),
                        "modification_created_after_cutoff": late_records[
                            "modification_created_at"
                        ].isoformat(),
                        "feature_set_id_unchanged": True,
                        "source_hash_unchanged": True,
                        "provenance_hash_unchanged": True,
                        "receipt_id_unchanged": True,
                    }

                    for family, frozen in anomaly_context["versions"].items():
                        test_pull = primary.pulls_by_session[12][0]
                        body = {
                            "pull_id": str(test_pull.pull_id),
                            "vehicle_id": str(test_pull.vehicle_id),
                            "observation_cutoff": (
                                datetime.now(UTC) + timedelta(seconds=1)
                            ).isoformat(),
                            "source_role": "synthetic",
                            "family": family,
                        }
                        start = time.perf_counter()
                        response = await client.post(
                            "/api/v1/prediction-service/anomalies",
                            json=body,
                            headers=headers,
                        )
                        _assert(
                            response.status_code == 200,
                            f"{family} HTTP anomaly result failed",
                        )
                        result = response.json()
                        anomaly_duration = time.perf_counter() - start
                        latency_samples.append(anomaly_duration)
                        direct_run = await prediction_service.anomaly_service.score_detector_version(
                            detector_version_id=frozen.detector_version_id,
                            pull_ids=(test_pull.pull_id,),
                            observation_cutoff=datetime.fromisoformat(
                                body["observation_cutoff"]
                            ),
                            source_role=SourceRole.SYNTHETIC,
                        )
                        _assert(
                            len(direct_run.finding_ids) == 1,
                            f"{family} direct 9C finding missing",
                        )
                        _assert(
                            result["lineage"]["anomaly_finding_id"]
                            == str(direct_run.finding_ids[0]),
                            f"{family} did not bind the canonical finding",
                        )
                        async with prediction_service.database.session() as db:
                            direct_finding = (
                                (
                                    await db.execute(
                                        text(
                                            "SELECT score,threshold,status,coverage,feature_set_id "
                                            "FROM anomaly_findings WHERE id=:id"
                                        ),
                                        {"id": direct_run.finding_ids[0]},
                                    )
                                )
                                .mappings()
                                .one()
                            )
                        finding_status = AnomalyStatus(str(direct_finding["status"]))
                        expected_result_status = (
                            PredictionStatus.READY_SCORE.value
                            if finding_status
                            in {AnomalyStatus.ANOMALOUS, AnomalyStatus.INLIER}
                            else {
                                AnomalyStatus.INSUFFICIENT_REFERENCE: PredictionStatus.ABSTAINED_INSUFFICIENT_REFERENCE,
                                AnomalyStatus.INSUFFICIENT_SIGNAL: PredictionStatus.ABSTAINED_INSUFFICIENT_SIGNAL,
                                AnomalyStatus.LOW_QUALITY: PredictionStatus.ABSTAINED_LOW_QUALITY,
                                AnomalyStatus.INCOMPATIBLE_CONTEXT: PredictionStatus.ABSTAINED_INCOMPATIBLE_CONTEXT,
                                AnomalyStatus.UNSUPPORTED_SOURCE: PredictionStatus.ABSTAINED_UNSUPPORTED_SOURCE,
                                AnomalyStatus.NOT_EVALUABLE: PredictionStatus.ABSTAINED_CUTOFF,
                            }[finding_status].value
                        )
                        _assert(
                            result["status"] == expected_result_status,
                            f"{family} 9D outcome differs from the canonical 9C finding",
                        )
                        _assert(
                            result["threshold"] == direct_finding["threshold"],
                            f"{family} threshold differs from frozen 9C threshold",
                        )
                        if finding_status in {
                            AnomalyStatus.ANOMALOUS,
                            AnomalyStatus.INLIER,
                        }:
                            _assert(
                                abs(
                                    float(result["anomaly_score"])
                                    - float(direct_finding["score"])
                                )
                                <= 1e-12,
                                f"{family} score differs from 9C",
                            )
                            _assert(
                                result["decision"] == finding_status.value,
                                f"{family} decision differs from 9C",
                            )
                        else:
                            _assert(
                                result["anomaly_score"] is None
                                and result["decision"] is None,
                                f"{family} abstention exposed a misleading numeric result",
                            )
                        _assert(
                            result["lineage"]["feature_set_id"]
                            == str(direct_finding["feature_set_id"]),
                            f"{family} did not retain canonical FeatureSet lineage",
                        )
                        report["anomaly_families"][family] = {
                            "detector_version_id": str(frozen.detector_version_id),
                            "binding_id": str(bindings[family]),
                            "status": result["status"],
                            "direct_9c_status": finding_status.value,
                            "score": result["anomaly_score"],
                            "threshold": result["threshold"],
                            "finding_id": result["lineage"]["anomaly_finding_id"],
                            "direct_9c_equal": True,
                            "method_and_threshold": anomaly_context["evidence"][family],
                        }
                        coverage[family] = {
                            "requested": 1,
                            "authorized": 1,
                            "admitted": 1,
                            "approved": 1,
                            "eligible": 1,
                            "scored": int(
                                result["status"] == PredictionStatus.READY_SCORE.value
                            ),
                            "abstained": int(
                                result["status"] != PredictionStatus.READY_SCORE.value
                            ),
                            "failed": 0,
                        }

                    other_vehicle_pull = secondary.pulls_by_session[0][0]
                    cross_vehicle_anomaly = await client.post(
                        "/api/v1/prediction-service/anomalies",
                        json={
                            "pull_id": str(other_vehicle_pull.pull_id),
                            "vehicle_id": str(other_vehicle_pull.vehicle_id),
                            "observation_cutoff": datetime.now(UTC).isoformat(),
                            "source_role": "synthetic",
                            "family": "thermal",
                        },
                        headers=headers,
                    )
                    _assert(
                        cross_vehicle_anomaly.status_code == 200
                        and cross_vehicle_anomaly.json()["status"]
                        == PredictionStatus.ABSTAINED_INCOMPATIBLE_CONTEXT.value,
                        "9C pooled a pull across its approved exact-vehicle reference cohort",
                    )
                    report["boundary_checks"]["cross_vehicle_reference_isolated"] = True

                    # Include cold first calls, warm artifact reloads, all model and detector
                    # paths, and a bounded near-capacity HTTP burst. These are observations,
                    # not an environment-independent latency SLA.
                    task_entries = list(trained.items())
                    family_entries = list(anomaly_context["versions"].items())
                    benchmark_cases = [
                        ("next_pull", task, None) for task, _result in task_entries
                    ] + [
                        ("anomaly", None, family) for family, _version in family_entries
                    ]
                    for index in range(27):
                        case_kind, case_task, case_family = benchmark_cases[
                            index % len(benchmark_cases)
                        ]
                        request_cutoff = datetime.now(UTC)
                        if case_kind == "next_pull":
                            assert case_task is not None
                            benchmark_body = {
                                "pull_id": str(pull_id),
                                "vehicle_id": str(vehicle_id),
                                "observation_cutoff": request_cutoff.isoformat(),
                                "source_role": "synthetic",
                                "task": case_task.value,
                            }
                            endpoint = "/api/v1/prediction-service/next-pull"
                            coverage_key = case_task.value
                        else:
                            benchmark_pull = primary.pulls_by_session[12][0]
                            assert case_family is not None
                            benchmark_body = {
                                "pull_id": str(benchmark_pull.pull_id),
                                "vehicle_id": str(benchmark_pull.vehicle_id),
                                "observation_cutoff": request_cutoff.isoformat(),
                                "source_role": "synthetic",
                                "family": case_family,
                            }
                            endpoint = "/api/v1/prediction-service/anomalies"
                            coverage_key = case_family
                        start = time.perf_counter()
                        benchmark_response = await client.post(
                            endpoint,
                            json=benchmark_body,
                            headers={
                                **headers,
                                "Idempotency-Key": f"phase9d-benchmark-{index:03d}",
                            },
                        )
                        elapsed = time.perf_counter() - start
                        _assert(
                            benchmark_response.status_code == 200,
                            "bounded benchmark request failed",
                        )
                        _assert(
                            elapsed < settings.prediction_request_timeout_seconds,
                            "bounded benchmark exceeded the request timeout",
                        )
                        latency_samples.append(elapsed)
                        bucket = coverage[coverage_key]
                        bucket["requested"] += 1
                        bucket["authorized"] += 1
                        bucket["admitted"] += 1
                        bucket["eligible"] += 1
                        if (
                            benchmark_response.json()["status"]
                            == PredictionStatus.READY_SCORE
                        ):
                            bucket["scored"] += 1
                        else:
                            bucket["abstained"] += 1

                    burst_started = datetime.now(UTC)

                    async def bounded_burst(index: int) -> tuple[int, float]:
                        task = task_entries[index % len(task_entries)][0]
                        burst_body = {
                            "pull_id": str(pull_id),
                            "vehicle_id": str(vehicle_id),
                            "observation_cutoff": (
                                burst_started + timedelta(milliseconds=index)
                            ).isoformat(),
                            "source_role": "synthetic",
                            "task": task.value,
                        }
                        started = time.perf_counter()
                        burst_response = await client.post(
                            "/api/v1/prediction-service/next-pull",
                            json=burst_body,
                            headers={
                                **headers,
                                "Idempotency-Key": f"phase9d-burst-{index:02d}",
                            },
                        )
                        return burst_response.status_code, time.perf_counter() - started

                    burst_results = await asyncio.gather(
                        *(bounded_burst(index) for index in range(10))
                    )
                    _assert(
                        all(
                            status in {200, 429} for status, _duration in burst_results
                        ),
                        "near-capacity burst escaped its bounded HTTP outcomes",
                    )
                    _assert(
                        app.state.prediction_budget_state.peak_in_flight
                        <= settings.prediction_max_concurrent_requests,
                        "request middleware exceeded its concurrency budget",
                    )
                    latency_samples.extend(
                        duration for status, duration in burst_results if status == 200
                    )
                    report["benchmark"] = {
                        "sample_count": len(latency_samples),
                        "percentile_state": "measured"
                        if len(latency_samples) >= 30
                        else "insufficient_samples",
                        "p50_seconds": _percentile(latency_samples, 0.50)
                        if len(latency_samples) >= 30
                        else None,
                        "p95_seconds": _percentile(latency_samples, 0.95)
                        if len(latency_samples) >= 30
                        else None,
                        "p99_seconds": _percentile(latency_samples, 0.99)
                        if len(latency_samples) >= 30
                        else None,
                        "median_seconds": statistics.median(latency_samples),
                        "burst_requested": len(burst_results),
                        "burst_status_counts": {
                            str(status): sum(
                                1
                                for current, _duration in burst_results
                                if current == status
                            )
                            for status in {
                                status for status, _duration in burst_results
                            }
                        },
                        "observed_peak_in_flight": app.state.prediction_budget_state.peak_in_flight,
                        "configured_max_in_flight": settings.prediction_max_concurrent_requests,
                        "configured_cpu_workers": settings.prediction_max_cpu_concurrency,
                        "latency_is_sla": False,
                    }

                    model_id = trained[MLTask.THERMAL_DEGRADATION].model_version_id
                    model_row = await prediction_service.repository.model_candidate(
                        model_id
                    )
                    if model_row is None:
                        raise AssertionError("registered model candidate disappeared")
                    model_path = prediction_service.model_artifacts.root / str(
                        model_row["artifact_path"]
                    )
                    original_model_bytes = model_path.read_bytes()
                    model_path.write_bytes(
                        bytes([original_model_bytes[0] ^ 0x01])
                        + original_model_bytes[1:]
                    )
                    try:
                        corrupt_model = await client.post(
                            "/api/v1/prediction-service/next-pull",
                            json={
                                "pull_id": str(pull_id),
                                "vehicle_id": str(vehicle_id),
                                "observation_cutoff": datetime.now(UTC).isoformat(),
                                "source_role": "synthetic",
                                "task": MLTask.THERMAL_DEGRADATION.value,
                            },
                            headers={
                                **headers,
                                "Idempotency-Key": "phase9d-corrupt-model-artifact",
                            },
                        )
                        _assert(
                            corrupt_model.status_code == 409
                            and model_path.as_posix() not in corrupt_model.text,
                            "tampered supervised artifact was loaded or disclosed",
                        )
                    finally:
                        model_path.write_bytes(original_model_bytes)

                    detector_id = anomaly_context["versions"][
                        "thermal"
                    ].detector_version_id
                    detector_row = (
                        await prediction_service.repository.detector_candidate(
                            detector_id
                        )
                    )
                    if detector_row is None:
                        raise AssertionError(
                            "registered detector candidate disappeared"
                        )
                    detector_path = prediction_service.anomaly_artifacts.root / str(
                        detector_row["artifact_path"]
                    )
                    original_detector_bytes = detector_path.read_bytes()
                    detector_path.write_bytes(
                        bytes([original_detector_bytes[0] ^ 0x01])
                        + original_detector_bytes[1:]
                    )
                    try:
                        corrupt_detector = await client.post(
                            "/api/v1/prediction-service/anomalies",
                            json={
                                "pull_id": str(primary.pulls_by_session[12][0].pull_id),
                                "vehicle_id": str(
                                    primary.pulls_by_session[12][0].vehicle_id
                                ),
                                "observation_cutoff": datetime.now(UTC).isoformat(),
                                "source_role": "synthetic",
                                "family": "thermal",
                            },
                            headers=headers,
                        )
                        _assert(
                            corrupt_detector.status_code == 409
                            and detector_path.as_posix() not in corrupt_detector.text,
                            "tampered detector artifact was loaded or disclosed",
                        )
                    finally:
                        detector_path.write_bytes(original_detector_bytes)
                    report["boundary_checks"]["model_and_detector_tampering_denied"] = (
                        True
                    )

                    failed_receipt_body = {
                        "pull_id": str(primary.pulls_by_session[12][0].pull_id),
                        "vehicle_id": str(primary.pulls_by_session[12][0].vehicle_id),
                        "observation_cutoff": datetime.now(UTC).isoformat(),
                        "source_role": "synthetic",
                        "family": "boost_air",
                    }
                    async with prediction_service.database.session() as db:
                        before_failed_receipt = int(
                            await db.scalar(
                                text("SELECT count(*) FROM prediction_receipts")
                            )
                            or 0
                        )
                    with patch.object(
                        prediction_service.repository,
                        "persist_receipt",
                        new=AsyncMock(
                            side_effect=RuntimeError("controlled persistence failure")
                        ),
                    ):
                        failed_receipt = await client.post(
                            "/api/v1/prediction-service/anomalies",
                            json=failed_receipt_body,
                            headers={
                                **headers,
                                "Idempotency-Key": "phase9d-failed-receipt-retry",
                            },
                        )
                    _assert(
                        failed_receipt.status_code == 500
                        and failed_receipt.json()["error"]["code"] == "INTERNAL_ERROR",
                        "receipt persistence failure was not sanitized",
                    )
                    async with prediction_service.database.session() as db:
                        after_failed_receipt = int(
                            await db.scalar(
                                text("SELECT count(*) FROM prediction_receipts")
                            )
                            or 0
                        )
                    _assert(
                        before_failed_receipt == after_failed_receipt,
                        "failed receipt persistence left a partial 9D receipt",
                    )
                    recovered_receipt = await client.post(
                        "/api/v1/prediction-service/anomalies",
                        json=failed_receipt_body,
                        headers={
                            **headers,
                            "Idempotency-Key": "phase9d-failed-receipt-retry",
                        },
                    )
                    _assert(
                        recovered_receipt.status_code == 200,
                        "retry did not recover a failed 9D receipt write",
                    )
                    report["boundary_checks"]["failed_receipt_recovered"] = True

                    fuel_pull = target_pulls["missing_fuel"]
                    missing_fuel_response = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(fuel_pull["id"]),
                            "vehicle_id": str(fuel_pull["vehicle_id"]),
                            "observation_cutoff": datetime.now(UTC).isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.FUEL_DEVIATION.value,
                        },
                        headers={**headers, "Idempotency-Key": "phase9d-missing-fuel"},
                    )
                    _assert(
                        missing_fuel_response.status_code == 200,
                        "missing fuel was not a typed result",
                    )
                    _assert(
                        missing_fuel_response.json()["status"]
                        == PredictionStatus.ABSTAINED_INSUFFICIENT_SIGNAL.value,
                        "fuel pressure was fabricated or silently imputed",
                    )
                    quality_pull = target_pulls["low_quality"]
                    low_quality = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(quality_pull["id"]),
                            "vehicle_id": str(quality_pull["vehicle_id"]),
                            "observation_cutoff": datetime.now(UTC).isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.THERMAL_DEGRADATION.value,
                        },
                        headers={**headers, "Idempotency-Key": "phase9d-low-quality"},
                    )
                    _assert(
                        low_quality.status_code == 200
                        and low_quality.json()["status"]
                        == PredictionStatus.ABSTAINED_LOW_QUALITY.value,
                        "low-quality input did not abstain",
                    )
                    unsupported_source = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(pull_id),
                            "vehicle_id": str(vehicle_id),
                            "observation_cutoff": datetime.now(UTC).isoformat(),
                            "source_role": "real_vehicle",
                            "task": MLTask.THERMAL_DEGRADATION.value,
                        },
                        headers=headers,
                    )
                    _assert(
                        unsupported_source.status_code == 409,
                        "synthetic version was exposed to an unapproved real-vehicle role",
                    )
                    unapproved_version = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(pull_id),
                            "vehicle_id": str(vehicle_id),
                            "observation_cutoff": datetime.now(UTC).isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.THERMAL_DEGRADATION.value,
                            "model_version_id": str(UUID(int=0)),
                        },
                        headers=headers,
                    )
                    _assert(
                        unapproved_version.status_code == 409,
                        "request-selected unapproved model version was served",
                    )
                    mixed_source = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(pull_id),
                            "vehicle_id": str(vehicle_id),
                            "observation_cutoff": datetime.now(UTC).isoformat(),
                            "source_role": "mixed",
                            "task": MLTask.THERMAL_DEGRADATION.value,
                        },
                        headers=headers,
                    )
                    _assert(
                        mixed_source.status_code == 422,
                        "mixed source role was accepted",
                    )
                    future_cutoff = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(pull_id),
                            "vehicle_id": str(vehicle_id),
                            "observation_cutoff": (
                                datetime.now(UTC)
                                + timedelta(
                                    seconds=settings.prediction_max_future_cutoff_seconds
                                    + 1
                                )
                            ).isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.THERMAL_DEGRADATION.value,
                        },
                        headers=headers,
                    )
                    _assert(
                        future_cutoff.status_code == 422, "future cutoff was accepted"
                    )
                    no_feature_cutoff = late_feature_pull.ended_at + timedelta(
                        seconds=1
                    )
                    no_feature_body = {
                        "pull_id": str(late_feature_pull.pull_id),
                        "vehicle_id": str(late_feature_pull.vehicle_id),
                        "observation_cutoff": no_feature_cutoff.isoformat(),
                        "source_role": "synthetic",
                        "task": MLTask.THERMAL_DEGRADATION.value,
                    }
                    before_no_feature_request = await _db_counts(database)
                    before_feature_cutoff = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json=no_feature_body,
                        headers={
                            **headers,
                            "Idempotency-Key": "phase9d-no-feature-yet",
                        },
                    )
                    _assert(
                        before_feature_cutoff.status_code == 200
                        and before_feature_cutoff.json()["status"]
                        == PredictionStatus.ABSTAINED_INSUFFICIENT_SIGNAL.value,
                        "missing as-of FeatureSet did not abstain",
                    )
                    after_no_feature_request = await _db_counts(database)
                    _assert(
                        before_no_feature_request == after_no_feature_request,
                        "serving generated Phase 9A features implicitly",
                    )
                    late_feature_cutoff = datetime.now(UTC) + timedelta(seconds=60)
                    await FeatureGenerationService(database, telemetry).generate_pull(
                        late_feature_pull.pull_id, late_feature_cutoff
                    )
                    late_feature_snapshot = (
                        await prediction_service.repository.feature_snapshot(
                            late_feature_pull.pull_id, late_feature_cutoff
                        )
                    )
                    _assert(
                        late_feature_snapshot is not None,
                        "offline preparation did not persist a canonical 9A FeatureSet",
                    )
                    if late_feature_snapshot is None:
                        raise AssertionError(
                            "offline preparation did not persist a canonical 9A FeatureSet"
                        )
                    replay_before_late_feature = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json=no_feature_body,
                        headers={
                            **headers,
                            "Idempotency-Key": "phase9d-no-feature-yet",
                        },
                    )
                    _assert(
                        replay_before_late_feature.status_code == 200
                        and replay_before_late_feature.json()["receipt_id"]
                        == before_feature_cutoff.json()["receipt_id"],
                        "a later FeatureSet changed a prior cutoff receipt",
                    )
                    after_offline_feature_preparation = await _db_counts(database)
                    late_feature_request = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            **no_feature_body,
                            "observation_cutoff": late_feature_cutoff.isoformat(),
                        },
                        headers={
                            **headers,
                            "Idempotency-Key": "phase9d-after-late-feature",
                        },
                    )
                    _assert(
                        late_feature_request.status_code == 200
                        and late_feature_request.json()["lineage"]["feature_set_id"]
                        == str(late_feature_snapshot.feature_set_id),
                        "later authorized cutoff did not select its persisted FeatureSet",
                    )
                    initial_counts = after_offline_feature_preparation
                    report["boundary_checks"]["no_implicit_feature_generation"] = True
                    report["boundary_checks"]["late_feature_cutoff_isolated"] = True
                    wrong_vehicle = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(pull_id),
                            "vehicle_id": str(UUID(int=0)),
                            "observation_cutoff": cutoff.isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.THERMAL_DEGRADATION.value,
                        },
                        headers=headers,
                    )
                    _assert(
                        wrong_vehicle.status_code == 404,
                        "wrong vehicle identity was exposed",
                    )
                    before_end = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(pull_id),
                            "vehicle_id": str(vehicle_id),
                            "observation_cutoff": (
                                eligible["ended_at"] - timedelta(seconds=1)
                            ).isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.THERMAL_DEGRADATION.value,
                        },
                        headers=headers,
                    )
                    _assert(
                        before_end.status_code == 422,
                        "cutoff before pull end was accepted",
                    )

                    thermal_binding_id = bindings[MLTask.THERMAL_DEGRADATION.value]
                    admission_binding = await prediction_service.repository.binding(
                        thermal_binding_id
                    )
                    if admission_binding is None:
                        raise AssertionError("active serving binding disappeared")
                    race_body = {
                        "pull_id": str(pull_id),
                        "vehicle_id": str(vehicle_id),
                        "observation_cutoff": datetime.now(UTC).isoformat(),
                        "source_role": "synthetic",
                        "task": MLTask.THERMAL_DEGRADATION.value,
                    }
                    scoring_entered = asyncio.Event()
                    allow_scoring = asyncio.Event()
                    actual_worker = prediction_service.worker

                    async def gated_worker(fn: Any, *args: Any, **kwargs: Any) -> Any:
                        if fn is offline_predict:
                            scoring_entered.set()
                            await allow_scoring.wait()
                        return await actual_worker(fn, *args, **kwargs)

                    with patch.object(prediction_service, "worker", new=gated_worker):
                        in_flight_request = asyncio.create_task(
                            client.post(
                                "/api/v1/prediction-service/next-pull",
                                json=race_body,
                                headers={
                                    **headers,
                                    "Idempotency-Key": "test-key-2",
                                },
                            )
                        )
                        async with asyncio.timeout(
                            settings.prediction_request_timeout_seconds
                        ):
                            await scoring_entered.wait()
                        await prediction_service.transition(
                            thermal_binding_id,
                            "revoke",
                            reason="Revoke during a request after its binding snapshot was admitted.",
                            operator_id="phase9d-evaluator",
                            environment_confirmation="test",
                        )
                        allow_scoring.set()
                        in_flight_response = await in_flight_request
                    _assert(
                        in_flight_response.status_code == 200,
                        "an in-flight request lost its captured approval snapshot",
                    )
                    async with prediction_service.database.session() as db:
                        captured_event_id = await db.scalar(
                            text(
                                "SELECT binding_event_id FROM prediction_receipts WHERE id=:id"
                            ),
                            {"id": in_flight_response.json()["receipt_id"]},
                        )
                    _assert(
                        captured_event_id == admission_binding.latest_event_id,
                        "in-flight receipt did not retain its admitted binding event",
                    )
                    denied_after_race_revoke = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json=race_body,
                        headers={
                            **headers,
                            "Idempotency-Key": "test-key-2",
                        },
                    )
                    _assert(
                        denied_after_race_revoke.status_code == 409,
                        "revoked binding served or replayed a new request after the race",
                    )
                    report["boundary_checks"]["revocation_race_snapshot_preserved"] = (
                        True
                    )

                    # Revoke a served version; an old idempotency key must not resurrect it.
                    revocation = await prediction_service.transition(
                        bindings[MLTask.PERFORMANCE_DEGRADATION.value],
                        "revoke",
                        reason="Revoke after controlled acceptance lifecycle assertion.",
                        operator_id="phase9d-evaluator",
                        environment_confirmation="test",
                    )
                    denied_after_revoke = await client.post(
                        "/api/v1/prediction-service/next-pull",
                        json={
                            "pull_id": str(pull_id),
                            "vehicle_id": str(vehicle_id),
                            "observation_cutoff": cutoff.isoformat(),
                            "source_role": "synthetic",
                            "task": MLTask.PERFORMANCE_DEGRADATION.value,
                        },
                        headers={
                            **headers,
                            "Idempotency-Key": "phase9d-performance-degradation",
                        },
                    )
                    _assert(
                        denied_after_revoke.status_code == 409,
                        "revoked approval served or replayed a stale receipt",
                    )
                    retrieved = await client.get(
                        "/api/v1/prediction-service/runs/"
                        + report["tasks"][MLTask.PERFORMANCE_DEGRADATION.value][
                            "receipt_id"
                        ],
                        headers=headers,
                    )
                    _assert(
                        retrieved.status_code == 200, "durable receipt retrieval failed"
                    )
                    _assert(
                        retrieved.json()["receipt_id"]
                        == report["tasks"][MLTask.PERFORMANCE_DEGRADATION.value][
                            "receipt_id"
                        ],
                        "receipt retrieval returned a different immutable receipt",
                    )
                    report["boundary_checks"].update(
                        {
                            "query_credential_denied": True,
                            "body_budget_enforced": True,
                            "approval_rollback_verified": True,
                            "missing_fuel_abstained": True,
                            "low_quality_abstained": True,
                            "missing_as_of_features_abstained": True,
                            "wrong_vehicle_hidden": True,
                            "cutoff_before_pull_rejected": True,
                            "revocation_precedes_replay": True,
                            "revocation_event_id": str(revocation[1]),
                            "receipt_read_status": retrieved.status_code,
                        }
                    )
                    app_metrics = app.state.telemetry.render_metrics().decode("utf-8")
                    app_trace_names = sorted(
                        {span.name for span in span_exporter_http.get_finished_spans()}
                    )
                    peak_in_flight = app.state.prediction_budget_state.peak_in_flight
                    rss_after_serving = _rss_kib()

            after_counts = await _db_counts(database)
            for key in initial_counts:
                _assert(
                    initial_counts[key] == after_counts[key],
                    f"serving mutated vehicle-domain table {key}",
                )
            async with database.session() as db:
                receipt_count = int(
                    await db.scalar(text("SELECT count(*) FROM prediction_receipts"))
                    or 0
                )
                immutable_id = await db.scalar(
                    text(
                        "SELECT id FROM prediction_receipts ORDER BY created_at LIMIT 1"
                    )
                )
                _assert(receipt_count >= 12, "serving did not persist durable receipts")
                if immutable_id is not None:
                    try:
                        await db.execute(
                            text(
                                "UPDATE prediction_receipts SET reason_code='tampered' WHERE id=:id"
                            ),
                            {"id": immutable_id},
                        )
                        await db.commit()
                    except SQLAlchemyError:
                        await db.rollback()
                    else:
                        raise AssertionError(
                            "prediction receipt mutation was not blocked"
                        )
                event_rows = (
                    (
                        await db.execute(
                            text(
                                "SELECT event_type,count(*) AS count FROM prediction_serving_events "
                                "GROUP BY event_type ORDER BY event_type"
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
                try:
                    await db.execute(
                        text(
                            "UPDATE prediction_serving_events SET reason='tampered' WHERE id=(SELECT id FROM prediction_serving_events LIMIT 1)"
                        )
                    )
                    await db.commit()
                except SQLAlchemyError:
                    await db.rollback()
                else:
                    raise AssertionError(
                        "serving event ledger mutation was not blocked"
                    )
            report["receipt_count"] = receipt_count
            report["database_before"] = initial_counts
            report["database_after"] = after_counts
            report["approval_count"] = len(bindings) + 1
            report["approval_events"] = {
                str(row["event_type"]): int(row["count"]) for row in event_rows
            }
            report["coverage"] = coverage
            report["observability"] = {
                "metrics": app_metrics,
                "request_trace_names": app_trace_names,
                "entity_ids_excluded_from_metrics": True,
                "token_excluded_from_metrics": token not in app_metrics,
            }
            metric_text = str(report["observability"]["metrics"])
            _assert(
                "prediction_service_requests" in metric_text,
                "prediction counters were not exported",
            )
            _assert(
                token not in metric_text
                and str(pull_id) not in metric_text
                and str(vehicle_id) not in metric_text,
                "sensitive values leaked into metrics",
            )
            expected_spans = {
                "prediction.request.admission",
                "prediction.request.denied",
                "prediction.binding.resolve",
                "prediction.feature.lookup",
                "prediction.artifact.verify",
                "prediction.model.score",
                "prediction.anomaly.score",
                "prediction.receipt.persist",
            }
            observed_spans = set(report["observability"]["request_trace_names"])
            _assert(
                expected_spans.issubset(observed_spans),
                f"prediction trace stages are missing: {expected_spans - observed_spans}",
            )
            report["resource_observations"] = {
                "rss_before_serving_kib": rss_before_serving,
                "rss_after_serving_kib": rss_after_serving,
                "peak_in_flight": peak_in_flight,
                "max_body_bytes": settings.prediction_max_body_bytes,
                "max_pull_batch_size": 1,
                "max_cpu_workers": settings.prediction_max_cpu_concurrency,
                "request_timeout_seconds": settings.prediction_request_timeout_seconds,
            }
            artifact_files = [
                path
                for path in artifact_root.rglob("*")
                if path.is_file() and not path.is_symlink()
            ]
            report["resource_observations"].update(
                {
                    "artifact_file_count": len(artifact_files),
                    "artifact_total_bytes": sum(
                        path.stat().st_size for path in artifact_files
                    ),
                    "artifact_max_bytes": max(
                        (path.stat().st_size for path in artifact_files), default=0
                    ),
                    "artifact_size_limit_bytes": 50 * 1024 * 1024,
                }
            )
            _assert(
                all(path.stat().st_size <= 50 * 1024 * 1024 for path in artifact_files),
                "generated artifact exceeded the configured trusted loader size ceiling",
            )
            report["execution_state"] = "PASS"
            report["status"] = "PASS"
            report["git_sha"] = os.environ.get("GIT_SHA", "unavailable")
    finally:
        telemetry.shutdown()
        await database.close()
    return report


async def main() -> None:
    report = await evaluate()
    evidence = Path(".validation/phase9d")
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "acceptance.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    summary = {
        "status": report["status"],
        "tasks": {
            key: value["direct_offline_equal"] for key, value in report["tasks"].items()
        },
        "anomaly_families": {
            key: value["direct_9c_equal"]
            for key, value in report["anomaly_families"].items()
        },
        "receipts": report["receipt_count"],
        "real_world_accuracy_claimed": report["real_world_accuracy_claimed"],
        "full_report": str(evidence / "acceptance.json"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
