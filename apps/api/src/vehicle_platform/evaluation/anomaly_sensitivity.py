from __future__ import annotations

import math
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr  # type: ignore[import-untyped]
from sqlalchemy import text

from vehicle_platform.anomalies.artifacts import ArtifactStore as AnomalyArtifactStore
from vehicle_platform.anomalies.detectors import DetectorFitError, fit_detector, score_observation
from vehicle_platform.anomalies.domain import AnomalyReferenceDataset, ReferenceRow, SourceRole
from vehicle_platform.anomalies.repository import _reference_row
from vehicle_platform.evaluation.anomaly import FAMILIES, METHODS
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database


class ReferenceSensitivityError(ValueError):
    pass


async def evaluate_reference_size_sensitivity(
    database: Database,
    receipt: dict[str, Any],
    *,
    artifact_roots: tuple[Path, ...],
) -> dict[str, Any]:
    """Refit actual frozen 9C definitions on deterministic whole-session subsets."""
    case_oracles = await _case_oracles(database, receipt)
    output: dict[str, Any] = {"schema_version": "phase9g-reference-sensitivity-v1", "families": {}}
    for family in FAMILIES:
        output["families"][family] = {}
        for method in METHODS:
            result = receipt["test_comparison_after_freeze"][family][method]
            artifact_checksum = str(result.get("artifact_checksum", ""))
            run_id = str(result.get("run_id", ""))
            if not run_id or len(artifact_checksum) != 64:
                raise ReferenceSensitivityError("9C case lacks registered detector identity")
            async with database.session() as db:
                detector_id_value = await db.scalar(
                    text(
                        "SELECT detector_version_id FROM anomaly_detection_runs "
                        "WHERE id=:run_id AND artifact_checksum=:checksum"
                    ),
                    {"run_id": run_id, "checksum": artifact_checksum},
                )
            detector_id = str(detector_id_value or "")
            if not detector_id:
                raise ReferenceSensitivityError("9C scoring run has no matching frozen artifact")
            root = await _find_artifact_root(artifact_roots, database, detector_id)
            artifact = await AnomalyArtifactStore(root).load_registered(database, detector_id)
            if artifact.artifact_checksum != artifact_checksum:
                raise ReferenceSensitivityError(
                    "registered 9C artifact checksum differs from receipt"
                )
            reference = await _load_reference_dataset(
                database, artifact.reference_dataset_id, artifact
            )
            test_cases = await _load_test_cases(
                database,
                artifact,
                case_oracles,
            )
            output["families"][family][method] = _fit_reference_subsets(
                artifact,
                reference,
                test_cases,
            )
    output["fit_data_oracle_labels_used"] = False
    output["original_registry_thresholds_mutated"] = False
    output["source_reference_rows_mutated"] = False
    return output


async def _case_oracles(database: Database, receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Bind the report's ordered fold oracles to canonical disposable DB pulls."""
    output: dict[str, dict[str, Any]] = {}
    reports: dict[str, list[dict[str, Any]]] = {}
    for family in FAMILIES:
        for method in METHODS:
            rows = receipt["test_comparison_after_freeze"][family][method].get("case_evaluation")
            if not isinstance(rows, list):
                raise ReferenceSensitivityError("9C report lacks test case identities")
            reports[f"{family}/{method}"] = rows

    first_rows = next(iter(reports.values()))
    if not first_rows:
        raise ReferenceSensitivityError("9C report contains no untouched test cases")
    for key, rows in reports.items():
        if [(row.get("fold"), row.get("scenario")) for row in rows] != [
            (row.get("fold"), row.get("scenario")) for row in first_rows
        ]:
            raise ReferenceSensitivityError(f"9C test oracle order differs for {key}")

    async with database.session() as db:
        sessions = (
            (
                await db.execute(
                    text(
                        "SELECT s.id FROM driving_sessions s JOIN vehicles v ON v.id=s.vehicle_id "
                        "WHERE v.model='N55-9C-primary' ORDER BY s.started_at,s.id"
                    )
                )
            )
            .scalars()
            .all()
        )
        if len(sessions) != 15:
            raise ReferenceSensitivityError("canonical Phase 9C primary fold layout changed")
        fold_pulls: dict[str, list[str]] = {}
        for fold_name in sorted({str(row.get("fold", "")) for row in first_rows}):
            if (
                not fold_name.startswith("session_")
                or not fold_name.removeprefix("session_").isdigit()
            ):
                raise ReferenceSensitivityError("9C test fold name is malformed")
            session_index = int(fold_name.removeprefix("session_"))
            if session_index >= len(sessions):
                raise ReferenceSensitivityError("9C test fold falls outside source sessions")
            pull_ids = (
                (
                    await db.execute(
                        text(
                            "SELECT id FROM pulls WHERE session_id=:session ORDER BY started_at,id"
                        ),
                        {"session": sessions[session_index]},
                    )
                )
                .scalars()
                .all()
            )
            fold_pulls[fold_name] = [stable_hash(str(item)) for item in pull_ids]

    report_pulls: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in first_rows:
        row_fold = row.get("fold")
        scenario = row.get("scenario")
        if not isinstance(row_fold, str) or not isinstance(scenario, str) or not scenario:
            raise ReferenceSensitivityError("9C test oracle fold or scenario is missing")
        report_pulls[row_fold].append(row)
    for fold, pull_fingerprints in fold_pulls.items():
        oracle_rows = report_pulls.get(fold, [])
        if len(oracle_rows) != len(pull_fingerprints):
            raise ReferenceSensitivityError("9C report fold support differs from source pulls")
        for fingerprint, row in zip(pull_fingerprints, oracle_rows, strict=True):
            output[fingerprint] = {
                "scenario": str(row["scenario"]),
                "fold": fold,
                "source_score": row.get("score"),
                "source_alarm": row.get("predicted_anomaly"),
            }
    if len(output) != len(first_rows):
        raise ReferenceSensitivityError("9C oracle mapping duplicated a source pull")
    return output


async def _find_artifact_root(
    roots: tuple[Path, ...], database: Database, detector_id: str
) -> Path:
    async with database.session() as db:
        relative = await db.scalar(
            text("SELECT artifact_path FROM anomaly_detector_versions WHERE id=:id"),
            {"id": detector_id},
        )
    if not isinstance(relative, str):
        raise ReferenceSensitivityError("registered detector path is missing")
    for root in roots:
        path = root / relative
        if path.is_file() and not path.is_symlink():
            return root
    raise ReferenceSensitivityError("registered detector artifact file is unavailable")


async def _load_reference_dataset(
    database: Database, reference_id: str, artifact: Any
) -> AnomalyReferenceDataset:
    async with database.session() as db:
        metadata = (
            (
                await db.execute(
                    text(
                        "SELECT rd.*,v.version AS source_feature_set_version "
                        "FROM anomaly_reference_datasets rd "
                        "JOIN feature_set_versions v ON v.id=rd.feature_set_version_id "
                        "WHERE rd.id=:id"
                    ),
                    {"id": reference_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if metadata is None:
            raise ReferenceSensitivityError("registered detector reference dataset is missing")
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT ar.row_id AS stored_row_id,ar.source_hash AS stored_source_hash,"
                        "ar.provenance_hash AS stored_provenance_hash,fs.*,"
                        "p.started_at AS pull_started_at,p.ended_at AS pull_ended_at,s.source_type "
                        "FROM anomaly_reference_rows ar "
                        "JOIN feature_sets fs ON fs.id=ar.feature_set_id "
                        "JOIN pulls p ON p.id=fs.pull_id "
                        "JOIN driving_sessions s ON s.id=fs.session_id "
                        "WHERE ar.reference_dataset_id=:reference_id "
                        "ORDER BY p.started_at,p.session_id,p.id"
                    ),
                    {"reference_id": reference_id},
                )
            )
            .mappings()
            .all()
        )
    reference_rows: list[ReferenceRow] = []
    for row in rows:
        parsed = _reference_row(row, artifact.definition.feature_keys)
        if (
            parsed.row_id != row["stored_row_id"]
            or parsed.source_hash != row["stored_source_hash"]
            or parsed.provenance_hash != row["stored_provenance_hash"]
        ):
            raise ReferenceSensitivityError("source FeatureSet differs from frozen 9C reference")
        reference_rows.append(parsed)
    manifest = metadata["manifest"]
    dataset = AnomalyReferenceDataset(
        family=artifact.definition.family,
        feature_set_version=str(metadata["feature_set_version"]),
        feature_set_version_checksum=str(metadata["feature_set_version_checksum"]),
        observation_cutoff=metadata["observation_cutoff"],
        cohort=artifact.cohort,
        rows=tuple(reference_rows),
        exclusions=tuple(metadata["exclusions"] or ()),
        source_role=SourceRole(str(metadata["source_role"])),
        created_at=metadata["created_at"],
        anchor_session_id=manifest.get("anchor_session_id"),
        policy_version=str(metadata["policy_version"]),
    )
    if (
        dataset.checksum(artifact.definition) != artifact.reference_checksum
        or str(metadata["checksum"]) != artifact.reference_checksum
        or str(metadata["source_feature_set_version"]) != dataset.feature_set_version
    ):
        raise ReferenceSensitivityError("9C frozen reference checksum or version is inconsistent")
    return dataset


async def _load_test_cases(
    database: Database,
    artifact: Any,
    oracles: dict[str, dict[str, Any]],
) -> tuple[tuple[ReferenceRow, dict[str, Any]], ...]:
    async with database.session() as db:
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT fs.*,p.started_at AS pull_started_at,p.ended_at AS pull_ended_at,"
                        "s.source_type FROM feature_sets fs "
                        "JOIN pulls p ON p.id=fs.pull_id "
                        "JOIN driving_sessions s ON s.id=fs.session_id "
                        "JOIN feature_set_versions v ON v.id=fs.feature_set_version_id "
                        "WHERE fs.entity_scope='pull' AND v.version=:version "
                        "ORDER BY p.started_at,p.session_id,p.id"
                    ),
                    {"version": artifact.reference_manifest["feature_set_version"]},
                )
            )
            .mappings()
            .all()
        )
    selected: dict[str, tuple[ReferenceRow, dict[str, Any]]] = {}
    for row in rows:
        pull_fingerprint = stable_hash(str(row["pull_id"]))
        oracle = oracles.get(pull_fingerprint)
        if oracle is None:
            continue
        observation = _reference_row(row, artifact.definition.feature_keys)
        selected[pull_fingerprint] = observation, oracle
    if set(selected) != set(oracles):
        raise ReferenceSensitivityError(
            "some 9C test cases cannot be resolved to canonical FeatureSets"
        )
    return tuple(selected[key] for key in sorted(selected))


def _fit_reference_subsets(
    artifact: Any,
    reference: AnomalyReferenceDataset,
    test_cases: tuple[tuple[ReferenceRow, dict[str, Any]], ...],
) -> dict[str, Any]:
    sessions: dict[str, list[ReferenceRow]] = defaultdict(list)
    for row in reference.rows:
        sessions[row.session_id].append(row)
    ordered_sessions = sorted(
        sessions,
        key=lambda item: (min(row.pull_started_at for row in sessions[item]), item),
    )
    if len(ordered_sessions) < 5:
        raise ReferenceSensitivityError(
            "reference-size experiment requires at least five source sessions"
        )
    source_scores = {
        stable_hash(str(observation.pull_id)): oracle.get("source_score")
        for observation, oracle in test_cases
    }
    source_alarms = {
        stable_hash(str(observation.pull_id)): oracle.get("source_alarm")
        for observation, oracle in test_cases
    }
    levels = sorted(
        {max(5, math.ceil(len(ordered_sessions) * fraction)) for fraction in (0.625, 0.75, 1.0)}
    )
    results: list[dict[str, Any]] = []
    for session_count in levels:
        indexes = np.linspace(0, len(ordered_sessions) - 1, session_count).round().astype(int)
        selected_sessions = {ordered_sessions[int(index)] for index in indexes}
        subset_rows = tuple(row for row in reference.rows if row.session_id in selected_sessions)
        subset = AnomalyReferenceDataset(
            family=reference.family,
            feature_set_version=reference.feature_set_version,
            feature_set_version_checksum=reference.feature_set_version_checksum,
            observation_cutoff=reference.observation_cutoff,
            cohort=reference.cohort,
            rows=subset_rows,
            exclusions=reference.exclusions,
            source_role=reference.source_role,
            created_at=reference.created_at,
            anchor_session_id=reference.anchor_session_id,
            policy_version=reference.policy_version,
        )
        entry: dict[str, Any] = {
            "reference_rows": len(subset_rows),
            "reference_sessions": len(selected_sessions),
            "reference_span_days": subset.temporal_span.total_seconds() / 86_400,
            "reference_fingerprint": subset.checksum(artifact.definition),
            "test_case_count": len(test_cases),
        }
        try:
            fitted = fit_detector(artifact.definition, subset)
        except DetectorFitError as error:
            entry.update(
                {
                    "status": "REFERENCE_INSUFFICIENT",
                    "reason_code": error.reason.value,
                    "scored": 0,
                    "abstained": len(test_cases),
                }
            )
            results.append(entry)
            continue
        scored: list[dict[str, Any]] = []
        for observation, oracle in test_cases:
            result = score_observation(
                artifact.definition,
                fitted,
                observation,
                observation_cutoff=observation.pull_ended_at + timedelta(seconds=1),
            )
            scored.append(
                {
                    **oracle,
                    "score": result.score,
                    "alarm": result.score is not None and result.score > fitted.threshold,
                    "status": result.status.value,
                    "fingerprint": stable_hash(observation.row_id),
                    "source_score": source_scores.get(stable_hash(str(observation.pull_id))),
                    "source_alarm": source_alarms.get(stable_hash(str(observation.pull_id))),
                }
            )
        eligible = [row for row in scored if row["score"] is not None]
        clean = [row for row in eligible if row["scenario"] == "clean"]
        target = [row for row in eligible if row["scenario"] == artifact.definition.family.value]
        cross = [
            row
            for row in eligible
            if row["scenario"] in FAMILIES and row["scenario"] != artifact.definition.family.value
        ]
        parity = [row for row in eligible if row["source_alarm"] is not None]
        paired = [
            (float(row["source_score"]), float(row["score"]))
            for row in eligible
            if row["source_score"] is not None
        ]
        correlation_value = (
            float(spearmanr([item[0] for item in paired], [item[1] for item in paired]).statistic)
            if len(paired) >= 3
            else None
        )
        correlation = (
            correlation_value
            if correlation_value is not None and math.isfinite(correlation_value)
            else None
        )
        entry.update(
            {
                "status": "SCORED",
                "threshold_reestimated_from_subset": fitted.threshold,
                "scored": len(eligible),
                "abstained": len(test_cases) - len(eligible),
                "clean_false_alarm": {
                    "alarms": sum(bool(row["alarm"]) for row in clean),
                    "scored_denominator": len(clean),
                    "eligible_denominator": sum(row["scenario"] == "clean" for row in scored),
                },
                "target_family_detection": {
                    "alarms": sum(bool(row["alarm"]) for row in target),
                    "scored_denominator": len(target),
                    "eligible_denominator": sum(
                        row["scenario"] == artifact.definition.family.value for row in scored
                    ),
                },
                "cross_family_alarm": {
                    "alarms": sum(bool(row["alarm"]) for row in cross),
                    "scored_denominator": len(cross),
                },
                "frozen_artifact_stability": {
                    "alarm_parity_count": sum(
                        bool(row["alarm"]) == bool(row["source_alarm"]) for row in parity
                    ),
                    "paired_scored_count": len(parity),
                    "score_rank_spearman": correlation,
                    "source_threshold_mutated": False,
                },
                "observations": [
                    {
                        "fingerprint": row["fingerprint"],
                        "scenario": row["scenario"],
                        "fold": row["fold"],
                        "source_score": row["source_score"],
                        "source_alarm": row["source_alarm"],
                        "score": row["score"],
                        "alarm": row["alarm"],
                        "status": row["status"],
                        "threshold": fitted.threshold,
                    }
                    for row in scored
                ],
                "oracle_labels_used_for_fit": False,
            }
        )
        results.append(entry)
    return {
        "registered_detector_version_id": artifact.detector_version_id,
        "registered_artifact_checksum": artifact.artifact_checksum,
        "frozen_threshold": artifact.fitted.threshold,
        "method_local_scale_only": True,
        "size_levels": results,
        "source_scores_are_reference": False,
    }
