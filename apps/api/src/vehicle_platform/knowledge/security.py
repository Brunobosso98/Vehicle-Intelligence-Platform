"""Operator-only acquisition: public pinned addresses, bounded reads, no redirects to LAN."""

import http.client
import ipaddress
import re
import socket
import ssl
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

MAX_BYTES = 12 * 1024 * 1024
ALLOWED_MIME = {"application/pdf", "text/html", "text/plain", "text/markdown"}
INJECTION = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous\s+|system\s+)?instructions|write[_\s-]?ecu|"
    r"(?:system|developer)\s*prompt|(?:reveal|print|send)\s+(?:the\s+)?api[_\s-]?key",
    re.I,
)


class IngestionError(ValueError):
    """A fixed category, without source text, paths, credentials or network exceptions."""


def quarantine_text(value: str) -> bool:
    return bool(INJECTION.search(value))


def safe_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise IngestionError("invalid_corpus_path")
    return path


def public_addresses(url: str) -> tuple[str, int, list[str]]:
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise IngestionError("invalid_source_url")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in {80, 443}:
            raise IngestionError("unsupported_source_port")
        host = parsed.hostname.encode("idna").decode()
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses = sorted({str(record[4][0]) for record in records})
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise IngestionError("nonpublic_source_address")
        return host, port, addresses
    except (ValueError, OSError, UnicodeError):
        raise IngestionError("invalid_source_url") from None


def download(url: str, *, max_bytes: int = MAX_BYTES, timeout: float = 20) -> tuple[bytes, str]:
    """Pin the validated IP and preserve hostname TLS/Host to prevent DNS rebinding."""
    deadline = time.monotonic() + timeout
    for _ in range(4):
        host, port, addresses = public_addresses(url)
        parsed = urlsplit(url)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise IngestionError("source_timeout")
        connection = http.client.HTTPConnection(host, port, timeout=remaining)
        try:
            pinned = socket.create_connection((addresses[0], port), timeout=remaining)
            if parsed.scheme == "https":
                context = ssl.create_default_context()
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                connection.sock = context.wrap_socket(pinned, server_hostname=host)
            else:
                connection.sock = pinned
            connection.request(
                "GET",
                parsed.path + ("?" + parsed.query if parsed.query else ""),
                headers={
                    "Host": host,
                    "User-Agent": "VIP-controlled-corpus/1.0",
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise IngestionError("invalid_source_redirect")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise IngestionError("source_download_failed")
            mime = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().lower()
            if (
                mime not in ALLOWED_MIME
                or response.getheader("Content-Encoding", "identity") != "identity"
            ):
                raise IngestionError("unsupported_source_type")
            length = response.getheader("Content-Length")
            if length and (not length.isdigit() or int(length) > max_bytes):
                raise IngestionError("source_size_limit")
            content = bytearray()
            while True:
                if time.monotonic() >= deadline:
                    raise IngestionError("source_timeout")
                if connection.sock:
                    connection.sock.settimeout(max(0.01, deadline - time.monotonic()))
                block = response.read(min(65536, max_bytes + 1 - len(content)))
                content.extend(block)
                if len(content) > max_bytes:
                    raise IngestionError("source_size_limit")
                if not block:
                    break
            data = bytes(content)
            if not data or (mime == "application/pdf" and not data.startswith(b"%PDF-")):
                raise IngestionError("source_content_mismatch")
            if data.startswith((b"MZ", b"PK\x03\x04", b"\x7fELF")):
                raise IngestionError("unsupported_source_type")
            return data, mime
        except (OSError, http.client.HTTPException, ssl.SSLError):
            raise IngestionError("source_download_failed") from None
        finally:
            connection.close()
    raise IngestionError("source_redirect_limit")
