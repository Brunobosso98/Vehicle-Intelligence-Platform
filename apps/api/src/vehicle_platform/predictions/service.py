from __future__ import annotations

import asyncio
import hashlib
import hmac
import math
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any, TypeVar, cast
from uuid import UUID, uuid4

from sqlalchemy import text
from threadpoolctl import threadpool_limits

from vehicle_platform.anomalies.artifacts import (
    AnomalyArtifactError,
)
from vehicle_platform.anomalies.artifacts import (
    ArtifactStore as AnomalyArtifactStore,
)
from vehicle_platform.anomalies.domain import AnomalyStatus, SourceRole
from vehicle_platform.anomalies.service import AnomalyService
from vehicle_platform.core.config import Settings
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.features.service import default_feature_version
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import (
    ArtifactStore as ModelArtifactStore,
)
from vehicle_platform.ml.artifacts import (
    ArtifactValidationError,
    TrustedModelArtifact,
    offline_predict,
)
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.predictions.domain import (
    AnomalyDecision,
    AnomalyRequest,
    FeatureSnapshot,
    NextPullRequest,
    PredictionError,
    PredictionKind,
    PredictionLineage,
    PredictionQuality,
    PredictionResponse,
    PredictionStatus,
    ServingBinding,
    ServingCandidate,
)
from vehicle_platform.predictions.repository import (
    CONTROLLED_SCOPE,
    FEATURE_SET_VERSION,
    PredictionRepository,
    json_object,
)

_MODEL_INTERPRETATION = "Engineering-validation score, not a real-world failure probability."
_ANOMALY_INTERPRETATION = "Offline engineering deviation, not a confirmed fault or diagnosis."
_LIMITATION = (
    "Retrospective, controlled-dataset output. It cannot diagnose a vehicle or control ECU systems."
)
_ABSTENTION_MAP = {
    AnomalyStatus.INSUFFICIENT_SIGNAL: PredictionStatus.ABSTAINED_INSUFFICIENT_SIGNAL,
    AnomalyStatus.LOW_QUALITY: PredictionStatus.ABSTAINED_LOW_QUALITY,
    AnomalyStatus.INSUFFICIENT_REFERENCE: PredictionStatus.ABSTAINED_INSUFFICIENT_REFERENCE,
    AnomalyStatus.INCOMPATIBLE_CONTEXT: PredictionStatus.ABSTAINED_INCOMPATIBLE_CONTEXT,
    AnomalyStatus.UNSUPPORTED_SOURCE: PredictionStatus.ABSTAINED_UNSUPPORTED_SOURCE,
    AnomalyStatus.NOT_EVALUABLE: PredictionStatus.ABSTAINED_CUTOFF,
}
_Result = TypeVar("_Result")


class BoundedInferenceWorker:
    """Run CPU and artifact work in a bounded pool with a hard per-call wait limit."""

    def __init__(
        self, concurrency: int, timeout_seconds: float, *, constrain_numerical_threads: bool = True
    ) -> None:
        self.executor = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="prediction")
        self.slots = asyncio.Semaphore(concurrency)
        self.timeout_seconds = timeout_seconds
        self.thread_limits = threadpool_limits(limits=1) if constrain_numerical_threads else None

    @staticmethod
    def _invoke(fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        return fn(*args, **kwargs)

    async def __call__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        try:
            async with asyncio.timeout(self.timeout_seconds):
                await self.slots.acquire()
        except TimeoutError as error:
            raise PredictionError(
                503, "PREDICTION_CPU_BUSY", "Prediction capacity is busy"
            ) from error
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(self.executor, self._invoke, fn, args, kwargs)

        def release(_: asyncio.Future[Any]) -> None:
            loop.call_soon_threadsafe(self.slots.release)

        future.add_done_callback(release)
        try:
            async with asyncio.timeout(self.timeout_seconds):
                return await asyncio.shield(future)
        except TimeoutError as error:
            raise PredictionError(
                504, "PREDICTION_COMPUTE_TIMEOUT", "Prediction computation timed out"
            ) from error

    async def shutdown(self) -> None:
        await asyncio.to_thread(self.executor.shutdown, wait=True, cancel_futures=True)
        if self.thread_limits is not None:
            self.thread_limits.restore_original_limits()


class PredictionService:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        *,
        model_artifacts: ModelArtifactStore | None = None,
        anomaly_artifacts: AnomalyArtifactStore | None = None,
        telemetry: Any | None = None,
    ) -> None:
        self.settings = settings
        self.database = database
        self.repository = PredictionRepository(database)
        self.model_artifacts = model_artifacts or ModelArtifactStore()
        self.anomaly_artifacts = anomaly_artifacts or AnomalyArtifactStore()
        self.worker = BoundedInferenceWorker(
            settings.prediction_max_cpu_concurrency,
            max(settings.prediction_request_timeout_seconds, 0.1),
            constrain_numerical_threads=settings.prediction_service_enabled,
        )
        self.telemetry = telemetry
        self.anomaly_service = AnomalyService(
            database,
            artifacts=self.anomaly_artifacts,
            telemetry=telemetry,
            inference_worker=self.worker,
        )

    async def close(self) -> None:
        await self.worker.shutdown()

    async def _traced(self, name: str, operation: Awaitable[_Result]) -> _Result:
        if self.telemetry is None:
            return await operation
        with self.telemetry.tracer.start_as_current_span(name):
            return await operation

    async def versions(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100 or not 0 <= offset <= 10_000:
            raise PredictionError(422, "PREDICTION_INVALID_PAGE", "Invalid page bounds")
        bindings = await self.repository.active_bindings(
            self.settings.environment, limit=limit, offset=offset
        )
        return [self._public_binding(binding) for binding in bindings]

    async def next_pull(
        self,
        payload: NextPullRequest,
        *,
        idempotency_key: str | None,
        operator_id: str = "controlled-api-operator",
    ) -> PredictionResponse:
        subject = payload.task.value
        binding = await self._traced(
            "prediction.binding.resolve",
            self._resolve_binding(
                "next_pull", subject, payload.source_role, payload.model_version_id
            ),
        )
        context = await self._pull(payload.pull_id, payload.vehicle_id)
        cutoff = self._validate_cutoff(payload.observation_cutoff, context.pull_ended_at)
        snapshot = await self._traced(
            "prediction.feature.lookup",
            self.repository.feature_snapshot(payload.pull_id, cutoff),
        )
        self._validate_binding_context(binding, context.source_role, payload.source_role)
        if snapshot is not None:
            reason = self._snapshot_problem(snapshot, context, payload.source_role, cutoff)
            if reason:
                raise PredictionError(409, "PREDICTION_FEATURE_CONTEXT_INVALID", reason)
            self._check_snapshot_binding(binding, snapshot)

        fingerprint = self._fingerprint(
            "next_pull", subject, binding, payload.source_role, cutoff, snapshot, payload.pull_id
        )
        replay = await self._replay(fingerprint, idempotency_key)
        if replay is not None:
            return replay

        if snapshot is None:
            result = self._abstention(
                "next_pull",
                payload,
                binding,
                None,
                PredictionStatus.ABSTAINED_INSUFFICIENT_SIGNAL,
                "FEATURE_SET_UNAVAILABLE",
            )
            return await self._persist(
                fingerprint, idempotency_key, binding, result, payload.pull_id, None, None, None
            )

        artifact = await self._traced("prediction.artifact.verify", self._load_model(binding))
        features, units, missing, qualities = self._model_inputs(artifact, snapshot)
        if (
            payload.task is MLTask.FUEL_DEVIATION
            and "fuel.high_pressure" not in snapshot.available_signals
        ):
            result = self._abstention(
                "next_pull",
                payload,
                binding,
                snapshot,
                PredictionStatus.ABSTAINED_INSUFFICIENT_SIGNAL,
                "FUEL_PRESSURE_SIGNAL_UNAVAILABLE",
            )
        elif self._model_quality_is_low(snapshot):
            result = self._abstention(
                "next_pull",
                payload,
                binding,
                snapshot,
                PredictionStatus.ABSTAINED_LOW_QUALITY,
                "INPUT_QUALITY_BELOW_SERVING_FLOOR",
            )
        else:
            prediction = await self._traced(
                "prediction.model.score",
                self.worker(
                    offline_predict,
                    artifact,
                    feature_set_version=snapshot.feature_set_version,
                    features=features,
                    units=units,
                    missing=missing,
                    feature_quality=qualities,
                ),
            )
            result = PredictionResponse(
                result_type="next_pull",
                task=payload.task,
                horizon="NEXT_PULL",
                status=PredictionStatus.READY_SCORE,
                receipt_id=uuid4(),
                requested_cutoff=payload.observation_cutoff,
                effective_cutoff=snapshot.observation_cutoff,
                source_role=payload.source_role,
                model_version_id=binding.model_version_id,
                feature_set_version=snapshot.feature_set_version,
                decision=bool(prediction["observable_behavior_prediction"]),
                engineering_validation_score=float(prediction["engineering_validation_score"]),
                threshold=float(prediction["decision_threshold"]),
                interpretation=_MODEL_INTERPRETATION,
                limitation=_LIMITATION,
                quality=self._quality(snapshot, features, missing),
                lineage=self._lineage(snapshot),
            )
        return await self._persist(
            fingerprint, idempotency_key, binding, result, payload.pull_id, snapshot, None, None
        )

    async def anomaly(
        self,
        payload: AnomalyRequest,
        *,
        idempotency_key: str | None,
    ) -> PredictionResponse:
        binding = await self._traced(
            "prediction.binding.resolve",
            self._resolve_binding(
                "anomaly", payload.family, payload.source_role, payload.detector_version_id
            ),
        )
        context = await self._pull(payload.pull_id, payload.vehicle_id)
        cutoff = self._validate_cutoff(payload.observation_cutoff, context.pull_ended_at)
        snapshot = await self._traced(
            "prediction.feature.lookup",
            self.repository.feature_snapshot(payload.pull_id, cutoff),
        )
        self._validate_binding_context(binding, context.source_role, payload.source_role)
        if snapshot is not None:
            reason = self._snapshot_problem(snapshot, context, payload.source_role, cutoff)
            if reason:
                raise PredictionError(409, "PREDICTION_FEATURE_CONTEXT_INVALID", reason)
            self._check_snapshot_binding(binding, snapshot)
        fingerprint = self._fingerprint(
            "anomaly",
            payload.family,
            binding,
            payload.source_role,
            cutoff,
            snapshot,
            payload.pull_id,
        )
        replay = await self._replay(fingerprint, idempotency_key)
        if replay is not None:
            return replay
        if snapshot is None:
            result = self._abstention(
                "anomaly",
                payload,
                binding,
                None,
                PredictionStatus.ABSTAINED_INSUFFICIENT_SIGNAL,
                "FEATURE_SET_UNAVAILABLE",
            )
            return await self._persist(
                fingerprint, idempotency_key, binding, result, payload.pull_id, None, None, None
            )
        detector_artifact = await self._traced(
            "prediction.artifact.verify", self._load_detector(binding)
        )
        run = await self._traced(
            "prediction.anomaly.score",
            self.anomaly_service.score_detector_version(
                detector_version_id=cast(UUID, binding.detector_version_id),
                pull_ids=(payload.pull_id,),
                observation_cutoff=cutoff,
                source_role=payload.source_role,
            ),
        )
        if len(run.finding_ids) != 1:
            raise PredictionError(
                503, "PREDICTION_ANOMALY_RESULT_MISSING", "Canonical anomaly result is unavailable"
            )
        if run.artifact_checksum != binding.artifact_checksum:
            raise PredictionError(
                409,
                "PREDICTION_ARTIFACT_CHANGED",
                "Detector artifact differs from the approved checksum",
            )
        finding_id = run.finding_ids[0]
        async with self.database.session() as db:
            finding = (
                (
                    await db.execute(
                        text(
                            "SELECT feature_set_id,source_hash,provenance_hash,"
                            "score,threshold,status,coverage "
                            "FROM anomaly_findings WHERE id=:id AND run_id=:run"
                        ),
                        {"id": finding_id, "run": run.run_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if finding is None:
            raise PredictionError(
                503, "PREDICTION_ANOMALY_RESULT_MISSING", "Canonical anomaly result is unavailable"
            )
        if (
            finding["feature_set_id"] != snapshot.feature_set_id
            or str(finding["source_hash"]) != snapshot.source_hash
            or str(finding["provenance_hash"]) != snapshot.provenance_hash
        ):
            raise PredictionError(
                409,
                "PREDICTION_FEATURE_SELECTION_MISMATCH",
                "Canonical anomaly scoring selected a different FeatureSet",
            )
        finding_status = AnomalyStatus(str(finding["status"]))
        ready = finding_status in {AnomalyStatus.ANOMALOUS, AnomalyStatus.INLIER}
        result = PredictionResponse(
            result_type="anomaly",
            family=payload.family,
            horizon="AFTER_PULL_OFFLINE",
            status=PredictionStatus.READY_SCORE if ready else _ABSTENTION_MAP[finding_status],
            reason_code=None if ready else finding_status.value,
            receipt_id=uuid4(),
            requested_cutoff=payload.observation_cutoff,
            effective_cutoff=snapshot.observation_cutoff,
            source_role=payload.source_role,
            detector_version_id=binding.detector_version_id,
            feature_set_version=snapshot.feature_set_version,
            decision=cast(AnomalyDecision, finding_status.value) if ready else None,
            anomaly_score=float(finding["score"])
            if ready and finding["score"] is not None
            else None,
            threshold=float(finding["threshold"]) if finding["threshold"] is not None else None,
            interpretation=_ANOMALY_INTERPRETATION,
            limitation=_LIMITATION,
            quality=self._quality(snapshot, {}, {}),
            lineage=self._lineage(snapshot, run.run_id, finding_id),
        )
        del detector_artifact  # The canonical 9C scorer performs its own trusted artifact load.
        return await self._persist(
            fingerprint,
            idempotency_key,
            binding,
            result,
            payload.pull_id,
            snapshot,
            run.run_id,
            finding_id,
        )

    async def receipt(self, receipt_id: UUID) -> PredictionResponse:
        result = await self.repository.receipt(receipt_id)
        if result is None:
            raise PredictionError(
                404, "PREDICTION_RECEIPT_NOT_FOUND", "Prediction receipt not found"
            )
        return result

    async def inspect_candidate(self, result_kind: str, version_id: UUID) -> ServingCandidate:
        expected_checksum = default_feature_version().checksum
        if result_kind == "next_pull":
            row = await self.repository.model_candidate(version_id)
            if row is None:
                raise PredictionError(
                    404, "PREDICTION_VERSION_NOT_FOUND", "Model version not found"
                )
            metrics = json_object(row.get("metrics"))
            acceptance = json_object(metrics.get("acceptance"))
            manifest = json_object(row.get("dataset_manifest"))
            role = manifest.get("source_role")
            try:
                task = MLTask(str(row["task"]))
                source_role = SourceRole(str(role))
            except ValueError as error:
                raise PredictionError(
                    409, "PREDICTION_CANDIDATE_INVALID", "Model source role is invalid"
                ) from error
            if (
                str(row["state"]) != "CANDIDATE"
                or not acceptance.get("all_criteria_pass")
                or source_role is SourceRole.MIXED
                or str(row["feature_version"]) != FEATURE_SET_VERSION
                or str(row["feature_version_checksum"]) != expected_checksum
            ):
                raise PredictionError(
                    409,
                    "PREDICTION_CANDIDATE_INVALID",
                    "Model is not an accepted compatible candidate",
                )
            try:
                model_artifact = await self.model_artifacts.load_registered(
                    self.database, str(version_id), worker=self.worker
                )
            except (ArtifactValidationError, ValueError, OSError) as error:
                raise PredictionError(
                    409,
                    "PREDICTION_ARTIFACT_INVALID",
                    "Registered model artifact failed verification",
                ) from error
            if model_artifact.model_version.task is not task:
                raise PredictionError(
                    409,
                    "PREDICTION_CANDIDATE_INVALID",
                    "Model task does not match its registration",
                )
            return ServingCandidate(
                "next_pull",
                task.value,
                version_id,
                source_role,
                str(row["state"]),
                model_artifact.model_version.artifact_checksum,
                FEATURE_SET_VERSION,
                str(row["feature_version_checksum"]),
                stable_hash(model_artifact.input_schema),
                str(acceptance.get("evaluation_class", "accepted")),
                "PASS",
                _MODEL_INTERPRETATION,
            )
        if result_kind == "anomaly":
            row = await self.repository.detector_candidate(version_id)
            if row is None:
                raise PredictionError(
                    404, "PREDICTION_VERSION_NOT_FOUND", "Detector version not found"
                )
            metrics = json_object(row.get("training_metrics"))
            manifest = json_object(row.get("reference_manifest"))
            cohort = json_object(manifest.get("cohort"))
            try:
                source_role = SourceRole(str(cohort.get("source_role") or row.get("source_role")))
            except ValueError as error:
                raise PredictionError(
                    409, "PREDICTION_CANDIDATE_INVALID", "Detector source role is invalid"
                ) from error
            if (
                str(row["state"]) != "ACCEPTED"
                or metrics.get("selection_state") != "ACCEPTED"
                or source_role is SourceRole.MIXED
                or str(row["feature_set_version"]) != FEATURE_SET_VERSION
                or str(row["feature_set_version_checksum"]) != expected_checksum
                or str(row["source_role"]) != source_role.value
                or str(row["family"]) not in {"thermal", "boost_air", "performance", "fuel"}
            ):
                raise PredictionError(
                    409,
                    "PREDICTION_CANDIDATE_INVALID",
                    "Detector is not an accepted compatible candidate",
                )
            try:
                detector_artifact = await self.anomaly_artifacts.load_registered(
                    self.database, str(version_id), worker=self.worker
                )
            except (AnomalyArtifactError, ValueError, OSError) as error:
                raise PredictionError(
                    409,
                    "PREDICTION_ARTIFACT_INVALID",
                    "Registered detector artifact failed verification",
                ) from error
            if source_role not in detector_artifact.definition.supported_source_roles:
                raise PredictionError(
                    409,
                    "PREDICTION_CANDIDATE_INVALID",
                    "Detector does not support this source role",
                )
            return ServingCandidate(
                "anomaly",
                detector_artifact.definition.family.value,
                version_id,
                source_role,
                str(row["state"]),
                detector_artifact.artifact_checksum,
                FEATURE_SET_VERSION,
                str(row["feature_set_version_checksum"]),
                detector_artifact.definition.checksum,
                "accepted",
                str(metrics.get("selection_state", "unknown")),
                _ANOMALY_INTERPRETATION,
            )
        raise PredictionError(422, "PREDICTION_INVALID_KIND", "Unsupported prediction kind")

    async def approve_candidate(
        self,
        result_kind: str,
        version_id: UUID,
        *,
        source_role: SourceRole,
        reason: str,
        operator_id: str,
        review_reference: str,
        environment_confirmation: str,
    ) -> tuple[UUID, UUID]:
        self._confirm_controlled_environment(environment_confirmation)
        candidate = await self.inspect_candidate(result_kind, version_id)
        if candidate.source_role is not source_role:
            raise PredictionError(
                409,
                "PREDICTION_SOURCE_ROLE_MISMATCH",
                "Approval source role differs from candidate provenance",
            )
        if not (
            20 <= len(reason.strip()) <= 500
            and 2 <= len(operator_id.strip()) <= 120
            and 5 <= len(review_reference.strip()) <= 240
        ):
            raise PredictionError(
                422,
                "PREDICTION_APPROVAL_EVIDENCE_REQUIRED",
                "Reason, operator identity and review reference are required",
            )
        if (
            source_role is SourceRole.SYNTHETIC
            and "synthetic" not in reason.lower()
            and "synthetic" not in review_reference.lower()
        ):
            raise PredictionError(
                422,
                "PREDICTION_SYNTHETIC_SCOPE_REQUIRED",
                "Synthetic approval must explicitly identify its scope",
            )
        binding_id, event_id = await self.repository.create_approval(
            candidate,
            environment=self.settings.environment,
            reason=reason.strip(),
            operator_id=operator_id.strip(),
            review_reference=review_reference.strip(),
        )
        if self.telemetry is not None:
            self.telemetry.prediction_approval_changes.add(
                1, {"kind": candidate.result_kind, "event": "approved"}
            )
        return binding_id, event_id

    async def transition(
        self,
        binding_id: UUID,
        action: str,
        *,
        reason: str,
        operator_id: str,
        environment_confirmation: str,
    ) -> tuple[ServingBinding, UUID]:
        self._confirm_controlled_environment(environment_confirmation)
        if len(reason.strip()) < 8 or len(operator_id.strip()) < 2:
            raise PredictionError(
                422,
                "PREDICTION_TRANSITION_EVIDENCE_REQUIRED",
                "Reason and operator identity are required",
            )
        binding = await self.repository.binding(binding_id)
        if binding is None:
            raise PredictionError(404, "PREDICTION_BINDING_NOT_FOUND", "Serving approval not found")
        if binding.environment != self.settings.environment or binding.scope != CONTROLLED_SCOPE:
            raise PredictionError(
                403,
                "PREDICTION_BINDING_ENVIRONMENT_MISMATCH",
                "Serving approval is outside the configured controlled environment",
            )
        if action in {"activate", "rollback"}:
            candidate = await self.inspect_candidate(
                binding.result_kind,
                binding.model_version_id or binding.detector_version_id or UUID(int=0),
            )
            if (
                candidate.source_role is not binding.source_role
                or candidate.artifact_checksum != binding.artifact_checksum
                or candidate.feature_set_version != binding.feature_set_version
                or candidate.feature_set_checksum != binding.feature_set_checksum
                or candidate.schema_checksum != binding.schema_checksum
            ):
                raise PredictionError(
                    409,
                    "PREDICTION_BINDING_STALE",
                    "Serving approval no longer matches its registered version",
                )
        updated, event_id = await self.repository.transition_binding(
            binding_id, action, reason=reason.strip(), operator_id=operator_id.strip()
        )
        if self.telemetry is not None and event_id != binding.latest_event_id:
            self.telemetry.prediction_approval_changes.add(
                1, {"kind": binding.result_kind, "event": updated.latest_event_type.value.lower()}
            )
        return updated, event_id

    async def _resolve_binding(
        self, kind: str, subject: str, source_role: SourceRole, version_id: UUID | None
    ) -> ServingBinding:
        if source_role is SourceRole.MIXED:
            raise PredictionError(
                409, "PREDICTION_SOURCE_UNSUPPORTED", "Mixed source roles cannot be served"
            )
        bindings = await self.repository.bindings_for_slot(
            cast(Any, kind), subject, source_role, self.settings.environment
        )
        active = [item for item in bindings if item.is_active]
        if version_id is not None:
            active = [
                item
                for item in active
                if item.model_version_id == version_id or item.detector_version_id == version_id
            ]
        if len(active) != 1:
            raise PredictionError(
                409,
                "PREDICTION_NO_UNIQUE_ACTIVE_VERSION",
                "No unique approved active version is available",
            )
        binding = active[0]
        candidate = await self.inspect_candidate(
            kind, binding.model_version_id or binding.detector_version_id or UUID(int=0)
        )
        if (
            candidate.artifact_checksum != binding.artifact_checksum
            or candidate.feature_set_version != binding.feature_set_version
            or candidate.feature_set_checksum != binding.feature_set_checksum
            or candidate.schema_checksum != binding.schema_checksum
            or candidate.source_role is not binding.source_role
        ):
            raise PredictionError(
                409,
                "PREDICTION_BINDING_STALE",
                "Approved model binding no longer matches its registered artifact",
            )
        return binding

    async def _load_model(self, binding: ServingBinding) -> TrustedModelArtifact:
        started = perf_counter()
        try:
            artifact = await self.model_artifacts.load_registered(
                self.database, str(binding.model_version_id), worker=self.worker
            )
            if not hmac.compare_digest(
                artifact.model_version.artifact_checksum, binding.artifact_checksum
            ):
                raise PredictionError(
                    409,
                    "PREDICTION_ARTIFACT_CHANGED",
                    "Model artifact differs from the approved checksum",
                )
            return artifact
        except (ArtifactValidationError, ValueError, OSError) as error:
            raise PredictionError(
                409,
                "PREDICTION_ARTIFACT_INVALID",
                "Registered model artifact failed verification",
            ) from error
        finally:
            if self.telemetry is not None:
                self.telemetry.prediction_artifact_load_duration.record(
                    perf_counter() - started, {"kind": "model"}
                )

    async def _load_detector(self, binding: ServingBinding) -> Any:
        started = perf_counter()
        try:
            artifact = await self.anomaly_artifacts.load_registered(
                self.database, str(binding.detector_version_id), worker=self.worker
            )
            if not hmac.compare_digest(artifact.artifact_checksum, binding.artifact_checksum):
                raise PredictionError(
                    409,
                    "PREDICTION_ARTIFACT_CHANGED",
                    "Detector artifact differs from the approved checksum",
                )
            return artifact
        except (AnomalyArtifactError, ValueError, OSError) as error:
            raise PredictionError(
                409,
                "PREDICTION_ARTIFACT_INVALID",
                "Registered detector artifact failed verification",
            ) from error
        finally:
            if self.telemetry is not None:
                self.telemetry.prediction_artifact_load_duration.record(
                    perf_counter() - started, {"kind": "detector"}
                )

    async def _pull(self, pull_id: UUID, vehicle_id: UUID | None) -> Any:
        context = await self.repository.pull_context(pull_id)
        if context is None:
            raise PredictionError(404, "PREDICTION_PULL_NOT_FOUND", "Pull not found")
        if vehicle_id is not None and vehicle_id != context.vehicle_id:
            raise PredictionError(404, "PREDICTION_PULL_NOT_FOUND", "Pull not found")
        if context.pull_ended_at is None or context.session_status not in {
            "complete",
            "completed",
            "finalized",
        }:
            raise PredictionError(
                409, "PREDICTION_PULL_NOT_FINALIZED", "Prediction requires a finalized pull"
            )
        if context.pull_ended_at > datetime.now(UTC):
            raise PredictionError(
                409, "PREDICTION_PULL_NOT_FINALIZED", "Prediction requires a finalized pull"
            )
        return context

    def _validate_cutoff(self, requested: datetime, pull_end: datetime) -> datetime:
        now = datetime.now(UTC)
        if requested < pull_end:
            raise PredictionError(
                422,
                "PREDICTION_CUTOFF_BEFORE_PULL",
                "Observation cutoff must include the completed pull",
            )
        if requested > now + timedelta(seconds=self.settings.prediction_max_future_cutoff_seconds):
            raise PredictionError(
                422, "PREDICTION_CUTOFF_IN_FUTURE", "Observation cutoff is too far in the future"
            )
        return requested.astimezone(UTC)

    def _validate_binding_context(
        self, binding: ServingBinding, actual: SourceRole, requested: SourceRole
    ) -> None:
        if (
            actual is SourceRole.MIXED
            or actual is not requested
            or actual is not binding.source_role
        ):
            raise PredictionError(
                409,
                "PREDICTION_SOURCE_ROLE_MISMATCH",
                "Request source role does not match pull provenance and approval",
            )

    def _snapshot_problem(
        self, snapshot: FeatureSnapshot, context: Any, role: SourceRole, cutoff: datetime
    ) -> str | None:
        if (
            snapshot.source_role is not role
            or snapshot.pull_id != context.pull_id
            or snapshot.vehicle_id != context.vehicle_id
        ):
            return "FeatureSet identity or source provenance differs from the request."
        if (
            snapshot.feature_set_version != FEATURE_SET_VERSION
            or snapshot.feature_set_version_checksum != default_feature_version().checksum
        ):
            return "FeatureSet version is not the canonical Phase 9A serving version."
        if snapshot.observation_cutoff > cutoff:
            return "FeatureSet observation cutoff exceeds the requested window."
        if snapshot.pull_created_at > snapshot.observation_cutoff:
            return "Pull context was created after the FeatureSet observation cutoff."
        if snapshot.observation_cutoff < snapshot.pull_ended_at:
            return "FeatureSet cutoff does not include the completed pull."
        if snapshot.source_window_end > snapshot.observation_cutoff:
            return "FeatureSet source window extends beyond its observation cutoff."
        if (
            snapshot.session_created_at > snapshot.observation_cutoff
            or snapshot.vehicle_created_at > snapshot.observation_cutoff
        ):
            return "FeatureSet context was created after its observation cutoff."
        if snapshot.configuration_id != snapshot.resolved_configuration_id:
            return "FeatureSet configuration no longer matches its as-of context."
        if (
            snapshot.configuration_created_at
            and snapshot.configuration_created_at > snapshot.observation_cutoff
        ):
            return "Configuration was created after the observation cutoff."
        expected_provenance = stable_hash(
            {
                "vehicle_id": str(snapshot.vehicle_id),
                "configuration_id": str(snapshot.resolved_configuration_id)
                if snapshot.resolved_configuration_id
                else None,
                "session_id": str(snapshot.session_id),
                "pull_id": str(snapshot.pull_id),
                "source_hash": snapshot.source_hash,
                "feature_set_version": FEATURE_SET_VERSION,
                "generator_version": "phase9a-feature-generator-v2",
            }
        )
        if not hmac.compare_digest(expected_provenance, snapshot.provenance_hash):
            return "FeatureSet provenance checksum is invalid."
        provenance = snapshot.provenance
        checks = {
            "source_hash": snapshot.source_hash,
            "feature_set_version": FEATURE_SET_VERSION,
            "configuration_id": str(snapshot.resolved_configuration_id)
            if snapshot.resolved_configuration_id
            else None,
        }
        for key, expected in checks.items():
            if provenance.get(key) != expected:
                return "FeatureSet provenance contents do not match their recorded identity."
        context_data = json_object(provenance.get("source_context"))
        modification_ids = context_data.get("active_modification_ids")
        if (
            not isinstance(modification_ids, list)
            or tuple(sorted(str(item) for item in modification_ids))
            != snapshot.current_modification_ids
        ):
            return "FeatureSet modification context is incompatible with current as-of history."
        for item in snapshot.values.values():
            available = self._parse_datetime(item.get("available_at"))
            window_end = self._parse_datetime(item.get("source_window_end"))
            if available is not None and available > snapshot.observation_cutoff:
                return "A selected feature became available after its FeatureSet cutoff."
            if window_end is not None and window_end > snapshot.observation_cutoff:
                return "A selected feature uses telemetry after its FeatureSet cutoff."
        return None

    def _check_snapshot_binding(self, binding: ServingBinding, snapshot: FeatureSnapshot) -> None:
        if (
            snapshot.feature_set_version != binding.feature_set_version
            or snapshot.feature_set_version_checksum != binding.feature_set_checksum
        ):
            raise PredictionError(
                409,
                "PREDICTION_FEATURE_VERSION_MISMATCH",
                "FeatureSet version differs from approved model binding",
            )

    def _model_inputs(
        self, artifact: TrustedModelArtifact, snapshot: FeatureSnapshot
    ) -> tuple[dict[str, Any], dict[str, str | None], dict[str, str], dict[str, str]]:
        order = tuple(str(item) for item in artifact.input_schema["raw_feature_order"])
        definitions = {item.key: item for item in DEFAULT_REGISTRY.list()}
        if set(snapshot.values) != set(definitions) or not set(order).issubset(snapshot.values):
            raise PredictionError(
                409,
                "PREDICTION_FEATURE_SCHEMA_MISMATCH",
                "FeatureSet schema is incomplete or unexpected",
            )
        features: dict[str, Any] = {}
        units: dict[str, str | None] = {}
        missing: dict[str, str] = {}
        qualities: dict[str, str] = {}
        for key in order:
            raw = snapshot.values[key]
            definition = definitions.get(key)
            if definition is None or raw.get("unit") != definition.unit:
                raise PredictionError(
                    409,
                    "PREDICTION_FEATURE_UNIT_MISMATCH",
                    "Feature unit differs from canonical schema",
                )
            value = raw.get("value")
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise PredictionError(
                    409,
                    "PREDICTION_FEATURE_VALUE_INVALID",
                    "Feature value is not a finite numeric value",
                )
            quality = str(raw.get("quality", ""))
            if quality not in {"valid", "limited", "unavailable", "invalid"}:
                raise PredictionError(
                    409, "PREDICTION_FEATURE_QUALITY_INVALID", "Feature quality is invalid"
                )
            reason = raw.get("missing_reason")
            if value is None:
                if not isinstance(reason, str):
                    raise PredictionError(
                        409, "PREDICTION_FEATURE_QUALITY_INVALID", "Missing feature has no reason"
                    )
                missing[key] = reason
            elif reason is not None or quality not in {"valid", "limited"}:
                raise PredictionError(
                    409,
                    "PREDICTION_FEATURE_QUALITY_INVALID",
                    "Available feature quality is inconsistent",
                )
            features[key] = value
            units[key] = definition.unit
            qualities[key] = quality
        return features, units, missing, qualities

    def _quality(
        self, snapshot: FeatureSnapshot, features: dict[str, Any], missing: dict[str, str]
    ) -> PredictionQuality:
        expected = len(features) if features else len(snapshot.values)
        observed = (
            expected - len(missing)
            if features
            else sum(item.get("value") is not None for item in snapshot.values.values())
        )
        coverage = observed / expected if expected else 0.0
        declared = snapshot.quality_metadata.get("expected_coverage_ratio")
        if isinstance(declared, (int, float)) and not isinstance(declared, bool):
            coverage = min(coverage, max(0.0, float(declared)))
        quality_class = (
            "high" if coverage >= 0.9 else "degraded" if coverage >= 0.5 else "insufficient"
        )
        counts: dict[str, int] = {}
        source = (
            missing.values()
            if missing
            else (
                str(item.get("missing_reason"))
                for item in snapshot.values.values()
                if item.get("missing_reason")
            )
        )
        for reason in source:
            allowed = {
                "unavailable_signal",
                "insufficient_coverage",
                "invalid_quality",
                "not_applicable",
                "not_observed_yet",
                "computation_error",
            }
            bounded_reason = reason if reason in allowed else "invalid_quality"
            counts[bounded_reason] = counts.get(bounded_reason, 0) + 1
        return PredictionQuality(
            quality_class=cast(Any, quality_class),
            observed_feature_count=observed,
            expected_feature_count=expected,
            coverage=coverage,
            missing_reason_counts=dict(sorted(counts.items())[:16]),
        )

    @staticmethod
    def _model_quality_is_low(snapshot: FeatureSnapshot) -> bool:
        completeness = snapshot.quality_metadata.get("pull_completeness")
        if (
            isinstance(completeness, bool)
            or not isinstance(completeness, (int, float))
            or not math.isfinite(float(completeness))
            or float(completeness) < 0.75
        ):
            return True
        for key in ("invalid_observation_count", "duplicate_timestamp_count"):
            count = snapshot.quality_metadata.get(key, 0)
            if isinstance(count, bool) or not isinstance(count, int) or count > 0:
                return True
        return False

    @staticmethod
    def _lineage(
        snapshot: FeatureSnapshot | None,
        run_id: UUID | None = None,
        finding_id: UUID | None = None,
    ) -> PredictionLineage:
        return PredictionLineage(
            feature_set_id=snapshot.feature_set_id if snapshot else None,
            anomaly_run_id=run_id,
            anomaly_finding_id=finding_id,
        )

    def _abstention(
        self,
        kind: str,
        payload: NextPullRequest | AnomalyRequest,
        binding: ServingBinding,
        snapshot: FeatureSnapshot | None,
        status: PredictionStatus,
        reason: str,
    ) -> PredictionResponse:
        return PredictionResponse(
            result_type=cast(PredictionKind, kind),
            task=payload.task if isinstance(payload, NextPullRequest) else None,
            family=payload.family if isinstance(payload, AnomalyRequest) else None,
            horizon="NEXT_PULL" if kind == "next_pull" else "AFTER_PULL_OFFLINE",
            status=status,
            reason_code=reason,
            receipt_id=uuid4(),
            requested_cutoff=payload.observation_cutoff,
            effective_cutoff=snapshot.observation_cutoff if snapshot else None,
            source_role=payload.source_role,
            model_version_id=binding.model_version_id,
            detector_version_id=binding.detector_version_id,
            feature_set_version=snapshot.feature_set_version if snapshot else None,
            interpretation="No score was produced because the required evidence was unavailable.",
            limitation=_LIMITATION,
            quality=self._quality(snapshot, {}, {})
            if snapshot
            else PredictionQuality(
                quality_class="unavailable",
                observed_feature_count=0,
                expected_feature_count=0,
                coverage=0,
            ),
            lineage=self._lineage(snapshot),
        )

    def _fingerprint(
        self,
        kind: str,
        subject: str,
        binding: ServingBinding,
        role: SourceRole,
        cutoff: datetime,
        snapshot: FeatureSnapshot | None,
        pull_id: UUID,
    ) -> str:
        return stable_hash(
            {
                "contract": "phase9d-prediction-request-v1",
                "kind": kind,
                "subject": subject,
                "binding_id": str(binding.id),
                "binding_event_id": str(binding.latest_event_id),
                "version_id": str(binding.model_version_id or binding.detector_version_id),
                "pull_id": str(pull_id),
                "artifact_checksum": binding.artifact_checksum,
                "source_role": role.value,
                "cutoff": cutoff.isoformat(),
                "feature_set_id": str(snapshot.feature_set_id) if snapshot else None,
                "feature_set_source_hash": snapshot.source_hash if snapshot else None,
                "feature_set_provenance_hash": snapshot.provenance_hash if snapshot else None,
            }
        )

    async def _replay(
        self, fingerprint: str, idempotency_key: str | None
    ) -> PredictionResponse | None:
        key_hash = (
            hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest() if idempotency_key else None
        )
        replay = await self.repository.find_replay(fingerprint, key_hash)
        if replay is None:
            return None
        old_fingerprint, body = replay
        if old_fingerprint != fingerprint:
            raise PredictionError(
                409,
                "PREDICTION_IDEMPOTENCY_CONFLICT",
                "Idempotency key is already bound to a different request",
            )
        return PredictionResponse.model_validate(body)

    async def _persist(
        self,
        fingerprint: str,
        idempotency_key: str | None,
        binding: ServingBinding,
        response: PredictionResponse,
        pull_id: UUID,
        snapshot: FeatureSnapshot | None,
        run_id: UUID | None,
        finding_id: UUID | None,
    ) -> PredictionResponse:
        key_hash = (
            hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest() if idempotency_key else None
        )
        saved, created = await self._traced(
            "prediction.receipt.persist",
            self.repository.persist_receipt(
                fingerprint=fingerprint,
                client_key_hash=key_hash,
                binding=binding,
                response=response,
                pull_id=pull_id,
                feature_snapshot=snapshot,
                anomaly_run_id=run_id,
                anomaly_finding_id=finding_id,
            ),
        )
        if self.telemetry is not None:
            self.telemetry.prediction_requests.add(
                1, {"kind": response.result_type, "status": response.status.value}
            )
            self.telemetry.prediction_receipts.add(
                1, {"kind": response.result_type, "created": str(created).lower()}
            )
            self.telemetry.log(
                "prediction.receipt.persisted",
                "prediction-service",
                prediction_endpoint=response.result_type,
                prediction_status=response.status.value,
                prediction_reason=response.reason_code or "none",
            )
        return saved

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed.astimezone(UTC) if parsed.tzinfo else None

    def _confirm_controlled_environment(self, confirmation: str) -> None:
        if (
            self.settings.environment not in {"development", "test"}
            or confirmation != self.settings.environment
        ):
            raise PredictionError(
                403,
                "PREDICTION_ENVIRONMENT_CONFIRMATION_REQUIRED",
                "Serving control is restricted to the confirmed development or test environment",
            )

    @staticmethod
    def _public_binding(binding: ServingBinding) -> dict[str, Any]:
        return {
            "binding_id": binding.id,
            "result_kind": binding.result_kind,
            "subject_key": binding.subject_key,
            "source_role": binding.source_role,
            "environment": binding.environment,
            "scope": CONTROLLED_SCOPE,
            "model_version_id": binding.model_version_id,
            "detector_version_id": binding.detector_version_id,
            "artifact_checksum": binding.artifact_checksum,
            "feature_set_version": binding.feature_set_version,
            "feature_set_checksum": binding.feature_set_checksum,
            "schema_checksum": binding.schema_checksum,
            "activation_event_id": binding.latest_event_id,
        }
