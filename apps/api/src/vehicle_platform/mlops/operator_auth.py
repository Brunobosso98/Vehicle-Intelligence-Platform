"""Explicit local reviewer authentication for append-only MLOps proposals."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

from vehicle_platform.infrastructure.trusted_files import TrustedFileError, read_bounded_bytes

MAX_REVIEWER_CONFIG_BYTES = 16 * 1024


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("reviewer configuration has duplicate keys")
        result[key] = value
    return result


def authenticated_reviewer() -> tuple[str, str]:
    """Resolve an operator from an owner-only config and a separate secret token."""
    config_value = os.environ.get("MLOPS_REVIEWER_CONFIG", "")
    token = os.environ.get("MLOPS_OPERATOR_TOKEN", "")
    if not config_value or not token or not 32 <= len(token) <= 256:
        raise RuntimeError("reviewer authentication is unavailable")
    path = Path(config_value)
    if not path.is_absolute() or ".." in path.parts or path.name in {"", ".", ".."}:
        raise RuntimeError("reviewer authentication is unavailable")
    try:
        payload = read_bounded_bytes(
            path.parent,
            path,
            maximum_bytes=MAX_REVIEWER_CONFIG_BYTES,
            expected_owner=os.getuid(),
            require_private=True,
        )
        document = json.loads(payload, object_pairs_hook=_unique_object)
    except (OSError, TrustedFileError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("reviewer authentication is unavailable") from error
    if not isinstance(document, dict) or set(document) != {"schema_version", "operators"}:
        raise RuntimeError("reviewer authentication is unavailable")
    if document.get("schema_version") != "phase10-review-auth-v1":
        raise RuntimeError("reviewer authentication is unavailable")
    operators = document.get("operators")
    if not isinstance(operators, list) or not 1 <= len(operators) <= 32:
        raise RuntimeError("reviewer authentication is unavailable")
    expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
    matches: list[tuple[str, str]] = []
    for operator in operators:
        if not isinstance(operator, dict) or set(operator) != {"id", "role", "token_sha256"}:
            raise RuntimeError("reviewer authentication is unavailable")
        operator_id = operator.get("id")
        role = operator.get("role")
        token_hash = operator.get("token_sha256")
        if (
            not isinstance(operator_id, str)
            or not 2 <= len(operator_id.strip()) <= 120
            or not isinstance(role, str)
            or role != "mlops_reviewer"
            or not isinstance(token_hash, str)
            or len(token_hash) != 64
            or any(char not in "0123456789abcdef" for char in token_hash)
        ):
            raise RuntimeError("reviewer authentication is unavailable")
        if hmac.compare_digest(expected, token_hash):
            matches.append((operator_id.strip(), role))
    if len(matches) != 1:
        raise RuntimeError("reviewer authentication is unavailable")
    return matches[0]
