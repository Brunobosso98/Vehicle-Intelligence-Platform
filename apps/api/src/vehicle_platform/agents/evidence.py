import hashlib
import json
import math
from typing import Any
from uuid import UUID, uuid4

from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import Evidence, Fact
from vehicle_platform.mcp.schemas import Envelope


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def facts(
    value: Any, path: str = "", depth: int = 0, omitted: list[str] | None = None
) -> list[Fact]:
    result: list[Fact] = []
    omissions = omitted if omitted is not None else []
    if depth > 12:
        omissions.append("depth")
        return result
    if isinstance(value, dict):
        unit = value.get("unit") if isinstance(value.get("unit"), str) else None
        for key, child in value.items():
            if key in {"notes", "metadata", "vin", "nickname", "source_reference"}:
                continue
            children = facts(child, f"{path}/{key}", depth + 1, omissions)
            if unit and key in {
                "value",
                "mean",
                "minimum",
                "maximum",
                "min",
                "max",
                "median",
                "delta",
                "p95",
                "before",
                "after",
                "absolute",
                "start",
                "end",
                "median_start_iat_increase",
            }:
                for item in children:
                    item.unit = unit
            result.extend(children)
            if len(result) > 160:
                break
    elif isinstance(value, list):
        if len(value) > 20:
            omissions.append("list")
        for index, child in enumerate(value[:20]):
            result.extend(facts(child, f"{path}/{index}", depth + 1, omissions))
            if len(result) > 160:
                break
    elif value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            raise AgentError("invalid_tool_result")
        if isinstance(value, str) and len(value) > 500:
            omissions.append("string")
            return result
        if len(path) > 300:
            omissions.append("path")
            return result
        result.append(Fact(path=path, value=value))
    return result


class EvidenceRegistry:
    def __init__(self, run_id: UUID, vehicle_id: UUID, maximum: int) -> None:
        self.run_id, self.vehicle_id, self.maximum = run_id, vehicle_id, maximum
        self.items: dict[UUID, Evidence] = {}

    def add(self, tool: str, call_id: UUID, envelope: Envelope) -> list[Evidence]:
        selected = str(self.vehicle_id)
        context = envelope.model_dump(mode="json")["context"]
        if context.get("vehicle_id") != selected:
            raise AgentError("incompatible_context")
        records = envelope.data if isinstance(envelope.data, list) else [envelope.data]
        if len(self.items) + len(records) > self.maximum:
            raise AgentError("evidence_budget_exhausted")
        added = []
        for record in records:
            # Validate nested identity too: an envelope alone is not evidence of ownership.
            self.check_ownership(record)
            identifiers: dict[str, UUID | None] = {}
            for key in ("configuration_id", "session_id", "pull_id", "event_id", "analysis_run_id"):
                value = record.get(key) or context.get(key)
                identifiers[key] = UUID(str(value)) if value else None
            entity_id = record.get("id") or record.get("calculation_id")
            if tool in {"get_vehicle_configuration", "list_vehicle_configurations"}:
                identifiers["configuration_id"] = UUID(str(entity_id)) if entity_id else None
            if tool in {"get_session", "list_sessions"}:
                identifiers["session_id"] = UUID(str(entity_id)) if entity_id else None
            if tool in {"get_pull", "list_session_pulls"}:
                identifiers["pull_id"] = UUID(str(entity_id)) if entity_id else None
            if tool in {"get_event", "list_session_events", "list_pull_events"}:
                identifiers["event_id"] = UUID(str(entity_id)) if entity_id else None
            # Project analytics summaries first, keeping large nested profiles out of model input.
            projected = record
            if isinstance(record.get("result"), dict):
                result = record["result"]
                keys = (
                    "sufficiency",
                    "thermal",
                    "metric_deltas",
                    "metrics",
                    "sequence",
                    "repeatability",
                    "associations",
                    "sample_sizes",
                    "common_rpm_range",
                    "limitations",
                    "units",
                    "quality_flags",
                    "warnings",
                )
                summary = {k: result[k] for k in keys if k in result}
                summary.update(
                    {
                        k: v
                        for k, v in result.items()
                        if k not in summary
                        and k
                        not in {
                            "comparison",
                            "before",
                            "after",
                            "profiles",
                            "bins",
                            "rpm_bins",
                            "comparability",
                        }
                    }
                )
                projected = record | {"result": summary}
            omissions: list[str] = []
            extracted = facts(projected, omitted=omissions)
            source_warnings = [w.code for w in envelope.warnings]
            raw_quality = record.get("result")
            quality = raw_quality if isinstance(raw_quality, dict) else record
            if quality.get("quality_flags") or quality.get("data_quality_flags"):
                source_warnings.append("source_quality_flags")
            completeness = quality.get("completeness", record.get("data_completeness"))
            if isinstance(completeness, (int, float)) and completeness < 0.9:
                source_warnings.append("source_incomplete")
            if quality.get("sufficiency", "sufficient") != "sufficient":
                source_warnings.append("source_insufficient")
            item = Evidence(
                id=uuid4(),
                run_id=self.run_id,
                vehicle_id=self.vehicle_id,
                evidence_type=tool,
                source_tool=tool,
                tool_call_id=call_id,
                source_fingerprint=canonical_hash(record),
                entity_id=UUID(str(entity_id)) if entity_id else None,
                summary=f"Registro determinístico: {tool}",
                facts=extracted[:160],
                provenance=envelope.provenance
                | {
                    "projection": "agent-summary-v1",
                    "selection": context,
                },
                warnings=list(dict.fromkeys(source_warnings))[:31],
                truncated=envelope.truncated,
                **identifiers,
            )
            if len(extracted) > 160 or omissions:
                item.truncated = True
                item.warnings.append("evidence_facts_truncated")
            self.items[item.id] = item
            added.append(item)
        return added

    def check_ownership(self, value: Any, depth: int = 0) -> None:
        if depth > 16:
            raise AgentError("invalid_tool_result")
        if isinstance(value, dict):
            if value.get("vehicle_id") is not None and str(value["vehicle_id"]) != str(
                self.vehicle_id
            ):
                raise AgentError("incompatible_context")
            for child in value.values():
                self.check_ownership(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                self.check_ownership(child, depth + 1)
