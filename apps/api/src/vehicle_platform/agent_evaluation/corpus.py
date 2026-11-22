import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from vehicle_platform.agent_evaluation.contracts import AgentEvalCase, SuiteSummary


class CorpusError(ValueError):
    pass


FROZEN_SUITE_VERSION = "phase11-agent-evals-v14"
FROZEN_SUITE_SHA256 = "285f94fe2ba3524574c56a2c5781b86157b539ca9fdd15e913292a0dbce99d04"
FROZEN_SUITES = {
    (
        "phase11-agent-evals-v5",
        "suite-v1.json",
    ): "f8e89dda926e64e4586416bd073ed7f86dc0a071a5ec8455db898133f558ac8a",
    (
        "phase11-agent-evals-v6",
        "suite-v2.json",
    ): "ecff27f5c704e7f7a63c9fb7babe209a0c2105b2d964e2e26993a5ab8b124077",
    (
        "phase11-agent-evals-v7",
        "suite-v3.json",
    ): "1ade777c6a8e443f5e5d85ba9ba609f01db1482688060c1c3b4200ce6e2dd7af",
    (
        "phase11-agent-evals-v8",
        "suite-v4.json",
    ): "0a358366be8c4f2d5841467ab58d7314b74fb619397ae43f9d1cc8ee855472e8",
    (
        "phase11-agent-evals-v9",
        "suite-v5.json",
    ): "47fec761139e566fa7cf6304a25259ec7faf73f7aa1ced722605fb5ac07573c5",
    (
        "phase11-agent-evals-v10",
        "suite-v6.json",
    ): "e5f852a6cf9572ed39ad23088ad944d3af22d65ccd8264a7ad583299491f4d4c",
    (
        "phase11-agent-evals-v11",
        "suite-v7.json",
    ): "d6b176b05b1f7f5336a85a8f12907fae387b8499e0cf4399e679329e4482d2dd",
    (
        "phase11-agent-evals-v12",
        "suite-v8.json",
    ): "933045f631bbfb3882f462ff7a41e42b306797989e303bfbbffaa9c3fcb13ea0",
    (
        "phase11-agent-evals-v13",
        "suite-v9.json",
    ): "a0a1a8ae6828f8e24831b9879fa8bc13654883cf868c9f4e1f23211ad1b631cb",
    (
        "phase11-agent-evals-v14",
        "suite-v10.json",
    ): "285f94fe2ba3524574c56a2c5781b86157b539ca9fdd15e913292a0dbce99d04",
    (
        "phase11-agent-evals-v15",
        "suite-v11.json",
    ): "51b9a8560c86c217d60003167714df46b09226f0d06eb21fc0ca9efa146d3cdf",
    (
        "phase11-agent-evals-v16",
        "suite-v12.json",
    ): "37d1c518f002cb39ab063acd3e5857af9fe71190c0e0e9d33c53576d03f6959d",
    (
        "phase11-agent-evals-v17",
        "suite-v13.json",
    ): "98d2ce8f42b4fa64682f3c7a5f0cf03814a3f24fb46d783bfd8080365a7487d0",
    (
        "phase11-agent-evals-v18",
        "suite-v14.json",
    ): "769a231f3994c0fba07e27081a68398beeb198cea78a13106e2202b0aea2390e",
}


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
    expected_digest = FROZEN_SUITES.get((document["suite_version"], path.name))
    if expected_digest is None or digest != expected_digest:
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
        intent_counts=dict(sorted(Counter(case.intent for case in cases).items())),
        source_surface_counts=dict(sorted(Counter(case.source_surface for case in cases).items())),
        attack_family_counts=dict(
            sorted(Counter(case.attack_family or "none" for case in cases).items())
        ),
        route_counts=dict(sorted(Counter(case.expected_route or "none" for case in cases).items())),
        source_role_counts=dict(sorted(Counter(case.source_role for case in cases).items())),
        allowed_tool_counts=dict(
            sorted(Counter(tool for case in cases for tool in case.allowed_tools).items())
        ),
        required_tool_counts=dict(
            sorted(Counter(tool for case in cases for tool in case.required_tools).items())
        ),
        forbidden_tool_counts=dict(
            sorted(Counter(tool for case in cases for tool in case.forbidden_tools).items())
        ),
    )
