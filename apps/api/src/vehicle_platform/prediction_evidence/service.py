"""Controlled Phase 9E materialization, safe reads and independent source checks."""

from __future__ import annotations

import asyncio
from contextlib import nullcontext
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import UUID

from vehicle_platform.infrastructure.database import Database
from vehicle_platform.prediction_evidence.builder import (
    build_evidence,
    fit_bundle_to_size,
    render_safe_projection,
)
from vehicle_platform.prediction_evidence.canonical import canonical_json
from vehicle_platform.prediction_evidence.domain import (
    MAX_EVIDENCE_JSON_BYTES,
    EvidenceVerificationResult,
    PredictionEvidenceBundle,
    PredictionEvidenceProjection,
    VerificationOutcome,
)
from vehicle_platform.prediction_evidence.repository import PredictionEvidenceRepository
from vehicle_platform.prediction_evidence.verifier import verify_bundle_sources
from vehicle_platform.predictions.domain import PredictionError

_ALLOWED_OUTCOMES = {
    "success",
    "reused",
    "not_verifiable",
    "failed_source_mismatch",
    "unsupported_schema",
    "timeout",
    "internal_error",
    "budget_exceeded",
    "immutable_conflict",
    "receipt_not_found",
    "projection_truncated",
    "verified",
    "verified_snapshot_artifact_unavailable",
    "audit_budget_exhausted",
}


class PredictionEvidenceService:
    def __init__(
        self,
        database: Database,
        *,
        model_artifacts: Any | None = None,
        anomaly_artifacts: Any | None = None,
        telemetry: Any | None = None,
        max_concurrent_builds: int = 2,
        timeout_seconds: float = 6.0,
    ) -> None:
        self.repository = PredictionEvidenceRepository(
            database,
            model_artifacts=model_artifacts,
            anomaly_artifacts=anomaly_artifacts,
        )
        self.telemetry = telemetry
        self.slots = asyncio.Semaphore(max_concurrent_builds)
        self.timeout_seconds = timeout_seconds

    async def materialize(
        self,
        receipt_id: UUID,
        *,
        schema_version: str = "phase9e-prediction-evidence-v1",
        dry_run: bool = False,
    ) -> tuple[PredictionEvidenceProjection, bool, PredictionEvidenceBundle]:
        if schema_version != "phase9e-prediction-evidence-v1":
            raise PredictionError(
                422,
                "PREDICTION_EVIDENCE_SCHEMA_UNSUPPORTED",
                "Evidence schema version is unsupported",
            )
        started = perf_counter()
        try:
            async with asyncio.timeout(self.timeout_seconds):
                await self.slots.acquire()
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    with self._span("prediction.evidence.source.resolve"):
                        source = await self.repository.source_snapshot(receipt_id)
                    with self._span("prediction.evidence.claim_construction"):
                        bundle = build_evidence(source, generated_at=datetime.now(UTC))
                    try:
                        bundle = fit_bundle_to_size(bundle)
                    except ValueError as error:
                        raise PredictionError(
                            422,
                            "PREDICTION_EVIDENCE_PROJECTION_TRUNCATED",
                            "Evidence cannot fit within the configured manifest bound",
                        ) from error
                    with self._span("prediction.evidence.canonical_hash"):
                        body_bytes = len(
                            canonical_json(bundle.model_dump(mode="json")).encode("utf-8")
                        )
                    if body_bytes > MAX_EVIDENCE_JSON_BYTES:
                        raise PredictionError(
                            422,
                            "PREDICTION_EVIDENCE_PROJECTION_TRUNCATED",
                            "Evidence exceeds the bounded manifest size",
                        )
                    if dry_run:
                        created = False
                    else:
                        with self._span("prediction.evidence.immutable_persist"):
                            bundle, created = await self.repository.persist(bundle)
                    self._observe(
                        "build",
                        "success",
                        bundle,
                        perf_counter() - started,
                        replay=not created and not dry_run,
                    )
                    return self._bounded_projection(bundle), created, bundle
            finally:
                self.slots.release()
        except TimeoutError as error:
            self._observe("build", "timeout", None, perf_counter() - started)
            raise PredictionError(
                503,
                "PREDICTION_EVIDENCE_BUDGET_EXCEEDED",
                "Evidence operation exceeded its time budget",
            ) from error
        except PredictionError as error:
            outcome = error.code.removeprefix("PREDICTION_EVIDENCE_").lower()
            self._observe("build", outcome, None, perf_counter() - started)
            raise
        except Exception as error:
            self._observe("build", "internal_error", None, perf_counter() - started)
            raise PredictionError(
                503, "PREDICTION_EVIDENCE_INTERNAL_ERROR", "Evidence operation is unavailable"
            ) from error

    async def read(self, evidence_id: UUID) -> PredictionEvidenceProjection:
        with self._span("prediction.evidence.read_projection"):
            bundle = await self.repository.get(evidence_id)
        if bundle is None:
            raise PredictionError(
                404, "PREDICTION_EVIDENCE_NOT_FOUND", "Prediction evidence was not found"
            )
        return self._bounded_projection(bundle)

    async def read_for_receipt(self, receipt_id: UUID) -> PredictionEvidenceProjection:
        with self._span("prediction.evidence.read_projection"):
            bundle = await self.repository.get_for_receipt(receipt_id)
        if bundle is None:
            raise PredictionError(
                404, "PREDICTION_EVIDENCE_NOT_FOUND", "Prediction evidence was not found"
            )
        return self._bounded_projection(bundle)

    async def verify(self, evidence_id: UUID) -> EvidenceVerificationResult:
        started = perf_counter()
        bundle = await self.repository.get(evidence_id)
        if bundle is None:
            raise PredictionError(
                404, "PREDICTION_EVIDENCE_NOT_FOUND", "Prediction evidence was not found"
            )
        try:
            async with asyncio.timeout(self.timeout_seconds):
                with self._span("prediction.evidence.source.resolve"):
                    source = await self.repository.source_snapshot(bundle.receipt_id)
                with self._span("prediction.evidence.independent_verify"):
                    integrity, errors = verify_bundle_sources(bundle, source)
                outcome = VerificationOutcome(
                    integrity=integrity,
                    reason_codes=tuple(errors),
                    source_count=len(bundle.nodes),
                )
                with self._span("prediction.evidence.audit_append"):
                    result = await self.repository.audit_verification(bundle, outcome)
                self._observe("verify", integrity.value.lower(), bundle, perf_counter() - started)
                return result
        except TimeoutError as error:
            self._observe("verify", "timeout", bundle, perf_counter() - started)
            raise PredictionError(
                503,
                "PREDICTION_EVIDENCE_BUDGET_EXCEEDED",
                "Evidence verification exceeded its time budget",
            ) from error
        except PredictionError as error:
            metric_outcome = error.code.removeprefix("PREDICTION_EVIDENCE_").lower()
            self._observe("verify", metric_outcome, bundle, perf_counter() - started)
            raise
        except Exception as error:
            self._observe("verify", "internal_error", bundle, perf_counter() - started)
            raise PredictionError(
                503, "PREDICTION_EVIDENCE_INTERNAL_ERROR", "Evidence verification is unavailable"
            ) from error

    @staticmethod
    def _bounded_projection(bundle: PredictionEvidenceBundle) -> PredictionEvidenceProjection:
        projection = render_safe_projection(bundle)
        if (
            len(canonical_json(projection.model_dump(mode="json")).encode("utf-8"))
            > MAX_EVIDENCE_JSON_BYTES
        ):
            raise PredictionError(
                422,
                "PREDICTION_EVIDENCE_PROJECTION_TRUNCATED",
                "Evidence projection exceeds its response size limit",
            )
        return projection

    def _observe(
        self,
        operation: str,
        outcome: str,
        bundle: PredictionEvidenceBundle | None,
        duration: float,
        *,
        replay: bool = False,
    ) -> None:
        if self.telemetry is None:
            return
        attrs = {
            "operation": operation,
            "outcome": outcome if outcome in _ALLOWED_OUTCOMES else "internal_error",
        }
        self.telemetry.prediction_evidence_operations.add(1, attrs)
        self.telemetry.prediction_evidence_duration.record(duration, {"operation": operation})
        if replay:
            self.telemetry.prediction_evidence_replays.add(1)
        if bundle is not None:
            self.telemetry.prediction_evidence_graph_size.record(
                len(bundle.nodes), {"dimension": "nodes"}
            )
            self.telemetry.prediction_evidence_graph_size.record(
                len(bundle.edges), {"dimension": "edges"}
            )
            self.telemetry.prediction_evidence_graph_size.record(
                len(bundle.facts), {"dimension": "facts"}
            )
            for gap in bundle.gaps:
                self.telemetry.prediction_evidence_gaps.add(1, {"reason": gap.code.value.lower()})

    def _span(self, name: str) -> Any:
        if self.telemetry is None:
            return nullcontext()
        return self.telemetry.tracer.start_as_current_span(name)
