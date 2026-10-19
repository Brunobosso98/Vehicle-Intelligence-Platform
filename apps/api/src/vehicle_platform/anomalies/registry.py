from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import text

from vehicle_platform.anomalies.artifacts import ArtifactReceipt
from vehicle_platform.anomalies.domain import (
    AnomalyDetectorDefinition,
    AnomalyFindingResult,
    AnomalyReferenceDataset,
    DetectorLifecycle,
    ReferenceRow,
    SourceRole,
)
from vehicle_platform.features.domain import canonical_json, stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import library_versions


class AnomalyRegistryConflict(ValueError):
    pass


class AnomalyRegistry:
    """Persists immutable, checksum-addressed Phase 9C evidence."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def persist_reference(
        self,
        definition: AnomalyDetectorDefinition,
        dataset: AnomalyReferenceDataset,
        *,
        feature_set_version_id: UUID,
    ) -> UUID:
        if definition.family is not dataset.family:
            raise AnomalyRegistryConflict("reference family differs from detector definition")
        manifest = dataset.manifest(definition)
        checksum = dataset.checksum(definition)
        async with self.database.session() as db:
            definition_id = await self._ensure_definition(db, definition)
            reference_id = (
                await db.execute(
                    text(
                        "INSERT INTO anomaly_reference_datasets(detector_definition_id,"
                        "feature_set_version_id,vehicle_id,configuration_id,feature_set_version,"
                        "feature_set_version_checksum,cohort_checksum,observation_cutoff,source_role,"
                        "source_type,policy_version,checksum,row_count,session_count,exclusions,manifest) "
                        "VALUES(:definition,:feature_version,:vehicle,:configuration,:version,"
                        ":version_checksum,:cohort_checksum,:cutoff,:role,:source_type,:policy,:checksum,"
                        ":row_count,:session_count,CAST(:exclusions AS jsonb),CAST(:manifest AS jsonb)) "
                        "ON CONFLICT(detector_definition_id,checksum) DO NOTHING RETURNING id"
                    ),
                    {
                        "definition": definition_id,
                        "feature_version": feature_set_version_id,
                        "vehicle": UUID(dataset.cohort.vehicle_id),
                        "configuration": (
                            UUID(dataset.cohort.configuration_id)
                            if dataset.cohort.configuration_id
                            else None
                        ),
                        "version": dataset.feature_set_version,
                        "version_checksum": dataset.feature_set_version_checksum,
                        "cohort_checksum": dataset.cohort.checksum,
                        "cutoff": dataset.observation_cutoff,
                        "role": dataset.source_role.value,
                        "source_type": dataset.cohort.source_type,
                        "policy": dataset.policy_version,
                        "checksum": checksum,
                        "row_count": len(dataset.rows),
                        "session_count": len({row.session_id for row in dataset.rows}),
                        "exclusions": canonical_json(list(dataset.exclusions)),
                        "manifest": canonical_json(manifest),
                    },
                )
            ).scalar_one_or_none()
            if reference_id is None:
                existing = (
                    (
                        await db.execute(
                            text(
                                "SELECT id,cohort_checksum,feature_set_version_checksum,manifest "
                                "FROM anomaly_reference_datasets WHERE detector_definition_id=:definition "
                                "AND checksum=:checksum"
                            ),
                            {"definition": definition_id, "checksum": checksum},
                        )
                    )
                    .mappings()
                    .one()
                )
                if (
                    existing["cohort_checksum"] != dataset.cohort.checksum
                    or existing["feature_set_version_checksum"]
                    != dataset.feature_set_version_checksum
                    or existing["manifest"] != manifest
                ):
                    raise AnomalyRegistryConflict(
                        "reference checksum conflicts with registered evidence"
                    )
                reference_id = existing["id"]
            else:
                for row in dataset.rows:
                    await db.execute(
                        text(
                            "INSERT INTO anomaly_reference_rows(reference_dataset_id,row_id,feature_set_id,"
                            "vehicle_id,configuration_id,session_id,pull_id,pull_started_at,pull_ended_at,"
                            "observation_cutoff,source_role,source_type,source_hash,provenance_hash,"
                            "modification_ids,available_signals,feature_values,feature_quality,"
                            "feature_missing,feature_availability,quality_metadata) VALUES(:reference,:row_id,"
                            ":feature_set,:vehicle,:configuration,:session,:pull,:started,:ended,:cutoff,:role,"
                            ":source_type,:source_hash,:provenance_hash,CAST(:modifications AS jsonb),"
                            "CAST(:signals AS jsonb),CAST(:values AS jsonb),CAST(:quality AS jsonb),"
                            "CAST(:missing AS jsonb),CAST(:availability AS jsonb),CAST(:metadata AS jsonb))"
                        ),
                        _reference_row_parameters(reference_id, row, definition),
                    )
            await db.commit()
        return cast(UUID, reference_id)

    async def reserve_version(self) -> str:
        async with self.database.session() as db:
            value = (
                await db.execute(text("SELECT nextval('anomaly_detector_version_seq')"))
            ).scalar_one()
        return f"a{int(value):08d}"

    async def persist_detector_version(
        self,
        definition: AnomalyDetectorDefinition,
        *,
        reference_dataset_id: UUID,
        fit_checksum: str,
        state: DetectorLifecycle,
        threshold: float | None,
        artifact: ArtifactReceipt | None,
        rejection_reason: str | None,
        training_metrics: dict[str, Any],
        input_schema: dict[str, Any],
        version: str,
        repository_sha: str,
    ) -> tuple[UUID, str, bool]:
        if state not in {
            DetectorLifecycle.CANDIDATE,
            DetectorLifecycle.ACCEPTED,
            DetectorLifecycle.REJECTED,
        }:
            raise AnomalyRegistryConflict("detector lifecycle state cannot be registered")
        if (state is not DetectorLifecycle.REJECTED) != (
            artifact is not None and threshold is not None
        ):
            raise AnomalyRegistryConflict("detector state and fitted artifact metadata disagree")
        if (state is DetectorLifecycle.REJECTED) != (rejection_reason is not None):
            raise AnomalyRegistryConflict("rejected versions require one bounded reason")
        async with self.database.session() as db:
            definition_id = await self._ensure_definition(db, definition)
            result = await db.execute(
                text(
                    "INSERT INTO anomaly_detector_versions(detector_definition_id,reference_dataset_id,"
                    "version,fit_checksum,algorithm_version,hyperparameters,library_versions,input_schema,"
                    "training_metrics,threshold,artifact_path,artifact_checksum,artifact_size_bytes,"
                    "repository_sha,state,rejection_reason) VALUES(:definition,:reference,:version,:fit,"
                    ":algorithm,CAST(:hyperparameters AS jsonb),CAST(:libraries AS jsonb),"
                    "CAST(:input_schema AS jsonb),CAST(:metrics AS jsonb),:threshold,:artifact_path,"
                    ":artifact_checksum,:artifact_size,:sha,:state,:reason) "
                    "ON CONFLICT(fit_checksum) DO NOTHING RETURNING id"
                ),
                {
                    "definition": definition_id,
                    "reference": reference_dataset_id,
                    "version": version,
                    "fit": fit_checksum,
                    "algorithm": definition.scoring_version,
                    "hyperparameters": canonical_json(definition.fit_parameters),
                    "libraries": canonical_json(library_versions()),
                    "input_schema": canonical_json(input_schema),
                    "metrics": canonical_json(training_metrics),
                    "threshold": threshold,
                    "artifact_path": artifact.relative_path if artifact else None,
                    "artifact_checksum": artifact.checksum if artifact else None,
                    "artifact_size": artifact.size_bytes if artifact else None,
                    "sha": repository_sha,
                    "state": state.value,
                    "reason": rejection_reason,
                },
            )
            version_id = result.scalar_one_or_none()
            created = version_id is not None
            if version_id is None:
                existing = (
                    (
                        await db.execute(
                            text(
                                "SELECT id,version,fit_checksum,state,artifact_checksum FROM "
                                "anomaly_detector_versions WHERE fit_checksum=:fit"
                            ),
                            {"fit": fit_checksum},
                        )
                    )
                    .mappings()
                    .one()
                )
                if (
                    existing["state"] != state.value
                    or existing["reference_dataset_id"] != reference_dataset_id
                ):
                    raise AnomalyRegistryConflict(
                        "fit checksum conflicts with another detector version"
                    )
                version_id = existing["id"]
                version = str(existing["version"])
            await db.commit()
        return cast(UUID, version_id), version, created

    async def persist_run(
        self,
        *,
        run_identity: str,
        detector_version_id: UUID,
        reference_dataset_id: UUID,
        observation_cutoff: datetime,
        source_role: SourceRole,
        input_checksum: str,
        artifact_checksum: str | None,
        requested_count: int,
        findings: tuple[tuple[ReferenceRow, AnomalyFindingResult, str], ...],
        summary: dict[str, Any],
        duration_seconds: float,
        trace_id: str | None = None,
    ) -> tuple[UUID, tuple[UUID, ...], bool]:
        counts: dict[str, int] = {}
        for _, finding, _ in findings:
            counts[finding.status.value] = counts.get(finding.status.value, 0) + 1
        async with self.database.session() as db:
            result = await db.execute(
                text(
                    "INSERT INTO anomaly_detection_runs(run_identity,detector_version_id,"
                    "reference_dataset_id,observation_cutoff,source_role,input_checksum,artifact_checksum,"
                    "status,requested_count,finding_count,status_counts,summary,duration_seconds,trace_id) "
                    "VALUES(:identity,:detector,:reference,:cutoff,:role,:input,:artifact,'COMPLETED',"
                    ":requested,:finding_count,CAST(:counts AS jsonb),CAST(:summary AS jsonb),:duration,:trace) "
                    "ON CONFLICT(run_identity) DO NOTHING RETURNING id"
                ),
                {
                    "identity": run_identity,
                    "detector": detector_version_id,
                    "reference": reference_dataset_id,
                    "cutoff": observation_cutoff,
                    "role": source_role.value,
                    "input": input_checksum,
                    "artifact": artifact_checksum,
                    "requested": requested_count,
                    "finding_count": len(findings),
                    "counts": canonical_json(counts),
                    "summary": canonical_json(summary),
                    "duration": duration_seconds,
                    "trace": trace_id,
                },
            )
            run_id = result.scalar_one_or_none()
            created = run_id is not None
            if run_id is None:
                existing = (
                    (
                        await db.execute(
                            text(
                                "SELECT id,input_checksum,detector_version_id,reference_dataset_id "
                                "FROM anomaly_detection_runs WHERE run_identity=:identity"
                            ),
                            {"identity": run_identity},
                        )
                    )
                    .mappings()
                    .one()
                )
                if (
                    existing["input_checksum"] != input_checksum
                    or existing["detector_version_id"] != detector_version_id
                    or existing["reference_dataset_id"] != reference_dataset_id
                ):
                    raise AnomalyRegistryConflict(
                        "run identity collides with different input evidence"
                    )
                run_id = existing["id"]
                finding_ids = tuple(
                    cast(UUID, item)
                    for item in (
                        await db.execute(
                            text(
                                "SELECT id FROM anomaly_findings WHERE run_id=:run "
                                "ORDER BY pull_id,feature_set_id"
                            ),
                            {"run": run_id},
                        )
                    ).scalars()
                )
                await db.commit()
                return cast(UUID, run_id), finding_ids, False

            for row, finding, identity in findings:
                scoped_identity = stable_hash(
                    {"run_identity": run_identity, "observation_identity": identity}
                )
                values = _finding_parameters(
                    cast(UUID, run_id),
                    detector_version_id,
                    reference_dataset_id,
                    row,
                    finding,
                    scoped_identity,
                    summary,
                    observation_cutoff,
                )
                inserted = await db.execute(
                    text(
                        "INSERT INTO anomaly_findings(run_id,detector_version_id,reference_dataset_id,"
                        "feature_set_id,vehicle_id,configuration_id,session_id,pull_id,finding_identity,"
                        "correlation_group_id,family,horizon,observation_cutoff,source_role,source_hash,"
                        "provenance_hash,score,threshold,status,coverage,observed_features,absent_features,"
                        "contributions,reason_codes,reference_summary,provenance) VALUES(:run,:detector,"
                        ":reference,:feature_set,:vehicle,:configuration,:session,:pull,:identity,:group,"
                        ":family,'AFTER_PULL_OFFLINE',:cutoff,:role,:source_hash,:provenance_hash,:score,"
                        ":threshold,:status,:coverage,CAST(:observed AS jsonb),CAST(:absent AS jsonb),"
                        "CAST(:contributions AS jsonb),CAST(:reasons AS jsonb),CAST(:reference_summary AS jsonb),"
                        "CAST(:provenance AS jsonb)) ON CONFLICT(finding_identity) DO NOTHING RETURNING id"
                    ),
                    values,
                )
                if inserted.scalar_one_or_none() is None:
                    raise AnomalyRegistryConflict(
                        "finding identity was already assigned to another detection run"
                    )
            ordered_finding_ids = tuple(
                cast(UUID, item)
                for item in (
                    await db.execute(
                        text(
                            "SELECT id FROM anomaly_findings WHERE run_id=:run "
                            "ORDER BY pull_id,feature_set_id"
                        ),
                        {"run": run_id},
                    )
                ).scalars()
            )
            await db.commit()
        return cast(UUID, run_id), ordered_finding_ids, created

    async def _ensure_definition(self, db: Any, definition: AnomalyDetectorDefinition) -> UUID:
        await db.execute(
            text(
                "INSERT INTO anomaly_detector_definitions(key,version,family,method,definition,checksum,"
                "lifecycle_status) VALUES(:key,:version,:family,:method,CAST(:definition AS jsonb),:checksum,"
                ":lifecycle) ON CONFLICT(key,version) DO NOTHING"
            ),
            {
                "key": definition.key,
                "version": definition.version,
                "family": definition.family.value,
                "method": definition.method.value,
                "definition": canonical_json(definition.manifest()),
                "checksum": definition.checksum,
                "lifecycle": definition.lifecycle_status.value,
            },
        )
        row = (
            (
                await db.execute(
                    text(
                        "SELECT id,checksum,family,method,definition FROM anomaly_detector_definitions "
                        "WHERE key=:key AND version=:version"
                    ),
                    {"key": definition.key, "version": definition.version},
                )
            )
            .mappings()
            .one()
        )
        if (
            row["checksum"] != definition.checksum
            or row["family"] != definition.family.value
            or row["method"] != definition.method.value
            or row["definition"] != definition.manifest()
        ):
            raise AnomalyRegistryConflict("detector definition key/version is already incompatible")
        return cast(UUID, row["id"])


def repository_sha() -> str:
    provided = os.environ.get("GIT_COMMIT_SHA")
    if provided and len(provided) == 40 and all(char in "0123456789abcdef" for char in provided):
        return provided
    git = shutil.which("git")
    if git is None:
        raise AnomalyRegistryConflict("repository SHA requires git or GIT_COMMIT_SHA")
    try:
        value = subprocess.check_output(  # noqa: S603 - fixed executable and constant arguments
            [git, "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        raise AnomalyRegistryConflict(
            "repository SHA must be supplied by git or GIT_COMMIT_SHA"
        ) from None
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise AnomalyRegistryConflict("repository SHA is invalid")
    return value


def _reference_row_parameters(
    reference_id: Any,
    row: ReferenceRow,
    definition: AnomalyDetectorDefinition,
) -> dict[str, Any]:
    values = {
        key: {
            "value": row.features[key].value,
            "unit": row.features[key].unit,
            "quality": row.features[key].quality,
        }
        for key in definition.feature_keys
        if key in row.features
    }
    qualities = {key: item.quality for key, item in row.features.items()}
    missing = {key: item.missing_reason for key, item in row.features.items() if item.value is None}
    availability = {
        key: {
            "available_at": item.available_at.isoformat() if item.available_at else None,
            "source_window_end": item.source_window_end.isoformat()
            if item.source_window_end
            else None,
            "source_signals": list(item.source_signals),
        }
        for key, item in row.features.items()
    }
    return {
        "reference": reference_id,
        "row_id": row.row_id,
        "feature_set": row.feature_set_id,
        "vehicle": UUID(row.vehicle_id),
        "configuration": UUID(row.configuration_id) if row.configuration_id else None,
        "session": UUID(row.session_id),
        "pull": UUID(row.pull_id),
        "started": row.pull_started_at,
        "ended": row.pull_ended_at,
        "cutoff": row.observation_cutoff,
        "role": row.source_role.value,
        "source_type": row.source_type,
        "source_hash": row.source_hash,
        "provenance_hash": row.provenance_hash,
        "modifications": canonical_json(list(row.modification_ids)),
        "signals": canonical_json(list(row.available_signals)),
        "values": canonical_json(values),
        "quality": canonical_json(qualities),
        "missing": canonical_json(missing),
        "availability": canonical_json(availability),
        "metadata": canonical_json(row.quality_metadata),
    }


def _finding_parameters(
    run_id: UUID,
    detector_version_id: UUID,
    reference_dataset_id: UUID,
    row: ReferenceRow,
    finding: AnomalyFindingResult,
    identity: str,
    reference_summary: dict[str, Any],
    observation_cutoff: datetime,
) -> dict[str, Any]:
    observed = {
        key: {
            "value": row.features[key].value,
            "unit": row.features[key].unit,
            "quality": row.features[key].quality,
        }
        for key in finding.observed_features
        if key in row.features
    }
    unavailable = {
        key: row.features[key].missing_reason
        for key in finding.absent_features
        if key in row.features
    }
    provenance = {
        "source_type": row.source_type,
        "modification_ids": list(row.modification_ids),
        "available_signals": list(row.available_signals),
        "observation_feature_set_id": str(row.feature_set_id),
        "feature_source_hash": row.source_hash,
        "feature_provenance_hash": row.provenance_hash,
        "horizon": "AFTER_PULL_OFFLINE",
        "interpretation": "relative engineering statistical deviation; not diagnosis",
    }
    return {
        "run": run_id,
        "detector": detector_version_id,
        "reference": reference_dataset_id,
        "feature_set": row.feature_set_id,
        "vehicle": UUID(row.vehicle_id),
        "configuration": UUID(row.configuration_id) if row.configuration_id else None,
        "session": UUID(row.session_id),
        "pull": UUID(row.pull_id),
        "identity": identity,
        "group": _correlation_group(row),
        "family": reference_summary["family"],
        "cutoff": observation_cutoff,
        "role": row.source_role.value,
        "source_hash": row.source_hash,
        "provenance_hash": row.provenance_hash,
        "score": finding.score,
        "threshold": finding.threshold,
        "status": finding.status.value,
        "coverage": finding.coverage,
        "observed": canonical_json(observed),
        "absent": canonical_json(unavailable),
        "contributions": canonical_json(list(finding.contributions)),
        "reasons": canonical_json([item.value for item in finding.reasons]),
        "reference_summary": canonical_json(reference_summary),
        "provenance": canonical_json(provenance),
    }


def _correlation_group(row: ReferenceRow) -> str:
    from vehicle_platform.features.domain import stable_hash

    return stable_hash(
        {
            "vehicle": row.vehicle_id,
            "configuration": row.configuration_id,
            "session": row.session_id,
            "pull": row.pull_id,
            "source_hash": row.source_hash,
        }
    )
