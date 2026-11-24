import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from vehicle_platform.agent_evaluation.contracts import AgentEvalCase, SuiteSummary


class CorpusError(ValueError):
    pass


FROZEN_SUITE_VERSION = "phase11-agent-evals-v49"
FROZEN_SUITE_SHA256 = "7177d97bc7313fa7dd9fb3191187c8515c20e69e1d231e99e64e095f5d9897b1"
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
    (
        "phase11-agent-evals-v19",
        "suite-v15.json",
    ): "e14469f3e2a6e7deb8139a713ceb1d414fc62be5cdb0ae7c8f8c4f1db859ca67",
    (
        "phase11-agent-evals-v20",
        "suite-v16.json",
    ): "85df473a144b254976ef897566623f399464ae795137bf10dfc96e42392265fb",
    (
        "phase11-agent-evals-v21",
        "suite-v17.json",
    ): "7391f06c8e8f0b9198e62b20b8ff365d7c42300f0fb218db4a500e4a238a0fc3",
    (
        "phase11-agent-evals-v22",
        "suite-v18.json",
    ): "2d5ec8b7ecc9a1210f552bb00092b0223363fd584e50da462e801255237d2920",
    (
        "phase11-agent-evals-v23",
        "suite-v19.json",
    ): "43854b2bb2adb75202266b9eba14382a4af587372c4c076dabb4d9f1ef2a5039",
    (
        "phase11-agent-evals-v24",
        "suite-v20.json",
    ): "26b42f22f66937dbdfd0f7d7681015d1e7265710064f6206e2f94096547ce106",
    (
        "phase11-agent-evals-v25",
        "suite-v21.json",
    ): "b324368f9a05d0f3b03441ae6e18b3f25d4864cbc37d795e6e0afb99c840d808",
    (
        "phase11-agent-evals-v26",
        "suite-v22.json",
    ): "5a951f13de7f347d18a811e6cb58153de0380eeaa37d37eca0765599461aab73",
    (
        "phase11-agent-evals-v27",
        "suite-v23.json",
    ): "78c90af380421b7b610430f4bd476df9d0023b3b3697ac02624cfc68de19564f",
    (
        "phase11-agent-evals-v28",
        "suite-v24.json",
    ): "97e020d1353cdd0fe98e4c21e621ee68168d727bc635e6e0f79c458361b32e74",
    (
        "phase11-agent-evals-v29",
        "suite-v25.json",
    ): "0f1a6e51b2f659b3913e126f835ca2e420b3a6975c809648a5c15ea0a9cdb103",
    (
        "phase11-agent-evals-v30",
        "suite-v26.json",
    ): "72ac358fea2c4807b93bf95005e4fd4028edbf6462a72b3aa5d3d45ffb8a15bd",
    (
        "phase11-agent-evals-v31",
        "suite-v27.json",
    ): "d1ce51eed1b4acce866028a4097caaf864e81658c7c7c74aa8440b094a635f7f",
    (
        "phase11-agent-evals-v32",
        "suite-v28.json",
    ): "2507766c3d1404f9175da41296217b5f52abbdeba9951a6413fea65c117195fa",
    (
        "phase11-agent-evals-v33",
        "suite-v29.json",
    ): "a47974c7c30082d528ddd123ee1bd0d2c5c4d5a21c8069fa75b5dd90481f7eed",
    (
        "phase11-agent-evals-v34",
        "suite-v30.json",
    ): "66ef4d40578e38127c26dcdca5abb343fe38fe3c91be4678693a9b05dad83284",
    (
        "phase11-agent-evals-v35",
        "suite-v31.json",
    ): "d16721d556d33ef56421f6f5bb6ac23c227ee90617626f5c0700dc7ffb9b7985",
    (
        "phase11-agent-evals-v36",
        "suite-v32.json",
    ): "aacfb84f0465c94888465b0c0adf2ded25005024f3524f59a443322992b2e030",
    (
        "phase11-agent-evals-v37",
        "suite-v33.json",
    ): "66e3e93b07c586a44b871f1d1cd88691e937e05d4f0784f6fcd7a9629a64cab7",
    (
        "phase11-agent-evals-v38",
        "suite-v34.json",
    ): "16b05ed861a5b44e05888e97b70db8b477587605f29a4838f65b59bb558b5664",
    (
        "phase11-agent-evals-v39",
        "suite-v35.json",
    ): "09b323e66bb005f9e5b8497622f8f0c43e6cce4cdcfa6ae730f9baa58c33d15a",
    (
        "phase11-agent-evals-v40",
        "suite-v36.json",
    ): "f7e2d8aacf24098bcb6eeec4f897456b3d36f7993830a6d9c725d66760dae8e2",
    (
        "phase11-agent-evals-v41",
        "suite-v37.json",
    ): "d6ea1fe84fab05705a7577c1db2c375d11bf3a6bdc1f463c1fc5b7e4fb7eff0d",
    (
        "phase11-agent-evals-v42",
        "suite-v38.json",
    ): "512b04086e3e7a5fe6bdd497c82ea7bcd135cdb416de5ac848d84c93f8810e5f",
    (
        "phase11-agent-evals-v43",
        "suite-v39.json",
    ): "68a1027fdd85a0cebcc6e8743f69535114e63cc10b976403c17a6357c6021862",
    (
        "phase11-agent-evals-v44",
        "suite-v40.json",
    ): "8f878eddddba011afbce6eb810f0b0f63356946ef1b1ca95ed460db9610753e9",
    (
        "phase11-agent-evals-v45",
        "suite-v41.json",
    ): "de4e1ebe5f073e906835fae74d545f1f34b25a07269350f5477683b68035658c",
    (
        "phase11-agent-evals-v46",
        "suite-v42.json",
    ): "58a78e9014b6ed0dff3489ad40eae21eacd48533694f3d5d9014c4d5526188bd",
    (
        "phase11-agent-evals-v47",
        "suite-v43.json",
    ): "18cd3bea4f6781918392cee37297a8f1c8e6d40f9d9d2276626f1a07baedc131",
    (
        "phase11-agent-evals-v48",
        "suite-v44.json",
    ): "7e49ca5de44686973bd2095a72d77561ef55c81b8847b693816da4ac8060845b",
    (
        "phase11-agent-evals-v49",
        "suite-v45.json",
    ): "7177d97bc7313fa7dd9fb3191187c8515c20e69e1d231e99e64e095f5d9897b1",
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
