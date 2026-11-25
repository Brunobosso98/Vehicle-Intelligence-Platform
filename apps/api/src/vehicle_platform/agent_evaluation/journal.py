"""Append-only, hash-chained checkpoints for completed evaluation attempts."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from vehicle_platform.agent_evaluation.contracts import CaseAttempt
from vehicle_platform.agent_evaluation.corpus import canonical_json, sha256_bytes

_ZERO_SHA256 = "0" * 64
_MAX_JOURNAL_BYTES = 32_000_000


class AttemptJournal:
    """Persist sanitized attempts immediately and make edits detectable by a hash chain."""

    def __init__(
        self,
        path: Path,
        *,
        run_id: str,
        repository_sha: str,
        suite_sha256: str,
    ) -> None:
        self.path = path
        self.run_id = run_id
        self.repository_sha = repository_sha
        self.suite_sha256 = suite_sha256
        self._previous_entry_sha256 = _ZERO_SHA256
        self._entries = 0
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path.parent, stat.S_IRWXU)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self._stream = os.fdopen(descriptor, "wb")

    @property
    def entries(self) -> int:
        return self._entries

    def append(self, attempt: CaseAttempt) -> None:
        attempt_payload = attempt.model_dump(mode="json")
        encoded_attempt = canonical_json(attempt_payload)
        entry = {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "repository_sha": self.repository_sha,
            "suite_sha256": self.suite_sha256,
            "sequence": self._entries + 1,
            "previous_entry_sha256": self._previous_entry_sha256,
            "attempt_sha256": sha256_bytes(encoded_attempt),
            "attempt": attempt_payload,
        }
        line = canonical_json(entry) + b"\n"
        self._stream.write(line)
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._previous_entry_sha256 = sha256_bytes(line)
        self._entries += 1

    def close(self) -> None:
        if not self._stream.closed:
            self._stream.flush()
            os.fsync(self._stream.fileno())
            self._stream.close()

    def summary(self) -> dict[str, str | int]:
        self.close()
        return {
            "path": self.path.as_posix(),
            "sha256": sha256_bytes(self.path.read_bytes()),
            "entries": self._entries,
        }


def verify_attempt_journal(
    path: Path,
    *,
    expected_run_id: str,
    expected_repository_sha: str,
    expected_suite_sha256: str,
    expected_sha256: str,
    expected_entries: int,
) -> tuple[bool, tuple[str, ...]]:
    """Independently verify the journal envelope, attempt hashes and ordered chain."""

    reasons: list[str] = []
    try:
        if path.stat().st_size > _MAX_JOURNAL_BYTES:
            return False, ("attempt_journal_too_large",)
        raw = path.read_bytes()
    except OSError:
        return False, ("attempt_journal_unavailable",)
    if not raw.endswith(b"\n"):
        reasons.append("attempt_journal_truncated")
    if sha256_bytes(raw) != expected_sha256:
        reasons.append("attempt_journal_sha256_mismatch")
    previous = _ZERO_SHA256
    parsed_entries = 0
    for index, line in enumerate(raw.splitlines(keepends=True), start=1):
        if not line.endswith(b"\n"):
            continue
        try:
            entry = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            reasons.append("attempt_journal_invalid_json")
            continue
        if not isinstance(entry, dict):
            reasons.append("attempt_journal_entry_invalid")
            continue
        attempt = entry.get("attempt")
        if (
            entry.get("schema_version") != "1.0"
            or entry.get("run_id") != expected_run_id
            or entry.get("repository_sha") != expected_repository_sha
            or entry.get("suite_sha256") != expected_suite_sha256
            or entry.get("sequence") != index
            or entry.get("previous_entry_sha256") != previous
            or not isinstance(attempt, dict)
        ):
            reasons.append("attempt_journal_chain_or_manifest_mismatch")
        elif sha256_bytes(canonical_json(attempt)) != entry.get("attempt_sha256"):
            reasons.append("attempt_journal_attempt_hash_mismatch")
        try:
            CaseAttempt.model_validate(attempt)
        except Exception:
            reasons.append("attempt_journal_attempt_invalid")
        previous = sha256_bytes(line)
        parsed_entries += 1
    if parsed_entries != expected_entries:
        reasons.append("attempt_journal_entry_count_mismatch")
    return not reasons, tuple(dict.fromkeys(reasons))
