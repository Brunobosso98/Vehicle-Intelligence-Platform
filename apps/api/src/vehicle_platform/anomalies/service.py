from __future__ import annotations

import math
import time
from contextlib import nullcontext
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import text

from vehicle_platform.anomalies.artifacts import (
    AnomalyArtifactError,
    ArtifactStore,
    TrustedAnomalyArtifact,
    fit_checksum_for,
)
from vehicle_platform.anomalies.definitions import detector_definition
from vehicle_platform.anomalies.detectors import (
    DetectorFitError,
    FittedDetector,
    fit_detector,
    score_observation,
)
from vehicle_platform.anomalies.domain import (
    MAX_SCORE_ROWS,
    AnomalyDetectorDefinition,
    AnomalyFindingResult,
    AnomalyReason,
    AnomalyReferenceDataset,
    AnomalyStatus,
    DetectorLifecycle,
    ReferenceRow,
    SourceRole,
    finding_idempotency_key,
)
from vehicle_platform.anomalies.registry import AnomalyRegistry, repository_sha
from vehicle_platform.anomalies.repository import (
    AnomalyDataRepository,
    AnomalyRepositoryError,
    _feature_exclusion,
    _quality_exclusion,
)
from vehicle_platform.features.domain import canonical_json, stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import library_versions


@dataclass(frozen=True)
class DetectorVersionResult:
    detector_version_id: UUID
    version: str
    state: DetectorLifecycle
    reference_dataset_id: UUID
    reference_checksum: str
    fit_checksum: str
    threshold: float | None
    artifact_checksum: str | None
    rejection_reason: str | None
    training_metrics: dict[str, Any]
    created: bool


@dataclass(frozen=True)
class DetectionRunResult:
    run_id: UUID
    run_identity: str
    detector_version_id: UUID
    reference_dataset_id: UUID
    observation_cutoff: datetime
    source_role: SourceRole
    requested_count: int
    scored_count: int
    missing_feature_set_count: int
    finding_ids: tuple[UUID, ...]
    status_counts: dict[str, int]
    input_checksum: str
    artifact_checksum: str | None
    duration_seconds: float
    target_read_seconds: float
    finding_persistence_seconds: float
    summary: dict[str, Any]
    idempotent_replay: bool


class AnomalyService:
    """Offline detector fitting and retrospective scoring over canonical Phase 9A data."""

    def __init__(
        self,
        database: Database,
        *,
        repository: AnomalyDataRepository | None = None,
        registry: AnomalyRegistry | None = None,
        artifacts: ArtifactStore | None = None,
        telemetry: Any | None = None,
    ) -> None:
        self.database = database
        self.repository = repository or AnomalyDataRepository(database)
        self.registry = registry or AnomalyRegistry(database)
        self.artifacts = artifacts or ArtifactStore()
        self.telemetry = telemetry

    async def fit_detector_version(
        self,
        *,
        anchor_pull_id: UUID,
        observation_cutoff: datetime,
        source_role: SourceRole,
        family: str,
        method: str,
        git_sha: str | None = None,
    ) -> DetectorVersionResult:
        started = time.perf_counter()
        definition = detector_definition(family, method)
        if source_role not in definition.supported_source_roles:
            raise AnomalyRepositoryError(
                AnomalyReason.SOURCE_NOT_ALLOWLISTED,
                "requested source role is outside this detector's allowlist",
            )
        anchor, feature_version_id, feature_version_checksum = await self.repository.load_anchor(
            anchor_pull_id, observation_cutoff, source_role, definition
        )
        if observation_cutoff < anchor.pull_ended_at:
            raise AnomalyRepositoryError(
                AnomalyReason.CUTOFF_BEFORE_PULL_END,
                "fitting cutoff must include the completed anchor pull",
            )
        if anchor.cohort.source_role is not source_role:
            raise AnomalyRepositoryError(
                AnomalyReason.SOURCE_ROLE_MISMATCH,
                "anchor source role differs from the requested source role",
            )
        with self._span("anomaly.reference.materialization", definition):
            with self._span("anomaly.reference.eligibility", definition):
                dataset = await self.repository.materialize_reference(
                    anchor,
                    feature_version_id,
                    feature_version_checksum,
                    definition,
                    source_role,
                )
        if self.telemetry is not None:
            exclusion_counts: dict[str, int] = {}
            for item in dataset.exclusions:
                reason = str(item.get("reason", "unknown"))
                exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
            for reason, count in exclusion_counts.items():
                self.telemetry.anomaly_reference_exclusions.add(
                    count,
                    {
                        "family": definition.family.value,
                        "method": definition.method.value,
                        "reason": reason,
                    },
                )
        reference_id = await self.registry.persist_reference(
            definition, dataset, feature_set_version_id=feature_version_id
        )
        fit_checksum = fit_checksum_for(definition, dataset.checksum(definition))
        version = await self.registry.reserve_version()
        commit = git_sha or repository_sha()

        fitted: FittedDetector | None = None
        rejection_reason: str | None = None
        try:
            with self._span("anomaly.detector.fit", definition) as span:
                fitted = fit_detector(definition, dataset)
                if span is not None:
                    span.set_attribute("reference.rows", len(dataset.rows))
                    span.set_attribute(
                        "reference.sessions", len({row.session_id for row in dataset.rows})
                    )
        except DetectorFitError as error:
            rejection_reason = error.reason.value

        if fitted is None:
            metrics = _rejected_training_metrics(dataset, definition, rejection_reason)
            version_id, registered_version, created = await self.registry.persist_detector_version(
                definition,
                reference_dataset_id=reference_id,
                fit_checksum=fit_checksum,
                state=DetectorLifecycle.REJECTED,
                threshold=None,
                artifact=None,
                rejection_reason=rejection_reason,
                training_metrics=metrics,
                input_schema=_input_schema(definition),
                version=version,
                repository_sha=commit,
            )
            self._record_fit_metrics(
                definition, DetectorLifecycle.REJECTED, started, len(dataset.rows)
            )
            return DetectorVersionResult(
                detector_version_id=version_id,
                version=registered_version,
                state=DetectorLifecycle.REJECTED,
                reference_dataset_id=reference_id,
                reference_checksum=dataset.checksum(definition),
                fit_checksum=fit_checksum,
                threshold=None,
                artifact_checksum=None,
                rejection_reason=rejection_reason,
                training_metrics=metrics,
                created=created,
            )

        with self._span("anomaly.artifact.stage", definition):
            receipt = self.artifacts.write(
                definition,
                fitted,
                version=version,
                fit_checksum=fit_checksum,
            )
        if self.telemetry is not None:
            self.telemetry.anomaly_artifact_size.record(
                receipt.size_bytes,
                {"family": definition.family.value, "method": definition.method.value},
            )
        try:
            self.artifacts.verify_staged(
                receipt,
                definition=definition,
                fitted=fitted,
                version=version,
                fit_checksum=fit_checksum,
            )
            metrics = _candidate_training_metrics(dataset, definition, fitted)
            version_id, registered_version, created = await self.registry.persist_detector_version(
                definition,
                reference_dataset_id=reference_id,
                fit_checksum=fit_checksum,
                state=DetectorLifecycle.CANDIDATE,
                threshold=fitted.threshold,
                artifact=receipt,
                rejection_reason=None,
                training_metrics=metrics,
                input_schema=_input_schema(definition),
                version=version,
                repository_sha=commit,
            )
        except Exception:
            self.artifacts.delete_staged(receipt)
            raise
        if not created:
            self.artifacts.delete_staged(receipt)
            artifact_checksum = await self._registered_artifact_checksum(version_id)
        else:
            artifact_checksum = receipt.checksum
        self._record_fit_metrics(
            definition, DetectorLifecycle.CANDIDATE, started, len(dataset.rows)
        )
        return DetectorVersionResult(
            detector_version_id=version_id,
            version=registered_version,
            state=DetectorLifecycle.CANDIDATE,
            reference_dataset_id=reference_id,
            reference_checksum=dataset.checksum(definition),
            fit_checksum=fit_checksum,
            threshold=fitted.threshold,
            artifact_checksum=artifact_checksum,
            rejection_reason=None,
            training_metrics=metrics,
            created=created,
        )

    async def score_detector_version(
        self,
        *,
        detector_version_id: UUID,
        pull_ids: tuple[UUID, ...],
        observation_cutoff: datetime,
        source_role: SourceRole,
        trace_id: str | None = None,
    ) -> DetectionRunResult:
        started = time.perf_counter()
        if not 1 <= len(pull_ids) <= MAX_SCORE_ROWS or len(set(pull_ids)) != len(pull_ids):
            raise AnomalyRepositoryError(
                AnomalyReason.RESOURCE_LIMIT,
                "score requests require 1 to 1000 unique pull IDs",
            )
        if observation_cutoff.tzinfo is None or observation_cutoff.utcoffset() is None:
            raise AnomalyRepositoryError(
                AnomalyReason.INVALID_CUTOFF, "score cutoff must include a timezone offset"
            )
        if source_role is SourceRole.MIXED:
            raise AnomalyRepositoryError(
                AnomalyReason.SOURCE_NOT_ALLOWLISTED, "mixed source role cannot be scored"
            )
        metadata = await self._load_version_metadata(detector_version_id)
        definition = detector_definition(str(metadata["family"]), str(metadata["method"]))
        registered_artifact: TrustedAnomalyArtifact | None = None
        if metadata["state"] in {
            DetectorLifecycle.CANDIDATE.value,
            DetectorLifecycle.ACCEPTED.value,
        }:
            with self._span("anomaly.artifact.validation", definition):
                registered_artifact = await self.artifacts.load_registered(
                    self.database, str(detector_version_id)
                )
            definition = registered_artifact.definition
        elif metadata["state"] != DetectorLifecycle.REJECTED.value:
            raise AnomalyArtifactError(
                "detector lifecycle state cannot be used for offline scoring"
            )

        target_read_started = time.perf_counter()
        with self._span("anomaly.target.materialization", definition) as span:
            rows = await self.repository.load_targets(pull_ids, observation_cutoff, definition)
            target_read_seconds = time.perf_counter() - target_read_started
            if span is not None:
                span.set_attribute("target.requested_count", len(pull_ids))
                span.set_attribute("target.feature_set_count", len(rows))
                span.set_attribute("target.read_seconds", target_read_seconds)
        if source_role not in definition.supported_source_roles:
            raise AnomalyRepositoryError(
                AnomalyReason.SOURCE_NOT_ALLOWLISTED,
                "requested source role is outside this detector's allowlist",
            )
        rows_by_pull = {UUID(row.pull_id): row for row in rows}
        absent_pulls = tuple(sorted(str(item) for item in set(pull_ids) - set(rows_by_pull)))
        findings: list[tuple[ReferenceRow, AnomalyFindingResult, str]] = []
        status_counts: dict[str, int] = {}
        rejected_reason = _reason_or_default(metadata.get("rejection_reason"))
        reference_summary = _reference_summary(metadata)
        for pull_id in pull_ids:
            observation = rows_by_pull.get(pull_id)
            if observation is None:
                continue
            if registered_artifact is None:
                rejected_status = (
                    AnomalyStatus.UNSUPPORTED_SOURCE
                    if rejected_reason
                    in {
                        AnomalyReason.REQUIRED_SIGNAL_UNAVAILABLE,
                        AnomalyReason.SOURCE_NOT_ALLOWLISTED,
                    }
                    else AnomalyStatus.INSUFFICIENT_REFERENCE
                )
                finding = _abstention(
                    observation,
                    rejected_status,
                    rejected_reason,
                    threshold=None,
                )
            elif reason := _cohort_mismatch(
                observation,
                registered_artifact,
                reference_summary,
                source_role,
            ):
                finding = _abstention(
                    observation,
                    AnomalyStatus.UNSUPPORTED_SOURCE
                    if reason
                    in {AnomalyReason.SOURCE_NOT_ALLOWLISTED, AnomalyReason.SOURCE_ROLE_MISMATCH}
                    else AnomalyStatus.INCOMPATIBLE_CONTEXT,
                    reason,
                    threshold=registered_artifact.fitted.threshold,
                )
            else:
                data_quality_reason = _quality_exclusion(observation, definition)
                if data_quality_reason is not None:
                    finding = _abstention(
                        observation,
                        AnomalyStatus.LOW_QUALITY,
                        _reason_or_default(data_quality_reason),
                        threshold=registered_artifact.fitted.threshold,
                    )
                elif feature_reason := _feature_exclusion(observation, definition):
                    mapped_status = (
                        AnomalyStatus.INSUFFICIENT_SIGNAL
                        if feature_reason
                        in {
                            AnomalyReason.REQUIRED_FEATURE_MISSING.value,
                            AnomalyReason.REQUIRED_SIGNAL_UNAVAILABLE.value,
                            AnomalyReason.FEATURE_COVERAGE_TOO_LOW.value,
                        }
                        else AnomalyStatus.LOW_QUALITY
                    )
                    finding = _abstention(
                        observation,
                        mapped_status,
                        _reason_or_default(feature_reason),
                        threshold=registered_artifact.fitted.threshold,
                    )
                else:
                    with self._span("anomaly.observation.score", definition):
                        finding = score_observation(
                            definition,
                            registered_artifact.fitted,
                            observation,
                            observation_cutoff=observation_cutoff,
                        )
            identity = finding_idempotency_key(
                detector_version_id=detector_version_id,
                observation=observation,
                observation_cutoff=observation_cutoff,
                scoring_version=definition.scoring_version,
                threshold=finding.threshold,
            )
            findings.append((observation, finding, identity))
            status_counts[finding.status.value] = status_counts.get(finding.status.value, 0) + 1
            if self.telemetry is not None:
                labels = {"family": definition.family.value, "method": definition.method.value}
                if finding.score is not None:
                    self.telemetry.anomaly_score.record(finding.score, labels)
                if finding.threshold is not None:
                    self.telemetry.anomaly_threshold.record(finding.threshold, labels)

        target_manifest = [
            {
                "pull_id": str(pull_id),
                "feature_set_id": str(rows_by_pull[pull_id].feature_set_id)
                if pull_id in rows_by_pull
                else None,
                "source_hash": rows_by_pull[pull_id].source_hash
                if pull_id in rows_by_pull
                else None,
                "provenance_hash": rows_by_pull[pull_id].provenance_hash
                if pull_id in rows_by_pull
                else None,
            }
            for pull_id in sorted(pull_ids, key=str)
        ]
        input_checksum = stable_hash(
            {
                "detector_version_id": str(detector_version_id),
                "reference_checksum": str(metadata["reference_checksum"]),
                "cutoff": observation_cutoff.isoformat(),
                "source_role": source_role.value,
                "targets": target_manifest,
            }
        )
        artifact_checksum = (
            str(metadata["artifact_checksum"])
            if metadata.get("artifact_checksum") is not None
            else None
        )
        duration = time.perf_counter() - started
        summary: dict[str, Any] = {
            "schema_version": "phase9c-detection-run-v1",
            "family": definition.family.value,
            "method": definition.method.value,
            "horizon": "AFTER_PULL_OFFLINE",
            "source_role": source_role.value,
            "observation_cutoff": observation_cutoff.isoformat(),
            "requested_count": len(pull_ids),
            "feature_set_count": len(rows),
            "missing_feature_set_count": len(absent_pulls),
            "scored_count": len(findings),
            "status_counts": dict(sorted(status_counts.items())),
            "missing_feature_set_ids": [],
            "missing_feature_set_count_only": len(absent_pulls),
            "target_read_seconds": target_read_seconds,
            "artifact_checksum": artifact_checksum,
            "reference_checksum": str(metadata["reference_checksum"]),
            "reference_summary": reference_summary,
            "rejection_reason": metadata.get("rejection_reason"),
            "score_orientation": "higher_is_more_statistically_unusual",
            "score_is_probability": False,
            "interpretation": "offline engineering deviation; not diagnosis or failure risk",
        }
        run_identity = stable_hash(
            {
                "detector_version_id": str(detector_version_id),
                "reference_dataset_id": str(metadata["reference_dataset_id"]),
                "input_checksum": input_checksum,
                "source_role": source_role.value,
                "cutoff": observation_cutoff.isoformat(),
            }
        )
        persistence_started = time.perf_counter()
        with self._span("anomaly.finding.persistence", definition) as span:
            run_id, finding_ids, created = await self.registry.persist_run(
                run_identity=run_identity,
                detector_version_id=detector_version_id,
                reference_dataset_id=cast(UUID, metadata["reference_dataset_id"]),
                observation_cutoff=observation_cutoff,
                source_role=source_role,
                input_checksum=input_checksum,
                artifact_checksum=artifact_checksum,
                requested_count=len(pull_ids),
                findings=tuple(findings),
                summary=summary,
                duration_seconds=duration,
                trace_id=trace_id,
            )
            finding_persistence_seconds = time.perf_counter() - persistence_started
            if span is not None:
                span.set_attribute("finding.count", len(findings))
                span.set_attribute("finding.persistence_seconds", finding_persistence_seconds)
        self._record_score_metrics(definition, status_counts, duration)
        return DetectionRunResult(
            run_id=run_id,
            run_identity=run_identity,
            detector_version_id=detector_version_id,
            reference_dataset_id=cast(UUID, metadata["reference_dataset_id"]),
            observation_cutoff=observation_cutoff,
            source_role=source_role,
            requested_count=len(pull_ids),
            scored_count=len(findings),
            missing_feature_set_count=len(absent_pulls),
            finding_ids=finding_ids,
            status_counts=status_counts,
            input_checksum=input_checksum,
            artifact_checksum=artifact_checksum,
            duration_seconds=duration,
            target_read_seconds=target_read_seconds,
            finding_persistence_seconds=finding_persistence_seconds,
            summary=summary,
            idempotent_replay=not created,
        )

    async def freeze_validation_threshold(
        self,
        *,
        detector_version_id: UUID,
        threshold: float,
        validation_checksum: str,
        selection_manifest: dict[str, Any],
        accepted: bool = False,
        git_sha: str | None = None,
    ) -> DetectorVersionResult:
        """Create a new immutable candidate with a validation-selected threshold."""
        if not math.isfinite(threshold) or threshold < 0:
            raise ValueError("frozen detector threshold must be finite and nonnegative")
        if len(validation_checksum) != 64 or any(
            char not in "0123456789abcdef" for char in validation_checksum
        ):
            raise ValueError("validation evidence checksum must be SHA-256")
        canonical_json(selection_manifest)
        prior = await self._load_version_metadata(detector_version_id)
        if prior["state"] != DetectorLifecycle.CANDIDATE.value:
            raise AnomalyArtifactError("only a fitted candidate can receive a frozen threshold")
        artifact = await self.artifacts.load_registered(self.database, str(detector_version_id))
        frozen = replace(artifact.fitted, threshold=float(threshold))
        fit_checksum = stable_hash(
            {
                "base_fit_checksum": artifact.fit_checksum,
                "definition_checksum": artifact.definition.checksum,
                "reference_checksum": artifact.reference_checksum,
                "threshold": float(threshold),
                "threshold_selection_version": "phase9c-validation-selection-v1",
                "acceptance_state": (
                    DetectorLifecycle.ACCEPTED.value
                    if accepted
                    else DetectorLifecycle.CANDIDATE.value
                ),
                "validation_checksum": validation_checksum,
                "selection_manifest": selection_manifest,
            }
        )
        version = await self.registry.reserve_version()
        receipt = self.artifacts.write(
            artifact.definition,
            frozen,
            version=version,
            fit_checksum=fit_checksum,
        )
        training_metrics = dict(prior["training_metrics"])
        training_metrics.update(
            {
                "fitted_checksum": frozen.checksum,
                "threshold": float(threshold),
                "threshold_source": "VALIDATION_ONLY",
                "threshold_selection_version": "phase9c-validation-selection-v1",
                "validation_checksum": validation_checksum,
                "threshold_selection": selection_manifest,
                "selection_state": (
                    DetectorLifecycle.ACCEPTED.value
                    if accepted
                    else DetectorLifecycle.CANDIDATE.value
                ),
            }
        )
        frozen_state = DetectorLifecycle.ACCEPTED if accepted else DetectorLifecycle.CANDIDATE
        try:
            self.artifacts.verify_staged(
                receipt,
                definition=artifact.definition,
                fitted=frozen,
                version=version,
                fit_checksum=fit_checksum,
            )
            version_id, registered_version, created = await self.registry.persist_detector_version(
                artifact.definition,
                reference_dataset_id=UUID(artifact.reference_dataset_id),
                fit_checksum=fit_checksum,
                state=frozen_state,
                threshold=float(threshold),
                artifact=receipt,
                rejection_reason=None,
                training_metrics=training_metrics,
                input_schema=dict(prior["input_schema"]),
                version=version,
                repository_sha=git_sha or repository_sha(),
            )
        except Exception:
            self.artifacts.delete_staged(receipt)
            raise
        if not created:
            self.artifacts.delete_staged(receipt)
            checksum = await self._registered_artifact_checksum(version_id)
        else:
            checksum = receipt.checksum
        return DetectorVersionResult(
            detector_version_id=version_id,
            version=registered_version,
            state=frozen_state,
            reference_dataset_id=UUID(artifact.reference_dataset_id),
            reference_checksum=artifact.reference_checksum,
            fit_checksum=fit_checksum,
            threshold=float(threshold),
            artifact_checksum=checksum,
            rejection_reason=None,
            training_metrics=training_metrics,
            created=created,
        )

    async def _load_version_metadata(self, version_id: UUID) -> dict[str, Any]:
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT dv.*,d.family,d.method,d.key,d.version AS definition_version,"
                            "rd.checksum AS reference_checksum,rd.cohort_checksum,"
                            "rd.manifest AS reference_manifest "
                            "FROM anomaly_detector_versions dv "
                            "JOIN anomaly_detector_definitions d ON d.id=dv.detector_definition_id "
                            "JOIN anomaly_reference_datasets rd ON rd.id=dv.reference_dataset_id "
                            "WHERE dv.id=:id"
                        ),
                        {"id": version_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise AnomalyArtifactError("detector version is not registered")
        return dict(row)

    async def _registered_artifact_checksum(self, version_id: UUID) -> str | None:
        async with self.database.session() as db:
            value = await db.scalar(
                text("SELECT artifact_checksum FROM anomaly_detector_versions WHERE id=:id"),
                {"id": version_id},
            )
        return str(value) if value is not None else None

    def _record_fit_metrics(
        self,
        definition: AnomalyDetectorDefinition,
        state: DetectorLifecycle,
        started: float,
        reference_rows: int,
    ) -> None:
        if self.telemetry is None:
            return
        attributes = {"family": definition.family.value, "method": definition.method.value}
        self.telemetry.anomaly_fit_runs.add(1, {**attributes, "state": state.value.lower()})
        self.telemetry.anomaly_fit_duration.record(time.perf_counter() - started, attributes)
        self.telemetry.anomaly_reference_rows.record(reference_rows, attributes)

    def _span(self, name: str, definition: AnomalyDetectorDefinition) -> Any:
        if self.telemetry is None:
            return nullcontext(None)
        manager = self.telemetry.tracer.start_as_current_span(name)
        span = manager.__enter__()
        span.set_attribute("detector.family", definition.family.value)
        span.set_attribute("detector.method", definition.method.value)
        return _SpanContext(manager, span)

    def _record_score_metrics(
        self,
        definition: AnomalyDetectorDefinition,
        counts: dict[str, int],
        duration: float,
    ) -> None:
        if self.telemetry is None:
            return
        attributes = {"family": definition.family.value, "method": definition.method.value}
        self.telemetry.anomaly_detection_runs.add(1, attributes)
        self.telemetry.anomaly_detection_duration.record(duration, attributes)
        for status, count in counts.items():
            self.telemetry.anomaly_findings.add(count, {**attributes, "status": status.lower()})


def _candidate_training_metrics(
    dataset: AnomalyReferenceDataset,
    definition: AnomalyDetectorDefinition,
    fitted: FittedDetector,
) -> dict[str, Any]:
    return {
        "reference_checksum": fitted.reference_checksum,
        "fitted_checksum": fitted.checksum,
        "threshold": fitted.threshold,
        "training_score_quantile": fitted.training_score_quantile,
        "training_score_summary": fitted.training_score_summary,
        "eligible_rows": len(dataset.rows),
        "independent_sessions": len({item.session_id for item in dataset.rows}),
        "reference_temporal_span_seconds": dataset.temporal_span.total_seconds(),
        "included_feature_order": list(fitted.feature_order),
        "excluded_constant_features": sorted(
            key for key, stats in fitted.robust_stats.items() if stats.constant
        ),
        "input_schema": _input_schema(definition),
        "library_versions": library_versions(),
        "fit_parameters": definition.fit_parameters,
        "threshold_policy": definition.threshold_policy,
        "score_orientation": "higher_is_more_statistically_unusual",
        "score_is_probability": False,
    }


def _rejected_training_metrics(
    dataset: AnomalyReferenceDataset,
    definition: AnomalyDetectorDefinition,
    reason: str | None,
) -> dict[str, Any]:
    return {
        "reference_checksum": dataset.checksum(definition),
        "rejection_reason": reason,
        "eligible_rows": len(dataset.rows),
        "independent_sessions": len({item.session_id for item in dataset.rows}),
        "reference_temporal_span_seconds": dataset.temporal_span.total_seconds(),
        "input_schema": _input_schema(definition),
        "library_versions": library_versions(),
        "score_orientation": "higher_is_more_statistically_unusual",
        "score_is_probability": False,
    }


def _input_schema(definition: AnomalyDetectorDefinition) -> dict[str, Any]:
    return {
        "schema_version": "phase9c-anomaly-input-v1",
        "feature_set_version": "phase9a-pull-v2",
        "family": definition.family.value,
        "features": [item.manifest() for item in definition.features],
        "required_signal_keys": list(definition.required_signal_keys),
        "horizon": "AFTER_PULL_OFFLINE",
        "cohort_policy": definition.cohort_policy,
        "quality_policy": definition.quality_policy,
    }


def _reason_or_default(value: Any) -> AnomalyReason:
    try:
        return value if isinstance(value, AnomalyReason) else AnomalyReason(str(value))
    except ValueError:
        return AnomalyReason.REFERENCE_SUPPORT_TOO_LOW


def _abstention(
    observation: ReferenceRow,
    status: AnomalyStatus,
    reason: AnomalyReason,
    *,
    threshold: float | None,
) -> AnomalyFindingResult:
    observed = tuple(
        key
        for key, item in sorted(observation.features.items())
        if item.value is not None and item.quality in {"valid", "limited"}
    )
    absent = tuple(key for key in sorted(observation.features) if key not in observed)
    coverage = len(observed) / len(observation.features) if observation.features else 0.0
    return AnomalyFindingResult(
        status=status,
        score=None,
        threshold=threshold,
        coverage=coverage,
        observed_features=observed,
        absent_features=absent,
        contributions=(),
        reasons=(reason,),
    )


def _cohort_mismatch(
    observation: ReferenceRow,
    artifact: TrustedAnomalyArtifact,
    reference_summary: dict[str, Any],
    source_role: SourceRole,
) -> AnomalyReason | None:
    cohort = artifact.cohort
    if observation.source_role is not source_role or source_role is not cohort.source_role:
        return AnomalyReason.SOURCE_ROLE_MISMATCH
    if observation.source_type != cohort.source_type:
        return AnomalyReason.SOURCE_NOT_ALLOWLISTED
    if observation.vehicle_id != cohort.vehicle_id:
        return AnomalyReason.VEHICLE_MISMATCH
    if observation.configuration_id != cohort.configuration_id:
        return AnomalyReason.CONFIGURATION_MISMATCH
    if observation.modification_ids != cohort.modification_ids:
        return AnomalyReason.MODIFICATION_MISMATCH
    manifest = artifact.reference_manifest
    anchor_session_id = manifest.get("anchor_session_id")
    if anchor_session_id is not None and observation.session_id == str(anchor_session_id):
        return AnomalyReason.SESSION_OVERLAP
    reference_sessions = manifest.get("selected_rows", [])
    if isinstance(reference_sessions, list) and any(
        isinstance(item, dict) and item.get("session_id") == observation.session_id
        for item in reference_sessions
    ):
        return AnomalyReason.SESSION_OVERLAP
    if reference_summary.get("cohort_checksum") != cohort.checksum:
        return AnomalyReason.FEATURE_SCHEMA_MISMATCH
    return None


def summarize_family_findings(
    findings: dict[str, AnomalyFindingResult],
) -> dict[str, Any]:
    """Create a descriptive cross-family summary without training a fifth detector."""
    eligible = {
        family: finding
        for family, finding in findings.items()
        if finding.status in {AnomalyStatus.ANOMALOUS, AnomalyStatus.INLIER}
        and finding.score is not None
        and finding.threshold is not None
        and finding.threshold > 0
    }
    ratios = {
        family: finding.score / finding.threshold
        for family, finding in sorted(eligible.items())
        if finding.score is not None and finding.threshold is not None
    }
    anomalous = sum(finding.status is AnomalyStatus.ANOMALOUS for finding in eligible.values())
    if len(eligible) < 2:
        status = "INSUFFICIENT_FAMILY_COVERAGE"
    elif anomalous >= 2:
        status = "MULTI_FAMILY_DEVIATION"
    else:
        status = "NO_MULTI_FAMILY_DEVIATION"
    return {
        "status": status,
        "eligible_family_count": len(eligible),
        "family_threshold_ratios": ratios,
        "interpretation": (
            "descriptive agreement across independent feature families; not diagnosis or risk"
        ),
    }


def _reference_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    manifest = metadata.get("reference_manifest")
    if not isinstance(manifest, dict):
        manifest = {}
    return {
        "family": str(metadata.get("family", "unknown")),
        "method": str(metadata.get("method", "unknown")),
        "reference_dataset_id": str(metadata.get("reference_dataset_id", "")),
        "reference_checksum": str(metadata.get("reference_checksum", "")),
        "cohort_checksum": str(metadata.get("cohort_checksum", "")),
        "observation_cutoff": str(manifest.get("observation_cutoff", "")),
        "row_count": int(manifest.get("row_count", 0)),
        "session_count": int(manifest.get("independent_session_count", 0)),
        "first_pull_at": manifest.get("first_pull_at"),
        "last_pull_at": manifest.get("last_pull_at"),
    }


class _SpanContext:
    def __init__(self, manager: Any, span: Any) -> None:
        self.manager = manager
        self.span = span

    def __enter__(self) -> Any:
        return self.span

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> Any:
        return self.manager.__exit__(exc_type, exc_value, traceback)
