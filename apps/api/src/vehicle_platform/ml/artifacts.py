from __future__ import annotations

import hashlib
import hmac
import os
import re
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, cast

import joblib
import numpy as np
from sqlalchemy import text

from vehicle_platform.features.domain import MissingReason
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.domain import MLModelVersion, MLTask, ModelState
from vehicle_platform.ml.labels import get_model_spec
from vehicle_platform.ml.training import matrix_for_feature_mapping

MAX_ARTIFACT_BYTES = 50 * 1024 * 1024
ARTIFACT_ROOT = Path("apps/api/.artifacts/phase9b")
_VERSION_PATTERN = re.compile(r"v[0-9]{4,8}\Z")
_ALLOWED_FAMILIES = {"dummy", "logistic_regression", "random_forest"}


class ArtifactValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactReceipt:
    relative_path: str
    checksum: str
    size_bytes: int


@dataclass(frozen=True)
class TrustedModelArtifact:
    model_version: MLModelVersion
    estimator: Any
    input_schema: dict[str, Any]
    model_spec_checksum: str


class ArtifactStore:
    """Read/write only internally generated registered artifacts under one fixed root."""

    def __init__(self, root: Path = ARTIFACT_ROOT) -> None:
        self.root = root.resolve()

    def write(
        self,
        task: MLTask,
        model_version: str,
        *,
        estimator: Any,
        input_schema: dict[str, Any],
        threshold: float,
        model_spec_checksum: str,
        family: str,
    ) -> ArtifactReceipt:
        if family not in _ALLOWED_FAMILIES:
            raise ArtifactValidationError("estimator family is outside the fixed allowlist")
        if not _VERSION_PATTERN.fullmatch(model_version):
            raise ArtifactValidationError("invalid internal model-version token")
        if not 0 < threshold < 1 or len(model_spec_checksum) != 64:
            raise ArtifactValidationError("invalid model artifact metadata")
        relative = Path(task.value) / f"model-{model_version}.joblib"
        target = self._checked_path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ArtifactValidationError("model artifact path already exists")
        bundle = {
            "task": task.value,
            "family": family,
            "estimator": estimator,
            "input_schema": input_schema,
            "threshold": threshold,
            "model_spec_checksum": model_spec_checksum,
            "library_versions": library_versions(),
        }
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".model-", suffix=".tmp", dir=target.parent
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            joblib.dump(bundle, temporary, compress=3, protocol=5)
            temporary.chmod(0o600)
            size_bytes = temporary.stat().st_size
            if size_bytes > MAX_ARTIFACT_BYTES:
                raise ArtifactValidationError("model artifact exceeds the 50 MiB limit")
            os.replace(temporary, target)
            checksum = _file_sha256(target)
            self._verify_trusted_bundle(target, checksum, task, family, input_schema, threshold)
            return ArtifactReceipt(relative.as_posix(), checksum, size_bytes)
        except Exception:
            temporary.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise

    def verify_staged(
        self,
        receipt: ArtifactReceipt,
        *,
        task: MLTask,
        family: str,
        input_schema: dict[str, Any],
        threshold: float,
        model_spec_checksum: str,
        smoke_matrix: np.ndarray,
    ) -> float:
        relative = Path(receipt.relative_path)
        path = self._checked_path(relative)
        if path.is_symlink() or not path.is_file():
            raise ArtifactValidationError("staged artifact is missing or unsafe")
        if path.stat().st_size != receipt.size_bytes or not hmac.compare_digest(
            _file_sha256(path), receipt.checksum
        ):
            raise ArtifactValidationError("staged artifact size or checksum changed")
        bundle = self._trusted_load(path)
        if (
            bundle.get("task") != task.value
            or bundle.get("family") != family
            or bundle.get("input_schema") != input_schema
            or bundle.get("threshold") != threshold
            or bundle.get("model_spec_checksum") != model_spec_checksum
            or bundle.get("library_versions") != library_versions()
        ):
            raise ArtifactValidationError("staged artifact metadata failed smoke validation")
        probabilities = np.asarray(
            bundle["estimator"].predict_proba(smoke_matrix), dtype=np.float64
        )
        if probabilities.shape != (len(smoke_matrix), 2) or not np.isfinite(probabilities).all():
            raise ArtifactValidationError("staged artifact failed the offline prediction smoke")
        if np.any((probabilities < 0.0) | (probabilities > 1.0)):
            raise ArtifactValidationError(
                "staged artifact returned values outside probability bounds"
            )
        return float(probabilities[0, 1])

    def delete_staged(self, receipt: ArtifactReceipt) -> None:
        path = self._checked_path(Path(receipt.relative_path))
        if path.is_file() and hmac.compare_digest(_file_sha256(path), receipt.checksum):
            path.unlink()

    async def load_registered(
        self, database: Database, model_version_id: str
    ) -> TrustedModelArtifact:
        async with database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT mv.*,m.task FROM ml_model_versions mv "
                            "JOIN ml_models m ON m.id=mv.ml_model_id WHERE mv.id=:id"
                        ),
                        {"id": model_version_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise ArtifactValidationError("model version is not registered")
        if row["state"] != "CANDIDATE":
            raise ArtifactValidationError("only internally registered candidate artifacts can load")
        task = MLTask(str(row["task"]))
        family = str(row["algorithm"])
        if family not in _ALLOWED_FAMILIES:
            raise ArtifactValidationError("registered estimator family is outside the allowlist")
        expected_relative = Path(task.value) / f"model-{row['version']}.joblib"
        if Path(str(row["artifact_path"])) != expected_relative:
            raise ArtifactValidationError("registered artifact path differs from the expected path")
        path = self._checked_path(expected_relative)
        if path.is_symlink() or not path.is_file():
            raise ArtifactValidationError("registered model artifact is missing or unsafe")
        if path.stat().st_size > MAX_ARTIFACT_BYTES:
            raise ArtifactValidationError("registered model artifact exceeds the size limit")
        checksum = _file_sha256(path)
        if not hmac.compare_digest(checksum, str(row["artifact_checksum"])):
            raise ArtifactValidationError("registered model artifact checksum mismatch")
        bundle = self._trusted_load(path)
        spec = get_model_spec(task)
        if bundle.get("task") != task.value or bundle.get("family") != family:
            raise ArtifactValidationError("registered model artifact identity mismatch")
        if bundle.get("model_spec_checksum") != spec.checksum:
            raise ArtifactValidationError("registered artifact ModelSpec is incompatible")
        if bundle.get("input_schema") != row["input_schema"]:
            raise ArtifactValidationError("registered artifact input schema mismatch")
        if bundle.get("threshold") != row["threshold"]:
            raise ArtifactValidationError("registered artifact threshold mismatch")
        if bundle.get("library_versions") != dict(row["library_versions"]):
            raise ArtifactValidationError(
                "model library versions differ from the registered artifact"
            )
        record = MLModelVersion(
            id=row["id"],
            model_id=row["ml_model_id"],
            task=task,
            version=str(row["version"]),
            algorithm=family,
            hyperparameters=dict(row["hyperparameters"]),
            random_seed=int(row["random_seed"]),
            feature_set_version_id=row["feature_set_version_id"],
            dataset_definition_id=row["dataset_definition_id"],
            outcome_dataset_definition_id=row["outcome_dataset_definition_id"],
            supervised_dataset_id=row["supervised_dataset_id"],
            label_definition_id=row["label_definition_id"],
            dataset_checksum=str(row["dataset_checksum"]),
            train_count=int(row["train_count"]),
            validation_count=int(row["validation_count"]),
            test_count=int(row["test_count"]),
            temporal_range=dict(row["temporal_range"]),
            metrics=dict(row["metrics"]),
            input_schema=dict(row["input_schema"]),
            threshold=float(row["threshold"]),
            artifact_path=str(row["artifact_path"]),
            artifact_checksum=checksum,
            repository_sha=str(row["repository_sha"]),
            library_versions=dict(row["library_versions"]),
            state=ModelState(str(row["state"])),
            created_at=row["created_at"],
        )
        return TrustedModelArtifact(
            record,
            bundle["estimator"],
            dict(bundle["input_schema"]),
            str(bundle["model_spec_checksum"]),
        )

    def _checked_path(self, relative: Path) -> Path:
        if relative.is_absolute() or any(part in {"..", ""} for part in relative.parts):
            raise ArtifactValidationError("artifact path is outside the controlled namespace")
        unresolved = self.root / relative
        parent = unresolved.parent
        while parent != self.root and self.root in parent.parents:
            if parent.is_symlink():
                raise ArtifactValidationError("artifact directory contains a symlink")
            parent = parent.parent
        if unresolved.is_symlink():
            raise ArtifactValidationError("artifact file cannot be a symlink")
        path = unresolved.resolve()
        try:
            path.relative_to(self.root)
        except ValueError as error:
            raise ArtifactValidationError(
                "artifact path escapes the controlled directory"
            ) from error
        return path

    def _verify_trusted_bundle(
        self,
        path: Path,
        checksum: str,
        task: MLTask,
        family: str,
        input_schema: dict[str, Any],
        threshold: float,
    ) -> None:
        if not hmac.compare_digest(_file_sha256(path), checksum):
            raise ArtifactValidationError("staged model artifact checksum mismatch")
        bundle = self._trusted_load(path)
        if (
            bundle.get("task") != task.value
            or bundle.get("family") != family
            or bundle.get("input_schema") != input_schema
            or bundle.get("threshold") != threshold
        ):
            raise ArtifactValidationError("staged model artifact metadata mismatch")

    @staticmethod
    def _trusted_load(path: Path) -> dict[str, Any]:
        # joblib is pickle-based; callers must establish internal provenance and checksum first.
        loaded = joblib.load(path)
        if not isinstance(loaded, dict):
            raise ArtifactValidationError("artifact root must be an internal model bundle")
        return cast(dict[str, Any], loaded)


def offline_predict(
    artifact: TrustedModelArtifact,
    *,
    feature_set_version: str,
    features: Mapping[str, Any],
    units: Mapping[str, str | None],
    missing: Mapping[str, str],
    feature_quality: Mapping[str, str],
) -> dict[str, Any]:
    model = artifact.model_version
    spec = get_model_spec(model.task)
    schema = artifact.input_schema
    required = tuple(str(item) for item in schema["raw_feature_order"])
    if feature_set_version != model.input_schema["feature_set_version"]:
        raise ArtifactValidationError("offline input FeatureSetVersion is incompatible")
    if tuple(features.keys()) != required or tuple(units.keys()) != required:
        raise ArtifactValidationError(
            "offline input feature keys/order differ from the registered schema"
        )
    if set(missing) - set(required) or set(feature_quality) != set(required):
        raise ArtifactValidationError(
            "offline input quality metadata differs from the registered schema"
        )
    expected_units = {
        item["key"]: item["unit"] or None
        for item in schema["matrix_columns"]
        if "__missing__" not in item["key"]
    }
    if dict(units) != expected_units:
        raise ArtifactValidationError("offline input units differ from the registered schema")
    values: dict[str, float | None] = {}
    missing_values = dict(missing)
    for key in required:
        raw = features[key]
        quality = feature_quality[key]
        if quality not in {"valid", "limited", "unavailable", "invalid"}:
            raise ArtifactValidationError(f"offline input quality for {key} is invalid")
        if raw is None:
            reason = missing_values.get(key)
            if reason not in {item.value for item in MissingReason}:
                raise ArtifactValidationError(f"offline missing feature {key} has no valid reason")
            if quality not in {"unavailable", "invalid", "limited"}:
                raise ArtifactValidationError(
                    f"offline missing feature {key} has incompatible quality"
                )
            values[key] = None
            continue
        if (
            isinstance(raw, bool)
            or not isinstance(raw, (int, float))
            or not np.isfinite(float(raw))
        ):
            raise ArtifactValidationError(f"offline numeric feature {key} has the wrong dtype")
        if key in missing_values or quality not in {"valid", "limited"}:
            raise ArtifactValidationError(
                f"offline available feature {key} has incompatible quality metadata"
            )
        values[key] = float(raw)
    matrix = matrix_for_feature_mapping(values, missing_values, spec)
    probabilities = np.asarray(artifact.estimator.predict_proba(matrix), dtype=np.float64)
    if probabilities.shape != (1, 2) or not np.isfinite(probabilities).all():
        raise ArtifactValidationError("offline model returned an invalid probability")
    score = float(probabilities[0, 1])
    return {
        "task": model.task.value,
        "observable_behavior_prediction": bool(score >= model.threshold),
        "engineering_validation_score": score,
        "decision_threshold": model.threshold,
        "probability_is_real_world_failure_probability": False,
        "interpretation": "engineering-validation score, not a mechanical failure probability",
    }


def library_versions() -> dict[str, str]:
    result = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"  # noqa: E501
    }
    for package in ("scikit-learn", "numpy", "scipy", "joblib"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = "unavailable"
    return result


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
