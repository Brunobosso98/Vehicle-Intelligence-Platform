"""Protect previously published Phase 9G test partitions from later reuse."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text

from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.domain import SupervisedRow
from vehicle_platform.mlops.policy import require_controlled_environment


async def prior_holdout_conflict(database: Database, rows: Sequence[SupervisedRow]) -> str | None:
    """Return a fail-closed reason if rows overlap a persisted supervised 9G test fold."""
    require_controlled_environment()
    if len(rows) > 21000:
        raise ValueError("holdout check exceeds its bounded row count")
    if not rows:
        return None
    fingerprints = {
        "row_ids": sorted({row.row_id for row in rows}),
        "session_fingerprints": sorted({stable_hash(row.session_id) for row in rows}),
        "vehicle_fingerprints": sorted({stable_hash(row.vehicle_id) for row in rows}),
        "configuration_fingerprints": sorted({stable_hash(row.configuration_id) for row in rows}),
        "pull_fingerprints": sorted(
            {stable_hash(pull) for row in rows for pull in (row.input_pull_id, row.target_pull_id)}
        ),
    }
    keys = tuple(fingerprints)
    async with database.session() as db, db.begin():
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        for key in keys:
            # The JSON key is bound, not interpolated, and only comes from the fixed catalog above.
            invalid = await db.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM evaluation_metric_reports "
                    "WHERE report_key LIKE 'supervised-%' AND "
                    "jsonb_typeof(report_body->'partitions'->'TEST'->:key) "
                    "IS DISTINCT FROM 'array')"
                ),
                {"key": key},
            )
            if invalid:
                return "HOLDOUT_HISTORY_UNVERIFIABLE"
            overlap = await db.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM evaluation_metric_reports r "
                    "CROSS JOIN LATERAL jsonb_array_elements_text("
                    "CASE WHEN jsonb_typeof(r.report_body->'partitions'->'TEST'->:key)='array' "
                    "THEN r.report_body->'partitions'->'TEST'->:key ELSE '[]'::jsonb END) "
                    "AS item(value) WHERE r.report_key LIKE 'supervised-%' "
                    "AND item.value=ANY(CAST(:values AS text[])))"
                ),
                {"key": key, "values": fingerprints[key]},
            )
            if overlap:
                return "PRIOR_RESERVED_HOLDOUT_OVERLAP"
    return None
