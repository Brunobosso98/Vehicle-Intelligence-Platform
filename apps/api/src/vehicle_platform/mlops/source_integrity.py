"""Deterministic read-only snapshots of prior-phase records around MLOps reads."""

from __future__ import annotations

from sqlalchemy import text

from vehicle_platform.evaluation.repository import SOURCE_TABLES
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database

_PHASE9G_TABLES = (
    "evaluation_protocols",
    "evaluation_runs",
    "evaluation_metric_reports",
    "evaluation_calibration_candidates",
    "evaluation_applicability_assessments",
)
PRIOR_IMMUTABLE_TABLES = (*SOURCE_TABLES, *_PHASE9G_TABLES)


async def prior_source_digest(database: Database) -> dict[str, str]:
    """Hash every pre-existing 9A–9G row from a fixed table allowlist."""
    result: dict[str, str] = {}
    async with database.session() as db, db.begin():
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        for table in PRIOR_IMMUTABLE_TABLES:
            rows = (
                (
                    await db.execute(
                        text(
                            f"SELECT row_to_json(item)::text FROM {table} "  # noqa: S608 -- fixed table allowlist
                            "item ORDER BY 1"
                        )
                    )
                )
                .scalars()
                .all()
            )
            result[table] = stable_hash([str(row) for row in rows])
    return result
