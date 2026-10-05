from typing import Any
from uuid import UUID

from vehicle_platform.acquisition.service import AcquisitionService
from vehicle_platform.analysis.service import SessionAnalysisService
from vehicle_platform.analytics.domain import AnalyticsConfig
from vehicle_platform.analytics.service import AnalyticsService
from vehicle_platform.api.domain_contracts import AnalyticsResultResponse
from vehicle_platform.core.config import Settings
from vehicle_platform.events.service import EventAnalysisService
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.mcp.catalog import Catalog, Entity
from vehicle_platform.mcp.errors import ErrorCode, PlatformError
from vehicle_platform.mcp.schemas import Envelope, Warning, Window
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.telemetry.domain import SIGNALS
from vehicle_platform.telemetry.service import QueryService


class Adapter:
    def __init__(self, database: Database, settings: Settings, telemetry: Telemetry) -> None:
        self.catalog = Catalog(database)
        self.analysis = SessionAnalysisService(database, telemetry)
        self.events = EventAnalysisService(database, telemetry)
        self.analytics = AnalyticsService(database, telemetry, read_only=True)
        self.acquisition = AcquisitionService(database, settings, telemetry)
        self.telemetry = QueryService(database, telemetry)
        self.config = AnalyticsConfig()

    async def entity(self, kind: Entity, identifier: UUID, vehicle_id: UUID) -> dict[str, Any]:
        data = await self.catalog.get(kind, identifier)
        actual = data["id"] if kind == "vehicle" else data["vehicle_id"]
        if str(actual) != str(vehicle_id):
            raise PlatformError(ErrorCode.INCOMPATIBLE_CONTEXT)
        return data

    async def pull(self, vehicle_id: UUID, pull_id: UUID) -> dict[str, Any]:
        data = await self.analysis.pull(pull_id)
        if data is None:
            raise PlatformError(ErrorCode.NOT_FOUND)
        if data.vehicle_id != vehicle_id:
            raise PlatformError(ErrorCode.INCOMPATIBLE_CONTEXT)
        return data.model_dump(mode="json")

    async def selected_pulls(
        self, vehicle_id: UUID, ids: list[UUID], *, same_configuration: bool = True
    ) -> list[dict[str, Any]]:
        if len(set(ids)) != len(ids) or not 1 <= len(ids) <= 20:
            raise PlatformError(ErrorCode.INVALID_ARGUMENT)
        pulls = [await self.pull(vehicle_id, item) for item in ids]
        if same_configuration and len({p["configuration_id"] for p in pulls}) != 1:
            raise PlatformError(ErrorCode.INCOMPATIBLE_CONTEXT)
        return pulls

    def envelope(
        self,
        data: dict[str, Any] | list[dict[str, Any]],
        context: dict[str, UUID | list[UUID] | None],
        *,
        limit: int | None = None,
    ) -> Envelope:
        truncated = isinstance(data, list) and limit is not None and len(data) > limit
        if isinstance(data, list) and limit is not None:
            data = data[:limit]
        return Envelope(
            data=data,
            context=context,
            provenance={"source": "canonical-platform-records", "snapshot": True},
            truncated=truncated,
            returned=len(data) if isinstance(data, list) else 1,
            warnings=[Warning(code="truncated_result")] if truncated else [],
        )

    async def analytical(
        self, result: AnalyticsResultResponse, context: dict[str, UUID | list[UUID] | None]
    ) -> Envelope:
        data = result.model_dump(mode="json")
        data["calculation_id"] = data.pop("id")
        response = self.envelope(data, context)
        response.provenance.update(
            {
                "analysis_run_id": None,
                "persistence": "transient",
                "source_fingerprint": result.source_fingerprint,
                "algorithm_version": result.algorithm_version,
                "configuration_hash": result.configuration_hash,
            }
        )
        if result.analytics_type in {"session", "vehicle_baseline", "trend", "cross_session"}:
            session_id = context.get("session_id")
            session_ids = context.get("session_ids")
            truncated = await self.catalog.history_truncated(
                result.vehicle_id,
                result.configuration_id if result.analytics_type == "vehicle_baseline" else None,
                session_id if isinstance(session_id, UUID) else None,
                session_ids if isinstance(session_ids, list) else None,
            )
            response.truncated = truncated
            response.provenance["maximum_selected_pulls"] = 20
            if truncated:
                response.warnings.append(Warning(code="truncated_result"))
        response.warnings.extend(Warning(code=code) for code in result.warnings)
        if result.status == "insufficient":
            response.warnings.append(Warning(code="insufficient_history"))
        return response

    async def window(
        self, vehicle_id: UUID, session_id: UUID, signals: list[str], window: Window, limit: int
    ) -> Envelope:
        session = await self.entity("session", session_id, vehicle_id)
        if len(set(signals)) != len(signals):
            raise PlatformError(ErrorCode.INVALID_ARGUMENT)
        if any(signal not in {item.key for item in SIGNALS} for signal in signals):
            raise PlatformError(ErrorCode.UNSUPPORTED_CAPABILITY)
        result = await self.telemetry.query(session_id, signals, window.start, window.end, limit)
        response = self.envelope(
            result.model_dump(mode="json"),
            {
                "vehicle_id": vehicle_id,
                "session_id": session_id,
                "configuration_id": UUID(session["configuration_id"])
                if session["configuration_id"]
                else None,
            },
        )
        response.truncated = result.truncated
        response.returned = result.returned
        if result.truncated:
            response.warnings.append(Warning(code="truncated_result"))
        missing = sorted(set(signals) - {p.signal for p in result.points})
        if missing:
            response.warnings.append(
                Warning(
                    code="partial_window", details={"signals_without_returned_samples": missing}
                )
                if result.truncated
                else Warning(code="missing_signal", details={"signals": missing})
            )
        response.provenance.update(
            {"source": "canonical-telemetry", "requested_window": window.model_dump(mode="json")}
        )
        return response
