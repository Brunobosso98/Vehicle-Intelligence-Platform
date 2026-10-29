from __future__ import annotations

from vehicle_platform.evaluation.contracts import (
    CalibrationMethod,
    EvaluationProtocol,
)
from vehicle_platform.ml.domain import MLTask

PROTOCOL_THRESHOLDS = tuple(index / 10 for index in range(1, 10))


def default_protocol(*, seed: int = 9142, max_rows: int = 20_000) -> EvaluationProtocol:
    return EvaluationProtocol(
        tasks=tuple(item.value for item in MLTask),
        anomaly_families=("thermal", "boost_air", "performance", "fuel"),
        split_policy="chronological-session-vehicle-configuration-holdout-v1",
        calibration_fraction=1 / 3,
        validation_fraction=1 / 3,
        calibration_methods=(
            CalibrationMethod.IDENTITY,
            CalibrationMethod.SIGMOID,
            CalibrationMethod.ISOTONIC,
        ),
        calibration_minimum_rows=40,
        calibration_minimum_each_class=10,
        calibration_minimum_clusters=10,
        isotonic_minimum_rows=100,
        isotonic_minimum_each_class=30,
        isotonic_minimum_clusters=30,
        reliability_bins=5,
        bootstrap_resamples=200,
        seed=seed,
        max_rows=max_rows,
        max_artifact_bytes=65_536,
        thresholds=PROTOCOL_THRESHOLDS,
        no_auto_promotion=True,
        no_real_failure_probability=True,
    )
