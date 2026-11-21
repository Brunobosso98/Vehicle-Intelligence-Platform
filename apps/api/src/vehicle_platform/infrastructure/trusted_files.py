"""Read hash-bound local files without reopening them or following symlinks."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import stat
from pathlib import Path


class TrustedFileError(ValueError):
    pass


def _relative_path(root: Path, path: Path) -> tuple[Path, Path]:
    root = Path(os.path.abspath(root))
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise TrustedFileError("artifact path escapes its trusted root") from error
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise TrustedFileError("artifact path is invalid")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise TrustedFileError("secure artifact access is unavailable")
    return root, relative


def _open_parent(root: Path, relative: Path, *, create: bool) -> int:
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = -1
    try:
        directory = os.open("/", directory_flags)
        for component in root.parts[1:]:
            if create:
                try:
                    os.mkdir(component, 0o700, dir_fd=directory)
                except FileExistsError:
                    pass
            child = os.open(component, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = child
        for component in relative.parts[:-1]:
            if create:
                try:
                    os.mkdir(component, 0o700, dir_fd=directory)
                except FileExistsError:
                    pass
            child = os.open(component, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = child
        return directory
    except OSError as error:
        if directory >= 0:
            os.close(directory)
        detail = (
            "symlink or unsafe directory"
            if error.errno == getattr(os, "ELOOP", 40)
            else "unsafe directory"
        )
        raise TrustedFileError(f"artifact path contains {detail}") from error


def read_bounded_bytes(
    root: Path,
    path: Path,
    *,
    maximum_bytes: int,
    expected_owner: int | None = None,
    require_private: bool = False,
) -> bytes:
    root, relative = _relative_path(root, path)
    if maximum_bytes < 1:
        raise TrustedFileError("artifact byte limit is invalid")
    directory = _open_parent(root, relative, create=False)
    descriptor = -1
    try:
        descriptor = os.open(
            relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
    except OSError as error:
        os.close(directory)
        detail = (
            "symlink or unsafe file"
            if error.errno == getattr(os, "ELOOP", 40)
            else "missing or unsafe file"
        )
        raise TrustedFileError(f"artifact is {detail}") from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size < 1:
            raise TrustedFileError("artifact is not a bounded regular file")
        if expected_owner is not None and info.st_uid != expected_owner:
            raise TrustedFileError("artifact owner is not trusted")
        if require_private and info.st_mode & 0o077:
            raise TrustedFileError("artifact permissions are not private")
        if info.st_size > maximum_bytes:
            raise TrustedFileError("artifact exceeds its byte limit")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            payload = stream.read(maximum_bytes + 1)
    finally:
        os.close(descriptor)
        os.close(directory)
    if len(payload) > maximum_bytes:
        raise TrustedFileError("artifact exceeds its byte limit")
    return payload


def write_exclusive_bytes(root: Path, relative: Path, payload: bytes) -> None:
    root = Path(os.path.abspath(root))
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise TrustedFileError("artifact path is invalid")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise TrustedFileError("secure artifact access is unavailable")
    directory = _open_parent(root, relative, create=True)
    temporary = f".artifact-{secrets.token_hex(16)}.tmp"
    descriptor = -1
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(
            temporary,
            relative.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
            follow_symlinks=False,
        )
        os.unlink(temporary, dir_fd=directory)
        os.fsync(directory)
    except FileExistsError:
        try:
            os.unlink(temporary, dir_fd=directory)
        except OSError:
            pass
        raise
    except BaseException as error:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=directory)
        except OSError:
            pass
        if isinstance(error, OSError):
            raise TrustedFileError("artifact could not be published safely") from error
        raise
    finally:
        os.close(directory)


def read_verified_bytes(
    root: Path,
    path: Path,
    expected_checksum: str,
    *,
    maximum_bytes: int,
    expected_size: int | None = None,
) -> bytes:
    payload = read_bounded_bytes(root, path, maximum_bytes=maximum_bytes)
    if expected_size is not None and len(payload) != expected_size:
        raise TrustedFileError("artifact size or checksum changed")
    if len(payload) > maximum_bytes or not hmac.compare_digest(
        hashlib.sha256(payload).hexdigest(), expected_checksum
    ):
        raise TrustedFileError("artifact checksum mismatch")
    return payload
