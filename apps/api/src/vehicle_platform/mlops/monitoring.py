from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timedelta
from statistics import mean
from time import perf_counter
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator
from sqlalchemy import text

from vehicle_platform.evaluation.contracts import SourceRole
from vehicle_platform.evaluation.drift import population_stability_index, robust_location_shift
from vehicle_platform.features.domain import FeatureDType, stable_hash
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.mlops.contracts import Contract
from vehicle_platform.mlops.policy import require_controlled_environment


class MonitoringProtocol(Contract):
    """Frozen, bounded receipt windows for one 9D binding and source role."""

    schema_version: Literal["phase10-monitoring-protocol-v1"] = "phase10-monitoring-protocol-v1"
    binding_id: UUID
    vehicle_id: UUID
    configuration_id: UUID
    source_role: SourceRole
    baseline_start: datetime
    baseline_end: datetime
    comparison_start: datetime
    comparison_end: datetime
    minimum_rows: int = Field(default=10, ge=2, le=10000)
    minimum_sessions: int = Field(default=5, ge=2, le=5000)
    max_rows_per_window: int = Field(default=10000, ge=2, le=10000)
    psi_bins: int = Field(default=10, ge=2, le=20)
    psi_warning: float = Field(default=0.2, gt=0, le=10)
    feature_keys: tuple[str, ...] = Field(min_length=1, max_length=32)
    feature_psi_bins: int = Field(default=10, ge=2, le=20)
    feature_psi_warning: float = Field(default=0.2, gt=0, le=10)
    missingness_warning_delta: float = Field(default=0.2, gt=0, le=1)
    source_composition_warning_delta: float = Field(default=0.2, gt=0, le=1)
    late_recorded_after_hours: int = Field(default=24, ge=1, le=720)

    @model_validator(mode="after")
    def valid_windows(self) -> MonitoringProtocol:
        times = (self.baseline_start, self.baseline_end, self.comparison_start, self.comparison_end)
        if any(value.utcoffset() is None or value.utcoffset() != timedelta(0) for value in times):
            raise ValueError("monitoring window timestamps must be UTC")
        if (
            not self.baseline_start
            < self.baseline_end
            <= self.comparison_start
            < self.comparison_end
        ):
            raise ValueError("monitoring windows must be disjoint and chronological")
        if self.comparison_end - self.baseline_start > timedelta(days=365):
            raise ValueError("monitoring window span exceeds one year")
        if self.minimum_rows > self.max_rows_per_window:
            raise ValueError("minimum support exceeds window bound")
        if (
            len(set(self.feature_keys)) != len(self.feature_keys)
            or tuple(sorted(self.feature_keys)) != self.feature_keys
        ):
            raise ValueError("monitoring feature keys must be unique and sorted")
        for key in self.feature_keys:
            definition = DEFAULT_REGISTRY.resolve(key)
            if definition.dtype not in {FeatureDType.FLOAT, FeatureDType.INTEGER}:
                raise ValueError("monitoring PSI features must be numeric")
        return self

    @property
    def checksum(self) -> str:
        return stable_hash(self.model_dump(mode="json"))


async def _read_monitoring_window(
    database: Database, protocol: MonitoringProtocol
) -> dict[str, Any]:
    """Read existing 9D receipts only; no inference, evidence generation, or serving writes."""
    environment = require_controlled_environment()
    feature_parameters = {"feature_keys": list(protocol.feature_keys)}
    async with database.session() as db, db.begin():
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        binding = (
            (
                await db.execute(
                    text(
                        "SELECT result_kind,subject_key,source_role,feature_set_version,"
                        "feature_set_checksum,environment "
                        "FROM prediction_serving_bindings WHERE id=:id"
                    ),
                    {"id": protocol.binding_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if (
            binding is None
            or binding["source_role"] != protocol.source_role.value
            or binding["environment"] != environment
        ):
            raise ValueError("binding missing or source role/environment mismatch")
        windows: dict[str, list[dict[str, Any]]] = {}
        for name, start, end in (
            ("baseline", protocol.baseline_start, protocol.baseline_end),
            ("comparison", protocol.comparison_start, protocol.comparison_end),
        ):
            result_rows = (
                (
                    await db.execute(
                        text(
                            "SELECT r.id,r.status,r.coverage,r.engineering_validation_score,"
                            "r.anomaly_score,r.effective_cutoff,r.created_at,"
                            "r.source_role,r.feature_set_version,"
                            "r.feature_set_checksum AS receipt_feature_source_checksum,"
                            "r.quality_summary,s.source_type,p.session_id,"
                            "p.ended_at AS observed_end,"
                            "fs.source_hash AS feature_source_checksum,"
                            "fs.quality_metadata AS feature_quality_metadata,"
                            "fsv.version AS stored_feature_set_version,"
                            "fsv.checksum AS feature_version_checksum,"
                            "(SELECT jsonb_object_agg(k.feature_key,"
                            "fs.feature_values->k.feature_key) "
                            "FROM unnest(CAST(:feature_keys AS text[])) AS k(feature_key)) "
                            "AS selected_features FROM prediction_receipts r "
                            "JOIN pulls p ON p.id=r.pull_id "
                            "JOIN driving_sessions s ON s.id=p.session_id "
                            "AND s.vehicle_id=p.vehicle_id LEFT JOIN feature_sets fs "
                            "ON fs.id=r.feature_set_id LEFT JOIN feature_set_versions fsv "
                            "ON fsv.id=fs.feature_set_version_id "
                            "WHERE r.binding_id=:binding AND p.vehicle_id=:vehicle "
                            "AND COALESCE(p.configuration_id,s.configuration_id)=:configuration "
                            "AND r.created_at>=:start AND r.created_at<:end "
                            "ORDER BY r.created_at,r.id LIMIT :limit"
                        ),
                        {
                            "binding": protocol.binding_id,
                            "vehicle": protocol.vehicle_id,
                            "configuration": protocol.configuration_id,
                            "start": start,
                            "end": end,
                            "limit": protocol.max_rows_per_window + 1,
                            **feature_parameters,
                        },
                    )
                )
                .mappings()
                .all()
            )
            if len(result_rows) > protocol.max_rows_per_window:
                raise ValueError("monitoring window exceeds row budget; narrow the window")
            windows[name] = [dict(row) for row in result_rows]
    summaries: dict[str, Any] = {}
    scores: dict[str, list[float]] = {}
    feature_scores: dict[str, dict[str, list[float]]] = {}
    feature_missingness: dict[str, dict[str, dict[str, Any]]] = {}
    feature_unit_mismatches: Counter[str] = Counter()
    role_counts: dict[str, dict[str, int]] = {}
    source_type_counts: dict[str, dict[str, int]] = {}
    feature_version_mismatches: dict[str, int] = {}
    feature_checksum_mismatches: dict[str, int] = {}
    required_signals = sorted(
        {
            signal
            for key in protocol.feature_keys
            for signal in DEFAULT_REGISTRY.resolve(key).required_signals
        }
    )
    signal_coverage: dict[str, dict[str, list[float]]] = {
        name: {signal: [] for signal in required_signals} for name in windows
    }
    quality_missing_reasons: dict[str, Counter[str]] = {name: Counter() for name in windows}
    feature_definitions = {key: DEFAULT_REGISTRY.resolve(key) for key in protocol.feature_keys}
    for name, rows in windows.items():
        if any(
            row["effective_cutoff"] is not None and row["effective_cutoff"] > row["created_at"]
            for row in rows
        ):
            raise ValueError("CUTOFF_LEAKAGE")
        statuses = Counter(str(row["status"]) for row in rows)
        roles = Counter(str(row["source_role"]) for row in rows)
        sources = Counter(str(row["source_type"]) for row in rows)
        role_counts[name] = dict(sorted(roles.items()))
        source_type_counts[name] = dict(sorted(sources.items()))
        version_mismatches = 0
        checksum_mismatches = 0
        values = []
        feature_scores[name] = {key: [] for key in protocol.feature_keys}
        feature_missingness[name] = {}
        feature_counts: dict[str, Any] = {}
        for key, definition in feature_definitions.items():
            missing_reasons: Counter[str] = Counter()
            missing = 0
            unit_mismatches = 0
            feature_counts[key] = {"available": 0, "missing": 0, "unit_mismatches": 0}
            for row in rows:
                selected = row.get("selected_features")
                item = selected.get(key) if isinstance(selected, dict) else None
                value = item.get("value") if isinstance(item, dict) else None
                reason = item.get("missing_reason") if isinstance(item, dict) else None
                unit = item.get("unit") if isinstance(item, dict) else None
                quality = item.get("quality") if isinstance(item, dict) else None
                if unit is not None and unit != definition.unit:
                    unit_mismatches += 1
                    feature_unit_mismatches[key] += 1
                if (
                    value is None
                    or quality not in {"valid", "limited"}
                    or unit != definition.unit
                    or isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                ):
                    missing += 1
                    missing_reasons[
                        str(
                            reason
                            or ("unit_mismatch" if unit != definition.unit else "unavailable")
                        )
                    ] += 1
                else:
                    feature_scores[name][key].append(float(value))
            feature_counts[key] = {
                "available": len(rows) - missing,
                "missing": missing,
                "unit_mismatches": unit_mismatches,
                "missing_reason_counts": dict(sorted(missing_reasons.items())),
            }
            feature_missingness[name][key] = {
                "rate": missing / len(rows) if rows else None,
                "rows": len(rows),
                "missing": missing,
                "available": len(rows) - missing,
                "sessions": len({row["session_id"] for row in rows}),
            }
        for row in rows:
            if (
                row["feature_set_version"] is not None
                and row["feature_set_version"] != binding["feature_set_version"]
            ) or (
                row["stored_feature_set_version"] is not None
                and row["stored_feature_set_version"] != binding["feature_set_version"]
            ):
                version_mismatches += 1
            if (
                row["feature_version_checksum"] is not None
                and row["feature_version_checksum"] != binding["feature_set_checksum"]
            ) or (
                row["feature_source_checksum"] is not None
                and row["receipt_feature_source_checksum"] != row["feature_source_checksum"]
            ):
                checksum_mismatches += 1
            score = row["engineering_validation_score"]
            if score is None:
                score = row["anomaly_score"]
            if row["status"] == "READY_SCORE":
                if score is None:
                    raise ValueError("scored receipt is missing its score")
                score_value = float(score)
                if not math.isfinite(score_value):
                    raise ValueError("receipt score must be finite")
                values.append(score_value)
            quality_summary = row.get("quality_summary")
            if isinstance(quality_summary, dict):
                missing_reasons = quality_summary.get("missing_reason_counts", {})
                if isinstance(missing_reasons, dict):
                    for reason, count in missing_reasons.items():
                        if isinstance(count, int) and count >= 0:
                            quality_missing_reasons[name][str(reason)] += count
            metadata = row.get("feature_quality_metadata")
            if isinstance(metadata, dict):
                coverage = metadata.get("signal_coverage", {})
                if isinstance(coverage, dict):
                    for signal in required_signals:
                        value = coverage.get(signal)
                        if isinstance(value, (int, float)) and not isinstance(value, bool):
                            numeric = float(value)
                            if math.isfinite(numeric) and 0 <= numeric <= 1:
                                signal_coverage[name][signal].append(numeric)
        feature_version_mismatches[name] = version_mismatches
        feature_checksum_mismatches[name] = checksum_mismatches
        scores[name] = values
        sessions = len({row["session_id"] for row in rows})
        scored_sessions = len({row["session_id"] for row in rows if row["status"] == "READY_SCORE"})
        summaries[name] = {
            "status": "NO_OBSERVATIONS"
            if not values
            else (
                "INSUFFICIENT_SUPPORT"
                if len(rows) < protocol.minimum_rows or sessions < protocol.minimum_sessions
                else "OBSERVED"
            ),
            "receipts": len(rows),
            "sessions": sessions,
            "scored": len(values),
            "scored_sessions": scored_sessions,
            "abstained": len(rows) - len(values),
            "status_counts": dict(sorted(statuses.items())),
            "mean_feature_coverage": mean(float(row["coverage"]) for row in rows) if rows else None,
            "feature_missingness": feature_counts,
            "quality_missing_reason_counts": dict(sorted(quality_missing_reasons[name].items())),
            "receipt_fingerprint": stable_hash(sorted(str(row["id"]) for row in rows)),
            "missing_effective_cutoff": sum(row["effective_cutoff"] is None for row in rows),
            "cutoff_after_recorded_time": sum(
                row["effective_cutoff"] is not None and row["effective_cutoff"] > row["created_at"]
                for row in rows
            ),
            "late_recorded_receipts": sum(
                row["created_at"] - row["observed_end"]
                > timedelta(hours=protocol.late_recorded_after_hours)
                for row in rows
            ),
            "earliest_observed_end": min(row["observed_end"] for row in rows).isoformat()
            if rows
            else None,
            "latest_observed_end": max(row["observed_end"] for row in rows).isoformat()
            if rows
            else None,
        }
    sufficient = all(
        summary["status"] == "OBSERVED"
        and summary["scored"] >= protocol.minimum_rows
        and summary["scored_sessions"] >= protocol.minimum_sessions
        for summary in summaries.values()
    )
    psi = (
        population_stability_index(scores["baseline"], scores["comparison"], bins=protocol.psi_bins)
        if sufficient
        else None
    )
    shift = robust_location_shift(scores["baseline"], scores["comparison"]) if sufficient else None
    feature_shift: dict[str, Any] = {}
    missingness_shift: dict[str, Any] = {}
    for key in protocol.feature_keys:
        base = feature_scores["baseline"][key]
        current = feature_scores["comparison"][key]
        support = min(len(base), len(current)) >= protocol.minimum_rows
        feature_psi = (
            population_stability_index(base, current, bins=protocol.feature_psi_bins)
            if support
            else None
        )
        feature_shift[key] = {
            "status": "INSUFFICIENT_SUPPORT"
            if feature_psi is None
            else (
                "WARNING"
                if feature_psi >= protocol.feature_psi_warning
                else "NO_PREDECLARED_WARNING"
            ),
            "psi": feature_psi,
            "robust_location_shift": robust_location_shift(base, current) if support else None,
            "warning_threshold": protocol.feature_psi_warning,
            "baseline_rows": len(base),
            "comparison_rows": len(current),
            "baseline_missingness": feature_missingness["baseline"][key],
            "comparison_missingness": feature_missingness["comparison"][key],
        }
        baseline_missing_rate = feature_missingness["baseline"][key]["rate"]
        comparison_missing_rate = feature_missingness["comparison"][key]["rate"]
        delta = (
            comparison_missing_rate - baseline_missing_rate
            if baseline_missing_rate is not None and comparison_missing_rate is not None
            else None
        )
        missingness_shift[key] = {
            "status": "INSUFFICIENT_SUPPORT"
            if delta is None
            else (
                "WARNING"
                if abs(delta) >= protocol.missingness_warning_delta
                else "NO_PREDECLARED_WARNING"
            ),
            "baseline_missing_rate": baseline_missing_rate,
            "comparison_missing_rate": comparison_missing_rate,
            "delta": delta,
            "warning_threshold": protocol.missingness_warning_delta,
        }
    signal_sampling_shift = {
        signal: {
            "baseline_mean_coverage": mean(signal_coverage["baseline"][signal])
            if signal_coverage["baseline"][signal]
            else None,
            "comparison_mean_coverage": mean(signal_coverage["comparison"][signal])
            if signal_coverage["comparison"][signal]
            else None,
            "baseline_receipts": len(signal_coverage["baseline"][signal]),
            "comparison_receipts": len(signal_coverage["comparison"][signal]),
        }
        for signal in required_signals
    }
    source_names = sorted(
        set(source_type_counts["baseline"]) | set(source_type_counts["comparison"])
    )
    baseline_total = sum(source_type_counts["baseline"].values())
    comparison_total = sum(source_type_counts["comparison"].values())
    source_composition = {
        source: {
            "baseline_count": source_type_counts["baseline"].get(source, 0),
            "comparison_count": source_type_counts["comparison"].get(source, 0),
            "baseline_share": (
                source_type_counts["baseline"].get(source, 0) / baseline_total
                if baseline_total
                else None
            ),
            "comparison_share": (
                source_type_counts["comparison"].get(source, 0) / comparison_total
                if comparison_total
                else None
            ),
        }
        for source in source_names
    }
    source_composition_changed = any(
        item["baseline_share"] is not None
        and item["comparison_share"] is not None
        and abs(item["comparison_share"] - item["baseline_share"])
        >= protocol.source_composition_warning_delta
        for item in source_composition.values()
    )
    source_role_mismatches = sum(
        count
        for role, count in Counter(
            str(row["source_role"]) for rows in windows.values() for row in rows
        ).items()
        if role != protocol.source_role.value
    )
    feature_source_mismatches = sum(feature_version_mismatches.values()) + sum(
        feature_checksum_mismatches.values()
    )
    feature_source_drift_status = (
        "NO_OBSERVATIONS"
        if not any(windows.values())
        else (
            "WARNING"
            if feature_source_mismatches or source_composition_changed
            else "NO_PREDECLARED_WARNING"
        )
    )
    return {
        "schema_version": "phase10-monitoring-window-v1",
        "protocol_checksum": protocol.checksum,
        "source_role": protocol.source_role.value,
        "subject_kind": binding["result_kind"],
        "subject_key": binding["subject_key"],
        "feature_set_version": binding["feature_set_version"],
        "binding_id": str(protocol.binding_id),
        "window_time_axis": "receipt_created_at_utc_half_open",
        "serving_action": "NONE",
        "windows": summaries,
        "source_type_composition": source_composition,
        "feature_source_drift": {
            "status": feature_source_drift_status,
            "feature_version_mismatches": feature_version_mismatches,
            "feature_checksum_mismatches": feature_checksum_mismatches,
            "source_composition_warning_delta": protocol.source_composition_warning_delta,
        },
        "source_role_drift": {
            "status": "WARNING"
            if source_role_mismatches
            else (
                "INSUFFICIENT_SUPPORT"
                if not windows["baseline"] or not windows["comparison"]
                else "NO_PREDECLARED_WARNING"
            ),
            "expected_source_role": protocol.source_role.value,
            "observed_role_counts": role_counts,
            "mismatched_receipts": source_role_mismatches,
        },
        "feature_distribution_shift": {
            "status": "INSUFFICIENT_SUPPORT"
            if any(item["status"] == "INSUFFICIENT_SUPPORT" for item in feature_shift.values())
            else (
                "WARNING"
                if any(item["status"] == "WARNING" for item in feature_shift.values())
                else "NO_PREDECLARED_WARNING"
            ),
            "features": feature_shift,
            "feature_psi_bins": protocol.feature_psi_bins,
            "feature_psi_warning": protocol.feature_psi_warning,
        },
        "missingness_shift": {
            "status": "WARNING"
            if any(item["status"] == "WARNING" for item in missingness_shift.values())
            else (
                "INSUFFICIENT_SUPPORT"
                if any(
                    item["status"] == "INSUFFICIENT_SUPPORT" for item in missingness_shift.values()
                )
                else "NO_PREDECLARED_WARNING"
            ),
            "features": missingness_shift,
            "warning_delta": protocol.missingness_warning_delta,
        },
        "sensor_sampling_shift": signal_sampling_shift,
        "score_distribution_shift": {
            "status": "INSUFFICIENT_SUPPORT"
            if psi is None
            else ("WARNING" if psi >= protocol.psi_warning else "NO_PREDECLARED_WARNING"),
            "psi": psi,
            "robust_location_shift": shift,
            "threshold": protocol.psi_warning,
        },
        "performance_drift": {
            "status": "UNKNOWN",
            "reason": "VERIFIED_LABELS_NOT_JOINED",
            "value": None,
        },
        "calibration_drift": {
            "status": "UNKNOWN",
            "reason": "VERIFIED_LABELS_NOT_JOINED",
            "value": None,
        },
        "reference_cohort_drift": {
            "status": "UNKNOWN",
            "reason": "NO_NEW_9C_REFERENCE_COHORT_REGISTERED",
            "value": None,
        },
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "scientific_limitations": [
            "Synthetic calibration does not prove real-world predictive validity.",
            "Supervised scores are not mechanical failure probabilities.",
            "Anomaly scores are not engine-health percentages or confirmed diagnoses.",
            "Unlabeled real-world telemetry cannot establish prediction accuracy, recall "
            "or calibration.",
            "Feature and score distribution drift does not prove model performance drift "
            "or mechanical failure.",
            "Real-world mechanical failure predictive reliability remains NOT_ESTABLISHED.",
        ],
        "limitation": (
            "Score distribution shift does not establish model degradation or mechanical "
            "failure; supervised scores and anomaly scores are not mechanical failure "
            "probabilities."
        ),
    }


async def monitor_receipts(
    database: Database,
    protocol: MonitoringProtocol,
    *,
    telemetry: Any | None = None,
) -> dict[str, Any]:
    """Trace one bounded monitor read and count findings without entity labels."""
    started = perf_counter()
    if telemetry is not None:
        span_context = telemetry.tracer.start_as_current_span("mlops.monitor")
    else:
        from opentelemetry import trace

        span_context = trace.get_tracer("vehicle_platform.mlops").start_as_current_span(
            "mlops.monitor"
        )
    try:
        with span_context as span:
            result = await _read_monitoring_window(database, protocol)
            span.set_attribute("mlops.monitor.source_role", protocol.source_role.value)
            span.set_attribute(
                "mlops.monitor.status",
                result["feature_source_drift"]["status"],
            )
            findings = (
                ("feature_source", result["feature_source_drift"]["status"]),
                ("feature_distribution", result["feature_distribution_shift"]["status"]),
                ("missingness", result["missingness_shift"]["status"]),
                ("source_role", result["source_role_drift"]["status"]),
                ("score_distribution", result["score_distribution_shift"]["status"]),
            )
            if telemetry is not None:
                for finding, state in findings:
                    if state == "WARNING":
                        telemetry.mlops_monitor_findings.add(
                            1, {"finding": finding, "state": state}
                        )
            return result
    finally:
        if telemetry is not None:
            telemetry.mlops_monitor_duration.record(perf_counter() - started)
