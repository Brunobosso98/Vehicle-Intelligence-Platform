from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from vehicle_platform.evaluation.anomaly import (
    AnomalyEvaluationError,
    _normalize_cases,
    _scenario_matrix,
)
from vehicle_platform.evaluation.applicability import assess_source_applicability
from vehicle_platform.evaluation.artifacts import (
    EvaluationArtifactError,
    read_calibrator,
    write_calibrator,
)
from vehicle_platform.evaluation.calibration import (
    CalibrationError,
    FittedCalibrator,
    apply_calibrator,
    calibration_row_checksum,
    fit_calibrator,
    select_calibration_method,
)
from vehicle_platform.evaluation.contracts import (
    AllowedClaimCategory,
    ApplicabilityStatus,
    CalibrationCandidate,
    CalibrationMethod,
    CalibrationValidityScope,
    ConfidenceInterval,
    DatasetManifest,
    DriftComparison,
    EvaluationEvidenceRef,
    EvaluationProtocol,
    EvaluationRun,
    FoldManifest,
    MetricDefinition,
    MetricResult,
    MetricStatus,
    ReliabilityBin,
    ScientificReadinessReport,
    SourceRole,
    StressScenario,
)
from vehicle_platform.evaluation.drift import (
    drift_experiment,
    ood_distances,
    population_stability_index,
    robust_location_shift,
)
from vehicle_platform.evaluation.metrics import (
    _metric_interval,
    _validate_binary_rows,
    anomaly_alarm_metrics,
    binary_metrics,
    reliability_bins,
)
from vehicle_platform.evaluation.protocol import default_protocol
from vehicle_platform.evaluation.splitting import (
    EvaluationSplitError,
    assert_disjoint_training_source,
    chronological_calibration_split,
)
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.ml.domain import SupervisedRow


def _row(
    index: int,
    *,
    session: str | None = None,
    at: datetime | None = None,
    input_pull: str | None = None,
) -> SupervisedRow:
    start = at or datetime(2026, 6, 1, tzinfo=UTC) + timedelta(days=index)
    session_id = session or f"session-{index}"
    pull = input_pull or f"pull-{index}"
    return SupervisedRow(
        row_id=f"row-{index}",
        group_id=session_id,
        vehicle_id=f"vehicle-{index}",
        configuration_id=f"configuration-{index}",
        session_id=session_id,
        input_pull_id=pull,
        target_pull_id=f"target-{index}",
        input_started_at=start,
        input_available_at=start + timedelta(minutes=1),
        target_started_at=start + timedelta(minutes=2),
        input_feature_set_id=f"input-feature-{index}",
        target_feature_set_id=f"target-feature-{index}",
        input_source_hash=stable_hash({"source": "input", "index": index}),
        target_source_hash=stable_hash({"source": "target", "index": index}),
        features={"thermal.iat_start": 300.0 + index},
        missing={},
        feature_quality={"thermal.iat_start": "valid"},
        target=bool(index % 2),
    )


def test_missing_fuel_only_requires_abstention_from_fuel_detector() -> None:
    missing_fuel_alarm = {
        "scenario": "missing_fuel",
        "score": 0.6,
        "status": "ANOMALOUS",
        "predicted_anomaly": True,
        "fold": "session-1",
    }
    boost = _normalize_cases([missing_fuel_alarm], family="boost_air", threshold=0.5)
    assert boost[0]["eligible"] is True
    assert (
        _scenario_matrix(boost, family="boost_air")["missing_fuel"]["oracle_role"]
        == "HARD_NEGATIVE_OR_CONTEXT_SHIFT"
    )

    fuel_abstention = _normalize_cases(
        [
            {
                **missing_fuel_alarm,
                "score": None,
                "status": "INSUFFICIENT_SIGNAL",
                "predicted_anomaly": None,
            }
        ],
        family="fuel",
        threshold=0.5,
    )
    assert fuel_abstention[0]["eligible"] is False
    assert (
        _scenario_matrix(fuel_abstention, family="fuel")["missing_fuel"]["oracle_role"]
        == "QUALITY_OR_CAPABILITY_ABSTENTION"
    )


def test_quality_duplicate_requires_safe_abstention_for_every_detector() -> None:
    with pytest.raises(AnomalyEvaluationError, match="was not abstained"):
        _normalize_cases(
            [
                {
                    "scenario": "quality_duplicate",
                    "score": 0.6,
                    "status": "ANOMALOUS",
                    "predicted_anomaly": True,
                    "fold": "session-1",
                }
            ],
            family="thermal",
            threshold=0.5,
        )


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def test_protocol_is_versioned_strict_and_frozen() -> None:
    protocol = default_protocol()

    assert protocol.protocol_version == "phase9g-protocol-v1"
    assert protocol.checksum == stable_hash(protocol.model_dump(mode="json"))
    assert set(protocol.tasks) == {
        "NEXT_PULL_THERMAL_DEGRADATION",
        "NEXT_PULL_PERFORMANCE_DEGRADATION",
        "NEXT_PULL_FUEL_DEVIATION",
    }
    with pytest.raises((FrozenInstanceError, ValidationError, TypeError)):
        protocol.seed = 4  # type: ignore[misc]
    with pytest.raises(ValidationError):
        EvaluationProtocol.model_validate({**protocol.model_dump(), "unknown": True})


def test_chronological_split_uses_whole_sessions_and_disjoint_training() -> None:
    future = tuple(_row(index) for index in range(20))
    partitions = chronological_calibration_split(future)
    training = (_row(100, at=datetime(2026, 1, 1, tzinfo=UTC)),)

    assert len(partitions.calibration) == 6
    assert len(partitions.validation) == 6
    assert len(partitions.test) == 8
    assert set(partitions.groups["calibration"]).isdisjoint(partitions.groups["test"])
    assert_disjoint_training_source(training, partitions)


def test_chronological_split_rejects_session_and_physical_pull_reuse() -> None:
    same_session = (replace(_row(0), group_id="not-the-session"),)
    with pytest.raises(EvaluationSplitError, match="grouping must use independent sessions"):
        chronological_calibration_split(same_session)

    rows = tuple(_row(index) for index in range(19)) + (_row(19, input_pull="pull-0"),)
    with pytest.raises(EvaluationSplitError, match="physical pull"):
        chronological_calibration_split(rows)


def test_binary_metrics_recompute_proper_scores_and_exclude_unlabeled() -> None:
    result = binary_metrics(
        (0.1, 0.4, 0.8, 0.9, None),
        (0, 1, 1, 0, None),
        threshold=0.5,
        source_role=SourceRole.SYNTHETIC,
        fold_id="test-v1",
        row_ids=("a", "b", "c", "d", "e"),
        clusters=("s1", "s2", "s3", "s4", "s5"),
        bootstrap_resamples=0,
    )

    assert result["brier_score"]["value"] == pytest.approx((0.01 + 0.36 + 0.04 + 0.81) / 4)
    assert result["log_loss"]["value"] == pytest.approx(
        (-math.log(0.9) - math.log(0.4) - math.log(0.8) - math.log(0.1)) / 4
    )
    assert result["support"] == {
        "eligible_requests": 5,
        "scored_labeled": 4,
        "positive": 2,
        "negative": 2,
        "abstained_or_unlabeled": 1,
        "coverage": 0.8,
        "independent_sessions": 4,
    }
    assert result["brier_score"]["denominator"] == 4
    assert result["brier_score"]["uncertainty"]["status"] == "NONINDEPENDENT_DESCRIPTIVE"
    assert sum(item["count"] for item in result["reliability_bins"]) == 4


def test_metric_inputs_reject_nonfinite_scores_and_nonbinary_labels() -> None:
    def evaluate(score: float, label: int) -> dict[str, object]:
        return binary_metrics(
            (score,),
            (label,),
            threshold=0.5,
            source_role=SourceRole.SYNTHETIC,
            fold_id="adversary",
            row_ids=("r1",),
            clusters=("s1",),
            bootstrap_resamples=0,
        )

    with pytest.raises(ValueError, match="finite"):
        evaluate(float("nan"), 0)
    with pytest.raises(ValueError, match="exactly zero or one"):
        evaluate(0.5, 2)


def test_session_cluster_intervals_require_independent_session_support() -> None:
    labels = tuple(label for _ in range(20) for label in (0, 1))
    scores = tuple(score for _ in range(20) for score in (0.1, 0.9))
    clusters = tuple(f"session-{index}" for index in range(20) for _ in range(2))
    rows = tuple(f"row-{index}" for index in range(len(labels)))
    report = binary_metrics(
        scores,
        labels,
        threshold=0.5,
        source_role=SourceRole.SYNTHETIC,
        fold_id="clustered-test",
        row_ids=rows,
        clusters=clusters,
        bootstrap_resamples=40,
        seed=12,
    )
    assert report["auroc"]["value"] == pytest.approx(1.0)
    assert report["auroc"]["uncertainty"]["cluster_count"] == 20
    assert report["auroc"]["uncertainty"]["status"] == "DEFINED"
    assert report["auroc"]["uncertainty"]["resamples"] == 40

    too_few = binary_metrics(
        scores[:20],
        labels[:20],
        threshold=0.5,
        source_role=SourceRole.SYNTHETIC,
        fold_id="small-cluster-test",
        row_ids=rows[:20],
        clusters=clusters[:20],
        bootstrap_resamples=40,
    )
    assert too_few["brier_score"]["uncertainty"]["lower"] is None
    assert too_few["brier_score"]["uncertainty"]["status"] == "NONINDEPENDENT_DESCRIPTIVE"


def test_drift_contract_does_not_call_unlabeled_concept_change_measured() -> None:
    with pytest.raises(ValidationError, match="label-dependent drift"):
        DriftComparison(
            feature_family="thermal",
            metric="CONCEPT_CHANGE",
            baseline_window="train",
            comparison_window="test",
            value=0.1,
            unit="brier_delta",
            status=MetricStatus.DEFINED,
            cutoff=datetime(2026, 9, 1, tzinfo=UTC),
            labeled_support=0,
            warning=True,
            interpretation="synthetic measurement",
        )


def test_calibration_fit_is_bounded_monotone_and_support_gated() -> None:
    scores = tuple(index / 100 for index in range(1, 100))
    labels = tuple(int(score >= 0.5) for score in scores)
    row_ids = tuple(f"row-{index}" for index in range(len(scores)))
    clusters = tuple(f"session-{index // 5}" for index in range(len(scores)))
    fitted = fit_calibrator(
        CalibrationMethod.SIGMOID,
        scores,
        labels,
        row_ids=row_ids,
        clusters=clusters,
        dataset_checksum=_sha("calibration-dataset"),
    )
    assert fitted is not None
    assert 0 <= fitted.parameters["slope"] <= 50
    mapped = apply_calibrator(fitted, scores)
    assert tuple(sorted(mapped)) == mapped

    insufficient = fit_calibrator(
        CalibrationMethod.ISOTONIC,
        scores,
        labels,
        row_ids=row_ids,
        clusters=clusters,
        dataset_checksum=_sha("calibration-dataset"),
    )
    assert insufficient is None
    assert (
        select_calibration_method(
            {
                CalibrationMethod.IDENTITY: {"eligible": True, "brier_score": {"value": 0.2}},
                CalibrationMethod.SIGMOID: {"eligible": True, "brier_score": {"value": 0.20005}},
            }
        )
        is CalibrationMethod.IDENTITY
    )


def test_calibration_rejects_duplicate_rows_and_single_class() -> None:
    with pytest.raises(CalibrationError, match="duplicate"):
        fit_calibrator(
            CalibrationMethod.SIGMOID,
            (0.2, 0.8),
            (0, 1),
            row_ids=("same", "same"),
            clusters=("a", "b"),
            dataset_checksum=_sha("data"),
            minimum_rows=2,
            minimum_each_class=1,
            minimum_clusters=2,
        )
    assert (
        fit_calibrator(
            CalibrationMethod.SIGMOID,
            tuple(index / 100 for index in range(1, 81)),
            (1,) * 80,
            row_ids=tuple(f"row-{index}" for index in range(80)),
            clusters=tuple(f"session-{index}" for index in range(80)),
            dataset_checksum=_sha("single-class"),
        )
        is None
    )


def test_calibrator_artifact_round_trip_rejects_tamper_and_symlinks(tmp_path: Path) -> None:
    scores = tuple(index / 100 for index in range(1, 100))
    labels = tuple(int(score >= 0.5) for score in scores)
    fitted = fit_calibrator(
        CalibrationMethod.SIGMOID,
        scores,
        labels,
        row_ids=tuple(f"row-{index}" for index in range(len(scores))),
        clusters=tuple(f"session-{index // 5}" for index in range(len(scores))),
        dataset_checksum=_sha("artifact-data"),
    )
    assert fitted is not None
    root = tmp_path / "research-artifacts"
    path, checksum, byte_count = write_calibrator(
        fitted,
        root=root,
        scope={
            "task": "NEXT_PULL_THERMAL_DEGRADATION",
            "source_role": "synthetic",
            "feature_set_version": "phase9a-v2",
            "label_definition_checksum": _sha("label"),
            "vehicle_context_fingerprint": _sha("vehicles"),
            "configuration_context_fingerprint": _sha("configurations"),
            "cutoff": "2026-08-01T00:00:00+00:00",
        },
        model_version_id="model-v1",
        model_artifact_checksum=_sha("model"),
        label_definition_checksum=_sha("label"),
        dependency_versions={
            name: importlib.metadata.version(name) for name in ("numpy", "scipy", "scikit-learn")
        },
    )
    assert byte_count == path.stat().st_size
    assert read_calibrator(path, root=root, expected_checksum=checksum)["not_for_serving"]

    content = bytearray(path.read_bytes())
    content[-2] ^= 1
    path.write_bytes(content)
    with pytest.raises(EvaluationArtifactError):
        read_calibrator(path, root=root, expected_checksum=checksum)

    target = root / "NEXT_PULL_THERMAL_DEGRADATION" / "other.json"
    target.write_text("{}", encoding="utf-8")
    link = root / "NEXT_PULL_THERMAL_DEGRADATION" / "linked.json"
    link.symlink_to(target)
    with pytest.raises(EvaluationArtifactError, match="symlink"):
        read_calibrator(link, root=root, expected_checksum=checksum)

    with pytest.raises(EvaluationArtifactError, match="escapes"):
        write_calibrator(
            fitted,
            root=root,
            scope={"task": "../escape", "source_role": "synthetic"},
            model_version_id="model-v1",
            model_artifact_checksum=_sha("model"),
            label_definition_checksum=_sha("label"),
            dependency_versions={
                name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "scikit-learn")
            },
        )


def test_real_unlabeled_sources_and_missing_signals_do_not_gain_calibration() -> None:
    result = assess_source_applicability(
        subject_kind="9B_TASK",
        subject_key="NEXT_PULL_THERMAL_DEGRADATION",
        subject_version="model-v1",
        source_role=SourceRole.REAL_VEHICLE,
        source_fingerprint=_sha("real-source"),
        evaluation_rows=50,
        labeled_outcomes=0,
        required_signals=("thermal.iat_start",),
        observed_signals=(),
        same_configuration_history=False,
        calibration_available=True,
    )
    assert result.status is ApplicabilityStatus.REAL_DATA_UNLABELED
    assert result.calibration_available is False
    assert result.diagnostic_claim_allowed is False

    incompatible = assess_source_applicability(
        subject_kind="9B_TASK",
        subject_key="NEXT_PULL_THERMAL_DEGRADATION",
        subject_version="model-v1",
        source_role=SourceRole.SYNTHETIC,
        source_fingerprint=_sha("missing-signal"),
        evaluation_rows=50,
        labeled_outcomes=50,
        required_signals=("thermal.iat_start",),
        observed_signals=(),
        same_configuration_history=False,
        calibration_available=False,
    )
    assert incompatible.status is ApplicabilityStatus.INCOMPATIBLE


def test_anomaly_clean_false_alarm_and_abstention_denominators_are_separate() -> None:
    result = anomaly_alarm_metrics(
        (1.1, 2.2, 0.4, None),
        (True, True, False, None),
        (True, True, True, True),
        clean=(True, False, True, True),
        clusters=("s1", "s1", "s2", "s3"),
    )

    assert result["clean_eligible"] == 3
    assert result["clean_scored"] == 2
    assert result["clean_abstained"] == 1
    assert result["clean_false_alarm_count"] == 1
    assert result["clean_fpr_per_scored"] == pytest.approx(0.5)
    assert result["alarm_rate_per_eligible"] == pytest.approx(2 / 4)
    assert result["independent_sessions_scored"] == 2
    assert result["sessions_with_alarm"] == 1


def test_unlabeled_drift_remains_unknown_and_feature_drift_is_not_performance_drift() -> None:
    result = drift_experiment(
        {"ambient": (10, 11, 12, 13, 14, 15)},
        {"ambient": (30, 31, 32, 33, 34, 35)},
    )
    assert result["feature_drift"]["status"] == "WARNING"
    assert result["concept_performance_drift"]["status"] == "UNKNOWN"
    assert result["label_prevalence_drift"]["status"] == "UNKNOWN"

    shifted_labels = drift_experiment(
        {"ambient": (10, 11, 12, 13, 14, 15)},
        {"ambient": (10, 11, 12, 13, 14, 15)},
        baseline_labels=(0, 0, 0, 0, 0, 0),
        comparison_labels=(1, 1, 1, 1, 1, 1),
        baseline_predictions=(0.2,) * 6,
        comparison_predictions=(0.2,) * 6,
    )
    assert shifted_labels["feature_drift"]["status"] == "NO_PREDECLARED_WARNING"
    assert (
        shifted_labels["concept_performance_drift"]["status"]
        == "MEASURED_SYNTHETIC_PERFORMANCE_CHANGE"
    )
    assert shifted_labels["concept_performance_drift"]["real_world_claim_allowed"] is False


def test_ood_flags_distribution_only_and_checks_frozen_feature_names() -> None:
    result = ood_distances({"x": tuple(float(i) for i in range(10))}, {"x": (100.0,)})
    assert result["features"]["x"]["status"] == "OOD_WARNING"
    assert "not a fault" in result["interpretation"]
    with pytest.raises(ValueError, match="names must match"):
        ood_distances({"x": (1.0,) * 10}, {"y": (1.0,) * 10})


@pytest.mark.parametrize(
    ("overrides", "expected"),
    (
        ({"out_of_domain": True}, ApplicabilityStatus.OOD_WARNING),
        (
            {"subject_kind": "9C_FAMILY", "same_configuration_history": False},
            ApplicabilityStatus.NO_REFERENCE,
        ),
        (
            {"evaluation_rows": 9, "labeled_outcomes": 9},
            ApplicabilityStatus.EVALUATION_INSUFFICIENT,
        ),
        ({"source_role": SourceRole.IMPORTED_FIXTURE}, ApplicabilityStatus.NOT_CALIBRATED),
        ({"calibration_available": True}, ApplicabilityStatus.SYNTHETIC_ONLY),
    ),
)
def test_applicability_covers_scope_and_support_states(
    overrides: dict[str, object], expected: ApplicabilityStatus
) -> None:
    parameters: dict[str, object] = {
        "subject_kind": "9B_TASK",
        "subject_key": "NEXT_PULL_THERMAL_DEGRADATION",
        "subject_version": "model-v1",
        "source_role": SourceRole.SYNTHETIC,
        "source_fingerprint": _sha("applicability-state"),
        "evaluation_rows": 50,
        "labeled_outcomes": 50,
        "required_signals": ("thermal.iat_start",),
        "observed_signals": ("thermal.iat_start",),
        "same_configuration_history": True,
        "calibration_available": False,
    }
    parameters.update(overrides)
    assert assess_source_applicability(**parameters).status is expected  # type: ignore[arg-type]


def test_applicability_reports_unobserved_and_empty_signal_contracts() -> None:
    unobserved = assess_source_applicability(
        subject_kind="9D_RECEIPT",
        subject_key="receipt",
        subject_version="v1",
        source_role=SourceRole.IMPORTED_FIXTURE,
        source_fingerprint=_sha("unobserved"),
        evaluation_rows=0,
        labeled_outcomes=0,
        required_signals=("fuel.pressure",),
        observed_signals=(),
        same_configuration_history=False,
        calibration_available=False,
    )
    assert "SOURCE_SIGNAL_AVAILABILITY_NOT_OBSERVED" in unobserved.reason_codes
    empty_contract = assess_source_applicability(
        subject_kind="9D_RECEIPT",
        subject_key="receipt",
        subject_version="v1",
        source_role=SourceRole.IMPORTED_FIXTURE,
        source_fingerprint=_sha("empty-contract"),
        evaluation_rows=0,
        labeled_outcomes=0,
        required_signals=(),
        observed_signals=(),
        same_configuration_history=False,
        calibration_available=False,
    )
    assert "NO_REQUIRED_SIGNAL_CONTRACT" in empty_contract.reason_codes


@pytest.mark.parametrize(
    ("calibration_fraction", "validation_fraction"),
    ((0.1, 0.2), (0.8, 0.2), (0.7, 0.25)),
)
def test_split_rejects_invalid_fraction_allocations(
    calibration_fraction: float, validation_fraction: float
) -> None:
    with pytest.raises(EvaluationSplitError):
        chronological_calibration_split(
            tuple(_row(index) for index in range(20)),
            calibration_fraction=calibration_fraction,
            validation_fraction=validation_fraction,
        )


def test_split_rejects_empty_duplicate_small_overlapping_and_leaking_sources() -> None:
    with pytest.raises(EvaluationSplitError, match="empty"):
        chronological_calibration_split(())
    with pytest.raises(EvaluationSplitError, match="duplicate"):
        chronological_calibration_split(tuple(_row(index) for index in range(19)) + (_row(18),))
    with pytest.raises(EvaluationSplitError, match="at least ten"):
        chronological_calibration_split(tuple(_row(index) for index in range(9)))
    pull_overlap = tuple(_row(index) for index in range(19)) + (_row(19, input_pull="target-0"),)
    with pytest.raises(EvaluationSplitError, match="physical pull"):
        chronological_calibration_split(pull_overlap)
    leaking_row = object.__new__(SupervisedRow)
    leaking_row.__dict__.update(_row(0).__dict__)
    object.__setattr__(leaking_row, "input_available_at", leaking_row.target_started_at)
    leaking = (leaking_row,) + tuple(_row(index) for index in range(1, 20))
    with pytest.raises(EvaluationSplitError, match="post-cutoff"):
        chronological_calibration_split(leaking)


@pytest.mark.parametrize("axis", ("vehicle_id", "configuration_id"))
def test_split_rejects_vehicle_and_configuration_reuse(axis: str) -> None:
    rows = [_row(index) for index in range(20)]
    rows[10] = replace(rows[10], **{axis: getattr(rows[0], axis)})
    with pytest.raises(EvaluationSplitError, match=axis):
        chronological_calibration_split(tuple(rows))


def test_training_split_rejects_missing_and_overlapping_sources() -> None:
    partitions = chronological_calibration_split(tuple(_row(index) for index in range(20)))
    with pytest.raises(EvaluationSplitError, match="training source is empty"):
        assert_disjoint_training_source((), partitions)
    conflicts = (_row(100, session="session-0", at=datetime(2026, 1, 1, tzinfo=UTC)),)
    with pytest.raises(EvaluationSplitError, match="sessions overlap"):
        assert_disjoint_training_source(conflicts, partitions)


def test_split_reports_empty_fold_summary_with_explicit_counts() -> None:
    from vehicle_platform.evaluation.splitting import fold_summary

    report = fold_summary(
        "TEST",
        (),
        row_fingerprint=_sha("rows"),
        session_fingerprint=_sha("sessions"),
        source_fingerprint=_sha("source"),
        eligible=False,
    )
    assert report["row_count"] == 0
    assert report["positive_count"] == report["negative_count"] == 0


def test_calibration_checksum_and_fit_reject_misaligned_invalid_inputs() -> None:
    with pytest.raises(CalibrationError, match="misaligned"):
        calibration_row_checksum(("r1",), (), ())
    with pytest.raises(CalibrationError, match="unique"):
        calibration_row_checksum(("r1", "r1"), (0.2, 0.8), (0, 1))
    with pytest.raises(CalibrationError, match="exactly zero or one"):
        calibration_row_checksum(("r1",), (0.2,), (2,))  # type: ignore[arg-type]
    with pytest.raises(CalibrationError, match="finite"):
        calibration_row_checksum(("r1",), (float("nan"),), (0,))
    with pytest.raises(CalibrationError, match="identical length"):
        fit_calibrator(
            CalibrationMethod.SIGMOID,
            (0.2,),
            (0, 1),
            row_ids=("r1",),
            clusters=("s1",),
            dataset_checksum=_sha("bad-length"),
        )


def test_calibration_eligible_isotonic_identity_and_method_selection() -> None:
    scores = tuple(index / 120 for index in range(1, 120))
    labels = tuple(int(index % 2) for index in range(1, 120))
    row_ids = tuple(f"iso-row-{index}" for index in range(len(scores)))
    clusters = tuple(f"iso-session-{index}" for index in range(len(scores)))
    isotonic = fit_calibrator(
        CalibrationMethod.ISOTONIC,
        scores,
        labels,
        row_ids=row_ids,
        clusters=clusters,
        dataset_checksum=_sha("isotonic"),
    )
    assert isotonic is not None
    assert tuple(sorted(apply_calibrator(isotonic, (0.99, 0.1, 0.5)))) == apply_calibrator(
        isotonic, (0.1, 0.5, 0.99)
    )
    identity = fit_calibrator(
        CalibrationMethod.IDENTITY,
        scores,
        labels,
        row_ids=row_ids,
        clusters=clusters,
        dataset_checksum="",
    )
    assert identity is not None and apply_calibrator(identity, (0.1, 0.9)) == (0.1, 0.9)
    assert select_calibration_method({}) is CalibrationMethod.IDENTITY
    assert (
        select_calibration_method(
            {CalibrationMethod.ISOTONIC: {"eligible": True, "brier_score": {"value": 0.1}}}
        )
        is CalibrationMethod.ISOTONIC
    )
    with pytest.raises(ValueError, match="tie tolerance"):
        select_calibration_method({}, tie_tolerance=0.02)


def test_calibration_rejects_bad_maps_and_inputs() -> None:
    identity = fit_calibrator(
        CalibrationMethod.IDENTITY,
        (0.2,),
        (0,),
        row_ids=("r1",),
        clusters=("s1",),
        dataset_checksum="",
    )
    assert identity is not None
    with pytest.raises(CalibrationError, match="finite"):
        apply_calibrator(identity, (float("inf"),))
    invalid_map = replace(
        identity,
        method=CalibrationMethod.ISOTONIC,
        parameters={"x": [0.8, 0.2], "y": [0.1, 0.9]},
    )
    with pytest.raises(CalibrationError, match="monotone"):
        apply_calibrator(invalid_map, (0.5,))


@pytest.mark.parametrize(
    "kwargs",
    (
        {
            "metric": "PSI",
            "labeled_support": 0,
            "value": float("nan"),
            "status": MetricStatus.DEFINED,
        },
        {"metric": "PSI", "labeled_support": 0, "value": None, "status": MetricStatus.DEFINED},
        {
            "metric": "CONCEPT_CHANGE",
            "labeled_support": 0,
            "value": 0.1,
            "status": MetricStatus.DEFINED,
        },
    ),
)
def test_drift_contract_rejects_invalid_or_unsupported_measurements(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        DriftComparison(
            feature_family="thermal",
            baseline_window="baseline",
            comparison_window="test",
            unit="ratio",
            cutoff=datetime(2026, 9, 1, tzinfo=UTC),
            warning=False,
            interpretation="bounded test",
            **kwargs,
        )


def test_drift_handles_insufficient_constant_and_invalid_data() -> None:
    assert population_stability_index((1.0,), (2.0,)) is None
    assert population_stability_index((1.0, 1.0), (1.0, 1.0)) == pytest.approx(0)
    assert robust_location_shift((1.0, 1.0, 1.0), (2.0,)) > 0
    with pytest.raises(ValueError, match="PSI bins"):
        population_stability_index((1.0, 2.0), (2.0, 3.0), bins=1)
    with pytest.raises(ValueError, match="finite"):
        population_stability_index((1.0, float("nan")), (2.0, 3.0))
    limited = ood_distances({"x": (1.0,) * 4}, {"x": ()})
    assert limited["features"]["x"]["status"] == "INSUFFICIENT_SUPPORT"
    with pytest.raises(ValueError, match="feature count"):
        ood_distances(
            {f"f{index}": (1.0,) for index in range(33)},
            {f"f{index}": (1.0,) for index in range(33)},
        )
    unknown_concept = drift_experiment(
        {"x": (1, 2, 3)},
        {"x": (1, 2, 3)},
        baseline_labels=(0, 1),
        comparison_labels=(0, 1),
    )
    assert unknown_concept["concept_performance_drift"]["status"] == "UNKNOWN"
    with pytest.raises(ValueError, match="binary labels"):
        drift_experiment({"x": (1, 2)}, {"x": (1, 2)}, baseline_labels=(2,), comparison_labels=(1,))
    with pytest.raises(ValueError, match="aligned finite probabilities"):
        drift_experiment(
            {"x": (1, 2)},
            {"x": (1, 2)},
            baseline_labels=(0, 1),
            comparison_labels=(0, 1),
            baseline_predictions=(0.4,),
            comparison_predictions=(0.4, 0.6),
        )


def test_metric_validation_and_reliability_bin_rejections() -> None:
    with pytest.raises(ValueError, match="aligned"):
        binary_metrics(
            (0.2,),
            (),
            threshold=0.5,
            source_role=SourceRole.SYNTHETIC,
            fold_id="invalid",
            row_ids=("r1",),
            clusters=("s1",),
        )
    with pytest.raises(ValueError, match="unique"):
        binary_metrics(
            (0.2, 0.8),
            (0, 1),
            threshold=0.5,
            source_role=SourceRole.SYNTHETIC,
            fold_id="invalid",
            row_ids=("same", "same"),
            clusters=("s1", "s2"),
        )
    with pytest.raises(ValueError, match="threshold"):
        binary_metrics(
            (0.2,),
            (0,),
            threshold=1.0,
            source_role=SourceRole.SYNTHETIC,
            fold_id="invalid",
            row_ids=("r1",),
            clusters=("s1",),
        )
    with pytest.raises(ValueError, match="exactly zero or one"):
        binary_metrics(
            (0.2,),
            (2,),
            threshold=0.5,
            source_role=SourceRole.SYNTHETIC,
            fold_id="invalid",
            row_ids=("r1",),
            clusters=("s1",),
        )
    with pytest.raises(ValueError, match="quantile reliability bins need"):
        reliability_bins((0.2,), (0,), bins=2, method="quantile")
    with pytest.raises(ValueError, match="between two and ten"):
        reliability_bins((0.2,), (0,), bins=1)
    with pytest.raises(ValueError, match="distinct score edges"):
        reliability_bins((0.2,) * 20, (0,) * 20, bins=2, method="quantile")
    with pytest.raises(ValueError, match="unknown reliability"):
        reliability_bins((0.2, 0.8), (0, 1), method="adaptive")
    one_class = binary_metrics(
        (0.0, 0.0),
        (0, 0),
        threshold=0.5,
        source_role=SourceRole.SYNTHETIC,
        fold_id="single-class",
        row_ids=("r1", "r2"),
        clusters=("s1", "s2"),
        bootstrap_resamples=0,
    )
    assert one_class["auroc"]["value"] is None
    assert one_class["decision"]["precision"] is None
    assert one_class["decision"]["f1"] is None


def test_anomaly_metric_zero_support_and_alignment_rejection() -> None:
    empty = anomaly_alarm_metrics((), (), (), clean=(), clusters=())
    assert empty["coverage"] == 0
    assert empty["clean_fpr_per_eligible"] is None
    with pytest.raises(ValueError, match="align"):
        anomaly_alarm_metrics((0.1,), (), (), clean=(), clusters=())


def _valid_scope(**changes: object) -> dict[str, object]:
    scope: dict[str, object] = {
        "source_role": SourceRole.SYNTHETIC,
        "task": "NEXT_PULL_THERMAL_DEGRADATION",
        "label_definition_checksum": _sha("label-definition"),
        "model_version_id": "model-v1",
        "model_artifact_checksum": _sha("model-artifact"),
        "feature_set_version": "phase9a-v2",
        "vehicle_context_fingerprint": _sha("vehicle-context"),
        "configuration_context_fingerprint": _sha("configuration-context"),
        "cutoff": datetime(2026, 8, 1, tzinfo=UTC),
    }
    scope.update(changes)
    return scope


def _valid_manifest(**changes: object) -> dict[str, object]:
    manifest: dict[str, object] = {
        "source_role": SourceRole.SYNTHETIC,
        "source_kind": "canonical_fixture",
        "row_count": 10,
        "labeled_count": 8,
        "unlabeled_count": 2,
        "vehicle_count": 2,
        "configuration_count": 2,
        "session_count": 2,
        "feature_set_version": "phase9a-v2",
        "source_fingerprint": _sha("source"),
        "row_fingerprint": _sha("rows"),
        "cutoff": datetime(2026, 8, 1, tzinfo=UTC),
        "known_at_policy": "available_at-v1",
        "generator_version": "fixture-v2",
    }
    manifest.update(changes)
    return manifest


def _valid_fold(**changes: object) -> dict[str, object]:
    fold: dict[str, object] = {
        "fold_id": "test-v1",
        "partition": "TEST",
        "row_count": 10,
        "positive_count": 5,
        "negative_count": 5,
        "session_count": 4,
        "vehicle_count": 3,
        "start_at": datetime(2026, 7, 1, tzinfo=UTC),
        "end_at": datetime(2026, 7, 2, tzinfo=UTC),
        "row_fingerprint": _sha("fold-rows"),
        "session_fingerprint": _sha("fold-sessions"),
        "source_fingerprint": _sha("fold-source"),
        "eligible": True,
    }
    fold.update(changes)
    return fold


def test_contracts_validate_metric_and_reliability_denominators() -> None:
    interval = ConfidenceInterval(
        lower=0.1,
        upper=0.4,
        method="cluster bootstrap",
        unit="session",
        cluster_count=20,
        resamples=200,
        status=MetricStatus.DEFINED,
    )
    definition = MetricDefinition(
        name="brier",
        version="v1",
        unit="ratio",
        formula="mean square error",
        denominator_definition="scored labels",
        independence_unit="session",
    )
    MetricResult(
        definition=definition,
        value=0.2,
        status=MetricStatus.DEFINED,
        denominator=10,
        positive_support=5,
        negative_support=5,
        excluded_or_abstained=2,
        source_role=SourceRole.SYNTHETIC,
        fold_id="test-v1",
        uncertainty=interval,
    )
    with pytest.raises(ValidationError, match="both be defined"):
        ConfidenceInterval(
            lower=None,
            upper=0.4,
            method="bootstrap",
            unit="session",
            cluster_count=20,
            resamples=20,
            status=MetricStatus.DEFINED,
        )
    with pytest.raises(ValidationError, match="lower bound exceeds"):
        ConfidenceInterval(
            lower=0.8,
            upper=0.4,
            method="bootstrap",
            unit="session",
            cluster_count=20,
            resamples=20,
            status=MetricStatus.DEFINED,
        )
    with pytest.raises(ValidationError, match="support exceeds"):
        MetricResult(
            definition=definition,
            value=0.2,
            status=MetricStatus.DEFINED,
            denominator=4,
            positive_support=3,
            negative_support=3,
            excluded_or_abstained=0,
            source_role=SourceRole.SYNTHETIC,
            fold_id="test-v1",
            uncertainty=interval,
        )
    with pytest.raises(ValidationError, match="require a finite value"):
        MetricResult(
            definition=definition,
            value=None,
            status=MetricStatus.DEFINED,
            denominator=0,
            positive_support=0,
            negative_support=0,
            excluded_or_abstained=0,
            source_role=SourceRole.SYNTHETIC,
            fold_id="test-v1",
            uncertainty=interval,
        )
    with pytest.raises(ValidationError, match="require a reason"):
        MetricResult(
            definition=definition,
            value=None,
            status=MetricStatus.UNDEFINED,
            denominator=0,
            positive_support=0,
            negative_support=0,
            excluded_or_abstained=0,
            source_role=SourceRole.SYNTHETIC,
            fold_id="test-v1",
            uncertainty=interval,
        )
    with pytest.raises(ValidationError, match="statistics"):
        ReliabilityBin(
            lower=0.1,
            upper=0.2,
            count=0,
            mean_score=0.1,
            observed_positive_rate=None,
            weighted_absolute_error=None,
            rate_interval=interval,
        )
    with pytest.raises(ValidationError, match="require measured"):
        ReliabilityBin(
            lower=0.1,
            upper=0.2,
            count=2,
            mean_score=0.1,
            observed_positive_rate=None,
            weighted_absolute_error=0.1,
            rate_interval=interval,
        )


def test_contracts_validate_calibration_candidate_scope_and_support() -> None:
    scope = CalibrationValidityScope(**_valid_scope())
    with pytest.raises(ValidationError, match="timezone-aware"):
        CalibrationValidityScope(**_valid_scope(cutoff=datetime(2026, 8, 1)))
    with pytest.raises(ValidationError, match="never serving"):
        CalibrationValidityScope(**_valid_scope(not_for_serving=False))
    candidate = {
        "method": CalibrationMethod.SIGMOID,
        "state": "SELECTED",
        "task": "NEXT_PULL_THERMAL_DEGRADATION",
        "model_version_id": "model-v1",
        "input_score_semantics": "bounded model score",
        "calibration_row_count": 40,
        "calibration_positive_count": 20,
        "calibration_negative_count": 20,
        "calibration_cluster_count": 20,
        "calibration_dataset_checksum": _sha("calibration"),
        "artifact_checksum": _sha("research-artifact"),
        "artifact_bytes": 1024,
        "validity_scope": scope,
    }
    CalibrationCandidate(**candidate)
    with pytest.raises(ValidationError, match="support exceeds"):
        CalibrationCandidate(**{**candidate, "calibration_row_count": 39})
    with pytest.raises(ValidationError, match="marked for serving"):
        CalibrationCandidate(**{**candidate, "not_for_serving": False})
    with pytest.raises(ValidationError, match="research artifact"):
        CalibrationCandidate(**{**candidate, "artifact_checksum": None, "artifact_bytes": 0})
    CalibrationCandidate(
        **{
            **candidate,
            "method": CalibrationMethod.IDENTITY,
            "state": "INSUFFICIENT_SUPPORT",
            "artifact_checksum": None,
            "artifact_bytes": 0,
        }
    )


def test_contracts_validate_dataset_fold_and_evidence_provenance() -> None:
    DatasetManifest(**_valid_manifest())
    with pytest.raises(ValidationError, match="at most 40 characters"):
        DatasetManifest(**_valid_manifest(source_kind="x" * 41))
    with pytest.raises(ValidationError, match="conserve"):
        DatasetManifest(**_valid_manifest(row_count=11))
    with pytest.raises(ValidationError, match="timezone-aware"):
        DatasetManifest(**_valid_manifest(cutoff=datetime(2026, 8, 1)))
    FoldManifest(**_valid_fold())
    with pytest.raises(ValidationError, match="exceed row"):
        FoldManifest(**_valid_fold(row_count=2))
    with pytest.raises(ValidationError, match="start must be timezone-aware"):
        FoldManifest(**_valid_fold(start_at=datetime(2026, 7, 1)))
    with pytest.raises(ValidationError, match="end must be timezone-aware"):
        FoldManifest(**_valid_fold(end_at=datetime(2026, 7, 2)))
    with pytest.raises(ValidationError, match="reversed"):
        FoldManifest(
            **_valid_fold(
                start_at=datetime(2026, 7, 3, tzinfo=UTC),
                end_at=datetime(2026, 7, 2, tzinfo=UTC),
            )
        )
    with pytest.raises(ValidationError, match="timezone-aware"):
        EvaluationEvidenceRef(
            kind="model",
            version="v1",
            entity_fingerprint=_sha("entity"),
            content_checksum=_sha("content"),
            source_role=SourceRole.SYNTHETIC,
            known_at=datetime(2026, 7, 1),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("tasks", ("a", "a", "c"), "unique 9B"),
        ("calibration_methods", (CalibrationMethod.IDENTITY,) * 3, "compare identity"),
        ("thresholds", (0.0, 0.5, 0.9), "strictly between"),
        ("validation_fraction", 0.6, "ten percent"),
        ("no_auto_promotion", False, "preserve the serving"),
        ("no_real_failure_probability", False, "preserve the serving"),
    ),
)
def test_protocol_rejects_unsafe_or_malformed_variants(
    field: str, value: object, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        EvaluationProtocol.model_validate({**default_protocol().model_dump(), field: value})


def test_contracts_validate_complete_run_safety_fences() -> None:
    manifest = DatasetManifest(**_valid_manifest())
    fold = FoldManifest(**_valid_fold())
    evidence = EvaluationEvidenceRef(
        kind="fixture",
        version="v1",
        entity_fingerprint=_sha("entity"),
        content_checksum=_sha("content"),
        source_role=SourceRole.SYNTHETIC,
        known_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    readiness = ScientificReadinessReport(
        engineering_pipeline="PASS",
        synthetic_calibration="SYNTHETIC_ONLY",
        real_world_predictive_validity="NOT_ESTABLISHED",
        real_world_calibration="NOT_ESTABLISHED",
        production_use="PROHIBITED",
        unsupported_claims=("diagnosis",),
    )
    run = {
        "protocol_checksum": _sha("protocol"),
        "git_sha": "a" * 40,
        "logical_key": _sha("logical"),
        "source_role": SourceRole.SYNTHETIC,
        "dataset_manifest": manifest,
        "folds": (fold,) * 4,
        "evidence": (evidence,),
        "metrics": (),
        "calibration_candidates": (),
        "applicability": (),
        "drift": (),
        "stress_scenarios": (),
        "engineering_status": "PASS",
        "scientific_readiness": readiness,
        "report_checksum": _sha("report"),
        "no_source_mutations": True,
        "serving_artifacts_unchanged": True,
    }
    EvaluationRun(**run)
    for fence in ("no_source_mutations", "serving_artifacts_unchanged", "not_for_serving"):
        with pytest.raises(ValidationError, match="source immutability"):
            EvaluationRun(**{**run, fence: False})
    scenario = StressScenario(
        scenario_id="ambient-shift-v1",
        family="thermal",
        oracle_kind="synthetic intervention",
        oracle_positive_families=("thermal",),
        expected_changes=("ambient temperature",),
        source_role=SourceRole.SYNTHETIC,
        generator_version="fixture-v2",
    )
    assert scenario.metadata_excluded_from_features is True
    assert AllowedClaimCategory.SCIENTIFIC_LIMITATION.value == "SCIENTIFIC_LIMITATION"


def test_metrics_cover_empty_bootstrap_validation_and_boolean_paths() -> None:
    with pytest.raises(ValueError, match="unique, aligned"):
        _validate_binary_rows((0.2, 0.8), (0, 1), ("same", "same"))
    with pytest.raises(ValueError, match="exactly zero or one"):
        _validate_binary_rows((0.2,), (0.5,), None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        _validate_binary_rows((float("nan"),), (0,), None)
    with pytest.raises(ValueError, match="lie in"):
        _validate_binary_rows((1.2,), (0,), None)
    interval, _ = _metric_interval(
        lambda scores, _labels: float(scores.mean()),
        np.asarray((0.1, 0.9)),
        np.asarray((0, 1)),
        None,
        seed=1,
        resamples=0,
    )
    assert interval.status is MetricStatus.INSUFFICIENT_SUPPORT
    with pytest.raises(ValueError, match="cluster identities"):
        _metric_interval(
            lambda scores, _labels: float(scores.mean()),
            np.asarray((0.1,)),
            np.asarray((0,)),
            ("",),
            seed=1,
            resamples=0,
        )
    insufficient, _ = _metric_interval(
        lambda _scores, _labels: float("nan"),
        np.asarray(tuple(index / 20 for index in range(20))),
        np.asarray(tuple(index % 2 for index in range(20))),
        tuple(f"session-{index}" for index in range(20)),
        seed=1,
        resamples=20,
    )
    assert insufficient.status is MetricStatus.INSUFFICIENT_SUPPORT
    quantile = reliability_bins(
        tuple(index / 19 for index in range(20)),
        tuple(index % 2 for index in range(20)),
        bins=2,
        method="quantile",
    )
    assert sum(item.count for item in quantile) == 20
    empty = binary_metrics(
        (None, None),
        (None, None),
        threshold=0.5,
        source_role=SourceRole.SYNTHETIC,
        fold_id="empty",
        row_ids=("r1", "r2"),
        clusters=("s1", "s2"),
    )
    assert empty["auroc"]["value"] is None
    boolean = binary_metrics(
        (0.2, 0.8),
        (False, True),
        threshold=0.5,
        source_role=SourceRole.SYNTHETIC,
        fold_id="boolean-labels",
        row_ids=("r1", "r2"),
        clusters=("s1", "s2"),
        bootstrap_resamples=0,
    )
    assert boolean["support"]["positive"] == 1


def test_split_checks_training_vehicle_configuration_pull_and_chronology() -> None:
    rows = tuple(_row(index) for index in range(20))
    partitions = chronological_calibration_split(rows)
    evaluation_row = partitions.calibration[0]
    for axis, message in (
        ("vehicle_id", "vehicles overlap"),
        ("configuration_id", "configurations overlap"),
        ("input_pull_id", "physical pull is reused"),
        ("target_pull_id", "physical pull is reused"),
    ):
        training = replace(
            _row(100, at=datetime(2026, 1, 1, tzinfo=UTC)),
            **{axis: getattr(evaluation_row, axis)},
        )
        with pytest.raises(EvaluationSplitError, match=message):
            assert_disjoint_training_source((training,), partitions)
    late_training = _row(100)
    with pytest.raises(EvaluationSplitError, match="strictly later"):
        assert_disjoint_training_source((late_training,), partitions)
    overlapping = [_row(index) for index in range(20)]
    overlapping[6] = _row(6, at=datetime(2026, 6, 6, tzinfo=UTC))
    with pytest.raises(EvaluationSplitError, match="time"):
        chronological_calibration_split(tuple(overlapping))


def _write_identity_artifact(root: Path) -> tuple[Path, str, dict[str, str]]:
    dependencies = {
        name: importlib.metadata.version(name) for name in ("numpy", "scipy", "scikit-learn")
    }
    calibrator = FittedCalibrator(
        method=CalibrationMethod.IDENTITY,
        parameters={},
        calibration_row_count=1,
        calibration_positive_count=0,
        calibration_negative_count=1,
        calibration_cluster_count=1,
        calibration_row_checksum=_sha("artifact-row"),
    )
    path, checksum, _ = write_calibrator(
        calibrator,
        root=root,
        scope={
            "task": "NEXT_PULL_THERMAL_DEGRADATION",
            "source_role": "synthetic",
            "feature_set_version": "phase9a-v2",
            "label_definition_checksum": _sha("artifact-label"),
            "vehicle_context_fingerprint": _sha("artifact-vehicles"),
            "configuration_context_fingerprint": _sha("artifact-configurations"),
            "cutoff": "2026-08-01T00:00:00+00:00",
        },
        model_version_id="model-v1",
        model_artifact_checksum=_sha("artifact-model"),
        label_definition_checksum=_sha("artifact-label"),
        dependency_versions=dependencies,
    )
    return path, checksum, dependencies


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("schema_version", "schema version"),
        ("serving_kind", "research-only"),
        ("dependencies", "dependency manifest"),
        ("unsupported_method", "method is unsupported"),
        ("bad_checksum_field", "source checksum"),
        ("bad_parameters", "parameter payload"),
        ("extra_scope_key", "validity scope"),
        ("wrong_source_role", "validity scope"),
        ("naive_cutoff", "timezone-aware"),
    ),
)
def test_artifact_reader_rejects_resigned_invalid_contracts(
    tmp_path: Path, mutation: str, message: str
) -> None:
    path, _, _ = _write_identity_artifact(tmp_path / "artifact-root")
    envelope = json.loads(path.read_text(encoding="utf-8"))
    body = {key: value for key, value in envelope.items() if key != "artifact_checksum"}
    if mutation == "schema_version":
        body["schema_version"] = "phase9g-research-calibrator-old"
    elif mutation == "serving_kind":
        body["not_for_serving"] = False
    elif mutation == "dependencies":
        body["dependency_versions"] = {"numpy": "0.0"}
    elif mutation == "unsupported_method":
        body["method"] = "unknown"
    elif mutation == "bad_checksum_field":
        body["calibration_row_checksum"] = "not-a-digest"
    elif mutation == "bad_parameters":
        body["parameters"] = None
    elif mutation == "extra_scope_key":
        body["scope"]["unreviewed"] = True
    elif mutation == "wrong_source_role":
        body["scope"]["source_role"] = "real_vehicle"
    else:
        body["scope"]["cutoff"] = "2026-08-01T00:00:00"
    content = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    checksum = hashlib.sha256(content).hexdigest()
    path.write_bytes(
        json.dumps(
            {**body, "artifact_checksum": checksum},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    )
    with pytest.raises(EvaluationArtifactError, match=message):
        read_calibrator(path, root=tmp_path / "artifact-root", expected_checksum=checksum)


def test_artifact_reader_bounds_paths_encoding_json_and_size(tmp_path: Path) -> None:
    path, checksum, _ = _write_identity_artifact(tmp_path / "artifact-root")
    root = tmp_path / "artifact-root"
    with pytest.raises(EvaluationArtifactError, match="read limit"):
        read_calibrator(path, root=root, expected_checksum=checksum, maximum_bytes=0)
    with pytest.raises(EvaluationArtifactError, match="malformed"):
        read_calibrator(path, root=root, expected_checksum="bad")
    with pytest.raises(EvaluationArtifactError, match="escapes"):
        read_calibrator(tmp_path / "elsewhere.json", root=root, expected_checksum=checksum)
    with pytest.raises(EvaluationArtifactError, match="missing or unsafe"):
        read_calibrator(Path("missing.json"), root=root, expected_checksum=checksum)
    with pytest.raises(EvaluationArtifactError, match="byte limit"):
        read_calibrator(path, root=root, expected_checksum=checksum, maximum_bytes=1)
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(EvaluationArtifactError, match="valid JSON"):
        read_calibrator(path, root=root, expected_checksum=checksum)
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(EvaluationArtifactError, match="root must be an object"):
        read_calibrator(path, root=root, expected_checksum=checksum)


def test_artifact_writer_refuses_unsafe_source_manifest_and_oversize(tmp_path: Path) -> None:
    dependencies = {
        name: importlib.metadata.version(name) for name in ("numpy", "scipy", "scikit-learn")
    }
    calibrator = FittedCalibrator(
        method=CalibrationMethod.IDENTITY,
        parameters={},
        calibration_row_count=1,
        calibration_positive_count=0,
        calibration_negative_count=1,
        calibration_cluster_count=1,
        calibration_row_checksum=_sha("writer-row"),
    )
    base = {
        "root": tmp_path / "writer-root",
        "scope": {
            "task": "NEXT_PULL_THERMAL_DEGRADATION",
            "source_role": "synthetic",
            "feature_set_version": "phase9a-v2",
            "label_definition_checksum": _sha("writer-label"),
            "vehicle_context_fingerprint": _sha("writer-vehicles"),
            "configuration_context_fingerprint": _sha("writer-configurations"),
            "cutoff": "2026-08-01T00:00:00+00:00",
        },
        "model_version_id": "model-v1",
        "model_artifact_checksum": _sha("writer-model"),
        "label_definition_checksum": _sha("writer-label"),
        "dependency_versions": dependencies,
    }
    with pytest.raises(EvaluationArtifactError, match="source model"):
        write_calibrator(calibrator, **{**base, "model_version_id": ""})
    with pytest.raises(EvaluationArtifactError, match="byte limit"):
        write_calibrator(calibrator, **{**base, "maximum_bytes": 100})
    with pytest.raises(EvaluationArtifactError, match="synthetic-only"):
        write_calibrator(
            calibrator,
            **{**base, "scope": {**base["scope"], "source_role": "imported"}},
        )
    with pytest.raises(EvaluationArtifactError, match="task scope"):
        write_calibrator(calibrator, **{**base, "scope": {"source_role": "synthetic"}})
    with pytest.raises(EvaluationArtifactError, match="manifest is incomplete"):
        write_calibrator(calibrator, **{**base, "dependency_versions": {"numpy": "x"}})
    with pytest.raises(EvaluationArtifactError, match="versions are incompatible"):
        write_calibrator(
            calibrator,
            **{
                **base,
                "dependency_versions": {**dependencies, "numpy": "0.0"},
            },
        )
    with pytest.raises(EvaluationArtifactError, match="byte limit"):
        write_calibrator(
            calibrator,
            **{
                **base,
                "scope": {**base["scope"], "large": "x" * 2_000},
                "maximum_bytes": 1024,
            },
        )
