import hashlib
import stat
from pathlib import Path

import pytest

from vehicle_platform.agent_evaluation.contracts import AttemptStatus, CaseAttempt
from vehicle_platform.agent_evaluation.corpus import canonical_json, sha256_bytes
from vehicle_platform.agent_evaluation.journal import AttemptJournal, verify_attempt_journal
from vehicle_platform.agent_evaluation.receipts import create_receipt


def _attempt(status: AttemptStatus) -> CaseAttempt:
    return CaseAttempt(case_id="P11-BENIGN-001", status=status)


def test_attempt_journal_is_private_append_only_and_hash_chained(tmp_path: Path) -> None:
    repository_sha = "a" * 40
    suite_sha = "b" * 64
    run_id = "c" * 32
    path = tmp_path / "private" / "run.jsonl"
    journal = AttemptJournal(
        path,
        run_id=run_id,
        repository_sha=repository_sha,
        suite_sha256=suite_sha,
    )
    journal.append(_attempt(AttemptStatus.ASSERTION_FAIL))
    journal.append(_attempt(AttemptStatus.PASS))
    summary = journal.summary()

    assert summary["entries"] == 2
    assert journal.entries == 2
    assert Path(str(summary["path"])) == path
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert verify_attempt_journal(
        path,
        expected_run_id=run_id,
        expected_repository_sha=repository_sha,
        expected_suite_sha256=suite_sha,
        expected_sha256=str(summary["sha256"]),
        expected_entries=2,
    ) == (True, ())


def test_attempt_journal_detects_mutation_and_wrong_manifest(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    journal = AttemptJournal(
        path,
        run_id="c" * 32,
        repository_sha="a" * 40,
        suite_sha256="b" * 64,
    )
    journal.append(_attempt(AttemptStatus.PASS))
    summary = journal.summary()
    original = path.read_bytes()

    changed = original.replace(b'"status":"PASS"', b'"status":"FAIL"')
    path.write_bytes(changed)
    ok, reasons = verify_attempt_journal(
        path,
        expected_run_id="c" * 32,
        expected_repository_sha="a" * 40,
        expected_suite_sha256="b" * 64,
        expected_sha256=str(summary["sha256"]),
        expected_entries=1,
    )
    assert not ok
    assert "attempt_journal_sha256_mismatch" in reasons
    assert "attempt_journal_attempt_hash_mismatch" in reasons

    path.write_bytes(original)
    ok, reasons = verify_attempt_journal(
        path,
        expected_run_id="d" * 32,
        expected_repository_sha="a" * 40,
        expected_suite_sha256="b" * 64,
        expected_sha256=str(summary["sha256"]),
        expected_entries=1,
    )
    assert not ok
    assert "attempt_journal_chain_or_manifest_mismatch" in reasons


def test_receipt_schema_1_1_cannot_drop_its_attempt_journal_reference() -> None:
    payload = {
        "schema_version": "1.1",
        "suite_version": "phase11-agent-evals-v30",
        "suite_sha256": "b" * 64,
        "repository_sha": "a" * 40,
        "source_fixture_sha256": "c" * 64,
        "scenario_generator_version": "1.0",
        "random_seed": 0,
        "dependency_manifest_sha256": "d" * 64,
        "prompt_manifest_sha256": "e" * 64,
        "tool_catalog_sha256": "f" * 64,
        "schema_revision": "0020",
        "environment": "test",
        "provider": "deterministic",
        "model": "scripted-v1",
        "attempt_journal_run_id": "1" * 32,
        "attempt_journal_path": ".validation/phase11/attempt-journals/run.jsonl",
        "attempt_journal_sha256": "2" * 64,
        "attempt_journal_entries": 1,
        "attempts": [CaseAttempt(case_id="P11-BENIGN-001", status=AttemptStatus.PASS)],
    }
    receipt = create_receipt(payload)
    raw = receipt.model_dump(mode="json")
    for field in (
        "attempt_journal_run_id",
        "attempt_journal_path",
        "attempt_journal_sha256",
        "attempt_journal_entries",
    ):
        raw.pop(field)

    with pytest.raises(ValueError, match="attempt_journal_required_for_receipt_schema_1_1"):
        type(receipt).model_validate(raw)


def test_attempt_journal_verifier_rejects_missing_truncated_oversized_and_invalid_entries(
    tmp_path: Path,
) -> None:
    common = {
        "expected_run_id": "c" * 32,
        "expected_repository_sha": "a" * 40,
        "expected_suite_sha256": "b" * 64,
        "expected_entries": 1,
    }
    missing, reasons = verify_attempt_journal(
        tmp_path / "missing.jsonl",
        **common,
        expected_sha256="0" * 64,
    )
    assert not missing and reasons == ("attempt_journal_unavailable",)

    oversized_path = tmp_path / "oversized.jsonl"
    oversized_path.write_bytes(b"\n")
    with oversized_path.open("r+b") as stream:
        stream.truncate(32_000_001)
    oversized, reasons = verify_attempt_journal(
        oversized_path,
        **common,
        expected_sha256="0" * 64,
    )
    assert not oversized and reasons == ("attempt_journal_too_large",)

    truncated_path = tmp_path / "truncated.jsonl"
    journal = AttemptJournal(
        truncated_path,
        run_id=common["expected_run_id"],
        repository_sha=common["expected_repository_sha"],
        suite_sha256=common["expected_suite_sha256"],
    )
    journal.append(_attempt(AttemptStatus.PASS))
    journal.summary()
    truncated = truncated_path.read_bytes()[:-1]
    truncated_path.write_bytes(truncated)
    valid, reasons = verify_attempt_journal(
        truncated_path,
        **common,
        expected_sha256=hashlib.sha256(truncated).hexdigest(),
    )
    assert not valid
    assert "attempt_journal_truncated" in reasons
    assert "attempt_journal_entry_count_mismatch" in reasons

    invalid_json_path = tmp_path / "invalid-json.jsonl"
    invalid_json = b"{not-json}\n"
    invalid_json_path.write_bytes(invalid_json)
    valid, reasons = verify_attempt_journal(
        invalid_json_path,
        **common,
        expected_sha256=hashlib.sha256(invalid_json).hexdigest(),
    )
    assert not valid
    assert "attempt_journal_invalid_json" in reasons

    invalid_attempt_path = tmp_path / "invalid-attempt.jsonl"
    entry = {
        "schema_version": "1.0",
        "run_id": common["expected_run_id"],
        "repository_sha": common["expected_repository_sha"],
        "suite_sha256": common["expected_suite_sha256"],
        "sequence": 1,
        "previous_entry_sha256": "0" * 64,
        "attempt_sha256": sha256_bytes(canonical_json({})),
        "attempt": {},
    }
    invalid_attempt = canonical_json(entry) + b"\n"
    invalid_attempt_path.write_bytes(invalid_attempt)
    valid, reasons = verify_attempt_journal(
        invalid_attempt_path,
        **common,
        expected_sha256=sha256_bytes(invalid_attempt),
    )
    assert not valid
    assert "attempt_journal_attempt_invalid" in reasons

    non_object_path = tmp_path / "non-object.jsonl"
    non_object = b"[]\n"
    non_object_path.write_bytes(non_object)
    valid, reasons = verify_attempt_journal(
        non_object_path,
        **common,
        expected_sha256=sha256_bytes(non_object),
    )
    assert not valid
    assert "attempt_journal_entry_invalid" in reasons
