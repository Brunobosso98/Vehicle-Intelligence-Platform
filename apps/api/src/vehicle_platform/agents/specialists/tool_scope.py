"""Describe existing specialist ID permissions in per-turn tool schemas."""

from copy import deepcopy
from typing import Any

from vehicle_platform.agents.schemas import Evidence, SpecialistRequest


def scoped_tool_definitions(
    request: SpecialistRequest, tools: list[dict[str, Any]], evidence: list[Evidence]
) -> list[dict[str, Any]]:
    sessions = {str(i) for i in request.session_ids}
    owned = [
        e
        for e in evidence
        if e.run_id == request.supervisor_run_id
        and e.vehicle_id == request.vehicle_id
        and str(e.session_id) in sessions
    ]
    pulls = sorted({str(e.pull_id) for e in owned if e.pull_id})
    events = sorted({str(e.event_id) for e in owned if e.event_id})
    identities = {
        "vehicle_id": [str(request.vehicle_id)],
        "session_id": sorted(sessions),
        "session_ids": sorted(sessions),
        "pull_id": pulls,
        "pull_ids": pulls,
        "before_pull_ids": pulls,
        "after_pull_ids": pulls,
        "event_id": events,
        "configuration_id": sorted({str(c["id"]) for c in request.context.configurations}),
    }
    result = []
    for original in tools:
        tool = deepcopy(original)
        parameters = tool["parameters"]
        required = set(parameters.get("required", []))
        eligible = True
        for name, schema in parameters.get("properties", {}).items():
            if name not in identities:
                continue
            identifiers = identities[name]
            nullable = any(v.get("type") == "null" for v in schema.get("anyOf", []))
            if name.endswith("_ids"):
                if len(identifiers) < schema.get("minItems", 1):
                    eligible = False
                    break
                schema["items"] = schema.get("items", {}) | {"enum": identifiers}
                schema["uniqueItems"] = True
            elif identifiers:
                schema["enum"] = [*identifiers, *([None] if nullable else [])]
            elif nullable:
                schema["enum"] = [None]
            elif name in required:
                eligible = False
                break
        if eligible:
            result.append(tool)
    return result
