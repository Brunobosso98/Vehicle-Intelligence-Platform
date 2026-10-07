from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import VehicleContext


def at(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise AgentError("invalid_tool_result")
    return parsed


def effective(record: dict[str, Any], timestamp: datetime, start: str, end: str) -> bool:
    return at(record[start]) <= timestamp and (not record.get(end) or timestamp < at(record[end]))


def resolve_context(
    vehicle_id: UUID,
    vehicle: dict[str, Any],
    configurations: list[dict[str, Any]],
    modifications: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    timestamp: datetime | None = None,
) -> VehicleContext:
    now = timestamp or datetime.now(UTC)
    if str(vehicle.get("id")) != str(vehicle_id):
        raise AgentError("incompatible_context")
    for record in configurations + modifications + sessions:
        if str(record.get("vehicle_id")) != str(vehicle_id):
            raise AgentError("incompatible_context")
    warnings: list[str] = []
    active = [c for c in configurations if effective(c, now, "effective_at", "ended_at")]
    if len(active) != 1:
        warnings.append(
            "active_configuration_unknown" if not active else "overlapping_configurations"
        )
    enriched = []
    for session in sessions:
        when = at(session["started_at"])
        applicable = [c for c in configurations if effective(c, when, "effective_at", "ended_at")]
        assigned = session.get("configuration_id")
        temporal_valid = len(applicable) == 1 and str(applicable[0]["id"]) == str(assigned)
        if not temporal_valid:
            warnings.append("session_configuration_unknown_or_inconsistent")
        enriched.append(
            session
            | {
                "temporal_configuration_valid": temporal_valid,
                "recorded_modification_ids": [
                    m["id"]
                    for m in modifications
                    if effective(m, when, "installed_at", "removed_at")
                    and (
                        not m.get("configuration_id") or str(m["configuration_id"]) == str(assigned)
                    )
                ],
            }
        )
    return VehicleContext(
        vehicle_id=vehicle_id,
        vehicle={k: v for k, v in vehicle.items() if k not in {"vin"}},
        active_configuration_id=UUID(str(active[0]["id"])) if len(active) == 1 else None,
        configurations=configurations,
        modifications=[
            m
            | {
                "active_at_context": effective(m, now, "installed_at", "removed_at"),
            }
            for m in modifications
        ],
        sessions=enriched,
        as_of=now,
        warnings=list(dict.fromkeys(warnings)),
    )
