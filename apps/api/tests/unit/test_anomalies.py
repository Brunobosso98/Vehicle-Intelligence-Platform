from __future__ import annotations

import argparse
import hashlib
import io
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import joblib
import numpy as np
import pytest

from vehicle_platform.anomalies.artifacts import (
    AnomalyArtifactError,
    ArtifactStore,
    TrustedAnomalyArtifact,
)
from vehicle_platform.anomalies.cli import parse_cutoff, parse_pull_ids
from vehicle_platform.anomalies.definitions import (
    DEFAULT_DETECTORS,
    _make_definition,
    detector_definition,
)
from vehicle_platform.anomalies.detectors import (
    DetectorFitError,
    _forest_matrix,
    _robust_score,
    _robust_stats,
    _summary,
    fit_detector,
    score_observation,
    transform_features,
)
from vehicle_platform.anomalies.domain import (
    AnomalyFamily,
    AnomalyFindingResult,
    AnomalyReason,
    AnomalyReferenceDataset,
    AnomalyRunResult,
    AnomalyStatus,
    CohortIdentity,
    DetectorFeatureSpec,
    DetectorMethod,
    DeviationDirection,
    FeatureObservation,
    ReferenceRow,
    SourceRole,
    finding_idempotency_key,
)
from vehicle_platform.anomalies.evaluation import (
    MethodCandidate,
    classification_metrics,
    select_detector_method,
    select_validation_threshold,
)
from vehicle_platform.anomalies.repository import AnomalyRepositoryError, _feature_exclusion
from vehicle_platform.anomalies.service import (
    AnomalyService,
    _cohort_mismatch,
    summarize_family_findings,
)
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.registry import DEFAULT_REGISTRY


def _reference(
    family: AnomalyFamily,
    method: DetectorMethod,
    *,
    count: int = 30,
) -> tuple[object, AnomalyReferenceDataset]:
    definition = detector_definition(family, method)
    base = datetime(2025, 1, 1, tzinfo=UTC)
    vehicle_id = str(uuid4())
    configuration_id = str(uuid4())
    rows: list[ReferenceRow] = []
    for index in range(count):
        session_index = index // 3
        started = base + timedelta(days=session_index * 2, seconds=(index % 3) * 20)
        ended = started + timedelta(seconds=10)
        values: dict[str, FeatureObservation] = {}
        for key in definition.feature_keys:
            registry_item = DEFAULT_REGISTRY.resolve(key)
            ordinal = sum(ord(char) for char in key) % 7
            if key == "thermal.iat_start":
                value = 295.0 + (index % 9) * 0.3 + ordinal * 0.02
            elif key == "thermal.pre_pull_iat_k":
                value = 294.0 + (index % 9) * 0.2 + ordinal * 0.01
            elif key.startswith("thermal."):
                value = 1.0 + (index % 7) * 0.13 + ordinal * 0.01
            elif key.startswith("boost_air."):
                value = 110_000.0 + (index % 11) * 300.0 + ordinal * 10.0
            elif key.startswith("performance."):
                value = 2.0 + (index % 10) * 0.05 + ordinal * 0.001
            elif key.startswith("fuel."):
                value = 15_000_000.0 + (index % 13) * 20_000.0 + ordinal * 100.0
            else:
                value = float(index + ordinal)
            if registry_item.bounds:
                low, high = registry_item.bounds
                if low is not None:
                    value = max(value, low + 1.0)
                if high is not None:
                    value = min(value, high - 1.0)
            values[key] = FeatureObservation(
                key=key,
                value=value,
                unit=registry_item.unit,
                quality="valid",
                missing_reason=None,
                available_at=ended,
                source_window_end=ended,
                source_signals=registry_item.required_signals,
            )
        rows.append(
            ReferenceRow(
                row_id=stable_hash([family.value, method.value, "row", index]),
                feature_set_id=uuid4(),
                vehicle_id=vehicle_id,
                configuration_id=configuration_id,
                session_id=f"session-{session_index}",
                pull_id=str(uuid4()),
                pull_started_at=started,
                pull_ended_at=ended,
                observation_cutoff=ended,
                source_hash=stable_hash(["source", index]),
                provenance_hash=stable_hash(["provenance", index]),
                source_type="synthetic",
                source_role=SourceRole.SYNTHETIC,
                modification_ids=(),
                available_signals=definition.required_signal_keys,
                quality_metadata={
                    "pull_completeness": 1.0,
                    "invalid_observation_count": 0,
                    "duplicate_timestamp_count": 0,
                },
                features=values,
            )
        )
    dataset = AnomalyReferenceDataset(
        family=family,
        feature_set_version="phase9a-pull-v2",
        feature_set_version_checksum=stable_hash("phase9a-v2"),
        observation_cutoff=base + timedelta(days=25),
        cohort=rows[0].cohort,
        rows=tuple(rows),
        exclusions=(),
        source_role=SourceRole.SYNTHETIC,
        created_at=base + timedelta(days=26),
        anchor_session_id="anchor-session",
    )
    return definition, dataset


def _outlier(row: ReferenceRow, key: str) -> ReferenceRow:
    original = row.features[key]
    assert original.value is not None
    if key.startswith("thermal."):
        offset = 20.0
    elif key.startswith("boost_air."):
        offset = 30_000.0
    elif key.startswith("performance."):
        offset = 2.0
    elif key.startswith("fuel."):
        offset = 2_000_000.0
    else:
        offset = 20.0
    features = dict(row.features)
    features[key] = replace(original, value=original.value + offset)
    return replace(row, features=features)


def _evaluation_rows(reference: AnomalyReferenceDataset, family: AnomalyFamily):
    rows: list[ReferenceRow] = []
    labels = []
    detector = detector_definition(family, DetectorMethod.ROBUST_MAD)
    for index in range(4):
        row = reference.rows[index]
        started = reference.observation_cutoff + timedelta(days=1, seconds=index * 30)
        row = replace(
            row,
            row_id=stable_hash(["phase10-eval", family.value, index]),
            feature_set_id=uuid4(),
            session_id=f"evaluation-session-{index}",
            pull_id=str(uuid4()),
            pull_started_at=started,
            pull_ended_at=started + timedelta(seconds=10),
            observation_cutoff=started + timedelta(seconds=10),
            source_hash=stable_hash(["phase10-eval-source", index]),
            provenance_hash=stable_hash(["phase10-eval-provenance", index]),
        )
        scenario = "clean" if index < 2 else family.value
        if scenario != "clean":
            row = _outlier(row, detector.feature_keys[0])
        rows.append(row)
        labels.append((UUID(row.pull_id), scenario))
    labels.sort(key=lambda item: str(item[0]))
    return tuple(rows), tuple(labels)


def test_registry_exposes_four_families_and_two_methods() -> None:
    assert len(DEFAULT_DETECTORS) == 8
    assert {item.family for item in DEFAULT_DETECTORS} == {
        AnomalyFamily.THERMAL,
        AnomalyFamily.BOOST_AIR,
        AnomalyFamily.PERFORMANCE,
        AnomalyFamily.FUEL,
    }
    assert {item.method for item in DEFAULT_DETECTORS} == set(DetectorMethod)
    assert all(item.horizon == "AFTER_PULL_OFFLINE" for item in DEFAULT_DETECTORS)


@pytest.mark.parametrize(
    "family",
    (AnomalyFamily.THERMAL, AnomalyFamily.BOOST_AIR, AnomalyFamily.PERFORMANCE, AnomalyFamily.FUEL),
)
def test_mlops_anomaly_evaluation_uses_separate_oracle_and_keeps_claims_bounded(family) -> None:
    from vehicle_platform.mlops.anomaly_evaluation import evaluate_anomaly_candidate

    definition, reference = _reference(family, DetectorMethod.ROBUST_MAD)
    fitted = fit_detector(definition, reference)
    artifact = TrustedAnomalyArtifact(
        detector_version_id=str(uuid4()),
        version="candidate-1",
        definition=definition,
        fitted=fitted,
        reference_dataset_id=str(uuid4()),
        reference_checksum=reference.checksum(definition),
        reference_manifest=reference.manifest(definition),
        cohort=reference.cohort,
        fit_checksum=stable_hash("fit"),
        artifact_checksum=stable_hash("artifact"),
    )
    rows, label_items = _evaluation_rows(reference, family)
    oracle = {str(pull_id): scenario for pull_id, scenario in label_items}
    report = evaluate_anomaly_candidate(
        artifact,
        rows,
        oracle,
        training_cutoff=reference.observation_cutoff,
        cutoff=reference.observation_cutoff + timedelta(days=3),
    )
    assert report["status"] == "SYNTHETIC_EVALUATED"
    assert report["support"]["partition_conservation"] is True
    assert report["support"]["clean_rows"] == 2
    assert report["support"]["target_injections"] == 2
    assert report["target_metrics"]["positive_support"] == 2
    assert report["target_metrics"]["negative_support"] == 2
    assert report["score_is_probability"] is False
    assert report["real_world_predictive_validity"] == "NOT_ESTABLISHED"
    assert report["serving_action"] == "NONE"
    with pytest.raises(ValueError, match="EVALUATION_SESSION_LEAKAGE"):
        evaluate_anomaly_candidate(
            artifact,
            (replace(rows[0], session_id=reference.rows[0].session_id), *rows[1:]),
            oracle,
            training_cutoff=reference.observation_cutoff,
            cutoff=reference.observation_cutoff + timedelta(days=3),
        )


def test_mlops_anomaly_evaluation_rejects_incompatible_lineage_and_unknown_oracle(monkeypatch):
    from vehicle_platform.mlops import anomaly_evaluation

    family = AnomalyFamily.THERMAL
    definition, reference = _reference(family, DetectorMethod.ROBUST_MAD)
    fitted = fit_detector(definition, reference)
    artifact = TrustedAnomalyArtifact(
        detector_version_id=str(uuid4()),
        version="lineage-candidate",
        definition=definition,
        fitted=fitted,
        reference_dataset_id=str(uuid4()),
        reference_checksum=reference.checksum(definition),
        reference_manifest=reference.manifest(definition),
        cohort=reference.cohort,
        fit_checksum=stable_hash("lineage-fit"),
        artifact_checksum=stable_hash("lineage-artifact"),
    )
    rows, label_items = _evaluation_rows(reference, family)
    oracle = {str(pull_id): scenario for pull_id, scenario in label_items}
    options = {
        "training_cutoff": reference.observation_cutoff,
        "cutoff": reference.observation_cutoff + timedelta(days=3),
    }

    with pytest.raises(ValueError, match="EVALUATION_COHORT_MISMATCH"):
        anomaly_evaluation.evaluate_anomaly_candidate(artifact, (), {}, **options)
    with pytest.raises(ValueError, match="EVALUATION_COHORT_MISMATCH"):
        anomaly_evaluation.evaluate_anomaly_candidate(artifact, rows, {}, **options)
    with pytest.raises(ValueError, match="REFERENCE_LINEAGE_MISSING"):
        anomaly_evaluation.evaluate_anomaly_candidate(
            replace(artifact, reference_manifest={}), rows, oracle, **options
        )
    overlapping = (replace(rows[0], session_id=reference.rows[0].session_id), *rows[1:])
    with pytest.raises(ValueError, match="EVALUATION_SESSION_LEAKAGE"):
        anomaly_evaluation.evaluate_anomaly_candidate(artifact, overlapping, oracle, **options)
    changed_cohort = (replace(rows[0], vehicle_id=uuid4()), *rows[1:])
    with pytest.raises(ValueError, match="EVALUATION_COHORT_INCOMPATIBLE"):
        anomaly_evaluation.evaluate_anomaly_candidate(artifact, changed_cohort, oracle, **options)
    with pytest.raises(ValueError, match="EVALUATION_TIME_LEAKAGE"):
        anomaly_evaluation.evaluate_anomaly_candidate(
            artifact,
            rows,
            oracle,
            training_cutoff=rows[0].pull_started_at,
            cutoff=options["cutoff"],
        )
    with pytest.raises(ValueError, match="ORACLE_SCENARIO_UNSUPPORTED"):
        anomaly_evaluation.evaluate_anomaly_candidate(
            artifact, rows, {**oracle, rows[0].pull_id: "invented_label"}, **options
        )
    imported = tuple(
        replace(row, source_role=SourceRole.IMPORTED, source_type="imported") for row in rows
    )
    with pytest.raises(ValueError, match="SOURCE_ROLE_MISMATCH"):
        anomaly_evaluation.evaluate_anomaly_candidate(
            replace(artifact, cohort=imported[0].cohort), imported, oracle, **options
        )
    with pytest.raises(ValueError, match="EVALUATION_TIME_LEAKAGE"):
        anomaly_evaluation.evaluate_anomaly_candidate(
            artifact,
            rows,
            oracle,
            cutoff=rows[0].pull_ended_at - timedelta(seconds=1),
            training_cutoff=options["training_cutoff"],
        )

    monkeypatch.setattr(
        anomaly_evaluation,
        "score_observation",
        lambda *_args, **_kwargs: SimpleNamespace(
            score=0.7, status=SimpleNamespace(value="ANOMALOUS")
        ),
    )
    quality_oracle = {**oracle, rows[0].pull_id: "quality_excluded"}
    with pytest.raises(ValueError, match="QUALITY_CASE_NOT_ABSTAINED"):
        anomaly_evaluation.evaluate_anomaly_candidate(artifact, rows, quality_oracle, **options)

    unsupported_artifact = SimpleNamespace(
        definition=SimpleNamespace(
            family=SimpleNamespace(value="unsupported"), method=SimpleNamespace(value="fixture")
        ),
        reference_manifest={"selected_rows": []},
        cohort=artifact.cohort,
        fitted=artifact.fitted,
        detector_version_id="unsupported-version",
        artifact_checksum="a" * 64,
        reference_checksum="b" * 64,
    )
    with pytest.raises(ValueError, match="DERIVED_FAMILY_NOT_EVALUABLE"):
        anomaly_evaluation.evaluate_anomaly_candidate(unsupported_artifact, rows, oracle, **options)


@pytest.mark.asyncio
async def test_mlops_anomaly_evaluation_worker_verifies_lineage_and_report(
    monkeypatch, tmp_path
) -> None:
    from vehicle_platform.evaluation.contracts import SourceRole as EvaluationSourceRole
    from vehicle_platform.mlops import executor
    from vehicle_platform.mlops.contracts import (
        AnomalyOracleLabel,
        PipelineDefinition,
        PipelineKind,
    )
    from vehicle_platform.mlops.planner import (
        anomaly_evaluation_checksum,
        anomaly_evaluation_source_fingerprint,
    )

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.chdir(tmp_path)
    family = AnomalyFamily.THERMAL
    detector, reference = _reference(family, DetectorMethod.ROBUST_MAD)
    rows, label_items = _evaluation_rows(reference, family)
    labels = tuple(
        AnomalyOracleLabel(pull_id=pull_id, scenario=scenario) for pull_id, scenario in label_items
    )
    evaluation_cutoff = reference.observation_cutoff + timedelta(days=3)
    source_fingerprint = anomaly_evaluation_source_fingerprint(rows)
    oracle_checksum = stable_hash([item.model_dump(mode="json") for item in labels])
    definition = PipelineDefinition(
        definition_version="anomaly-evaluation-worker-v1",
        kind=PipelineKind.ANOMALY,
        family=family.value,
        method=DetectorMethod.ROBUST_MAD.value,
        anchor_pull_id=uuid4(),
        source_role=EvaluationSourceRole.SYNTHETIC,
        cutoff=reference.rows[-1].pull_ended_at,
        git_sha="a" * 40,
        expected_source_fingerprint=reference.source_fingerprint,
        expected_dataset_checksum=reference.checksum(detector),
        expected_feature_checksum=reference.feature_set_version_checksum,
        evaluation_cutoff=evaluation_cutoff,
        evaluation_pull_ids=tuple(sorted((UUID(row.pull_id) for row in rows), key=str)),
        expected_evaluation_checksum="0" * 64,
        expected_evaluation_source_fingerprint=source_fingerprint,
        evaluation_oracle=labels,
        expected_oracle_checksum=oracle_checksum,
    )
    definition = definition.model_copy(
        update={
            "expected_evaluation_checksum": anomaly_evaluation_checksum(
                definition,
                detector.checksum,
                reference.feature_set_version_checksum,
                rows,
            )
        }
    )
    fitted = fit_detector(detector, reference)
    artifact = TrustedAnomalyArtifact(
        detector_version_id=str(uuid4()),
        version="candidate-1",
        definition=detector,
        fitted=fitted,
        reference_dataset_id=str(uuid4()),
        reference_checksum=reference.checksum(detector),
        reference_manifest=reference.manifest(detector),
        cohort=reference.cohort,
        fit_checksum=stable_hash("fit"),
        artifact_checksum=stable_hash("artifact"),
    )
    database_digests = {"feature_sets": "1" * 64, "serving_bindings": "2" * 64}
    repository = SimpleNamespace(load_targets=AsyncMock(return_value=rows))
    store = SimpleNamespace(load_registered=AsyncMock(return_value=artifact))
    monkeypatch.setattr(executor, "AnomalyDataRepository", lambda _: repository)
    monkeypatch.setattr(executor, "DetectorArtifactStore", lambda: store)
    monkeypatch.setattr(executor, "checkout_is_dirty", AsyncMock(return_value=False))
    monkeypatch.setattr(executor, "source_table_digests", AsyncMock(return_value=database_digests))
    run_id = uuid4()
    result = await executor.evaluate_anomaly_job(
        None, definition, run_id=run_id, detector_version_id=UUID(artifact.detector_version_id)
    )
    from vehicle_platform.mlops.report_store import read_report

    assert result["evaluation_status"] == "SYNTHETIC_EVALUATED"
    assert read_report(run_id, expected_checksum=result["report_file_checksum"]) == result["report"]
    assert result["report"]["source_mutations"] is False
    assert result["report"]["phase9g_protocol_version"] == "phase9g-protocol-v2"
    assert result["serving_action"] == "NONE"
    assert result["real_world_predictive_validity"] == "NOT_ESTABLISHED"


@pytest.mark.asyncio
async def test_anomaly_comparison_uses_matched_active_binding_without_mutation(monkeypatch):
    from vehicle_platform.evaluation.contracts import SourceRole as EvaluationSourceRole
    from vehicle_platform.mlops import anomaly_comparison, planner
    from vehicle_platform.mlops.contracts import (
        AnomalyOracleLabel,
        PipelineDefinition,
        PipelineKind,
    )

    monkeypatch.setenv("ENVIRONMENT", "test")
    family = AnomalyFamily.THERMAL
    detector, reference = _reference(family, DetectorMethod.ROBUST_MAD)
    rows, label_items = _evaluation_rows(reference, family)
    labels = tuple(
        AnomalyOracleLabel(pull_id=pull_id, scenario=scenario) for pull_id, scenario in label_items
    )
    monkeypatch.setattr(
        planner,
        "default_feature_version",
        lambda: SimpleNamespace(
            version=reference.feature_set_version,
            checksum=reference.feature_set_version_checksum,
        ),
    )
    definition = PipelineDefinition(
        definition_version="anomaly-compare-v1",
        kind=PipelineKind.ANOMALY,
        family=family.value,
        method=DetectorMethod.ROBUST_MAD.value,
        anchor_pull_id=uuid4(),
        source_role=EvaluationSourceRole.SYNTHETIC,
        cutoff=reference.rows[-1].pull_ended_at,
        git_sha="a" * 40,
        expected_source_fingerprint=reference.source_fingerprint,
        expected_dataset_checksum=reference.checksum(detector),
        expected_feature_checksum=reference.feature_set_version_checksum,
        evaluation_cutoff=reference.observation_cutoff + timedelta(days=3),
        evaluation_pull_ids=tuple(sorted((UUID(row.pull_id) for row in rows), key=str)),
        expected_evaluation_checksum="0" * 64,
        expected_evaluation_source_fingerprint=planner.anomaly_evaluation_source_fingerprint(rows),
        evaluation_oracle=labels,
        expected_oracle_checksum=stable_hash([item.model_dump(mode="json") for item in labels]),
    )
    definition = definition.model_copy(
        update={
            "expected_evaluation_checksum": planner.anomaly_evaluation_checksum(
                definition,
                detector.checksum,
                reference.feature_set_version_checksum,
                rows,
            )
        }
    )
    fitted = fit_detector(detector, reference)
    champion = TrustedAnomalyArtifact(
        detector_version_id=str(uuid4()),
        version="champion-1",
        definition=detector,
        fitted=fitted,
        reference_dataset_id=str(uuid4()),
        reference_checksum=reference.checksum(detector),
        reference_manifest=reference.manifest(detector),
        cohort=reference.cohort,
        fit_checksum=stable_hash("champion-fit"),
        artifact_checksum=stable_hash("champion-artifact"),
    )
    challenger = replace(
        champion,
        detector_version_id=str(uuid4()),
        version="challenger-1",
        fit_checksum=stable_hash("challenger-fit"),
        artifact_checksum=stable_hash("challenger-artifact"),
    )
    binding_id, event_id = uuid4(), uuid4()
    binding = SimpleNamespace(
        id=binding_id,
        is_active=True,
        detector_version_id=UUID(champion.detector_version_id),
        artifact_checksum=champion.artifact_checksum,
        environment="test",
        scope="controlled-engineering-dataset",
        result_kind="anomaly",
        subject_key=family.value,
        source_role=EvaluationSourceRole.SYNTHETIC,
        feature_set_version="phase9a-pull-v2",
        feature_set_checksum=reference.feature_set_version_checksum,
        latest_event_id=event_id,
    )
    database_digests = {"feature_sets": "1" * 64, "serving_bindings": "2" * 64}
    prediction_repo = SimpleNamespace(binding=AsyncMock(return_value=binding))
    anomaly_repo = SimpleNamespace(load_targets=AsyncMock(return_value=rows))
    artifacts = SimpleNamespace(
        load_registered=AsyncMock(side_effect=[champion, challenger, champion, challenger])
    )
    monkeypatch.setattr(anomaly_comparison, "checkout_is_dirty", AsyncMock(return_value=False))
    monkeypatch.setattr(anomaly_comparison, "PredictionRepository", lambda _: prediction_repo)
    monkeypatch.setattr(anomaly_comparison, "AnomalyDataRepository", lambda _: anomaly_repo)
    monkeypatch.setattr(anomaly_comparison, "DetectorArtifactStore", lambda: artifacts)
    monkeypatch.setattr(
        anomaly_comparison, "prior_source_digest", AsyncMock(return_value=database_digests)
    )
    result = await anomaly_comparison.compare_anomaly(
        object(),
        definition,
        champion_binding_id=binding_id,
        challenger_version_id=UUID(challenger.detector_version_id),
    )
    assert result["status"] == "COMPARABLE_OFFLINE"
    assert result["eligible_rows"] == len(rows)
    assert result["method_score_scales_compared"] is False
    assert result["delta"]["recall"] == 0.0
    assert result["serving_action"] == "NONE"
    assert result["real_world_predictive_validity"] == "NOT_ESTABLISHED"


@pytest.mark.asyncio
async def test_detector_fit_rejects_changed_reference_before_any_registration(tmp_path) -> None:
    definition, reference = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    anchor = reference.rows[-1]
    repo = SimpleNamespace(
        load_anchor=AsyncMock(
            return_value=(anchor, uuid4(), reference.feature_set_version_checksum)
        ),
        materialize_reference=AsyncMock(return_value=reference),
    )
    registry = SimpleNamespace(persist_reference=AsyncMock())
    service = AnomalyService(
        None, repository=repo, registry=registry, artifacts=ArtifactStore(tmp_path)
    )
    request = {
        "anchor_pull_id": uuid4(),
        "observation_cutoff": anchor.pull_ended_at,
        "source_role": SourceRole.SYNTHETIC,
        "family": "thermal",
        "method": "robust_mad",
    }
    for invalid in (
        {"expected_feature_checksum": "0" * 64},
        {"expected_reference_checksum": "0" * 64},
        {"expected_source_fingerprint": "0" * 64},
        {"expected_source_type": "obd"},
        {"max_reference_rows": 1},
        {"max_reference_sessions": 1},
    ):
        with pytest.raises(AnomalyRepositoryError):
            await service.fit_detector_version(**request, **invalid)
    registry.persist_reference.assert_not_awaited()
    assert (
        reference.source_fingerprint
        != replace(
            reference, rows=(replace(reference.rows[0], source_hash="0" * 64), *reference.rows[1:])
        ).source_fingerprint
    )
    assert reference.checksum(definition) != "0" * 64


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "family",
    (AnomalyFamily.THERMAL, AnomalyFamily.BOOST_AIR, AnomalyFamily.PERFORMANCE, AnomalyFamily.FUEL),
)
@pytest.mark.parametrize("method", (DetectorMethod.ROBUST_MAD, DetectorMethod.ISOLATION_FOREST))
async def test_guarded_detector_fit_uses_actual_9c_path(tmp_path, family, method) -> None:
    detector, reference = _reference(family, method)
    anchor = reference.rows[-1]
    reference_id, version_id = uuid4(), uuid4()
    repo = SimpleNamespace(
        load_anchor=AsyncMock(
            return_value=(anchor, uuid4(), reference.feature_set_version_checksum)
        ),
        materialize_reference=AsyncMock(return_value=reference),
    )
    registry = SimpleNamespace(
        persist_reference=AsyncMock(return_value=reference_id),
        reserve_version=AsyncMock(return_value="a00000001"),
        persist_detector_version=AsyncMock(return_value=(version_id, "a00000001", True)),
    )
    service = AnomalyService(
        None, repository=repo, registry=registry, artifacts=ArtifactStore(tmp_path)
    )
    result = await service.fit_detector_version(
        anchor_pull_id=uuid4(),
        observation_cutoff=anchor.pull_ended_at,
        source_role=SourceRole.SYNTHETIC,
        family=family.value,
        method=method.value,
        git_sha="a" * 40,
        expected_reference_checksum=reference.checksum(detector),
        expected_source_fingerprint=reference.source_fingerprint,
        expected_feature_checksum=reference.feature_set_version_checksum,
        expected_source_type="synthetic",
        max_reference_rows=40,
        max_reference_sessions=15,
    )
    assert result.reference_checksum == reference.checksum(detector)
    assert result.detector_version_id == version_id
    assert result.artifact_checksum is not None
    assert result.state.value == "CANDIDATE"
    registry.persist_reference.assert_awaited_once()
    registry.persist_detector_version.assert_awaited_once()
    assert list(tmp_path.rglob("*.joblib"))


@pytest.mark.asyncio
async def test_detector_artifact_budget_cleans_unregistered_staging(tmp_path) -> None:
    _, reference = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    anchor = reference.rows[-1]
    repo = SimpleNamespace(
        load_anchor=AsyncMock(
            return_value=(anchor, uuid4(), reference.feature_set_version_checksum)
        ),
        materialize_reference=AsyncMock(return_value=reference),
    )
    registry = SimpleNamespace(
        persist_reference=AsyncMock(return_value=uuid4()),
        reserve_version=AsyncMock(return_value="a00000001"),
        persist_detector_version=AsyncMock(),
    )
    service = AnomalyService(
        None, repository=repo, registry=registry, artifacts=ArtifactStore(tmp_path)
    )
    with pytest.raises(AnomalyRepositoryError, match="artifact exceeds"):
        await service.fit_detector_version(
            anchor_pull_id=uuid4(),
            observation_cutoff=anchor.pull_ended_at,
            source_role=SourceRole.SYNTHETIC,
            family="thermal",
            method="robust_mad",
            git_sha="a" * 40,
            max_artifact_bytes=1,
        )
    registry.persist_detector_version.assert_not_awaited()
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


@pytest.mark.asyncio
async def test_reference_preflight_uses_snapshot_and_rejects_oversized_selection() -> None:
    from vehicle_platform.anomalies.repository import AnomalyDataRepository

    definition, reference = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    response = SimpleNamespace(
        mappings=lambda: SimpleNamespace(one=lambda: {"row_count": 11, "payload_bytes": 1})
    )

    class ReadSession:
        def __init__(self):
            self.commands = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def execute(self, statement, *_):
            self.commands.append(str(statement))
            return response

    session = ReadSession()
    repo = AnomalyDataRepository(SimpleNamespace(session=lambda: session))
    with pytest.raises(AnomalyRepositoryError, match="declared row bound"):
        await repo.materialize_reference(
            reference.rows[-1],
            uuid4(),
            reference.feature_set_version_checksum,
            definition,
            SourceRole.SYNTHETIC,
            max_rows=10,
        )
    assert "REPEATABLE READ READ ONLY" in session.commands[0]
    assert len(session.commands) == 2


@pytest.mark.asyncio
async def test_mlops_anomaly_worker_records_only_verified_candidate(monkeypatch) -> None:
    from vehicle_platform.anomalies.domain import DetectorLifecycle
    from vehicle_platform.evaluation.contracts import SourceRole as EvaluationSourceRole
    from vehicle_platform.mlops import executor
    from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind

    monkeypatch.setenv("ENVIRONMENT", "test")
    detector, reference = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    definition = PipelineDefinition(
        definition_version="anomaly-worker-v1",
        kind=PipelineKind.ANOMALY,
        family="thermal",
        method="robust_mad",
        anchor_pull_id=uuid4(),
        source_role=EvaluationSourceRole.SYNTHETIC,
        cutoff=reference.rows[-1].pull_ended_at,
        git_sha="a" * 40,
        expected_source_fingerprint=reference.source_fingerprint,
        expected_dataset_checksum=reference.checksum(detector),
        expected_feature_checksum=reference.feature_set_version_checksum,
    )
    version_id = uuid4()
    checksum = "c" * 64
    fit = SimpleNamespace(
        state=DetectorLifecycle.CANDIDATE,
        detector_version_id=version_id,
        reference_dataset_id=uuid4(),
        reference_checksum=definition.expected_dataset_checksum,
        artifact_checksum=checksum,
    )
    service = SimpleNamespace(fit_detector_version=AsyncMock(return_value=fit))
    artifact = SimpleNamespace(
        artifact_checksum=checksum,
        reference_checksum=definition.expected_dataset_checksum,
        definition=detector,
    )
    store = SimpleNamespace(load_registered=AsyncMock(return_value=artifact))
    record = AsyncMock()
    monkeypatch.setattr(executor, "checkout_is_dirty", AsyncMock(return_value=False))
    monkeypatch.setattr(executor, "AnomalyService", lambda _: service)
    monkeypatch.setattr(executor, "DetectorArtifactStore", lambda: store)
    monkeypatch.setattr(
        executor, "ControlPlaneRepository", lambda _: SimpleNamespace(record_step=record)
    )
    output = await executor.execute_anomaly_fit_job(
        None, definition, run_id=uuid4(), token=uuid4(), fence=1
    )
    assert output["evaluation_status"] == "NOT_EXECUTED"
    assert output["serving_action"] == "NONE"
    assert [call.kwargs["state"] for call in record.await_args_list] == [
        "RUNNING",
        "SUCCEEDED",
        "RUNNING",
        "SUCCEEDED",
    ]
    assert service.fit_detector_version.await_args.kwargs["expected_source_type"] == "synthetic"
    artifact.artifact_checksum = "d" * 64
    with pytest.raises(ValueError, match="ARTIFACT_TAMPERED"):
        await executor.execute_anomaly_fit_job(
            None, definition, run_id=uuid4(), token=uuid4(), fence=1
        )
    assert record.await_args_list[-1].kwargs["state"] == "FAILED"
    assert record.await_args_list[-1].kwargs["output"]["reason"] == "ARTIFACT_INVALID"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "family",
    (AnomalyFamily.THERMAL, AnomalyFamily.BOOST_AIR, AnomalyFamily.PERFORMANCE, AnomalyFamily.FUEL),
)
async def test_mlops_anomaly_plan_checks_reference_and_source_without_writes(monkeypatch, family):
    from vehicle_platform.evaluation.contracts import SourceRole as EvaluationSourceRole
    from vehicle_platform.mlops import planner
    from vehicle_platform.mlops.contracts import (
        AnomalyOracleLabel,
        PipelineDefinition,
        PipelineKind,
    )

    monkeypatch.setenv("ENVIRONMENT", "test")
    detector, reference = _reference(family, DetectorMethod.ROBUST_MAD)
    anchor = reference.rows[-1]
    evaluation_rows, oracle_labels = _evaluation_rows(reference, family)
    repo = SimpleNamespace(
        load_anchor=AsyncMock(
            return_value=(anchor, uuid4(), reference.feature_set_version_checksum)
        ),
        materialize_reference=AsyncMock(return_value=reference),
        load_targets=AsyncMock(return_value=evaluation_rows),
    )
    monkeypatch.setattr(planner, "checkout_is_dirty", AsyncMock(return_value=False))
    monkeypatch.setattr(planner, "AnomalyDataRepository", lambda _: repo)
    monkeypatch.setattr(
        planner,
        "default_feature_version",
        lambda: SimpleNamespace(
            version=reference.feature_set_version, checksum=reference.feature_set_version_checksum
        ),
    )
    evaluation_oracle = tuple(
        AnomalyOracleLabel(pull_id=pull_id, scenario=scenario)
        for pull_id, scenario in oracle_labels
    )
    definition = PipelineDefinition(
        definition_version=f"anomaly-{family.value}-v1",
        kind=PipelineKind.ANOMALY,
        family=family.value,
        method="robust_mad",
        anchor_pull_id=uuid4(),
        source_role=EvaluationSourceRole.SYNTHETIC,
        cutoff=anchor.pull_ended_at,
        git_sha="a" * 40,
        expected_source_fingerprint=reference.source_fingerprint,
        expected_dataset_checksum=reference.checksum(detector),
        expected_feature_checksum=reference.feature_set_version_checksum,
        evaluation_cutoff=reference.observation_cutoff + timedelta(days=3),
        evaluation_pull_ids=tuple(sorted((UUID(row.pull_id) for row in evaluation_rows), key=str)),
        expected_evaluation_checksum="0" * 64,
        expected_evaluation_source_fingerprint=planner.anomaly_evaluation_source_fingerprint(
            evaluation_rows
        ),
        evaluation_oracle=evaluation_oracle,
        expected_oracle_checksum=stable_hash(
            [item.model_dump(mode="json") for item in evaluation_oracle]
        ),
    )
    definition = definition.model_copy(
        update={
            "expected_evaluation_checksum": planner.anomaly_evaluation_checksum(
                definition,
                detector.checksum,
                reference.feature_set_version_checksum,
                evaluation_rows,
            )
        }
    )
    result = await planner.plan_anomaly(None, definition)
    assert result["status"] == "READY_TO_REVIEW"
    assert result["evaluation_status"] == "READY"
    assert result["evaluation_rows"] == 4
    assert result["writes_on_plan"] == []
    assert result["serving_action"] == "NONE"
    bad = definition.model_copy(update={"expected_source_fingerprint": "0" * 64})
    assert (await planner.plan_anomaly(None, bad))["reason"] == "SOURCE_FINGERPRINT_MISMATCH"
    repo.load_anchor.return_value = (
        replace(anchor, source_type="obd"),
        uuid4(),
        reference.feature_set_version_checksum,
    )
    assert (await planner.plan_anomaly(None, definition))["reason"] == "SOURCE_ROLE_MISMATCH"


def test_definition_lookup_rejects_unknown_and_derived_families() -> None:
    with pytest.raises(ValueError, match="unknown anomaly"):
        detector_definition("unknown", DetectorMethod.ROBUST_MAD)
    with pytest.raises(ValueError, match="unknown anomaly"):
        detector_definition(AnomalyFamily.THERMAL, "unknown")
    with pytest.raises(ValueError, match="derived"):
        detector_definition(AnomalyFamily.MULTIVARIATE, DetectorMethod.ROBUST_MAD)
    with pytest.raises(ValueError, match="derived"):
        _make_definition(AnomalyFamily.MULTIVARIATE, DetectorMethod.ROBUST_MAD)


def test_boost_detector_v2_excludes_rolling_9a_history_deviation() -> None:
    definition = detector_definition(AnomalyFamily.BOOST_AIR, DetectorMethod.ROBUST_MAD)

    assert definition.version == "2.0.0"
    assert "boost_air.history_deviation_pa" not in definition.feature_keys
    assert "boost_air.pressure_mean" in definition.feature_keys


@pytest.mark.parametrize("method", tuple(DetectorMethod))
@pytest.mark.parametrize(
    ("family", "key"),
    (
        (AnomalyFamily.THERMAL, "thermal.iat_delta_k"),
        (AnomalyFamily.BOOST_AIR, "boost_air.pressure_mean"),
        (AnomalyFamily.PERFORMANCE, "performance.rpm_3500_4500_s_per_1000rpm"),
        (AnomalyFamily.FUEL, "fuel.rail_pressure_min"),
    ),
)
def test_all_families_score_deterministic_point_deviations(
    family: AnomalyFamily,
    key: str,
    method: DetectorMethod,
) -> None:
    definition, dataset = _reference(family, method)
    fitted = fit_detector(definition, dataset)
    repeated = fit_detector(definition, dataset)
    assert fitted.checksum == repeated.checksum
    target = _outlier(dataset.rows[len(dataset.rows) // 2], key)
    cutoff = dataset.observation_cutoff + timedelta(days=1)
    first = score_observation(definition, fitted, target, observation_cutoff=cutoff)
    second = score_observation(definition, fitted, target, observation_cutoff=cutoff)
    assert first.score == second.score
    assert first.score is not None and first.threshold is not None
    if method is DetectorMethod.ROBUST_MAD:
        assert first.status is AnomalyStatus.ANOMALOUS
        assert first.score > first.threshold
    else:
        baseline = score_observation(
            definition,
            fitted,
            dataset.rows[len(dataset.rows) // 2],
            observation_cutoff=cutoff,
        )
        assert baseline.score is not None
        assert first.score > baseline.score
    assert first.score_orientation == "higher_is_more_statistically_unusual"


def test_oracle_labels_and_entity_ids_cannot_influence_detector_score() -> None:
    definition, dataset = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    fitted = fit_detector(definition, dataset)
    target = dataset.rows[-1]
    cutoff = dataset.observation_cutoff + timedelta(days=1)
    baseline = score_observation(definition, fitted, target, observation_cutoff=cutoff)

    features = dict(target.features)
    features["evaluation.oracle_scenario"] = FeatureObservation(
        key="evaluation.oracle_scenario",
        value=1_000_000.0,
        unit="label",
        quality="valid",
        missing_reason=None,
        available_at=target.pull_ended_at,
        source_window_end=target.pull_ended_at,
    )
    adversarial = replace(
        target,
        vehicle_id="oracle-vehicle-id",
        session_id="oracle-session-id",
        pull_id="oracle-target-pull-id",
        features=features,
        quality_metadata={**target.quality_metadata, "scenario_label": "thermal"},
    )
    result = score_observation(definition, fitted, adversarial, observation_cutoff=cutoff)
    assert "evaluation.oracle_scenario" not in definition.feature_keys
    assert result.score == baseline.score
    assert result.status is baseline.status


def test_cohort_modification_change_is_incompatible_before_session_overlap() -> None:
    definition, dataset = _reference(AnomalyFamily.BOOST_AIR, DetectorMethod.ROBUST_MAD)
    fitted = fit_detector(definition, dataset)
    artifact = TrustedAnomalyArtifact(
        detector_version_id="version-id",
        version="a00000001",
        definition=definition,
        fitted=fitted,
        reference_dataset_id="reference-id",
        reference_checksum=dataset.checksum(definition),
        reference_manifest=dataset.manifest(definition),
        cohort=dataset.cohort,
        fit_checksum=stable_hash("fit"),
        artifact_checksum=stable_hash("artifact"),
    )
    changed = replace(dataset.rows[-1], modification_ids=("new-intake-modification",))
    reason = _cohort_mismatch(
        changed,
        artifact,
        {"cohort_checksum": dataset.cohort.checksum},
        SourceRole.SYNTHETIC,
    )
    assert reason is AnomalyReason.MODIFICATION_MISMATCH


def test_missing_required_feature_abstains_instead_of_scoring() -> None:
    definition, dataset = _reference(AnomalyFamily.FUEL, DetectorMethod.ROBUST_MAD)
    fitted = fit_detector(definition, dataset)
    target = dataset.rows[-1]
    key = definition.required_feature_keys[0]
    features = dict(target.features)
    features[key] = replace(
        features[key],
        value=None,
        quality="missing",
        missing_reason="unavailable_signal",
    )
    target = replace(target, features=features, available_signals=())
    result = score_observation(
        definition,
        fitted,
        target,
        observation_cutoff=dataset.observation_cutoff + timedelta(days=1),
    )
    assert result.status is AnomalyStatus.UNSUPPORTED_SOURCE
    assert result.score is None
    assert result.reasons == (AnomalyReason.REQUIRED_SIGNAL_UNAVAILABLE,)


def test_optional_unavailable_feature_is_missing_but_invalid_quality_is_rejected() -> None:
    definition, dataset = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    target = dataset.rows[-1]
    optional_key = "thermal.pre_pull_iat_k"
    features = dict(target.features)
    features[optional_key] = replace(
        features[optional_key],
        value=None,
        quality="unavailable",
        missing_reason="unavailable_signal",
    )
    unavailable = replace(target, features=features)
    assert _feature_exclusion(unavailable, definition) is None

    features[optional_key] = replace(features[optional_key], quality="invalid")
    invalid = replace(target, features=features)
    assert _feature_exclusion(invalid, definition) == AnomalyReason.INVALID_FEATURE_VALUE.value


def test_future_feature_and_cutoff_are_not_scored() -> None:
    definition, dataset = _reference(AnomalyFamily.BOOST_AIR, DetectorMethod.ROBUST_MAD)
    fitted = fit_detector(definition, dataset)
    target = dataset.rows[-1]
    key = definition.required_feature_keys[0]
    features = dict(target.features)
    features[key] = replace(
        features[key], available_at=dataset.observation_cutoff + timedelta(hours=1)
    )
    future = replace(target, features=features)
    result = score_observation(
        definition,
        fitted,
        future,
        observation_cutoff=dataset.observation_cutoff,
    )
    assert result.status is AnomalyStatus.NOT_EVALUABLE
    assert result.reasons == (AnomalyReason.FUTURE_FEATURE,)
    early = score_observation(
        definition,
        fitted,
        target,
        observation_cutoff=target.pull_started_at,
    )
    assert early.status is AnomalyStatus.NOT_EVALUABLE
    assert early.reasons == (AnomalyReason.CUTOFF_BEFORE_PULL_END,)


def test_unit_mismatch_is_treated_as_missing_signal_not_an_extreme() -> None:
    definition, dataset = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    fitted = fit_detector(definition, dataset)
    target = dataset.rows[-1]
    key = definition.required_feature_keys[0]
    features = dict(target.features)
    features[key] = replace(features[key], unit="degC")
    target = replace(target, features=features)
    transformed, missing = transform_features(definition, target)
    assert transformed[definition.features[1].score_key] is None
    assert key in missing
    result = score_observation(
        definition,
        fitted,
        target,
        observation_cutoff=dataset.observation_cutoff + timedelta(days=1),
    )
    assert result.status is AnomalyStatus.INSUFFICIENT_SIGNAL
    assert result.score is None


def test_isolation_forest_needs_more_rows_and_constant_features_are_excluded() -> None:
    definition, small = _reference(
        AnomalyFamily.PERFORMANCE,
        DetectorMethod.ISOLATION_FOREST,
        count=20,
    )
    with pytest.raises(DetectorFitError) as raised:
        fit_detector(definition, small)
    assert raised.value.reason is AnomalyReason.REFERENCE_SUPPORT_TOO_LOW

    definition, dataset = _reference(AnomalyFamily.PERFORMANCE, DetectorMethod.ROBUST_MAD)
    constant_features = {
        key: replace(item, value=1.0) for key, item in dataset.rows[0].features.items()
    }
    constant_rows = tuple(replace(row, features=constant_features) for row in dataset.rows)
    constant = replace(dataset, rows=constant_rows)
    with pytest.raises(DetectorFitError) as constant_error:
        fit_detector(definition, constant)
    assert constant_error.value.reason is AnomalyReason.CONSTANT_FEATURES_ONLY


def test_isolation_forest_fits_and_scores_optional_missingness_indicators() -> None:
    definition, dataset = _reference(AnomalyFamily.FUEL, DetectorMethod.ISOLATION_FOREST)
    optional_key = next(
        key for key in definition.feature_keys if key not in definition.required_feature_keys
    )
    first_features = dict(dataset.rows[0].features)
    first_features[optional_key] = replace(
        first_features[optional_key],
        value=None,
        quality="missing",
        missing_reason="unavailable_signal",
    )
    rows = (replace(dataset.rows[0], features=first_features), *dataset.rows[1:])
    incomplete = replace(dataset, rows=rows)
    fitted = fit_detector(definition, incomplete)
    assert optional_key in fitted.missing_indicator_order
    abstained = score_observation(
        definition,
        fitted,
        incomplete.rows[0],
        observation_cutoff=incomplete.observation_cutoff + timedelta(days=1),
    )
    assert abstained.reasons == (AnomalyReason.FEATURE_COVERAGE_TOO_LOW,)
    scored = score_observation(
        definition,
        fitted,
        incomplete.rows[-1],
        observation_cutoff=incomplete.observation_cutoff + timedelta(days=1),
    )
    assert scored.score is not None


def test_artifact_round_trip_rejects_tampering_and_traversal(tmp_path) -> None:
    definition, dataset = _reference(AnomalyFamily.FUEL, DetectorMethod.ISOLATION_FOREST)
    fitted = fit_detector(definition, dataset)
    store = ArtifactStore(tmp_path)
    fit_checksum = stable_hash([definition.checksum, dataset.checksum(definition)])
    receipt = store.write(definition, fitted, version="a00000001", fit_checksum=fit_checksum)
    store.verify_staged(
        receipt,
        definition=definition,
        fitted=fitted,
        version="a00000001",
        fit_checksum=fit_checksum,
    )
    artifact_path = tmp_path / receipt.relative_path
    artifact_path.write_bytes(artifact_path.read_bytes() + b"tamper")
    with pytest.raises(AnomalyArtifactError, match="checksum changed"):
        store.verify_staged(
            receipt,
            definition=definition,
            fitted=fitted,
            version="a00000001",
            fit_checksum=fit_checksum,
        )
    with pytest.raises(AnomalyArtifactError, match="outside"):
        store._checked_path(tmp_path / "../escape")


def test_artifact_staging_failure_removes_unregistered_files(tmp_path, monkeypatch) -> None:
    definition, dataset = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    fitted = fit_detector(definition, dataset)
    store = ArtifactStore(tmp_path)
    fit_checksum = stable_hash([definition.checksum, dataset.checksum(definition)])

    def fail_verification(*args, **kwargs):
        raise AnomalyArtifactError("injected interrupted verification")

    monkeypatch.setattr(store, "_verify_staged", fail_verification)
    with pytest.raises(AnomalyArtifactError, match="interrupted verification"):
        store.write(definition, fitted, version="a00000002", fit_checksum=fit_checksum)
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_detector_loads_only_the_verified_snapshot(tmp_path, monkeypatch) -> None:
    root = tmp_path / "root"
    root.mkdir()
    artifact = root / "detector.joblib"
    stream = io.BytesIO()
    joblib.dump({"safe": True}, stream)
    content = stream.getvalue()
    artifact.write_bytes(content)
    checksum = hashlib.sha256(content).hexdigest()
    load = joblib.load

    def replace_after_verification(source):
        artifact.write_bytes(b"replaced after verification")
        assert isinstance(source, io.BytesIO)
        return load(source)

    monkeypatch.setattr(joblib, "load", replace_after_verification)
    store = ArtifactStore(root)
    assert store._load_verified(artifact, checksum) == {"safe": True}
    monkeypatch.setattr(joblib, "load", lambda *_: pytest.fail("unverified bytes were loaded"))
    with pytest.raises(AnomalyArtifactError, match="checksum"):
        store._load_verified(artifact, checksum)
    artifact.unlink()
    external = tmp_path / "external.joblib"
    external.write_bytes(content)
    artifact.symlink_to(external)
    with pytest.raises(AnomalyArtifactError, match="unsafe"):
        store._load_verified(artifact, checksum)


def test_cli_requires_timezone_and_bounded_unique_pull_ids() -> None:
    assert parse_cutoff("2026-01-01T00:00:00Z").utcoffset() == timedelta(0)
    with pytest.raises(argparse.ArgumentTypeError):
        parse_cutoff("2026-01-01T00:00:00")
    pull_id = uuid4()
    assert parse_pull_ids(str(pull_id)) == (pull_id,)
    with pytest.raises(argparse.ArgumentTypeError):
        parse_pull_ids(f"{pull_id},{pull_id}")


def test_validation_threshold_selection_and_candidate_tie_break_are_deterministic() -> None:
    metrics = classification_metrics((0.1, 0.4, 0.8, None), (False, False, True, True), 0.5)
    assert metrics["tp"] == 1 and metrics["tn"] == 2
    assert metrics["abstained_positive"] == 1
    assert metrics["recall"] == 0.5
    selected = select_validation_threshold(
        scores=(0.1, 0.2, 0.8, 0.9),
        labels=(False, False, True, True),
        initial_threshold=0.5,
        maximum_clean_false_positive_rate=0.0,
        minimum_coverage=1.0,
        minimum_injection_recall=0.5,
    )
    assert selected.accepted
    assert selected.threshold == 0.5
    robust = MethodCandidate(
        DetectorMethod.ROBUST_MAD,
        0.2,
        {"false_positive_rate": 0.0, "anomaly_coverage": 1.0, "recall": 0.5, "precision": 1.0},
    )
    forest = MethodCandidate(
        DetectorMethod.ISOLATION_FOREST,
        0.2,
        {"false_positive_rate": 0.0, "anomaly_coverage": 1.0, "recall": 0.5, "precision": 1.0},
    )
    assert (
        select_detector_method(
            (forest, robust),
            maximum_clean_false_positive_rate=0.0,
            minimum_coverage=1.0,
        ).method
        is DetectorMethod.ROBUST_MAD
    )


def test_multifamily_summary_is_insufficient_until_two_family_scores_exist() -> None:
    anomalous = AnomalyFindingResult(
        status=AnomalyStatus.ANOMALOUS,
        score=5.0,
        threshold=4.0,
        coverage=1.0,
        observed_features=("x",),
        absent_features=(),
        contributions=(),
        reasons=(),
    )
    inlier = replace(anomalous, status=AnomalyStatus.INLIER, score=1.0)
    one = summarize_family_findings({"thermal": anomalous})
    assert one["status"] == "INSUFFICIENT_FAMILY_COVERAGE"
    two = summarize_family_findings({"thermal": anomalous, "boost_air": inlier})
    assert two["status"] == "NO_MULTI_FAMILY_DEVIATION"
    three = summarize_family_findings(
        {"thermal": anomalous, "boost_air": inlier, "fuel": anomalous}
    )
    assert three["status"] == "MULTI_FAMILY_DEVIATION"


def test_domain_value_objects_reject_invalid_shapes_and_preserve_identity() -> None:
    with pytest.raises(ValueError, match="key, unit"):
        DetectorFeatureSpec("", "K", "PULL_END")
    with pytest.raises(ValueError, match="matching units"):
        DetectorFeatureSpec(
            "x", "K", "PULL_END", transform="difference", context_key="y", context_unit="C"
        )
    with pytest.raises(ValueError, match="valid only"):
        DetectorFeatureSpec("x", "K", "PULL_END", context_key="y", context_unit="K")

    definition, dataset = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    with pytest.raises(ValueError, match="feature count"):
        replace(definition, features=())
    with pytest.raises(ValueError, match="feature count"):
        replace(definition, features=definition.features * 3)
    with pytest.raises(ValueError, match="unique"):
        replace(definition, features=(definition.features[0], definition.features[0]))
    with pytest.raises(ValueError, match="identity and intent"):
        replace(definition, key="")
    with pytest.raises(ValueError, match="seed and scoring"):
        replace(definition, seed=-1)
    with pytest.raises(ValueError, match="capability signals"):
        replace(definition, required_signal_keys=())
    with pytest.raises(ValueError, match="mixed-source"):
        replace(definition, supported_source_roles=(SourceRole.MIXED,))
    too_many_inputs = tuple(
        DetectorFeatureSpec(
            f"feature-{index}",
            "K",
            "PULL_END",
            transform="difference",
            context_key=f"context-{index}",
            context_unit="K",
        )
        for index in range(5)
    )
    with pytest.raises(ValueError, match="input feature count"):
        replace(definition, features=too_many_inputs)

    with pytest.raises(ValueError, match="cohort vehicle"):
        CohortIdentity("", "config", (), SourceRole.SYNTHETIC, "synthetic")
    with pytest.raises(ValueError, match="cohort vehicle"):
        CohortIdentity("vehicle", "config", (), SourceRole.SYNTHETIC, "")
    with pytest.raises(ValueError, match="mixed source role"):
        CohortIdentity("vehicle", "config", (), SourceRole.MIXED, "synthetic")
    cohort = CohortIdentity(
        "vehicle", "config", ("mod-b", "mod-a", "mod-a"), SourceRole.SYNTHETIC, "synthetic"
    )
    assert cohort.modification_ids == ("mod-a", "mod-b")

    row = dataset.rows[0]
    FeatureObservation("x", None, "K", "missing", "unavailable", None, None)
    with pytest.raises(ValueError, match="timezone offset"):
        FeatureObservation("x", 1.0, "K", "valid", None, datetime(2025, 1, 1), None)
    with pytest.raises(ValueError, match="inverted"):
        replace(row, pull_ended_at=row.pull_started_at - timedelta(seconds=1))
    with pytest.raises(ValueError, match="predates"):
        replace(row, observation_cutoff=row.pull_started_at - timedelta(seconds=1))
    with pytest.raises(ValueError, match="identity and source hashes"):
        replace(row, row_id="", source_hash="bad")
    with pytest.raises(ValueError, match="identity and source hashes"):
        replace(row, source_hash="bad")
    with pytest.raises(ValueError, match="duplicate FeatureSets"):
        replace(dataset, rows=(row, row))
    with pytest.raises(ValueError, match="future FeatureSet"):
        replace(
            dataset,
            rows=(replace(row, observation_cutoff=dataset.observation_cutoff + timedelta(1)),),
        )
    with pytest.raises(ValueError, match="incompatible cohort"):
        replace(dataset, rows=(replace(row, vehicle_id="another-vehicle"),))
    with pytest.raises(ValueError, match="source role differs"):
        replace(dataset, source_role=SourceRole.IMPORTED)
    with pytest.raises(ValueError, match="10000-row bound"):
        replace(dataset, rows=dataset.rows * 334)
    assert dataset.manifest(definition) != replace(dataset, rows=()).manifest(definition)
    assert replace(dataset, rows=()).temporal_span == timedelta(0)

    assert finding_idempotency_key(
        detector_version_id=uuid4(),
        observation=row,
        observation_cutoff=row.observation_cutoff,
        scoring_version="phase9c-score-v1",
        threshold=None,
    )
    with pytest.raises(ValueError, match="coverage"):
        AnomalyFindingResult(AnomalyStatus.INLIER, None, None, 1.1, (), (), (), ())
    with pytest.raises(ValueError, match="coverage"):
        AnomalyFindingResult(AnomalyStatus.INLIER, None, None, -0.1, (), (), (), ())
    with pytest.raises(ValueError, match="reason codes"):
        AnomalyFindingResult(
            AnomalyStatus.INLIER,
            None,
            None,
            0.0,
            (),
            (),
            (),
            (AnomalyReason.INVALID_CUTOFF,) * 9,
        )
    with pytest.raises(ValueError, match="score must be finite"):
        AnomalyFindingResult(AnomalyStatus.INLIER, float("nan"), None, 0.0, (), (), (), ())
    with pytest.raises(ValueError, match="threshold must be finite"):
        AnomalyFindingResult(AnomalyStatus.INLIER, None, float("inf"), 0.0, (), (), (), ())
    with pytest.raises(ValueError, match="duration"):
        AnomalyRunResult(
            "identity",
            "COMPLETED",
            uuid4(),
            uuid4(),
            row.observation_cutoff,
            SourceRole.SYNTHETIC,
            (),
            {},
            -1.0,
            None,
            stable_hash("input"),
        )
    with pytest.raises(ValueError, match="SHA-256"):
        AnomalyRunResult(
            "identity",
            "COMPLETED",
            uuid4(),
            uuid4(),
            row.observation_cutoff,
            SourceRole.SYNTHETIC,
            (),
            {},
            0.0,
            None,
            "bad",
        )
    with pytest.raises(ValueError, match="trace ID"):
        AnomalyRunResult(
            "identity",
            "COMPLETED",
            uuid4(),
            uuid4(),
            row.observation_cutoff,
            SourceRole.SYNTHETIC,
            (),
            {},
            0.0,
            None,
            stable_hash("input"),
            trace_id="short",
        )
    AnomalyRunResult(
        "identity",
        "COMPLETED",
        uuid4(),
        uuid4(),
        row.observation_cutoff,
        SourceRole.SYNTHETIC,
        (),
        {},
        0.0,
        stable_hash("artifact"),
        stable_hash("input"),
    )
    with pytest.raises(ValueError, match="must include a timezone offset"):
        finding_idempotency_key(
            detector_version_id=uuid4(),
            observation=row,
            observation_cutoff=datetime(2025, 1, 1),
            scoring_version="phase9c-score-v1",
            threshold=None,
        )


def test_fit_rejections_cover_source_support_quality_and_robust_fallback() -> None:
    definition, dataset = _reference(AnomalyFamily.PERFORMANCE, DetectorMethod.ROBUST_MAD)
    other_family = replace(definition, family=AnomalyFamily.THERMAL)
    with pytest.raises(DetectorFitError) as family_error:
        fit_detector(other_family, dataset)
    assert family_error.value.reason is AnomalyReason.FEATURE_SCHEMA_MISMATCH
    with pytest.raises(DetectorFitError) as source_error:
        fit_detector(replace(definition, supported_source_roles=()), dataset)
    assert source_error.value.reason is AnomalyReason.SOURCE_NOT_ALLOWLISTED
    with pytest.raises(DetectorFitError) as empty_error:
        fit_detector(definition, replace(dataset, rows=(), exclusions=()))
    assert empty_error.value.reason is AnomalyReason.REFERENCE_SUPPORT_TOO_LOW
    with pytest.raises(DetectorFitError) as source_empty_error:
        fit_detector(
            definition,
            replace(
                dataset,
                rows=(),
                exclusions=({"reason": AnomalyReason.REQUIRED_SIGNAL_UNAVAILABLE.value},),
            ),
        )
    assert source_empty_error.value.reason is AnomalyReason.REQUIRED_SIGNAL_UNAVAILABLE

    with pytest.raises(DetectorFitError) as row_support_error:
        fit_detector(definition, replace(dataset, rows=dataset.rows[:1]))
    assert row_support_error.value.reason is AnomalyReason.REFERENCE_SUPPORT_TOO_LOW
    single_session = tuple(replace(row, session_id="one-session") for row in dataset.rows)
    with pytest.raises(DetectorFitError) as session_support_error:
        fit_detector(definition, replace(dataset, rows=single_session))
    assert session_support_error.value.reason is AnomalyReason.REFERENCE_SESSION_SUPPORT_TOO_LOW
    short_span = tuple(
        replace(
            row,
            pull_started_at=dataset.rows[0].pull_started_at + timedelta(seconds=index),
            pull_ended_at=dataset.rows[0].pull_started_at + timedelta(seconds=index + 10),
            observation_cutoff=dataset.rows[0].pull_started_at + timedelta(seconds=index + 10),
        )
        for index, row in enumerate(dataset.rows)
    )
    with pytest.raises(DetectorFitError) as span_error:
        fit_detector(definition, replace(dataset, rows=short_span))
    assert span_error.value.reason is AnomalyReason.REFERENCE_SPAN_TOO_SHORT

    required_key = definition.required_feature_keys[0]
    missing_features = dict(dataset.rows[0].features)
    missing_features[required_key] = replace(
        missing_features[required_key], value=None, quality="missing", missing_reason="dropped"
    )
    partially_missing = replace(
        dataset,
        rows=(replace(dataset.rows[0], features=missing_features), *dataset.rows[1:]),
    )
    with pytest.raises(DetectorFitError) as coverage_error:
        fit_detector(definition, partially_missing)
    assert coverage_error.value.reason is AnomalyReason.FEATURE_COVERAGE_TOO_LOW

    shifted = [0.0, 0.0, 0.0, 1.0, 2.0]
    fallback = _robust_stats(shifted, "unit", 1.0)
    assert fallback.mad == 0 and fallback.scale > 0 and not fallback.constant
    assert _robust_stats([2.0, 2.0, 2.0], "unit", 1.0).constant


def test_fit_rejects_invalid_method_threshold_and_isolation_forest_support() -> None:
    robust_definition, robust_data = _reference(
        AnomalyFamily.PERFORMANCE, DetectorMethod.ROBUST_MAD
    )
    with pytest.raises(DetectorFitError) as method_error:
        fit_detector(replace(robust_definition, method="unknown"), robust_data)
    assert method_error.value.reason is AnomalyReason.FEATURE_SCHEMA_MISMATCH
    no_floor = replace(
        robust_definition,
        threshold_policy=robust_definition.threshold_policy | {"robust_minimum_threshold": None},
    )
    with pytest.raises(DetectorFitError) as threshold_error:
        fit_detector(no_floor, robust_data)
    assert threshold_error.value.reason is AnomalyReason.FEATURE_SCHEMA_MISMATCH

    forest_definition, forest_data = _reference(AnomalyFamily.FUEL, DetectorMethod.ISOLATION_FOREST)
    stricter_training_floor = replace(
        forest_definition,
        fit_parameters=forest_definition.fit_parameters | {"minimum_training_rows": 31},
    )
    with pytest.raises(DetectorFitError) as training_error:
        fit_detector(stricter_training_floor, forest_data)
    assert training_error.value.reason is AnomalyReason.REFERENCE_SUPPORT_TOO_LOW

    required_key = forest_definition.required_feature_keys[0]
    weakened_rows = []
    for index, row in enumerate(forest_data.rows):
        features = dict(row.features)
        if index < 7:
            features[required_key] = replace(
                features[required_key], value=None, quality="missing", missing_reason="missing"
            )
        weakened_rows.append(replace(row, features=features))
    with pytest.raises(DetectorFitError) as coverage_error:
        fit_detector(forest_definition, replace(forest_data, rows=tuple(weakened_rows)))
    assert coverage_error.value.reason is AnomalyReason.FEATURE_COVERAGE_TOO_LOW


def test_scoring_abstains_for_invalid_cutoffs_quality_and_missing_model() -> None:
    definition, dataset = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    fitted = fit_detector(definition, dataset)
    observation = dataset.rows[-1]

    result = score_observation(
        replace(definition, version="changed"),
        fitted,
        observation,
        observation_cutoff=dataset.observation_cutoff + timedelta(days=1),
    )
    assert result.reasons == (AnomalyReason.FEATURE_SCHEMA_MISMATCH,)
    result = score_observation(
        definition, fitted, observation, observation_cutoff=datetime(2026, 1, 1)
    )
    assert result.reasons == (AnomalyReason.INVALID_CUTOFF,)
    later_snapshot = replace(
        observation,
        observation_cutoff=observation.pull_ended_at + timedelta(seconds=2),
    )
    result = score_observation(
        definition,
        fitted,
        later_snapshot,
        observation_cutoff=observation.pull_ended_at + timedelta(seconds=1),
    )
    assert result.reasons == (AnomalyReason.FUTURE_FEATURE,)

    key = definition.required_feature_keys[0]
    missing = dict(observation.features)
    missing[key] = replace(missing[key], value=None, quality="missing", missing_reason="absent")
    result = score_observation(
        definition,
        fitted,
        replace(observation, features=missing),
        observation_cutoff=dataset.observation_cutoff + timedelta(days=1),
    )
    assert result.status is AnomalyStatus.INSUFFICIENT_SIGNAL
    assert result.reasons == (AnomalyReason.REQUIRED_FEATURE_MISSING,)

    optional_keys = [
        key for key in definition.feature_keys if key not in definition.required_feature_keys
    ]
    sparse = dict(observation.features)
    for optional_key in optional_keys[:3]:
        sparse.pop(optional_key)
    result = score_observation(
        definition,
        fitted,
        replace(observation, features=sparse),
        observation_cutoff=dataset.observation_cutoff + timedelta(days=1),
    )
    assert result.reasons == (AnomalyReason.FEATURE_COVERAGE_TOO_LOW,)

    forest_definition, forest_data = _reference(AnomalyFamily.FUEL, DetectorMethod.ISOLATION_FOREST)
    forest_fit = fit_detector(forest_definition, forest_data)
    result = score_observation(
        forest_definition,
        replace(forest_fit, estimator=None),
        forest_data.rows[-1],
        observation_cutoff=forest_data.observation_cutoff + timedelta(days=1),
    )
    assert result.reasons == (AnomalyReason.ARTIFACT_SCHEMA_MISMATCH,)

    class NonFiniteScorer:
        @staticmethod
        def score_samples(matrix: object) -> list[float]:
            del matrix
            return [float("nan")]

    result = score_observation(
        forest_definition,
        replace(forest_fit, estimator=NonFiniteScorer()),
        forest_data.rows[-1],
        observation_cutoff=forest_data.observation_cutoff + timedelta(days=1),
    )
    assert result.reasons == (AnomalyReason.INVALID_FEATURE_VALUE,)


def test_transform_and_robust_score_handle_direction_bounds_and_nonfinite_values() -> None:
    definition, dataset = _reference(AnomalyFamily.BOOST_AIR, DetectorMethod.ROBUST_MAD)
    feature = definition.features[0]
    high_definition = replace(
        definition,
        features=(replace(feature, direction=DeviationDirection.HIGH), *definition.features[1:]),
    )
    fitted = fit_detector(high_definition, dataset)
    target = dataset.rows[-1]
    key = feature.key
    features = dict(target.features)
    original = features[key]
    assert original.value is not None
    features[key] = replace(original, value=max(1.0, original.value - 20_000.0))
    low_row = replace(target, features=features)
    low_score, _ = _robust_score(
        high_definition, low_row, fitted.robust_stats, fitted.feature_order
    )
    assert low_score < fitted.threshold

    features[key] = replace(original, value=original.value + 20_000.0)
    high_row = replace(target, features=features)
    high_score, contributions = _robust_score(
        high_definition, high_row, fitted.robust_stats, fitted.feature_order
    )
    assert high_score == 8.0 and contributions[0]["normalized_deviation"] == 8.0

    stats_without_feature = dict(fitted.robust_stats)
    stats_without_feature.pop(key)
    score_without_stats, skipped_contributions = _robust_score(
        high_definition, target, stats_without_feature, fitted.feature_order
    )
    assert score_without_stats >= 0.0
    assert all(item["score_feature_key"] != key for item in skipped_contributions)
    constant_stats = dict(fitted.robust_stats)
    constant_stats[key] = replace(constant_stats[key], constant=True)
    _, constant_contributions = _robust_score(
        high_definition, target, constant_stats, fitted.feature_order
    )
    assert all(item["score_feature_key"] != key for item in constant_contributions)

    bad_values = dict(target.features)
    bad_values[key] = replace(original, value=float("inf"))
    transformed, absent = transform_features(high_definition, replace(target, features=bad_values))
    assert transformed[key] is None and key in absent

    difference, thermal_dataset = _reference(AnomalyFamily.THERMAL, DetectorMethod.ROBUST_MAD)
    thermal_row = thermal_dataset.rows[-1]
    # A row missing the contextual temperature keeps the derived feature unavailable.
    without_context = dict(thermal_row.features)
    without_context.pop("thermal.pre_pull_iat_k", None)
    values, missing = transform_features(difference, replace(thermal_row, features=without_context))
    score_key = difference.features[0].score_key
    assert values[score_key] is None
    assert "thermal.pre_pull_iat_k" in missing


def test_low_direction_and_forest_matrix_validation() -> None:
    definition, dataset = _reference(AnomalyFamily.BOOST_AIR, DetectorMethod.ROBUST_MAD)
    feature = definition.features[0]
    low_definition = replace(
        definition,
        features=(replace(feature, direction=DeviationDirection.LOW), *definition.features[1:]),
    )
    fitted = fit_detector(low_definition, dataset)
    target = dataset.rows[-1]
    features = dict(target.features)
    observed = features[feature.key]
    assert observed.value is not None
    features[feature.key] = replace(observed, value=observed.value + 20_000.0)
    score, contributions = _robust_score(
        low_definition,
        replace(target, features=features),
        fitted.robust_stats,
        fitted.feature_order,
    )
    directional = next(item for item in contributions if item["score_feature_key"] == feature.key)
    assert directional["normalized_deviation"] == 0.0
    assert score < fitted.threshold

    with pytest.raises(DetectorFitError, match="required feature"):
        _forest_matrix(
            [{"required": None}],
            ("required",),
            (),
            (),
            {"required": 1.0},
            {"required": 1.0},
            {"required": 1.0},
        )
    with pytest.raises(DetectorFitError, match="non-finite"):
        _forest_matrix(
            [{"required": float("inf")}],
            ("required",),
            (),
            (),
            {"required": 1.0},
            {"required": 1.0},
            {"required": 1.0},
        )
    assert _summary(np.array([]))["count"] == 0.0


def test_evaluation_metrics_cover_empty_support_and_rejected_candidates() -> None:
    with pytest.raises(ValueError, match="counts differ"):
        classification_metrics((1.0,), (), 0.0)
    with pytest.raises(ValueError, match="threshold must be finite"):
        classification_metrics((1.0,), (True,), float("nan"))
    empty = classification_metrics((None, float("nan")), (None, False), 0.0)
    assert empty["precision"] is None and empty["recall"] is None
    assert empty["false_positive_rate"] == 0.0
    assert empty["metric_state"] == "INSUFFICIENT_SUPPORT"

    invalid_parameters = (
        {
            "maximum_clean_false_positive_rate": 1.1,
            "minimum_coverage": 0.0,
            "minimum_injection_recall": 0.0,
        },
        {
            "maximum_clean_false_positive_rate": 0.0,
            "minimum_coverage": -0.1,
            "minimum_injection_recall": 0.0,
        },
        {
            "maximum_clean_false_positive_rate": 0.0,
            "minimum_coverage": 0.0,
            "minimum_injection_recall": 2.0,
        },
    )
    for parameters in invalid_parameters:
        with pytest.raises(ValueError):
            select_validation_threshold(scores=(), labels=(), initial_threshold=0.0, **parameters)
    selected = select_validation_threshold(
        scores=(0.2,),
        labels=(True,),
        initial_threshold=0.1,
        maximum_clean_false_positive_rate=0.0,
        minimum_coverage=1.0,
        minimum_injection_recall=1.0,
    )
    assert not selected.accepted
    with pytest.raises(ValueError, match="at least one"):
        select_detector_method((), maximum_clean_false_positive_rate=0.0, minimum_coverage=1.0)
    fallback = select_detector_method(
        (
            MethodCandidate(
                DetectorMethod.ISOLATION_FOREST, 0.1, {"recall": 0.5, "precision": 1.0}
            ),
            MethodCandidate(DetectorMethod.ROBUST_MAD, 0.2, {"recall": 0.5, "precision": 1.0}),
        ),
        maximum_clean_false_positive_rate=0.0,
        minimum_coverage=1.0,
    )
    assert fallback.method is DetectorMethod.ROBUST_MAD
