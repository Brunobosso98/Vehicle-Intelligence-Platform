"""Operator-only immutable refresh candidates; acquisition never publishes an index."""

import argparse
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter
from vehicle_platform.knowledge.domain import Applicability, Topic, digest
from vehicle_platform.knowledge.embeddings import EmbeddingSettings
from vehicle_platform.knowledge.extraction import extract
from vehicle_platform.knowledge.security import (
    IngestionError,
    download,
    quarantine_text,
    safe_path,
)


def write_immutable(path: Path, content: bytes) -> None:
    key = EmbeddingSettings(_env_file=".env").agent_api_key
    if key and key.get_secret_value() and key.get_secret_value().encode() in content:
        raise ValueError("private_key_cannot_be_saved_in_refresh_artifacts")
    if path.is_symlink():
        raise ValueError("refresh_artifact_symlink_rejected")
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("refresh_artifact_is_immutable")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=".pending-refresh-")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != content:
                raise ValueError("refresh_artifact_is_immutable") from None
    finally:
        temporary.unlink(missing_ok=True)


def stage(
    manifest_path: Path, key: str, root: Path, *, existing_local: bool = False
) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", key):
        raise ValueError("invalid_refresh_source_key")
    manifest = json.loads(manifest_path.read_text())
    source = next(s for s in manifest["sources"] if s["key"] == key)
    if existing_local:
        suffix = ".pdf" if source["mime"] == "application/pdf" else ".html"
        local = Path(source.get("local_path", ".knowledge/raw/" + key + suffix))
        if local.is_symlink() or not local.resolve().is_relative_to(
            Path(".knowledge").resolve()
        ):
            raise ValueError("approved_local_source_path_outside_corpus")
        data, mime = local.read_bytes(), source["mime"]
        if digest(data) != source["checksum"]:
            raise ValueError("approved_local_source_checksum_changed")
    else:
        data, mime = download(source["canonical_url"])
    key_value = EmbeddingSettings(_env_file=".env").agent_api_key
    if (
        key_value
        and key_value.get_secret_value()
        and key_value.get_secret_value().encode() in data
    ):
        raise ValueError("private_key_detected_in_refresh_candidate")
    if mime != source["mime"]:
        raise ValueError("refresh_mime_changed_review_required")
    checksum = digest(data)
    folder = safe_path(root, key + "/" + checksum)
    receipt_path = folder / "candidate.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt["manifest_checksum"] != digest(manifest_path.read_bytes()):
            raise ValueError("refresh_base_manifest_changed")
        return receipt_path
    status = "UNCHANGED"
    limitations = source.get("reviewed_extraction_limitations", [])
    if checksum != source["checksum"]:
        try:
            sections, limitations = extract(data, mime)
            status = (
                "QUARANTINED"
                if not sections or any(quarantine_text(s.text) for s in sections)
                else "REVIEW_REQUIRED"
            )
        except (IngestionError, ValueError):
            status = "QUARANTINED"
            limitations = ["candidate_extraction_failed"]
        write_immutable(folder / "source.bin", data)
    receipt = {
        "schema_version": "1.0",
        "source_key": key,
        "manifest_checksum": digest(manifest_path.read_bytes()),
        "base_source_checksum": source["checksum"],
        "candidate_checksum": checksum,
        "mime": mime,
        "retrieved_at": source["retrieved_at"]
        if existing_local
        else datetime.now(UTC).isoformat(),
        "acquisition": "verified_local_snapshot"
        if existing_local
        else "controlled_download",
        "status": status,
        "extraction_limitations": limitations,
    }
    write_immutable(receipt_path, (json.dumps(receipt, indent=2) + "\n").encode())
    return receipt_path


def review(manifest_path: Path, candidate_path: Path, review_path: Path) -> Path:
    """Produce a reviewed reconstruction manifest without replacing the approved corpus/raw files."""
    manifest = json.loads(manifest_path.read_text())
    candidate = json.loads(candidate_path.read_text())
    decision = json.loads(review_path.read_text())
    if candidate["manifest_checksum"] != digest(manifest_path.read_bytes()):
        raise ValueError("refresh_base_manifest_changed")
    if (
        decision.get("candidate_checksum") != candidate["candidate_checksum"]
        or decision.get("base_source_checksum") != candidate["base_source_checksum"]
        or not isinstance(decision.get("reviewer"), str)
        or not 3 <= len(decision["reviewer"]) <= 160
        or not isinstance(decision.get("reason"), str)
        or not 10 <= len(decision["reason"]) <= 1000
    ):
        raise ValueError("refresh_review_must_identify_exact_candidate_and_rationale")
    outcome = decision.get("decision")
    if outcome not in {"ACCEPTED", "REJECTED", "QUARANTINED"}:
        raise ValueError("invalid_refresh_review_decision")
    if candidate["status"] == "UNCHANGED" and not decision.get("metadata"):
        raise ValueError("unchanged_source_needs_no_new_version")
    if candidate["status"] == "UNCHANGED":
        source = next(
            s for s in manifest["sources"] if s["key"] == candidate["source_key"]
        )
        suffix = ".pdf" if source["mime"] == "application/pdf" else ".html"
        data_path = Path(
            source.get("local_path", ".knowledge/raw/" + source["key"] + suffix)
        )
    else:
        data_path = safe_path(candidate_path.parent, "source.bin")
    if digest(data_path.read_bytes()) != candidate["candidate_checksum"]:
        raise ValueError("refresh_candidate_checksum_changed")
    saved_review = candidate_path.parent / "review.json"
    if saved_review.exists() and json.loads(saved_review.read_text()) != decision:
        raise ValueError("refresh_review_is_immutable")
    if outcome == "ACCEPTED":
        if candidate["status"] not in {"REVIEW_REQUIRED", "UNCHANGED"}:
            raise ValueError("quarantined_candidate_cannot_be_approved")
        if (
            decision.get("reviewed_extraction_limitations")
            != candidate["extraction_limitations"]
        ):
            raise ValueError("refresh_extraction_limitations_require_explicit_review")
        from prepare_knowledge_corpus import SELECTIONS

        selections = decision.get("selection_overrides", {})
        expected = {
            slug for key, slug, _, _ in SELECTIONS if key == candidate["source_key"]
        }
        if (
            not isinstance(selections, dict)
            or set(selections) != expected
            or not expected
        ):
            raise ValueError(
                "refresh_requires_reviewed_locators_for_every_source_selection"
            )
        sections, _ = extract(data_path.read_bytes(), candidate["mime"])
        for locators in selections.values():
            if not isinstance(locators, list) or not locators:
                raise ValueError("refresh_requires_nonempty_selected_locators")
            for locator in locators:
                if (
                    not isinstance(locator, list)
                    or len(locator) != 2
                    or type(locator[0]) is not int
                    or not 0 <= locator[0] < len(sections)
                ):
                    raise ValueError("invalid_reviewed_section_locator")
                paragraph = locator[1]
                text = sections[locator[0]].text
                if paragraph is not None:
                    if type(paragraph) is int:
                        paragraphs = re.split(r"\n\s*\n", text)
                        if not 0 <= paragraph < len(paragraphs):
                            raise ValueError("invalid_reviewed_paragraph_locator")
                    elif (
                        not isinstance(paragraph, str)
                        or not paragraph.startswith("before:")
                        or not paragraph.removeprefix("before:")
                        or paragraph.removeprefix("before:") not in text
                    ):
                        raise ValueError("invalid_reviewed_selection_marker")
        source_conflicts = decision.get("source_conflicts")
        if not isinstance(source_conflicts, list) or len(source_conflicts) > 32:
            raise ValueError("refresh_requires_explicit_source_conflict_review")
        for conflict in source_conflicts:
            if (
                not isinstance(conflict, dict)
                or set(conflict) != {"selection", "topic", "explanation"}
                or conflict["selection"] not in expected
                or not isinstance(conflict["explanation"], str)
                or not 10 <= len(conflict["explanation"]) <= 1000
            ):
                raise ValueError("invalid_reviewed_source_conflict")
            TypeAdapter(Topic).validate_python(conflict["topic"])
        source = next(
            s for s in manifest["sources"] if s["key"] == candidate["source_key"]
        )
        metadata = decision.get("metadata", {})
        allowed = {
            "title",
            "publication_date",
            "version_label",
            "applicability",
            "license_note",
        }
        if not isinstance(metadata, dict) or set(metadata) - allowed:
            raise ValueError(
                "refresh_cannot_silently_change_publisher_trust_or_identity"
            )
        if "applicability" in metadata:
            Applicability.model_validate(metadata["applicability"])
        source.update(metadata)
        source.update(
            checksum=candidate["candidate_checksum"],
            source_version=source.get("source_version", 1) + 1,
            retrieved_at=candidate["retrieved_at"],
            verified_at=datetime.now(UTC).isoformat(),
            local_path=str(data_path.resolve()),
            reviewed_extraction_limitations=candidate["extraction_limitations"],
            ingestion_status="REFRESH_REVIEWED_NOT_YET_INDEXED",
            reviewed_source_conflicts=source_conflicts,
        )
        manifest.setdefault("selection_overrides", {}).update(selections)
        target = candidate_path.parent / "reviewed-manifest.json"
        write_immutable(saved_review, (json.dumps(decision, indent=2) + "\n").encode())
        if not target.exists():
            write_immutable(target, (json.dumps(manifest, indent=2) + "\n").encode())
    else:
        target = candidate_path.parent / "review.json"
    write_immutable(
        candidate_path.parent / "review.json",
        (json.dumps(decision, indent=2) + "\n").encode(),
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=Path("docs/knowledge/n55-source-manifest.json")
    )
    commands = parser.add_subparsers(dest="command", required=True)
    acquire = commands.add_parser("stage")
    acquire.add_argument("source")
    acquire.add_argument("--root", type=Path, default=Path(".knowledge/refresh"))
    acquire.add_argument("--existing-local", action="store_true")
    approve = commands.add_parser("review")
    approve.add_argument("candidate", type=Path)
    approve.add_argument("decision", type=Path)
    args = parser.parse_args()
    try:
        target = (
            stage(
                args.manifest,
                args.source,
                args.root,
                existing_local=args.existing_local,
            )
            if args.command == "stage"
            else review(args.manifest, args.candidate, args.decision)
        )
        print(json.dumps({"refresh": "RECORDED", "artifact": str(target)}))
    except Exception:  # noqa: BLE001 - raw source/provider/config errors must not disclose secrets
        raise SystemExit(
            "Refresh stopped; approved corpus and index were not replaced."
        ) from None


if __name__ == "__main__":
    main()
