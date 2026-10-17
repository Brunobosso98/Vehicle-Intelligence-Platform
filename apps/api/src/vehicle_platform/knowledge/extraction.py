"""Heading/page/table-aware extraction. Image-only pages remain explicit limitations."""

import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from uuid import UUID, uuid5

from vehicle_platform.knowledge.domain import DocumentChunk, digest
from vehicle_platform.knowledge.security import MAX_BYTES, IngestionError, quarantine_text

MAX_CHARS = 1_500_000
MAX_PAGES = 250
MAX_CHUNK = 4000


@dataclass(frozen=True)
class Section:
    heading: tuple[str, ...]
    text: str
    page: int | None = None
    table: bool = False
    ambiguous: bool = False


class StructuredHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.sections: list[Section] = []
        self.headings: list[str] = []
        self.ignored = 0
        self.heading: list[str] | None = None
        self.level = 1
        self.in_table = False

    def flush(self) -> None:
        text = re.sub(r"[ \t]+", " ", "".join(self.parts)).strip()
        if text:
            self.sections.append(Section(tuple(self.headings), text, table=self.in_table))
        self.parts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "footer", "noscript", "svg"}:
            self.ignored += 1
        if self.ignored:
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading, self.level = [], int(tag[1])
        if tag == "table":
            self.flush()
            self.in_table = True
        if tag in {"p", "li", "tr", "br", "div"}:
            self.parts.append("\n\n")
        if tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer", "noscript", "svg"}:
            self.ignored = max(0, self.ignored - 1)
            return
        if self.ignored:
            return
        if re.fullmatch(r"h[1-6]", tag) and self.heading is not None:
            title = "".join(self.heading).strip()[:160]
            self.headings = self.headings[: self.level - 1] + [title or "Untitled section"]
            self.heading = None
        if tag == "table":
            self.flush()
            self.in_table = False
        if tag in {"p", "li", "tr", "div"}:
            self.parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            (self.heading if self.heading is not None else self.parts).append(data)


def extract(data: bytes, mime: str) -> tuple[list[Section], list[str]]:
    if data.startswith((b"MZ", b"PK\x03\x04", b"\x7fELF")):
        raise IngestionError("unsupported_source_type")
    if len(data) > MAX_BYTES:
        raise IngestionError("source_size_limit")
    limitations: list[str] = []
    if mime == "application/pdf":
        # Parser runs in a resource-limited subprocess at the ingestion boundary.
        try:
            parsed = subprocess.run(  # noqa: S603 - fixed module, bytes on stdin, clean environment
                [sys.executable, "-I", "-m", "vehicle_platform.knowledge.pdf_worker"],
                input=data,
                capture_output=True,
                timeout=15,
                check=True,
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            )
            pages = json.loads(parsed.stdout)
            if not isinstance(pages, list) or any(not isinstance(p, str) for p in pages):
                raise IngestionError("invalid_pdf_extraction")
            return pdf_sections(pages)
        except (subprocess.SubprocessError, ValueError, OSError):
            raise IngestionError("pdf_parser_failed") from None
    if mime not in {"text/plain", "text/markdown", "text/html"}:
        raise IngestionError("unsupported_source_type")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError:
        raise IngestionError("invalid_source_encoding") from None
    if len(text) > MAX_CHARS or "\x00" in text:
        raise IngestionError("parser_character_limit")
    if mime == "text/html":
        parser = StructuredHTML()
        parser.feed(text)
        parser.flush()
        sections = parser.sections
    else:
        sections = markdown_sections(text)
    if not sections or sum(len(s.text) for s in sections) < 20:
        raise IngestionError("empty_extraction")
    if any(quarantine_text(s.text + " ".join(s.heading)) for s in sections):
        limitations.append("document_instruction_quarantined")
    return sections, limitations


def markdown_sections(text: str, page: int | None = None) -> list[Section]:
    result: list[Section] = []
    heading: list[str] = []
    lines: list[str] = []
    table = False

    def flush() -> None:
        nonlocal lines
        content = "\n".join(lines).strip()
        if content:
            result.append(Section(tuple(heading), content, page, table))
        lines = []

    for line in text.splitlines():
        found = re.match(r"^(#{1,6})\s+(.+)$", line)
        is_table = line.strip().startswith("|")
        if found:
            flush()
            heading = heading[: len(found[1]) - 1] + [found[2].strip()[:160]]
        else:
            if is_table != table:
                flush()
                table = is_table
            lines.append(line)
    flush()
    return result


def pdf_sections(pages: list[str]) -> tuple[list[Section], list[str]]:
    if len(pages) > MAX_PAGES or sum(map(len, pages)) > MAX_CHARS:
        raise IngestionError("parser_resource_limit")
    repeated = Counter(
        line.strip()
        for page in pages
        for line in set(page.splitlines())
        if 1 <= len(line.strip()) < 120
    )
    footers = {line for line, count in repeated.items() if count >= max(3, len(pages) * 0.6)}
    sections: list[Section] = []
    limitations: list[str] = []
    for number, page in enumerate(pages, 1):
        if len(page.strip()) < 20:
            limitations.append(f"page_{number}_image_or_empty_no_ocr")
            continue
        clean = "\n".join(line for line in page.splitlines() if line.strip() not in footers)
        # PDF text layout does not establish reliable table cells/numeric specifications.
        heading = next((s.strip() for s in clean.splitlines() if s.strip()), f"Page {number}")
        sections.append(Section((heading[:160],), clean, number, ambiguous=False))
    limitations.append("pdf_tables_and_diagrams_require_review")
    return sections, limitations


def chunks(version_id: UUID, sections: list[Section]) -> list[DocumentChunk]:
    result: list[DocumentChunk] = []
    seen: set[str] = set()
    for section in sections:
        text = re.sub(r"[ \t]+", " ", section.text).strip()
        if section.table and len(text) < 20 and section.heading:
            text = section.heading[-1] + "\n" + text
        if section.table and len(text) > MAX_CHUNK:
            raise IngestionError("oversize_table_requires_review")
        # Preserve paragraphs; long indivisible paragraphs need manual structure review.
        paragraphs = re.split(r"\n\s*\n", text) if not section.table else [text]
        groups: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(paragraph) > MAX_CHUNK:
                raise IngestionError("oversize_paragraph_requires_review")
            if len(current) + len(paragraph) + 2 > MAX_CHUNK:
                groups.append(current)
                current = ""
            current = (current + "\n\n" + paragraph).strip()
        if current:
            groups.append(current)
        for content in groups:
            checksum = digest(content)
            if len(content) < 20 or checksum in seen:
                continue
            seen.add(checksum)
            ordinal = len(result)
            result.append(
                DocumentChunk(
                    id=uuid5(version_id, f"{ordinal}:{checksum}"),
                    version_id=version_id,
                    ordinal=ordinal,
                    page=section.page,
                    section=section.heading[-1] if section.heading else "Document body",
                    heading_path=list(section.heading),
                    text=content,
                    checksum=checksum,
                    token_bound=len(content.encode()),
                    table=section.table,
                    quality="ambiguous" if section.ambiguous else "extracted",
                )
            )
    if not result:
        raise IngestionError("no_usable_chunks")
    return result
