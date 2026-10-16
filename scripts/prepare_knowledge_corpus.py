"""Reconstruct reviewed source selections locally, without committing copyrighted text."""

import argparse
import json
import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from vehicle_platform.knowledge.domain import (
    Applicability,
    DocumentChunk,
    DocumentVersion,
    KnowledgeIndexVersion,
    KnowledgeSource,
    NumericFact,
    SourceConflict,
    SourceStatus,
    Trust,
    digest,
)
from vehicle_platform.knowledge.extraction import Section, chunks, extract
from vehicle_platform.knowledge.security import IngestionError, download, safe_path

# Reviewed source paragraph locators, bound to the manifest's exact raw-source checksums.
# Source HTML paragraph/heading provenance is preserved; locator labels are not invented OEM titles.
SELECTIONS = [
    (
        "bmw-f30-introduction",
        "f30-n55-architecture",
        ["architecture", "boost"],
        [(5, 57)],
    ),
    (
        "bmw-n55-introduction",
        "n55-architecture",
        ["architecture", "boost"],
        [(6, 29), (6, 31)],
    ),
    ("bmw-n55-introduction", "n55-charge-air-cooling", ["thermal", "boost"], [(6, 33)]),
    ("bosch-gdi", "gdi-operating-principle", ["fuel", "architecture"], [(6, None)]),
    ("bosch-gdi", "gdi-components", ["fuel", "diagnostics"], [(7, None), (28, None)]),
    ("bosch-hdp", "hdp-operating-principle", ["fuel"], [(1, None), (8, None)]),
    (
        "bosch-ecu",
        "ecu-control-principles",
        ["architecture", "fuel", "boost", "diagnostics"],
        [(1, 0), (7, 0)],
    ),
    (
        "garrett-wastegate",
        "wastegate-control-principles",
        ["boost", "thermal"],
        [(4, 1)],
    ),
    (
        "mhd-n55",
        "n55-map-variants",
        ["calibration", "fuel", "boost"],
        [(1, 43), (1, 44), (1, 45), (7, None)],
    ),
    (
        "bootmod3-n55",
        "n55-ewg-calibration",
        ["calibration", "fuel"],
        [(2, 1), (2, 3), (2, 4)],
    ),
    ("bootmod3-logging", "logging-export", ["diagnostics"], [(2, 0), (3, 13), (3, 22)]),
    (
        "bmw-cooling-service",
        "n55-cooling-service-conditions",
        ["thermal", "diagnostics"],
        [(0, "before:PROCEDURE")],
    ),
]

NUMERIC_REVIEWS = {
    "f30-n55-architecture": [
        NumericFact(
            value=6,
            unit="cylinder",
            original="6-cylinder",
            conditions="inline 6-cylinder engine (N55)",
            kind="descriptive",
            topic="architecture",
        )
    ],
}


def prepare(
    manifest_path: Path = Path("docs/knowledge/n55-source-manifest.json"),
    target: Path = Path(".knowledge/approved-corpus.json"),
) -> None:
    manifest = json.loads(manifest_path.read_text())
    sources = {s["key"]: s for s in manifest["sources"]}
    root = Path(".knowledge/raw")
    root.mkdir(parents=True, exist_ok=True)
    parsed: dict[str, list[Section]] = {}
    documents = []
    for key, slug, topics, locators in SELECTIONS:
        locators = manifest.get("selection_overrides", {}).get(slug, locators)
        metadata = sources[key]
        suffix = ".pdf" if metadata["mime"] == "application/pdf" else ".html"
        if metadata.get("local_path"):
            path = Path(metadata["local_path"])
            if (
                not path.resolve().is_relative_to(Path(".knowledge").resolve())
                or path.is_symlink()
            ):
                raise IngestionError("reviewed_source_path_outside_local_corpus")
        else:
            path = safe_path(root, key + suffix)
        if not path.exists():
            data, mime = download(metadata["canonical_url"])
            if mime != metadata["mime"]:
                raise IngestionError("source_mime_changed_review_required")
            path.write_bytes(data)
        data = path.read_bytes()
        if digest(data) != metadata["checksum"]:
            raise IngestionError("source_checksum_changed_review_required")
        if key not in parsed:
            sections, limitations = extract(data, metadata["mime"])
            if set(limitations) - set(
                metadata.get("reviewed_extraction_limitations", [])
            ):
                raise IngestionError("source_extraction_requires_review")
            parsed[key] = sections
        selected: list[Section] = []
        for section_number, paragraph_number in locators:
            section = parsed[key][section_number]
            if isinstance(paragraph_number, str):
                marker = paragraph_number.removeprefix("before:")
                if marker not in section.text:
                    raise IngestionError("reviewed_selection_marker_missing")
                content = section.text.split(marker, 1)[0]
            else:
                content = (
                    section.text
                    if paragraph_number is None
                    else re.split(r"\n\s*\n", section.text)[paragraph_number]
                )
            kind = f"PDF page {section.page}" if section.page else "HTML"
            locator = f"{kind} section {section_number}" + (
                f"; paragraph {paragraph_number}"
                if paragraph_number is not None
                else ""
            )
            selected.append(
                Section(
                    (section.heading[0][:160], locator)
                    if section.heading
                    else (locator,),
                    content.strip(),
                    page=section.page,
                    table=section.table,
                )
            )
        source_id = uuid5(NAMESPACE_URL, metadata["canonical_url"])
        document_id = uuid5(source_id, slug)
        source_checksum = digest(data)
        reviewed = NUMERIC_REVIEWS.get(slug, [])
        checksum = digest(
            json.dumps(
                {
                    "source_checksum": source_checksum,
                    "selection_version": "selection-v2-reviewed-numeric",
                    "numeric_reviews": [
                        fact.model_dump(mode="json") for fact in reviewed
                    ],
                    "chunker": "heading-table-v1",
                    "sections": [
                        {"heading": section.heading, "text": section.text}
                        for section in selected
                    ],
                },
                sort_keys=True,
            )
        )
        document_version = uuid5(
            document_id,
            checksum
            + digest(
                json.dumps(
                    {k: v for k, v in metadata.items() if k != "local_path"},
                    sort_keys=True,
                )
            ),
        )
        app = dict(metadata["applicability"])
        app["subsystems"] = topics
        if key == "bootmod3-n55" and metadata.get("source_version", 1) == 1:
            # Preserve reconstruction of the original snapshot; reviewed versions use hardware.
            app["engine_variant"] = "EWG"
        source = KnowledgeSource(
            id=source_id,
            publisher=metadata["publisher"],
            canonical_url=metadata["canonical_url"],
            source_type=metadata["source_type"],
            trust=Trust(metadata["trust"]),
            status=SourceStatus.VERIFIED,
            verified_at=metadata["verified_at"],
            version=metadata.get("source_version", 1),
        )
        doc = DocumentVersion(
            id=document_version,
            document_id=document_id,
            source_id=source_id,
            source_version=source.version,
            title=metadata["title"],
            publication_date=metadata["publication_date"],
            version_label=metadata.get("version_label"),
            retrieved_at=metadata["retrieved_at"],
            checksum=checksum,
            source_checksum=source_checksum,
            extraction_version="selection-v2-reviewed-numeric",
            mime=metadata["mime"],
            applicability=Applicability.model_validate(app),
            license_note=metadata["license_note"],
            redistribution="metadata_only",
            status="EXTRACTED",
            limitations=["selected_source_paragraphs_only", "no_diagram_interpretation"]
            + (["conflicting_stage2_hardware_sections"] if key == "mhd-n55" else []),
        )
        pieces = chunks(doc.id, selected)
        for fact in reviewed:
            applicable = [
                piece
                for piece in pieces
                if fact.original in piece.text and fact.conditions in piece.text
            ]
            if not applicable:
                raise IngestionError("reviewed_numeric_literal_missing_from_source")
            for piece in applicable:
                piece.numeric_facts.append(fact)
                piece.quality = "reviewed"
        pieces = [DocumentChunk.model_validate(piece.model_dump()) for piece in pieces]
        documents.append(
            {
                "key": slug,
                "source": source.model_dump(mode="json"),
                "document": doc.model_dump(mode="json"),
                "chunks": [c.model_dump(mode="json") for c in pieces],
            }
        )
    conflicts = []
    for key, slug, _, _ in SELECTIONS:
        metadata = sources[key]
        entry = next(item for item in documents if item["key"] == slug)
        document = DocumentVersion.model_validate(entry["document"])
        for conflict in metadata.get("reviewed_source_conflicts", []):
            if conflict["selection"] == slug:
                conflicts.append(
                    SourceConflict(
                        id=uuid5(
                            document.id, digest(json.dumps(conflict, sort_keys=True))
                        ),
                        left_version_id=document.id,
                        right_version_id=document.id,
                        topic=conflict["topic"],
                        explanation=conflict["explanation"],
                    ).model_dump(mode="json")
                )
    tuner = next(
        (item for item in documents if item["key"] == "n55-map-variants"), None
    )
    if tuner is not None:
        known_conflicting_text = sources["mhd-n55"]["checksum"] == (
            "d56f23edf9d7f7c67172e6b5cbd9720ff7c131befc1bc15743e3567f2db2b18d"
        )
        if (
            not known_conflicting_text
            and "reviewed_source_conflicts" not in sources["mhd-n55"]
        ):
            raise IngestionError("changed_mhd_source_requires_explicit_conflict_review")
        tuner_version = DocumentVersion.model_validate(tuner["document"])
        legacy_conflicts = [
            SourceConflict(
                id=uuid5(tuner_version.id, "mhd-stage2-hardware-conflict-v1"),
                left_version_id=tuner_version.id,
                right_version_id=tuner_version.id,
                topic="calibration",
                explanation=(
                    "The reviewed MHD page gives different Stage 2 hardware prerequisites in its "
                    "main map description and later Stage 2 Maps section. The former allows an "
                    "intercooler or downpipe; the latter specifies a downpipe. Exact map identity "
                    "and vendor clarification remain unavailable; neither becomes a universal requirement."
                ),
            ).model_dump(mode="json")
        ]
        if known_conflicting_text:
            conflicts.extend(legacy_conflicts)
    corpus_hash = digest(
        json.dumps({"documents": documents, "conflicts": conflicts}, sort_keys=True)
    )
    verified = max(
        KnowledgeSource.model_validate(d["source"]).verified_at for d in documents
    )
    index = KnowledgeIndexVersion(
        id="n55-public-selection-v3-" + corpus_hash[:16],
        corpus_checksum=corpus_hash,
        # Bind the reconstruction timestamp to reviewed provenance. Compiling the same
        # manifest to another path must not create a different immutable index snapshot.
        created_at=verified,
    )
    # Pipeline changes require a deliberate new identity even when source text is unchanged.
    identity = digest(index.model_dump_json(exclude={"id", "created_at"}))
    index.id = "n55-public-selection-v3-" + identity[:16]
    output = {
        "index": index.model_dump(mode="json"),
        "manifest_checksum": digest(manifest_path.read_bytes()),
        "documents": documents,
        "conflicts": conflicts,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    output["index"] = index.model_dump(mode="json")
    target.write_text(json.dumps(output, indent=2) + "\n")
    target.chmod(0o600)
    print(
        json.dumps(
            {
                "sources": len({d["source"]["id"] for d in documents}),
                "documents": len(documents),
                "chunks": sum(len(d["chunks"]) for d in documents),
                "index": index.id,
                "status": "PREPARED_LOCAL_ONLY",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=Path("docs/knowledge/n55-source-manifest.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path(".knowledge/approved-corpus.json")
    )
    args = parser.parse_args()
    prepare(args.manifest, args.output)
