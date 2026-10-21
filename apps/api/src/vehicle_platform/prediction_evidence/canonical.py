"""Versioned canonical JSON and hashing for Phase 9E evidence."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast
from uuid import UUID

EVIDENCE_NAMESPACE = UUID("c97d658f-707d-4343-88de-76d25e07b07f")


def canonical_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("canonical timestamps must be timezone aware")
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("canonical decimals must be finite")
        return format(value.normalize(), "f")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical floats must be finite")
        return value
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): canonical_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [canonical_value(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256(value: Any) -> str:
    encoded = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def canonical_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("evidence timestamps must be timezone aware")
    return value.astimezone(UTC)


def evidence_content_payload(bundle: Any) -> dict[str, Any]:
    payload = bundle.model_dump(mode="json")
    for key in ("evidence_id", "logical_fingerprint", "content_checksum"):
        payload.pop(key, None)
    return cast(dict[str, Any], payload)


def evidence_identity_payload(bundle: Any) -> dict[str, Any]:
    payload = evidence_content_payload(bundle)
    payload.pop("generated_at", None)
    return payload
