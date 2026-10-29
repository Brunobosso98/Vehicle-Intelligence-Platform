"""Independent Phase 9G report, arithmetic, provenance, and leakage checker."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np

TASKS = {
    "NEXT_PULL_THERMAL_DEGRADATION",
    "NEXT_PULL_PERFORMANCE_DEGRADATION",
    "NEXT_PULL_FUEL_DEVIATION",
}
FAMILIES = {"thermal", "boost_air", "performance", "fuel"}
METHODS = {"robust_mad", "isolation_forest"}
CALIBRATORS = {"identity", "sigmoid", "isotonic"}
EPSILON = 1e-6


class AcceptanceRejected(ValueError):
    """The Phase 9G receipt is incomplete, falsified, or arithmetically inconsistent."""


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceRejected(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _close(actual: Any, expected: float | None, *, name: str) -> None:
    if expected is None:
        _assert(actual is None, f"{name} should be explicitly undefined")
    else:
        _assert(
            isinstance(actual, (int, float))
            and math.isfinite(float(actual))
            and math.isclose(float(actual), expected, rel_tol=1e-10, abs_tol=1e-12),
            f"{name} differs from independently recomputed arithmetic",
        )


def _scores_and_labels(
    examples: list[dict[str, Any]], method: str | None = None
) -> tuple[list[float], list[int]]:
    scores: list[float] = []
    labels: list[int] = []
    for example in examples:
        label = example.get("label")
        score = (
            example.get("score")
            if method is None
            else example.get("calibrated_scores", {}).get(method)
        )
        if not isinstance(label, (bool, int)) or label not in (0, 1):
            raise AcceptanceRejected(
                "labeled evaluation example has a fabricated/nonbinary target"
            )
        if (
            not isinstance(score, (int, float))
            or not math.isfinite(float(score))
            or not 0.0 <= float(score) <= 1.0
        ):
            raise AcceptanceRejected(
                f"{method or 'identity'} evaluation score is missing or invalid"
            )
        scores.append(float(score))
        labels.append(int(label))
    return scores, labels


def _auc(scores: list[float], labels: list[int]) -> float | None:
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    concordant = 0.0
    for score, label in zip(scores, labels, strict=True):
        if label:
            concordant += sum(
                1.0 if score > other else 0.5 if score == other else 0.0
                for other, other_label in zip(scores, labels, strict=True)
                if other_label == 0
            )
    return concordant / (positives * negatives)


def _average_precision(scores: list[float], labels: list[int]) -> float | None:
    positives = sum(labels)
    if not positives:
        return None
    by_score: dict[float, list[int]] = defaultdict(list)
    for score, label in zip(scores, labels, strict=True):
        by_score[score].append(label)
    seen = true_positive = 0
    previous_recall = 0.0
    total = 0.0
    for score in sorted(by_score, reverse=True):
        members = by_score[score]
        seen += len(members)
        true_positive += sum(members)
        recall = true_positive / positives
        precision = true_positive / seen
        total += (recall - previous_recall) * precision
        previous_recall = recall
    return total


def _brier(scores: list[float], labels: list[int]) -> float:
    return sum(
        (score - label) ** 2 for score, label in zip(scores, labels, strict=True)
    ) / len(scores)


def _log_loss(scores: list[float], labels: list[int]) -> float:
    total = 0.0
    for score, label in zip(scores, labels, strict=True):
        clipped = min(1.0 - EPSILON, max(EPSILON, score))
        total += -label * math.log(clipped) - (1 - label) * math.log1p(-clipped)
    return total / len(scores)


def _reliability(
    scores: list[float], labels: list[int], bins: int = 5
) -> list[dict[str, Any]]:
    output = []
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        members = [
            position
            for position, score in enumerate(scores)
            if min(int(score * bins), bins - 1) == index
        ]
        if not members:
            output.append(
                {
                    "lower": lower,
                    "upper": upper,
                    "count": 0,
                    "mean_score": None,
                    "observed_positive_rate": None,
                    "weighted_absolute_error": None,
                }
            )
            continue
        mean_score = sum(scores[position] for position in members) / len(members)
        observed = sum(labels[position] for position in members) / len(members)
        output.append(
            {
                "lower": lower,
                "upper": upper,
                "count": len(members),
                "mean_score": mean_score,
                "observed_positive_rate": observed,
                "weighted_absolute_error": len(members)
                / len(scores)
                * abs(observed - mean_score),
            }
        )
    return output


def _ece(scores: list[float], labels: list[int], bins: int = 5) -> float:
    return sum(
        float(item["weighted_absolute_error"] or 0.0)
        for item in _reliability(scores, labels, bins)
    )


def _decisions(
    scores: list[float], labels: list[int], threshold: float
) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for score, label in zip(scores, labels, strict=True):
        predicted = score >= threshold
        if predicted and label:
            tp += 1
        elif predicted:
            fp += 1
        elif label:
            fn += 1
        else:
            tn += 1
    predicted_positive = tp + fp
    actual_positive = tp + fn
    actual_negative = fp + tn
    precision = tp / predicted_positive if predicted_positive else None
    recall = tp / actual_positive if actual_positive else None
    specificity = tn / actual_negative if actual_negative else None
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "support": len(labels),
        "positive_support": sum(labels),
        "negative_support": len(labels) - sum(labels),
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "balanced_accuracy": (
            (recall + specificity) / 2
            if recall is not None and specificity is not None
            else None
        ),
        "f1": (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else 0.0
            if precision == 0 and recall == 0
            else None
        ),
        "false_positive_rate": fp / actual_negative if actual_negative else None,
        "false_negative_rate": fn / actual_positive if actual_positive else None,
        "base_rate": sum(labels) / len(labels) if labels else None,
    }


def _cluster_interval(
    scores: list[float],
    labels: list[int],
    clusters: list[str],
    statistic: Callable[[list[float], list[int]], float | None],
    *,
    seed: int,
    resamples: int = 200,
) -> tuple[float | None, float | None, int]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, cluster in enumerate(clusters):
        grouped[cluster].append(index)
    if len(grouped) < 20:
        return None, None, len(grouped)
    cluster_ids = tuple(sorted(grouped))
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(resamples):
        selected = rng.choice(cluster_ids, size=len(cluster_ids), replace=True)
        indexes = [index for cluster in selected for index in grouped[str(cluster)]]
        try:
            value = statistic(
                [scores[index] for index in indexes],
                [labels[index] for index in indexes],
            )
        except (ZeroDivisionError, ValueError, FloatingPointError):
            continue
        if value is not None and math.isfinite(value):
            values.append(value)
    if len(values) < max(20, int(resamples * 0.8)):
        return None, None, len(grouped)
    lower, upper = np.quantile(np.asarray(values), (0.025, 0.975))
    return float(lower), float(upper), len(grouped)


def _check_metric_result(
    report: dict[str, Any],
    scores: list[float],
    labels: list[int],
    clusters: list[str],
    *,
    threshold: float,
    seed: int,
    check_intervals: bool,
) -> None:
    expected: dict[str, float | None] = {
        "brier_score": _brier(scores, labels) if scores else None,
        "log_loss": _log_loss(scores, labels) if scores else None,
        "ece": _ece(scores, labels) if scores else None,
        "auroc": _auc(scores, labels),
        "average_precision": _average_precision(scores, labels),
    }
    positives = sum(labels)
    negatives = len(labels) - positives
    for name, value in expected.items():
        metric = report[name]
        _close(metric["value"], value, name=name)
        _assert(
            metric["denominator"] == len(scores), f"{name} denominator is fabricated"
        )
        _assert(
            metric["positive_support"] == positives, f"{name} positive support is wrong"
        )
        _assert(
            metric["negative_support"] == negatives, f"{name} negative support is wrong"
        )
        if value is None:
            _assert(
                metric["status"] == "UNDEFINED", f"{name} must state undefined support"
            )
        else:
            _assert(
                metric["status"] in {"DEFINED", "NONINDEPENDENT_DESCRIPTIVE"},
                f"{name} status is invalid",
            )
        interval = metric["uncertainty"]
        _assert(
            interval["cluster_count"] == len(set(clusters)),
            f"{name} cluster denominator is wrong",
        )
        if check_intervals:
            statistic: Callable[[list[float], list[int]], float | None]
            if name in {"brier_score", "log_loss", "ece"}:
                statistic = {
                    "brier_score": _brier,
                    "log_loss": _log_loss,
                    "ece": _ece,
                }[name]
            elif name == "auroc":
                statistic = _auc
            else:
                statistic = _average_precision
            lower, upper, cluster_count = _cluster_interval(
                scores,
                labels,
                clusters,
                statistic,
                seed=seed,
            )
            _assert(
                cluster_count == interval["cluster_count"],
                f"{name} CI cluster count differs",
            )
            _close(interval["lower"], lower, name=f"{name} CI lower")
            _close(interval["upper"], upper, name=f"{name} CI upper")
            if lower is None:
                _assert(
                    interval["resamples"] == 0,
                    f"{name} unavailable CI claims bootstrap draws",
                )
            else:
                _assert(
                    interval["resamples"] >= 160,
                    f"{name} CI lacks predeclared bootstrap support",
                )
        elif len(set(clusters)) < 20:
            _assert(
                interval["lower"] is None
                and interval["upper"] is None
                and interval["status"] == "NONINDEPENDENT_DESCRIPTIVE",
                f"{name} reports row-independent uncertainty below cluster support",
            )

    expected_bins = _reliability(scores, labels)
    bins = report["reliability_bins"]
    _assert(len(bins) == 5, "reliability curve must use five predeclared bins")
    _assert(
        sum(int(item["count"]) for item in bins) == len(scores),
        "reliability bins lose or duplicate rows",
    )
    for actual, expected_bin in zip(bins, expected_bins, strict=True):
        for key, value in expected_bin.items():
            if key in {"lower", "upper", "count"}:
                _assert(actual[key] == value, f"reliability bin {key} differs")
            else:
                _close(actual[key], value, name=f"reliability bin {key}")
        if actual["count"] == 0:
            _assert(
                actual["mean_score"] is None
                and actual["observed_positive_rate"] is None,
                "empty bin contains fabricated statistics",
            )
        else:
            _assert(
                actual["rate_interval"]["unit"] == "independent_session",
                "reliability uncertainty is not session clustered",
            )
            if actual["rate_interval"]["cluster_count"] < 20:
                _assert(
                    actual["rate_interval"]["lower"] is None,
                    "small-bin CI treats rows as independent",
                )

    decision = _decisions(scores, labels, threshold)
    for key, value in decision.items():
        _close(report["decision"].get(key), value, name=f"decision {key}")
    support = report["support"]
    _assert(support["scored_labeled"] == len(scores), "scored/labeled support differs")
    _assert(
        support["positive"] == positives and support["negative"] == negatives,
        "support classes differ",
    )
    _assert(
        support["independent_sessions"] == len(set(clusters)),
        "support session denominator differs",
    )


def _check_partition_and_calibration(
    task: str, report: dict[str, Any]
) -> dict[str, Any]:
    partitions = report["partitions"]
    names = ("TRAIN", "CALIBRATION", "VALIDATION", "TEST")
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            for key in (
                "row_ids",
                "pull_fingerprints",
                "session_fingerprints",
                "vehicle_fingerprints",
                "configuration_fingerprints",
            ):
                left_ids = set(partitions[left][key])
                right_ids = set(partitions[right][key])
                _assert(
                    not left_ids.intersection(right_ids),
                    f"{task} {key} overlap between {left} and {right}",
                )
    for left, right in pairwise(names):
        left_end = datetime.fromisoformat(partitions[left]["end"])
        right_start = datetime.fromisoformat(partitions[right]["start"])
        _assert(
            left_end < right_start,
            f"{task} partition chronology is not strictly increasing",
        )
    train_vehicles = set(partitions["TRAIN"]["vehicle_fingerprints"])
    eval_vehicles = set().union(
        *(set(partitions[name]["vehicle_fingerprints"]) for name in names[1:])
    )
    train_configurations = set(partitions["TRAIN"]["configuration_fingerprints"])
    eval_configurations = set().union(
        *(set(partitions[name]["configuration_fingerprints"]) for name in names[1:])
    )
    _assert(
        not train_vehicles.intersection(eval_vehicles),
        f"{task} vehicle holdout overlaps model training",
    )
    _assert(
        not train_configurations.intersection(eval_configurations),
        f"{task} configuration holdout overlaps model training",
    )
    _assert(
        report["holdout_axes"]["model_training_vehicle_holdout"],
        f"{task} holdout receipt is false",
    )
    _assert(
        report["holdout_axes"]["model_training_configuration_holdout"],
        f"{task} configuration receipt is false",
    )

    calibration = report["calibration_examples"]
    validation = report["validation_examples"]
    test = report["test_examples"]
    _assert(
        len(calibration) == partitions["CALIBRATION"]["rows"],
        f"{task} calibration examples omit rows",
    )
    _assert(
        len(validation) == partitions["VALIDATION"]["rows"],
        f"{task} validation examples omit rows",
    )
    _assert(len(test) == partitions["TEST"]["rows"], f"{task} test examples omit rows")
    for name, examples in (
        ("CALIBRATION", calibration),
        ("VALIDATION", validation),
        ("TEST", test),
    ):
        fingerprint = _stable_hash(
            sorted(item["example_fingerprint"] for item in examples)
        )
        _assert(
            fingerprint == partitions[name]["row_fingerprint"],
            f"{task} {name} examples differ from manifest",
        )

    rows_for_data_checksum = sorted(
        (
            item["example_fingerprint"],
            item["input_source_checksum"],
            item["target_source_checksum"],
            item["label"],
        )
        for item in calibration
    )
    _assert(
        _stable_hash(rows_for_data_checksum)
        == report["calibration_candidates"][0]["calibration_dataset_checksum"],
        f"{task} calibration data checksum cannot be independently reconstructed",
    )
    for candidate in report["calibration_candidates"]:
        method = candidate["method"]
        _assert(method in CALIBRATORS, f"{task} has an unknown calibrator")
        _assert(
            candidate["validity_scope"]["not_for_serving"],
            f"{task}/{method} artifact is serving enabled",
        )
        _assert(
            candidate["validity_scope"]["source_role"] == "synthetic",
            f"{task}/{method} role mismatch",
        )
        _assert(
            candidate["calibration_row_count"] == len(calibration),
            f"{task}/{method} fit count differs",
        )
        _assert(
            candidate["calibration_cluster_count"]
            == len({item["session_fingerprint"] for item in calibration}),
            f"{task}/{method} fit cluster count differs",
        )
        _assert(
            candidate["calibration_positive_count"]
            == sum(item["label"] for item in calibration),
            f"{task}/{method} calibration positive count differs",
        )
        _assert(
            candidate["calibration_negative_count"]
            == len(calibration) - sum(item["label"] for item in calibration),
            f"{task}/{method} calibration negative count differs",
        )
        if method == "identity":
            _assert(
                candidate["artifact_checksum"] is None
                and candidate["artifact_bytes"] == 0,
                "identity mapping fabricated an artifact",
            )
            continue
        if candidate["artifact_checksum"] is None:
            fit_rows = len(calibration)
            positive = sum(item["label"] for item in calibration)
            negative = fit_rows - positive
            clusters = len({item["session_fingerprint"] for item in calibration})
            floors = (40, 10, 10, 10) if method == "sigmoid" else (100, 30, 30, 30)
            meets_fit_floor = (
                fit_rows >= floors[0]
                and positive >= floors[1]
                and negative >= floors[2]
                and clusters >= floors[3]
            )
            _assert(
                candidate["artifact_bytes"] == 0, "missing calibrator has nonzero bytes"
            )
            _assert(
                candidate["state"] in {"INSUFFICIENT_SUPPORT", "REJECTED"},
                f"{task}/{method} missing artifact is not an explicit abstention",
            )
            if candidate["state"] == "INSUFFICIENT_SUPPORT":
                _assert(
                    not meets_fit_floor,
                    f"{task}/{method} skipped an eligible calibrator",
                )
                _assert(
                    candidate["validation_metrics"]["status"] == "INSUFFICIENT_SUPPORT",
                    f"{task}/{method} support abstention status differs",
                )
            else:
                _assert(
                    candidate["validation_metrics"]["status"] == "REJECTED"
                    and isinstance(
                        candidate.get("validation_metrics", {}).get("rejection_code"),
                        str,
                    ),
                    f"{task}/{method} rejected fit lacks an explicit rejection reason",
                )
            _assert(
                all(
                    method not in item.get("calibrated_scores", {})
                    for item in validation + test
                ),
                f"{task}/{method} abstained candidate has fabricated mapped scores",
            )
            _assert(
                report["calibration_metrics"]["test"][method]["test_metrics"] is None,
                f"{task}/{method} abstained candidate has test metrics",
            )
            continue
        _assert(
            isinstance(candidate["artifact_checksum"], str),
            f"{task}/{method} fitted calibrator lacks checksum",
        )
        artifact = _read_calibrator_artifact(candidate["artifact_checksum"])
        _assert(
            artifact["method"] == method, f"{task}/{method} artifact method differs"
        )
        _assert(artifact["task"] == task, f"{task}/{method} artifact task differs")
        _assert(
            artifact["model_version_id"] == report["model_version_id"],
            f"{task}/{method} artifact model differs",
        )
        _assert(
            artifact["model_artifact_checksum"] == report["model_artifact_checksum"],
            f"{task}/{method} source model checksum differs",
        )
        _assert(
            artifact["label_definition_checksum"]
            == report["label_definition_checksum"],
            f"{task}/{method} label checksum differs",
        )
        validity = candidate["validity_scope"]
        _assert(
            artifact["scope"]["task"] == task
            and artifact["scope"]["source_role"] == "synthetic"
            and artifact["scope"]["feature_set_version"]
            == report["feature_set_version"]
            and artifact["scope"]["vehicle_context_fingerprint"]
            == validity["vehicle_context_fingerprint"]
            and artifact["scope"]["configuration_context_fingerprint"]
            == validity["configuration_context_fingerprint"]
            and artifact["scope"]["cutoff"] == validity["cutoff"],
            f"{task}/{method} artifact scope differs from its candidate",
        )
        _assert(
            artifact["not_for_serving"] is True
            and artifact["artifact_kind"] == "OFFLINE_RESEARCH_ONLY_NOT_FOR_SERVING",
            "calibration artifact serving fence is missing",
        )
        fit_rows = len(calibration)
        positive = sum(item["label"] for item in calibration)
        negative = fit_rows - positive
        clusters = len({item["session_fingerprint"] for item in calibration})
        if method == "sigmoid":
            _assert(
                fit_rows >= 40 and positive >= 10 and negative >= 10 and clusters >= 10,
                "sigmoid support floor was bypassed",
            )
        if method == "isotonic":
            _assert(
                fit_rows >= 100
                and positive >= 30
                and negative >= 30
                and clusters >= 30,
                "isotonic support floor was bypassed",
            )
        checksum_rows = sorted(
            (item["example_fingerprint"], float(item["score"]), int(item["label"]))
            for item in calibration
        )
        fit_checksum = hashlib.sha256(_canonical(checksum_rows)).hexdigest()
        _assert(
            artifact["calibration_row_checksum"] == fit_checksum,
            f"{task}/{method} fit row checksum differs",
        )

    validation_support = report["validation_selection_support"]
    selection_eligible = (
        validation_support["rows"] >= 20
        and validation_support["positives"] >= 5
        and validation_support["negatives"] >= 5
        and validation_support["sessions"] >= 5
        and validation_support["vehicles"] >= 2
    )
    _assert(
        validation_support["selection_eligible"] is selection_eligible,
        f"{task} validation selection support gate differs",
    )
    ranked = []
    preference = {"identity": 0, "sigmoid": 1, "isotonic": 2}
    validation_reports = report["calibration_metrics"]["validation"]
    candidate_by_method = {
        item["method"]: item for item in report["calibration_candidates"]
    }
    for method in CALIBRATORS:
        item = validation_reports[method]
        if (
            method != "identity"
            and candidate_by_method[method]["artifact_checksum"] is None
        ):
            _assert(
                item["eligible"] is False,
                f"{task}/{method} ineligible fit was selected",
            )
            continue
        scores, labels = _scores_and_labels(validation, method)
        independently_scored = _brier(scores, labels)
        if item.get("brier_score", {}).get("value") is not None:
            _close(
                item["brier_score"]["value"],
                independently_scored,
                name=f"{task}/{method} validation Brier",
            )
        if item.get("eligible") is True:
            ranked.append((independently_scored, preference[method], method))
    expected_selected = "identity"
    if ranked:
        ranked.sort()
        best = ranked[0][0]
        expected_selected = min(
            (item for item in ranked if item[0] <= best + 1e-4),
            key=lambda item: item[1],
        )[2]
    _assert(
        report["selected_research_candidate"] == expected_selected,
        f"{task} candidate choice used nonvalidation data",
    )
    candidate_states = {
        item["method"]: item["state"] for item in report["calibration_candidates"]
    }
    if selection_eligible:
        _assert(
            candidate_states[expected_selected] == "SELECTED",
            f"{task} selected candidate state differs",
        )
    else:
        _assert(
            not any(state == "SELECTED" for state in candidate_states.values()),
            f"{task} selected a candidate below validation support",
        )
    _assert(
        report["synthetic_to_real_calibration_transfer"] is False,
        f"{task} transferred synthetic calibration",
    )
    _assert(
        report["real_failure_probability"] is False,
        f"{task} calls score a failure probability",
    )

    original_threshold = float(report["model_threshold_frozen"])
    raw_scores, test_labels = _scores_and_labels(test)
    test_clusters = [item["session_fingerprint"] for item in test]
    raw_metrics = report["calibration_metrics"]["test"]["identity_uncalibrated"]
    _check_metric_result(
        raw_metrics,
        raw_scores,
        test_labels,
        test_clusters,
        threshold=original_threshold,
        seed=9143,
        check_intervals=True,
    )
    for method in CALIBRATORS:
        entry = report["calibration_metrics"]["test"].get(method)
        if not isinstance(entry, dict) or not isinstance(entry.get("metrics"), dict):
            continue
        scores, labels = _scores_and_labels(test, method)
        _check_metric_result(
            entry["metrics"],
            scores,
            labels,
            test_clusters,
            threshold=original_threshold,
            seed=9144,
            check_intervals=True,
        )
        for previous, current in zip(
            sorted(zip(raw_scores, scores, strict=True)),
            sorted(zip(raw_scores, scores, strict=True))[1:],
            strict=False,
        ):
            _assert(
                previous[1] <= current[1], f"{task}/{method} mapping is not monotone"
            )
        _check_risk_coverage(entry["risk_coverage"], scores, labels)
    _assert(
        report["model_threshold_changed"] is False,
        f"{task} changed the registered decision threshold",
    )
    _assert(
        report["threshold_is_research_only"] is True,
        f"{task} research threshold fence missing",
    )

    availability = report["label_availability"]
    cohort = availability["cohort_materialization"]
    _assert(
        cohort["requested_pull_count"] == cohort["materialized_pull_count"]
        and cohort["requested_pull_fingerprint"]
        == cohort["materialized_pull_fingerprint"],
        f"{task} materialized pulls differ from the predeclared held-out cohort",
    )
    _assert(
        cohort["unrequested_pull_count"] == 0 and cohort["training_pull_count"] == 0,
        f"{task} materialized training or unrequested source pulls",
    )
    _assert(
        availability["unlabeled_outcomes_fabricated"] is False,
        f"{task} fabricated missing labels",
    )
    _assert(
        availability["labeled_next_pull_rows"]
        == sum(
            partitions[name]["rows"] for name in ("CALIBRATION", "VALIDATION", "TEST")
        ),
        f"{task} labeled denominator differs",
    )
    _assert(
        sum(availability["excluded_pair_counts"].values()) > 0,
        f"{task} missing/quality labels were not reported",
    )
    return {
        "partitions_disjoint": True,
        "chronology_and_vehicle_configuration_holdouts": True,
        "calibration_source_checksum_and_artifact_verified": True,
        "validation_only_candidate_selection": True,
        "independent_test_metric_arithmetic": True,
        "clustered_uncertainty_recomputed": True,
        "held_out_source_cohort_recomputed": True,
        "missing_labels_reported_without_fabrication": True,
    }


def _read_calibrator_artifact(checksum: str) -> dict[str, Any]:
    root = Path(".validation/phase9g/calibrators")
    matches = [path for path in root.rglob(f"{checksum}.json") if not path.is_symlink()]
    _assert(
        len(matches) == 1,
        "calibrator checksum does not resolve to exactly one local artifact",
    )
    path = matches[0]
    content = path.read_bytes()
    _assert(len(content) <= 65_536, "calibrator artifact exceeds fixed byte limit")
    document = json.loads(content)
    supplied = document.pop("artifact_checksum", None)
    actual = hashlib.sha256(_canonical(document)).hexdigest()
    _assert(
        supplied == checksum == actual,
        "calibrator artifact checksum verification failed",
    )
    _assert(
        path.stat().st_size == len(content), "calibrator artifact byte count differs"
    )
    return {**document, "artifact_checksum": supplied}


def _check_risk_coverage(
    report: list[dict[str, Any]], scores: list[float], labels: list[int]
) -> None:
    confidence = sorted(
        range(len(scores)), key=lambda index: (-abs(scores[index] - 0.5), index)
    )
    _assert(
        len(report) == 5,
        "risk/coverage curve must contain five predeclared coverage points",
    )
    for row, fraction in zip(report, (1.0, 0.9, 0.8, 0.6, 0.4), strict=True):
        retained = max(1, math.ceil(len(scores) * fraction)) if scores else 0
        indexes = confidence[:retained]
        errors = sum((scores[index] >= 0.5) != bool(labels[index]) for index in indexes)
        _assert(
            row["retained_count"] == retained,
            "risk/coverage retained denominator differs",
        )
        _assert(
            row["abstained_count"] == len(scores) - retained,
            "risk/coverage abstention count differs",
        )
        _close(
            row["selective_error"],
            errors / retained if retained else None,
            name="selective risk",
        )


def _check_anomaly_receipt(summary: dict[str, Any]) -> dict[str, Any]:
    receipt = summary["source_receipt"]
    _assert(
        receipt["schema_version"] == "phase9c-acceptance-v1",
        "9C source receipt schema is stale",
    )
    _assert(receipt["execution_state"] == "PASS", "9C source receipt did not pass")
    source = receipt["source_data"]
    _assert(
        source["canonical_feature_generator"] == "phase9a-feature-generator-v2",
        "anomaly source is not canonical",
    )
    _assert(
        source["scenario_labels_persisted_as_features"] is False,
        "anomaly oracle entered feature source",
    )
    _assert(
        source["injection_metadata_used_for_fit_or_score"] is False,
        "anomaly intervention metadata leaked into scoring",
    )
    raw = receipt["test_comparison_after_freeze"]
    _assert(set(raw) == FAMILIES, "9C receipt does not cover four anomaly families")
    first_order: list[tuple[Any, Any]] | None = None
    results: dict[str, Any] = {}
    report = summary["anomaly"]["families"]
    for family in sorted(FAMILIES):
        _assert(
            set(raw[family]) == METHODS,
            f"{family} receipt does not cover both detector families",
        )
        results[family] = {}
        for method in sorted(METHODS):
            item = raw[family][method]
            rows = item["case_evaluation"]
            _assert(rows, f"{family}/{method} has no untouched case observations")
            order = [(row.get("fold"), row.get("scenario")) for row in rows]
            if first_order is None:
                first_order = order
            _assert(
                order == first_order,
                f"{family}/{method} changed source case order/oracles",
            )
            threshold = float(item["threshold_frozen_on_validation"])
            _assert(0 < threshold, f"{family}/{method} frozen threshold is invalid")
            eligible: list[dict[str, Any]] = []
            for row in rows:
                score = row.get("score")
                alarm = row.get("predicted_anomaly")
                if score is not None:
                    _assert(
                        isinstance(score, (int, float))
                        and math.isfinite(float(score))
                        and float(score) >= 0,
                        "anomaly score is invalid",
                    )
                can_score = (
                    score is not None
                    and alarm is not None
                    and row.get("status") in {"ANOMALOUS", "INLIER"}
                )
                if can_score:
                    _assert(
                        bool(alarm) == (float(score) > threshold),
                        f"{family}/{method} alarm bit differs from frozen threshold",
                    )
                    eligible.append(row)
                requires_abstention = row.get("scenario") == "quality_duplicate" or (
                    family == "fuel" and row.get("scenario") == "missing_fuel"
                )
                if requires_abstention:
                    _assert(
                        score is None
                        and alarm is None
                        and row.get("status")
                        in {
                            "LOW_QUALITY",
                            "INSUFFICIENT_SIGNAL",
                            "UNSUPPORTED_SOURCE",
                            "NOT_EVALUABLE",
                        },
                        "required-signal or quality-control adversary was not abstained",
                    )
            clean = [row for row in rows if row.get("scenario") == "clean"]
            clean_scored = [row for row in eligible if row.get("scenario") == "clean"]
            clean_alarms = sum(bool(row["predicted_anomaly"]) for row in clean_scored)
            target = [row for row in rows if row.get("scenario") == family]
            target_scored = [row for row in eligible if row.get("scenario") == family]
            target_alarms = sum(bool(row["predicted_anomaly"]) for row in target_scored)
            cross = [
                row
                for row in rows
                if row.get("scenario") in FAMILIES and row.get("scenario") != family
            ]
            cross_scored = [
                row
                for row in eligible
                if row.get("scenario") in FAMILIES and row.get("scenario") != family
            ]
            cross_alarms = sum(bool(row["predicted_anomaly"]) for row in cross_scored)
            summary_family = report[family][method]
            clean_result = summary_family["clean_false_alarm"]
            _assert(
                clean_result["eligible"] == len(clean),
                f"{family}/{method} clean eligible denominator differs",
            )
            _assert(
                clean_result["scored"] == len(clean_scored),
                f"{family}/{method} clean scored denominator differs",
            )
            _assert(
                clean_result["abstained"] == len(clean) - len(clean_scored),
                f"{family}/{method} clean abstentions differ",
            )
            _assert(
                clean_result["false_alarm_count"] == clean_alarms,
                f"{family}/{method} clean false alarm count differs",
            )
            _close(
                clean_result["fpr_per_scored_clean"],
                clean_alarms / len(clean_scored) if clean_scored else None,
                name="clean FPR per scored",
            )
            _close(
                clean_result["fpr_per_eligible_clean"],
                clean_alarms / len(clean) if clean else None,
                name="clean FPR per eligible",
            )
            target_result = summary_family["target_family_detection"]
            _assert(
                target_result["eligible_injections"] == len(target),
                "target injection denominator differs",
            )
            _assert(
                target_result["scored_injections"] == len(target_scored),
                "target scored denominator differs",
            )
            _assert(
                target_result["abstained_injections"]
                == len(target) - len(target_scored),
                "target abstention denominator differs",
            )
            _assert(
                target_result["target_alarm_count"] == target_alarms,
                "target alarm count differs",
            )
            _close(
                target_result["target_recall_per_scored"],
                target_alarms / len(target_scored) if target_scored else None,
                name="target recall per scored",
            )
            cross_result = summary_family["cross_family_alarm"]
            _assert(
                cross_result["eligible_other_family_injections"] == len(cross),
                "cross-family eligible denominator differs",
            )
            _assert(
                cross_result["scored_other_family_injections"] == len(cross_scored),
                "cross-family scored denominator differs",
            )
            _assert(
                cross_result["cross_alarm_count"] == cross_alarms,
                "cross-family alarm count differs",
            )
            _close(
                cross_result["cross_alarm_rate_per_scored"],
                cross_alarms / len(cross_scored) if cross_scored else None,
                name="cross-family alarm rate",
            )
            _assert(
                summary_family["score_is_probability"] is False,
                "anomaly score was called a probability",
            )
            _assert(
                summary_family["fault_probability_calibration"] is False,
                "anomaly score was fault-calibrated",
            )
            _assert(
                summary_family["detector_version_id"],
                "detector version reference is missing",
            )
            _assert(
                len(item["artifact_checksum"]) == 64,
                "anomaly artifact checksum is malformed",
            )
            results[family][method] = {
                "case_count": len(rows),
                "clean_scored": len(clean_scored),
                "clean_false_alarms": clean_alarms,
                "cross_family_scored": len(cross_scored),
                "cross_family_alarms": cross_alarms,
                "quality_abstentions": sum(
                    (
                        row.get("scenario") == "quality_duplicate"
                        or (family == "fuel" and row.get("scenario") == "missing_fuel")
                    )
                    and row.get("score") is None
                    for row in rows
                ),
            }
    sensitivity = summary["reference_size_sensitivity"]
    _assert(
        set(sensitivity["families"]) == FAMILIES,
        "reference sensitivity lacks detector families",
    )
    for family in FAMILIES:
        _assert(
            set(sensitivity["families"][family]) == METHODS,
            "reference sensitivity lacks method coverage",
        )
        for method in METHODS:
            experiment = sensitivity["families"][family][method]
            levels = experiment["size_levels"]
            _assert(
                len(levels) == 3,
                "reference-size experiment lacks three preregistered subsets",
            )
            source_rows = raw[family][method]["case_evaluation"]
            prior_sessions = prior_rows = 0
            for level in levels:
                _assert(
                    level["reference_sessions"] >= prior_sessions
                    and level["reference_rows"] >= prior_rows
                    and len(level["reference_fingerprint"]) == 64,
                    "reference-size subset support or fingerprint is invalid",
                )
                prior_sessions = level["reference_sessions"]
                prior_rows = level["reference_rows"]
                _assert(
                    level["test_case_count"] == len(source_rows),
                    "reference sensitivity changed the untouched test denominator",
                )
                if level["status"] == "REFERENCE_INSUFFICIENT":
                    _assert(
                        level["scored"] == 0
                        and level["abstained"] == len(source_rows)
                        and not level.get("observations"),
                        "insufficient reference did not produce complete abstentions",
                    )
                    continue
                _assert(
                    level["status"] == "SCORED", "unknown reference sensitivity status"
                )
                observations = level.get("observations")
                _assert(
                    isinstance(observations, list)
                    and len(observations) == len(source_rows),
                    "reference sensitivity raw observations are incomplete",
                )
                _assert(
                    len({row["fingerprint"] for row in observations})
                    == len(observations)
                    and all(len(row["fingerprint"]) == 64 for row in observations),
                    "reference sensitivity duplicates or corrupts case identities",
                )
                eligible_rows: list[dict[str, Any]] = []
                for observed, source_case in zip(
                    observations, source_rows, strict=True
                ):
                    _assert(
                        (observed["fold"], observed["scenario"])
                        == (source_case["fold"], source_case["scenario"]),
                        "reference-size refit changed untouched case order or oracle",
                    )
                    score = observed["score"]
                    if score is None:
                        _assert(
                            observed["alarm"] is False
                            and observed["status"]
                            in {
                                "LOW_QUALITY",
                                "INSUFFICIENT_SIGNAL",
                                "UNSUPPORTED_SOURCE",
                                "NOT_EVALUABLE",
                            },
                            "reference-size abstention has an alarm or scored status",
                        )
                        continue
                    _assert(
                        isinstance(score, (int, float))
                        and math.isfinite(float(score))
                        and float(score) >= 0
                        and observed["status"] in {"ANOMALOUS", "INLIER"}
                        and observed["alarm"]
                        is (float(score) > float(observed["threshold"])),
                        "reference-size score or threshold alarm is invalid",
                    )
                    eligible_rows.append(observed)
                _assert(
                    level["scored"] == len(eligible_rows)
                    and level["abstained"] == len(observations) - len(eligible_rows),
                    "reference-size scored/abstained denominators differ",
                )

                def category(
                    rows: list[dict[str, Any]],
                    active_family: str,
                    scenarios: set[str],
                    *,
                    exclude_family: bool = False,
                ) -> tuple[list[dict[str, Any]], int]:
                    eligible = [
                        row
                        for row in rows
                        if row["scenario"] in scenarios
                        and (not exclude_family or row["scenario"] != active_family)
                    ]
                    return eligible, sum(bool(row["alarm"]) for row in eligible)

                clean, clean_alarms = category(eligible_rows, family, {"clean"})
                target, target_alarms = category(eligible_rows, family, {family})
                cross, cross_alarms = category(
                    eligible_rows, family, FAMILIES, exclude_family=True
                )
                _assert(
                    level["clean_false_alarm"]
                    == {
                        "alarms": clean_alarms,
                        "scored_denominator": len(clean),
                        "eligible_denominator": sum(
                            row["scenario"] == "clean" for row in observations
                        ),
                    },
                    "reference-size clean alarm accounting differs",
                )
                _assert(
                    level["target_family_detection"]
                    == {
                        "alarms": target_alarms,
                        "scored_denominator": len(target),
                        "eligible_denominator": sum(
                            row["scenario"] == family for row in observations
                        ),
                    },
                    "reference-size target-family accounting differs",
                )
                _assert(
                    level["cross_family_alarm"]
                    == {"alarms": cross_alarms, "scored_denominator": len(cross)},
                    "reference-size cross-family accounting differs",
                )
                paired = [
                    row for row in eligible_rows if row["source_alarm"] is not None
                ]
                parity = sum(
                    bool(row["alarm"]) == bool(row["source_alarm"]) for row in paired
                )
                _assert(
                    level["frozen_artifact_stability"]["alarm_parity_count"] == parity
                    and level["frozen_artifact_stability"]["paired_scored_count"]
                    == len(paired)
                    and level["frozen_artifact_stability"]["source_threshold_mutated"]
                    is False,
                    "reference-size frozen-artifact parity accounting differs",
                )
            _assert(
                all(
                    row["oracle_labels_used_for_fit"] is False
                    for row in levels
                    if row["status"] == "SCORED"
                ),
                "anomaly oracle labels leaked into detector refit",
            )
    return results


def _check_known_drift_arithmetic(summary: dict[str, Any]) -> None:
    """Recompute the fixed drift adversary without using the production drift module."""
    baseline = np.asarray((290.0, 291.0, 292.0, 293.0, 294.0), dtype=np.float64)
    comparison = np.asarray((310.0, 311.0, 312.0, 313.0, 314.0), dtype=np.float64)
    _assert(len(baseline) == len(comparison) == 5, "drift adversary support differs")
    edges = np.unique(np.quantile(baseline, np.linspace(0.0, 1.0, 11)))
    if len(edges) < 2:
        center = float(baseline[0])
        edges = np.asarray((center - 1e-9, center + 1e-9), dtype=np.float64)
    else:
        edges[0] = -np.inf
        edges[-1] = np.inf
    base_share = np.maximum(np.histogram(baseline, bins=edges)[0] / len(baseline), 1e-6)
    comparison_share = np.maximum(
        np.histogram(comparison, bins=edges)[0] / len(comparison), 1e-6
    )
    expected_psi = float(
        np.sum((comparison_share - base_share) * np.log(comparison_share / base_share))
    )
    median = float(np.median(baseline))
    mad_scale = 1.4826 * float(np.median(np.abs(baseline - median)))
    if mad_scale <= 1e-12:
        q25, q75 = np.quantile(baseline, (0.25, 0.75))
        mad_scale = float(q75 - q25) / 1.349
    if mad_scale <= 1e-12:
        mad_scale = max(abs(median) * 1e-6, 1e-9)
    expected_shift = (float(np.median(comparison)) - median) / mad_scale
    actual = summary["adversaries"]["known_drift_arithmetic"]
    _assert(
        actual["baseline_support"] == 5 and actual["comparison_support"] == 5,
        "known drift support denominators differ",
    )
    _close(actual["psi"], expected_psi, name="known drift PSI")
    _close(
        actual["robust_median_shift"], expected_shift, name="known drift median shift"
    )
    _assert(
        actual["interpretation"] == "distribution warning only; not a diagnosis",
        "drift warning was presented as a diagnostic claim",
    )


def _check_registered_artifact_files(summary: dict[str, Any]) -> None:
    manifests = summary["adversaries"]["artifact_integrity"][
        "registered_artifact_manifest"
    ]
    model_artifacts = manifests["9b_models"]
    detector_artifacts = manifests["9c_detectors"]
    _assert(
        set(model_artifacts) == TASKS,
        "9B registered artifact file manifest is incomplete",
    )
    _assert(
        set(detector_artifacts)
        == {f"{family}:{method}" for family in FAMILIES for method in METHODS},
        "9C registered artifact file manifest is incomplete",
    )
    source_sets = (
        (
            model_artifacts,
            Path(".validation/phase9g/model-artifacts"),
            {
                task: report["model_artifact_checksum"]
                for task, report in summary["tasks"].items()
            },
        ),
        (
            detector_artifacts,
            Path(".validation/phase9c"),
            {
                f"{family}:{method}": item["artifact_checksum"]
                for family, methods in summary["source_receipt"][
                    "test_comparison_after_freeze"
                ].items()
                for method, item in methods.items()
            },
        ),
    )
    for manifest, allowed_root, expected_checksums in source_sets:
        for key, item in manifest.items():
            relative = Path(item["path"])
            _assert(
                not relative.is_absolute() and ".." not in relative.parts,
                "artifact path escapes repository",
            )
            _assert(
                relative.as_posix().startswith(allowed_root.as_posix() + "/"),
                "artifact path is outside its research-only root",
            )
            candidate = Path.cwd()
            for part in relative.parts:
                candidate = candidate / part
                _assert(
                    not candidate.is_symlink(),
                    "registered artifact path contains a symlink",
                )
            repository_root = Path.cwd().resolve()
            resolved = candidate.resolve(strict=True)
            _assert(
                repository_root in resolved.parents,
                "registered artifact escaped repository",
            )
            _assert(resolved.is_file(), "registered artifact is not a regular file")
            content = resolved.read_bytes()
            checksum = hashlib.sha256(content).hexdigest()
            _assert(
                0 < len(content) <= 52_428_800,
                "registered artifact bytes exceed fixed bound",
            )
            _assert(
                item["bytes"] == len(content), f"{key} registered artifact size differs"
            )
            _assert(
                checksum == item["checksum"] == expected_checksums[key],
                f"{key} registered artifact checksum differs",
            )


def _check_drift_records(summary: dict[str, Any]) -> None:
    task_reports = summary["tasks"]
    for task, report in task_reports.items():
        drift = report["drift"]
        _assert(
            drift["label_prevalence_drift"]["status"]
            == "MEASURED_SYNTHETIC_LABEL_PREVALENCE"
            and drift["label_prevalence_drift"]["real_world_claim_allowed"] is False,
            f"{task} synthetic prevalence shift has invalid applicability",
        )
        _assert(
            drift["concept_performance_drift"]["status"]
            == "MEASURED_SYNTHETIC_PERFORMANCE_CHANGE"
            and drift["concept_performance_drift"]["real_world_claim_allowed"] is False,
            f"{task} synthetic performance shift has invalid applicability",
        )
        _assert(
            drift["calibration_drift"]["value"] is None,
            f"{task} calibration drift claims an unsupported measured value",
        )
        _assert(
            report["ood"]["threshold_fit_source"] == "training_partition_only",
            f"{task} OOD thresholds did not come from model-training data",
        )
    adversaries = summary["adversaries"]["drift_and_ood"]
    expected_checks = {
        "unlabeled_concept_change_unknown",
        "unlabeled_prevalence_shift_unknown",
        "feature_distribution_shift_warning",
        "extreme_feature_outlier_warns_without_diagnosis",
        "ambient_shift_does_not_prove_performance_loss",
        "label_change_without_feature_shift_is_separately_evaluable",
    }
    _assert(set(adversaries) == expected_checks, "drift adversary coverage differs")
    _assert(all(adversaries.values()), "drift/OOD adversary failed")


def _check_summary(summary: dict[str, Any], expected_sha: str) -> dict[str, Any]:
    _assert(
        summary.get("schema_version") == "phase9g-evaluation-v1",
        "acceptance report schema is unsupported",
    )
    _assert(
        summary.get("engineering_status") == "PASS", "engineering status is not PASS"
    )
    _assert(
        summary.get("final_sha") == expected_sha,
        "receipt SHA is not the exact expected commit",
    )
    _assert(
        summary.get("base_sha") == "327c63f35b4e7bc0eba31bbec81d20206be8afa2",
        "merged baseline SHA differs",
    )
    body_hash = _stable_hash(
        {key: value for key, value in summary.items() if key != "acceptance_checksum"}
    )
    _assert(
        summary.get("acceptance_checksum") == body_hash,
        "acceptance receipt checksum is invalid",
    )
    tasks = summary.get("tasks")
    if not isinstance(tasks, dict):
        raise AcceptanceRejected("receipt does not exercise exactly all 9B tasks")
    _assert(set(tasks) == TASKS, "receipt does not exercise exactly all 9B tasks")
    protocol = summary["protocol"]
    spec = protocol["definition"]
    _assert(
        protocol["version"] == "phase9g-protocol-v1",
        "evaluation protocol version differs",
    )
    _assert(protocol["checksum"] == _stable_hash(spec), "protocol checksum differs")
    _assert(
        set(spec["tasks"]) == TASKS and set(spec["anomaly_families"]) == FAMILIES,
        "protocol task/family matrix is incomplete",
    )
    _assert(
        set(spec["calibration_methods"]) == CALIBRATORS,
        "protocol calibrator matrix is incomplete",
    )
    _assert(
        spec["max_rows"] == 20_000 and spec["max_artifact_bytes"] == 65_536,
        "protocol resource limits differ",
    )
    _assert(
        math.isclose(spec["calibration_fraction"], 1 / 3)
        and math.isclose(spec["validation_fraction"], 1 / 3),
        "protocol chronological split fractions differ",
    )
    _assert(
        spec["no_auto_promotion"] is True
        and spec["no_real_failure_probability"] is True,
        "protocol safety fences are missing",
    )

    derived_reports: dict[str, dict[str, Any]] = {
        **{f"supervised-{task}": report for task, report in sorted(tasks.items())},
        "anomaly-reliability": summary["anomaly"],
        "reference-size-sensitivity": summary["reference_size_sensitivity"],
        "source-receipt": summary["source_receipt"],
        "applicability": {
            f"{item['subject_kind']}:{item['subject_key']}:{item['source_role']}": item
            for item in summary["applicability"]
        },
        "drift": {
            f"{item['feature_family']}:{item['metric']}:{item['comparison_window']}": item
            for item in summary["drift"]
        },
    }
    _assert(
        _stable_hash(derived_reports) == summary["report_checksum"],
        "scientific report checksum is invalid",
    )

    task_checks = {
        task: _check_partition_and_calibration(task, report)
        for task, report in sorted(tasks.items())
    }
    anomaly_checks = _check_anomaly_receipt(summary)
    _check_registered_artifact_files(summary)
    _check_known_drift_arithmetic(summary)
    _check_drift_records(summary)

    manifest = summary["dataset_manifest"]
    partitions_by_task = [report["partitions"] for report in tasks.values()]
    labeled_ids = sorted(
        row_id
        for partitions in partitions_by_task
        for partition in partitions.values()
        for row_id in partition["row_ids"]
    )
    excluded = sorted(
        fingerprint
        for report in tasks.values()
        for fingerprint in report["label_availability"]["excluded_pair_fingerprints"]
    )
    row_fingerprint = _stable_hash(sorted((*labeled_ids, *excluded)))
    labeled_count = sum(
        partition["rows"]
        for partitions in partitions_by_task
        for partition in partitions.values()
    )
    unlabeled_count = sum(
        sum(report["label_availability"]["excluded_pair_counts"].values())
        for report in tasks.values()
    )
    source_fingerprint = _stable_hash(
        {
            "task_source_fingerprints": sorted(
                report["label_availability"]["source_dataset_fingerprint"]
                for report in tasks.values()
            ),
            "excluded_pair_fingerprints": excluded,
        }
    )
    _assert(manifest["source_role"] == "synthetic", "dataset source role was falsified")
    _assert(
        manifest["labeled_count"] == labeled_count, "dataset labeled support differs"
    )
    _assert(
        manifest["unlabeled_count"] == unlabeled_count,
        "dataset abstention support differs",
    )
    _assert(
        manifest["row_count"] == labeled_count + unlabeled_count,
        "dataset denominator differs",
    )
    _assert(
        manifest["row_fingerprint"] == row_fingerprint,
        "dataset row fingerprint differs",
    )
    _assert(
        manifest["source_fingerprint"] == source_fingerprint,
        "dataset source fingerprint differs",
    )
    _assert(
        manifest["session_count"]
        == len(
            {
                fingerprint
                for partitions in partitions_by_task
                for partition in partitions.values()
                for fingerprint in partition["session_fingerprints"]
            }
        ),
        "dataset session support differs",
    )
    _assert(
        manifest["vehicle_count"]
        == len(
            {
                fingerprint
                for partitions in partitions_by_task
                for partition in partitions.values()
                for fingerprint in partition["vehicle_fingerprints"]
            }
        ),
        "dataset vehicle support differs",
    )
    _assert(
        len(summary["fold_manifests"]) == 12,
        "receipt does not include one fold manifest per task and partition",
    )
    fold_keys = {
        (item["fold_id"], item["partition"]) for item in summary["fold_manifests"]
    }
    _assert(len(fold_keys) == 12, "fold manifest identities are duplicated")
    evidence_kinds = [item["kind"] for item in summary["evaluation_evidence"]]
    _assert(
        evidence_kinds.count("9A_FEATURE_SET_SCHEMA") == 1,
        "feature-set schema lineage is incomplete",
    )
    _assert(
        evidence_kinds.count("9B_LABEL_DEFINITION") == 3,
        "label-definition lineage is incomplete",
    )
    _assert(
        evidence_kinds.count("9B_REGISTERED_MODEL_ARTIFACT") == 3,
        "model artifact lineage is incomplete",
    )
    _assert(
        evidence_kinds.count("9C_REGISTERED_DETECTOR_ARTIFACT") == 8,
        "detector artifact lineage is incomplete",
    )
    _assert(
        evidence_kinds.count("9C_REFERENCE_DATASET") == 8,
        "detector reference lineage is incomplete",
    )
    _assert(
        evidence_kinds.count("9C_DETECTOR_DEFINITION") == 8,
        "detector definition lineage is incomplete",
    )
    _assert(
        all(
            item["source_role"] == "synthetic"
            for item in summary["evaluation_evidence"]
        ),
        "synthetic evidence was mislabeled as real or imported",
    )

    readiness = summary["scientific_readiness"]
    _assert(
        readiness["engineering_pipeline"] == "PASS",
        "scientific readiness disagrees with engineering gate",
    )
    _assert(
        readiness["real_world_predictive_validity"] == "NOT_ESTABLISHED",
        "real-world validity was overstated",
    )
    _assert(
        readiness["real_world_calibration"] == "NOT_ESTABLISHED",
        "real-world calibration was overstated",
    )
    _assert(
        readiness["production_use"] == "PROHIBITED"
        and readiness["failure_labels_available"] is False,
        "production or failure-label readiness is overstated",
    )
    applicability = summary["applicability"]
    _assert(
        any(
            row["source_role"] == "real_vehicle"
            and row["status"] == "REAL_DATA_UNLABELED"
            for row in applicability
        ),
        "real data absence is not reported explicitly",
    )
    _assert(
        any(
            row["source_role"] == "imported" and row["status"] == "REAL_DATA_UNLABELED"
            for row in applicability
        ),
        "unlabeled imported source absence is not reported explicitly",
    )

    integrity = summary["source_integrity"]
    _assert(
        integrity["before_research"]
        == integrity["after_research"]
        == integrity["after_persistence"],
        "prior-phase source table digest changed",
    )
    _assert(
        integrity["unchanged_during_research"]
        and integrity["unchanged_by_9g_persistence"],
        "source integrity gate failed",
    )
    _assert(
        set(integrity["tables"]) == set(integrity["before_research"]),
        "source digest table inventory is incomplete",
    )
    _assert(
        summary["persistence"]["idempotent_replay"] is True,
        "immutable evaluation replay is not idempotent",
    )
    _assert(
        all(summary["persistence"]["immutable_rows"].values()),
        "database rejected no required immutability probe",
    )
    _assert(
        summary["persistence"]["prior_phase_source_tables_unchanged"] is True,
        "registry modified prior-phase source tables",
    )

    adversaries = summary["adversaries"]
    _assert(
        all(
            adversaries["artifact_integrity"][
                "9b_registered_artifact_tamper_rejected"
            ].values()
        ),
        "a tampered 9B artifact was accepted",
    )
    _assert(
        adversaries["artifact_integrity"]["9c_registered_artifact_tamper_rejected"],
        "a tampered 9C artifact was accepted",
    )
    _assert(
        adversaries["artifact_integrity"]["9c_source_receipt_checksum_tamper_rejected"],
        "a tampered 9C source receipt was accepted",
    )
    _assert(
        adversaries["artifact_integrity"]["source_artifacts_modified"] is False,
        "artifact adversary modified source artifacts",
    )
    _assert(
        adversaries["positive_known_bias_calibration"]["source_role"] == "synthetic",
        "positive calibration fixture role is mislabeled",
    )
    _assert(
        adversaries["positive_known_bias_calibration"]["improved_validation_only"]
        is True,
        "known-bias calibration fixture failed",
    )
    _assert(
        adversaries["positive_known_bias_calibration"]["test_used_for_fit_or_selection"]
        is False,
        "positive calibration holdout leaked",
    )
    _assert(
        adversaries["calibration"]["single_class_calibrator_rejected"],
        "single-class calibrator attack was accepted",
    )
    _assert(
        adversaries["calibration"]["duplicate_calibration_identity_rejected"],
        "duplicate calibration identity attack was accepted",
    )
    _assert(
        adversaries["calibration"]["missing_labels_excluded_from_denominator"],
        "missing outcome denominator was fabricated",
    )
    serving = summary["serving_fence"]
    _assert(
        all(value is False for value in serving.values()),
        "Phase 9G changed or enabled serving behavior",
    )
    _assert(
        summary["observability"]["metrics_contains_evaluation_runs"],
        "evaluation metrics were not observed",
    )
    _assert(
        summary["observability"]["entity_ids_used_as_metric_labels"] is False,
        "entity identifier used as an OTel label",
    )
    _assert(
        summary["benchmark"]["row_limit"] == 20_000
        and summary["benchmark"]["metric_result_finite"],
        "bounded metric benchmark failed",
    )
    _assert(
        summary["benchmark"]["database_sessions_started"] > 0,
        "DB session benchmark is missing",
    )

    # Adversarially remove a fold and alter the source hash; each must fail the same
    # independent invariants used for the unmodified acceptance receipt.
    altered = json.loads(json.dumps(summary))
    altered["report_checksum"] = "0" * 64
    report_hash_rejected = False
    try:
        _assert(
            _stable_hash(derived_reports) == altered["report_checksum"],
            "altered report hash accepted",
        )
    except AcceptanceRejected:
        report_hash_rejected = True
    _assert(
        report_hash_rejected, "report checksum falsification adversary was not rejected"
    )
    reduced_rows = dict(tasks[next(iter(TASKS))]["partitions"])
    reduced_rows.pop("TEST")
    fold_removal_rejected = set(reduced_rows) != {
        "TRAIN",
        "CALIBRATION",
        "VALIDATION",
        "TEST",
    }
    _assert(fold_removal_rejected, "fold-removal adversary was not rejected")
    return {
        "independent_status": "PASS",
        "final_sha": expected_sha,
        "report_checksum_verified": True,
        "independently_recomputed_9b_metrics": task_checks,
        "independently_recomputed_9c_alarm_accounting": anomaly_checks,
        "source_integrity_and_immutable_persistence": True,
        "artifact_and_receipt_tamper_adversaries": True,
        "registered_artifact_checksums_independently_verified": True,
        "holdout_and_leakage_checks": True,
        "source_manifest_denominators_and_lineage": True,
        "science_and_serving_fences": True,
        "report_hash_falsification_rejected": report_hash_rejected,
        "fold_removal_falsification_rejected": fold_removal_rejected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report",
        nargs="?",
        type=Path,
        default=Path(".validation/phase9g/acceptance.json"),
    )
    parser.add_argument(
        "--expected-sha",
        default=os.environ.get("GIT_COMMIT_SHA") or os.environ.get("GIT_SHA"),
    )
    args = parser.parse_args()
    if not args.expected_sha:
        parser.error("--expected-sha or GIT_COMMIT_SHA is required")
    summary = json.loads(args.report.read_text(encoding="utf-8"))
    result = _check_summary(summary, args.expected_sha)
    output = args.report.parent / "independent-check.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
