"""Only MCP-resolved context may establish vehicle knowledge applicability."""

from typing import Any
from uuid import UUID

from vehicle_platform.agents.schemas import VehicleContext
from vehicle_platform.knowledge.domain import VehicleScope


def text_field(record: dict[str, Any], name: str) -> str | None:
    value = record.get(name)
    return value[:160] if isinstance(value, str) and value.strip() else None


def knowledge_scope(context: VehicleContext, session_id: UUID | None) -> VehicleScope:
    session = next((s for s in context.sessions if str(s["id"]) == str(session_id)), None)
    if session_id is not None and session is None:
        raise ValueError("knowledge_session_context_missing")
    configuration_id = (
        session.get("configuration_id") if session else context.active_configuration_id
    )
    config = next((c for c in context.configurations if str(c["id"]) == str(configuration_id)), {})
    valid = (
        bool(session.get("temporal_configuration_valid"))
        if session
        else bool(
            config
            and not {"overlapping_configurations", "context_history_truncated"}
            & set(context.warnings)
        )
    )
    valid = valid and "context_history_truncated" not in context.warnings
    metadata = config.get("metadata", {}) if valid else {}
    if not isinstance(metadata, dict):
        metadata = {}
    active_ids = (
        set(session.get("recorded_modification_ids", []))
        if session
        else {m["id"] for m in context.modifications if m.get("active_at_context")}
    )
    mods = [m for m in context.modifications if m["id"] in active_ids] if valid else []
    calibration = metadata.get("calibration", "unknown")
    return VehicleScope(
        vehicle_id=context.vehicle_id,
        configuration_id=UUID(str(configuration_id)) if configuration_id else None,
        session_id=session_id,
        as_of=session["started_at"] if session else context.as_of,
        make=text_field(context.vehicle, "manufacturer"),
        model=text_field(context.vehicle, "model"),
        platform=text_field(context.vehicle, "generation"),
        engine=text_field(context.vehicle, "engine_code"),
        transmission=text_field(context.vehicle, "transmission"),
        model_year=context.vehicle.get("model_year"),
        calibration=calibration if calibration in {"stock", "tuned"} else "unknown",
        tuner=text_field(metadata, "tuner"),
        map_version=text_field(metadata, "map_version"),
        stage=text_field(metadata, "stage"),
        fuel=text_field(metadata, "fuel"),
        hardware=[m["product"][:160] for m in mods if isinstance(m.get("product"), str)],
        # Existing Modification has no explicit part_number field: never infer from its label.
        part_numbers=[],
        temporal_valid=valid,
    )
