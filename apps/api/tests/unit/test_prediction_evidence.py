import copy
import json
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from vehicle_platform.anomalies.domain import SourceRole
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.prediction_evidence.builder import (
    _anomaly_facts,
    _anomaly_interpretation,
    _completeness,
    _datetime,
    _dedupe_gaps,
    _eligible_feature_keys,
    _fact_quality,
    _feature_definition,
    _finite_number,
    _model_output_facts,
    _nested,
    _optional_int,
    _supervised_interpretation,
    build_evidence,
    fit_bundle_to_size,
    rehash_bundle,
    render_safe_projection,
)
from vehicle_platform.prediction_evidence.canonical import (
    canonical_json,
    canonical_time,
    canonical_value,
    evidence_content_payload,
    sha256,
)
from vehicle_platform.prediction_evidence.domain import (
    ArtifactAvailability,
    ClaimTemplate,
    EvidenceCompleteness,
    EvidenceEdge,
    EvidenceEdgeType,
    EvidenceFact,
    EvidenceFactType,
    EvidenceGap,
    EvidenceGapCode,
    EvidenceIntegrity,
    EvidenceNode,
    EvidenceResultKind,
    EvidenceSourceSnapshot,
    FactQuality,
    OriginalPrediction,
    PredictionEvidenceBundle,
    SourceKind,
    SourceRecordSnapshot,
)
from vehicle_platform.prediction_evidence.repository import (
    _decode_bundle,
    _finding_matches_receipt,
    _finding_reference_matches,
    _model_threshold_matches_response,
    _response_decision_consistent,
)
from vehicle_platform.prediction_evidence.verifier import (
    _aware_datetime,
    _contribution_fact_matches,
    _feature_quality_matches,
    _prediction_decision_consistent,
    _prediction_equal,
    _rooted_acyclic_graph,
    verify_bundle_sources,
)
from vehicle_platform.predictions.domain import (
    PredictionLineage,
    PredictionQuality,
    PredictionResponse,
    PredictionStatus,
)

_CUTOFF = datetime(2025, 1, 1, 12, tzinfo=UTC)


def _record(
    kind: SourceKind, entity_id: UUID, payload: Mapping[str, object]
) -> SourceRecordSnapshot:
    return SourceRecordSnapshot(
        kind=kind,
        entity_id=entity_id,
        checksum=sha256(payload),
        schema_checksum=sha256(f"test:{kind.value}:v1"),
        payload=cast(dict[str, Any], dict(payload)),
    )


def _source(
    *, available_at: datetime = _CUTOFF, status: PredictionStatus = PredictionStatus.READY_SCORE
) -> EvidenceSourceSnapshot:
    receipt_id, binding_id, event_id = uuid4(), uuid4(), uuid4()
    model_id, feature_id, feature_version_id = uuid4(), uuid4(), uuid4()
    score = 0.72 if status is PredictionStatus.READY_SCORE else None
    threshold = 0.6
    decision = score >= threshold if score is not None else None
    response = PredictionResponse(
        result_type="next_pull",
        task=MLTask.THERMAL_DEGRADATION,
        horizon="NEXT_PULL",
        status=status,
        reason_code=None if score is not None else "INPUT_QUALITY_BELOW_SERVING_FLOOR",
        receipt_id=receipt_id,
        requested_cutoff=_CUTOFF,
        effective_cutoff=_CUTOFF if score is not None else None,
        source_role=SourceRole.SYNTHETIC,
        model_version_id=model_id,
        feature_set_version="phase9a-pull-v2",
        decision=decision,
        engineering_validation_score=score,
        threshold=threshold if score is not None else None,
        interpretation="Engineering-validation score, not a real-world failure probability.",
        limitation="Controlled engineering output only.",
        quality=PredictionQuality(
            quality_class="high" if score is not None else "insufficient",
            observed_feature_count=1 if score is not None else 0,
            expected_feature_count=1,
            coverage=1.0 if score is not None else 0.0,
        ),
        lineage=PredictionLineage(feature_set_id=feature_id),
    )
    feature = {
        "feature_values": {
            "thermal.iat_delta_k": {
                "value": 2.5,
                "unit": "K",
                "quality": "valid",
                "missing_reason": None,
                "available_at": available_at.isoformat(),
                "source_window_start": (_CUTOFF - timedelta(minutes=1)).isoformat(),
                "source_window_end": _CUTOFF.isoformat(),
                "details": {},
            }
        }
    }
    records = {
        SourceKind.PREDICTION_RECEIPT: _record(
            SourceKind.PREDICTION_RECEIPT,
            receipt_id,
            {"request_fingerprint": "a" * 64},
        ),
        SourceKind.SERVING_BINDING: _record(SourceKind.SERVING_BINDING, binding_id, {}),
        SourceKind.APPROVAL_EVENT: _record(SourceKind.APPROVAL_EVENT, event_id, {}),
        SourceKind.FEATURE_SET: _record(SourceKind.FEATURE_SET, feature_id, feature),
        SourceKind.FEATURE_VERSION: _record(SourceKind.FEATURE_VERSION, feature_version_id, {}),
        SourceKind.MODEL_VERSION: _record(
            SourceKind.MODEL_VERSION,
            model_id,
            {
                "input_schema": {"raw_feature_order": ["thermal.iat_delta_k"]},
                "label_definition": {
                    "key": "thermal_degradation",
                    "version": "1.0.0",
                    "name": "Next pull thermal progression",
                    "source_outcome": "next pull IAT start rule",
                },
            },
        ),
    }
    return EvidenceSourceSnapshot(
        receipt=records[SourceKind.PREDICTION_RECEIPT],
        response=response,
        records=records,
        integrity=EvidenceIntegrity.VERIFIED,
        gaps=(),
        artifact_availability=ArtifactAvailability.VERIFIED,
    )


def _anomaly_source(
    *, status: PredictionStatus = PredictionStatus.READY_SCORE
) -> EvidenceSourceSnapshot:
    source = _source(status=status)
    run_id, finding_id, detector_id, dataset_id = uuid4(), uuid4(), uuid4(), uuid4()
    contribution = {
        "feature_key": "thermal.iat_delta_k",
        "direction": "high",
        "unit": "K",
        "observed": 5.0,
        "reference_median": 4.0,
        "reference_q25": 3.0,
        "reference_q75": 5.0,
        "normalized_deviation": 2.0,
        "signed_robust_deviation": 1.5,
    }
    finding = _record(
        SourceKind.ANOMALY_FINDING,
        finding_id,
        {
            "observed_features": {
                "thermal.iat_delta_k": {"value": 5.0, "unit": "K", "quality": "valid"}
            },
            "contributions": [contribution],
            "reference_summary": {
                "schema_version": "phase9c-detection-run-v1",
                "reference_summary": {
                    "reference_dataset_id": str(dataset_id),
                    "reference_checksum": "a" * 64,
                    "cohort_checksum": "b" * 64,
                    "row_count": 12,
                    "session_count": 4,
                    "observation_cutoff": _CUTOFF.isoformat(),
                },
            },
        },
    )
    records = dict(source.records)
    records.pop(SourceKind.MODEL_VERSION)
    records.update(
        {
            SourceKind.DETECTOR_VERSION: _record(
                SourceKind.DETECTOR_VERSION, detector_id, {"family": "thermal"}
            ),
            SourceKind.ANOMALY_RUN: _record(
                SourceKind.ANOMALY_RUN, run_id, {"cutoff": _CUTOFF.isoformat()}
            ),
            SourceKind.ANOMALY_FINDING: finding,
            SourceKind.REFERENCE_DATASET: _record(
                SourceKind.REFERENCE_DATASET,
                dataset_id,
                {
                    "row_count": 12,
                    "session_count": 4,
                    "reference_cutoff": _CUTOFF.isoformat(),
                },
            ),
        }
    )
    response = source.response.model_copy(
        update={
            "result_type": "anomaly",
            "task": None,
            "family": "thermal",
            "horizon": "AFTER_PULL_OFFLINE",
            "model_version_id": None,
            "detector_version_id": detector_id,
            "engineering_validation_score": None,
            "anomaly_score": 0.85 if status is PredictionStatus.READY_SCORE else None,
            "threshold": 0.6 if status is PredictionStatus.READY_SCORE else None,
            "decision": "ANOMALOUS" if status is PredictionStatus.READY_SCORE else None,
            "reason_code": None
            if status is PredictionStatus.READY_SCORE
            else "ABSTAINED_INSUFFICIENT_REFERENCE",
            "lineage": PredictionLineage(
                feature_set_id=source.response.lineage.feature_set_id,
                anomaly_run_id=run_id,
                anomaly_finding_id=finding_id,
            ),
        }
    )
    return replace(source, response=response, records=records)


def test_build_is_stable_and_excludes_generated_time_from_logical_identity() -> None:
    source = _source()
    first = build_evidence(source, generated_at=_CUTOFF + timedelta(minutes=1))
    second = build_evidence(source, generated_at=_CUTOFF + timedelta(minutes=2))

    assert first.evidence_id == second.evidence_id
    assert first.logical_fingerprint == second.logical_fingerprint
    assert first.content_checksum != second.content_checksum
    assert first.completeness is EvidenceCompleteness.COMPLETE
    assert first.horizon.value == "NEXT_PULL"
    assert all("target" not in fact.key for fact in first.facts)
    assert all(
        fact.cutoff_eligible and fact.cutoff <= first.effective_cutoff for fact in first.facts
    )


def test_stored_bundle_round_trips_from_jsonb_dict_and_json_text() -> None:
    bundle = build_evidence(_source(), generated_at=_CUTOFF + timedelta(minutes=1))
    body = canonical_json(bundle.model_dump(mode="json"))

    assert _decode_bundle(json.loads(body)) == bundle
    assert _decode_bundle(body) == bundle


def test_reference_verifier_accepts_phase9c_nested_summary_and_flat_summary() -> None:
    reference_id = uuid4()
    reference = {
        "id": reference_id,
        "reference_checksum": "a" * 64,
        "cohort_checksum": "b" * 64,
        "row_count": 40,
        "session_count": 8,
    }
    summary = {
        "reference_dataset_id": str(reference_id),
        "reference_checksum": reference["reference_checksum"],
        "cohort_checksum": reference["cohort_checksum"],
        "row_count": 40,
        "session_count": 8,
    }
    detector = {"reference_id": reference_id}
    finding = {"reference_dataset_id": reference_id, "reference_summary": summary}

    assert _finding_reference_matches(finding, detector, reference)
    finding["reference_summary"] = {"reference_summary": summary}
    assert _finding_reference_matches(finding, detector, reference)


def test_anomaly_finding_cutoff_binds_to_requested_not_feature_cutoff() -> None:
    source = _anomaly_source()
    response = source.response.model_copy(
        update={"effective_cutoff": _CUTOFF - timedelta(minutes=1)}
    )
    finding_id, run_id = uuid4(), uuid4()
    detector_id = response.detector_version_id
    reference_id = uuid4()
    feature_id = response.lineage.feature_set_id
    finding = {
        "id": finding_id,
        "run_id": run_id,
        "detector_version_id": detector_id,
        "feature_set_id": feature_id,
        "source_hash": "a" * 64,
        "provenance_hash": "b" * 64,
        "family": response.family,
        "observation_cutoff": response.requested_cutoff,
        "score": response.anomaly_score,
        "threshold": response.threshold,
        "status": "ANOMALOUS",
        "reference_dataset_id": reference_id,
    }
    run = {
        "id": run_id,
        "detector_version_id": detector_id,
        "reference_dataset_id": reference_id,
    }
    receipt = {
        "anomaly_finding_id": finding_id,
        "anomaly_run_id": run_id,
        "detector_version_id": detector_id,
        "feature_set_id": feature_id,
        "feature_set_checksum": "a" * 64,
        "feature_provenance_checksum": "b" * 64,
    }

    assert _finding_matches_receipt(finding, run, receipt, response)


def test_late_ingested_feature_becomes_gap_and_never_a_fact() -> None:
    source = _source(available_at=_CUTOFF + timedelta(seconds=1))
    bundle = build_evidence(source, generated_at=_CUTOFF + timedelta(minutes=1))

    assert bundle.completeness is EvidenceCompleteness.PARTIAL
    assert not any(fact.key == "thermal.iat_delta_k" for fact in bundle.facts)
    assert any(gap.code.value == "FEATURE_NOT_YET_OBSERVED" for gap in bundle.gaps)


def test_naive_feature_timestamp_is_a_schema_gap_not_an_eligible_fact() -> None:
    source = _source()
    feature = source.records[SourceKind.FEATURE_SET]
    payload = copy.deepcopy(feature.payload)
    payload["feature_values"]["thermal.iat_delta_k"]["available_at"] = "2025-01-01T12:00:00"
    source = replace(
        source,
        records=source.records | {SourceKind.FEATURE_SET: replace(feature, payload=payload)},
    )
    bundle = build_evidence(source, generated_at=_CUTOFF + timedelta(minutes=1))

    assert not any(fact.key == "thermal.iat_delta_k" for fact in bundle.facts)
    assert any(
        gap.code is EvidenceGapCode.SOURCE_SCHEMA_MISMATCH
        and gap.reason_code == "FEATURE_TIME_NAIVE_OR_INVALID"
        for gap in bundle.gaps
    )


def test_abstention_remains_an_abstention_explanation() -> None:
    bundle = build_evidence(
        _source(status=PredictionStatus.ABSTAINED_LOW_QUALITY),
        generated_at=_CUTOFF + timedelta(minutes=1),
    )

    assert bundle.completeness is EvidenceCompleteness.ABSTAINED
    assert bundle.prediction.status == "ABSTAINED_LOW_QUALITY"
    assert bundle.prediction.score is None
    assert any(gap.code.value == "INPUT_ABSTAINED" for gap in bundle.gaps)


def test_safe_projection_omits_internal_graph_sources() -> None:
    bundle = build_evidence(_source(), generated_at=_CUTOFF + timedelta(minutes=1))
    result = render_safe_projection(bundle).model_dump(mode="json")

    assert result["score"] == 0.72
    assert "nodes" not in result
    assert "source_entity_id" not in str(result)
    assert result["horizon"] == "NEXT_PULL"


def test_size_limit_omits_whole_facts_and_marks_partial_with_new_hashes() -> None:
    bundle = build_evidence(_source(), generated_at=_CUTOFF + timedelta(minutes=1))
    extra_facts = [
        EvidenceFact(
            fact_id=f"large-{index}",
            key=f"context.large_{index}",
            fact_type=EvidenceFactType.CONTEXT_DESCRIPTOR,
            value="x" * 3_500,
            source_node_id="feature-set",
            cutoff=_CUTOFF,
            cutoff_eligible=True,
            quality=FactQuality.VALID,
            meaning="bounded test context",
        )
        for index in range(24)
    ]
    oversized = rehash_bundle(bundle.model_copy(update={"facts": bundle.facts + extra_facts}))

    fitted = fit_bundle_to_size(oversized)

    assert fitted.omitted_count > 0
    assert fitted.completeness is EvidenceCompleteness.PARTIAL
    assert any(gap.code is EvidenceGapCode.INCOMPLETE_PROJECTION for gap in fitted.gaps)
    assert len(fitted.facts) < len(oversized.facts)
    assert sha256(evidence_content_payload(fitted)) == fitted.content_checksum
    assert len(render_safe_projection(fitted).model_dump_json().encode("utf-8")) <= 65_536


def test_size_limit_removes_claims_and_fails_when_fixed_manifest_cannot_fit() -> None:
    bundle = build_evidence(_source(), generated_at=_CUTOFF + timedelta(minutes=1))
    claim = bundle.claims[0].model_copy(
        update={"fact_ids": [fact.fact_id for fact in bundle.facts]}
    )
    bounded_gap_list = [
        EvidenceGap(
            code=EvidenceGapCode.LOW_QUALITY,
            reason_code=f"gap-{index}",
        )
        for index in range(16)
    ]
    bounded_limitations = [f"limit-{index}" for index in range(12)]
    oversized = bundle.model_copy(
        update={"claims": [claim], "gaps": bounded_gap_list, "limitations": bounded_limitations}
    )

    with pytest.raises(ValueError, match="cannot fit"):
        fit_bundle_to_size(oversized, max_bytes=1)


def test_interpretation_rejects_diagnostic_language() -> None:
    bundle = build_evidence(_source(), generated_at=_CUTOFF + timedelta(minutes=1))
    with pytest.raises(ValidationError):
        PredictionEvidenceBundle.model_validate(
            bundle.model_dump(mode="python") | {"interpretation": "This proves a defect."}
        )


def test_independent_verifier_detects_changed_feature_and_missing_source() -> None:
    source = _source()
    bundle = build_evidence(source, generated_at=_CUTOFF + timedelta(minutes=1))
    integrity, reasons = verify_bundle_sources(bundle, source)
    assert integrity is EvidenceIntegrity.VERIFIED
    assert reasons == []

    feature = source.records[SourceKind.FEATURE_SET]
    payload = copy.deepcopy(feature.payload)
    payload["feature_values"]["thermal.iat_delta_k"]["value"] = 999.0
    tampered = replace(
        source,
        records=source.records | {SourceKind.FEATURE_SET: replace(feature, payload=payload)},
    )
    integrity, reasons = verify_bundle_sources(bundle, tampered)
    assert integrity is EvidenceIntegrity.FAILED_SOURCE_MISMATCH
    assert "FACT_SOURCE_VALUE_MISMATCH" in reasons

    missing = replace(
        source,
        records={
            kind: record
            for kind, record in source.records.items()
            if kind is not SourceKind.MODEL_VERSION
        },
        integrity=EvidenceIntegrity.NOT_VERIFIABLE,
        gaps=(EvidenceGapCode.EVIDENCE_SOURCE_MISSING,),
    )
    integrity, reasons = verify_bundle_sources(bundle, missing)
    assert integrity is EvidenceIntegrity.NOT_VERIFIABLE
    assert "SOURCE_UNAVAILABLE_MODEL_VERSION" in reasons


def test_anomaly_evidence_preserves_reference_and_contribution_lineage() -> None:
    source = _anomaly_source()
    bundle = build_evidence(source, generated_at=_CUTOFF + timedelta(minutes=1))

    assert bundle.result_type is EvidenceResultKind.ANOMALY
    assert bundle.horizon.value == "AFTER_PULL_OFFLINE"
    assert bundle.family == "thermal"
    assert {node.source_kind for node in bundle.nodes} >= {
        SourceKind.DETECTOR_VERSION,
        SourceKind.ANOMALY_RUN,
        SourceKind.ANOMALY_FINDING,
        SourceKind.REFERENCE_DATASET,
    }
    assert any(fact.key == "reference.observation_cutoff" for fact in bundle.facts)
    assert any(fact.key == "thermal.iat_delta_k.normalized_deviation" for fact in bundle.facts)
    assert all(fact.cutoff <= bundle.effective_cutoff for fact in bundle.facts)
    integrity, reasons = verify_bundle_sources(bundle, source)
    assert integrity is EvidenceIntegrity.VERIFIED
    assert reasons == []

    finding = source.records[SourceKind.ANOMALY_FINDING]
    payload = copy.deepcopy(finding.payload)
    payload["contributions"][0]["normalized_deviation"] = 3.0
    tampered = replace(
        source,
        records=source.records
        | {
            SourceKind.ANOMALY_FINDING: _record(
                SourceKind.ANOMALY_FINDING, finding.entity_id, payload
            )
        },
    )
    integrity, reasons = verify_bundle_sources(bundle, tampered)
    assert integrity is EvidenceIntegrity.FAILED_SOURCE_MISMATCH
    assert "SOURCE_CHECKSUM_MISMATCH_ANOMALY_FINDING" in reasons


def test_anomaly_abstention_without_finding_does_not_claim_a_deviation() -> None:
    source = _anomaly_source(status=PredictionStatus.ABSTAINED_INSUFFICIENT_REFERENCE)
    records = dict(source.records)
    records.pop(SourceKind.ANOMALY_FINDING)
    source = replace(source, records=records)

    bundle = build_evidence(source, generated_at=_CUTOFF + timedelta(minutes=1))

    assert bundle.completeness is EvidenceCompleteness.ABSTAINED
    assert bundle.prediction.score is None
    assert not any(fact.key.endswith("normalized_deviation") for fact in bundle.facts)
    assert all(claim.template is not ClaimTemplate.FEATURE_ASSOCIATION for claim in bundle.claims)


def test_builder_emits_typed_gaps_for_missing_and_malformed_feature_sources() -> None:
    source = _source()
    feature_record = source.records[SourceKind.FEATURE_SET]
    model_record = source.records[SourceKind.MODEL_VERSION]

    missing_source = replace(
        source,
        records={
            kind: record
            for kind, record in source.records.items()
            if kind is not SourceKind.FEATURE_SET
        },
    )
    missing_bundle = build_evidence(missing_source, generated_at=_CUTOFF + timedelta(minutes=1))
    assert any(gap.code is EvidenceGapCode.NO_FEATURE_SET for gap in missing_bundle.gaps)
    assert not missing_bundle.source_summary.feature_set_available

    cases = [
        (
            "thermal.iat_delta_k",
            {"feature_values": {"thermal.iat_delta_k": "not-an-object"}},
            EvidenceGapCode.PROVENANCE_MISMATCH,
        ),
        (
            "unsupported.feature",
            {"feature_values": {"unsupported.feature": {"unit": "x", "quality": "valid"}}},
            EvidenceGapCode.SOURCE_SCHEMA_MISMATCH,
        ),
        (
            "thermal.iat_delta_k",
            {
                "feature_values": {
                    "thermal.iat_delta_k": {
                        "unit": "K",
                        "quality": "valid",
                        "available_at": _CUTOFF.isoformat(),
                        "source_window_start": _CUTOFF.isoformat(),
                        "source_window_end": (_CUTOFF - timedelta(seconds=1)).isoformat(),
                    }
                }
            },
            EvidenceGapCode.SOURCE_SCHEMA_MISMATCH,
        ),
        (
            "thermal.iat_delta_k",
            {
                "feature_values": {
                    "thermal.iat_delta_k": {
                        "unit": "K",
                        "quality": "valid",
                        "available_at": "2025-01-01T12:00:00",
                    }
                }
            },
            EvidenceGapCode.SOURCE_SCHEMA_MISMATCH,
        ),
        (
            "thermal.iat_delta_k",
            {
                "feature_values": {
                    "thermal.iat_delta_k": {
                        "unit": "K",
                        "quality": "valid",
                        "available_at": (_CUTOFF + timedelta(seconds=1)).isoformat(),
                    }
                }
            },
            EvidenceGapCode.FEATURE_NOT_YET_OBSERVED,
        ),
    ]
    for key, payload, expected_gap in cases:
        feature = replace(feature_record, payload=payload)
        model_payload = {"input_schema": {"raw_feature_order": [key]}}
        model = replace(model_record, payload=model_payload)
        candidate = replace(
            source,
            records=source.records
            | {SourceKind.FEATURE_SET: feature, SourceKind.MODEL_VERSION: model},
        )
        bundle = build_evidence(candidate, generated_at=_CUTOFF + timedelta(minutes=1))
        assert any(gap.code is expected_gap for gap in bundle.gaps)


def test_builder_preserves_source_limits_quality_summaries_and_receipt_fallbacks() -> None:
    source = _source()
    feature = source.records[SourceKind.FEATURE_SET]
    feature_payload = copy.deepcopy(feature.payload)
    feature_payload["quality_metadata"] = {
        "available_signals": ["fuel", 3, "thermal"],
        "source_type": "dyno",
        "invalid_observation_count": 2,
        "duplicate_timestamp_count": "bad",
        "pull_completeness": 0.75,
    }
    feature = replace(feature, payload=feature_payload)
    model = source.records[SourceKind.MODEL_VERSION]
    model_payload = copy.deepcopy(model.payload)
    model_payload["input_schema"]["feature_importance"] = [
        {"feature": "thermal.iat_delta_k", "importance": 0.4}
    ]
    model = replace(model, payload=model_payload)
    response = source.response.model_copy(
        update={
            "quality": source.response.quality.model_copy(
                update={"missing_reason_counts": {"missing": 2, "invalid": 129}}
            )
        }
    )
    receipt = replace(source.receipt, payload={"request_fingerprint": "short"})
    updated = replace(
        source,
        receipt=receipt,
        response=response,
        records=source.records
        | {
            SourceKind.PREDICTION_RECEIPT: receipt,
            SourceKind.FEATURE_SET: feature,
            SourceKind.MODEL_VERSION: model,
        },
    )

    bundle = build_evidence(updated, generated_at=_CUTOFF + timedelta(minutes=1))

    assert bundle.receipt_fingerprint == receipt.checksum
    assert bundle.source_summary.available_signals == ["fuel", "thermal"]
    assert bundle.source_summary.source_type == "dyno"
    assert bundle.source_summary.invalid_observation_count == 2
    assert bundle.source_summary.duplicate_timestamp_count is None
    assert bundle.source_summary.pull_completeness == 0.75
    assert bundle.source_summary.missing_reason_counts == {"missing": 2}
    assert any(fact.key == "model.feature_importance_available" for fact in bundle.facts)

    unsupported_schema = replace(model, payload={"input_schema": "invalid"})
    malformed = replace(
        updated,
        records=updated.records | {SourceKind.MODEL_VERSION: unsupported_schema},
    )
    assert build_evidence(malformed, generated_at=_CUTOFF + timedelta(minutes=1))

    untrusted = replace(updated, integrity=EvidenceIntegrity.NOT_VERIFIABLE)
    untrusted_bundle = build_evidence(untrusted, generated_at=_CUTOFF + timedelta(minutes=1))
    assert not untrusted_bundle.claims
    assert "cannot support an affirmative evidence claim" in untrusted_bundle.interpretation


class _ExampleEnum(StrEnum):
    LABEL = "label"


def test_canonical_json_normalizes_supported_values_and_rejects_ambiguous_values() -> None:
    identifier = uuid4()
    normalized = canonical_value(
        {
            "time": _CUTOFF.astimezone(timezone(timedelta(hours=-3))),
            "decimal": Decimal("12.3400"),
            "enum": _ExampleEnum.LABEL,
            "id": identifier,
            "sequence": (1, "two"),
            "finite": 1.25,
        }
    )
    assert normalized == {
        "time": "2025-01-01T12:00:00.000000Z",
        "decimal": "12.34",
        "enum": "label",
        "id": str(identifier),
        "sequence": [1, "two"],
        "finite": 1.25,
    }
    assert canonical_json("already-canonical") == '"already-canonical"'
    assert canonical_time(_CUTOFF) == _CUTOFF
    for invalid in (
        datetime(2025, 1, 1),
        Decimal("NaN"),
        float("inf"),
        object(),
    ):
        with pytest.raises((TypeError, ValueError)):
            canonical_value(invalid)
    with pytest.raises(ValueError, match="timezone aware"):
        canonical_time(datetime(2025, 1, 1))


def test_builder_helpers_cover_feature_quality_time_and_interpretation_variants() -> None:
    source = _source()
    feature_key = "thermal.iat_delta_k"
    values = {feature_key: {"value": 2.5}}
    assert _feature_definition(feature_key) is not None
    assert _feature_definition("unsupported.feature") is None
    assert _eligible_feature_keys(source, values) == [feature_key]

    model = source.records[SourceKind.MODEL_VERSION]
    malformed_schema = replace(model, payload={"input_schema": {"raw_feature_order": "bad"}})
    assert (
        _eligible_feature_keys(
            replace(source, records=source.records | {SourceKind.MODEL_VERSION: malformed_schema}),
            values,
        )
        == []
    )
    no_model = replace(
        source,
        records={
            kind: record
            for kind, record in source.records.items()
            if kind is not SourceKind.MODEL_VERSION
        },
    )
    assert _eligible_feature_keys(no_model, values) == []

    anomaly = _anomaly_source()
    finding = anomaly.records[SourceKind.ANOMALY_FINDING]
    assert _eligible_feature_keys(anomaly, values) == [feature_key]
    legacy_finding = replace(finding, payload={"observed_features": [feature_key]})
    assert _eligible_feature_keys(
        replace(anomaly, records=anomaly.records | {SourceKind.ANOMALY_FINDING: legacy_finding}),
        values,
    ) == [feature_key]
    malformed_finding = replace(finding, payload={"observed_features": "bad"})
    assert (
        _eligible_feature_keys(
            replace(
                anomaly, records=anomaly.records | {SourceKind.ANOMALY_FINDING: malformed_finding}
            ),
            values,
        )
        == []
    )
    missing_finding = replace(
        anomaly,
        records={
            kind: record
            for kind, record in anomaly.records.items()
            if kind is not SourceKind.ANOMALY_FINDING
        },
    )
    assert _eligible_feature_keys(missing_finding, values) == []

    assert _fact_quality("valid", 1.0) is FactQuality.VALID
    assert _fact_quality("limited", 1.0) is FactQuality.LIMITED
    assert _fact_quality("unavailable", 1.0) is FactQuality.MISSING
    assert _fact_quality("unknown", 1.0) is FactQuality.INVALID
    assert _fact_quality("valid", None) is FactQuality.MISSING
    assert _finite_number(1) and _finite_number(1.5)
    assert not _finite_number(True) and not _finite_number(float("nan"))

    response = source.response
    full_output = _model_output_facts(response, "receipt", _CUTOFF, 0, {"key": "label"})
    assert {fact.key for fact in full_output} >= {
        "prediction.status",
        "prediction.score",
        "prediction.threshold",
        "prediction.decision",
        "prediction.predicted_outcome_definition",
    }
    empty_output = _model_output_facts(
        response.model_copy(
            update={
                "engineering_validation_score": None,
                "threshold": None,
                "decision": None,
            }
        ),
        "receipt",
        _CUTOFF,
        0,
        {},
    )
    assert [fact.key for fact in empty_output] == ["prediction.status"]

    assert "next-pull outcome is not observed" in _supervised_interpretation(
        source.response.model_copy(update={"status": PredictionStatus.ABSTAINED_LOW_QUALITY}),
        None,
        {},
    )
    assert "versioned next-pull outcome rule" in _supervised_interpretation(
        source.response.model_copy(update={"task": None}), None, None
    )
    assert "descriptive and not causal" in _anomaly_interpretation(anomaly.response, "thermal")
    assert "no measured deviation is asserted" in _anomaly_interpretation(
        anomaly.response.model_copy(
            update={"status": PredictionStatus.ABSTAINED_INSUFFICIENT_REFERENCE}
        ),
        None,
    )

    record = _record(SourceKind.MODEL_VERSION, uuid4(), {"count": 5, "bad": True})
    assert _optional_int(record, "count", 10) == 5
    assert _optional_int(record, "bad", 10) is None
    assert _optional_int(replace(record, payload={"count": -1}), "count", 10) is None
    assert _optional_int(None, "count", 10) is None
    assert _datetime(_CUTOFF) == _CUTOFF
    assert _datetime(_CUTOFF.isoformat()) == _CUTOFF
    assert _datetime("not-a-time") is None
    assert _datetime(datetime(2025, 1, 1)) is None
    assert _nested({"a": {"b": 1}}, "a", "b") == 1
    assert _nested({"a": 1}, "a", "b") is None
    gap = EvidenceGap(code=EvidenceGapCode.LOW_QUALITY, reason_code="low")
    assert len(_dedupe_gaps([gap, gap])) == 1


def test_anomaly_contributions_are_bounded_and_keep_only_supported_units() -> None:
    facts = _anomaly_facts(
        [
            {
                "feature_key": "thermal.iat_delta_k",
                "normalized_deviation": 2.0,
                "signed_robust_deviation": 1.5,
                "observed": 5.0,
                "reference_median": 4.0,
                "reference_q25": 3.0,
                "reference_q75": 5.0,
                "unit": "K",
            },
            {"feature_key": "unsupported.feature", "normalized_deviation": 1.0},
            {"feature_key": "thermal.iat_delta_k", "normalized_deviation": 4.0, "unit": "psi"},
            {"feature_key": "thermal.iat_delta_k", "normalized_deviation": float("nan")},
            "not a contribution",
        ],
        {SourceKind.ANOMALY_FINDING: "finding"},
        _CUTOFF,
        2,
    )
    assert len(facts) == 6
    assert all(fact.source_node_id == "finding" for fact in facts)
    assert _anomaly_facts(None, {}, _CUTOFF, 0) == []


def test_builder_completeness_uses_status_integrity_quality_and_gaps() -> None:
    source = _source()
    response = source.response
    assert _completeness(source, response, [], []) is EvidenceCompleteness.COMPLETE
    assert (
        _completeness(
            source,
            response.model_copy(update={"status": PredictionStatus.ABSTAINED_LOW_QUALITY}),
            [],
            [],
        )
        is EvidenceCompleteness.ABSTAINED
    )
    assert (
        _completeness(replace(source, integrity=EvidenceIntegrity.NOT_VERIFIABLE), response, [], [])
        is EvidenceCompleteness.PARTIAL
    )
    assert (
        _completeness(source, response, [], [EvidenceGap(code=EvidenceGapCode.LOW_QUALITY)])
        is EvidenceCompleteness.PARTIAL
    )
    assert (
        _completeness(
            source,
            response.model_copy(
                update={
                    "quality": response.quality.model_copy(update={"quality_class": "degraded"})
                }
            ),
            [],
            [],
        )
        is EvidenceCompleteness.PARTIAL
    )


def test_verifier_helpers_cover_prediction_graph_quality_and_contribution_checks() -> None:
    source = _source()
    bundle = build_evidence(source, generated_at=_CUTOFF + timedelta(minutes=1))
    assert _prediction_equal(bundle, source.response)
    bad_score = bundle.prediction.model_copy(update={"score": 0.0})
    assert not _prediction_equal(
        bundle.model_copy(update={"prediction": bad_score}), source.response
    )

    assert _prediction_decision_consistent(source.response)
    abstained = _source(status=PredictionStatus.ABSTAINED_LOW_QUALITY).response
    assert _prediction_decision_consistent(abstained)
    assert not _prediction_decision_consistent(abstained.model_copy(update={"decision": False}))
    assert not _prediction_decision_consistent(abstained.model_copy(update={"threshold": 0.6}))
    assert _response_decision_consistent(abstained)
    assert not _response_decision_consistent(abstained.model_copy(update={"threshold": 0.6}))
    model = {"threshold": 0.6}
    assert _model_threshold_matches_response(model, source.response)
    assert _model_threshold_matches_response(model, abstained)
    assert not _model_threshold_matches_response(
        model, abstained.model_copy(update={"threshold": 0.6})
    )
    anomaly_abstention = _anomaly_source(
        status=PredictionStatus.ABSTAINED_INSUFFICIENT_REFERENCE
    ).response.model_copy(update={"threshold": 0.6})
    assert _prediction_decision_consistent(anomaly_abstention)
    assert _response_decision_consistent(anomaly_abstention)
    assert not _prediction_decision_consistent(
        source.response.model_copy(update={"threshold": None})
    )
    anomaly_response = _anomaly_source().response
    assert _prediction_decision_consistent(anomaly_response)
    assert _prediction_decision_consistent(
        anomaly_response.model_copy(update={"anomaly_score": 0.4, "decision": "INLIER"})
    )
    assert not _prediction_decision_consistent(
        anomaly_response.model_copy(update={"anomaly_score": 0.4, "decision": "ANOMALOUS"})
    )

    assert _rooted_acyclic_graph(bundle)
    event_edge = next(
        edge
        for edge in bundle.edges
        if edge.source_node_id == "receipt" and edge.target_node_id == "event"
    )
    assert not _rooted_acyclic_graph(
        bundle.model_copy(update={"edges": [edge for edge in bundle.edges if edge != event_edge]})
    )
    cycle = EvidenceEdge(
        edge_id="cycle",
        source_node_id="binding",
        target_node_id="receipt",
        relation=EvidenceEdgeType.DERIVED_FROM,
    )
    assert not _rooted_acyclic_graph(bundle.model_copy(update={"edges": bundle.edges + [cycle]}))
    assert not _rooted_acyclic_graph(
        bundle.model_copy(update={"edges": bundle.edges + [bundle.edges[0]]})
    )
    dangling = EvidenceEdge(
        edge_id="dangling",
        source_node_id="receipt",
        target_node_id="missing",
        relation=EvidenceEdgeType.DERIVED_FROM,
    )
    assert not _rooted_acyclic_graph(bundle.model_copy(update={"edges": [dangling]}))

    assert _feature_quality_matches({"quality": "valid"}, "VALID")
    assert _feature_quality_matches({"quality": "limited"}, "LIMITED")
    assert _feature_quality_matches({"quality": "unavailable"}, "MISSING")
    assert _feature_quality_matches({"quality": "invalid"}, "INVALID")
    assert not _feature_quality_matches({"quality": "unknown"}, "VALID")
    assert _aware_datetime(_CUTOFF) == _CUTOFF
    assert _aware_datetime(_CUTOFF.isoformat()) == _CUTOFF
    assert _aware_datetime("not-a-time") is None
    assert _aware_datetime(datetime(2025, 1, 1)) is None
    assert _aware_datetime(3) is None
    contributions = [{"feature_key": "thermal.iat_delta_k", "normalized_deviation": 2.0}]
    assert _contribution_fact_matches(
        "thermal.iat_delta_k.normalized_deviation", 2.0, contributions
    )
    assert not _contribution_fact_matches(
        "thermal.iat_delta_k.normalized_deviation", 3.0, contributions
    )
    assert not _contribution_fact_matches("malformed", 2.0, contributions)
    assert not _contribution_fact_matches("x.metric", 1.0, None)


def test_verifier_reports_artifact_availability_and_unsupported_schema() -> None:
    source = _source()
    bundle = build_evidence(source, generated_at=_CUTOFF + timedelta(minutes=1))
    unavailable = replace(source, artifact_availability=ArtifactAvailability.UNAVAILABLE)
    integrity, reasons = verify_bundle_sources(bundle, unavailable)
    assert integrity is EvidenceIntegrity.VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE
    assert reasons == ["ARTIFACT_UNAVAILABLE"]
    mismatch = replace(source, artifact_availability=ArtifactAvailability.CHECKSUM_MISMATCH)
    integrity, reasons = verify_bundle_sources(bundle, mismatch)
    assert integrity is EvidenceIntegrity.FAILED_SOURCE_MISMATCH
    assert reasons == ["ARTIFACT_CHECKSUM_MISMATCH"]

    unsupported_response = source.response.model_copy(update={"schema_version": "future-schema"})
    integrity, reasons = verify_bundle_sources(
        bundle, replace(source, response=unsupported_response)
    )
    assert integrity is EvidenceIntegrity.UNSUPPORTED_SCHEMA
    assert reasons == ["RECEIPT_SCHEMA_UNSUPPORTED"]
    integrity, reasons = verify_bundle_sources(
        bundle,
        replace(
            source,
            integrity=EvidenceIntegrity.UNSUPPORTED_SCHEMA,
            gaps=(EvidenceGapCode.EVIDENCE_SOURCE_MISSING,),
        ),
    )
    assert integrity is EvidenceIntegrity.UNSUPPORTED_SCHEMA
    assert reasons == [EvidenceGapCode.EVIDENCE_SOURCE_MISSING.value]


def test_verifier_rejects_tampered_receipt_graph_quality_and_source_bindings() -> None:
    source = _source()
    bundle = build_evidence(source, generated_at=_CUTOFF + timedelta(minutes=1))
    summary = bundle.source_summary
    bad_fact = bundle.facts[0].model_copy(update={"cutoff_eligible": False})
    bad_receipt_node = bundle.nodes[0].model_copy(update={"source_entity_id": uuid4()})
    duplicate_source_nodes = list(bundle.nodes)
    duplicate_source_nodes[-1] = duplicate_source_nodes[-1].model_copy(
        update={"source_kind": duplicate_source_nodes[0].source_kind}
    )
    cases: list[tuple[PredictionEvidenceBundle, EvidenceSourceSnapshot, str]] = [
        (
            bundle.model_copy(update={"content_checksum": "f" * 64}),
            source,
            "BUNDLE_CONTENT_CHECKSUM_MISMATCH",
        ),
        (
            bundle.model_copy(update={"logical_fingerprint": "e" * 64}),
            source,
            "BUNDLE_IDENTITY_MISMATCH",
        ),
        (
            bundle.model_copy(update={"evidence_id": uuid4()}),
            source,
            "BUNDLE_IDENTITY_MISMATCH",
        ),
        (
            bundle.model_copy(update={"receipt_id": uuid4()}),
            source,
            "RECEIPT_ID_MISMATCH",
        ),
        (
            bundle.model_copy(
                update={"prediction": bundle.prediction.model_copy(update={"score": 0.1})}
            ),
            source,
            "RESPONSE_BINDING_MISMATCH",
        ),
        (
            bundle.model_copy(update={"source_role": SourceRole.REAL_VEHICLE}),
            source,
            "SOURCE_ROLE_MISMATCH",
        ),
        (
            bundle.model_copy(update={"effective_cutoff": _CUTOFF - timedelta(seconds=1)}),
            source,
            "CUTOFF_MISMATCH",
        ),
        (
            bundle.model_copy(update={"nodes": duplicate_source_nodes}),
            source,
            "DUPLICATE_SOURCE_NODE_KIND",
        ),
        (
            bundle.model_copy(update={"nodes": [bad_receipt_node, *bundle.nodes[1:]]}),
            source,
            "ROOT_RECEIPT_REFERENCE_MISMATCH",
        ),
        (
            bundle.model_copy(update={"provenance_manifest_checksum": "d" * 64}),
            source,
            "PROVENANCE_MANIFEST_CHECKSUM_MISMATCH",
        ),
        (
            bundle.model_copy(
                update={
                    "source_summary": summary.model_copy(
                        update={"source_role": SourceRole.REAL_VEHICLE}
                    )
                }
            ),
            source,
            "QUALITY_SOURCE_ROLE_MISMATCH",
        ),
        (
            bundle.model_copy(
                update={"source_summary": summary.model_copy(update={"quality_class": "degraded"})}
            ),
            source,
            "QUALITY_CLASS_MISMATCH",
        ),
        (
            bundle.model_copy(
                update={"source_summary": summary.model_copy(update={"receipt_coverage": 0.5})}
            ),
            source,
            "QUALITY_COVERAGE_MISMATCH",
        ),
        (
            bundle.model_copy(update={"facts": [bad_fact, *bundle.facts[1:]]}),
            source,
            "FACT_CUTOFF_INELIGIBLE",
        ),
        (
            bundle.model_copy(update={"integrity": EvidenceIntegrity.NOT_VERIFIABLE}),
            source,
            "COMPLETENESS_UPGRADE",
        ),
    ]
    for candidate, current, expected_reason in cases:
        integrity, reasons = verify_bundle_sources(candidate, current)
        assert integrity is EvidenceIntegrity.FAILED_SOURCE_MISMATCH
        assert expected_reason in reasons

    model = source.records[SourceKind.MODEL_VERSION]
    source_mismatches = [
        (
            replace(model, entity_id=uuid4()),
            "SOURCE_ID_MISMATCH_MODEL_VERSION",
        ),
        (
            replace(model, checksum="c" * 64),
            "SOURCE_CHECKSUM_MISMATCH_MODEL_VERSION",
        ),
        (
            replace(model, schema_checksum=sha256("different-schema")),
            "SOURCE_SCHEMA_CHECKSUM_MISMATCH_MODEL_VERSION",
        ),
    ]
    for altered_record, expected_reason in source_mismatches:
        current = replace(
            source,
            records=source.records | {SourceKind.MODEL_VERSION: altered_record},
        )
        integrity, reasons = verify_bundle_sources(bundle, current)
        assert integrity is EvidenceIntegrity.FAILED_SOURCE_MISMATCH
        assert expected_reason in reasons

    extra = _record(SourceKind.REFERENCE_DATASET, uuid4(), {})
    extra_source = replace(
        source,
        records=source.records | {SourceKind.REFERENCE_DATASET: extra},
    )
    integrity, reasons = verify_bundle_sources(bundle, extra_source)
    assert integrity is EvidenceIntegrity.FAILED_SOURCE_MISMATCH
    assert "UNBOUND_SOURCE_RECORD_REFERENCE_DATASET" in reasons

    inconsistent = replace(
        source,
        response=source.response.model_copy(update={"decision": False}),
    )
    integrity, reasons = verify_bundle_sources(bundle, inconsistent)
    assert integrity is EvidenceIntegrity.FAILED_SOURCE_MISMATCH
    assert "MODEL_SCORE_DECISION_MISMATCH" in reasons


def test_domain_validators_reject_unbounded_values_and_invalid_graph_bindings() -> None:
    def fact_input(value: Any, **updates: Any) -> dict[str, Any]:
        return {
            "fact_id": "fact",
            "key": "context.test",
            "fact_type": EvidenceFactType.CONTEXT_DESCRIPTOR,
            "value": value,
            "source_node_id": "receipt",
            "cutoff": _CUTOFF,
            "cutoff_eligible": True,
            "quality": FactQuality.VALID if value is not None else FactQuality.MISSING,
            "meaning": "test value",
            **updates,
        }

    EvidenceFact.model_validate(fact_input({"nested": [None, True, 1, 1.0]}))
    too_deep: Any = None
    for _ in range(10):
        too_deep = [too_deep]
    invalid_values = [
        float("nan"),
        "x" * 4_097,
        [None] * 65,
        {str(index): index for index in range(33)},
        {1: "invalid key"},
        too_deep,
        object(),
    ]
    for value in invalid_values:
        with pytest.raises(ValidationError):
            EvidenceFact.model_validate(fact_input(value))
    with pytest.raises(ValidationError):
        EvidenceFact.model_validate(fact_input(None, quality=FactQuality.VALID))
    with pytest.raises(ValidationError):
        EvidenceFact.model_validate(fact_input(1, missing_reason="unexpected"))
    with pytest.raises(ValidationError):
        EvidenceFact.model_validate(
            fact_input(
                1, source_window_start=_CUTOFF, source_window_end=_CUTOFF - timedelta(seconds=1)
            )
        )
    for time_field in ("observed_at", "available_at", "source_window_end"):
        with pytest.raises(ValidationError):
            EvidenceFact.model_validate(
                fact_input(1, **{time_field: _CUTOFF + timedelta(seconds=1)})
            )

    node = build_evidence(_source(), generated_at=_CUTOFF + timedelta(minutes=1)).nodes[0]
    with pytest.raises(ValidationError, match="time scope is inverted"):
        EvidenceNode.model_validate(
            node.model_dump(mode="python")
            | {
                "valid_from": _CUTOFF,
                "valid_through": _CUTOFF - timedelta(seconds=1),
            }
        )
    with pytest.raises(ValidationError, match="cannot reference itself"):
        EvidenceEdge(
            edge_id="self",
            source_node_id="receipt",
            target_node_id="receipt",
            relation=EvidenceEdgeType.DERIVED_FROM,
        )
    with pytest.raises(ValidationError, match="must be finite"):
        OriginalPrediction(status="READY_SCORE", score=float("inf"))

    bundle = build_evidence(_source(), generated_at=_CUTOFF + timedelta(minutes=1))
    base = bundle.model_dump(mode="python")
    invalid_bundles: list[dict[str, Any]] = []
    duplicate_node = copy.deepcopy(base)
    duplicate_node["nodes"][1] = duplicate_node["nodes"][0]
    invalid_bundles.append(duplicate_node)
    duplicate_fact = copy.deepcopy(base)
    duplicate_fact["facts"][1]["fact_id"] = duplicate_fact["facts"][0]["fact_id"]
    invalid_bundles.append(duplicate_fact)
    dangling_edge = copy.deepcopy(base)
    dangling_edge["edges"][0]["target_node_id"] = "absent"
    invalid_bundles.append(dangling_edge)
    dangling_fact = copy.deepcopy(base)
    dangling_fact["facts"][0]["source_node_id"] = "absent"
    invalid_bundles.append(dangling_fact)
    dangling_gap = copy.deepcopy(base)
    dangling_gap["gaps"] = [
        EvidenceGap(code=EvidenceGapCode.LOW_QUALITY, source_node_id="absent").model_dump(
            mode="python"
        )
    ]
    invalid_bundles.append(dangling_gap)
    dangling_claim = copy.deepcopy(base)
    dangling_claim["claims"][0]["fact_ids"] = ["absent"]
    invalid_bundles.append(dangling_claim)
    invalid_horizon = copy.deepcopy(base)
    invalid_horizon["horizon"] = "AFTER_PULL_OFFLINE"
    invalid_bundles.append(invalid_horizon)
    invalid_cutoff = copy.deepcopy(base)
    invalid_cutoff["requested_cutoff"] = _CUTOFF - timedelta(minutes=1)
    invalid_bundles.append(invalid_cutoff)
    for invalid_bundle in invalid_bundles:
        with pytest.raises(ValidationError):
            PredictionEvidenceBundle.model_validate(invalid_bundle)
