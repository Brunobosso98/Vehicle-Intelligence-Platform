from __future__ import annotations

import hashlib
import hmac
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import joblib
from sklearn.ensemble import IsolationForest
from sqlalchemy import text

from vehicle_platform.anomalies.definitions import detector_definition
from vehicle_platform.anomalies.detectors import FittedDetector
from vehicle_platform.anomalies.domain import (
    AnomalyDetectorDefinition,
    CohortIdentity,
    DetectorMethod,
    SourceRole,
)
from vehicle_platform.features.domain import canonical_json
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.artifacts import library_versions

MAX_ARTIFACT_BYTES = 50 * 1024 * 1024
ARTIFACT_ROOT = Path("apps/api/.artifacts/phase9c")
_VERSION_PATTERN = re.compile(r"a[0-9]{8}\Z")
_FAMILY_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")
_METHOD_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")


class AnomalyArtifactError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactReceipt:
    relative_path: str
    checksum: str
    size_bytes: int


@dataclass(frozen=True)
class TrustedAnomalyArtifact:
    detector_version_id: str
    version: str
    definition: AnomalyDetectorDefinition
    fitted: FittedDetector
    reference_dataset_id: str
    reference_checksum: str
    reference_manifest: dict[str, Any]
    cohort: CohortIdentity
    fit_checksum: str
    artifact_checksum: str


class ArtifactStore:
    """Read/write only internally generated registry-backed Phase 9C artifacts."""

    def __init__(self, root: Path = ARTIFACT_ROOT) -> None:
        self.root = root.resolve()

    def write(
        self,
        definition: AnomalyDetectorDefinition,
        fitted: FittedDetector,
        *,
        version: str,
        fit_checksum: str,
    ) -> ArtifactReceipt:
        if not _VERSION_PATTERN.fullmatch(version):
            raise AnomalyArtifactError("invalid internal detector-version token")
        if len(fit_checksum) != 64 or fitted.definition_checksum != definition.checksum:
            raise AnomalyArtifactError("detector artifact metadata is inconsistent")
        if fitted.method is DetectorMethod.ISOLATION_FOREST:
            if not isinstance(fitted.estimator, IsolationForest):
                raise AnomalyArtifactError("Isolation Forest artifact has the wrong estimator type")
        elif fitted.method is not DetectorMethod.ROBUST_MAD or fitted.estimator is not None:
            raise AnomalyArtifactError("robust detector artifact contains an unexpected estimator")
        relative = self._expected_relative(definition, version)
        target = self._checked_path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise AnomalyArtifactError("detector artifact path already exists")
        bundle = {
            "format_version": "phase9c-fitted-v1",
            "definition_key": definition.key,
            "definition_version": definition.version,
            "definition_checksum": definition.checksum,
            "reference_checksum": fitted.reference_checksum,
            "fit_checksum": fit_checksum,
            "version": version,
            "library_versions": library_versions(),
            "fitted_detector": fitted,
        }
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".detector-", suffix=".tmp", dir=target.parent
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            joblib.dump(bundle, temporary, compress=3, protocol=5)
            temporary.chmod(0o600)
            size_bytes = temporary.stat().st_size
            if not 1 <= size_bytes <= MAX_ARTIFACT_BYTES:
                raise AnomalyArtifactError("detector artifact is empty or exceeds the 50 MiB limit")
            os.replace(temporary, target)
            checksum = _file_sha256(target)
            self._verify_staged(
                target,
                checksum,
                definition=definition,
                fitted=fitted,
                version=version,
                fit_checksum=fit_checksum,
            )
            return ArtifactReceipt(relative.as_posix(), checksum, size_bytes)
        except Exception:
            temporary.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise

    def verify_staged(
        self,
        receipt: ArtifactReceipt,
        *,
        definition: AnomalyDetectorDefinition,
        fitted: FittedDetector,
        version: str,
        fit_checksum: str,
    ) -> None:
        relative = Path(receipt.relative_path)
        expected = self._expected_relative(definition, version)
        if relative != expected:
            raise AnomalyArtifactError("staged artifact path differs from its fixed namespace")
        path = self._checked_path(relative)
        if path.is_symlink() or not path.is_file():
            raise AnomalyArtifactError("staged artifact is missing or unsafe")
        if path.stat().st_size != receipt.size_bytes or not hmac.compare_digest(
            _file_sha256(path), receipt.checksum
        ):
            raise AnomalyArtifactError("staged artifact size or checksum changed")
        self._verify_staged(
            path,
            receipt.checksum,
            definition=definition,
            fitted=fitted,
            version=version,
            fit_checksum=fit_checksum,
        )

    async def load_registered(
        self,
        database: Database,
        detector_version_id: str,
    ) -> TrustedAnomalyArtifact:
        async with database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT dv.*,d.key,d.version AS definition_version,d.family,d.method,"
                            "d.definition,d.checksum AS definition_checksum,rd.id AS reference_id,"
                            "rd.checksum AS reference_checksum,rd.manifest AS reference_manifest "
                            "FROM anomaly_detector_versions dv "
                            "JOIN anomaly_detector_definitions d ON d.id=dv.detector_definition_id "
                            "JOIN anomaly_reference_datasets rd ON rd.id=dv.reference_dataset_id "
                            "WHERE dv.id=:id"
                        ),
                        {"id": detector_version_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise AnomalyArtifactError("detector version is not registered")
        if row["state"] not in {"CANDIDATE", "ACCEPTED"}:
            raise AnomalyArtifactError("detector version has no accepted fitted artifact")
        try:
            definition = detector_definition(str(row["family"]), str(row["method"]))
        except ValueError as error:
            raise AnomalyArtifactError(
                "registered detector method is outside the allowlist"
            ) from error
        if (
            definition.key != row["key"]
            or definition.version != row["definition_version"]
            or definition.checksum != row["definition_checksum"]
        ):
            raise AnomalyArtifactError("registered detector definition is incompatible")
        version = str(row["version"])
        expected = self._expected_relative(definition, version)
        if Path(str(row["artifact_path"])) != expected:
            raise AnomalyArtifactError("registered artifact path differs from its fixed namespace")
        path = self._checked_path(expected)
        if path.is_symlink() or not path.is_file():
            raise AnomalyArtifactError("registered detector artifact is missing or unsafe")
        size = path.stat().st_size
        if size != int(row["artifact_size_bytes"]) or not 1 <= size <= MAX_ARTIFACT_BYTES:
            raise AnomalyArtifactError("registered detector artifact size is invalid")
        checksum = _file_sha256(path)
        if not hmac.compare_digest(checksum, str(row["artifact_checksum"])):
            raise AnomalyArtifactError("registered detector artifact checksum mismatch")
        bundle = self._trusted_load(path)
        self._validate_bundle(
            bundle,
            definition=definition,
            version=version,
            fit_checksum=str(row["fit_checksum"]),
        )
        fitted = bundle["fitted_detector"]
        if not isinstance(fitted, FittedDetector):
            raise AnomalyArtifactError("artifact root does not contain the trusted fitted schema")
        if (
            fitted.checksum != str(row["training_metrics"].get("fitted_checksum", ""))
            or fitted.reference_checksum
            != str(row["training_metrics"].get("reference_checksum", ""))
            or fitted.reference_checksum != str(row["reference_checksum"])
            or fitted.threshold != float(row["threshold"])
        ):
            raise AnomalyArtifactError(
                "registered detector training schema does not match artifact"
            )
        if fitted.method is DetectorMethod.ISOLATION_FOREST:
            if not isinstance(fitted.estimator, IsolationForest):
                raise AnomalyArtifactError("registered forest artifact has an unexpected estimator")
        elif fitted.estimator is not None:
            raise AnomalyArtifactError("registered robust artifact contains an estimator")
        reference_manifest = row["reference_manifest"]
        if not isinstance(reference_manifest, dict):
            raise AnomalyArtifactError("registered reference manifest has an unexpected schema")
        cohort_payload = reference_manifest.get("cohort")
        if not isinstance(cohort_payload, dict):
            raise AnomalyArtifactError("registered reference cohort is unavailable")
        try:
            cohort = CohortIdentity(
                vehicle_id=str(cohort_payload["vehicle_id"]),
                configuration_id=(
                    str(cohort_payload["configuration_id"])
                    if cohort_payload.get("configuration_id") is not None
                    else None
                ),
                modification_ids=tuple(str(item) for item in cohort_payload["modification_ids"]),
                source_role=SourceRole(str(cohort_payload["source_role"])),
                source_type=str(cohort_payload["source_type"]),
                compatibility_version=str(cohort_payload["compatibility_version"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise AnomalyArtifactError("registered reference cohort is malformed") from error
        return TrustedAnomalyArtifact(
            detector_version_id=str(row["id"]),
            version=version,
            definition=definition,
            fitted=fitted,
            reference_dataset_id=str(row["reference_id"]),
            reference_checksum=str(row["reference_checksum"]),
            reference_manifest=reference_manifest,
            cohort=cohort,
            fit_checksum=str(row["fit_checksum"]),
            artifact_checksum=checksum,
        )

    def delete_staged(self, receipt: ArtifactReceipt) -> None:
        path = self._checked_path(Path(receipt.relative_path))
        if path.is_file() and hmac.compare_digest(_file_sha256(path), receipt.checksum):
            path.unlink()

    def _verify_staged(
        self,
        path: Path,
        checksum: str,
        *,
        definition: AnomalyDetectorDefinition,
        fitted: FittedDetector,
        version: str,
        fit_checksum: str,
    ) -> None:
        if not hmac.compare_digest(_file_sha256(path), checksum):
            raise AnomalyArtifactError("staged detector artifact checksum mismatch")
        bundle = self._trusted_load(path)
        self._validate_bundle(
            bundle,
            definition=definition,
            version=version,
            fit_checksum=fit_checksum,
        )
        if bundle["fitted_detector"].checksum != fitted.checksum:
            raise AnomalyArtifactError("staged detector fit differs from the fitted input")

    def _validate_bundle(
        self,
        bundle: dict[str, Any],
        *,
        definition: AnomalyDetectorDefinition,
        version: str,
        fit_checksum: str,
    ) -> None:
        expected_keys = {
            "format_version",
            "definition_key",
            "definition_version",
            "definition_checksum",
            "reference_checksum",
            "fit_checksum",
            "version",
            "library_versions",
            "fitted_detector",
        }
        if set(bundle) != expected_keys:
            raise AnomalyArtifactError(
                "detector artifact schema differs from the allowlisted format"
            )
        if (
            bundle.get("format_version") != "phase9c-fitted-v1"
            or bundle.get("definition_key") != definition.key
            or bundle.get("definition_version") != definition.version
            or bundle.get("definition_checksum") != definition.checksum
            or bundle.get("version") != version
            or bundle.get("fit_checksum") != fit_checksum
            or bundle.get("library_versions") != library_versions()
        ):
            raise AnomalyArtifactError("detector artifact metadata is incompatible")
        fitted = bundle.get("fitted_detector")
        if not isinstance(fitted, FittedDetector):
            raise AnomalyArtifactError("detector artifact fitted schema is invalid")
        if (
            fitted.definition_checksum != definition.checksum
            or fitted.reference_checksum != bundle.get("reference_checksum")
            or fitted.method is not definition.method
            or fitted.family is not definition.family
        ):
            raise AnomalyArtifactError("detector artifact family, method, or reference mismatch")

    @staticmethod
    def _trusted_load(path: Path) -> dict[str, Any]:
        # joblib uses pickle semantics; this is reached only after a registry path and SHA check.
        try:
            loaded = joblib.load(path)
        except Exception:
            raise AnomalyArtifactError("trusted detector artifact failed deserialization") from None
        if not isinstance(loaded, dict):
            raise AnomalyArtifactError("detector artifact root must be an internal bundle")
        return cast(dict[str, Any], loaded)

    def _checked_path(self, relative: Path) -> Path:
        if relative.is_absolute() or any(part in {"..", ""} for part in relative.parts):
            raise AnomalyArtifactError("artifact path is outside the controlled namespace")
        unresolved = self.root / relative
        parent = unresolved.parent
        while parent != self.root and self.root in parent.parents:
            if parent.is_symlink():
                raise AnomalyArtifactError("artifact directory contains a symlink")
            parent = parent.parent
        if unresolved.is_symlink():
            raise AnomalyArtifactError("artifact file cannot be a symlink")
        path = unresolved.resolve()
        try:
            path.relative_to(self.root)
        except ValueError as error:
            raise AnomalyArtifactError("artifact path escapes the controlled directory") from error
        return path

    @staticmethod
    def _expected_relative(
        definition: AnomalyDetectorDefinition,
        version: str,
    ) -> Path:
        if not _VERSION_PATTERN.fullmatch(version):
            raise AnomalyArtifactError("invalid registered detector-version token")
        if not _FAMILY_PATTERN.fullmatch(definition.family.value) or not _METHOD_PATTERN.fullmatch(
            definition.method.value
        ):
            raise AnomalyArtifactError("detector artifact namespace is invalid")
        return (
            Path(definition.family.value) / definition.method.value / f"detector-{version}.joblib"
        )


def fit_checksum_for(
    definition: AnomalyDetectorDefinition,
    reference_checksum: str,
) -> str:
    return hashlib.sha256(
        canonical_json(
            {
                "definition_checksum": definition.checksum,
                "reference_checksum": reference_checksum,
                "library_versions": library_versions(),
                "fit_parameters": definition.fit_parameters,
                "normalization_policy": definition.normalization_policy,
                "threshold_policy": definition.threshold_policy,
                "seed": definition.seed,
            }
        ).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
