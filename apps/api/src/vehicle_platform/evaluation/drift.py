from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np


def population_stability_index(
    baseline: Sequence[float], comparison: Sequence[float], *, bins: int = 10
) -> float | None:
    base = _finite_vector(baseline)
    current = _finite_vector(comparison)
    if len(base) < 2 or len(current) < 2:
        return None
    if not 2 <= bins <= 20:
        raise ValueError("PSI bins must be between two and twenty")
    edges = np.unique(np.quantile(base, np.linspace(0.0, 1.0, bins + 1)))
    if len(edges) < 2:
        center = float(base[0])
        edges = np.asarray([center - 1e-9, center + 1e-9])
    else:
        edges[0] = -np.inf
        edges[-1] = np.inf
    base_counts = np.histogram(base, bins=edges)[0].astype(np.float64)
    current_counts = np.histogram(current, bins=edges)[0].astype(np.float64)
    base_share = np.maximum(base_counts / len(base), 1e-6)
    current_share = np.maximum(current_counts / len(current), 1e-6)
    value = float(np.sum((current_share - base_share) * np.log(current_share / base_share)))
    return value if math.isfinite(value) else None


def robust_location_shift(baseline: Sequence[float], comparison: Sequence[float]) -> float | None:
    base = _finite_vector(baseline)
    current = _finite_vector(comparison)
    if len(base) < 2 or len(current) < 1:
        return None
    median = float(np.median(base))
    mad_scale = 1.4826 * float(np.median(np.abs(base - median)))
    if mad_scale <= 1e-12:
        q25, q75 = np.quantile(base, (0.25, 0.75))
        mad_scale = float(q75 - q25) / 1.349
    if mad_scale <= 1e-12:
        mad_scale = max(abs(median) * 1e-6, 1e-9)
    return (float(np.median(current)) - median) / mad_scale


def ood_distances(
    training_features: dict[str, Sequence[float]],
    comparison_features: dict[str, Sequence[float]],
    *,
    maximum_features: int = 32,
) -> dict[str, Any]:
    if len(training_features) > maximum_features or len(comparison_features) > maximum_features:
        raise ValueError("OOD feature count exceeds the fixed protocol bound")
    if set(training_features) != set(comparison_features):
        raise ValueError("OOD feature order and names must match the frozen train schema")
    output: dict[str, Any] = {}
    warnings = 0
    for name in sorted(training_features):
        train = _finite_vector(training_features[name])
        later = _finite_vector(comparison_features[name])
        if len(train) < 5 or len(later) < 1:
            output[name] = {"status": "INSUFFICIENT_SUPPORT", "distance": None, "warning": False}
            continue
        median = float(np.median(train))
        q01, q99 = np.quantile(train, (0.01, 0.99))
        scale = max(float(q99 - q01), abs(median) * 1e-6, 1e-9)
        distances = np.abs(later - median) / scale
        score = float(np.quantile(distances, 0.95))
        warning = score > 2.0
        warnings += int(warning)
        output[name] = {
            "status": "OOD_WARNING" if warning else "WITHIN_TRAIN_REFERENCE_RANGE",
            "distance": score,
            "warning_threshold": 2.0,
            "baseline_rows": len(train),
            "comparison_rows": len(later),
            "warning": warning,
        }
    return {
        "feature_count": len(output),
        "warning_feature_count": warnings,
        "features": output,
        "threshold_fit_source": "training_partition_only",
        "interpretation": "distribution warning only; not a fault or performance conclusion",
    }


def drift_experiment(
    baseline_features: dict[str, Sequence[float]],
    comparison_features: dict[str, Sequence[float]],
    *,
    baseline_labels: Sequence[int | bool] | None = None,
    comparison_labels: Sequence[int | bool] | None = None,
    baseline_predictions: Sequence[float] | None = None,
    comparison_predictions: Sequence[float] | None = None,
) -> dict[str, Any]:
    if set(baseline_features) != set(comparison_features):
        raise ValueError("drift feature names must match")
    feature_results = {
        name: {
            "psi": population_stability_index(baseline_features[name], comparison_features[name]),
            "robust_median_shift": robust_location_shift(
                baseline_features[name], comparison_features[name]
            ),
        }
        for name in sorted(baseline_features)
    }
    labeled = baseline_labels is not None and comparison_labels is not None
    label_shift: dict[str, Any]
    concept_shift: dict[str, Any]
    if not labeled:
        label_shift = {"status": "UNKNOWN", "value": None, "reason": "TRUSTED_LABELS_UNAVAILABLE"}
        concept_shift = {
            "status": "UNKNOWN",
            "value": None,
            "reason": "TRUSTED_LABELS_UNAVAILABLE",
        }
    else:
        baseline_y = np.asarray(baseline_labels, dtype=np.int8)
        comparison_y = np.asarray(comparison_labels, dtype=np.int8)
        if (
            len(baseline_y) == 0
            or len(comparison_y) == 0
            or not np.isin(baseline_y, (0, 1)).all()
            or not np.isin(comparison_y, (0, 1)).all()
        ):
            raise ValueError("label drift requires nonempty binary labels")
        baseline_rate = float(np.mean(baseline_y))
        comparison_rate = float(np.mean(comparison_y))
        label_shift = {
            "status": "MEASURED_SYNTHETIC_LABEL_PREVALENCE",
            "baseline_rate": baseline_rate,
            "comparison_rate": comparison_rate,
            "value": comparison_rate - baseline_rate,
            "real_world_claim_allowed": False,
        }
        if baseline_predictions is None or comparison_predictions is None:
            concept_shift = {
                "status": "UNKNOWN",
                "value": None,
                "reason": "FROZEN_MODEL_PREDICTIONS_REQUIRED",
            }
        else:
            baseline_error = _brier(baseline_predictions, baseline_y)
            comparison_error = _brier(comparison_predictions, comparison_y)
            concept_shift = {
                "status": "MEASURED_SYNTHETIC_PERFORMANCE_CHANGE",
                "metric": "Brier score",
                "baseline": baseline_error,
                "comparison": comparison_error,
                "value": comparison_error - baseline_error,
                "real_world_claim_allowed": False,
            }
    feature_drift = any(
        result["psi"] is not None and result["psi"] >= 0.20 for result in feature_results.values()
    )
    return {
        "feature_drift": {
            "status": "WARNING" if feature_drift else "NO_PREDECLARED_WARNING",
            "features": feature_results,
            "psi_warning_threshold": 0.20,
            "threshold_is_not_performance_evidence": True,
        },
        "label_prevalence_drift": label_shift,
        "concept_performance_drift": concept_shift,
        "calibration_drift": {
            "status": "UNKNOWN" if not labeled else "REQUIRES_RELIABILITY_COMPARISON",
            "value": None,
            "reason": "no adjudicated real-world mechanical outcomes are available",
        },
        "detector_reference_drift": {
            "status": "OFFLINE_REFERENCE_COMPARISON_ONLY",
            "interpretation": "reference cohort changes require a new versioned evaluation",
        },
    }


def _brier(predictions: Sequence[float], labels: np.ndarray) -> float:
    predicted = np.asarray(predictions, dtype=np.float64)
    if (
        len(predicted) != len(labels)
        or not np.isfinite(predicted).all()
        or ((predicted < 0) | (predicted > 1)).any()
    ):
        raise ValueError("drift performance comparison requires aligned finite probabilities")
    return float(np.mean(np.square(predicted - labels)))


def _finite_vector(values: Sequence[float]) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64)
    if not np.isfinite(result).all():
        raise ValueError("drift inputs must be finite")
    return result
