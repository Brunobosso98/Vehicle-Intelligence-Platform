from __future__ import annotations

import re
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Security
from fastapi.security import HTTPBearer
from pydantic import BaseModel, ConfigDict

from vehicle_platform.api.contracts import ErrorResponse
from vehicle_platform.prediction_evidence.domain import PredictionEvidenceProjection
from vehicle_platform.prediction_evidence.service import PredictionEvidenceService
from vehicle_platform.predictions.domain import AnomalyRequest, NextPullRequest, PredictionResponse
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
