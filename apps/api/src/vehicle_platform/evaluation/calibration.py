from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize  # type: ignore[import-untyped]
from sklearn.isotonic import IsotonicRegression

from vehicle_platform.evaluation.contracts import CalibrationMethod

CALIBRATOR_SCHEMA = "phase9g-research-calibrator-v1"
CALIBRATOR_ROOT = Path("apps/api/.artifacts/phase9g/research")
MAX_CALIBRATOR_BYTES = 65_536
SIGMOID_EPSILON = 1e-6


@dataclass(frozen=True)
class FittedCalibrator:
    method: CalibrationMethod
    parameters: dict[str, Any]
    calibration_row_count: int
    calibration_positive_count: int
    calibration_negative_count: int
    calibration_cluster_count: int
    calibration_row_checksum: str

    def manifest(self) -> dict[str, Any]:
        return {
            "method": self.method.value,
            "parameters": self.parameters,
            "calibration_row_count": self.calibration_row_count,
            "calibration_positive_count": self.calibration_positive_count,
            "calibration_negative_count": self.calibration_negative_count,
            "calibration_cluster_count": self.calibration_cluster_count,
            "calibration_row_checksum": self.calibration_row_checksum,
        }


class CalibrationError(ValueError):
    pass


def calibration_row_checksum(
    row_ids: Sequence[str], scores: Sequence[float], labels: Sequence[int | bool]
) -> str:
    if len(row_ids) != len(scores) or len(scores) != len(labels):
        raise CalibrationError("calibration row IDs, scores and labels are misaligned")
    if len(set(row_ids)) != len(row_ids):
        raise CalibrationError("calibration row IDs must be unique")
    normalized_labels = tuple(_binary_label(label) for label in labels)
    values = tuple(float(score) for score in scores)
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values):
        raise CalibrationError("calibration scores must be finite values in [0,1]")
    rows = sorted(
        (str(row_id), score, label)
        for row_id, score, label in zip(row_ids, values, normalized_labels, strict=True)
    )
    return hashlib.sha256(_canonical(rows)).hexdigest()


def fit_calibrator(
    method: CalibrationMethod,
    scores: Sequence[float],
    labels: Sequence[int | bool],
    *,
    row_ids: Sequence[str],
    clusters: Sequence[str],
    dataset_checksum: str,
    minimum_rows: int = 40,
    minimum_each_class: int = 10,
    minimum_clusters: int = 10,
    isotonic_minimum_rows: int = 100,
    isotonic_minimum_each_class: int = 30,
    isotonic_minimum_clusters: int = 30,
) -> FittedCalibrator | None:
    values = np.asarray(scores, dtype=np.float64)
    normalized_labels = tuple(_binary_label(label) for label in labels)
    targets = np.asarray(normalized_labels, dtype=np.int8)
    if not (len(values) == len(targets) == len(row_ids) == len(clusters)):
        raise CalibrationError("calibration vectors must have identical length")
    if len(set(row_ids)) != len(row_ids):
        raise CalibrationError("duplicate calibration example identity")
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise CalibrationError("calibration scores must be finite values in [0,1]")
    if method is CalibrationMethod.IDENTITY:
        return FittedCalibrator(
            method=method,
            parameters={},
            calibration_row_count=len(values),
            calibration_positive_count=int(np.sum(targets)),
            calibration_negative_count=len(targets) - int(np.sum(targets)),
            calibration_cluster_count=len(set(clusters)),
            calibration_row_checksum=calibration_row_checksum(
                row_ids,
                tuple(float(item) for item in values),
                tuple(int(item) for item in targets),
            ),
        )
    positives = int(np.sum(targets))
    negatives = len(targets) - positives
    independent_clusters = len(set(clusters))
    if method is CalibrationMethod.ISOTONIC:
        minimum_rows = isotonic_minimum_rows
        minimum_each_class = isotonic_minimum_each_class
        minimum_clusters = isotonic_minimum_clusters
    if (
        len(values) < minimum_rows
        or positives < minimum_each_class
        or negatives < minimum_each_class
        or independent_clusters < minimum_clusters
    ):
        return None
    if not dataset_checksum or len(dataset_checksum) != 64:
        raise CalibrationError("calibration source checksum must be SHA-256")
    if method is CalibrationMethod.SIGMOID:
        model = _fit_monotone_sigmoid(values, targets)
        params: dict[str, Any] = {
            "intercept": model[0],
            "slope": model[1],
            "input_transform": "logit_clipped_probability",
            "epsilon": SIGMOID_EPSILON,
        }
    elif method is CalibrationMethod.ISOTONIC:
        estimator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        estimator.fit(values, targets)
        thresholds_x = [float(item) for item in estimator.X_thresholds_]
        thresholds_y = [float(item) for item in estimator.y_thresholds_]
        if len(thresholds_x) < 2 or len(thresholds_x) > 512:
            raise CalibrationError("isotonic knots exceed fixed serialization bounds")
        params = {"x": thresholds_x, "y": thresholds_y, "out_of_bounds": "clip"}
    else:
        raise CalibrationError("unknown calibration method")
    return FittedCalibrator(
        method=method,
        parameters=params,
        calibration_row_count=len(values),
        calibration_positive_count=positives,
        calibration_negative_count=negatives,
        calibration_cluster_count=independent_clusters,
        calibration_row_checksum=calibration_row_checksum(
            row_ids,
            tuple(float(item) for item in values),
            tuple(int(item) for item in targets),
        ),
    )


def _fit_monotone_sigmoid(scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    x = np.log(np.clip(scores, SIGMOID_EPSILON, 1.0 - SIGMOID_EPSILON)) - np.log1p(
        -np.clip(scores, SIGMOID_EPSILON, 1.0 - SIGMOID_EPSILON)
    )

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        intercept, slope = parameters
        linear = intercept + slope * x
        probabilities = np.exp(-np.logaddexp(0.0, -linear))
        loss = np.mean(np.logaddexp(0.0, linear) - labels * linear) + 1e-6 * slope * slope
        residual = probabilities - labels
        gradient = np.asarray(
            [np.mean(residual), np.mean(residual * x) + 2e-6 * slope], dtype=np.float64
        )
        return float(loss), gradient

    result = minimize(
        objective,
        np.asarray([0.0, 1.0]),
        method="L-BFGS-B",
        jac=True,
        bounds=((None, None), (0.0, 50.0)),
        options={"maxiter": 500, "ftol": 1e-12, "gtol": 1e-8},
    )
    if not result.success or not np.isfinite(result.fun):
        raise CalibrationError("monotone sigmoid optimizer did not produce finite parameters")
    intercept, slope = (float(item) for item in result.x)
    if not math.isfinite(intercept) or not math.isfinite(slope) or slope < 0:
        raise CalibrationError("monotone sigmoid parameters are invalid")
    return intercept, slope


def apply_calibrator(calibrator: FittedCalibrator, scores: Sequence[float]) -> tuple[float, ...]:
    values = np.asarray(scores, dtype=np.float64)
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise CalibrationError("calibrator inputs must be finite values in [0,1]")
    if calibrator.method is CalibrationMethod.IDENTITY:
        return tuple(float(item) for item in values)
    if calibrator.method is CalibrationMethod.SIGMOID:
        clipped = np.clip(values, SIGMOID_EPSILON, 1.0 - SIGMOID_EPSILON)
        logits = np.log(clipped) - np.log1p(-clipped)
        linear = (
            float(calibrator.parameters["intercept"])
            + float(calibrator.parameters["slope"]) * logits
        )
        calibrated = np.exp(-np.logaddexp(0.0, -linear))
    elif calibrator.method is CalibrationMethod.ISOTONIC:
        x = np.asarray(calibrator.parameters["x"], dtype=np.float64)
        y = np.asarray(calibrator.parameters["y"], dtype=np.float64)
        if len(x) < 2 or len(x) != len(y) or np.any(np.diff(x) < 0) or np.any(np.diff(y) < 0):
            raise CalibrationError("isotonic map is not a bounded monotone map")
        calibrated = np.interp(values, x, y, left=y[0], right=y[-1])
    else:
        raise CalibrationError("unknown calibration method")
    if not np.isfinite(calibrated).all() or ((calibrated < 0) | (calibrated > 1)).any():
        raise CalibrationError("calibration map produced invalid probability values")
    return tuple(float(item) for item in calibrated)


def select_calibration_method(
    candidates: dict[CalibrationMethod, dict[str, Any]],
    *,
    tie_tolerance: float = 1e-4,
) -> CalibrationMethod:
    """Choose by validation Brier only; ties prefer identity, then sigmoid."""
    if not 0 <= tie_tolerance <= 0.01:
        raise ValueError("calibration tie tolerance is outside the fixed range")
    ranked: list[tuple[float, int, CalibrationMethod]] = []
    preference = {
        CalibrationMethod.IDENTITY: 0,
        CalibrationMethod.SIGMOID: 1,
        CalibrationMethod.ISOTONIC: 2,
    }
    for method, report in candidates.items():
        result = report.get("brier_score", {})
        value = result.get("value")
        if (
            report.get("eligible") is True
            and isinstance(value, (int, float))
            and math.isfinite(value)
        ):
            ranked.append((float(value), preference[method], method))
    if not ranked:
        return CalibrationMethod.IDENTITY
    ranked.sort()
    best_value = ranked[0][0]
    tied = [item for item in ranked if item[0] <= best_value + tie_tolerance]
    return min(tied, key=lambda item: item[1])[2]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _binary_label(value: int | bool) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in (0, 1):
        return value
    raise CalibrationError("calibration labels must be exactly zero or one")
