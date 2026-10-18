from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import text

from vehicle_platform.features.datasets import DatasetBuild
from vehicle_platform.features.domain import canonical_json
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import library_versions
from vehicle_platform.ml.domain import (
    ModelSpec,
    ModelState,
    SupervisedDataset,
)
from vehicle_platform.ml.training import TaskTrainingResult


class RegistryConflict(ValueError):
    pass


class MLRegistry:
    """Persists immutable supervised snapshots and evaluated offline model versions."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def ensure_definitions(
        self, spec: ModelSpec, input_dataset: DatasetBuild, outcome_dataset: DatasetBuild
    ) -> tuple[UUID, UUID, UUID, UUID, UUID]:
        async with self.database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO label_definitions(key,version,definition,checksum) "
                    "VALUES(:key,:version,CAST(:definition AS jsonb),:checksum) "
                    "ON CONFLICT(key,version) DO NOTHING"
                ),
                {
                    "key": spec.label_definition.key,
                    "version": spec.label_definition.version,
                    "definition": canonical_json(spec.label_definition.manifest()),
                    "checksum": spec.label_definition.checksum,
                },
            )
            label = (
                await db.execute(
                    text(
                        "SELECT id,checksum FROM label_definitions WHERE key=:key AND version=:version"  # noqa: E501
                    ),
                    {"key": spec.label_definition.key, "version": spec.label_definition.version},
                )
            ).one()
            if label.checksum != spec.label_definition.checksum:
                raise RegistryConflict(
                    "label key/version is already registered with another definition"
                )

            model_id = (
                await db.execute(
                    text(
                        "INSERT INTO ml_models(task,description,label_key,prediction_horizon,intended_scope) "  # noqa: E501
                        "VALUES(:task,:description,:label,:horizon,:scope) "
                        "ON CONFLICT(task) DO UPDATE SET task=EXCLUDED.task RETURNING id"
                    ),
                    {
                        "task": spec.task.value,
                        "description": spec.label_definition.description[:500],
                        "label": spec.label_definition.key,
                        "horizon": spec.label_definition.horizon.kind.value,
                        "scope": "offline engineering validation; no diagnosis or failure probability",  # noqa: E501
                    },
                )
            ).scalar_one()
            input_id = await self._ensure_dataset_definition(db, input_dataset)
            outcome_id = await self._ensure_dataset_definition(db, outcome_dataset)
            feature_version_id = (
                await db.execute(
                    text("SELECT id FROM feature_set_versions WHERE version=:version"),
                    {"version": spec.feature_set_version},
                )
            ).scalar_one_or_none()
            if feature_version_id is None:
                raise RegistryConflict("Phase 9A FeatureSetVersion is not registered")
            await db.commit()
        return (
            cast(UUID, label.id),
            cast(UUID, model_id),
            cast(UUID, feature_version_id),
            input_id,
            outcome_id,
        )

    async def persist_dataset(
        self,
        dataset: SupervisedDataset,
        *,
        label_definition_id: UUID,
        feature_set_version_id: UUID,
        input_dataset_definition_id: UUID,
        outcome_dataset_definition_id: UUID,
        repository_sha: str,
    ) -> UUID:
        async with self.database.session() as db:
            result = await db.execute(
                text(
                    "INSERT INTO supervised_datasets(task,label_definition_id,feature_set_version_id,"  # noqa: E501
                    "dataset_definition_id,outcome_dataset_definition_id,repository_sha,source_fingerprint,"
                    "checksum,row_count,exclusion_count,manifest,exclusions) "
                    "VALUES(:task,:label,:feature_version,:input_definition,:outcome_definition,:sha,"
                    ":fingerprint,:checksum,:row_count,:exclusion_count,CAST(:manifest AS jsonb),"
                    "CAST(:exclusions AS jsonb)) ON CONFLICT(task,checksum) DO NOTHING RETURNING id"
                ),
                {
                    "task": dataset.task.value,
                    "label": label_definition_id,
                    "feature_version": feature_set_version_id,
                    "input_definition": input_dataset_definition_id,
                    "outcome_definition": outcome_dataset_definition_id,
                    "sha": repository_sha,
                    "fingerprint": dataset.source_fingerprint,
                    "checksum": dataset.checksum,
                    "row_count": len(dataset.rows),
                    "exclusion_count": len(dataset.exclusions),
                    "manifest": canonical_json(dataset.manifest),
                    "exclusions": canonical_json(list(dataset.exclusions)),
                },
            )
            dataset_id = result.scalar_one_or_none()
            if dataset_id is None:
                existing = (
                    await db.execute(
                        text(
                            "SELECT id,source_fingerprint FROM supervised_datasets WHERE task=:task AND checksum=:checksum"  # noqa: E501
                        ),
                        {"task": dataset.task.value, "checksum": dataset.checksum},
                    )
                ).one()
                if existing.source_fingerprint != dataset.source_fingerprint:
                    raise RegistryConflict("supervised dataset checksum collision")
                dataset_id = existing.id
            else:
                for row in dataset.rows:
                    await db.execute(
                        text(
                            "INSERT INTO supervised_dataset_rows(supervised_dataset_id,row_id,vehicle_id,"  # noqa: E501
                            "configuration_id,session_id,input_pull_id,target_pull_id,input_feature_set_id,"
                            "target_feature_set_id,input_source_hash,target_source_hash,input_started_at,"
                            "input_available_at,target_started_at,target_value,features,missing,feature_quality,"
                            "label_provenance,scenario_family,quality_class) VALUES(:dataset,:row_id,:vehicle,"  # noqa: E501
                            ":configuration,:session,:input_pull,:target_pull,:input_set,:target_set,:input_hash,"
                            ":target_hash,:input_started,:available,:target_started,:target,CAST(:features AS jsonb),"  # noqa: E501
                            "CAST(:missing AS jsonb),CAST(:quality AS jsonb),CAST(:provenance AS jsonb),:scenario,:class)"  # noqa: E501
                        ),
                        {
                            "dataset": dataset_id,
                            "row_id": row.row_id,
                            "vehicle": row.vehicle_id,
                            "configuration": row.configuration_id,
                            "session": row.session_id,
                            "input_pull": row.input_pull_id,
                            "target_pull": row.target_pull_id,
                            "input_set": row.input_feature_set_id,
                            "target_set": row.target_feature_set_id,
                            "input_hash": row.input_source_hash,
                            "target_hash": row.target_source_hash,
                            "input_started": row.input_started_at,
                            "available": row.input_available_at,
                            "target_started": row.target_started_at,
                            "target": row.target,
                            "features": canonical_json(row.features),
                            "missing": canonical_json(row.missing),
                            "quality": canonical_json(row.feature_quality),
                            "provenance": canonical_json(row.label_provenance),
                            "scenario": row.scenario_family,
                            "class": row.quality_class,
                        },
                    )
            await db.commit()
        return cast(UUID, dataset_id)

    async def start_run(
        self,
        dataset: SupervisedDataset,
        *,
        spec: ModelSpec,
        label_definition_id: UUID,
        input_dataset_definition_id: UUID,
        outcome_dataset_definition_id: UUID,
        supervised_dataset_id: UUID,
        repository_sha: str,
        trace_id: str | None = None,
    ) -> UUID:
        started = datetime.now(UTC)
        async with self.database.session() as db:
            run_id = (
                await db.execute(
                    text(
                        "INSERT INTO training_runs(task,label_definition_id,dataset_definition_id,"
                        "outcome_dataset_definition_id,supervised_dataset_id,dataset_checksum,repository_sha,"
                        "model_spec,candidate_models,seed,state,trace_id,started_at) VALUES(:task,:label,"  # noqa: E501
                        ":input_definition,:outcome_definition,:dataset_id,:checksum,:sha,CAST(:spec AS jsonb),"  # noqa: E501
                        "CAST(:candidates AS jsonb),:seed,'TRAINING',:trace_id,:started) RETURNING id"  # noqa: E501
                    ),
                    {
                        "task": dataset.task.value,
                        "label": label_definition_id,
                        "input_definition": input_dataset_definition_id,
                        "outcome_definition": outcome_dataset_definition_id,
                        "dataset_id": supervised_dataset_id,
                        "checksum": dataset.checksum,
                        "sha": repository_sha,
                        "spec": canonical_json(spec.manifest()),
                        "candidates": "[]",
                        "seed": spec.seed,
                        "trace_id": trace_id,
                        "started": started,
                    },
                )
            ).scalar_one()
            await db.commit()
        return cast(UUID, run_id)

    async def finish_run(
        self,
        run_id: UUID,
        *,
        result: TaskTrainingResult | None,
        state: ModelState,
        error_category: str | None = None,
        artifact_checksum: str | None = None,
        model_version_id: UUID | None = None,
    ) -> None:
        async with self.database.session() as db:
            await db.execute(
                text(
                    "UPDATE training_runs SET finished_at=:finished,state=:state,metrics=CAST(:metrics AS jsonb),"  # noqa: E501
                    "candidate_models=CAST(:candidates AS jsonb),selected_model_family=:family,"
                    "artifact_checksum=:artifact,error_category=:error,ml_model_version_id=:model_version "  # noqa: E501
                    "WHERE id=:id AND state='TRAINING'"
                ),
                {
                    "finished": datetime.now(UTC),
                    "state": state.value,
                    "metrics": canonical_json(result.manifest() if result else {}),
                    "candidates": canonical_json(
                        [item.manifest() for item in result.candidates] if result else []
                    ),
                    "family": result.selected_family.value if result else None,
                    "artifact": artifact_checksum,
                    "error": error_category,
                    "model_version": model_version_id,
                    "id": run_id,
                },
            )
            await db.commit()

    async def register_model_version(
        self,
        result: TaskTrainingResult,
        dataset: SupervisedDataset,
        *,
        model_id: UUID,
        label_definition_id: UUID,
        feature_set_version_id: UUID,
        input_dataset_definition_id: UUID,
        outcome_dataset_definition_id: UUID,
        supervised_dataset_id: UUID,
        repository_sha: str,
        version_token: str,
        artifact_path: str,
        artifact_checksum: str,
        state: ModelState,
    ) -> UUID:
        if (
            len(version_token) != 9
            or not version_token.startswith("v")
            or not version_token[1:].isdigit()
        ):
            raise RegistryConflict("invalid reserved model version")
        temporal_range = {
            "train_start": min(row.input_started_at for row in result.split.train).isoformat(),
            "train_end": max(row.target_started_at for row in result.split.train).isoformat(),
            "validation_start": min(
                row.input_started_at for row in result.split.validation
            ).isoformat(),
            "validation_end": max(
                row.target_started_at for row in result.split.validation
            ).isoformat(),
            "test_start": min(row.input_started_at for row in result.split.test).isoformat(),
            "test_end": max(row.target_started_at for row in result.split.test).isoformat(),
        }
        async with self.database.session() as db:
            version_id = (
                await db.execute(
                    text(
                        "INSERT INTO ml_model_versions(ml_model_id,label_definition_id,feature_set_version_id,"  # noqa: E501
                        "dataset_definition_id,outcome_dataset_definition_id,supervised_dataset_id,version,algorithm,"
                        "hyperparameters,random_seed,dataset_checksum,source_fingerprint,train_count,validation_count,"
                        "test_count,temporal_range,metrics,input_schema,threshold,artifact_path,artifact_checksum,"
                        "repository_sha,library_versions,state) VALUES(:model,:label,:feature_version,:input_definition,"  # noqa: E501
                        ":outcome_definition,:dataset_id,:version,:algorithm,CAST(:parameters AS jsonb),:seed,:checksum,"  # noqa: E501
                        ":fingerprint,:train,:validation,:test,CAST(:range AS jsonb),CAST(:metrics AS jsonb),"  # noqa: E501
                        "CAST(:schema AS jsonb),:threshold,:path,:artifact,:sha,CAST(:libraries AS jsonb),:state) RETURNING id"  # noqa: E501
                    ),
                    {
                        "model": model_id,
                        "label": label_definition_id,
                        "feature_version": feature_set_version_id,
                        "input_definition": input_dataset_definition_id,
                        "outcome_definition": outcome_dataset_definition_id,
                        "dataset_id": supervised_dataset_id,
                        "version": version_token,
                        "algorithm": result.selected_family.value,
                        "parameters": canonical_json(result.selected_parameters),
                        "seed": dataset.model_spec.seed,
                        "checksum": dataset.checksum,
                        "fingerprint": dataset.source_fingerprint,
                        "train": len(result.split.train),
                        "validation": len(result.split.validation),
                        "test": len(result.split.test),
                        "range": canonical_json(temporal_range),
                        "metrics": canonical_json(result.manifest()),
                        "schema": canonical_json(result.input_schema),
                        "threshold": result.selected_threshold,
                        "path": artifact_path,
                        "artifact": artifact_checksum,
                        "sha": repository_sha,
                        "libraries": canonical_json(library_versions()),
                        "state": state.value,
                    },
                )
            ).scalar_one()
            await db.commit()
        return cast(UUID, version_id)

    async def reserve_model_version(self) -> str:
        async with self.database.session() as db:
            value = (await db.execute(text("SELECT nextval('ml_model_version_seq')"))).scalar_one()
        return f"v{int(value):08d}"

    async def _ensure_dataset_definition(self, db: Any, dataset: DatasetBuild) -> UUID:
        row = (
            await db.execute(
                text(
                    "SELECT id,checksum FROM dataset_definitions WHERE name=:name AND version=:version"  # noqa: E501
                ),
                {"name": dataset.definition.name, "version": dataset.definition.version},
            )
        ).one_or_none()
        if row is None or row.checksum != dataset.definition.checksum:
            raise RegistryConflict("Phase 9A DatasetDefinition is not registered as built")
        return cast(UUID, row.id)


def repository_sha() -> str:
    import os
    import shutil
    import subprocess

    provided = os.environ.get("GIT_COMMIT_SHA")
    if provided and len(provided) == 40 and all(char in "0123456789abcdef" for char in provided):
        return provided
    git = shutil.which("git")
    if git is None:
        raise RegistryConflict("repository SHA requires git or GIT_COMMIT_SHA")
    try:
        value = subprocess.check_output(  # noqa: S603 - fixed executable and constant git arguments
            [git, "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True, timeout=2
        ).strip()
    except (OSError, subprocess.SubprocessError):
        raise RegistryConflict("repository SHA must be supplied by git or GIT_COMMIT_SHA") from None
    if len(value) != 40:
        raise RegistryConflict("repository SHA is invalid")
    return value
