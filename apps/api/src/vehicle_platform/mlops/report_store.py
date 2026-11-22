"""Private, bounded, exclusive report publication under a fixed local root."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import stat
from typing import Any
from uuid import UUID

MAX_REPORT_BYTES = 4 * 1024 * 1024
_REPORT_COMPONENTS = ("apps", "api", ".artifacts", "phase10", "reports")


def _open_directory(*, create: bool) -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise RuntimeError("safe local report storage is unavailable")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(".", flags)
    try:
        for component in _REPORT_COMPONENTS:
            if create:
                try:
                    os.mkdir(component, 0o700, dir_fd=directory)
                except FileExistsError:
                    pass
            child = os.open(component, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        return directory
    except BaseException:
        os.close(directory)
        raise


def write_report(run_id: UUID, report: dict[str, Any]) -> tuple[str, int]:
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("report exceeds the fixed size budget")
    directory = _open_directory(create=True)
    try:
        name = f"{run_id}.json"
        descriptor = os.open(
            name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(directory)
        except BaseException:
            os.unlink(name, dir_fd=directory)
            raise
    finally:
        os.close(directory)
    return hashlib.sha256(payload).hexdigest(), len(payload)


def read_report(run_id: UUID, *, expected_checksum: str) -> dict[str, Any]:
    if len(expected_checksum) != 64 or any(c not in "0123456789abcdef" for c in expected_checksum):
        raise ValueError("invalid report checksum")
    directory = _open_directory(create=False)
    try:
        descriptor = os.open(
            f"{run_id}.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_REPORT_BYTES:
                raise ValueError("report is not a bounded regular file")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                payload = stream.read(MAX_REPORT_BYTES + 1)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory)
    if len(payload) > MAX_REPORT_BYTES or not hmac.compare_digest(
        hashlib.sha256(payload).hexdigest(), expected_checksum
    ):
        raise ValueError("report checksum mismatch")
    result = json.loads(
        payload, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite value"))
    )
    if not isinstance(result, dict):
        raise ValueError("report root must be an object")
    return result
