from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vehicle_platform.features.datasets import DatasetBuild, DatasetCandidate
from vehicle_platform.features.domain import (
    CutoffPolicy,
    DatasetDefinition,
    EntityScope,
    HorizonKind,
    PredictionHorizon,
    stable_hash,
)
from vehicle_platform.ml.artifacts import ArtifactStore, ArtifactValidationError
from vehicle_platform.ml.domain import (
    CandidateFamily,
    CandidateSpec,
    LabelExclusionReason,
    MLTask,
    SupervisedDataset,
    SupervisedRow,
)
from vehicle_platform.ml.labels import (
    SupervisedDatasetError,
    _input_vector,
    _make_target,
    build_supervised_dataset,
    get_model_spec,
    pair_compatibility_reason,
    validate_model_features,
)
from vehicle_platform.ml.splitting import (
    SplitValidationError,
    chronological_group_split,
    scenario_holdout_split,
    temporal_blocks,
    walk_forward_splits,
)
from vehicle_platform.ml.training import (
    InsufficientTrainingData,
    _fit_candidates,
    _probabilities,
    _select_candidate,
    _validate_data_floor,
    _validate_split_rows,
    _walk_forward_evaluation,
    classification_metrics,
    input_schema,
    matrix_for_feature_mapping,
    matrix_for_rows,
    train_and_evaluate,
)


def _builds(task: MLTask) -> tuple[DatasetBuild, DatasetBuild]:
    spec = get_model_spec(task)
    cutoff = datetime(2026, 8, 1, tzinfo=UTC)
    definitions = (
        DatasetDefinition(
            name=f"{task.value}-input",
            version="v1",
            row_scope=EntityScope.PULL,
            feature_set_version=spec.feature_set_version,
            selected_features=spec.feature_keys,
            observation_cutoff=cutoff,
            cutoff_policy=CutoffPolicy.ROW_END,
            source="synthetic",
        ),
        DatasetDefinition(
            name=f"{task.value}-outcome",
            version="v1",
            row_scope=EntityScope.PULL,
            feature_set_version=spec.feature_set_version,
            selected_features=spec.outcome_feature_keys,
            observation_cutoff=cutoff,
            cutoff_policy=CutoffPolicy.ROW_END,
            source="synthetic",
        ),
    )
    input_rows: list[dict[str, object]] = []
    outcome_rows: list[dict[str, object]] = []
    candidates: list[DatasetCandidate] = []
    for session_index in range(12):
        vehicle_id = f"vehicle-{session_index // 3}"
        configuration_id = f"configuration-{session_index // 6}"
        session_id = f"session-{session_index}"
        session_start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=session_index)
        for pull_index in range(5):
            pull_id = f"pull-{session_index}-{pull_index}"
            started = session_start + timedelta(seconds=pull_index * 20)
            ended = started + timedelta(seconds=5)
            feature_set_id = f"feature-set-{session_index}-{pull_index}"
            source_hash = stable_hash({"pull": pull_id})
            row_id = stable_hash({"pull": pull_id, "version": spec.feature_set_version})
            input_features = {
                key: float((session_index * 3 + pull_index * 5 + index) % 19)
                for index, key in enumerate(spec.feature_keys)
            }
            outcome_features: dict[str, float] = {}
            for key in spec.outcome_feature_keys:
                if key == "thermal.iat_start":
                    outcome_features[key] = 300.0 + pull_index * 4.0
                elif key == "performance.rpm_3500_4500_s_per_1000rpm":
                    outcome_features[key] = 1.0 + (0.2 if pull_index % 2 else 0.0)
                elif key == "fuel.rail_pressure_min":
                    outcome_features[key] = 12_000_000.0 if pull_index % 2 else 14_800_000.0
                elif key == "history.prior_fuel_mean_pa":
                    outcome_features[key] = 15_000_000.0
                elif key == "temporal_context.prior_pull_count":
                    outcome_features[key] = float(pull_index)
                else:
                    outcome_features[key] = float(pull_index + 1)
            base_row: dict[str, object] = {
                "row_id": row_id,
                "vehicle_id": vehicle_id,
                "configuration_id": configuration_id,
                "session_id": session_id,
                "pull_id": pull_id,
                "observation_cutoff": ended.isoformat(),
                "started_at": started.isoformat(),
                "ended_at": ended.isoformat(),
                "feature_set_id": feature_set_id,
                "feature_set_source_hash": source_hash,
                "provenance_hash": stable_hash({"provenance": pull_id}),
                "quality": {"pull_completeness": 1.0},
                "features": input_features,
                "missing": {},
                "feature_quality": {key: "valid" for key in spec.feature_keys},
                "active_modification_ids": [],
            }
            input_rows.append(base_row)
            outcome_rows.append(
                {
                    **base_row,
                    "features": outcome_features,
                    "feature_quality": {key: "valid" for key in spec.outcome_feature_keys},
                }
            )
            candidates.append(
                DatasetCandidate(
                    pull_id=pull_id,
                    vehicle_id=vehicle_id,
                    configuration_id=configuration_id,
                    session_id=session_id,
                    started_at=started.isoformat(),
                    ended_at=ended.isoformat(),
                    feature_set_id=feature_set_id,
                    feature_set_source_hash=source_hash,
                    row_id=row_id,
                )
            )
    input_build = DatasetBuild(
        definitions[0], tuple(input_rows), (), stable_hash(input_rows), {}, {}, tuple(candidates)
    )
    outcome_build = DatasetBuild(
        definitions[1],
        tuple(outcome_rows),
        (),
        stable_hash(outcome_rows),
        {},
        {},
        tuple(candidates),
    )
    return input_build, outcome_build


def _training_dataset() -> SupervisedDataset:
    spec = get_model_spec(MLTask.THERMAL_DEGRADATION)
    rows: list[SupervisedRow] = []
    for session_index in range(30):
        start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=session_index)
        for row_index in range(6):
            latent = (session_index * 3 + row_index * 7) % 10 < 5
            noise = (session_index + row_index) % 7 == 0
            target = latent != noise
            values = {
                "thermal.iat_delta_k": 4.0 if latent else 1.0,
                "thermal.iat_slope_k_per_s": 0.6 if latent else 0.1,
                "thermal.pre_pull_iat_k": 292.0 + session_index % 9,
                "thermal.iat_recovery_delta_k": float((session_index + row_index) % 4),
                "boost_air.pressure_stddev_pa": float((session_index * 13 + row_index * 3) % 70),
                "performance.rpm_2500_3500_s_per_1000rpm": 1.0 + (session_index % 4) * 0.1,
                "quality.sample_interval_stddev_s": float((session_index * 17 + row_index) % 11)
                / 10.0,
            }
            input_started = start + timedelta(seconds=row_index * 20)
            rows.append(
                SupervisedRow(
                    row_id=stable_hash({"s": session_index, "r": row_index}),
                    group_id=f"session-{session_index}",
                    vehicle_id=f"vehicle-{session_index % 5}",
                    configuration_id=f"config-{session_index % 3}",
                    session_id=f"session-{session_index}",
                    input_pull_id=f"input-{session_index}-{row_index}",
                    target_pull_id=f"target-{session_index}-{row_index}",
                    input_started_at=input_started,
                    input_available_at=input_started + timedelta(seconds=5),
                    target_started_at=input_started + timedelta(seconds=10),
                    input_feature_set_id=f"fs-in-{session_index}-{row_index}",
                    target_feature_set_id=f"fs-out-{session_index}-{row_index}",
                    input_source_hash=stable_hash(
                        {"source": "in", "s": session_index, "r": row_index}
                    ),
                    target_source_hash=stable_hash(
                        {"source": "out", "s": session_index, "r": row_index}
                    ),
                    features=values,
                    missing={},
                    feature_quality={key: "valid" for key in values},
                    target=target,
                    scenario_family="held" if session_index >= 24 else "known",
                )
            )
    checksum = stable_hash([row.row_id for row in rows])
    return SupervisedDataset(
        task=spec.task,
        model_spec=spec,
        input_dataset_checksum=stable_hash("input"),
        outcome_dataset_checksum=stable_hash("outcome"),
        checksum=checksum,
        source_fingerprint=stable_hash("sources"),
        rows=tuple(rows),
        exclusions=(),
        manifest={"source_role": "synthetic"},
    )


@pytest.mark.parametrize("task", list(MLTask))
def test_all_model_specs_and_label_generators_are_versioned(task: MLTask) -> None:
    input_build, outcome_build = _builds(task)
    spec = get_model_spec(task)
    validate_model_features(spec)
    dataset = build_supervised_dataset(
        input_build,
        outcome_build,
        spec,
        repository_sha="a" * 40,
    )
    assert dataset.rows
    assert len(dataset.checksum) == 64
    assert dataset.manifest["validation_type"] == "ENGINEERING_VALIDATION"
    assert set(spec.feature_keys).isdisjoint(spec.label_definition.source_feature_keys)
    assert all(set(row.features) == set(spec.feature_keys) for row in dataset.rows)
    assert all(row.input_available_at < row.target_started_at for row in dataset.rows)
    assert all(row.input_pull_id != row.target_pull_id for row in dataset.rows)


def test_label_builder_does_not_skip_an_ineligible_immediate_next_pull() -> None:
    input_build, outcome_build = _builds(MLTask.THERMAL_DEGRADATION)
    target_candidate = outcome_build.candidates[1]
    candidates = list(outcome_build.candidates)
    candidates[1] = replace(target_candidate, exclusion_reason="minimum_quality_not_met")
    outcome = replace(
        outcome_build,
        rows=tuple(row for row in outcome_build.rows if row["pull_id"] != target_candidate.pull_id),
        candidates=tuple(candidates),
    )
    dataset = build_supervised_dataset(
        input_build,
        outcome,
        get_model_spec(MLTask.THERMAL_DEGRADATION),
        repository_sha="b" * 40,
    )
    excluded = [
        item for item in dataset.exclusions if item["target_pull_id"] == target_candidate.pull_id
    ]
    assert excluded
    assert all(item["reason"] == "INSUFFICIENT_OUTCOME_QUALITY" for item in excluded)


def test_label_builder_rejects_future_cutoff_and_source_role_mismatch() -> None:
    input_build, outcome_build = _builds(MLTask.THERMAL_DEGRADATION)
    future_rows = tuple(
        {**row, "observation_cutoff": "2027-01-01T00:00:00+00:00"}
        if row["pull_id"] == "pull-0-0"
        else row
        for row in input_build.rows
    )
    future_input = replace(input_build, rows=future_rows)
    future_dataset = build_supervised_dataset(
        future_input,
        outcome_build,
        get_model_spec(MLTask.THERMAL_DEGRADATION),
        repository_sha="c" * 40,
    )
    assert any(item["reason"] == "FUTURE_DATA" for item in future_dataset.exclusions)
    imported_definition = replace(outcome_build.definition, source="imported")
    with pytest.raises(SupervisedDatasetError, match="source roles"):
        build_supervised_dataset(
            input_build,
            replace(outcome_build, definition=imported_definition),
            get_model_spec(MLTask.THERMAL_DEGRADATION),
            repository_sha="c" * 40,
        )


@pytest.mark.parametrize(
    ("changed_input", "changed_outcome", "message"),
    [
        (
            lambda build: replace(
                build, definition=replace(build.definition, feature_set_version="v99")
            ),
            None,
            "input dataset FeatureSetVersion",
        ),
        (
            lambda build: replace(
                build,
                definition=replace(
                    build.definition,
                    selected_features=tuple(reversed(build.definition.selected_features)),
                ),
            ),
            None,
            "feature order",
        ),
        (
            None,
            lambda build: replace(
                build, definition=replace(build.definition, feature_set_version="v99")
            ),
            "outcome dataset FeatureSetVersion",
        ),
        (
            None,
            lambda build: replace(
                build,
                definition=replace(
                    build.definition,
                    selected_features=(get_model_spec(MLTask.THERMAL_DEGRADATION).feature_keys[0],),
                ),
            ),
            "missing label source",
        ),
        (
            lambda build: replace(
                build,
                definition=replace(
                    build.definition,
                    observation_cutoff=build.definition.observation_cutoff - timedelta(days=1),
                ),
            ),
            None,
            "share an observation cutoff",
        ),
    ],
)
def test_label_builder_rejects_incompatible_dataset_definitions(
    changed_input: object, changed_outcome: object, message: str
) -> None:
    input_build, outcome_build = _builds(MLTask.THERMAL_DEGRADATION)
    if changed_input is not None:
        input_build = changed_input(input_build)  # type: ignore[operator]
    if changed_outcome is not None:
        outcome_build = changed_outcome(outcome_build)  # type: ignore[operator]
    with pytest.raises(SupervisedDatasetError, match=message):
        build_supervised_dataset(
            input_build,
            outcome_build,
            get_model_spec(MLTask.THERMAL_DEGRADATION),
            repository_sha="d" * 40,
        )


@pytest.mark.parametrize(
    ("missing_reason", "quality", "expected"),
    [
        ("unavailable_signal", "valid", LabelExclusionReason.MISSING_OUTCOME_SIGNAL),
        ("not_applicable", "valid", LabelExclusionReason.LABEL_NOT_APPLICABLE),
        ("unknown_reason", "valid", LabelExclusionReason.INSUFFICIENT_OUTCOME_QUALITY),
        (None, "limited", LabelExclusionReason.INSUFFICIENT_OUTCOME_QUALITY),
    ],
)
def test_target_builder_preserves_unavailable_signal_and_quality_reasons(
    missing_reason: str | None,
    quality: str,
    expected: LabelExclusionReason,
) -> None:
    _, outcome_build = _builds(MLTask.THERMAL_DEGRADATION)
    spec = get_model_spec(MLTask.THERMAL_DEGRADATION)
    prior, target = outcome_build.rows[:2]
    key = spec.outcome_feature_keys[0]
    changed_prior = {
        **prior,
        "features": {**prior["features"], key: None},
        "missing": {} if missing_reason is None else {key: missing_reason},
        "feature_quality": {**prior["feature_quality"], key: quality},
    }
    label, _, exclusion = _make_target(changed_prior, target, spec)
    assert label is None
    assert exclusion is expected


def test_matrix_mapping_checks_schema_missing_reason_dtype_and_finiteness() -> None:
    spec = get_model_spec(MLTask.THERMAL_DEGRADATION)
    features = {key: 1.0 for key in spec.feature_keys}
    with pytest.raises(ValueError, match="feature keys"):
        matrix_for_feature_mapping({"wrong": 1.0}, {}, spec)
    with pytest.raises(ValueError, match="known missing reason"):
        matrix_for_feature_mapping(
            {**features, spec.feature_keys[0]: None}, {spec.feature_keys[0]: "unknown"}, spec
        )
    with pytest.raises(ValueError, match="also has a missing reason"):
        matrix_for_feature_mapping(features, {spec.feature_keys[0]: "unavailable_signal"}, spec)
    with pytest.raises(ValueError, match="wrong dtype"):
        matrix_for_feature_mapping({**features, spec.feature_keys[0]: True}, {}, spec)
    with pytest.raises(ValueError, match="non-finite"):
        matrix_for_feature_mapping({**features, spec.feature_keys[0]: float("inf")}, {}, spec)


def test_classification_metrics_report_missing_classes_and_empty_support() -> None:
    all_negative = classification_metrics(np.array([0, 0]), np.array([0.1, 0.2]), 0.5)
    assert all_negative["recall"] is None
    assert all_negative["roc_auc"] is None
    all_missed = classification_metrics(np.array([1, 1]), np.array([0.1, 0.2]), 0.5)
    assert all_missed["precision"] is None
    assert all_missed["balanced_accuracy"] is None
    assert all_missed["brier_score"] is not None
    assert classification_metrics(np.array([]), np.array([]), 0.5)["brier_score"] is None


def test_empty_matrix_and_missing_class_training_partition_are_rejected_or_bounded() -> None:
    spec = get_model_spec(MLTask.THERMAL_DEGRADATION)
    matrix, labels, columns, row_ids = matrix_for_rows((), spec)
    assert matrix.shape == (0, len(columns))
    assert labels.size == 0
    assert row_ids == ()

    dataset = _training_dataset()
    split = chronological_group_split(dataset)
    one_class_validation = tuple(replace(row, target=False) for row in split.validation)
    with pytest.raises(InsufficientTrainingData, match="CLASS_MISSING_IN_TRAIN_OR_VALIDATION"):
        _fit_candidates(replace(split, validation=one_class_validation), spec, None)


@pytest.mark.parametrize(
    ("model", "message"),
    [
        (SimpleNamespace(), "must expose probabilities"),
        (
            SimpleNamespace(
                predict_proba=lambda matrix: np.ones((len(matrix), 1)), classes_=np.array([0])
            ),
            "invalid probability matrix",
        ),
        (
            SimpleNamespace(
                predict_proba=lambda matrix: np.full((len(matrix), 2), np.nan),
                classes_=np.array([0, 1]),
            ),
            "invalid probability matrix",
        ),
        (
            SimpleNamespace(
                predict_proba=lambda matrix: np.full((len(matrix), 2), 0.5),
                classes_=np.array([0, 2]),
            ),
            "binary label schema",
        ),
    ],
)
def test_probability_adapter_rejects_invalid_estimator_outputs(model: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _probabilities(model, np.zeros((2, 1)))


def test_split_validation_rejects_test_before_validation() -> None:
    dataset = _training_dataset()
    split = chronological_group_split(dataset)
    with pytest.raises(ValueError, match="test is not strictly later"):
        _validate_split_rows(
            dataset,
            replace(split, validation=split.test, test=split.validation),
        )


def test_feature_validator_blocks_target_future_and_identity_inputs() -> None:
    spec = get_model_spec(MLTask.THERMAL_DEGRADATION)
    for key, message in (
        (spec.label_definition.source_feature_keys[0], "target outcome"),
        ("future.outcome_mean", "future-only"),
        ("vehicle.id", "identity feature"),
        ("unregistered.feature", "unregistered model feature"),
    ):
        bad_spec = SimpleNamespace(feature_keys=(key,), label_definition=spec.label_definition)
        with pytest.raises(SupervisedDatasetError, match=message):
            validate_model_features(bad_spec)


def test_pair_compatibility_rejects_cross_vehicle_config_session_and_future() -> None:
    first = DatasetCandidate(
        pull_id="first",
        vehicle_id="v1",
        configuration_id="c1",
        session_id="s1",
        started_at="2026-01-01T00:00:00+00:00",
        ended_at="2026-01-01T00:00:05+00:00",
    )
    target = DatasetCandidate(
        pull_id="second",
        vehicle_id="v1",
        configuration_id="c1",
        session_id="s1",
        started_at="2026-01-01T00:00:10+00:00",
        ended_at="2026-01-01T00:00:15+00:00",
    )
    assert pair_compatibility_reason(first, target) is None
    assert pair_compatibility_reason(first, replace(target, vehicle_id="v2")) is not None
    assert pair_compatibility_reason(first, replace(target, configuration_id="c2")) is not None
    assert pair_compatibility_reason(first, replace(target, session_id="s2")) is not None
    assert pair_compatibility_reason(replace(first, ended_at=target.started_at), target) is not None


def test_temporal_split_walk_forward_and_scenario_holdout_are_grouped() -> None:
    dataset = _training_dataset()
    split = chronological_group_split(dataset)
    assert not ({row.group_id for row in split.train} & {row.group_id for row in split.validation})
    assert not ({row.group_id for row in split.validation} & {row.group_id for row in split.test})
    assert max(row.target_started_at for row in split.train) < min(
        row.input_started_at for row in split.validation
    )
    assert walk_forward_splits(dataset)
    scenario = scenario_holdout_split(dataset, held_out_family="held")
    assert {row.scenario_family for row in scenario.test} == {"held"}
    assert {row.group_id for row in scenario.train}.isdisjoint(
        {row.group_id for row in scenario.test}
    )


def test_training_uses_bounded_baselines_and_repeats_deterministically() -> None:
    dataset = _training_dataset()
    split = chronological_group_split(dataset)
    first = train_and_evaluate(dataset, split)
    second = train_and_evaluate(dataset, split)
    assert {item.family for item in first.candidates} == set(CandidateFamily)
    assert first.test_evaluated_after_selection
    selected = next(item for item in first.candidates if item.family is first.selected_family)
    later_groups_without_positive_support = replace(
        dataset,
        rows=tuple(
            replace(row, target=False)
            if int(row.group_id.rsplit("-", maxsplit=1)[1]) >= 26
            else row
            for row in dataset.rows
        ),
    )
    walk_forward = _walk_forward_evaluation(
        later_groups_without_positive_support, dataset.model_spec, selected
    )
    assert walk_forward["fold_count"] == 3
    assert {fold["status"] for fold in walk_forward["folds"]} == {"CLASS_MISSING_IN_FOLD"}
    assert first.manifest()["test_influenced_selection"] is False
    assert first.selected_family == second.selected_family
    assert first.selected_parameters == second.selected_parameters
    assert first.test_metrics == second.test_metrics
    assert first.feature_importance == second.feature_importance
    test_matrix, _, _, _ = matrix_for_rows(split.test, dataset.model_spec)
    assert np.array_equal(
        _probabilities(first.selected_model, test_matrix),
        _probabilities(second.selected_model, test_matrix),
    )
    assert first.walk_forward["fold_count"] >= 1


def test_metrics_report_undefined_class_support() -> None:
    result = classification_metrics(np.array([0, 0]), np.array([0.2, 0.4]), 0.5)
    assert result["balanced_accuracy"] is None
    assert result["average_precision"] is None
    assert "roc_auc:class_missing" in result["undefined_metrics"]


def test_missing_indicators_preserve_reason_and_reject_unexplained_nulls() -> None:
    spec = get_model_spec(MLTask.THERMAL_DEGRADATION)
    values = {key: 1.0 for key in spec.feature_keys}
    key = spec.feature_keys[0]
    values[key] = None
    matrix = matrix_for_feature_mapping(values, {key: "unavailable_signal"}, spec)
    schema = input_schema(spec)
    reason_column = f"{key}__missing__unavailable_signal"
    column_index = [item["key"] for item in schema["matrix_columns"]].index(reason_column)
    assert matrix[0, column_index] == 1.0
    with pytest.raises(ValueError, match="known missing reason"):
        matrix_for_feature_mapping(values, {}, spec)


def test_artifact_staging_checks_checksum_schema_and_smoke_prediction(tmp_path: Path) -> None:
    dataset = _training_dataset()
    split = chronological_group_split(dataset)
    result = train_and_evaluate(dataset, split)
    spec = dataset.model_spec
    matrix, _, _, _ = matrix_for_rows((split.test[0],), spec)
    store = ArtifactStore(tmp_path)
    family = result.selected_family.value
    receipt = store.write(
        spec.task,
        "v00000001",
        estimator=result.selected_model,
        input_schema=result.input_schema,
        threshold=result.selected_threshold,
        model_spec_checksum=spec.checksum,
        family=family,
    )
    score = store.verify_staged(
        receipt,
        task=spec.task,
        family=family,
        input_schema=result.input_schema,
        threshold=result.selected_threshold,
        model_spec_checksum=spec.checksum,
        smoke_matrix=matrix,
    )
    assert 0.0 <= score <= 1.0
    with pytest.raises(ArtifactValidationError, match="outside the controlled namespace"):
        store._checked_path(Path("../escape.joblib"))
    (tmp_path / receipt.relative_path).write_bytes(b"changed")
    with pytest.raises(ArtifactValidationError, match="checksum"):
        store.verify_staged(
            receipt,
            task=spec.task,
            family=family,
            input_schema=result.input_schema,
            threshold=result.selected_threshold,
            model_spec_checksum=spec.checksum,
            smoke_matrix=matrix,
        )


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"version": "invalid version"}, "invalid model specification version"),
        (
            {
                "label_definition": replace(
                    get_model_spec(MLTask.THERMAL_DEGRADATION).label_definition, key="OTHER"
                )
            },
            "model task and label definition differ",
        ),
        (
            {
                "label_definition": replace(
                    get_model_spec(MLTask.THERMAL_DEGRADATION).label_definition,
                    horizon=PredictionHorizon(HorizonKind.NEXT_SESSION),
                )
            },
            "next-pull label",
        ),
        ({"feature_set_version": ""}, "datasets and feature set version are required"),
        ({"feature_keys": ()}, "feature count is outside its bounded range"),
        (
            {"feature_keys": ("thermal.iat_delta_k", "thermal.iat_delta_k")},
            "feature keys must be unique",
        ),
        ({"outcome_feature_keys": ("not_a_label_source",)}, "declared by the label"),
        ({"feature_keys": ("thermal.iat_start",)}, "overlap target outcome"),
        ({"candidates": ()}, "requires dummy, linear and nonlinear"),
        ({"minimum_rows": 0}, "minimums must be positive"),
        ({"seed": -1}, "invalid random seed"),
        ({"maximum_feature_count": 0}, "feature count is outside"),
        ({"threshold_grid": ()}, "threshold candidates"),
        ({"threshold_grid": (1.0,)}, "threshold candidates"),
        ({"selection_margin": 1.1}, "acceptance thresholds"),
    ],
)
def test_model_spec_rejects_invalid_versioning_and_bounds(
    updates: dict[str, object], message: str
) -> None:
    spec = get_model_spec(MLTask.THERMAL_DEGRADATION)
    with pytest.raises(ValueError, match=message):
        replace(spec, **updates)


def test_candidate_and_supervised_row_constructors_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="complexity rank"):
        CandidateSpec(CandidateFamily.LOGISTIC_REGRESSION, {}, -1)
    row = _training_dataset().rows[0]
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(row, input_started_at=row.input_started_at.replace(tzinfo=None))
    with pytest.raises(ValueError, match="strictly before"):
        replace(row, input_available_at=row.target_started_at)
    with pytest.raises(ValueError, match="requires model input features"):
        replace(row, features={})
    with pytest.raises(ValueError, match="identity cannot"):
        replace(row, features={**row.features, "vehicle_id": 1.0})


def test_pair_compatibility_returns_specific_configuration_and_session_reasons() -> None:
    current = DatasetCandidate(
        "input", "v1", "c1", "s1", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:05+00:00"
    )
    target = DatasetCandidate(
        "target", "v1", "c1", "s1", "2026-01-01T00:00:10+00:00", "2026-01-01T00:00:15+00:00"
    )
    assert (
        pair_compatibility_reason(replace(current, vehicle_id="v2"), target)
        is LabelExclusionReason.CONFIGURATION_BOUNDARY
    )
    assert (
        pair_compatibility_reason(current, replace(target, session_id="s2"))
        is LabelExclusionReason.INCOMPATIBLE_SESSION
    )
    assert (
        pair_compatibility_reason(current, replace(target, configuration_id=None))
        is LabelExclusionReason.CONFIGURATION_BOUNDARY
    )
    assert (
        pair_compatibility_reason(replace(current, active_modification_ids=("mod-a",)), target)
        is LabelExclusionReason.CONFIGURATION_BOUNDARY
    )


def test_label_builder_excludes_unavailable_immediate_outcome() -> None:
    input_build, outcome_build = _builds(MLTask.THERMAL_DEGRADATION)
    target_pull = outcome_build.candidates[1].pull_id
    rows = tuple(
        {
            **row,
            "features": {**row["features"], "thermal.iat_start": None},
            "missing": {"thermal.iat_start": "unavailable_signal"},
            "feature_quality": {"thermal.iat_start": "unavailable"},
        }
        if row["pull_id"] == target_pull
        else row
        for row in outcome_build.rows
    )
    dataset = build_supervised_dataset(
        input_build,
        replace(outcome_build, rows=rows),
        get_model_spec(MLTask.THERMAL_DEGRADATION),
        repository_sha="d" * 40,
    )
    assert any(
        item["target_pull_id"] == target_pull
        and item["reason"] == LabelExclusionReason.MISSING_OUTCOME_SIGNAL.value
        for item in dataset.exclusions
    )


@pytest.mark.parametrize(
    ("task", "mutate", "reason"),
    [
        (
            MLTask.THERMAL_DEGRADATION,
            lambda key, prior, target: (
                {
                    **prior,
                    "features": {**prior["features"], key: None},
                    "missing": {key: "not_applicable"},
                },
                target,
            ),
            LabelExclusionReason.LABEL_NOT_APPLICABLE,
        ),
        (
            MLTask.THERMAL_DEGRADATION,
            lambda key, prior, target: (
                {**prior, "feature_quality": {key: "limited"}},
                target,
            ),
            LabelExclusionReason.INSUFFICIENT_OUTCOME_QUALITY,
        ),
        (
            MLTask.PERFORMANCE_DEGRADATION,
            lambda key, prior, target: (
                {**prior, "features": {**prior["features"], key: 0.0}},
                target,
            ),
            LabelExclusionReason.LABEL_NOT_APPLICABLE,
        ),
        (
            MLTask.FUEL_DEVIATION,
            lambda key, prior, target: (
                prior,
                {
                    **target,
                    "features": {
                        **target["features"],
                        "history.prior_fuel_mean_pa": 0.0,
                    },
                },
            ),
            LabelExclusionReason.LABEL_NOT_APPLICABLE,
        ),
        (
            MLTask.FUEL_DEVIATION,
            lambda key, prior, target: (
                prior,
                {
                    **target,
                    "features": {
                        **target["features"],
                        "temporal_context.prior_pull_count": 0.0,
                    },
                },
            ),
            LabelExclusionReason.NO_COMPATIBLE_PRIOR,
        ),
    ],
)
def test_target_builder_reports_quality_and_relative_baseline_exclusions(
    task: MLTask, mutate: object, reason: LabelExclusionReason
) -> None:
    _, outcome_build = _builds(task)
    spec = get_model_spec(task)
    prior, target = outcome_build.rows[:2]
    source_key = spec.outcome_feature_keys[0]
    changed_prior, changed_target = mutate(source_key, prior, target)  # type: ignore[operator]
    label, _, exclusion = _make_target(changed_prior, changed_target, spec)
    assert label is None
    assert exclusion is reason


def test_input_vector_rejects_boolean_and_nonfinite_values() -> None:
    _, outcome_build = _builds(MLTask.THERMAL_DEGRADATION)
    spec = get_model_spec(MLTask.THERMAL_DEGRADATION)
    row = outcome_build.rows[0]
    feature_key = spec.feature_keys[0]
    with pytest.raises(SupervisedDatasetError, match="nonnumeric"):
        _input_vector({**row, "features": {**row["features"], feature_key: True}}, spec)
    with pytest.raises(SupervisedDatasetError, match="not finite"):
        _input_vector({**row, "features": {**row["features"], feature_key: float("nan")}}, spec)


def test_temporal_split_rejects_insufficient_groups_and_invalid_fold_count() -> None:
    dataset = _training_dataset()
    one_block = replace(dataset, rows=dataset.rows[:6])
    assert temporal_blocks(()) == ()
    with pytest.raises(SplitValidationError, match="three nonoverlapping"):
        chronological_group_split(one_block)
    with pytest.raises(ValueError, match="between one and ten"):
        walk_forward_splits(dataset, maximum_folds=0)
    no_known = replace(
        dataset,
        rows=tuple(replace(row, scenario_family="held") for row in dataset.rows),
    )
    with pytest.raises(SplitValidationError, match="known and reserved"):
        scenario_holdout_split(no_known, held_out_family="held")


def test_three_group_split_uses_minimum_partition_fallback() -> None:
    dataset = _training_dataset()
    split = chronological_group_split(replace(dataset, rows=dataset.rows[:18]))
    assert len(split.train) and len(split.validation) and len(split.test)


def test_scenario_holdout_must_follow_known_training_and_validation_windows() -> None:
    dataset = _training_dataset()
    held_before_known = replace(
        dataset,
        rows=tuple(
            replace(row, scenario_family="held" if row.group_id < "session-06" else "known")
            for row in dataset.rows
        ),
    )
    with pytest.raises(SplitValidationError, match="not strictly later than training"):
        scenario_holdout_split(held_before_known, held_out_family="held")

    held_between_known_blocks = replace(
        dataset,
        rows=tuple(
            replace(
                row,
                scenario_family=(
                    "held"
                    if row.group_id in {f"session-{index}" for index in range(12, 24)}
                    else "known"
                ),
            )
            for row in dataset.rows
        ),
    )
    with pytest.raises(SplitValidationError, match="not strictly later than validation"):
        scenario_holdout_split(held_between_known_blocks, held_out_family="held")


def test_training_validators_reject_data_and_split_boundaries() -> None:
    dataset = _training_dataset()
    split = chronological_group_split(dataset)
    with pytest.raises(InsufficientTrainingData, match="minimum_total_rows"):
        _validate_data_floor(replace(dataset, rows=dataset.rows[:5]), split)
    no_positive = replace(dataset, rows=tuple(replace(row, target=False) for row in dataset.rows))
    with pytest.raises(InsufficientTrainingData, match="minimum_positive_support"):
        _validate_data_floor(no_positive, split)
    no_negative = replace(dataset, rows=tuple(replace(row, target=True) for row in dataset.rows))
    with pytest.raises(InsufficientTrainingData, match="minimum_negative_support"):
        _validate_data_floor(no_negative, split)
    with pytest.raises(InsufficientTrainingData, match="empty_temporal_partition"):
        _validate_data_floor(dataset, replace(split, test=()))
    with pytest.raises(ValueError, match="duplicated or absent"):
        _validate_split_rows(dataset, replace(split, test=split.test + split.test[:1]))
    overlapping_groups = tuple(
        replace(row, group_id=split.train[0].group_id) for row in split.validation
    )
    with pytest.raises(ValueError, match="cross split boundaries"):
        _validate_split_rows(dataset, replace(split, validation=overlapping_groups))
    with pytest.raises(ValueError, match="validation is not strictly later"):
        _validate_split_rows(
            dataset,
            replace(split, train=split.validation, validation=split.train),
        )


def test_candidate_selection_prefers_simpler_near_tie_and_rejects_no_candidate() -> None:
    dataset = _training_dataset()
    result = train_and_evaluate(dataset, chronological_group_split(dataset))
    with pytest.raises(InsufficientTrainingData, match="DUMMY_BASELINE_FAILED"):
        _select_candidate((), dataset.model_spec)
    dummy = next(item for item in result.candidates if item.family is CandidateFamily.DUMMY)
    logistic = next(
        item for item in result.candidates if item.family is CandidateFamily.LOGISTIC_REGRESSION
    )
    forest = next(
        item for item in result.candidates if item.family is CandidateFamily.RANDOM_FOREST
    )
    validation = {"average_precision": 0.8, "f1": 0.9, "balanced_accuracy": 0.9}
    simple = replace(logistic, complexity_rank=1, validation_metrics=validation)
    complex_model = replace(
        forest,
        complexity_rank=3,
        validation_metrics={**validation, "average_precision": 0.79},
    )
    selected = _select_candidate((dummy, complex_model, simple), dataset.model_spec)
    assert selected.family is CandidateFamily.LOGISTIC_REGRESSION
    with pytest.raises(InsufficientTrainingData, match="ALL_NONLINEAR_AND_LINEAR"):
        _select_candidate((dummy,), dataset.model_spec)
