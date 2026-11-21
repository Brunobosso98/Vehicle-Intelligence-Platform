"""Read-only same-cohort 9C challenger comparison against the active 9D binding."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from vehicle_platform.anomalies.artifacts import AnomalyArtifactError
from vehicle_platform.anomalies.artifacts import ArtifactStore as DetectorArtifactStore
from vehicle_platform.anomalies.definitions import detector_definition
from vehicle_platform.anomalies.repository import AnomalyDataRepository
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.mlops.anomaly_evaluation import evaluate_anomaly_candidate
from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind
from vehicle_platform.mlops.planner import (
    anomaly_evaluation_checksum,
    anomaly_evaluation_source_fingerprint,
    checkout_is_dirty,
)
from vehicle_platform.mlops.policy import require_controlled_environment
from vehicle_platform.mlops.source_integrity import prior_source_digest
from vehicle_platform.predictions.repository import CONTROLLED_SCOPE, PredictionRepository


def _not_comparable(reason: str) -> dict[str, Any]:
    return {
        "schema_version": "phase10-anomaly-comparison-v1",
        "status": "NOT_COMPARABLE",
        "reason": reason,
        "serving_action": "NONE",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "limitation": (
            "Anomaly scores are method-specific engineering deviations, not health "
            "percentages, mechanical failure probabilities or diagnoses."
        ),
    }


async def compare_anomaly(
    database: Database,
    definition: PipelineDefinition,
    *,
    champion_binding_id: UUID | None,
    challenger_version_id: UUID,
) -> dict[str, Any]:
    """Compare a candidate with its actual active 9D binding on identical frozen rows."""
    environment = require_controlled_environment()
    if (
        definition.kind is not PipelineKind.ANOMALY
        or definition.family is None
        or definition.method is None
        or definition.evaluation_cutoff is None
        or definition.expected_evaluation_checksum is None
        or definition.expected_evaluation_source_fingerprint is None
        or definition.expected_oracle_checksum is None
        or not definition.evaluation_pull_ids
        or not definition.evaluation_oracle
    ):
        raise ValueError("ANOMALY_EVALUATION_MANIFEST_REQUIRED")
    if definition.source_role.value != "synthetic":
        return _not_comparable("SYNTHETIC_PROTOCOL_REQUIRED")
    if await checkout_is_dirty(definition.git_sha):
        return _not_comparable("DIRTY_WORKTREE")
    if champion_binding_id is None:
        return _not_comparable("NO_ACTIVE_CHAMPION_SELECTED")

    repository = PredictionRepository(database)
    binding = await repository.binding(champion_binding_id)
    if binding is None or not binding.is_active or binding.detector_version_id is None:
        return _not_comparable("NO_ACTIVE_CHAMPION")
    if (
        binding.environment != environment
        or binding.scope != CONTROLLED_SCOPE
        or binding.result_kind != "anomaly"
        or binding.subject_key != definition.family
        or binding.source_role.value != definition.source_role.value
        or binding.feature_set_version != "phase9a-pull-v2"
        or binding.feature_set_checksum != definition.expected_feature_checksum
    ):
        return _not_comparable("CHAMPION_SCOPE_OR_SCHEMA_MISMATCH")

    detector = detector_definition(definition.family, definition.method)
    rows = await AnomalyDataRepository(database).load_targets(
        definition.evaluation_pull_ids, definition.evaluation_cutoff, detector
    )
    if {row.pull_id for row in rows} != {str(item) for item in definition.evaluation_pull_ids}:
        return _not_comparable("EVALUATION_COHORT_MISMATCH")
    if (
        anomaly_evaluation_source_fingerprint(rows)
        != definition.expected_evaluation_source_fingerprint
        or anomaly_evaluation_checksum(
            definition,
            detector.checksum,
            definition.expected_feature_checksum,
            rows,
        )
        != definition.expected_evaluation_checksum
        or stable_hash([item.model_dump(mode="json") for item in definition.evaluation_oracle])
        != definition.expected_oracle_checksum
    ):
        return _not_comparable("EVALUATION_LINEAGE_MISMATCH")

    store = DetectorArtifactStore()
    try:
        champion = await store.load_registered(database, str(binding.detector_version_id))
        challenger = await store.load_registered(database, str(challenger_version_id))
    except (AnomalyArtifactError, ValueError, OSError):
        return _not_comparable("ARTIFACT_INVALID")
    if (
        champion.artifact_checksum != binding.artifact_checksum
        or challenger.detector_version_id != str(challenger_version_id)
        or champion.definition.family != challenger.definition.family
        or champion.definition.family.value != definition.family
        or champion.definition.feature_keys != challenger.definition.feature_keys
        or champion.cohort != challenger.cohort
    ):
        return _not_comparable("MODEL_SCHEMA_SOURCE_OR_TARGET_MISMATCH")

    source_before = await prior_source_digest(database)
    oracle = {str(item.pull_id): item.scenario for item in definition.evaluation_oracle}
    try:
        baseline = evaluate_anomaly_candidate(
            champion,
            rows,
            oracle,
            training_cutoff=definition.cutoff,
            cutoff=definition.evaluation_cutoff,
        )
        candidate = evaluate_anomaly_candidate(
            challenger,
            rows,
            oracle,
            training_cutoff=definition.cutoff,
            cutoff=definition.evaluation_cutoff,
        )
    except ValueError:
        return _not_comparable("EVALUATION_INELIGIBLE")
    if await prior_source_digest(database) != source_before:
        return _not_comparable("PRIOR_SOURCE_MUTATION_DURING_COMPARISON")
    latest = await repository.binding(champion_binding_id)
    if latest is None or not latest.is_active or latest.latest_event_id != binding.latest_event_id:
        return _not_comparable("STALE_CHAMPION_BINDING")
    if baseline["status"] != "SYNTHETIC_EVALUATED" or candidate["status"] != "SYNTHETIC_EVALUATED":
        return _not_comparable("INSUFFICIENT_MATCHED_SUPPORT")

    def delta(key: str) -> float | None:
        old = baseline["target_metrics"].get(key)
        new = candidate["target_metrics"].get(key)
        if old is None or new is None:
            return None
        return float(new) - float(old)

    return {
        "schema_version": "phase10-anomaly-comparison-v1",
        "status": "COMPARABLE_OFFLINE",
        "family": definition.family,
        "source_role": definition.source_role.value,
        "evaluation_dataset_checksum": definition.expected_evaluation_checksum,
        "evaluation_source_fingerprint": definition.expected_evaluation_source_fingerprint,
        "oracle_checksum": definition.expected_oracle_checksum,
        "matched_row_fingerprint": stable_hash(sorted(row.row_id for row in rows)),
        "eligible_rows": len(rows),
        "champion_binding_id": str(binding.id),
        "champion_event_id": str(binding.latest_event_id),
        "champion_detector_version_id": str(binding.detector_version_id),
        "challenger_detector_version_id": str(challenger_version_id),
        "champion_artifact_checksum": champion.artifact_checksum,
        "challenger_artifact_checksum": challenger.artifact_checksum,
        "champion_method": champion.definition.method.value,
        "challenger_method": challenger.definition.method.value,
        "method_score_scales_compared": False,
        "champion_metrics": baseline["target_metrics"],
        "challenger_metrics": candidate["target_metrics"],
        "champion_alert_burden": baseline["alert_burden"],
        "challenger_alert_burden": candidate["alert_burden"],
        "champion_support": baseline["support"],
        "challenger_support": candidate["support"],
        "delta": {
            "recall": delta("recall"),
            "precision": delta("precision"),
            "false_positive_rate": delta("false_positive_rate"),
            "coverage": candidate["alert_burden"]["coverage"]
            - baseline["alert_burden"]["coverage"],
        },
        "abstentions": {
            "champion": baseline["support"]["abstained"],
            "challenger": candidate["support"]["abstained"],
        },
        "real_world_predictive_validity": "NOT_ESTABLISHED",
        "serving_action": "NONE",
        "limitation": (
            "Synthetic anomaly injections support only this frozen engineering comparison. "
            "Scores are not engine-health percentages, failure probabilities or diagnoses."
        ),
    }
