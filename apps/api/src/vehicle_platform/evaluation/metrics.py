from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import Any, cast

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from vehicle_platform.evaluation.contracts import (
    ConfidenceInterval,
    MetricDefinition,
    MetricResult,
    MetricStatus,
    ReliabilityBin,
    SourceRole,
)

LOG_LOSS_EPSILON = 1e-6
BOOTSTRAP_MINIMUM_CLUSTERS = 20


def _validate_binary_rows(
    scores: Sequence[float], labels: Sequence[int | bool], row_ids: Sequence[str] | None
) -> tuple[np.ndarray, np.ndarray]:
    if len(scores) != len(labels):
        raise ValueError("scores and labels must have identical length")
    if row_ids is not None and (len(row_ids) != len(scores) or len(set(row_ids)) != len(row_ids)):
        raise ValueError("metric rows require unique, aligned example IDs")
    score_array = np.asarray(scores, dtype=np.float64)
    if any(
        not isinstance(label, (bool, int, np.integer)) or int(label) not in (0, 1)
        for label in labels
    ):
        raise ValueError("binary labels must be exactly zero or one")
    label_array = np.asarray(labels, dtype=np.int8)
    if not np.isfinite(score_array).all():
        raise ValueError("metric scores must be finite")
    if ((score_array < 0) | (score_array > 1)).any():
        raise ValueError("supervised scores must lie in [0,1]")
    # Inputs were constrained to binary bool/int values before the int8 conversion.
    if not np.isin(label_array, (0, 1)).all():  # pragma: no branch
        raise ValueError("binary labels must be zero or one")
    return score_array, label_array


def _brier(scores: np.ndarray, labels: np.ndarray) -> float:
    return float(np.mean(np.square(scores - labels)))


def _log_loss(scores: np.ndarray, labels: np.ndarray) -> float:
    clipped = np.clip(scores, LOG_LOSS_EPSILON, 1.0 - LOG_LOSS_EPSILON)
    losses = -(labels * np.log(clipped) + (1 - labels) * np.log1p(-clipped))
    return float(np.mean(losses))


def _ece(scores: np.ndarray, labels: np.ndarray, bins: int) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    indices = np.minimum(np.searchsorted(edges, scores, side="right") - 1, bins - 1)
    indices = np.maximum(indices, 0)
    total = len(scores)
    return float(
        sum(
            (int(np.sum(indices == index)) / total)
            * abs(
                float(np.mean(labels[indices == index])) - float(np.mean(scores[indices == index]))
            )
            for index in range(bins)
            if np.any(indices == index)
        )
    )


def _metric_interval(
    metric: Callable[[np.ndarray, np.ndarray], float],
    scores: np.ndarray,
    labels: np.ndarray,
    clusters: Sequence[str] | None,
    *,
    seed: int,
    resamples: int,
) -> tuple[ConfidenceInterval, float | None]:
    if clusters is None or len(clusters) != len(scores):
        return (
            ConfidenceInterval(
                lower=None,
                upper=None,
                method="not_computed",
                unit="independent_session",
                cluster_count=0,
                resamples=0,
                status=MetricStatus.INSUFFICIENT_SUPPORT,
            ),
            None,
        )
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, cluster in enumerate(clusters):
        if not cluster:
            raise ValueError("bootstrap cluster identities must be nonempty")
        grouped[cluster].append(index)
    cluster_ids = tuple(sorted(grouped))
    if len(cluster_ids) < BOOTSTRAP_MINIMUM_CLUSTERS or resamples < 20:
        return (
            ConfidenceInterval(
                lower=None,
                upper=None,
                method="session_cluster_bootstrap",
                unit="independent_session",
                cluster_count=len(cluster_ids),
                resamples=0,
                status=MetricStatus.NONINDEPENDENT_DESCRIPTIVE,
            ),
            None,
        )
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(resamples):
        selected = rng.choice(cluster_ids, size=len(cluster_ids), replace=True)
        indices = np.fromiter(
            (row_index for cluster_id in selected for row_index in grouped[str(cluster_id)]),
            dtype=np.int64,
        )
        try:
            value = metric(scores[indices], labels[indices])
        except (ValueError, ZeroDivisionError, FloatingPointError):
            continue
        if math.isfinite(value):
            values.append(value)
    if len(values) < max(20, int(resamples * 0.8)):
        return (
            ConfidenceInterval(
                lower=None,
                upper=None,
                method="session_cluster_bootstrap",
                unit="independent_session",
                cluster_count=len(cluster_ids),
                resamples=len(values),
                status=MetricStatus.INSUFFICIENT_SUPPORT,
            ),
            None,
        )
    lower, upper = np.quantile(np.asarray(values), (0.025, 0.975))
    return (
        ConfidenceInterval(
            lower=float(lower),
            upper=float(upper),
            method="session_cluster_percentile_bootstrap",
            unit="independent_session",
            cluster_count=len(cluster_ids),
            resamples=len(values),
            status=MetricStatus.DEFINED,
        ),
        None,
    )


def _result(
    *,
    name: str,
    value: float | None,
    reason: str | None,
    denominator: int,
    positives: int,
    negatives: int,
    excluded: int,
    source_role: SourceRole,
    fold_id: str,
    interval: ConfidenceInterval,
    unit: str = "ratio",
    formula: str,
    status: MetricStatus | None = None,
) -> MetricResult:
    result_status = status or (
        MetricStatus.DEFINED if value is not None else MetricStatus.UNDEFINED
    )
    return MetricResult(
        definition=MetricDefinition(
            name=name,
            version="phase9g-metric-v1",
            unit=unit,
            formula=formula,
            denominator_definition=(
                "eligible scored examples; abstained and unlabeled rows excluded"
            ),
            independence_unit="session",
        ),
        value=value,
        status=result_status,
        undefined_reason=reason,
        denominator=denominator,
        positive_support=positives,
        negative_support=negatives,
        excluded_or_abstained=excluded,
        source_role=source_role,
        fold_id=fold_id,
        uncertainty=interval,
    )


def _undefined_interval() -> ConfidenceInterval:
    return ConfidenceInterval(
        lower=None,
        upper=None,
        method="undefined_or_insufficient_support",
        unit="independent_session",
        cluster_count=0,
        resamples=0,
        status=MetricStatus.INSUFFICIENT_SUPPORT,
    )


def reliability_bins(
    scores: Sequence[float],
    labels: Sequence[int | bool],
    *,
    bins: int = 5,
    method: str = "fixed_width",
    clusters: Sequence[str] | None = None,
    seed: int = 9142,
    bootstrap_resamples: int = 200,
) -> tuple[ReliabilityBin, ...]:
    score_array, label_array = _validate_binary_rows(scores, labels, None)
    if not 2 <= bins <= 10:
        raise ValueError("reliability bins must be between two and ten")
    if method == "fixed_width":
        edges = np.linspace(0.0, 1.0, bins + 1)
    elif method == "quantile":
        if len(score_array) < bins * 10:
            raise ValueError("quantile reliability bins need at least ten rows per requested bin")
        edges = np.unique(np.quantile(score_array, np.linspace(0.0, 1.0, bins + 1)))
        if len(edges) < 3:
            raise ValueError("quantile reliability bins require at least two distinct score edges")
        edges[0] = 0.0
        edges[-1] = 1.0
    else:
        raise ValueError("unknown reliability bin method")
    assignments = np.minimum(np.searchsorted(edges, score_array, side="right") - 1, len(edges) - 2)
    assignments = np.maximum(assignments, 0)
    output: list[ReliabilityBin] = []
    for index, (lower, upper) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
        selected = assignments == index
        count = int(np.sum(selected))
        if count == 0:
            output.append(
                ReliabilityBin(
                    lower=float(lower),
                    upper=float(upper),
                    count=0,
                    mean_score=None,
                    observed_positive_rate=None,
                    weighted_absolute_error=None,
                    rate_interval=_undefined_interval(),
                )
            )
            continue
        mean_score = float(np.mean(score_array[selected]))
        positive_rate = float(np.mean(label_array[selected]))
        rate_interval = _cluster_interval_unavailable(0)
        if clusters is not None:
            selected_clusters = [
                cluster for cluster, keep in zip(clusters, selected, strict=True) if keep
            ]
            cluster_ci, _ = _metric_interval(
                lambda _s, y: float(np.mean(y)),
                score_array[selected],
                label_array[selected],
                selected_clusters,
                seed=seed + index,
                resamples=bootstrap_resamples,
            )
            if cluster_ci.lower is not None and cluster_ci.upper is not None:
                rate_interval = cluster_ci
            # A selected bin has at least one aligned, validated session identity.
            elif cluster_ci.cluster_count:  # pragma: no branch
                rate_interval = _cluster_interval_unavailable(cluster_ci.cluster_count)
        output.append(
            ReliabilityBin(
                lower=float(lower),
                upper=float(upper),
                count=count,
                mean_score=mean_score,
                observed_positive_rate=positive_rate,
                weighted_absolute_error=(count / len(score_array))
                * abs(positive_rate - mean_score),
                rate_interval=rate_interval,
            )
        )
    return tuple(output)


def _cluster_interval_unavailable(cluster_count: int) -> ConfidenceInterval:
    return ConfidenceInterval(
        lower=None,
        upper=None,
        method="clustered_interval_not_computed_below_20_sessions",
        unit="independent_session",
        cluster_count=cluster_count,
        resamples=0,
        status=(
            MetricStatus.NONINDEPENDENT_DESCRIPTIVE
            if cluster_count
            else MetricStatus.INSUFFICIENT_SUPPORT
        ),
    )


def binary_metrics(
    scores: Sequence[float | None],
    labels: Sequence[int | bool | None],
    *,
    threshold: float,
    source_role: SourceRole,
    fold_id: str,
    row_ids: Sequence[str],
    clusters: Sequence[str],
    bin_count: int = 5,
    bootstrap_resamples: int = 200,
    seed: int = 9142,
) -> dict[str, Any]:
    if len(scores) != len(labels) or len(row_ids) != len(scores) or len(clusters) != len(scores):
        raise ValueError("scores, labels, row IDs and clusters must be aligned")
    if len(set(row_ids)) != len(row_ids):
        raise ValueError("metric example IDs must be unique")
    if not 0 < threshold < 1:
        raise ValueError("decision threshold must be strictly between zero and one")
    for label in labels:
        if label is not None:
            _normalize_binary_label(label)
    selected_indices = [
        index
        for index, (score, label) in enumerate(zip(scores, labels, strict=True))
        if score is not None and label is not None
    ]
    abstained = len(scores) - len(selected_indices)
    selected_scores = [
        float(cast(float, scores[index])) for index in selected_indices if scores[index] is not None
    ]
    selected_labels = [
        _normalize_binary_label(cast(int | bool, labels[index]))
        for index in selected_indices
        if labels[index] is not None
    ]
    selected_ids = [row_ids[index] for index in selected_indices]
    selected_clusters = [clusters[index] for index in selected_indices]
    score_array, label_array = _validate_binary_rows(selected_scores, selected_labels, selected_ids)
    positives = int(np.sum(label_array))
    negatives = len(label_array) - positives

    metric_functions: dict[str, tuple[Callable[[np.ndarray, np.ndarray], float], str, str]] = {
        "brier_score": (_brier, "ratio", "mean((p-y)^2)"),
        "log_loss": (
            _log_loss,
            "nats",
            f"mean(-y*log(clip(p,{LOG_LOSS_EPSILON}))-(1-y)*log(1-clip(p)))",
        ),
        "ece": (
            lambda p, y: _ece(p, y, bin_count),
            "ratio",
            "sum_b(n_b/n*abs(mean(y_b)-mean(p_b)))",
        ),
    }
    output: dict[str, Any] = {}
    for metric_index, (name, (function, unit, formula)) in enumerate(metric_functions.items()):
        if not len(score_array):
            output[name] = _result(
                name=name,
                value=None,
                reason="NO_SCORED_LABELED_EXAMPLES",
                denominator=0,
                positives=0,
                negatives=0,
                excluded=abstained,
                source_role=source_role,
                fold_id=fold_id,
                interval=_undefined_interval(),
                unit=unit,
                formula=formula,
            ).model_dump(mode="json")
            continue
        ci, _ = _metric_interval(
            function,
            score_array,
            label_array,
            selected_clusters,
            seed=seed + metric_index,
            resamples=bootstrap_resamples,
        )
        status = ci.status if ci.status is MetricStatus.NONINDEPENDENT_DESCRIPTIVE else None
        output[name] = _result(
            name=name,
            value=function(score_array, label_array),
            reason=None,
            denominator=len(score_array),
            positives=positives,
            negatives=negatives,
            excluded=abstained,
            source_role=source_role,
            fold_id=fold_id,
            interval=ci,
            unit=unit,
            formula=formula,
            status=status,
        ).model_dump(mode="json")

    bins = reliability_bins(
        selected_scores,
        selected_labels,
        bins=bin_count,
        clusters=selected_clusters,
        seed=seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    auroc: MetricResult | None
    average_precision: MetricResult | None
    if positives == 0 or negatives == 0:
        auroc = _result(
            name="auroc",
            value=None,
            reason="SINGLE_CLASS_SUPPORT",
            denominator=len(score_array),
            positives=positives,
            negatives=negatives,
            excluded=abstained,
            source_role=source_role,
            fold_id=fold_id,
            interval=_undefined_interval(),
            formula="rank-based ROC area over eligible labeled examples",
        )
        average_precision = _result(
            name="average_precision",
            value=None,
            reason="SINGLE_CLASS_SUPPORT",
            denominator=len(score_array),
            positives=positives,
            negatives=negatives,
            excluded=abstained,
            source_role=source_role,
            fold_id=fold_id,
            interval=_undefined_interval(),
            formula="mean precision at each positive rank over eligible labeled examples",
        )
    # Reaching this branch requires both positive and negative support.
    elif len(score_array):  # pragma: no branch
        auroc_ci, _ = _metric_interval(
            lambda p, y: float(roc_auc_score(y, p)),
            score_array,
            label_array,
            selected_clusters,
            seed=seed + 20,
            resamples=bootstrap_resamples,
        )
        ap_ci, _ = _metric_interval(
            lambda p, y: float(average_precision_score(y, p)),
            score_array,
            label_array,
            selected_clusters,
            seed=seed + 21,
            resamples=bootstrap_resamples,
        )
        auroc = _result(
            name="auroc",
            value=float(roc_auc_score(label_array, score_array)),
            reason=None,
            denominator=len(score_array),
            positives=positives,
            negatives=negatives,
            excluded=abstained,
            source_role=source_role,
            fold_id=fold_id,
            interval=auroc_ci,
            formula="rank-based ROC area over eligible labeled examples",
        )
        average_precision = _result(
            name="average_precision",
            value=float(average_precision_score(label_array, score_array)),
            reason=None,
            denominator=len(score_array),
            positives=positives,
            negatives=negatives,
            excluded=abstained,
            source_role=source_role,
            fold_id=fold_id,
            interval=ap_ci,
            formula="mean precision at each positive rank over eligible labeled examples",
        )
    else:
        auroc = average_precision = None

    # AUROC and AP are created together or both omitted for an empty dataset.
    if auroc is not None and average_precision is not None:  # pragma: no branch
        output["auroc"] = auroc.model_dump(mode="json")
        output["average_precision"] = average_precision.model_dump(mode="json")
    output["reliability_bins"] = [item.model_dump(mode="json") for item in bins]
    output["ece_definition"] = {
        "binning": "fixed_width",
        "bin_count": bin_count,
        "edges": [index / bin_count for index in range(bin_count + 1)],
        "formula": "sum_b(n_b/n*abs(observed_positive_rate_b-mean_score_b))",
        "empty_bins": "count 0; all statistics remain null",
    }
    output["decision"] = _threshold_metrics(label_array, score_array, threshold)
    output["support"] = {
        "eligible_requests": len(scores),
        "scored_labeled": len(score_array),
        "positive": positives,
        "negative": negatives,
        "abstained_or_unlabeled": abstained,
        "coverage": len(score_array) / len(scores) if scores else 0.0,
        "independent_sessions": len(set(selected_clusters)),
    }
    output["log_loss_policy"] = {
        "epsilon": LOG_LOSS_EPSILON,
        "reason": (
            "finite numerical stability only; unclipped scores are preserved in reliability output"
        ),
    }
    return output


def _normalize_binary_label(value: int | bool) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, np.integer)) and int(value) in (0, 1):
        return int(value)
    raise ValueError("binary labels must be exactly zero or one")


def _threshold_metrics(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    predictions = scores >= threshold
    true_positive = int(np.sum(predictions & (labels == 1)))
    false_positive = int(np.sum(predictions & (labels == 0)))
    false_negative = int(np.sum(~predictions & (labels == 1)))
    true_negative = int(np.sum(~predictions & (labels == 0)))
    total = len(labels)
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else None
    )
    recall = (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else None
    )
    specificity = (
        true_negative / (true_negative + false_positive) if true_negative + false_positive else None
    )
    balanced_accuracy = (
        (recall + specificity) / 2 if recall is not None and specificity is not None else None
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else 0.0
        if precision == 0 and recall == 0
        else None
    )
    return {
        "threshold": threshold,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "support": total,
        "positive_support": int(np.sum(labels)),
        "negative_support": total - int(np.sum(labels)),
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "balanced_accuracy": balanced_accuracy,
        "false_positive_rate": false_positive / (false_positive + true_negative)
        if false_positive + true_negative
        else None,
        "false_negative_rate": false_negative / (false_negative + true_positive)
        if false_negative + true_positive
        else None,
        "base_rate": float(np.mean(labels)) if total else None,
    }


def anomaly_alarm_metrics(
    scores: Sequence[float | None],
    alarms: Sequence[bool | None],
    eligible: Sequence[bool],
    *,
    clean: Sequence[bool],
    clusters: Sequence[str],
) -> dict[str, Any]:
    lengths = {len(scores), len(alarms), len(eligible), len(clean), len(clusters)}
    if len(lengths) != 1:
        raise ValueError("anomaly observations and denominators must align")
    eligible_count = sum(eligible)
    scored_indices = [
        index
        for index in range(len(scores))
        if eligible[index] and scores[index] is not None and alarms[index] is not None
    ]
    clean_indices = [index for index in scored_indices if clean[index]]
    alarm_count = sum(bool(alarms[index]) for index in scored_indices)
    clean_alarm_count = sum(bool(alarms[index]) for index in clean_indices)
    sessions = {clusters[index] for index in scored_indices}
    alarm_sessions = {clusters[index] for index in scored_indices if bool(alarms[index])}
    return {
        "eligible": eligible_count,
        "scored": len(scored_indices),
        "abstained": eligible_count - len(scored_indices),
        "coverage": len(scored_indices) / eligible_count if eligible_count else 0.0,
        "alarm_count": alarm_count,
        "alarm_rate_per_eligible": alarm_count / eligible_count if eligible_count else None,
        "alarm_rate_per_scored": alarm_count / len(scored_indices) if scored_indices else None,
        "independent_sessions_scored": len(sessions),
        "sessions_with_alarm": len(alarm_sessions),
        "alarm_burden_per_scored_session": len(alarm_sessions) / len(sessions)
        if sessions
        else None,
        "clean_eligible": sum(eligible[index] for index in range(len(clean)) if clean[index]),
        "clean_scored": len(clean_indices),
        "clean_abstained": sum(eligible[index] and clean[index] for index in range(len(clean)))
        - len(clean_indices),
        "clean_false_alarm_count": clean_alarm_count,
        "clean_fpr_per_scored": clean_alarm_count / len(clean_indices) if clean_indices else None,
        "clean_fpr_per_eligible": clean_alarm_count
        / sum(eligible[index] and clean[index] for index in range(len(clean)))
        if any(eligible[index] and clean[index] for index in range(len(clean)))
        else None,
    }
