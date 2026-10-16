"""Trust, temporal applicability and immutable documentary provenance contracts."""

import hashlib
import json
import math
import re
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=160)]
Checksum = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Topic = Literal["architecture", "fuel", "boost", "thermal", "calibration", "diagnostics"]
KnowledgeNeed = Literal["principle", "normative_target"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class Trust(StrEnum):
    TIER_1_AUTHORITATIVE = "TIER_1_AUTHORITATIVE"
    TIER_2_STRONG_TECHNICAL = "TIER_2_STRONG_TECHNICAL"
    TIER_3_CURATED_INTERNAL = "TIER_3_CURATED_INTERNAL"
    TIER_4_COMMUNITY = "TIER_4_COMMUNITY"


class SourceStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


class Applicability(Model):
    make: Text | None = None
    model: Text | None = None
    platform: Text | None = None
    engine: Text | None = None
    engine_variant: Text | None = None
    year_from: int | None = Field(default=None, ge=1900, le=2200)
    year_to: int | None = Field(default=None, ge=1900, le=2200)
    transmission: Text | None = None
    region: Text | None = None
    subsystems: list[Text] = Field(default_factory=list, max_length=16)
    component: Text | None = None
    part_number: Text | None = None
    calibration: Literal["principle", "stock", "tune_specific"] = "principle"
    tuner: Text | None = None
    map_version: Text | None = None
    stage: Text | None = None
    fuel: Text | None = None
    hardware: list[Text] = Field(default_factory=list, max_length=16)
    effective_from: AwareDatetime | None = None
    effective_to: AwareDatetime | None = None

    @model_validator(mode="after")
    def ordered(self) -> "Applicability":
        if self.year_from and self.year_to and self.year_to < self.year_from:
            raise ValueError("Invalid model year interval")
        if self.effective_from and self.effective_to and self.effective_to <= self.effective_from:
            raise ValueError("Invalid applicability interval")
        return self


class VehicleScope(Model):
    vehicle_id: UUID
    configuration_id: UUID | None = None
    session_id: UUID | None = None
    as_of: AwareDatetime
    make: Text | None = None
    model: Text | None = None
    platform: Text | None = None
    engine: Text | None = None
    engine_variant: Text | None = None
    model_year: int | None = None
    transmission: Text | None = None
    region: Text | None = None
    calibration: Literal["unknown", "stock", "tuned"] = "unknown"
    tuner: Text | None = None
    map_version: Text | None = None
    stage: Text | None = None
    fuel: Text | None = None
    hardware: list[Text] = Field(default_factory=list, max_length=20)
    part_numbers: list[Text] = Field(default_factory=list, max_length=20)
    temporal_valid: bool = False


class Match(Model):
    status: Literal["APPLICABLE", "PARTIAL", "UNKNOWN", "INCOMPATIBLE"]
    score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(max_length=32)
    normative: bool = False


def match(app: Applicability, context: VehicleScope) -> Match:
    """Unknown metadata lowers specificity; it never establishes an exact calibration match."""
    reasons: list[str] = []
    incompatible = False
    specificity = 0.0
    if (
        context.calibration == "stock"
        and context.stage
        and re.sub(r"[^a-z0-9]", "", context.stage.casefold())
        not in {"stock", "oem", "factory", "stage0", "0"}
    ):
        reasons.append("conflicting_stock_stage_metadata")
    for field in (
        "make",
        "model",
        "platform",
        "engine",
        "engine_variant",
        "transmission",
        "region",
    ):
        expected, actual = getattr(app, field), getattr(context, field)
        if expected is None:
            continue
        if actual is None:
            reasons.append(f"unknown_{field}")
        elif expected.casefold() != actual.casefold():
            incompatible = True
            reasons.append(f"incompatible_{field}")
        else:
            specificity += 0.05
    if app.year_from or app.year_to:
        if context.model_year is None:
            reasons.append("unknown_model_year")
        elif (app.year_from and context.model_year < app.year_from) or (
            app.year_to and context.model_year > app.year_to
        ):
            reasons.append("incompatible_model_year")
            incompatible = True
    if (app.effective_from and context.as_of < app.effective_from) or (
        app.effective_to and context.as_of >= app.effective_to
    ):
        reasons.append("incompatible_effective_date")
        incompatible = True
    for field in ("tuner", "map_version", "stage", "fuel"):
        expected, actual = getattr(app, field), getattr(context, field)
        if expected:
            if actual is None:
                reasons.append(f"unknown_{field}")
            elif expected.casefold() != actual.casefold():
                reasons.append(f"incompatible_{field}")
                incompatible = True
    if app.part_number and app.part_number.casefold() not in {
        p.casefold() for p in context.part_numbers
    }:
        reasons.append("unverified_part_identity")
    if set(h.casefold() for h in app.hardware) - set(h.casefold() for h in context.hardware):
        reasons.append("unverified_hardware_requirements")
    if app.calibration == "stock" and context.calibration != "stock":
        reasons.append("stock_reference_not_tune_target")
    if app.calibration == "tune_specific" and (
        not app.tuner or not app.map_version or not context.tuner or not context.map_version
    ):
        reasons.append("exact_tune_unknown")
    if not context.temporal_valid:
        reasons.append("configuration_temporal_context_unknown")
    if not app.engine:
        reasons.append("generic_engine_principles_only")
    if incompatible:
        return Match(status="INCOMPATIBLE", score=0, reasons=reasons)
    if reasons:
        return Match(status="PARTIAL", score=min(0.7, 0.4 + specificity), reasons=reasons)
    return Match(status="APPLICABLE", score=min(1, 0.75 + specificity), reasons=[], normative=True)


class KnowledgeSource(Model):
    id: UUID
    publisher: Text
    canonical_url: str = Field(min_length=8, max_length=2048)
    source_type: Literal[
        "oem_training", "oem_service", "oem_press", "supplier", "tuner", "internal", "community"
    ]
    trust: Trust
    status: SourceStatus = SourceStatus.UNVERIFIED
    verified_at: AwareDatetime | None = None
    version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def valid_source(self) -> "KnowledgeSource":
        url = urlsplit(self.canonical_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            raise ValueError("A public HTTP(S) canonical source URL is required")
        if url.fragment or url.query:
            raise ValueError("Canonical source URLs must not contain credentials or query strings")
        if self.status == SourceStatus.VERIFIED and self.verified_at is None:
            raise ValueError("Source verification requires an explicit timestamp")
        if self.source_type == "community" and self.trust != Trust.TIER_4_COMMUNITY:
            raise ValueError("Community sources cannot be promoted to authoritative trust")
        return self


class DocumentVersion(Model):
    id: UUID
    document_id: UUID
    source_id: UUID
    source_version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=300)
    version_label: Text | None = None
    publication_date: date | None = None
    retrieved_at: AwareDatetime
    checksum: Checksum
    source_checksum: Checksum | None = None
    extraction_version: str = "selection-v1"
    language: str = Field(default="en", min_length=2, max_length=10)
    mime: Literal["application/pdf", "text/html", "text/plain", "text/markdown"]
    applicability: Applicability
    license_note: str = Field(min_length=5, max_length=1000)
    redistribution: Literal["metadata_only", "permitted", "synthetic"] = "metadata_only"
    status: Literal["PENDING", "EXTRACTED", "INDEXED", "FAILED", "QUARANTINED"] = "PENDING"
    limitations: list[Text] = Field(default_factory=list, max_length=32)


class NumericFact(Model):
    value: float = Field(allow_inf_nan=False, strict=True)
    unit: Text
    conditions: str = Field(min_length=5, max_length=500)
    original: str = Field(min_length=1, max_length=160)
    kind: Literal["descriptive", "stock_target", "tune_target", "service_limit"] = "descriptive"
    topic: Topic | None = None

    @model_validator(mode="after")
    def literal_support(self) -> "NumericFact":
        if self.kind != "descriptive" and self.topic is None:
            raise ValueError("Normative numeric review requires an explicit subsystem")
        numbers = re.findall(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?", self.original)
        if {Decimal(str(self.value))} != {
            Decimal(n.replace(",", ".")) for n in numbers
        } or not re.search(
            r"(?<!\w)" + re.escape(self.unit) + r"(?!\w)", self.original + " " + self.conditions
        ):
            raise ValueError("Reviewed numeric value and unit must occur in the source literal")
        return self


class DocumentChunk(Model):
    id: UUID
    version_id: UUID
    ordinal: int = Field(ge=0)
    page: int | None = Field(default=None, ge=1)
    section: str = Field(min_length=1, max_length=300)
    heading_path: list[Text] = Field(max_length=12)
    text: str = Field(min_length=20, max_length=12000)
    checksum: Checksum
    token_bound: int = Field(ge=1, le=16000)
    table: bool = False
    quality: Literal["reviewed", "extracted", "ambiguous"] = "extracted"
    numeric_facts: list[NumericFact] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def consistent(self) -> "DocumentChunk":
        if digest(self.text) != self.checksum or self.token_bound < len(self.text.encode()):
            raise ValueError("Chunk checksum/token bound mismatch")
        for fact in self.numeric_facts:
            if fact.original not in self.text or fact.conditions not in self.text:
                raise ValueError("Reviewed numeric facts must preserve source text and conditions")
        return self


class KnowledgeIndexVersion(Model):
    id: Text
    model: Literal["text-embedding-3-small"] = "text-embedding-3-small"
    dimensions: Literal[1536] = 1536
    chunker: str = "heading-table-v1"
    normalization: str = "utf8-whitespace-v1"
    embedding_version: str = "embedding-cache-v1"
    lexical: str = "postgres-simple-or-v2"
    ranking: str = "rrf-trust-applicability-identifiers-v3"
    corpus_checksum: Checksum
    created_at: AwareDatetime

    def cache_key(self, document_checksum: str, chunk_checksum: str) -> str:
        return digest(
            json.dumps(
                [
                    document_checksum,
                    chunk_checksum,
                    self.model,
                    self.dimensions,
                    self.chunker,
                    self.normalization,
                    self.embedding_version,
                ]
            )
        )


class SourceConflict(Model):
    id: UUID
    left_version_id: UUID
    right_version_id: UUID
    topic: Topic
    status: Literal["OPEN", "RESOLVED"] = "OPEN"
    explanation: str = Field(min_length=10, max_length=1000)


class KnowledgeEvidence(Model):
    id: UUID
    retrieval_run_id: UUID
    index_id: Text
    vehicle_id: UUID
    scope_hash: Checksum
    source: KnowledgeSource
    document: DocumentVersion
    chunk_id: UUID
    chunk_checksum: Checksum
    page: int | None
    section: str
    heading_path: list[str]
    snippet: str = Field(max_length=1000)
    applicability: Match
    lexical_score: float
    vector_score: float | None
    fused_score: float
    quality: Literal["reviewed", "extracted", "ambiguous"]
    numeric_facts: list[NumericFact] = Field(default_factory=list, max_length=32)
    conflict_ids: list[UUID] = Field(default_factory=list, max_length=16)

    @property
    def eligible(self) -> bool:
        return (
            self.source.status == SourceStatus.VERIFIED
            and self.document.status in {"EXTRACTED", "INDEXED"}
            and self.source.trust in {Trust.TIER_1_AUTHORITATIVE, Trust.TIER_2_STRONG_TECHNICAL}
            and self.applicability.normative
            and self.quality != "ambiguous"
            and not self.conflict_ids
        )


class RetrievalIntent(Model):
    query: str = Field(min_length=3, max_length=1000)
    topic: Topic
    need: KnowledgeNeed = "principle"
    top_k: int = Field(default=5, ge=1, le=5)
    source_tuner: Text | None = None


class RetrievalResult(Model):
    id: UUID
    index_id: Text
    scope: VehicleScope
    intent: RetrievalIntent
    evidence: list[KnowledgeEvidence] = Field(default_factory=list, max_length=5)
    knowledge_gaps: list[str] = Field(default_factory=list, max_length=16)
    source_conflicts: list[SourceConflict] = Field(default_factory=list, max_length=16)
    candidate_count: int = Field(ge=0)
    wrong_platform_rejections: int = Field(default=0, ge=0)
    vector_available: bool = False
    latency_seconds: float = Field(ge=0)
    timings: dict[str, float] = Field(default_factory=dict)


def digest(text: str | bytes) -> str:
    return hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()


def scope_hash(scope: VehicleScope) -> str:
    return digest(scope.model_dump_json())


def validate_vector(vector: list[float], dimensions: int = 1536) -> list[float]:
    if len(vector) != dimensions or any(not math.isfinite(v) for v in vector):
        raise ValueError("Invalid embedding vector")
    if not any(vector):
        raise ValueError("Zero embedding vector")
    return vector


class KnowledgeClaim(Model):
    id: UUID
    evidence_id: UUID
    classification: Literal["DOCUMENTARY_REFERENCE"] = "DOCUMENTARY_REFERENCE"
    excerpt: str = Field(min_length=1, max_length=350)
    normative: bool = False
    numeric_fact: NumericFact | None = None


class KnowledgeReport(Model):
    schema_version: Literal["1.0"] = "1.0"
    request_type: Literal[
        "KNOWLEDGE_FACT",
        "HYBRID_COMPARISON",
        "TECHNICAL_KNOWLEDGE_INSUFFICIENT",
        "VEHICLE_EVIDENCE_INSUFFICIENT",
    ]
    retrieval: RetrievalResult
    claims: list[KnowledgeClaim] = Field(default_factory=list, max_length=5)
