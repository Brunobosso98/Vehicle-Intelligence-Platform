from __future__ import annotations

import random
from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from vehicle_platform.features.domain import MissingReason
from vehicle_platform.ml.domain import (
    CandidateFamily,
    CandidateSpec,
    ModelSpec,
    ModelState,
    SupervisedDataset,
    SupervisedRow,
    TemporalSplit,
)

MISSING_REASON_FEATURES = tuple(item.value for item in MissingReason)
MINIMUM_TEST_CLASS_SUPPORT = 5
OVERFIT_AP_GAP = 0.25
OVERFIT_F1_GAP = 0.25


class InsufficientTrainingData(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class CandidateEvaluation:
    family: CandidateFamily
    parameters: dict[str, Any]
    complexity_rank: int
    threshold: float
    train_metrics: dict[str, Any]
    validation_metrics: dict[str, Any]
    model: Any
    fit_seconds: float
    warnings: tuple[str, ...]

    def manifest(self) -> dict[str, Any]:
        return {
            "family": self.family.value,
            "parameters": self.parameters,
            "complexity_rank": self.complexity_rank,
            "threshold": self.threshold,
            "train_metrics": self.train_metrics,
            "validation_metrics": self.validation_metrics,
            "fit_seconds": self.fit_seconds,
            "status": "failed" if self.warnings else "evaluated",
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class TaskTrainingResult:
    task: str
    state: ModelState
    dataset_checksum: str
    split: TemporalSplit
    candidates: tuple[CandidateEvaluation, ...]
    selected_family: CandidateFamily
    selected_parameters: dict[str, Any]
    selected_threshold: float
    selected_train_metrics: dict[str, Any]
    selected_validation_metrics: dict[str, Any]
    test_metrics: dict[str, dict[str, Any]]
    feature_importance: dict[str, Any]
    walk_forward: dict[str, Any]
    overfit_warnings: tuple[str, ...]
    acceptance: dict[str, Any]
    input_schema: dict[str, Any]
    selected_model: Any
    stage_seconds: dict[str, float]
    test_evaluated_after_selection: bool

    def manifest(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "state": self.state.value,
            "dataset_checksum": self.dataset_checksum,
            "split": {
                "cutoffs": self.split.cutoffs,
                "group_counts": self.split.group_counts,
                "row_counts": {
                    "train": len(self.split.train),
                    "validation": len(self.split.validation),
                    "test": len(self.split.test),
                },
            },
            "candidates": [item.manifest() for item in self.candidates],
            "selected_model": {
                "family": self.selected_family.value,
                "parameters": self.selected_parameters,
                "threshold": self.selected_threshold,
                "train_metrics": self.selected_train_metrics,
                "validation_metrics": self.selected_validation_metrics,
            },
            "test_metrics": self.test_metrics,
            "feature_importance": self.feature_importance,
            "walk_forward": self.walk_forward,
            "overfit_warnings": list(self.overfit_warnings),
            "acceptance": self.acceptance,
            "input_schema": self.input_schema,
            "stage_seconds": self.stage_seconds,
            "test_evaluated_after_selection": self.test_evaluated_after_selection,
            "test_influenced_selection": False,
        }


def reset_random_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def input_schema(spec: ModelSpec) -> dict[str, Any]:
    from vehicle_platform.features.registry import DEFAULT_REGISTRY

    columns: list[dict[str, str]] = []
    for key in spec.feature_keys:
        definition = DEFAULT_REGISTRY.resolve(key)
        columns.append({"key": key, "dtype": definition.dtype.value, "unit": definition.unit or ""})
        columns.extend(
            {
                "key": f"{key}__missing__{reason}",
                "dtype": "boolean_indicator",
                "unit": "",
            }
            for reason in MISSING_REASON_FEATURES
        )
    return {
        "feature_set_version": spec.feature_set_version,
        "raw_feature_keys": list(spec.feature_keys),
        "raw_feature_order": list(spec.feature_keys),
        "matrix_columns": columns,
        "missing_reason_categories": list(MISSING_REASON_FEATURES),
        "numeric_imputation": (
            "median fitted on train partition only; all-missing columns use placeholder zero "
            "with explicit reason indicators"
        ),
        "linear_scaling": "StandardScaler fitted inside train-only candidate pipeline",
    }


def matrix_for_rows(
    rows: tuple[SupervisedRow, ...], spec: ModelSpec
) -> tuple[np.ndarray, np.ndarray, tuple[str, ...], tuple[str, ...]]:
    column_names = matrix_column_names(spec)
    matrix = np.full((len(rows), len(column_names)), np.nan, dtype=np.float64)
    labels = np.zeros(len(rows), dtype=np.int64)
    for row_index, row in enumerate(rows):
        matrix[row_index] = matrix_for_feature_mapping(row.features, row.missing, spec)[0]
        labels[row_index] = int(row.target)
    indicator_indices = [index for index, name in enumerate(column_names) if "__missing__" in name]
    if len(rows) and not np.isfinite(matrix[:, indicator_indices]).all():
        raise ValueError("missing reason indicators must be finite")
    return (
        matrix,
        labels,
        column_names,
        tuple(row.row_id for row in rows),
    )


def matrix_for_feature_mapping(
    features: dict[str, float | None], missing: dict[str, str], spec: ModelSpec
) -> np.ndarray:
    if set(features) != set(spec.feature_keys):
        raise ValueError("input feature keys differ from the recorded model schema")
    matrix = np.full((1, len(matrix_column_names(spec))), np.nan, dtype=np.float64)
    column_index = 0
    for key in spec.feature_keys:
        value = features[key]
        missing_reason = missing.get(key)
        if value is None:
            if missing_reason not in MISSING_REASON_FEATURES:
                raise ValueError(f"missing input feature {key} has no known missing reason")
        else:
            if missing_reason is not None:
                raise ValueError(f"available input feature {key} also has a missing reason")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"numeric input feature {key} has the wrong dtype")
            numeric = float(value)
            if not np.isfinite(numeric):
                raise ValueError(f"numeric input feature {key} is non-finite")
            matrix[0, column_index] = numeric
        column_index += 1
        for reason in MISSING_REASON_FEATURES:
            matrix[0, column_index] = float(missing_reason == reason)
            column_index += 1
    return matrix


def matrix_column_names(spec: ModelSpec) -> tuple[str, ...]:
    columns: list[str] = []
    for key in spec.feature_keys:
        columns.append(key)
        columns.extend(f"{key}__missing__{reason}" for reason in MISSING_REASON_FEATURES)
    return tuple(columns)


def train_and_evaluate(
    dataset: SupervisedDataset,
    split: TemporalSplit,
    *,
    telemetry: Any | None = None,
) -> TaskTrainingResult:
    spec = dataset.model_spec
    started = perf_counter()
    reset_random_seeds(spec.seed)
    _validate_data_floor(dataset, split)
    schema = input_schema(spec)
    with _span(telemetry, "ml.leakage_validation", {"ml.task": spec.task.value}):
        _validate_split_rows(dataset, split)
    with _span(telemetry, "ml.candidate_training", {"ml.task": spec.task.value}):
        candidates, stage_seconds = _fit_candidates(split, spec, telemetry)
    with _span(telemetry, "ml.validation_selection", {"ml.task": spec.task.value}):
        selected = _select_candidate(candidates, spec)
    with _span(telemetry, "ml.test_evaluation", {"ml.task": spec.task.value}):
        test_metrics = _evaluate_test_baselines_and_selected(split, selected, candidates, spec)
    feature_importance = _feature_importance(selected, split.validation, spec)
    walk_forward = _walk_forward_evaluation(dataset, spec, selected)
    overfit = _overfit_warnings(selected, test_metrics)
    acceptance = _acceptance_state(dataset, split, candidates, selected, test_metrics, spec)
    elapsed = perf_counter() - started
    stage_seconds.update({"total_training_and_evaluation": elapsed})
    if telemetry is not None:
        telemetry.candidate_models.add(len(candidates), {"task": spec.task.value})
        telemetry.model_evaluations.add(1, {"task": spec.task.value, "state": acceptance["state"]})
        telemetry.candidate_training_duration.record(elapsed, {"task": spec.task.value})
        telemetry.dataset_rows_training.record(len(dataset.rows), {"task": spec.task.value})
    return TaskTrainingResult(
        task=spec.task.value,
        state=ModelState(acceptance["state"]),
        dataset_checksum=dataset.checksum,
        split=split,
        candidates=candidates,
        selected_family=selected.family,
        selected_parameters=selected.parameters,
        selected_threshold=selected.threshold,
        selected_train_metrics=selected.train_metrics,
        selected_validation_metrics=selected.validation_metrics,
        test_metrics=test_metrics,
        feature_importance=feature_importance,
        walk_forward=walk_forward,
        overfit_warnings=tuple(overfit),
        acceptance=acceptance,
        input_schema=schema,
        selected_model=selected.model,
        stage_seconds=stage_seconds,
        test_evaluated_after_selection=True,
    )


def _fit_candidates(
    split: TemporalSplit, spec: ModelSpec, telemetry: Any | None
) -> tuple[tuple[CandidateEvaluation, ...], dict[str, float]]:
    x_train, y_train, _, _ = matrix_for_rows(split.train, spec)
    x_validation, y_validation, _, _ = matrix_for_rows(split.validation, spec)
    if len(set(y_train.tolist())) < 2 or len(set(y_validation.tolist())) < 2:
        raise InsufficientTrainingData("CLASS_MISSING_IN_TRAIN_OR_VALIDATION")
    results: list[CandidateEvaluation] = []
    stages: dict[str, float] = {}
    for candidate in spec.candidates:
        started = perf_counter()
        try:
            pipeline = _build_pipeline(candidate, spec.seed)
            with threadpool_limits(limits=1):
                pipeline.fit(x_train, y_train)
            train_probability = _probabilities(pipeline, x_train)
            validation_probability = _probabilities(pipeline, x_validation)
            threshold = (
                0.5
                if candidate.key is CandidateFamily.DUMMY
                else _select_threshold(y_validation, validation_probability, spec.threshold_grid)
            )
            train_metrics = classification_metrics(y_train, train_probability, threshold)
            validation_metrics = classification_metrics(
                y_validation, validation_probability, threshold
            )
            results.append(
                CandidateEvaluation(
                    candidate.key,
                    candidate.parameters,
                    candidate.complexity_rank,
                    threshold,
                    train_metrics,
                    validation_metrics,
                    pipeline,
                    perf_counter() - started,
                    (),
                )
            )
            stages[f"candidate_{candidate.key.value}"] = perf_counter() - started
            if telemetry is not None:
                telemetry.candidate_training_duration.record(
                    stages[f"candidate_{candidate.key.value}"],
                    {"task": spec.task.value, "family": candidate.key.value},
                )
        except Exception as error:
            # Do not render estimator/data error strings into logs or stored traces.
            results.append(
                CandidateEvaluation(
                    candidate.key,
                    candidate.parameters,
                    candidate.complexity_rank,
                    0.5,
                    {},
                    {},
                    None,
                    perf_counter() - started,
                    (type(error).__name__,),
                )
            )
            stages[f"candidate_{candidate.key.value}"] = perf_counter() - started
    if not any(item.family is CandidateFamily.DUMMY and not item.warnings for item in results):
        raise InsufficientTrainingData("DUMMY_BASELINE_FAILED")
    return tuple(results), stages


def _build_pipeline(candidate: CandidateSpec, seed: int) -> Pipeline:
    steps: list[tuple[str, Any]] = [
        ("impute", SimpleImputer(strategy="median", keep_empty_features=True))
    ]
    if candidate.key is CandidateFamily.DUMMY:
        estimator: Any = DummyClassifier(**candidate.parameters, random_state=seed)
    elif candidate.key is CandidateFamily.LOGISTIC_REGRESSION:
        steps.append(("scale", StandardScaler()))
        estimator = LogisticRegression(**candidate.parameters, random_state=seed)
    elif candidate.key is CandidateFamily.RANDOM_FOREST:
        estimator = RandomForestClassifier(**candidate.parameters, random_state=seed)
    else:
        raise ValueError("candidate is not in the fixed estimator allowlist")
    steps.append(("estimator", estimator))
    return Pipeline(steps)


def _probabilities(model: Any, matrix: np.ndarray) -> np.ndarray:
    if not hasattr(model, "predict_proba"):
        raise ValueError("fixed Phase 9B classifiers must expose probabilities")
    result = np.asarray(model.predict_proba(matrix), dtype=np.float64)
    if result.ndim != 2 or result.shape[1] != 2 or not np.isfinite(result).all():
        raise ValueError("classifier returned an invalid probability matrix")
    classes = tuple(int(item) for item in model.classes_)
    if classes != (0, 1):
        raise ValueError("classifier classes differ from the binary label schema")
    return result[:, 1]


def _select_threshold(
    y_true: np.ndarray, probability: np.ndarray, thresholds: tuple[float, ...]
) -> float:
    options: list[tuple[float, float, float, float]] = []
    for threshold in thresholds:
        metrics = classification_metrics(y_true, probability, threshold)
        options.append(
            (
                float(metrics["f1"] or 0.0),
                float(metrics["balanced_accuracy"] or 0.0),
                float(metrics["recall"] or 0.0),
                -abs(threshold - 0.5),
            )
        )
    best = max(options)
    return thresholds[options.index(best)]


def _select_candidate(
    candidates: tuple[CandidateEvaluation, ...], spec: ModelSpec
) -> CandidateEvaluation:
    dummy = next(
        (item for item in candidates if item.family is CandidateFamily.DUMMY and not item.warnings),
        None,
    )
    if dummy is None:
        raise InsufficientTrainingData("DUMMY_BASELINE_FAILED")
    dummy_ap = dummy.validation_metrics.get("average_precision")
    eligible: list[CandidateEvaluation] = []
    for candidate in candidates:
        if candidate.family is CandidateFamily.DUMMY or candidate.warnings:
            continue
        metrics = candidate.validation_metrics
        if (
            metrics.get("average_precision") is not None
            and dummy_ap is not None
            and metrics["average_precision"] >= dummy_ap + spec.minimum_average_precision_lift
            and (metrics.get("f1") or 0.0) >= spec.minimum_f1
            and (metrics.get("balanced_accuracy") or 0.0) >= spec.minimum_balanced_accuracy
        ):
            eligible.append(candidate)
    non_dummy = [
        item
        for item in candidates
        if item.family is not CandidateFamily.DUMMY and not item.warnings
    ]
    if not non_dummy:
        raise InsufficientTrainingData("ALL_NONLINEAR_AND_LINEAR_CANDIDATES_FAILED")
    pool = eligible or non_dummy
    best_ap = max(float(item.validation_metrics.get("average_precision") or 0.0) for item in pool)
    near_best = [
        item
        for item in pool
        if best_ap - float(item.validation_metrics.get("average_precision") or 0.0)
        <= spec.selection_margin
    ]
    return min(
        near_best,
        key=lambda item: (
            item.complexity_rank,
            -float(item.validation_metrics.get("average_precision") or 0.0),
        ),
    )


def _evaluate_test_baselines_and_selected(
    split: TemporalSplit,
    selected: CandidateEvaluation,
    candidates: tuple[CandidateEvaluation, ...],
    spec: ModelSpec,
) -> dict[str, dict[str, Any]]:
    x_test, y_test, _, _ = matrix_for_rows(split.test, spec)
    dummy = next(item for item in candidates if item.family is CandidateFamily.DUMMY)
    test: dict[str, dict[str, Any]] = {
        "dummy": classification_metrics(y_test, _probabilities(dummy.model, x_test), 0.5),
        "selected": classification_metrics(
            y_test, _probabilities(selected.model, x_test), selected.threshold
        ),
    }
    # Baseline evaluation happens after model selection and never changes the selected family.
    test["selection_policy"] = {
        "selected_before_test_evaluation": True,
        "test_used_for_selection": False,
        "selected_family": selected.family.value,
        "threshold_source": "validation",
    }
    return test


def classification_metrics(
    y_true: np.ndarray, probability: np.ndarray, threshold: float
) -> dict[str, Any]:
    actual = np.asarray(y_true, dtype=np.int64)
    scores = np.asarray(probability, dtype=np.float64)
    predicted = (scores >= threshold).astype(np.int64)
    tn = int(np.sum((actual == 0) & (predicted == 0)))
    fp = int(np.sum((actual == 0) & (predicted == 1)))
    fn = int(np.sum((actual == 1) & (predicted == 0)))
    tp = int(np.sum((actual == 1) & (predicted == 1)))
    negative_support = tn + fp
    positive_support = tp + fn
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / positive_support if positive_support else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else 0.0
        if precision == 0 and recall == 0
        else None
    )
    balanced_accuracy = (
        0.5 * (tp / positive_support + tn / negative_support)
        if positive_support and negative_support
        else None
    )
    both_classes = bool(positive_support and negative_support)
    undefined: list[str] = []
    if precision is None:
        undefined.append("precision:no_positive_predictions")
    if recall is None:
        undefined.append("recall:no_positive_support")
    if balanced_accuracy is None:
        undefined.append("balanced_accuracy:class_missing")
    if not both_classes:
        undefined.extend(("roc_auc:class_missing", "average_precision:class_missing"))
    return {
        "threshold": threshold,
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "balanced_accuracy": balanced_accuracy,
        "roc_auc": _metric_or_none("roc_auc", actual, scores, both_classes),
        "average_precision": _metric_or_none("average_precision", actual, scores, both_classes),
        "brier_score": float(np.mean((scores - actual) ** 2)) if len(actual) else None,
        "class_support": {"negative": negative_support, "positive": positive_support},
        "positive_prevalence": positive_support / len(actual) if len(actual) else None,
        "predicted_positive_support": int(np.sum(predicted == 1)),
        "reliability_summary": reliability_summary(actual, scores),
        "undefined_metrics": undefined,
    }


def _metric_or_none(
    name: str, actual: np.ndarray, scores: np.ndarray, defined: bool
) -> float | None:
    if not defined:
        return None
    if name == "average_precision":
        return float(average_precision_score(actual, scores))
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(actual, scores))


def reliability_summary(y_true: np.ndarray, probability: np.ndarray) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    edges = np.linspace(0.0, 1.0, 6)
    for index in range(len(edges) - 1):
        lower, upper = float(edges[index]), float(edges[index + 1])
        selected = (probability >= lower) & (
            probability < upper if index < len(edges) - 2 else probability <= upper
        )
        count = int(np.sum(selected))
        result.append(
            {
                "lower_bound": lower,
                "upper_bound": upper,
                "support": count,
                "mean_probability": float(np.mean(probability[selected])) if count else None,
                "observed_positive_rate": float(np.mean(y_true[selected])) if count else None,
            }
        )
    return result


def _feature_importance(
    selected: CandidateEvaluation, validation_rows: tuple[SupervisedRow, ...], spec: ModelSpec
) -> dict[str, Any]:
    x_validation, y_validation, matrix_columns, _ = matrix_for_rows(validation_rows, spec)
    if len(set(y_validation.tolist())) < 2:
        return {"method": "unavailable", "reason": "validation class missing", "values": []}
    permutation = permutation_importance(
        selected.model,
        x_validation,
        y_validation,
        scoring="average_precision",
        n_repeats=5,
        random_state=spec.seed,
        n_jobs=1,
    )
    grouped: dict[str, float] = {key: 0.0 for key in spec.feature_keys}
    raw_coefficients: dict[str, float] = {}
    estimator = selected.model.named_steps["estimator"]
    coefficients = getattr(estimator, "coef_", None)
    if coefficients is not None:
        for column, coefficient in zip(matrix_columns, coefficients[0], strict=True):
            feature = column.split("__missing__", maxsplit=1)[0]
            raw_coefficients[column] = float(coefficient)
            grouped[feature] = grouped.get(feature, 0.0) + abs(float(coefficient))
    else:
        for column, importance in zip(matrix_columns, permutation.importances_mean, strict=True):
            feature = column.split("__missing__", maxsplit=1)[0]
            grouped[feature] = grouped.get(feature, 0.0) + float(importance)
    values: list[dict[str, str | float]] = [
        {"feature_key": key, "association_importance": value}
        for key, value in sorted(grouped.items(), key=lambda item: (-item[1], item[0]))
    ]
    total = 0.0
    for item in values:
        total += abs(cast(float, item["association_importance"]))
    noise_share = 0.0
    for item in values:
        if item["feature_key"] == "quality.sample_interval_stddev_s" and total:
            noise_share = abs(cast(float, item["association_importance"])) / total
    return {
        "method": "validation permutation importance grouped by raw feature",
        "linear_coefficients": raw_coefficients,
        "values": values,
        "noise_control_key": "quality.sample_interval_stddev_s",
        "noise_control_importance_share": noise_share,
        "interpretation": "feature contribution/association is not mechanical causality.",
    }


def _walk_forward_evaluation(
    dataset: SupervisedDataset, spec: ModelSpec, main_selected: CandidateEvaluation
) -> dict[str, Any]:
    from vehicle_platform.ml.splitting import walk_forward_splits

    folds: list[dict[str, Any]] = []
    for fold in walk_forward_splits(dataset):
        if (
            len({row.target for row in fold.train}) < 2
            or len({row.target for row in fold.validation}) < 2
        ):
            folds.append(
                {
                    "fold": fold.index,
                    "status": "CLASS_MISSING_IN_FOLD",
                    "train_count": len(fold.train),
                    "validation_count": len(fold.validation),
                    "test_count": len(fold.test),
                    "train_end": fold.train_end.isoformat(),
                    "validation_end": fold.validation_end.isoformat(),
                    "test_end": fold.test_end.isoformat(),
                }
            )
            continue
        candidate_spec = next(item for item in spec.candidates if item.key is main_selected.family)
        x_train, y_train, _, _ = matrix_for_rows(fold.train, spec)
        x_validation, y_validation, _, _ = matrix_for_rows(fold.validation, spec)
        x_test, y_test, _, _ = matrix_for_rows(fold.test, spec)
        model = _build_pipeline(candidate_spec, spec.seed)
        with threadpool_limits(limits=1):
            model.fit(x_train, y_train)
        threshold = _select_threshold(
            y_validation, _probabilities(model, x_validation), spec.threshold_grid
        )
        metrics = classification_metrics(y_test, _probabilities(model, x_test), threshold)
        warnings = []
        support = metrics["class_support"]
        if (
            support["positive"] < MINIMUM_TEST_CLASS_SUPPORT
            or support["negative"] < MINIMUM_TEST_CLASS_SUPPORT
        ):
            warnings.append("INSUFFICIENT_TEST_SUPPORT")
        folds.append(
            {
                "fold": fold.index,
                "status": "evaluated",
                "train_count": len(fold.train),
                "validation_count": len(fold.validation),
                "test_count": len(fold.test),
                "train_end": fold.train_end.isoformat(),
                "validation_end": fold.validation_end.isoformat(),
                "test_end": fold.test_end.isoformat(),
                "threshold_from_validation": threshold,
                "metrics": metrics,
                "warnings": warnings,
            }
        )
    evaluated = [item["metrics"] for item in folds if item.get("status") == "evaluated"]
    aggregate: dict[str, float | None] = {}
    for key in ("f1", "balanced_accuracy", "average_precision", "roc_auc", "brier_score"):
        values = [float(item[key]) for item in evaluated if item.get(key) is not None]
        aggregate[key] = float(np.mean(values)) if values else None
        aggregate[f"{key}_stddev"] = float(np.std(values)) if values else None
    return {
        "policy": "expanding train prefix, later validation for threshold, then later test block",
        "selected_family_fixed_from_main_validation": main_selected.family.value,
        "fold_count": len(folds),
        "folds": folds,
        "aggregate_mean_and_stddev": aggregate,
    }


def _overfit_warnings(
    selected: CandidateEvaluation, test_metrics: dict[str, dict[str, Any]]
) -> list[str]:
    warnings: list[str] = []
    train_ap = selected.train_metrics.get("average_precision")
    validation_ap = selected.validation_metrics.get("average_precision")
    test_ap = test_metrics["selected"].get("average_precision")
    if (
        train_ap is not None
        and validation_ap is not None
        and train_ap - validation_ap > OVERFIT_AP_GAP
    ):
        warnings.append("OVERFIT_WARNING: train/validation average-precision gap exceeds 0.25")
    train_f1 = selected.train_metrics.get("f1")
    validation_f1 = selected.validation_metrics.get("f1")
    if (
        train_f1 is not None
        and validation_f1 is not None
        and train_f1 - validation_f1 > OVERFIT_F1_GAP
    ):
        warnings.append("OVERFIT_WARNING: train/validation F1 gap exceeds 0.25")
    if (
        validation_ap is not None
        and test_ap is not None
        and validation_ap - test_ap > OVERFIT_AP_GAP
    ):
        warnings.append("OVERFIT_WARNING: validation/test average-precision gap exceeds 0.25")
    support = test_metrics["selected"]["class_support"]
    if (
        support["positive"] < MINIMUM_TEST_CLASS_SUPPORT
        or support["negative"] < MINIMUM_TEST_CLASS_SUPPORT
    ):
        warnings.append("INSUFFICIENT_TEST_SUPPORT")
    return warnings


def _acceptance_state(
    dataset: SupervisedDataset,
    split: TemporalSplit,
    candidates: tuple[CandidateEvaluation, ...],
    selected: CandidateEvaluation,
    test_metrics: dict[str, dict[str, Any]],
    spec: ModelSpec,
) -> dict[str, Any]:
    labels = [row.target for row in dataset.rows]
    positives = sum(labels)
    negatives = len(labels) - positives
    dummy_ap = float(
        next(
            item for item in candidates if item.family is CandidateFamily.DUMMY
        ).validation_metrics["average_precision"]
    )
    selected_validation = selected.validation_metrics
    selected_test = test_metrics["selected"]
    dummy_test = test_metrics["dummy"]
    criteria = {
        "minimum_total_rows": len(dataset.rows) >= spec.minimum_rows,
        "minimum_positive_rows": positives >= spec.minimum_positive,
        "minimum_negative_rows": negatives >= spec.minimum_negative,
        "both_classes_in_train_validation_test": all(
            len({row.target for row in rows}) == 2
            for rows in (split.train, split.validation, split.test)
        ),
        "validation_f1_threshold": (selected_validation.get("f1") or 0.0) >= spec.minimum_f1,
        "validation_balanced_accuracy_threshold": (
            selected_validation.get("balanced_accuracy") or 0.0
        )
        >= spec.minimum_balanced_accuracy,
        "validation_ap_above_dummy": (selected_validation.get("average_precision") or 0.0)
        >= dummy_ap + spec.minimum_average_precision_lift,
        "test_ap_above_dummy": (selected_test.get("average_precision") or 0.0)
        > (dummy_test.get("average_precision") or 0.0),
        "test_f1_above_dummy": (selected_test.get("f1") or 0.0) > (dummy_test.get("f1") or 0.0),
        "test_support_sufficient": min(selected_test["class_support"].values())
        >= MINIMUM_TEST_CLASS_SUPPORT,
    }
    return {
        "state": ModelState.CANDIDATE.value
        if all(criteria.values())
        else ModelState.REJECTED.value,
        "criteria": criteria,
        "all_criteria_pass": all(criteria.values()),
        "thresholds_defined_in_model_spec_before_test": True,
        "positive_count": positives,
        "negative_count": negatives,
        "prevalence": positives / len(labels) if labels else None,
        "candidate_trial_count": len(spec.candidates),
        "hyperparameter_search_trial_count": 0,
        "test_data_used_for_tuning_or_selection": False,
    }


def _validate_data_floor(dataset: SupervisedDataset, split: TemporalSplit) -> None:
    labels = [row.target for row in dataset.rows]
    spec = dataset.model_spec
    positive, negative = sum(labels), len(labels) - sum(labels)
    if len(labels) < spec.minimum_rows:
        raise InsufficientTrainingData(
            f"INSUFFICIENT_TRAINING_DATA:{spec.task.value}:minimum_total_rows:{len(labels)}"
        )
    if positive < spec.minimum_positive:
        raise InsufficientTrainingData(
            f"INSUFFICIENT_TRAINING_DATA:{spec.task.value}:minimum_positive_support:{positive}"
        )
    if negative < spec.minimum_negative:
        raise InsufficientTrainingData(
            f"INSUFFICIENT_TRAINING_DATA:{spec.task.value}:minimum_negative_support:{negative}"
        )
    if not split.train or not split.validation or not split.test:
        raise InsufficientTrainingData("INSUFFICIENT_TRAINING_DATA: empty_temporal_partition")


def _validate_split_rows(dataset: SupervisedDataset, split: TemporalSplit) -> None:
    dataset_ids = {row.row_id for row in dataset.rows}
    partitions = (split.train, split.validation, split.test)
    partition_ids = [row.row_id for rows in partitions for row in rows]
    if len(partition_ids) != len(set(partition_ids)) or not set(partition_ids).issubset(
        dataset_ids
    ):
        raise ValueError("split rows are duplicated or absent from the supervised dataset")
    group_sets = [{row.group_id for row in rows} for rows in partitions]
    if (
        group_sets[0] & group_sets[1]
        or group_sets[0] & group_sets[2]
        or group_sets[1] & group_sets[2]
    ):
        raise ValueError("temporal session groups cross split boundaries")
    if max(row.target_started_at for row in split.train) >= min(
        row.input_started_at for row in split.validation
    ):
        raise ValueError("validation is not strictly later than training")
    if max(row.target_started_at for row in split.validation) >= min(
        row.input_started_at for row in split.test
    ):
        raise ValueError("test is not strictly later than validation")


def _span(telemetry: Any | None, name: str, attributes: dict[str, Any]) -> Any:
    if telemetry is None:
        return _NoopSpan()
    return telemetry.tracer.start_as_current_span(name, attributes=attributes)


class _NoopSpan:
    def __enter__(self) -> _NoopSpan:
        return self

    def __exit__(self, *args: object) -> None:
        return None
