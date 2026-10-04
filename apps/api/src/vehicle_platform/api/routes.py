import asyncio
from collections.abc import AsyncIterator
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from pydantic import AwareDatetime
from sqlalchemy import text
from starlette.responses import StreamingResponse

from vehicle_platform.acquisition.domain import (
    DeviceCapabilities,
    LoggingRecipe,
    Support,
    preflight,
)
from vehicle_platform.acquisition.quality import collector_health
from vehicle_platform.acquisition.recipes import BY_KEY, RECIPES
from vehicle_platform.acquisition.service import (
    AcquisitionAuthError,
    AcquisitionError,
    AcquisitionService,
)
from vehicle_platform.analysis.service import AnalysisLimitError, SessionAnalysisService
from vehicle_platform.analytics.domain import AnalyticsConfig
from vehicle_platform.analytics.service import AnalyticsService
from vehicle_platform.api.contracts import ErrorResponse, Health, Ready, Version
from vehicle_platform.api.domain_contracts import (
    AcquisitionBatch,
    AcquisitionBatchAccepted,
    AcquisitionCreate,
    AcquisitionCreated,
    AcquisitionFinalized,
    AcquisitionHeartbeat,
    AcquisitionLiveSnapshot,
    AcquisitionStatusResponse,
    AnalysisRequest,
    AnalysisResult,
    AnalyticsRequest,
    AnalyticsResultResponse,
    ConfigurationCreate,
    CSVImportPreview,
    CSVPreviewPoint,
    DatasetCapabilityReport,
    DetectedEvent,
    DrivingSession,
    EventAnalysisRequest,
    EventAnalysisResult,
    EventSummary,
    ImportResult,
    LoggingRecipeResponse,
    Modification,
    ModificationCreate,
    ObjectiveResponse,
    PreflightRequest,
    PreflightResponse,
    ProvisionalFindingResponse,
    Pull,
    SessionCreate,
    SessionSegment,
    Signal,
    TelemetryWindow,
    Vehicle,
    VehicleConfiguration,
    VehicleCreate,
    VehicleUpdate,
)
from vehicle_platform.core.config import Settings
from vehicle_platform.events.service import EventAnalysisLimitError, EventAnalysisService
from vehicle_platform.infrastructure.database import Database, DatabaseProbe
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.telemetry.domain import SIGNAL_BY_ALIAS, SIGNALS, normalize_value
from vehicle_platform.telemetry.mapping import (
    CSVColumnMapping,
    MappedCSVTelemetrySource,
    inspect_csv,
)
from vehicle_platform.telemetry.service import (
    IngestionService,
    QueryService,
    validate_vehicle_context,
)
from vehicle_platform.telemetry.sources import CSVTelemetrySource


def router(
    settings: Settings, database: DatabaseProbe, telemetry: Telemetry | None = None
) -> APIRouter:
    routes = APIRouter()

    @routes.get("/health/live", response_model=Health, operation_id="health_live")
    async def live() -> Health:
        return Health()

    @routes.get(
        "/health/ready",
        response_model=Ready,
        operation_id="health_ready",
        responses={503: {"model": ErrorResponse}},
    )
    async def ready(request: Request) -> Ready:
        await database.check()
        return Ready()

    @routes.get("/version", response_model=Version, operation_id="version")
    async def version() -> Version:
        return Version(
            version=settings.app_version,
            git_sha=settings.git_sha,
            build_timestamp=settings.build_timestamp,
            environment=settings.environment,
        )

    def store() -> Database:
        if not isinstance(database, Database):
            raise HTTPException(503, "domain database unavailable")
        return database

    @routes.post(
        "/api/v1/vehicles", response_model=Vehicle, status_code=201, operation_id="create_vehicle"
    )
    async def create_vehicle(payload: VehicleCreate) -> Vehicle:
        async with store().session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            """INSERT INTO vehicles(vin,manufacturer,model,generation,model_year,engine_code,transmission,nickname) VALUES(:vin,:manufacturer,:model,:generation,:model_year,:engine_code,:transmission,:nickname) RETURNING *"""
                        ),
                        payload.model_dump(),
                    )
                )
                .mappings()
                .one()
            )
            await db.commit()
        return Vehicle.model_validate(row)

    @routes.get("/api/v1/vehicles", response_model=list[Vehicle], operation_id="list_vehicles")
    async def list_vehicles() -> list[Vehicle]:
        async with store().session() as db:
            rows = (
                await db.execute(text("SELECT * FROM vehicles ORDER BY created_at,id LIMIT 100"))
            ).mappings()
        return [Vehicle.model_validate(row) for row in rows]

    @routes.get(
        "/api/v1/vehicles/{vehicle_id}",
        response_model=Vehicle,
        operation_id="get_vehicle",
        responses={404: {"model": ErrorResponse}},
    )
    async def get_vehicle(vehicle_id: UUID) -> Vehicle:
        async with store().session() as db:
            row = (
                (await db.execute(text("SELECT * FROM vehicles WHERE id=:id"), {"id": vehicle_id}))
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise HTTPException(404, "vehicle not found")
        return Vehicle.model_validate(row)

    @routes.patch(
        "/api/v1/vehicles/{vehicle_id}",
        response_model=Vehicle,
        operation_id="update_vehicle",
        responses={404: {"model": ErrorResponse}},
    )
    async def update_vehicle(vehicle_id: UUID, payload: VehicleUpdate) -> Vehicle:
        async with store().session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "UPDATE vehicles SET nickname=:nickname,transmission=:transmission,updated_at=now() WHERE id=:id RETURNING *"
                        ),
                        {"id": vehicle_id, **payload.model_dump()},
                    )
                )
                .mappings()
                .one_or_none()
            )
            await db.commit()
        if row is None:
            raise HTTPException(404, "vehicle not found")
        return Vehicle.model_validate(row)

    @routes.post(
        "/api/v1/vehicles/{vehicle_id}/configurations",
        response_model=VehicleConfiguration,
        status_code=201,
        operation_id="create_configuration",
    )
    async def create_configuration(
        vehicle_id: UUID, payload: ConfigurationCreate
    ) -> VehicleConfiguration:
        values = payload.model_dump()
        values["metadata"] = __import__("json").dumps(values["metadata"])
        async with store().session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            """INSERT INTO vehicle_configurations(vehicle_id,effective_at,ended_at,description,metadata,provenance) VALUES(:vehicle_id,:effective_at,:ended_at,:description,CAST(:metadata AS jsonb),:provenance) RETURNING *"""
                        ),
                        {"vehicle_id": vehicle_id, **values},
                    )
                )
                .mappings()
                .one()
            )
            await db.commit()
        return VehicleConfiguration.model_validate(row)

    @routes.get(
        "/api/v1/vehicles/{vehicle_id}/configurations",
        response_model=list[VehicleConfiguration],
        operation_id="list_configurations",
    )
    async def list_configurations(
        vehicle_id: UUID, effective_at: datetime | None = None
    ) -> list[VehicleConfiguration]:
        sql = (
            "SELECT * FROM vehicle_configurations WHERE vehicle_id=:id"
            + (
                " AND effective_at<=:at AND (ended_at IS NULL OR ended_at>:at)"
                if effective_at
                else ""
            )
            + " ORDER BY effective_at DESC"
        )
        async with store().session() as db:
            rows = (await db.execute(text(sql), {"id": vehicle_id, "at": effective_at})).mappings()
        return [VehicleConfiguration.model_validate(row) for row in rows]

    @routes.post(
        "/api/v1/vehicles/{vehicle_id}/modifications",
        response_model=Modification,
        status_code=201,
        operation_id="create_modification",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def create_modification(vehicle_id: UUID, payload: ModificationCreate) -> Modification:
        async with store().session() as db:
            try:
                await validate_vehicle_context(db, vehicle_id, payload.configuration_id)
            except LookupError as exc:
                raise HTTPException(404, "vehicle or configuration not found") from exc
            except ValueError as exc:
                raise HTTPException(422, "invalid vehicle configuration association") from exc
            row = (
                (
                    await db.execute(
                        text(
                            """INSERT INTO modifications(vehicle_id,category,manufacturer,product,installed_at,removed_at,notes,configuration_id) VALUES(:vehicle_id,:category,:manufacturer,:product,:installed_at,:removed_at,:notes,:configuration_id) RETURNING *"""
                        ),
                        {"vehicle_id": vehicle_id, **payload.model_dump()},
                    )
                )
                .mappings()
                .one()
            )
            await db.commit()
        return Modification.model_validate(row)

    @routes.get(
        "/api/v1/vehicles/{vehicle_id}/modifications",
        response_model=list[Modification],
        operation_id="list_modifications",
    )
    async def list_modifications(vehicle_id: UUID) -> list[Modification]:
        async with store().session() as db:
            rows = (
                await db.execute(
                    text("SELECT * FROM modifications WHERE vehicle_id=:id ORDER BY installed_at"),
                    {"id": vehicle_id},
                )
            ).mappings()
        return [Modification.model_validate(row) for row in rows]

    @routes.post(
        "/api/v1/sessions",
        response_model=DrivingSession,
        status_code=201,
        operation_id="create_session",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def create_session(payload: SessionCreate) -> DrivingSession:
        values = payload.model_dump()
        values["metadata"] = __import__("json").dumps(values["metadata"])
        async with store().session() as db:
            try:
                await validate_vehicle_context(
                    db, payload.vehicle_id, payload.configuration_id, payload.started_at
                )
            except LookupError as exc:
                raise HTTPException(404, "vehicle or configuration not found") from exc
            except ValueError as exc:
                raise HTTPException(422, "invalid vehicle configuration association") from exc
            row = (
                (
                    await db.execute(
                        text(
                            """INSERT INTO driving_sessions(vehicle_id,configuration_id,source_type,source_reference,started_at,ended_at,source_timezone,metadata) VALUES(:vehicle_id,:configuration_id,:source_type,:source_reference,:started_at,:ended_at,:source_timezone,CAST(:metadata AS jsonb)) RETURNING *"""
                        ),
                        values,
                    )
                )
                .mappings()
                .one()
            )
            await db.commit()
        return DrivingSession.model_validate(row)

    @routes.get(
        "/api/v1/sessions", response_model=list[DrivingSession], operation_id="list_sessions"
    )
    async def list_sessions(vehicle_id: UUID | None = None) -> list[DrivingSession]:
        sql = (
            "SELECT * FROM driving_sessions"
            + (" WHERE vehicle_id=:id" if vehicle_id else "")
            + " ORDER BY started_at DESC NULLS LAST LIMIT 100"
        )
        async with store().session() as db:
            rows = (await db.execute(text(sql), {"id": vehicle_id})).mappings()
        return [DrivingSession.model_validate(row) for row in rows]

    @routes.get(
        "/api/v1/sessions/{session_id}",
        response_model=DrivingSession,
        operation_id="get_session",
        responses={404: {"model": ErrorResponse}},
    )
    async def get_session(session_id: UUID) -> DrivingSession:
        async with store().session() as db:
            row = (
                (
                    await db.execute(
                        text("SELECT * FROM driving_sessions WHERE id=:id"), {"id": session_id}
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise HTTPException(404, "session not found")
        return DrivingSession.model_validate(row)

    @routes.post(
        "/api/v1/sessions/{session_id}/imports/csv",
        response_model=ImportResult,
        operation_id="import_csv",
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            415: {"model": ErrorResponse},
        },
    )
    async def import_csv(
        session_id: UUID,
        file: UploadFile = File(...),
        mapping: str | None = Form(default=None, max_length=16384),
    ) -> ImportResult:
        if file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
            raise HTTPException(415, "CSV content type required")
        content = await file.read(10_000_001)
        async with store().session() as db:
            if (
                await db.scalar(
                    text("SELECT 1 FROM driving_sessions WHERE id=:id"), {"id": session_id}
                )
                is None
            ):
                raise HTTPException(404, "session not found")
        try:
            source = (
                MappedCSVTelemetrySource(content, CSVColumnMapping.model_validate_json(mapping))
                if mapping is not None
                else CSVTelemetrySource(content)
            )
            return await IngestionService(store(), telemetry=telemetry).ingest(
                session_id, "csv", source
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @routes.post(
        "/api/v1/sessions/{session_id}/imports/csv/preview",
        response_model=CSVImportPreview,
        operation_id="preview_csv_import",
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            415: {"model": ErrorResponse},
        },
    )
    async def preview_csv_import(
        session_id: UUID,
        file: UploadFile = File(...),
        mapping: str | None = Form(default=None, max_length=16384),
    ) -> CSVImportPreview:
        if file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
            raise HTTPException(415, "CSV content type required")
        async with store().session() as db:
            if (
                await db.scalar(
                    text("SELECT 1 FROM driving_sessions WHERE id=:id"), {"id": session_id}
                )
                is None
            ):
                raise HTTPException(404, "session not found")
        content = await file.read(10_000_001)
        try:
            _, columns = inspect_csv(content)
            if mapping is None and set(columns) != {
                "timestamp",
                "signal",
                "value",
                "unit",
                "record_id",
                "sequence",
            }:
                return CSVImportPreview(
                    columns=columns,
                    unmapped_columns=columns,
                    requires_mapping=True,
                    warnings=[
                        "Choose explicit timestamp, canonical signal and source-unit mappings; unmapped columns are not imported"
                    ],
                )
            parsed = CSVColumnMapping.model_validate_json(mapping) if mapping is not None else None
            source = (
                MappedCSVTelemetrySource(content, parsed) if parsed else CSVTelemetrySource(content)
            )
            preview = CSVImportPreview(
                columns=columns,
                requires_mapping=False,
                mapping=parsed,
                mapping_hash=parsed.configuration_hash if parsed else None,
                unmapped_columns=source.unmapped_columns
                if isinstance(source, MappedCSVTelemetrySource)
                else [],
            )
            async for record in source.read():
                if len(preview.preview_points) + len(preview.warnings) >= 25:
                    preview.preview_truncated = True
                    break
                definition = SIGNAL_BY_ALIAS.get(record.signal.lower())
                if definition is None:
                    preview.warnings.append(
                        "Unsupported signal in preview; choose a verified canonical mapping"
                    )
                    continue
                value, quality = normalize_value(record.value, record.unit, definition)
                preview.preview_points.append(
                    CSVPreviewPoint(
                        observed_at=record.observed_at,
                        raw_signal=record.raw_signal or record.signal,
                        signal=definition.key,
                        value=value,
                        unit=definition.unit,
                        quality=quality.value,
                    )
                )
            return preview
        except ValueError as exc:
            raise HTTPException(400, "Invalid CSV or explicit column mapping") from exc

    @routes.get("/api/v1/signals", response_model=list[Signal], operation_id="list_signals")
    async def list_signals() -> list[Signal]:
        return [
            Signal(
                key=s.key,
                name=s.name,
                category=s.category,
                unit=s.unit,
                minimum=s.minimum,
                maximum=s.maximum,
                aliases=list(s.aliases),
            )
            for s in SIGNALS
        ]

    def recipe_response(recipe: LoggingRecipe) -> LoggingRecipeResponse:
        values = asdict(recipe)
        values["configuration_hash"] = recipe.configuration_hash
        return LoggingRecipeResponse.model_validate(values)

    @routes.get(
        "/api/v1/logging/objectives",
        response_model=list[ObjectiveResponse],
        operation_id="list_logging_objectives",
    )
    async def list_logging_objectives() -> list[ObjectiveResponse]:
        return [ObjectiveResponse(key=item.objective, recipe_key=item.key) for item in RECIPES]

    @routes.get(
        "/api/v1/logging/recipes",
        response_model=list[LoggingRecipeResponse],
        operation_id="list_logging_recipes",
    )
    async def list_logging_recipes() -> list[LoggingRecipeResponse]:
        return [recipe_response(item) for item in RECIPES]

    @routes.get(
        "/api/v1/logging/recipes/{recipe_key}",
        response_model=LoggingRecipeResponse,
        operation_id="get_logging_recipe",
        responses={404: {"model": ErrorResponse}},
    )
    async def get_logging_recipe(recipe_key: str) -> LoggingRecipeResponse:
        recipe = BY_KEY.get(recipe_key)
        if recipe is None:
            raise HTTPException(404, "logging recipe not found")
        return recipe_response(recipe)

    @routes.post(
        "/api/v1/logging/recipes/{recipe_key}/preflight",
        response_model=PreflightResponse,
        operation_id="preflight_logging_recipe",
        responses={404: {"model": ErrorResponse}},
    )
    async def preflight_logging_recipe(
        recipe_key: str, payload: PreflightRequest
    ) -> PreflightResponse:
        recipe = BY_KEY.get(recipe_key)
        if recipe is None:
            raise HTTPException(404, "logging recipe not found")
        capabilities = DeviceCapabilities(
            payload.adapter,
            {key: Support(value) for key, value in payload.signals.items()},
            payload.maximum_requests_per_second,
            payload.discovery_supported,
        )
        return PreflightResponse.model_validate(asdict(preflight(recipe, capabilities)))

    def bearer(value: str | None) -> str:
        if value is None or not value.startswith("Bearer ") or len(value) > 256:
            raise HTTPException(401, "valid bearer acquisition credential required")
        return value.removeprefix("Bearer ")

    @routes.post(
        "/api/v1/acquisitions",
        response_model=AcquisitionCreated,
        status_code=201,
        operation_id="create_acquisition",
        responses={422: {"model": ErrorResponse}},
    )
    async def create_acquisition(
        payload: AcquisitionCreate, request: Request
    ) -> AcquisitionCreated:
        try:
            return await AcquisitionService(
                store(),
                settings,
                request.app.state.telemetry,
                request.app.state.acquisition_publisher,
            ).create(payload)
        except AcquisitionError as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.post(
        "/api/v1/acquisitions/{acquisition_id}/heartbeat",
        response_model=AcquisitionStatusResponse,
        operation_id="report_acquisition_heartbeat",
        responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def report_acquisition_heartbeat(
        acquisition_id: UUID,
        payload: AcquisitionHeartbeat,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> AcquisitionStatusResponse:
        try:
            return await AcquisitionService(
                store(), settings, request.app.state.telemetry
            ).heartbeat(acquisition_id, bearer(authorization), payload)
        except AcquisitionAuthError as exc:
            raise HTTPException(401, "invalid, expired, or closed acquisition credential") from exc
        except AcquisitionError as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.post(
        "/api/v1/acquisitions/{acquisition_id}/batches",
        response_model=AcquisitionBatchAccepted,
        status_code=202,
        operation_id="publish_acquisition_batch",
        responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def publish_acquisition_batch(
        acquisition_id: UUID,
        payload: AcquisitionBatch,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> AcquisitionBatchAccepted:
        try:
            return await AcquisitionService(
                store(),
                settings,
                request.app.state.telemetry,
                request.app.state.acquisition_publisher,
            ).publish(acquisition_id, bearer(authorization), payload)
        except AcquisitionAuthError as exc:
            raise HTTPException(401, "invalid, expired, or closed acquisition credential") from exc
        except AcquisitionError as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.post(
        "/api/v1/acquisitions/{acquisition_id}/synthetic",
        status_code=202,
        operation_id="start_synthetic_acquisition",
        responses={401: {"model": ErrorResponse}},
    )
    async def start_synthetic_acquisition(
        acquisition_id: UUID,
        background: BackgroundTasks,
        request: Request,
        scenario: Literal["boost_drop", "missing_recommended"] = Query("boost_drop"),
        authorization: str | None = Header(default=None),
    ) -> dict[str, str]:
        token = bearer(authorization)
        service = AcquisitionService(
            store(), settings, request.app.state.telemetry, request.app.state.acquisition_publisher
        )
        try:
            await service._authorized(acquisition_id, token)
        except AcquisitionAuthError as exc:
            raise HTTPException(401, "invalid, expired, or closed acquisition credential") from exc
        background.add_task(service.run_synthetic, acquisition_id, token, scenario)
        return {"status": "started", "provisional": "true"}

    @routes.get(
        "/api/v1/acquisitions/{acquisition_id}",
        response_model=AcquisitionStatusResponse,
        operation_id="get_acquisition",
        responses={404: {"model": ErrorResponse}},
    )
    async def get_acquisition(acquisition_id: UUID, request: Request) -> AcquisitionStatusResponse:
        try:
            return await AcquisitionService(
                store(),
                settings,
                request.app.state.telemetry,
                request.app.state.acquisition_publisher,
            ).status(acquisition_id)
        except LookupError as exc:
            raise HTTPException(404, "acquisition not found") from exc

    @routes.get(
        "/api/v1/acquisitions/{acquisition_id}/live",
        operation_id="stream_acquisition_live",
        response_model=AcquisitionLiveSnapshot,
        response_class=StreamingResponse,
        responses={
            200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}},
            404: {"model": ErrorResponse},
        },
    )
    async def stream_acquisition_live(acquisition_id: UUID) -> StreamingResponse:
        async with store().session() as db:
            exists = await db.scalar(
                text("SELECT 1 FROM acquisition_sessions WHERE id=:id"),
                {"id": acquisition_id},
            )
        if exists is None:
            raise HTTPException(404, "acquisition not found")

        async def events() -> AsyncIterator[str]:
            for _ in range(600):
                async with store().session() as db:
                    state = (
                        (
                            await db.execute(
                                text("SELECT state,quality FROM acquisition_sessions WHERE id=:id"),
                                {"id": acquisition_id},
                            )
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if state is None:
                        yield 'event: error\ndata: {"code":"not_found"}\n\n'
                        return
                    points = (
                        (
                            await db.execute(
                                text(
                                    """SELECT signal_key,numeric_value,normalized_unit,observed_at FROM telemetry_samples WHERE session_id=(SELECT driving_session_id FROM acquisition_sessions WHERE id=:id) AND observed_at>=(SELECT max(observed_at)-interval '60 seconds' FROM telemetry_samples WHERE session_id=(SELECT driving_session_id FROM acquisition_sessions WHERE id=:id)) ORDER BY observed_at DESC,signal_key,sample_id LIMIT 2000"""
                                ),
                                {"id": acquisition_id},
                            )
                        )
                        .mappings()
                        .all()
                    )
                    findings = (
                        (
                            await db.execute(
                                text(
                                    """SELECT id,finding_type,category,started_at,ended_at,evidence,status AS reconciliation_status,canonical_reference FROM provisional_findings WHERE acquisition_session_id=:id ORDER BY started_at DESC LIMIT 20"""
                                ),
                                {"id": acquisition_id},
                            )
                        )
                        .mappings()
                        .all()
                    )
                payload = {
                    "schema_version": "1.0",
                    "state": state["state"],
                    "quality": state["quality"]
                    | {"collector_health": collector_health(state["quality"], datetime.now(UTC))},
                    "provisional": True,
                    "window_seconds": 60,
                    "points": [
                        {
                            "signal": row["signal_key"],
                            "value": row["numeric_value"],
                            "unit": row["normalized_unit"],
                            "observed_at": row["observed_at"].isoformat(),
                        }
                        for row in reversed(points)
                    ],
                    "findings": [
                        {
                            **dict(row),
                            "id": str(row["id"]),
                            "canonical_reference": str(row["canonical_reference"])
                            if row["canonical_reference"]
                            else None,
                            "started_at": row["started_at"].isoformat(),
                            "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
                        }
                        for row in reversed(findings)
                    ],
                }
                snapshot = AcquisitionLiveSnapshot.model_validate(payload)
                yield f"event: telemetry\ndata: {snapshot.model_dump_json(exclude_none=True)}\n\n"
                if state["state"] in {"completed", "failed"}:
                    return
                await asyncio.sleep(1)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @routes.get(
        "/api/v1/acquisitions/{acquisition_id}/findings",
        response_model=list[ProvisionalFindingResponse],
        operation_id="list_acquisition_findings",
        responses={404: {"model": ErrorResponse}},
    )
    async def list_acquisition_findings(
        acquisition_id: UUID,
    ) -> list[ProvisionalFindingResponse]:
        async with store().session() as db:
            exists = await db.scalar(
                text("SELECT 1 FROM acquisition_sessions WHERE id=:id"),
                {"id": acquisition_id},
            )
            if exists is None:
                raise HTTPException(404, "acquisition not found")
            rows = (
                (
                    await db.execute(
                        text(
                            """SELECT id,finding_type,category,started_at,ended_at,evidence,status AS reconciliation_status,canonical_reference FROM provisional_findings WHERE acquisition_session_id=:id ORDER BY started_at,id LIMIT 500"""
                        ),
                        {"id": acquisition_id},
                    )
                )
                .mappings()
                .all()
            )
        return [ProvisionalFindingResponse.model_validate(row) for row in rows]

    @routes.post(
        "/api/v1/acquisitions/{acquisition_id}/stop",
        response_model=AcquisitionStatusResponse,
        operation_id="stop_acquisition",
        responses={401: {"model": ErrorResponse}},
    )
    async def stop_acquisition(
        acquisition_id: UUID, request: Request, authorization: str | None = Header(default=None)
    ) -> AcquisitionStatusResponse:
        try:
            return await AcquisitionService(
                store(),
                settings,
                request.app.state.telemetry,
                request.app.state.acquisition_publisher,
            ).stop(acquisition_id, bearer(authorization))
        except AcquisitionAuthError as exc:
            raise HTTPException(401, "invalid, expired, or closed acquisition credential") from exc

    @routes.post(
        "/api/v1/acquisitions/{acquisition_id}/finalize",
        response_model=AcquisitionFinalized,
        operation_id="finalize_acquisition",
        responses={409: {"model": ErrorResponse}},
    )
    async def finalize_acquisition(acquisition_id: UUID, request: Request) -> AcquisitionFinalized:
        try:
            return await AcquisitionService(
                store(), settings, request.app.state.telemetry
            ).finalize(acquisition_id)
        except AcquisitionError as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.get(
        "/api/v1/sessions/{session_id}/telemetry",
        response_model=TelemetryWindow,
        operation_id="query_telemetry",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def query_telemetry(
        session_id: UUID,
        signal: list[str] = Query(min_length=1),
        start: AwareDatetime | None = None,
        end: AwareDatetime | None = None,
        limit: int = Query(2000, ge=1, le=10000),
    ) -> TelemetryWindow:
        unknown = set(signal) - {item.key for item in SIGNALS}
        if unknown:
            raise HTTPException(422, "unknown canonical signal")
        try:
            return await QueryService(store(), telemetry).query(
                session_id, signal, start, end, limit
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, "session not found") from exc

    @routes.get(
        "/api/v1/sessions/{session_id}/capabilities",
        response_model=DatasetCapabilityReport,
        operation_id="assess_session_capabilities",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def assess_session_capabilities(
        session_id: UUID, request: Request, recipe_key: str = Query("general-health")
    ) -> DatasetCapabilityReport:
        try:
            report = await AcquisitionService(
                store(), settings, request.app.state.telemetry
            ).capability_report(session_id, recipe_key)
            return DatasetCapabilityReport.model_validate(report)
        except LookupError as exc:
            raise HTTPException(404, "session not found") from exc
        except AcquisitionError as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.post(
        "/api/v1/sessions/{session_id}/analysis",
        response_model=AnalysisResult,
        operation_id="analyze_session",
        responses={404: {"model": ErrorResponse}, 413: {"model": ErrorResponse}},
    )
    async def analyze_session(session_id: UUID, payload: AnalysisRequest) -> AnalysisResult:
        try:
            return await SessionAnalysisService(store(), telemetry).run(
                session_id, payload.profile, payload.replace
            )
        except LookupError as exc:
            raise HTTPException(404, "session not found") from exc
        except AnalysisLimitError as exc:
            raise HTTPException(413, str(exc)) from exc

    @routes.get(
        "/api/v1/sessions/{session_id}/segments",
        response_model=list[SessionSegment],
        operation_id="list_session_segments",
    )
    async def list_session_segments(
        session_id: UUID,
        segment_type: str | None = Query(
            default=None, pattern="^(idle|warm_up|cruise|acceleration|pull|deceleration|unknown)$"
        ),
        limit: int = Query(200, ge=1, le=500),
    ) -> list[SessionSegment]:
        return await SessionAnalysisService(store()).segments(session_id, segment_type, limit)

    @routes.get(
        "/api/v1/sessions/{session_id}/pulls",
        response_model=list[Pull],
        operation_id="list_session_pulls",
    )
    async def list_session_pulls(
        session_id: UUID, limit: int = Query(100, ge=1, le=200)
    ) -> list[Pull]:
        return await SessionAnalysisService(store()).pulls(session_id, None, limit)

    @routes.get("/api/v1/pulls", response_model=list[Pull], operation_id="list_pulls")
    async def list_pulls(
        vehicle_id: UUID,
        limit: int = Query(100, ge=1, le=200),
        configuration_id: UUID | None = None,
    ) -> list[Pull]:
        return await SessionAnalysisService(store()).pulls(
            None, vehicle_id, limit, configuration_id
        )

    @routes.get(
        "/api/v1/pulls/{pull_id}",
        response_model=Pull,
        operation_id="get_pull",
        responses={404: {"model": ErrorResponse}},
    )
    async def get_pull(pull_id: UUID) -> Pull:
        result = await SessionAnalysisService(store()).pull(pull_id)
        if result is None:
            raise HTTPException(404, "pull not found")
        return result

    @routes.post(
        "/api/v1/sessions/{session_id}/events/analyze",
        response_model=EventAnalysisResult,
        operation_id="analyze_session_events",
        responses={404: {"model": ErrorResponse}, 413: {"model": ErrorResponse}},
    )
    async def analyze_session_events(
        session_id: UUID, payload: EventAnalysisRequest, request: Request
    ) -> EventAnalysisResult:
        try:
            return await EventAnalysisService(store(), request.app.state.telemetry).run(
                session_id, payload.replace
            )
        except LookupError as exc:
            raise HTTPException(404, "session not found") from exc
        except EventAnalysisLimitError as exc:
            raise HTTPException(413, str(exc)) from exc

    @routes.get(
        "/api/v1/sessions/{session_id}/events",
        response_model=list[DetectedEvent],
        operation_id="list_session_events",
    )
    async def list_session_events(
        session_id: UUID,
        event_type: str | None = Query(default=None, max_length=80),
        category: str | None = Query(
            default=None,
            pattern="^(performance|thermal|fuel|ignition|combustion|mixture|sensor|telemetry_quality|control_behavior)$",
        ),
        severity: str | None = Query(default=None, pattern="^(info|low|moderate|high)$"),
        pull_id: UUID | None = None,
        start: AwareDatetime | None = None,
        end: AwareDatetime | None = None,
        limit: int = Query(100, ge=1, le=500),
    ) -> list[DetectedEvent]:
        if start and end and start >= end:
            raise HTTPException(422, "start must precede end")
        return await EventAnalysisService(store()).events(
            session_id, None, event_type, category, severity, pull_id, start, end, limit
        )

    @routes.get(
        "/api/v1/sessions/{session_id}/events/summary",
        response_model=EventSummary,
        operation_id="summarize_session_events",
    )
    async def summarize_session_events(session_id: UUID) -> EventSummary:
        return await EventAnalysisService(store()).summary(session_id)

    @routes.get(
        "/api/v1/events", response_model=list[DetectedEvent], operation_id="list_vehicle_events"
    )
    async def list_vehicle_events(
        vehicle_id: UUID,
        event_type: str | None = Query(default=None, max_length=80),
        limit: int = Query(100, ge=1, le=500),
    ) -> list[DetectedEvent]:
        return await EventAnalysisService(store()).events(
            None, vehicle_id, event_type, None, None, None, None, None, limit
        )

    @routes.get(
        "/api/v1/events/{event_id}",
        response_model=DetectedEvent,
        operation_id="get_event",
        responses={404: {"model": ErrorResponse}},
    )
    async def get_event(event_id: UUID) -> DetectedEvent:
        result = await EventAnalysisService(store()).event(event_id)
        if result is None:
            raise HTTPException(404, "event not found")
        return result

    def analytics_config(payload: AnalyticsRequest) -> AnalyticsConfig:
        return AnalyticsConfig(
            rpm_bin_size=payload.rpm_bin_size,
            minimum_bin_samples=payload.minimum_bin_samples,
            maximum_gap_seconds=payload.maximum_gap_seconds,
            speed_intervals_kmh=tuple(payload.speed_intervals_kmh),
        )

    @routes.post(
        "/api/v1/pulls/{pull_id}/analytics",
        response_model=AnalyticsResultResponse,
        operation_id="get_pull_analytics",
        responses={404: {"model": ErrorResponse}},
    )
    async def get_pull_analytics(
        pull_id: UUID, payload: AnalyticsRequest
    ) -> AnalyticsResultResponse:
        try:
            return await AnalyticsService(store(), telemetry).pull(
                pull_id, analytics_config(payload), payload.recompute
            )
        except LookupError as exc:
            raise HTTPException(404, "pull not found") from exc

    @routes.post(
        "/api/v1/analytics/pulls/compare",
        response_model=AnalyticsResultResponse,
        operation_id="compare_pull_analytics",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def compare_pull_analytics(payload: AnalyticsRequest) -> AnalyticsResultResponse:
        try:
            return await AnalyticsService(store(), telemetry).comparison(
                payload.pull_ids, analytics_config(payload), payload.recompute
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, "pull not found") from exc

    @routes.post(
        "/api/v1/analytics/pulls/repeated",
        response_model=AnalyticsResultResponse,
        operation_id="analyze_repeated_pulls",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def analyze_repeated_pulls(payload: AnalyticsRequest) -> AnalyticsResultResponse:
        try:
            return await AnalyticsService(store(), telemetry).repeated(
                payload.pull_ids, analytics_config(payload), payload.recompute
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, "analytics source not found") from exc

    @routes.post(
        "/api/v1/sessions/{session_id}/analytics",
        response_model=AnalyticsResultResponse,
        operation_id="get_session_analytics",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def get_session_analytics(
        session_id: UUID, payload: AnalyticsRequest
    ) -> AnalyticsResultResponse:
        try:
            return await AnalyticsService(store(), telemetry).session(
                session_id, analytics_config(payload), payload.recompute
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, "analytics source not found") from exc

    @routes.post(
        "/api/v1/analytics/sessions/compare",
        response_model=AnalyticsResultResponse,
        operation_id="compare_sessions",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def compare_sessions(
        payload: AnalyticsRequest, session_ids: list[UUID] = Query(max_length=10)
    ) -> AnalyticsResultResponse:
        try:
            return await AnalyticsService(store(), telemetry).cross_sessions(
                session_ids, analytics_config(payload), payload.recompute
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, "analytics source not found") from exc

    @routes.post(
        "/api/v1/vehicles/{vehicle_id}/configurations/{configuration_id}/baseline",
        response_model=AnalyticsResultResponse,
        operation_id="build_vehicle_baseline",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def build_vehicle_baseline(
        vehicle_id: UUID, configuration_id: UUID, payload: AnalyticsRequest
    ) -> AnalyticsResultResponse:
        try:
            return await AnalyticsService(store(), telemetry).vehicle_baseline(
                vehicle_id, configuration_id, analytics_config(payload), payload.recompute
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, "analytics source not found") from exc

    @routes.post(
        "/api/v1/vehicles/{vehicle_id}/trends/{metric}",
        response_model=AnalyticsResultResponse,
        operation_id="get_vehicle_trends",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def get_vehicle_trends(
        vehicle_id: UUID, metric: str, payload: AnalyticsRequest
    ) -> AnalyticsResultResponse:
        try:
            return await AnalyticsService(store(), telemetry).trends(
                vehicle_id, metric, analytics_config(payload)
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, "analytics source not found") from exc

    @routes.post(
        "/api/v1/analytics/configurations/compare",
        response_model=AnalyticsResultResponse,
        operation_id="compare_configurations",
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def compare_configurations(
        payload: AnalyticsRequest, after_pull_ids: list[UUID] = Query(max_length=20)
    ) -> AnalyticsResultResponse:
        try:
            return await AnalyticsService(store(), telemetry).modifications(
                payload.pull_ids, after_pull_ids, analytics_config(payload)
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, "analytics source not found") from exc

    return routes
