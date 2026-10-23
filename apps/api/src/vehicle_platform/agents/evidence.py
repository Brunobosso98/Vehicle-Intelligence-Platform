import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import Evidence, Fact
from vehicle_platform.mcp.schemas import Envelope, PredictionEvidenceMCPProjection


@dataclass(frozen=True)
class PredictionEvidenceLink:
    run_evidence_id: UUID
    source_evidence_id: UUID
    receipt_id: UUID
    source_vehicle_id: UUID
    source_session_id: UUID
    source_pull_id: UUID
    source_configuration_id: UUID | None
    source_feature_set_id: UUID | None
    result_type: str
    horizon: str
    task: str | None
    family: str | None
    model_version: str | None
    model_algorithm: str | None
    detector_version: str | None
    detector_algorithm_version: str | None
    detector_method: str | None
    source_role: str
    effective_cutoff: datetime
    integrity: str
    completeness: str
    artifact_availability: str
    projection_version: str


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
    def __init__(
        self,
        run_id: UUID,
        vehicle_id: UUID,
        maximum: int,
        selected_session_id: UUID | None = None,
        selected_pull_id: UUID | None = None,
        selected_prediction_ids: tuple[UUID, ...] = (),
    ) -> None:
        self.run_id, self.vehicle_id, self.maximum = run_id, vehicle_id, maximum
        self.selected_session_id, self.selected_pull_id = selected_session_id, selected_pull_id
        self.selected_prediction_ids = frozenset(selected_prediction_ids)
        self.items: dict[UUID, Evidence] = {}
        self.prediction_links: list[PredictionEvidenceLink] = []

    def ordered(self) -> list[Evidence]:
        """Merge independent reads by tool/selection, preserving each MCP result's row order."""
        positions: dict[UUID, int] = {}
        counts: dict[UUID, int] = {}
        for item in self.items.values():
            positions[item.id] = counts.get(item.tool_call_id, 0)
            counts[item.tool_call_id] = positions[item.id] + 1
        return sorted(
            self.items.values(),
            key=lambda item: (
                item.source_tool,
                canonical_hash(item.provenance.get("selection", {})),
                positions[item.id],
                item.source_fingerprint,
            ),
        )

    def add(self, tool: str, call_id: UUID, envelope: Envelope) -> list[Evidence]:
        if tool == "get_prediction_evidence":
            return self._add_prediction(call_id, envelope)
        selected = str(self.vehicle_id)
        context = envelope.model_dump(mode="json")["context"]
        if context.get("vehicle_id") != selected:
            raise AgentError("incompatible_context")
        records = envelope.data if isinstance(envelope.data, list) else [envelope.data]
        collection = isinstance(envelope.data, list)
        if len(self.items) + len(records) + int(collection) > self.maximum:
            raise AgentError("evidence_budget_exhausted")
        for record in records:
            self.check_ownership(record)
        added = []
        for record in records:
            # Validate nested identity too: an envelope alone is not evidence of ownership.
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
        if collection:
            metadata: dict[str, int | bool] = {
                "returned_count": len(records),
                "complete": not envelope.truncated,
            }
            if not envelope.truncated:
                metadata["total_count"] = len(records)
            item = Evidence(
                id=uuid4(),
                run_id=self.run_id,
                vehicle_id=self.vehicle_id,
                evidence_type=f"{tool}_collection",
                source_tool=tool,
                tool_call_id=call_id,
                source_fingerprint=canonical_hash(
                    {"data": envelope.data, "context": context, "truncated": envelope.truncated}
                ),
                session_id=UUID(str(context["session_id"])) if context.get("session_id") else None,
                pull_id=UUID(str(context["pull_id"])) if context.get("pull_id") else None,
                summary=f"Coleção determinística: {tool}",
                facts=facts({"collection": {tool: metadata}}),
                provenance=envelope.provenance
                | {"projection": "agent-collection-v1", "selection": context},
                warnings=[warning.code for warning in envelope.warnings][:32],
                truncated=envelope.truncated,
            )
            self.items[item.id] = item
            added.append(item)
        return added

    def _add_prediction(self, call_id: UUID, envelope: Envelope) -> list[Evidence]:
        if not isinstance(envelope.data, dict) or len(self.items) >= self.maximum:
            raise AgentError("invalid_tool_result")
        projection = PredictionEvidenceMCPProjection.model_validate_json(json.dumps(envelope.data))
        if (
            str(envelope.context.get("vehicle_id")) != str(self.vehicle_id)
            or (
                self.selected_prediction_ids
                and projection.evidence_id not in self.selected_prediction_ids
            )
            or any(
                link.source_evidence_id == projection.evidence_id for link in self.prediction_links
            )
            or projection.source_vehicle_id != self.vehicle_id
            or (
                self.selected_session_id
                and projection.source_session_id != self.selected_session_id
            )
            or (self.selected_pull_id and projection.source_pull_id != self.selected_pull_id)
            or envelope.context.get("session_id") != projection.source_session_id
            or envelope.context.get("pull_id") != projection.source_pull_id
        ):
            raise AgentError("incompatible_context")
        if projection.schema_version != "prediction-agent-summary-v1":
            raise AgentError("unsupported_prediction_schema")

        evidence_id = uuid4()
        warnings: list[str] = []
        if projection.integrity.value not in {
            "VERIFIED",
            "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE",
        }:
            warnings.append("prediction_source_not_verifiable")
        if projection.integrity.value == "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE":
            warnings.append("prediction_snapshot_artifact_unavailable")
        if projection.completeness.value == "PARTIAL":
            warnings.append("prediction_evidence_partial")
        elif projection.completeness.value == "ABSTAINED":
            warnings.append("prediction_evidence_abstained")
        if projection.quality_class != "high":
            warnings.append("prediction_source_quality_limited")
        if projection.omitted_count:
            warnings.append("prediction_projection_omitted")

        values: dict[str, str | float | int | bool | None] = {
            "result_type": projection.result_type.value,
            "horizon": projection.horizon.value,
            "task": projection.task,
            "family": projection.family,
            "status": projection.status,
            "reason_code": projection.reason_code,
            "model_version": projection.model_version,
            "model_algorithm": projection.model_algorithm,
            "detector_version": projection.detector_version,
            "detector_algorithm_version": projection.detector_algorithm_version,
            "detector_method": projection.detector_method,
            "decision": projection.decision,
            "score": projection.score,
            "threshold": projection.threshold,
            "score_is_probability": projection.score_is_probability,
            "source_role": projection.source_role.value,
            "requested_cutoff": projection.requested_cutoff.isoformat(),
            "effective_cutoff": projection.effective_cutoff.isoformat(),
            "completeness": projection.completeness.value,
            "integrity": projection.integrity.value,
            "artifact_availability": projection.artifact_availability.value,
            "quality_class": projection.quality_class,
            "coverage": projection.coverage,
            "feature_coverage": projection.feature_coverage,
            "observed_feature_count": projection.observed_feature_count,
            "expected_feature_count": projection.expected_feature_count,
            "source_type": projection.source_type,
            "invalid_observation_count": projection.invalid_observation_count,
            "duplicate_timestamp_count": projection.duplicate_timestamp_count,
            "pull_completeness": projection.pull_completeness,
            "reference_row_count": projection.reference_row_count,
            "reference_session_count": projection.reference_session_count,
            "omitted_count": projection.omitted_count,
        }
        projected_facts = [
            Fact(
                path=f"/prediction/{key}",
                value=value,
                unit=(
                    "engineering_validation_score"
                    if key in {"score", "threshold"} and projection.horizon.value == "NEXT_PULL"
                    else "detector_specific_nonprobability_score"
                    if key in {"score", "threshold"}
                    and projection.horizon.value == "AFTER_PULL_OFFLINE"
                    else None
                ),
            )
            for key, value in values.items()
            if value is None or type(value) in {str, bool, int, float}
        ]
        for index, reason in enumerate(projection.verification_reasons[:16]):
            if reason.isascii() and reason.replace("_", "").replace("-", "").isalnum():
                projected_facts.append(
                    Fact(path=f"/prediction/verification_reasons/{index}", value=reason)
                )
        for key, count in sorted(projection.missing_reason_counts.items()):
            if not key.isascii() or not key.replace("_", "").isalnum() or len(key) > 48:
                warnings.append("prediction_projection_omitted")
                continue
            projected_facts.append(
                Fact(path=f"/prediction/missing_reason_counts/{key}", value=count)
            )
        for index, signal in enumerate(projection.available_signals):
            projected_facts.append(
                Fact(path=f"/prediction/available_signals/{index}", value=signal)
            )
        for index, gap in enumerate(projection.gaps[:16]):
            projected_facts.append(Fact(path=f"/prediction/gaps/{index}", value=gap))
        for item in projection.facts:
            projected_facts.append(
                Fact(
                    path=f"/prediction/features/{item.key}",
                    value=item.value,
                    unit=item.unit,
                )
            )
            projected_facts.extend(
                [
                    Fact(
                        path=f"/prediction/feature_quality/{item.key}",
                        value=item.quality.value,
                    ),
                    Fact(
                        path=f"/prediction/feature_cutoff/{item.key}",
                        value=item.cutoff.isoformat(),
                    ),
                ]
            )
            if item.observed_at is not None:
                projected_facts.append(
                    Fact(
                        path=f"/prediction/feature_observed_at/{item.key}",
                        value=item.observed_at.isoformat(),
                    )
                )
            if item.available_at is not None:
                projected_facts.append(
                    Fact(
                        path=f"/prediction/feature_available_at/{item.key}",
                        value=item.available_at.isoformat(),
                    )
                )
        if len(projected_facts) > 160:
            projected_facts = projected_facts[:160]
            warnings.append("prediction_projection_omitted")

        safe_projection = {
            "schema_version": projection.schema_version,
            "result_type": projection.result_type.value,
            "horizon": projection.horizon.value,
            "task": projection.task,
            "family": projection.family,
            "source_role": projection.source_role.value,
            "effective_cutoff": projection.effective_cutoff.isoformat(),
            "status": projection.status,
            "score": projection.score,
            "threshold": projection.threshold,
            "completeness": projection.completeness.value,
            "integrity": projection.integrity.value,
            "quality_class": projection.quality_class,
            "facts": [item.model_dump(mode="json") for item in projected_facts],
        }
        evidence = Evidence(
            id=evidence_id,
            run_id=self.run_id,
            vehicle_id=self.vehicle_id,
            evidence_type="predictive_evidence",
            source_tool="get_prediction_evidence",
            tool_call_id=call_id,
            source_fingerprint=canonical_hash(safe_projection),
            summary=(
                f"Registered {projection.horizon.value} predictive evidence; "
                f"source role {projection.source_role.value}; status {projection.status}."
            ),
            facts=projected_facts,
            provenance={
                "projection": projection.schema_version,
                "horizon": projection.horizon.value,
                "source_role": projection.source_role.value,
                "effective_cutoff": projection.effective_cutoff.isoformat(),
                "integrity": projection.integrity.value,
                "completeness": projection.completeness.value,
            },
            warnings=list(dict.fromkeys(warnings))[:16],
            truncated=projection.omitted_count > 0 or len(projected_facts) == 160,
        )
        self.items[evidence.id] = evidence
        self.prediction_links.append(
            PredictionEvidenceLink(
                run_evidence_id=evidence.id,
                source_evidence_id=projection.evidence_id,
                receipt_id=projection.receipt_id,
                source_vehicle_id=projection.source_vehicle_id,
                source_session_id=projection.source_session_id,
                source_pull_id=projection.source_pull_id,
                source_configuration_id=projection.source_configuration_id,
                source_feature_set_id=projection.source_feature_set_id,
                result_type=projection.result_type.value,
                horizon=projection.horizon.value,
                task=projection.task,
                family=projection.family,
                model_version=projection.model_version,
                model_algorithm=projection.model_algorithm,
                detector_version=projection.detector_version,
                detector_algorithm_version=projection.detector_algorithm_version,
                detector_method=projection.detector_method,
                source_role=projection.source_role.value,
                effective_cutoff=projection.effective_cutoff,
                integrity=projection.integrity.value,
                completeness=projection.completeness.value,
                artifact_availability=projection.artifact_availability.value,
                projection_version=projection.schema_version,
            )
        )
        return [evidence]

    def check_ownership(self, value: Any, depth: int = 0) -> None:
        if depth > 16:
            raise AgentError("invalid_tool_result")
        if isinstance(value, dict):
            for identity_key in (
                "vehicle_id",
                "source_vehicle_id",
                "pull_vehicle_id",
                "session_vehicle_id",
            ):
                if value.get(identity_key) is not None and str(value[identity_key]) != str(
                    self.vehicle_id
                ):
                    raise AgentError("incompatible_context")
            for child in value.values():
                self.check_ownership(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                self.check_ownership(child, depth + 1)
