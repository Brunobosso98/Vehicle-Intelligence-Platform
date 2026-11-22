import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from vehicle_platform.agent_evaluation.contracts import AgentEvalCase, SuiteSummary


class CorpusError(ValueError):
    pass


FROZEN_SUITE_VERSION = "phase11-agent-evals-v4"
FROZEN_SUITE_SHA256 = "17de386fd3345a2e004391bd7f0acdd661e471e1f04025639618ba5bdfd771bb"


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CorpusError("duplicate_json_key")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> None:
    raise CorpusError("non_finite_json_number")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_corpus(path: Path) -> tuple[dict[str, Any], tuple[AgentEvalCase, ...], str]:
    try:
        raw = path.read_bytes()
        if len(raw) > 4_000_000:
            raise CorpusError("corpus_too_large")
        document = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
    except CorpusError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorpusError("corpus_unreadable") from exc
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "suite_version",
        "author",
        "frozen",
        "cases",
    }:
        raise CorpusError("corpus_shape_invalid")
    if document["schema_version"] != "1.0" or document["frozen"] is not True:
        raise CorpusError("corpus_version_or_freeze_invalid")
    entries = document["cases"]
    if not isinstance(entries, list) or not entries or len(entries) > 1000:
        raise CorpusError("corpus_case_count_invalid")
    try:
        cases = tuple(AgentEvalCase.model_validate(item) for item in entries)
    except ValidationError as exc:
        raise CorpusError("corpus_case_invalid") from exc
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise CorpusError("corpus_case_ids_not_unique")
    digest = sha256_bytes(canonical_json(document))
    if document["suite_version"] != FROZEN_SUITE_VERSION or digest != FROZEN_SUITE_SHA256:
        raise CorpusError("frozen_suite_checksum_mismatch")
    return document, cases, digest


def summarize(suite_version: str, cases: tuple[AgentEvalCase, ...], digest: str) -> SuiteSummary:
    return SuiteSummary(
        suite_version=suite_version,
        suite_sha256=digest,
        cases=len(cases),
        family_counts=dict(sorted(Counter(case.family.value for case in cases).items())),
        severity_counts=dict(sorted(Counter(case.severity.value for case in cases).items())),
        language_counts=dict(sorted(Counter(case.language for case in cases).items())),
        expected_behavior_counts=dict(
            sorted(Counter(case.expected_behavior.value for case in cases).items())
        ),
    )
