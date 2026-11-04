"""Verify the static Phase 9G UI summary against the independent source report."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


def rounded(value: Any, places: int = 5) -> float | None:
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return round(float(value), places)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _test_metric(task: dict[str, Any], map_name: str, metric: str) -> Any:
    return task["calibration_metrics"]["test"][map_name]["metrics"][metric]


def _reliability(task: dict[str, Any], map_name: str) -> list[dict[str, Any]]:
    examples = task["test_examples"]
    bins: list[dict[str, Any]] = []
    for index in range(5):
        low, high = index / 5, (index + 1) / 5
        members = []
        for example in examples:
            score = example.get("calibrated_scores", {}).get(map_name)
            if (isinstance(score, (int, float)) and low <= score < high) or (
                index == 4 and isinstance(score, (int, float)) and score == high
            ):
                members.append(
                    (
                        float(score),
                        int(example["label"]),
                        example["session_fingerprint"],
                    )
                )
        band = f"{low:.1f}–{high:.1f}"
        if not members:
            bins.append(
                {
                    "bin": band,
                    "meanScore": None,
                    "observedRate": None,
                    "rows": 0,
                    "sessions": 0,
                }
            )
            continue
        bins.append(
            {
                "bin": band,
                "meanScore": round(sum(item[0] for item in members) / len(members), 4),
                "observedRate": round(
                    sum(item[1] for item in members) / len(members), 4
                ),
                "rows": len(members),
                "sessions": len({item[2] for item in members}),
            }
        )
    return bins


def _check_supervised(report: dict[str, Any], summary: dict[str, Any]) -> None:
    summaries = {item["task"]: item for item in summary["supervised"]}
    require(
        set(summaries) == set(report["tasks"]),
        "research summary 9B tasks differ from source report",
    )
    for task_key, source in report["tasks"].items():
        output = summaries[task_key]
        selected = source["selected_research_candidate"]
        metric_values = {
            name: _test_metric(source, selected, name)
            for name in ("brier_score", "log_loss", "ece", "auroc", "average_precision")
        }
        denominator = metric_values["brier_score"]["denominator"]
        sessions = len(
            {item["session_fingerprint"] for item in source["test_examples"]}
        )
        require(
            output["n"] == denominator == len(source["test_examples"]),
            f"{task_key}: support mismatch",
        )
        require(output["sessions"] == sessions, f"{task_key}: session support mismatch")
        require(
            output["threshold"] == source["model_threshold_frozen"],
            f"{task_key}: threshold changed",
        )
        require(
            output["selectedMap"] == selected,
            f"{task_key}: selected research map mismatch",
        )
        require(
            output["mapForServing"] is False,
            f"{task_key}: research map marked for serving",
        )
        for field, metric_name in (
            ("brier", "brier_score"),
            ("logLoss", "log_loss"),
            ("ece", "ece"),
            ("auroc", "auroc"),
            ("averagePrecision", "average_precision"),
        ):
            require(
                output[field] == rounded(metric_values[metric_name]["value"]),
                f"{task_key}: {field} mismatch",
            )
        for field, metric_name in (("brierCi", "brier_score"), ("eceCi", "ece")):
            uncertainty = metric_values[metric_name].get("uncertainty") or {}
            expected = [
                rounded(uncertainty.get("lower")),
                rounded(uncertainty.get("upper")),
            ]
            require(output[field] == expected, f"{task_key}: {field} mismatch")
        require(
            output["reliability"] == _reliability(source, selected),
            f"{task_key}: reliability bins differ",
        )


def _alarm_ratio(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}"


def _check_anomaly(report: dict[str, Any], summary: dict[str, Any]) -> None:
    families = report["anomaly"]["families"]
    outputs = {item["family"]: item for item in summary["anomaly"]}
    require(
        set(outputs) == set(families),
        "research summary 9C families differ from source report",
    )
    method_keys = {"isolation_forest": "Isolation Forest", "robust_mad": "Robust MAD"}
    for family_key, family in families.items():
        output = outputs[family_key]
        methods = {item["name"]: item for item in output["methods"]}
        require(
            set(methods) == set(method_keys.values()),
            f"{family_key}: detector methods differ",
        )
        for method_key, method_name in method_keys.items():
            source = family[method_key]
            target = methods[method_name]
            clean = source["clean_false_alarm"]
            cross = source["cross_family_alarm"]
            detections = source["target_family_detection"]
            clean_text = _alarm_ratio(clean["false_alarm_count"], clean["eligible"])
            if clean["scored"] < clean["eligible"]:
                clean_text += (
                    f" eligible; {clean['false_alarm_count']}/{clean['scored']} scored"
                )
            matrix = source["scenario_matrix"]
            require(
                target["cleanAlarms"] == clean_text,
                f"{family_key}/{method_key}: clean alarms mismatch",
            )
            require(
                target["crossFamilyAlarms"]
                == _alarm_ratio(
                    cross["cross_alarm_count"],
                    cross["eligible_other_family_injections"],
                ),
                f"{family_key}/{method_key}: cross-family alarms mismatch",
            )
            require(
                target["targetDetections"]
                == _alarm_ratio(
                    detections["target_alarm_count"], detections["eligible_injections"]
                ),
                f"{family_key}/{method_key}: target detections mismatch",
            )
            require(
                target["totalAlarms"]
                == sum(case["alarm_count"] for case in matrix.values()),
                f"{family_key}/{method_key}: alarm count mismatch",
            )
            require(
                target["scored"] == sum(case["scored"] for case in matrix.values()),
                f"{family_key}/{method_key}: scored support mismatch",
            )


def check(report_path: Path, summary_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    require(
        report.get("engineering_status") == "PASS",
        "Phase 9G source report did not pass engineering checks",
    )
    require(
        report.get("source_receipt", {}).get("execution_state") == "PASS",
        "Phase 9G source receipt did not pass",
    )
    require(
        summary.get("schemaVersion") == "phase9g-synthetic-research-summary-v1",
        "unsupported static research summary",
    )
    require(
        summary.get("scope") == "SYNTHETIC_ONLY",
        "static research summary source role must stay synthetic-only",
    )
    require(
        summary.get("protocol") == report["protocol"]["version"],
        "protocol version mismatch",
    )
    require(
        summary.get("generator") == report["dataset_manifest"]["generator_version"],
        "generator version mismatch",
    )
    require(
        summary.get("featureVersion")
        == report["dataset_manifest"]["feature_set_version"],
        "feature version mismatch",
    )
    require(
        re.fullmatch(r"[0-9a-f]{40}", summary.get("sourceCodeSha", "")) is not None,
        "source code SHA is malformed",
    )
    source_acceptance = Path("docs/validation/phase-9g-acceptance.md").read_text(
        encoding="utf-8"
    )
    require(
        summary.get("sourceCodeSha") in source_acceptance,
        "source code SHA is not documented in the 9G acceptance",
    )
    require(
        summary.get("sourceReceiptSha256") in source_acceptance,
        "original source report checksum is not documented in the 9G acceptance",
    )
    require(
        summary.get("realWorldCalibration") == "NOT_ESTABLISHED",
        "real-world calibration claim must remain NOT_ESTABLISHED",
    )
    require(
        summary.get("servingPromotion") is False,
        "research results must not be promoted to serving",
    )
    require(
        all(value is False for value in report["serving_fence"].values()),
        "Phase 9G serving fence is not intact",
    )
    _check_supervised(report, summary)
    _check_anomaly(report, summary)
    drift = report["drift"]
    psi = [item for item in drift if item.get("unit") == "population_stability_index"]
    expected_applicability = {
        "driftObservations": len(drift),
        "psiComparisons": len(psi),
        "psiWarnings": sum(item.get("warning") is True for item in psi),
        "trainingOnlyOodWarnings": sum(
            value["ood"]["warning_feature_count"]
            for value in report["ood_and_coverage"].values()
        ),
        "assessmentCount": len(report["applicability"]),
        "syntheticRows": report["dataset_manifest"]["row_count"],
        "labeledRows": report["dataset_manifest"]["labeled_count"],
        "sessions": report["dataset_manifest"]["session_count"],
    }
    require(
        summary["applicability"] == expected_applicability,
        "applicability/drift aggregates differ from source report",
    )
    return {
        "status": "PASS",
        "current_source_report_checksum": report["report_checksum"],
        "original_summary_source_report_checksum": summary["sourceReceiptSha256"],
        "summary_source_sha": summary["sourceCodeSha"],
        "supervised_tasks": len(summary["supervised"]),
        "anomaly_families": len(summary["anomaly"]),
        "applicability_and_drift": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("apps/web/src/lib/predictive/research-summary.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path(".validation/phase9h/research-check.json")
    )
    args = parser.parse_args()
    result = check(args.report, args.summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
