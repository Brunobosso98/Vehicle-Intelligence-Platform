"""Verify raw publisher artifacts before narrowly scoped secret-scan exceptions apply."""

import hashlib
import os
from pathlib import Path

from dotenv import dotenv_values

PUBLIC_HTML_EXCEPTIONS = {
    "bmw-n55-introduction",
    "bmw-f30-introduction",
    "bootmod3-logging",
    "bootmod3-n55",
    "mhd-n55",
    "garrett-wastegate",
}


def verify(root: Path, manifest: dict, private_key: str | None) -> dict[str, int]:
    sources = {source["key"]: source for source in manifest["sources"]}
    checked = 0
    corpus = root / ".knowledge"
    if not corpus.exists():
        return {"verified_raw_files": 0, "private_key_scan_files": 0}
    if corpus.is_symlink():
        raise ValueError("knowledge_scan_path_outside_corpus")
    for path in (corpus / "raw").glob("*"):
        if path.is_symlink() or not path.resolve().is_relative_to(corpus.resolve()):
            raise ValueError("knowledge_scan_path_outside_corpus")
        source = sources.get(path.stem)
        if path.stem in PUBLIC_HTML_EXCEPTIONS and (
            not source
            or not source.get("checksum")
            or source.get("review_status") != "APPROVED_SELECTED_PARAGRAPHS_V1"
        ):
            raise ValueError(
                "publisher_token_exception_requires_reviewed_source_checksum"
            )
        if source and source.get("checksum"):
            if hashlib.sha256(path.read_bytes()).hexdigest() != source["checksum"]:
                raise ValueError("knowledge_raw_checksum_changed_review_required")
            checked += 1
    scanned = 0
    if private_key:
        secret = private_key.encode()
        for path in corpus.rglob("*"):
            if not path.is_file():
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(corpus.resolve()):
                raise ValueError("knowledge_scan_path_outside_corpus")
            with path.open("rb") as handle:
                overlap = b""
                while block := handle.read(65536):
                    content = overlap + block
                    if secret in content:
                        raise ValueError("private_embedding_key_detected_in_corpus")
                    overlap = (
                        content[-max(0, len(secret) - 1) :] if len(secret) > 1 else b""
                    )
            scanned += 1
    return {"verified_raw_files": checked, "private_key_scan_files": scanned}


def main() -> None:
    import json

    root = Path.cwd()
    manifest = json.loads(
        (root / "docs/knowledge/n55-source-manifest.json").read_text()
    )
    key = os.environ.get("VIP_AGENT_API_KEY") or dotenv_values(root / ".env").get(
        "VIP_AGENT_API_KEY"
    )
    result = verify(root, manifest, key)
    print(
        json.dumps(
            {"knowledge_security": "PASS", **result, "private_key_available": bool(key)}
        )
    )


if __name__ == "__main__":
    main()
