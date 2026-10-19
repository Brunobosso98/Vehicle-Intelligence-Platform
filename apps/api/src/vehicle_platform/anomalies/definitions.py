from __future__ import annotations

from collections.abc import Iterable

from vehicle_platform.anomalies.domain import (
    AnomalyDetectorDefinition,
    AnomalyFamily,
    DetectorFeatureSpec,
    DetectorLifecycle,
    DetectorMethod,
    DeviationDirection,
    SourceRole,
)
from vehicle_platform.features.registry import DEFAULT_REGISTRY

SCORING_VERSION = "phase9c-score-v1"
FEATURE_SET_VERSION = "phase9a-pull-v2"
SUPPORTED_ROLES = (
    SourceRole.SYNTHETIC,
    SourceRole.REAL_VEHICLE,
    SourceRole.IMPORTED,
    SourceRole.IMPORTED_FIXTURE,
)

_FAMILY_FEATURES: dict[
    AnomalyFamily, tuple[tuple[str, bool, DeviationDirection, str, str | None], ...]
] = {
    AnomalyFamily.THERMAL: (
        (
            "thermal.iat_start",
            False,
            DeviationDirection.BOTH,
            "difference",
            "thermal.pre_pull_iat_k",
        ),
        ("thermal.iat_delta_k", True, DeviationDirection.BOTH, "identity", None),
        ("thermal.iat_slope_k_per_s", False, DeviationDirection.BOTH, "identity", None),
        ("thermal.iat_recovery_delta_k", False, DeviationDirection.BOTH, "identity", None),
    ),
    AnomalyFamily.BOOST_AIR: (
        ("boost_air.pressure_mean", True, DeviationDirection.BOTH, "identity", None),
        ("boost_air.pressure_max", True, DeviationDirection.BOTH, "identity", None),
        (
            "boost_air.pressure_rise_rate_pa_per_s",
            False,
            DeviationDirection.BOTH,
            "identity",
            None,
        ),
        ("boost_air.pressure_stddev_pa", False, DeviationDirection.BOTH, "identity", None),
    ),
    AnomalyFamily.PERFORMANCE: (
        (
            "performance.rpm_3500_4500_s_per_1000rpm",
            True,
            DeviationDirection.BOTH,
            "identity",
            None,
        ),
        (
            "performance.rpm_2500_3500_s_per_1000rpm",
            False,
            DeviationDirection.BOTH,
            "identity",
            None,
        ),
        (
            "performance.rpm_4500_5500_s_per_1000rpm",
            False,
            DeviationDirection.BOTH,
            "identity",
            None,
        ),
        ("performance.pull_duration_s", False, DeviationDirection.BOTH, "identity", None),
    ),
    AnomalyFamily.FUEL: (
        ("fuel.rail_pressure_min", True, DeviationDirection.BOTH, "identity", None),
        ("fuel.rail_pressure_mean", True, DeviationDirection.BOTH, "identity", None),
        ("fuel.rail_pressure_delta_pa", False, DeviationDirection.BOTH, "identity", None),
        ("fuel.rail_pressure_stddev_pa", False, DeviationDirection.BOTH, "identity", None),
    ),
}


def _feature_spec(
    key: str,
    *,
    required: bool,
    direction: DeviationDirection,
    transform: str,
    context_key: str | None,
) -> DetectorFeatureSpec:
    definition = DEFAULT_REGISTRY.resolve(key)
    if definition.unit is None:
        raise ValueError(f"anomaly feature {key} has no unit")
    context = DEFAULT_REGISTRY.resolve(context_key) if context_key else None
    if context is not None and context.unit != definition.unit:
        raise ValueError(f"anomaly context feature {context_key} has an incompatible unit")
    return DetectorFeatureSpec(
        key=key,
        unit=definition.unit,
        temporal_availability=definition.availability.value,
        required=required,
        direction=direction,
        transform=transform,  # type: ignore[arg-type]
        context_key=context_key,
        context_unit=context.unit if context else None,
        context_temporal_availability=context.availability.value if context else None,
    )


def _feature_keys(family: AnomalyFamily) -> tuple[DetectorFeatureSpec, ...]:
    return tuple(
        _feature_spec(
            key,
            required=required,
            direction=direction,
            transform=transform,
            context_key=context_key,
        )
        for key, required, direction, transform, context_key in _FAMILY_FEATURES[family]
    )


def _required_signals(features: Iterable[DetectorFeatureSpec]) -> tuple[str, ...]:
    keys = {key for feature in features for key in feature.input_keys}
    signals = {
        signal for key in keys for signal in (*DEFAULT_REGISTRY.resolve(key).required_signals,)
    }
    return tuple(sorted(signals))


def _cohort_policy(method: DetectorMethod) -> dict[str, object]:
    return {
        "version": "same-vehicle-effective-configuration-modifications-source-v1",
        "scope": (
            "one vehicle, exact effective configuration, exact active modification set, "
            "exact source type and role"
        ),
        "cross_vehicle_pooling": False,
        "cross_configuration_pooling": False,
        "same_session_reference_rows": False,
        "minimum_reference_rows": 24 if method is DetectorMethod.ISOLATION_FOREST else 12,
        "minimum_independent_sessions": 3,
        "minimum_chronological_span_seconds": 604800,
        "maximum_reference_rows": 10_000,
        "minimum_feature_coverage": 0.8,
    }


def _quality_policy() -> dict[str, object]:
    return {
        "version": "phase9c-quality-v1",
        "minimum_pull_completeness": 0.75,
        "maximum_invalid_observation_count": 0,
        "maximum_duplicate_timestamp_count": 0,
        "minimum_feature_coverage": 0.8,
        "required_feature_quality": "valid",
        "optional_feature_quality": ["valid", "limited"],
        "missing_required_signal": "abstain",
        "invalid_or_missing_is_not_anomaly": True,
    }


def _normalization_policy(method: DetectorMethod) -> dict[str, object]:
    if method is DetectorMethod.ROBUST_MAD:
        return {
            "version": "median-mad-iqr-constant-exclusion-v1",
            "center": "median",
            "scale": (
                "1.4826 * MAD; if MAD is zero use IQR / 1.349; "
                "if both are zero exclude constant feature"
            ),
            "score": "direction-aware absolute robust z-score, capped at 8",
            "aggregation": (
                "maximum eligible per-feature deviation; feature count cannot inflate score"
            ),
            "zero_mad": "IQR fallback, then deterministic constant-feature exclusion",
        }
    return {
        "version": "train-only-median-imputation-robust-scaling-missing-indicators-v1",
        "imputation": "training median for optional features only",
        "missingness": "one indicator for each optional feature with training coverage >= 0.8",
        "scale": "training IQR / 1.349 with unit scale for constant inputs",
        "score_transform": "negative IsolationForest score_samples; larger means more unusual",
        "score_is_probability": False,
        "contributions": (
            "descriptive robust feature comparisons; not a decomposition of forest scores"
        ),
    }


def _threshold_policy(method: DetectorMethod) -> dict[str, object]:
    return {
        "version": "validation-frozen-threshold-v2",
        "initial_candidate_threshold": "95th percentile of training-reference scores",
        "frozen_threshold": "selected from a predeclared validation-only threshold grid",
        "quantile": 0.95,
        "validation_use": "candidate comparison and threshold selection before test access",
        "test_use": "never used for threshold selection",
        "robust_minimum_threshold": 3.5 if method is DetectorMethod.ROBUST_MAD else None,
        "semantics": "relative engineering outlier cutoff, not a probability or defect risk",
        "candidate_selection": [
            "meet clean false-positive and eligible coverage floors",
            "higher validation injection recall and precision when both pass",
            "prefer robust transparent baseline on a tie",
            "test partition remains untouched until choices are frozen",
        ],
    }


def _make_definition(family: AnomalyFamily, method: DetectorMethod) -> AnomalyDetectorDefinition:
    if family not in _FAMILY_FEATURES:
        raise ValueError("multivariate aggregation is derived from eligible family scores")
    features = _feature_keys(family)
    return AnomalyDetectorDefinition(
        key=f"phase9c.{family.value}.{method.value}",
        version="2.0.0" if family is AnomalyFamily.BOOST_AIR else "1.0.0",
        family=family,
        method=method,
        intent=(
            f"Detect relative {family.value} feature deviations after a completed pull; "
            "this is descriptive engineering evidence, not diagnosis."
        ),
        features=features,
        required_signal_keys=_required_signals(features),
        supported_source_roles=SUPPORTED_ROLES,
        cohort_policy=_cohort_policy(method),
        quality_policy=_quality_policy(),
        seed=9142,
        fit_parameters=(
            {
                "training_reference_quantile": 0.95,
                "maximum_score": 8.0,
                "minimum_feature_coverage": 0.8,
                "constant_feature_epsilon_relative": 1e-12,
            }
            if method is DetectorMethod.ROBUST_MAD
            else {
                "n_estimators": 128,
                "max_samples": 256,
                "max_features": 1.0,
                "maximum_descriptive_deviation": 8.0,
                "contamination": "auto",
                "n_jobs": 1,
                "training_reference_quantile": 0.95,
                "minimum_feature_coverage": 0.8,
                "minimum_training_rows": 24,
                "maximum_score_rows": 1_000,
            }
        ),
        normalization_policy=_normalization_policy(method),
        threshold_policy=_threshold_policy(method),
        scoring_version=SCORING_VERSION,
        lifecycle_status=DetectorLifecycle.CANDIDATE,
    )


DEFAULT_DETECTORS = tuple(
    _make_definition(family, method)
    for family in (
        AnomalyFamily.THERMAL,
        AnomalyFamily.BOOST_AIR,
        AnomalyFamily.PERFORMANCE,
        AnomalyFamily.FUEL,
    )
    for method in (DetectorMethod.ROBUST_MAD, DetectorMethod.ISOLATION_FOREST)
)
_DETECTOR_BY_IDENTITY = {(item.family, item.method): item for item in DEFAULT_DETECTORS}


def detector_definition(
    family: AnomalyFamily | str, method: DetectorMethod | str
) -> AnomalyDetectorDefinition:
    try:
        family_value = family if isinstance(family, AnomalyFamily) else AnomalyFamily(family)
        method_value = method if isinstance(method, DetectorMethod) else DetectorMethod(method)
    except ValueError as error:
        raise ValueError("unknown anomaly family or method") from error
    try:
        return _DETECTOR_BY_IDENTITY[(family_value, method_value)]
    except KeyError as error:
        raise ValueError("multivariate score is derived and has no fitted detector") from error
