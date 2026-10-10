"""Source capability snapshots from the local collector, never inferred from absence."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import text

from vehicle_platform.acquisition.adapters import PIDS
from vehicle_platform.acquisition.domain import DeviceCapabilities, Support
from vehicle_platform.api.domain_contracts import PreflightRequest
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.telemetry.domain import SIGNAL_BY_KEY

Adapter = Literal["obd", "replay", "synthetic"]
FRESHNESS = timedelta(days=1)


@dataclass(frozen=True)
class SourceCapabilitySnapshot:
    capabilities: DeviceCapabilities
    received_at: datetime
    acquisition_id: UUID | None = None
    preflight_id: UUID | None = None


def validated_report(adapter: Adapter, report: PreflightRequest) -> DeviceCapabilities:
    known = set(SIGNAL_BY_KEY)
    signals = set(report.signals)
    if not signals <= known:
        raise ValueError("source report contains unknown canonical signals")
    if adapter == "obd" and (
        not report.adapter.startswith("elm327-standard-read-only")
        or not signals <= {pid.signal for pid in PIDS}
        or report.maximum_requests_per_second > 12
    ):
        raise ValueError("OBD report is not supported by the read-only standard adapter")
    if adapter == "replay" and not report.adapter.startswith("csv-replay"):
        raise ValueError("replay report source mismatch")
    if adapter == "synthetic" and not report.adapter.startswith("synthetic"):
        raise ValueError("synthetic report source mismatch")
    return DeviceCapabilities(
        report.adapter,
        {signal: Support(value) for signal, value in report.signals.items()},
        report.maximum_requests_per_second,
        report.discovery_supported,
    )


def fresh(received: datetime) -> bool:
    now = datetime.now(UTC)
    return (
        received.utcoffset() is not None
        and received <= now + timedelta(seconds=5)
        and now - received <= FRESHNESS
    )


class AcquisitionCapabilitySource:
    """Phase 4 owner of source support; a dataset report is not source support."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def register(
        self,
        vehicle_id: UUID,
        configuration_id: UUID,
        adapter: Literal["obd", "replay"],
        source_id: str,
        report: PreflightRequest,
    ) -> SourceCapabilitySnapshot:
        if not 1 <= len(source_id) <= 80:
            raise ValueError("invalid source identity")
        capabilities = validated_report(adapter, report)
        observed = datetime.now(UTC)
        async with self.database.session() as db:
            valid = await db.scalar(
                text(
                    "SELECT 1 FROM vehicle_configurations WHERE id=:configuration "
                    "AND vehicle_id=:vehicle AND effective_at<=:now "
                    "AND (ended_at IS NULL OR ended_at>:now)"
                ),
                {"configuration": configuration_id, "vehicle": vehicle_id, "now": observed},
            )
            if valid is None:
                raise ValueError("source preflight requires the active vehicle configuration")
            identifier = await db.scalar(
                text(
                    "INSERT INTO acquisition_source_capabilities "
                    "(id,vehicle_id,configuration_id,adapter,source_id,observed_at,report) "
                    "VALUES (:id,:vehicle,:configuration,:adapter,:source,:observed,"
                    "CAST(:report AS jsonb)) "
                    "ON CONFLICT ON CONSTRAINT uq_acquisition_source_capability "
                    "DO UPDATE SET observed_at=EXCLUDED.observed_at,report=EXCLUDED.report "
                    "RETURNING id"
                ),
                {
                    "id": uuid4(),
                    "vehicle": vehicle_id,
                    "configuration": configuration_id,
                    "adapter": adapter,
                    "source": source_id,
                    "observed": observed,
                    "report": report.model_dump_json(),
                },
            )
            await db.commit()
        return SourceCapabilitySnapshot(capabilities, observed, preflight_id=identifier)

    async def latest(
        self,
        vehicle_id: UUID,
        configuration_id: UUID | None,
        adapter: Adapter,
        source_id: str,
    ) -> SourceCapabilitySnapshot | None:
        if not 1 <= len(source_id) <= 80:
            raise ValueError("invalid source identity")
        if configuration_id is None:
            return None
        async with self.database.session() as db:
            preflight = (
                (
                    await db.execute(
                        text(
                            "SELECT id,observed_at,report FROM acquisition_source_capabilities "
                            "WHERE vehicle_id=:vehicle AND configuration_id=:configuration "
                            "AND adapter=:adapter AND source_id=:source"
                        ),
                        {
                            "vehicle": vehicle_id,
                            "configuration": configuration_id,
                            "adapter": adapter,
                            "source": source_id,
                        },
                    )
                )
                .mappings()
                .one_or_none()
            )
            collector = (
                (
                    await db.execute(
                        text(
                            "SELECT a.id,a.quality->'collector' AS report "
                            "FROM acquisition_sessions a JOIN driving_sessions s "
                            "ON s.id=a.driving_session_id "
                            "WHERE s.vehicle_id=:vehicle AND s.configuration_id=:configuration "
                            "AND a.adapter=:adapter AND s.source_reference=:source "
                            "AND a.quality->'collector'->'capability_snapshot' IS NOT NULL "
                            "ORDER BY a.updated_at DESC,a.id DESC LIMIT 1"
                        ),
                        {
                            "vehicle": vehicle_id,
                            "configuration": configuration_id,
                            "adapter": adapter,
                            "source": source_id,
                        },
                    )
                )
                .mappings()
                .one_or_none()
            )
        candidates: list[SourceCapabilitySnapshot] = []
        if preflight is not None:
            try:
                observed = preflight["observed_at"]
                if fresh(observed):
                    report = PreflightRequest.model_validate(preflight["report"])
                    capabilities = validated_report(adapter, report)
                    candidates.append(
                        SourceCapabilitySnapshot(
                            capabilities, observed, preflight_id=preflight["id"]
                        )
                    )
            except (TypeError, ValueError, ValidationError):
                pass
        if collector is not None and isinstance(collector["report"], dict):
            try:
                payload = collector["report"]
                observed = datetime.fromisoformat(
                    str(payload["received_at"]).replace("Z", "+00:00")
                )
                if fresh(observed) and payload.get("adapter_state") == "connected":
                    report = PreflightRequest.model_validate(payload["capability_snapshot"])
                    capabilities = validated_report(adapter, report)
                    candidates.append(
                        SourceCapabilitySnapshot(
                            capabilities, observed, acquisition_id=collector["id"]
                        )
                    )
            except (KeyError, TypeError, ValueError, ValidationError):
                pass
        return max(candidates, key=lambda item: item.received_at) if candidates else None
