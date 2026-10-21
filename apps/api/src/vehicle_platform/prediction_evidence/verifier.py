"""Independent bounded verifier for stored 9E bundles against current source records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid5

from vehicle_platform.prediction_evidence.canonical import (
    EVIDENCE_NAMESPACE,
    canonical_json,
    evidence_content_payload,
    evidence_identity_payload,
    sha256,
)
from vehicle_platform.prediction_evidence.domain import (
    ArtifactAvailability,
    EvidenceCompleteness,
    EvidenceFactType,
    EvidenceIntegrity,
    EvidenceSourceSnapshot,
    PredictionEvidenceBundle,
    SourceKind,
)
from vehicle_platform.predictions.domain import PredictionResponse


def verify_bundle_sources(
    bundle: PredictionEvidenceBundle,
    current: EvidenceSourceSnapshot,
) -> tuple[EvidenceIntegrity, list[str]]:
    errors: list[str] = []
    unverifiable: list[str] = []
    if sha256(evidence_content_payload(bundle)) != bundle.content_checksum:
        errors.append("BUNDLE_CONTENT_CHECKSUM_MISMATCH")
    logical = sha256(evidence_identity_payload(bundle))
    if (
        logical != bundle.logical_fingerprint
        or uuid5(EVIDENCE_NAMESPACE, logical) != bundle.evidence_id
    ):
        errors.append("BUNDLE_IDENTITY_MISMATCH")
    if current.response.schema_version != "phase9d-prediction-response-v1":
        return EvidenceIntegrity.UNSUPPORTED_SCHEMA, ["RECEIPT_SCHEMA_UNSUPPORTED"]
    if (
        current.receipt.entity_id != bundle.receipt_id
        or current.response.receipt_id != bundle.receipt_id
    ):
        errors.append("RECEIPT_ID_MISMATCH")
    if not _prediction_equal(bundle, current.response):
        errors.append("RESPONSE_BINDING_MISMATCH")
    if (
        current.response.result_type != bundle.result_type.value
        or current.response.horizon != bundle.horizon.value
    ):
        errors.append("HORIZON_OR_KIND_MISMATCH")
    if current.response.source_role != bundle.source_role:
        errors.append("SOURCE_ROLE_MISMATCH")
    current_cutoff = (
        current.response.effective_cutoff or current.response.requested_cutoff
    ).astimezone(UTC)
    if current_cutoff != bundle.effective_cutoff:
        errors.append("CUTOFF_MISMATCH")
    if current.integrity is EvidenceIntegrity.FAILED_SOURCE_MISMATCH:
        errors.extend(code.value for code in current.gaps)
    if current.integrity is EvidenceIntegrity.UNSUPPORTED_SCHEMA:
        return EvidenceIntegrity.UNSUPPORTED_SCHEMA, [code.value for code in current.gaps]

    records = current.records
    node_by_kind = {node.source_kind: node for node in bundle.nodes}
    if len(node_by_kind) != len(bundle.nodes):
        errors.append("DUPLICATE_SOURCE_NODE_KIND")
    receipt_node = node_by_kind.get(SourceKind.PREDICTION_RECEIPT)
    if receipt_node is None or receipt_node.source_entity_id != bundle.receipt_id:
        errors.append("ROOT_RECEIPT_REFERENCE_MISMATCH")
    manifest = [
        {
            "kind": node.source_kind.value,
            "entity_id": str(node.source_entity_id),
            "checksum": node.source_checksum,
            "schema_checksum": node.source_schema_checksum,
        }
        for node in sorted(bundle.nodes, key=lambda item: item.source_kind.value)
    ]
    if sha256(manifest) != bundle.provenance_manifest_checksum:
        errors.append("PROVENANCE_MANIFEST_CHECKSUM_MISMATCH")
    for kind, node in node_by_kind.items():
        record = records.get(kind)
        if record is None:
            unverifiable.append(f"SOURCE_UNAVAILABLE_{kind.value.upper()}")
        elif record.entity_id != node.source_entity_id:
            errors.append(f"SOURCE_ID_MISMATCH_{kind.value.upper()}")
        elif record.checksum != node.source_checksum:
            errors.append(f"SOURCE_CHECKSUM_MISMATCH_{kind.value.upper()}")
        elif record.schema_checksum != node.source_schema_checksum:
            errors.append(f"SOURCE_SCHEMA_CHECKSUM_MISMATCH_{kind.value.upper()}")
    for kind in records:
        if kind not in node_by_kind:
            errors.append(f"UNBOUND_SOURCE_RECORD_{kind.value.upper()}")

    if not _rooted_acyclic_graph(bundle):
        errors.append("GRAPH_NOT_ROOTED_OR_CYCLIC")
    if not _facts_bind_source(bundle, current):
        errors.append("FACT_SOURCE_VALUE_MISMATCH")
    if not _prediction_decision_consistent(current.response):
        errors.append("MODEL_SCORE_DECISION_MISMATCH")
    if bundle.source_summary.source_role != current.response.source_role:
        errors.append("QUALITY_SOURCE_ROLE_MISMATCH")
    if bundle.source_summary.quality_class != current.response.quality.quality_class:
        errors.append("QUALITY_CLASS_MISMATCH")
    if abs(bundle.source_summary.receipt_coverage - current.response.quality.coverage) > 1e-12:
        errors.append("QUALITY_COVERAGE_MISMATCH")
    if not all(
        fact.cutoff_eligible and fact.cutoff <= bundle.effective_cutoff for fact in bundle.facts
    ):
        errors.append("FACT_CUTOFF_INELIGIBLE")
    if bundle.completeness is EvidenceCompleteness.COMPLETE and (
        current.response.status.value != "READY_SCORE"
        or bundle.integrity
        not in {
            EvidenceIntegrity.VERIFIED,
            EvidenceIntegrity.VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE,
        }
        or bundle.source_summary.quality_class != "high"
    ):
        errors.append("COMPLETENESS_UPGRADE")
    if errors:
        return EvidenceIntegrity.FAILED_SOURCE_MISMATCH, sorted(set(errors))[:16]
    if current.integrity is EvidenceIntegrity.NOT_VERIFIABLE or unverifiable:
        return EvidenceIntegrity.NOT_VERIFIABLE, sorted(
            set(unverifiable + [code.value for code in current.gaps])
        )[:16]
    if current.artifact_availability is ArtifactAvailability.CHECKSUM_MISMATCH:
        return EvidenceIntegrity.FAILED_SOURCE_MISMATCH, ["ARTIFACT_CHECKSUM_MISMATCH"]
    if current.artifact_availability is ArtifactAvailability.UNAVAILABLE:
        return EvidenceIntegrity.VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE, ["ARTIFACT_UNAVAILABLE"]
    return EvidenceIntegrity.VERIFIED, []


def _prediction_equal(bundle: PredictionEvidenceBundle, response: PredictionResponse) -> bool:
    expected_score = (
        response.engineering_validation_score
        if response.result_type == "next_pull"
        else response.anomaly_score
    )
    expected = {
        "status": response.status.value,
        "reason_code": response.reason_code,
        "score": expected_score,
        "threshold": response.threshold,
        "decision": response.decision,
        "score_is_probability": False,
    }
    actual = bundle.prediction.model_dump(mode="json")
    if actual.get("score") is not None and expected_score is not None:
        try:
            if abs(float(actual["score"]) - expected_score) > 1e-12:
                return False
        except (TypeError, ValueError):
            return False
        actual["score"] = expected_score
    if actual.get("threshold") is not None and response.threshold is not None:
        try:
            if abs(float(actual["threshold"]) - response.threshold) > 1e-12:
                return False
        except (TypeError, ValueError):
            return False
        actual["threshold"] = response.threshold
    return canonical_json(actual) == canonical_json(expected)


def _prediction_decision_consistent(response: PredictionResponse) -> bool:
    if response.status.value != "READY_SCORE":
        return (
            response.decision is None
            and response.engineering_validation_score is None
            and response.anomaly_score is None
        )
    if response.threshold is None or response.decision is None:
        return False
    if response.result_type == "next_pull":
        score = response.engineering_validation_score
        return (
            score is not None
            and 0 <= score <= 1
            and response.decision is (score >= response.threshold)
        )
    score = response.anomaly_score
    expected = "ANOMALOUS" if score is not None and score > response.threshold else "INLIER"
    return score is not None and str(response.decision) == expected


def _rooted_acyclic_graph(bundle: PredictionEvidenceBundle) -> bool:
    nodes = {node.node_id for node in bundle.nodes}
    root: str = bundle.root_node_id
    if root not in nodes:
        return False
    adjacency: dict[str, list[str]] = {node: [] for node in nodes}
    for edge in bundle.edges:
        if edge.source_node_id not in nodes or edge.target_node_id not in nodes:
            return False
        adjacency[edge.source_node_id].append(edge.target_node_id)
    edge_tuples = [
        (edge.source_node_id, edge.target_node_id, edge.relation.value) for edge in bundle.edges
    ]
    if len(edge_tuples) != len(set(edge_tuples)):
        return False
    reachable = {root}
    stack = [root]
    while stack:
        current = stack.pop()
        for target in adjacency[current]:
            if target not in reachable:
                reachable.add(target)
                stack.append(target)
    if reachable != nodes:
        return False
    active: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in active:
            return False
        if node in visited:
            return True
        active.add(node)
        for child in adjacency[node]:
            if not visit(child):
                return False
        active.remove(node)
        visited.add(node)
        return True

    return visit(root)


def _facts_bind_source(bundle: PredictionEvidenceBundle, current: EvidenceSourceSnapshot) -> bool:
    node_map = {node.node_id: node for node in bundle.nodes}
    feature_record = current.records.get(SourceKind.FEATURE_SET)
    feature_values = feature_record.payload.get("feature_values", {}) if feature_record else {}
    anomaly = current.records.get(SourceKind.ANOMALY_FINDING)
    contributions = anomaly.payload.get("contributions", []) if anomaly else []
    reference = current.records.get(SourceKind.REFERENCE_DATASET)
    for fact in bundle.facts:
        source_node = node_map.get(fact.source_node_id)
        if source_node is None:
            return False
        if source_node.source_kind not in current.records:
            continue
        if fact.fact_type is EvidenceFactType.COMPUTED_FEATURE:
            if not isinstance(feature_values, dict):
                return False
            source = feature_values.get(fact.key)
            if not isinstance(source, dict) or canonical_json(
                source.get("value")
            ) != canonical_json(fact.value):
                return False
            if source.get("unit") != fact.unit or not _feature_quality_matches(
                source, fact.quality.value
            ):
                return False
        elif fact.fact_type in {
            EvidenceFactType.SOURCE_MEASUREMENT,
            EvidenceFactType.STATISTICAL_REFERENCE,
        } and fact.key.startswith("prediction."):
            continue
        elif fact.fact_type is EvidenceFactType.STATISTICAL_REFERENCE and fact.key.startswith(
            "reference."
        ):
            if anomaly is None:
                return False
            summary = anomaly.payload.get("reference_summary", {})
            metadata = reference.payload if reference else {}
            property_name = fact.key.removeprefix("reference.")
            if not isinstance(summary, dict):
                return False
            expected = summary.get(property_name)
            if expected is None and property_name == "row_count":
                expected = summary.get("eligible_count")
            if property_name in {"row_count", "session_count"}:
                if not metadata or metadata.get(property_name) != expected:
                    return False
            elif property_name == "observation_cutoff":
                from_summary = _aware_datetime(expected)
                from_reference = _aware_datetime(metadata.get("reference_cutoff"))
                from_fact = _aware_datetime(fact.value)
                if (
                    from_summary is None
                    or from_reference is None
                    or from_fact is None
                    or from_summary != from_reference
                    or from_fact != from_reference
                    or from_reference > bundle.effective_cutoff
                    or fact.observed_at != from_reference
                ):
                    return False
            if canonical_json(expected) != canonical_json(fact.value):
                return False
        elif (
            fact.fact_type
            in {EvidenceFactType.SOURCE_MEASUREMENT, EvidenceFactType.STATISTICAL_REFERENCE}
            and anomaly
        ):
            if not _contribution_fact_matches(fact.key, fact.value, contributions):
                return False
        elif fact.key == "prediction.status" and fact.value != current.response.status.value:
            return False
        elif fact.key == "prediction.score":
            score = (
                current.response.engineering_validation_score
                if current.response.result_type == "next_pull"
                else current.response.anomaly_score
            )
            if score is None or abs(float(fact.value) - score) > 1e-12:
                return False
        elif fact.key == "prediction.threshold":
            if (
                current.response.threshold is None
                or abs(float(fact.value) - current.response.threshold) > 1e-12
            ):
                return False
        elif fact.key == "prediction.decision" and str(fact.value) != str(
            current.response.decision
        ):
            return False
    return True


def _feature_quality_matches(source: dict[str, Any], quality: str) -> bool:
    actual = str(source.get("quality", "")).upper()
    mapping = {
        "VALID": "VALID",
        "LIMITED": "LIMITED",
        "UNAVAILABLE": "MISSING",
        "INVALID": "INVALID",
    }
    return mapping.get(actual) == quality


def _aware_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return (
            value.astimezone(UTC)
            if value.tzinfo is not None and value.utcoffset() is not None
            else None
        )
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return (
            parsed.astimezone(UTC)
            if parsed.tzinfo is not None and parsed.utcoffset() is not None
            else None
        )
    return None


def _contribution_fact_matches(key: str, value: Any, contributions: Any) -> bool:
    if not isinstance(contributions, list):
        return False
    parts = key.rsplit(".", 1)
    if len(parts) != 2:
        return False
    feature_key, metric = parts
    if metric == "normalized_deviation":
        source_metric = "normalized_deviation"
    elif metric == "signed_robust_deviation":
        source_metric = "signed_robust_deviation"
    else:
        source_metric = metric
    for item in contributions:
        if isinstance(item, dict) and item.get("feature_key") == feature_key:
            recorded = item.get(source_metric)
            if isinstance(value, (int, float)) and isinstance(recorded, (int, float)):
                return abs(float(value) - float(recorded)) <= 1e-12
            return canonical_json(value) == canonical_json(recorded)
    return False
