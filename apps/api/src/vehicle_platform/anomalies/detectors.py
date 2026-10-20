from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from threadpoolctl import threadpool_limits

from vehicle_platform.anomalies.domain import (
    AnomalyDetectorDefinition,
    AnomalyFamily,
    AnomalyFindingResult,
    AnomalyReason,
    AnomalyReferenceDataset,
    AnomalyStatus,
    DetectorMethod,
    DeviationDirection,
    FeatureObservation,
    ReferenceRow,
)
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.ml.artifacts import library_versions


class DetectorFitError(ValueError):
    def __init__(self, reason: AnomalyReason, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class RobustFeatureStats:
    median: float
    mad: float
    scale: float
    q25: float
    q75: float
    unit: str
    coverage: float
    constant: bool

    def manifest(self) -> dict[str, Any]:
        return {
            "median": self.median,
            "mad": self.mad,
            "scale": self.scale,
            "q25": self.q25,
            "q75": self.q75,
            "unit": self.unit,
            "coverage": self.coverage,
            "constant": self.constant,
        }


@dataclass(frozen=True)
class FittedDetector:
    definition_checksum: str
    reference_checksum: str
    family: AnomalyFamily
    method: DetectorMethod
    feature_order: tuple[str, ...]
    robust_stats: dict[str, RobustFeatureStats]
    optional_feature_order: tuple[str, ...]
    imputation_medians: dict[str, float]
    robust_centers: dict[str, float]
    robust_scales: dict[str, float]
    missing_indicator_order: tuple[str, ...]
    threshold: float
    training_score_quantile: float
    training_score_summary: dict[str, float]
    estimator: IsolationForest | None = None
    library_version_map: dict[str, str] | None = None

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "phase9c-fitted-detector-v1",
            "definition_checksum": self.definition_checksum,
            "reference_checksum": self.reference_checksum,
            "family": self.family.value,
            "method": self.method.value,
            "feature_order": list(self.feature_order),
            "robust_stats": {
                key: value.manifest() for key, value in sorted(self.robust_stats.items())
            },
            "optional_feature_order": list(self.optional_feature_order),
            "imputation_medians": dict(sorted(self.imputation_medians.items())),
            "robust_centers": dict(sorted(self.robust_centers.items())),
            "robust_scales": dict(sorted(self.robust_scales.items())),
            "missing_indicator_order": list(self.missing_indicator_order),
            "threshold": self.threshold,
            "training_score_quantile": self.training_score_quantile,
            "training_score_summary": dict(sorted(self.training_score_summary.items())),
            "library_versions": self.library_version_map or library_versions(),
            "score_orientation": "higher_is_more_statistically_unusual",
            "score_is_probability": False,
        }

    @property
    def checksum(self) -> str:
        return stable_hash(self.manifest())


def fit_detector(
    definition: AnomalyDetectorDefinition,
    reference: AnomalyReferenceDataset,
) -> FittedDetector:
    if definition.family is not reference.family:
        raise DetectorFitError(AnomalyReason.FEATURE_SCHEMA_MISMATCH, "family mismatch")
    if reference.source_role not in definition.supported_source_roles:
        raise DetectorFitError(AnomalyReason.SOURCE_NOT_ALLOWLISTED, "source role is unsupported")
    if not reference.rows:
        if reference.exclusions and all(
            row.get("reason") == AnomalyReason.REQUIRED_SIGNAL_UNAVAILABLE.value
            for row in reference.exclusions
        ):
            raise DetectorFitError(
                AnomalyReason.REQUIRED_SIGNAL_UNAVAILABLE,
                "the selected source does not provide this detector's required telemetry",
            )
        raise DetectorFitError(
            AnomalyReason.REFERENCE_SUPPORT_TOO_LOW, "reference contains no eligible rows"
        )

    cohort_policy = definition.cohort_policy
    min_rows = int(cohort_policy["minimum_reference_rows"])
    min_sessions = int(cohort_policy["minimum_independent_sessions"])
    min_span_seconds = float(cohort_policy["minimum_chronological_span_seconds"])
    if len(reference.rows) < min_rows:
        raise DetectorFitError(
            AnomalyReason.REFERENCE_SUPPORT_TOO_LOW,
            f"reference has {len(reference.rows)} rows; minimum is {min_rows}",
        )
    independent_sessions = {row.session_id for row in reference.rows}
    if len(independent_sessions) < min_sessions:
        raise DetectorFitError(
            AnomalyReason.REFERENCE_SESSION_SUPPORT_TOO_LOW,
            f"reference has {len(independent_sessions)} independent sessions; "
            f"minimum is {min_sessions}",
        )
    if reference.temporal_span.total_seconds() < min_span_seconds:
        raise DetectorFitError(
            AnomalyReason.REFERENCE_SPAN_TOO_SHORT,
            "reference does not span the declared minimum chronological period",
        )

    feature_order = _eligible_feature_order(definition, reference.rows)
    if not feature_order:
        raise DetectorFitError(
            AnomalyReason.CONSTANT_FEATURES_ONLY,
            "no feature varies enough in the reference to support a statistical detector",
        )
    transformed = [transform_features(definition, row) for row in reference.rows]
    matrix_rows = [item[0] for item in transformed]
    for item in matrix_rows:
        for key in feature_order:
            if item.get(key) is None and key in definition.required_feature_keys:
                raise DetectorFitError(
                    AnomalyReason.FEATURE_COVERAGE_TOO_LOW,
                    f"required feature {key} is missing from a reference row",
                )

    coverage_floor = float(definition.fit_parameters["minimum_feature_coverage"])
    robust_stats = _fit_robust_stats(definition, reference.rows, feature_order)
    if not any(not item.constant for item in robust_stats.values()):
        raise DetectorFitError(
            AnomalyReason.CONSTANT_FEATURES_ONLY,
            "all usable reference features are constant",
        )

    if definition.method is DetectorMethod.ROBUST_MAD:
        scores = [
            _robust_score(definition, row, robust_stats, feature_order)[0] for row in reference.rows
        ]
        scores_array = np.asarray(scores, dtype=np.float64)
        minimum_threshold = definition.threshold_policy["robust_minimum_threshold"]
        if minimum_threshold is None:
            raise DetectorFitError(
                AnomalyReason.FEATURE_SCHEMA_MISMATCH,
                "robust detector definition must include a nonnegative score floor",
            )
        threshold = max(
            float(minimum_threshold),
            float(np.quantile(scores_array, float(definition.threshold_policy["quantile"]))),
        )
        fitted = FittedDetector(
            definition_checksum=definition.checksum,
            reference_checksum=reference.checksum(definition),
            family=definition.family,
            method=definition.method,
            feature_order=feature_order,
            robust_stats=robust_stats,
            optional_feature_order=tuple(
                key for key in feature_order if key not in definition.required_feature_keys
            ),
            imputation_medians={},
            robust_centers={key: item.median for key, item in robust_stats.items()},
            robust_scales={key: item.scale for key, item in robust_stats.items()},
            missing_indicator_order=(),
            threshold=threshold,
            training_score_quantile=float(definition.threshold_policy["quantile"]),
            training_score_summary=_summary(scores_array),
            library_version_map=library_versions(),
        )
        return fitted

    if definition.method is not DetectorMethod.ISOLATION_FOREST:
        raise DetectorFitError(AnomalyReason.FEATURE_SCHEMA_MISMATCH, "method is not allowlisted")

    coverage_by_key = {
        key: sum(item.get(key) is not None for item in matrix_rows) / len(matrix_rows)
        for key in feature_order
    }
    if any(coverage_by_key[key] < coverage_floor for key in definition.required_feature_keys):
        raise DetectorFitError(
            AnomalyReason.FEATURE_COVERAGE_TOO_LOW,
            "required feature coverage is below the declared training floor",
        )
    optional_features = tuple(
        key for key in feature_order if key not in definition.required_feature_keys
    )
    missing_indicators = tuple(key for key in optional_features if 0 < coverage_by_key[key] < 1)
    medians = {key: float(np.median(_observed_values(matrix_rows, key))) for key in feature_order}
    centers = {key: robust_stats[key].median for key in feature_order}
    scales = {
        key: robust_stats[key].scale if not robust_stats[key].constant else 1.0
        for key in feature_order
    }
    matrix = _forest_matrix(
        matrix_rows,
        feature_order,
        optional_features,
        missing_indicators,
        medians,
        centers,
        scales,
    )
    if len(matrix) < int(definition.fit_parameters["minimum_training_rows"]):
        raise DetectorFitError(
            AnomalyReason.REFERENCE_SUPPORT_TOO_LOW,
            "Isolation Forest reference is below its minimum training-row count",
        )
    estimator = IsolationForest(
        n_estimators=int(definition.fit_parameters["n_estimators"]),
        max_samples=min(int(definition.fit_parameters["max_samples"]), len(matrix)),
        max_features=float(definition.fit_parameters["max_features"]),
        contamination="auto",
        n_jobs=1,
        random_state=definition.seed,
        bootstrap=False,
    )
    with threadpool_limits(limits=1):
        estimator.fit(matrix)
        scores_array = -np.asarray(estimator.score_samples(matrix), dtype=np.float64)
    if not np.isfinite(scores_array).all():
        raise DetectorFitError(
            AnomalyReason.INVALID_FEATURE_VALUE, "forest returned non-finite scores"
        )
    threshold = float(np.quantile(scores_array, float(definition.threshold_policy["quantile"])))
    return FittedDetector(
        definition_checksum=definition.checksum,
        reference_checksum=reference.checksum(definition),
        family=definition.family,
        method=definition.method,
        feature_order=feature_order,
        robust_stats=robust_stats,
        optional_feature_order=optional_features,
        imputation_medians=medians,
        robust_centers=centers,
        robust_scales=scales,
        missing_indicator_order=missing_indicators,
        threshold=threshold,
        training_score_quantile=float(definition.threshold_policy["quantile"]),
        training_score_summary=_summary(scores_array),
        estimator=estimator,
        library_version_map=library_versions(),
    )


def score_observation(
    definition: AnomalyDetectorDefinition,
    fitted: FittedDetector,
    observation: ReferenceRow,
    *,
    observation_cutoff: Any,
) -> AnomalyFindingResult:
    if definition.checksum != fitted.definition_checksum:
        return _abstention(
            AnomalyStatus.NOT_EVALUABLE,
            AnomalyReason.FEATURE_SCHEMA_MISMATCH,
            _coverage(definition, observation),
            observation,
        )
    if observation_cutoff.tzinfo is None or observation_cutoff.utcoffset() is None:
        return _abstention(
            AnomalyStatus.NOT_EVALUABLE,
            AnomalyReason.INVALID_CUTOFF,
            _coverage(definition, observation),
            observation,
        )
    if observation.pull_ended_at > observation_cutoff:
        return _abstention(
            AnomalyStatus.NOT_EVALUABLE,
            AnomalyReason.CUTOFF_BEFORE_PULL_END,
            _coverage(definition, observation),
            observation,
        )
    if observation.observation_cutoff > observation_cutoff:
        return _abstention(
            AnomalyStatus.NOT_EVALUABLE,
            AnomalyReason.FUTURE_FEATURE,
            _coverage(definition, observation),
            observation,
        )
    for key in definition.feature_keys:
        item = observation.features.get(key)
        if item is not None and (
            (item.available_at is not None and item.available_at > observation_cutoff)
            or (item.source_window_end is not None and item.source_window_end > observation_cutoff)
        ):
            return _abstention(
                AnomalyStatus.NOT_EVALUABLE,
                AnomalyReason.FUTURE_FEATURE,
                _coverage(definition, observation),
                observation,
            )

    values, missing = transform_features(definition, observation)
    absent = tuple(key for key in definition.feature_keys if key in missing)
    required_missing = tuple(key for key in definition.required_feature_keys if key in missing)
    observed = tuple(key for key in definition.feature_keys if key not in missing)
    coverage = len(observed) / len(definition.feature_keys)
    if required_missing:
        has_source = set(definition.required_signal_keys).intersection(
            observation.available_signals
        )
        if not has_source:
            return AnomalyFindingResult(
                status=AnomalyStatus.UNSUPPORTED_SOURCE,
                score=None,
                threshold=fitted.threshold,
                coverage=coverage,
                observed_features=observed,
                absent_features=absent,
                contributions=(),
                reasons=(AnomalyReason.REQUIRED_SIGNAL_UNAVAILABLE,),
            )
        return AnomalyFindingResult(
            status=AnomalyStatus.INSUFFICIENT_SIGNAL,
            score=None,
            threshold=fitted.threshold,
            coverage=coverage,
            observed_features=observed,
            absent_features=absent,
            contributions=(),
            reasons=(AnomalyReason.REQUIRED_FEATURE_MISSING,),
        )
    if coverage < float(definition.quality_policy.get("minimum_feature_coverage", 0.0)):
        return AnomalyFindingResult(
            status=AnomalyStatus.INSUFFICIENT_SIGNAL,
            score=None,
            threshold=fitted.threshold,
            coverage=coverage,
            observed_features=observed,
            absent_features=absent,
            contributions=(),
            reasons=(AnomalyReason.FEATURE_COVERAGE_TOO_LOW,),
        )

    if definition.method is DetectorMethod.ROBUST_MAD:
        score, contributions = _robust_score(
            definition, observation, fitted.robust_stats, fitted.feature_order
        )
    else:
        if fitted.estimator is None:
            return _abstention(
                AnomalyStatus.NOT_EVALUABLE,
                AnomalyReason.ARTIFACT_SCHEMA_MISMATCH,
                coverage,
                observation,
                threshold=fitted.threshold,
                observed=observed,
                absent=absent,
            )
        matrix = _forest_matrix(
            [values],
            fitted.feature_order,
            fitted.optional_feature_order,
            fitted.missing_indicator_order,
            fitted.imputation_medians,
            fitted.robust_centers,
            fitted.robust_scales,
        )
        with threadpool_limits(limits=1):
            score = float(-fitted.estimator.score_samples(matrix)[0])
        if not math.isfinite(score):
            return _abstention(
                AnomalyStatus.NOT_EVALUABLE,
                AnomalyReason.INVALID_FEATURE_VALUE,
                coverage,
                observation,
                threshold=fitted.threshold,
                observed=observed,
                absent=absent,
            )
        _, contributions = _robust_score(
            definition, observation, fitted.robust_stats, fitted.feature_order
        )

    status = AnomalyStatus.ANOMALOUS if score > fitted.threshold else AnomalyStatus.INLIER
    return AnomalyFindingResult(
        status=status,
        score=float(score),
        threshold=fitted.threshold,
        coverage=coverage,
        observed_features=observed,
        absent_features=absent,
        contributions=tuple(contributions[:3]),
        reasons=(),
    )


def transform_features(
    definition: AnomalyDetectorDefinition,
    row: ReferenceRow,
) -> tuple[dict[str, float | None], dict[str, str]]:
    transformed: dict[str, float | None] = {}
    missing: dict[str, str] = {}
    for spec in definition.features:
        primary = row.features.get(spec.key)
        if not _usable_feature(primary, spec.key, spec.unit):
            transformed[spec.score_key] = None
            missing[spec.key] = (
                primary.missing_reason if primary and primary.missing_reason else "not_observed"
            )
            continue
        if primary is None or primary.value is None:
            continue
        value = float(primary.value)
        if spec.context_key is not None:
            context = row.features.get(spec.context_key)
            if not _usable_feature(context, spec.context_key, spec.context_unit or spec.unit):
                transformed[spec.score_key] = None
                missing[spec.context_key] = (
                    context.missing_reason if context and context.missing_reason else "not_observed"
                )
                continue
            if context is None or context.value is None:
                continue
            value -= float(context.value)
        if not math.isfinite(value):
            transformed[spec.score_key] = None
            missing[spec.key] = "invalid_numeric_value"
        else:
            transformed[spec.score_key] = value
    return transformed, missing


def _usable_feature(
    item: FeatureObservation | None,
    key: str,
    expected_unit: str,
) -> bool:
    if item is None or item.value is None:
        return False
    if item.quality not in {"valid", "limited"}:
        return False
    if item.unit != expected_unit:
        return False
    if not math.isfinite(float(item.value)):
        return False
    definition = DEFAULT_REGISTRY.resolve(key)
    if definition.bounds:
        lower, upper = definition.bounds
        if lower is not None and item.value < lower:
            return False
        if upper is not None and item.value > upper:
            return False
    return True


def _eligible_feature_order(
    definition: AnomalyDetectorDefinition,
    rows: tuple[ReferenceRow, ...],
) -> tuple[str, ...]:
    floor = float(definition.fit_parameters["minimum_feature_coverage"])
    eligible: list[str] = []
    for spec in definition.features:
        values: list[float] = []
        for row in rows:
            transformed, _ = transform_features(definition, row)
            value = transformed.get(spec.score_key)
            if value is not None:
                values.append(value)
        coverage = len(values) / len(rows)
        if spec.required and coverage < floor:
            raise DetectorFitError(
                AnomalyReason.FEATURE_COVERAGE_TOO_LOW,
                f"required feature {spec.score_key} coverage is {coverage:.3f}",
            )
        if (
            coverage >= floor
            and values
            and _robust_stats(values, spec.unit, coverage).constant is False
        ):
            eligible.append(spec.score_key)
    if any(
        key not in eligible
        for key in definition.required_feature_keys
        if key in definition.score_feature_keys
    ):
        # The value and model key are identical for required identity features.
        raise DetectorFitError(
            AnomalyReason.CONSTANT_FEATURES_ONLY,
            "a required feature is constant or unavailable in the reference cohort",
        )
    return tuple(eligible)


def _fit_robust_stats(
    definition: AnomalyDetectorDefinition,
    rows: tuple[ReferenceRow, ...],
    feature_order: tuple[str, ...],
) -> dict[str, RobustFeatureStats]:
    stats: dict[str, RobustFeatureStats] = {}
    spec_by_score = {item.score_key: item for item in definition.features}
    for key in feature_order:
        spec = spec_by_score[key]
        values: list[float] = []
        for row in rows:
            transformed, _ = transform_features(definition, row)
            value = transformed.get(key)
            if value is not None:
                values.append(value)
        coverage = len(values) / len(rows)
        stats[key] = _robust_stats(values, spec.unit, coverage)
    return stats


def _robust_stats(values: list[float], unit: str, coverage: float) -> RobustFeatureStats:
    if not values:
        return RobustFeatureStats(0.0, 0.0, 0.0, 0.0, 0.0, unit, coverage, True)
    ordered = np.asarray(values, dtype=np.float64)
    median = float(np.median(ordered))
    deviations = np.abs(ordered - median)
    mad = float(np.median(deviations))
    q25 = float(np.quantile(ordered, 0.25))
    q75 = float(np.quantile(ordered, 0.75))
    epsilon = max(1.0, abs(median)) * 1e-12
    if mad > epsilon:
        scale = 1.4826 * mad
    elif q75 - q25 > epsilon:
        scale = (q75 - q25) / 1.349
    else:
        scale = 0.0
    return RobustFeatureStats(
        median=median,
        mad=mad,
        scale=scale,
        q25=q25,
        q75=q75,
        unit=unit,
        coverage=coverage,
        constant=scale == 0.0,
    )


def _robust_score(
    definition: AnomalyDetectorDefinition,
    observation: ReferenceRow,
    stats: dict[str, RobustFeatureStats],
    feature_order: tuple[str, ...],
) -> tuple[float, list[dict[str, Any]]]:
    transformed, _ = transform_features(definition, observation)
    spec_by_score = {item.score_key: item for item in definition.features}
    deviations: list[tuple[float, dict[str, Any]]] = []
    score_cap = float(
        definition.fit_parameters.get(
            "maximum_score", definition.fit_parameters.get("maximum_descriptive_deviation", 8.0)
        )
    )
    for key in feature_order:
        item_stats = stats.get(key)
        value = transformed.get(key)
        if item_stats is None or value is None or item_stats.constant:
            continue
        signed = (value - item_stats.median) / item_stats.scale
        direction = spec_by_score[key].direction
        if direction is DeviationDirection.HIGH:
            magnitude = max(0.0, signed)
        elif direction is DeviationDirection.LOW:
            magnitude = max(0.0, -signed)
        else:
            magnitude = abs(signed)
        bounded = min(score_cap, magnitude)
        deviations.append(
            (
                bounded,
                {
                    "feature_key": spec_by_score[key].key,
                    "score_feature_key": key,
                    "unit": spec_by_score[key].unit,
                    "observed": value,
                    "reference_median": item_stats.median,
                    "reference_q25": item_stats.q25,
                    "reference_q75": item_stats.q75,
                    "signed_robust_deviation": signed,
                    "normalized_deviation": bounded,
                    "interpretation": "associated statistical deviation, not root cause",
                },
            )
        )
    deviations.sort(key=lambda item: (-item[0], item[1]["score_feature_key"]))
    return (deviations[0][0] if deviations else 0.0), [item[1] for item in deviations]


def _forest_matrix(
    rows: list[dict[str, float | None]],
    feature_order: tuple[str, ...],
    optional_features: tuple[str, ...],
    missing_indicators: tuple[str, ...],
    medians: dict[str, float],
    centers: dict[str, float],
    scales: dict[str, float],
) -> np.ndarray:
    matrix = np.empty((len(rows), len(feature_order) + len(missing_indicators)), dtype=np.float64)
    optional = set(optional_features)
    for row_index, row in enumerate(rows):
        for column, key in enumerate(feature_order):
            raw = row.get(key)
            if raw is None and key not in optional:
                raise DetectorFitError(
                    AnomalyReason.REQUIRED_FEATURE_MISSING,
                    f"required feature {key} is missing",
                )
            value = medians[key] if raw is None else float(raw)
            matrix[row_index, column] = (value - centers[key]) / scales[key]
        offset = len(feature_order)
        for indicator_index, key in enumerate(missing_indicators):
            matrix[row_index, offset + indicator_index] = float(row.get(key) is None)
    if not np.isfinite(matrix).all():
        raise DetectorFitError(AnomalyReason.INVALID_FEATURE_VALUE, "model matrix is non-finite")
    return matrix


def _summary(scores: np.ndarray) -> dict[str, float]:
    if len(scores) == 0:
        return {"count": 0.0, "min": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0}
    return {
        "count": float(len(scores)),
        "min": float(np.min(scores)),
        "median": float(np.median(scores)),
        "p95": float(np.quantile(scores, 0.95)),
        "max": float(np.max(scores)),
    }


def _observed_values(
    rows: list[dict[str, float | None]],
    key: str,
) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if value is not None:
            values.append(float(value))
    return values


def _coverage(definition: AnomalyDetectorDefinition, observation: ReferenceRow) -> float:
    transformed, _ = transform_features(definition, observation)
    present_count = sum(value is not None for value in transformed.values())
    return present_count / max(1, len(definition.features))


def _abstention(
    status: AnomalyStatus,
    reason: AnomalyReason,
    coverage: float,
    observation: ReferenceRow,
    *,
    threshold: float | None = None,
    observed: tuple[str, ...] = (),
    absent: tuple[str, ...] = (),
) -> AnomalyFindingResult:
    if not observed and not absent:
        observed = tuple(
            key for key, value in observation.features.items() if value.value is not None
        )[:MAX_SCORE_FEATURES]
    return AnomalyFindingResult(
        status=status,
        score=None,
        threshold=threshold,
        coverage=coverage,
        observed_features=observed,
        absent_features=absent,
        contributions=(),
        reasons=(reason,),
    )


MAX_SCORE_FEATURES = 8
