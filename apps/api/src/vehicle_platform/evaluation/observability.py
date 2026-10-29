from __future__ import annotations

from typing import Any

from vehicle_platform.evaluation.contracts import SourceRole


def record_run_metrics(
    telemetry: Any,
    *,
    source_role: SourceRole,
    status: str,
    duration_seconds: float,
    row_count: int,
    abstentions: int,
    artifact_bytes: int,
    integrity_violations: int,
    drift_features: int,
    session_count: int = 0,
    calibration_candidates: tuple[tuple[str, str], ...] = (),
    abstention_reasons: dict[str, int] | None = None,
) -> None:
    if status not in {"PASS", "FAIL", "SUPPORT_INSUFFICIENT", "NOT_ESTABLISHED"}:
        raise ValueError("evaluation metric status is outside its bounded vocabulary")
    if (
        min(
            duration_seconds,
            row_count,
            abstentions,
            artifact_bytes,
            integrity_violations,
            drift_features,
            session_count,
        )
        < 0
    ):
        raise ValueError("evaluation measurements cannot be negative")
    attributes = {"source_role": source_role.value, "status": status}
    telemetry.evaluation_runs.add(1, attributes)
    telemetry.evaluation_duration.record(duration_seconds, attributes)
    telemetry.evaluation_rows.record(row_count, attributes)
    telemetry.evaluation_sessions.record(session_count, attributes)
    for method, candidate_status in calibration_candidates:
        if method not in {"identity", "sigmoid", "isotonic"} or candidate_status not in {
            "ELIGIBLE",
            "INSUFFICIENT_SUPPORT",
            "SELECTED",
            "REJECTED",
        }:
            raise ValueError("calibration metric labels are outside their bounded vocabulary")
        telemetry.evaluation_calibration_candidates.add(
            1,
            {
                "method": method,
                "status": candidate_status,
                "source_role": source_role.value,
            },
        )
    if abstentions:
        telemetry.evaluation_abstentions.add(abstentions, attributes)
    allowed_reasons = {"MISSING_SIGNAL", "LOW_QUALITY", "NO_COMPATIBLE_TARGET", "OTHER"}
    for reason, count in (abstention_reasons or {}).items():
        if reason not in allowed_reasons or count < 0:
            raise ValueError("abstention reason metrics are outside their bounded vocabulary")
        if count:
            telemetry.evaluation_abstention_reasons.add(
                count, {"reason": reason, "source_role": source_role.value}
            )
    if artifact_bytes:
        telemetry.evaluation_artifact_bytes.record(artifact_bytes, attributes)
    if integrity_violations:
        telemetry.evaluation_integrity_violations.add(
            integrity_violations, {"reason": "SOURCE_OR_ARTIFACT_MISMATCH"}
        )
    if drift_features:
        telemetry.evaluation_drift_features.add(
            drift_features, {"feature_family": "canonical_feature"}
        )
