"""Source-aware, offline evaluation for one registered 9C detector candidate."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from vehicle_platform.anomalies.artifacts import TrustedAnomalyArtifact
from vehicle_platform.anomalies.detectors import score_observation
from vehicle_platform.anomalies.domain import ReferenceRow
from vehicle_platform.anomalies.evaluation import classification_metrics
from vehicle_platform.evaluation.metrics import anomaly_alarm_metrics


def evaluate_anomaly_candidate(
    artifact: TrustedAnomalyArtifact,
    rows: tuple[ReferenceRow, ...],
    oracle: Mapping[str, str],
    *,
    training_cutoff: datetime,
    cutoff: datetime,
) -> dict[str, Any]:
    """Score a frozen cohort without persisting 9C findings or changing its artifact."""
    definition = artifact.definition
    expected = {row.pull_id for row in rows}
    if not rows or expected != set(oracle) or len(expected) != len(rows):
        raise ValueError("EVALUATION_COHORT_MISMATCH")
    reference_rows = artifact.reference_manifest.get("selected_rows")
    if not isinstance(reference_rows, list):
        raise ValueError("REFERENCE_LINEAGE_MISSING")
    reference_sessions = {
        str(item["session_id"])
        for item in reference_rows
        if isinstance(item, dict) and isinstance(item.get("session_id"), str)
    }
    if any(row.session_id in reference_sessions for row in rows):
        raise ValueError("EVALUATION_SESSION_LEAKAGE")
    if any(row.cohort != artifact.cohort for row in rows):
        raise ValueError("EVALUATION_COHORT_INCOMPATIBLE")
    if any(row.pull_started_at <= training_cutoff for row in rows):
        raise ValueError("EVALUATION_TIME_LEAKAGE")

    scores: list[float | None] = []
    alarms: list[bool | None] = []
    labels: list[bool | None] = []
    eligible: list[bool] = []
    clean: list[bool] = []
    clusters: list[str] = []
    status_counts: Counter[str] = Counter()
    scenario_counts: Counter[str] = Counter()
    scenario_sessions: dict[str, set[str]] = defaultdict(set)
    scenario_alarms: Counter[str] = Counter()

    family = definition.family.value
    families = {"thermal", "boost_air", "performance", "fuel"}
    if family not in families:
        raise ValueError("DERIVED_FAMILY_NOT_EVALUABLE")
    for row in sorted(rows, key=lambda item: (item.pull_started_at, item.session_id, item.pull_id)):
        scenario = oracle[row.pull_id]
        if scenario not in {*families, "clean", "ambiguous", "quality_excluded", "unlabeled"}:
            raise ValueError("ORACLE_SCENARIO_UNSUPPORTED")
        if row.source_role.value != "synthetic" or row.source_type != "synthetic":
            raise ValueError("SOURCE_ROLE_MISMATCH")
        if row.pull_ended_at > cutoff or row.observation_cutoff > cutoff:
            raise ValueError("EVALUATION_TIME_LEAKAGE")
        finding = score_observation(definition, artifact.fitted, row, observation_cutoff=cutoff)
        status_counts[finding.status.value] += 1
        scenario_counts[scenario] += 1
        scenario_sessions[scenario].add(row.session_id)
        score = finding.score
        alarm = finding.status.value == "ANOMALOUS" if score is not None else None
        if scenario == "quality_excluded" and score is not None:
            raise ValueError("QUALITY_CASE_NOT_ABSTAINED")
        label = (
            False
            if scenario == "clean" or scenario in families and scenario != family
            else (True if scenario == family else None)
        )
        scores.append(score)
        alarms.append(alarm)
        labels.append(label)
        eligible.append(label is not None)
        clean.append(scenario == "clean")
        clusters.append(row.session_id)
        if alarm:
            scenario_alarms[scenario] += 1

    metrics = classification_metrics(tuple(scores), tuple(labels), artifact.fitted.threshold)
    burden = anomaly_alarm_metrics(
        scores,
        alarms,
        eligible,
        clean=clean,
        clusters=clusters,
    )
    clean_sessions = scenario_sessions["clean"]
    target_sessions = scenario_sessions[family]
    target_support = scenario_counts[family]
    clean_support = scenario_counts["clean"]
    enough_support = (
        target_support >= 2
        and clean_support >= 2
        and len(target_sessions) >= 2
        and len(clean_sessions) >= 2
    )
    cross_family = {
        name: {
            "support": scenario_counts[name],
            "sessions": len(scenario_sessions[name]),
            "alarms": scenario_alarms[name],
            "alarm_rate": scenario_alarms[name] / scenario_counts[name]
            if scenario_counts[name]
            else None,
        }
        for name in sorted(families - {family})
    }
    return {
        "schema_version": "phase10-9g-anomaly-evaluation-v1",
        "status": "SYNTHETIC_EVALUATED" if enough_support else "INSUFFICIENT_SUPPORT",
        "family": family,
        "method": definition.method.value,
        "detector_version_id": artifact.detector_version_id,
        "artifact_checksum": artifact.artifact_checksum,
        "reference_checksum": artifact.reference_checksum,
        "threshold": artifact.fitted.threshold,
        "score_orientation": "higher_is_more_statistically_unusual",
        "score_is_probability": False,
        "support": {
            "rows": len(rows),
            "scored": sum(score is not None for score in scores),
            "abstained": sum(score is None for score in scores),
            "clean_rows": clean_support,
            "clean_sessions": len(clean_sessions),
            "target_injections": target_support,
            "target_sessions": len(target_sessions),
            "ambiguous_or_unlabeled": sum(
                scenario_counts[name] for name in ("ambiguous", "unlabeled")
            ),
            "quality_excluded": scenario_counts["quality_excluded"],
            "status_counts": dict(sorted(status_counts.items())),
            "scenario_counts": dict(sorted(scenario_counts.items())),
            "partition_conservation": sum(scenario_counts.values()) == len(rows),
        },
        "target_metrics": metrics,
        "alert_burden": burden,
        "cross_family_alerts": cross_family,
        "scientific_limitations": [
            "Synthetic anomaly injections do not establish real-world detection performance.",
            "Anomaly scores are not engine-health percentages or confirmed diagnoses.",
            "Unlabeled real-world telemetry cannot establish accuracy, recall or calibration.",
            "Real-world mechanical failure predictive reliability remains NOT_ESTABLISHED.",
        ],
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "serving_action": "NONE",
    }
