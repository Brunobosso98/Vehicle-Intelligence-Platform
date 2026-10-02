import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from vehicle_platform.analysis.alignment import align_observations
from vehicle_platform.analysis.domain import DetectorProfile, Observation
from vehicle_platform.api.domain_contracts import DetectedEvent, EventAnalysisResult
from vehicle_platform.events.domain import EventProfile, PullWindow
from vehicle_platform.events.engine import EventEngine
from vehicle_platform.infrastructure.database import Database

MAX_EVENT_OBSERVATIONS = 500_000


class EventAnalysisLimitError(ValueError):
    pass


class EventAnalysisService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def run(self, session_id: UUID, replace: bool) -> EventAnalysisResult:
        profile, engine = EventProfile(), EventEngine()
        async with self.database.session() as db:
            session = (
                (
                    await db.execute(
                        text("SELECT vehicle_id FROM driving_sessions WHERE id=:id"),
                        {"id": session_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if session is None:
                raise LookupError("session not found")
            existing = (
                (
                    await db.execute(
                        text(
                            "SELECT id,event_count FROM event_analysis_runs WHERE session_id=:id AND profile=:profile AND configuration_hash=:hash AND status='completed' ORDER BY finished_at DESC LIMIT 1"
                        ),
                        {
                            "id": session_id,
                            "profile": profile.name,
                            "hash": profile.configuration_hash,
                        },
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing and not replace:
                return EventAnalysisResult(
                    session_id=session_id,
                    analysis_run_id=existing["id"],
                    profile=profile.name,
                    configuration_hash=profile.configuration_hash,
                    event_count=existing["event_count"],
                    reused=True,
                )
            rows = (
                await db.execute(
                    text(
                        "SELECT observed_at,signal_key,numeric_value,sample_id FROM telemetry_samples WHERE session_id=:id AND quality IN ('valid','out_of_range') ORDER BY observed_at,signal_key,sample_id LIMIT :limit"
                    ),
                    {"id": session_id, "limit": MAX_EVENT_OBSERVATIONS + 1},
                )
            ).all()
            if len(rows) > MAX_EVENT_OBSERVATIONS:
                raise EventAnalysisLimitError(
                    "session exceeds 500000 observation event-analysis limit"
                )
            frames = align_observations(
                [
                    Observation(r.observed_at, r.signal_key, r.numeric_value, r.sample_id)
                    for r in rows
                ],
                DetectorProfile(),
            )
            pull_rows = (
                (
                    await db.execute(
                        text(
                            "SELECT id,started_at,ended_at FROM pulls WHERE session_id=:id ORDER BY started_at,id LIMIT 200"
                        ),
                        {"id": session_id},
                    )
                )
                .mappings()
                .all()
            )
            pulls = [
                PullWindow(
                    row["started_at"],
                    row["ended_at"],
                    tuple(
                        f for f in frames if row["started_at"] <= f.observed_at <= row["ended_at"]
                    ),
                    str(row["id"]),
                )
                for row in pull_rows
            ]
            events, results = engine.analyze(frames, pulls)
            if replace:
                await db.execute(
                    text(
                        "DELETE FROM detected_events WHERE session_id=:id AND configuration_hash=:hash"
                    ),
                    {"id": session_id, "hash": profile.configuration_hash},
                )
            run: UUID = (
                await db.execute(
                    text(
                        "INSERT INTO event_analysis_runs(session_id,profile,configuration_hash,status,detector_states,event_count,warnings,finished_at) VALUES(:id,:profile,:hash,'completed',CAST(:states AS jsonb),:count,:warnings,now()) RETURNING id"
                    ),
                    {
                        "id": session_id,
                        "profile": profile.name,
                        "hash": profile.configuration_hash,
                        "states": json.dumps({r.detector: r.state.value for r in results}),
                        "count": len(events),
                        "warnings": [w for result in results for w in result.warnings],
                    },
                )
            ).scalar_one()
            for event in events:
                pull_id = (
                    pull_rows[event.pull_index]["id"]
                    if event.pull_index is not None and event.pull_index < len(pull_rows)
                    else None
                )
                values = {
                    "vehicle_id": session["vehicle_id"],
                    "session_id": session_id,
                    "pull_id": pull_id,
                    "run": run,
                    "event_type": event.event_type,
                    "category": event.category.value,
                    "started_at": event.started_at,
                    "ended_at": event.ended_at,
                    "duration_ms": int((event.ended_at - event.started_at).total_seconds() * 1000),
                    "severity": event.severity.value,
                    "confidence": event.confidence,
                    "algorithm_name": event.algorithm_name,
                    "algorithm_version": event.algorithm_version,
                    "configuration_hash": event.configuration_hash,
                    "baseline_type": event.baseline_type.value,
                    "baseline_reference": json.dumps(event.baseline_reference),
                    "evidence": json.dumps(event.evidence),
                    "quality_flags": list(event.quality_flags),
                }
                await db.execute(
                    text(
                        """INSERT INTO detected_events(vehicle_id,session_id,pull_id,analysis_run_id,event_type,category,started_at,ended_at,duration_ms,severity,confidence,algorithm_name,algorithm_version,configuration_hash,baseline_type,baseline_reference,evidence,quality_flags) VALUES(:vehicle_id,:session_id,:pull_id,:run,:event_type,:category,:started_at,:ended_at,:duration_ms,:severity,:confidence,:algorithm_name,:algorithm_version,:configuration_hash,:baseline_type,CAST(:baseline_reference AS jsonb),CAST(:evidence AS jsonb),:quality_flags) ON CONFLICT ON CONSTRAINT uq_detected_event_identity DO NOTHING"""
                    ),
                    values,
                )
            await db.commit()
        return EventAnalysisResult(
            session_id=session_id,
            analysis_run_id=run,
            profile=profile.name,
            configuration_hash=profile.configuration_hash,
            event_count=len(events),
            reused=False,
        )

    async def events(
        self,
        session_id: UUID | None,
        vehicle_id: UUID | None,
        event_type: str | None,
        category: str | None,
        severity: str | None,
        pull_id: UUID | None,
        start: datetime | None,
        end: datetime | None,
        limit: int,
    ) -> list[DetectedEvent]:
        conditions: list[str] = []
        values: dict[str, object] = {"limit": limit}
        for column, value in (
            ("session_id", session_id),
            ("vehicle_id", vehicle_id),
            ("event_type", event_type),
            ("category", category),
            ("severity", severity),
            ("pull_id", pull_id),
        ):
            if value is not None:
                conditions.append(f"{column}=:{column}")
                values[column] = value
        if start:
            conditions.append("ended_at>=:start")
            values["start"] = start
        if end:
            conditions.append("started_at<:end")
            values["end"] = end
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        async with self.database.session() as db:
            rows = (
                await db.execute(
                    text(
                        f"SELECT * FROM detected_events{where} ORDER BY started_at,id LIMIT :limit"
                    ),
                    values,
                )
            ).mappings()
            return [DetectedEvent.model_validate(row) for row in rows]

    async def event(self, event_id: UUID) -> DetectedEvent | None:
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text("SELECT * FROM detected_events WHERE id=:id"), {"id": event_id}
                    )
                )
                .mappings()
                .one_or_none()
            )
            return DetectedEvent.model_validate(row) if row else None
