from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr, ValidationError

from vehicle_platform.anomalies.domain import SourceRole
from vehicle_platform.core.config import Settings
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.predictions.domain import (
    PredictionAgentRunContext,
    PredictionError,
    PredictionLineage,
    PredictionQuality,
    PredictionReceiptHistoryItem,
    PredictionReceiptHistoryPage,
    PredictionResponse,
    PredictionStatus,
    ServingEventType,
)
from vehicle_platform.predictions.repository import PredictionRepository
from vehicle_platform.predictions.routes import prediction_router
from vehicle_platform.predictions.service import PredictionService

VEHICLE_ID = UUID("b11d5220-a3ae-4f0d-a6c8-7d26cc3a7351")
RECEIPT_ID = UUID("083bdb40-cf06-4413-b829-990902d7e66b")
SESSION_ID = UUID("4515885a-b302-49c1-ae07-1b9f62e72cb2")
PULL_ID = UUID("c2c11208-fb11-477e-91a2-79ba50b05afb")
NOW = datetime(2026, 10, 1, tzinfo=UTC)


def prediction() -> PredictionResponse:
    return PredictionResponse(
        result_type="next_pull",
        task=MLTask.FUEL_DEVIATION,
        horizon="NEXT_PULL",
        status=PredictionStatus.READY_SCORE,
        receipt_id=RECEIPT_ID,
        requested_cutoff=NOW,
        effective_cutoff=NOW,
        source_role=SourceRole.SYNTHETIC,
        model_version_id=UUID("d4dc544c-9717-4f50-8670-22b6075ce98a"),
        decision=True,
        engineering_validation_score=0.46317,
        threshold=0.4,
        interpretation="Controlled engineering score.",
        limitation="Not a mechanical diagnosis.",
        quality=PredictionQuality(
            quality_class="high",
            observed_feature_count=8,
            expected_feature_count=8,
            coverage=1,
        ),
        lineage=PredictionLineage(),
    )


def page() -> PredictionReceiptHistoryPage:
    result = prediction()
    return PredictionReceiptHistoryPage(
        items=[
            PredictionReceiptHistoryItem(
                prediction=result,
                recorded_at=NOW,
                vehicle_id=VEHICLE_ID,
                session_id=SESSION_ID,
                pull_id=PULL_ID,
                configuration_id=None,
                source_type="synthetic",
                evidence_available=False,
                captured_binding_state=ServingEventType.ACTIVATED,
                current_binding_state=ServingEventType.ACTIVATED,
            )
        ],
        total=1,
        limit=20,
        offset=0,
        has_more=False,
    )


def test_vehicle_allowlist_is_canonicalized_and_bounded() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql+asyncpg://vehicle:secret@localhost:5432/vehicle"),
        environment="test",
        prediction_service_enabled=True,
        prediction_operator_token=SecretStr("a" * 48),
        prediction_operator_vehicle_ids=f" {VEHICLE_ID}, {SESSION_ID} ",
    )

    assert settings.prediction_operator_vehicle_ids == f"{VEHICLE_ID},{SESSION_ID}"
    with pytest.raises(ValidationError):
        Settings(
            database_url=SecretStr("postgresql+asyncpg://vehicle:secret@localhost:5432/vehicle"),
            environment="test",
            prediction_operator_vehicle_ids="not-a-uuid",
        )


@pytest.mark.asyncio
async def test_vehicle_receipt_routes_return_original_scoped_values_and_filter_history() -> None:
    scoped_prediction = prediction()
    service = SimpleNamespace(
        receipt_history=AsyncMock(return_value=page()),
        receipt_for_vehicle=AsyncMock(return_value=scoped_prediction),
        agent_context=AsyncMock(
            return_value=PredictionAgentRunContext(receipt_id=RECEIPT_ID, items=[])
        ),
    )
    app = FastAPI()
    app.include_router(prediction_router(cast(PredictionService, service)))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        history_response = await client.get(
            f"/api/v1/prediction-service/vehicles/{VEHICLE_ID}/runs",
            params={
                "result_kind": "next_pull",
                "task": "NEXT_PULL_FUEL_DEVIATION",
                "source_role": "synthetic",
                "horizon": "NEXT_PULL",
                "offset": 0,
                "limit": 20,
            },
        )
        detail_response = await client.get(
            f"/api/v1/prediction-service/vehicles/{VEHICLE_ID}/runs/{RECEIPT_ID}"
        )
        agent_response = await client.get(
            f"/api/v1/prediction-service/vehicles/{VEHICLE_ID}/runs/{RECEIPT_ID}/agent-context"
        )

    assert history_response.status_code == 200
    assert (
        history_response.json()["items"][0]["prediction"]["engineering_validation_score"] == 0.46317
    )
    assert history_response.json()["items"][0]["prediction"]["threshold"] == 0.4
    assert detail_response.status_code == 200
    assert detail_response.json()["receipt_id"] == str(RECEIPT_ID)
    assert detail_response.json()["source_role"] == "synthetic"
    assert agent_response.status_code == 200
    assert agent_response.json()["items"] == []
    assert service.receipt_history.await_args.args[1].task == "NEXT_PULL_FUEL_DEVIATION"
    service.agent_context.assert_awaited_once_with(VEHICLE_ID, RECEIPT_ID)


@pytest.mark.asyncio
async def test_agent_context_checks_allowlisted_vehicle_and_persisted_receipt_first() -> None:
    service = object.__new__(PredictionService)
    service.settings = cast(
        Settings, SimpleNamespace(prediction_operator_vehicle_ids=str(VEHICLE_ID))
    )
    receipt_history = AsyncMock(return_value=page())
    agent_context = AsyncMock(
        return_value=PredictionAgentRunContext(receipt_id=RECEIPT_ID, items=[])
    )
    service.repository = cast(
        PredictionRepository,
        SimpleNamespace(receipt_history=receipt_history, agent_context=agent_context),
    )

    result = await service.agent_context(VEHICLE_ID, RECEIPT_ID)
    assert result.receipt_id == RECEIPT_ID
    agent_context.assert_awaited_once_with(VEHICLE_ID, RECEIPT_ID)
    receipt_history.assert_awaited_once()

    foreign = UUID("5285886b-ae24-4244-bb19-37030bcfd17d")
    with pytest.raises(PredictionError) as error:
        await service.agent_context(foreign, RECEIPT_ID)
    assert error.value.status_code == 404
    receipt_history.assert_awaited_once()
