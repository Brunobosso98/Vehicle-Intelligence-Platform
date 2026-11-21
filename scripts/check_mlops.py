#!/usr/bin/env python3
"""Independently verify the Phase 10 acceptance receipt and persisted records."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import shutil
import stat
import subprocess
from datetime import datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import text
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / ".validation" / "phase10" / "acceptance.json"
TASKS = {
    "NEXT_PULL_THERMAL_DEGRADATION",
    "NEXT_PULL_PERFORMANCE_DEGRADATION",
    "NEXT_PULL_FUEL_DEVIATION",
}
FAMILIES = {"thermal", "boost_air", "performance", "fuel"}
STAGES = (
    "select",
    "validate",
    "fit",
    "verify_artifact",
    "evaluate",
    "compare",
    "report",
)
MAX_ARTIFACT_BYTES = 50 * 1024 * 1024
MAX_DOSSIER_BYTES = 64 * 1024


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _as_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} is not an object")
    return value


def _canonical_hash(value: Any) -> str:
    body = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _independent_psi(
    baseline: list[float], comparison: list[float], bins: int
) -> float | None:
    """Plain-Python PSI oracle; intentionally independent of NumPy and Phase 9G."""
    if len(baseline) < 2 or len(comparison) < 2:
        return None
    if not 2 <= bins <= 20:
        raise ValueError("oracle PSI bins are outside the declared bound")
    edges = sorted({_quantile(baseline, index / bins) for index in range(bins + 1)})
    if len(edges) < 2:
        center = baseline[0]
        edges = [center - 1e-9, center + 1e-9]
    else:
        edges[0] = -math.inf
        edges[-1] = math.inf

    def histogram(values: list[float]) -> list[int]:
        counts = [0] * (len(edges) - 1)
        for value in values:
            for index, (left, right) in enumerate(pairwise(edges)):
                if left <= value < right or index == len(counts) - 1 and value == right:
                    counts[index] += 1
                    break
        return counts

    base_share = [max(count / len(baseline), 1e-6) for count in histogram(baseline)]
    current_share = [
        max(count / len(comparison), 1e-6) for count in histogram(comparison)
    ]
    return sum(
        (current - base) * math.log(current / base)
        for base, current in zip(base_share, current_share, strict=True)
    )


def _assert_number(actual: Any, expected: float, *, name: str) -> None:
    _require(
        isinstance(actual, (int, float))
        and not isinstance(actual, bool)
        and math.isfinite(float(actual))
        and math.isclose(float(actual), expected, rel_tol=1e-10, abs_tol=1e-12),
        f"independent arithmetic mismatch for {name}",
    )


def _metric_values(metrics: Any) -> dict[str, float | None]:
    if not isinstance(metrics, dict):
        return {}
    values: dict[str, float | None] = {}
    for name, result in metrics.items():
        if not isinstance(result, dict) or "value" not in result:
            continue
        value = result["value"]
        if value is None:
            values[str(name)] = None
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            values[str(name)] = float(value)
    return values


def _verify_comparison_arithmetic(comparison: dict[str, Any]) -> int:
    """Recompute candidate-minus-champion metrics from the persisted comparison row."""
    if comparison.get("schema_version") == "phase10-anomaly-comparison-v1":
        old = _as_mapping(comparison.get("champion_metrics"), "champion metrics")
        new = _as_mapping(comparison.get("challenger_metrics"), "challenger metrics")
        old_alert = _as_mapping(
            comparison.get("champion_alert_burden"), "champion alert burden"
        )
        new_alert = _as_mapping(
            comparison.get("challenger_alert_burden"), "challenger alert burden"
        )
        observed = _as_mapping(comparison.get("delta"), "anomaly comparison delta")
        checked = 0
        for key in ("recall", "precision", "false_positive_rate"):
            before, after = old.get(key), new.get(key)
            if before is None or after is None:
                raise ValueError(f"comparison metric {key} is undefined")
            _assert_number(
                observed.get(key),
                float(after) - float(before),
                name=f"anomaly {key} delta",
            )
            checked += 1
        before, after = old_alert.get("coverage"), new_alert.get("coverage")
        if before is None or after is None:
            raise ValueError("comparison coverage inputs are undefined")
        _assert_number(
            observed.get("coverage"),
            float(after) - float(before),
            name="anomaly coverage delta",
        )
        return checked + 1

    old = _metric_values(comparison.get("champion"))
    new = _metric_values(comparison.get("challenger"))
    observed = _as_mapping(comparison.get("metric_delta"), "supervised metric deltas")
    shared = sorted(set(old).intersection(new))
    _require(bool(shared), "supervised comparison has no shared primary metrics")
    for name in shared:
        before, after = old[name], new[name]
        expected = (
            float(after) - float(before)
            if before is not None and after is not None
            else None
        )
        actual = observed.get(name)
        if expected is None:
            _require(actual is None, f"undefined metric delta {name} became numeric")
        else:
            _assert_number(actual, expected, name=f"supervised {name} delta")
    _require(set(observed) == set(shared), "supervised metric delta keys differ")
    return len(shared)


def _verify_bounded_oracle_fixture() -> dict[str, Any]:
    """Hand-computed small arithmetic fixture, separate from production metric code."""
    baseline = [0.0, 0.0, 1.0, 1.0]
    comparison = [0.0, 1.0, 1.0, 1.0]
    psi = _independent_psi(baseline, comparison, 2)
    expected_psi = 0.25 * math.log(3.0)
    _require(psi is not None, "bounded PSI fixture has insufficient support")
    _assert_number(psi, expected_psi, name="bounded fixture PSI")
    baseline_scored, baseline_abstained = 3, 1
    comparison_scored, comparison_abstained = 4, 0
    _require(
        baseline_scored + baseline_abstained == len(baseline)
        and comparison_scored + comparison_abstained == len(comparison),
        "bounded fixture does not conserve per-window counts",
    )
    _assert_number(
        baseline_scored / len(baseline), 0.75, name="baseline scored coverage"
    )
    _assert_number(
        comparison_scored / len(comparison), 1.0, name="comparison scored coverage"
    )
    _assert_number(0.75 - 0.5, 0.25, name="bounded fixture comparison delta")
    source_ids = ["fixture-row-a", "fixture-row-b", "fixture-row-c", "fixture-row-d"]
    _require(
        _canonical_hash(sorted(source_ids))
        == "67b3905485a22f913bef24ccd4cf8866254d1d0c6715bf4bf14c6e70826fd106",
        "bounded fixture source/cohort fingerprint changed",
    )
    return {
        "status": "PASS",
        "psi": psi,
        "baseline_receipts": len(baseline),
        "baseline_scored": baseline_scored,
        "baseline_abstained": baseline_abstained,
        "baseline_scored_coverage": 0.75,
        "comparison_receipts": len(comparison),
        "comparison_scored": comparison_scored,
        "comparison_abstained": comparison_abstained,
        "comparison_scored_coverage": 1.0,
        "comparison_delta": 0.25,
        "source_cohort_fingerprint": _canonical_hash(sorted(source_ids)),
    }


async def _verify_monitoring_arithmetic(
    database: Database, monitor: dict[str, Any]
) -> dict[str, Any]:
    protocol = _as_mapping(monitor.get("protocol"), "frozen monitoring protocol")
    _require(
        _canonical_hash(protocol) == monitor.get("protocol_checksum"),
        "monitoring protocol checksum differs",
    )
    binding_id = UUID(protocol["binding_id"])
    vehicle_id = UUID(protocol["vehicle_id"])
    configuration_id = UUID(protocol["configuration_id"])
    windows = (
        ("baseline", "baseline_start", "baseline_end"),
        ("comparison", "comparison_start", "comparison_end"),
    )
    observed_ids: dict[str, set[str]] = {}
    observed_sessions: dict[str, set[str]] = {}
    score_values: dict[str, list[float]] = {}
    feature_values: dict[str, dict[str, list[float]]] = {}
    output: dict[str, Any] = {}
    async with database.session() as session, session.begin():
        await session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        )
        binding = (
            (
                await session.execute(
                    text(
                        "SELECT result_kind,subject_key,source_role,environment,"
                        "feature_set_version,feature_set_checksum "
                        "FROM prediction_serving_bindings WHERE id=:id"
                    ),
                    {"id": binding_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if binding is None:
            raise ValueError("monitoring source binding is missing")
        _require(
            binding["source_role"] == protocol["source_role"] == "synthetic"
            and binding["environment"] in {"development", "test"},
            "monitoring source role or controlled environment differs",
        )
        _require(
            binding["feature_set_version"] == monitor.get("feature_set_version"),
            "monitoring feature schema differs from the bound 9D feature version",
        )
        feature_version = (
            (
                await session.execute(
                    text(
                        "SELECT checksum,feature_definitions FROM feature_set_versions "
                        "WHERE version=:version"
                    ),
                    {"version": binding["feature_set_version"]},
                )
            )
            .mappings()
            .one_or_none()
        )
        if feature_version is None:
            raise ValueError("monitoring feature definition version is missing")
        _require(
            feature_version["checksum"] == binding["feature_set_checksum"],
            "bound feature version checksum does not match its immutable definition",
        )
        definitions = feature_version["feature_definitions"]
        if not isinstance(definitions, list):
            raise TypeError("immutable feature definitions are not a list")
        feature_units = {
            entry["key"]: entry["unit"]
            for entry in definitions
            if isinstance(entry, dict)
            and isinstance(entry.get("key"), str)
            and isinstance(entry.get("unit"), str)
        }
        feature_keys = protocol["feature_keys"]
        _require(
            isinstance(feature_keys, list)
            and all(key in feature_units for key in feature_keys),
            "monitoring protocol references an unknown or unversioned feature",
        )
        for name, start_key, end_key in windows:
            start = datetime.fromisoformat(protocol[start_key].replace("Z", "+00:00"))
            end = datetime.fromisoformat(protocol[end_key].replace("Z", "+00:00"))
            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT r.id::text AS id,r.status,r.coverage,r.engineering_validation_score,"
                            "r.anomaly_score,r.source_role,r.effective_cutoff,r.created_at,"
                            "r.quality_summary,p.source_type,p.ended_at AS observed_end,"
                            "p.session_id::text AS session_id,p.vehicle_id,"
                            "COALESCE(p.configuration_id,s.configuration_id) AS configuration_id,"
                            "(SELECT jsonb_object_agg(k.feature_key,fs.feature_values->k.feature_key) "
                            "FROM unnest(CAST(:feature_keys AS text[])) AS k(feature_key)) "
                            "AS selected_features "
                            ",fs.quality_metadata AS feature_quality_metadata "
                            ",r.quality_summary "
                            "FROM prediction_receipts r JOIN pulls p ON p.id=r.pull_id "
                            "JOIN driving_sessions s ON s.id=p.session_id AND s.vehicle_id=p.vehicle_id "
                            "LEFT JOIN feature_sets fs ON fs.id=r.feature_set_id "
                            "WHERE r.binding_id=:binding AND p.vehicle_id=:vehicle "
                            "AND COALESCE(p.configuration_id,s.configuration_id)=:configuration "
                            "AND r.created_at>=:start AND r.created_at<:end "
                            "ORDER BY r.created_at,r.id LIMIT :limit"
                        ),
                        {
                            "binding": binding_id,
                            "vehicle": vehicle_id,
                            "configuration": configuration_id,
                            "feature_keys": feature_keys,
                            "start": start,
                            "end": end,
                            "limit": int(protocol["max_rows_per_window"]) + 1,
                        },
                    )
                )
                .mappings()
                .all()
            )
            _require(
                len(rows) <= int(protocol["max_rows_per_window"]),
                f"{name} persisted source window exceeds its declared cap",
            )
            ids = {str(row["id"]) for row in rows}
            sessions = {str(row["session_id"]) for row in rows}
            _require(
                len(ids) == len(rows),
                f"{name} source window contains duplicate receipts",
            )
            _require(
                all(
                    row["source_role"] == protocol["source_role"]
                    and row["vehicle_id"] == vehicle_id
                    and row["configuration_id"] == configuration_id
                    for row in rows
                ),
                f"{name} source/cohort scope does not match the frozen protocol",
            )
            statuses: dict[str, int] = {}
            source_types: dict[str, int] = {}
            scores: list[float] = []
            quality_missing_reasons: dict[str, int] = {}
            feature_coverage_values: list[float] = []
            missingness: dict[str, dict[str, Any]] = {
                key: {
                    "available": 0,
                    "missing": 0,
                    "unit_mismatches": 0,
                    "missing_reason_counts": {},
                }
                for key in feature_keys
            }
            feature_values[name] = {key: [] for key in feature_keys}
            for row in rows:
                status = str(row["status"])
                statuses[status] = statuses.get(status, 0) + 1
                source = str(row["source_type"])
                source_types[source] = source_types.get(source, 0) + 1
                if row["coverage"] is not None:
                    feature_coverage_values.append(float(row["coverage"]))
                quality_summary = row["quality_summary"]
                if isinstance(quality_summary, dict):
                    reasons = quality_summary.get("missing_reason_counts", {})
                    if isinstance(reasons, dict):
                        for reason, count in reasons.items():
                            if isinstance(count, int) and count >= 0:
                                key = str(reason)
                                quality_missing_reasons[key] = (
                                    quality_missing_reasons.get(key, 0) + count
                                )
                if status == "READY_SCORE":
                    value = row["engineering_validation_score"]
                    if value is None:
                        value = row["anomaly_score"]
                    _require(
                        isinstance(value, (int, float))
                        and not isinstance(value, bool)
                        and math.isfinite(float(value)),
                        f"{name} scored source row has no finite score",
                    )
                    scores.append(float(value))
                selected = row["selected_features"]
                for key in feature_keys:
                    entry = selected.get(key) if isinstance(selected, dict) else None
                    feature = entry if isinstance(entry, dict) else {}
                    value = feature.get("value")
                    reason = feature.get("missing_reason")
                    unit = feature.get("unit")
                    quality = feature.get("quality")
                    expected_unit = feature_units[key]
                    unit_mismatch = unit is not None and unit != expected_unit
                    if unit_mismatch:
                        missingness[key]["unit_mismatches"] += 1
                    invalid_value = (
                        value is None
                        or quality not in {"valid", "limited"}
                        or unit != expected_unit
                        or isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(float(value))
                    )
                    if invalid_value:
                        missingness[key]["missing"] += 1
                        missing_reason = str(
                            reason
                            or (
                                "unit_mismatch"
                                if unit != expected_unit
                                else "unavailable"
                            )
                        )
                        counts = missingness[key]["missing_reason_counts"]
                        counts[missing_reason] = counts.get(missing_reason, 0) + 1
                    else:
                        if isinstance(value, bool) or not isinstance(
                            value, (int, float)
                        ):
                            raise TypeError(
                                "feature availability oracle accepted a nonnumeric value"
                            )
                        missingness[key]["available"] += 1
                        feature_values[name][key].append(float(value))
            for key in feature_keys:
                missingness[key]["missing_reason_counts"] = dict(
                    sorted(missingness[key]["missing_reason_counts"].items())
                )
            scored = len(scores)
            receipts = len(rows)
            summary = monitor[name]
            _require(
                summary["receipts"] == receipts
                and summary["sessions"] == len(sessions)
                and summary["scored"] == scored
                and summary["abstained"] == receipts - scored
                and summary["status_counts"] == dict(sorted(statuses.items()))
                and summary["receipt_fingerprint"] == _canonical_hash(sorted(ids)),
                f"{name} reported counts or cohort identity differ from immutable receipt rows",
            )
            _require(
                summary["feature_missingness"] == missingness,
                f"{name} feature availability differs from immutable feature values",
            )
            sorted_quality_reasons = dict(sorted(quality_missing_reasons.items()))
            _require(
                summary["quality_missing_reason_counts"] == sorted_quality_reasons,
                f"{name} quality missingness differs from immutable receipt rows",
            )
            expected_coverage = (
                sum(feature_coverage_values) / receipts
                if feature_coverage_values
                else None
            )
            if expected_coverage is None:
                _require(
                    summary["mean_feature_coverage"] is None,
                    f"{name} coverage is unexpected",
                )
            else:
                _assert_number(
                    summary["mean_feature_coverage"],
                    expected_coverage,
                    name=f"{name} persisted feature coverage",
                )
            effective_cutoffs = [row["effective_cutoff"] for row in rows]
            created_times = [row["created_at"] for row in rows]
            observed_ends = [row["observed_end"] for row in rows]
            _require(
                summary["missing_effective_cutoff"]
                == sum(cutoff is None for cutoff in effective_cutoffs)
                and summary["cutoff_after_recorded_time"]
                == sum(
                    cutoff is not None and cutoff > created
                    for cutoff, created in zip(
                        effective_cutoffs, created_times, strict=True
                    )
                ),
                f"{name} cutoff accounting differs from immutable receipt timestamps",
            )
            late_cutoff = timedelta(hours=int(protocol["late_recorded_after_hours"]))
            late_count = sum(
                created - observed > late_cutoff
                for created, observed in zip(created_times, observed_ends, strict=True)
            )
            _require(
                summary["late_recorded_receipts"] == late_count,
                f"{name} late-recorded count differs from immutable receipt timestamps",
            )
            _require(
                summary["earliest_observed_end"] == min(observed_ends).isoformat()
                if observed_ends
                else summary["earliest_observed_end"] is None,
                f"{name} earliest observation time differs",
            )
            _require(
                summary["latest_observed_end"] == max(observed_ends).isoformat()
                if observed_ends
                else summary["latest_observed_end"] is None,
                f"{name} latest observation time differs",
            )
            _require(
                scored + summary["abstained"] == receipts,
                f"{name} counts do not conserve",
            )
            observed_ids[name] = ids
            observed_sessions[name] = sessions
            score_values[name] = scores
            output[name] = {
                "receipts": receipts,
                "sessions": len(sessions),
                "scored": scored,
                "abstained": receipts - scored,
                "scored_coverage": scored / receipts if receipts else None,
                "source_types": dict(sorted(source_types.items())),
                "source_cohort_fingerprint": _canonical_hash(sorted(ids)),
                "feature_missingness": missingness,
            }
    _require(
        not observed_ids["baseline"].intersection(observed_ids["comparison"]),
        "monitoring windows double-count an immutable receipt",
    )
    _require(
        not observed_sessions["baseline"].intersection(observed_sessions["comparison"]),
        "monitoring windows reuse a session across independent cohorts",
    )
    actual_composition = _as_mapping(
        monitor.get("source_type_composition"), "monitoring source composition"
    )
    for source in set(output["baseline"]["source_types"]) | set(
        output["comparison"]["source_types"]
    ):
        baseline_count = output["baseline"]["source_types"].get(source, 0)
        comparison_count = output["comparison"]["source_types"].get(source, 0)
        expected_entry = {
            "baseline_count": baseline_count,
            "comparison_count": comparison_count,
            "baseline_share": baseline_count / output["baseline"]["receipts"]
            if output["baseline"]["receipts"]
            else None,
            "comparison_share": comparison_count / output["comparison"]["receipts"]
            if output["comparison"]["receipts"]
            else None,
        }
        actual = _as_mapping(actual_composition.get(source), "monitoring source type")
        for key, value in expected_entry.items():
            if value is None:
                _require(
                    actual.get(key) is None, f"source composition {key} is unexpected"
                )
            else:
                _assert_number(
                    actual.get(key),
                    float(value),
                    name=f"source composition {source}.{key}",
                )
    enough_support = all(
        output[name]["receipts"] >= int(protocol["minimum_rows"])
        and output[name]["sessions"] >= int(protocol["minimum_sessions"])
        and output[name]["scored"] >= int(protocol["minimum_rows"])
        for name in ("baseline", "comparison")
    )
    expected_psi = (
        _independent_psi(
            score_values["baseline"],
            score_values["comparison"],
            int(protocol["psi_bins"]),
        )
        if enough_support
        else None
    )
    drift_findings = _as_mapping(
        monitor.get("drift_findings"), "monitoring drift findings"
    )
    score_distribution = _as_mapping(
        drift_findings.get("score_distribution"), "score distribution finding"
    )
    reported_psi = score_distribution.get("psi")
    if expected_psi is None:
        _require(
            reported_psi is None, "unsupported monitoring window reported a PSI value"
        )
    else:
        _assert_number(reported_psi, expected_psi, name="persisted-source score PSI")
    feature_distribution = _as_mapping(
        _as_mapping(monitor.get("drift_findings"), "monitor drift findings").get(
            "feature_distribution"
        ),
        "feature distribution finding",
    )
    feature_findings = _as_mapping(
        feature_distribution.get("features"), "feature PSI findings"
    )
    missingness_finding = _as_mapping(
        _as_mapping(monitor.get("drift_findings"), "monitor drift findings").get(
            "missingness"
        ),
        "missingness finding",
    )
    missingness_features = _as_mapping(
        missingness_finding.get("features"), "feature missingness findings"
    )
    for key in feature_keys:
        baseline_values = feature_values["baseline"][key]
        comparison_values = feature_values["comparison"][key]
        enough_feature_support = min(
            len(baseline_values), len(comparison_values)
        ) >= int(protocol["minimum_rows"])
        expected_feature_psi = (
            _independent_psi(
                baseline_values,
                comparison_values,
                int(protocol["feature_psi_bins"]),
            )
            if enough_feature_support
            else None
        )
        feature_result = _as_mapping(
            feature_findings.get(key), f"feature PSI result {key}"
        )
        _require(
            feature_result.get("baseline_rows") == len(baseline_values)
            and feature_result.get("comparison_rows") == len(comparison_values),
            f"feature {key} PSI row counts differ from immutable feature values",
        )
        if expected_feature_psi is None:
            _require(
                feature_result.get("psi") is None, f"feature {key} PSI lacks support"
            )
        else:
            _assert_number(
                feature_result.get("psi"),
                expected_feature_psi,
                name=f"feature {key} PSI",
            )
        expected_feature_status = (
            "INSUFFICIENT_SUPPORT"
            if expected_feature_psi is None
            else (
                "WARNING"
                if expected_feature_psi >= float(protocol["feature_psi_warning"])
                else "NO_PREDECLARED_WARNING"
            )
        )
        _require(
            feature_result.get("status") == expected_feature_status,
            f"feature {key} drift status differs from independent PSI and frozen threshold",
        )
        baseline_rows = output["baseline"]["receipts"]
        comparison_rows = output["comparison"]["receipts"]
        baseline_missing = output["baseline"]["feature_missingness"][key]["missing"]
        comparison_missing = output["comparison"]["feature_missingness"][key]["missing"]
        baseline_rate = baseline_missing / baseline_rows if baseline_rows else None
        comparison_rate = (
            comparison_missing / comparison_rows if comparison_rows else None
        )
        expected_missingness_delta = (
            comparison_rate - baseline_rate
            if baseline_rate is not None and comparison_rate is not None
            else None
        )
        missing_result = _as_mapping(
            missingness_features.get(key), f"feature {key} missingness result"
        )
        if (
            baseline_rate is None
            or comparison_rate is None
            or expected_missingness_delta is None
        ):
            _require(
                missing_result.get("delta") is None,
                f"feature {key} missingness drift reported without observations",
            )
        else:
            _assert_number(
                missing_result.get("baseline_missing_rate"),
                baseline_rate,
                name=f"feature {key} baseline missingness",
            )
            _assert_number(
                missing_result.get("comparison_missing_rate"),
                comparison_rate,
                name=f"feature {key} comparison missingness",
            )
            _assert_number(
                missing_result.get("delta"),
                expected_missingness_delta,
                name=f"feature {key} missingness delta",
            )
            expected_missingness_status = (
                "WARNING"
                if abs(expected_missingness_delta)
                >= float(protocol["missingness_warning_delta"])
                else "NO_PREDECLARED_WARNING"
            )
            _require(
                missing_result.get("status") == expected_missingness_status,
                f"feature {key} missingness status differs from the frozen threshold",
            )
    _require(
        monitor.get("source_role_drift", {}).get("expected_source_role") == "synthetic"
        and monitor.get("source_role_drift", {}).get("mismatched_receipts") == 0,
        "monitoring source-role identity differs from immutable rows",
    )
    return {
        "status": "PASS",
        "source_role": "synthetic",
        "windows": output,
        "psi": expected_psi,
        "distinct_receipts": len(observed_ids["baseline"] | observed_ids["comparison"]),
        "disjoint_receipts": True,
        "disjoint_sessions": True,
    }


def _current_sha() -> str:
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("git is unavailable")
    result = subprocess.run(
        [executable, "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
        timeout=5,
    )
    return result.stdout.strip()


def _read_private_artifact(
    kind: str, relative_path: str, checksum: str, size: int
) -> None:
    _require(0 < size <= MAX_ARTIFACT_BYTES, "artifact size exceeds acceptance bound")
    relative = Path(relative_path)
    _require(
        not relative.is_absolute()
        and bool(relative.parts)
        and all(part not in {"", ".", ".."} for part in relative.parts),
        "artifact path is outside its trusted namespace",
    )
    components = (
        "apps",
        "api",
        ".artifacts",
        "phase9b" if kind == "supervised" else "phase9c",
    )
    if kind not in {"supervised", "anomaly"}:
        raise ValueError("unknown registered artifact kind")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(ROOT, flags)
    try:
        for component in (*components, *relative.parts[:-1]):
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=descriptor,
        )
        try:
            metadata = os.fstat(file_descriptor)
            _require(stat.S_ISREG(metadata.st_mode), "artifact is not a regular file")
            _require(
                metadata.st_uid == os.getuid(),
                "artifact owner is not the acceptance user",
            )
            _require(
                metadata.st_mode & 0o077 == 0, "artifact permissions are not private"
            )
            _require(
                metadata.st_size == size, "artifact size differs from registry receipt"
            )
            chunks: list[bytes] = []
            remaining = MAX_ARTIFACT_BYTES + 1
            while remaining:
                chunk = os.read(file_descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
        finally:
            os.close(file_descriptor)
    finally:
        os.close(descriptor)
    _require(
        len(payload) == size, "artifact read was truncated or exceeded its size receipt"
    )
    _require(
        hashlib.sha256(payload).hexdigest() == checksum,
        "artifact bytes fail registry checksum",
    )


def _read_candidate_dossier(item: dict[str, Any]) -> None:
    relative = Path(str(item.get("candidate_dossier_file", "")))
    expected_root = (".validation", "phase10", "candidate-dossiers")
    _require(
        not relative.is_absolute()
        and relative.parts[:3] == expected_root
        and len(relative.parts) == 4
        and all(part not in {"", ".", ".."} for part in relative.parts),
        "candidate dossier path is outside its acceptance namespace",
    )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(ROOT, flags)
    try:
        for component in relative.parts[:-1]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=descriptor,
        )
        try:
            metadata = os.fstat(file_descriptor)
            _require(
                stat.S_ISREG(metadata.st_mode),
                "candidate dossier is not a regular file",
            )
            _require(
                metadata.st_uid == os.getuid(), "candidate dossier owner is untrusted"
            )
            _require(
                metadata.st_mode & 0o077 == 0,
                "candidate dossier permissions are not private",
            )
            _require(
                0 < metadata.st_size <= MAX_DOSSIER_BYTES,
                "candidate dossier exceeds its bound",
            )
            payload = os.read(file_descriptor, MAX_DOSSIER_BYTES + 1)
        finally:
            os.close(file_descriptor)
    finally:
        os.close(descriptor)
    _require(len(payload) <= MAX_DOSSIER_BYTES, "candidate dossier exceeds its bound")
    dossier = json.loads(payload)
    _require(
        dossier == item.get("candidate_dossier"),
        "candidate dossier file differs from receipt",
    )
    _require(
        _canonical_hash(dossier) == item.get("candidate_dossier_checksum"),
        "candidate dossier checksum differs",
    )


async def _verify_run(database: Database, item: dict[str, Any]) -> int:
    run_id = UUID(item["run_id"])
    async with database.session() as session, session.begin():
        await session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        )
        run = (
            (
                await session.execute(
                    text(
                        "SELECT r.state,r.definition_fingerprint,r.source_role,r.attempt,"
                        "d.body,d.fingerprint FROM mlops_runs r JOIN mlops_definitions d "
                        "ON d.fingerprint=r.definition_fingerprint WHERE r.id=:id"
                    ),
                    {"id": run_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if run is None:
            raise ValueError("acceptance run is missing from the control plane")
        _require(run["state"] == "COMPLETED", "persisted run did not complete")
        _require(run["source_role"] == "synthetic", "persisted source role changed")
        _require(run["attempt"] == 1, "acceptance run has an unexpected attempt number")
        _require(
            run["fingerprint"] == item["definition_fingerprint"],
            "definition fingerprint differs",
        )
        _require(
            _canonical_hash(run["body"]) == run["fingerprint"],
            "definition body checksum differs",
        )
        run_events = (
            await session.execute(
                text(
                    "SELECT from_state,to_state FROM mlops_run_events WHERE run_id=:id "
                    "ORDER BY event_number"
                ),
                {"id": run_id},
            )
        ).all()
        step_events = (
            (
                await session.execute(
                    text(
                        "SELECT step_name,state,output_body FROM mlops_step_events WHERE run_id=:id "
                        "ORDER BY event_number"
                    ),
                    {"id": run_id},
                )
            )
            .mappings()
            .all()
        )
        proposal = (
            (
                await session.execute(
                    text(
                        "SELECT id,candidate_kind,model_version_id,detector_version_id,source_role "
                        "FROM mlops_proposals WHERE run_id=:id"
                    ),
                    {"id": run_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if proposal is None:
            raise ValueError("candidate proposal is not persisted")
        body_row = (
            (
                await session.execute(
                    text(
                        "SELECT body,content_checksum,artifact_checksum,evaluation_checksum,"
                        "body->>'serving_permission' AS serving_permission,"
                        "body->'candidate_dossier' AS candidate_dossier,"
                        "body->>'candidate_dossier_checksum' AS candidate_dossier_checksum "
                        "FROM mlops_proposals WHERE run_id=:id"
                    ),
                    {"id": run_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if body_row is None:
            raise ValueError("proposal body is missing")
        review_events = (
            await session.execute(
                text(
                    "SELECT state,environment,reviewer_role FROM mlops_proposal_events "
                    "WHERE proposal_id=:id ORDER BY event_number"
                ),
                {"id": proposal["id"]},
            )
        ).all()
        if item["kind"] not in {"supervised", "anomaly"}:
            raise ValueError("unknown acceptance artifact kind")
        candidate_query = (
            "SELECT artifact_path,artifact_checksum,artifact_size_bytes "
            "FROM ml_model_versions WHERE id=:id"
            if item["kind"] == "supervised"
            else "SELECT artifact_path,artifact_checksum,artifact_size_bytes "
            "FROM anomaly_detector_versions WHERE id=:id"
        )
        candidate_id = item["candidate_version_id"]
        candidate_row = (
            (await session.execute(text(candidate_query), {"id": candidate_id}))
            .mappings()
            .one_or_none()
        )
        successful_steps = {
            str(row["step_name"]): row["output_body"]
            for row in step_events
            if row["state"] == "SUCCEEDED"
        }
        evaluation_output = successful_steps.get("evaluate")
        if not isinstance(evaluation_output, dict):
            raise TypeError("persisted evaluation stage output is missing")
        evaluation_source_role: str | None = None
        evaluation_engineering_status: str | None = None
        test_cohort_fingerprint: str | None = None
        if item["kind"] == "supervised":
            evaluation_run = (
                (
                    await session.execute(
                        text(
                            "SELECT source_role,engineering_status,source_manifest "
                            "FROM evaluation_runs WHERE id=:id"
                        ),
                        {"id": UUID(evaluation_output["evaluation_run_id"])},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if evaluation_run is None:
                raise ValueError("immutable Phase 9G evaluation source is missing")
            evaluation_source_role = str(evaluation_run["source_role"])
            evaluation_engineering_status = str(evaluation_run["engineering_status"])
            manifest = _as_mapping(
                evaluation_run["source_manifest"], "Phase 9G source manifest"
            )
            folds = manifest.get("folds")
            if not isinstance(folds, list):
                raise TypeError("Phase 9G fold manifest is not a list")
            test_fold = next(
                (
                    fold
                    for fold in folds
                    if isinstance(fold, dict) and fold.get("partition") == "TEST"
                ),
                None,
            )
            if not isinstance(test_fold, dict):
                raise ValueError("immutable Phase 9G test cohort is missing")
            test_cohort_fingerprint = str(test_fold["row_fingerprint"])
        else:
            evaluation_ids = run["body"].get("evaluation_pull_ids", [])
            if not isinstance(evaluation_ids, list) or not evaluation_ids:
                raise ValueError("anomaly definition has no frozen evaluation cohort")
            source_rows = (
                (
                    await session.execute(
                        text(
                            "SELECT id::text AS id,source_type,started_at,ended_at "
                            "FROM pulls WHERE id=ANY(CAST(:ids AS uuid[])) ORDER BY id"
                        ),
                        {"ids": [UUID(value) for value in evaluation_ids]},
                    )
                )
                .mappings()
                .all()
            )
            evaluation_source = {str(row["id"]): row for row in source_rows}
            if len(evaluation_source) != len(evaluation_ids):
                raise ValueError(
                    "immutable anomaly comparison cohort lost source pulls"
                )
            if any(row["source_type"] != "synthetic" for row in source_rows):
                raise ValueError(
                    "anomaly comparison cohort source role is not synthetic"
                )
            training_cutoff = datetime.fromisoformat(
                run["body"]["cutoff"].replace("Z", "+00:00")
            )
            evaluation_cutoff = datetime.fromisoformat(
                run["body"]["evaluation_cutoff"].replace("Z", "+00:00")
            )
            if any(
                row["started_at"] <= training_cutoff
                or row["ended_at"] > evaluation_cutoff
                for row in source_rows
            ):
                raise ValueError(
                    "anomaly comparison source cohort violates the temporal cutoff"
                )
            if _canonical_hash(sorted(evaluation_source)) != item["comparison"].get(
                "matched_row_fingerprint"
            ):
                raise ValueError(
                    "anomaly matched cohort fingerprint differs from immutable pulls"
                )
    _require(
        [(row[0], row[1]) for row in run_events]
        == [
            (None, "PLANNED"),
            ("PLANNED", "CLAIMED"),
            ("CLAIMED", "RUNNING"),
            ("RUNNING", "COMPLETED"),
        ],
        "run state transition history is incomplete or out of order",
    )
    _require(
        [(row["step_name"], row["state"]) for row in step_events]
        == [(name, state) for name in STAGES for state in ("RUNNING", "SUCCEEDED")],
        "stage history is incomplete or out of order",
    )
    persisted_comparison = _as_mapping(
        successful_steps.get("compare"), "persisted comparison stage"
    )
    _require(
        persisted_comparison == item.get("comparison"),
        "acceptance comparison differs from the immutable persisted compare stage",
    )
    metric_deltas_checked = _verify_comparison_arithmetic(persisted_comparison)
    if item["kind"] == "supervised":
        _require(
            evaluation_source_role == "synthetic"
            and evaluation_engineering_status == "PASS"
            and test_cohort_fingerprint
            == persisted_comparison.get("matched_row_fingerprint"),
            "supervised comparison cohort differs from the immutable Phase 9G test fold",
        )
    _require(
        metric_deltas_checked > 0, "independent comparison arithmetic was not exercised"
    )
    _require(proposal["id"] == UUID(item["proposal_id"]), "proposal id differs")
    _require(proposal["source_role"] == "synthetic", "proposal source role changed")
    proposal_candidate_id = (
        proposal["model_version_id"] or proposal["detector_version_id"]
    )
    _require(
        proposal_candidate_id == UUID(item["candidate_version_id"]),
        "proposal candidate id differs",
    )
    _require(
        body_row["serving_permission"] == "false", "proposal granted serving permission"
    )
    _require(
        body_row["body"].get("serving_action") == "NONE",
        "proposal crossed serving boundary",
    )
    _require(
        body_row["candidate_dossier"] == item.get("candidate_dossier")
        and body_row["candidate_dossier_checksum"]
        == item.get("candidate_dossier_checksum"),
        "candidate dossier differs from the immutable proposal",
    )
    _require(
        body_row["body"].get("real_world_predictive_validity") == "NOT_ESTABLISHED",
        "proposal overclaimed validity",
    )
    _require(
        len(body_row["body"].get("scientific_limitations", [])) >= 4,
        "proposal omitted scientific limitations",
    )
    _require(
        _canonical_hash(body_row["body"]) == body_row["content_checksum"],
        "proposal content checksum differs",
    )
    _require(
        any(
            row[0] in {"REVIEW_REQUIRED", "APPROVED_FOR_CONTROLLED_REVIEW"}
            for row in review_events
        ),
        "proposal review history is missing",
    )
    if item.get("human_reviewed") is True:
        _require(
            any(
                row[0] == "APPROVED_FOR_CONTROLLED_REVIEW"
                and row[1] == "test"
                and row[2] == "mlops_reviewer"
                for row in review_events
            ),
            "explicit authenticated human review receipt is missing",
        )
    if candidate_row is None:
        raise ValueError("registered candidate artifact is missing")
    _require(
        candidate_row["artifact_checksum"] == item["artifact_checksum"],
        "artifact checksum differs",
    )
    _require(
        body_row["artifact_checksum"] == item["artifact_checksum"],
        "proposal artifact checksum differs",
    )
    _require(
        body_row["evaluation_checksum"] == item["evaluation_checksum"],
        "proposal evaluation checksum differs",
    )
    _read_private_artifact(
        item["kind"],
        str(candidate_row["artifact_path"]),
        str(candidate_row["artifact_checksum"]),
        int(candidate_row["artifact_size_bytes"]),
    )
    return metric_deltas_checked


def _verify_receipt(report: dict[str, Any], expected_sha: str) -> list[dict[str, Any]]:
    _require(
        report.get("schema_version") == "phase10-acceptance-v1",
        "unsupported receipt schema",
    )
    _require(report.get("status") == "PASS", "Phase 10 evaluator did not pass")
    _require(
        report.get("git_sha") == expected_sha == _current_sha(),
        "receipt is not tied to the exact checkout SHA",
    )
    recorded_checksum = report.get("acceptance_checksum")
    unsigned = {
        key: value for key, value in report.items() if key != "acceptance_checksum"
    }
    _require(
        recorded_checksum == _canonical_hash(unsigned),
        "acceptance receipt checksum is invalid",
    )
    _require(
        set(report.get("supervised", {})) == TASKS,
        "receipt does not cover all three 9B tasks",
    )
    _require(
        set(report.get("anomaly", {})) == FAMILIES,
        "receipt does not cover all four 9C families",
    )
    items: list[dict[str, Any]] = []
    for expected_kind, group in (
        ("supervised", report["supervised"]),
        ("anomaly", report["anomaly"]),
    ):
        _require(isinstance(group, dict), f"{expected_kind} receipt group is malformed")
        for subject, item in group.items():
            _require(isinstance(item, dict), "candidate receipt is malformed")
            _require(
                item.get("kind") == expected_kind,
                "candidate kind differs from its group",
            )
            _require(
                item.get("subject") == subject, "candidate subject differs from its key"
            )
            items.append(item)
    reproduction = report.get("deterministic_reproduction", {})
    _require(
        reproduction.get("status") == "REPRODUCED",
        "same-seed experiment was not reproduced",
    )
    _require(
        reproduction.get("artifact_checksum_equal") is True,
        "reproduced artifact differs",
    )
    _require(
        reproduction.get("evaluation_dataset_checksum_equal") is True,
        "reproduced experiment changed its holdout",
    )
    _require(
        reproduction.get("candidate_metrics_equal") is True, "reproduced metrics differ"
    )
    reproduced = reproduction.get("reproduction")
    _require(isinstance(reproduced, dict), "reproduction run receipt is missing")
    original = next(
        (
            item
            for item in items
            if item.get("definition_fingerprint")
            == reproduction.get("original_definition_fingerprint")
        ),
        None,
    )
    _require(
        reproduced.get("kind") == "supervised"
        and original is not None
        and reproduced.get("subject") == original.get("subject"),
        "reproduction does not reference the original supervised task",
    )
    items.append(reproduced)
    reviewed_proposal_id = (
        report.get("proposal_review", {}).get("decision", {}).get("proposal_id")
    )
    for item in items:
        item["human_reviewed"] = str(item.get("proposal_id")) == str(
            reviewed_proposal_id
        )
        _require(
            item.get("plan_status") == "READY_TO_REVIEW",
            "candidate plan was not eligible",
        )
        _require(
            item.get("comparison", {}).get("status") == "COMPARABLE_OFFLINE",
            "matched offline comparison missing",
        )
        _require(
            item.get("comparison", {}).get("matched_row_fingerprint") is not None,
            "matched evaluation cohort missing",
        )
        _require(
            item.get("comparison", {}).get("serving_action") == "NONE",
            "comparison crossed serving boundary",
        )
        _require(item.get("serving_action") == "NONE", "run crossed serving boundary")
        _require(
            item.get("real_world_predictive_validity") == "NOT_ESTABLISHED",
            "run overclaimed scientific validity",
        )
        _require(
            set(item.get("stages", {})) == set(STAGES), "run omitted required stages"
        )
        _require(
            all(
                value in {"SUCCEEDED", "SKIPPED_INELIGIBLE"}
                for value in item["stages"].values()
            ),
            "run stage is incomplete",
        )
        _require(
            item.get("exact_replay") is True, "idempotent replay receipt is absent"
        )
        for key in (
            "definition_fingerprint",
            "artifact_checksum",
            "evaluation_checksum",
            "proposal_checksum",
        ):
            _require(
                isinstance(item.get(key), str) and len(item[key]) == 64,
                f"invalid {key}",
            )
        dossier = item.get("candidate_dossier")
        if not isinstance(dossier, dict):
            raise TypeError("candidate dossier is missing")
        _require(
            item.get("candidate_dossier_checksum") == _canonical_hash(dossier),
            "candidate dossier checksum is invalid",
        )
        _require(
            dossier.get("task_or_family") == item.get("subject")
            and dossier.get("artifact_checksum") == item.get("artifact_checksum")
            and dossier.get("real_world_predictive_validity") == "NOT_ESTABLISHED"
            and dossier.get("real_world_mechanical_failure_predictive_reliability")
            == "NOT_ESTABLISHED",
            "candidate dossier lineage or scientific status differs",
        )
        _read_candidate_dossier(item)
    monitoring = report.get("monitoring", {})
    _require(
        monitoring.get("status") == "PASS", "retrospective monitoring did not pass"
    )
    _require(
        monitoring.get("drift_findings", {}).get("performance", {}).get("status")
        == "UNKNOWN",
        "unlabeled telemetry became performance evidence",
    )
    _require(
        monitoring.get("drift_findings", {}).get("feature_source") is not None,
        "source drift was not reported separately",
    )
    _require(
        monitoring.get("source_immutable_during_monitor") is True,
        "monitor mutated Phase 9 source records",
    )
    before = report.get("source_immutability", {}).get(
        "before_offline_comparison_monitor_review"
    )
    after = report.get("source_immutability", {}).get("after_comparison_monitor_review")
    _require(
        isinstance(before, dict) and before == after,
        "Phase 9 source digest changed during MLOps reads",
    )
    _require(
        report.get("adversaries", {}).get("source_tables_immutable_during_mlops")
        is True,
        "MLOps immutability receipt failed",
    )
    _require(
        report.get("adversaries", {}).get("incompatible_candidate_rejected") is True,
        "incompatible candidate was accepted",
    )
    _require(
        report.get("adversaries", {}).get("source_role_spoof_rejected") is True,
        "source-role spoof was accepted",
    )
    _require(
        report.get("adversaries", {}).get("registered_artifact_tamper_rejected_count")
        == 8,
        "tampered artifacts were not all rejected",
    )
    _require(
        report.get("adversaries", {}).get(
            "serving_changes_only_after_separate_9d_action"
        )
        is True,
        "serving boundary evidence is invalid",
    )
    _require(
        report.get("adversaries", {}).get("rollback_planning_preserved_sources")
        is True,
        "rollback planning mutated prior source records",
    )
    _require(
        report.get("proposal_review", {}).get("invalid_token_denied") is True,
        "invalid reviewer credentials were accepted",
    )
    _require(
        report.get("rollback_readiness", {}).get("status")
        == "READY_FOR_SEPARATE_9D_REVIEW",
        "rollback plan readiness was not verified",
    )
    rollback_rehearsal = _as_mapping(
        report.get("rollback_rehearsal"), "isolated Phase 9D rollback rehearsal"
    )
    _require(
        rollback_rehearsal.get("status") == "PASS"
        and rollback_rehearsal.get("simulated_fault")
        == "post_activation_candidate_fault"
        and rollback_rehearsal.get("serving_action_recorded_by_mlops") == "NONE"
        and rollback_rehearsal.get("active_binding_after_activation")
        == rollback_rehearsal.get("candidate_binding_id")
        and rollback_rehearsal.get("active_binding_after_rollback")
        == rollback_rehearsal.get("previous_active_binding_id")
        and rollback_rehearsal.get("rollback_cli", {}).get("status") == "ROLLED_BACK"
        and rollback_rehearsal.get("denied_repeat", {}).get("status") == "DENIED"
        and rollback_rehearsal.get("denied_repeat_had_no_source_effect") is True
        and rollback_rehearsal.get("readiness_plan_after_rollback") == "STALE",
        "separate 9D rollback rehearsal or denied-action no-effect receipt is invalid",
    )
    limitations = report.get("scientific_readiness", {}).get("limitations", [])
    _require(len(limitations) >= 5, "mandatory scientific limitations are incomplete")
    _require(
        report.get("scientific_readiness", {}).get("real_world_predictive_validity")
        == "NOT_ESTABLISHED",
        "real-world validity status changed",
    )
    return items


async def _verify_database(
    items: list[dict[str, Any]], database_url: str, monitor: dict[str, Any]
) -> dict[str, Any]:
    _require(
        database_url.rsplit("/", 1)[-1].startswith("vehicle_test"),
        "checker requires disposable vehicle_test database",
    )
    settings = Settings(database_url=SecretStr(database_url), environment="test")
    database = Database(settings, command_timeout=120)
    try:
        comparison_deltas = 0
        for item in items:
            comparison_deltas += await _verify_run(database, item)
        monitoring = await _verify_monitoring_arithmetic(database, monitor)
        monitoring["comparison_delta_fields_checked"] = comparison_deltas
        return monitoring
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--expected-sha", default=os.environ.get("GIT_SHA"))
    args = parser.parse_args()
    expected_sha = args.expected_sha or _current_sha()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    items = _verify_receipt(report, expected_sha)
    bounded_fixture = _verify_bounded_oracle_fixture()
    database_url = os.environ.get("TEST_DATABASE_URL", "")
    database_oracle = asyncio.run(
        _verify_database(items, database_url, report.get("monitoring", {}))
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "git_sha": expected_sha,
                "supervised_tasks": len(TASKS),
                "anomaly_families": len(FAMILIES),
                "persisted_runs_verified": len(items),
                "registered_artifacts_verified": len(items),
                "bounded_arithmetic_fixture": bounded_fixture,
                "persisted_source_oracle": database_oracle,
                "acceptance_checksum": report["acceptance_checksum"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
