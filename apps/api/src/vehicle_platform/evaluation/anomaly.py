from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from vehicle_platform.evaluation.metrics import anomaly_alarm_metrics

FAMILIES = ("thermal", "boost_air", "performance", "fuel")
METHODS = ("robust_mad", "isolation_forest")
MULTI_FAMILY_SCENARIOS = {"subtle_multivariate"}
HARD_NEGATIVE_SCENARIOS = {"boost_fluctuation", "config_holdout", "normal_unusual_configuration"}
QUALITY_ABSTENTION_SCENARIOS = {"quality_duplicate"}


def _quality_abstention_scenarios(family: str) -> set[str]:
    return QUALITY_ABSTENTION_SCENARIOS | ({"missing_fuel"} if family == "fuel" else set())


class AnomalyEvaluationError(ValueError):
    pass


def evaluate_phase9c_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    if receipt.get("schema_version") != "phase9c-acceptance-v1":
        raise AnomalyEvaluationError("unsupported or stale Phase 9C acceptance receipt")
    if receipt.get("execution_state") != "PASS":
        raise AnomalyEvaluationError("Phase 9C source evaluation did not pass its engineering gate")
    source_data = receipt.get("source_data", {})
    if source_data.get("canonical_feature_generator") != "phase9a-feature-generator-v2":
        raise AnomalyEvaluationError(
            "Phase 9C receipt does not prove canonical 9A feature generation"
        )
    if source_data.get("scenario_labels_persisted_as_features") is not False:
        raise AnomalyEvaluationError("scenario oracle metadata leaked into detector inputs")
    if source_data.get("injection_metadata_used_for_fit_or_score") is not False:
        raise AnomalyEvaluationError("anomaly injection metadata was used by detector scoring")
    test_results = receipt.get("test_comparison_after_freeze")
    if not isinstance(test_results, dict) or set(test_results) != set(FAMILIES):
        raise AnomalyEvaluationError("Phase 9C test receipt lacks all four detector families")

    output: dict[str, Any] = {
        "source_receipt_schema": receipt["schema_version"],
        "source_receipt_integrity": "VERIFIED_BY_PHASE9C_ACCEPTANCE_AND_RECOMPUTED_HERE",
        "canonical_feature_generator": source_data["canonical_feature_generator"],
        "reference_rows": receipt.get("benchmark", {}).get("reference_rows"),
        "scenario_labels_used_as_features": False,
        "anomaly_probability_calibration": "PROHIBITED_NO_VERIFIED_MECHANICAL_GROUND_TRUTH",
        "families": {},
        "cross_family_matrix": {
            "rows": list(FAMILIES),
            "columns": [],
            "cells": {},
            "oracle_policy": (
                "only the named intervention family is positive; multi-family interventions "
                "are separately ambiguous"
            ),
        },
    }
    all_scenarios: set[str] = set()
    for family in FAMILIES:
        method_results = test_results[family]
        if set(method_results) != set(METHODS):
            raise AnomalyEvaluationError(
                f"{family} lacks robust MAD or Isolation Forest source results"
            )
        output["families"][family] = {}
        for method in METHODS:
            result = method_results[method]
            rows = result.get("case_evaluation")
            if not isinstance(rows, list) or not rows:
                raise AnomalyEvaluationError(f"{family}/{method} has no raw scored case evidence")
            threshold = result.get("threshold_frozen_on_validation")
            artifact_checksum = result.get("artifact_checksum")
            if not isinstance(threshold, (float, int)) or not math.isfinite(float(threshold)):
                raise AnomalyEvaluationError(f"{family}/{method} frozen threshold is missing")
            if not isinstance(artifact_checksum, str) or not _sha256(artifact_checksum):
                raise AnomalyEvaluationError(
                    f"{family}/{method} registered artifact checksum is missing"
                )
            normalized = _normalize_cases(rows, family=family, threshold=float(threshold))
            all_scenarios.update(item["scenario"] for item in normalized)
            scores = [item["score"] for item in normalized]
            alarms = [item["alarm"] for item in normalized]
            eligible = [item["eligible"] for item in normalized]
            clean = [item["scenario"] == "clean" for item in normalized]
            clusters = [item["session"] for item in normalized]
            rates = anomaly_alarm_metrics(
                scores,
                alarms,
                eligible,
                clean=clean,
                clusters=clusters,
            )
            target_cases = [item for item in normalized if item["scenario"] == family]
            target_scored = [item for item in target_cases if item["eligible"]]
            target_alarms = sum(bool(item["alarm"]) for item in target_scored)
            other_single_family = [
                item
                for item in normalized
                if item["scenario"] in FAMILIES and item["scenario"] != family
            ]
            other_scored = [item for item in other_single_family if item["eligible"]]
            cross_alarms = sum(bool(item["alarm"]) for item in other_scored)
            scenario_matrix = _scenario_matrix(normalized, family=family)
            output["families"][family][method] = {
                "detector_version_id": result.get("detector_version_id"),
                "artifact_checksum": artifact_checksum,
                "method": method,
                "threshold_frozen_on_validation": float(threshold),
                "clean_false_alarm": {
                    "eligible": rates["clean_eligible"],
                    "scored": rates["clean_scored"],
                    "abstained": rates["clean_abstained"],
                    "false_alarm_count": rates["clean_false_alarm_count"],
                    "fpr_per_scored_clean": rates["clean_fpr_per_scored"],
                    "fpr_per_eligible_clean": rates["clean_fpr_per_eligible"],
                },
                "all_intervention_burden": rates,
                "target_family_detection": {
                    "eligible_injections": len(target_cases),
                    "scored_injections": len(target_scored),
                    "abstained_injections": len(target_cases) - len(target_scored),
                    "target_alarm_count": target_alarms,
                    "target_recall_per_scored": target_alarms / len(target_scored)
                    if target_scored
                    else None,
                    "target_recall_per_eligible": target_alarms / len(target_cases)
                    if target_cases
                    else None,
                },
                "cross_family_alarm": {
                    "eligible_other_family_injections": len(other_single_family),
                    "scored_other_family_injections": len(other_scored),
                    "abstained_other_family_injections": len(other_single_family)
                    - len(other_scored),
                    "cross_alarm_count": cross_alarms,
                    "cross_alarm_rate_per_scored": cross_alarms / len(other_scored)
                    if other_scored
                    else None,
                },
                "scenario_matrix": scenario_matrix,
                "multi_family_ambiguous": _scenario_subset(normalized, MULTI_FAMILY_SCENARIOS),
                "hard_negative_stress": _scenario_subset(normalized, HARD_NEGATIVE_SCENARIOS),
                "quality_capability_abstentions": _scenario_subset(
                    normalized, _quality_abstention_scenarios(family)
                ),
                "alarm_threshold_sensitivity": _threshold_sensitivity(normalized, float(threshold)),
                "score_distribution_within_method_only": _score_distribution(normalized),
                "alarm_deduplication": _deduplicated_burden(normalized),
                "score_is_probability": False,
                "fault_probability_calibration": False,
            }
            for intervention, cell in scenario_matrix.items():
                output["cross_family_matrix"]["cells"][f"{family}/{method}/{intervention}"] = cell
    output["cross_family_matrix"]["columns"] = sorted(all_scenarios)
    output["reference_context"] = {
        "reference_rows": output["reference_rows"],
        "reference_sessions": source_data.get("primary_vehicle_reference_sessions"),
        "minimum_same_configuration_history_enforced_by_9c": True,
        "cross_vehicle_fallback": False,
        "reference_size_sensitivity": {
            "policy_floor_robust_mad_rows": 12,
            "policy_floor_isolation_forest_rows": 24,
            "reference_size_sensitivity_experiment": (
                "NOT_RUN_BY_PHASE9C_RECEIPT; 9G reports support floors and withholds "
                "comparative claim"
            ),
        },
    }
    output["notable_prior_limitations"] = {
        "thermal_cross_family_alarm_reference": (
            "Phase 9C historical cross-family fixture result 6/12 is retained in the "
            "source receipt and exact-case matrix"
        ),
        "fuel_boost_cross_family_alarm_reference": (
            "Phase 9C historical fuel/boost fixture result 4/12 is retained in the "
            "source receipt and exact-case matrix"
        ),
        "source_receipt_cross_family_counts": {
            family: {
                method: test_results[family][method].get("cross_family_injection_alarm_rate", {})
                for method in METHODS
            }
            for family in FAMILIES
        },
        "clean_false_alarm_is_separate_from_cross_family_alarm": True,
    }
    return output


def _normalize_cases(
    rows: list[dict[str, Any]], *, family: str, threshold: float
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            raise AnomalyEvaluationError("anomaly raw score row is not an object")
        scenario = str(item.get("scenario", ""))
        score = item.get("score")
        status = str(item.get("status", "UNKNOWN"))
        alarm = item.get("predicted_anomaly")
        if score is not None and (
            not isinstance(score, (int, float))
            or not math.isfinite(float(score))
            or float(score) < 0
        ):
            raise AnomalyEvaluationError("anomaly score is non-finite or negative")
        eligible = score is not None and alarm is not None and status in {"ANOMALOUS", "INLIER"}
        score_value = float(score) if score is not None else None
        if eligible and score_value is not None and bool(alarm) != (score_value > threshold):
            raise AnomalyEvaluationError("anomaly alarm bit does not match frozen threshold")
        if scenario in _quality_abstention_scenarios(family) and (
            status
            not in {"LOW_QUALITY", "INSUFFICIENT_SIGNAL", "UNSUPPORTED_SOURCE", "NOT_EVALUABLE"}
            or score is not None
            or alarm is not None
        ):
            raise AnomalyEvaluationError(
                "required-signal or quality-control adversary was not abstained"
            )
        normalized.append(
            {
                "index": index,
                "scenario": scenario,
                "score": score_value,
                "threshold": float(item.get("threshold") or threshold),
                "alarm": bool(alarm) if alarm is not None else None,
                "status": status,
                "eligible": eligible,
                "session": str(item.get("fold", "unknown")),
                "environment_shift": bool(item.get("environmental_context_shift", False)),
                "evaluation_role": str(item.get("evaluation_role", "unknown")),
            }
        )
    return normalized


def _scenario_matrix(rows: list[dict[str, Any]], *, family: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["scenario"]].append(row)
    output: dict[str, dict[str, Any]] = {}
    for scenario, values in sorted(groups.items()):
        scored = [item for item in values if item["eligible"]]
        output[scenario] = {
            "eligible": len(values),
            "scored": len(scored),
            "abstained": len(values) - len(scored),
            "alarm_count": sum(bool(item["alarm"]) for item in scored),
            "alarm_rate_per_scored": sum(bool(item["alarm"]) for item in scored) / len(scored)
            if scored
            else None,
            "oracle_role": (
                "CLEAN_CONTROL"
                if scenario == "clean"
                else "TARGET_FAMILY_INJECTION"
                if scenario in FAMILIES
                else "MULTI_FAMILY_OR_AMBIGUOUS"
                if scenario in MULTI_FAMILY_SCENARIOS
                else "QUALITY_OR_CAPABILITY_ABSTENTION"
                if scenario in _quality_abstention_scenarios(family)
                else "HARD_NEGATIVE_OR_CONTEXT_SHIFT"
            ),
            "cross_family_false_positive": False,
        }
    return output


def _scenario_subset(rows: list[dict[str, Any]], selected: set[str]) -> dict[str, Any]:
    cases = [row for row in rows if row["scenario"] in selected]
    scored = [row for row in cases if row["eligible"]]
    return {
        "eligible": len(cases),
        "scored": len(scored),
        "abstained": len(cases) - len(scored),
        "alarm_count": sum(bool(row["alarm"]) for row in scored),
        "alarms_by_scenario": dict(
            sorted(Counter(row["scenario"] for row in scored if row["alarm"]).items())
        ),
        "oracle_labels_are_not_detector_inputs": True,
    }


def _threshold_sensitivity(
    rows: list[dict[str, Any]], original_threshold: float
) -> list[dict[str, Any]]:
    scored = [row for row in rows if row["eligible"]]
    grid = sorted({original_threshold * multiplier for multiplier in (0.5, 0.75, 1.0, 1.25, 1.5)})
    output = []
    for threshold in grid:
        clean = [row for row in scored if row["scenario"] == "clean"]
        target = [row for row in scored if row["scenario"] in FAMILIES]
        output.append(
            {
                "research_threshold": threshold,
                "is_original_frozen_threshold": math.isclose(threshold, original_threshold),
                "clean_false_alarm_count": sum(float(row["score"]) > threshold for row in clean),
                "clean_scored_denominator": len(clean),
                "all_injection_alarm_count": sum(float(row["score"]) > threshold for row in target),
                "all_injection_scored_denominator": len(target),
                "test_used_to_choose_threshold": False,
            }
        )
    return output


def _score_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = sorted(float(row["score"]) for row in rows if row["score"] is not None)
    if not values:
        return {
            "status": "NO_SCORED_ROWS",
            "count": 0,
            "median": None,
            "p95": None,
            "maximum": None,
        }
    return {
        "status": "DESCRIPTIVE_METHOD_LOCAL_SCALE",
        "count": len(values),
        "median": _quantile(values, 0.5),
        "p95": _quantile(values, 0.95),
        "maximum": max(values),
        "scale_compared_across_methods": False,
        "percentage_of_component_health": False,
    }


def _deduplicated_burden(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [row for row in rows if row["eligible"]]
    alarm_events = [row for row in scored if row["alarm"]]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in alarm_events:
        groups[row["session"]].append(row)
    return {
        "finding_count": len(alarm_events),
        "independent_sessions_with_alarm": len(groups),
        "deduplicated_session_alarm_count": len(groups),
        "repeated_findings_collapsed_for_research": sum(
            max(len(items) - 1, 0) for items in groups.values()
        ),
        "grouping_policy": "same detector family and 9C fold/session; research summary only",
        "persisted_findings_mutated": False,
    }


def _quantile(values: list[float], probability: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def _sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
