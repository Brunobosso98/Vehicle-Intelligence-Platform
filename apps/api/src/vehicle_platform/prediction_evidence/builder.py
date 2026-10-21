"""Deterministic pure builders for bounded evidence and safe operator projections."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import UUID, uuid5

from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.prediction_evidence.canonical import (
    EVIDENCE_NAMESPACE,
    canonical_json,
    evidence_content_payload,
    evidence_identity_payload,
    sha256,
)
from vehicle_platform.prediction_evidence.domain import (
    MAX_EVIDENCE_FACTS,
    MAX_EVIDENCE_GAPS,
    MAX_EVIDENCE_JSON_BYTES,
    PREDICTION_EVIDENCE_PROJECTION,
    PREDICTION_EVIDENCE_SCHEMA,
    PREDICTION_EVIDENCE_VERIFIER,
    ClaimBinding,
    ClaimCategory,
    ClaimScope,
    ClaimTemplate,
    ClaimValidation,
    EvidenceCompleteness,
    EvidenceEdge,
    EvidenceEdgeType,
    EvidenceFact,
    EvidenceFactType,
    EvidenceGap,
    EvidenceGapCode,
    EvidenceHorizon,
    EvidenceIntegrity,
    EvidenceNode,
    EvidenceNodeType,
    EvidenceResultKind,
    EvidenceSourceSnapshot,
    EvidenceSourceSummary,
    FactQuality,
    PredictionEvidenceBundle,
    PredictionEvidenceProjection,
    ProjectionClass,
    SourceKind,
    SourceTrustRole,
)

_LIMITATIONS = [
    "This record preserves the engineering output and source lineage; it is not a diagnosis.",
    "Model scores are not calibrated mechanical failure probabilities or confidence values.",
    "Source hashes establish consistency with the trusted database snapshot, not authenticity.",
]


def build_evidence(
    source: EvidenceSourceSnapshot,
    *,
    generated_at: datetime,
) -> PredictionEvidenceBundle:
    response = source.response
    receipt = source.receipt
    payloads = source.records
    if response.schema_version != "phase9d-prediction-response-v1":
        raise ValueError("unsupported original prediction response schema")
    if response.effective_cutoff is None:
        cutoff = response.requested_cutoff.astimezone(UTC)
    else:
        cutoff = response.effective_cutoff.astimezone(UTC)
    role = response.source_role
    kind = EvidenceResultKind(response.result_type)
    horizon = EvidenceHorizon(response.horizon)
    nodes: list[EvidenceNode] = []
    edges: list[EvidenceEdge] = []
    facts: list[EvidenceFact] = []
    gaps = [EvidenceGap(code=code) for code in source.gaps]
    claims: list[ClaimBinding] = []
    if response.status.value != "READY_SCORE":
        gaps.append(
            EvidenceGap(code=EvidenceGapCode.INPUT_ABSTAINED, reason_code=response.reason_code)
        )
        reason_gap = {
            "FEATURE_SET_UNAVAILABLE": EvidenceGapCode.NO_FEATURE_SET,
            "FUEL_PRESSURE_SIGNAL_UNAVAILABLE": EvidenceGapCode.SIGNAL_UNAVAILABLE,
            "INPUT_QUALITY_BELOW_SERVING_FLOOR": EvidenceGapCode.LOW_QUALITY,
            "ABSTAINED_INSUFFICIENT_REFERENCE": EvidenceGapCode.REFERENCE_INSUFFICIENT,
            "ABSTAINED_INCOMPATIBLE_CONTEXT": EvidenceGapCode.CONTEXT_INCOMPATIBLE,
            "ABSTAINED_UNSUPPORTED_SOURCE": EvidenceGapCode.UNSUPPORTED_SOURCE,
            "ABSTAINED_CUTOFF": EvidenceGapCode.CUTOFF_MISMATCH,
        }.get(response.reason_code or "")
        if reason_gap is not None:
            gaps.append(EvidenceGap(code=reason_gap, reason_code=response.reason_code))
    root_id = "receipt"

    def add_node(
        node_id: str,
        node_type: EvidenceNodeType,
        source_kind: SourceKind,
        *,
        trust: SourceTrustRole,
        projection: ProjectionClass,
    ) -> str | None:
        record = payloads.get(source_kind)
        if record is None:
            gaps.append(EvidenceGap(code=EvidenceGapCode.EVIDENCE_SOURCE_MISSING))
            return None
        valid_from = _datetime(record.payload.get("valid_from"))
        valid_through = _datetime(record.payload.get("valid_through"))
        nodes.append(
            EvidenceNode(
                node_id=node_id,
                node_type=node_type,
                source_kind=source_kind,
                source_entity_id=record.entity_id,
                source_checksum=record.checksum,
                source_schema_checksum=record.schema_checksum,
                valid_from=valid_from,
                valid_through=valid_through,
                trust_role=trust,
                projection_class=projection,
            )
        )
        return node_id

    def add_edge(source_id: str, target_id: str, relation: EvidenceEdgeType) -> None:
        edge_id = f"edge-{len(edges):02d}"
        edges.append(
            EvidenceEdge(
                edge_id=edge_id,
                source_node_id=source_id,
                target_node_id=target_id,
                relation=relation,
            )
        )

    add_node(
        root_id,
        EvidenceNodeType.PREDICTION_RECEIPT,
        SourceKind.PREDICTION_RECEIPT,
        trust=SourceTrustRole.IMMUTABLE_SOURCE,
        projection=ProjectionClass.OPERATOR_RESULT,
    )
    link_specs = [
        (
            "binding",
            EvidenceNodeType.SERVING_BINDING,
            SourceKind.SERVING_BINDING,
            EvidenceEdgeType.SELECTED_BY,
        ),
        (
            "event",
            EvidenceNodeType.APPROVAL_EVENT,
            SourceKind.APPROVAL_EVENT,
            EvidenceEdgeType.SUPPORTED_BY,
        ),
        (
            "feature-set",
            EvidenceNodeType.FEATURE_SET,
            SourceKind.FEATURE_SET,
            EvidenceEdgeType.DERIVED_FROM,
        ),
        (
            "feature-version",
            EvidenceNodeType.FEATURE_VERSION,
            SourceKind.FEATURE_VERSION,
            EvidenceEdgeType.LIMITED_BY,
        ),
        (
            "model",
            EvidenceNodeType.MODEL_VERSION,
            SourceKind.MODEL_VERSION,
            EvidenceEdgeType.SCORED_WITH,
        ),
        (
            "detector",
            EvidenceNodeType.DETECTOR_VERSION,
            SourceKind.DETECTOR_VERSION,
            EvidenceEdgeType.SCORED_WITH,
        ),
        (
            "anomaly-run",
            EvidenceNodeType.ANOMALY_RUN,
            SourceKind.ANOMALY_RUN,
            EvidenceEdgeType.DERIVED_FROM,
        ),
        (
            "finding",
            EvidenceNodeType.ANOMALY_FINDING,
            SourceKind.ANOMALY_FINDING,
            EvidenceEdgeType.OBSERVED_IN,
        ),
        (
            "reference",
            EvidenceNodeType.REFERENCE_DATASET,
            SourceKind.REFERENCE_DATASET,
            EvidenceEdgeType.COMPARED_AGAINST,
        ),
    ]
    node_ids: dict[SourceKind, str] = {}
    for node_id, node_type, source_kind, relation in link_specs:
        if source_kind not in payloads:
            continue
        trust = (
            SourceTrustRole.IMMUTABLE_SOURCE
            if source_kind
            in {SourceKind.APPROVAL_EVENT, SourceKind.ANOMALY_RUN, SourceKind.ANOMALY_FINDING}
            else SourceTrustRole.VERSIONED_SOURCE
        )
        projection = (
            ProjectionClass.INTERNAL_SOURCE
            if source_kind in {SourceKind.SERVING_BINDING, SourceKind.APPROVAL_EVENT}
            else ProjectionClass.INTERNAL_LINEAGE
        )
        added = add_node(node_id, node_type, source_kind, trust=trust, projection=projection)
        if added:
            node_ids[source_kind] = added
            add_edge(root_id, added, relation)
    if SourceKind.FEATURE_VERSION in node_ids and SourceKind.FEATURE_SET in node_ids:
        add_edge(
            node_ids[SourceKind.FEATURE_SET],
            node_ids[SourceKind.FEATURE_VERSION],
            EvidenceEdgeType.LIMITED_BY,
        )
    if SourceKind.MODEL_VERSION in node_ids and SourceKind.FEATURE_VERSION in node_ids:
        add_edge(
            node_ids[SourceKind.MODEL_VERSION],
            node_ids[SourceKind.FEATURE_VERSION],
            EvidenceEdgeType.SELECTED_BY,
        )
    if SourceKind.DETECTOR_VERSION in node_ids and SourceKind.REFERENCE_DATASET in node_ids:
        add_edge(
            node_ids[SourceKind.DETECTOR_VERSION],
            node_ids[SourceKind.REFERENCE_DATASET],
            EvidenceEdgeType.COMPARED_AGAINST,
        )
    if SourceKind.ANOMALY_FINDING in node_ids and SourceKind.ANOMALY_RUN in node_ids:
        add_edge(
            node_ids[SourceKind.ANOMALY_FINDING],
            node_ids[SourceKind.ANOMALY_RUN],
            EvidenceEdgeType.DERIVED_FROM,
        )

    feature_record = payloads.get(SourceKind.FEATURE_SET)
    feature_values = feature_record.payload.get("feature_values", {}) if feature_record else {}
    quality = response.quality
    if feature_record is not None:
        features = _eligible_feature_keys(source, feature_values)
        for ordinal, key in enumerate(features[:24]):
            raw = feature_values.get(key)
            if not isinstance(raw, dict):
                gaps.append(
                    EvidenceGap(
                        code=EvidenceGapCode.PROVENANCE_MISMATCH, source_node_id="feature-set"
                    )
                )
                continue
            value = raw.get("value")
            feature_quality = str(raw.get("quality", "invalid")).lower()
            missing_reason = raw.get("missing_reason")
            unit = raw.get("unit")
            definition = _feature_definition(key)
            if definition is None or unit != definition.unit:
                gaps.append(
                    EvidenceGap(
                        code=EvidenceGapCode.SOURCE_SCHEMA_MISMATCH,
                        source_node_id="feature-set",
                        reason_code="FEATURE_UNIT_OR_KEY_UNSUPPORTED",
                    )
                )
                continue
            raw_times = {
                "observed_at": _nested(raw, "details", "observed_at"),
                "available_at": raw.get("available_at"),
                "source_window_start": raw.get("source_window_start"),
                "source_window_end": raw.get("source_window_end"),
            }
            parsed_times = {key: _datetime(value) for key, value in raw_times.items()}
            if any(raw_times[key] is not None and parsed_times[key] is None for key in raw_times):
                gaps.append(
                    EvidenceGap(
                        code=EvidenceGapCode.SOURCE_SCHEMA_MISMATCH,
                        source_node_id="feature-set",
                        reason_code="FEATURE_TIME_NAIVE_OR_INVALID",
                    )
                )
                continue
            observed_at = parsed_times["observed_at"]
            available_at = parsed_times["available_at"]
            window_start = parsed_times["source_window_start"]
            window_end = parsed_times["source_window_end"]
            if window_start is not None and window_end is not None and window_start > window_end:
                gaps.append(
                    EvidenceGap(
                        code=EvidenceGapCode.SOURCE_SCHEMA_MISMATCH,
                        source_node_id="feature-set",
                        reason_code="FEATURE_WINDOW_INVERTED",
                    )
                )
                continue
            if any(
                item is not None and item > cutoff
                for item in (observed_at, available_at, window_start, window_end)
            ):
                gaps.append(
                    EvidenceGap(
                        code=EvidenceGapCode.FEATURE_NOT_YET_OBSERVED,
                        source_node_id="feature-set",
                        reason_code="FEATURE_TIME_AFTER_CUTOFF",
                    )
                )
                continue
            q = _fact_quality(feature_quality, value)
            node_id = node_ids.get(SourceKind.FEATURE_SET, root_id)
            facts.append(
                EvidenceFact(
                    fact_id=f"feature-{ordinal:02d}",
                    key=key,
                    fact_type=EvidenceFactType.COMPUTED_FEATURE,
                    value=value,
                    unit=unit,
                    source_node_id=node_id,
                    cutoff=cutoff,
                    cutoff_eligible=True,
                    quality=q,
                    missing_reason=str(missing_reason) if missing_reason else None,
                    observed_at=observed_at,
                    available_at=available_at,
                    source_window_start=window_start,
                    source_window_end=window_end,
                    ordinal=ordinal,
                    meaning=(
                        f"Recorded Phase 9A feature {key}; this is an input feature, "
                        "not an observed future outcome."
                    ),
                )
            )
    elif response.status.value == "READY_SCORE":
        gaps.append(EvidenceGap(code=EvidenceGapCode.NO_FEATURE_SET))

    missing_reason_counts = {
        str(key): int(value)
        for key, value in response.quality.missing_reason_counts.items()
        if isinstance(key, str) and 0 <= value <= 128
    }
    for index, (reason, count) in enumerate(sorted(missing_reason_counts.items())):
        facts.append(
            EvidenceFact(
                fact_id=f"quality-missing-{index:02d}",
                key=f"quality.missing_reason.{reason}",
                fact_type=EvidenceFactType.QUALITY_INDICATOR,
                value=count,
                source_node_id=node_ids.get(SourceKind.FEATURE_SET, root_id),
                cutoff=cutoff,
                cutoff_eligible=True,
                quality=FactQuality.VALID,
                ordinal=len(facts),
                meaning="Count from the immutable 9D input quality summary.",
            )
        )

    if kind is EvidenceResultKind.NEXT_PULL:
        model_record = payloads.get(SourceKind.MODEL_VERSION)
        schema = model_record.payload.get("input_schema", {}) if model_record else {}
        label = model_record.payload.get("label_definition", {}) if model_record else {}
        facts.extend(_model_output_facts(response, root_id, cutoff, len(facts), label))
        if model_record and isinstance(schema, dict):
            associations = schema.get("feature_importance", [])
            # Model-level importance is recorded only as metadata, not per-instance attribution.
            if associations:
                facts.append(
                    EvidenceFact(
                        fact_id=f"association-{len(facts):02d}",
                        key="model.feature_importance_available",
                        fact_type=EvidenceFactType.INTERPRETATION_LIMIT,
                        value=True,
                        source_node_id=node_ids.get(SourceKind.MODEL_VERSION, root_id),
                        cutoff=cutoff,
                        cutoff_eligible=True,
                        quality=FactQuality.LIMITED,
                        ordinal=len(facts),
                        meaning=(
                            "Versioned model-level associations are not per-prediction attribution."
                        ),
                    )
                )
        claim_ids = [
            fact.fact_id for fact in facts if fact.fact_type is EvidenceFactType.MODEL_OUTPUT
        ]
        if claim_ids:
            abstained = response.status.value != "READY_SCORE"
            claims.append(
                ClaimBinding(
                    claim_id="claim-result",
                    template=(
                        ClaimTemplate.ABSTENTION if abstained else ClaimTemplate.NEXT_PULL_RESULT
                    ),
                    category=(
                        ClaimCategory.ABSTENTION if abstained else ClaimCategory.MODEL_OUTPUT
                    ),
                    fact_ids=claim_ids[:3],
                    expected_value=response.status.value,
                    cutoff=cutoff,
                    scope=ClaimScope(
                        result_type=kind, horizon=horizon, source_role=role, cutoff=cutoff
                    ),
                    validation=ClaimValidation.CONSISTENT,
                )
            )
        task = response.task.value if response.task else None
        family = None
        interpretation = _supervised_interpretation(response, task, label)
    else:
        task = None
        family = response.family
        anomaly = payloads.get(SourceKind.ANOMALY_FINDING)
        if anomaly:
            anomaly_payload = anomaly.payload
            contributions = anomaly_payload.get("contributions", [])
            facts.extend(_anomaly_facts(contributions, node_ids, cutoff, len(facts)))
            reference = anomaly_payload.get("reference_summary", {})
            if isinstance(reference, dict):
                for key in ("row_count", "session_count", "observation_cutoff"):
                    value = reference.get(key)
                    if value is None:
                        continue
                    observed_at = _datetime(value) if key == "observation_cutoff" else None
                    if key == "observation_cutoff" and (
                        observed_at is None or observed_at > cutoff
                    ):
                        gaps.append(
                            EvidenceGap(
                                code=EvidenceGapCode.SOURCE_SCHEMA_MISMATCH,
                                source_node_id="reference",
                                reason_code="REFERENCE_CUTOFF_NAIVE_OR_INVALID",
                            )
                        )
                        continue
                    facts.append(
                        EvidenceFact(
                            fact_id=f"reference-{len(facts):02d}",
                            key=f"reference.{key}",
                            fact_type=EvidenceFactType.STATISTICAL_REFERENCE,
                            value=value,
                            source_node_id=node_ids.get(SourceKind.REFERENCE_DATASET, root_id),
                            cutoff=cutoff,
                            cutoff_eligible=True,
                            quality=FactQuality.VALID,
                            ordinal=len(facts),
                            observed_at=observed_at,
                            meaning="Frozen 9C reference cohort summary; not an OEM target.",
                        )
                    )
        result_facts = _model_output_facts(response, root_id, cutoff, len(facts), {})
        result_fact_ids = [fact.fact_id for fact in result_facts]
        facts.extend(result_facts)
        if result_fact_ids:
            abstained = response.status.value != "READY_SCORE"
            claims.append(
                ClaimBinding(
                    claim_id="claim-result",
                    template=(
                        ClaimTemplate.ABSTENTION if abstained else ClaimTemplate.ANOMALY_RESULT
                    ),
                    category=(
                        ClaimCategory.ABSTENTION if abstained else ClaimCategory.MODEL_OUTPUT
                    ),
                    fact_ids=result_fact_ids[:4],
                    expected_value=response.status.value,
                    cutoff=cutoff,
                    scope=ClaimScope(
                        result_type=kind, horizon=horizon, source_role=role, cutoff=cutoff
                    ),
                    validation=ClaimValidation.CONSISTENT,
                )
            )
        claim_ids = [
            fact.fact_id
            for fact in facts
            if fact.fact_type
            in {EvidenceFactType.STATISTICAL_REFERENCE, EvidenceFactType.SOURCE_MEASUREMENT}
        ]
        if claim_ids and response.status.value == "READY_SCORE":
            claims.append(
                ClaimBinding(
                    claim_id="claim-deviation",
                    template=ClaimTemplate.FEATURE_ASSOCIATION,
                    category=ClaimCategory.STATISTICAL_ASSOCIATION,
                    fact_ids=claim_ids[:8],
                    expected_value="descriptive deviation against frozen reference",
                    cutoff=cutoff,
                    scope=ClaimScope(
                        result_type=kind, horizon=horizon, source_role=role, cutoff=cutoff
                    ),
                    validation=ClaimValidation.CONSISTENT,
                )
            )
        interpretation = _anomaly_interpretation(response, family)

    if source.integrity in {
        EvidenceIntegrity.FAILED_SOURCE_MISMATCH,
        EvidenceIntegrity.NOT_VERIFIABLE,
        EvidenceIntegrity.UNSUPPORTED_SCHEMA,
    }:
        claims = []
        interpretation = (
            "The source chain cannot support an affirmative evidence claim. "
            "The original 9D receipt is preserved with its verification gaps."
        )

    completeness = _completeness(source, response, facts, gaps)
    expected = quality.expected_feature_count
    observed_count = quality.observed_feature_count
    artifact = source.artifact_availability
    quality_metadata = feature_record.payload.get("quality_metadata", {}) if feature_record else {}
    quality_metadata = quality_metadata if isinstance(quality_metadata, dict) else {}
    available_signals = quality_metadata.get("available_signals", [])
    available_signals = (
        sorted(item for item in available_signals if isinstance(item, str))[:32]
        if isinstance(available_signals, list)
        else []
    )
    invalid_count = quality_metadata.get("invalid_observation_count")
    duplicate_count = quality_metadata.get("duplicate_timestamp_count")
    pull_completeness = quality_metadata.get("pull_completeness")
    source_summary = EvidenceSourceSummary(
        source_role=role,
        source_type=(
            str(quality_metadata["source_type"])
            if isinstance(quality_metadata.get("source_type"), str)
            else None
        ),
        quality_class=quality.quality_class,
        receipt_coverage=quality.coverage,
        feature_coverage=(observed_count / expected if expected else 0.0),
        observed_feature_count=observed_count,
        expected_feature_count=expected,
        missing_reason_counts=missing_reason_counts,
        available_signals=available_signals,
        invalid_observation_count=invalid_count if type(invalid_count) is int else None,
        duplicate_timestamp_count=duplicate_count if type(duplicate_count) is int else None,
        pull_completeness=pull_completeness
        if isinstance(pull_completeness, (int, float))
        else None,
        feature_set_available=feature_record is not None,
        reference_row_count=_optional_int(
            payloads.get(SourceKind.REFERENCE_DATASET), "row_count", 10_000
        ),
        reference_session_count=_optional_int(
            payloads.get(SourceKind.REFERENCE_DATASET), "session_count", 10_000
        ),
        artifact_availability=artifact,
    )
    source_manifest = [
        {
            "kind": record.kind.value,
            "entity_id": str(record.entity_id),
            "checksum": record.checksum,
            "schema_checksum": record.schema_checksum,
        }
        for record in sorted(payloads.values(), key=lambda item: item.kind.value)
    ]
    provenance_checksum = sha256(source_manifest)
    receipt_fingerprint = str(receipt.payload.get("request_fingerprint", ""))
    if len(receipt_fingerprint) != 64:
        receipt_fingerprint = receipt.checksum
    unique_gaps = _dedupe_gaps(gaps)
    omitted_count = max(0, len(facts) - MAX_EVIDENCE_FACTS)
    omitted_count += max(0, len(unique_gaps) - MAX_EVIDENCE_GAPS)
    retained_facts = facts[:MAX_EVIDENCE_FACTS]
    retained_fact_ids = {fact.fact_id for fact in retained_facts}
    retained_claims = [
        claim for claim in claims[:8] if set(claim.fact_ids).issubset(retained_fact_ids)
    ]
    omitted_count += len(claims) - len(retained_claims)
    facts = retained_facts
    gaps = unique_gaps[:MAX_EVIDENCE_GAPS]
    claims = retained_claims
    if omitted_count:
        if len(gaps) >= MAX_EVIDENCE_GAPS:
            gaps.pop()
            omitted_count += 1
        gaps.append(
            EvidenceGap(
                code=EvidenceGapCode.INCOMPLETE_PROJECTION,
                reason_code=f"omitted_count:{omitted_count}",
            )
        )
        if response.status.value == "READY_SCORE":
            completeness = EvidenceCompleteness.PARTIAL
    draft = PredictionEvidenceBundle(
        schema_version=cast(Literal["phase9e-prediction-evidence-v1"], PREDICTION_EVIDENCE_SCHEMA),
        projection_version=cast(
            Literal["phase9e-safe-projection-v1"], PREDICTION_EVIDENCE_PROJECTION
        ),
        verifier_policy_version=cast(
            Literal["phase9e-source-verifier-v1"], PREDICTION_EVIDENCE_VERIFIER
        ),
        evidence_id=UUID(int=0),
        receipt_id=response.receipt_id,
        receipt_fingerprint=receipt_fingerprint,
        logical_fingerprint="0" * 64,
        content_checksum="0" * 64,
        provenance_manifest_checksum=provenance_checksum,
        result_type=kind,
        horizon=horizon,
        task=task,
        family=family,
        source_role=role,
        requested_cutoff=response.requested_cutoff.astimezone(UTC),
        effective_cutoff=cutoff,
        completeness=completeness,
        integrity=source.integrity,
        prediction=_prediction(response),
        source_summary=source_summary,
        nodes=nodes,
        edges=edges,
        facts=facts,
        gaps=gaps,
        claims=claims,
        omitted_count=omitted_count,
        interpretation=interpretation,
        limitations=_LIMITATIONS,
        generated_at=generated_at.astimezone(UTC),
    )
    return rehash_bundle(draft)


def rehash_bundle(bundle: PredictionEvidenceBundle) -> PredictionEvidenceBundle:
    content_checksum = sha256(evidence_content_payload(bundle))
    logical_fingerprint = sha256(evidence_identity_payload(bundle))
    return bundle.model_copy(
        update={
            "evidence_id": uuid5(EVIDENCE_NAMESPACE, logical_fingerprint),
            "logical_fingerprint": logical_fingerprint,
            "content_checksum": content_checksum,
        }
    )


def fit_bundle_to_size(
    bundle: PredictionEvidenceBundle,
    *,
    max_bytes: int = MAX_EVIDENCE_JSON_BYTES,
) -> PredictionEvidenceBundle:
    """Drop optional records at boundaries and retain an explicit omission count."""
    current = bundle
    while len(canonical_json(current.model_dump(mode="json")).encode("utf-8")) > max_bytes:
        facts = list(current.facts)
        claims = list(current.claims)
        gaps = list(current.gaps)
        referenced = {fact_id for claim in claims for fact_id in claim.fact_ids}
        removable = [fact for fact in facts if fact.fact_id not in referenced]
        omitted = current.omitted_count
        if removable:
            removed = removable[-1]
            facts.remove(removed)
            omitted += 1
        elif claims:
            removed_claim = claims.pop()
            omitted += 1
            still_referenced = {fact_id for claim in claims for fact_id in claim.fact_ids}
            removed_facts = [
                fact
                for fact in facts
                if fact.fact_id in removed_claim.fact_ids and fact.fact_id not in still_referenced
            ]
            for fact in removed_facts:
                facts.remove(fact)
            omitted += len(removed_facts)
        elif facts:
            facts.pop()
            omitted += 1
        else:
            raise ValueError("evidence manifest cannot fit the configured size bound")

        gaps = [gap for gap in gaps if gap.code is not EvidenceGapCode.INCOMPLETE_PROJECTION]
        if len(gaps) >= MAX_EVIDENCE_GAPS:
            gaps.pop()
            omitted += 1
        gaps.append(
            EvidenceGap(
                code=EvidenceGapCode.INCOMPLETE_PROJECTION,
                reason_code=f"omitted_count:{omitted}",
            )
        )
        limitations = list(current.limitations)
        omission_note = "Optional evidence records were omitted to stay within the size bound."
        if omission_note not in limitations:
            if len(limitations) >= 12:
                limitations[-1] = omission_note
            else:
                limitations.append(omission_note)
        completeness = (
            EvidenceCompleteness.ABSTAINED
            if current.completeness is EvidenceCompleteness.ABSTAINED
            else EvidenceCompleteness.PARTIAL
        )
        current = rehash_bundle(
            current.model_copy(
                update={
                    "facts": facts,
                    "claims": claims,
                    "gaps": gaps,
                    "omitted_count": omitted,
                    "completeness": completeness,
                    "limitations": limitations,
                }
            )
        )
    return current


def render_safe_projection(bundle: PredictionEvidenceBundle) -> PredictionEvidenceProjection:
    public_facts = [
        {
            "id": item.fact_id,
            "key": item.key,
            "type": item.fact_type.value,
            "value": item.value,
            "unit": item.unit,
            "quality": item.quality.value,
            "missing_reason": item.missing_reason,
            "meaning": item.meaning,
        }
        for item in bundle.facts
    ]
    claims = [
        {
            "id": item.claim_id,
            "template": item.template.value,
            "category": item.category.value,
            "fact_ids": item.fact_ids,
            "validation": item.validation.value,
        }
        for item in bundle.claims
    ]
    return PredictionEvidenceProjection(
        schema_version=cast(Literal["phase9e-safe-projection-v1"], PREDICTION_EVIDENCE_PROJECTION),
        evidence_id=bundle.evidence_id,
        receipt_id=bundle.receipt_id,
        result_type=bundle.result_type,
        horizon=bundle.horizon,
        task=bundle.task,
        family=bundle.family,
        source_role=bundle.source_role,
        cutoff=bundle.effective_cutoff,
        status=bundle.prediction.status,
        reason_code=bundle.prediction.reason_code,
        score=bundle.prediction.score,
        threshold=bundle.prediction.threshold,
        decision=bundle.prediction.decision,
        completeness=bundle.completeness,
        integrity=bundle.integrity,
        coverage=bundle.source_summary.receipt_coverage,
        observed_feature_count=bundle.source_summary.observed_feature_count,
        expected_feature_count=bundle.source_summary.expected_feature_count,
        source_type=bundle.source_summary.source_type,
        missing_reason_counts=bundle.source_summary.missing_reason_counts,
        available_signals=bundle.source_summary.available_signals,
        invalid_observation_count=bundle.source_summary.invalid_observation_count,
        duplicate_timestamp_count=bundle.source_summary.duplicate_timestamp_count,
        pull_completeness=bundle.source_summary.pull_completeness,
        artifact_availability=bundle.source_summary.artifact_availability,
        facts=public_facts,
        gaps=bundle.gaps,
        claims=claims,
        omitted_count=bundle.omitted_count,
        node_count=len(bundle.nodes),
        edge_count=len(bundle.edges),
        fact_count=len(bundle.facts),
        fingerprint=bundle.logical_fingerprint[:24],
        interpretation=bundle.interpretation,
        limitations=bundle.limitations,
    )


def _feature_definition(key: str) -> Any | None:
    try:
        return DEFAULT_REGISTRY.resolve(key)
    except KeyError:
        return None


def _eligible_feature_keys(source: EvidenceSourceSnapshot, values: dict[str, Any]) -> list[str]:
    if source.response.result_type == "next_pull":
        model = source.records.get(SourceKind.MODEL_VERSION)
        schema = model.payload.get("input_schema", {}) if model else {}
        keys = (
            schema.get("raw_feature_order", schema.get("raw_feature_keys", []))
            if isinstance(schema, dict)
            else []
        )
        if not isinstance(keys, list):
            return []
        return [key for key in keys if isinstance(key, str) and key in values]
    finding = source.records.get(SourceKind.ANOMALY_FINDING)
    if finding is None:
        return []
    observed = finding.payload.get("observed_features", [])
    keys = observed if isinstance(observed, list) else []
    return sorted(key for key in keys if key in values)[:24]


def _model_output_facts(
    response: Any, node_id: str, cutoff: datetime, start: int, label: Any
) -> list[EvidenceFact]:
    facts = [
        EvidenceFact(
            fact_id=f"output-status-{start:02d}",
            key="prediction.status",
            fact_type=EvidenceFactType.MODEL_OUTPUT,
            value=response.status.value,
            source_node_id=node_id,
            cutoff=cutoff,
            cutoff_eligible=True,
            quality=FactQuality.VALID,
            ordinal=start,
            meaning="Status recorded in the immutable 9D receipt.",
        )
    ]
    score = (
        response.engineering_validation_score
        if response.result_type == "next_pull"
        else response.anomaly_score
    )
    if score is not None:
        facts.append(
            EvidenceFact(
                fact_id=f"output-score-{start:02d}",
                key="prediction.score",
                fact_type=EvidenceFactType.MODEL_OUTPUT,
                value=score,
                source_node_id=node_id,
                cutoff=cutoff,
                cutoff_eligible=True,
                quality=FactQuality.VALID,
                ordinal=start + 1,
                meaning="Original engineering score; not a calibrated probability.",
            )
        )
    if response.threshold is not None:
        facts.append(
            EvidenceFact(
                fact_id=f"output-threshold-{start:02d}",
                key="prediction.threshold",
                fact_type=EvidenceFactType.MODEL_OUTPUT,
                value=response.threshold,
                source_node_id=node_id,
                cutoff=cutoff,
                cutoff_eligible=True,
                quality=FactQuality.VALID,
                ordinal=start + 2,
                meaning="Threshold recorded for the selected version.",
            )
        )
    if response.decision is not None:
        facts.append(
            EvidenceFact(
                fact_id=f"output-decision-{start:02d}",
                key="prediction.decision",
                fact_type=EvidenceFactType.MODEL_OUTPUT,
                value=str(response.decision),
                source_node_id=node_id,
                cutoff=cutoff,
                cutoff_eligible=True,
                quality=FactQuality.VALID,
                ordinal=start + 3,
                meaning="Decision preserved from the original 9D response.",
            )
        )
    if label:
        facts.append(
            EvidenceFact(
                fact_id=f"outcome-definition-{start:02d}",
                key="prediction.predicted_outcome_definition",
                fact_type=EvidenceFactType.MODEL_OUTPUT,
                value={
                    "key": label.get("key"),
                    "version": label.get("version"),
                    "source_outcome": label.get("source_outcome"),
                },
                source_node_id=node_id,
                cutoff=cutoff,
                cutoff_eligible=True,
                quality=FactQuality.LIMITED,
                ordinal=start + 4,
                meaning="Versioned future outcome rule; no target pull or label is included.",
            )
        )
    return facts


def _anomaly_facts(
    contributions: Any, nodes: dict[SourceKind, str], cutoff: datetime, start: int
) -> list[EvidenceFact]:
    if not isinstance(contributions, list):
        return []
    ordered = sorted(
        (
            item
            for item in contributions
            if isinstance(item, dict) and _finite_number(item.get("normalized_deviation"))
        ),
        key=lambda item: (
            -abs(float(item["normalized_deviation"])),
            str(item.get("feature_key", "")),
            str(item.get("direction", "")),
        ),
    )[:3]
    result: list[EvidenceFact] = []
    for index, item in enumerate(ordered):
        key = item.get("feature_key")
        definition = _feature_definition(key) if isinstance(key, str) else None
        if not isinstance(key, str) or definition is None:
            continue
        recorded_unit = item.get("unit")
        if recorded_unit is not None and recorded_unit != definition.unit:
            continue
        for metric in (
            "observed",
            "reference_median",
            "reference_q25",
            "reference_q75",
            "normalized_deviation",
            "signed_robust_deviation",
        ):
            value = item.get(metric)
            if value is None:
                continue
            fact_type = (
                EvidenceFactType.SOURCE_MEASUREMENT
                if metric == "observed"
                else EvidenceFactType.STATISTICAL_REFERENCE
            )
            result.append(
                EvidenceFact(
                    fact_id=f"deviation-{index:02d}-{metric}",
                    key=f"{key}.{metric}",
                    fact_type=fact_type,
                    value=value,
                    unit=definition.unit
                    if metric in {"observed", "reference_median", "reference_q25", "reference_q75"}
                    else None,
                    source_node_id=nodes.get(SourceKind.ANOMALY_FINDING, "receipt"),
                    cutoff=cutoff,
                    cutoff_eligible=True,
                    quality=FactQuality.VALID,
                    ordinal=start + len(result),
                    meaning=(
                        "Persisted descriptive 9C deviation against the frozen reference; "
                        "not causal attribution."
                    ),
                )
            )
    return result


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _fact_quality(value: str, raw: Any) -> FactQuality:
    if raw is None:
        return FactQuality.MISSING
    if value == "valid":
        return FactQuality.VALID
    if value == "limited":
        return FactQuality.LIMITED
    if value == "unavailable":
        return FactQuality.MISSING
    return FactQuality.INVALID


def _completeness(
    source: EvidenceSourceSnapshot,
    response: Any,
    facts: list[EvidenceFact],
    gaps: list[EvidenceGap],
) -> EvidenceCompleteness:
    if response.status.value != "READY_SCORE":
        return EvidenceCompleteness.ABSTAINED
    if (
        source.integrity
        in {
            EvidenceIntegrity.FAILED_SOURCE_MISMATCH,
            EvidenceIntegrity.NOT_VERIFIABLE,
            EvidenceIntegrity.UNSUPPORTED_SCHEMA,
        }
        or gaps
    ):
        return EvidenceCompleteness.PARTIAL
    if response.quality.quality_class != "high" or response.quality.coverage < 1:
        return EvidenceCompleteness.PARTIAL
    return EvidenceCompleteness.COMPLETE


def _prediction(response: Any) -> Any:
    from vehicle_platform.prediction_evidence.domain import OriginalPrediction

    score = (
        response.engineering_validation_score
        if response.result_type == "next_pull"
        else response.anomaly_score
    )
    return OriginalPrediction(
        status=response.status.value,
        reason_code=response.reason_code,
        score=score,
        threshold=response.threshold,
        decision=response.decision,
    )


def _supervised_interpretation(response: Any, task: str | None, label: Any) -> str:
    if response.status.value != "READY_SCORE":
        return (
            f"The registered {task or 'supervised'} model did not score this receipt "
            f"({response.reason_code or response.status.value}). "
            "The next-pull outcome is not observed here."
        )
    definition = label.get("name") if isinstance(label, dict) else None
    return (
        f"At the frozen cutoff, the registered {task or 'supervised'} model recorded an "
        f"engineering score against its threshold for "
        f"{definition or 'a versioned next-pull outcome rule'}. "
        "The future outcome is not observed here."
    )


def _anomaly_interpretation(response: Any, family: str | None) -> str:
    if response.status.value != "READY_SCORE":
        return (
            f"The offline {family or 'anomaly'} evaluation was not evaluable "
            f"({response.reason_code or response.status.value}); "
            "no measured deviation is asserted."
        )
    return (
        f"The frozen 9C {family or 'anomaly'} detector recorded a retrospective deviation "
        "for this completed pull against its selected reference. "
        "This is descriptive and not causal."
    )


def _optional_int(record: Any, key: str, maximum: int) -> int | None:
    value = record.payload.get(key) if record else None
    return value if type(value) is int and 0 <= value <= maximum else None


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(UTC) if parsed.tzinfo else None
    return None


def _nested(value: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _dedupe_gaps(values: list[EvidenceGap]) -> list[EvidenceGap]:
    unique: dict[tuple[str, str | None, str | None], EvidenceGap] = {}
    for item in values:
        unique[(item.code.value, item.source_node_id, item.reason_code)] = item
    return [unique[key] for key in sorted(unique)]
