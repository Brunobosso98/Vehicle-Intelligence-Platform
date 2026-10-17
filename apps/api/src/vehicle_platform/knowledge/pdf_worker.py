"""Isolated PDF process. No network, file arguments, credentials, script execution or OCR."""

import io
import json
import resource
import sys


def main() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    from pypdf import PdfReader

    from vehicle_platform.knowledge.extraction import MAX_CHARS, MAX_PAGES
    from vehicle_platform.knowledge.security import MAX_BYTES

    data = sys.stdin.buffer.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or not data.startswith(b"%PDF-"):
        raise ValueError("invalid_pdf")
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted or len(reader.pages) > MAX_PAGES:
        raise ValueError("unsupported_pdf")
    pages: list[str] = []
    characters = 0
    for page in reader.pages:
        content = page.extract_text() or ""
        characters += len(content)
        if characters > MAX_CHARS:
            raise ValueError("pdf_character_limit")
        pages.append(content)
    sys.stdout.write(json.dumps(pages))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(1) from None
