"""Raw HTML scan exceptions cannot hide changed material or the actual operator key."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[4] / "scripts/check_knowledge_security.py"
spec = importlib.util.spec_from_file_location("knowledge_security", MODULE)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(root: Path, content: bytes) -> tuple[Path, dict]:
    raw = root / ".knowledge/raw"
    raw.mkdir(parents=True)
    path = raw / "mhd-n55.html"
    path.write_bytes(content)
    manifest = {
        "sources": [
            {
                "key": "mhd-n55",
                "checksum": hashlib.sha256(content).hexdigest(),
                "review_status": "APPROVED_SELECTED_PARAGRAPHS_V1",
            }
        ]
    }
    return path, manifest


def test_changed_public_html_cannot_bypass_the_secret_gate(tmp_path):
    path, manifest = fixture(tmp_path, b"synthetic public player token")
    assert module.verify(tmp_path, manifest, None)["verified_raw_files"] == 1
    path.write_bytes(b"changed content must be reviewed")
    with pytest.raises(ValueError, match="checksum_changed"):
        module.verify(tmp_path, manifest, None)


def test_actual_key_is_rejected_even_in_an_approved_public_artifact(tmp_path):
    sentinel = "synthetic-private-key-for-local-unit-test"
    _, manifest = fixture(tmp_path, ("untrusted source " + sentinel).encode())
    with pytest.raises(ValueError, match="private_embedding_key_detected") as error:
        module.verify(tmp_path, manifest, sentinel)
    assert sentinel not in str(error.value)


def test_scan_requires_review_and_cannot_follow_a_corpus_symlink(tmp_path):
    path, _ = fixture(tmp_path, b"synthetic reference")
    with pytest.raises(ValueError, match="requires_reviewed_source"):
        module.verify(tmp_path, {"sources": []}, None)
    path.unlink()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside corpus")
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="path_outside"):
        module.verify(tmp_path, {"sources": []}, None)


def test_streaming_scan_checks_chunk_boundaries_and_other_artifacts(tmp_path):
    _, manifest = fixture(tmp_path, b"synthetic public reference")
    sentinel = "synthetic-boundary-key"
    (tmp_path / ".knowledge/cache.bin").write_bytes(b"x" * 65530 + sentinel.encode())
    with pytest.raises(ValueError, match="private_embedding_key_detected"):
        module.verify(tmp_path, manifest, sentinel)
    (tmp_path / ".knowledge/cache.bin").unlink()
    result = module.verify(tmp_path, manifest, sentinel)
    assert result["private_key_scan_files"] == 1
