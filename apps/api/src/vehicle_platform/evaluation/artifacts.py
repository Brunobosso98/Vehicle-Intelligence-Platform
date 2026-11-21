from __future__ import annotations

import hashlib
import hmac
import importlib.metadata
import json
import os
import re
from pathlib import Path
from typing import Any

from vehicle_platform.evaluation.calibration import (
    CALIBRATOR_ROOT,
    CALIBRATOR_SCHEMA,
    MAX_CALIBRATOR_BYTES,
    FittedCalibrator,
)
from vehicle_platform.evaluation.contracts import CalibrationMethod
from vehicle_platform.infrastructure.trusted_files import (
    TrustedFileError,
    read_bounded_bytes,
    write_exclusive_bytes,
)


class EvaluationArtifactError(ValueError):
    pass


def write_calibrator(
    calibrator: FittedCalibrator,
    *,
    root: Path = CALIBRATOR_ROOT,
    scope: dict[str, Any],
    model_version_id: str,
    model_artifact_checksum: str,
    label_definition_checksum: str,
    dependency_versions: dict[str, str],
    maximum_bytes: int = MAX_CALIBRATOR_BYTES,
) -> tuple[Path, str, int]:
    if (
        not model_version_id
        or not _sha256(model_artifact_checksum)
        or not _sha256(label_definition_checksum)
    ):
        raise EvaluationArtifactError("calibrator source model and label hashes are required")
    if not 1024 <= maximum_bytes <= MAX_CALIBRATOR_BYTES:
        raise EvaluationArtifactError("calibrator byte limit is outside the fixed bound")
    if scope.get("source_role") != "synthetic":
        raise EvaluationArtifactError("calibrator source scope must remain synthetic-only")
    task_scope = scope.get("task")
    if not isinstance(task_scope, str):
        raise EvaluationArtifactError("calibrator task scope is missing")
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", task_scope):
        if "/" in task_scope or "\\" in task_scope or ".." in Path(task_scope).parts:
            raise EvaluationArtifactError("calibrator task path escapes the controlled root")
        raise EvaluationArtifactError("calibrator task scope is malformed")
    supported_dependencies = {"numpy", "scipy", "scikit-learn"}
    if set(dependency_versions) != supported_dependencies:
        raise EvaluationArtifactError("calibrator dependency manifest is incomplete")
    try:
        current_dependencies = {
            name: importlib.metadata.version(name) for name in supported_dependencies
        }
    except importlib.metadata.PackageNotFoundError as error:
        raise EvaluationArtifactError("calibrator dependency is unavailable") from error
    if dependency_versions != current_dependencies:
        raise EvaluationArtifactError("calibrator dependency versions are incompatible")
    body: dict[str, Any] = {
        "schema_version": CALIBRATOR_SCHEMA,
        "artifact_kind": "OFFLINE_RESEARCH_ONLY_NOT_FOR_SERVING",
        "method": calibrator.method.value,
        "task": str(scope["task"]),
        "model_version_id": model_version_id,
        "model_artifact_checksum": model_artifact_checksum,
        "label_definition_checksum": label_definition_checksum,
        "calibration_row_checksum": calibrator.calibration_row_checksum,
        "calibration_rows": calibrator.calibration_row_count,
        "calibration_positive_count": calibrator.calibration_positive_count,
        "calibration_negative_count": calibrator.calibration_negative_count,
        "calibration_cluster_count": calibrator.calibration_cluster_count,
        "scope": scope,
        "parameters": calibrator.parameters,
        "dependency_versions": dependency_versions,
        "not_for_serving": True,
    }
    content = _canonical(body)
    digest = hashlib.sha256(content).hexdigest()
    envelope = {**body, "artifact_checksum": digest}
    payload = _canonical(envelope)
    if len(payload) > maximum_bytes:
        raise EvaluationArtifactError("calibrator artifact exceeds its byte limit")
    relative = Path(str(scope["task"])) / f"{digest}.json"
    trusted_root = Path(os.path.abspath(root))
    path = trusted_root / relative
    try:
        write_exclusive_bytes(trusted_root, relative, payload)
    except FileExistsError:
        verified = read_calibrator(
            path, root=root, expected_checksum=digest, maximum_bytes=maximum_bytes
        )
        if verified != envelope:
            raise EvaluationArtifactError(
                "existing calibrator artifact differs from its checksum"
            ) from None
        return path, digest, len(payload)
    except TrustedFileError as error:
        raise EvaluationArtifactError(str(error)) from error
    return path, digest, len(payload)


def read_calibrator(
    path: Path,
    *,
    root: Path = CALIBRATOR_ROOT,
    expected_checksum: str,
    maximum_bytes: int = MAX_CALIBRATOR_BYTES,
) -> dict[str, Any]:
    if not 1 <= maximum_bytes <= MAX_CALIBRATOR_BYTES:
        raise EvaluationArtifactError("calibrator read limit is outside the fixed bound")
    if not _sha256(expected_checksum):
        raise EvaluationArtifactError("expected calibrator checksum is malformed")
    trusted_root = Path(os.path.abspath(root))
    if path.is_absolute():
        try:
            relative = path.relative_to(trusted_root)
        except ValueError as error:
            raise EvaluationArtifactError("artifact path escapes the controlled root") from error
    else:
        relative = path
    try:
        payload = read_bounded_bytes(
            trusted_root, trusted_root / relative, maximum_bytes=maximum_bytes
        )
        document = json.loads(payload)
    except (TrustedFileError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvaluationArtifactError(
            f"calibrator artifact is missing, unsafe, or invalid JSON: {error}"
        ) from error
    if not isinstance(document, dict):
        raise EvaluationArtifactError("calibrator artifact root must be an object")
    supplied = document.pop("artifact_checksum", None)
    if not isinstance(supplied, str) or not hmac.compare_digest(supplied, expected_checksum):
        raise EvaluationArtifactError("calibrator checksum does not match expected provenance")
    actual = hashlib.sha256(_canonical(document)).hexdigest()
    if not hmac.compare_digest(actual, expected_checksum):
        raise EvaluationArtifactError("calibrator artifact content checksum mismatch")
    required = {
        "schema_version",
        "artifact_kind",
        "method",
        "task",
        "model_version_id",
        "model_artifact_checksum",
        "label_definition_checksum",
        "calibration_row_checksum",
        "calibration_rows",
        "calibration_positive_count",
        "calibration_negative_count",
        "calibration_cluster_count",
        "scope",
        "parameters",
        "dependency_versions",
        "not_for_serving",
    }
    if set(document) != required:
        raise EvaluationArtifactError("calibrator artifact schema is not allowlisted")
    if document["schema_version"] != CALIBRATOR_SCHEMA:
        raise EvaluationArtifactError("calibrator artifact schema version is unsupported")
    if (
        document["artifact_kind"] != "OFFLINE_RESEARCH_ONLY_NOT_FOR_SERVING"
        or document["not_for_serving"] is not True
    ):
        raise EvaluationArtifactError("calibrator artifact is outside the research-only namespace")
    dependency_versions = document["dependency_versions"]
    supported_dependencies = {"numpy", "scipy", "scikit-learn"}
    if (
        not isinstance(dependency_versions, dict)
        or set(dependency_versions) != supported_dependencies
        or any(
            not isinstance(version, str) or not 1 <= len(version) <= 80
            for version in dependency_versions.values()
        )
    ):
        raise EvaluationArtifactError("calibrator dependency manifest is invalid")
    try:
        current_dependencies = {
            name: importlib.metadata.version(name) for name in supported_dependencies
        }
    except importlib.metadata.PackageNotFoundError as error:
        raise EvaluationArtifactError("calibrator dependency is unavailable") from error
    if dependency_versions != current_dependencies:
        raise EvaluationArtifactError("calibrator dependency versions are incompatible")
    try:
        method = CalibrationMethod(document["method"])
    except (TypeError, ValueError) as error:
        raise EvaluationArtifactError("calibrator method is unsupported") from error
    for key in ("model_artifact_checksum", "label_definition_checksum", "calibration_row_checksum"):
        if not _sha256(document[key]):
            raise EvaluationArtifactError("calibrator source checksum is malformed")
    parameters = document["parameters"]
    if not isinstance(parameters, dict):
        raise EvaluationArtifactError("calibrator parameter payload is malformed")
    if method is CalibrationMethod.SIGMOID:
        if set(parameters) != {"intercept", "slope", "input_transform", "epsilon"}:
            raise EvaluationArtifactError("sigmoid parameter schema is not allowlisted")
        if (
            parameters["input_transform"] != "logit_clipped_probability"
            or not isinstance(parameters["intercept"], (float, int))
            or not isinstance(parameters["slope"], (float, int))
            or not 0 <= float(parameters["slope"]) <= 50
            or not 0 < float(parameters["epsilon"]) < 0.01
        ):
            raise EvaluationArtifactError("sigmoid parameters violate their bounds")
    elif method is CalibrationMethod.ISOTONIC:
        if set(parameters) != {"x", "y", "out_of_bounds"}:
            raise EvaluationArtifactError("isotonic parameter schema is not allowlisted")
        x_values, y_values = parameters["x"], parameters["y"]
        if (
            not isinstance(x_values, list)
            or not isinstance(y_values, list)
            or not 2 <= len(x_values) <= 512
            or len(x_values) != len(y_values)
            or parameters["out_of_bounds"] != "clip"
            or any(not isinstance(value, (float, int)) for value in (*x_values, *y_values))
            or any(left > right for left, right in zip(x_values, x_values[1:], strict=False))
            or any(left > right for left, right in zip(y_values, y_values[1:], strict=False))
            or any(not 0 <= float(value) <= 1 for value in (*x_values, *y_values))
        ):
            raise EvaluationArtifactError("isotonic parameters violate monotonicity or bounds")
    elif parameters:
        raise EvaluationArtifactError("identity calibrator cannot carry fitted parameters")
    scope = document["scope"]
    if (
        not isinstance(scope, dict)
        or set(scope)
        != {
            "task",
            "source_role",
            "feature_set_version",
            "label_definition_checksum",
            "vehicle_context_fingerprint",
            "configuration_context_fingerprint",
            "cutoff",
        }
        or scope["task"] != document["task"]
        or not isinstance(scope["task"], str)
        or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", scope["task"])
        or scope["label_definition_checksum"] != document["label_definition_checksum"]
        or scope["source_role"] != "synthetic"
        or not isinstance(scope["feature_set_version"], str)
        or not scope["feature_set_version"]
        or not _sha256(scope["vehicle_context_fingerprint"])
        or not _sha256(scope["configuration_context_fingerprint"])
        or not isinstance(scope["cutoff"], str)
    ):
        raise EvaluationArtifactError("calibrator validity scope is malformed")
    try:
        from datetime import datetime

        cutoff = datetime.fromisoformat(scope["cutoff"])
    except ValueError as error:
        raise EvaluationArtifactError("calibrator cutoff is malformed") from error
    if cutoff.tzinfo is None:
        raise EvaluationArtifactError("calibrator cutoff must be timezone-aware")
    return {**document, "artifact_checksum": supplied}


def _safe_path(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or any(part in {"..", ""} for part in relative.parts):
        raise EvaluationArtifactError("artifact path escapes the controlled namespace")
    return Path(os.path.abspath(root)) / relative


def _sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
