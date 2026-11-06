from __future__ import annotations

import re
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Security
from fastapi.security import HTTPBearer
from pydantic import AwareDatetime, BaseModel, ConfigDict

from vehicle_platform.anomalies.domain import SourceRole
from vehicle_platform.api.contracts import ErrorResponse
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.prediction_evidence.domain import PredictionEvidenceProjection
from vehicle_platform.prediction_evidence.service import PredictionEvidenceService
from vehicle_platform.predictions.domain import (
    AnomalyFamily,
    AnomalyRequest,
    NextPullRequest,
    PredictionAgentRunContext,
    PredictionError,
    PredictionKind,
    PredictionReceiptHistoryFilters,
    PredictionReceiptHistoryPage,
    PredictionResponse,
    PredictionStatus,
)
from vehicle_platform.predictions.service import PredictionService

_bearer = HTTPBearer(auto_error=False, scheme_name="PredictionOperatorBearer")
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


class PredictionBindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_id: UUID
    result_kind: str
    subject_key: str
    source_role: str
    environment: str
    scope: str
    model_version_id: UUID | None
    detector_version_id: UUID | None
    artifact_checksum: str
    feature_set_version: str
    feature_set_checksum: str
    schema_checksum: str
    activation_event_id: UUID


class PredictionVersionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "phase9d-serving-versions-v1"
    items: list[PredictionBindingResponse]
    limit: int
    offset: int


class PredictionEvidenceMaterializeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase9e-prediction-evidence-v1"] = "phase9e-prediction-evidence-v1"


class PredictionEvidenceMaterializeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materialized: bool
    evidence: PredictionEvidenceProjection


def prediction_router(
    service: PredictionService,
    evidence_service: PredictionEvidenceService | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/prediction-service", tags=["prediction-service"])
    error_responses: dict[int | str, dict[str, Any]] = {
        401: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    }

    @router.get(
        "/versions",
        response_model=PredictionVersionsResponse,
        operation_id="prediction_service_versions",
        responses=error_responses,
        dependencies=[Security(_bearer)],
    )
    async def versions(
        request: Request,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=10_000),
    ) -> PredictionVersionsResponse:
        request.state.prediction_endpoint = "versions"
        items = await service.versions(limit=limit, offset=offset)
        return PredictionVersionsResponse(
            items=[PredictionBindingResponse.model_validate(item) for item in items],
            limit=limit,
            offset=offset,
        )

    @router.post(
        "/next-pull",
        response_model=PredictionResponse,
        operation_id="prediction_service_next_pull",
        responses=error_responses,
        dependencies=[Security(_bearer)],
    )
    async def next_pull(
        payload: NextPullRequest,
        request: Request,
        idempotency_key: Annotated[
            str | None, Header(alias="Idempotency-Key", max_length=128)
        ] = None,
    ) -> PredictionResponse:
        _validate_idempotency_key(idempotency_key)
        request.state.prediction_endpoint = "next_pull"
        return await service.next_pull(
            payload,
            idempotency_key=idempotency_key,
            operator_id="controlled-api-operator",
        )

    @router.post(
        "/anomalies",
        response_model=PredictionResponse,
        operation_id="prediction_service_anomalies",
        responses=error_responses,
        dependencies=[Security(_bearer)],
    )
    async def anomalies(
        payload: AnomalyRequest,
        request: Request,
        idempotency_key: Annotated[
            str | None, Header(alias="Idempotency-Key", max_length=128)
        ] = None,
    ) -> PredictionResponse:
        _validate_idempotency_key(idempotency_key)
        request.state.prediction_endpoint = "anomalies"
        return await service.anomaly(payload, idempotency_key=idempotency_key)

    @router.get(
        "/runs/{receipt_id}",
        response_model=PredictionResponse,
        operation_id="prediction_service_receipt",
        responses={**error_responses, 404: {"model": ErrorResponse}},
        dependencies=[Security(_bearer)],
    )
    async def receipt(receipt_id: UUID, request: Request) -> PredictionResponse:
        request.state.prediction_endpoint = "receipt"
        return await service.receipt(receipt_id)

    @router.get(
        "/vehicles/{vehicle_id}/runs",
        response_model=PredictionReceiptHistoryPage,
        operation_id="prediction_service_vehicle_receipt_history",
        responses={**error_responses, 404: {"model": ErrorResponse}},
        dependencies=[Security(_bearer)],
    )
    async def vehicle_receipt_history(
        vehicle_id: UUID,
        request: Request,
        limit: int = Query(default=20, ge=1, le=20),
        offset: int = Query(default=0, ge=0, le=500),
        receipt_id: UUID | None = None,
        result_kind: PredictionKind | None = None,
        task: MLTask | None = None,
        family: AnomalyFamily | None = None,
        horizon: Literal["NEXT_PULL", "AFTER_PULL_OFFLINE"] | None = None,
        source_role: SourceRole | None = None,
        status: PredictionStatus | None = None,
        session_id: UUID | None = None,
        pull_id: UUID | None = None,
        configuration_id: UUID | None = None,
        recorded_from: AwareDatetime | None = None,
        recorded_to: AwareDatetime | None = None,
        evidence_completeness: Literal["COMPLETE", "PARTIAL", "ABSTAINED"] | None = None,
        evidence_integrity: Literal[
            "VERIFIED",
            "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE",
            "FAILED_SOURCE_MISMATCH",
            "NOT_VERIFIABLE",
            "UNSUPPORTED_SCHEMA",
        ]
        | None = None,
    ) -> PredictionReceiptHistoryPage:
        request.state.prediction_endpoint = "receipt_history"
        filters = PredictionReceiptHistoryFilters(
            limit=limit,
            offset=offset,
            receipt_id=receipt_id,
            result_kind=result_kind,
            task=task,
            family=family,
            horizon=horizon,
            source_role=source_role,
            status=status,
            session_id=session_id,
            pull_id=pull_id,
            configuration_id=configuration_id,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
            evidence_completeness=evidence_completeness,
            evidence_integrity=evidence_integrity,
        )
        return await service.receipt_history(vehicle_id, filters)

    @router.get(
        "/vehicles/{vehicle_id}/runs/{receipt_id}",
        response_model=PredictionResponse,
        operation_id="prediction_service_vehicle_receipt",
        responses={**error_responses, 404: {"model": ErrorResponse}},
        dependencies=[Security(_bearer)],
    )
    async def vehicle_receipt(
        vehicle_id: UUID, receipt_id: UUID, request: Request
    ) -> PredictionResponse:
        request.state.prediction_endpoint = "vehicle_receipt"
        result = await service.receipt_for_vehicle(vehicle_id, receipt_id)
        if result is None:
            raise PredictionError(
                404, "PREDICTION_RECEIPT_NOT_FOUND", "Prediction receipt not found"
            )
        return result

    @router.get(
        "/vehicles/{vehicle_id}/runs/{receipt_id}/agent-context",
        response_model=PredictionAgentRunContext,
        operation_id="prediction_service_receipt_agent_context",
        responses={**error_responses, 404: {"model": ErrorResponse}},
        dependencies=[Security(_bearer)],
    )
    async def receipt_agent_context(
        vehicle_id: UUID, receipt_id: UUID, request: Request
    ) -> PredictionAgentRunContext:
        request.state.prediction_endpoint = "agent_context_read"
        return await service.agent_context(vehicle_id, receipt_id)

    if evidence_service is not None:

        @router.post(
            "/runs/{receipt_id}/evidence",
            response_model=PredictionEvidenceMaterializeResponse,
            operation_id="prediction_service_materialize_evidence",
            responses={**error_responses, 404: {"model": ErrorResponse}},
            dependencies=[Security(_bearer)],
        )
        async def materialize_evidence(
            receipt_id: UUID,
            payload: PredictionEvidenceMaterializeRequest,
            request: Request,
            idempotency_key: Annotated[
                str | None, Header(alias="Idempotency-Key", max_length=128)
            ] = None,
        ) -> PredictionEvidenceMaterializeResponse:
            _validate_idempotency_key(idempotency_key)
            request.state.prediction_endpoint = "evidence_materialize"
            projection, created, _ = await evidence_service.materialize(
                receipt_id, schema_version=payload.schema_version
            )
            return PredictionEvidenceMaterializeResponse(materialized=created, evidence=projection)

        @router.get(
            "/evidence/{evidence_id}",
            response_model=PredictionEvidenceProjection,
            operation_id="prediction_service_evidence",
            responses={**error_responses, 404: {"model": ErrorResponse}},
            dependencies=[Security(_bearer)],
        )
        async def evidence(evidence_id: UUID, request: Request) -> PredictionEvidenceProjection:
            request.state.prediction_endpoint = "evidence_read"
            return await evidence_service.read(evidence_id)

        @router.get(
            "/runs/{receipt_id}/evidence",
            response_model=PredictionEvidenceProjection,
            operation_id="prediction_service_receipt_evidence",
            responses={**error_responses, 404: {"model": ErrorResponse}},
            dependencies=[Security(_bearer)],
        )
        async def receipt_evidence(
            receipt_id: UUID, request: Request
        ) -> PredictionEvidenceProjection:
            request.state.prediction_endpoint = "evidence_read"
            return await evidence_service.read_for_receipt(receipt_id)

        @router.get(
            "/vehicles/{vehicle_id}/runs/{receipt_id}/evidence",
            response_model=PredictionEvidenceProjection,
            operation_id="prediction_service_vehicle_receipt_evidence",
            responses={**error_responses, 404: {"model": ErrorResponse}},
            dependencies=[Security(_bearer)],
        )
        async def vehicle_receipt_evidence(
            vehicle_id: UUID, receipt_id: UUID, request: Request
        ) -> PredictionEvidenceProjection:
            request.state.prediction_endpoint = "vehicle_evidence_read"
            receipt = await service.receipt_for_vehicle(vehicle_id, receipt_id)
            if receipt is None:
                raise PredictionError(
                    404, "PREDICTION_RECEIPT_NOT_FOUND", "Prediction receipt not found"
                )
            return await evidence_service.read_for_receipt(receipt_id)

        @router.post(
            "/evidence/{evidence_id}/verify",
            operation_id="prediction_service_verify_evidence",
            responses={**error_responses, 404: {"model": ErrorResponse}},
            dependencies=[Security(_bearer)],
        )
        async def verify_evidence(evidence_id: UUID, request: Request) -> Any:
            request.state.prediction_endpoint = "evidence_verify"
            return await evidence_service.verify(evidence_id)

    return router


def _validate_idempotency_key(value: str | None) -> None:
    if value is not None and not _IDEMPOTENCY_KEY.fullmatch(value):
        from vehicle_platform.predictions.domain import PredictionError

        raise PredictionError(
            422, "PREDICTION_INVALID_IDEMPOTENCY_KEY", "Idempotency key format is invalid"
        )
