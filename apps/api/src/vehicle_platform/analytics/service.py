# ruff: noqa: E501
import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from opentelemetry import trace
from sqlalchemy import text

from vehicle_platform.analytics.domain import (
    AnalyticsConfig,
    PullInput,
    Sample,
    baseline,
    compare_pulls,
    configuration_comparison,
    pull_profile,
    repeated_pulls,
    trend,
)
from vehicle_platform.api.domain_contracts import AnalyticsResultResponse
from vehicle_platform.infrastructure.database import Database

ALGORITHM_NAME = "deterministic-automotive-analytics"
ALGORITHM_VERSION = "1.0.0"
MAX_OBSERVATIONS = 500_000


class AnalyticsLimitError(ValueError):
    pass


class AnalyticsService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.tracer = trace.get_tracer("vehicle_platform.analytics")

    async def _load(self, pull_ids: list[UUID]) -> list[PullInput]:
        if not pull_ids or len(pull_ids) > 20:
            raise AnalyticsLimitError("between 1 and 20 pull IDs are required")
        with self.tracer.start_as_current_span("analytics.source_selection"):
            return await self._load_selected(pull_ids)

    async def _load_selected(self, pull_ids: list[UUID]) -> list[PullInput]:
        async with self.database.session() as db:
            pulls = (
                (
                    await db.execute(
                        text("SELECT * FROM pulls WHERE id = ANY(:ids) ORDER BY started_at,id"),
                        {"ids": pull_ids},
                    )
                )
                .mappings()
                .all()
            )
            if len(pulls) != len(set(pull_ids)):
                raise LookupError("pull not found")
            output: list[PullInput] = []
            total = 0
            for pull in pulls:
                rows = (
                    await db.execute(
                        text("""SELECT observed_at,signal_key,numeric_value FROM telemetry_samples
                    WHERE session_id=:session AND observed_at>=:start AND observed_at<=:end
                    AND quality IN ('valid','out_of_range') ORDER BY observed_at,signal_key,sample_id"""),
                        {
                            "session": pull["session_id"],
                            "start": pull["started_at"],
                            "end": pull["ended_at"],
                        },
                    )
                ).all()
                total += len(rows)
                if total > MAX_OBSERVATIONS:
                    raise AnalyticsLimitError("analytics request exceeds 500000 observations")
                frames: dict[datetime, dict[str, float]] = {}
                for at, signal, value in rows:
                    frames.setdefault(at, {})[signal] = value
                samples = tuple(
                    Sample(at, values["engine.rpm"], values)
                    for at, values in frames.items()
                    if "engine.rpm" in values
                )
                events: list[UUID] = list(
                    (
                        await db.execute(
                            text(
                                "SELECT id FROM detected_events WHERE pull_id=:id ORDER BY started_at,id"
                            ),
                            {"id": pull["id"]},
                        )
                    )
                    .scalars()
                    .all()
                )
                output.append(
                    PullInput(
                        str(pull["id"]),
                        str(pull["session_id"]),
                        str(pull["vehicle_id"]),
                        str(pull["configuration_id"]) if pull["configuration_id"] else None,
                        pull["started_at"],
                        pull["ended_at"],
                        pull["data_completeness"],
                        samples,
                        tuple(map(str, events)),
                        tuple(pull["quality_flags"]),
                    )
                )
            return output

    async def _persist(
        self,
        analytics_type: str,
        pulls: list[PullInput],
        config: AnalyticsConfig,
        compute: Callable[[], dict[str, object]],
        recompute: bool,
    ) -> AnalyticsResultResponse:
        source = hashlib.sha256("\x1f".join(sorted(p.id for p in pulls)).encode()).hexdigest()
        vehicle_id, configuration_id = UUID(pulls[0].vehicle_id), pulls[0].configuration_id
        async with self.database.session() as db:
            existing = (
                (
                    await db.execute(
                        text("""SELECT * FROM analytics_runs WHERE analytics_type=:type AND algorithm_version=:version
                AND configuration_hash=:hash AND source_fingerprint=:source ORDER BY generated_at DESC LIMIT 1"""),
                        {
                            "type": analytics_type,
                            "version": ALGORITHM_VERSION,
                            "hash": config.configuration_hash,
                            "source": source,
                        },
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing and not recompute:
                return AnalyticsResultResponse.model_validate({**existing, "reused": True})
            with self.tracer.start_as_current_span("analytics.metric_extraction"):
                result = compute()
            status_value = str(result.get("sufficiency", "sufficient"))
            status = "completed" if status_value == "sufficient" else status_value
            limitation_value = result.get("limitations", [])
            warnings = (
                [str(item) for item in limitation_value]
                if isinstance(limitation_value, list)
                else []
            )
            with self.tracer.start_as_current_span("analytics.persistence"):
                row = (
                    (
                        await db.execute(
                            text("""INSERT INTO analytics_runs
                (analytics_type,algorithm_name,algorithm_version,configuration_hash,source_fingerprint,vehicle_id,configuration_id,status,warnings,input_summary,result)
                VALUES(:type,:name,:version,:hash,:source,:vehicle,:configuration,:status,:warnings,CAST(:input AS jsonb),CAST(:result AS jsonb)) RETURNING *"""),
                            {
                                "type": analytics_type,
                                "name": ALGORITHM_NAME,
                                "version": ALGORITHM_VERSION,
                                "hash": config.configuration_hash,
                                "source": source,
                                "vehicle": vehicle_id,
                                "configuration": UUID(configuration_id)
                                if configuration_id
                                else None,
                                "status": status,
                                "warnings": warnings,
                                "input": json.dumps(
                                    {
                                        "pull_ids": [p.id for p in pulls],
                                        "observation_count": sum(len(p.samples) for p in pulls),
                                    }
                                ),
                                "result": json.dumps(result, default=str),
                            },
                        )
                    )
                    .mappings()
                    .one()
                )
                await db.commit()
            return AnalyticsResultResponse.model_validate({**row, "reused": False})

    async def pull(
        self, pull_id: UUID, config: AnalyticsConfig, recompute: bool = False
    ) -> AnalyticsResultResponse:
        pulls = await self._load([pull_id])
        return await self._persist(
            "pull", pulls, config, lambda: pull_profile(pulls[0], config), recompute
        )

    async def comparison(
        self, ids: list[UUID], config: AnalyticsConfig, recompute: bool = False
    ) -> AnalyticsResultResponse:
        pulls = await self._load(ids)
        return await self._persist(
            "pull_comparison", pulls, config, lambda: compare_pulls(pulls, config), recompute
        )

    async def repeated(
        self, ids: list[UUID], config: AnalyticsConfig, recompute: bool = False
    ) -> AnalyticsResultResponse:
        pulls = await self._load(ids)
        return await self._persist(
            "repeated_pulls", pulls, config, lambda: repeated_pulls(pulls, config), recompute
        )

    async def session(
        self, session_id: UUID, config: AnalyticsConfig, recompute: bool = False
    ) -> AnalyticsResultResponse:
        async with self.database.session() as db:
            ids: list[UUID] = list(
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE session_id=:id ORDER BY started_at LIMIT 20"
                        ),
                        {"id": session_id},
                    )
                ).scalars()
            )
        pulls = await self._load(ids)
        return await self._persist(
            "session", pulls, config, lambda: repeated_pulls(pulls, config), recompute
        )

    async def cross_sessions(
        self, session_ids: list[UUID], config: AnalyticsConfig, recompute: bool = False
    ) -> AnalyticsResultResponse:
        if not 2 <= len(session_ids) <= 10:
            raise AnalyticsLimitError("cross-session comparison requires 2 to 10 sessions")
        async with self.database.session() as db:
            ids: list[UUID] = list(
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE session_id = ANY(:ids) "
                            "ORDER BY started_at,id LIMIT 20"
                        ),
                        {"ids": session_ids},
                    )
                ).scalars()
            )
        pulls = await self._load(ids)
        return await self._persist(
            "cross_session", pulls, config, lambda: compare_pulls(pulls, config), recompute
        )

    async def vehicle_baseline(
        self,
        vehicle_id: UUID,
        configuration_id: UUID,
        config: AnalyticsConfig,
        recompute: bool = False,
    ) -> AnalyticsResultResponse:
        async with self.database.session() as db:
            ids: list[UUID] = list(
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE vehicle_id=:vehicle AND configuration_id=:configuration AND data_completeness>=:quality ORDER BY started_at DESC LIMIT 20"
                        ),
                        {
                            "vehicle": vehicle_id,
                            "configuration": configuration_id,
                            "quality": config.minimum_completeness,
                        },
                    )
                ).scalars()
            )
        pulls = await self._load(ids)
        return await self._persist(
            "vehicle_baseline", pulls, config, lambda: baseline(pulls, config), recompute
        )

    async def trends(
        self, vehicle_id: UUID, metric: str, config: AnalyticsConfig
    ) -> AnalyticsResultResponse:
        if metric not in {"boost", "iat", "coolant", "oil", "fuel", "speed", "throttle"}:
            raise AnalyticsLimitError("unsupported trend metric")
        async with self.database.session() as db:
            ids: list[UUID] = list(
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE vehicle_id=:vehicle ORDER BY started_at DESC LIMIT 20"
                        ),
                        {"vehicle": vehicle_id},
                    )
                ).scalars()
            )
        pulls = await self._load(ids)
        return await self._persist(
            "trend", pulls, config, lambda: trend(pulls, metric, config), False
        )

    async def modifications(
        self, before_ids: list[UUID], after_ids: list[UUID], config: AnalyticsConfig
    ) -> AnalyticsResultResponse:
        pulls = await self._load(before_ids + after_ids)
        by_id = {p.id: p for p in pulls}
        before, after = (
            [by_id[str(item)] for item in before_ids],
            [by_id[str(item)] for item in after_ids],
        )
        return await self._persist(
            "modification_comparison",
            pulls,
            config,
            lambda: configuration_comparison(before, after, config),
            False,
        )
