from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import text

from vehicle_platform.analysis.service import AnalysisLimitError, SessionAnalysisService
from vehicle_platform.api.contracts import ErrorResponse, Health, Ready, Version
from vehicle_platform.api.domain_contracts import (
    AnalysisRequest,
    AnalysisResult,
    ConfigurationCreate,
    DetectedEvent,
    DrivingSession,
    EventAnalysisRequest,
    EventAnalysisResult,
    ImportResult,
    Modification,
    ModificationCreate,
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
from vehicle_platform.telemetry.domain import SIGNALS
from vehicle_platform.telemetry.service import IngestionService, QueryService
from vehicle_platform.telemetry.sources import CSVTelemetrySource


def router(settings: Settings, database: DatabaseProbe) -> APIRouter:
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

    @routes.get("/api/v1/vehicles/{vehicle_id}", response_model=Vehicle, operation_id="get_vehicle")
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
        "/api/v1/vehicles/{vehicle_id}", response_model=Vehicle, operation_id="update_vehicle"
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
    )
    async def create_modification(vehicle_id: UUID, payload: ModificationCreate) -> Modification:
        async with store().session() as db:
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
    )
    async def create_session(payload: SessionCreate) -> DrivingSession:
        values = payload.model_dump()
        values["metadata"] = __import__("json").dumps(values["metadata"])
        async with store().session() as db:
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
        "/api/v1/sessions/{session_id}", response_model=DrivingSession, operation_id="get_session"
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
    )
    async def import_csv(session_id: UUID, file: UploadFile = File(...)) -> ImportResult:
        if file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
            raise HTTPException(415, "CSV content type required")
        content = await file.read(10_000_001)
        try:
            source = CSVTelemetrySource(content)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return await IngestionService(store()).ingest(session_id, "csv", source)

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

    @routes.get(
        "/api/v1/sessions/{session_id}/telemetry",
        response_model=TelemetryWindow,
        operation_id="query_telemetry",
    )
    async def query_telemetry(
        session_id: UUID,
        signal: list[str] = Query(min_length=1),
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = Query(2000, ge=1, le=10000),
    ) -> TelemetryWindow:
        unknown = set(signal) - {item.key for item in SIGNALS}
        if unknown:
            raise HTTPException(422, "unknown canonical signal")
        try:
            return await QueryService(store()).query(session_id, signal, start, end, limit)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.post(
        "/api/v1/sessions/{session_id}/analysis",
        response_model=AnalysisResult,
        operation_id="analyze_session",
    )
    async def analyze_session(session_id: UUID, payload: AnalysisRequest) -> AnalysisResult:
        try:
            return await SessionAnalysisService(store()).run(
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
    async def list_pulls(vehicle_id: UUID, limit: int = Query(100, ge=1, le=200)) -> list[Pull]:
        return await SessionAnalysisService(store()).pulls(None, vehicle_id, limit)

    @routes.get("/api/v1/pulls/{pull_id}", response_model=Pull, operation_id="get_pull")
    async def get_pull(pull_id: UUID) -> Pull:
        result = await SessionAnalysisService(store()).pull(pull_id)
        if result is None:
            raise HTTPException(404, "pull not found")
        return result

    @routes.post(
        "/api/v1/sessions/{session_id}/events/analyze",
        response_model=EventAnalysisResult,
        operation_id="analyze_session_events",
    )
    async def analyze_session_events(
        session_id: UUID, payload: EventAnalysisRequest
    ) -> EventAnalysisResult:
        try:
            return await EventAnalysisService(store()).run(session_id, payload.replace)
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
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = Query(100, ge=1, le=500),
    ) -> list[DetectedEvent]:
        return await EventAnalysisService(store()).events(
            session_id, None, event_type, category, severity, pull_id, start, end, limit
        )

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

    @routes.get("/api/v1/events/{event_id}", response_model=DetectedEvent, operation_id="get_event")
    async def get_event(event_id: UUID) -> DetectedEvent:
        result = await EventAnalysisService(store()).event(event_id)
        if result is None:
            raise HTTPException(404, "event not found")
        return result

    return routes
