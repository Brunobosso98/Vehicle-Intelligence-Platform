"""Bounded context repository for records currently owned by HTTP SQL handlers."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text

from vehicle_platform.api.domain_contracts import (
    DrivingSession,
    Modification,
    Vehicle,
    VehicleConfiguration,
)
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.mcp.errors import ErrorCode, PlatformError

Entity = Literal["vehicle", "configuration", "session"]


class Catalog:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def get(self, entity: Entity, identifier: UUID) -> dict[str, Any]:
        choices: dict[Entity, tuple[str, type[BaseModel]]] = {
            "vehicle": ("SELECT * FROM vehicles WHERE id=:id", Vehicle),
            "configuration": (
                "SELECT * FROM vehicle_configurations WHERE id=:id",
                VehicleConfiguration,
            ),
            "session": ("SELECT * FROM driving_sessions WHERE id=:id", DrivingSession),
        }
        query, model = choices[entity]
        async with self.database.session() as db:
            row = (await db.execute(text(query), {"id": identifier})).mappings().one_or_none()
        if row is None:
            raise PlatformError(ErrorCode.NOT_FOUND)
        return model.model_validate(row).model_dump(mode="json")

    async def vehicles(self, limit: int) -> list[dict[str, Any]]:
        async with self.database.session() as db:
            rows = (
                (
                    await db.execute(
                        text("SELECT * FROM vehicles ORDER BY created_at,id LIMIT :limit"),
                        {"limit": limit},
                    )
                )
                .mappings()
                .all()
            )
        return [Vehicle.model_validate(row).model_dump(mode="json") for row in rows]

    async def sessions(
        self, vehicle_id: UUID, configuration_id: UUID | None, limit: int
    ) -> list[dict[str, Any]]:
        async with self.database.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT * FROM driving_sessions WHERE vehicle_id=:vehicle "
                            "AND (CAST(:configuration AS uuid) IS NULL "
                            "OR configuration_id=:configuration) "
                            "ORDER BY started_at DESC NULLS LAST,id LIMIT :limit"
                        ),
                        {"vehicle": vehicle_id, "configuration": configuration_id, "limit": limit},
                    )
                )
                .mappings()
                .all()
            )
        return [DrivingSession.model_validate(row).model_dump(mode="json") for row in rows]

    async def modifications(self, vehicle_id: UUID, limit: int) -> list[dict[str, Any]]:
        async with self.database.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT * FROM modifications WHERE vehicle_id=:vehicle "
                            "ORDER BY installed_at,id LIMIT :limit"
                        ),
                        {"vehicle": vehicle_id, "limit": limit},
                    )
                )
                .mappings()
                .all()
            )
        return [Modification.model_validate(row).model_dump(mode="json") for row in rows]

    async def configurations(self, vehicle_id: UUID, limit: int) -> list[dict[str, Any]]:
        async with self.database.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT * FROM vehicle_configurations WHERE vehicle_id=:vehicle "
                            "ORDER BY effective_at DESC,id LIMIT :limit"
                        ),
                        {"vehicle": vehicle_id, "limit": limit},
                    )
                )
                .mappings()
                .all()
            )
        return [VehicleConfiguration.model_validate(row).model_dump(mode="json") for row in rows]

    async def history_truncated(
        self,
        vehicle_id: UUID,
        configuration_id: UUID | None = None,
        session_id: UUID | None = None,
        session_ids: list[UUID] | None = None,
    ) -> bool:
        # Count only a bounded 21-ID probe, never load an unbounded history.
        async with self.database.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE vehicle_id=:vehicle "
                            "AND (CAST(:configuration AS uuid) IS NULL "
                            "OR configuration_id=:configuration) "
                            "AND (CAST(:session AS uuid) IS NULL OR session_id=:session) "
                            "AND (CAST(:sessions AS uuid[]) IS NULL "
                            "OR session_id=ANY(:sessions)) LIMIT 21"
                        ),
                        {
                            "vehicle": vehicle_id,
                            "configuration": configuration_id,
                            "session": session_id,
                            "sessions": session_ids,
                        },
                    )
                )
                .scalars()
                .all()
            )
        return len(rows) > 20
