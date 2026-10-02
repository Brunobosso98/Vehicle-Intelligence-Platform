import json
from dataclasses import asdict
from uuid import UUID

from sqlalchemy import text

from vehicle_platform.analysis.alignment import align_observations
from vehicle_platform.analysis.detectors import HeuristicPullDetector, HeuristicSegmentDetector
from vehicle_platform.analysis.domain import N55_REFERENCE_PROFILE, DetectorProfile, Observation
from vehicle_platform.api.domain_contracts import AnalysisResult, Pull, SessionSegment
from vehicle_platform.infrastructure.database import Database

MAX_ANALYSIS_POINTS = 500_000
PROFILES = {"generic-v1": DetectorProfile(), N55_REFERENCE_PROFILE.name: N55_REFERENCE_PROFILE}


class AnalysisLimitError(ValueError):
    pass


class SessionAnalysisService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def run(self, session_id: UUID, profile_name: str, replace: bool) -> AnalysisResult:
        profile = PROFILES[profile_name]
        segmenter, pull_detector = HeuristicSegmentDetector(profile), HeuristicPullDetector(profile)
        async with self.database.session() as db:
            session = (
                (
                    await db.execute(
                        text(
                            "SELECT vehicle_id,configuration_id FROM driving_sessions WHERE id=:id"
                        ),
                        {"id": session_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if session is None:
                raise LookupError("session not found")
            existing: int = (
                await db.execute(
                    text(
                        "SELECT count(*) FROM session_segments WHERE session_id=:id AND detector_name=:name AND algorithm_version=:version AND configuration_hash=:hash"
                    ),
                    {
                        "id": session_id,
                        "name": profile.name,
                        "version": segmenter.algorithm_version,
                        "hash": profile.configuration_hash,
                    },
                )
            ).scalar_one()
            if existing and not replace:
                existing_pulls: int = (
                    await db.execute(
                        text(
                            "SELECT count(*) FROM pulls WHERE session_id=:id AND detector_name=:name AND configuration_hash=:hash"
                        ),
                        {
                            "id": session_id,
                            "name": profile.name,
                            "hash": profile.configuration_hash,
                        },
                    )
                ).scalar_one()
                return AnalysisResult(
                    session_id=session_id,
                    profile=profile.name,
                    algorithm_version=segmenter.algorithm_version,
                    configuration_hash=profile.configuration_hash,
                    segment_count=existing,
                    pull_count=existing_pulls,
                    reused=True,
                )
            rows = (
                await db.execute(
                    text(
                        "SELECT observed_at,signal_key,numeric_value,sample_id FROM telemetry_samples WHERE session_id=:id AND quality IN ('valid','out_of_range') ORDER BY observed_at,signal_key,sample_id LIMIT :limit"
                    ),
                    {"id": session_id, "limit": MAX_ANALYSIS_POINTS + 1},
                )
            ).all()
            if len(rows) > MAX_ANALYSIS_POINTS:
                raise AnalysisLimitError("session exceeds 500000 observation analysis limit")
            observations = [
                Observation(row.observed_at, row.signal_key, row.numeric_value, row.sample_id)
                for row in rows
            ]
            frames = align_observations(observations, profile)
            segments, pulls = segmenter.detect(frames), pull_detector.detect(frames)
            if replace:
                await db.execute(
                    text(
                        "DELETE FROM pulls WHERE session_id=:id AND detector_name=:name AND algorithm_version=:version AND configuration_hash=:hash"
                    ),
                    {
                        "id": session_id,
                        "name": profile.name,
                        "version": pull_detector.algorithm_version,
                        "hash": profile.configuration_hash,
                    },
                )
                await db.execute(
                    text(
                        "DELETE FROM session_segments WHERE session_id=:id AND detector_name=:name AND algorithm_version=:version AND configuration_hash=:hash"
                    ),
                    {
                        "id": session_id,
                        "name": profile.name,
                        "version": segmenter.algorithm_version,
                        "hash": profile.configuration_hash,
                    },
                )
            for segment in segments:
                await db.execute(
                    text(
                        """INSERT INTO session_segments(session_id,segment_type,started_at,ended_at,duration_ms,confidence,detector_name,algorithm_version,configuration_hash,quality_flags,metadata) VALUES(:session_id,:segment_type,:started_at,:ended_at,:duration_ms,:confidence,:detector_name,:algorithm_version,:configuration_hash,:quality_flags,CAST(:metadata AS jsonb)) ON CONFLICT ON CONSTRAINT uq_segment_analysis_identity DO NOTHING"""
                    ),
                    {
                        "session_id": session_id,
                        "segment_type": segment.segment_type.value,
                        "started_at": segment.started_at,
                        "ended_at": segment.ended_at,
                        "duration_ms": int(
                            (segment.ended_at - segment.started_at).total_seconds() * 1000
                        ),
                        "confidence": segment.confidence,
                        "detector_name": profile.name,
                        "algorithm_version": segmenter.algorithm_version,
                        "configuration_hash": profile.configuration_hash,
                        "quality_flags": list(segment.quality_flags),
                        "metadata": json.dumps(segment.evidence),
                    },
                )
            for pull in pulls:
                metrics = asdict(pull.metrics)
                metrics.pop("available_signals")
                metadata = {
                    "evidence": pull.evidence,
                    "available_signals": list(pull.metrics.available_signals),
                    "boundary_semantics": "[started_at, ended_at)",
                }
                await db.execute(
                    text(
                        """INSERT INTO pulls(session_id,vehicle_id,configuration_id,started_at,ended_at,duration_ms,confidence,detector_name,algorithm_version,configuration_hash,quality_flags,metadata,start_rpm,end_rpm,min_rpm,max_rpm,start_speed,end_speed,max_speed,max_boost,average_boost,start_iat,end_iat,iat_delta,max_oil_temperature,max_coolant_temperature,average_throttle,max_throttle,sample_count,data_completeness) VALUES(:session_id,:vehicle_id,:configuration_id,:started_at,:ended_at,:duration_ms,:confidence,:detector_name,:algorithm_version,:configuration_hash,:quality_flags,CAST(:metadata AS jsonb),:start_rpm,:end_rpm,:min_rpm,:max_rpm,:start_speed,:end_speed,:max_speed,:max_boost,:average_boost,:start_iat,:end_iat,:iat_delta,:max_oil_temperature,:max_coolant_temperature,:average_throttle,:max_throttle,:sample_count,:data_completeness) ON CONFLICT ON CONSTRAINT uq_pull_analysis_identity DO NOTHING"""
                    ),
                    {
                        "session_id": session_id,
                        "vehicle_id": session["vehicle_id"],
                        "configuration_id": session["configuration_id"],
                        "started_at": pull.started_at,
                        "ended_at": pull.ended_at,
                        "confidence": pull.confidence,
                        "detector_name": profile.name,
                        "algorithm_version": pull_detector.algorithm_version,
                        "configuration_hash": profile.configuration_hash,
                        "quality_flags": list(pull.quality_flags),
                        "metadata": json.dumps(metadata),
                        **metrics,
                    },
                )
            await db.commit()
        return AnalysisResult(
            session_id=session_id,
            profile=profile.name,
            algorithm_version=segmenter.algorithm_version,
            configuration_hash=profile.configuration_hash,
            segment_count=len(segments),
            pull_count=len(pulls),
            reused=False,
        )

    async def segments(
        self, session_id: UUID, segment_type: str | None, limit: int
    ) -> list[SessionSegment]:
        clause = " AND segment_type=:type" if segment_type else ""
        async with self.database.session() as db:
            rows = (
                await db.execute(
                    text(
                        f"SELECT * FROM session_segments WHERE session_id=:id{clause} ORDER BY started_at,id LIMIT :limit"
                    ),
                    {"id": session_id, "type": segment_type, "limit": limit},
                )
            ).mappings()
            return [SessionSegment.model_validate(row) for row in rows]

    async def pulls(
        self, session_id: UUID | None, vehicle_id: UUID | None, limit: int
    ) -> list[Pull]:
        conditions: list[str] = []
        values: dict[str, object] = {"limit": limit}
        if session_id:
            conditions.append("session_id=:session_id")
            values["session_id"] = session_id
        if vehicle_id:
            conditions.append("vehicle_id=:vehicle_id")
            values["vehicle_id"] = vehicle_id
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        async with self.database.session() as db:
            rows = (
                await db.execute(
                    text(f"SELECT * FROM pulls{where} ORDER BY started_at,id LIMIT :limit"), values
                )
            ).mappings()
            return [Pull.model_validate(row) for row in rows]

    async def pull(self, pull_id: UUID) -> Pull | None:
        async with self.database.session() as db:
            row = (
                (await db.execute(text("SELECT * FROM pulls WHERE id=:id"), {"id": pull_id}))
                .mappings()
                .one_or_none()
            )
            return Pull.model_validate(row) if row else None
