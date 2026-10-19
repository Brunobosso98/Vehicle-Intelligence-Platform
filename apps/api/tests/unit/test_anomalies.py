from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
from vehicle_platform.anomalies.repository import _feature_exclusion
from vehicle_platform.anomalies.service import _cohort_mismatch, summarize_family_findings
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
