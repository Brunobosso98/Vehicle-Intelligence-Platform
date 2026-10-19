from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from vehicle_platform.anomalies.domain import DetectorMethod


@dataclass(frozen=True)
class ThresholdCandidate:
    threshold: float
    metrics: dict[str, Any]
    accepted: bool


@dataclass(frozen=True)
class MethodCandidate:
    method: DetectorMethod
    threshold: float
    validation_metrics: dict[str, Any]


def classification_metrics(
    scores: tuple[float | None, ...],
    labels: tuple[bool | None, ...],
    threshold: float,
) -> dict[str, Any]:
    if len(scores) != len(labels):
        raise ValueError("score and oracle label counts differ")
    if not math.isfinite(threshold):
        raise ValueError("threshold must be finite")
    tp = fp = tn = fn = abstained_positive = abstained_negative = 0
    for score, label in zip(scores, labels, strict=True):
        if score is None or label is None or not math.isfinite(score):
            if label is True:
                abstained_positive += 1
            elif label is False:
                abstained_negative += 1
            continue
        predicted = score > threshold
        if label and predicted:
            tp += 1
        elif label:
            fn += 1
        elif predicted:
            fp += 1
        else:
            tn += 1
    scored = tp + fp + tn + fn
    positive_support = tp + fn + abstained_positive
    negative_support = fp + tn + abstained_negative
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / positive_support if positive_support else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "support": len(scores),
        "scored": scored,
        "abstained": len(scores) - scored,
        "abstained_positive": abstained_positive,
        "abstained_negative": abstained_negative,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "positive_support": positive_support,
        "negative_support": negative_support,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fp / negative_support if negative_support else None,
        "anomaly_coverage": scored / len(scores) if scores else 0.0,
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "metric_state": (
            "DEFINED" if positive_support and negative_support else "INSUFFICIENT_SUPPORT"
        ),
    }


def select_validation_threshold(
    *,
    scores: tuple[float | None, ...],
    labels: tuple[bool | None, ...],
    initial_threshold: float,
    maximum_clean_false_positive_rate: float,
    minimum_coverage: float,
    minimum_injection_recall: float,
) -> ThresholdCandidate:
    """Select only over the supplied validation fold; never accepts test labels."""
    if not 0 <= maximum_clean_false_positive_rate <= 1:
        raise ValueError("false-positive-rate floor must be between zero and one")
    if not 0 <= minimum_coverage <= 1 or not 0 <= minimum_injection_recall <= 1:
        raise ValueError("coverage and recall floors must be between zero and one")
    thresholds = {float(initial_threshold)}
    thresholds.update(
        float(score) for score in scores if score is not None and math.isfinite(score)
    )
    candidates: list[ThresholdCandidate] = []
    for threshold in sorted(thresholds):
        metrics = classification_metrics(scores, labels, threshold)
        fpr = metrics["false_positive_rate"]
        recall = metrics["recall"]
        accepted = (
            fpr is not None
            and fpr <= maximum_clean_false_positive_rate
            and metrics["anomaly_coverage"] >= minimum_coverage
            and recall is not None
            and recall >= minimum_injection_recall
        )
        candidates.append(ThresholdCandidate(threshold, metrics, accepted))
    eligible = [item for item in candidates if item.accepted]
    pool = eligible or candidates
    selected = max(
        pool,
        key=lambda item: (
            item.metrics["recall"] if item.metrics["recall"] is not None else -1.0,
            item.metrics["precision"] if item.metrics["precision"] is not None else -1.0,
            -item.metrics["false_positive_rate"]
            if item.metrics["false_positive_rate"] is not None
            else -1.0,
            item.threshold,
        ),
    )
    return selected


def select_detector_method(
    candidates: tuple[MethodCandidate, ...],
    *,
    maximum_clean_false_positive_rate: float,
    minimum_coverage: float,
) -> MethodCandidate:
    if not candidates:
        raise ValueError("at least one validation candidate is required")

    def meets_floors(candidate: MethodCandidate) -> bool:
        metrics = candidate.validation_metrics
        fpr = metrics.get("false_positive_rate")
        return (
            fpr is not None
            and float(fpr) <= maximum_clean_false_positive_rate
            and float(metrics.get("anomaly_coverage", 0.0)) >= minimum_coverage
        )

    passing = [candidate for candidate in candidates if meets_floors(candidate)]
    pool = passing or list(candidates)
    return max(
        pool,
        key=lambda candidate: (
            candidate.validation_metrics.get("recall")
            if candidate.validation_metrics.get("recall") is not None
            else -1.0,
            candidate.validation_metrics.get("precision")
            if candidate.validation_metrics.get("precision") is not None
            else -1.0,
            candidate.method is DetectorMethod.ROBUST_MAD,
        ),
    )
